from typing import Dict

from .common import Vec2
from .graphics import Canvas, Sprite, Drawable


class Bullet(Drawable):
    def __init__(self, x: int, y: int, speed: int, size: int) -> None:
        super().__init__(x, y)
        self.speed = speed

        self.radius = size // 2
        self.sprite = Sprite(size, size)
        self.sprite.draw_circle(self.radius, self.radius, self.radius)

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
        self.sprite = Sprite()
        self.sprite.from_png(config['sprite'])

    def update(self, canvas: Canvas) -> None:
        self.draw(canvas)

    def bullet_spawn_pos(self) -> Vec2:
        return Vec2(self.x + self.sprite.width, self.yc)