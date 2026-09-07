from dataclasses import dataclass


@dataclass(frozen=True)
class ResolvedLocation:
    name: str
    timezone: str


_ALIASES = {
    "魔都": ("上海", "Asia/Shanghai"),
    "沪": ("上海", "Asia/Shanghai"),
    "帝都": ("北京", "Asia/Shanghai"),
    "京": ("北京", "Asia/Shanghai"),
    "广州": ("广州", "Asia/Shanghai"),
    "深圳": ("深圳", "Asia/Shanghai"),
    "杭州": ("杭州", "Asia/Shanghai"),
    "东京": ("东京", "Asia/Tokyo"),
    "纽约": ("纽约", "America/New_York"),
    "伦敦": ("伦敦", "Europe/London"),
    "巴黎": ("巴黎", "Europe/Paris"),
}

def resolve_location(value: str) -> ResolvedLocation:
    cleaned = value.strip()
    if cleaned in _ALIASES:
        name, timezone = _ALIASES[cleaned]
        return ResolvedLocation(name, timezone)
    timezone = "Asia/Shanghai"
    if any(token in cleaned for token in ("东京", "日本")):
        timezone = "Asia/Tokyo"
    elif any(token in cleaned for token in ("纽约", "美国")):
        timezone = "America/New_York"
    elif any(token in cleaned for token in ("伦敦", "英国")):
        timezone = "Europe/London"
    elif any(token in cleaned for token in ("巴黎", "法国")):
        timezone = "Europe/Paris"
    return ResolvedLocation(cleaned, timezone)
