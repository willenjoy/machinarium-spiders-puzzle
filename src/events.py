from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

@dataclass
class Event:
    pass


@dataclass
class AnimationEndedEvent(Event):
    sender: 'AnimatedSprite'
    
    
@dataclass
class CollisionEvent:
    collider: 'Object'
    collided: 'Object'


class CollisionTypes(Enum):
    BULLET_BLOCK = ('Bullet', 'Block') 
    BULLET_ENEMY = ('Bullet', 'Enemy')