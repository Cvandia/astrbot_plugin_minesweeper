"""Minesweeper rules adapted from MeetWq/noneplugin's MIT implementation."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

MIN_ROWS, MAX_ROWS = 8, 24
MIN_COLUMNS, MAX_COLUMNS = 8, 30
MIN_MINES = 10


class GameState(Enum):
    PREPARE = "prepare"
    GAMING = "gaming"
    WIN = "win"
    FAIL = "fail"


class MoveResult(Enum):
    OK = "ok"
    OUT = "out"
    OPENED = "opened"
    FLAGGED = "flagged"
    WIN = "win"
    FAIL = "fail"
    FINISHED = "finished"


@dataclass
class Tile:
    is_mine: bool = False
    is_open: bool = False
    marked: bool = False
    boom: bool = False
    count: int = 0


class MineSweeper:
    """A bounded board; mines are sampled only after the first valid opening."""

    def __init__(
        self, row: int, column: int, mine_num: int, rng: random.Random | None = None
    ) -> None:
        if not MIN_ROWS <= row <= MAX_ROWS:
            raise ValueError("行数应在 8~24 之间")
        if not MIN_COLUMNS <= column <= MAX_COLUMNS:
            raise ValueError("列数应在 8~30 之间")
        if not MIN_MINES <= mine_num < row * column:
            raise ValueError("雷数应不少于 10，且必须小于行数×列数")
        self.row = row
        self.column = column
        self.mine_num = mine_num
        self.tiles = [[Tile() for _ in range(column)] for _ in range(row)]
        self.state = GameState.PREPARE
        self.started_at: float | None = None
        self.ended_at: float | None = None
        self.rng = rng or random.Random()  # noqa: S311 - non-security game randomness

    @property
    def finished(self) -> bool:
        return self.state in (GameState.WIN, GameState.FAIL)

    @property
    def elapsed(self) -> int:
        if self.started_at is None:
            return 0
        end = self.ended_at if self.ended_at is not None else time.monotonic()
        return max(0, int(end - self.started_at))

    @property
    def flags(self) -> int:
        return sum(tile.marked for tile in self.all_tiles())

    def all_tiles(self) -> Iterator[Tile]:
        for row in self.tiles:
            yield from row

    def is_valid(self, x: int, y: int) -> bool:
        return 0 <= x < self.row and 0 <= y < self.column

    def neighbors(self, x: int, y: int) -> Iterator[tuple[int, int]]:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if (dx or dy) and self.is_valid(x + dx, y + dy):
                    yield x + dx, y + dy

    def _plant(self, first_x: int, first_y: int) -> None:
        candidates = [
            (x, y)
            for x in range(self.row)
            for y in range(self.column)
            if (x, y) != (first_x, first_y)
        ]
        for x, y in self.rng.sample(candidates, self.mine_num):
            self.tiles[x][y].is_mine = True
        for x in range(self.row):
            for y in range(self.column):
                self.tiles[x][y].count = sum(
                    self.tiles[nx][ny].is_mine for nx, ny in self.neighbors(x, y)
                )
        self.started_at = time.monotonic()
        self.state = GameState.GAMING

    def _finish(self, state: GameState) -> MoveResult:
        self.state = state
        self.ended_at = time.monotonic()
        for tile in self.all_tiles():
            if (tile.is_mine and not tile.marked) or (tile.marked and not tile.is_mine):
                tile.is_open = True
        return MoveResult.WIN if state == GameState.WIN else MoveResult.FAIL

    def open(self, x: int, y: int) -> MoveResult:  # noqa: PLR0911 - distinct move outcomes
        if self.finished:
            return MoveResult.FINISHED
        if not self.is_valid(x, y):
            return MoveResult.OUT
        tile = self.tiles[x][y]
        if tile.is_open:
            return MoveResult.OPENED
        if tile.marked:
            return MoveResult.FLAGGED
        if self.state == GameState.PREPARE:
            self._plant(x, y)
        if tile.is_mine:
            tile.boom = True
            return self._finish(GameState.FAIL)

        pending = [(x, y)]
        while pending:
            nx, ny = pending.pop()
            current = self.tiles[nx][ny]
            if current.is_open or current.marked or current.is_mine:
                continue
            current.is_open = True
            if current.count == 0:
                pending.extend(self.neighbors(nx, ny))
        if all(t.is_open or t.is_mine for t in self.all_tiles()):
            return self._finish(GameState.WIN)
        return MoveResult.OK

    def mark(self, x: int, y: int) -> MoveResult:
        if self.finished:
            return MoveResult.FINISHED
        if not self.is_valid(x, y):
            return MoveResult.OUT
        tile = self.tiles[x][y]
        if tile.is_open:
            return MoveResult.OPENED
        tile.marked = not tile.marked
        if (
            self.state == GameState.GAMING
            and self.flags == self.mine_num
            and all(not t.marked or t.is_mine for t in self.all_tiles())
        ):
            return self._finish(GameState.WIN)
        return MoveResult.OK

    def text_board(self) -> str:
        """Render only public tile state, including a legend and row/column labels."""
        lines = ["    " + " ".join(f"{n:>2}" for n in range(1, self.column + 1))]
        for x, row in enumerate(self.tiles):
            cells = []
            for tile in row:
                symbol = "#"
                if tile.is_open:
                    symbol = "*" if tile.is_mine else str(tile.count or ".")
                    if tile.marked and not tile.is_mine:
                        symbol = "!"
                elif tile.marked:
                    symbol = "F"
                cells.append(f"{symbol:>2}")
            lines.append(f"{chr(65 + x)} | " + " ".join(cells))
        lines.append(f"剩余雷数：{self.mine_num - self.flags}；用时：{self.elapsed} 秒")
        lines.append("# 未挖开 / F 标记 / . 空白 / * 地雷 / ! 错误标记")
        return "\n".join(lines)
