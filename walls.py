"""
جدران بسيطة مثل النسخة القديمة + رسمها + مساعد تصادم.
"""

import pygame

BROWN_DARK = (120, 70, 30)
BROWN_BORDER = (50, 30, 15)

def create_demo_walls(width, height, tile=64):
    """يبني جدران واضحة: إطار + ممرات بسيطة."""
    walls = []

    # إطار
    thickness = tile // 2
    walls.append(pygame.Rect(0, 0, width, thickness))                    # أعلى
    walls.append(pygame.Rect(0, height - thickness, width, thickness))   # أسفل
    walls.append(pygame.Rect(0, 0, thickness, height))                   # يسار
    walls.append(pygame.Rect(width - thickness, 0, thickness, height))   # يمين

    # أعمدة/حواجز داخلية بسيطة
    walls += [
        pygame.Rect(tile*3, tile*2, tile*5, tile//2),
        pygame.Rect(tile*7, tile*4, tile*6, tile//2),
        pygame.Rect(tile*4, tile*6, tile//2, tile*2),
    ]
    return walls

def draw_walls(screen, walls):
    for r in walls:
        pygame.draw.rect(screen, BROWN_DARK, r, border_radius=6)
        pygame.draw.rect(screen, BROWN_BORDER, r, width=2, border_radius=6)

def collide_rect_list(rect, rects):

    for r in rects:
        if rect.colliderect(r):
            return r
    return None
