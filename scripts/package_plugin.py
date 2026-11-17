"""Build a complete AstrBot source ZIP, including the case-sensitive logo alias."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

EXCLUDED = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "data",
}


def package_plugin(root: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if (
                path.is_file()
                and not EXCLUDED.intersection(relative.parts)
                and path.suffix not in (".pyc", ".zip")
                and relative.as_posix() != "logo.png"
            ):
                archive.write(path, str(Path(root.name) / relative))
        archive.write(root / "LOGO.png", f"{root.name}/logo.png")
    return destination


if __name__ == "__main__":
    plugin_root = Path(__file__).resolve().parents[1]
    package_plugin(plugin_root, plugin_root.parent / f"{plugin_root.name}.zip")
