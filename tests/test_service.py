import pytest

from astrbot_plugin_minesweeper.commands import parse_positions, parse_start
from astrbot_plugin_minesweeper.game import GameState
from astrbot_plugin_minesweeper.service import GameService


def test_custom_options_and_presets():
    options = parse_start("--row=12 -c 16 --num 30 -s OCEAN", "winxp")
    assert (options.rows, options.columns, options.mines, options.skin) == (
        12,
        16,
        30,
        "ocean",
    )
    assert parse_start("中级", "winxp").mines == 40
    assert parse_start("", "winxp", "高级").columns == 30


@pytest.mark.parametrize(
    "text", ["-r", "-r x", "--unknown 1", "-s ../winxp", "--skin=", '"', "1 2 3"]
)
def test_invalid_start_arguments(text):
    with pytest.raises(
        ValueError, match=r"缺少值|整数|未知参数|支持的皮肤|No closing quotation"
    ):
        parse_start(text, "winxp")


def test_positions_deduplicate_and_accept_separators():
    assert parse_positions("a1 A1，B2、c3") == [
        ("A1", 0, 0),
        ("B2", 1, 1),
        ("C3", 2, 2),
    ]


@pytest.mark.parametrize(
    "text", ["", "A0", "AA1", "A-1", "A1000", "A1 oops", "A1 " * 101]
)
def test_invalid_position_batch_rejected(text):
    with pytest.raises(ValueError, match=r"请提供位置|不合法|最多操作"):
        parse_positions(text)


def start(service, key="group", owner="alice"):
    return service.start(
        key, owner, "platform:GroupMessage:1", parse_start("", "winxp")
    )


def test_session_isolation_capacity_and_duplicate_start():
    service = GameService(max_games=2)
    first = start(service)
    assert first.session is not None
    assert start(service).session is None
    assert start(service, "private").session is not None
    assert start(service, "third").session is None
    service.move("group", "A1", mark=True)
    assert not service.sessions["private"].game.tiles[0][0].marked


def test_atomic_format_validation_and_per_position_boundary_feedback():
    service = GameService()
    session = start(service).session
    with pytest.raises(ValueError, match="不合法"):
        service.move("group", "A1 oops")
    assert session.game.state == GameState.PREPARE
    assert "超出边界" in service.move("group", "Z99 A1", mark=True).text
    assert session.game.tiles[0][0].marked


def test_owner_permission_and_expiry(monkeypatch):
    service = GameService(timeout=10)
    session = start(service).session
    assert "只有" in service.stop("group", "bob", False, True).text
    assert "已结束" in service.stop("group", "bob", True, True).text
    session = start(service).session
    monkeypatch.setattr(
        "astrbot_plugin_minesweeper.service.time.monotonic",
        lambda: session.updated_at + 11,
    )
    assert service.expire() == [session.origin]
    assert service.expire() == []
    assert service.show("group").session is None


def test_finished_batch_removes_session_and_stops_remaining_moves():
    service = GameService()
    reply = service.start(
        "dense", "a", "p:GroupMessage:1", parse_start("-n 63", "winxp")
    )
    result = service.move("dense", "A1 B1")
    assert "胜利" in result.text
    assert result.session is reply.session
    assert "dense" not in service.sessions
