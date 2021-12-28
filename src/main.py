"""
Braille unicode for refining console graphics

http://www.alanwood.net/unicode/braille_patterns.html
https://github.com/asciimoo/drawille

dots:
   ,___,
   |1 4|
   |2 5|
   |3 6|
   |7 8|
   `````
"""

import curses
import imageio as iio
import logging
import numpy as np
import pygame
import time

from collections import namedtuple
from curses import wrapper
from typing import List, Tuple

logging.basicConfig(level=logging.INFO, 
                    format='[%(levelname)s] %(filename)s:%(lineno)s - %(message)s', 
                    filemode='w', filename='log.txt')
logger = logging.getLogger(__name__)

Point = namedtuple('Point', ['x', 'y'])

BRAILLE_OFFSET = 0x2800
H_STEP = 2
V_STEP = 4
PIXEL_MAP = np.array(
    [[0x01, 0x08], 
     [0x02, 0x10], 
     [0x04, 0x20], 
     [0x40, 0x80]]
)

BG_COLOR = (156, 173, 124)
FG_COLOR = (22, 22, 22)

SIZE = 80
CENTER = Point(SIZE // 2, SIZE // 2)
RADIUS = 10
BULLET_SIZE = 4

CONFIG = {
    'sounds': {
        'shoot': 'assets/sounds/shoot.wav',
        'block_hit': 'assets/sounds/block_hit.wav',
        'player_hit': 'assets/sounds/player_hit.wav',
        'spider_hit': 'assets/sounds/spider_hit.wav'
    }
}

# TODO: investigate newline alternatives in curses to avoid -1 offset
# TODO: check whether it's possible to reduce the amount of redraws
def terminal_size(stdscr) -> Tuple[int, int]:
    """
    Get terminal size in characters and multiply by V_STEP and H_STEP
    """
    rows, cols = stdscr.getmaxyx()
    return (cols - 1) * H_STEP, (rows - 1) * V_STEP


def dist2(p1: Point, p2: Point) -> float:
    return (p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2


def braille_cell(cell: np.array, bg_char: str = None) -> str:
    value = np.sum(cell * PIXEL_MAP)
    if bg_char and not value:
        return bg_char
    return chr(BRAILLE_OFFSET + value)


# TODO: braillify might output one more row than terminal size
# TODO: add inverse mode for braille
def braillify(frame: np.array) -> str:
    rows, cols = frame.shape    

    braille = ''
    for row in range(0, rows, V_STEP):
        for col in range(0, cols, H_STEP):
            braille += braille_cell(frame[row:row+V_STEP, col:col+H_STEP])
        braille += '\n'
    
    return braille


class SoundManager:
    def __init__(self, sound_config):
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


class Canvas:
    def __init__(self, window, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.window = window
        self.clear()
    
    def clear(self) -> None:
        # erase instead of clear helps avoid flickering!!!
        self.window.erase()
        self.frame = np.zeros((self.height, self.width), dtype=np.uint8)

    def update(self) -> None:
        # debug_str = f'{self.width}x{self.height} - {len(braillify(self.frame))}'
        # self.window.addstr(0, 0, debug_str)
        self.window.addstr(0, 0, braillify(self.frame), curses.color_pair(1))
        self.window.refresh()


class Sprite:
    def __init__(self, width: int = 0, height: int = 0) -> None:
        self.width = width
        self.height = height
        self.data = np.zeros((height, width), dtype=np.uint8)

    def draw_circle(self, x: int, y: int, radius: int) -> None:
        for row in range(self.height):
            for col in range(self.width):
                if dist2(Point(col, row), Point(x, y)) < radius ** 2:
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

    def bullet_spawn_point(self, bullet_size) -> Point:
        return self.x + self.sprite.width - bullet_size // 2, self.yc


class Game:
    def __init__(self, window, size, sound_manager) -> None:
        self.canvas = Canvas(window, *size)
        self.player = Player(SIZE // 4, SIZE // 2)
        self.bullets = []
        self.sound_manager = sound_manager
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
            bullet = Bullet(*self.player.bullet_spawn_point(BULLET_SIZE), 
                            size=BULLET_SIZE)
            self.bullets.append(bullet)
            self.sound_manager.play('shoot')
        return True

    def update(self, delta: float) -> None:
        self.canvas.clear()
        self.player.update(self.canvas)
        for bullet in self.bullets:
            bullet.update(self.canvas, delta)
        self.canvas.update()


def scale2curses(val):
    if not 0 <= val <= 255:
        raise ValueError(f'{val} is not in range 0..255')
    return round(1000 * val / 255)


def rgb2curses(r, g, b):
    return scale2curses(r), scale2curses(g), scale2curses(b)


def main(stdscr):
    pygame.mixer.init()
    sound_manager = SoundManager(CONFIG['sounds'])

    logger.info(f'Terminal size: {terminal_size(stdscr)}')
    logger.info(f'Terminal can change color: {curses.can_change_color()}')
    logger.info(f'Colors available: {curses.has_colors()}')

    curses.start_color()
    curses.init_color(10, *rgb2curses(*BG_COLOR))
    curses.init_color(11, *rgb2curses(*FG_COLOR))
    curses.init_pair(1, 11, 10)
    curses.curs_set(0)
    stdscr.nodelay(1)

    clock = Clock()
    game = Game(stdscr, terminal_size(stdscr), sound_manager)

    clock.start()
    while game.is_running:
        delta = clock.getElapsed()
        game.update(delta)
        game.process_input(stdscr.getch())
        
        debug_str = 'FPS: {:.2f}'.format(1 / delta)
        stdscr.addstr(0, 0, debug_str)
        stdscr.refresh()
        


if __name__ == "__main__":
    wrapper(main)