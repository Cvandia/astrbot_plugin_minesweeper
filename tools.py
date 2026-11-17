"""AstrBot function tools for natural-language game lifecycle requests."""

from collections.abc import Awaitable, Callable
from typing import Any

from astrbot.api import FunctionTool
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.astr_agent_context import AstrAgentContext
from jsonschema import Draft202012Validator
from pydantic import Field
from pydantic.dataclasses import dataclass

from .src.astrbot_plugin_minesweeper.skins import skin_list


@dataclass
class MinesweeperTool(FunctionTool[AstrAgentContext]):
    callback: Callable[..., Awaitable[str]] | None = Field(
        default=None, exclude=True, repr=False
    )

    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs: Any
    ) -> str:
        """Validate model input and always derive the target from the real event."""
        error = next(Draft202012Validator(self.parameters).iter_errors(kwargs), None)
        if error is not None:
            return (
                f"扫雷工具参数错误：{error.message}。请修正参数后重试，当前游戏未变更。"
            )
        event = context.context.event
        if event is None or self.callback is None:
            return "扫雷工具当前不可用，未变更任何游戏。"
        return await self.callback(event, **kwargs)


@dataclass
class StartMinesweeperTool(MinesweeperTool):
    name: str = "minesweeper_start"
    description: str = (
        "在当前群聊或私聊开始一局扫雷，并直接向当前聊天发送棋盘。"
        "当用户明确要求开局，例如‘来一局扫雷’‘开始中级扫雷’时使用。"
        "默认初级；支持自定义行、列、雷数和皮肤。已有游戏时保留原局。"
        "仅询问玩法或闲聊提到扫雷时不要调用。请依据工具返回报告实际结果，无需重复发送棋盘。"
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "difficulty": {
                    "type": "string",
                    "enum": ["初级", "中级", "高级"],
                    "description": "难度，默认初级；未指定的棋盘参数采用该难度预设。",
                },
                "rows": {
                    "type": "integer",
                    "minimum": 8,
                    "maximum": 24,
                    "description": "自定义行数，覆盖难度预设。",
                },
                "columns": {
                    "type": "integer",
                    "minimum": 8,
                    "maximum": 30,
                    "description": "自定义列数，覆盖难度预设。",
                },
                "mines": {
                    "type": "integer",
                    "minimum": 10,
                    "maximum": 719,
                    "description": "自定义雷数，必须小于行数×列数。",
                },
                "skin": {
                    "type": "string",
                    "enum": skin_list,
                    "description": "皮肤名称，省略时使用插件默认皮肤。",
                },
            },
            "required": [],
            "additionalProperties": False,
        }
    )


@dataclass
class StopMinesweeperTool(MinesweeperTool):
    name: str = "minesweeper_stop"
    description: str = (
        "结束当前群聊或私聊正在进行的扫雷，并发送实际处理结果。"
        "仅在用户明确要求结束或取消当前扫雷，例如‘结束这局扫雷’‘不玩扫雷了’时使用。"
        "遵守插件的发起者/管理员结束权限；不接受用户身份、权限或会话参数。"
        "没有游戏或权限不足时如实返回，不会结束其他聊天的游戏。"
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }
    )
