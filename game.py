# game.py


from __future__ import annotations
import os
import math
import random
import pygame
from util import (
    draw_text, draw_shadow_text, clamp,
    load_image, load_image_to_height, load_sound, Button
)
from walls import create_demo_walls, draw_walls, collide_rect_list


# ---------- Constants ----------
WINDOW_W, WINDOW_H = 1280, 720
FPS = 60
ARENA_BROWN = (166, 98, 42)


# ===================== Animated Menu Background =====================
class MenuBackground:
    """
    Animated menu background:
      - Night sky gradient
      - 3 skyline parallax layers
      - Moving fog bands
      - Sweeping light beams
      - Optional semi-transparent zombie silhouettes if assets exist
    """
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

        z = (
            load_image_to_height("zombie_left.png", 140) or
            load_image_to_height("zombie_right.png", 140) or
            load_image_to_height("zombie_up.png", 140) or
            load_image_to_height("zombie_down.png", 140)
        )
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
            y_base = L["y"]
            blocks = []
            x = -80
            while x < self.W + 80:
                w = rng.randint(40, 120)
                h = rng.randint(60, 220)
                blocks.append(pygame.Rect(x, y_base - h, w, h))
                x += w + rng.randint(12, 28)
            L["blocks"] = blocks
            L["offset"] = 0.0

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
        rng = random.Random(11)
        res = []
        for _ in range(n):
            res.append({
                "x": rng.randint(-60, self.W - 60),
                "y": rng.randint(30, int(self.H * 0.55)),
                "vx": rng.choice([-1, 1]) * rng.uniform(8, 20),
            })
        return res

    def draw(self, screen: pygame.Surface, dt: float):
        W, H = self.W, self.H

        for i in range(H):
            t = i / max(H - 1, 1)
            c = (int(14 + 20 * (1 - t)), int(16 + 24 * (1 - t)), int(22 + 34 * (1 - t)))
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
            poly = [
                (b["x"] - 12, self.layers[0]["y"] - 4),
                (b["x"] + 12, self.layers[0]["y"] - 4),
                (b["x"] + math.cos(ang) * b["w"], self.layers[0]["y"] - 240 + math.sin(ang) * 90),
            ]
            cone = pygame.Surface((W, H), pygame.SRCALPHA)
            pygame.draw.polygon(cone, (255, 255, 210, b["alpha"]), poly)
            screen.blit(cone, (0, 0), special_flags=pygame.BLEND_PREMULTIPLIED)

        for i, fog in enumerate(self.fog):
            self.fog_x[i] = (self.fog_x[i] + self.fog_v[i] * dt) % fog.get_width()
            x = -self.fog_x[i]
            y = int(H * 0.35) + i * 28
            screen.blit(fog, (x, y))
            screen.blit(fog, (x + fog.get_width(), y))

        if self.ghost_img:
            for g in self.ghosts:
                g["x"] += g["vx"] * dt
                if g["x"] < -120: g["x"] = W + 40
                if g["x"] > W + 40: g["x"] = -120
                screen.blit(self.ghost_img, (int(g["x"]), int(g["y"])))

        screen.blit(self.vignette, (0, 0))


# ===================== Minimal Main Menu + How to Play =====================
def main_menu(screen: pygame.Surface, clock: pygame.time.Clock, version: str) -> str | None:
   
    bg = MenuBackground(screen)
    start_btn = Button(pygame.Rect(WINDOW_W // 2 - 120, WINDOW_H // 2 - 26, 240, 52), "Start")
    howto_btn = Button(pygame.Rect(WINDOW_W // 2 - 120, WINDOW_H // 2 + 40, 240, 44), "How to Play")
    quit_btn  = Button(pygame.Rect(WINDOW_W // 2 - 120, WINDOW_H // 2 + 90, 240, 44), "Quit")

    showing_help = False

    while True:
        dt = clock.get_time() / 1000.0
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return None
            if e.type == pygame.KEYDOWN:
                if not showing_help:
                    if e.key == pygame.K_RETURN: return "start"
                    if e.key == pygame.K_ESCAPE: return None
                else:
                    if e.key == pygame.K_ESCAPE: showing_help = False
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if not showing_help:
                    if start_btn.hit(e.pos): return "start"
                    if howto_btn.hit(e.pos):  showing_help = True
                    if quit_btn.hit(e.pos):   return None
                else:
                    showing_help = False

        bg.draw(screen, dt)
        title = "Zombie Shooter" if not version else f"Zombie Shooter — {version}"
        draw_text(screen, title, (36, 28), size=34, color=(225, 231, 239))

        if not showing_help:
            start_btn.draw(screen)
            howto_btn.draw(screen)
            quit_btn.draw(screen)
        else:
            _draw_howto_panel(screen)

        pygame.display.flip()
        clock.tick(FPS)


def _draw_howto_panel(screen: pygame.Surface):
    """Elegant ASCII-only help panel (matches the screenshot style)."""
    rect = pygame.Rect(WINDOW_W // 2 - 380, WINDOW_H // 2 - 190, 760, 340)

    dim = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 110))
    screen.blit(dim, (0, 0))

    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    panel.fill((18, 18, 24, 235))  # dark semi-transparent
    pygame.draw.rect(panel, (232, 232, 240), panel.get_rect(), width=2, border_radius=12)
    inner = panel.get_rect().inflate(-14, -14)
    pygame.draw.rect(panel, (60, 60, 68, 70), inner, width=0, border_radius=10)

    
    notch = pygame.Surface((60, 24), pygame.SRCALPHA)
    pygame.draw.polygon(notch, (242, 242, 242, 210), [(0, 24), (44, 24), (16, 0)])
    panel.blit(notch, (18, panel.get_height() - 30))

   
    screen.blit(panel, rect.topleft)

    
    draw_shadow_text(screen, "How to Play", (rect.x + 22, rect.y + 18), size=36, color=(220, 220, 228))

    y = rect.y + 78
    lines = [
        "Move: Z/Q/S/D (French) or WASD or Arrow Keys",
        "Shoot: Space or Left Mouse (Pistol) | Right Mouse (Shotgun if ammo)",
        "Pause/Back: ESC",
        "Open Speed Chests for a temporary speed boost!",
        "Goal: Kill enough zombies to advance (Levels 1..4).",
    ]
    for line in lines:
        draw_text(screen, line, (rect.x + 22, y), size=22, color=(235, 235, 235))
        y += 36

    # Footer hint
    draw_text(screen, "Press ESC to return", (rect.x + 22, rect.y + rect.h - 44),
              size=20, color=(210, 210, 210))


# ===================== Demo Level =====================
def _maybe_music():
    """Optional background music (sounds/background_music.wav)."""
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        bg = os.path.join("sounds", "background_music.wav")
        if os.path.isfile(bg):
            pygame.mixer.music.load(bg)
            pygame.mixer.music.set_volume(0.35)
            pygame.mixer.music.play(-1)
    except Exception:
        pass


def _load_player_sprites(target_h: int = 56) -> dict[str, pygame.Surface | None]:
    return {
        "up":    load_image_to_height("player_up.png", target_h),
        "down":  load_image_to_height("player_down.png", target_h),
        "left":  load_image_to_height("player_left.png", target_h),
        "right": load_image_to_height("player_right.png", target_h),
    }


def _load_zombie_sprite(target_h: int = 90) -> pygame.Surface | None:
    
    for n in ("zombie_right.png", "zombie_left.png", "zombie_up.png", "zombie_down.png"):
        s = load_image_to_height(n, target_h)
        if s: return s
    return None


def _spawn_zombies(w: int, count: int = 6, top_band: tuple[int, int] = (20, 180)) -> list[dict]:
    
    spr = _load_zombie_sprite()
    zs = []
    for _ in range(count):
        x = random.randint(220, w - 220)
        y = random.randint(top_band[0], top_band[1])
        speed = random.uniform(0.7, 1.2)  # أسرع قليلًا كي يبان
        zw, zh = (spr.get_width(), spr.get_height()) if spr else (60, 60)
        zs.append({
            "x": float(x), "y": float(y),
            "w": zw, "h": zh,
            "sprite": spr,
            "speed": speed,
            "dir": 1
        })
    return zs


def run_demo_level(screen: pygame.Surface, clock: pygame.time.Clock, version: str = "") -> str | None:
    WIDTH, HEIGHT = screen.get_size()
    _maybe_music()

    # Walls
    walls = create_demo_walls(WIDTH, HEIGHT, tile=64)

    # Player (centered)
    p_sprites = _load_player_sprites(target_h=56)
    if p_sprites["down"]:
        p_w, p_h = p_sprites["down"].get_width(), p_sprites["down"].get_height()
    else:
        p_w, p_h = 36, 36
    px, py = WIDTH // 2 - p_w // 2, HEIGHT // 2 - p_h // 2
    p_speed = 5
    facing = "down"

    # Footstep sound disabled by default (you can enable later)
    footstep = None
    foot_cd = 0.0

    zombies = _spawn_zombies(WIDTH, count=6, top_band=(20, 180))

    score = 0.0
    level_no = 1
    health = 5
    heart_img = load_image_to_height("heart.png", 22)  # optional

    show_hud = True

    running = True
    while running:
        dt = clock.get_time() / 1000.0

        for e in pygame.event.get():
            if e.type == pygame.QUIT: return None
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: return "menu"
                if e.key == pygame.K_h:      show_hud = not show_hud  # toggle HUD

        keys = pygame.key.get_pressed()
        right = keys[pygame.K_d]  # D → right
        left  = keys[pygame.K_q]  # Q → left
        down  = keys[pygame.K_s]  # S → down
        up    = keys[pygame.K_z]  # Z → up

        dx = int(right) - int(left)
        dy = int(down)  - int(up)

        if dx or dy:
            if abs(dx) > abs(dy):
                facing = "right" if dx > 0 else "left"
            elif dy != 0:
                facing = "down" if dy > 0 else "up"
            if footstep and foot_cd <= 0:
                try: footstep.play()
                except Exception: pass
                foot_cd = 0.16
        if foot_cd > 0: foot_cd -= dt

        new_rect_x = pygame.Rect(px + dx * p_speed, py, p_w, p_h)
        if not collide_rect_list(new_rect_x, walls):
            px = clamp(new_rect_x.x, 0, WIDTH - p_w)
        new_rect_y = pygame.Rect(px, py + dy * p_speed, p_w, p_h)
        if not collide_rect_list(new_rect_y, walls):
            py = clamp(new_rect_y.y, 0, HEIGHT - p_h)

        for z in zombies:
            new_x = z["x"] + z["speed"] * z["dir"]
            zrect_try = pygame.Rect(int(new_x), int(z["y"]), z["w"], z["h"])

            if collide_rect_list(zrect_try, walls):
                z["dir"] *= -1
            else:
                z["x"] = new_x

            z["x"] = clamp(z["x"], 0, WIDTH - z["w"])

        screen.fill(ARENA_BROWN)
        draw_walls(screen, walls)

        # Player
        spr = p_sprites.get(facing)
        if spr:
            screen.blit(spr, (px, py))
        else:
            pygame.draw.rect(screen, (80, 200, 255), pygame.Rect(px, py, p_w, p_h), border_radius=4)

        # Zombies
        for z in zombies:
            if z["sprite"]:
                screen.blit(z["sprite"], (int(z["x"]), int(z["y"])))
            else:
                cx = int(z["x"] + z["w"] // 2)
                cy = int(z["y"] + z["h"] // 2)
                r = min(z["w"], z["h"]) // 2
                pygame.draw.circle(screen, (40, 40, 40), (cx, cy), r)

        # HUD
        if show_hud:
            hud_x, hud_y = 16, 14
            draw_shadow_text(screen, f"Score: {int(score)}", (hud_x, hud_y), size=34, color=(0, 0, 0))
            draw_shadow_text(screen, f"Level: {level_no}", (hud_x, hud_y + 36), size=34, color=(0, 0, 0))
            if heart_img:
                for i in range(health):
                    screen.blit(heart_img, (hud_x + i * (heart_img.get_width() + 6), hud_y + 72))
            else:
                draw_shadow_text(screen, f"Health: {health}", (hud_x, hud_y + 72), size=34, color=(0, 0, 0))

        pygame.display.flip()
        clock.tick(FPS)
