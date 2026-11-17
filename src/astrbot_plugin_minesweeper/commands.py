"""Strict command parsing with no argparse exits or process-global state."""

import re
import shlex
from dataclasses import dataclass

from .skins import skin_list

PRESETS = {"初级": (8, 8, 10), "中级": (16, 16, 40), "高级": (16, 30, 99)}
MAX_POSITIONS = 100
HELP = """扫雷 / minesweeper：开始初级游戏
扫雷初级 / 扫雷中级 / 扫雷高级：选择难度
扫雷 -r 12 -c 16 -n 30 -s winxp：自定义
挖开 / open / wk A1 B2：批量挖开
标记 / mark / bj A1 B2：标记或取消标记
查看游戏 / 查看扫雷：查看棋盘
结束扫雷 / 结束游戏 / 结束：结束游戏
扫雷皮肤：列出全部皮肤；扫雷帮助：查看帮助
字母表示行，数字表示列；首次挖开安全。
启用支持工具调用的模型后，也可说“来一局扫雷”“结束这局扫雷”。"""


@dataclass(frozen=True)
class StartOptions:
    rows: int
    columns: int
    mines: int
    skin: str


def parse_start(text: str, default_skin: str, preset: str = "初级") -> StartOptions:
    tokens = shlex.split(text)
    if tokens and tokens[0] in PRESETS:
        preset = tokens.pop(0)
    rows, columns, mines = PRESETS[preset]
    values = {"rows": rows, "columns": columns, "mines": mines, "skin": default_skin}
    names = {
        "-r": "rows",
        "--row": "rows",
        "-c": "columns",
        "--col": "columns",
        "-n": "mines",
        "--num": "mines",
        "-s": "skin",
        "--skin": "skin",
    }
    while tokens:
        option = tokens.pop(0)
        key, sep, inline = option.partition("=")
        if key not in names:
            raise ValueError(f"未知参数：{key}。发送“扫雷帮助”查看用法")
        if sep:
            value = inline
        elif tokens:
            value = tokens.pop(0)
        else:
            raise ValueError(f"参数 {key} 缺少值")
        name = names[key]
        if name != "skin":
            try:
                value = int(value)
            except ValueError as exc:
                raise ValueError(f"参数 {key} 必须是整数") from exc
        values[name] = value
    skin = str(values["skin"]).lower()
    if skin not in skin_list:
        raise ValueError("支持的皮肤：" + ", ".join(skin_list))
    return StartOptions(
        int(values["rows"]), int(values["columns"]), int(values["mines"]), skin
    )


def parse_positions(text: str) -> list[tuple[str, int, int]]:
    tokens = re.split(r"[\s,，、;；]+", text.strip())
    if not text.strip():
        raise ValueError("请提供位置，例如：挖开 A1 B2")
    if len(tokens) > MAX_POSITIONS:
        raise ValueError("每次最多操作 100 个位置")
    result = []
    for token in tokens:
        if not token:
            continue
        match = re.fullmatch(r"([A-Za-z])([1-9][0-9]{0,2})", token)
        if not match:
            raise ValueError(f"位置 {token} 不合法，须为字母+数字，例如 A1")
        x, y = ord(match[1].upper()) - 65, int(match[2]) - 1
        if (x, y) not in [(p[1], p[2]) for p in result]:
            result.append((token.upper(), x, y))
    return result
