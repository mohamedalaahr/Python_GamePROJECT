
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
    enable_skin: bool = True
    # نوع السبرايت (player | commando)
    sprite_prefix: str = "player"
    
    # 🔥 === قدرات خاصة للجندي (Commando) ===
    # قدرة الاندفاع (Dash)
    dash_cooldown: float = 0.0
    dash_max_cooldown: float = 2.5  # 2.5 ثواني بين كل اندفاع (أسرع من قبل)
    is_dashing: bool = False
    dash_timer: float = 0.0
    dash_duration: float = 0.5  # مدة الاندفاع (0.5 ثانية = واضح جداً!)
    dash_speed_mult: float = 8.0  # مضاعف السرعة أثناء الاندفاع (8x = سريع جداً!)
    dash_direction: Tuple[float, float] = (0, 0)
    
    # قدرة الدرع المؤقت (Shield)
    shield_active: bool = False
    shield_timer: float = 0.0
    shield_duration: float = 2.0  # مدة الدرع
    shield_cooldown: float = 0.0
    shield_max_cooldown: float = 10.0  # 10 ثواني بين كل درع

    def _prepare_sprite(self, surf: pygame.Surface, target_h: int = 56) -> pygame.Surface:
        """قص الحواف الشفافة ثم تحجيم السبرايت لارتفاع ثابت لضمان وضوح ومحاذاة سليمة."""
        try:
            rect = surf.get_bounding_rect(min_alpha=10)
            if rect.width > 0 and rect.height > 0:
                surf = surf.subsurface(rect).copy()
        except Exception:
            pass
        w, h = surf.get_size()
        if h > 0 and h != target_h:
            scale_w = int(w * (target_h / h))
            surf = pygame.transform.smoothscale(surf, (scale_w, target_h))
        return surf

    def _load_image_candidates(self, names):
        """يحاول تحميل أول صورة متاحة من قائمة أسماء (مع أو بدون .png)."""
        for name in names:
            if not name:
                continue
            file_name = name if name.lower().endswith('.png') else f"{name}.png"
            img = load_image(file_name)
            if img:
                return self._prepare_sprite(img, self._target_height())
        return None

    def _load_commando_direction(self, direction: str) -> Optional[pygame.Surface]:
        """تحميل صور مخصصة لاتجاهات commando من الملفات التي وضعتها في images/."""
        if direction == "right":
            return self._load_image_candidates([
                "pngtree-hero-game-character-png-image_15305059_Copie_right",
                "pngtree-hero-game-character-png-image_15305059_right",
                "pngtree-hero-game-character-png-image_15305059",
                "commando_right",
            ])
        if direction == "left":
            # محاولة تحميل صورة اليسار أولاً، وإلا سيتم قلب اليمين لاحقاً
            return self._load_image_candidates([
                "pngtree-hero-game-character-png-image_15305059_left",
                "commando_left",
            ])
        if direction == "up":
            return self._load_image_candidates([
                "pngtree-hero-game-character-png-image_15305059_up",
                "commando_up",
            ])
        if direction == "down":
            return self._load_image_candidates([
                "pngtree-hero-game-character-png-image_15305059_down",
                "commando_down",
            ])
        return None

    def _target_height(self) -> int:
        return 72 if self.sprite_prefix == "commando" else 56

    def __post_init__(self):
        # محاولة تحميل الصور حسب البادئة (player_up/down/left/right)
        for d in ("up", "down", "left", "right"):
            img = load_image(f"{self.sprite_prefix}_{d}.png")
            if img:
                self.sprites[d] = self._prepare_sprite(img, self._target_height())

        # 🔥 تحميل ملفات commando المخصصة لجميع الاتجاهات
        if self.sprite_prefix == "commando":
            for d in ("right", "left", "up", "down"):
                if not self.sprites.get(d):
                    img = self._load_commando_direction(d)
                    if img:
                        self.sprites[d] = img

        # دعم خاص لشخصية commando باستخدام اسم ملف احتياطي إذا لم تتوفر right
        if self.sprite_prefix == "commando" and not self.sprites.get("right"):
            fallback_name = "pngtree-hero-game-character-png-image_15305059.png"
            img = load_image(fallback_name)
            if img:
                self.sprites["right"] = self._prepare_sprite(img, self._target_height())
        
        # 🔥 توليد left من right إن لزم (مهم جداً للـ commando)
        if self.sprites.get("right") and not self.sprites.get("left"):
            self.sprites["left"] = pygame.transform.flip(self.sprites["right"], True, False)
        
        # 🔥 استخدام right/left كخلفية لـ up/down إن لم تتوفر
        if self.sprites.get("right"):
            if not self.sprites.get("up"):
                self.sprites["up"] = self.sprites["right"]
            if not self.sprites.get("down"):
                self.sprites["down"] = self.sprites["right"]
        
        # 🔥 تطبيق اللون على الصور
        self._apply_skin_tint()
        
        # إذا كان خيار عدم المظهر مفعلاً، عطّل التأثيرات فوراً
        if not self.enable_skin:
            self.tinted_sprites = {}
        
        # 🔥 طباعة تشخيصية للتأكد من تحميل الصور
        loaded_dirs = [d for d in ("up", "down", "left", "right") if self.sprites.get(d)]
        print(f"[CHAR] {self.sprite_prefix}: Loaded sprites for directions: {loaded_dirs}")

    def _apply_skin_tint(self):
        """تطبيق لون المظهر على صور الشخصية - طريقة سريعة وواضحة"""
        for direction, sprite in self.sprites.items():
            if sprite:
                # إنشاء نسخة من الصورة
                tinted = sprite.copy().convert_alpha()
                w, h = tinted.get_size()
                
                # إنشاء طبقة لونية
                overlay = pygame.Surface((w, h), pygame.SRCALPHA)
                # إذا كان خيار عدم المظهر مفعلاً، لا تضف أي تلوين
                if not self.enable_skin:
                    self.tinted_sprites[direction] = sprite
                    continue
                tint_alpha = 0 if self.sprite_prefix == "commando" else 120
                overlay.fill((*self.skin_color, tint_alpha))  # لون مع شفافية
                
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
        # تجاوز خيار use_skin إن كان اللاعب بدون مظهر
        if not self.enable_skin:
            use_skin = False
        """رسم الشخصية - مع أو بدون المظهر"""
        # 🔥 رسم حلقة ملونة تحت الشخصية (مؤشر المظهر) - مع إيقافها لشخصية commando
        effective_use_skin = use_skin and (self.sprite_prefix != "commando")
        if effective_use_skin:
            center_x = int(self.x + self.w // 2)
            center_y = int(self.y + self.h + 2)  # تحت الشخصية
            # رسم ظل
            pygame.draw.ellipse(screen, (0, 0, 0, 100), 
                              (center_x - 18, center_y - 4, 36, 8))
            # رسم الحلقة الملونة
            pygame.draw.ellipse(screen, self.skin_color, 
                              (center_x - 16, center_y - 3, 32, 6))
        
        if effective_use_skin and self.tinted_sprites.get(self.facing):
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
        
        # 🔥 رسم تأثيرات خاصة للجندي (Commando)
        if self.sprite_prefix == "commando":
            self._draw_commando_effects(screen)
    
    def _draw_commando_effects(self, screen: pygame.Surface):
        """رسم التأثيرات الخاصة بالجندي"""
        # رسم الدرع إذا كان نشطاً
        if self.shield_active:
            center_x = int(self.x + self.w // 2)
            center_y = int(self.y + self.h // 2)
            shield_radius = max(self.w, self.h) // 2 + 10
            
            # تأثير نبض الدرع
            pulse = 0.8 + 0.2 * math.sin(self.shield_timer * 10)
            alpha = int(100 * pulse)
            
            # رسم الدرع (دائرة شفافة زرقاء)
            shield_surf = pygame.Surface((shield_radius * 2 + 10, shield_radius * 2 + 10), pygame.SRCALPHA)
            pygame.draw.circle(shield_surf, (50, 150, 255, alpha),
                             (shield_radius + 5, shield_radius + 5), int(shield_radius * pulse))
            pygame.draw.circle(shield_surf, (100, 200, 255, alpha + 50),
                             (shield_radius + 5, shield_radius + 5), int(shield_radius * pulse), 3)
            screen.blit(shield_surf, (center_x - shield_radius - 5, center_y - shield_radius - 5))
        
        # رسم تأثير الاندفاع
        if self.is_dashing:
            # خط سريع خلف الشخصية
            trail_length = 30
            dx, dy = self.dash_direction
            for i in range(5):
                alpha = int(150 * (1 - i / 5))
                trail_x = int(self.x + self.w // 2 - dx * trail_length * (i + 1) / 5)
                trail_y = int(self.y + self.h // 2 - dy * trail_length * (i + 1) / 5)
                trail_surf = pygame.Surface((10, 10), pygame.SRCALPHA)
                pygame.draw.circle(trail_surf, (255, 200, 50, alpha), (5, 5), 5 - i)
                screen.blit(trail_surf, (trail_x - 5, trail_y - 5))
    
    def update_abilities(self, dt: float):
        """تحديث قدرات الجندي الخاصة"""
        if self.sprite_prefix != "commando":
            return
        
        # تحديث cooldowns
        if self.dash_cooldown > 0:
            self.dash_cooldown -= dt
        if self.shield_cooldown > 0:
            self.shield_cooldown -= dt
        
        # تحديث الاندفاع
        if self.is_dashing:
            self.dash_timer -= dt
            if self.dash_timer <= 0:
                self.is_dashing = False
                self.speed = self.speed / self.dash_speed_mult  # إعادة السرعة الطبيعية
        
        # تحديث الدرع
        if self.shield_active:
            self.shield_timer += dt
            if self.shield_timer >= self.shield_duration:
                self.shield_active = False
                self.shield_timer = 0.0
    
    def activate_dash(self, dx: float, dy: float) -> bool:
        """تفعيل قدرة الاندفاع (للجندي فقط)"""
        if self.sprite_prefix != "commando":
            return False
        if self.dash_cooldown > 0 or self.is_dashing:
            return False
        
        # تحديد اتجاه الاندفاع
        length = math.sqrt(dx * dx + dy * dy)
        if length == 0:
            # استخدام اتجاه النظر
            dir_map = {"right": (1, 0), "left": (-1, 0), "up": (0, -1), "down": (0, 1)}
            dx, dy = dir_map.get(self.facing, (1, 0))
        else:
            dx, dy = dx / length, dy / length
        
        self.dash_direction = (dx, dy)
        self.is_dashing = True
        self.dash_timer = self.dash_duration
        self.dash_cooldown = self.dash_max_cooldown
        self.speed = self.speed * self.dash_speed_mult
        
        print(f"[COMMANDO] Dash activated! Direction: ({dx:.2f}, {dy:.2f})")
        return True
    
    def activate_shield(self) -> bool:
        """تفعيل قدرة الدرع (للجندي فقط)"""
        if self.sprite_prefix != "commando":
            return False
        if self.shield_cooldown > 0 or self.shield_active:
            return False
        
        self.shield_active = True
        self.shield_timer = 0.0
        self.shield_cooldown = self.shield_max_cooldown
        
        print(f"[COMMANDO] Shield activated!")
        return True
    
    def is_shielded(self) -> bool:
        """التحقق إذا كان الدرع نشطاً"""
        return self.shield_active and self.sprite_prefix == "commando"
    
    def get_ability_status(self) -> dict:
        """الحصول على حالة القدرات للعرض في HUD"""
        if self.sprite_prefix != "commando":
            return {}
        
        return {
            "dash_ready": self.dash_cooldown <= 0 and not self.is_dashing,
            "dash_cooldown": max(0, self.dash_cooldown),
            "shield_ready": self.shield_cooldown <= 0 and not self.shield_active,
            "shield_cooldown": max(0, self.shield_cooldown),
            "shield_active": self.shield_active,
            "is_dashing": self.is_dashing
        }

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
