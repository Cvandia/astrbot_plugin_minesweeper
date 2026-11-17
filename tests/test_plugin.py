"""Integration tests against an installed real AstrBot SDK (optional dev group)."""

import asyncio
import importlib
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("astrbot", reason="安装 integration 依赖组以验证真实 AstrBot SDK")

from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import Image, Plain
from astrbot.api.star import Context as SDKContext
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.tool import ToolSet
from astrbot.core.astr_agent_tool_exec import FunctionToolExecutor
from astrbot.core.platform.astrbot_message import AstrBotMessage, MessageMember
from astrbot.core.platform.message_type import MessageType
from astrbot.core.platform.platform_metadata import PlatformMetadata
from astrbot.core.star.star_handler import star_handlers_registry

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "_minesweeper_sdk_test",
    ROOT / "__init__.py",
    submodule_search_locations=[str(ROOT)],
)
package = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = package
spec.loader.exec_module(package)
entry = importlib.import_module("_minesweeper_sdk_test.main")


class Event(AstrMessageEvent):
    def __init__(
        self, text="扫雷", sender="alice", group="g1", platform="p1", bot="bot1"
    ):
        message = AstrBotMessage()
        message.type = (
            MessageType.GROUP_MESSAGE if group else MessageType.FRIEND_MESSAGE
        )
        message.group_id = group
        message.self_id = bot
        message.sender = MessageMember(sender, sender)
        message.message = [Plain(text)]
        super().__init__(
            text,
            message,
            PlatformMetadata("aiocqhttp", "test", platform),
            f"{group}_{sender}",
        )
        self.is_at_or_wake_command = True
        self.sent = []
        self.fail_images = False

    async def send(self, message):
        if self.fail_images and any(isinstance(c, Image) for c in message.chain):
            raise RuntimeError("simulated image rejection")
        self.sent.append(message)


class Context:
    def __init__(self):
        self.registered_web_apis = []
        self.provider_manager = SimpleNamespace(llm_tools=ToolSet())
        self.send_message = AsyncMock()

    add_llm_tools = SDKContext.add_llm_tools
    get_llm_tool_manager = SDKContext.get_llm_tool_manager


@pytest.fixture
def plugin():
    return entry.MinesweeperPlugin(Context(), {"text_mode": True})


async def dispatch(plugin, event):
    handlers = star_handlers_registry.get_handlers_by_module_name(entry.__name__)
    for handler in handlers:
        if all(f.filter(event, {}) for f in handler.event_filters):
            await handler.handler(plugin, event, **event.get_extra("parsed_params", {}))
            return
    raise AssertionError(f"No registered command matched {event.message_str}")


@pytest.mark.parametrize(
    "command",
    [
        "扫雷",
        "minesweeper",
        "扫雷初级",
        "扫雷中级",
        "扫雷高级",
        "扫雷 -r 12 -c 16 -n 30 -s ocean",
    ],
)
async def test_sdk_command_registration_and_greedy_arguments(plugin, command):
    event = Event(command)
    await dispatch(plugin, event)
    assert len(plugin.service.sessions) == 1
    assert event.is_stopped()
    assert event.sent
    if "ocean" in command:
        session = next(iter(plugin.service.sessions.values()))
        assert (session.game.row, session.skin) == (12, "ocean")
    await plugin.terminate()


async def test_sdk_multiplayer_and_session_boundaries(plugin):
    await dispatch(plugin, Event())
    event = Event("bj A1 B2", sender="bob")
    await dispatch(plugin, event)
    session = next(iter(plugin.service.sessions.values()))
    assert session.game.flags == 2
    assert entry.session_key(Event()) == entry.session_key(Event(sender="bob"))
    assert entry.session_key(Event()) != entry.session_key(Event(platform="p2"))
    assert entry.session_key(Event()) != entry.session_key(Event(bot="bot2"))
    assert entry.session_key(Event(group="", sender="alice")) != entry.session_key(
        Event(group="", sender="bob")
    )
    flagged = Event("wk A1 B2")
    await dispatch(plugin, flagged)
    assert "取消标记" in flagged.sent[0].chain[0].text
    assert session.game.flags == 2
    await plugin.terminate()


async def test_sdk_image_delivery_and_fallback(plugin):
    plugin.config["text_mode"] = False
    event = Event()
    await dispatch(plugin, event)
    assert any(isinstance(c, Image) for c in event.sent[0].chain)
    view = Event("查看游戏")
    view.fail_images = True
    await dispatch(plugin, view)
    assert "未挖开" in view.sent[0].chain[0].text
    await plugin.terminate()


async def test_sdk_invalid_batch_and_permissions(plugin):
    plugin.config["stop_owner_only"] = True
    await dispatch(plugin, Event())
    event = Event("挖开 A1 bad")
    await dispatch(plugin, event)
    assert "不合法" in event.sent[0].chain[0].text
    denied = Event("结束扫雷", sender="bob")
    await dispatch(plugin, denied)
    assert "只有" in denied.sent[0].chain[0].text
    denied.role = "admin"
    await dispatch(plugin, denied)
    assert not plugin.service.sessions
    await plugin.terminate()


async def test_sdk_concurrent_start_lifecycle_and_tool_removal(plugin):
    await plugin.initialize()
    task = plugin.cleanup_task
    await plugin.initialize()
    assert plugin.cleanup_task is task
    await asyncio.gather(
        dispatch(plugin, Event()), dispatch(plugin, Event(sender="bob"))
    )
    assert len(plugin.service.sessions) == 1
    manager = plugin.context.get_llm_tool_manager()
    assert {tool.name for tool in manager.func_list} == {
        "minesweeper_start",
        "minesweeper_stop",
    }
    assert all(tool.handler_module_path == entry.__name__ for tool in manager.func_list)
    await plugin.terminate()
    assert task.cancelled()
    assert not plugin.service.sessions
    assert not plugin.context.registered_web_apis
    assert not manager.func_list
    await plugin.terminate()


async def test_sdk_expired_game_notifies_and_can_restart(plugin):
    await dispatch(plugin, Event())
    session = next(iter(plugin.service.sessions.values()))
    session.updated_at -= 301
    await dispatch(plugin, Event())
    plugin.context.send_message.assert_awaited_once()
    assert len(plugin.service.sessions) == 1
    await plugin.terminate()


async def call_tool(plugin, name, event, **kwargs):
    tool = plugin.context.get_llm_tool_manager().get_tool(name)
    wrapper = ContextWrapper(context=SimpleNamespace(event=event))
    responses = [
        response
        async for response in FunctionToolExecutor._execute_local(
            tool, wrapper, **kwargs
        )
    ]
    return "".join(
        content.text for response in responses for content in response.content
    )


async def test_llm_default_start_sends_board_without_stopping_agent(plugin):
    event = Event("来一局扫雷")
    result = await call_tool(plugin, "minesweeper_start", event)
    assert "扫雷开始" in result
    assert event.sent
    assert not event.is_stopped()
    session = next(iter(plugin.service.sessions.values()))
    assert session.game.row == 8
    duplicate = await call_tool(plugin, "minesweeper_start", event, difficulty="高级")
    assert "已有" in duplicate
    assert next(iter(plugin.service.sessions.values())) is session
    await plugin.terminate()


async def test_llm_custom_start_and_image_board(plugin):
    plugin.config["text_mode"] = False
    event = Event("来一局12行16列30雷的扫雷，用海洋皮肤")
    result = await call_tool(
        plugin, "minesweeper_start", event, rows=12, columns=16, mines=30, skin="ocean"
    )
    session = next(iter(plugin.service.sessions.values()))
    assert "扫雷开始" in result
    assert (
        session.game.row,
        session.game.column,
        session.game.mine_num,
        session.skin,
    ) == (12, 16, 30, "ocean")
    assert any(isinstance(component, Image) for component in event.sent[0].chain)
    await plugin.terminate()


@pytest.mark.parametrize(
    "arguments",
    [
        {"rows": True},
        {"rows": 7},
        {"difficulty": "unknown"},
        {"skin": "../winxp"},
        {"session": "other"},
        {"mines": 64},
    ],
)
async def test_llm_invalid_arguments_leave_game_unchanged(plugin, arguments):
    result = await call_tool(plugin, "minesweeper_start", Event(), **arguments)
    assert "错误" in result or "必须小于" in result
    assert not plugin.service.sessions
    await plugin.terminate()


async def test_llm_stop_uses_real_identity_permission_and_session(plugin):
    plugin.config["stop_owner_only"] = True
    await call_tool(plugin, "minesweeper_start", Event())
    missing = await call_tool(plugin, "minesweeper_stop", Event(group="other"))
    assert "没有" in missing
    denied = await call_tool(plugin, "minesweeper_stop", Event(sender="bob"))
    assert "只有" in denied
    forged = await call_tool(
        plugin, "minesweeper_stop", Event(sender="bob"), is_admin=True
    )
    assert "参数错误" in forged
    assert len(plugin.service.sessions) == 1
    admin = Event(sender="bob")
    admin.role = "admin"
    assert "已结束" in await call_tool(plugin, "minesweeper_stop", admin)
    assert not plugin.service.sessions
    assert "没有" in await call_tool(plugin, "minesweeper_stop", admin)
    await plugin.terminate()


async def test_llm_tools_retired_on_reload_without_removing_new_instance(plugin):
    replacement = entry.MinesweeperPlugin(plugin.context, {"text_mode": True})
    await plugin.terminate()
    assert len(plugin.context.get_llm_tool_manager().func_list) == 2
    assert "已停用" in await plugin.llm_start(Event())
    await replacement.terminate()
    assert not plugin.context.get_llm_tool_manager().func_list
