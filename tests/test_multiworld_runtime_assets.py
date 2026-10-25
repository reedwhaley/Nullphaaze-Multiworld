"""Compiler-free seed binding, corruption rejection and instruction preservation."""
import copy
import hashlib
import json
from pathlib import Path
import struct

import pytest

from nullphaaze_network.prime3_lua_service import runtime_assets, runtime_export, seed_data


@pytest.fixture
def manifest():
    return json.loads((Path(__file__).parent / 'fixtures/runtime-multiworld-manifest.json').read_text())


@pytest.fixture
def mapping():
    return runtime_export.pickup_map()['pickups']


@pytest.fixture
def assets(tmp_path, manifest, mapping):
    root = tmp_path / 'templates'
    root.mkdir()
    data = seed_data.compile_data(manifest, mapping)
    profile = bytes.fromhex(manifest['checkpoint_profile'])
    binary = b'INSTRUCTIONS!' + data + b'CODE' + profile + b'END'
    payload = b'BOOTSTRAP' + binary + b'TAIL'
    sha = runtime_assets.sha
    base = 0x817c1000
    meta = dict(address=base, reserved_high=0x817c0000, size=len(binary), binary_sha256=sha(binary),
                symbols={'owned_cp3w_claim_connection_notice': base},
                multiworld={'patchable_seed_data': dict(address=base+13, size=len(data), sha256=sha(data),
                    checkpoint_address=base+13+len(data)+4, checkpoint_size=80)})
    from nullphaaze_network.prime3_lua_service import frame_poll
    meta["network_frame_service"] = frame_poll.CONTRACT
    meta["symbols"].update({name: base for name in frame_poll.SYMBOLS})
    boot = dict(bootstrap_address=0x806843c0, bootstrap_sha256=sha(payload),
                cache_range_start=base, cache_range_size=len(binary))
    files = {'bridge.bin': binary, 'bridge.json': json.dumps(meta).encode(),
             'payload.bin': payload, 'payload.json': json.dumps(boot).encode()}
    for name, value in files.items():
        (root/name).write_bytes(value)
    (root/'assets.json').write_text(json.dumps({'schema': 1, 'files': {k: sha(v) for k,v in files.items()}}))
    return root


def test_fixed_table_layout_and_all_location_indices(manifest, mapping):
    raw = seed_data.compile_data(manifest, mapping)
    assert len(raw) == 42736 and raw[:8] == b'NPMWPL01'
    assert struct.unpack_from('>II', raw, 8) == (1, len(raw))
    assert struct.unpack_from('>I', raw, 64)[0] == manifest['save_slot']
    for index, row in enumerate(mapping):
        _, high, low = struct.unpack_from('>III', raw, len(raw)-1200+index*12)
        assert (high << 32) | low == row['area']


def test_seed_binding_changes_only_declared_data(assets, tmp_path, manifest, mapping):
    original = (assets/'bridge.bin').read_bytes()
    manifest['save_slot'] = 2
    metadata = runtime_assets.bind_seed(manifest, mapping, tmp_path/'bound', directory=assets)
    binary = (tmp_path/'bound/bridge.bin').read_bytes()
    payload, report = runtime_assets.bind_bootstrap(assets, binary, metadata)
    assert binary[:13] == original[:13] and binary[-3:] == b'END'
    assert payload == b'BOOTSTRAP' + binary + b'TAIL'
    assert report['native_personalization'] == 'bounded_seed_table_and_checkpoint_identity_only'
    assert metadata['multiworld']['save_slot'] == 2
    assert len(metadata['multiworld']['save_filename']) == 8


def test_old_room_driven_runtime_is_rejected_before_export(assets):
    metadata = json.loads((assets / 'bridge.json').read_text())
    metadata.pop('network_frame_service')
    encoded = json.dumps(metadata).encode()
    (assets / 'bridge.json').write_bytes(encoded)
    receipt = json.loads((assets / 'assets.json').read_text())
    receipt['files']['bridge.json'] = runtime_assets.sha(encoded)
    (assets / 'assets.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='independent native networking'):
        runtime_assets.load(assets)


def test_startup_only_display_wait_runtime_is_rejected_before_export(assets):
    metadata = json.loads((assets / 'bridge.json').read_text())
    metadata['network_frame_service'].update(
        schema=1, kind='retail_vi_wait_for_retrace', address=0x804efc64,
        function_size=84,
        function_sha256='444be256fc2e393f9b5f042e6cd420212ff080af3bece1263996c00aca028f6d')
    encoded = json.dumps(metadata).encode()
    (assets / 'bridge.json').write_bytes(encoded)
    receipt = json.loads((assets / 'assets.json').read_text())
    receipt['files']['bridge.json'] = runtime_assets.sha(encoded)
    (assets / 'assets.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='independent native networking'):
        runtime_assets.load(assets)


def test_instruction_changes_rejected_even_with_updated_hash(assets, tmp_path, manifest, mapping):
    meta = runtime_assets.bind_seed(manifest, mapping, tmp_path/'bound', directory=assets)
    binary = bytearray((tmp_path/'bound/bridge.bin').read_bytes())
    binary[0] ^= 1
    meta['binary_sha256'] = runtime_assets.sha(binary)
    with pytest.raises(ValueError, match='instructions'):
        runtime_assets.bind_bootstrap(assets, binary, meta)


@pytest.mark.parametrize('name', runtime_assets.ASSET_NAMES)
def test_template_asset_tampering_fails(assets, name):
    path = assets/name
    path.write_bytes(path.read_bytes()+b'x')
    with pytest.raises(ValueError, match='hash mismatch'):
        runtime_assets.load(assets)


@pytest.mark.parametrize('field,value', [('world_uuid','ffffffff-ffff-4fff-8fff-ffffffffffff'),
                                       ('seed_fingerprint','ff'*32), ('save_slot',3)])
def test_identity_mismatch_fails_before_output(assets, tmp_path, manifest, mapping, field, value):
    manifest[field] = value
    with pytest.raises(ValueError):
        runtime_assets.bind_seed(manifest, mapping, tmp_path/'invalid', directory=assets)
    assert not (tmp_path/'invalid').exists()


def test_missing_or_out_of_range_pickup_mapping_fails(manifest, mapping):
    with pytest.raises(ValueError, match='100 audited'):
        seed_data.compile_data(manifest, mapping[:-1])
    mapping[1]['area'] = -1
    with pytest.raises(ValueError, match='Unmapped'):
        seed_data.compile_data(manifest, mapping)
