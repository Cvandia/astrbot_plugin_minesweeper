"""Pillow rendering using the upstream Minesweeper X sprite sheets."""

from io import BytesIO

from PIL import ImageDraw
from PIL.Image import Resampling

from .game import GameState, MineSweeper
from .skins import load_font, load_skin


def render_board(game: MineSweeper, skin_name: str = "winxp", scale: int = 3) -> bytes:
    """Return a complete PNG without writing temporary files."""
    skin = load_skin(game.row, game.column, skin_name)
    bg = skin.background.copy()
    face_num = {GameState.WIN: 3, GameState.FAIL: 2}.get(game.state, 0)
    face = skin.faces[face_num]
    bg.paste(face, ((bg.width - face.width) // 2, 15))
    remaining = max(-99, min(999, game.mine_num - game.flags))
    for i, char in enumerate(f"{remaining:03d}"):
        digit = skin.digits[10 if char == "-" else int(char)]
        bg.paste(digit, (18 + i * (digit.width + 2), 17))
    for i, char in enumerate(f"{min(999, game.elapsed):03d}"):
        digit = skin.digits[int(char)]
        bg.paste(digit, (bg.width - 16 - (3 - i) * (digit.width + 2), 17))
    for x, row in enumerate(game.tiles):
        for y, tile in enumerate(row):
            if tile.is_open:
                if tile.is_mine:
                    image = skin.icons[5 if tile.boom else 2]
                elif tile.marked:
                    image = skin.icons[4]
                else:
                    image = skin.numbers[tile.count]
            else:
                image = skin.icons[3 if tile.marked else 0]
            bg.paste(image, (12 + y * image.width, 55 + x * image.height))
    bg = bg.resize((bg.width * scale, bg.height * scale), Resampling.NEAREST)
    font = load_font("00TT.TTF", 7 * scale)
    draw = ImageDraw.Draw(bg)
    for x, row in enumerate(game.tiles):
        for y, tile in enumerate(row):
            if tile.is_open or tile.marked:
                continue
            text = f"{chr(65 + x)}{y + 1}"
            left, top, right, bottom = font.getbbox(text)
            px = (12 + y * 16 + 8) * scale - (right - left) / 2 - left
            py = (55 + x * 16 + 8) * scale - (bottom - top) / 2 - top
            draw.text((px, py), text, font=font, fill="black")
    output = BytesIO()
    bg.save(output, format="PNG")
    return output.getvalue()
