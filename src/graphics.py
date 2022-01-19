from __future__ import annotations

import curses
from dataclasses import dataclass
from enum import Enum, auto
import logging
import numpy as np

from typing import Dict, Optional

from .braillify import braillify, H_STEP, V_STEP
from .common import Vec2, dist2
from .textures import Texture


logger = logging.getLogger(__name__)


def scale2curses(val):
    if not 0 <= val <= 255:
        raise ValueError(f'{val} is not in range 0..255')
    return round(1000 * val / 255)


def rgb2curses(r, g, b):
    return scale2curses(r), scale2curses(g), scale2curses(b)


@dataclass
class Camera:
    x: int
    mode: str
    speed: int

    def update(self, delta: float):
        self.x += round(self.speed * delta)


class CanvasMode(Enum):
    ROW_BY_ROW = 'row-by-row'
    ALL_AT_ONCE = 'all-at-once'


# TODO: assign game objects to layers to control draw order
class Canvas:
    def __init__(self, window, canvas_config: Dict) -> None:
        self.window = window
        width, height = canvas_config['size']
        self.draw_width, self.draw_height = canvas_config['window_size']
        self.width = width
        self.height = height

        logger.info(f'Creating canvas, size={width}x{height}')
        logger.info(f'Visible area in the terminal window, size={self.draw_width}x{self.draw_height}')

        self.frame = np.zeros((self.height, self.width), dtype=np.uint8)
        self.inverse = canvas_config['inverse']
        self.mode = canvas_config['mode']
        if self.mode not in [CanvasMode.ROW_BY_ROW.value, CanvasMode.ALL_AT_ONCE.value]:
            raise ValueError(f"Unsupported camera mode: {self.mode}")

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

    def update(self, camera: Camera) -> None:
        visible_area = self.frame[:, camera.x:camera.x+self.draw_width]
        if self.mode == CanvasMode.ROW_BY_ROW.value:
            for i, row in enumerate(braillify(visible_area, self.inverse)):
                self.window.addstr(i, 0, row, curses.color_pair(self.cp))
        elif self.mode == CanvasMode.ALL_AT_ONCE.value:
            self.window.addstr(0, 0, '\n'.join(braillify(visible_area, self.inverse)), 
                            curses.color_pair(self.cp))
        self.window.refresh()


class Sprite:
    def __init__(self, texture: Texture) -> None:
        self.texture = texture
        self.width = texture.width
        self.height = texture.height

    @property
    def data(self):
        return self.texture.data

    @property
    def mask(self):
        return self.texture.mask

    # TODO: handle case of negative y somehow
    def draw(self, canvas: Canvas, x: int, y: int):
        w_visible = min(self.width, canvas.width - x)
        h_visible = min(self.height, canvas.height - y)
        # logger.info(f'{canvas.frame}')
        # logger.info(f'x={x}, y={y}, w={w_visible}, h={h_visible}')
        if w_visible > 0 and h_visible > 0:
            np.putmask(canvas.frame[y:y+h_visible, x:x+w_visible],
                       self.mask[:h_visible, :w_visible],
                       self.data[:h_visible, :w_visible])


class AnimatedSprite(Sprite):
    SUPPORTED_MODES = ['repeat', 'stop']

    def __init__(self, texture: Texture,
                 mode: str = 'repeat', fps: int = 5) -> None:
        self.texture = texture
        self.width = texture.width
        self.height = texture.height
        self.frames = texture.frames
        
        self.fps = fps
        self.update_time = 1.0 / fps
        self.mode = mode
        if mode not in self.SUPPORTED_MODES:
            assert False, f"mode {self.mode} is not implemented"

        logger.info(f'Added new animated sprite: mode={mode}, fps={fps}')

        self.current_frame = 0
        self.elapsed = 0
    
    @property
    def data(self):
        return np.squeeze(self.texture.data[:, :, self.current_frame])

    @property
    def mask(self):
        return np.squeeze(self.texture.mask[:, :, self.current_frame])

    def update(self, delta: float):
        """
        Returns false if got rid of animation frames, true otherwise
        (when did not update frame, there are enough frames, or mode
        is set to repeat)
        """
        self.elapsed += delta
        if self.elapsed < self.update_time:
            return True
        
        self.elapsed -= self.update_time
        self.current_frame += 1
        if self.current_frame < self.frames:
            return True
        
        if self.mode == "repeat":
            self.current_frame = 0
        elif self.mode == "stop":
            self.current_frame -= 1
            logger.info('Animation ended - sprite update')
            return False
        else:
            assert False, "unreachable"
        return True


class LineType(Enum):
    SOLID = auto()
    DASHED = auto()


@dataclass
class Line:
    xs: int
    ys: int
    xe: int
    ye: int
    width: int
    data: np.array
    type: LineType

    def generate_data(self, length, width, type, dash_size):
        if type == LineType.SOLID:
            self.data = np.ones((length, width))
        elif type == LineType.DASHED:
            self.data = np.zeros((length, width))
            xs = np.linspace(0, length, length // (2 * dash_size), dtype=np.uint8)
            for x in xs:
                logger.info(f'{x}, {dash_size}')
                self.data[x:x+dash_size, :] = 1
        else:
            raise ValueError(f'Unsupported line type: {type}')

    def draw(self, canvas: Canvas):
        if self.xs == self.xe:
            dx = (self.width + 1) // 2
            length = self.ye - self.ys
            canvas.frame[self.ys:self.ye, self.xs-dx:self.xs+dx-1] = self.data[:length, :]
        elif self.ys == self.ye:
            dy = (self.width + 1) // 2
            length = self.xe - self.xs
            canvas.frame[self.ys-dy:self.ys+dy-1, self.xs:self.xe] = self.data[:length, :].T
        else:
            raise ValueError('Only vertical or horizontal lines are supported')
