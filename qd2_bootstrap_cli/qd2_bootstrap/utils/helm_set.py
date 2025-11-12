from typing import Any, Dict, List

def _escape_value(v: str) -> str:
    """
    Escape characters that break Helm --set parsing and quote when needed.
    """
    needs_quotes = False
    if "," in v:
        v = v.replace(",", r"\,")
    for ch in [" ", "=", ":", "{", "}", "[", "]", '"', "'"]:
        if ch in v:
            needs_quotes = True
            break
    if needs_quotes and not (v.startswith('"') and v.endswith('"')):
        v = f'"{v}"'
    return v

def _to_scalar(v: Any) -> str:
    """
    Convert Python value to a Helm --set scalar string.
    Lists/dicts inline are best-effort; for complex structures a values file is safer,
    but we stick to --set as requested.
    """
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        return _escape_value(v)
    if isinstance(v, list):
        items = ",".join(_to_scalar(x).strip('"') for x in v)
        return "{" + items + "}"
    if isinstance(v, dict):
        parts = []
        for k, val in v.items():
            val_str = _to_scalar(val).strip('"')
            parts.append(f"{k}:{val_str}")
        inner = ",".join(parts)
        return "{" + inner + "}"
    return _escape_value(str(v))

def flatten_to_set_expressions(values: Dict[str, Any], prefix: str = "") -> List[str]:
    """
    Flatten nested dict into Helm --set expressions (dot-notation):
      {'a': {'b': 1}, 'c': 'x'} -> ['a.b=1', 'c=x']
    """
    out: List[str] = []
    def walk(node: Any, path: List[str]):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, path + [k])
        else:
            key = ".".join(path)
            out.append(f"{key}={_to_scalar(node)}")
    walk(values, [prefix] if prefix else [])
    return out
