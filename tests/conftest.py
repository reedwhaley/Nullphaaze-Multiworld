import os
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from _host import use_host

host = os.environ.get("NULLPHAAZE_MULTIWORLD_HOST")
if host:
    use_host(host)
else:
    raise pytest.UsageError("Set NULLPHAAZE_MULTIWORLD_HOST to a compatible host source checkout")
