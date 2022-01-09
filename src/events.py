from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .common import Vec2


@dataclass
class Event:
    pass


@dataclass
class AnimationEndedEvent(Event):
    sender: 'AnimatedSprite'
    
    
@dataclass
class PlayerShootEvent(Event):
    sender: 'Player'


@dataclass
class CollisionEvent:
    collider: 'Object'
    collided: 'Object'
    pos: Vec2


class CollisionTypes(Enum):
    BULLET_BLOCK = ('Bullet', 'Block') 
    BULLET_ENEMY = ('Bullet', 'Enemy')