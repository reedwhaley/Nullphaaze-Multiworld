"""Fail closed on a different function body or entry instruction."""
import hashlib
import struct

import pytest

from nullphaaze_network.prime3_lua_service import frame_poll
from randovania.games.prime3.exporter.dol_patcher import (
    decode_ppc_unconditional_branch,
    Prime3DolPatchError,
)


@pytest.fixture
def dol(monkeypatch):
    body = struct.pack('>I', 0x9421FED0) + bytes(frame_poll.SIZE - 4)
    header = bytearray(0x100)
    for offset, value in ((0, 0x100), (0x48, frame_poll.ADDRESS), (0x90, len(body))):
        struct.pack_into('>I', header, offset, value)
    monkeypatch.setattr(frame_poll, 'SHA256', hashlib.sha256(body).hexdigest())
    return bytes(header) + body


def test_frame_hook_replaces_only_entry_and_reaches_wrapper(dol):
    target = 0x817c63f4
    result, _ = frame_poll.patch(dol, dol, {'network_frame_poll_hook': target})
    branch = decode_ppc_unconditional_branch(struct.unpack_from('>I', result, 0x100)[0], frame_poll.ADDRESS)
    assert branch.target_address == target
    assert result[:0x100] == dol[:0x100]
    assert result[0x104:] == dol[0x104:]


def test_frame_hook_fingerprints_entire_function(dol):
    changed = bytearray(dol)
    changed[-1] ^= 1
    with pytest.raises(ValueError, match='EndScene'):
        frame_poll.patch(bytes(changed), bytes(changed), {'network_frame_poll_hook': 0x817c63f4})


def test_frame_hook_rejects_preexisting_conflicting_patch(dol):
    changed = bytearray(dol)
    struct.pack_into('>I', changed, 0x100, 0x60000000)
    with pytest.raises(Prime3DolPatchError):
        frame_poll.patch(dol, bytes(changed), {'network_frame_poll_hook': 0x817c63f4})
