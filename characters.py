"""
Player/Enemy بكلاسات نظيفة.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import math
import pygame
from util import load_image, load_image_to_height, COLORS, clamp

@dataclass
class Player:
    x: float
    y: float
    speed: float = 5.0
    w: int = 36
    h: int = 36
    facing: str = "down"
    sprites: Dict[str, Optional[pygame.Surface]] = field(default_factory=dict)

    def __post_init__(self):
        # نحمّل sprites إن وُجدت (نضبط ارتفاع موحّد)
        for d in ("up", "down", "left", "right"):
            img = load_image_to_height(f"player_{d}.png", 56)
            if img:
                self.sprites[d] = img

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def move_try(self, dx: int, dy: int, walls, W, H):
        # محاكاة خطوة X
        r = self.rect
        rx = pygame.Rect(r.x + dx * self.speed, r.y, r.w, r.h)
        if not any(rx.colliderect(w) for w in walls):
            self.x = clamp(rx.x, 0, W - self.w)
        # محاكاة خطوة Y
        ry = pygame.Rect(int(self.x), r.y + dy * self.speed, r.w, r.h)
        if not any(ry.colliderect(w) for w in walls):
            self.y = clamp(ry.y, 0, H - self.h)

        # تحديث اتجاه الوجه
        if dx or dy:
            if abs(dx) > abs(dy):
                self.facing = "right" if dx > 0 else "left"
            elif dy != 0:
                self.facing = "down" if dy > 0 else "up"

    def draw(self, screen: pygame.Surface):
        spr = self.sprites.get(self.facing)
        if spr:
            # ضبط أبعاد w/h حسب الصورة مرة واحدة
            self.w, self.h = spr.get_width(), spr.get_height()
            screen.blit(spr, self.rect.topleft)
        else:
            pygame.draw.rect(screen, COLORS["white"], self.rect, border_radius=4)

@dataclass
class Enemy:
    x: float
    y: float
    speed: float = 1.2
    sprite: Optional[pygame.Surface] = None
    w: int = 44
    h: int = 44

    def __post_init__(self):
        if self.sprite is None:
            for name in ("zombie_right.png", "zombie_left.png", "zombie_up.png", "zombie_down.png"):
                img = load_image_to_height(name, 78)
                if img:
                    self.sprite = img
                    self.w, self.h = img.get_width(), img.get_height()
                    break

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def _move_axis(self, dx, dy, walls):
        # تحريك ومحاولة تصادم على محور-محور
        r = self.rect
        if dx != 0:
            rx = pygame.Rect(r.x + dx, r.y, r.w, r.h)
            if not any(rx.colliderect(w) for w in walls):
                self.x += dx
        if dy != 0:
            ry = pygame.Rect(int(self.x), r.y + dy, r.w, r.h)
            if not any(ry.colliderect(w) for w in walls):
                self.y += dy

    def update_seek(self, target: Tuple[float, float], walls, dt: float):
        # اتّجاه نحو اللاعب
        tx, ty = target
        dx = tx - self.x
        dy = ty - self.y
        L = math.hypot(dx, dy) or 1.0
        ux, uy = dx / L, dy / L
        step = self.speed * dt * 60  # تعديل بسيط لتناسب حركة اللاعب (speed بوحدة/فريم تقريبًا)

        self._move_axis(ux * step, 0, walls)
        self._move_axis(0, uy * step, walls)

    def draw(self, screen: pygame.Surface):
        if self.sprite:
            screen.blit(self.sprite, (int(self.x), int(self.y)))
        else:
            # بديل: دائرة حمراء داخل الصندوق
            cx = int(self.x + self.w // 2)
            cy = int(self.y + self.h // 2)
            r = min(self.w, self.h) // 2
            pygame.draw.circle(screen, (240, 80, 80), (cx, cy), r)
