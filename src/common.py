from collections import namedtuple

Vec2 = namedtuple('Vec2', ['x', 'y'])

def dist2(p1: Vec2, p2: Vec2) -> float:
    return (p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2