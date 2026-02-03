# skins.py - Character Skins System for Zombie Shooter
"""
نظام المظاهر للشخصيات:
- 5 ألوان مختلفة للشخصيات
- دعم الشبكة لمشاركة المظهر
- تأثير اللون على الـ Sprite
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Optional
import pygame

# ============== Skin Definitions ==============
SKINS: Dict[str, Dict] = {
    "soldier": {
        "name": "Soldier",
        "name_ar": "جندي",
        "color": (100, 150, 200),      # أزرق فاتح
        "outline": (60, 100, 160),
        "description": "Default military uniform",
    },
    "crimson": {
        "name": "Crimson",
        "name_ar": "قرمزي",
        "color": (200, 60, 60),         # أحمر
        "outline": (150, 40, 40),
        "description": "Red combat suit",
    },
    "ranger": {
        "name": "Ranger",
        "name_ar": "حارس",
        "color": (60, 180, 60),         # أخضر
        "outline": (40, 130, 40),
        "description": "Forest ranger outfit",
    },
    "champion": {
        "name": "Champion",
        "name_ar": "بطل",
        "color": (255, 200, 50),        # ذهبي
        "outline": (200, 150, 30),
        "description": "Golden champion armor",
    },
    "mystic": {
        "name": "Mystic",
        "name_ar": "غامض",
        "color": (150, 60, 200),        # بنفسجي
        "outline": (100, 40, 150),
        "description": "Mysterious purple cloak",
    },
}

# قائمة أسماء المظاهر بالترتيب
SKIN_ORDER = ["none", "soldier", "crimson", "ranger", "champion", "mystic"]
DEFAULT_SKIN = "soldier"

# ============== Skin Functions ==============
def get_skin_names() -> list:
    """الحصول على قائمة أسماء المظاهر"""
    return SKIN_ORDER.copy()

def get_skin_data(skin_id: str) -> Dict:
    """الحصول على بيانات مظهر معين"""
    if skin_id == "none":
        # تعريف مخصص لعدم وجود مظهر
        return {
            "name": "No Skin",
            "name_ar": "بدون مظهر",
            "color": (230, 230, 230),
            "outline": (150, 150, 150),
            "description": "Play without tint/effects",
        }
    return SKINS.get(skin_id, SKINS[DEFAULT_SKIN])

def get_skin_color(skin_id: str) -> Tuple[int, int, int]:
    """الحصول على لون مظهر معين"""
    return get_skin_data(skin_id)["color"]

def get_next_skin(current_skin: str) -> str:
    """الحصول على المظهر التالي"""
    try:
        idx = SKIN_ORDER.index(current_skin)
        return SKIN_ORDER[(idx + 1) % len(SKIN_ORDER)]
    except ValueError:
        return DEFAULT_SKIN

def get_prev_skin(current_skin: str) -> str:
    """الحصول على المظهر السابق"""
    try:
        idx = SKIN_ORDER.index(current_skin)
        return SKIN_ORDER[(idx - 1) % len(SKIN_ORDER)]
    except ValueError:
        return DEFAULT_SKIN

# ============== Sprite Tinting ==============
def apply_skin_tint(surface: pygame.Surface, skin_id: str, intensity: float = 0.4) -> pygame.Surface:
    """
    تطبيق لون المظهر على الـ Sprite
    intensity: قوة التأثير (0.0 - 1.0)
    """
    if surface is None:
        return None
        
    skin_color = get_skin_color(skin_id)
    
    # إنشاء نسخة جديدة
    tinted = surface.copy()
    
    # إنشاء سطح اللون
    color_surface = pygame.Surface(tinted.get_size(), pygame.SRCALPHA)
    color_surface.fill((*skin_color, int(255 * intensity)))
    
    # تطبيق اللون
    tinted.blit(color_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    
    return tinted



# ============== Skin Preview ==============
def draw_skin_preview(screen: pygame.Surface, x: int, y: int, skin_id: str, 
                      size: int = 60, selected: bool = False):
    """رسم معاينة المظهر"""
    skin_data = get_skin_data(skin_id)
    color = skin_data["color"]
    outline = skin_data["outline"]
    
    # مربع الخلفية
    bg_rect = pygame.Rect(x - 5, y - 5, size + 10, size + 35)
    bg_color = (60, 60, 80) if selected else (40, 40, 50)
    border_color = (255, 200, 50) if selected else (100, 100, 100)
    pygame.draw.rect(screen, bg_color, bg_rect, border_radius=8)
    pygame.draw.rect(screen, border_color, bg_rect, width=3 if selected else 1, border_radius=8)
    
    # دائرة الشخصية (تمثيل بسيط)
    center_x = x + size // 2
    center_y = y + size // 2
    
    # الجسم
    pygame.draw.circle(screen, outline, (center_x, center_y), size // 2 + 2)
    pygame.draw.circle(screen, color, (center_x, center_y), size // 2)
    
    # الوجه
    face_color = (min(255, color[0] + 40), min(255, color[1] + 40), min(255, color[2] + 40))
    pygame.draw.circle(screen, face_color, (center_x, center_y - 5), size // 4)
    
    # اسم المظهر
    font = pygame.font.Font(None, 18)
    name_surf = font.render(skin_data["name"], True, (255, 255, 255))
    name_rect = name_surf.get_rect(center=(center_x, y + size + 12))
    screen.blit(name_surf, name_rect)

def draw_skin_selector(screen: pygame.Surface, current_skin: str, 
                       center_x: int, y: int) -> pygame.Rect:
    """
    رسم واجهة اختيار المظهر
    يرجع الـ Rect الكلي للواجهة
    """
    skin_size = 50
    spacing = 75
    total_width = len(SKIN_ORDER) * spacing
    start_x = center_x - total_width // 2
    
    # عنوان
    font = pygame.font.Font(None, 28)
    title_surf = font.render("Choose Your Skin", True, (255, 255, 255))
    title_rect = title_surf.get_rect(center=(center_x, y - 30))
    screen.blit(title_surf, title_rect)
    
    # رسم كل المظاهر
    for i, skin_id in enumerate(SKIN_ORDER):
        skin_x = start_x + i * spacing
        is_selected = (skin_id == current_skin)
        draw_skin_preview(screen, skin_x, y, skin_id, skin_size, is_selected)
    
    # المساحة الكلية
    return pygame.Rect(start_x - 10, y - 40, total_width + 20, skin_size + 70)

def get_clicked_skin(click_pos: Tuple[int, int], center_x: int, y: int) -> Optional[str]:
    """
    التحقق من أي مظهر تم النقر عليه
    يرجع None إذا لم يتم النقر على أي مظهر
    """
    skin_size = 50
    spacing = 75
    total_width = len(SKIN_ORDER) * spacing
    start_x = center_x - total_width // 2
    
    click_x, click_y = click_pos
    
    for i, skin_id in enumerate(SKIN_ORDER):
        skin_x = start_x + i * spacing
        skin_rect = pygame.Rect(skin_x - 5, y - 5, skin_size + 10, skin_size + 35)
        if skin_rect.collidepoint(click_x, click_y):
            return skin_id
    
    return None



# ============== Player Indicator ==============
def draw_player_indicator(screen: pygame.Surface, x: int, y: int, 
                          skin_id: str, player_name: str = "", 
                          is_local: bool = True):
    """
    رسم مؤشر اللاعب فوق رأسه
    """
    skin_color = get_skin_color(skin_id)
    
    # خلفية الاسم
    font = pygame.font.Font(None, 20)
    if player_name:
        name_surf = font.render(player_name, True, (255, 255, 255))
        name_rect = name_surf.get_rect(center=(x, y - 35))
        
        bg_rect = name_rect.inflate(10, 4)
        bg_color = (*skin_color, 180)
        pygame.draw.rect(screen, bg_color, bg_rect, border_radius=4)
        screen.blit(name_surf, name_rect)
    
    # مؤشر اللاعب المحلي
    if is_local:
        indicator_y = y - 50 if player_name else y - 35
        pygame.draw.polygon(screen, skin_color, [
            (x, indicator_y + 8),
            (x - 6, indicator_y),
            (x + 6, indicator_y),
        ])