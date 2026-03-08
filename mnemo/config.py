"""Configuration loading and validation for Mnemo."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


class MnemoConfigError(ValueError):
    """Raised when configuration is missing or invalid."""


@dataclass(slots=True)
class InjectConfig:
    """Injection-related configuration."""

    enabled: bool = False
    debounce_hash: bool = True
    skip_timestamp_fields: bool = True
    skip_fields: list[str] = field(default_factory=list)
    mode: str = "primary"


@dataclass(slots=True)
class MnemoConfig:
    """Root config model for Mnemo."""

    schema_version: str
    project: str
    enabled: bool
    feature_flags: dict[str, bool]
    inject: InjectConfig
    lanes: dict[str, Any]
    priority: list[str]
    extra: dict[str, Any] = field(default_factory=dict)


def _atomic_write(path: Path, data: str) -> None:
    """Write file atomically using .tmp + replace."""

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(path)


def _apply_env_overrides(payload: dict[str, Any]) -> dict[str, Any]:
    """Apply MNEMO_* environment variables into nested config."""

    out = dict(payload)
    for key, value in os.environ.items():
        if not key.startswith("MNEMO_"):
            continue
        sub = key[len("MNEMO_") :].lower()
        parts = sub.split("__")
        ref: dict[str, Any] = out
        for p in parts[:-1]:
            if p not in ref or not isinstance(ref[p], dict):
                ref[p] = {}
            ref = ref[p]
        parsed: Any = value
        lv = value.lower()
        if lv in {"true", "false"}:
            parsed = lv == "true"
        else:
            try:
                parsed = int(value)
            except ValueError:
                try:
                    parsed = float(value)
                except ValueError:
                    parsed = value
        ref[parts[-1]] = parsed
    return out


def _validate(payload: dict[str, Any]) -> MnemoConfig:
    """Validate raw config and return typed dataclass."""

    required = ["schema_version", "project", "inject"]
    missing = [k for k in required if k not in payload]
    if missing:
        raise MnemoConfigError(f"Config validation failed: missing fields {missing}")
    inject_raw = payload.get("inject")
    if not isinstance(inject_raw, dict):
        raise MnemoConfigError("Config validation failed: inject must be object")
    mode = inject_raw.get("mode", "primary")
    if mode not in {"readonly", "dualwrite", "primary"}:
        raise MnemoConfigError(f"Config validation failed: inject.mode invalid: {mode}")

    inject = InjectConfig(
        enabled=bool(inject_raw.get("enabled", False)),
        debounce_hash=bool(inject_raw.get("debounce_hash", True)),
        skip_timestamp_fields=bool(inject_raw.get("skip_timestamp_fields", True)),
        skip_fields=list(inject_raw.get("skip_fields", [])),
        mode=mode,
    )
    known = {
        "schema_version",
        "project",
        "enabled",
        "feature_flags",
        "inject",
        "lanes",
        "priority",
    }
    extra = {k: v for k, v in payload.items() if k not in known}
    return MnemoConfig(
        schema_version=str(payload["schema_version"]),
        project=str(payload["project"]),
        enabled=bool(payload.get("enabled", True)),
        feature_flags=dict(payload.get("feature_flags", {})),
        inject=inject,
        lanes=dict(payload.get("lanes", {})),
        priority=list(payload.get("priority", ["urgent", "preconscious", "snapshot"])),
        extra=extra,
    )


def load_config(workspace: Path) -> MnemoConfig:
    """Load and validate config from config/mnemo.default.json with env override."""

    config_path = workspace / "config" / "mnemo.default.json"
    if not config_path.exists():
        raise MnemoConfigError(f"Config file not found: {config_path}")
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MnemoConfigError(f"Config JSON parse failed: {exc}") from exc
    payload = _apply_env_overrides(payload)
    return _validate(payload)


def dump_config_snapshot(workspace: Path, config: MnemoConfig) -> None:
    """Persist a runtime config snapshot in state directory."""

    target = workspace / "state" / "config.runtime.json"
    _atomic_write(target, json.dumps(asdict(config), ensure_ascii=False, indent=2) + "\n")
