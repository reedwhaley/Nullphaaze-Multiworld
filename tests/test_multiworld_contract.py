"""Private session/receipt boundaries, independent of game media and hardware."""
import base64
import hashlib
import json
import uuid

import pytest

from randovania.game_connection.prime3_multiworld_protocol import (
    MultiworldStatus, STATUS, delivery_request,
)
from randovania.games.prime3.multiworld.ledger import DeliveryLedger
from randovania.games.prime3.multiworld.manifest import validate_manifest
from randovania.network_common.nullphaaze_multiworld import BUILD_HEADER, BUILD_ID, CONTRACT, HEADER, validate_contract


@pytest.fixture
def manifest():
    world = uuid.UUID("10000000-0000-4000-8000-000000000001")
    seed = "11" * 32
    lineage = uuid.uuid5(world, seed)
    profile = world.bytes + lineage.bytes + b"".join(uuid.uuid5(lineage, f"CP3W slot {i}").bytes for i in range(3))
    recipes = {}
    for name in (b"pickup-a", b"pickup-b"):
        recipes[hashlib.sha256(name).hexdigest()] = {"name": name.decode(), "pickup": base64.b85encode(name).decode()}
    return {"schema": 1, "contract": CONTRACT, "world_uuid": str(world), "seed_fingerprint": seed,
            "save_slot": 0, "save_policy": "new-multiworld-save-only", "checkpoint_profile": profile.hex(),
            "incoming_recipes": recipes,
            "locations": [{"index": i, "recipient_game": "prime3", "recipient_world": str(world),
                           "local": True} for i in range(100)]}


def status(ledger, cursor=0, saved=0, ready=True, pending=False):
    return MultiworldStatus(uuid.UUID(ledger.binding["world_uuid"]), ledger.binding["seed_fingerprint"],
                           ledger.binding["save_slot"], 1, cursor, saved, ready, pending,
                           ledger.history(cursor), frozenset())


def test_private_protocol_is_required():
    validate_contract({HEADER: CONTRACT, BUILD_HEADER: BUILD_ID})
    for headers in ({}, {HEADER: "stock-rdv"}, {HEADER: CONTRACT}, {HEADER: CONTRACT, BUILD_HEADER: "old-build"}):
        with pytest.raises(ValueError):
            validate_contract(headers)


@pytest.mark.parametrize("field,value", [
    ("schema", 2), ("contract", "other"), ("world_uuid", str(uuid.UUID(int=0))),
    ("save_slot", 3), ("save_policy", "migrate"), ("seed_fingerprint", "22" * 32),
])
def test_manifest_identity_rejection(manifest, field, value):
    manifest[field] = value
    with pytest.raises(ValueError):
        validate_manifest(manifest)


def test_location_mapping_is_complete_and_unique(manifest):
    validate_manifest(manifest)
    manifest["locations"][4]["index"] = 3
    with pytest.raises(ValueError, match="100 distinct"):
        validate_manifest(manifest)


def test_queue_persists_before_delivery_and_replays_rollback(tmp_path, manifest):
    path = tmp_path / "ledger.json"
    ledger = DeliveryLedger(path, manifest)
    keys = list(manifest["incoming_recipes"])
    ledger.accept_incoming(keys)
    assert json.loads(path.read_text())["incoming"] == keys
    assert ledger.reconcile(status(ledger)) == (1, keys[0])
    assert ledger.reconcile(status(ledger, cursor=1)) == (2, keys[1])
    assert ledger.reconcile(status(ledger, cursor=2, saved=2)) is None
    # Restart and an older checkpoint must restore missing items automatically.
    restored = DeliveryLedger(path, manifest)
    assert restored.reconcile(status(restored)) == (1, keys[0])
    assert restored.reconcile(status(restored, cursor=2, pending=True)) is None


def test_queue_rejects_shrink_reorder_unknown_and_conflicting_receipts(tmp_path, manifest):
    ledger = DeliveryLedger(tmp_path / "ledger.json", manifest)
    keys = list(manifest["incoming_recipes"])
    ledger.accept_incoming(keys)
    for values in (keys[:1], list(reversed(keys)), keys + ["ff" * 32]):
        with pytest.raises(ValueError):
            ledger.accept_incoming(values)
    wrong = status(ledger)
    from dataclasses import replace
    with pytest.raises(ValueError, match="history"):
        ledger.reconcile(replace(wrong, history=b"x" * 32))
    with pytest.raises(ValueError, match="identity"):
        ledger.reconcile(replace(wrong, world_uuid=uuid.uuid4()))


def test_pending_locations_survive_restart_and_are_deduplicated(tmp_path, manifest):
    path = tmp_path / "ledger.json"
    ledger = DeliveryLedger(path, manifest)
    ledger.collect([0, 3, 99])
    ledger.collect([3])
    assert DeliveryLedger(path, manifest).pending_locations == (0, 3, 99)
    ledger.mark_uploaded([3])
    assert DeliveryLedger(path, manifest).pending_locations == (0, 99)
    with pytest.raises(ValueError):
        ledger.mark_uploaded([5])
    with pytest.raises(ValueError):
        ledger.collect([100])


def test_other_save_cannot_open_ledger(tmp_path, manifest):
    path = tmp_path / "ledger.json"
    DeliveryLedger(path, manifest).accept_incoming([])
    manifest["save_slot"] = 1
    with pytest.raises(ValueError, match="another world"):
        DeliveryLedger(path, manifest)


def test_disk_failure_does_not_advance_volatile_host_queue(tmp_path, manifest, monkeypatch):
    ledger = DeliveryLedger(tmp_path / "ledger.json", manifest)
    keys = list(manifest["incoming_recipes"])
    ledger.accept_incoming(keys[:1])

    def fail(*_):
        raise OSError("disk full")

    monkeypatch.setattr("randovania.games.prime3.multiworld.ledger.os.replace", fail)
    with pytest.raises(OSError, match="disk full"):
        ledger.accept_incoming(keys)
    assert ledger.data["incoming"] == keys[:1]
    assert json.loads(ledger.path.read_text())["incoming"] == keys[:1]
    assert not list(tmp_path.glob("ledger.json.*"))


def test_seed_authorized_counts_are_enforced(tmp_path, manifest):
    key = next(iter(manifest["incoming_recipes"]))
    manifest["incoming_recipes"][key]["sources"] = [{"world_uuid": str(uuid.uuid4()), "index": 4}]
    ledger = DeliveryLedger(tmp_path / "ledger.json", manifest)
    with pytest.raises(ValueError, match="authorized count"):
        ledger.accept_incoming([key, key])
    assert ledger.data["incoming"] == []


def test_wire_status_and_delivery_are_bounded(tmp_path, manifest):
    ledger = DeliveryLedger(tmp_path / "ledger.json", manifest)
    value = status(ledger)
    bitmap = bytes([1]) + bytes(11) + bytes([8])
    raw = STATUS.pack(b"MW01", value.world_uuid.bytes, bytes.fromhex(value.seed_fingerprint),
                      0, 1, 0, 0, 1, 0, value.history, bitmap, 0, 0, 0)
    decoded = MultiworldStatus.decode(raw)
    assert decoded.locations == frozenset((0, 99))
    assert decoded.binding == ledger.binding
    assert len(delivery_request(decoded, 1, next(iter(manifest["incoming_recipes"])))) == 128
    for invalid in (raw[:-1], raw + b"x", raw[:120] + b"\x80" + raw[121:]):
        with pytest.raises(ValueError):
            MultiworldStatus.decode(invalid)
    with pytest.raises(ValueError):
        delivery_request(decoded, 2, next(iter(manifest["incoming_recipes"])))
