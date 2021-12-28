from collections import defaultdict
from typing import Dict

from .common import Vec2
from .graphics import Canvas, Sprite, Drawable


class ObjectManager:
    def __init__(self, config: Dict) -> None:
        self.objects = defaultdict(list)
        self.update_params = {}

        self.add_object('player', Player(config['player']))
        self.add_object('block', Block(config['block']))

    @property
    def player(self):
        return self.objects['player'][0]

    @property
    def kinds(self):
        return self.objects.keys()

    def traverse(self):
        for objects in self.objects.values():
            for object in objects:
                yield object

    def add_object(self, kind, object):
        if kind == 'player':
            assert len(self.objects[kind]) == 0, "Player must be unique"
        self.objects[kind].append(object)

    def process_input(self, key: int):
        for object in self.traverse():
            if hasattr(object, 'process_input'):
                object.process_input(key)

    def update(self, canvas: Canvas, delta: float):
        for object in self.traverse():
            object.update(canvas, delta)


class Bullet(Drawable):
    def __init__(self, x: int, y: int, speed: int, size: int) -> None:
        super().__init__(x, y)
        self.speed = speed

        self.sprite = Sprite.from_circle(size)

    def update(self, canvas: Canvas, delta: float) -> None:
        self.xc += round(self.speed * delta)
        self.draw(canvas)


class BulletFactory:
    def __init__(self, config: Dict):
        self.config = config
        self.bullet_size = config['size']

    def create(self, pos: Vec2):
        return Bullet(pos.x - self.bullet_size // 2, pos.y, **self.config)


class Player(Drawable):
    def __init__(self, config: Dict) -> None:
        x, y = config['start_pos']
        super().__init__(x, y)
        self.sprite = Sprite.from_png(config['sprite'])

    def process_input(self, key: int) -> None:
        if key == ord('w'):
            self.yc -= 1
        elif key == ord('s'):
            self.yc += 1

    def update(self, canvas: Canvas, delta: float) -> None:
        self.draw(canvas)

    def bullet_spawn_pos(self) -> Vec2:
        return Vec2(self.x + self.sprite.width, self.yc)


class Block(Drawable):
    def __init__(self, config: Dict) -> None:
        x, y = config['start_pos']
        super().__init__(x, y)
        self.sprite = Sprite.from_png(config['sprite'])

    def update(self, canvas: Canvas, delta: float) -> None:
        self.draw(canvas)