import json
from llm_router import smart_chat, classify_prompt, model_status

def register(mcp):
    @mcp.tool()
    def llm_smart_chat(prompt: str, system_prompt: str = "",
                       temperature: float = 0.2, max_tokens: int = 1200,
                       force_tier: str = "auto") -> str:
        """Ask the routed LLM. auto selects low/medium/heavy by prompt complexity and falls back on provider errors. force_tier can be auto, low, medium, heavy."""
        return json.dumps(smart_chat(prompt, system_prompt, temperature, max_tokens, force_tier), ensure_ascii=False)

    @mcp.tool()
    def llm_classify_prompt(prompt: str) -> str:
        """Preview the estimated prompt complexity and chosen tier without making an LLM request."""
        return json.dumps(classify_prompt(prompt), ensure_ascii=False)

    @mcp.tool()
    def llm_list_models() -> str:
        """Show configured model IDs and whether their provider API keys are present."""
        return json.dumps(model_status(), ensure_ascii=False, indent=2)
