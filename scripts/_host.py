"""Read-only host adapter loading; never installs or builds a host application."""
from pathlib import Path
import importlib
import sys

ROOT = Path(__file__).resolve().parents[1]

def use_host(host):
    sys.dont_write_bytecode = True
    host = Path(host).resolve()
    source = host / "cdv" if (host / "cdv/randovania/__init__.py").is_file() else host
    if not (source / "randovania/__init__.py").is_file():
        raise ValueError("--host must name an existing compatible host source checkout")
    sys.path[:0] = [str(ROOT / "src"), str(source)]
    package = importlib.import_module("randovania")
    if not Path(package.__file__).resolve().is_relative_to(source):
        raise ValueError("A different host was already imported in this interpreter")
    overlay = ROOT / "adapters"
    directories = {path.parent for path in overlay.rglob("*.py")}
    for directory in list(directories):
        directories.update(parent for parent in directory.parents if parent.is_relative_to(overlay) and parent != overlay)
    for directory in sorted(directories, key=lambda p: (len(p.parts), str(p))):
        name = directory.relative_to(overlay).as_posix().replace("/", ".")
        module = importlib.import_module(name)
        if str(directory) not in module.__path__:
            module.__path__.insert(0, str(directory))
    return source
