from __future__ import annotations

import logging
import numpy as np

from collections import defaultdict
from typing import Dict, Optional, List

from .common import Vec2, dist2
from .events import AnimationEndedEvent, Event, PlayerShootEvent
from .graphics import Canvas, Line, LineType, Sprite, AnimatedSprite
from .textures import TextureManager, Texture


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

    @classmethod
    def from_texture(cls, texture: Texture) -> Hitbox:
        hitbox_mask = texture.mask > 0
        if texture.mask.ndim > 2:
            hitbox_mask = texture.mask.sum(axis = 2) > 0
        logger.info(f'Hitbox mask shape: {hitbox_mask.shape}')
        return Hitbox(texture.height, texture.width, hitbox_mask)


class Object():
    kind = 'Object'

    def __init__(self, x, y) -> None:
        self.xc = x
        self.yc = y
        self.sprite = Sprite(texture=TextureManager.blank())
        self.hitbox = Hitbox(0, 0)

    @property
    def x(self) -> int:
        return self.xc - self.sprite.width // 2
    
    @property
    def y(self) -> int:
        return self.yc - self.sprite.height // 2

    def draw(self, canvas: Canvas):
        self.sprite.draw(canvas, self.x, self.y)


class Bullet(Object):
    kind = 'Bullet'

    def __init__(self, x: int, y: int, speed: int, size: int, sprite: str) -> None:
        super().__init__(x, y)
        self.speed = speed

        texture = TextureManager.get(sprite)
        self.sprite = Sprite(texture)
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

    def __init__(self, **config) -> None:
        x, y = config['start_pos']
        super().__init__(x, y)
        texture = TextureManager.get(config['sprite'])
        self.speed = config['speed']
        self.sprite = Sprite(texture)
        self.hitbox = Hitbox.from_texture(texture)
        self.ymax = config['ymax'] - self.sprite.height // 2
        self.ymin = self.sprite.height // 2

    def process_input(self, key: int) -> List[Event]:
        events = []
        if key == ord('w') and self.in_bounds(self.yc - 1):
            self.yc -= 1
        elif key == ord('s') and self.in_bounds(self.yc + 1):
            self.yc += 1
        elif key == ord(' '):
            events.append(PlayerShootEvent(sender=self))
        return events

    def in_bounds(self, yc):
        return self.ymin <= yc < self.ymax

    def update(self, canvas: Canvas, delta: float) -> Optional[Event]:
        self.xc += round(self.speed * delta)
        self.draw(canvas)

    def bullet_spawn_pos(self) -> Vec2:
        return Vec2(self.x + self.sprite.width, self.yc)


class Block(Object):
    kind = 'Block'

    def __init__(self, config: Dict) -> None:
        x, y = config['start_pos']
        super().__init__(x, y)
        texture = TextureManager.get(config['sprite'])
        self.sprite = Sprite(texture)
        self.hitbox = Hitbox.from_rectangle(self.sprite.width, self.sprite.height)

    def update(self, canvas: Canvas, delta: float) -> Optional[Event]:
        self.draw(canvas)


class Enemy(Object):
    kind = 'Enemy'
    MAX_LENGTH = 200

    def __init__(self, config: Dict) -> None:
        x, y = config.pop('start_pos')
        super().__init__(x, y)
        name = config.pop('sprite')
        texture = TextureManager.get(name)
        
        self.hangs = config.pop('hangs')
        self.line = None
        if self.hangs:
            self.line = Line(xs=self.xc, ys=0, xe=self.xc, ye=self.yc, 
                             width=1, type=LineType.DASHED, data=np.array([]))
            self.line.generate_data(self.MAX_LENGTH, 1, LineType.DASHED, 1)
        
        self.sprite = AnimatedSprite(texture=texture, **config)
        self.hitbox = Hitbox.from_texture(texture)

    def draw(self, canvas: Canvas):
        super().draw(canvas)
        if self.hangs:
            self.line.draw(canvas)

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

        name = kwargs.pop('sprite')
        texture = TextureManager.get(name)
        self.sprite = AnimatedSprite(texture=texture, **kwargs)

    def update(self, canvas: Canvas, delta: float):
        e = self.sprite.update(delta)
        if not e:
            logger.info('Explosion animation ended')
            return AnimationEndedEvent(sender=self)
        self.draw(canvas)


class Goal(Object):
    kind = 'Goal'

    def __init__(self, config: Dict) -> None:
        x, y = config['start_pos']
        super().__init__(x, y)
        texture = TextureManager.get(config['sprite'])
        self.sprite = Sprite(texture)
        self.hitbox = Hitbox.from_rectangle(self.sprite.width, self.sprite.height)

    def update(self, canvas: Canvas, delta: float) -> Optional[Event]:
        self.draw(canvas)


class ObjectManager:
    def __init__(self) -> None:
        self.objects = defaultdict(list)
        self.remove_queue = []

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

    def process_input(self, key: int) -> List[Event]:
        events = []
        for object in self.traverse():
            if hasattr(object, 'process_input'):
                events.extend(object.process_input(key))
        return events

    def update(self, canvas: Canvas, delta: float):
        events = []
        for object in self.traverse():
            e = object.update(canvas, delta)
            if e:
                events.append(e)
        return events