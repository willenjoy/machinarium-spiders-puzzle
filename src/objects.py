from __future__ import annotations

import logging
import numpy as np

from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Optional

from .common import Vec2, dist2
from .events import AnimationEndedEvent, CollisionEvent, Event
from .graphics import Canvas, Sprite, AnimatedSprite, Drawable
from .sounds import SoundManager


logger = logging.getLogger(__name__)


class Hitbox:
    def __init__(self, width: int, height: int, data: Optional[np.array] = None) -> None:
        self.width = width
        self.height = height
        if data is not None:
            self.data = data
        else:
            self.data = np.zeros((height, width), dtype=np.uint8)

    @classmethod
    def from_circle(cls, diameter: int) -> Hitbox:
        radius = diameter // 2
        center = Vec2(diameter // 2, diameter // 2)
        hitbox = Hitbox(diameter, diameter)
        for row in range(diameter):
            for col in range(diameter):
                if dist2(Vec2(col, row), center) < radius ** 2:
                    hitbox.data[row, col] = 1
        return hitbox

    @classmethod
    def from_rectangle(cls, width: int, height: int) -> Hitbox:
        return Hitbox(width, height, np.ones((width, height), dtype=np.uint8))


class Object(Drawable):
    kind = 'Object'

    def __init(self, x: int, y: int):
        super().__init__(x, y)
        self.hitbox = Hitbox(0, 0)


class Bullet(Object):
    kind = 'Bullet'

    def __init__(self, x: int, y: int, speed: int, size: int) -> None:
        super().__init__(x, y)
        self.speed = speed

        self.sprite = Sprite.from_circle(size)
        self.hitbox = Hitbox.from_circle(size)

    def update(self, canvas: Canvas, delta: float) -> Optional[Event]:
        self.xc += round(self.speed * delta)
        self.draw(canvas)


class BulletFactory:
    def __init__(self, config: Dict):
        self.config = config
        self.bullet_size = config['size']

    def create(self, pos: Vec2):
        return Bullet(pos.x - self.bullet_size // 2, pos.y, **self.config)


class Player(Object):
    kind = 'Player'

    def __init__(self, config: Dict) -> None:
        x, y = config['start_pos']
        super().__init__(x, y)
        self.sprite = Sprite.from_png(config['sprite'])

    # TODO: player should not be able to go out of bounds
    def process_input(self, key: int) -> None:
        if key == ord('w'):
            self.yc -= 1
        elif key == ord('s'):
            self.yc += 1

    def update(self, canvas: Canvas, delta: float) -> Optional[Event]:
        self.draw(canvas)

    def bullet_spawn_pos(self) -> Vec2:
        return Vec2(self.x + self.sprite.width, self.yc)


class Block(Object):
    kind = 'Block'

    def __init__(self, config: Dict) -> None:
        x, y = config['start_pos']
        super().__init__(x, y)
        self.sprite = Sprite.from_png(config['sprite'])
        self.hitbox = Hitbox.from_rectangle(self.sprite.width, self.sprite.height)

    def update(self, canvas: Canvas, delta: float) -> Optional[Event]:
        self.draw(canvas)


class Enemy(Object):
    kind = 'Enemy'

    def __init__(self, config: Dict) -> None:
        x, y = config.pop('start_pos')
        super().__init__(x, y)
        fname = config.pop('sprite')
        self.sprite = AnimatedSprite.from_gif(fname, **config)
        self.hitbox = Hitbox.from_rectangle(self.sprite.width, self.sprite.height)

    def update(self, canvas: Canvas, delta: float) -> Optional[Event]:
        e = self.sprite.update(delta)
        if not e:
            logger.info('Explosion animation ended')
            return AnimationEndedEvent(sender=self)
        self.draw(canvas)


class ExplosionFactory:
    def __init__(self, config: Dict):
        self.config = config

    def create(self, pos: Vec2) -> Explosion:
        return Explosion(pos.x, pos.y, **self.config)


class Explosion(Object):
    kind = 'Explosion'

    def __init__(self, x: int = 0, y: int = 0, **kwargs) -> Optional[Event]:
        super().__init__(x, y)

        fname = kwargs.pop('sprite')
        self.sprite = AnimatedSprite.from_gif(fname, **kwargs)

    def update(self, canvas: Canvas, delta: float):
        e = self.sprite.update(delta)
        if not e:
            logger.info('Explosion animation ended')
            return AnimationEndedEvent(sender=self)
        self.draw(canvas)


class ObjectManager:
    def __init__(self) -> None:
        self.objects = defaultdict(list)
        self.remove_queue = []

    @property
    def player(self):
        assert self.objects[Player.kind], "Player was not added"
        return self.objects[Player.kind][0]

    def traverse(self):
        for objects in self.objects.values():
            for object in objects:
                yield object

    def add_object(self, object):
        kind = object.kind
        if kind == Player.kind:
            assert len(self.objects[kind]) == 0, "Player must be unique"
        self.objects[kind].append(object)
        logger.info(f'Adding object to the game: {kind} - {object}')

    def remove_object(self, object):
        kind = object.kind
        self.objects[kind].remove(object)
        logger.info(f'Removing object from the game: {kind} - {object}')

    def process_input(self, key: int):
        for object in self.traverse():
            if hasattr(object, 'process_input'):
                object.process_input(key)

    def update(self, canvas: Canvas, delta: float):
        events = []
        for object in self.traverse():
            e = object.update(canvas, delta)
            if e:
                events.append(e)
        return events