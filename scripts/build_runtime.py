"""Compile reproducible runtime templates using an explicitly supplied host."""
import argparse
import json
from pathlib import Path
from _host import ROOT, use_host

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=ROOT / "fixtures/runtime-template-manifest.json")
    args = parser.parse_args()
    use_host(args.host)
    from nullphaaze_network.prime3_lua_service import runtime_assets, runtime_export
    manifest = json.loads(args.manifest.read_text())
    receipt = runtime_assets.build_assets(args.output.resolve(), manifest, runtime_export.pickup_map()["pickups"])
    print(json.dumps(receipt, indent=2))

if __name__ == "__main__":
    main()
