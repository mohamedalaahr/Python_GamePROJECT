"""
Characters (Player ready, Enemy for later).
Player uses directional sprites from /images if available.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
import pygame
from util import load_image, COLORS


@dataclass
class Player:
    x: float
    y: float
    speed: float = 5.0
    w: int = 36
    h: int = 36
    facing: str = "down"
    sprites: Dict[str, pygame.Surface] = field(default_factory=dict)

    def __post_init__(self):
        for d in ("up", "down", "left", "right"):
            img = load_image(f"player_{d}.png")
            if img:
                self.sprites[d] = img

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def move(self, dx: int, dy: int):
        self.x += dx * self.speed
        self.y += dy * self.speed
        if abs(dx) > abs(dy):
            self.facing = "right" if dx > 0 else "left"
        elif dy != 0:
            self.facing = "down" if dy > 0 else "up"

    def draw(self, screen: pygame.Surface):
        spr = self.sprites.get(self.facing)
        if spr:
            screen.blit(spr, self.rect.topleft)
        else:
            pygame.draw.rect(screen, COLORS["white"], self.rect, border_radius=4)


@dataclass
class Enemy:
    x: float
    y: float
    speed: float = 1.0
    sprite: Optional[pygame.Surface] = None
    radius: int = 18

    def __post_init__(self):
        if self.sprite is None:
            for name in ("zombie_right.png", "zombie_left.png", "zombie_up.png", "zombie_down.png"):
                img = load_image(name)
                if img:
                    self.sprite = img
                    break

    def draw(self, screen: pygame.Surface):
        if self.sprite:
            screen.blit(self.sprite, (int(self.x), int(self.y)))
        else:
            pygame.draw.circle(screen, (240, 80, 80), (int(self.x), int(self.y)), self.radius)
