import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings

def get_tier_cost(tier: str) -> float:
    base = {"exam": 0.00073, "practice": 0.00036, "budget": 0.00009}.get(tier, 0.00036)
    if settings.llm_provider == "gemini":
        return base * 8.6
    return base

_lock = threading.Lock()
_store_path = Path(settings.storage_dir) / "budget.json"


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _load() -> dict:
    if _store_path.exists():
        try:
            return json.loads(_store_path.read_text())
        except Exception:
            return {}
    return {}


def _save(data: dict) -> None:
    _store_path.parent.mkdir(parents=True, exist_ok=True)
    _store_path.write_text(json.dumps(data))


def record(tier: str) -> None:
    cost = get_tier_cost(tier)
    with _lock:
        data = _load()
        key = _month_key()
        data[key] = data.get(key, 0.0) + cost
        _save(data)


def current_month_total() -> float:
    return _load().get(_month_key(), 0.0)


def fraction() -> float:
    cap = settings.monthly_spend_cap_usd
    return current_month_total() / cap if cap > 0 else 0.0


def resolve_tier(requested: str) -> str:
    frac = fraction()
    if frac >= 0.95:
        return "budget"
    if frac >= 0.90:
        return "budget" if requested == "practice" else "practice"
    return requested
