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
        self.animation_progress = 0  # For pulse/glow effects
        self.flicker_timer = 0  # 🔥 Horror flicker effect

    def draw(self, surface: pygame.Surface):
        import math
        import random
        
        # Check hover
        mouse_pos = pygame.mouse.get_pos()
        hovered = (not self.disabled) and self.rect.collidepoint(mouse_pos)
        
        # Update flicker timer for horror effect
        self.flicker_timer += 0.1
        flicker = 0.9 + 0.1 * math.sin(self.flicker_timer * 3) + random.uniform(-0.05, 0.05)
        
        # Animate glow effect
        if hovered:
            self.animation_progress = min(self.animation_progress + 0.15, 1.0)
        else:
            self.animation_progress = max(self.animation_progress - 0.1, 0.0)
        
        # 🔥 HORROR THEME - Blood red and dark colors with CLEARER TEXT
        if self.disabled:
            bg_color = (20, 15, 15, 180)
            border_color = (50, 30, 30)
            text_color = (100, 80, 80)
            glow_color = None
        elif hovered:
            # Blood red glow on hover - BRIGHT WHITE TEXT for readability
            bg_color = (60, 15, 15, 240)
            border_color = (220, 50, 50)  # Brighter blood red
            text_color = (255, 255, 255)  # Pure white for maximum readability
            glow_color = (180, 0, 0, int(120 * self.animation_progress * flicker))
        else:
            # Dark base state - LIGHT TEXT for contrast
            bg_color = (35, 12, 12, 220)
            border_color = (140, 50, 50)  # Visible red border
            text_color = (230, 220, 220)  # Light gray-white for readability
            glow_color = (80, 20, 20, int(40 * self.animation_progress))

        # 🔥 Draw eerie outer glow effect (blood red)
        if glow_color and self.animation_progress > 0:
            glow_size = int(10 * self.animation_progress * flicker)
            glow_rect = self.rect.inflate(glow_size * 2, glow_size * 2)
            glow_surf = pygame.Surface((glow_rect.w, glow_rect.h), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, glow_color, glow_surf.get_rect(), border_radius=15)
            surface.blit(glow_surf, (glow_rect.x, glow_rect.y))

        # Draw main button background
        btn_surf = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        pygame.draw.rect(btn_surf, bg_color, btn_surf.get_rect(), border_radius=8)
        surface.blit(btn_surf, (self.rect.x, self.rect.y))
        
        # Draw border
        border_width = 3 if hovered else 2
        pygame.draw.rect(surface, border_color, self.rect, width=border_width, border_radius=8)
        
        # 🔥 CLEAR READABLE FONT - Arial Bold for best readability
        font = pygame.font.SysFont("arial", 24, bold=True)
        txt = font.render(self.label, True, text_color)
        
        # 🔥 BLACK OUTLINE for text clarity (renders text readable on any background)
        if not self.disabled:
            outline_color = (0, 0, 0)
            outline_txt = font.render(self.label, True, outline_color)
            tx = self.rect.x + (self.rect.w - txt.get_width()) // 2
            ty = self.rect.y + (self.rect.h - txt.get_height()) // 2
            # Draw outline in 4 directions
            for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
                surface.blit(outline_txt, (tx + ox, ty + oy))
        
        # Main text
        tx = self.rect.x + (self.rect.w - txt.get_width()) // 2
        ty = self.rect.y + (self.rect.h - txt.get_height()) // 2
        surface.blit(txt, (tx, ty))

    def hit(self, pos) -> bool:
        return (not self.disabled) and self.rect.collidepoint(pos)


class Slider:
    """Horizontal slider UI component for volume controls."""
    
    def __init__(self, rect: pygame.Rect, value: float = 0.5, label: str = ""):
        self.rect = rect
        self.value = max(0.0, min(1.0, value))
        self.label = label
        self.dragging = False
        self.handle_width = 16
        self.flicker_timer = 0.0
    
    def _get_handle_rect(self) -> pygame.Rect:
        """Get the handle rectangle based on current value."""
        track_width = self.rect.width - self.handle_width
        handle_x = self.rect.x + int(self.value * track_width)
        return pygame.Rect(handle_x, self.rect.y - 4, self.handle_width, self.rect.height + 8)
    
    def draw(self, surface: pygame.Surface):
        import math
        import random
        
        self.flicker_timer += 0.1
        flicker = 0.95 + 0.05 * math.sin(self.flicker_timer * 2)
        
        mouse_pos = pygame.mouse.get_pos()
        handle_rect = self._get_handle_rect()
        hovered = handle_rect.collidepoint(mouse_pos) or self.dragging
        
        # 🔥 Horror-themed track background
        track_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(track_surf, (25, 12, 12, 220), track_surf.get_rect(), border_radius=4)
        surface.blit(track_surf, (self.rect.x, self.rect.y))
        
        # Track border
        pygame.draw.rect(surface, (80, 40, 40), self.rect, width=1, border_radius=4)
        
        # 🔥 Filled portion (blood red gradient effect)
        if self.value > 0:
            fill_width = int((self.rect.width - self.handle_width) * self.value + self.handle_width / 2)
            fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_width, self.rect.height)
            fill_surf = pygame.Surface((fill_width, self.rect.height), pygame.SRCALPHA)
            fill_color = (int(140 * flicker), 30, 30, 200)
            pygame.draw.rect(fill_surf, fill_color, fill_surf.get_rect(), border_radius=4)
            surface.blit(fill_surf, (self.rect.x, self.rect.y))
        
        # 🔥 Handle with glow
        if hovered or self.dragging:
            # Glow effect
            glow_surf = pygame.Surface((handle_rect.width + 8, handle_rect.height + 8), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (180, 50, 50, 100), glow_surf.get_rect(), border_radius=6)
            surface.blit(glow_surf, (handle_rect.x - 4, handle_rect.y - 4))
            handle_color = (200, 60, 60)
            border_color = (255, 100, 100)
        else:
            handle_color = (160, 50, 50)
            border_color = (200, 80, 80)
        
        pygame.draw.rect(surface, handle_color, handle_rect, border_radius=4)
        pygame.draw.rect(surface, border_color, handle_rect, width=2, border_radius=4)
        
        # Label and value text
        if self.label:
            font = pygame.font.SysFont("arial", 18, bold=True)
            label_surf = font.render(self.label, True, (220, 210, 210))
            surface.blit(label_surf, (self.rect.x, self.rect.y - 22))
            
            # Value percentage
            value_text = f"{int(self.value * 100)}%"
            value_surf = font.render(value_text, True, (200, 180, 180))
            surface.blit(value_surf, (self.rect.x + self.rect.width + 10, self.rect.y))
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle mouse events. Returns True if value changed."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            handle_rect = self._get_handle_rect()
            if handle_rect.collidepoint(event.pos) or self.rect.collidepoint(event.pos):
                self.dragging = True
                return self._update_value_from_pos(event.pos[0])
        
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_dragging = self.dragging
            self.dragging = False
            return was_dragging
        
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            return self._update_value_from_pos(event.pos[0])
        
        return False
    
    def _update_value_from_pos(self, x: int) -> bool:
        """Update value based on mouse x position."""
        track_width = self.rect.width - self.handle_width
        new_value = (x - self.rect.x - self.handle_width / 2) / track_width
        new_value = max(0.0, min(1.0, new_value))
        
        if abs(new_value - self.value) > 0.001:
            self.value = new_value
            return True
        return False


class Dropdown:
    """Dropdown selection UI component for resolution selection."""
    
    def __init__(self, rect: pygame.Rect, options: list, selected_index: int = 0, label: str = ""):
        self.rect = rect
        self.options = options  # List of display strings
        self.selected_index = selected_index
        self.label = label
        self.expanded = False
        self.flicker_timer = 0.0
        self.hover_index = -1
    
    def get_selected(self):
        """Get the currently selected option."""
        if 0 <= self.selected_index < len(self.options):
            return self.options[self.selected_index]
        return None
    
    def draw(self, surface: pygame.Surface):
        import math
        import random
        
        self.flicker_timer += 0.1
        flicker = 0.95 + 0.05 * math.sin(self.flicker_timer * 2)
        
        mouse_pos = pygame.mouse.get_pos()
        hovered = self.rect.collidepoint(mouse_pos)
        
        # 🔥 Horror-themed main button
        if hovered or self.expanded:
            bg_color = (50, 15, 15, 240)
            border_color = (200, 60, 60)
        else:
            bg_color = (30, 12, 12, 220)
            border_color = (140, 50, 50)
        
        btn_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(btn_surf, bg_color, btn_surf.get_rect(), border_radius=6)
        surface.blit(btn_surf, (self.rect.x, self.rect.y))
        pygame.draw.rect(surface, border_color, self.rect, width=2, border_radius=6)
        
        # Selected text
        font = pygame.font.SysFont("arial", 18, bold=True)
        if 0 <= self.selected_index < len(self.options):
            text = self.options[self.selected_index]
        else:
            text = "Select..."
        
        text_surf = font.render(text, True, (230, 220, 220))
        tx = self.rect.x + 10
        ty = self.rect.y + (self.rect.height - text_surf.get_height()) // 2
        surface.blit(text_surf, (tx, ty))
        
        # Dropdown arrow
        arrow_x = self.rect.x + self.rect.width - 25
        arrow_y = self.rect.y + self.rect.height // 2
        if self.expanded:
            # Up arrow
            points = [(arrow_x, arrow_y + 4), (arrow_x + 10, arrow_y + 4), (arrow_x + 5, arrow_y - 4)]
        else:
            # Down arrow
            points = [(arrow_x, arrow_y - 4), (arrow_x + 10, arrow_y - 4), (arrow_x + 5, arrow_y + 4)]
        pygame.draw.polygon(surface, (200, 150, 150), points)
        
        # Label
        if self.label:
            label_surf = font.render(self.label, True, (220, 210, 210))
            surface.blit(label_surf, (self.rect.x, self.rect.y - 22))
        
        # Expanded dropdown list
        if self.expanded:
            list_height = len(self.options) * 32
            list_rect = pygame.Rect(self.rect.x, self.rect.y + self.rect.height + 2, 
                                    self.rect.width, list_height)
            
            # Background
            list_surf = pygame.Surface((list_rect.width, list_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(list_surf, (25, 10, 10, 250), list_surf.get_rect(), border_radius=6)
            surface.blit(list_surf, (list_rect.x, list_rect.y))
            pygame.draw.rect(surface, (140, 50, 50), list_rect, width=2, border_radius=6)
            
            # Options
            for i, option in enumerate(self.options):
                item_rect = pygame.Rect(list_rect.x, list_rect.y + i * 32, list_rect.width, 32)
                
                if item_rect.collidepoint(mouse_pos):
                    self.hover_index = i
                    # Highlight
                    highlight_surf = pygame.Surface((item_rect.width - 4, item_rect.height - 2), pygame.SRCALPHA)
                    pygame.draw.rect(highlight_surf, (80, 25, 25, 200), highlight_surf.get_rect(), border_radius=4)
                    surface.blit(highlight_surf, (item_rect.x + 2, item_rect.y + 1))
                
                # Option text
                if i == self.selected_index:
                    opt_color = (255, 150, 150)  # Highlight selected
                else:
                    opt_color = (220, 210, 210)
                
                opt_surf = font.render(option, True, opt_color)
                surface.blit(opt_surf, (item_rect.x + 10, item_rect.y + 6))
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle mouse events. Returns True if selection changed."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.expanded = not self.expanded
                return False
            
            if self.expanded:
                # Check if clicked on an option
                list_y = self.rect.y + self.rect.height + 2
                for i in range(len(self.options)):
                    item_rect = pygame.Rect(self.rect.x, list_y + i * 32, self.rect.width, 32)
                    if item_rect.collidepoint(event.pos):
                        old_index = self.selected_index
                        self.selected_index = i
                        self.expanded = False
                        return old_index != i
                
                # Clicked outside - close dropdown
                self.expanded = False
        
        return False
    
    def get_expanded_rect(self) -> pygame.Rect:
        """Get the full rect including expanded dropdown."""
        if not self.expanded:
            return self.rect
        list_height = len(self.options) * 32
        return pygame.Rect(self.rect.x, self.rect.y, 
                          self.rect.width, self.rect.height + list_height + 2)

