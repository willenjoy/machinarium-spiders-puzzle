from __future__ import annotations

import curses
import imageio as iio
import logging
import numpy as np

from typing import Dict, Optional

from .braillify import braillify, H_STEP, V_STEP
from .common import Vec2, dist2


logger = logging.getLogger(__name__)


def scale2curses(val):
    if not 0 <= val <= 255:
        raise ValueError(f'{val} is not in range 0..255')
    return round(1000 * val / 255)


def rgb2curses(r, g, b):
    return scale2curses(r), scale2curses(g), scale2curses(b)


# TODO: consider using pads for camera movements
class Canvas:
    def __init__(self, window, canvas_config: Dict) -> None:
        self.window = window
        width, height = canvas_config['size']
        self.width = width
        self.height = height

        logger.info(f'Creating terminal window, size={width}x{height}')

        self.frame = np.zeros((self.height, self.width), dtype=np.uint8)
        self.inverse = canvas_config['inverse']

        self.cp = None
        self._init_colors(canvas_config['colors'])

        # hide cursor
        curses.curs_set(0)

        # run getch in a separate thread to avoid blocking
        self.window.nodelay(1)

    def _init_colors(self, color_config) -> None:
        self.cp = 0
        if not color_config['use_colors']:
            logger.info(f'Using the default color scheme')
            return

        curses.start_color()
        logger.info(f'Terminal can change color: {curses.can_change_color()}')
        logger.info(f'Colors available: {curses.has_colors()}')

        if not curses.can_change_color():
            logger.info(f'Cannot set custom colors')
            return 

        # Default color pair cannot be changed, use color_pair 1
        self.cp = 1
        curses.init_color(10, *rgb2curses(*color_config['bg_color']))
        curses.init_color(11, *rgb2curses(*color_config['fg_color']))
        curses.init_pair(self.cp, 11, 10)
        logger.info(f'Successfully set custom foreground and background colors')

    def clear(self) -> None:
        # erase instead of clear helps avoid flickering!!!
        self.window.erase()
        self.frame = np.zeros((self.height, self.width), dtype=np.uint8)

    def update(self) -> None:
        for i, row in enumerate(braillify(self.frame, self.inverse)):
            self.window.addstr(i, 0, row, curses.color_pair(self.cp))
        self.window.refresh()


class Sprite:
    def __init__(self, width: int = 0, height: int = 0, data: Optional[np.array] = None) -> None:
        self.width = width
        self.height = height
        self.data = data if data is not None else np.zeros((height, width), dtype=np.uint8)
    
    @classmethod
    def from_circle(cls, diameter: int) -> Sprite:
        radius = diameter // 2
        center = Vec2(diameter // 2, diameter // 2)
        sprite = Sprite(diameter, diameter)
        for row in range(diameter):
            for col in range(diameter):
                if dist2(Vec2(col, row), center) < radius ** 2:
                    sprite.data[row, col] = 1
        return sprite

    @classmethod
    def from_png(cls, fname: str) -> Sprite:
        read_kwargs = {'pilmode': 'L'}
        img = iio.imread(fname, **read_kwargs)
        data = np.squeeze(img == 0).astype(np.uint8)
        height, width = data.shape
        return Sprite(width, height, data)


class Drawable:
    def __init__(self, x, y) -> None:
        self.xc = x
        self.yc = y
        self.sprite = Sprite()

    @property
    def x(self) -> int:
        return self.xc - self.sprite.width // 2
    
    @property
    def y(self) -> int:
        return self.yc - self.sprite.height // 2

    def draw(self, canvas: Canvas):
        w_visible = min(self.sprite.width, canvas.width - self.x)
        h_visible = min(self.sprite.height, canvas.height - self.y)
        if w_visible > 0 and h_visible > 0:
            canvas.frame[self.y:self.y+h_visible, self.x:self.x+w_visible] = self.sprite.data[:h_visible, :w_visible]
