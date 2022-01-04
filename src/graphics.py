from __future__ import annotations

import curses
import imageio as iio
import logging
import numpy as np

from typing import Dict, Optional

from src.events import AnimationEndedEvent

from .braillify import braillify, H_STEP, V_STEP
from .common import Vec2, dist2


logger = logging.getLogger(__name__)


def scale2curses(val):
    if not 0 <= val <= 255:
        raise ValueError(f'{val} is not in range 0..255')
    return round(1000 * val / 255)


def rgb2curses(r, g, b):
    return scale2curses(r), scale2curses(g), scale2curses(b)


def preprocess_image(img):
    return np.squeeze(img[:, :, 1] > 0).astype(np.uint8)


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
    
    # TODO: sprites should have an option to be transparent
    def draw(self, canvas: Canvas, x: int, y: int):
        w_visible = min(self.width, canvas.width - x)
        h_visible = min(self.height, canvas.height - y)
        # logger.info(f'{self.kind} x={self.x}, y={self.y}, w={w_visible}, h={h_visible}')
        if w_visible > 0 and h_visible > 0:
            canvas.frame[y:y+h_visible, x:x+w_visible] = self.data[:h_visible, :w_visible]

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


class AnimatedSprite(Sprite):
    SUPPORTED_MODES = ['repeat', 'stop']

    def __init__(self, width: int = 0, height: int = 0, frames: int = 0,
                 frame_data: Optional[np.array] = None, 
                 mode: str = 'repeat', fps: int = 5) -> None:
        self.width = width
        self.height = height
        self.frames = frames
        self.frame_data = frame_data if frame_data is not None \
            else np.zeros((height, width, frames), dtype=np.uint8)
        
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
        return np.squeeze(self.frame_data[:, :, self.current_frame])

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

    # TODO: load sprites from files only once, not at every spawn
    @classmethod
    def from_gif(cls, fname: str, **kwargs: Dict) -> AnimatedSprite:
        read_kwargs = {'pilmode': 'LA'}
        im = iio.get_reader(fname, **read_kwargs)
        frames = [preprocess_image(im.get_data(i)) for i in range(len(im))]
        data = np.dstack(frames)
        height, width, n_frames = data.shape
        logger.info(f'Read GIF - {n_frames} frames of size {width}x{height}')
        return AnimatedSprite(width, height, n_frames, data, **kwargs)