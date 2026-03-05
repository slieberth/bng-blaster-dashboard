# dashboard/services/key_value_store.py
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Optional, Dict

import redis
from pydantic import TypeAdapter

from dashboard.models.bbl_models import InstanceMeta


@dataclass(frozen=True)
class StoreConfig:
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    decode_responses: bool = True
    prefix: str = "bbl-db"
    summaries_ttl_sec: int = 60


def _env_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def make_store_from_env(prefix: str = "bbl-db") -> "KeyValueStore":
    p = prefix.upper().replace("-", "_")

    url = os.getenv(f"{p}_REDIS_URL")
    ttl = int(os.getenv(f"{p}_REDIS_SUMMARIES_TTL_SEC", "60"))

    if url:
        client = redis.Redis.from_url(url, decode_responses=True)
        return KeyValueStore(client=client, prefix=prefix, summaries_ttl_sec=ttl)

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
        summaries_ttl_sec=ttl,
    )
    return KeyValueStore.from_config(cfg)


class KeyValueStore:
    # Atomic hash patch (HSET + HDEL) via Lua
    _LUA_HPATCH = """
    local patch = cjson.decode(ARGV[1])
    local dels = cjson.decode(ARGV[2])

    for k, v in pairs(patch) do
        redis.call('HSET', KEYS[1], k, v)
    end
    for i, k in ipairs(dels) do
        redis.call('HDEL', KEYS[1], k)
    end
    return 1
    """

    _JSON_FIELDS = {"startup_params"}  # summaries will be separate keys with TTL
    _INT_FIELDS = {"created_ts", "started_ts", "stopped_ts", "last_seen_ts"}

    def __init__(self, client: redis.Redis, prefix: str = "bbl-db", *, summaries_ttl_sec: int = 60):
        self._redis = client
        self._prefix = prefix
        self._summaries_ttl = int(summaries_ttl_sec)

        self._hpatch = self._redis.register_script(self._LUA_HPATCH)
        self._meta_adapter = TypeAdapter(InstanceMeta)

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
        return cls(client=client, prefix=cfg.prefix, summaries_ttl_sec=cfg.summaries_ttl_sec)

    # ----------------------------
    # Key helpers
    # ----------------------------
    def _k(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    def key_instance_meta(self, instance_name: str) -> str:
        return self._k(f"instance:{instance_name}:meta")

    def key_session_summary(self, instance_name: str) -> str:
        return self._k(f"instance:{instance_name}:session_summary")

    def key_stream_summary(self, instance_name: str) -> str:
        return self._k(f"instance:{instance_name}:stream_summary")

    # ----------------------------
    # Instance Meta (HASH)
    # ----------------------------
    def load_instance_meta(self, instance_name: str) -> InstanceMeta:
        key = self.key_instance_meta(instance_name)
        raw = self._redis.hgetall(key)  # dict[str,str]
        if not raw:
            return InstanceMeta(name=instance_name)

        data = self._decode_hash(raw)
        data.setdefault("name", instance_name)
        return self._meta_adapter.validate_python(data)

    def update_instance_meta(self, instance_name: str, patch: dict[str, Any]) -> InstanceMeta:
        key = self.key_instance_meta(instance_name)
        patch = dict(patch)
        patch.setdefault("name", instance_name)

        mapping, dels = self._encode_patch(patch)
        self._hpatch(keys=[key], args=[json.dumps(mapping), json.dumps(dels)])

        return self.load_instance_meta(instance_name)

    def save_instance_meta(self, meta: InstanceMeta) -> None:
        # overwrite = just patch all non-none fields
        data = self._meta_adapter.dump_python(meta, exclude_none=True)
        self.update_instance_meta(meta.name, data)

    # ----------------------------
    # Summaries with TTL (separate keys)
    # ----------------------------
    def set_session_summary(self, instance_name: str, summary: dict[str, Any], *, ex: Optional[int] = None) -> None:
        key = self.key_session_summary(instance_name)
        self._redis.set(key, json.dumps(summary, ensure_ascii=False), ex=int(ex or self._summaries_ttl))

    def get_session_summary(self, instance_name: str) -> Optional[dict[str, Any]]:
        raw = self._redis.get(self.key_session_summary(instance_name))
        return json.loads(raw) if raw else None

    def set_stream_summary(self, instance_name: str, summary: dict[str, Any], *, ex: Optional[int] = None) -> None:
        key = self.key_stream_summary(instance_name)
        self._redis.set(key, json.dumps(summary, ensure_ascii=False), ex=int(ex or self._summaries_ttl))

    def get_stream_summary(self, instance_name: str) -> Optional[dict[str, Any]]:
        raw = self._redis.get(self.key_stream_summary(instance_name))
        return json.loads(raw) if raw else None

    # ----------------------------
    # Internal encode/decode
    # ----------------------------
    def _encode_patch(self, patch: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
        mapping: dict[str, str] = {}
        dels: list[str] = []

        for k, v in patch.items():
            if v is None:
                dels.append(k)
                continue

            # Enums like InstanceStatus
            if hasattr(v, "value") and isinstance(getattr(v, "value"), str):
                mapping[k] = v.value
                continue

            if k in self._JSON_FIELDS and isinstance(v, (dict, list)):
                mapping[k] = json.dumps(v, ensure_ascii=False, separators=(",", ":"))
                continue

            if isinstance(v, (dict, list)):
                mapping[k] = json.dumps(v, ensure_ascii=False, separators=(",", ":"))
                continue

            mapping[k] = str(v)

        return mapping, dels

    def _decode_hash(self, raw: Dict[str, str]) -> dict[str, Any]:
        out: dict[str, Any] = dict(raw)

        for k in list(out.keys()):
            v = out[k]
            if k in self._INT_FIELDS:
                try:
                    out[k] = int(v)
                except Exception:
                    pass
            elif k in self._JSON_FIELDS:
                try:
                    out[k] = json.loads(v)
                except Exception:
                    pass

        return out