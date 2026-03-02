# wui/lib/key_value_store.py
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Optional, Type, TypeVar

import redis
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class StoreConfig:
    """Configuration for a Redis/Valkey connection."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    decode_responses: bool = True
    prefix: str = "bbl-wui"


def _env_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def make_store_from_env(prefix: str = "bbl-wui") -> "KeyValueStore":
    """
    Create store from environment variables.

    Supported env vars (with prefix):
      - {PREFIX}_REDIS_HOST
      - {PREFIX}_REDIS_PORT
      - {PREFIX}_REDIS_DB
      - {PREFIX}_REDIS_PASSWORD
      - {PREFIX}_REDIS_SSL
      - {PREFIX}_REDIS_URL   (optional, overrides host/port/db/password/ssl)

    Example:
      BBL_WUI_REDIS_HOST=localhost
      BBL_WUI_REDIS_PORT=6379
      BBL_WUI_REDIS_DB=0
    """
    p = prefix.upper().replace("-", "_")

    url = os.getenv(f"{p}_REDIS_URL")
    if url:
        client = redis.Redis.from_url(url, decode_responses=True)
        return KeyValueStore(client=client, prefix=prefix)

    host = os.getenv(f"{p}_REDIS_HOST", "localhost")
    port = int(os.getenv(f"{p}_REDIS_PORT", "6379"))
    db = int(os.getenv(f"{p}_REDIS_DB", "0"))
    password = os.getenv(f"{p}_REDIS_PASSWORD") or None
    ssl = _env_bool(os.getenv(f"{p}_REDIS_SSL"), default=False)

    cfg = StoreConfig(
        host=host,
        port=port,
        db=db,
        password=password,
        ssl=ssl,
        decode_responses=True,
        prefix=prefix,
    )
    return KeyValueStore.from_config(cfg)


class KeyValueStore:
    """
    Thin wrapper around Redis/Valkey with:
      - namespaced keys (prefix)
      - JSON dict helpers
      - typed Pydantic helpers (save_model/load_model)
      - domain helpers for your instance keys
    """

    def __init__(self, client: redis.Redis, prefix: str = "bbl-wui"):
        self._redis = client
        self._prefix = prefix

    @classmethod
    def from_config(cls, cfg: StoreConfig) -> "KeyValueStore":
        client = redis.Redis(
            host=cfg.host,
            port=cfg.port,
            db=cfg.db,
            password=cfg.password,
            ssl=cfg.ssl,
            decode_responses=cfg.decode_responses,
        )
        return cls(client=client, prefix=cfg.prefix)

    # ----------------------------
    # Key helpers
    # ----------------------------
    def _k(self, key: str) -> str:
        """Apply store prefix namespace."""
        return f"{self._prefix}:{key}"

    def key_start_params(self, instance_name: str) -> str:
        return self._k(f"instance:{instance_name}:start_params")

    def key_runtime_state(self, instance_name: str) -> str:
        return self._k(f"instance:{instance_name}:runtime_state")

    # ----------------------------
    # Low-level helpers
    # ----------------------------
    def delete(self, key: str) -> int:
        return int(self._redis.delete(key))

    def get_raw(self, key: str) -> Optional[str]:
        return self._redis.get(key)

    def set_raw(self, key: str, value: str) -> None:
        self._redis.set(key, value)

    # ----------------------------
    # JSON dict helpers
    # ----------------------------
    def set_json(self, key: str, value: dict[str, Any]) -> None:
        self._redis.set(key, json.dumps(value))

    def get_json(self, key: str) -> Optional[dict[str, Any]]:
        raw = self._redis.get(key)
        if not raw:
            return None
        return json.loads(raw)

    # ----------------------------
    # Typed Pydantic helpers
    # ----------------------------
    def save_model(self, key: str, model: BaseModel) -> None:
        """Store a pydantic model as JSON string."""
        self._redis.set(key, model.model_dump_json())

    def load_model(self, key: str, model_cls: Type[T], default: T) -> T:
        """Load a pydantic model from JSON; fallback to default on missing/invalid."""
        raw = self._redis.get(key)
        if not raw:
            return default
        try:
            return model_cls.model_validate_json(raw)
        except Exception:
            return default

    # ----------------------------
    # Domain: start_params (legacy dict API)
    # ----------------------------
    def save_start_params(self, instance_name: str, start_params: dict[str, Any]) -> None:
        key = self.key_start_params(instance_name)
        self.set_json(key, start_params)

    def load_start_params(self, instance_name: str, default: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        key = self.key_start_params(instance_name)
        data = self.get_json(key)
        if data is None or not isinstance(data, dict):
            return default or {}
        return data

    # ----------------------------
    # Domain: runtime_state (legacy dict API)
    # ----------------------------
    def save_runtime_state(self, instance_name: str, state: dict[str, Any]) -> None:
        key = self.key_runtime_state(instance_name)
        self.set_json(key, state)

    def load_runtime_state(self, instance_name: str, default: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        key = self.key_runtime_state(instance_name)
        data = self.get_json(key)
        if data is None or not isinstance(data, dict):
            return default or {}
        return data

    def update_runtime_state(self, instance_name: str, patch: dict[str, Any]) -> dict[str, Any]:
        current = self.load_runtime_state(instance_name, default={})
        updated = {**current, **patch}
        self.save_runtime_state(instance_name, updated)
        return updated

    # ----------------------------
    # NEW: cache keys for session-info
    # ----------------------------
    def key_session_info_cache(self, instance_name: str) -> str:
        return self._k(f"instance:{instance_name}:session_info_cache")

    def key_session_info_meta(self, instance_name: str) -> str:
        return self._k(f"instance:{instance_name}:session_info_meta")

    # ----------------------------
    # NEW: JSON helpers with TTL
    # ----------------------------
    def set_json_ex(self, key: str, value: dict[str, Any], ex: int) -> None:
        """Set JSON with TTL (seconds)."""
        self._redis.set(key, json.dumps(value, ensure_ascii=False), ex=int(ex))

    def set_raw_ex(self, key: str, value: str, ex: int) -> None:
        self._redis.set(key, value, ex=int(ex))