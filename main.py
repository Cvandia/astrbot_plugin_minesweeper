"""AstrBot entrypoint; game rules and rendering live in the src package."""

import asyncio
import json
import shlex
from contextlib import suppress
from typing import Any

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.api.message_components import Image, Plain
from astrbot.api.star import Context, Star
from astrbot.core.star.filter.command import GreedyStr

from .src.astrbot_plugin_minesweeper.commands import HELP, parse_start
from .src.astrbot_plugin_minesweeper.render import render_board
from .src.astrbot_plugin_minesweeper.service import GameService, Reply
from .src.astrbot_plugin_minesweeper.skins import skin_list
from .tools import StartMinesweeperTool, StopMinesweeperTool


def session_key(event: AstrMessageEvent) -> str:
    """Share a group board even when AstrBot enables unique user sessions."""
    group = event.get_group_id()
    scope = ["group", group] if group else ["private", event.get_sender_id()]
    return json.dumps([event.get_platform_id(), event.get_self_id(), *scope])


class MinesweeperPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        super().__init__(context)
        self.config = config
        self.service = GameService(
            timeout=max(10, int(config.get("game_timeout", 300))),
            max_games=max(1, int(config.get("max_games", 100))),
        )
        self.lock = asyncio.Lock()
        self.cleanup_task: asyncio.Task | None = None
        self.closed = False
        self.llm_tools = [
            StartMinesweeperTool(callback=self.llm_start),
            StopMinesweeperTool(callback=self.llm_stop),
        ]
        context.add_llm_tools(*self.llm_tools)
        for tool in self.llm_tools:
            # AstrBot associates tools with the Star entrypoint for enable/unload handling.
            tool.handler_module_path = self.__module__

    async def initialize(self) -> None:
        """Start idle-session cleanup when AstrBot activates this plugin."""
        if self.cleanup_task is None or self.cleanup_task.done():
            self.closed = False
            self.cleanup_task = asyncio.create_task(self._cleanup())

    async def _cleanup(self) -> None:
        while True:
            await asyncio.sleep(5)
            async with self.lock:
                origins = self.service.expire()
            for origin in origins:
                await self._notify_expired(origin)

    async def _notify_expired(self, origin: str) -> None:
        try:
            await self.context.send_message(
                origin, MessageChain([Plain("扫雷超时，游戏已结束")])
            )
        except Exception:
            logger.exception("扫雷超时通知发送失败")

    async def _send_reply(self, event: AstrMessageEvent, reply: Reply) -> None:
        if reply.session is None:
            await event.send(event.plain_result(reply.text))
            return
        game = reply.session.game
        if self.config.get("text_mode", False):
            await event.send(
                event.plain_result((reply.text + "\n" + game.text_board()).strip())
            )
            return
        try:
            png = await asyncio.to_thread(render_board, game, reply.session.skin)
            components = [Plain(reply.text)] if reply.text else []
            components.append(Image.fromBytes(png))
            await event.send(event.chain_result(components))
        except Exception:
            logger.exception("扫雷棋盘图片生成或发送失败，改用文本棋盘")
            await event.send(
                event.plain_result((reply.text + "\n" + game.text_board()).strip())
            )

    async def _run(
        self,
        event: AstrMessageEvent,
        action: str,
        args: str = "",
        preset: str = "初级",
        *,
        from_tool: bool = False,
    ) -> str:
        if not from_tool:
            event.stop_event()
        async with self.lock:
            if self.closed:
                return "扫雷插件已停用，未变更任何游戏。"
            expired = self.service.expire()
            for origin in expired:
                await self._notify_expired(origin)
            key = session_key(event)
            try:
                if action == "start":
                    if args.strip() in ("帮助", "help", "-h", "--help"):
                        reply = Reply(HELP)
                    else:
                        options = parse_start(
                            args, self.config.get("default_skin", "winxp"), preset
                        )
                        reply = self.service.start(
                            key,
                            event.get_sender_id(),
                            event.unified_msg_origin,
                            options,
                        )
                elif action == "show":
                    reply = self.service.show(key)
                elif action in ("open", "mark"):
                    reply = self.service.move(key, args, mark=action == "mark")
                else:
                    reply = self.service.stop(
                        key,
                        event.get_sender_id(),
                        event.is_admin(),
                        self.config.get("stop_owner_only", False),
                    )
            except ValueError as exc:
                reply = Reply(str(exc))
            await self._send_reply(event, reply)
            return reply.text

    async def llm_start(
        self, event: AstrMessageEvent, difficulty: str = "初级", **kwargs: Any
    ) -> str:
        """Use the same board validation and session handling as command starts."""
        flags = {
            "rows": "--row",
            "columns": "--col",
            "mines": "--num",
            "skin": "--skin",
        }
        args = shlex.join(
            [value for key, item in kwargs.items() for value in (flags[key], str(item))]
        )
        return await self._run(event, "start", args, difficulty, from_tool=True)

    async def llm_stop(self, event: AstrMessageEvent) -> str:
        """Check the real sender's configured stop permission within the shared lock."""
        return await self._run(event, "stop", from_tool=True)

    @filter.command("扫雷", alias={"minesweeper"})
    async def start(self, event: AstrMessageEvent, args: GreedyStr) -> None:
        """开始扫雷；支持 -r 行数 -c 列数 -n 雷数 -s 皮肤。"""
        await self._run(event, "start", args)

    @filter.command("扫雷初级")
    async def easy(self, event: AstrMessageEvent, args: GreedyStr) -> None:
        """开始 8×8、10 雷的初级扫雷。"""
        await self._run(event, "start", args, "初级")

    @filter.command("扫雷中级")
    async def medium(self, event: AstrMessageEvent, args: GreedyStr) -> None:
        """开始 16×16、40 雷的中级扫雷。"""
        await self._run(event, "start", args, "中级")

    @filter.command("扫雷高级")
    async def hard(self, event: AstrMessageEvent, args: GreedyStr) -> None:
        """开始 16×30、99 雷的高级扫雷。"""
        await self._run(event, "start", args, "高级")

    @filter.command("挖开", alias={"open", "wk"})
    async def open_tiles(self, event: AstrMessageEvent, positions: GreedyStr) -> None:
        """挖开一个或多个格子，例如：挖开 A1 B2。"""
        await self._run(event, "open", positions)

    @filter.command("标记", alias={"mark", "bj"})
    async def mark_tiles(self, event: AstrMessageEvent, positions: GreedyStr) -> None:
        """插旗或取消标记，例如：标记 A1 B2。"""
        await self._run(event, "mark", positions)

    @filter.command(
        "查看游戏", alias={"查看游戏盘", "显示游戏", "显示游戏盘", "查看扫雷"}
    )
    async def show(self, event: AstrMessageEvent) -> None:
        """查看当前会话的扫雷棋盘。"""
        await self._run(event, "show")

    @filter.command("结束扫雷", alias={"结束游戏", "结束"})
    async def stop(self, event: AstrMessageEvent) -> None:
        """结束当前会话的扫雷游戏。"""
        await self._run(event, "stop")

    @filter.command("扫雷帮助")
    async def help(self, event: AstrMessageEvent) -> None:
        """显示扫雷命令与规则。"""
        event.stop_event()
        await event.send(event.plain_result(HELP))

    @filter.command("扫雷皮肤")
    async def skins(self, event: AstrMessageEvent) -> None:
        """列出可用的扫雷皮肤。"""
        event.stop_event()
        await event.send(event.plain_result("支持的皮肤：" + ", ".join(skin_list)))

    async def terminate(self) -> None:
        """Cancel background work, discard boards, and unregister this instance's tools."""
        self.closed = True
        if self.cleanup_task is not None:
            self.cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await self.cleanup_task
            self.cleanup_task = None
        async with self.lock:
            self.service.sessions.clear()
        manager = self.context.get_llm_tool_manager()
        manager.func_list[:] = [
            tool
            for tool in manager.func_list
            if not any(tool is own for own in self.llm_tools)
        ]
