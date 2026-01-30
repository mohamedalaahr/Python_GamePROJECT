# walls.py

from __future__ import annotations
import pygame

# ألوان (كما هي)
FILL = (92, 55, 24)
EDGE = (40, 26, 15)
INNER = (26, 90, 58)

def collide_rect_list(rect: pygame.Rect, rects: list[pygame.Rect]):
    for r in rects:
        if rect.colliderect(r):
            return r
    return None

def draw_walls(screen: pygame.Surface, walls: list[pygame.Rect]):
    for r in walls:
        pygame.draw.rect(screen, FILL, r, border_radius=8)
        pygame.draw.rect(screen, EDGE, r, width=2, border_radius=8)
        inner = r.inflate(-6, -6)
        if inner.w > 0 and inner.h > 0:
            pygame.draw.rect(screen, INNER, inner, width=1, border_radius=6)

def _rp(W: int, H: int, x: float, y: float, w: float, h: float) -> pygame.Rect:
    return pygame.Rect(
        int(x * W), 
        int(y * H), 
        max(1, int(w * W)), 
        max(1, int(h * H))
    )


def _level1(W: int, H: int) -> list[pygame.Rect]:
    walls: list[pygame.Rect] = []
    walls.append(_rp(W, H, 0.15, 0.15, 0.15, 0.04)) # أعلى اليسار
    walls.append(_rp(W, H, 0.70, 0.15, 0.15, 0.04)) # أعلى اليمين
    walls.append(_rp(W, H, 0.15, 0.81, 0.15, 0.04)) # أسفل اليسار
    walls.append(_rp(W, H, 0.70, 0.81, 0.15, 0.04)) # أسفل اليمين
    walls.append(_rp(W, H, 0.47, 0.47, 0.06, 0.06)) # صندوق صغير في المنتصف
    return walls

def _level2(W: int, H: int) -> list[pygame.Rect]:
    walls: list[pygame.Rect] = []
    walls.append(_rp(W, H, 0.20, 0.20, 0.03, 0.60)) 
    walls.append(_rp(W, H, 0.77, 0.20, 0.03, 0.60)) 
    walls.append(_rp(W, H, 0.23, 0.48, 0.54, 0.04)) 
    return walls

def _level3(W: int, H: int) -> list[pygame.Rect]:
    walls: list[pygame.Rect] = []
    walls.append(_rp(W, H, 0.25, 0.20, 0.05, 0.60)) 
    walls.append(_rp(W, H, 0.70, 0.20, 0.05, 0.60)) 
    walls.append(_rp(W, H, 0.30, 0.48, 0.40, 0.05)) 
    # عوائق إضافية
    walls.append(_rp(W, H, 0.10, 0.10, 0.10, 0.04))
    walls.append(_rp(W, H, 0.80, 0.86, 0.10, 0.04))
    return walls

def _level4(W: int, H: int) -> list[pygame.Rect]:
    walls: list[pygame.Rect] = []
    # صليب في المنتصف (مع فتحات للعبور)
    walls.append(_rp(W, H, 0.475, 0.0, 0.05, 0.40))  
    walls.append(_rp(W, H, 0.475, 0.6, 0.05, 0.40))  
    walls.append(_rp(W, H, 0.0, 0.475, 0.40, 0.05))  # شريط يسار
    walls.append(_rp(W, H, 0.6, 0.475, 0.40, 0.05))  # شريط يمين
    # عوائق في الزوايا
    walls.append(_rp(W, H, 0.20, 0.20, 0.10, 0.04))
    walls.append(_rp(W, H, 0.70, 0.20, 0.10, 0.04))
    walls.append(_rp(W, H, 0.20, 0.76, 0.10, 0.04))
    walls.append(_rp(W, H, 0.70, 0.76, 0.10, 0.04))
    return walls

def _level5(W: int, H: int) -> list[pygame.Rect]:
    walls: list[pygame.Rect] = []
    walls.append(_rp(W, H, 0.0, 0.33, 0.25, 0.04)) 
    walls.append(_rp(W, H, 0.22, 0.15, 0.03, 0.36))
    walls.append(_rp(W, H, 0.10, 0.50, 0.25, 0.04)) 
    
    walls.append(_rp(W, H, 0.40, 0.0, 0.04, 0.60)) 
    walls.append(_rp(W, H, 0.44, 0.25, 0.20, 0.04))
    
    walls.append(_rp(W, H, 0.70, 0.20, 0.30, 0.04)) 
    walls.append(_rp(W, H, 0.70, 0.40, 0.04, 0.40))   
    walls.append(_rp(W, H, 0.70, 0.80, 0.30, 0.04)) 
    walls.append(_rp(W, H, 0.50, 0.60, 0.20, 0.04)) 
    return walls

def _level6(W: int, H: int) -> list[pygame.Rect]:
    walls: list[pygame.Rect] = []

    

    walls.append(_rp(W, H, 0.2, 0.1, 0.7, 0.04)) 

    walls.append(_rp(W, H, 0.1, 0.2, 0.04, 0.24)) 

    walls.append(_rp(W, H, 0.1, 0.86, 0.8, 0.04)) 
    walls.append(_rp(W, H, 0.1, 0.56, 0.04, 0.30)) 
    walls.append(_rp(W, H, 0.86, 0.14, 0.04, 0.30)) 
    walls.append(_rp(W, H, 0.86, 0.56, 0.04, 0.30)) 

    # فتح فتحة وسطية في الشريط العلوي للمربع الداخلي
    walls.append(_rp(W, H, 0.3, 0.3, 0.16, 0.04))
    walls.append(_rp(W, H, 0.54, 0.3, 0.16, 0.04))
    # فتح فتحة وسطية في الشريط السفلي للمربع الداخلي
    walls.append(_rp(W, H, 0.3, 0.66, 0.16, 0.04))
    walls.append(_rp(W, H, 0.54, 0.66, 0.16, 0.04))
    walls.append(_rp(W, H, 0.3, 0.34, 0.04, 0.32))
    walls.append(_rp(W, H, 0.66, 0.34, 0.04, 0.32))

    return walls


def create_walls_for_level(level: int, width: int, height: int, tile: int = 64) -> list[pygame.Rect]:
    
   
    
    walls_list: list[pygame.Rect] = []
    
    level_functions = {
        1: _level1,
        2: _level2,
        3: _level3,
        4: _level4,
        5: _level5,
        6: _level6,
    }
    
    selected_level_func = level_functions.get(level, _level6)
    
    walls_list.extend(selected_level_func(width, height))
    
    return walls_list