# Nullphaaze-Multiworld

Source-only integration and CP3W native runtime for NullPhaaze Corruption
multiworld. Includes the Wii/vWii native bridge and runtime source, bounded
seed binding, checkpoint/receipt support, UDP client/protocol adapters,
recipient-aware manifest/recipe/ledger adapters, host connector adapters and
focused synthetic tests.

This repository contains no CDV desktop application, generator application,
GUI resources, app-freezing recipes or private server. It cannot build CDV.
The independent MIT patching core lives separately in
[NullPhaaze](https://github.com/reedwhaley/NullPhaaze).

## Source boundary

`src/nullphaaze_network/` contains the runtime library and native source.
`adapters/randovania/` is an explicit source overlay for a compatible host's
existing game/resource/serialization APIs; it is not a complete host package.
Those APIs and the core are external prerequisites for seed-aware operations.
The raw CP3W framing definitions in `nullphaaze_network.prime3_wii_runtime.protocol`
can be imported using only the Python standard library.

The adapters retain the `nullphaaze-multiworld-v1` contract and matching build ID.
Use a matching host integration; stock upstream client/server compatibility is
not implied. `SOURCE.json` records the exact source revision and file hashes.
The host source revision used for extraction is historical provenance, not a
promise that the core-only repository still contains that frontend tree.

## Install the runtime source package

Use Python 3.12 in your own environment:

```sh
python -m pip install -e .
python -c "from nullphaaze_network.prime3_wii_runtime import protocol; print(protocol.PROTOCOL_MAGIC)"
```

Seed compilation additionally requires an existing compatible host source
checkout with its dependencies installed, the separate NullPhaaze core, and
`retro-data-structures==0.44.1` / `open-prime-rando==0.15.1` APIs. This repository
does not fetch or install a desktop host application or a server.

## Rebuild and validate native templates

Install devkitPPC release 47.1 (GCC 15.1.0, binutils 2.44), devkitppc-rules and
libogc. Use the compatible host environment's Python. Replace `HOST_SOURCE`
with that existing checkout root (or its `cdv` directory):

```sh
python scripts/build_runtime.py --host HOST_SOURCE --output artifacts/runtime-new
python scripts/verify_runtime.py --host HOST_SOURCE --assets artifacts/runtime-new --report artifacts/runtime-validation.json
```

Use a new output directory each time. The builder compiles twice and checks
reproducibility. The bundled manifest is synthetic and has no real session,
credentials or save. These commands load this repository's adapters in memory;
they never write or copy files into the host checkout. Built templates remain
local artifacts and must match the client integration's native source.
The retained payload helper supports the production bridge build; historical
probe/standalone build modes are not standalone application targets here.

For integration in another host, use the adapters as explicit reference source
and provide the matching APIs. The connector adapters expect host-owned settings,
timers, resource databases and authenticated multiworld orchestration. The
standalone core CLI does not become a multiworld client merely by installing
this package.

## Synthetic tests

In a compatible host environment with pytest installed:

```sh
export NULLPHAAZE_MULTIWORLD_HOST=HOST_SOURCE
python -m pytest tests -q
```

In PowerShell use `$env:NULLPHAAZE_MULTIWORLD_HOST='HOST_SOURCE'`.
These tests exercise protocol rejection, receipt/ledger integrity, runtime
binding and guarded native hooks. They do not prove live item delivery, native
save durability, console gameplay or physical-hardware acceptance.

## License and exclusions

GPL-3.0-or-later; see `LICENSE` and retained source notices. Upstream
Corruptovania/Randovania attribution is recorded in `SOURCE.json`. This does
not change the separate MIT core's license. No compiled templates, game media,
personal configuration, credentials, sessions or saves are included.
