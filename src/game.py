import logging
import time

from .braillify import H_STEP, V_STEP
from .common import Vec2
from .graphics import Canvas
from .objects import Bullet, Enemy, ObjectManager, BulletFactory, Block
from .physics import CollisionManager
from .sounds import SoundManager


logger = logging.getLogger(__name__)


def terminal_size(stdscr) -> Vec2:
    """
    Get terminal size in characters and multiply by V_STEP and H_STEP
    """
    rows, cols = stdscr.getmaxyx()
    return Vec2((cols - 1) * H_STEP, rows * V_STEP)


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


class Game:
    def __init__(self, window, config) -> None:       
        self.window = window
        self.clock = Clock()
        self.debug = config['debug']

        # Set up sounds
        self.sound_manager = SoundManager(config['sounds'])

        # Set up canvas
        canvas_config = config['canvas']
        if canvas_config['size'] == 'auto':
            canvas_config['size'] = list(terminal_size(window))
        self.canvas = Canvas(window, canvas_config)
        
        # Set up in-game objects
        object_config = config['objects']
        self.object_manager = ObjectManager(object_config)
        self.bullet_factory = BulletFactory(object_config['bullet'])
        
        # Set up collision physics
        self.collision_manager = CollisionManager(self.object_manager, [
            (Bullet.kind, Block.kind),
            (Bullet.kind, Enemy.kind)
        ])

        self.is_running = True

    def process_input(self, key: int) -> None:
        self.object_manager.process_input(key)
        if key == ord('q'):
            self.is_running = False
        elif key == ord(' '):
            # TODO: refactor it as player's method (how to pass sound manager?)
            bullet = self.bullet_factory.create(self.object_manager.player.bullet_spawn_pos())
            self.object_manager.add_object(bullet)
            self.sound_manager.play('shoot')

    def run(self):
        self.clock.start()
        while self.is_running:
            delta = self.clock.getElapsed()
            self.update(delta)
            self.process_input(self.window.getch())
            
            if self.debug:
                debug_str = 'FPS: {:.2f}'.format(1 / delta)
                self.window.addstr(0, 0, debug_str)
                self.window.refresh()

    def update(self, delta: float) -> None:
        self.canvas.clear()
        self.object_manager.update(self.canvas, delta)
        collisions = list(self.collision_manager.update())
        self.object_manager.resolve(collisions)
        self.canvas.update()