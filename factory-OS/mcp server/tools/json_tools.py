"""JSON parsing and nested-value helpers."""
import json


def parse_json(data: str):
    if not isinstance(data, str):
        raise ValueError("data must be a JSON string")
    return json.loads(data)


def pretty_json(data: str) -> str:
    return json.dumps(parse_json(data), indent=2, ensure_ascii=False)


def get_json_value(data: str, path: str):
    current = parse_json(data)
    if not path.strip():
        return current
    for part in path.strip(".").split("."):
        if isinstance(current, dict):
            if part not in current:
                return {"found": False, "value": None}
            current = current[part]
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return {"found": False, "value": None}
        else:
            return {"found": False, "value": None}
    return {"found": True, "value": current}


def set_json_value(data: str, path: str, value_json: str) -> str:
    current = parse_json(data)
    value = parse_json(value_json)
    parts = [p for p in path.strip(".").split(".") if p]
    if not parts or not isinstance(current, dict):
        raise ValueError("Path must be non-empty and the JSON root must be an object")
    target = current
    for part in parts[:-1]:
        if part not in target:
            target[part] = {}
        if not isinstance(target[part], dict):
            raise ValueError(f"Intermediate path '{part}' is not an object")
        target = target[part]
    target[parts[-1]] = value
    return json.dumps(current, indent=2, ensure_ascii=False)


def delete_json_value(data: str, path: str) -> str:
    current = parse_json(data)
    parts = [p for p in path.strip(".").split(".") if p]
    if not parts or not isinstance(current, dict):
        raise ValueError("Path must be non-empty and the JSON root must be an object")
    target = current
    for part in parts[:-1]:
        if part not in target or not isinstance(target[part], dict):
            raise KeyError(path)
        target = target[part]
    if parts[-1] not in target:
        raise KeyError(path)
    del target[parts[-1]]
    return json.dumps(current, indent=2, ensure_ascii=False)
