# TODO: introduce better object naming system for logging
# e.g. <Sound object at 0x7fa535d23870> -> Sound X

import logging
import time

from numpy import exp
from typing import List

from .braillify import H_STEP, V_STEP
from .common import Vec2
from .events import AnimationEndedEvent, CollisionEvent, Event, CollisionTypes, PlayerShootEvent
from .graphics import Canvas, Camera
from .objects import Bullet, Enemy, ExplosionFactory, Player, \
                     ObjectManager, BulletFactory, Block, Explosion
from .physics import CollisionManager
from .sounds import SoundManager
from .textures import TextureManager


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

    def get_elapsed(self) -> float:
        now = time.time()
        elapsed = now - self.time
        self.time = now
        return elapsed


class Profiler:
    PROFILE_CAPTION = ['clear_canvas', 'update_objects', 'check_collisions', 
                       'resolve_events', 'update_camera', 'update_canvas']

    def __init__(self) -> None:
        self.clock = Clock()
        self.profile_times = []

    def start(self):
        self.clock.start()

    def tick(self):
        self.profile_times.append(self.clock.get_elapsed())

    def dump(self):
        result = ', '.join([f'{c}={dt:.5f}s' 
                            for c, dt in zip(self.PROFILE_CAPTION, self.profile_times)])
        self.profile_times = []
        return result
    

class Game:
    def __init__(self, window, config) -> None:       
        self.window = window
        self.clock = Clock()
        self.debug = config['debug']

        if self.debug:
            self.profiler = Profiler()

        # Set up sounds
        SoundManager.init(config['sounds'])

        # Load textures
        TextureManager.init(config['textures'])

        # Set up canvas
        canvas_config = config['canvas']
        size = list(terminal_size(window))
        canvas_config['size'][1] = size[1]
        canvas_config['window_size'] = size
        self.canvas = Canvas(window, canvas_config)

        # Set up camera
        camera_mode = config['camera']['mode']
        if camera_mode != 'follow':
            raise ValueError("Unsupported camera mode")
        camera_speed = config['objects']['player']['speed']
        self.camera = Camera(x=0, mode=camera_mode, speed=camera_speed)
        
        # Set up in-game objects
        object_config = config['objects']
        self.object_manager = ObjectManager()
        self.bullet_factory = BulletFactory(object_config['bullet'])
        self.explosion_factory = ExplosionFactory(object_config['explosion'])
        self.object_manager.add_object(Player(**object_config['player'], 
                                              ymax=self.canvas.height))
        for block in object_config['block']:
            self.object_manager.add_object(Block(block))
        for enemy in object_config['enemy']:
            self.object_manager.add_object(Enemy(enemy))

        # Set up collision physics
        self.collision_manager = CollisionManager(self.object_manager, [
            (Bullet.kind, Block.kind),
            (Bullet.kind, Enemy.kind)
        ])

        self.is_running = True

    def process_input(self, key: int) -> List[Event]:
        events = self.object_manager.process_input(key)
        if key == ord('q'):
            self.is_running = False
        return events

    def run(self):
        self.clock.start()
        if self.debug:
            self.profiler.start()
        while self.is_running:
            delta = self.clock.get_elapsed(reset=True)
            input_events = self.process_input(self.window.getch())
            self.update(delta, input_events)
            
            if self.debug:
                debug_str = 'FPS: {:.2f}'.format(1 / delta)
                self.window.addstr(0, 0, debug_str)
                self.window.refresh()

    def update(self, delta: float, input_events: List[Event]) -> None:
        self.canvas.clear()
        
        if self.debug:
            self.profiler.tick()
        
        events = self.object_manager.update(self.canvas, delta)
        
        if self.debug:
            self.profiler.tick()

        collisions = list(self.collision_manager.update())
        
        if self.debug:
            self.profiler.tick()

        self.resolve(input_events + events + collisions)
        
        if self.debug:
            self.profiler.tick()

        self.camera.update(delta)

        if self.debug:
            self.profiler.tick()

        self.canvas.update(self.camera)

        if self.debug:
            self.profiler.tick()
            logger.info(self.profiler.dump())

    def resolve(self, events: List[Event]):
        for e in events:
            logger.info(f'Resolving event {e}')
            if isinstance(e, CollisionEvent):
                self.resolve_collision(e)
            elif isinstance(e, AnimationEndedEvent):
                self.resolve_animation_end(e)
            elif isinstance(e, PlayerShootEvent):
                self.resolve_player_shoot(e)
            else:
                raise TypeError("Unsupported event type in resolve")
    
    def resolve_animation_end(self, e: AnimationEndedEvent):
        obj = e.sender
        logger.info(f'Resolving animation end event from {type(obj)}')
        if isinstance(obj, Explosion):
            self.object_manager.remove_object(obj)
        else:
            raise TypeError("Unexpected object type in resolve_animation_end")

    def resolve_collision(self, c: CollisionEvent):
        obj1, obj2 = c.collider, c.collided
        typ = (obj1.kind, obj2.kind)

        # Spawn an explosion at the center of the first object
        # TODO: does not look so good when spiders are hit
        explosion = self.explosion_factory.create(Vec2(obj1.xc, obj1.yc))
        self.object_manager.add_object(explosion)

        if typ == CollisionTypes.BULLET_BLOCK.value:
            # when bullet hits block, remove bullet
            self.object_manager.remove_object(obj1)
            SoundManager.play('block_hit')
        elif typ == CollisionTypes.BULLET_ENEMY.value:
            # when bullet hits enemy, remove both enemy and bullet
            self.object_manager.remove_object(obj1)
            self.object_manager.remove_object(obj2)
            SoundManager.play('spider_hit')
        else:
            raise ValueError(f"bad collision type: {typ}")

    def resolve_player_shoot(self, e):
        bullet = self.bullet_factory.create(e.sender.bullet_spawn_pos())
        self.object_manager.add_object(bullet)
        SoundManager.play('shoot')
