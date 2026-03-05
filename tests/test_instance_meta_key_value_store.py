import os
import time
import uuid
import pytest

from dashboard.services.key_value_store import make_store_from_env
from dashboard.models.bbl_models import InstanceStatus


@pytest.fixture
def store():
    prefix = os.getenv("BBL_DB_PREFIX", "bbl-db")
    return make_store_from_env(prefix=prefix)


@pytest.fixture
def instance_name(store):
    name = f"pytest_{uuid.uuid4().hex[:8]}"
    yield name

    # cleanup after test
    pattern = store._k(f"instance:{name}:*")
    for key in store._redis.scan_iter(pattern):
        store._redis.delete(key)


def test_update_and_load_instance_meta(store, instance_name):
    now = int(time.time())

    meta = store.update_instance_meta(
        instance_name,
        {
            "status": InstanceStatus.STOPPED,
            "created_ts": now,
            "config_json_str": '{"foo":"bar"}',
            "startup_params": {"logging": True},
        },
    )

    assert meta.name == instance_name
    assert meta.status == InstanceStatus.STOPPED
    assert meta.created_ts == now
    assert meta.startup_params == {"logging": True}


def test_atomic_patch(store, instance_name):
    store.update_instance_meta(instance_name, {"status": InstanceStatus.STOPPED})

    meta = store.update_instance_meta(
        instance_name,
        {"status": InstanceStatus.STARTED, "started_ts": 1234},
    )

    assert meta.status == InstanceStatus.STARTED
    assert meta.started_ts == 1234


def test_summary_ttl(store, instance_name):
    store.set_session_summary(instance_name, {"sessions": 1}, ex=1)

    assert store.get_session_summary(instance_name) == {"sessions": 1}

    time.sleep(1.2)

    assert store.get_session_summary(instance_name) is None