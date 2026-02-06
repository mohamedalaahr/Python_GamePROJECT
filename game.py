from __future__ import annotations
import os
import math
import random
import pygame

from util import (
    draw_text, draw_shadow_text, clamp, COLORS,
    load_image_to_height, load_sound, Button, Slider, Dropdown
)
from settings import game_settings, AVAILABLE_RESOLUTIONS
from walls import create_walls_for_level, collide_rect_list
from walls import create_walls_for_level, collide_rect_list
# from bullet import Bullet  <-- REMOVED
from characters import Player
from characters import Player

# 🔥 === استيراد الأنظمة الجديدة ===
from weapons import WeaponManager, WeaponType, WEAPON_STATS, AmmoPickup
from minimap import Minimap
from skins import (
    SKINS, SKIN_ORDER, DEFAULT_SKIN, get_skin_names, get_skin_data,
    get_skin_color, get_next_skin, get_prev_skin, apply_skin_tint,
    draw_skin_selector, get_clicked_skin, draw_player_indicator
)
from leaderboard import LeaderboardManager, show_leaderboard, show_name_input

# 🔥 متغير عام لتخزين المظهر المختار
CURRENT_SKIN = DEFAULT_SKIN

# ---------------- Window / World ----------------
WINDOW_W, WINDOW_H = 1280, 720
FPS = 60
LEVEL_COLORS = {
    1: (166, 98, 42),   # المستوى 1: رمل صحراوي/بني (اللون الأصلي)
    2: (110, 110, 110), # المستوى 2: خرسانة حضرية/رمادي (Urban Concrete)
    3: (75, 90, 75),    # المستوى 3: غابة/طحلب داكن (Dark Moss)
    4: (40, 40, 90),    # المستوى 4: سماء ليلية/أزرق عميق (Deep Blue Night)
    5: (140, 60, 40),   # المستوى 5: صهارة حمراء/أرض محروقة (Burning Magma)
    6: (30, 30, 30),    # المستوى 6: هاوية/مواجهة نهائية سوداء (Abyss/Final Arena)
}
GAME_OVER_IMAGE = None

# 🔥 --- (جديد) --- قاموس لألوان الجدران حسب المستوى ---
LEVEL_WALL_STYLES = {
    # (لون التعبئة، لون الحافة، لون الخط الداخلي)
    1: {"fill": (92, 55, 24), "edge": (40, 26, 15), "inner": (26, 90, 58)},  # 1: صحراء (الأصلي)
    2: {"fill": (80, 80, 85), "edge": (50, 50, 55), "inner": (110, 110, 115)}, # 2: خرسانة حضرية
    3: {"fill": (55, 70, 55), "edge": (30, 40, 30), "inner": (80, 100, 80)},  # 3: غابة/طحلب
    4: {"fill": (30, 30, 60), "edge": (15, 15, 35), "inner": (60, 60, 90)},  # 4: سماء ليلية
    5: {"fill": (70, 40, 30), "edge": (40, 20, 15), "inner": (150, 60, 40)},  # 5: صهارة/أرض محروقة
    6: {"fill": (25, 25, 25), "edge": (10, 10, 10), "inner": (50, 50, 50)},  # 6: هاوية/أسود
}
DEFAULT_WALL_STYLE = LEVEL_WALL_STYLES[1] # اللون الافتراضي إذا فشل شيء

# 🔥 --- (جديد) --- قاموس لحفظ المؤثرات البرمجية للخلفية ---
BG_EFFECTS = {}
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
            pygame.mixer.music.set_volume(game_settings.music_volume)
            pygame.mixer.music.play(-1)
    except Exception:
        pass

# ---------------- Camera ----------------
class Camera:
    def __init__(self, world_w: int, world_h: int, view_w: int, view_h: int):
        self.world_w, self.world_h = world_w, world_h
        self.view_w, self.view_h = view_w, view_h
        self.x, self.y = 0.0, 0.0

        # 🔥 --- (جديد) --- متغيرات اهتزاز الشاشة ---
        self.shake_intensity = 0.0
        self.shake_offset_x = 0.0
        self.shake_offset_y = 0.0

    def follow(self, target_rect: pygame.Rect, lerp: float = 0.15):
        tx = target_rect.centerx - self.view_w // 2
        ty = target_rect.centery - self.view_h // 2
        self.x += (tx - self.x) * lerp
        self.y += (ty - self.y) * lerp
        self.x = clamp(self.x, 0, max(0, self.world_w - self.view_w))
        self.y = clamp(self.y, 0, max(0, self.world_h - self.view_h))
    def trigger_shake(self, intensity: float = 12.0):
        """يتم استدعاؤها لبدء الاهتزاز"""
        self.shake_intensity = intensity

    def update(self, dt: float):
        """يجب استدعاؤها كل إطار لتحديث منطق الاهتزاز"""
        if self.shake_intensity > 0:
            # تقليل الشدة بمرور الوقت
            self.shake_intensity -= dt * 25.0 # (25.0 هي سرعة التلاشي)

            if self.shake_intensity <= 0:
                self.shake_intensity = 0.0
                self.shake_offset_x = 0.0
                self.shake_offset_y = 0.0
            else:
                # اختر إزاحة عشوائية بناءً على الشدة
                self.shake_offset_x = random.uniform(-self.shake_intensity, self.shake_intensity)
                self.shake_offset_y = random.uniform(-self.shake_intensity, self.shake_intensity)
        else:
            self.shake_intensity = 0.0
            self.shake_offset_x = 0.0
            self.shake_offset_y = 0.0    

    def apply_rect(self, r: pygame.Rect) -> pygame.Rect:
    # 🔥 إضافة إزاحة الاهتزاز
     return r.move(-int(self.x) + int(self.shake_offset_x), 
                  -int(self.y) + int(self.shake_offset_y))

    def apply_xy(self, x: float, y: float) -> tuple[int, int]:
    # 🔥 إضافة إزاحة الاهتزاز
        return (int(x - self.x) + int(self.shake_offset_x), 
            int(y - self.y) + int(self.shake_offset_y))

# ---------- Animated HORROR menu background ----------
class MenuBackground:
    def __init__(self, screen: pygame.Surface):
        self.W, self.H = screen.get_size()
        # 🔥 HORROR THEME - Dark cemetery/haunted layers
        self.layers = [
            {"y": int(self.H * 0.72), "speed": 6, "color": (25, 10, 10)},    # Blood-stained darkness
            {"y": int(self.H * 0.78), "speed": 12, "color": (18, 8, 8)},     # Deep crimson shadows
            {"y": int(self.H * 0.85), "speed": 20, "color": (12, 5, 5)},     # Abyssal black-red
        ]
        self._build_skyline()
        # 🔥 Blood-red fog
        self.fog = [self._make_fog(0.20), self._make_fog(0.15)]
        self.fog_x = [0.0, -self.W * 0.4]
        self.fog_v = [8.0, 14.0]
        # 🔥 Eerie flickering lights instead of search beams
        self.beams = [
            {"x": self.W * 0.24, "w": 180, "ang": 0.0, "vang": 0.4, "alpha": 40},
            {"x": self.W * 0.72, "w": 200, "ang": 0.7, "vang": -0.3, "alpha": 35},
        ]
        z = (load_image_to_height("zombie_left.png", 160) or
             load_image_to_height("zombie_right.png", 160) or
             load_image_to_height("zombie_up.png", 160) or
             load_image_to_height("zombie_down.png", 160))
        self.ghost_img = None
        if z:
            # 🔥 Create eerie red-tinted ghost
            g = pygame.Surface(z.get_size(), pygame.SRCALPHA)
            g.blit(z, (0, 0))
            g.fill((180, 50, 50, 80), special_flags=pygame.BLEND_RGBA_MULT)
            self.ghost_img = g
        self.ghosts = self._spawn_ghosts(8) if self.ghost_img else []
        
        # 🔥 Darker, blood-red vignette
        self.vignette = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        pygame.draw.rect(self.vignette, (0, 0, 0, 160), self.vignette.get_rect())
        pygame.draw.rect(self.vignette, (0, 0, 0, 0), (80, 80, self.W - 160, self.H - 160))
        
        # 🔥 Blood spots/splatters
        self.blood_spots = self._create_blood_spots()
        
        # 🔥 Lightning flash timer
        self.lightning_timer = 0.0
        self.lightning_active = False
        self.lightning_alpha = 0

    def _build_skyline(self):
        rng = random.Random(666)  # 🔥 Evil seed
        for L in self.layers:
            yb = L["y"]; blocks = []; x = -80
            while x < self.W + 80:
                # 🔥 Tombstone/ruins-like shapes
                w = rng.randint(30, 90); h = rng.randint(80, 280)
                blocks.append(pygame.Rect(x, yb - h, w, h))
                x += w + rng.randint(15, 35)
            L["blocks"] = blocks; L["offset"] = 0.0

    def _make_fog(self, alpha: float) -> pygame.Surface:
        s = pygame.Surface((int(self.W * 1.4), int(self.H * 0.5)), pygame.SRCALPHA)
        rng = random.Random(13 if alpha < 0.18 else 17)  # 🔥 Superstitious numbers
        for _ in range(250):
            r = rng.randint(50, 140)
            x = rng.randint(-50, s.get_width() - 50)
            y = rng.randint(0, s.get_height() - 30)
            a = int(255 * alpha * rng.uniform(0.5, 1.0))
            # 🔥 Blood red mist
            pygame.draw.circle(s, (120, 20, 20, a), (x, y), r)
        return s

    def _spawn_ghosts(self, n: int):
        rng = random.Random(13); res = []
        for _ in range(n):
            res.append({"x": rng.randint(-60, self.W - 60),
                        "y": rng.randint(30, int(self.H * 0.55)),
                        "vx": rng.choice([-1, 1]) * rng.uniform(5, 15),
                        "alpha": rng.randint(40, 100)})  # 🔥 Variable opacity
        return res
    
    def _create_blood_spots(self):
        """Create random blood splatter positions"""
        rng = random.Random(31)
        spots = []
        for _ in range(15):
            spots.append({
                "x": rng.randint(0, self.W),
                "y": rng.randint(0, self.H),
                "size": rng.randint(10, 40),
                "alpha": rng.randint(30, 80)
            })
        return spots

    def draw(self, screen: pygame.Surface, dt: float):
        W, H = self.W, self.H
        
        # 🔥 HORROR gradient - Deep black to blood red
        for i in range(H):
            t = i / max(H - 1, 1)
            # Top: Near black (5, 0, 0) | Bottom: Deep blood red (30, 5, 5)
            r = int(5 + 25 * t)
            g = int(0 + 5 * t)
            b = int(5 + 3 * t)
            pygame.draw.line(screen, (r, g, b), (0, i), (W, i))
        
        # 🔥 Blood spots background effect
        for spot in self.blood_spots:
            spot_surf = pygame.Surface((spot["size"]*2, spot["size"]*2), pygame.SRCALPHA)
            pygame.draw.circle(spot_surf, (100, 10, 10, spot["alpha"]), 
                             (spot["size"], spot["size"]), spot["size"])
            screen.blit(spot_surf, (spot["x"] - spot["size"], spot["y"] - spot["size"]))
        
        # 🔥 Tombstone/ruins silhouettes
        for L in self.layers:
            L["offset"] = (L["offset"] - L["speed"] * dt) % (W + 40)
            ox = -L["offset"]
            for r in L["blocks"]:
                rr = r.move(ox, 0)
                pygame.draw.rect(screen, L["color"], rr)
                pygame.draw.rect(screen, L["color"], rr.move(W + 40, 0))
                
        # 🔥 Eerie red flickering lights (instead of search beams)
        for b in self.beams:
            b["ang"] += b["vang"] * dt
            flicker = 0.7 + 0.3 * math.sin(b["ang"] * 5) + random.uniform(-0.1, 0.1)
            ang = math.sin(b["ang"]) * 0.8
            
            # 🔥 Blood red light cone
            poly = [(b["x"] - 8, self.layers[0]["y"] - 4),
                    (b["x"] + 8, self.layers[0]["y"] - 4),
                    (b["x"] + math.cos(ang) * b["w"], self.layers[0]["y"] - 200 + math.sin(ang) * 70)]
            cone = pygame.Surface((W, H), pygame.SRCALPHA)
            cone_alpha = int(b["alpha"] * flicker)
            pygame.draw.polygon(cone, (180, 30, 30, cone_alpha), poly)
            screen.blit(cone, (0, 0), special_flags=pygame.BLEND_PREMULTIPLIED)
            
        # 🔥 Blood red fog
        for i, fog in enumerate(self.fog):
            self.fog_x[i] = (self.fog_x[i] + self.fog_v[i] * dt) % fog.get_width()
            x = -self.fog_x[i]; y = int(H * 0.40) + i * 35
            screen.blit(fog, (x, y)); screen.blit(fog, (x + fog.get_width(), y))
            
        # 🔥 Haunting ghosts with flickering opacity
        if self.ghost_img:
            for g in self.ghosts:
                g["x"] += g["vx"] * dt
                if g["x"] < -140: g["x"] = W + 60
                if g["x"] > W + 60: g["x"] = -140
                
                # 🔥 Flickering ghost effect
                flicker = int(g["alpha"] * (0.8 + 0.2 * math.sin(g["x"] * 0.05)))
                ghost_copy = self.ghost_img.copy()
                ghost_copy.set_alpha(flicker)
                screen.blit(ghost_copy, (int(g["x"]), int(g["y"])))
        
        # 🔥 Random lightning flash
        self.lightning_timer += dt
        if self.lightning_timer > random.uniform(4.0, 8.0):
            self.lightning_timer = 0.0
            self.lightning_active = True
            self.lightning_alpha = 180
            
        if self.lightning_active:
            lightning_surf = pygame.Surface((W, H), pygame.SRCALPHA)
            lightning_surf.fill((200, 180, 180, self.lightning_alpha))
            screen.blit(lightning_surf, (0, 0))
            self.lightning_alpha -= 15
            if self.lightning_alpha <= 0:
                self.lightning_active = False
        
        # 🔥 Dark vignette overlay
        screen.blit(self.vignette, (0, 0))

# ---------------- Menus ----------------


def main_menu(screen: pygame.Surface, clock: pygame.time.Clock, version: str) -> str | None:
    global CURRENT_SKIN
    bg = MenuBackground(screen)
    
    # 🔥 أضف هذا السطر - تعريف cx و cy
    cx, cy = WINDOW_W // 2, WINDOW_H // 2
    
    # الأزرار الأصلية - تم إعادة ترتيبها
    start_btn = Button(pygame.Rect(cx - 120, cy - 110, 240, 48), "Single Player")
    howto_btn = Button(pygame.Rect(cx - 120, cy - 55, 240, 42), "How to Play")
    skins_btn = Button(pygame.Rect(cx - 120, cy - 5, 240, 42), "🎨 Select Skin")
    leaderboard_btn = Button(pygame.Rect(cx - 120, cy + 45, 240, 42), "🏆 Leaderboard")
    multiplayer_btn = Button(pygame.Rect(cx - 120, cy + 95, 240, 42), "👥 Multiplayer")
    settings_btn = Button(pygame.Rect(cx - 120, cy + 145, 240, 42), "⚙️ Settings")
    quit_btn  = Button(pygame.Rect(cx - 120, cy + 195, 240, 42), "Quit")
    
    # Settings panel UI components
    music_slider = None
    sfx_slider = None
    resolution_dropdown = None
    settings_back_btn = None

    mode = "menu"  # "menu" | "howto" | "skins" | "settings"
    while True:
        dt = clock.get_time() / 1000.0
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return None
            if e.type == pygame.KEYDOWN:
                if mode == "menu":
                    if e.key == pygame.K_RETURN: return "start"
                    if e.key == pygame.K_ESCAPE: return None
                    if e.key == pygame.K_l: return "leaderboard"
                elif mode == "skins":
                    if e.key == pygame.K_ESCAPE: mode = "menu"
                    # تغيير المظهر بالأسهم
                    if e.key == pygame.K_LEFT:
                        CURRENT_SKIN = get_prev_skin(CURRENT_SKIN)
                    if e.key == pygame.K_RIGHT:
                        CURRENT_SKIN = get_next_skin(CURRENT_SKIN)
                elif mode == "settings":
                    if e.key == pygame.K_ESCAPE:
                        game_settings.save()
                        mode = "menu"
                else:
                    if e.key == pygame.K_ESCAPE: mode = "menu"
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if mode == "menu":
                    if start_btn.hit(e.pos): return "start"
                    if howto_btn.hit(e.pos):  mode = "howto"
                    if skins_btn.hit(e.pos):  mode = "skins"
                    if leaderboard_btn.hit(e.pos): return "leaderboard"
                    if quit_btn.hit(e.pos):   return None
                    # 🔥 معالجة زر Multiplayer
                    if multiplayer_btn.hit(e.pos): return "multiplayer"
                    # 🔥 معالجة زر Settings
                    if settings_btn.hit(e.pos):
                        mode = "settings"
                        # Initialize settings UI
                        panel_x = cx - 280
                        music_slider = Slider(
                            pygame.Rect(panel_x + 140, cy - 60, 280, 18),
                            value=game_settings.music_volume,
                            label="Music Volume"
                        )
                        sfx_slider = Slider(
                            pygame.Rect(panel_x + 140, cy + 10, 280, 18),
                            value=game_settings.sfx_volume,
                            label="SFX Volume"
                        )
                        settings_back_btn = Button(pygame.Rect(cx - 80, cy + 100, 160, 44), "Back")
                elif mode == "skins":
                    # التحقق من النقر على المظاهر
                    clicked_skin = get_clicked_skin(e.pos, cx, cy + 50)
                    if clicked_skin:
                        CURRENT_SKIN = clicked_skin
                    # النقر خارج منطقة المظاهر للخروج
                    selector_rect = pygame.Rect(cx - 200, cy, 400, 150)
                    if not selector_rect.collidepoint(e.pos):
                        mode = "menu"
                elif mode == "settings":
                    # Settings panel events
                    if settings_back_btn and settings_back_btn.hit(e.pos):
                        # Save settings before going back
                        game_settings.save()
                        mode = "menu"
                else:
                    mode = "menu"
            
            # Handle slider events for settings mode
            if mode == "settings":
                if music_slider:
                    if music_slider.handle_event(e):
                        game_settings.set_music_volume(music_slider.value)
                if sfx_slider:
                    if sfx_slider.handle_event(e):
                        game_settings.set_sfx_volume(sfx_slider.value)

        bg.draw(screen, dt)
        
        # Modern Title Rendering
        title = "Zombie Shooter"
             
        # Draw Title with Glow - CLEAR READABLE VERSION
        # Center the title
        title_font = pygame.font.SysFont("arial", 56, bold=True)
        
        # 🔥 BLACK OUTLINE for maximum readability
        outline_surf = title_font.render(title, True, (0, 0, 0))
        title_rect = outline_surf.get_rect(center=(WINDOW_W // 2, 80))
        for ox, oy in [(-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2), (-2, 2), (2, -2)]:
            screen.blit(outline_surf, (title_rect.x + ox, title_rect.y + oy))
        
        # 🔥 BRIGHT RED GLOW behind text
        glow_surf = title_font.render(title, True, (200, 40, 40))
        for offset in [(-1, -1), (1, 1), (-1, 1), (1, -1)]:
            screen.blit(glow_surf, (title_rect.x + offset[0], title_rect.y + offset[1]))
        
        # 🔥 MAIN TITLE - Bright white/cream for clarity
        title_surf = title_font.render(title, True, (255, 240, 240))
        screen.blit(title_surf, title_rect)
        
        if mode == "menu":
            start_btn.draw(screen)
            howto_btn.draw(screen)
            skins_btn.draw(screen)
            leaderboard_btn.draw(screen)
            multiplayer_btn.draw(screen)
            settings_btn.draw(screen)
            quit_btn.draw(screen)
            
            # 🔥 عرض المظهر الحالي في الزاوية
            skin_data = get_skin_data(CURRENT_SKIN)
            skin_text = f"Skin: {skin_data['name']}"
            draw_text(screen, skin_text, (WINDOW_W - 180, 28), size=20, color=skin_data['color'])
            
        elif mode == "skins":
            _draw_skins_panel(screen, cx, cy)
        elif mode == "settings":
            _draw_settings_panel(screen, cx, cy, music_slider, sfx_slider, settings_back_btn)
        else:
            _draw_howto_panel(screen)

        pygame.display.flip()
        clock.tick(FPS)

        

def _draw_howto_panel(screen: pygame.Surface):
    # 🔥 HORROR THEME - Dark panel with blood red accents
    rect = pygame.Rect(WINDOW_W//2 - 360, WINDOW_H//2 - 200, 720, 380)
    pygame.draw.rect(screen, (20, 10, 12, 245), rect, border_radius=10)
    pygame.draw.rect(screen, (180, 50, 50), rect, width=3, border_radius=10)
    draw_shadow_text(screen, "How to Survive", (rect.x+20, rect.y+16), size=32, color=(255, 100, 100))
    y = rect.y + 60
    lines = [
        "Move: Z/Q/S/D or WASD or Arrow Keys",
        "Shoot: Space or Left Mouse | Right Mouse (Shotgun)",
        "",
        "WEAPONS:",
        "  [1] Pistol - Unlimited ammo, fast fire",
        "  [2] Shotgun - 5 pellets spread, needs ammo",
        "  [3] Grenade - Area damage, limited supply",
        "",
        "[M] Toggle Mini-map | [H] Toggle HUD | [ESC] Pause",
        "Open Speed Chests for a temporary speed boost!",
        "Find and enter the DOOR to escape this nightmare!",
    ]
    for line in lines:
        # 🔥 BRIGHT text colors for readability
        if "WEAPONS" in line:
            color = (255, 120, 120)  # Bright red for section header
        else:
            color = (240, 235, 235)  # Near-white for body text
        draw_text(screen, line, (rect.x+20, y), size=20, color=color)
        y += 28
    draw_text(screen, "Press ESC to go back", (rect.x+20, rect.y+rect.h-42), size=20, color=(200, 180, 180))

def _draw_skins_panel(screen: pygame.Surface, cx: int, cy: int):
    """🔥 HORROR THEME - رسم لوحة اختيار المظاهر"""
    global CURRENT_SKIN
    
    # 🔥 Dark horror panel with blood red border
    rect = pygame.Rect(cx - 280, cy - 100, 560, 280)
    pygame.draw.rect(screen, (20, 10, 12, 245), rect, border_radius=12)
    pygame.draw.rect(screen, (180, 50, 50), rect, width=3, border_radius=12)
    
    # 🔥 Horror title - BRIGHT for readability
    draw_shadow_text(screen, "Choose Your Character", (cx - 140, cy - 80), size=30, color=(255, 100, 100))
    
    # رسم المظاهر
    draw_skin_selector(screen, CURRENT_SKIN, cx, cy + 10)
    
    # معلومات المظهر المختار - BRIGHT text
    skin_data = get_skin_data(CURRENT_SKIN)
    info_text = f"Selected: {skin_data['name']} - {skin_data['description']}"
    draw_text(screen, info_text, (cx - 200, cy + 110), size=20, color=(240, 230, 230))
    
    # تعليمات - READABLE
    draw_text(screen, "Click to select | [Arrow Keys] Navigate | [ESC] Back", 
             (cx - 200, cy + 145), size=18, color=(200, 180, 180))

def _draw_settings_panel(screen: pygame.Surface, cx: int, cy: int, 
                         music_slider, sfx_slider, back_btn):
    """🔥 HORROR THEME - Settings panel with volume controls"""
    # Dark horror panel with blood red border
    rect = pygame.Rect(cx - 300, cy - 120, 600, 280)
    panel_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(panel_surf, (20, 10, 12, 245), panel_surf.get_rect(), border_radius=12)
    screen.blit(panel_surf, (rect.x, rect.y))
    pygame.draw.rect(screen, (180, 50, 50), rect, width=3, border_radius=12)
    
    # Title
    draw_shadow_text(screen, "⚙️ Settings", (cx - 60, rect.y + 20), size=32, color=(255, 100, 100))
    
    # Draw sliders
    if music_slider:
        music_slider.draw(screen)
    if sfx_slider:
        sfx_slider.draw(screen)
    
    # Key bindings display (read-only)
    key_y = cy + 60
    draw_text(screen, "Key Bindings:", (rect.x + 30, key_y), size=18, color=(255, 120, 120), bold=True)
    key_y += 28
    key_info = [
        "Move: W/Z/S/D or Arrow Keys",
        "Shoot: SPACE | Weapons: 1/2/3"
    ]
    for line in key_info:
        draw_text(screen, line, (rect.x + 40, key_y), size=16, color=(200, 190, 190))
        key_y += 22
    
    # Back button
    if back_btn:
        back_btn.draw(screen)
    
    # Instructions
    draw_text(screen, "Settings are saved automatically", 
             (cx - 110, rect.y + rect.height - 30), size=14, color=(160, 150, 150))

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


# ---------------- Door Navigation System ----------------
def calculate_door_direction(player_x: float, player_y: float, door_x: float, door_y: float) -> tuple[float, float, float]:
    """حساب اتجاه الباب بالنسبة للاعب وإرجاع (angle, distance, normalized_vector)"""
    dx = door_x - player_x
    dy = door_y - player_y
    distance = math.sqrt(dx*dx + dy*dy)
    
    if distance == 0:
        return 0, 0, (0, 0)
    
    # حساب الزاوية بالراديان
    angle = math.atan2(dy, dx)
    
    # تطبيع المتجه
    norm_dx = dx / distance
    norm_dy = dy / distance
    
    return angle, distance, (norm_dx, norm_dy)

def create_navigation_arrow(angle: float, size: int = 40) -> pygame.Surface:
    """إنشاء سهم اتجاه باتجاه الباب"""
    arrow_surface = pygame.Surface((size, size), pygame.SRCALPHA)
    
    # نقاط السهم (مثلث)
    points = [
        (size//2, 0),  # رأس السهم
        (0, size),     # قاعدة يسار
        (size, size)   # قاعدة يمين
    ]
    
    # تدوير النقاط حسب الزاوية
    rotated_points = []
    center_x, center_y = size//2, size//2
    
    for x, y in points:
        # نقل النقاط لتكون مركزة على الأصل
        x -= center_x
        y -= center_y
        
        # التدوير
        new_x = x * math.cos(angle) - y * math.sin(angle)
        new_y = x * math.sin(angle) + y * math.cos(angle)
        
        # إعادة النقاط إلى مكانها
        rotated_points.append((new_x + center_x, new_y + center_y))
    
    # رسم السهم
    pygame.draw.polygon(arrow_surface, (255, 255, 0, 200), rotated_points)
    pygame.draw.polygon(arrow_surface, (255, 200, 0), rotated_points, 2)
    
    return arrow_surface

def create_distance_indicator(distance: float) -> tuple[str, tuple[int, int, int]]:
    """إنشاء مؤشر المسافة مع اللون المناسب"""
    if distance < 300:
        return "VERY CLOSE", (0, 255, 0)  # أخضر
    elif distance < 600:
        return "CLOSE", (255, 255, 0)     # أصفر
    elif distance < 1000:
        return "NEARBY", (255, 165, 0)    # برتقالي
    else:
        return "FAR", (255, 0, 0)         # أحمر            

# ---------------- Door System ----------------
# ---------------- Enhanced Door System ----------------
class LevelDoor:
    """باب محسن للانتقال بين المستويات مع نظام ملاحة"""
    def __init__(self, x: float, y: float, level: int):
        self.x, self.y = float(x), float(y)
        self.level = level
        self.w, self.h = 80, 120  # حجم الباب
        self.active = False
        self.glow_timer = 0.0
        self.pulse_speed = 2.0
        self.beacon_timer = 0.0
        self.beacon_interval = 1.5  # فترة إرسال المنارة
        self.navigation_enabled = False
        
        # 🔥 محاولة تحميل صور متعددة للباب
        self.img_closed = load_image_to_height("door_closed.png", self.h)
        self.img_open = load_image_to_height("door_open.png", self.h)
        self.img = self.img_closed or self.img_open
        
        # 🔥 تأثيرات بصرية محسنة
        self.beacon_particles = []
        self.activation_time = None
        
        # 🔥 نظام الصوت
        self.activation_sound = load_sound("door_activate.wav")
        self.beacon_sound = load_sound("door_beacon.wav")
        self.navigation_sound = load_sound("door_navigation.wav")
        
        # 🔥 رسائل التوجيه
        self.hint_messages = [
            "Find the glowing door to advance!",
            "Follow the golden arrow to the exit!",
            "The door is calling you! Follow the light!",
            "Escape through the portal to next level!"
        ]
        self.current_hint = random.choice(self.hint_messages)
        
    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)
        
    def activate(self):
        """تفعيل الباب عندما يقتل اللاعب عدد كافي من الزومبي"""
        if not self.active:
            self.active = True
            self.activation_time = pygame.time.get_ticks()
            self.navigation_enabled = True
            
            # تشغيل صوت التفعيل
            if self.activation_sound:
                self.activation_sound.play()
                
            # 🔥 تغيير صورة الباب إذا كانت متوفرة
            if self.img_open:
                self.img = self.img_open
                
            print(f"🚪 Door activated for Level {self.level + 1}")
            
    def update(self, dt: float, player_x: float = None, player_y: float = None):
        if self.active:
            self.glow_timer += dt * self.pulse_speed
            self.beacon_timer += dt
            
            # 🔥 إرسال منارة دورية للملاحة
            if self.beacon_timer >= self.beacon_interval:
                self.beacon_timer = 0
                if self.beacon_sound:
                    self.beacon_sound.play()
                
                # 🔥 إنشاء جزيئات المنارة إذا كان اللاعب بعيداً
                if player_x is not None and player_y is not None:
                    distance = math.sqrt((player_x - self.x)**2 + (player_y - self.y)**2)
                    if distance > 500:  # فقط إذا كان اللاعب بعيداً
                        self._create_beacon_particles()
                        
            # 🔥 تحديث جزيئات المنارة
            for particle in self.beacon_particles[:]:
                particle['timer'] += dt
                if particle['timer'] >= particle['lifetime']:
                    self.beacon_particles.remove(particle)
                    
    def _create_beacon_particles(self):
        """إنشاء جزيئات المنارة للإشارة إلى موقع الباب"""
        for i in range(8):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 150)
            distance = random.uniform(20, 60)
            
            self.beacon_particles.append({
                'x': self.x + self.w/2 + math.cos(angle) * distance,
                'y': self.y + self.h/2 + math.sin(angle) * distance,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'color': (255, 255, 100, 255),
                'size': random.uniform(3, 8),
                'lifetime': random.uniform(0.8, 1.5),
                'timer': 0.0
            })
            
    def draw_navigation(self, screen: pygame.Surface, player_x: float, player_y: float):
        """رسم نظام الملاحة للباب"""
        if not self.active or not self.navigation_enabled:
            return
            
        angle, distance, direction = calculate_door_direction(
            player_x + 18, player_y + 18,  # مركز اللاعب
            self.x + self.w/2, self.y + self.h/2
        )
        
        # 🔥 رسم سهم التوجيه في حافة الشاشة
        if distance > 200:  # فقط إذا كان الباب خارج الشاشة
            arrow_size = 35
            margin = 60
            
            # حساب موقع السهم على حافة الشاشة
            screen_center_x, screen_center_y = WINDOW_W // 2, WINDOW_H // 2
            max_dist = min(screen_center_x, screen_center_y) - margin
            
            arrow_x = screen_center_x + direction[0] * max_dist
            arrow_y = screen_center_y + direction[1] * max_dist
            
            # إنشاء السهم
            arrow_surface = create_navigation_arrow(angle, arrow_size)
            arrow_rect = arrow_surface.get_rect(center=(arrow_x, arrow_y))
            
            # رسم السهم
            screen.blit(arrow_surface, arrow_rect)
            
            # 🔥 رسم دائرة حول السهم
            pygame.draw.circle(screen, (255, 255, 0, 100), (int(arrow_x), int(arrow_y)), 
                             arrow_size//2 + 5, 2)
            
            # 🔥 عرض المسافة
            distance_text, color = create_distance_indicator(distance)
            dist_font = pygame.font.Font(None, 22)
            dist_surface = dist_font.render(f"{distance_text} ({int(distance)}m)", True, color)
            dist_rect = dist_surface.get_rect(center=(arrow_x, arrow_y + arrow_size//2 + 20))
            
            # خلفية للنص
            bg_rect = dist_rect.inflate(10, 5)
            pygame.draw.rect(screen, (0, 0, 0, 180), bg_rect, border_radius=3)
            screen.blit(dist_surface, dist_rect)
        
    def draw(self, screen: pygame.Surface, cam: Camera):
        if not self.active:
            return
            
        dx, dy = cam.apply_xy(self.x, self.y)
        door_rect = pygame.Rect(dx, dy, self.w, self.h)
        
        # 🔥 تأثير الوميض المحسن
        glow_intensity = (math.sin(self.glow_timer) + 1) * 0.4 + 0.3
        pulse_scale = 1.0 + math.sin(self.glow_timer * 3) * 0.1  # تأثير نبض
        
        if self.img:
            # نسخ الصورة وتطبيق التأثيرات
            img_copy = self.img.copy()
            current_size = self.img.get_size()
            
            # تطبيق تأثير النبض
            if pulse_scale != 1.0:
                new_size = (int(current_size[0] * pulse_scale), int(current_size[1] * pulse_scale))
                img_copy = pygame.transform.scale(img_copy, new_size)
                # تعديل الموضع للحفاظ على المركز
                dx = dx - (new_size[0] - current_size[0]) // 2
                dy = dy - (new_size[1] - current_size[1]) // 2
            
            # تأثير الوميض الذهبي
            glow_surf = pygame.Surface(img_copy.get_size(), pygame.SRCALPHA)
            glow_color = (255, 255, 150, int(150 * glow_intensity))
            glow_surf.fill(glow_color)
            img_copy.blit(glow_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            
            # تأثير هالة حول الباب
            halo_radius = max(self.w, self.h) * 0.8
            halo_surf = pygame.Surface((int(halo_radius*2), int(halo_radius*2)), pygame.SRCALPHA)
            halo_color = (255, 255, 100, int(80 * glow_intensity))
            pygame.draw.circle(halo_surf, halo_color, 
                             (int(halo_radius), int(halo_radius)), 
                             int(halo_radius))
            screen.blit(halo_surf, 
                       (dx + self.w//2 - halo_radius, dy + self.h//2 - halo_radius),
                       special_flags=pygame.BLEND_RGBA_ADD)
            
            screen.blit(img_copy, (dx, dy))
        else:
            # 🔥 رسم باب بدائي محسن
            door_color = (160, 120, 60)  # بني ذهبي
            glow_color = (255, 255, 150, int(255 * glow_intensity))
            
            # الباب الأساسي مع تأثير النبض
            door_rect = pygame.Rect(dx, dy, int(self.w * pulse_scale), int(self.h * pulse_scale))
            pygame.draw.rect(screen, door_color, door_rect, border_radius=10)
            pygame.draw.rect(screen, (80, 60, 30), door_rect, width=3, border_radius=10)
            
            # تفاصيل الباب
            detail_color = (100, 80, 40)
            for i in range(3):
                pygame.draw.rect(screen, detail_color, 
                               (dx + 15, dy + 20 + i*30, self.w - 30, 2))
            
            # مقبض الباب متوهج
            handle_pos = (dx + self.w - 25, dy + self.h // 2)
            pygame.draw.circle(screen, (255, 255, 100), handle_pos, 10)
            pygame.draw.circle(screen, (255, 200, 50), handle_pos, 6)
        
        # 🔥 رسم جزيئات المنارة
        for particle in self.beacon_particles:
            p_alpha = 255 * (1 - particle['timer'] / particle['lifetime'])
            p_color = (*particle['color'][:3], int(p_alpha))
            p_x, p_y = cam.apply_xy(particle['x'], particle['y'])
            pygame.draw.circle(screen, p_color, (int(p_x), int(p_y)), int(particle['size']))
        
        # 🔥 نص المستوى التالي محسن
        level_text = f"LEVEL {self.level + 1}"
        font = pygame.font.Font(None, 26)
        text_surf = font.render(level_text, True, (255, 255, 200))
        text_rect = text_surf.get_rect(center=(dx + self.w//2, dy - 25))
        
        # خلفية متطورة للنص
        text_bg = pygame.Rect(text_rect.x - 8, text_rect.y - 4, 
                            text_rect.width + 16, text_rect.height + 8)
        pygame.draw.rect(screen, (0, 0, 0, 200), text_bg, border_radius=6)
        pygame.draw.rect(screen, (255, 255, 100), text_bg, width=1, border_radius=6)
        
        # تأثير توهج للنص
        text_glow = font.render(level_text, True, (255, 255, 100, 100))
        for offset in [(1,1), (-1,1), (1,-1), (-1,-1)]:
            screen.blit(text_glow, (text_rect.x + offset[0], text_rect.y + offset[1]))
        
        screen.blit(text_surf, text_rect)
        

# ---------------- Zombie (نوع واحد فقط مع نظام المستويات) ----------------
ZOMBIE_SIZE = 96  # حجم واحد لجميع الزومبي

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
    """نوع واحد من الزومبي مع زيادة القوة حسب المستوى."""
    def __init__(self, x: float, y: float, level: int = 1):
        self.level = level

        # ✅ تعديل معادلة السرعة - زيادة أكثر تدريجية وتوازناً
        level_multiplier = 1.0 + (level - 1) * 0.12  # 🔥 كان 0.15
        
        # ✅ إحصائيات الزومبي الواحد مع زيادة معتدلة بالمستوى
        self.speed = (1.3 + (level * 0.12)) * level_multiplier  # 🔥 كان 1.4 + 0.15
        self.hp = int((2 + (level * 0.6)) * level_multiplier)   # 🔥 كان 0.8
        self.damage = 1 + (level // 3)  # 🔥 يزيد الضرر كل  3مستويات بدلاً من 4
            
        self.size = ZOMBIE_SIZE
        self.max_hp = self.hp

        # باقي الكود يبقى كما هو...
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
        
        # رسم الزومبي
        if self.sprite:
            off = math.sin(self.bob_t) * 1.5
            screen.blit(self.sprite, (dx, dy + off))
        else:
            # لون يتغير حسب المستوى (أفتح مع زيادة المستوى)
            base_color = (90, 160, 220)
            level_effect = min(100, self.level * 15)
            color = (
                min(255, base_color[0] + level_effect),
                max(0, base_color[1] - level_effect // 2),
                max(0, base_color[2] - level_effect // 3)
            )
            r = pygame.Rect(dx, dy, self.w, self.h)
            pygame.draw.rect(screen, color, r, border_radius=6)
            pygame.draw.rect(screen, (30, 30, 30), r, width=2, border_radius=6)
        
        # رسم شريط الصحة
        if self.hp < self.max_hp:
            bar_width = self.w
            bar_height = 6
            health_ratio = self.hp / self.max_hp
            
            # خلفية الشريط
            pygame.draw.rect(screen, (50, 50, 50), (dx, dy - 10, bar_width, bar_height))
            # الشريط الأخضر للصحة
            pygame.draw.rect(screen, (0, 255, 0), (dx, dy - 10, bar_width * health_ratio, bar_height))
            
        # عرض مستوى الزومبي فوقه
        level_text = f"Lv{self.level}"
        font = pygame.font.Font(None, 20)
        text_surf = font.render(level_text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=(dx + self.w//2, dy - 20))
        screen.blit(text_surf, text_rect)

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
# ---------------- Levels (difficulty) ----------------
LEVELS = {
    1: {"goal_kills": 1,  "spawn_every": 1.8,  "max_alive": 4},
    2: {"goal_kills": 1,  "spawn_every": 1.5,  "max_alive": 5},
    3: {"goal_kills": 1,  "spawn_every": 1.3,  "max_alive": 6},
    4: {"goal_kills": 1,  "spawn_every": 1.1,  "max_alive": 7},
    5: {"goal_kills": 1,  "spawn_every": 1.0,  "max_alive": 8},   # 🔥 كان 13
    6: {"goal_kills": 1,  "spawn_every": 0.9,  "max_alive": 9},   # 🔥 كان 13
}

# ---------------- Utilities ----------------

def get_muzzle_xy(player: Player, target_x: float, target_y: float) -> tuple[float, float]:
    """حساب نقطة فوهة السلاح ديناميكياً اعتماداً على اتجاه التصويب وحجم السبرايت.
    هذا يعطي نتيجة أدق ويمنع خروج الرصاصة من الرأس."""
    x, y, w, h = player.x, player.y, player.w, player.h
    prefix = getattr(player, "sprite_prefix", "player")
    
    # متجه التصويب من مركز اللاعب نحو الهدف
    cx, cy = x + w * 0.5, y + h * 0.5
    dx, dy = target_x - cx, target_y - cy
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    
    # قاعدة الفوهة بالقرب من منطقة السلاح على الجسم
    if prefix == "commando":
        base_x = x + w * 0.55
        base_y = y + h * 0.62  # أسفل منتصف الرأس قليلاً (منطقة السلاح)
        forward = min(w, h) * 0.42  # تقدّم للأمام باتجاه التصويب
    else:
        base_x = x + w * 0.52
        base_y = y + h * 0.56
        forward = min(w, h) * 0.35
    
    mx = base_x + ux * forward
    my = base_y + uy * forward
    return mx, my

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

def find_door_location(walls: list[pygame.Rect], player_x: float, player_y: float, W: int, H: int):
    """إيجاد موقع مناسب للباب بعيداً عن اللاعب"""
    for _ in range(50):
        x = random.randint(100, W - 100)
        y = random.randint(100, H - 100)
        
        # التأكد من أن الباب بعيد عن اللاعب
        if not far_from_player(player_x, player_y, x, y, min_dist=400.0):
            continue
            
        # التأكد من أن الباب ليس داخل جدار
        door_rect = pygame.Rect(x, y, 80, 120)
        if not collide_rect_list(door_rect, walls):
            return float(x), float(y)
    
    # إذا لم نجد موقع مناسب، نضع الباب في الزاوية
    return float(W - 150), float(H - 200)


# ---------------- Game Over Scene ----------------
# ---------------- Game Over Scene ----------------
class GameOverScene:
    """شاشة Game Over مع خيارات إعادة اللعب أو الخروج"""
    def __init__(self, screen: pygame.Surface, score: int = 0, level: int = 1):
        self.screen = screen
        self.W, self.H = screen.get_size()
        self.score = score
        self.level = level
        
        # تحميل صورة Game Over (إذا وجدت)
        self.bg_image = None
        try:
            # محاولة تحميل الصورة التي أرفقتها
            self.bg_image = pygame.image.load("360_F_693042027_th0Yf1aofOwdQdabsMVLRtNieakvmDGr.jpg")
            # احتفظ بالنسب الأصلية للصورة
            img_ratio = self.bg_image.get_width() / self.bg_image.get_height()
            new_height = min(self.H, int(self.W / img_ratio))
            new_width = int(new_height * img_ratio)
            self.bg_image = pygame.transform.scale(self.bg_image, (new_width, new_height))
            
            # 🔥 زيادة سطوع الصورة
            brightened_image = pygame.Surface((new_width, new_height))
            # زيادة الإضاءة بإضافة لون أبيض شفاف
            brightened_image.fill((255, 255, 255, 60))  # أبيض شفاف
            self.bg_image.blit(brightened_image, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            
            # زيادة التباين
            brightened_image2 = pygame.Surface((new_width, new_height))
            brightened_image2.fill((30, 30, 30, 0))  # زيادة سطوع إضافية
            self.bg_image.blit(brightened_image2, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            
            self.bg_x = (self.W - new_width) // 2
            self.bg_y = (self.H - new_height) // 2
        except:
            # إذا فشل التحميل، نستخدم خلفية بديلة
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
        
        # تأثيرات بصرية - جعلها أقل ظلمة
        self.fade_surface = pygame.Surface((self.W, self.H))
        self.fade_surface.fill((0, 0, 0))
        self.fade_alpha = 0
        self.fade_speed = 6  # 🔥 جعل التعتيم أسرع وأقل
        
        # جزيئات الدم (تأثير إضافي)
        self.blood_particles = []
        self._create_blood_particles()
        
        # مؤقت للرسوم المتحركة
        self.animation_timer = 0.0
        
        # 🔥 إضافة سطح للإضاءة العامة
        self.bright_overlay = pygame.Surface((self.W, self.H))
        self.bright_overlay.fill((255, 255, 255))
        self.bright_overlay.set_alpha(30)  # 🔥 زيادة شفافية الطبقة المضيئة
    
    def _create_blood_particles(self):
        """إنشاء جزيئات دم متناثرة"""
        for _ in range(20):
            self.blood_particles.append({
                'x': random.randint(0, self.W),
                'y': random.randint(0, self.H),
                'size': random.randint(2, 6),
                'alpha': random.randint(80, 180),
                'speed': random.uniform(0.5, 2.0)
            })
    
    def update(self, dt: float):
        """تحديث تأثيرات الشاشة"""
        self.animation_timer += dt
        
        # تأثير التعتيم التدريجي - جعله أخف
        if self.fade_alpha < 120:  # 🔥 تقليل الحد الأقصى للتعتيم
            self.fade_alpha += self.fade_speed
            self.fade_surface.set_alpha(min(self.fade_alpha, 120))
    
    def draw(self):
        """رسم شاشة Game Over"""
        screen = self.screen
        
        # 🔥 خلفية أقل ظلمة
        screen.fill((50, 20, 20))  # 🔥 تغيير من (30, 0, 0) إلى لون أفتح
        
        # رسم الخلفية
        if self.bg_image:
            screen.blit(self.bg_image, (self.bg_x, self.bg_y))
            
            # 🔥 طبقة شبه شفافة فوق الصورة - جعلها أخف
            overlay = pygame.Surface((self.W, self.H))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(80)  # 🔥 تقليل من 120 إلى 80
            screen.blit(overlay, (0, 0))
            
            # 🔥 إضافة طبقة مضيئة فوق الصورة
            screen.blit(self.bright_overlay, (0, 0))
        else:
            # خلفية بديلة - جعلها أفتح
            screen.fill((60, 30, 30))  # 🔥 لون أفتح من الأحمر الداكن
            
            # رسم جزيئات الدم
            for particle in self.blood_particles:
                alpha = particle['alpha'] + int(50 * math.sin(self.animation_timer * particle['speed']))
                alpha = max(0, min(255, alpha))
                color = (150 + random.randint(0, 50), 40, 40, alpha)  # 🔥 ألوان أفتح
                pos = (particle['x'], particle['y'])
                pygame.draw.circle(screen, color, pos, particle['size'])
        
        # 🔥 رسم نص GAME OVER كبير مع تأثير أكثر إشراقاً
        title_y = self.H // 3 - 50
        
        # تأثير النص المتقطع
        if int(self.animation_timer * 3) % 3 != 0:
            font_large = pygame.font.Font(None, 72)
            
            # 🔥 جعل النص أكثر إشراقاً
            main_color = (255, 50, 50)  # 🔥 أحمر أكثر إشراقاً
            shadow_color = (150, 0, 0)   # 🔥 ظل أفتح
            
            text_surf = font_large.render("GAME OVER", True, main_color)
            text_rect = text_surf.get_rect(center=(self.W//2, title_y))
            
            # تأثير ظل للنص
            shadow_surf = font_large.render("GAME OVER", True, shadow_color)
            shadow_rect = shadow_surf.get_rect(center=(self.W//2 + 3, title_y + 3))
            screen.blit(shadow_surf, shadow_rect)
            screen.blit(text_surf, text_rect)
        
        # رسالة ثانوية - جعلها أكثر وضوحاً
        font_medium = pygame.font.Font(None, 32)
        sub_text = "The zombies got you..."
        sub_surf = font_medium.render(sub_text, True, (240, 240, 240))  # 🔥 لون أبيض نقي
        sub_rect = sub_surf.get_rect(center=(self.W//2, title_y + 60))
        screen.blit(sub_surf, sub_rect)
        
        # عرض الإحصائيات - جعل الخلفية أقل ظلمة
        stats_y = title_y + 120
        stats_text = f"Score: {self.score}  |  Level: {self.level}"
        stats_surf = font_medium.render(stats_text, True, (255, 255, 180))  # 🔥 لون أكثر إشراقاً
        
        stats_rect = stats_surf.get_rect(center=(self.W//2, stats_y))
        
        # خلفية للإحصائيات - جعلها أكثر شفافية
        stats_bg = pygame.Rect(stats_rect.x - 15, stats_rect.y - 8, stats_rect.width + 30, stats_rect.height + 16)
        pygame.draw.rect(screen, (0, 0, 0, 120), stats_bg, border_radius=10)  # 🔥 تقليل العتامة
        pygame.draw.rect(screen, (150, 150, 150), stats_bg, width=2, border_radius=10)  # 🔥 حدود أفتح
        screen.blit(stats_surf, stats_rect)
        
        # 🔥 جعل الأزرار أكثر إشراقاً
        self.play_again_btn.color = (100, 100, 180)  # 🔥 أزرق أفتح
        self.play_again_btn.hover_color = (120, 120, 210)
        self.menu_btn.color = (180, 100, 100)  # 🔥 أحمر أفتح
        self.menu_btn.hover_color = (210, 120, 120)
        
        # رسم الأزرار
        self.play_again_btn.draw(screen)
        self.menu_btn.draw(screen)
        
        # تعليمات التحكم - جعلها أكثر وضوحاً
        controls_y = self.H - 40
        controls_text = "Press R to Play Again  |  Press M for Main Menu  |  Press ESC to Quit"
        controls_surf = pygame.font.Font(None, 20).render(controls_text, True, (200, 200, 200))  # 🔥 لون أفتح
        controls_rect = controls_surf.get_rect(center=(self.W//2, controls_y))
        screen.blit(controls_surf, controls_rect)
        
        # تأثير التعتيم - جعله أخف
        if self.fade_alpha > 0:
            screen.blit(self.fade_surface, (0, 0))
    
    def handle_event(self, event) -> str | None:
        """معالجة الأحداث والاختيارات"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.play_again_btn.hit(event.pos):
                return "restart"
            elif self.menu_btn.hit(event.pos):
                return "menu"
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:  # R لإعادة اللعب
                return "restart"
            elif event.key == pygame.K_m:  # M للقائمة الرئيسية
                return "menu"
            elif event.key == pygame.K_RETURN:  # ENTER لإعادة اللعب
                return "restart"
            elif event.key == pygame.K_ESCAPE:  # ESC للقائمة الرئيسية
                return "menu"
        
        return None

def show_game_over_screen(screen: pygame.Surface, clock: pygame.time.Clock, score: int = 0, level: int = 1) -> str:
    """عرض شاشة Game Over وانتظار اختيار اللاعب"""
    game_over_scene = GameOverScene(screen, score, level)
    
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
# في نهاية ملف game.py - أضف هذا الكود بعد دالة show_game_over_screen

# ---------------- Victory Scene ----------------
class VictoryScene:
    """شاشة النصر بعد إكمال جميع المستويات"""
    def __init__(self, screen: pygame.Surface, score: int = 0, total_kills: int = 0):
        self.screen = screen
        self.W, self.H = screen.get_size()
        self.score = score
        self.total_kills = total_kills
        
        # تحميل صورة النصر (الصورة التي أرسلتها)
        self.bg_image = None
        try:
            # محاولة تحميل الصورة التي أرفقتها
            self.bg_image = pygame.image.load("BP3_CX11_blog_images1.jpg")
            # احتفظ بالنسب الأصلية للصورة مع ملء الشاشة
            img_ratio = self.bg_image.get_width() / self.bg_image.get_height()
            screen_ratio = self.W / self.H
            
            if img_ratio > screen_ratio:
                # الصورة أوسع من الشاشة
                new_height = self.H
                new_width = int(new_height * img_ratio)
            else:
                # الصورة أطول من الشاشة
                new_width = self.W
                new_height = int(new_width / img_ratio)
                
            self.bg_image = pygame.transform.scale(self.bg_image, (new_width, new_height))
            self.bg_x = (self.W - new_width) // 2
            self.bg_y = (self.H - new_height) // 2
            
            # 🔥 تحسين جودة الصورة - زيادة السطوع والتباين
            brightened_image = pygame.Surface((new_width, new_height))
            brightened_image.fill((80, 80, 80, 0))  # زيادة السطوع
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
        self.golden_overlay.fill((255, 215, 0))  # لون ذهبي
        self.golden_overlay.set_alpha(20)
    
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
        """رسم شاشة النصر الاحترافية."""
        screen = self.screen
        W, H = self.W, self.H

        # 1) الخلفية: صورة إذا توفرت، وإلا تدرّج دافئ
        if self.bg_image:
            screen.blit(self.bg_image, (self.bg_x, self.bg_y))
        else:
            for i in range(H):
                t = i / max(H - 1, 1)
                c = (int(24 + 70*(1-t)), int(20 + 60*(1-t)), int(10 + 30*(1-t)))
                pygame.draw.line(screen, c, (0, i), (W, i))

        # 2) طبقة ذهبية نابضة لإحساس الفوز
        pulse = (math.sin(self.animation_timer * 1.2) + 1) * 0.5
        self.golden_overlay.set_alpha(25 + int(35 * pulse))
        screen.blit(self.golden_overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        # 3) أشعة شعاعية من المركز (هالة الانتصار)
        rays = pygame.Surface((W, H), pygame.SRCALPHA)
        cx, cy = W // 2, int(H * 0.38)
        ray_count = 24
        base_angle = self.animation_timer * 0.4
        for i in range(ray_count):
            ang = base_angle + (i / ray_count) * (2 * math.pi)
            length = max(W, H)
            x2 = cx + math.cos(ang) * length
            y2 = cy + math.sin(ang) * length
            col = (255, 220, 120, 28)
            pygame.draw.line(rays, col, (cx, cy), (x2, y2), 24)
        screen.blit(rays, (0, 0), special_flags=pygame.BLEND_PREMULTIPLIED)

        # 4) فينييت لتغميق الأطراف وإبراز المركز
        vignette = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.rect(vignette, (0, 0, 0, 160), (0, 0, W, H))
        pygame.draw.rect(vignette, (0, 0, 0, 0), (60, 60, W - 120, H - 120))
        screen.blit(vignette, (0, 0))

        # 5) رسم الكونفيتي
        for p in self.confetti_particles:
            color = (p['color'][0], p['color'][1], p['color'][2], 200)
            pygame.draw.circle(screen, color, (int(p['x']), int(p['y'])), p['size'])

        # 6) كأس فوز مرسوم (Vector Trophy)
        trophy_x, trophy_y = cx - 80, cy - 60
        trophy = pygame.Surface((160, 140), pygame.SRCALPHA)
        # القاعدة
        pygame.draw.rect(trophy, (230, 180, 60), (50, 100, 60, 18), border_radius=6)
        pygame.draw.rect(trophy, (200, 160, 50), (50, 100, 60, 18), 2, border_radius=6)
        pygame.draw.rect(trophy, (230, 180, 60), (40, 88, 80, 14), border_radius=6)
        pygame.draw.rect(trophy, (200, 160, 50), (40, 88, 80, 14), 2, border_radius=6)
        # الكأس
        cup_rect = pygame.Rect(28, 8, 104, 82)
        pygame.draw.rect(trophy, (240, 190, 70), cup_rect, border_radius=20)
        pygame.draw.rect(trophy, (200, 160, 50), cup_rect, 3, border_radius=20)
        # المقابض
        pygame.draw.arc(trophy, (240, 190, 70), (2, 18, 64, 72), math.pi * 0.3, math.pi * 1.3, 10)
        pygame.draw.arc(trophy, (240, 190, 70), (94, 18, 64, 72), -math.pi * 0.3, math.pi * 0.7, 10)
        # نجمة وسطية
        star_points = []
        sx, sy, R, r = 80, 48, 18, 8
        for k in range(10):
            ang = (2 * math.pi) * k / 10.0 - math.pi / 2
            rad = R if (k % 2 == 0) else r
            star_points.append((sx + math.cos(ang) * rad, sy + math.sin(ang) * rad))
        pygame.draw.polygon(trophy, (255, 230, 120), star_points)
        pygame.draw.polygon(trophy, (210, 180, 80), star_points, 2)
        screen.blit(trophy, (trophy_x, trophy_y))

        # 7) عنوان الفوز متوهج
        title = "VICTORY!"
        font_big = pygame.font.Font(None, 96)
        glow_col = (255, 220, 120)
        text_col = (255, 245, 200)
        text_surf = font_big.render(title, True, text_col)
        text_rect = text_surf.get_rect(center=(cx, cy + 40))
        for off in [(0, 0), (2, 2), (-2, 2), (2, -2), (-2, -2)]:
            glow = font_big.render(title, True, glow_col)
            screen.blit(glow, (text_rect.x + off[0], text_rect.y + off[1]))
        screen.blit(text_surf, text_rect)

        # 8) شريط معلومات (النقاط والقتل)
        font_med = pygame.font.Font(None, 36)
        sub = f"Score: {self.score}   |   Kills: {self.total_kills}"
        sub_surf = font_med.render(sub, True, (240, 240, 240))
        sub_rect = sub_surf.get_rect(center=(cx, text_rect.bottom + 40))
        info_bg = pygame.Rect(sub_rect.x - 14, sub_rect.y - 8, sub_rect.width + 28, sub_rect.height + 16)
        pygame.draw.rect(screen, (0, 0, 0, 160), info_bg, border_radius=10)
        pygame.draw.rect(screen, (255, 220, 120), info_bg, 2, border_radius=10)
        screen.blit(sub_surf, sub_rect)

        # 9) الأزرار
        self.play_again_btn.color = (70, 120, 220)
        self.play_again_btn.hover_color = (90, 150, 255)
        self.menu_btn.color = (230, 180, 60)
        self.menu_btn.hover_color = (255, 210, 80)
        self.play_again_btn.draw(screen)
        self.menu_btn.draw(screen)

        # 10) طبقة التعتيم النهائية (خفيفة)
        if self.fade_alpha > 0:
            screen.blit(self.fade_surface, (0, 0))
    
    
    def handle_event(self, event) -> str | None:
        """معالجة الأحداث والاختيارات"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.play_again_btn.hit(event.pos):
                return "restart"
            elif self.menu_btn.hit(event.pos):
                return "menu"
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r or event.key == pygame.K_RETURN:  # R أو ENTER لإعادة اللعب
                return "restart"
            elif event.key == pygame.K_m:  # M للقائمة الرئيسية
                return "menu"
            elif event.key == pygame.K_ESCAPE:  # ESC للخروج
                return "quit"
        
        return None

def show_victory_screen(screen: pygame.Surface, clock: pygame.time.Clock, score: int = 0, total_kills: int = 0) -> str:
    """عرض شاشة النصر وانتظار اختيار اللاعب"""
    victory_scene = VictoryScene(screen, score, total_kills)
    
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

# 🔥 --- (جديد) --- دالة لإنشاء مؤثرات الخلفية برمجياً ---
# 🔥 --- (جديد ومحسن) --- دالة لإنشاء مؤثرات الخلفية برمجياً ---
def generate_background_effects(level: int, effects_dict: dict, W: int, H: int):
    """
    ينشئ ويخزن المؤثرات البرمجية (نجوم، شقوق، بقع) للخلفية.
    🔥 يرسمها مسبقاً على سطح واحد كبير لتحقيق أقصى أداء.
    """
    effects_dict.clear() # تنظيف المؤثرات القديمة
    rng = random.Random(level) # استخدام نفس البذرة لنفس المستوى

    # 1. إنشاء "اللوحة" الكبيرة
    # استخدم convert() لزيادة سرعة الرسم (blit) لاحقاً
    bg_surf = pygame.Surface((W, H)).convert() 

    # 2. ملء اللون الأساسي
    base_col = LEVEL_COLORS.get(level, (166, 98, 42))
    bg_surf.fill(base_col)

    # 3. رسم المؤثرات الثابتة على "اللوحة"
    if level == 2: # مدينة - شبكة بلاط
        tile_size = 80
        grid_color = (100, 100, 100)
        for x in range(0, W, tile_size):
            pygame.draw.line(bg_surf, grid_color, (x, 0), (x, H), 1)
        for y in range(0, H, tile_size):
            pygame.draw.line(bg_surf, grid_color, (0, y), (W, y), 1)

    elif level == 3: # غابة
        for _ in range(400): # 400 بقعة عشب
            x = rng.randint(0, W)
            y = rng.randint(0, H)
            r = rng.randint(15, 45) # نصف قطر
            col_darken = rng.randint(5, 20)
            col = (
                max(0, LEVEL_COLORS[3][0] - col_darken),
                max(0, LEVEL_COLORS[3][1] - col_darken),
                max(0, LEVEL_COLORS[3][2] - col_darken)
            )
            pygame.draw.circle(bg_surf, col, (x, y), r)

    elif level == 4: # فضاء
        for _ in range(1000): # 1000 نجمة
            x = rng.randint(0, W)
            y = rng.randint(0, H)
            r = rng.randint(1, 3) # حجم النجمة
            brightness = rng.randint(150, 255)
            col = (brightness, brightness, brightness)
            pygame.draw.circle(bg_surf, col, (x, y), r)

    elif level == 5: # بركان
        crack_color = (20, 10, 10) # لون الشقوق (أسود مائل للأحمر)
        for _ in range(150): # 150 شرخ
            x1 = rng.randint(0, W)
            y1 = rng.randint(0, H)
            angle = rng.uniform(0, 2 * math.pi)
            length = rng.randint(50, 200)
            x2 = x1 + int(math.cos(angle) * length)
            y2 = y1 + int(math.sin(angle) * length)
            width = rng.randint(2, 5)
            pygame.draw.line(bg_surf, crack_color, (x1, y1), (x2, y2), width)

    # 4. تخزين "اللوحة" الجاهزة
    effects_dict["pre_rendered_bg"] = bg_surf

# 🔥 --- (جديد) --- دالة لرسم الخلفية البرمجية ---
# 🔥 --- (جديد ومحسن) --- دالة لرسم الخلفية البرمجية ---
def draw_level_background(screen: pygame.Surface, level: int, cam: Camera, effects_dict: dict):
    """
    يرسم الخلفية: يستخدم "اللوحة" المرسومة مسبقاً.
    """
    # 1. احصل على "اللوحة" المرسومة مسبقاً
    bg_surf = effects_dict.get("pre_rendered_bg")

    if bg_surf:
        # 2. احسب الجزء المرئي فقط من "اللوحة" بناءً على الكاميرا
        visible_area = pygame.Rect(int(cam.x), int(cam.y), WINDOW_W, WINDOW_H)

        # 3. ارسم ذلك الجزء فقط على الشاشة (هذا سريع جداً!)
        screen.blit(bg_surf, (0, 0), area=visible_area)
    else:
        # (كود احتياطي إذا فشل التحميل)
        current_bg_color = LEVEL_COLORS.get(level, (166, 98, 42)) 
        screen.fill(current_bg_color)
# 🔥 --- (جديد) --- دالة لتحميل صورة Game Over ---
def load_game_over_image():
    """تحميل وتجهيز صورة Game Over."""
    global GAME_OVER_IMAGE
    try:
        path = os.path.join("images", "360_F_693042027_th0Yf1aofOwdQdabsMVLRtNieakvmDGr.jpg")
        if os.path.isfile(path):
            # تحميل الصورة وتحويلها
            img = pygame.image.load(path).convert_alpha() # استخدم convert_alpha للصور الشفافة
            
            # 🔥 --- (التعديل هنا) ---
            # استخدمنا WINDOW_W و WINDOW_H بدلاً من SCREEN_W و SCREEN_H
            GAME_OVER_IMAGE = pygame.transform.scale(img, (WINDOW_W, WINDOW_H))
            
            print("✅ Loaded and scaled game_over.png")
        else:
            print(f"❌ game_over.png not found at {path}. Game Over will be text-based.")
    except Exception as e:
        print(f"❌ Error loading game_over.png: {e}. Game Over will be text-based.")         

# الآن في دالة run_game، عدل جزء إكمال المستوى 6 ليظهر شاشة النصر:
# ---------------- Game Loop ----------------
# ---------------- Game Loop ----------------
def run_game(screen: pygame.Surface, clock: pygame.time.Clock, version: str = "", *, character: str = "player") -> str | None:
    global CURRENT_SKIN
    _maybe_music()
    
    # 🔥 --- (جديد) --- تحميل صورة Game Over مرة واحدة ---
    load_game_over_image() 

    # أصوات (اختيارية)
    snd_shoot   = load_sound("shotgun-146188.mp3")
    snd_shotgun = load_sound("shotgun-146188.mp3")
    snd_hit     = load_sound("hit.wav")
    snd_pick    = load_sound("pickup.wav")
    snd_hurt    = load_sound("hurt.wav")
    snd_crate   = load_sound("crate.wav")
    snd_door    = load_sound("door.wav")  # صوت للباب
    snd_grenade = load_sound("grenade_throw.wav")  # صوت القنبلة
    
    level_no = 1
    score = 0
    kills = 0
    total_kills = 0  # 🔥 إجمالي الزومبي المقتولين

    # --- Health / Hearts ---
    hearts_max = 4        # ← عدد القلوب الكلي
    health     = hearts_max
    heart_img  = load_image_to_height("heart.png", 24)  # اختياري
    damage_cd  = 0.0      # invincibility frames بعد الضربة
    DAMAGE_IFRAMES = 1.0  # ثانية حصانة

    show_hud = True
    show_minimap = True  # 🔥 إظهار الخريطة المصغرة

    # 🔥 === نظام الأسلحة الجديد ===
    weapon_manager = WeaponManager(player_id=1)
    
    # 🔥 === نظام الخريطة المصغرة ===
    minimap = Minimap(WORLD_W, WORLD_H, WINDOW_W, WINDOW_H, size=160)
    
    # 🔥 === مدير قائمة المتصدرين ===
    leaderboard_manager = LeaderboardManager()

    # أسلحة قديمة (للتوافق مع الكود القديم)
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
    # 🔥 إنشاء اللاعب مع المظهر المختار
    skin_color = get_skin_color(CURRENT_SKIN)
    enable_skin = (CURRENT_SKIN != "none")
    p = Player(x=p_spawn_x, y=p_spawn_y, speed=base_speed, skin_color=skin_color, sprite_prefix=character, enable_skin=enable_skin)

    # كاميرا
    cam = Camera(WORLD_W, WORLD_H, WINDOW_W, WINDOW_H)
    cam.follow(p.rect)  # موضعة أولية

    # كائنات
    enemies: list[Zombie] = []
    enemies: list[Zombie] = []
    # bullets: list[Bullet] = []  <-- REMOVED, usage replaced by weapon_manager.bullets
    pickups: list["Pickup"] = []
    pickups: list["Pickup"] = []
    crates:  list[SpeedCrate] = []
    blood_fx: list[BloodParticle] = []
    
    # 🔥 الباب الجديد
    level_door: LevelDoor | None = None

    # Pickups (medkit / ammo)
    class Pickup:
        def __init__(self, x: float, y: float, kind: str):
            self.x, self.y, self.kind = float(x), float(y), kind  # "medkit" | "shotgun_ammo" | "grenade_ammo"
            self.w, self.h = 32, 32
            self.alive = True
        @property
        def rect(self) -> pygame.Rect: return pygame.Rect(int(self.x), int(self.y), self.w, self.h)
        def draw(self, screen: pygame.Surface, cam: Camera):
            if not self.alive: return
            
            # 🔥 حركة طفو
            t = pygame.time.get_ticks() / 1000.0
            bob_offset = math.sin(t * 3) * 4.0
            
            dx, dy = cam.apply_xy(self.x, self.y)
            dx = int(dx)
            dy = int(dy + bob_offset)
            
            w, h = 40, 30
            
            if self.kind == "medkit":
                # 🏥 حقيبة إسعافات احترافية
                case_color = (240, 240, 245)
                cross_color = (220, 20, 60)
                handle_color = (60, 60, 60)
                shadow_color = (180, 180, 190)
                
                shadow_width = w + int(math.sin(t*3)*4)
                pygame.draw.ellipse(screen, (0, 0, 0, 60), (dx + (w-shadow_width)//2, dy + h + 10 - bob_offset, shadow_width, 8))
                pygame.draw.rect(screen, shadow_color, (dx + 4, dy - 4, w, h), border_radius=6)
                rect = pygame.Rect(dx, dy, w, h)
                pygame.draw.rect(screen, case_color, rect, border_radius=6)
                pygame.draw.rect(screen, (200, 200, 210), rect, width=2, border_radius=6)
                pygame.draw.rect(screen, handle_color, (dx + w//2 - 6, dy - 8, 12, 8), border_radius=2)
                pygame.draw.rect(screen, (0,0,0), (dx + w//2 - 4, dy - 6, 8, 4))
                cw, ch = 8, 20
                cx, cy = dx + w//2, dy + h//2
                pygame.draw.rect(screen, cross_color, (cx - cw//2, cy - ch//2, cw, ch), border_radius=2)
                pygame.draw.rect(screen, cross_color, (cx - ch//2, cy - cw//2, ch, cw), border_radius=2)
                pygame.draw.ellipse(screen, (255, 255, 255), (dx + 4, dy + 4, 12, 8))

            elif self.kind == "shotgun_ammo" or self.kind == "grenade_ammo":
                # 📦 صندوق ذخيرة عسكري 3D
                if self.kind == "shotgun_ammo":
                    main_color = (180, 40, 40); light_color = (220, 60, 60); dark_color = (120, 30, 30)
                    icon_color = (255, 200, 50); label = "SHELLS"
                else:
                    main_color = (50, 80, 50); light_color = (70, 100, 70); dark_color = (30, 50, 30)
                    icon_color = (200, 200, 200); label = "NADES"

                shadow_width = w + int(math.sin(t*3)*2)
                pygame.draw.ellipse(screen, (0, 0, 0, 80), (dx + (w-shadow_width)//2, dy + h + 5 - bob_offset, shadow_width, 8))
                pygame.draw.rect(screen, dark_color, (dx + 4, dy - 4, w, h), border_radius=4)
                rect = pygame.Rect(dx, dy, w, h)
                pygame.draw.rect(screen, main_color, rect, border_radius=4)
                pygame.draw.rect(screen, light_color, rect, width=2, border_radius=4)
                corner_len = 8; corner_color = (180, 180, 180)
                pygame.draw.line(screen, corner_color, (dx, dy), (dx + corner_len, dy), 2)
                pygame.draw.line(screen, corner_color, (dx, dy), (dx, dy + corner_len), 2)
                pygame.draw.line(screen, corner_color, (dx + w, dy + h), (dx + w - corner_len, dy + h), 2)
                pygame.draw.line(screen, corner_color, (dx + w, dy + h), (dx + w, dy + h - corner_len), 2)
                
                font = pygame.font.SysFont("arial", 9, bold=True)
                text_surf = font.render(label, True, icon_color)
                text_rect = text_surf.get_rect(center=rect.center)
                pygame.draw.rect(screen, (0, 0, 0, 100), text_rect.inflate(4, 2), border_radius=2)
                screen.blit(text_surf, text_rect)
            
            else:
                # 📦 صندوق غامض (Mystery Crate)
                box_color = (100, 80, 60); tape_color = (200, 180, 140)
                pygame.draw.ellipse(screen, (0, 0, 0, 80), (dx + 2, dy + h + 2, w - 4, 8))
                rect = pygame.Rect(dx, dy, w, h)
                pygame.draw.rect(screen, box_color, rect, border_radius=4)
                pygame.draw.rect(screen, (80, 60, 40), rect, width=2, border_radius=4)
                pygame.draw.line(screen, tape_color, (dx + w//2, dy), (dx + w//2, dy + h), 4)
                pygame.draw.line(screen, tape_color, (dx, dy + h//2), (dx + w, dy + h//2), 4)

    # مؤقتات
    spawn_t = 0.0
    pk_timer = 0.0
    crate_t = 0.0

    def reset_level(new_level: int):
        nonlocal enemies, pickups, kills, walls, spawn_t, pk_timer, crate_t, boost_t, health, damage_cd, level_door
        enemies = []; pickups = []; crates.clear(); blood_fx.clear()
        weapon_manager.bullets.clear(); weapon_manager.explosions.clear()
        kills = 0; spawn_t = 0.0; pk_timer = 0.0; crate_t = 0.0; boost_t = 0.0
        health = hearts_max; damage_cd = 0.0
        walls[:] = create_walls_for_level(new_level, WORLD_W, WORLD_H, tile=64)
        px, py = find_free_spawn(walls, WORLD_W, WORLD_H, p.w, p.h)
        p.x, p.y = px, py
        
        # 🔥 إنشاء الباب في موقع عشوائي
        door_x, door_y = find_door_location(walls, p.x, p.y, WORLD_W, WORLD_H)
        level_door = LevelDoor(door_x, door_y, new_level)
        
        cam.follow(p.rect, lerp=1.0)  # قفز للموضع الجديد
        
        # 🔥 --- أنشئ مؤثرات الخلفية لهذا المستوى ---
        generate_background_effects(new_level, BG_EFFECTS, WORLD_W, WORLD_H)
        
        # 🔥 تحديث جدران الخريطة المصغرة
        minimap.set_walls(walls)

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

            # إنشاء زومبي واحد فقط مع المستوى الحالي
            z = Zombie(float(x), float(y), level_no)
            if collide_rect_list(z.rect, walls):   # لا يولد داخل جدار
                continue
            if not far_from_player(p.x, p.y, z.x, z.y, min_dist=300.0):  # بعيد عن اللاعب
                continue
            enemies.append(z)
            return

    def fire_weapon():
        """🔥 إطلاق النار باستخدام نظام الأسلحة الجديد"""
        nonlocal pistol_cd, shotgun_cd
        
        if not weapon_manager.can_fire():
            return
        
        # الاتجاه
        dir_map = {"right": (1,0), "left": (-1,0), "up": (0,-1), "down": (0,1)}
        vx, vy = dir_map.get(p.facing, (1,0))
        bx = p.x + p.w/2
        by = p.y + p.h/2
        
        # حساب الهدف
        target_x = bx + vx * 100
        target_y = by + vy * 100
        
        # إطلاق النار
        # إطلاق النار
        # استبدال نقطة البداية بفوهة السلاح لمطابقة السبرايت بصرياً
        mx, my = get_muzzle_xy(p, target_x, target_y)
        weapon_manager.fire(mx, my, target_x, target_y)
        
        # (Removed old Bullet wrapper logic)
        
        # تشغيل الصوت المناسب
        current_weapon = weapon_manager.current_weapon
        if current_weapon == WeaponType.PISTOL and snd_shoot:
            snd_shoot.set_volume(game_settings.sfx_volume)
            snd_shoot.play()
        elif current_weapon == WeaponType.SHOTGUN and snd_shotgun:
            snd_shotgun.set_volume(game_settings.sfx_volume)
            snd_shotgun.play()
        elif current_weapon == WeaponType.GRENADE and snd_grenade:
            snd_grenade.set_volume(game_settings.sfx_volume)
            snd_grenade.play()
        elif current_weapon == WeaponType.GRENADE and snd_pick:
            snd_pick.set_volume(game_settings.sfx_volume)
            snd_pick.play()  # صوت بديل للقنبلة

    def fire_pistol():
        """للتوافق مع الكود القديم - يستخدم المسدس"""
        if weapon_manager.current_weapon != WeaponType.PISTOL:
            weapon_manager.switch_weapon(WeaponType.PISTOL)
        fire_weapon()

    def fire_shotgun():
        """للتوافق مع الكود القديم - يستخدم الشوتجن"""
        if weapon_manager.current_weapon != WeaponType.SHOTGUN:
            weapon_manager.switch_weapon(WeaponType.SHOTGUN)
        fire_weapon()

    def spawn_pickup():
        # 🔥 أنواع أكثر من الـ pickups
        kind = random.choice(["medkit", "shotgun_ammo", "grenade_ammo", "shotgun_ammo"])
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

    # 🔥 تهيئة الباب في المستوى الأول
    reset_level(level_no)
    
    # 🔥 تهيئة الخريطة المصغرة بالجدران
    minimap.set_walls(walls)

    # 🔥 --- (جديد) --- متغير للتحكم بحالة Game Over ---
    game_over_state = False

    running = True
    while running:

        # 🔥 --- (جديد) --- منطق شاشة Game Over ---
        # إذا كانت اللعبة "Game Over"، اعرض الشاشة وتوقف عن تحديث اللعبة
        if game_over_state:
            screen.fill((0, 0, 0)) # خلفية سوداء
            
            if GAME_OVER_IMAGE:
                # ارسم الصورة التي تم تحميلها
                screen.blit(GAME_OVER_IMAGE, (0, 0))
                # (يمكنك إضافة نص فوق الصورة إذا أردت)
                draw_shadow_text(screen, "Press [ENTER] to Play Again", (WINDOW_W // 2 - 150, WINDOW_H - 100), size=28, color=(255,255,255))
                draw_shadow_text(screen, "Press [ESC] to Quit to Menu", (WINDOW_W // 2 - 150, WINDOW_H - 60), size=28, color=(200,200,200))
            else:
                # كود احتياطي إذا لم يتم تحميل الصورة (يستخدم WINDOW_W الصحيح)
                draw_text(screen, "GAME OVER", WINDOW_W // 2, WINDOW_H // 2 - 50, color=(255, 0, 0), size=60, center=True)
                draw_text(screen, "Play Again? (Press ENTER)", WINDOW_W // 2, WINDOW_H // 2 + 50, color=(255, 255, 255), size=40, center=True)
                draw_text(screen, "Quit to Menu? (Press ESC)", WINDOW_W // 2, WINDOW_H // 2 + 100, color=(200, 200, 200), size=30, center=True)

            # معالجة الأحداث أثناء Game Over
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return None # خروج كامل
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_RETURN: # 'Enter'
                        return "start" # إشارة لإعادة التشغيل
                    if e.key == pygame.K_ESCAPE: # 'Escape'
                        return "menu" # إشارة للعودة للقائمة
                        
            pygame.display.flip()
            clock.tick(FPS) # استمر في تحديد FPS
            continue # 🔥 تخطي باقي حلقة اللعبة
        
        # --- إذا لم تكن اللعبة Game Over، استمر كالمعتاد ---

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
                # 🔥 تبديل الخريطة المصغرة
                if e.key == pygame.K_m:
                    show_minimap = not show_minimap
                    minimap.visible = show_minimap
                # 🔥 تبديل الأسلحة
                if e.key == pygame.K_1:
                    weapon_manager.switch_weapon(WeaponType.PISTOL)
                if e.key == pygame.K_2:
                    weapon_manager.switch_weapon(WeaponType.SHOTGUN)
                if e.key == pygame.K_3:
                    weapon_manager.switch_weapon(WeaponType.GRENADE)
                if e.key == pygame.K_SPACE:
                    # Space → إطلاق النار بالسلاح الحالي
                    fire_weapon()
                # 🔥 قدرات الكوماندوز الخاصة
                if e.key == pygame.K_LSHIFT or e.key == pygame.K_RSHIFT:
                    # Shift → قدرة الاندفاع
                    # حساب اتجاه الاندفاع من facing (لأن dx, dy لم يتم حسابهما بعد)
                    facing_dir_map = {"right": (1, 0), "left": (-1, 0), "up": (0, -1), "down": (0, 1)}
                    dash_dx, dash_dy = facing_dir_map.get(p.facing, (1, 0))
                    p.activate_dash(dash_dx, dash_dy)
                if e.key == pygame.K_LCTRL or e.key == pygame.K_RCTRL:
                    # Ctrl → قدرة الدرع
                    p.activate_shield()
            if e.type == pygame.MOUSEBUTTONDOWN:
                if e.button == 1:   # Left click → Pistol
                    fire_pistol()
                elif e.button == 3: # Right click → Shotgun
                    fire_shotgun()

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

        # 🔥 تجنب إعادة تعيين السرعة إذا كان اللاعب يندفع!
        if boost_t > 0:
            boost_t -= dt
            if not p.is_dashing:  # لا تتعارض مع الاندفاش
                p.speed = base_speed * boost_mult
        elif not p.is_dashing:  # لا تعيد تعيين السرعة أثناء الاندفاش!
            p.speed = base_speed

        # 🔥 تحديث قدرات الكوماندوز (Dash و Shield)
        p.update_abilities(dt)

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
        if pk_timer >= 4.0:
            pk_timer = 0.0
            # احتمالية متساوية (50%)
            if random.random() < 0.5:
                spawn_pickup()

        crate_t += dt
        if crate_t >= 4.0:
            crate_t = 0.0
            # احتمالية متساوية (50%)
            if len(crates) < 4 and random.random() < 0.5:
                spawn_crate()

        player_center = pygame.Vector2(p.x + p.w/2, p.y + p.h/2)
        for i, en in enumerate(enemies):
            nearby = [other for j, other in enumerate(enemies)
                      if j != i and (abs(other.x - en.x) < 72 and abs(other.y - en.y) < 72)]
            en.update(player_center, walls, dt, nearby)

        dead_indices = set()
        # 🔥 === معالجة اصطدام الرصاص (النظام الجديد) ===
        # ملاحظة: weapon_manager.update(dt) يتم استدعاؤه لاحقاً في قسم HUD لرسم الانفجارات
        # لكن نحتاج للتحقق من الاصطدامات هنا أو هناك. 
        # الأفضل هو تحديثه هنا لنضمن تزامن المنطق.
        
        # سنقوم بتحديث المدير هنا، ثم نرسمه لاحقاً.
        # (تم إزالة استدعاء update من قسم HUD لتجنب التكرار)
        explosions = weapon_manager.update(dt)

        # معالجة الانفجارات (ضرر الزومبي واللاعب)
        for ex, ey, radius, damage, _owner_id in explosions:
            # 1. ضرر الزومبي
            for en in enemies[:]:
                if en.hp > 0:
                    dist = math.sqrt((en.x - ex)**2 + (en.y - ey)**2)
                    if dist < radius:
                        dmg = int(damage * (1 - dist/radius))
                        en.hp -= dmg
                        if en.hp <= 0:
                            dead_indices.add(enemies.index(en))
                            # (Logic copied from below to ensure consistency)
                            kills += 1
                            total_kills += 1
                            score += 15 + (en.level * 5)
                            for _ in range(12):
                                blood_fx.append(BloodParticle(en.x + en.w/2, en.y + en.h/2))
            
            # 2. ضرر اللاعب (اختياري، يمكن إضافته هنا)
            p_dist = math.sqrt((p.x + p.w/2 - ex)**2 + (p.y + p.h/2 - ey)**2)
            if p_dist < radius * 0.6:
                health -= 1
                damage_cd = DAMAGE_IFRAMES
                if snd_hurt: snd_hurt.play()
                cam.trigger_shake(15.0)

        # معالجة اصطدام الرصاص المباشر
        for b in weapon_manager.bullets:
            if not b.alive: continue
            
            # 1. اصطدام بالجدران
            b_rect = pygame.Rect(int(b.x)-3, int(b.y)-3, 6, 6)
            if collide_rect_list(b_rect, walls):
                b.alive = False
                continue
                
            # 2. اصطدام بالأعداء
            for idx, en in enumerate(enemies):
                if en.rect.collidepoint(int(b.x), int(b.y)):
                    # إذا كانت قنبلة، لا تنفجر باللمس (أو يمكن جعلها تنفجر)
                    # حالياً القنابل تنفجر بالوقت.
                    if b.is_grenade:
                        continue # القنبلة ترتد أو تمر (أو يمكن تفعيلها)
                        
                    en.hp -= b.damage
                    b.alive = False
                    if snd_hit: snd_hit.play()
                    if en.hp <= 0:
                        dead_indices.add(idx)
                        kills += 1
                        total_kills += 1
                        score += 10 + (en.level * 5)
                        ex, ey = en.x + en.w/2, en.y + en.h/2
                        for _ in range(16):
                            blood_fx.append(BloodParticle(ex, ey))
                    break
        if dead_indices:
            enemies = [en for i, en in enumerate(enemies) if i not in dead_indices]

        # 🔥 تفعيل الباب عندما يقتل اللاعب عدد كافي من الزومبي
        if level_door and not level_door.active and kills >= goal_kills:
            level_door.activate()
            if snd_door: snd_door.play()

        # 🔥 التحقق من دخول اللاعب إلى الباب
        if level_door and level_door.active and p.rect.colliderect(level_door.rect):
            if level_no < 6:
                level_no += 1
                reset_level(level_no)
                continue  # تخطي الباقي والبدء من جديد
            else:
                # 🔥 === حفظ النتيجة في قائمة المتصدرين ===
                if leaderboard_manager.is_high_score(score):
                    # إدخال اسم اللاعب
                    player_name = show_name_input(screen, clock, score, total_kills, level_no)
                    rank = leaderboard_manager.add_score(player_name, score, total_kills, level_no)
                    print(f"🏆 New High Score! Rank: {rank}")
                
                # عرض شاشة النصر
                choice = show_victory_screen(screen, clock, score, total_kills)
                
                if choice == "restart":
                    return "start"
                elif choice == "menu":
                    return "menu"
                elif choice == "quit":
                    return None
                else:
                    return "menu"

        # تحديث نظام الضرر ليتناسب مع مستوى الزومبي
        if damage_cd <= 0.0:
            for en in enemies:
                if p.rect.colliderect(en.rect):
                    # 🔥 التحقق من الدرع (للكوماندوز)
                    if p.is_shielded():
                        # دفع العدو للخلف بدلاً من اللاعب عند تفعيل الدرع
                        en.x -= (p.x - en.x) * 0.1
                        en.y -= (p.y - en.y) * 0.1
                        continue  # لا ضرر!

                    # الضرر يعتمد على مستوى الزومبي
                    damage = en.damage
                    health -= damage
                    damage_cd = DAMAGE_IFRAMES
                    if snd_hurt: snd_hurt.play()
                    cam.trigger_shake(10.0) # (10.0 هي شدة الاهتزاز، يمكنك تغييرها)
                    push_force = 0.08 + (en.level * 0.02)
                    
                    # دفع اللاعب للخلف بقوة تعتمد على مستوى الزومبي
                    push_force = 0.08 + (en.level * 0.02)  # زيادة قوة الدفع مع المستوى
                    p.x = clamp(p.x - (player_center.x - en.x) * push_force, 0, WORLD_W - p.w)
                    p.y = clamp(p.y - (player_center.y - en.y) * push_force, 0, WORLD_H - p.h)
                    
                    # 🔥 --- (التعديل الأهم هنا) ---
                    # استبدلنا استدعاء show_game_over_screen
                    # بتعيين الحالة فقط
                    if health <= 0:
                        if not game_over_state: # قم بتشغيل هذا مرة واحدة فقط
                            game_over_state = True
                            pygame.mixer.music.fadeout(1000)
                            
                            # 🔥 === حفظ النتيجة في قائمة المتصدرين ===
                            if leaderboard_manager.is_high_score(score):
                                # إدخال اسم اللاعب
                                player_name = show_name_input(screen, clock, score, total_kills, level_no)
                                rank = leaderboard_manager.add_score(player_name, score, total_kills, level_no)
                                print(f"🏆 New High Score! Rank: {rank}")
                        break # اخرج من حلقة الأعداء
                    # --- (نهاية التعديل) ---
                    break  # تجنب أضرار متعددة في نفس الإطار

        for pk in pickups:
            if pk.alive and p.rect.colliderect(pk.rect):
                pk.alive = False
                if pk.kind == "medkit":
                    health = min(hearts_max, health + 1)
                elif pk.kind == "shotgun_ammo":
                    # 🔥 إضافة الذخيرة لنظام الأسلحة الجديد
                    weapon_manager.add_ammo(WeaponType.SHOTGUN, 5)
                    shotgun_ammo += 3  # للتوافق مع الكود القديم
                elif pk.kind == "grenade_ammo":
                    # 🔥 إضافة قنابل
                    weapon_manager.add_ammo(WeaponType.GRENADE, 2)
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

        # 🔥 تحديث الباب
        if level_door:
                level_door.update(dt, p.x, p.y)  # تمرير موقع اللاعب للملاحة


        # -------- Update Blood FX --------
        for pfx in blood_fx:
            pfx.update(dt)
        blood_fx = [pfx for pfx in blood_fx if pfx.alive]
        cam.update(dt)
        # -------- Camera follow --------
        cam.follow(p.rect)

        # -------- Render (apply camera) --------
        
        # 🔥 --- (تنظيف) --- تم إزالة كود الرسم القديم المكرر ---

        # 🔥 --- (جديد) --- رسم الخلفية البرمجية المذهلة ---
        draw_level_background(screen, level_no, cam, BG_EFFECTS)

        # 🔥 --- (مُعدل) --- رسم الجدران بالألوان الديناميكية ---
        
        # احصل على أسلوب الألوان الصحيح لهذا المستوى
        wall_style = LEVEL_WALL_STYLES.get(level_no, DEFAULT_WALL_STYLE)
        fill_col = wall_style["fill"]
        edge_col = wall_style["edge"]
        inner_col = wall_style["inner"]

        for r in walls:
            sr = cam.apply_rect(r)
            
            # تحسين: لا ترسم الجدران البعيدة عن الشاشة
            if not sr.colliderect(screen.get_rect()):
                continue
            
            # ارسم الجدار بالألوان الصحيحة
            pygame.draw.rect(screen, fill_col, sr, border_radius=8)
            pygame.draw.rect(screen, edge_col, sr, width=2, border_radius=8)
            inner = sr.inflate(-6, -6)
            if inner.w > 0 and inner.h > 0:
                pygame.draw.rect(screen, inner_col, inner, width=1, border_radius=6)

       
        for pfx in blood_fx:
            pfx.draw(screen, cam)

       
        for pk in pickups: pk.draw(screen, cam)
        for cr in crates:  cr.draw(screen, cam)
        for en in enemies: en.draw(screen, cam)
        
        # 🔥 رسم الباب
        if level_door:
            level_door.draw(screen, cam)

        # Player - 🔥 استخدام المظهر المختار
        dx, dy = cam.apply_xy(p.x, p.y)
        
        # 🔥 رسم حلقة ملونة تحت الشخصية (مؤشر المظهر)
        skin_color = p.skin_color
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
            if damage_cd > 0 and int(pygame.time.get_ticks() * 0.02) % 2 == 0:
                pass  # تخطي الرسم لإحساس الوميض
            else:
                screen.blit(spr, (dx, dy))
        else:
            # 🔥 رسم مربع بلون المظهر إذا لم توجد صورة
            color = skin_color if damage_cd <= 0 else (255, 220, 120)
            pygame.draw.rect(screen, color, pygame.Rect(dx, dy, p.w, p.h), border_radius=8)
            # حدود داكنة
            darker = (max(0, skin_color[0]-50), max(0, skin_color[1]-50), max(0, skin_color[2]-50))
            pygame.draw.rect(screen, darker, pygame.Rect(dx, dy, p.w, p.h), width=3, border_radius=8)
            # عيون
            eye_y = int(dy + p.h * 0.35)
            pygame.draw.circle(screen, (255, 255, 255), (int(dx + p.w * 0.35), eye_y), 4)
            pygame.draw.circle(screen, (255, 255, 255), (int(dx + p.w * 0.65), eye_y), 4)
            pygame.draw.circle(screen, (0, 0, 0), (int(dx + p.w * 0.35), eye_y), 2)
            pygame.draw.circle(screen, (0, 0, 0), (int(dx + p.w * 0.65), eye_y), 2)

        # Bullets
        # Bullets - Handled by weapon_manager.draw_bullets()
        
        # 🔥 === رسم تأثيرات الكوماندوز ===
        if p.sprite_prefix == "commando":
            player_screen_x, player_screen_y = cam.apply_xy(p.x, p.y)
            player_center_x = int(player_screen_x + p.w // 2)
            player_center_y = int(player_screen_y + p.h // 2)
            
            # رسم الدرع إذا كان نشطاً
            if p.shield_active:
                shield_radius = max(p.w, p.h) // 2 + 15
                
                # تأثير نبض الدرع
                pulse = 0.85 + 0.15 * math.sin(p.shield_timer * 8)
                alpha = int(120 * pulse)
                
                # رسم الدرع (دائرة شفافة زرقاء متوهجة)
                shield_surf = pygame.Surface((shield_radius * 2 + 20, shield_radius * 2 + 20), pygame.SRCALPHA)
                # طبقة خارجية متوهجة
                pygame.draw.circle(shield_surf, (50, 150, 255, alpha // 2),
                                 (shield_radius + 10, shield_radius + 10), int(shield_radius * pulse) + 8)
                # الدرع الرئيسي
                pygame.draw.circle(shield_surf, (50, 150, 255, alpha),
                                 (shield_radius + 10, shield_radius + 10), int(shield_radius * pulse))
                # حدود الدرع
                pygame.draw.circle(shield_surf, (150, 220, 255, min(255, alpha + 80)),
                                 (shield_radius + 10, shield_radius + 10), int(shield_radius * pulse), 3)
                # خط داخلي
                pygame.draw.circle(shield_surf, (200, 240, 255, alpha // 2),
                                 (shield_radius + 10, shield_radius + 10), int(shield_radius * pulse * 0.7), 2)
                screen.blit(shield_surf, (player_center_x - shield_radius - 10, player_center_y - shield_radius - 10))
            
            # رسم تأثير الاندفاع
            if p.is_dashing:
                dash_dx, dash_dy = p.dash_direction
                trail_length = 50
                
                # رسم ذيل متلاشي خلف الشخصية
                for i in range(8):
                    alpha = int(200 * (1 - i / 8))
                    size = 12 - i
                    trail_x = int(player_center_x - dash_dx * trail_length * (i + 1) / 8)
                    trail_y = int(player_center_y - dash_dy * trail_length * (i + 1) / 8)
                    
                    trail_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                    # لون ذهبي/برتقالي متوهج
                    pygame.draw.circle(trail_surf, (255, 200, 50, alpha), (size, size), size)
                    pygame.draw.circle(trail_surf, (255, 150, 0, alpha // 2), (size, size), size + 3)
                    screen.blit(trail_surf, (trail_x - size, trail_y - size))
                
                # وميض حول اللاعب أثناء الاندفاع
                glow_surf = pygame.Surface((p.w + 30, p.h + 30), pygame.SRCALPHA)
                pygame.draw.ellipse(glow_surf, (255, 200, 50, 100), (0, 0, p.w + 30, p.h + 30))
                screen.blit(glow_surf, (player_screen_x - 15, player_screen_y - 15))

        # HUD
        if show_hud:
            hud_x, hud_y = 16, 14
            draw_shadow_text(screen, f"Kills: {kills}/{goal_kills}", (hud_x, hud_y), size=28, color=(0,0,0))
            draw_shadow_text(screen, f"Level: {level_no}", (hud_x+180, hud_y), size=28, color=(0,0,0))
            draw_shadow_text(screen, f"Score: {score}", (hud_x+310, hud_y), size=28, color=(0,0,0))
            
            # 🔥 رسالة الباب
            if level_door and level_door.active:
                draw_shadow_text(screen, "DOOR ACTIVE! Find the glowing door!", (hud_x, hud_y + 90), size=22, color=(255, 255, 0))
            
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
            
            # 🔥 === واجهة الأسلحة الجديدة ===
            weapon_manager.draw_hud(screen, 16, WINDOW_H - 80)
            
            # 🔥 === واجهة قدرات الكوماندوز ===
            if p.sprite_prefix == "commando":
                ability_status = p.get_ability_status()
                ability_x = WINDOW_W - 180  # الجانب الأيمن من الشاشة
                ability_y = WINDOW_H - 120
                
                # خلفية شبه شفافة للقدرات
                ability_bg = pygame.Surface((170, 110), pygame.SRCALPHA)
                ability_bg.fill((0, 0, 0, 150))
                pygame.draw.rect(ability_bg, (255, 200, 0), (0, 0, 170, 110), width=2, border_radius=8)
                screen.blit(ability_bg, (ability_x - 10, ability_y - 10))
                
                # عنوان
                draw_shadow_text(screen, "⚡ ABILITIES", (ability_x, ability_y - 5), size=16, color=(255, 200, 0))
                
                # === قدرة الاندفاع (Dash) ===
                dash_y = ability_y + 20
                dash_ready = ability_status.get("dash_ready", False)
                dash_cd = ability_status.get("dash_cooldown", 0)
                is_dashing = ability_status.get("is_dashing", False)
                
                # لون الحالة
                if is_dashing:
                    dash_color = (255, 200, 50)  # أصفر ذهبي أثناء الاندفاع
                    dash_text = "DASHING!"
                elif dash_ready:
                    dash_color = (100, 255, 100)  # أخضر = جاهز
                    dash_text = "READY [SHIFT]"
                else:
                    dash_color = (150, 150, 150)  # رمادي = انتظار
                    dash_text = f"Wait {dash_cd:.1f}s"
                
                # رسم أيقونة الاندفاع (سهم)
                pygame.draw.polygon(screen, dash_color, [
                    (ability_x, dash_y + 10),
                    (ability_x + 15, dash_y + 5),
                    (ability_x + 15, dash_y + 15)
                ])
                draw_shadow_text(screen, f"DASH: {dash_text}", (ability_x + 22, dash_y), size=14, color=dash_color)
                
                # شريط cooldown للاندفاع
                bar_width = 140
                bar_height = 6
                bar_x = ability_x
                bar_y = dash_y + 22
                pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height), border_radius=3)
                if dash_ready or is_dashing:
                    pygame.draw.rect(screen, dash_color, (bar_x, bar_y, bar_width, bar_height), border_radius=3)
                else:
                    fill_ratio = 1 - (dash_cd / 2.5)  # 2.5 ثواني cooldown
                    pygame.draw.rect(screen, dash_color, (bar_x, bar_y, int(bar_width * fill_ratio), bar_height), border_radius=3)
                
                # === قدرة الدرع (Shield) ===
                shield_y = ability_y + 55
                shield_ready = ability_status.get("shield_ready", False)
                shield_cd = ability_status.get("shield_cooldown", 0)
                shield_active = ability_status.get("shield_active", False)
                
                # لون الحالة
                if shield_active:
                    shield_color = (50, 150, 255)  # أزرق ساطع = نشط
                    shield_text = "ACTIVE!"
                elif shield_ready:
                    shield_color = (100, 255, 100)  # أخضر = جاهز
                    shield_text = "READY [CTRL]"
                else:
                    shield_color = (150, 150, 150)  # رمادي = انتظار
                    shield_text = f"Wait {shield_cd:.1f}s"
                
                # رسم أيقونة الدرع (دائرة)
                pygame.draw.circle(screen, shield_color, (ability_x + 8, shield_y + 8), 8, width=2)
                draw_shadow_text(screen, f"SHIELD: {shield_text}", (ability_x + 22, shield_y), size=14, color=shield_color)
                
                # شريط cooldown للدرع
                bar_y = shield_y + 22
                pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height), border_radius=3)
                if shield_ready:
                    pygame.draw.rect(screen, shield_color, (bar_x, bar_y, bar_width, bar_height), border_radius=3)
                elif shield_active:
                    # شريط المدة المتبقية
                    shield_timer = p.shield_timer
                    remaining_ratio = 1 - (shield_timer / 2.0)  # 2 ثواني مدة
                    pygame.draw.rect(screen, shield_color, (bar_x, bar_y, int(bar_width * remaining_ratio), bar_height), border_radius=3)
                else:
                    fill_ratio = 1 - (shield_cd / 10.0)  # 10 ثواني cooldown
                    pygame.draw.rect(screen, shield_color, (bar_x, bar_y, int(bar_width * fill_ratio), bar_height), border_radius=3)
            
            # 🔥 تحديث نظام الأسلحة (تم نقله للأعلى)
            # explosions = weapon_manager.update(dt) <--- MOVED UP
            # (تمت معالجة الانفجارات في حلقة التحديث الرئيسية)
            
            # رسم رصاصات الأسلحة والانفجارات
            weapon_manager.draw_bullets(screen, (int(cam.x), int(cam.y)))
            weapon_manager.draw_explosions(screen, (int(cam.x), int(cam.y)))
            
            # FPS
            draw_text(screen, f"{int(clock.get_fps()):02d} FPS", (WINDOW_W-100, 10), size=18, color=(220,220,220))
            
            # 🔥 === الخريطة المصغرة ===
            if show_minimap:
                # تحويل الزومبي لقاموس للخريطة
                zombies_dict = {i: en for i, en in enumerate(enemies) if en.hp > 0}
                minimap.draw(
                    screen,
                    (p.x, p.y),
                    {},  # لا يوجد لاعبون آخرون في وضع اللاعب الفردي
                    zombies_dict,
                    level_door,
                    walls
                )
            
            if level_door:
                level_door.draw_navigation(screen, p.x, p.y)
        
        pygame.display.flip()
        clock.tick(FPS)

# (باقي الملف: _draw_center_panel, _wait_enter_or_quit, etc.)
# ---------------- Victory Scene ----------------



class VictoryScene:
    def __init__(self, screen, score=0, totalkills=0):
        self.screen = screen
        self.W, self.H = screen.get_size()
        self.score = score
        self.totalkills = totalkills
        self.text_glow_timer = 0.0
        self.confetti_particles = self.create_confetti_particles()
        self.golden_overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        self.golden_overlay.fill((255, 215, 0, 20))  # light golden overlay

    def create_confetti_particles(self):
        particles = []
        colors = [(255, 50, 50), (50, 255, 50), (255, 255, 255), (255, 50, 255)]
        for _ in range(100):
            particle = {
                "x": random.randint(0, self.W),
                "y": random.randint(-100, 0),
                "color": random.choice(colors),
                "size": random.randint(4, 8),
                "speed": random.uniform(2, 6),
                "sway": random.uniform(-1, 1),
                "rotation": random.uniform(0, 360),
            }
            particles.append(particle)
        return particles

    def update(self, dt):
        self.text_glow_timer += dt
        for p in self.confetti_particles:
            p["y"] += p["speed"]
            p["x"] += p["sway"]
            p["rotation"] += 2
            if p["y"] > self.H:
                p["y"] = random.randint(-100, 0)
                p["x"] = random.randint(0, self.W)

    def draw(self):
        self.screen.fill((0, 0, 0))  # Black background

        # Draw confetti particles
        for p in self.confetti_particles:
            particle_surf = pygame.Surface((p["size"], p["size"]), pygame.SRCALPHA)
            pygame.draw.rect(particle_surf, p["color"], (0, 0, p["size"], p["size"]))
            rotated = pygame.transform.rotate(particle_surf, p["rotation"])
            rect = rotated.get_rect(center=(p["x"], p["y"]))
            self.screen.blit(rotated, rect.topleft)
        
        # Golden overlay for glow effect
        self.screen.blit(self.golden_overlay, (0, 0))

        # Victory text glow
        glow_intensity = (math.sin(self.text_glow_timer * 3) + 1) * 0.3 + 0.4
        main_color = (255, 215, 0)  # gold color
        glow_color = (255, 255, 150, int(200 * glow_intensity))

        font_large = pygame.font.Font(None, 82)
        text_surf = font_large.render("VICTORY!", True, main_color)
        text_rect = text_surf.get_rect(center=(self.W // 2, self.H // 3 - 60))

        glow_surf = font_large.render("VICTORY!", True, glow_color)
        for offset in [(2,2), (-2,2), (2,-2), (-2,-2), (0,3), (0,-3), (3,0), (-3,0)]:
            self.screen.blit(glow_surf, (text_rect.x + offset[0], text_rect.y + offset[1]))
        self.screen.blit(text_surf, text_rect)

        # Subtext
        font_medium = pygame.font.Font(None, 36)
        subtext_surf = font_medium.render("All Levels Completed!", True, (255, 255, 200))
        subtext_rect = subtext_surf.get_rect(center=(self.W // 2, self.H // 3 + 10))
        self.screen.blit(subtext_surf, subtext_rect)

        # Stats box
        stats_y = self.H // 3 + 70
        stats_bg = pygame.Rect(self.W // 2 - 200, stats_y - 20, 400, 120)
        pygame.draw.rect(self.screen, (0, 0, 0, 160), stats_bg, border_radius=15)
        pygame.draw.rect(self.screen, (255, 215, 0), stats_bg, width=2, border_radius=15)

        # Score
        score_font = pygame.font.Font(None, 32)
        score_surf = score_font.render(f"Final Score: {self.score}", True, (255, 255, 180))
        score_rect = score_surf.get_rect(center=(self.W // 2, stats_y + 10))
        self.screen.blit(score_surf, score_rect)

        # Zombies killed
        kills_surf = score_font.render(f"Total Zombies Killed: {self.totalkills}", True, (255, 255, 180))
        kills_rect = kills_surf.get_rect(center=(self.W // 2, stats_y + 50))
        self.screen.blit(kills_surf, kills_rect)

        # Achievement bonus
        achievement_surf = score_font.render("You are the ultimate survivor!", True, (200, 255, 200))
        achievement_rect = achievement_surf.get_rect(center=(self.W // 2, stats_y + 90))
        self.screen.blit(achievement_surf, achievement_rect)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r or event.key == pygame.K_RETURN:
                return "restart"
            elif event.key == pygame.K_m:
                return "menu"
            elif event.key == pygame.K_ESCAPE:
                return "quit"
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Implement button hitboxes if buttons added
            pass
        return None



# -------- Compatibility wrapper for your main.py --------
def run_demo_level(screen: pygame.Surface, clock: pygame.time.Clock, version: str = "") -> str | None:
    """حفاظًا على التوافق مع main.py الحالي."""
    return run_game(screen, clock, version)
