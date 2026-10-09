"""Cost-aware LLM router with provider fallback for Groq, Gemini, and OpenRouter."""
from __future__ import annotations
import os
import re
import time
from dataclasses import dataclass
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Model:
    name: str
    provider: str
    base_url: str
    api_key_env: str
    tier: str
    capabilities: tuple[str, ...] = ()

    @property
    def api_key(self) -> str:
        return os.getenv(self.api_key_env, "").strip()

# IDs are configurable because provider catalogues and availability can change.
MODELS = [
    Model(os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
          "groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY",
          "low", ("general", "coding", "simple", "fast")),
    Model(os.getenv("OPENROUTER_LOW_MODEL", "deepseek/deepseek-v4-flash"),
          "openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY",
          "low", ("general", "simple", "fast")),
    Model(os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
          "gemini", "https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY",
          "medium", ("general", "coding", "reasoning", "fast")),
    Model(os.getenv("OPENROUTER_MEDIUM_MODEL", "z-ai/glm-5.3-flash"),
          "openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY",
          "medium", ("general", "coding", "agents")),
    Model(os.getenv("OPENROUTER_HEAVY_MODEL", "xiaomi/mimo-v2.6-pro"),
          "openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY",
          "heavy", ("coding", "reasoning", "agents", "complex")),
    Model(os.getenv("OPENROUTER_HEAVY_BACKUP_MODEL", "deepseek/deepseek-v4-pro"),
          "openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY",
          "heavy", ("coding", "reasoning", "complex")),
]

HEAVY_TERMS = {
    "architecture", "debug", "debugging", "refactor", "security audit",
    "production", "distributed", "multi-agent", "mcp server", "design a system",
    "optimize", "algorithm", "prove", "research", "compare tradeoffs",
    "root cause", "migration", "scalable", "concurrency", "reasoning",
}
MEDIUM_TERMS = {
    "write code", "implement", "function", "class", "api", "database",
    "explain code", "plan", "summarize", "analyze", "analyse", "workflow",
}

def classify_prompt(prompt: str) -> dict[str, Any]:
    """Cheap deterministic heuristic; no extra LLM call is needed to route."""
    text = prompt.strip().lower()
    words = re.findall(r"\w+", text)
    score = 0
    reasons = []
    if len(words) > 180:
        score += 2; reasons.append("long prompt")
    elif len(words) > 70:
        score += 1; reasons.append("moderately long prompt")
    for term in HEAVY_TERMS:
        if term in text:
            score += 2; reasons.append(f"complexity signal: {term}")
    for term in MEDIUM_TERMS:
        if term in text:
            score += 1; reasons.append(f"task signal: {term}")
    if re.search(r"```|traceback|stack trace|exception|error:", text):
        score += 2; reasons.append("code or error analysis")
    if re.search(r"\b(step[- ]by[- ]step|multiple files|end[- ]to[- ]end|full project)\b", text):
        score += 2; reasons.append("multi-step deliverable")
    if len(words) <= 12 and not any(term in text for term in HEAVY_TERMS | MEDIUM_TERMS):
        score = min(score, 0)
    tier = "heavy" if score >= 4 else "medium" if score >= 2 else "low"
    return {"tier": tier, "score": score, "reasons": reasons or ["short/general prompt"]}

def _candidates(tier: str) -> list[Model]:
    available = [m for m in MODELS if m.api_key]
    preferred = {"low": ["low", "medium", "heavy"],
                 "medium": ["medium", "low", "heavy"],
                 "heavy": ["heavy", "medium", "low"]}[tier]
    ordered = []
    for t in preferred:
        ordered.extend(m for m in available if m.tier == t and m not in ordered)
    return ordered

def _chat(model: Model, messages: list[dict[str, str]], temperature: float,
          max_tokens: int, timeout: int) -> str:
    headers = {
        "Authorization": f"Bearer {model.api_key}",
        "Content-Type": "application/json",
    }
    if model.provider == "openrouter":
        headers["HTTP-Referer"] = os.getenv("OPENROUTER_SITE_URL", "http://localhost")
        headers["X-Title"] = os.getenv("OPENROUTER_APP_NAME", "Factory OS MCP")
    payload = {
        "model": model.name,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    response = requests.post(
        f"{model.base_url.rstrip('/')}/chat/completions",
        headers=headers, json=payload, timeout=timeout,
    )
    if response.status_code >= 400:
        # Do not include API keys in surfaced error text.
        raise RuntimeError(f"{model.provider}/{model.name} returned HTTP {response.status_code}: {response.text[:500]}")
    data = response.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"{model.provider}/{model.name} returned no choices.")
    return choices[0].get("message", {}).get("content", "") or ""

def smart_chat(prompt: str, system_prompt: str = "",
               temperature: float = 0.2, max_tokens: int = 1200,
               force_tier: str = "auto", timeout: int = 60) -> dict[str, Any]:
    """Route a prompt to a cost-appropriate model and try alternate configured models on failure."""
    if not prompt.strip():
        raise ValueError("prompt cannot be empty")
    if force_tier not in {"auto", "low", "medium", "heavy"}:
        raise ValueError("force_tier must be auto, low, medium, or heavy")
    classification = classify_prompt(prompt)
    tier = classification["tier"] if force_tier == "auto" else force_tier
    candidates = _candidates(tier)
    if not candidates:
        missing = [m.api_key_env for m in MODELS]
        raise RuntimeError(
            "No configured provider API key is available. Set at least one of: "
            + ", ".join(dict.fromkeys(missing))
        )
    messages = []
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})
    messages.append({"role": "user", "content": prompt})
    errors = []
    for model in candidates:
        started = time.perf_counter()
        try:
            answer = _chat(model, messages, max(0, min(temperature, 2)),
                           max(1, min(max_tokens, 8192)), max(5, min(timeout, 180)))
            return {
                "answer": answer,
                "selected_tier": tier,
                "classified_tier": classification["tier"],
                "classification_score": classification["score"],
                "classification_reasons": classification["reasons"],
                "provider": model.provider,
                "model": model.name,
                "latency_ms": round((time.perf_counter() - started) * 1000),
                "fallback_used": len(errors) > 0,
                "fallback_errors": errors,
            }
        except Exception as exc:
            errors.append(f"{model.provider}/{model.name}: {str(exc)[:350]}")
    raise RuntimeError("All configured models failed. " + " | ".join(errors))

def model_status() -> list[dict[str, str]]:
    return [
        {"provider": m.provider, "model": m.name, "tier": m.tier,
         "configured": "yes" if m.api_key else "no"}
        for m in MODELS
    ]
