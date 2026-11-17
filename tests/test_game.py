import random
from io import BytesIO

import pytest
from PIL import Image

from astrbot_plugin_minesweeper.game import GameState, MineSweeper, MoveResult
from astrbot_plugin_minesweeper.render import render_board
from astrbot_plugin_minesweeper.skins import load_skin, skin_list


@pytest.mark.parametrize(
    ("rows", "cols", "mines"),
    [(8, 8, 64), (8, 8, 65), (7, 8, 10), (25, 8, 10), (8, 31, 10), (8, 8, 9)],
)
def test_reject_invalid_board(rows, cols, mines):
    with pytest.raises(ValueError, match=r"行数|列数|雷数"):
        MineSweeper(rows, cols, mines)


@pytest.mark.parametrize("seed", range(30))
def test_first_open_safe_and_counts_correct(seed):
    game = MineSweeper(8, 8, 10, random.Random(seed))
    assert game.open(3, 3) != MoveResult.FAIL
    assert not game.tiles[3][3].is_mine
    assert sum(t.is_mine for t in game.all_tiles()) == game.mine_num
    for x in range(game.row):
        for y in range(game.column):
            assert game.tiles[x][y].count == sum(
                game.tiles[nx][ny].is_mine for nx, ny in game.neighbors(x, y)
            )


def test_dense_board_terminates_and_wins_on_only_safe_cell():
    game = MineSweeper(8, 8, 63)
    assert game.open(0, 0) == MoveResult.WIN
    assert game.state == GameState.WIN
    assert game.elapsed == 0
    assert game.open(0, 1) == MoveResult.FINISHED


def test_large_zero_area_iterates_and_preserves_flags():
    game = MineSweeper(24, 30, 10)
    game.state = GameState.GAMING
    # Place ten mines at the bottom right, leaving a large connected zero area.
    for y in range(20, 30):
        game.tiles[23][y].is_mine = True
    for x in range(game.row):
        for y in range(game.column):
            game.tiles[x][y].count = sum(
                game.tiles[nx][ny].is_mine for nx, ny in game.neighbors(x, y)
            )
    game.mark(0, 1)
    assert game.open(0, 0) == MoveResult.OK
    assert game.tiles[0][1].marked
    assert not game.tiles[0][1].is_open
    game.mark(0, 1)
    assert game.open(0, 1) == MoveResult.WIN


def test_mark_toggle_open_guard_and_preparation():
    game = MineSweeper(8, 8, 10)
    assert game.mark(0, 0) == MoveResult.OK
    assert game.open(0, 0) == MoveResult.FLAGGED
    assert game.state == GameState.PREPARE
    assert game.mark(0, 0) == MoveResult.OK
    game.open(0, 0)
    assert game.open(0, 0) == MoveResult.OPENED
    assert game.mark(0, 0) == MoveResult.OPENED
    assert game.open(-1, 0) == MoveResult.OUT
    assert game.mark(8, 0) == MoveResult.OUT


def test_correct_flags_win_and_mine_explosion_loses():
    game = MineSweeper(8, 8, 10, random.Random(7))
    game.open(0, 0)
    mines = [(x, y) for x in range(8) for y in range(8) if game.tiles[x][y].is_mine]
    for x, y in mines:
        result = game.mark(x, y)
    assert result == MoveResult.WIN
    assert game.mark(0, 0) == MoveResult.FINISHED
    other = MineSweeper(8, 8, 10, random.Random(7))
    other.open(0, 0)
    x, y = mines[0]
    assert other.open(x, y) == MoveResult.FAIL
    assert other.tiles[x][y].boom
    assert all(t.is_open for t in other.all_tiles() if t.is_mine)


def test_open_all_safe_tiles_wins_and_hidden_text_does_not_leak():
    game = MineSweeper(8, 8, 10, random.Random(9))
    before = game.text_board()
    game._plant(0, 0)
    assert game.text_board() == before
    for x in range(game.row):
        for y in range(game.column):
            if not game.tiles[x][y].is_mine and not game.finished:
                game.open(x, y)
    assert game.state == GameState.WIN


@pytest.mark.parametrize("skin", skin_list)
def test_all_skins_render_valid_png_without_mutating_game(skin):
    game = MineSweeper(8, 8, 10)
    text = game.text_board()
    first = render_board(game, skin)
    assert first == render_board(game, skin)
    assert game.text_board() == text
    with Image.open(BytesIO(first)) as image:
        assert image.format == "PNG"
        assert image.size == (456, 582)
        image.verify()


def test_invalid_skin_cannot_traverse_resource_directory():
    with pytest.raises(ValueError, match="未知的扫雷皮肤"):
        load_skin(8, 8, "../winxp")
