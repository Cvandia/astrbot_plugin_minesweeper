import importlib.util
import json
import re
import tomllib
from pathlib import Path
from zipfile import ZipFile

import yaml

from astrbot_plugin_minesweeper import __version__
from astrbot_plugin_minesweeper.skins import skin_list

ROOT = Path(__file__).resolve().parents[1]


def test_metadata_version_platforms_and_schema_match_files():
    metadata = yaml.safe_load((ROOT / "metadata.yaml").read_text(encoding="utf-8"))
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert metadata["name"] == ROOT.name
    assert metadata["version"] == "v" + __version__
    assert project["project"]["version"] == __version__
    assert metadata["astrbot_version"] == ">=4.16,<5"
    assert len(metadata["support_platforms"]) == 10
    assert "pages" not in metadata
    assert not list((ROOT / "pages").rglob("index.html"))
    schema = json.loads((ROOT / "_conf_schema.json").read_text(encoding="utf-8"))
    assert schema["default_skin"]["options"] == skin_list
    assert schema["default_skin"]["default"] in skin_list


def test_readme_preserves_template_sections_and_folding():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert re.findall(r"^#{2,} .+$", readme, re.M) == [
        "## 📝 介绍",
        "## 📜 免责声明",
        "## 💿 安装",
        "## 🚀 使用",
        "### 指令：",
        "## ⚙️ 配置",
        "## 🌙 Todo",
        "## 💝 特别鸣谢",
        "## Contributer",
        "## 📚 更多帮助",
    ]
    assert readme.count("<details>") == readme.count("</details>") == 2
    assert '<div align="center">' in readme


def test_release_archive_has_required_files_and_linux_logo(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "package_plugin", ROOT / "scripts/package_plugin.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    destination = module.package_plugin(ROOT, tmp_path / "plugin.zip")
    with ZipFile(destination) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        prefix = ROOT.name + "/"
        for path in (
            "main.py",
            "metadata.yaml",
            "LOGO.png",
            "logo.png",
            "uv.lock",
            "changelog.md",
            "tools.py",
        ):
            assert prefix + path in names
        assert archive.read(prefix + "LOGO.png") == archive.read(prefix + "logo.png")
        assert not any(
            "__pycache__" in name or ".pytest_cache" in name for name in names
        )
