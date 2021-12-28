import time

from .braillify import H_STEP, V_STEP
from .common import Vec2
from .graphics import Canvas
from .objects import Player, BulletFactory
from .sounds import SoundManager


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

        # Set up sounds
        self.sound_manager = SoundManager(config['sounds'])

        # Set up canvas
        canvas_config = config['canvas']
        if canvas_config['size'] == 'auto':
            canvas_config['size'] = list(terminal_size(window))
        self.canvas = Canvas(window, canvas_config)
        
        # Set up in-game objects
        object_config = config['objects']
        self.player = Player(object_config['player'])
        self.bullet_factory = BulletFactory(object_config['bullet'])
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
            bullet = self.bullet_factory.create(self.player.bullet_spawn_pos())
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