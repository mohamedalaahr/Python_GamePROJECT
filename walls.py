# walls.py


from __future__ import annotations
import pygame

# ألوان
FILL  = (92, 55, 24)
EDGE  = (40, 26, 15)
INNER = (26, 90, 58)

def collide_rect_list(rect: pygame.Rect, rects: list[pygame.Rect]):
    """يرجع أول جدار يصطدم به المستطيل أو None."""
    for r in rects:
        if rect.colliderect(r):
            return r
    return None

def draw_walls(screen: pygame.Surface, walls: list[pygame.Rect]):
    """رسم بسيط أنيق."""
    for r in walls:
        pygame.draw.rect(screen, FILL, r, border_radius=8)
        pygame.draw.rect(screen, EDGE, r, width=2, border_radius=8)
        inner = r.inflate(-6, -6)
        if inner.w > 0 and inner.h > 0:
            pygame.draw.rect(screen, INNER, inner, width=1, border_radius=6)

# ---------- أدوات نسبة مئوية + منع تداخل ----------
def _rp(W: int, H: int, x: float, y: float, w: float, h: float) -> pygame.Rect:
    """Rect بنسبة مئوية من أبعاد العالم."""
    return pygame.Rect(int(x * W), int(y * H), int(w * W), int(h * H))

def _add_safe(walls: list[pygame.Rect], r: pygame.Rect, gap: int = 28) -> bool:
    """
    يضيف مستطيلاً إذا لم يتداخل أو يلتصق بجدار آخر.
    gap: هامش فصل لمنع الالتقاء المباشر.
    """
    expand = r.inflate(gap, gap)
    for w in walls:
        if expand.colliderect(w):
            return False
    walls.append(r)
    return True

# ---------- تخطيطات قليلة ونظيفة لكل مستوى ----------
def _level1(W: int, H: int) -> list[pygame.Rect]:
    """Level 1: 4 جدران قصيرة ومتباعدة — مساحة مفتوحة جداً."""
    walls: list[pygame.Rect] = []
    _add_safe(walls, _rp(W, H, 0.32, 0.22, 0.28, 0.030))   # شريط علوي قصير
    _add_safe(walls, _rp(W, H, 0.14, 0.52, 0.22, 0.034))   # يسار-وسط
    _add_safe(walls, _rp(W, H, 0.62, 0.64, 0.26, 0.032))   # يمين-أسفل
    _add_safe(walls, _rp(W, H, 0.42, 0.36, 0.030, 0.22))   # عمودي رفيع في الوسط
    return walls

def _level2(W: int, H: int) -> list[pygame.Rect]:
    """Level 2: 5–6 عناصر مع اختلاف أطوال واتجاهات."""
    walls: list[pygame.Rect] = []
    _add_safe(walls, _rp(W, H, 0.18, 0.18, 0.30, 0.032))
    _add_safe(walls, _rp(W, H, 0.68, 0.22, 0.22, 0.030))
    _add_safe(walls, _rp(W, H, 0.28, 0.46, 0.030, 0.24))
    _add_safe(walls, _rp(W, H, 0.62, 0.52, 0.026, 0.22))
    _add_safe(walls, _rp(W, H, 0.36, 0.76, 0.28, 0.034))
    _add_safe(walls, _rp(W, H, 0.78, 0.68, 0.18, 0.030))
    return walls

def _level3(W: int, H: int) -> list[pygame.Rect]:
    """Level 3: 6–7 عناصر – فراغات واسعة، بدون تداخل."""
    walls: list[pygame.Rect] = []
    _add_safe(walls, _rp(W, H, 0.10, 0.16, 0.26, 0.032))
    _add_safe(walls, _rp(W, H, 0.46, 0.18, 0.24, 0.030))
    _add_safe(walls, _rp(W, H, 0.82, 0.24, 0.030, 0.24))
    _add_safe(walls, _rp(W, H, 0.24, 0.44, 0.030, 0.26))
    _add_safe(walls, _rp(W, H, 0.68, 0.48, 0.26, 0.032))
    _add_safe(walls, _rp(W, H, 0.18, 0.76, 0.24, 0.034))
    _add_safe(walls, _rp(W, H, 0.74, 0.74, 0.22, 0.030))
    return walls

def _level4(W: int, H: int) -> list[pygame.Rect]:
    """Level 4: 7 عناصر لكن موزّعة باحتراف — لا تقفل المسارات."""
    walls: list[pygame.Rect] = []
    _add_safe(walls, _rp(W, H, 0.12, 0.18, 0.24, 0.030))
    _add_safe(walls, _rp(W, H, 0.42, 0.22, 0.22, 0.032))
    _add_safe(walls, _rp(W, H, 0.78, 0.18, 0.18, 0.030))
    _add_safe(walls, _rp(W, H, 0.26, 0.50, 0.030, 0.24))
    _add_safe(walls, _rp(W, H, 0.62, 0.46, 0.030, 0.26))
    _add_safe(walls, _rp(W, H, 0.18, 0.78, 0.26, 0.034))
    _add_safe(walls, _rp(W, H, 0.68, 0.74, 0.24, 0.032))
    return walls

def create_walls_for_level(level: int, width: int, height: int, tile: int = 64) -> list[pygame.Rect]:
   
    if level <= 1:
        return _level1(width, height)
    elif level == 2:
        return _level2(width, height)
    elif level == 3:
        return _level3(width, height)
    else:
        return _level4(width, height)
