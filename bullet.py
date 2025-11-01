"""
Bullets: رسم/تحديث/تصادم مستطيل بسيط.
"""
from dataclasses import dataclass
import math
import pygame

@dataclass
class Bullet:
    x: float
    y: float
    vx: float
    vy: float
    speed: float = 420.0
    lifetime: float = 1.2
    alive: bool = True
    radius: int = 4
    damage: int = 1

    def update(self, dt: float):
        if not self.alive:
            return
        self.x += self.vx * self.speed * dt
        self.y += self.vy * self.speed * dt
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False

    def rect(self) -> pygame.Rect:
        r = self.radius
        return pygame.Rect(int(self.x - r), int(self.y - r), 2*r, 2*r)

    def draw(self, screen: pygame.Surface):
        if not self.alive:
            return
        pygame.draw.circle(screen, (250, 230, 60), (int(self.x), int(self.y)), self.radius)

def normalized(dx, dy):
    L = math.hypot(dx, dy) or 1.0
    return dx / L, dy / L
