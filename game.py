
from __future__ import annotations
import os
import math
import random
import pygame

from util import (
    draw_text, draw_shadow_text, clamp, COLORS,
    load_image_to_height, load_sound, Button
)
from walls import create_walls_for_level, collide_rect_list
from bullet import Bullet
from characters import Player

# ---------------- Window / World ----------------
WINDOW_W, WINDOW_H = 1280, 720
FPS = 60
BG_COLOR = (166, 98, 42)  # Arena brown

# عالم كبير يتحرّك بداخله اللاعب
WORLD_W, WORLD_H = 3200, 2400

# ------------- Music (optional) -------------
def _maybe_music():
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        bg = os.path.join("sounds", "background_music.wav")
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

    def follow(self, target_rect: pygame.Rect, lerp: float = 0.15):
        tx = target_rect.centerx - self.view_w // 2
        ty = target_rect.centery - self.view_h // 2
        self.x += (tx - self.x) * lerp
        self.y += (ty - self.y) * lerp
        self.x = clamp(self.x, 0, max(0, self.world_w - self.view_w))
        self.y = clamp(self.y, 0, max(0, self.world_h - self.view_h))

    def apply_rect(self, r: pygame.Rect) -> pygame.Rect:
        return r.move(-int(self.x), -int(self.y))

    def apply_xy(self, x: float, y: float) -> tuple[int, int]:
        return int(x - self.x), int(y - self.y)

# ---------- Animated menu background ----------
class MenuBackground:
    def __init__(self, screen: pygame.Surface):
        self.W, self.H = screen.get_size()
        self.layers = [
            {"y": int(self.H * 0.72), "speed": 10, "color": (20, 22, 28)},
            {"y": int(self.H * 0.78), "speed": 18, "color": (18, 20, 26)},
            {"y": int(self.H * 0.85), "speed": 28, "color": (14, 16, 22)},
        ]
        self._build_skyline()
        self.fog = [self._make_fog(0.18), self._make_fog(0.12)]
        self.fog_x = [0.0, -self.W * 0.4]
        self.fog_v = [12.0, 18.0]
        self.beams = [
            {"x": self.W * 0.24, "w": 220, "ang": 0.0, "vang": 0.25, "alpha": 65},
            {"x": self.W * 0.72, "w": 240, "ang": 0.7, "vang": -0.2, "alpha": 55},
        ]
        z = (load_image_to_height("zombie_left.png", 140) or
             load_image_to_height("zombie_right.png", 140) or
             load_image_to_height("zombie_up.png", 140) or
             load_image_to_height("zombie_down.png", 140))
        self.ghost_img = None
        if z:
            g = pygame.Surface(z.get_size(), pygame.SRCALPHA)
            g.blit(z, (0, 0))
            g.fill((255, 255, 255, 60), special_flags=pygame.BLEND_RGBA_MULT)
            self.ghost_img = g
        self.ghosts = self._spawn_ghosts(6) if self.ghost_img else []
        self.vignette = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        pygame.draw.rect(self.vignette, (0, 0, 0, 120), self.vignette.get_rect())
        pygame.draw.rect(self.vignette, (0, 0, 0, 0), (60, 60, self.W - 120, self.H - 120))

    def _build_skyline(self):
        rng = random.Random(42)
        for L in self.layers:
            yb = L["y"]; blocks = []; x = -80
            while x < self.W + 80:
                w = rng.randint(40, 120); h = rng.randint(60, 220)
                blocks.append(pygame.Rect(x, yb - h, w, h))
                x += w + rng.randint(12, 28)
            L["blocks"] = blocks; L["offset"] = 0.0

    def _make_fog(self, alpha: float) -> pygame.Surface:
        s = pygame.Surface((int(self.W * 1.4), int(self.H * 0.5)), pygame.SRCALPHA)
        rng = random.Random(7 if alpha < 0.15 else 9)
        for _ in range(220):
            r = rng.randint(40, 120)
            x = rng.randint(-50, s.get_width() - 50)
            y = rng.randint(0, s.get_height() - 30)
            a = int(255 * alpha * rng.uniform(0.4, 1.0))
            pygame.draw.circle(s, (220, 220, 230, a), (x, y), r)
        return s

    def _spawn_ghosts(self, n: int):
        rng = random.Random(11); res = []
        for _ in range(n):
            res.append({"x": rng.randint(-60, self.W - 60),
                        "y": rng.randint(30, int(self.H * 0.55)),
                        "vx": rng.choice([-1, 1]) * rng.uniform(8, 20)})
        return res

    def draw(self, screen: pygame.Surface, dt: float):
        W, H = self.W, self.H
        for i in range(H):
            t = i / max(H - 1, 1)
            c = (int(14 + 20*(1-t)), int(16 + 24*(1-t)), int(22 + 34*(1-t)))
            pygame.draw.line(screen, c, (0, i), (W, i))
        for L in self.layers:
            L["offset"] = (L["offset"] - L["speed"] * dt) % (W + 40)
            ox = -L["offset"]
            for r in L["blocks"]:
                rr = r.move(ox, 0)
                pygame.draw.rect(screen, L["color"], rr)
                pygame.draw.rect(screen, L["color"], rr.move(W + 40, 0))
        for b in self.beams:
            b["ang"] += b["vang"] * dt
            ang = math.sin(b["ang"]) * 0.6
            poly = [(b["x"] - 12, self.layers[0]["y"] - 4),
                    (b["x"] + 12, self.layers[0]["y"] - 4),
                    (b["x"] + math.cos(ang) * b["w"], self.layers[0]["y"] - 240 + math.sin(ang) * 90)]
            cone = pygame.Surface((W, H), pygame.SRCALPHA)
            pygame.draw.polygon(cone, (255, 255, 210, b["alpha"]), poly)
            screen.blit(cone, (0, 0), special_flags=pygame.BLEND_PREMULTIPLIED)
        for i, fog in enumerate(self.fog):
            self.fog_x[i] = (self.fog_x[i] + self.fog_v[i] * dt) % fog.get_width()
            x = -self.fog_x[i]; y = int(H * 0.35) + i * 28
            screen.blit(fog, (x, y)); screen.blit(fog, (x + fog.get_width(), y))
        if self.ghost_img:
            for g in self.ghosts:
                g["x"] += g["vx"] * dt
                if g["x"] < -120: g["x"] = W + 40
                if g["x"] > W + 40: g["x"] = -120
                screen.blit(self.ghost_img, (int(g["x"]), int(g["y"])))
        screen.blit(self.vignette, (0, 0))

# ---------------- Menus ----------------
def main_menu(screen: pygame.Surface, clock: pygame.time.Clock, version: str) -> str | None:
    bg = MenuBackground(screen)
    cx, cy = WINDOW_W // 2, WINDOW_H // 2
    start_btn = Button(pygame.Rect(cx - 120, cy - 26, 240, 52), "Start")
    howto_btn = Button(pygame.Rect(cx - 120, cy + 40, 240, 44), "How to Play")
    quit_btn  = Button(pygame.Rect(cx - 120, cy + 90, 240, 44), "Quit")

    mode = "menu"  # "menu" | "howto"
    while True:
        dt = clock.get_time() / 1000.0
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return None
            if e.type == pygame.KEYDOWN:
                if mode == "menu":
                    if e.key == pygame.K_RETURN: return "start"
                    if e.key == pygame.K_ESCAPE: return None
                else:
                    if e.key == pygame.K_ESCAPE: mode = "menu"
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if mode == "menu":
                    if start_btn.hit(e.pos): return "start"
                    if howto_btn.hit(e.pos):  mode = "howto"
                    if quit_btn.hit(e.pos):   return None
                else:
                    mode = "menu"

        bg.draw(screen, dt)
        title = "Zombie Shooter" if not version else f"Zombie Shooter — {version}"
        draw_text(screen, title, (36, 28), size=34, color=(225, 231, 239))
        if mode == "menu":
            start_btn.draw(screen); howto_btn.draw(screen); quit_btn.draw(screen)
        else:
            _draw_howto_panel(screen)

        pygame.display.flip()
        clock.tick(FPS)

def _draw_howto_panel(screen: pygame.Surface):
    rect = pygame.Rect(WINDOW_W//2 - 360, WINDOW_H//2 - 180, 720, 320)
    pygame.draw.rect(screen, (20, 20, 26, 220), rect, border_radius=10)
    pygame.draw.rect(screen, (230, 230, 240), rect, width=2, border_radius=10)
    draw_shadow_text(screen, "How to Play", (rect.x+20, rect.y+16), size=32, color=(200,200,200))
    y = rect.y + 70
    lines = [
    "Move: Z/Q/S/D or WASD or Arrow Keys",
    "Shoot: Space or Left Mouse (Pistol) | Right Mouse (Shotgun if ammo)",
    "Toggle HUD: H | Pause/Back: ESC",
    "Open Speed Chests for a temporary speed boost!",
    "Goal: Kill enough zombies to advance (Levels 1..4).",
    ]
    for line in lines:
        draw_text(screen, line, (rect.x+20, y), size=22, color=(235,235,235))
        y += 36
    draw_text(screen, "Press ESC to return", (rect.x+20, rect.y+rect.h-42), size=20, color=(210,210,210))

# ---------------- Helpers ----------------
def normalized(x: float, y: float) -> tuple[float, float]:
    L = math.hypot(x, y) or 1.0
    return x / L, y / L

# ---------------- Speed Crate ----------------
CRATE_H = 52  # ↞ تحكم سريع بحجم الصندوق

class SpeedCrate:
    """صندوق سرعة: مغلق -> يُفتح عند الالتقاط -> يظهر مفتوحًا لحظات ثم يختفي."""
    def __init__(self, x: float, y: float):
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
            cx, cy = r.center
            bolt = [(cx, cy-12), (cx+6, cy), (cx-1, cy), (cx+1, cy+14), (cx-8, cy)]
            pygame.draw.polygon(screen, (255, 230, 80), bolt)

# ---------------- Zombie (improved sizes) ----------------
ZOMBIE_SIZES = {
    "runner": 84,   # سريع/نحيف
    "walker": 96,   # قياسي
    "tank":   112,  # ثقيل
}

def raycast_clear(a: pygame.Vector2, b: pygame.Vector2, walls: list[pygame.Rect], step: float = 18.0) -> bool:
    """تحقق خط رؤية بسيط داخل عالم كبير."""
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
    """3 أنواع مع حركة محسّنة وفصل بسيط وتتبّع حسب Line-of-Sight."""
    def __init__(self, kind: str, x: float, y: float):
        self.kind = kind  # "walker" | "runner" | "tank"

        # أحجام وسرعات/HP متوازنة
        size = ZOMBIE_SIZES.get(kind, 96)
        if kind == "runner":
            self.speed = 2.2; self.hp = 1
        elif kind == "tank":
            self.speed = 1.1; self.hp = 3
        else:
            self.speed = 1.6; self.hp = 2
        self.size = size

        self.sprite = (
            load_image_to_height("zombie_right.png", self.size) or
            load_image_to_height("zombie_left.png",  self.size) or
            load_image_to_height("zombie_up.png",    self.size) or
            load_image_to_height("zombie_down.png",  self.size)
        )
        if self.sprite:
            self.w, self.h = self.sprite.get_width(), self.sprite.get_height()
        else:
            self.w, self.h = int(self.size*0.75), int(self.size*0.75)

        self.x, self.y = float(x), float(y)
        self.bob_t = random.random() * 100.0
        self.waypoint: pygame.Vector2 | None = None
        self.way_timer = 0.0

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def _pick_waypoint(self, W: int, H: int, walls: list[pygame.Rect]):
        for _ in range(16):
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

    def update(self, player_pos: pygame.Vector2, walls: list[pygame.Rect], dt: float, neighbors: list["Zombie"]):
        spd = self.speed * 60.0 * dt

        # Separation: إبعاد بسيط عن الجيران
        sep_x = sep_y = 0.0
        for other in neighbors:
            if other is self: continue
            dx = self.x - other.x; dy = self.y - other.y
            dsq = dx*dx + dy*dy
            if dsq < 1e-4: continue
            if dsq < (56*56):
                inv = 1.0 / math.sqrt(dsq)
                sep_x += dx * inv
                sep_y += dy * inv

        center = pygame.Vector2(self.x + self.w/2, self.y + self.h/2)
        can_see = raycast_clear(center, player_pos, walls)

        if can_see:
            target = player_pos
            self.waypoint = None; self.way_timer = 0.0
        else:
            if (self.waypoint is None) or (self.way_timer <= 0):
                self._pick_waypoint(WORLD_W, WORLD_H, walls)
            target = self.waypoint if self.waypoint is not None else player_pos
            self.way_timer = max(0.0, self.way_timer - dt)

        dir_x = dir_y = 0.0
        if target is not None:
            dx = target.x - center.x; dy = target.y - center.y
            L = math.hypot(dx, dy) or 1.0
            dir_x, dir_y = dx / L, dy / L

        dir_x += 0.6 * sep_x
        dir_y += 0.6 * sep_y
        norm = math.hypot(dir_x, dir_y) or 1.0
        dir_x /= norm; dir_y /= norm

        self._slide_move(dir_x * spd, 0, walls)
        self._slide_move(0, dir_y * spd, walls)

        self.bob_t += dt * 6.0

    def draw(self, screen: pygame.Surface, cam: Camera):
        dx, dy = cam.apply_xy(self.x, self.y)
        if self.sprite:
            off = math.sin(self.bob_t) * 1.5
            screen.blit(self.sprite, (dx, dy + off))
        else:
            color = (70, 180, 90) if self.kind == "runner" else ((90, 160, 220) if self.kind == "walker" else (180, 100, 60))
            r = pygame.Rect(dx, dy, self.w, self.h)
            pygame.draw.rect(screen, color, r, border_radius=6)
            pygame.draw.rect(screen, (30, 30, 30), r, width=2, border_radius=6)

# ---------------- Blood FX ----------------
class BloodParticle:
    """جزيئات دم تتلاشى تدريجيًا."""
    def __init__(self, x: float, y: float):
        self.x = float(x); self.y = float(y)
        ang = random.uniform(0, 2*math.pi)
        sp  = random.uniform(40, 160)
        self.vx = math.cos(ang) * sp
        self.vy = math.sin(ang) * sp
        self.r  = random.uniform(2.5, 5.0)
        self.life = random.uniform(0.5, 1.1)  # المدة
        self.age  = 0.0
        self.col  = (170, 20, 20)

    def update(self, dt: float):
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        # تباطؤ بسيط
        self.vx *= (0.96)
        self.vy *= (0.96)

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

# ---------------- Levels (difficulty) ----------------
LEVELS = {
    1: {"goal_kills": 8,  "spawn_every": 1.6, "max_alive": 6,  "mix": {"walker": 0.75, "runner": 0.20, "tank": 0.05}},
    2: {"goal_kills": 14, "spawn_every": 1.25,"max_alive": 9,  "mix": {"walker": 0.60, "runner": 0.30, "tank": 0.10}},
    3: {"goal_kills": 22, "spawn_every": 1.00,"max_alive": 12, "mix": {"walker": 0.45, "runner": 0.40, "tank": 0.15}},
    4: {"goal_kills": 32, "spawn_every": 0.90,"max_alive": 14, "mix": {"walker": 0.35, "runner": 0.45, "tank": 0.20}},
}

def _choose_kind(mix: dict[str, float]) -> str:
    r = random.random(); acc = 0.0
    for k, p in mix.items():
        acc += p
        if r <= acc:
            return k
    return "walker"

# ---------------- Utilities ----------------
def find_free_spawn(walls: list[pygame.Rect], W: int, H: int, w: int, h: int, attempts: int = 80, margin: int = 80):
    for _ in range(attempts):
        x = random.randint(margin, W - margin - w)
        y = random.randint(margin, H - margin - h)
        r = pygame.Rect(x, y, w, h)
        if not collide_rect_list(r, walls):
            return float(x), float(y)
    return float(W//2 - w//2), float(H//2 - h//2)

def far_from_player(px: float, py: float, x: float, y: float, min_dist: float = 280.0) -> bool:
    return (px - x) ** 2 + (py - y) ** 2 >= (min_dist ** 2)

# ---------------- Game Loop ----------------
def run_game(screen: pygame.Surface, clock: pygame.time.Clock, version: str = "") -> str | None:
    _maybe_music()

    # أصوات (اختيارية)
    snd_shoot   = load_sound("shotgun-146188.mp3")
    snd_shotgun = load_sound("shotgun-146188.mp3")
    snd_hit     = load_sound("hit.wav")
    snd_pick    = load_sound("pickup.wav")
    snd_hurt    = load_sound("hurt.wav")
    snd_crate   = load_sound("crate.wav")
    
    level_no = 1
    score = 0
    kills = 0

    # --- Health / Hearts ---
    hearts_max = 4        # ← عدد القلوب الكلي
    health     = hearts_max
    heart_img  = load_image_to_height("heart.png", 24)  # اختياري
    damage_cd  = 0.0      # invincibility frames بعد الضربة
    DAMAGE_IFRAMES = 1.0  # ثانية حصانة

    show_hud = True

    # أسلحة
    shotgun_ammo = 8
    pistol_cool = 0.18
    shotgun_cool = 0.70
    pistol_cd = 0.0
    shotgun_cd = 0.0

    # Boost السرعة
    base_speed = 5.5
    boost_mult = 1.8
    boost_time = 4.0
    boost_t = 0.0

    
    walls = create_walls_for_level(level_no, WORLD_W, WORLD_H, tile=64)

    p_spawn_x, p_spawn_y = find_free_spawn(walls, WORLD_W, WORLD_H, 36, 36)
    p = Player(x=p_spawn_x, y=p_spawn_y, speed=base_speed)  # characters.Player

    # كاميرا
    cam = Camera(WORLD_W, WORLD_H, WINDOW_W, WINDOW_H)
    cam.follow(p.rect)  # موضعة أولية

    # كائنات
    enemies: list[Zombie] = []
    bullets: list[Bullet] = []
    pickups: list["Pickup"] = []
    crates:  list[SpeedCrate] = []
    blood_fx: list[BloodParticle] = []

    # Pickups (medkit / ammo)
    class Pickup:
        def __init__(self, x: float, y: float, kind: str):
            self.x, self.y, self.kind = float(x), float(y), kind  # "medkit" | "shotgun_ammo"
            self.w, self.h = 32, 32
            self.alive = True
        @property
        def rect(self) -> pygame.Rect: return pygame.Rect(int(self.x), int(self.y), self.w, self.h)
        def draw(self, screen: pygame.Surface, cam: Camera):
            if not self.alive: return
            r = pygame.Rect(*cam.apply_xy(self.x, self.y), self.w, self.h)
            if self.kind == "medkit":
                pygame.draw.rect(screen, (200,40,40), r, border_radius=6)
                pygame.draw.line(screen, (235,235,235), (r.centerx, r.top+6), (r.centerx, r.bottom-6), 3)
                pygame.draw.line(screen, (235,235,235), (r.left+6, r.centery), (r.right-6, r.centery), 3)
            else:
                pygame.draw.rect(screen, (230,200,60), r, border_radius=6)
                pygame.draw.rect(screen, (120,90,20), r, width=2, border_radius=6)

    # مؤقتات
    spawn_t = 0.0
    pk_timer = 0.0
    crate_t = 0.0

    def reset_level(new_level: int):
        nonlocal enemies, bullets, pickups, kills, walls, spawn_t, pk_timer, crate_t, boost_t, health, damage_cd
        enemies = []; bullets = []; pickups = []; crates.clear(); blood_fx.clear()
        kills = 0; spawn_t = 0.0; pk_timer = 0.0; crate_t = 0.0; boost_t = 0.0
        health = hearts_max; damage_cd = 0.0
        walls[:] = create_walls_for_level(new_level, WORLD_W, WORLD_H, tile=64)
        px, py = find_free_spawn(walls, WORLD_W, WORLD_H, p.w, p.h)
        p.x, p.y = px, py
        cam.follow(p.rect, lerp=1.0)  # قفز للموضع الجديد

    def spawn_enemy():
        params = LEVELS[level_no]
        for _ in range(40):
            side = random.choice(["top","bottom","left","right","random"])
            m = 64
            if side == "top":
                x = random.randint(m, WORLD_W - m); y = m
            elif side == "bottom":
                x = random.randint(m, WORLD_W - m); y = WORLD_H - m - 48
            elif side == "left":
                x = m; y = random.randint(m, WORLD_H - m)
            elif side == "right":
                x = WORLD_W - m - 48; y = random.randint(m, WORLD_H - m)
            else:
                x = random.randint(m, WORLD_W - m); y = random.randint(m, WORLD_H - m)

            kind = _choose_kind(params["mix"])
            z = Zombie(kind, float(x), float(y))
            if collide_rect_list(z.rect, walls):   # لا يولد داخل جدار
                continue
            if not far_from_player(p.x, p.y, z.x, z.y, min_dist=300.0):  # بعيد عن اللاعب
                continue
            enemies.append(z)
            return

    def fire_pistol():
        nonlocal pistol_cd
        if pistol_cd > 0: return
        pistol_cd = pistol_cool
        dir_map = {"right": (1,0), "left": (-1,0), "up": (0,-1), "down": (0,1)}
        vx, vy = dir_map.get(p.facing, (1,0))
        vx, vy = normalized(vx, vy)
        bx = p.x + p.w/2; by = p.y + p.h/2
        bullets.append(Bullet(bx, by, vx, vy, speed=480.0, lifetime=1.1))
        if snd_shoot: snd_shoot.play()

    def fire_shotgun():
        nonlocal shotgun_cd, shotgun_ammo
        if shotgun_cd > 0 or shotgun_ammo <= 0: return
        shotgun_cd = shotgun_cool
        shotgun_ammo -= 1
        dir_map = {"right": (1,0), "left": (-1,0), "up": (0,-1), "down": (0,1)}
        vx, vy = dir_map.get(p.facing, (1,0))
        bx = p.x + p.w/2; by = p.y + p.h/2
        spread = [ -0.35, -0.18, 0.0, 0.18, 0.35 ]
        for ang in spread:
            rx = vx*math.cos(ang) - vy*math.sin(ang)
            ry = vx*math.sin(ang) + vy*math.cos(ang)
            rx, ry = normalized(rx, ry)
            bullets.append(Bullet(bx, by, rx, ry, speed=540.0, lifetime=0.9))
        if snd_shotgun: snd_shotgun.play()

    def spawn_pickup():
        kind = random.choice(["medkit", "shotgun_ammo"])
        for _ in range(20):
            x = random.randint(80, WORLD_W-80)
            y = random.randint(80, WORLD_H-80)
            pk = Pickup(x, y, kind)
            if not collide_rect_list(pk.rect, walls):
                pickups.append(pk); break

    def spawn_crate():
        if len(crates) >= 4:
            return
        for _ in range(20):
            x = random.randint(70, WORLD_W-70)
            y = random.randint(70, WORLD_H-70)
            cr = SpeedCrate(x, y)
            if not collide_rect_list(cr.rect, walls):
                crates.append(cr); break

    running = True
    while running:
        dt = clock.get_time() / 1000.0
        params = LEVELS[level_no]
        goal_kills = params["goal_kills"]

                # -------- Events --------
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return None
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return "menu"
                if e.key == pygame.K_h:
                    show_hud = not show_hud
                if e.key == pygame.K_SPACE:
                    # Space → Pistol
                    fire_pistol()
                    if snd_shoot:
                        snd_shoot.set_volume(0.5)
                        snd_shoot.play()
            if e.type == pygame.MOUSEBUTTONDOWN:
                if e.button == 1:   # Left click → Pistol
                    fire_pistol()
                    if snd_shoot:
                            snd_shoot.set_volume(0.5)
                            snd_shoot.play()
                elif e.button == 3: # Right click → Shotgun
                    fire_shotgun()
                    if snd_shotgun:
                        snd_shotgun.set_volume(0.6)
                        snd_shotgun.play()


        if pistol_cd > 0: pistol_cd -= dt
        if shotgun_cd > 0: shotgun_cd -= dt
        if damage_cd > 0:  damage_cd -= dt

        # -------- INPUT (ZQSD + WASD + ARROWS) --------
        keys = pygame.key.get_pressed()
        right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        left  = keys[pygame.K_q] or keys[pygame.K_a] or keys[pygame.K_LEFT]
        down  = keys[pygame.K_s] or keys[pygame.K_DOWN]
        up    = keys[pygame.K_z] or keys[pygame.K_w] or keys[pygame.K_UP]
        dx = int(bool(right)) - int(bool(left))
        dy = int(bool(down))  - int(bool(up))

        if dx or dy:
            if abs(dx) > abs(dy):
                p.facing = "right" if dx > 0 else "left"
            elif dy != 0:
                p.facing = "down" if dy > 0 else "up"

        if boost_t > 0:
            boost_t -= dt; p.speed = base_speed * boost_mult
        else:
            p.speed = base_speed

        spd = p.speed
        new_rect_x = pygame.Rect(int(p.x + dx * spd), int(p.y), p.w, p.h)
        if (0 <= new_rect_x.left) and (new_rect_x.right <= WORLD_W) and not collide_rect_list(new_rect_x, walls):
            p.x = new_rect_x.x
        new_rect_y = pygame.Rect(int(p.x), int(p.y + dy * spd), p.w, p.h)
        if (0 <= new_rect_y.top) and (new_rect_y.bottom <= WORLD_H) and not collide_rect_list(new_rect_y, walls):
            p.y = new_rect_y.y

        spawn_t += dt
        if spawn_t >= params["spawn_every"] and len(enemies) < params["max_alive"] and kills < goal_kills:
            spawn_t = 0.0
            for _ in range(random.randint(1, 2)):
                if len(enemies) < params["max_alive"]:
                    spawn_enemy()

        pk_timer += dt
        if pk_timer >= 1.3:
            pk_timer = 0.0
            if random.random() < (0.008 if level_no == 1 else 0.006):
                spawn_pickup()

        crate_t += dt
        if crate_t >= 5.0:
            crate_t = 0.0
            if random.random() < 0.55:
                spawn_crate()

        player_center = pygame.Vector2(p.x + p.w/2, p.y + p.h/2)
        for i, en in enumerate(enemies):
            nearby = [other for j, other in enumerate(enemies)
                      if j != i and (abs(other.x - en.x) < 72 and abs(other.y - en.y) < 72)]
            en.update(player_center, walls, dt, nearby)

        dead_indices = set()
        for b in list(bullets):
            b.update(dt)
            if collide_rect_list(pygame.Rect(int(b.x)-3, int(b.y)-3, 6, 6), walls):
                b.alive = False
                continue
            if b.alive:
                for idx, en in enumerate(enemies):
                    if en.rect.collidepoint(int(b.x), int(b.y)):
                        en.hp -= 1
                        b.alive = False
                        if snd_hit: snd_hit.play()
                        if en.hp <= 0:
                            dead_indices.add(idx)
                            kills += 1
                            score += 10
                            ex, ey = en.x + en.w/2, en.y + en.h/2
                            for _ in range(16):
                                blood_fx.append(BloodParticle(ex, ey))
                        break
        bullets = [b for b in bullets if b.alive]
        if dead_indices:
            enemies = [en for i, en in enumerate(enemies) if i not in dead_indices]

        if damage_cd <= 0.0:
            if any(p.rect.colliderect(en.rect) for en in enemies):
                health -= 1
                damage_cd = DAMAGE_IFRAMES
                if snd_hurt: snd_hurt.play()
                p.x = clamp(p.x - (player_center.x - enemies[0].x) * 0.08, 0, WORLD_W - p.w)
                p.y = clamp(p.y - (player_center.y - enemies[0].y) * 0.08, 0, WORLD_H - p.h)
                if health <= 0:
                    _draw_center_panel(screen, "You Died!", "Press ENTER to return to Menu")
                    pygame.display.flip()
                    if _wait_enter_or_quit(clock): return "menu"

        for pk in pickups:
            if pk.alive and p.rect.colliderect(pk.rect):
                pk.alive = False
                if pk.kind == "medkit":
                    health = min(hearts_max, health + 1)
                else:
                    shotgun_ammo += 3
                if snd_pick: snd_pick.play()
        pickups = [pk for pk in pickups if pk.alive]

        for cr in crates:
            if cr.alive and (not cr.open) and p.rect.colliderect(cr.rect):
                boost_t = boost_time
                if snd_crate: snd_crate.play()
                cr.trigger_open(show_time=0.40)
        for cr in crates:
            cr.update(dt)
        crates = [cr for cr in crates if cr.alive]

        # -------- Level Complete (based on kills) --------
        if kills >= goal_kills:
            if level_no < 4:
                _draw_center_panel(screen, f"Level {level_no} Complete!", "Press ENTER for next level")
            else:
                _draw_center_panel(screen, f"Level {level_no} Complete!", "All levels done! ENTER to Menu")
            pygame.display.flip()
            if _wait_enter_or_quit(clock):
                if level_no < 4:
                    level_no += 1
                    reset_level(level_no)
                else:
                    return "menu"

        # -------- Update Blood FX --------
        for pfx in blood_fx:
            pfx.update(dt)
        blood_fx = [pfx for pfx in blood_fx if pfx.alive]

        # -------- Camera follow --------
        cam.follow(p.rect)

        # -------- Render (apply camera) --------
        screen.fill(BG_COLOR)

        for r in walls:
            sr = cam.apply_rect(r)
            pygame.draw.rect(screen, (92,55,24), sr, border_radius=8)
            pygame.draw.rect(screen, (40,26,15), sr, width=2, border_radius=8)
            inner = sr.inflate(-6, -6)
            if inner.w > 0 and inner.h > 0:
                pygame.draw.rect(screen, (26,90,58), inner, width=1, border_radius=6)

       
        for pfx in blood_fx:
            pfx.draw(screen, cam)

       
        for pk in pickups: pk.draw(screen, cam)
        for cr in crates:  cr.draw(screen, cam)
        for en in enemies: en.draw(screen, cam)

        # Player
        spr = getattr(p, "sprites", {}).get(p.facing)
        dx, dy = cam.apply_xy(p.x, p.y)
        if spr:
          
            if damage_cd > 0 and int(pygame.time.get_ticks() * 0.02) % 2 == 0:
                pass  # تخطي الرسم لإحساس الوميض
            else:
                screen.blit(spr, (dx, dy))
        else:
            color = (80, 200, 255) if damage_cd <= 0 else (255, 220, 120)
            pygame.draw.rect(screen, color, pygame.Rect(dx, dy, p.w, p.h), border_radius=4)

        # Bullets
        for b in bullets:
            bx, by = cam.apply_xy(b.x, b.y)
            pygame.draw.circle(screen, (245, 235, 225), (bx, by), 4)

        # HUD
        if show_hud:
            hud_x, hud_y = 16, 14
            draw_shadow_text(screen, f"Kills: {kills}/{goal_kills}", (hud_x, hud_y), size=28, color=(0,0,0))
            draw_shadow_text(screen, f"Level: {level_no}", (hud_x+210, hud_y), size=28, color=(0,0,0))
            draw_shadow_text(screen, f"Shotgun Ammo: {shotgun_ammo}", (hud_x+370, hud_y), size=28, color=(0,0,0))
            # Hearts
            hx = hud_x; hy = hud_y + 34
            for i in range(hearts_max):
                if heart_img:
                    img = heart_img.copy()
                    if i >= health:
                        img.fill((255,255,255,120), special_flags=pygame.BLEND_RGBA_MULT)
                    screen.blit(img, (hx + i*(img.get_width()+6), hy))
                else:
                    r = pygame.Rect(hx + i*28, hy, 22, 22)
                    col = (230,60,60) if i < health else (120,60,60)
                    pygame.draw.rect(screen, col, r, border_radius=5)
                    pygame.draw.rect(screen, (30,30,30), r, width=1, border_radius=5)
            draw_text(screen, f"{int(clock.get_fps()):02d} FPS", (WINDOW_W-100, 10), size=18, color=(220,220,220))

        pygame.display.flip()
        clock.tick(FPS)

# -------- Small UI helpers --------
def _draw_center_panel(screen: pygame.Surface, title: str, subtitle: str):
    rect = pygame.Rect(WINDOW_W//2 - 260, WINDOW_H//2 - 120, 520, 220)
    pygame.draw.rect(screen, (20,20,26,220), rect, border_radius=10)
    pygame.draw.rect(screen, (230,230,240), rect, width=2, border_radius=10)
    draw_shadow_text(screen, title, (rect.x+20, rect.y+24), size=34, color=(200,200,200))
    draw_text(screen, subtitle, (rect.x+20, rect.y+90), size=24, color=(235,235,235))

def _wait_enter_or_quit(clock: pygame.time.Clock) -> bool:
    """ينتظر ENTER أو إغلاق النافذة. يرجع True عند ENTER."""
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return True
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                return True
        clock.tick(60)

# -------- Compatibility wrapper for your main.py --------
def run_demo_level(screen: pygame.Surface, clock: pygame.time.Clock, version: str = "") -> str | None:
    """حفاظًا على التوافق مع main.py الحالي."""
    return run_game(screen, clock, version)