import curses
import imageio as iio
import logging
import numpy as np
import pygame
import time

from collections import namedtuple
from curses import wrapper
from typing import List, Sized, Tuple

from .braillify import braillify, H_STEP, V_STEP


logging.basicConfig(level=logging.INFO, 
                    format='[%(levelname)s] %(filename)s:%(lineno)s - %(message)s', 
                    filemode='w', filename='log.txt')
logger = logging.getLogger(__name__)


Vec2 = namedtuple('Vec2', ['x', 'y'])

BG_COLOR = (156, 173, 124)
FG_COLOR = (22, 22, 22)

SIZE = 80
CENTER = Vec2(SIZE // 2, SIZE // 2)
RADIUS = 10
BULLET_SIZE = 4


# TODO: investigate newline alternatives in curses to avoid -1 offset
# TODO: check whether it's possible to reduce the amount of redraws
def terminal_size(stdscr) -> Vec2:
    """
    Get terminal size in characters and multiply by V_STEP and H_STEP
    """
    rows, cols = stdscr.getmaxyx()
    return Vec2((cols - 1) * H_STEP, rows * V_STEP)


def dist2(p1: Vec2, p2: Vec2) -> float:
    return (p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2


def scale2curses(val):
    if not 0 <= val <= 255:
        raise ValueError(f'{val} is not in range 0..255')
    return round(1000 * val / 255)


def rgb2curses(r, g, b):
    return scale2curses(r), scale2curses(g), scale2curses(b)


class SoundManager:
    def __init__(self, sound_config):
        pygame.mixer.init()

        self.sounds = {}
        for name, path in sound_config.items():
            self.add(name, path)
            logger.info(f'Added sound {name}:' + 
                        f' length={self.sounds[name].get_length():.3f},' +
                        f' volume={self.sounds[name].get_volume()}')

    def add(self, name, path):
        self.sounds[name] = pygame.mixer.Sound(path)

    def play(self, name):
        logger.info(f'Playing sound {self.sounds[name]}')
        ch = self.sounds[name].play()
        # TODO: is it ok to leave channel open? otherwise blocks some animations
        # while ch.get_busy():
        #     pygame.time.delay(100)


class Clock:
    def __init__(self) -> None:
        self.time = 0

    def start(self) -> None:
        self.time = time.time()

    def getElapsed(self) -> float:
        now = time.time()
        elapsed = now - self.time
        self.time = now
        return elapsed


# TODO: consider using pads for camera movements
class Canvas:
    def __init__(self, window, width: int, height: int, use_colors: bool = True) -> None:
        logger.info(f'Creating terminal window, size={width}x{height}')

        self.width = width
        self.height = height
        self.window = window

        self.frame = np.zeros((self.height, self.width), dtype=np.uint8)

        self.cp = None
        self._init_colors(use_colors)

        # hide cursor
        curses.curs_set(0)

        # run getch in a separate thread to avoid blocking
        self.window.nodelay(1)

    def _init_colors(self, use_colors) -> None:
        self.cp = 0
        if not use_colors:
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
        curses.init_color(10, *rgb2curses(*BG_COLOR))
        curses.init_color(11, *rgb2curses(*FG_COLOR))
        curses.init_pair(self.cp, 11, 10)
        logger.info(f'Successfully set custom foreground and background colors')

    def clear(self) -> None:
        # erase instead of clear helps avoid flickering!!!
        self.window.erase()
        self.frame = np.zeros((self.height, self.width), dtype=np.uint8)

    def update(self) -> None:
        for i, row in enumerate(braillify(self.frame)):
            self.window.addstr(i, 0, row, curses.color_pair(self.cp))
        self.window.refresh()


class Sprite:
    def __init__(self, width: int = 0, height: int = 0) -> None:
        self.width = width
        self.height = height
        self.data = np.zeros((height, width), dtype=np.uint8)

    def draw_circle(self, x: int, y: int, radius: int) -> None:
        for row in range(self.height):
            for col in range(self.width):
                if dist2(Vec2
            (col, row), Vec2
            (x, y)) < radius ** 2:
                    self.data[row, col] = 1

    def from_png(self, fname: str) -> None:
        read_kwargs = {'pilmode': 'L'}
        img = iio.imread(fname, **read_kwargs)
        self.data = np.squeeze(img == 0).astype(np.uint8)
        self.height, self.width = self.data.shape


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


class Bullet(Drawable):
    def __init__(self, x: int = 0, y: int = 0, speed: int = 100, size: int = 4) -> None:
        super().__init__(x, y)
        self.speed = speed

        self.radius = size // 2
        self.sprite = Sprite(size, size)
        self.sprite.draw_circle(self.radius, self.radius, self.radius)

    def update(self, canvas: Canvas, delta: float) -> None:
        self.xc += round(self.speed * delta)
        self.draw(canvas)


class Player(Drawable):
    def __init__(self, x, y) -> None:
        super().__init__(x, y)
        self.sprite = Sprite()
        self.sprite.from_png('assets/images/key.png')

    def update(self, canvas: Canvas) -> None:
        self.draw(canvas)

    def bullet_spawn_pos(self, bullet_size) -> Vec2:
        return Vec2(self.x + self.sprite.width - bullet_size // 2, self.yc)


class Game:
    def __init__(self, window, sound_config) -> None:
        self.window = window
        self.clock = Clock()
        self.sound_manager = SoundManager(sound_config)

        size = terminal_size(window)
        self.canvas = Canvas(window, *size)
        
        self.player = Player(SIZE // 4, SIZE // 2)
        self.bullets = []        
        
        self.is_running = True

    def process_input(self, key: int) -> None:
        if key == ord('q'):
            self.is_running = False
        elif key == ord('w'):
            self.player.yc -= 1
        elif key == ord('s'):
            self.player.yc += 1
        elif key == ord(' '):
            # TODO: refactor it as player's method (how to pass sound manager?)
            bullet = Bullet(*self.player.bullet_spawn_pos(BULLET_SIZE), 
                            size=BULLET_SIZE)
            self.bullets.append(bullet)
            self.sound_manager.play('shoot')
        return True

    def run(self):
        self.clock.start()
        while self.is_running:
            delta = self.clock.getElapsed()
            self.update(delta)
            self.process_input(self.window.getch())
            
            debug_str = 'FPS: {:.2f}'.format(1 / delta)
            self.window.addstr(0, 0, debug_str)
            self.window.refresh()

    def update(self, delta: float) -> None:
        self.canvas.clear()
        self.player.update(self.canvas)
        for bullet in self.bullets:
            bullet.update(self.canvas, delta)
        self.canvas.update()