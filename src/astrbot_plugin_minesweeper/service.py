"""Session state without platform dependencies; callers serialize mutations."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .commands import StartOptions, parse_positions
from .game import GameState, MineSweeper, MoveResult


@dataclass
class Session:
    game: MineSweeper
    skin: str
    owner: str
    origin: str
    updated_at: float = field(default_factory=time.monotonic)


@dataclass
class Reply:
    text: str = ""
    session: Session | None = None


class GameService:
    def __init__(self, timeout: int = 300, max_games: int = 100) -> None:
        self.timeout = timeout
        self.max_games = max_games
        self.sessions: dict[str, Session] = {}

    def expire(self) -> list[str]:
        now = time.monotonic()
        keys = [
            k for k, s in self.sessions.items() if now - s.updated_at >= self.timeout
        ]
        return [self.sessions.pop(key).origin for key in keys]

    def start(self, key: str, owner: str, origin: str, options: StartOptions) -> Reply:
        if key in self.sessions:
            return Reply("当前会话已有扫雷游戏，请继续游戏或发送“结束扫雷”")
        if len(self.sessions) >= self.max_games:
            return Reply("当前进行中的游戏过多，请稍后再试")
        game = MineSweeper(options.rows, options.columns, options.mines)
        session = Session(game, options.skin, owner, origin)
        self.sessions[key] = session
        return Reply("扫雷开始！使用“挖开 A1 B2”挖开、“标记 C3”插旗。", session)

    def show(self, key: str) -> Reply:
        session = self.sessions.get(key)
        if session is None:
            return Reply("当前会话没有扫雷游戏，发送“扫雷”开始")
        session.updated_at = time.monotonic()
        return Reply(session=session)

    def move(self, key: str, positions: str, mark: bool = False) -> Reply:
        session = self.sessions.get(key)
        if session is None:
            return Reply("当前会话没有扫雷游戏，发送“扫雷”开始")
        parsed = parse_positions(positions)
        messages = []
        for label, x, y in parsed:
            result = session.game.mark(x, y) if mark else session.game.open(x, y)
            if result in (MoveResult.WIN, MoveResult.FAIL):
                self.sessions.pop(key)
                text = (
                    "恭喜，扫雷胜利！"
                    if session.game.state == GameState.WIN
                    else "踩到地雷，游戏失败！"
                )
                messages.append(f"{text}用时 {session.game.elapsed} 秒")
                break
            if result == MoveResult.OUT:
                messages.append(f"位置 {label} 超出边界")
            elif result == MoveResult.OPENED:
                messages.append(f"位置 {label} 已被挖开")
            elif result == MoveResult.FLAGGED:
                messages.append(f"位置 {label} 已标记，请先取消标记")
        session.updated_at = time.monotonic()
        return Reply("\n".join(messages), session)

    def stop(self, key: str, sender: str, is_admin: bool, owner_only: bool) -> Reply:
        session = self.sessions.get(key)
        if session is None:
            return Reply("当前会话没有扫雷游戏")
        if owner_only and sender != session.owner and not is_admin:
            return Reply("只有本局发起者或 AstrBot 管理员可以结束游戏")
        self.sessions.pop(key)
        return Reply("扫雷游戏已结束")
