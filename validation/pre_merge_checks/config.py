import copy
import json
import os
from pathlib import Path


DEFAULT_CONFIG = {
    "policy": {
        "required_sections": [
            "Perustiedot",
            "Kuvaus",
            "Vaikutusanalyysi",
        ],
        "required_approvers": {
            "1": 1,
            "2": 2,
            "3": 3,
        },
        "allowed_environments": [
            "dev",
            "staging",
            "production",
        ],
        "freeze_periods": [],
        "rule_toggles": {
            "require_risk_justification": True,
            "require_rollback_for_class_2_3": True,
            "require_rollback_test_for_class_3": True,
            "require_test_plan_for_class_2_3": True,
            "require_freeze_check_for_class_3": True,
            "warn_on_absolute_paths": True,
        },
    }
}


def _deep_merge(base, override):
    merged = copy.deepcopy(base)
    if not isinstance(override, dict):
        return merged

    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _load_raw_config(path):
    if not path.exists():
        return {}

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return {}

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore

            loaded = yaml.safe_load(content)
            return loaded if isinstance(loaded, dict) else {}
        except Exception:
            return {}


def _normalize_required_approvers(raw):
    defaults = {1: 1, 2: 2, 3: 3}
    if not isinstance(raw, dict):
        return defaults

    normalized = {}
    for key, value in raw.items():
        try:
            normalized[int(key)] = int(value)
        except (TypeError, ValueError):
            continue

    for rk, rv in defaults.items():
        normalized.setdefault(rk, rv)

    return normalized


def _normalize_freeze_periods(raw):
    periods = []
    if not isinstance(raw, list):
        return periods

    for item in raw:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            start, end = item
            if isinstance(start, str) and isinstance(end, str):
                periods.append((start, end))
        elif isinstance(item, dict):
            start = item.get("start")
            end = item.get("end")
            if isinstance(start, str) and isinstance(end, str):
                periods.append((start, end))
    return periods


def load_config(config_path=None):
    candidates = []
    if config_path:
        candidates.append(Path(config_path))

    env_path = os.getenv("GATEHOUSE_CONFIG")
    if env_path:
        candidates.append(Path(env_path))

    candidates.append(Path.cwd() / "gatehouse.yaml")
    candidates.append(Path(__file__).resolve().parents[2] / "gatehouse.yaml")

    raw = {}
    for candidate in candidates:
        if candidate.exists():
            raw = _load_raw_config(candidate)
            break

    merged = _deep_merge(DEFAULT_CONFIG, raw)
    return merged


def get_required_sections(config):
    sections = config.get("policy", {}).get("required_sections")
    if isinstance(sections, list) and sections:
        return [s for s in sections if isinstance(s, str) and s.strip()]
    return DEFAULT_CONFIG["policy"]["required_sections"]


def get_allowed_environments(config):
    envs = config.get("policy", {}).get("allowed_environments")
    if isinstance(envs, list) and envs:
        clean = [str(e).strip().lower() for e in envs if str(e).strip()]
        return clean if clean else DEFAULT_CONFIG["policy"]["allowed_environments"]
    return DEFAULT_CONFIG["policy"]["allowed_environments"]


def get_required_approvers(config):
    raw = config.get("policy", {}).get("required_approvers", {})
    return _normalize_required_approvers(raw)


def get_freeze_periods(config):
    raw = config.get("policy", {}).get("freeze_periods", [])
    return _normalize_freeze_periods(raw)


def get_rule_toggle(config, toggle_name, default=True):
    toggles = config.get("policy", {}).get("rule_toggles", {})
    value = toggles.get(toggle_name, default)
    return bool(value)
