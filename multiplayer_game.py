# multiplayer_game.py - (FINAL-FIXED Version: Co-op Door & Backgrounds + Victory/Spectator/GameOver)
import os
import pygame
import time
import math
import random
from util import Button, clamp, draw_shadow_text, draw_text, load_sound, load_image_to_height
from walls import create_walls_for_level, collide_rect_list

from characters import Player

# 🔥 استيراد الأنظمة الجديدة
from weapons import WeaponManager, WeaponType, WEAPON_STATS, AmmoPickup
from chat import ChatSystem, ChatMessage
from minimap import Minimap
from skins import get_skin_color, DEFAULT_SKIN
FEATURES_ENABLED = True

def get_current_skin():
    """الحصول على المظهر المختار من game.py"""
    try:
        from game import CURRENT_SKIN
        return CURRENT_SKIN
    except ImportError:
        return DEFAULT_SKIN

# ---------------- Window / World ----------------
WINDOW_W, WINDOW_H = 1280, 720
FPS = 60
WORLD_W, WORLD_H = 3200, 2400

# 🔥 --- (جديد) --- نظام الألوان والخلفيات من game.py ---
LEVEL_COLORS = {
    1: (166, 98, 42),   # المستوى 1: رمل صحراوي/بني (اللون الأصلي)
    2: (110, 110, 110), # المستوى 2: خرسانة حضرية/رمادي (Urban Concrete)
    3: (75, 90, 75),    # المستوى 3: غابة/طحلب داكن (Dark Moss)
    4: (40, 40, 90),    # المستوى 4: سماء ليلية/أزرق عميق (Deep Blue Night)
    5: (140, 60, 40),   # المستوى 5: صهارة حمراء/أرض محروقة (Burning Magma)
    6: (30, 30, 30),    # المستوى 6: هاوية/مواجهة نهائية سوداء (Abyss/Final Arena)
}
BG_EFFECTS = {} # (سيحتوي على الخلفيات المرسومة مسبقاً)

# ------------- Music -------------
def _maybe_music():
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        bg = "sounds/background_music.wav"
        if os.path.isfile(bg):
            pygame.mixer.music.load(bg)
            pygame.mixer.music.set_volume(0.30)
            pygame.mixer.music.play(-1)
    except Exception:
        pass

# ---------------- Camera ----------------
class Camera:
    def __init__(self, world_w: int, world_h: int, view_w: int, view_h: int):
        self.world_w, self.world_h = world_w, world_h
        self.view_w, self.view_h = view_w, view_h
        self.x, self.y = 0.0, 0.0
        # (يمكن إضافة متغيرات اهتزاز الشاشة هنا إذا أردت)

    def follow(self, target_rect: pygame.Rect, lerp: float = 0.15):
        tx = target_rect.centerx - self.view_w // 2
        ty = target_rect.centery - self.view_h // 2
        self.x += (tx - self.x) * lerp
        self.y += (ty - self.y) * lerp
        self.x = max(0, min(self.x, self.world_w - self.view_w))
        self.y = max(0, min(self.y, self.world_h - self.view_h))

    def apply_rect(self, r: pygame.Rect) -> pygame.Rect:
        return r.move(-int(self.x), -int(self.y))

    def apply_xy(self, x: float, y: float) -> tuple[int, int]:
        return int(x - self.x), int(y - self.y)

# ---------------- Speed Crate ----------------
CRATE_H = 52
class SpeedCrate:
    def __init__(self, x: float, y: float, crate_id: int = 0):
        self.id = crate_id
        self.x, self.y = float(x), float(y)
        self.img_closed = load_image_to_height("chest_closed.png", CRATE_H)
        self.img_opened = load_image_to_height("chest_opened.png", CRATE_H)
        if self.img_closed:
            self.w, self.h = self.img_closed.get_width(), self.img_closed.get_height()
        else:
            self.w, self.h = CRATE_H, CRATE_H
        self.alive = True
        self.open = False
        self.open_timer = 0.0
    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)
    def trigger_open(self, show_time: float = 0.35):
        if self.open: return
        self.open = True
        self.open_timer = show_time
    def update(self, dt: float):
        if not self.alive: return
        if self.open:
            self.open_timer -= dt
            if self.open_timer <= 0:
                self.alive = False
    def draw(self, screen: pygame.Surface, cam: Camera):
        if not self.alive: return
        dx, dy = cam.apply_xy(self.x, self.y)
        if self.open and self.img_opened:
            screen.blit(self.img_opened, (dx, dy))
        elif (not self.open) and self.img_closed:
            screen.blit(self.img_closed, (dx, dy))
        else:
            r = pygame.Rect(dx, dy, self.w, self.h)
            pygame.draw.rect(screen, (120, 85, 40), r, border_radius=6)
            pygame.draw.rect(screen, (220, 200, 160), r, width=2, border_radius=6)
    def to_dict(self):
        return { 'id': self.id, 'x': self.x, 'y': self.y, 'alive': self.alive, 'open': self.open }
    @staticmethod
    def from_dict(data):
        crate = SpeedCrate(data['x'], data['y'], data['id'])
        crate.alive = data['alive']
        crate.open = data['open']
        return crate

# 🔥 --- (جديد) --- دوال مساعدة لنظام الملاحة (من game.py) ---
def calculate_door_direction(player_x: float, player_y: float, door_x: float, door_y: float) -> tuple[float, float, float]:
    dx = door_x - player_x
    dy = door_y - player_y
    distance = math.sqrt(dx*dx + dy*dy)
    if distance == 0:
        return 0, 0, (0, 0)
    angle = math.atan2(dy, dx)
    norm_dx = dx / distance
    norm_dy = dy / distance
    return angle, distance, (norm_dx, norm_dy)

def create_navigation_arrow(angle: float, size: int = 40) -> pygame.Surface:
    arrow_surface = pygame.Surface((size, size), pygame.SRCALPHA)
    points = [ (size//2, 0), (0, size), (size, size) ]
    rotated_points = []
    center_x, center_y = size//2, size//2
    for x, y in points:
        x -= center_x
        y -= center_y
        new_x = x * math.cos(angle) - y * math.sin(angle)
        new_y = x * math.sin(angle) + y * math.cos(angle)
        rotated_points.append((new_x + center_x, new_y + center_y))
    pygame.draw.polygon(arrow_surface, (255, 255, 0, 200), rotated_points)
    pygame.draw.polygon(arrow_surface, (255, 200, 0), rotated_points, 2)
    return arrow_surface

def create_distance_indicator(distance: float) -> tuple[str, tuple[int, int, int]]:
    if distance < 300: return "VERY CLOSE", (0, 255, 0)
    elif distance < 600: return "CLOSE", (255, 255, 0)
    elif distance < 1000: return "NEARBY", (255, 165, 0)
    else: return "FAR", (255, 0, 0)

# 🔥 --- (جديد) --- كلاس الباب الاحترافي (من game.py) ---
class LevelDoor:
    """باب محسن للانتقال بين المستويات مع نظام ملاحة"""
    def __init__(self, x: float, y: float, level: int):
        self.x, self.y = float(x), float(y)
        self.level = level
        self.w, self.h = 80, 120
        self.active = False
        self.glow_timer = 0.0
        self.pulse_speed = 2.0
        self.img_closed = load_image_to_height("door_closed.png", self.h)
        self.img_open = load_image_to_height("door_open.png", self.h)
        self.img = self.img_closed # (البداية مغلق)
        
    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)
        
    def activate(self):
        if not self.active:
            self.active = True
            if self.img_open:
                self.img = self.img_open
            
    def update(self, dt: float):
        if self.active:
            self.glow_timer += dt * self.pulse_speed
            
    def draw_navigation(self, screen: pygame.Surface, player_x: float, player_y: float):
        if not self.active:
            return
            
        angle, distance, direction = calculate_door_direction(
            player_x + 18, player_y + 18,
            self.x + self.w/2, self.y + self.h/2
        )
        
        if distance > 200:
            arrow_size = 35
            margin = 60
            screen_center_x, screen_center_y = WINDOW_W // 2, WINDOW_H // 2
            max_dist = min(screen_center_x, screen_center_y) - margin
            arrow_x = screen_center_x + direction[0] * max_dist
            arrow_y = screen_center_y + direction[1] * max_dist
            
            arrow_surface = create_navigation_arrow(angle, arrow_size)
            arrow_rect = arrow_surface.get_rect(center=(arrow_x, arrow_y))
            screen.blit(arrow_surface, arrow_rect)
            
            distance_text, color = create_distance_indicator(distance)
            dist_font = pygame.font.Font(None, 22)
            dist_surface = dist_font.render(f"{distance_text} ({int(distance)}m)", True, color)
            dist_rect = dist_surface.get_rect(center=(arrow_x, arrow_y + arrow_size//2 + 20))
            bg_rect = dist_rect.inflate(10, 5)
            pygame.draw.rect(screen, (0, 0, 0, 180), bg_rect, border_radius=3)
            screen.blit(dist_surface, dist_rect)
        
    def draw(self, screen: pygame.Surface, cam: Camera):
        """رسم باب بسيط وجميل - محسّن للأداء"""
        dx, dy = cam.apply_xy(self.x, self.y)
        center_x = dx + self.w // 2
        center_y = dy + self.h // 2
        
        if self.active:
            # === الباب النشط: بوابة متوهجة بسيطة ===
            pulse = 1.0 + math.sin(self.glow_timer * 3) * 0.1
            ring_radius = int((self.w // 2 + 5) * pulse)
            
            # توهج بسيط (دائرة واحدة فقط)
            glow_surf = pygame.Surface((ring_radius * 3, ring_radius * 3), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (100, 200, 255, 80), (ring_radius * 3 // 2, ring_radius * 3 // 2), ring_radius)
            screen.blit(glow_surf, (center_x - ring_radius * 3 // 2, center_y - ring_radius * 3 // 2))
            
            # المركز (دائرة واحدة متوهجة)
            pygame.draw.circle(screen, (80, 150, 255), (center_x, center_y), ring_radius - 5)
            pygame.draw.circle(screen, (150, 220, 255), (center_x, center_y), ring_radius - 10)
            
            # الحلقة الخارجية
            pygame.draw.circle(screen, (100, 200, 255), (center_x, center_y), ring_radius, 4)
            
            # 4 جزيئات فقط (بدلاً من 8)
            for i in range(4):
                angle = self.glow_timer * 2 + i * (math.pi / 2)
                px = center_x + int(math.cos(angle) * (ring_radius + 8))
                py = center_y + int(math.sin(angle) * (ring_radius + 8))
                pygame.draw.circle(screen, (200, 240, 255), (px, py), 3)
            
            # نص المستوى
            font = pygame.font.Font(None, 26)
            text_surf = font.render(f"LEVEL {self.level + 1}", True, (255, 255, 200))
            text_rect = text_surf.get_rect(center=(center_x, dy - 20))
            pygame.draw.rect(screen, (0, 0, 50), text_rect.inflate(16, 8), border_radius=6)
            screen.blit(text_surf, text_rect)
        else:
            # === الباب المغلق: بسيط وسريع ===
            door_rect = pygame.Rect(dx, dy, self.w, self.h)
            
            # ظل
            pygame.draw.rect(screen, (20, 15, 10), door_rect.move(3, 3), border_radius=6)
            
            # الباب (لون واحد)
            pygame.draw.rect(screen, (70, 50, 35), door_rect, border_radius=6)
            
            # إطار
            pygame.draw.rect(screen, (40, 28, 18), door_rect, 3, border_radius=6)
            
            # لوحتين بسيطتين
            panel1 = pygame.Rect(dx + 6, dy + 6, self.w - 12, self.h // 2 - 9)
            panel2 = pygame.Rect(dx + 6, dy + self.h // 2 + 3, self.w - 12, self.h // 2 - 9)
            pygame.draw.rect(screen, (55, 40, 28), panel1, 2, border_radius=3)
            pygame.draw.rect(screen, (55, 40, 28), panel2, 2, border_radius=3)
            
            # مقبض
            pygame.draw.circle(screen, (90, 70, 45), (dx + self.w - 14, center_y), 5)




    def to_dict(self):
        return {
            'x': self.x,
            'y': self.y,
            'active': self.active,
            'level': self.level
        }

# ---------------- Zombie (OPTIMIZED) ----------------
ZOMBIE_SIZE = 96
def raycast_clear(a: pygame.Vector2, b: pygame.Vector2, walls: list[pygame.Rect], step: float = 32.0) -> bool:
    d = b - a
    dist = d.length() or 1.0
    n = max(1, int(dist / step))
    u = d / dist
    p = a.copy()
    for _ in range(n):
        p += u * step
        test = pygame.Rect(int(p.x) - 2, int(p.y) - 2, 4, 4)
        if collide_rect_list(test, walls):
            return False
    return True
class Zombie:
    def __init__(self, x: float, y: float, level: int = 1, zombie_id: int = 0):
        self.id = zombie_id
        self.level = level
        
        # 🔥 تحسين السرعة - فرق واضح بين المستويات
        # المستوى 1: بطيء (1.2), المستوى 6: سريع جداً (3.0+)
        base_speed = 1.2  # سرعة أساسية أبطأ
        speed_increase_per_level = 0.35  # زيادة ملحوظة لكل مستوى
        self.speed = base_speed + (level * speed_increase_per_level)
        
        # صحة الزومبي تزداد مع المستوى
        self.hp = int(2 + (level * 1.0))  # 3 HP في المستوى 1, 8 HP في المستوى 6
        self.damage = 1 + (level // 3)  # ضرر يزداد كل 3 مستويات
        self.max_hp = self.hp
        
        self.size = ZOMBIE_SIZE
        self.sprite = ( load_image_to_height("zombie_right.png", self.size) or load_image_to_height("zombie_left.png",  self.size) or load_image_to_height("zombie_up.png",    self.size) or load_image_to_height("zombie_down.png",  self.size) )
        if self.sprite: self.w, self.h = self.sprite.get_width(), self.sprite.get_height()
        else: self.w, self.h = int(self.size*0.75), int(self.size*0.75)
        self.x, self.y = float(x), float(y)
        self.bob_t = random.random() * 100.0
        self.waypoint: pygame.Vector2 | None = None
        self.way_timer = 0.0
        self.raycast_timer = 0.0
        self.can_see_player = False
        self.lerp_target_x = float(x)
        self.lerp_target_y = float(y)
    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)
    def _pick_waypoint(self, W: int, H: int, walls: list[pygame.Rect]):
        for _ in range(8):
            tx = random.randint(60, W - 60)
            ty = random.randint(60, H - 60)
            r = pygame.Rect(tx, ty, 6, 6)
            if not collide_rect_list(r, walls):
                self.waypoint = pygame.Vector2(tx, ty)
                self.way_timer = random.uniform(1.5, 3.0)
                return
        self.waypoint = None
        self.way_timer = 0.5
    def _slide_move(self, dx: float, dy: float, walls: list[pygame.Rect]):
        r = self.rect
        if dx != 0:
            rx = pygame.Rect(r.x + int(dx), r.y, r.w, r.h)
            if not collide_rect_list(rx, walls): self.x += dx
        if dy != 0:
            ry = pygame.Rect(int(self.x), r.y + int(dy), r.w, r.h)
            if not collide_rect_list(ry, walls): self.y += dy
    def update_host(self, player_pos: pygame.Vector2, walls: list[pygame.Rect], dt: float, neighbors: list["Zombie"]):
        spd = self.speed * 60.0 * dt
        sep_x = sep_y = 0.0
        for other in neighbors:
            dx = self.x - other.x
            dy = self.y - other.y
            dsq = dx*dx + dy*dy
            if 0 < dsq < 3136:
                inv = 1.0 / math.sqrt(dsq)
                sep_x += dx * inv
                sep_y += dy * inv
        center = pygame.Vector2(self.x + self.w/2, self.y + self.h/2)
        self.raycast_timer -= dt
        if self.raycast_timer <= 0:
            self.raycast_timer = 0.3
            self.can_see_player = raycast_clear(center, player_pos, walls)
        if self.can_see_player:
            target = player_pos
            self.waypoint = None
            self.way_timer = 0.0
        else:
            if (self.waypoint is None) or (self.way_timer <= 0):
                self._pick_waypoint(WORLD_W, WORLD_H, walls)
            target = self.waypoint if self.waypoint is not None else player_pos
            self.way_timer = max(0.0, self.way_timer - dt)
        dir_x = dir_y = 0.0
        if target is not None:
            dx = target.x - center.x
            dy = target.y - center.y
            L = math.hypot(dx, dy) or 1.0
            dir_x, dir_y = dx / L, dy / L
        dir_x += 0.6 * sep_x
        dir_y += 0.6 * sep_y
        norm = math.hypot(dir_x, dir_y) or 1.0
        dir_x /= norm
        dir_y /= norm
        self._slide_move(dir_x * spd, 0, walls)
        self._slide_move(0, dir_y * spd, walls)
        self.bob_t += dt * 6.0
        self.lerp_target_x = self.x
        self.lerp_target_y = self.y
    def update_client(self, dt: float):
        self.bob_t += dt * 6.0
        self.x += (self.lerp_target_x - self.x) * dt * 10.0
        self.y += (self.lerp_target_y - self.y) * dt * 10.0
    def draw(self, screen: pygame.Surface, cam: Camera):
        dx, dy = cam.apply_xy(self.x, self.y)
        if self.sprite:
            off = math.sin(self.bob_t) * 1.5
            screen.blit(self.sprite, (dx, dy + off))
        else:
            r = pygame.Rect(dx, dy, self.w, self.h)
            pygame.draw.rect(screen, (90, 160, 220), r, border_radius=6)
        
        # 🔥 عرض مستوى الزومبي فوق رأسه
        level_text = f"LVL{self.level}"
        font = pygame.font.Font(None, 18)
        text_surf = font.render(level_text, True, (255, 255, 100))
        text_rect = text_surf.get_rect(center=(dx + self.w//2, dy - 20))
        
        # خلفية شبه شفافة للنص لتحسين الوضوح
        bg_rect = text_rect.inflate(6, 2)
        bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg_surf.fill((0, 0, 0, 160))
        screen.blit(bg_surf, bg_rect.topleft)
        screen.blit(text_surf, text_rect)
        
        # عرض شريط الصحة (إذا كان مصاباً)
        if self.hp < self.max_hp:
            health_ratio = self.hp / self.max_hp
            # رفع شريط الصحة قليلاً لإفساح المجال للنص
            health_y = dy - 35
            pygame.draw.rect(screen, (50, 50, 50), (dx, health_y, self.w, 6))
            pygame.draw.rect(screen, (0, 255, 0), (dx, health_y, self.w * health_ratio, 6))
    def to_dict(self):
        return { 'id': self.id, 'x': self.x, 'y': self.y, 'hp': self.hp, 'level': self.level }
    @staticmethod
    def from_dict(data):
        z = Zombie(data['x'], data['y'], data['level'], data['id'])
        z.hp = data['hp']
        z.lerp_target_x = data['x']
        z.lerp_target_y = data['y']
        return z

# ---------------- Blood FX (OPTIMIZED) ----------------
class BloodParticle:
    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)
        ang = random.uniform(0, 2*math.pi)
        sp  = random.uniform(40, 160)
        self.vx = math.cos(ang) * sp
        self.vy = math.sin(ang) * sp
        self.r  = random.uniform(2.5, 5.0)
        self.life = random.uniform(0.4, 0.8)
        self.age  = 0.0
        self.col  = (170, 20, 20)
    def update(self, dt: float):
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.96
        self.vy *= 0.96
    @property
    def alive(self) -> bool:
        return self.age < self.life
    def draw(self, screen: pygame.Surface, cam: Camera):
        if not self.alive: return
        alpha = max(0, 255 * (1.0 - self.age / self.life))
        color = (self.col[0], self.col[1], self.col[2], int(alpha))
        surf = pygame.Surface((int(self.r*2)+2, int(self.r*2)+2), pygame.SRCALPHA)
        pygame.draw.circle(surf, color, (surf.get_width()//2, surf.get_height()//2), int(self.r))
        dx, dy = cam.apply_xy(self.x, self.y)
        screen.blit(surf, (dx - surf.get_width()//2, dy - surf.get_height()//2))

# ---------------- Pickup ----------------
class Pickup:
    def __init__(self, x: float, y: float, kind: str, pickup_id: int = 0):
        self.id = pickup_id
        self.x, self.y, self.kind = float(x), float(y), kind
        self.w, self.h = 32, 32
        self.alive = True
    @property
    def rect(self) -> pygame.Rect: 
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)
    def draw(self, screen: pygame.Surface, cam: Camera):
        if not self.alive: return
        
        # 🔥 حركة طفو
        t = time.time() * 4.0
        bob_offset = math.sin(t) * 4.0
        
        dx, dy = cam.apply_xy(self.x, self.y)
        dx = int(dx)
        dy = int(dy + bob_offset)
        
        w, h = 40, 30
        
        if self.kind == "medkit":
            # 🏥 حقيبة إسعافات احترافية (Medical Case)
            # الألوان
            case_color = (240, 240, 245)    # أبيض
            cross_color = (220, 20, 60)     # أحمر
            handle_color = (60, 60, 60)     # رمادي غامق
            shadow_color = (180, 180, 190)  # ظل الحقيبة
            
            # الظل على الأرض
            shadow_width = w + int(math.sin(t)*4)
            pygame.draw.ellipse(screen, (0, 0, 0, 60), 
                              (dx + (w-shadow_width)//2, dy + h + 10 - bob_offset, shadow_width, 8))
            
            # جسم الحقيبة (3D Look)
            # الوجه الخلفي/الجانبي
            pygame.draw.rect(screen, shadow_color, (dx + 4, dy - 4, w, h), border_radius=6)
            # الوجه الأمامي
            rect = pygame.Rect(dx, dy, w, h)
            pygame.draw.rect(screen, case_color, rect, border_radius=6)
            pygame.draw.rect(screen, (200, 200, 210), rect, width=2, border_radius=6)
            
            # المقبض في الأعلى
            pygame.draw.rect(screen, handle_color, (dx + w//2 - 6, dy - 8, 12, 8), border_radius=2)
            pygame.draw.rect(screen, (0,0,0), (dx + w//2 - 4, dy - 6, 8, 4)) # فراغ المقبض
            
            # الصليب الأحمر (Red Cross)
            cw, ch = 8, 20
            cx, cy = dx + w//2, dy + h//2
            pygame.draw.rect(screen, cross_color, (cx - cw//2, cy - ch//2, cw, ch), border_radius=2)
            pygame.draw.rect(screen, cross_color, (cx - ch//2, cy - cw//2, ch, cw), border_radius=2)
            
            # لمعان
            pygame.draw.ellipse(screen, (255, 255, 255), (dx + 4, dy + 4, 12, 8))
            
        elif self.kind == "shotgun_ammo" or self.kind == "grenade_ammo":
            # 📦 صندوق ذخيرة عسكري 3D
            if self.kind == "shotgun_ammo":
                main_color = (180, 40, 40)      # أحمر للخرطوش
                light_color = (220, 60, 60)
                dark_color = (120, 30, 30)
                icon_color = (255, 200, 50)     # ذهبي
                label = "SHELLS"
            else: # grenade_ammo
                main_color = (50, 80, 50)       # أخضر عسكري
                light_color = (70, 100, 70)
                dark_color = (30, 50, 30)
                icon_color = (200, 200, 200)    # فضي
                label = "NADES"

            # الظل
            shadow_width = w + int(math.sin(t*3)*2)
            pygame.draw.ellipse(screen, (0, 0, 0, 80), 
                              (dx + (w-shadow_width)//2, dy + h + 5 - bob_offset, shadow_width, 8))

            # الوجه الخلفي
            pygame.draw.rect(screen, dark_color, (dx + 4, dy - 4, w, h), border_radius=4)
            # الوجه الأمامي
            rect = pygame.Rect(dx, dy, w, h)
            pygame.draw.rect(screen, main_color, rect, border_radius=4)
            
            # تفاصيل الإطار
            pygame.draw.rect(screen, light_color, rect, width=2, border_radius=4)
            corner_len = 8
            corner_color = (180, 180, 180)
            pygame.draw.line(screen, corner_color, (dx, dy), (dx + corner_len, dy), 2)
            pygame.draw.line(screen, corner_color, (dx, dy), (dx, dy + corner_len), 2)
            pygame.draw.line(screen, corner_color, (dx + w, dy + h), (dx + w - corner_len, dy + h), 2)
            pygame.draw.line(screen, corner_color, (dx + w, dy + h), (dx + w, dy + h - corner_len), 2)
            
            # الرمز
            font = pygame.font.SysFont("arial", 9, bold=True)
            text_surf = font.render(label, True, icon_color)
            text_rect = text_surf.get_rect(center=rect.center)
            bg_text_rect = text_rect.inflate(4, 2)
            pygame.draw.rect(screen, (0, 0, 0, 100), bg_text_rect, border_radius=2)
            screen.blit(text_surf, text_rect)
            
        else:
            # 📦 صندوق غامض (Mystery Crate) - فقط للأنواع غير المعروفة
            box_color = (100, 80, 60)
            tape_color = (200, 180, 140)
            
            # الظل
            pygame.draw.ellipse(screen, (0, 0, 0, 80), (dx + 2, dy + h + 2, w - 4, 8))
            
            # الصندوق
            rect = pygame.Rect(dx, dy, w, h)
            pygame.draw.rect(screen, box_color, rect, border_radius=4)
            pygame.draw.rect(screen, (80, 60, 40), rect, width=2, border_radius=4)
            
            # شريط لاصق
            pygame.draw.line(screen, tape_color, (dx + w//2, dy), (dx + w//2, dy + h), 4)
            pygame.draw.line(screen, tape_color, (dx, dy + h//2), (dx + w, dy + h//2), 4)

    def to_dict(self):
        return { 'id': self.id, 'x': self.x, 'y': self.y, 'kind': self.kind, 'alive': self.alive }
    @staticmethod
    def from_dict(data):
        p = Pickup(data['x'], data['y'], data['kind'], data['id'])
        p.alive = data['alive']
        return p

# ---------------- Levels ----------------
LEVELS = {
    1: {"goal_kills": 2,  "spawn_every": 1.6, "max_alive": 6},
    2: {"goal_kills": 2, "spawn_every": 1.25,"max_alive": 9},
    3: {"goal_kills": 2, "spawn_every": 1.00,"max_alive": 12},
    4: {"goal_kills": 2, "spawn_every": 0.90,"max_alive": 14},
    5: {"goal_kills": 2, "spawn_every": 0.80,"max_alive": 16},
    6: {"goal_kills": 2, "spawn_every": 0.70,"max_alive": 18},
}

# ---------------- Utilities ----------------
def find_free_spawn(walls: list[pygame.Rect], W: int, H: int, w: int, h: int, attempts: int = 40, margin: int = 80):
    for _ in range(attempts):
        x = random.randint(margin, W - margin - w)
        y = random.randint(margin, H - margin - h)
        r = pygame.Rect(x, y, w, h)
        if not collide_rect_list(r, walls):
            return float(x), float(y)
    return float(W//2 - w//2), float(H//2 - h//2)

def far_from_player(px: float, py: float, x: float, y: float, min_dist: float = 280.0) -> bool:
    return (px - x) ** 2 + (py - y) ** 2 >= (min_dist ** 2)

def find_door_location(walls: list[pygame.Rect], player_x: float, player_y: float, W: int, H: int):
    for _ in range(30):
        x = random.randint(100, W - 100)
        y = random.randint(100, H - 100)
        if not far_from_player(player_x, player_y, x, y, min_dist=400.0):
            continue
        door_rect = pygame.Rect(x, y, 80, 120)
        if not collide_rect_list(door_rect, walls):
            return float(x), float(y)
    return float(W - 150), float(H - 200)

# 🔥 --- (جديد) --- دوال الخلفيات من game.py ---
def generate_background_effects(level: int, effects_dict: dict, W: int, H: int):
    """
    ينشئ ويخزن المؤثرات البرمجية (نجوم، شقوق، بقع) للخلفية.
    يرسمها مسبقاً على سطح واحد كبير لتحقيق أقصى أداء.
    """
    effects_dict.clear() 
    rng = random.Random(level) 
    
    bg_surf = pygame.Surface((W, H)).convert() 
    
    base_col = LEVEL_COLORS.get(level, (166, 98, 42))
    bg_surf.fill(base_col)

    if level == 2: # مدينة - شبكة بلاط
        tile_size = 80
        grid_color = (100, 100, 100)
        for x in range(0, W, tile_size):
            pygame.draw.line(bg_surf, grid_color, (x, 0), (x, H), 1)
        for y in range(0, H, tile_size):
            pygame.draw.line(bg_surf, grid_color, (0, y), (W, y), 1)

    elif level == 3: # غابة
        for _ in range(400):
            x = rng.randint(0, W); y = rng.randint(0, H)
            r = rng.randint(15, 45)
            col_darken = rng.randint(5, 20)
            col = (
                max(0, LEVEL_COLORS[3][0] - col_darken),
                max(0, LEVEL_COLORS[3][1] - col_darken),
                max(0, LEVEL_COLORS[3][2] - col_darken)
            )
            pygame.draw.circle(bg_surf, col, (x, y), r)
            
    elif level == 4: # فضاء
        for _ in range(1000):
            x = rng.randint(0, W); y = rng.randint(0, H)
            r = rng.randint(1, 3)
            brightness = rng.randint(150, 255)
            col = (brightness, brightness, brightness)
            pygame.draw.circle(bg_surf, col, (x, y), r)

    elif level == 5: # بركان
        crack_color = (20, 10, 10)
        for _ in range(150):
            x1 = rng.randint(0, W); y1 = rng.randint(0, H)
            angle = rng.uniform(0, 2 * math.pi)
            length = rng.randint(50, 200)
            x2 = x1 + int(math.cos(angle) * length)
            y2 = y1 + int(math.sin(angle) * length)
            width = rng.randint(2, 5)
            pygame.draw.line(bg_surf, crack_color, (x1, y1), (x2, y2), width)

    effects_dict["pre_rendered_bg"] = bg_surf

def draw_level_background(screen: pygame.Surface, level: int, cam: Camera, effects_dict: dict):
    """
    يرسم الخلفية: يستخدم "اللوحة" المرسومة مسبقاً.
    """
    bg_surf = effects_dict.get("pre_rendered_bg")
    
    if bg_surf:
        visible_area = pygame.Rect(int(cam.x), int(cam.y), WINDOW_W, WINDOW_H)
        screen.blit(bg_surf, (0, 0), area=visible_area)
    else:
        # (كود احتياطي إذا فشل التحميل)
        current_bg_color = LEVEL_COLORS.get(level, (166, 98, 42)) 
        screen.fill(current_bg_color)

# 🔥 --- (جديد) --- شاشة النصر للاعبين المتعددين ---

# تدرّج ذهبي احترافي لشاشة النصر المتعددة
def _lerp_m(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def _mix_m(c1: tuple[int,int,int], c2: tuple[int,int,int], t: float) -> tuple[int,int,int]:
    return (
        int(_lerp_m(c1[0], c2[0], t)),
        int(_lerp_m(c1[1], c2[1], t)),
        int(_lerp_m(c1[2], c2[2], t))
    )

def create_victory_gradient_m(W: int, H: int) -> pygame.Surface:
    """خلفية ذهبية فاخرة مع تدرّج شعاعي وخطوط ناعمة."""
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    base_dark = (24, 20, 14)
    surf.fill(base_dark)
    cx, cy = W // 2, int(H * 0.38)
    max_r = int((W**2 + H**2) ** 0.5)
    inner = (255, 236, 170)
    mid   = (220, 180, 100)
    outer = base_dark
    steps = 72
    for i in range(steps, 0, -1):
        t = i / steps
        tt = t * t * (3 - 2 * t)
        col = _mix_m(mid, inner, (tt - 0.5) / 0.5) if tt > 0.5 else _mix_m(outer, mid, tt / 0.5)
        alpha = int(220 * (t ** 1.6))
        pygame.draw.circle(surf, (*col, alpha), (cx, cy), int(max_r * (1.0 - (i - 1) / steps)))
    stripes = pygame.Surface((W, H), pygame.SRCALPHA)
    for y in range(0, H, 5):
        a = int(16 * (1.0 - y / H))
        pygame.draw.line(stripes, (255, 235, 160, a), (0, y), (W, y))
    surf.blit(stripes, (0, 0), special_flags=pygame.BLEND_ADD)
    return surf
class MultiplayerVictoryScene:
    def __init__(self, screen: pygame.Surface, score: int = 0, total_kills: int = 0):
        self.screen = screen
        self.W, self.H = screen.get_size()
        self.score = score
        self.total_kills = total_kills
        
        # تحميل صورة النصر
        self.bg_image = None
        try:
            self.bg_image = pygame.image.load("BP3_CX11_blog_images1.jpg")
            img_ratio = self.bg_image.get_width() / self.bg_image.get_height()
            screen_ratio = self.W / self.H
            
            if img_ratio > screen_ratio:
                new_height = self.H
                new_width = int(new_height * img_ratio)
            else:
                new_width = self.W
                new_height = int(new_width / img_ratio)
                
            self.bg_image = pygame.transform.scale(self.bg_image, (new_width, new_height))
            self.bg_x = (self.W - new_width) // 2
            self.bg_y = (self.H - new_height) // 2
            
            # 🔥 تحسين جودة الصورة - زيادة السطوع والتباين
            brightened_image = pygame.Surface((new_width, new_height))
            brightened_image.fill((80, 80, 80, 0))
            self.bg_image.blit(brightened_image, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            
        except Exception as e:
            print(f"Failed to load victory image: {e}")
            self.bg_image = None
        
        # إنشاء الأزرار
        button_width, button_height = 200, 50
        center_x = self.W // 2
        
        self.play_again_btn = Button(
            pygame.Rect(center_x - button_width - 20, self.H - 100, button_width, button_height),
            "PLAY AGAIN"
        )
        
        self.menu_btn = Button(
            pygame.Rect(center_x + 20, self.H - 100, button_width, button_height),
            "MAIN MENU"
        )
        
        # تأثيرات بصرية
        self.fade_surface = pygame.Surface((self.W, self.H))
        self.fade_surface.fill((0, 0, 0))
        self.fade_alpha = 0
        self.fade_speed = 4
        
        # جزيئات احتفالية
        self.confetti_particles = []
        self._create_confetti_particles()
        
        # مؤقت للرسوم المتحركة
        self.animation_timer = 0.0
        
        # تأثيرات نصية متلألئة
        self.text_glow_timer = 0.0
        
        # 🔥 إضافة سطح للإضاءة الذهبية
        self.golden_overlay = pygame.Surface((self.W, self.H))
        self.golden_overlay.fill((255, 215, 0))
        self.golden_overlay.set_alpha(20)
        # خلفية تدرّج ذهبية مرسومة مسبقاً
        self.gradient_bg = create_victory_gradient_m(self.W, self.H)
    
    def _create_confetti_particles(self):
        """إنشاء جزيئات احتفالية (كونفيتي)"""
        colors = [
            (255, 50, 50),    # أحمر
            (50, 255, 50),    # أخضر
            (50, 50, 255),    # أزرق
            (255, 255, 50),   # أصفر
            (255, 50, 255),   # وردي
            (50, 255, 255),   # سماوي
        ]
        
        for _ in range(100):
            self.confetti_particles.append({
                'x': random.randint(0, self.W),
                'y': random.randint(-100, 0),
                'color': random.choice(colors),
                'size': random.randint(4, 8),
                'speed': random.uniform(2, 6),
                'sway': random.uniform(-1, 1),
                'rotation': random.uniform(0, 360)
            })
    
    def update(self, dt: float):
        """تحديث تأثيرات الشاشة"""
        self.animation_timer += dt
        self.text_glow_timer += dt
        
        # تأثير التعتيم التدريجي
        if self.fade_alpha < 180:
            self.fade_alpha += self.fade_speed
            self.fade_surface.set_alpha(min(self.fade_alpha, 180))
        
        # تحديث جزيئات الكونفيتي
        for particle in self.confetti_particles:
            particle['y'] += particle['speed']
            particle['x'] += particle['sway'] * 0.5
            particle['rotation'] += 2
            
            # إعادة الجزيئات التي سقطت للأسفل
            if particle['y'] > self.H:
                particle['y'] = random.randint(-100, 0)
                particle['x'] = random.randint(0, self.W)
    
    def draw(self):
        """رسم شاشة النصر"""
        screen = self.screen
        
        # خلفية
        if self.bg_image:
            screen.blit(self.bg_image, (self.bg_x, self.bg_y))
            # تعزيز السطوع بإضافة طفيفة بيضاء/ذهبية
            brighten = pygame.Surface((self.W, self.H))
            brighten.fill((255, 255, 255))
            brighten.set_alpha(50)
            screen.blit(brighten, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        else:
            # خلفية ذهبية فاخرة عند عدم توفر الصورة
            screen.blit(self.gradient_bg, (0, 0))
        
        # رسم الكونفيتي
        for particle in self.confetti_particles:
            particle_surf = pygame.Surface((particle['size'], particle['size']), pygame.SRCALPHA)
            pygame.draw.rect(particle_surf, particle['color'], (0, 0, particle['size'], particle['size']))
            rotated = pygame.transform.rotate(particle_surf, particle['rotation'])
            rect = rotated.get_rect(center=(particle['x'], particle['y']))
            screen.blit(rotated, rect.topleft)
        
        # أشعة شعاعية ذهبية ساطعة
        rays = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        cx, cy = self.W // 2, int(self.H * 0.38)
        ray_count = 36
        base_angle = self.text_glow_timer * 0.5
        for i in range(ray_count):
            ang = base_angle + (i / ray_count) * (2 * math.pi)
            length = max(self.W, self.H) * 1.2
            x2 = cx + math.cos(ang) * length
            y2 = cy + math.sin(ang) * length
            pygame.draw.line(rays, (255, 240, 180, 60), (cx, cy), (x2, y2), 28)
        screen.blit(rays, (0, 0), special_flags=pygame.BLEND_PREMULTIPLIED)

        # توهج مركزي (Bloom) لإبراز السطوع
        bloom = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        for r in range(320, 0, -24):
            a = max(0, 60 - (320 - r) // 6)
            pygame.draw.circle(bloom, (255, 255, 220, a), (cx, cy), r)
        screen.blit(bloom, (0, 0), special_flags=pygame.BLEND_ADD)

        # طبقة ذهبية نابضة قوية
        pulse = (math.sin(self.text_glow_timer * 1.2) + 1) * 0.5
        self.golden_overlay.set_alpha(int(80 + 110 * pulse))
        screen.blit(self.golden_overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        
        # نص VICTORY مع تأثير التوهج
        glow_intensity = (math.sin(self.text_glow_timer * 3) + 1) * 0.3 + 0.4
        main_color = (255, 215, 0)
        glow_color = (255, 255, 150, int(200 * glow_intensity))

        font_large = pygame.font.Font(None, 82)
        text_surf = font_large.render("VICTORY!", True, main_color)
        text_rect = text_surf.get_rect(center=(self.W // 2, self.H // 3 - 60))

        glow_surf = font_large.render("VICTORY!", True, glow_color)
        for offset in [(2,2), (-2,2), (2,-2), (-2,-2), (0,3), (0,-3), (3,0), (-3,0)]:
            screen.blit(glow_surf, (text_rect.x + offset[0], text_rect.y + offset[1]))
        screen.blit(text_surf, text_rect)

        # رسالة التهنئة
        font_medium = pygame.font.Font(None, 36)
        subtext_surf = font_medium.render("All Levels Completed!", True, (0, 0, 0))
        subtext_rect = subtext_surf.get_rect(center=(self.W // 2, self.H // 3 + 10))
        screen.blit(subtext_surf, subtext_rect)

        # مربع الإحصائيات (فاتح وذهبي)
        stats_y = self.H // 3 + 70
        stats_bg = pygame.Rect(self.W // 2 - 200, stats_y - 20, 400, 120)
        panel = pygame.Surface((stats_bg.width, stats_bg.height), pygame.SRCALPHA)
        for py in range(panel.get_height()):
            prog = py / panel.get_height()
            col = (255, int(245 - 30 * prog), int(200 - 60 * prog), 90)
            pygame.draw.line(panel, col, (0, py), (panel.get_width(), py))
        pygame.draw.rect(panel, (255, 215, 0, 180), panel.get_rect(), 3, border_radius=15)
        screen.blit(panel, stats_bg.topleft)

        # النقاط النهائية
        score_font = pygame.font.Font(None, 32)
        score_surf = score_font.render(f"Final Score: {self.score}", True, (0, 0, 0))
        score_rect = score_surf.get_rect(center=(self.W // 2, stats_y + 10))
        screen.blit(score_surf, score_rect)

        # الزومبي المقتولين
        kills_surf = score_font.render(f"Total Zombies Killed: {self.total_kills}", True, (0, 0, 0))
        kills_rect = kills_surf.get_rect(center=(self.W // 2, stats_y + 50))
        screen.blit(kills_surf, kills_rect)

        # إنجاز
        achievement_surf = score_font.render("You are the ultimate survivors!", True, (0, 0, 0))
        achievement_rect = achievement_surf.get_rect(center=(self.W // 2, stats_y + 90))
        screen.blit(achievement_surf, achievement_rect)

        # الأزرار
        self.play_again_btn.draw(screen)
        self.menu_btn.draw(screen)

        # تأثير التعتيم (محجّم بقيمة صغيرة جداً للحفاظ على السطوع)
        if self.fade_alpha > 0:
            self.fade_surface.set_alpha(min(30, self.fade_alpha))
            screen.blit(self.fade_surface, (0, 0))
    
    def handle_event(self, event) -> str | None:
        """معالجة الأحداث والاختيارات"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.play_again_btn.hit(event.pos):
                return "restart"
            elif self.menu_btn.hit(event.pos):
                return "menu"
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r or event.key == pygame.K_RETURN:
                return "restart"
            elif event.key == pygame.K_m:
                return "menu"
            elif event.key == pygame.K_ESCAPE:
                return "quit"
        
        return None

def show_multiplayer_victory_screen(screen: pygame.Surface, clock: pygame.time.Clock, score: int = 0, total_kills: int = 0) -> str:
    """عرض شاشة النصر للاعبين المتعددين"""
    victory_scene = MultiplayerVictoryScene(screen, score, total_kills)
    
    # إيقاف الموسيقى الخلفية إذا كانت تعمل
    try:
        pygame.mixer.music.stop()
    except:
        pass
    
    # تشغيل صوت النصر إذا وجد
    try:
        victory_sound = load_sound("victory.wav")
        if victory_sound:
            victory_sound.play()
    except:
        pass
    
    running = True
    while running:
        dt = clock.get_time() / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            
            result = victory_scene.handle_event(event)
            if result:
                return result
        
        victory_scene.update(dt)
        victory_scene.draw()
        
        pygame.display.flip()
        clock.tick(FPS)
    
    return "menu"

# 🔥 --- شاشة Game Over المحسنة والجذابة للاعبين المتعددين ---
class MultiplayerGameOverScene:
    def __init__(self, screen: pygame.Surface, score: int = 0, level: int = 1, player1_stats: dict = None, player2_stats: dict = None):
        self.screen = screen
        self.W, self.H = screen.get_size()
        self.score = score
        self.level = level
        self.player1_stats = player1_stats or {}
        self.player2_stats = player2_stats or {}
        
        # تحميل صورة الخلفية
        self.bg_image = None
        try:
            self.bg_image = pygame.image.load("360_F_693042027_th0Yf1aofOwdQdabsMVLRtNieakvmDGr.jpg")
            img_ratio = self.bg_image.get_width() / self.bg_image.get_height()
            new_height = max(self.H, int(self.W / img_ratio))
            new_width = int(new_height * img_ratio)
            self.bg_image = pygame.transform.scale(self.bg_image, (new_width, new_height))
            self.bg_x = (self.W - new_width) // 2
            self.bg_y = (self.H - new_height) // 2
        except:
            self.bg_image = None
        
        # 🔥 جزيئات الدم المتطايرة
        self.blood_particles = []
        self.falling_skulls = []
        self.floating_texts = []
        self._create_particles()
        
        # 🔥 تأثيرات بصرية متقدمة
        self.animation_timer = 0.0
        self.title_scale = 0.0
        self.stats_alpha = 0
        self.buttons_y_offset = 100
        self.shake_intensity = 20
        self.glow_intensity = 0
        self.pulse_timer = 0
        
        # 🔥 تأثير الصدمة الأولي
        self.initial_shake = True
        self.shake_timer = 0.5
        
        # أزرار جذابة
        button_width, button_height = 220, 55
        center_x = self.W // 2
        
        self.play_again_btn = GlowButton(
            pygame.Rect(center_x - button_width - 30, self.H - 120, button_width, button_height),
            "⚔ PLAY AGAIN",
            base_color=(60, 180, 100),
            glow_color=(100, 255, 150)
        )
        
        self.menu_btn = GlowButton(
            pygame.Rect(center_x + 30, self.H - 120, button_width, button_height),
            "🏠 MAIN MENU",
            base_color=(180, 80, 80),
            glow_color=(255, 120, 120)
        )
        
        # 🔥 صوت الموت
        self.death_sound_played = False
    
    def _create_particles(self):
        """إنشاء جزيئات بصرية متنوعة"""
        # جزيئات الدم
        for _ in range(40):
            self.blood_particles.append({
                'x': random.randint(0, self.W),
                'y': random.randint(-200, self.H),
                'size': random.randint(3, 12),
                'speed_y': random.uniform(30, 120),
                'speed_x': random.uniform(-20, 20),
                'alpha': random.randint(150, 255),
                'color': (random.randint(150, 255), random.randint(0, 50), random.randint(0, 30))
            })
        
        # جماجم متساقطة صغيرة
        for _ in range(8):
            self.falling_skulls.append({
                'x': random.randint(50, self.W - 50),
                'y': random.randint(-300, -50),
                'speed': random.uniform(20, 60),
                'rotation': random.uniform(0, 360),
                'rot_speed': random.uniform(-90, 90),
                'size': random.randint(15, 30)
            })
    
    def update(self, dt: float):
        """تحديث التأثيرات"""
        self.animation_timer += dt
        self.pulse_timer += dt * 3
        
        # تأثير الصدمة
        if self.shake_timer > 0:
            self.shake_timer -= dt
            self.shake_intensity = max(0, self.shake_intensity - dt * 40)
        else:
            self.initial_shake = False
            self.shake_intensity = 0
        
        # تأثير ظهور العنوان
        if self.title_scale < 1.0:
            self.title_scale = min(1.0, self.title_scale + dt * 2.5)
        
        # ظهور الإحصائيات تدريجياً
        if self.animation_timer > 0.5 and self.stats_alpha < 255:
            self.stats_alpha = min(255, self.stats_alpha + int(dt * 400))
        
        # حركة الأزرار
        if self.animation_timer > 0.8 and self.buttons_y_offset > 0:
            self.buttons_y_offset = max(0, self.buttons_y_offset - dt * 200)
        
        # توهج
        self.glow_intensity = 0.5 + 0.5 * math.sin(self.pulse_timer)
        
        # تحديث الجزيئات
        for particle in self.blood_particles:
            particle['y'] += particle['speed_y'] * dt
            particle['x'] += particle['speed_x'] * dt
            if particle['y'] > self.H + 50:
                particle['y'] = random.randint(-100, -20)
                particle['x'] = random.randint(0, self.W)
        
        # تحديث الجماجم
        for skull in self.falling_skulls:
            skull['y'] += skull['speed'] * dt
            skull['rotation'] += skull['rot_speed'] * dt
            if skull['y'] > self.H + 50:
                skull['y'] = random.randint(-200, -50)
                skull['x'] = random.randint(50, self.W - 50)
        
        # تحديث الأزرار
        mouse_pos = pygame.mouse.get_pos()
        self.play_again_btn.update(dt, mouse_pos)
        self.menu_btn.update(dt, mouse_pos)
    
    def draw(self):
        """رسم شاشة Game Over الجذابة"""
        screen = self.screen
        
        # حساب الاهتزاز
        shake_x = random.randint(-int(self.shake_intensity), int(self.shake_intensity)) if self.initial_shake else 0
        shake_y = random.randint(-int(self.shake_intensity), int(self.shake_intensity)) if self.initial_shake else 0
        
        # 🔥 خلفية متدرجة داكنة
        for y in range(0, self.H, 2):
            progress = y / self.H
            r = int(40 + 30 * progress)
            g = int(10 + 15 * progress)
            b = int(15 + 20 * progress)
            pygame.draw.line(screen, (r, g, b), (0, y), (self.W, y))
        
        # صورة الخلفية
        if self.bg_image:
            screen.blit(self.bg_image, (self.bg_x + shake_x, self.bg_y + shake_y))
            # طبقة داكنة
            dark_overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            dark_overlay.fill((0, 0, 0, 180))
            screen.blit(dark_overlay, (0, 0))
        
        # 🔥 جزيئات الدم
        for particle in self.blood_particles:
            glow_size = particle['size'] + 4
            glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*particle['color'], 50), (glow_size, glow_size), glow_size)
            screen.blit(glow_surf, (int(particle['x'] - glow_size), int(particle['y'] - glow_size)))
            pygame.draw.circle(screen, particle['color'], (int(particle['x']), int(particle['y'])), particle['size'])
        
        # 🔥 جماجم متساقطة
        for skull in self.falling_skulls:
            self._draw_skull(screen, skull['x'], skull['y'], skull['size'], skull['rotation'])
        
        # 🔥 عنوان GAME OVER مع تأثير متقدم
        title_y = self.H // 4
        self._draw_game_over_title(screen, self.W // 2 + shake_x, title_y + shake_y)
        
        # 🔥 رسالة ثانوية
        if self.animation_timer > 0.3:
            alpha = min(255, int((self.animation_timer - 0.3) * 500))
            font_medium = pygame.font.Font(None, 32)
            pulse = 1 + 0.05 * math.sin(self.pulse_timer * 2)
            sub_text = "☠ Both warriors have fallen... ☠"
            sub_surf = font_medium.render(sub_text, True, (255, 200, 200))
            sub_surf.set_alpha(alpha)
            sub_rect = sub_surf.get_rect(center=(self.W // 2, title_y + 80))
            screen.blit(sub_surf, sub_rect)
        
        # 🔥 لوحة الإحصائيات الجذابة
        if self.stats_alpha > 0:
            self._draw_stats_panel(screen, self.W // 2, title_y + 160)
        
        # 🔥 الأزرار مع تأثير الظهور
        btn_offset = int(self.buttons_y_offset)
        self.play_again_btn.rect.centery = self.H - 90 + btn_offset
        self.menu_btn.rect.centery = self.H - 90 + btn_offset
        
        if self.animation_timer > 0.8:
            self.play_again_btn.draw(screen)
            self.menu_btn.draw(screen)
        
        # 🔥 تعليمات التحكم المتوهجة
        if self.animation_timer > 1.2:
            controls_alpha = min(255, int((self.animation_timer - 1.2) * 300))
            self._draw_controls(screen, controls_alpha)
        
        # 🔥 تأثير الحواف المتوهجة
        self._draw_vignette(screen)
    
    def _draw_game_over_title(self, screen, x, y):
        """رسم عنوان GAME OVER بتأثير جذاب"""
        scale = self.title_scale
        
        # الحجم الأساسي
        base_size = int(90 * scale)
        if base_size < 10:
            return
            
        font_large = pygame.font.Font(None, base_size)
        
        # 🔥 تأثير التوهج الخلفي
        glow_colors = [
            (255, 50, 50, int(30 * self.glow_intensity)),
            (255, 80, 80, int(20 * self.glow_intensity)),
            (255, 100, 100, int(10 * self.glow_intensity))
        ]
        
        for i, (r, g, b, a) in enumerate(glow_colors):
            offset = (i + 1) * 4
            glow_surf = font_large.render("GAME OVER", True, (r, g, b))
            glow_rect = glow_surf.get_rect(center=(x, y))
            for dx in [-offset, 0, offset]:
                for dy in [-offset, 0, offset]:
                    screen.blit(glow_surf, glow_rect.move(dx, dy))
        
        # 🔥 النص الرئيسي مع تأثير النبض
        pulse = 1 + 0.03 * math.sin(self.pulse_timer * 4)
        main_color = (255, int(50 + 30 * self.glow_intensity), int(50 + 30 * self.glow_intensity))
        
        # ظل
        shadow_surf = font_large.render("GAME OVER", True, (80, 0, 0))
        shadow_rect = shadow_surf.get_rect(center=(x + 4, y + 4))
        screen.blit(shadow_surf, shadow_rect)
        
        # النص
        text_surf = font_large.render("GAME OVER", True, main_color)
        text_rect = text_surf.get_rect(center=(x, y))
        screen.blit(text_surf, text_rect)
        
        # 🔥 خط ديكوري
        line_width = int(300 * scale)
        line_y = y + 45
        pygame.draw.line(screen, (255, 80, 80), (x - line_width//2, line_y), (x + line_width//2, line_y), 3)
        # نقاط ديكورية
        pygame.draw.circle(screen, (255, 100, 100), (x - line_width//2, line_y), 5)
        pygame.draw.circle(screen, (255, 100, 100), (x + line_width//2, line_y), 5)
    
    def _draw_stats_panel(self, screen, x, y):
        """رسم لوحة الإحصائيات"""
        panel_width, panel_height = 400, 120
        panel_rect = pygame.Rect(x - panel_width//2, y - panel_height//2, panel_width, panel_height)
        
        # خلفية اللوحة مع شفافية
        panel_surf = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        
        # تدرج الخلفية
        for py in range(panel_height):
            progress = py / panel_height
            alpha = int(180 - 30 * progress)
            pygame.draw.line(panel_surf, (30, 20, 25, alpha), (0, py), (panel_width, py))
        
        # حدود متوهجة
        border_color = (255, int(80 + 40 * self.glow_intensity), int(80 + 40 * self.glow_intensity))
        pygame.draw.rect(panel_surf, border_color, (0, 0, panel_width, panel_height), 3, border_radius=15)
        
        panel_surf.set_alpha(self.stats_alpha)
        screen.blit(panel_surf, panel_rect)
        
        # 🔥 الإحصائيات
        font_stats = pygame.font.Font(None, 36)
        font_label = pygame.font.Font(None, 24)
        
        # النتيجة
        score_text = f"🏆 FINAL SCORE"
        score_surf = font_label.render(score_text, True, (200, 180, 150))
        score_surf.set_alpha(self.stats_alpha)
        screen.blit(score_surf, score_surf.get_rect(center=(x, y - 35)))
        
        score_value = f"{self.score:,}"
        value_surf = font_stats.render(score_value, True, (255, 220, 100))
        value_surf.set_alpha(self.stats_alpha)
        screen.blit(value_surf, value_surf.get_rect(center=(x, y - 5)))
        
        # المستوى
        level_text = f"📍 Reached Level {self.level}"
        level_surf = font_label.render(level_text, True, (150, 200, 255))
        level_surf.set_alpha(self.stats_alpha)
        screen.blit(level_surf, level_surf.get_rect(center=(x, y + 30)))
    
    def _draw_skull(self, screen, x, y, size, rotation):
        """رسم جمجمة صغيرة"""
        # جمجمة بسيطة
        skull_color = (200, 180, 160)
        pygame.draw.circle(screen, skull_color, (int(x), int(y)), size // 2)
        # عيون
        eye_size = max(2, size // 6)
        pygame.draw.circle(screen, (40, 30, 30), (int(x - size//5), int(y - size//8)), eye_size)
        pygame.draw.circle(screen, (40, 30, 30), (int(x + size//5), int(y - size//8)), eye_size)
    
    def _draw_controls(self, screen, alpha):
        """رسم تعليمات التحكم"""
        font = pygame.font.Font(None, 22)
        controls = [
            ("R", "Play Again"),
            ("M", "Main Menu"),
            ("ESC", "Quit")
        ]
        
        y = self.H - 35
        total_width = sum(len(c[0]) * 12 + len(c[1]) * 8 + 40 for c in controls)
        start_x = (self.W - total_width) // 2
        
        for key, action in controls:
            # خلفية المفتاح
            key_width = len(key) * 12 + 16
            key_rect = pygame.Rect(start_x, y - 10, key_width, 22)
            pygame.draw.rect(screen, (60, 60, 70), key_rect, border_radius=4)
            pygame.draw.rect(screen, (100, 100, 120), key_rect, 1, border_radius=4)
            
            # النص
            key_surf = font.render(key, True, (255, 255, 255))
            key_surf.set_alpha(alpha)
            screen.blit(key_surf, key_surf.get_rect(center=key_rect.center))
            
            # الإجراء
            action_surf = font.render(action, True, (180, 180, 180))
            action_surf.set_alpha(alpha)
            screen.blit(action_surf, (start_x + key_width + 8, y - 6))
            
            start_x += key_width + len(action) * 8 + 35
    
    def _draw_vignette(self, screen):
        """تأثير الحواف الداكنة"""
        vignette = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        
        # حواف سوداء متدرجة
        for i in range(80):
            alpha = int((80 - i) * 2.5)
            pygame.draw.rect(vignette, (0, 0, 0, alpha), (i, i, self.W - 2*i, self.H - 2*i), 2)
        
        # تأثير أحمر في الأعلى
        red_overlay = pygame.Surface((self.W, 60), pygame.SRCALPHA)
        for y in range(60):
            alpha = int(40 * (1 - y / 60))
            pygame.draw.line(red_overlay, (150, 0, 0, alpha), (0, y), (self.W, y))
        screen.blit(red_overlay, (0, 0))
        
        screen.blit(vignette, (0, 0))
    
    def handle_event(self, event) -> str | None:
        """معالجة الأحداث"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.animation_timer > 0.8:
                if self.play_again_btn.hit(event.pos):
                    return "restart"
                elif self.menu_btn.hit(event.pos):
                    return "menu"
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                return "restart"
            elif event.key == pygame.K_m:
                return "menu"
            elif event.key == pygame.K_RETURN:
                return "restart"
            elif event.key == pygame.K_ESCAPE:
                return "menu"
        
        return None


# 🔥 --- زر متوهج جذاب ---
class GlowButton:
    def __init__(self, rect, text, base_color=(80, 80, 120), glow_color=(120, 120, 180)):
        self.rect = rect
        self.text = text
        self.base_color = base_color
        self.glow_color = glow_color
        self.hover = False
        self.hover_scale = 1.0
        self.glow_timer = 0
        
    def update(self, dt, mouse_pos):
        self.glow_timer += dt * 3
        self.hover = self.rect.collidepoint(mouse_pos)
        
        target_scale = 1.08 if self.hover else 1.0
        self.hover_scale += (target_scale - self.hover_scale) * dt * 10
    
    def hit(self, pos):
        return self.rect.collidepoint(pos)
    
    def draw(self, screen):
        # حجم الزر
        scale = self.hover_scale
        scaled_rect = pygame.Rect(
            self.rect.centerx - int(self.rect.width * scale / 2),
            self.rect.centery - int(self.rect.height * scale / 2),
            int(self.rect.width * scale),
            int(self.rect.height * scale)
        )
        
        # 🔥 توهج خلفي
        glow_intensity = 0.5 + 0.5 * math.sin(self.glow_timer)
        if self.hover:
            glow_intensity = 1.0
        
        glow_size = 8 if self.hover else 4
        glow_surf = pygame.Surface((scaled_rect.width + glow_size*2, scaled_rect.height + glow_size*2), pygame.SRCALPHA)
        glow_color = (*self.glow_color, int(80 * glow_intensity))
        pygame.draw.rect(glow_surf, glow_color, (0, 0, glow_surf.get_width(), glow_surf.get_height()), border_radius=12)
        screen.blit(glow_surf, (scaled_rect.x - glow_size, scaled_rect.y - glow_size))
        
        # الزر الأساسي
        color = tuple(min(255, int(c * (1.2 if self.hover else 1.0))) for c in self.base_color)
        pygame.draw.rect(screen, color, scaled_rect, border_radius=10)
        
        # حدود
        border_color = self.glow_color if self.hover else tuple(min(255, c + 40) for c in self.base_color)
        pygame.draw.rect(screen, border_color, scaled_rect, 2, border_radius=10)
        
        # النص
        font = pygame.font.Font(None, 28)
        text_color = (255, 255, 255) if self.hover else (220, 220, 220)
        text_surf = font.render(self.text, True, text_color)
        text_rect = text_surf.get_rect(center=scaled_rect.center)
        screen.blit(text_surf, text_rect)

def show_multiplayer_game_over_screen(screen: pygame.Surface, clock: pygame.time.Clock, score: int = 0, level: int = 1) -> str:
    """عرض شاشة Game Over للاعبين المتعددين"""
    game_over_scene = MultiplayerGameOverScene(screen, score, level)
    
    # إيقاف الموسيقى الخلفية إذا كانت تعمل
    try:
        pygame.mixer.music.stop()
    except:
        pass
    
    # تشغيل صوت Game Over إذا وجد
    try:
        game_over_sound = load_sound("game_over.wav")
        if game_over_sound:
            game_over_sound.play()
    except:
        pass
    
    running = True
    while running:
        dt = clock.get_time() / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            
            result = game_over_scene.handle_event(event)
            if result:
                return result
        
        game_over_scene.update(dt)
        game_over_scene.draw()
        
        pygame.display.flip()
        clock.tick(FPS)
    
    return "menu"

# ---------------- Game State Manager ----------------
class GameState:
    def __init__(self):
        self.zombies: dict[int, Zombie] = {}
        # self.bullets: dict[int, Bullet] = {}  <-- REMOVED
        self.pickups: dict[int, Pickup] = {}
        self.crates: dict[int, SpeedCrate] = {}
        self.door = None
        self.level = 1
        self.total_kills = 0
        self.next_zombie_id = 0
        self.next_bullet_id = 0
        self.next_pickup_id = 0
        self.next_crate_id = 0
        
    def to_dict(self):
        return {
            'zombies': [z.to_dict() for z in self.zombies.values()],
            # 'bullets': ... <-- REMOVED
            'pickups': [p.to_dict() for p in self.pickups.values() if p.alive],
            'crates': [c.to_dict() for c in self.crates.values() if c.alive],
            'door': self.door.to_dict() if self.door else None,
            'level': self.level,
            'total_kills': self.total_kills
        }

# -------- UI helpers --------
def _draw_center_panel(screen: pygame.Surface, title: str, subtitle: str):
    WINDOW_W, WINDOW_H = screen.get_size()
    rect = pygame.Rect(WINDOW_W//2 - 260, WINDOW_H//2 - 120, 520, 220)
    pygame.draw.rect(screen, (20, 20, 26), rect, border_radius=10)
    pygame.draw.rect(screen, (230, 230, 240), rect, width=2, border_radius=10)
    draw_shadow_text(screen, title, (rect.x + 20, rect.y + 24), size=34, color=(200, 200, 200))
    draw_text(screen, subtitle, (rect.x + 20, rect.y + 90), size=24, color=(235, 235, 235))

def _wait_enter_or_quit(clock: pygame.time.Clock) -> bool:
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                return True
        clock.tick(60)
    return True

# ---------------- Multiplayer Game Loop (OPTIMIZED) ----------------
def run_multiplayer_game(screen, clock, network, player_id, version=""):
    print(f"🎮 Starting multiplayer as Player {player_id}")
    _maybe_music()

    # Sounds
    snd_shoot = load_sound("shotgun-146188.mp3")
    snd_shotgun = load_sound("shotgun-146188.mp3")
    snd_hit = load_sound("hit.wav")
    snd_pick = load_sound("pickup.wav")
    snd_hurt = load_sound("hurt.wav")
    snd_crate = load_sound("crate.wav")
    snd_door = load_sound("door.wav")
    
    # Game variables
    level_no = 1
    score = 0
    kills = 0
    hearts_max = 4
    health = hearts_max
    heart_img = load_image_to_height("heart.png", 24)
    damage_cd = 0.0
    DAMAGE_IFRAMES = 1.0
    show_hud = True

    shotgun_ammo = 8
    pistol_cool = 0.18
    shotgun_cool = 0.70
    pistol_cd = 0.0
    shotgun_cd = 0.0

    base_speed = 5.5
    boost_mult = 1.8
    boost_time = 4.0
    boost_t = 0.0

    walls = create_walls_for_level(level_no, WORLD_W, WORLD_H, tile=64)
    # 🔥 (جديد) - إنشاء الخلفية للمستوى 1
    generate_background_effects(level_no, BG_EFFECTS, WORLD_W, WORLD_H)

    if player_id == 1:
        p_spawn_x, p_spawn_y = find_free_spawn(walls, WORLD_W, WORLD_H, 36, 36)
    else:
        p_spawn_x, p_spawn_y = find_free_spawn(walls, WORLD_W, WORLD_H, 36, 36)
        if p_spawn_x < WORLD_W / 2: p_spawn_x += 200
        else: p_spawn_x -= 200
        
    # 🔥 إنشاء اللاعب مع المظهر المختار
    current_skin = get_current_skin()
    skin_color = get_skin_color(current_skin)
    p = Player(x=p_spawn_x, y=p_spawn_y, speed=base_speed, skin_color=skin_color)
    cam = Camera(WORLD_W, WORLD_H, WINDOW_W, WINDOW_H)
    cam.follow(p.rect, lerp=1.0) 

    is_host = (player_id == 1)
    game_state = GameState() if is_host else None
    
    enemies_dict: dict[int, Zombie] = {}
    # bullets_dict: dict[int, Bullet] = {}  <-- REMOVED
    pickups_dict: dict[int, Pickup] = {}
    pickups_dict: dict[int, Pickup] = {}
    crates_dict: dict[int, SpeedCrate] = {}
    
    blood_fx = []
    level_door = None

    other_players = {}

    # 🔥 --- (جديد) --- متغيرات نظام الموت والمشاهدة ---
    is_dead = False
    death_timer = 0.0
    RESPAWN_TIME = 5.0  # ثواني قبل إعادة الظهور (إذا بقي لاعب حي)
    spectating_player_id = None
    can_respawn = False

    # Timers
    spawn_t = 0.0
    pk_timer = 0.0
    crate_t = 0.0
    last_send_time = 0
    SEND_INTERVAL = 0.1
    
    pending_actions = []
    ai_update_counter = 0 

    # 🔥 === أنظمة جديدة: الأسلحة، الدردشة، الخريطة ===
    weapon_manager = None
    chat_system = None
    minimap_system = None
    ammo_pickups = {}  # صناديق الذخيرة
    show_minimap = True
    
    if FEATURES_ENABLED:
        # نظام الأسلحة
        weapon_manager = WeaponManager(player_id)
        
        # نظام الدردشة
        chat_system = ChatSystem(WINDOW_W, WINDOW_H, player_id, f"Player{player_id}")
        
        # نظام الخريطة المصغرة
        minimap_system = Minimap(WORLD_W, WORLD_H, WINDOW_W, WINDOW_H, 160)
        minimap_system.set_walls(walls)
        
        print("🔫 Weapons, Chat, and Minimap systems initialized!") 

    def send_player_data():
        player_data = {
            "type": "player_update",
            "player_id": player_id,
            "x": p.x,
            "y": p.y,
            "facing": p.facing,
            "health": health,
            "score": score,
            "kills": kills,
            "level": level_no,
            "is_dead": is_dead,  # 🔥 إرسال حالة الموت
            "death_timer": death_timer  # 🔥 إرسال مؤقت الموت
        }
        network.send_game_state(player_data)

    def send_full_game_state():
        if not is_host or not game_state: return
        full_state = {
            "type": "full_game_state",
            "game_state": game_state.to_dict(),
            "timestamp": time.time()
        }
        network.send_game_state(full_state)

    def send_player_action(action_type, action_data):
        pending_actions.append({
            "type": "player_action",
            "player_id": player_id,
            "action_type": action_type,
            "action_data": action_data,
            "timestamp": time.time()
        })

    def flush_pending_actions():
        if pending_actions:
            for action in pending_actions:
                network.send_game_state(action)
            pending_actions.clear()

    def reset_level_multiplayer(new_level: int):
        nonlocal level_no, kills, score, walls, level_door, enemies_dict, pickups_dict, crates_dict, game_state, p, spawn_t, pk_timer, crate_t, is_dead, death_timer, health
        
        print(f"--- PLAYER {player_id} RESETTING TO LEVEL {new_level} ---")
        
        level_no = new_level
        kills = 0
        
        enemies_dict.clear()
        # bullets_dict.clear() <-- REMOVED
        weapon_manager.bullets.clear(); weapon_manager.explosions.clear()
        pickups_dict.clear()
        crates_dict.clear()
        blood_fx.clear()
        
        spawn_t = 0.0
        pk_timer = 0.0
        crate_t = 0.0
        
        # 🔥 إعادة إحياء اللاعب إذا كان ميتاً
        is_dead = False
        death_timer = 0.0
        health = hearts_max
        
        walls[:] = create_walls_for_level(new_level, WORLD_W, WORLD_H, tile=64)
        generate_background_effects(new_level, BG_EFFECTS, WORLD_W, WORLD_H)
        
        # 🔥 تحديث الخريطة المصغرة لتعكس المستوى الجديد
        if minimap_system:
            minimap_system.set_walls(walls)
        
        if player_id == 1:
            p.x, p.y = find_free_spawn(walls, WORLD_W, WORLD_H, 36, 36)
        else:
            p_spawn_x, p_spawn_y = find_free_spawn(walls, WORLD_W, WORLD_H, 36, 36)
            if p_spawn_x < WORLD_W / 2: p.x = p_spawn_x + 200
            else: p.x = p_spawn_x - 200
            p.y = p_spawn_y
        
        cam.follow(p.rect, lerp=1.0) 

        if is_host and game_state:
            door_x, door_y = find_door_location(walls, p.x, p.y, WORLD_W, WORLD_H)
            level_door = LevelDoor(door_x, door_y, new_level)
            
            game_state.level = new_level
            game_state.total_kills = 0
            game_state.zombies.clear()
            # game_state.bullets.clear() <-- REMOVED
            game_state.pickups.clear()
            game_state.crates.clear()
            game_state.door = level_door
            
            network.send_game_state({
                "type": "level_change",
                "level": new_level,
                "door_pos": (door_x, door_y)
            })
        elif not is_host:
            level_door = None

    def process_received_data():
        nonlocal other_players, enemies_dict, pickups_dict, crates_dict, level_door, kills, score, level_no, can_respawn
        
        received = network.get_received_data()
        for data in received:
            msg_type = data.get("type")
            
            if msg_type == "player_update":
                other_id = data["player_id"]
                if other_id != player_id:
                    other_players[other_id] = data
                    
                    # 🔥 التحقق إذا كان هناك لاعب حي يمكن إعادة الظهور بجانبه
                    if is_dead and not data.get("is_dead", False):
                        can_respawn = True
            
            # 🔥 معالجة الدردشة
            elif msg_type == "chat" and chat_system:
                chat_system.receive_message(data)
                
            # 🔥 معالجة تحديث المظاهر
            elif msg_type == "skin_update":
                other_id = data["player_id"]
                skin_id = data["skin_id"]
                # تخزين المظهر في بيانات اللاعب الآخر
                if other_id not in other_players:
                    other_players[other_id] = {}
                other_players[other_id]["skin_id"] = skin_id
                
            # 🔥 معالجة إطلاق النار
            elif msg_type == "shoot_weapon":
                # انشاء رصاصة مرئية فقط (بدون منطق) للمحاكاة
                bx, by = data['x'], data['y']
                vx, vy = data['vx'], data['vy']
                w_type = data.get('weapon_type', 1)
                
                # إضافة تأثير بصري أو صوتي
                try:
                    if w_type == 1 and snd_shoot: snd_shoot.play()
                    elif w_type == 2 and snd_shotgun: snd_shotgun.play()
                    elif w_type == 3 and snd_pick: snd_pick.play()
                except: pass
                
                # إذا كنت المضيف، فإن weapon_manager لديه الرصاصات بالفعل ولا حاجة لإضافتها يدوياً لـ bullets_dict
                # (تم استخدام weapon_manager.fire محلياً عند استلام الحدث إذا أردنا محاكاة دقيقة، لكن الحدث shoot_weapon يكفي للعرض)
                
                # تحديث: يمكننا استدعاء weapon_manager.fire هنا لتوليد رصاصة "بصرية" ومنطقية
                if weapon_manager:
                     # نحتاج نقطة هدف تقريبية بناءً على السرعة
                     target_x = bx + vx * 100
                     target_y = by + vy * 100
                     weapon_manager.fire(bx, by, target_x, target_y)
                    
            elif msg_type == "level_change" and not is_host:
                new_level = data["level"]
                door_pos = data["door_pos"]
                print(f"CLIENT: Received level change! Moving to level {new_level}")
                reset_level_multiplayer(new_level) 
                level_door = LevelDoor(door_pos[0], door_pos[1], new_level)
                
            elif data.get("type") == "full_game_state" and not is_host:
                gs = data["game_state"]
                
                new_zombie_ids = set()
                for z_data in gs.get('zombies', []):
                    z_id = z_data['id']
                    new_zombie_ids.add(z_id)
                    if z_id in enemies_dict:
                        enemies_dict[z_id].lerp_target_x = z_data['x']
                        enemies_dict[z_id].lerp_target_y = z_data['y']
                        enemies_dict[z_id].hp = z_data['hp']
                    else:
                        enemies_dict[z_id] = Zombie.from_dict(z_data)
                ids_to_remove = set(enemies_dict.keys()) - new_zombie_ids
                for z_id in ids_to_remove: enemies_dict.pop(z_id, None)

                # (Bullet Sync Removed - Using Events)

                new_pickup_ids = set()
                for p_data in gs.get('pickups', []):
                    p_id = p_data['id']
                    new_pickup_ids.add(p_id)
                    if p_id not in pickups_dict:
                        pickups_dict[p_id] = Pickup.from_dict(p_data)
                ids_to_remove = set(pickups_dict.keys()) - new_pickup_ids
                for p_id in ids_to_remove: pickups_dict.pop(p_id, None)

                new_crate_ids = set()
                for c_data in gs.get('crates', []):
                    c_id = c_data['id']
                    new_crate_ids.add(c_id)
                    if c_id not in crates_dict:
                        crates_dict[c_id] = SpeedCrate.from_dict(c_data)
                ids_to_remove = set(crates_dict.keys()) - new_crate_ids
                for c_id in ids_to_remove: crates_dict.pop(c_id, None)
                
                door_data = gs.get('door')
                if door_data and not level_door:
                    level_door = LevelDoor(door_data['x'], door_data['y'], door_data['level'])
                if level_door and door_data:
                    level_door.active = door_data['active']
                
                kills = gs.get('total_kills', kills)
                
            elif data.get("type") == "player_action":
                action_type = data.get("action_type")
                action_data = data.get("action_data")
                
                if action_type == "shoot" and is_host:
                    # المضيف ينشئ الرصاصة عبر weapon_manager (تمت معالجتها أعلاه أو سيتم معالجتها تلقائياً)
                    pass
                
                # 🔥 معالجة إطلاق النار من اللاعب الآخر (إصلاح مشكلة العميل لا يستطيع قتل الزومبي)
                elif action_type == "shoot_weapon" and weapon_manager:
                    # معالجة إطلاق النار من اللاعبين الآخرين (للمضيف والعملاء)
                    # نتأكد أننا لا نكرر رصاصتنا الخاصة
                    sender_id = data.get("player_id")
                    if sender_id != player_id:
                        ad = action_data or {}
                        bx, by = ad.get('x', 0), ad.get('y', 0)
                        vx, vy = ad.get('vx', 1), ad.get('vy', 0)
                        w_type = ad.get('weapon_type', 1)
                        
                        # تبديل السلاح مؤقتاً لإطلاق النوع الصحيح
                        original_weapon = weapon_manager.current_weapon
                        if w_type == 1:
                            weapon_manager.switch_weapon(WeaponType.PISTOL)
                        elif w_type == 2:
                            weapon_manager.switch_weapon(WeaponType.SHOTGUN)
                        elif w_type == 3:
                            weapon_manager.switch_weapon(WeaponType.GRENADE)
                        
                        # إجبار إعادة تعيين cooldown للسماح بالإطلاق
                        weapon_manager.fire_cooldown = 0
                        
                        # إطلاق النار (يتم تحديده كمضيف أو عميل بناءً على المنطق في الأسفل)
                        target_x = bx + vx * 100
                        target_y = by + vy * 100
                        weapon_manager.fire(bx, by, target_x, target_y)
                        
                        # إعادة السلاح الأصلي
                        weapon_manager.switch_weapon(original_weapon)
                        
                        # تشغيل الصوت
                        try:
                            if w_type == 1 and snd_shoot: snd_shoot.play()
                            elif w_type == 2 and snd_shotgun: snd_shotgun.play()
                            elif w_type == 3 and snd_pick: snd_pick.play()
                        except: pass
                        
                        role = "HOST" if is_host else "CLIENT"
                        print(f"{role}: Spawning remote bullet from P{sender_id}")
                
                elif action_type == "touched_door" and is_host:
                    print("HOST: Received 'touched_door' from client.")
                    if level_door and level_door.active and level_no < 6:
                        print("HOST: Client touched door, advancing level.")
                        reset_level_multiplayer(level_no + 1)

    if is_host:
        door_x, door_y = find_door_location(walls, p.x, p.y, WORLD_W, WORLD_H)
        level_door = LevelDoor(door_x, door_y, level_no)
        game_state.door = level_door
        
    def spawn_enemy():
        if not is_host or not game_state: return
        
        params = LEVELS.get(level_no, LEVELS[6])
        for _ in range(20):
            side = random.choice(["top","bottom","left","right"])
            m = 64
            if side == "top": x = random.randint(m, WORLD_W - m); y = m
            elif side == "bottom": x = random.randint(m, WORLD_W - m); y = WORLD_H - m - 48
            elif side == "left": x = m; y = random.randint(m, WORLD_H - m)
            else: x = WORLD_W - m - 48; y = random.randint(m, WORLD_H - m)

            z = Zombie(float(x), float(y), level_no, game_state.next_zombie_id)
            z_id = game_state.next_zombie_id
            game_state.next_zombie_id += 1
            
            if collide_rect_list(z.rect, walls): continue
            if not far_from_player(p.x, p.y, z.x, z.y, min_dist=300.0): continue
            
            enemies_dict[z_id] = z
            game_state.zombies = enemies_dict
            return

    def fire_weapon():
        """إطلاق النار باستخدام النظام الجديد"""
        if not weapon_manager or is_dead: return
        
        # الاتجاه
        dir_map = {"right": (1,0), "left": (-1,0), "up": (0,-1), "down": (0,1)}
        vx, vy = dir_map.get(p.facing, (1,0))
        bx = p.x + p.w/2
        by = p.y + p.h/2
        
        # محاولة الإطلاق
        if weapon_manager.can_fire():
            target_x = bx + vx * 100
            target_y = by + vy * 100
            
            # إطلاق النار محلياً
            new_bullets = weapon_manager.fire(bx, by, target_x, target_y)
            
            # تشغيل الصوت
            w_stats = WEAPON_STATS[weapon_manager.current_weapon]
            snd_name = w_stats["sound"]
            # سنقوم بتحميل الصوت إذا لم يكن محملاً
            try:
                # محاولة تحميل الصوت ديناميكياً أو استخدام الأصوات الموجودة
                if weapon_manager.current_weapon == WeaponType.PISTOL and snd_shoot:
                    snd_shoot.play()
                elif weapon_manager.current_weapon == WeaponType.SHOTGUN and snd_shotgun:
                    snd_shotgun.play()
                elif weapon_manager.current_weapon == WeaponType.GRENADE and snd_pick: # صوت مؤقت للقنبلة
                    snd_pick.play()
            except:
                pass
            
            # إرسال إلى الشبكة
            # سنرسل فقط نوع السلاح والموقع
            send_player_action("shoot_weapon", {
                'x': bx, 'y': by, 
                'vx': vx, 'vy': vy,
                'weapon_type': weapon_manager.current_weapon.value
            })
            
            # 🔥 (HOST ONLY)
            # weapon_manager يدير الرصاصات الآن. لا حاجة لـ bullets_dict.
            # سيتم تحديث weapon_manager في الحلقة الرئيسية ومعالجة التصادمات منها.

    # دالة توافق legacy
    def fire_pistol():
        fire_weapon()

    # دالة توافق legacy
    def fire_shotgun():
        if weapon_manager:
            if weapon_manager.current_weapon != WeaponType.SHOTGUN:
                weapon_manager.switch_weapon(WeaponType.SHOTGUN)
            fire_weapon()

    def respawn_player():
        """إعادة إحياء اللاعب الميت"""
        nonlocal is_dead, death_timer, health, p
        
        if not is_dead or not can_respawn:
            return False
            
        # البحث عن موقع آمن بعيد عن الزومبي
        for _ in range(20):
            spawn_x, spawn_y = find_free_spawn(walls, WORLD_W, WORLD_H, p.w, p.h)
            
            # التحقق من أن الموقع بعيد عن الزومبي
            safe_location = True
            for enemy in enemies_dict.values():
                if math.sqrt((spawn_x - enemy.x)**2 + (spawn_y - enemy.y)**2) < 200:
                    safe_location = False
                    break
            
            if safe_location:
                p.x, p.y = spawn_x, spawn_y
                health = hearts_max // 2  # إعادة بجزء من الصحة
                is_dead = False
                death_timer = 0.0
                print(f"🎮 Player {player_id} respawned!")
                return True
        
        return False

    def check_all_players_dead():
        """التحقق إذا مات جميع اللاعبين (2 لاعبين فقط أو لاعب واحد)"""
        if not is_dead:
            return False  # اللاعب الحالي ليس ميتاً
        
        # 🔥 إذا كان اللاعب وحده (لا يوجد لاعبون آخرون متصلون)
        # ومات = Game Over مباشرة
        if len(other_players) == 0:
            print(f"💀 Player {player_id} died while playing SOLO! Game Over!")
            return True  # أنت الوحيد وميت = Game Over
        
        # التحقق من اللاعب الآخر (في حالة لعبة ثنائية)
        for other_id, other_data in other_players.items():
            is_other_dead = other_data.get("is_dead", False)
            print(f"🔍 Check: Player {player_id} is dead. Player {other_id} is_dead={is_other_dead}")
            
            if is_other_dead:
                print(f"✅ Both players are DEAD! Showing Game Over...")
                return True
            else:
                return False  # اللاعب الآخر لا يزال حياً
        
        
        return False

    def switch_spectate_target():
        """تبديل الهدف في وضع المشاهدة"""
        nonlocal spectating_player_id
        
        if not is_dead or len(other_players) == 0:
            return
            
        other_ids = list(other_players.keys())
        if not other_ids:
            return
            
        if spectating_player_id is None:
            spectating_player_id = other_ids[0]
        else:
            current_index = other_ids.index(spectating_player_id) if spectating_player_id in other_ids else -1
            next_index = (current_index + 1) % len(other_ids)
            spectating_player_id = other_ids[next_index]

    running = True
    while running:
        dt = clock.get_time() / 1000.0
        dt = min(dt, 0.1) 
        
        current_time = time.time()
        params = LEVELS.get(level_no, LEVELS[6]) 
        goal_kills = params["goal_kills"]

        if current_time - last_send_time > SEND_INTERVAL:
            send_player_data()
            flush_pending_actions()
            if is_host:
                send_full_game_state()
            last_send_time = current_time
        
        process_received_data()

        # Events
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return None
            
            # 🔥 معالجة الدردشة أولاً (لها الأولوية عند الكتابة)
            if chat_system and chat_system.is_typing():
                chat_result = chat_system.handle_event(e)
                if chat_result:
                    # إرسال رسالة الدردشة عبر الشبكة بالتنسيق الصحيح
                    # chat_result يحتوي على {"type": "chat", "message": {...}}
                    # نحتاج إرسال البيانات بالتنسيق الذي تتوقعه receive_message
                    network.send_game_state(chat_result)
                continue  # تجاهل المدخلات الأخرى عند الكتابة
            
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: return "menu"
                if e.key == pygame.K_h: show_hud = not show_hud
                
                # 🔥 تبديل الأسلحة (1, 2, 3)
                if weapon_manager and not is_dead:
                    if e.key == pygame.K_1:
                        weapon_manager.switch_weapon(WeaponType.PISTOL)
                        print("🔫 Switched to Pistol")
                    elif e.key == pygame.K_2:
                        weapon_manager.switch_weapon(WeaponType.SHOTGUN)
                        print("🔫 Switched to Shotgun")
                    elif e.key == pygame.K_3:
                        weapon_manager.switch_weapon(WeaponType.GRENADE)
                        print("💣 Switched to Grenade")
                
                # 🔥 فتح الدردشة (T)
                if e.key == pygame.K_t and chat_system:
                    chat_system.toggle_input()
                
                # 🔥 تبديل الخريطة (M)
                if e.key == pygame.K_m and minimap_system:
                    minimap_system.toggle()
                    show_minimap = minimap_system.visible
                
                if e.key == pygame.K_SPACE and not is_dead: fire_pistol()
                if e.key == pygame.K_TAB and is_dead: switch_spectate_target()
                if e.key == pygame.K_r and is_dead and can_respawn and death_timer >= RESPAWN_TIME: respawn_player()
                
            if e.type == pygame.MOUSEBUTTONDOWN and not is_dead:
                if e.button == 1: fire_pistol()
                elif e.button == 3: fire_shotgun()

        if pistol_cd > 0: pistol_cd -= dt
        if shotgun_cd > 0: shotgun_cd -= dt
        if damage_cd > 0: damage_cd -= dt

        # 🔥 تحديث مؤقت الموت
        if is_dead:
            death_timer += dt

        # 🔥 التحكم في اللاعب (فقط إذا لم يكن ميتاً)
        if not is_dead:
            keys = pygame.key.get_pressed()
            right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
            left = keys[pygame.K_q] or keys[pygame.K_a] or keys[pygame.K_LEFT]
            down = keys[pygame.K_s] or keys[pygame.K_DOWN]
            up = keys[pygame.K_z] or keys[pygame.K_w] or keys[pygame.K_UP]
            dx = int(bool(right)) - int(bool(left))
            dy = int(bool(down)) - int(bool(up))

            if dx or dy:
                if abs(dx) > abs(dy): p.facing = "right" if dx > 0 else "left"
                elif dy != 0: p.facing = "down" if dy > 0 else "up"

            if boost_t > 0:
                boost_t -= dt; p.speed = base_speed * boost_mult
            else: p.speed = base_speed

            spd = p.speed
            new_rect_x = pygame.Rect(int(p.x + dx * spd), int(p.y), p.w, p.h)
            if (0 <= new_rect_x.left) and (new_rect_x.right <= WORLD_W) and not collide_rect_list(new_rect_x, walls):
                p.x = new_rect_x.x
            new_rect_y = pygame.Rect(int(p.x), int(p.y + dy * spd), p.w, p.h)
            if (0 <= new_rect_y.top) and (new_rect_y.bottom <= WORLD_H) and not collide_rect_list(new_rect_y, walls):
                p.y = new_rect_y.y

        player_center = pygame.Vector2(p.x + p.w/2, p.y + p.h/2)

        if is_host:
            spawn_t += dt
            if spawn_t >= params["spawn_every"] and len(enemies_dict) < params["max_alive"] and game_state.total_kills < goal_kills:
                spawn_t = 0.0
                if len(enemies_dict) < params["max_alive"]:
                    spawn_enemy()

            # 🔥 إعادة توازن ظهور الصناديق والذخيرة (50% لكل منهما)
            pk_timer += dt
            if pk_timer >= 4.0:
                pk_timer = 0.0
                # 50% احتمالية ظهور
                if random.random() < 0.5:
                    kind = random.choice(["medkit", "shotgun_ammo", "grenade_ammo", "shotgun_ammo"])
                    for _ in range(20):
                        x = random.randint(80, WORLD_W-80)
                        y = random.randint(80, WORLD_H-80)
                        pk_id = game_state.next_pickup_id
                        
                        pk = Pickup(x, y, kind, pk_id)
                        if not collide_rect_list(pk.rect, walls):
                            game_state.next_pickup_id += 1
                            pickups_dict[pk_id] = pk
                            game_state.pickups = pickups_dict
                            break

            crate_t += dt
            if crate_t >= 4.0:
                crate_t = 0.0
                # 50% احتمالية ظهور
                if len(crates_dict) < 4 and random.random() < 0.5:
                    for _ in range(20):
                        x = random.randint(70, WORLD_W-70)
                        y = random.randint(70, WORLD_H-70)
                        c_id = game_state.next_crate_id
                        
                        cr = SpeedCrate(x, y, c_id)
                        if not collide_rect_list(cr.rect, walls):
                            game_state.next_crate_id += 1
                            crates_dict[c_id] = cr
                            game_state.crates = crates_dict
                            break

            # 🔥 (ZOMBIE & BULLET UPDATE REMOVED - will be handled below)
            # فقط تحديث الزومبي هنا (بدون الرصاص)
            all_zombies_list = list(enemies_dict.values())
            ai_update_counter += 1
            frame_mod = ai_update_counter % 3
            
            for i, en in enumerate(all_zombies_list):
                if i % 3 == frame_mod:
                    nearby = []
                    for other in all_zombies_list:
                        if other is en: continue
                        if (other.x - en.x)**2 + (other.y - en.y)**2 < 10000:
                            nearby.append(other)
                    en.update_host(player_center, walls, dt, nearby)
                else:
                    en.bob_t += dt * 6.0 

            # تنظيف الزومبي الميتين
            dead_zombie_ids = set()
            # (سيتم تحديث القتلى في حلقة التصادم بالأسفل)
            
            # game_state.zombies = enemies_dict (سيتم التحديث لاحقاً)

        else:
            # --- (العميل) ---
            for en in enemies_dict.values():
                en.update_client(dt) 
            
            # (bullets_dict Removed)

        # (تفعيل الباب - 'kills' متزامن من المضيف)
        if level_door and not level_door.active and kills >= goal_kills:
            print(f"PLAYER {player_id}: Door Active! Kills: {kills}/{goal_kills}")
            level_door.activate()
            if is_host and game_state:
                game_state.door.activate() 
            if snd_door: snd_door.play()

        # 🔥 --- منطق الباب التعاوني مع نظام الموت ---
        if level_door and level_door.active and not is_dead and p.rect.colliderect(level_door.rect):
            if level_no < 6:
                if is_host:
                    # (المضيف يلمس الباب، يغير المستوى فوراً)
                    print("HOST: Touched door, advancing level.")
                    reset_level_multiplayer(level_no + 1)
                else:
                    # (العميل يلمس الباب، يرسل إشعاراً للمضيف)
                    print("CLIENT: Touched door, notifying host.")
                    send_player_action("touched_door", {})
            else:
                # 🔥 إكمال جميع المستويات - شاشة النصر
                total_kills = score // 15  # تقدير تقريبي
                choice = show_multiplayer_victory_screen(screen, clock, score, total_kills)
                
                if choice == "restart":
                    return "start"
                elif choice == "menu":
                    return "menu"
                elif choice == "quit":
                    return None
                else:
                    return "menu"

        # 🔥 --- نظام الضرر والموت ---
        if damage_cd <= 0.0 and not is_dead:
            for en in enemies_dict.values():
                if p.rect.colliderect(en.rect):
                    damage = en.damage
                    health -= damage
                    damage_cd = DAMAGE_IFRAMES
                    if snd_hurt: snd_hurt.play()
                    
                    push_force = 0.08 + (en.level * 0.02)
                    p.x = clamp(p.x - (player_center.x - en.x) * push_force, 0, WORLD_W - p.w)
                    p.y = clamp(p.y - (player_center.y - en.y) * push_force, 0, WORLD_H - p.h)
                    
                    if health <= 0:
                        is_dead = True
                        death_timer = 0.0
                        print(f"💀 Player {player_id} died!")
                        
                        # 🔥 إرسال فوري متعدد لحالة الموت للاعبين الآخرين (للتأكد من الاستلام)
                        for _ in range(3):
                            send_player_data()
                            flush_pending_actions()
                        
                        # 🔥 التحقق إذا مات جميع اللاعبين
                        if check_all_players_dead():
                            print("💀 All players died! Game Over!")
                            choice = show_multiplayer_game_over_screen(screen, clock, score, level_no)
                            
                            if choice == "restart":
                                return "start"
                            elif choice == "menu":
                                return "menu"
                            elif choice == "quit":
                                return None
                            else:
                                return "menu"
                    break

        # 🔥 --- نظام المشاهدة - تحديث الكاميرا ---
        if is_dead:
            # إذا كان اللاعب ميتاً، اتبع اللاعب الذي تتم مشاهدته
            if spectating_player_id and spectating_player_id in other_players:
                other_data = other_players[spectating_player_id]
                fake_rect = pygame.Rect(int(other_data["x"]), int(other_data["y"]), p.w, p.h)
                cam.follow(fake_rect)
            else:
                # إذا لم يكن هناك هدف للمشاهدة، اتبع اللاعب الخاص بك (لرؤية جثته)
                cam.follow(p.rect)
            
            # 🔥 --- تحقق مستمر: إذا مات جميع اللاعبين أثناء المشاهدة ---
            # هذا يصلح المشكلة حيث كان اللاعب الأول الميت لا يرى شاشة Game Over
            if check_all_players_dead():
                print("💀 All players died! (Detected while spectating) Game Over!")
                choice = show_multiplayer_game_over_screen(screen, clock, score, level_no)
                
                if choice == "restart":
                    return "start"
                elif choice == "menu":
                    return "menu"
                elif choice == "quit":
                    return None
                else:
                    return "menu"
        else:
            # إذا كان اللاعب حياً، اتبع اللاعب الخاص به
            cam.follow(p.rect)

        for pk in pickups_dict.values():
            if pk.alive and not is_dead and p.rect.colliderect(pk.rect):  # 🔥 اللاعب الميت لا يمكنه جمع الأشياء
                pk.alive = False 
                if pk.kind == "medkit":
                    health = min(hearts_max, health + 1)
                elif pk.kind == "shotgun_ammo":
                    if weapon_manager:
                        weapon_manager.add_ammo(WeaponType.SHOTGUN, 5)
                        shotgun_ammo += 3 # (Legacy support)
                elif pk.kind == "grenade_ammo":
                    if weapon_manager:
                        weapon_manager.add_ammo(WeaponType.GRENADE, 2)
                
                # صوت الالتقاط
                if snd_pick: snd_pick.play()

        for cr in crates_dict.values():
            if cr.alive and (not cr.open) and not is_dead and p.rect.colliderect(cr.rect):  # 🔥 اللاعب الميت لا يمكنه جمع الصناديق
                boost_t = boost_time
                if snd_crate: snd_crate.play()
                cr.trigger_open(show_time=0.40) 

        if level_door: level_door.update(dt)

        for pfx in blood_fx: pfx.update(dt)
        blood_fx = [pfx for pfx in blood_fx if pfx.alive]
        if len(blood_fx) > 50: blood_fx = blood_fx[-50:]

        # -------- Render (الرسم) --------
        
        # 🔥 رسم الخلفية الديناميكية
        draw_level_background(screen, level_no, cam, BG_EFFECTS)

        # رسم الجدران
        for r in walls:
            sr = cam.apply_rect(r)
            pygame.draw.rect(screen, (92,55,24), sr, border_radius=8)
            pygame.draw.rect(screen, (40,26,15), sr, width=2, border_radius=8)
            inner = sr.inflate(-6, -6)
            if inner.w > 0 and inner.h > 0:
                pygame.draw.rect(screen, (26,90,58), inner, width=1, border_radius=6)

        for pfx in blood_fx: pfx.draw(screen, cam)
        
        for pk in pickups_dict.values(): pk.draw(screen, cam)
        for cr in crates_dict.values(): cr.draw(screen, cam)
        for en in enemies_dict.values(): en.draw(screen, cam)
        
        for other_id, other_data in other_players.items():
            other_x, other_y = cam.apply_xy(other_data["x"], other_data["y"])
            other_facing = other_data.get('facing', 'right')
            
            sprite_name = f"player_{other_facing}.png"
            other_sprite = load_image_to_height(sprite_name, 56)
            
            if other_sprite:
                screen.blit(other_sprite, (other_x, other_y))
            else:
                other_color = (255, 100, 100)
                pygame.draw.rect(screen, other_color, (other_x, other_y, p.w, p.h), border_radius=4)
            
            # 🔥 عرض حالة اللاعب (حي/ميت)
            status_text = "DEAD" if other_data.get("is_dead", False) else f"HP:{other_data.get('health', '?')}"
            status_color = (255, 0, 0) if other_data.get("is_dead", False) else (0, 255, 0)
            
            font = pygame.font.Font(None, 20)
            name_text = font.render(f"P{other_id} ({status_text})", True, (255, 255, 255))
            name_bg = pygame.Surface((name_text.get_width() + 8, name_text.get_height() + 4), pygame.SRCALPHA)
            name_bg.fill((0, 0, 0, 180))
            screen.blit(name_bg, (other_x - 4, other_y - 28))
            screen.blit(name_text, (other_x, other_y - 26))
            
            border_color = (255, 200, 0) if not other_data.get("is_dead", False) else (100, 100, 100)
            border_rect = pygame.Rect(other_x - 2, other_y - 2, p.w + 4, p.h + 4)
            pygame.draw.rect(screen, border_color, border_rect, width=2, border_radius=4)

        if level_door:
            level_door.draw(screen, cam)

        # 🔥 رسم اللاعب الخاص (مع تأثير الشفافية إذا كان ميتاً) - مع المظهر
        dx, dy = cam.apply_xy(p.x, p.y)
        
        # 🔥 رسم حلقة ملونة تحت الشخصية (مؤشر المظهر)
        skin_color = getattr(p, 'skin_color', (80, 200, 255))
        center_x = int(dx + p.w // 2)
        center_y = int(dy + p.h + 2)
        pygame.draw.ellipse(screen, (0, 0, 0), (center_x - 18, center_y - 4, 36, 8))
        pygame.draw.ellipse(screen, skin_color, (center_x - 16, center_y - 3, 32, 6))
        
        # 🔥 استخدام الصورة الملونة
        if hasattr(p, 'tinted_sprites') and p.tinted_sprites.get(p.facing):
            spr = p.tinted_sprites.get(p.facing)
        else:
            spr = getattr(p, "sprites", {}).get(p.facing)
        
        if spr:
            if damage_cd > 0 and int(pygame.time.get_ticks() * 0.02) % 2 == 0: pass
            else: 
                if is_dead:
                    # 🔥 جعل اللاعب الميت شفافاً
                    spr_copy = spr.copy()
                    spr_copy.set_alpha(128)
                    screen.blit(spr_copy, (dx, dy))
                else:
                    screen.blit(spr, (dx, dy))
        else:
            # 🔥 رسم مربع بلون المظهر
            color = skin_color if damage_cd <= 0 else (255, 220, 120)
            rect = pygame.Rect(dx, dy, p.w, p.h)
            if is_dead:
                # رسم مع شفافية
                surf = pygame.Surface((p.w, p.h), pygame.SRCALPHA)
                pygame.draw.rect(surf, (*color, 128), surf.get_rect(), border_radius=8)
                screen.blit(surf, (dx, dy))
            else:
                pygame.draw.rect(screen, color, rect, border_radius=8)
                # حدود داكنة
                darker = (max(0, skin_color[0]-50), max(0, skin_color[1]-50), max(0, skin_color[2]-50))
                pygame.draw.rect(screen, darker, rect, width=3, border_radius=8)
                # عيون
                eye_y = int(dy + p.h * 0.35)
                pygame.draw.circle(screen, (255, 255, 255), (int(dx + p.w * 0.35), eye_y), 4)
                pygame.draw.circle(screen, (255, 255, 255), (int(dx + p.w * 0.65), eye_y), 4)
                pygame.draw.circle(screen, (0, 0, 0), (int(dx + p.w * 0.35), eye_y), 2)
                pygame.draw.circle(screen, (0, 0, 0), (int(dx + p.w * 0.65), eye_y), 2)

        # 🔥 رسم الرصاصات (فقط الحية)
        # (يتم الرسم بواسطة weapon_manager.draw_bullets في الأعلى)
        pass

        # HUD
        if show_hud:
            hud_x, hud_y = 16, 14
            draw_shadow_text(screen, f"Kills: {kills}/{goal_kills}", (hud_x, hud_y), size=28, color=(0,0,0))
            draw_shadow_text(screen, f"Level: {level_no}", (hud_x+210, hud_y), size=28, color=(0,0,0))
            draw_shadow_text(screen, f"Score: {score}", (hud_x+370, hud_y), size=28, color=(0,0,0))
            draw_shadow_text(screen, f"Shotgun: {shotgun_ammo}", (hud_x+520, hud_y), size=28, color=(0,0,0))
            
            role = "HOST" if is_host else "CLIENT"
            role_color = (255, 255, 0) if is_host else (100, 200, 255)
            draw_shadow_text(screen, f"[{role}]", (hud_x+720, hud_y), size=24, color=role_color)
            
            # 🔥 عرض حالة اللاعب
            if is_dead:
                status_text = "SPECTATING"
                status_color = (255, 0, 0)
                if spectating_player_id:
                    status_text = f"SPECTATING P{spectating_player_id}"
                
                # 🔥 عرض مؤقت إعادة الظهور
                if can_respawn and death_timer >= RESPAWN_TIME:
                    respawn_text = "Press R to Respawn"
                    draw_shadow_text(screen, respawn_text, (hud_x, hud_y + 90), size=24, color=(0, 255, 0))
                else:
                    respawn_time = max(0, RESPAWN_TIME - death_timer)
                    respawn_text = f"Respawn in: {respawn_time:.1f}s"
                    draw_shadow_text(screen, respawn_text, (hud_x, hud_y + 90), size=24, color=(255, 255, 0))
                    
                draw_shadow_text(screen, "Press TAB to switch target", (hud_x, hud_y + 120), size=20, color=(200, 200, 200))
            else:
                status_text = "ALIVE"
                status_color = (0, 255, 0)
            
            draw_shadow_text(screen, status_text, (hud_x+850, hud_y), size=24, color=status_color)
            
            if level_door and level_door.active:
                draw_shadow_text(screen, "DOOR ACTIVE!", (hud_x, hud_y + 60), size=24, color=(255, 255, 0))
            
            hx = hud_x
            hy = hud_y + 34
            for i in range(hearts_max):
                if heart_img:
                    img = heart_img.copy()
                    if i >= health: img.fill((255,255,255,120), special_flags=pygame.BLEND_RGBA_MULT)
                    screen.blit(img, (hx + i*(img.get_width()+6), hy))
                else:
                    r = pygame.Rect(hx + i*28, hy, 22, 22)
                    col = (230,60,60) if i < health else (120,60,60)
                    pygame.draw.rect(screen, col, r, border_radius=5)
                    pygame.draw.rect(screen, (30,30,30), r, width=1, border_radius=5)
            
            if other_players and len(other_players) < 5:
                y_offset = 90
                for other_id, other_data in other_players.items():
                    player_status = "DEAD" if other_data.get("is_dead", False) else "ALIVE"
                    status_color = (255, 0, 0) if other_data.get("is_dead", False) else (0, 255, 0)
                    player_info = f"P{other_id}: {player_status} | HP {other_data.get('health', '?')} | Score {other_data.get('score', 0)}"
                    draw_shadow_text(screen, player_info, (hud_x, hud_y + y_offset), size=22, color=status_color)
                    y_offset += 28
            
            conn_status = "Connected" if network.connected else "Disconnected"
            conn_color = (0, 255, 0) if network.connected else (255, 0, 0)
            draw_text(screen, conn_status, (WINDOW_W-120, 10), size=18, color=conn_color)
            draw_text(screen, f"{int(clock.get_fps())} FPS", (WINDOW_W-120, 30), size=18, color=(220,220,220))
            
            if level_door and not is_dead:  # 🔥 فقط اللاعبون الأحياء يرون سهم التوجيه
                level_door.draw_navigation(screen, p.x, p.y)
            
            # 🔥 === رسم الأنظمة الجديدة ===
            
            # رسم واجهة الأسلحة
            if weapon_manager:
                weapon_manager.draw_hud(screen, 16, WINDOW_H - 80)
                # رسم رصاصات الأسلحة والانفجارات
                weapon_manager.draw_bullets(screen, (int(cam.x), int(cam.y)))
                weapon_manager.draw_explosions(screen, (int(cam.x), int(cam.y)))
            
            # 🔥 رسم الخريطة المصغرة
            if minimap_system and show_minimap:
                minimap_system.draw(
                    screen,
                    (p.x, p.y),
                    other_players,
                    enemies_dict,
                    level_door,
                    walls
                )
        
        # 🔥 رسم الدردشة (دائماً مرئية)
        if chat_system:
            chat_system.update(dt)
            chat_system.draw(screen)
        
        # 🔥 تحديث نظام الأسلحة
        if weapon_manager:
            # 🔥 (FIX) معالجة تصادم الرصاص قبل التحديث (لمنع اختراق الزومبي)
            dead_zombie_ids = set()
            
            for b in weapon_manager.bullets:
                if not b.alive:
                    continue
                    
                # 1. تصادم مع الجدران (للجميع لتجنب اختراق الجدران بصرياً)
                b_rect = pygame.Rect(int(b.x)-4, int(b.y)-4, 8, 8)
                if collide_rect_list(b_rect, walls):
                    b.alive = False
                    continue
                
                # 2. تصادم مع الزومبي (للجميع - بصرياً ومنطقياً)
                # السماح للعميل أيضاً بحساب الإصابة لقتل الرصاصة بصرياً
                for z_id, en in list(enemies_dict.items()):
                    if en.hp > 0 and en.rect.colliderect(b_rect):
                        # 🔥 إيقاف الرصاصة فوراً عند الإصابة (للكل)
                        b.alive = False
                        
                        # تشغيل الصوت والمؤثرات (للكل)
                        if snd_hit: snd_hit.play()
                        
                        bx, by = en.x + en.w/2, en.y + en.h/2
                        for _ in range(3): blood_fx.append(BloodParticle(bx, by))

                        # (للمضيف فقط - Authority) تطبيق الضرر وحساب النقاط
                        if is_host:
                            # حساب الضرر من نوع السلاح
                            damage = getattr(b, 'damage', 1)
                            en.hp -= damage
                            
                            # الموت
                            if en.hp <= 0:
                                dead_zombie_ids.add(z_id)
                                # تحديث الإحصائيات
                                if game_state:
                                    kills = game_state.total_kills + 1
                                    game_state.total_kills = kills
                                score += 10 + (en.level * 5)
                                
                                # تأثير الدم الكبير عند الموت
                                for _ in range(5): blood_fx.append(BloodParticle(bx, by))
                        
                        # 🔥 الخروج من حلقة الزومبي (رصاصة واحدة = زومبي واحد)
                        break
            
            # تنظيف الزومبي الميتين (للمضيف)
            if is_host and dead_zombie_ids:
                for z_id in dead_zombie_ids:
                    enemies_dict.pop(z_id, None)
                if game_state:
                    game_state.zombies = enemies_dict
            
            # 🔥 تحديث نظام الأسلحة بعد التصادم
            explosions = weapon_manager.update(dt)

            # معالجة الانفجارات (ضرر الزومبي)
            for ex, ey, radius, damage in explosions:
                for z_id, zombie in list(enemies_dict.items()):
                    if hasattr(zombie, 'hp') and zombie.hp > 0:
                        dist = math.sqrt((zombie.x - ex)**2 + (zombie.y - ey)**2)
                        if dist < radius:
                            dmg = int(damage * (1 - dist/radius))
                            zombie.hp -= dmg
                            if zombie.hp <= 0:
                                kills += 1
                                score += 15
                                if is_host:
                                    dead_zombie_ids.add(z_id)
            
            # تنظيف إضافي للزومبي من الانفجارات
            if is_host and dead_zombie_ids:
                for z_id in dead_zombie_ids:
                    enemies_dict.pop(z_id, None)
                if game_state:
                    game_state.zombies = enemies_dict

        pygame.display.flip()
        clock.tick(FPS)

    return "menu"