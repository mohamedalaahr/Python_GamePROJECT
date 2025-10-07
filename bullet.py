"""
Bullets (WIP) — ready for future integration.
"""

from dataclasses import dataclass

@dataclass
class Bullet:
    x: float
    y: float
    vx: float
    vy: float
    speed: float = 420.0
    lifetime: float = 1.5
    alive: bool = True

    def update(self, dt: float):
        if not self.alive:
            return
        self.x += self.vx * self.speed * dt
        self.y += self.vy * self.speed * dt
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False
