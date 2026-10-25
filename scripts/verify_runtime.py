"""Validate native templates, source provenance and bounded seed binding."""
import argparse
import json
from pathlib import Path
import tempfile
from _host import ROOT, use_host

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, type=Path)
    parser.add_argument("--assets", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    use_host(args.host)
    from nullphaaze_network.prime3_lua_service import runtime_assets, runtime_export
    from randovania.game_connection.prime3_multiworld_client import Prime3MultiworldClient
    from randovania.network_common import nullphaaze_multiworld
    assert Path(nullphaaze_multiworld.__file__).resolve().is_relative_to(ROOT / "adapters")
    manifest = json.loads((ROOT / "fixtures/runtime-template-manifest.json").read_text())
    asset_root, files, native, boot = runtime_assets.load(args.assets)
    receipt = json.loads((asset_root / "assets.json").read_text())
    assert receipt["native_sources"] == runtime_assets.source_hashes()
    mapping, presentation = runtime_export.preflight(manifest, asset_directory=args.assets)
    with tempfile.TemporaryDirectory() as temporary:
        target = Path(temporary) / "bound"
        bound = runtime_assets.bind_seed(manifest, mapping["pickups"], target, directory=args.assets)
        runtime_assets.bind_bootstrap(args.assets, (target / "bridge.bin").read_bytes(), bound)
    client = Prime3MultiworldClient("127.0.0.1", manifest)
    assert client.socket is None
    report = {"passed": True, "runtimeSourcesMatch": True, "seedBindingValidated": True,
              "clientConstructedWithoutNetwork": True, "privateServerIncluded": False,
              "hostWritten": False, "gameplayValidated": False,
              "runtimeModule": str(Path(runtime_assets.__file__).resolve()),
              "clientModule": str(Path(__import__(Prime3MultiworldClient.__module__, fromlist=["_"]).__file__).resolve())}
    assert Path(report["runtimeModule"]).is_relative_to(ROOT / "src")
    assert Path(report["clientModule"]).is_relative_to(ROOT / "adapters")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))

if __name__ == "__main__":
    main()
