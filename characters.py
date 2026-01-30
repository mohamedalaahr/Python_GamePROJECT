
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
    facing: str = "right"
    sprites: Dict[str, Optional[pygame.Surface]] = field(default_factory=dict)
    # 🔥 إضافة دعم المظاهر (Skins)
    skin_color: Tuple[int, int, int] = (100, 150, 200)  # اللون الافتراضي (أزرق)
    tinted_sprites: Dict[str, Optional[pygame.Surface]] = field(default_factory=dict)

    def __post_init__(self):
        for d in ("up", "down", "left", "right"):
            img = load_image_to_height(f"player_{d}.png", 56)
            if img:
                self.sprites[d] = img
        # 🔥 تطبيق اللون على الصور
        self._apply_skin_tint()

    def _apply_skin_tint(self):
        """تطبيق لون المظهر على صور الشخصية - طريقة سريعة وواضحة"""
        for direction, sprite in self.sprites.items():
            if sprite:
                # إنشاء نسخة من الصورة
                tinted = sprite.copy().convert_alpha()
                w, h = tinted.get_size()
                
                # إنشاء طبقة لونية
                overlay = pygame.Surface((w, h), pygame.SRCALPHA)
                overlay.fill((*self.skin_color, 120))  # لون مع شفافية
                
                # دمج الطبقة مع الصورة (ADD للتفتيح)
                tinted.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                
                self.tinted_sprites[direction] = tinted
            else:
                self.tinted_sprites[direction] = None

    def set_skin(self, color: Tuple[int, int, int]):
        """تغيير لون المظهر"""
        self.skin_color = color
        self._apply_skin_tint()

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def move_try(self, dx: int, dy: int, walls, W, H):
        r = self.rect
        rx = pygame.Rect(r.x + dx * self.speed, r.y, r.w, r.h)
        if not any(rx.colliderect(w) for w in walls):
            self.x = clamp(rx.x, 0, W - self.w)
        ry = pygame.Rect(int(self.x), r.y + dy * self.speed, r.w, r.h)
        if not any(ry.colliderect(w) for w in walls):
            self.y = clamp(ry.y, 0, H - self.h)

        if dx or dy:
            if abs(dx) > abs(dy):
                self.facing = "right" if dx > 0 else "left"
            elif dy != 0:
                self.facing = "down" if dy > 0 else "up"

    def draw(self, screen: pygame.Surface, use_skin: bool = True):
        """رسم الشخصية - مع أو بدون المظهر"""
        # 🔥 رسم حلقة ملونة تحت الشخصية (مؤشر المظهر)
        if use_skin:
            center_x = int(self.x + self.w // 2)
            center_y = int(self.y + self.h + 2)  # تحت الشخصية
            # رسم ظل
            pygame.draw.ellipse(screen, (0, 0, 0, 100), 
                              (center_x - 18, center_y - 4, 36, 8))
            # رسم الحلقة الملونة
            pygame.draw.ellipse(screen, self.skin_color, 
                              (center_x - 16, center_y - 3, 32, 6))
        
        if use_skin and self.tinted_sprites.get(self.facing):
            spr = self.tinted_sprites.get(self.facing)
        else:
            spr = self.sprites.get(self.facing)
        
        if spr:
            self.w, self.h = spr.get_width(), spr.get_height()
            screen.blit(spr, self.rect.topleft)
        else:
            # 🔥 رسم مربع بلون المظهر إذا لم توجد صورة
            pygame.draw.rect(screen, self.skin_color, self.rect, border_radius=8)
            # إضافة حدود داكنة
            darker = (max(0, self.skin_color[0]-50), 
                     max(0, self.skin_color[1]-50), 
                     max(0, self.skin_color[2]-50))
            pygame.draw.rect(screen, darker, self.rect, width=3, border_radius=8)
            # رسم عيون صغيرة
            eye_y = int(self.y + self.h * 0.35)
            pygame.draw.circle(screen, (255, 255, 255), (int(self.x + self.w * 0.35), eye_y), 4)
            pygame.draw.circle(screen, (255, 255, 255), (int(self.x + self.w * 0.65), eye_y), 4)
            pygame.draw.circle(screen, (0, 0, 0), (int(self.x + self.w * 0.35), eye_y), 2)
            pygame.draw.circle(screen, (0, 0, 0), (int(self.x + self.w * 0.65), eye_y), 2)

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
        tx, ty = target    
        dx = tx - self.x   
        dy = ty - self.y    
        L = math.hypot(dx, dy) or 1.0 
        ux, uy = dx / L, dy / L
        step = self.speed * dt * 60  

        self._move_axis(ux * step, 0, walls)
        self._move_axis(0, uy * step, walls)

    def draw(self, screen: pygame.Surface):
        if self.sprite:
            screen.blit(self.sprite, (int(self.x), int(self.y)))
        else:
            cx = int(self.x + self.w // 2)
            cy = int(self.y + self.h // 2)
            r = min(self.w, self.h) // 2
            pygame.draw.circle(screen, (240, 80, 80), (cx, cy), r)
