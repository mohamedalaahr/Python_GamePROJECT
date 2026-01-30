# util.py
import os
import pygame

COLORS = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "hud_fg": (235, 235, 235),
    "hud_shadow": (0, 0, 0),
    "panel": (0, 0, 0, 140),
    "green": (30, 180, 90),
    "red": (210, 60, 60),
    "yellow": (250, 230, 60),
}

IMG_DIR = "images"
SND_DIR = "sounds"


def draw_text(surface, text, pos, *, size=24, color=(255, 255, 255), bold=False):
    font = pygame.font.SysFont("arial", size, bold=bold)
    srf = font.render(text, True, color)
    surface.blit(srf, pos)

def draw_shadow_text(surface, text, pos, *, size=32, color=(0, 0, 0),
                     shadow=(235, 235, 235), offset=2, bold=True):
    font = pygame.font.SysFont("arial", size, bold=bold)
    x, y = pos
    srf_sh = font.render(text, True, shadow)
    surface.blit(srf_sh, (x + offset, y + offset))
    srf = font.render(text, True, color)
    surface.blit(srf, (x, y))



def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def load_image(name, *, scale=None):
    path = os.path.join(IMG_DIR, name)
    if not os.path.isfile(path):
        return None
    try:
        img = pygame.image.load(path).convert_alpha()
        if scale is not None:
            w, h = img.get_size()
            img = pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))
        return img
    except Exception:
        return None

def load_image_to_height(name, height):
    surf = load_image(name)
    if not surf:
        return None
    w, h = surf.get_size()
    if h <= 0:
        return surf
    new_w = int(w * (height / h))
    return pygame.transform.smoothscale(surf, (new_w, height))

def load_sound(name):
    path = os.path.join(SND_DIR, name)
    if not os.path.isfile(path):
        return None
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        return pygame.mixer.Sound(path)
    except Exception:
        return None

class Button:
    def __init__(self, rect: pygame.Rect, label: str, disabled: bool = False):
        self.rect = rect
        self.label = label
        self.disabled = disabled

    def draw(self, surface: pygame.Surface):
        bg = (62, 132, 216) if not self.disabled else (90, 90, 90)
        border = (235, 235, 235)
        pygame.draw.rect(surface, bg, self.rect, border_radius=10)
        pygame.draw.rect(surface, border, self.rect, width=2, border_radius=10)
        font = pygame.font.SysFont("arial", 22, bold=True)
        txt = font.render(self.label, True, (255, 255, 255))
        surface.blit(
            txt,
            (
                self.rect.x + (self.rect.w - txt.get_width()) // 2,
                self.rect.y + (self.rect.h - txt.get_height()) // 2,
            ),
        )

    def hit(self, pos) -> bool:
        return (not self.disabled) and self.rect.collidepoint(pos)
