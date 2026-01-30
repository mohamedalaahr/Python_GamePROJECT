# minimap.py - Mini-map System for Zombie Shooter
"""
نظام الخريطة المصغرة:
- عرض موقع اللاعبين والأعداء والباب
- تبديل العرض بمفتاح M
- خلفية شبه شفافة
"""

from typing import Dict, List, Tuple, Optional
import math
import pygame

# ============== Constants ==============
MINIMAP_SIZE = 180        # حجم الخريطة
MINIMAP_MARGIN = 15       # هامش من حافة الشاشة
TOGGLE_KEY = pygame.K_m   # مفتاح التبديل

# ============== Minimap ==============
class Minimap:
    """نظام الخريطة المصغرة"""
    
    def __init__(self, world_w: int, world_h: int, screen_w: int, screen_h: int, size: int = MINIMAP_SIZE):
        self.world_w = world_w
        self.world_h = world_h
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.size = size
        
        # الحجم النهائي مع الحفاظ على النسبة
        aspect_ratio = world_w / world_h
        if aspect_ratio > 1:
            self.map_width = size
            self.map_height = int(size / aspect_ratio)
        else:
            self.map_height = size
            self.map_width = int(size * aspect_ratio)
        
        # موقع الخريطة (الزاوية العليا اليمنى)
        self.x = screen_w - self.map_width - MINIMAP_MARGIN
        self.y = MINIMAP_MARGIN + 50  # تحت الـ HUD
        
        # مقياس التحويل
        self.scale_x = self.map_width / world_w
        self.scale_y = self.map_height / world_h
        
        # الظهور
        self.visible = True
        self.alpha = 200
        
        # الجدران المرسومة مسبقاً
        self.walls_surface: Optional[pygame.Surface] = None
        self.walls_dirty = True
        
    def toggle(self):
        """تبديل ظهور الخريطة"""
        self.visible = not self.visible
    
    def handle_event(self, event) -> bool:
        """معالجة الأحداث"""
        if event.type == pygame.KEYDOWN and event.key == TOGGLE_KEY:
            self.toggle()
            return True
        return False
    
    def world_to_map(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """تحويل إحداثيات العالم إلى إحداثيات الخريطة"""
        map_x = int(world_x * self.scale_x)
        map_y = int(world_y * self.scale_y)
        return (self.x + map_x, self.y + map_y)
    
    def set_walls(self, walls: List[pygame.Rect]):
        """تعيين الجدران لرسمها مسبقاً"""
        self.walls_dirty = True
        self._render_walls(walls)
    
    def _render_walls(self, walls: List[pygame.Rect]):
        """رسم الجدران على سطح منفصل"""
        if not self.walls_dirty:
            return
            
        self.walls_surface = pygame.Surface((self.map_width, self.map_height), pygame.SRCALPHA)
        
        for wall in walls:
            # تحويل الجدار
            wx = int(wall.x * self.scale_x)
            wy = int(wall.y * self.scale_y)
            ww = max(1, int(wall.width * self.scale_x))
            wh = max(1, int(wall.height * self.scale_y))
            
            pygame.draw.rect(self.walls_surface, (80, 60, 40, 255), 
                           (wx, wy, ww, wh))
        
        self.walls_dirty = False
    
    def draw(self, screen: pygame.Surface, 
             player_pos: Tuple[float, float],
             other_players: Dict[int, Dict],
             zombies: Dict[int, object],
             door: Optional[object] = None,
             walls: Optional[List[pygame.Rect]] = None):
        """
        رسم الخريطة المصغرة
        
        Args:
            player_pos: موقع اللاعب المحلي (x, y)
            other_players: قاموس اللاعبين الآخرين
            zombies: قاموس الزومبي
            door: الباب (إذا كان موجوداً ونشطاً)
            walls: قائمة الجدران (لرسمها مسبقاً)
        """
        if not self.visible:
            return
        
        # تحديث الجدران إذا لزم الأمر
        if walls and self.walls_dirty:
            self._render_walls(walls)
        
        # إنشاء سطح الخريطة
        map_surface = pygame.Surface((self.map_width, self.map_height), pygame.SRCALPHA)
        
        # خلفية
        pygame.draw.rect(map_surface, (20, 25, 35, self.alpha), 
                        (0, 0, self.map_width, self.map_height),
                        border_radius=8)
        
        # الجدران
        if self.walls_surface:
            map_surface.blit(self.walls_surface, (0, 0))
        
        # الباب (إذا كان نشطاً)
        if door and hasattr(door, 'active') and door.active:
            door_map_x = int(door.x * self.scale_x)
            door_map_y = int(door.y * self.scale_y)
            door_size = max(6, int(80 * self.scale_x))
            
            # توهج الباب
            pygame.draw.rect(map_surface, (255, 255, 100, 150),
                           (door_map_x - 2, door_map_y - 2, door_size + 4, door_size + 4),
                           border_radius=2)
            pygame.draw.rect(map_surface, (255, 200, 50),
                           (door_map_x, door_map_y, door_size, door_size),
                           border_radius=2)
        
        # الزومبي (نقاط حمراء)
        for z_id, zombie in zombies.items():
            if hasattr(zombie, 'hp') and zombie.hp > 0:
                zx = int(zombie.x * self.scale_x)
                zy = int(zombie.y * self.scale_y)
                pygame.draw.circle(map_surface, (255, 50, 50), (zx, zy), 3)
        
        # اللاعبون الآخرون (نقاط خضراء)
        for other_id, other_data in other_players.items():
            if not other_data.get("is_dead", False):
                ox = int(other_data["x"] * self.scale_x)
                oy = int(other_data["y"] * self.scale_y)
                # نقطة خضراء مع حدود
                pygame.draw.circle(map_surface, (50, 255, 50), (ox, oy), 5)
                pygame.draw.circle(map_surface, (200, 255, 200), (ox, oy), 5, 1)
        
        # اللاعب المحلي (نقطة زرقاء)
        px = int(player_pos[0] * self.scale_x)
        py = int(player_pos[1] * self.scale_y)
        # نقطة زرقاء مع توهج
        pygame.draw.circle(map_surface, (100, 150, 255, 150), (px, py), 7)
        pygame.draw.circle(map_surface, (50, 100, 255), (px, py), 5)
        pygame.draw.circle(map_surface, (200, 220, 255), (px, py), 3)
        
        # الحدود
        pygame.draw.rect(map_surface, (100, 100, 120),
                        (0, 0, self.map_width, self.map_height),
                        width=2, border_radius=8)
        
        # رسم على الشاشة
        screen.blit(map_surface, (self.x, self.y))
        
        # عنوان الخريطة
        font = pygame.font.Font(None, 18)
        title_surf = font.render("MINIMAP [M]", True, (150, 150, 150))
        screen.blit(title_surf, (self.x + 5, self.y - 18))
        
        # دليل الألوان (مختصر)
        legend_y = self.y + self.map_height + 5
        legend_font = pygame.font.Font(None, 14)
        
        # لاعب محلي
        pygame.draw.circle(screen, (50, 100, 255), (self.x + 8, legend_y + 6), 4)
        
        # لاعب آخر
        pygame.draw.circle(screen, (50, 255, 50), (self.x + 48, legend_y + 6), 4)
        
        # زومبي
        pygame.draw.circle(screen, (255, 50, 50), (self.x + 88, legend_y + 6), 4)
        
        # الباب
        pygame.draw.rect(screen, (255, 200, 50), (self.x + 120, legend_y + 2, 8, 8))
        
    def draw_simple(self, screen: pygame.Surface, 
                    player_x: float, player_y: float,
                    level_no: int = 1):
        """رسم خريطة بسيطة (بدون تفاصيل)"""
        if not self.visible:
            return
            
        # خلفية
        map_rect = pygame.Rect(self.x, self.y, self.map_width, self.map_height)
        pygame.draw.rect(screen, (20, 25, 35, 200), map_rect, border_radius=8)
        pygame.draw.rect(screen, (100, 100, 120), map_rect, width=2, border_radius=8)
        
        # اللاعب
        px, py = self.world_to_map(player_x, player_y)
        pygame.draw.circle(screen, (50, 100, 255), (px, py), 5)
        
        # العنوان
        font = pygame.font.Font(None, 18)
        title_surf = font.render(f"LEVEL {level_no}", True, (150, 150, 150))
        screen.blit(title_surf, (self.x + 5, self.y - 18))



