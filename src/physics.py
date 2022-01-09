"""
Object kinds and collision consequences:

player -- block -> remove player
player -- enemy -> remove player
bullet -- block -> remove bullet
bullet -- enemy -> remove enemy

no players in game -- game over
"""

from __future__ import annotations

import logging
import numpy as np

from collections import defaultdict
from typing import List, Tuple

from .common import Vec2
from .events import CollisionEvent
from .objects import ObjectManager


logger = logging.getLogger(__name__)


# TODO: check distance between objects to reduce long collision checks
# TODO: check consistency of y vs x axis across the whole codebase
def collide(obj, other):
    top = min(obj.y, other.y)
    left = min(obj.x, other.x)
    bottom = max(obj.y + obj.hitbox.height, other.y + other.hitbox.height)
    right = max(obj.x + obj.hitbox.width, other.x + other.hitbox.width)

    width = right - left
    height = bottom - top

    container = np.zeros((width, height))

    def add_to_container(o):
        obj_top = o.y - top
        obj_left = o.x - left
        obj_width = o.hitbox.width
        obj_height = o.hitbox.height
        container[obj_left:obj_left+obj_width, obj_top:obj_top+obj_height] += o.hitbox.data

    add_to_container(obj)
    add_to_container(other)

    if not np.any(container > 1):
        return False, 0

    grid = np.indices((width, height))
    r = np.mean(grid[0][container > 1])
    c = np.mean(grid[1][container > 1])

    return True, Vec2(top + r, left + c)


class CollisionManager:
    def __init__(self, object_manager: ObjectManager, collide_kinds: List[Tuple[str, str]]) -> None:
        self.collide = defaultdict(list)
        self.object_manager = object_manager
        for kind_pair in collide_kinds:
            self.add_collision(*kind_pair)

    def add_collision(self, kind1, kind2):
        self.collide[kind1].append(kind2)
        logger.info(f'Added collision type: {kind1} -- {kind2}')
        logger.info(self.collide)

    def check(self, obj):
        for kind_other in self.collide[obj.kind]:
            for other in self.object_manager.objects[kind_other]:
                collided, pos = collide(obj, other)
                if collided:
                    yield CollisionEvent(collider=obj, collided=other, pos=pos)
                

    def update(self):
        for kind, objects in self.object_manager.objects.items():
            if kind not in self.collide:
                continue

            logger.info(f'Checking collisions for {kind}: {objects}')
            for object in objects:
                yield from self.check(object)
                logger.info(self.object_manager.objects)