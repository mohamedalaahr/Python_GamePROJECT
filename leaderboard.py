# leaderboard.py - High Scores System for Zombie Shooter
"""
نظام قائمة أفضل النتائج:
- حفظ وتحميل من ملف JSON
- أفضل 10 نتائج
- عرض شاشة خاصة
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import pygame

# ============== Constants ==============
LEADERBOARD_FILE = "scores.json"
MAX_ENTRIES = 10

# ============== Score Entry ==============
@dataclass
class ScoreEntry:
    """إدخال نتيجة واحدة"""
    player_name: str
    score: int
    kills: int
    level: int
    date: str = ""
    
    def __post_init__(self):
        if not self.date:
            self.date = datetime.now().strftime("%Y-%m-%d %H:%M")

# ============== Leaderboard Manager ==============
class LeaderboardManager:
    """مدير قائمة أفضل النتائج"""
    
    def __init__(self, file_path: str = LEADERBOARD_FILE):
        self.file_path = file_path
        self.scores: List[ScoreEntry] = []
        self.load_scores()
    
    def load_scores(self) -> bool:
        """تحميل النتائج من الملف"""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.scores = [
                        ScoreEntry(**entry) for entry in data.get("scores", [])
                    ]
                    return True
        except Exception as e:
            print(f"Error loading leaderboard: {e}")
        
        self.scores = []
        return False
    
    def save_scores(self) -> bool:
        """حفظ النتائج في الملف"""
        try:
            data = {
                "scores": [asdict(s) for s in self.scores],
                "last_updated": datetime.now().isoformat()
            }
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving leaderboard: {e}")
            return False
    
    def add_score(self, player_name: str, score: int, kills: int, level: int) -> int:
        """
        إضافة نتيجة جديدة
        يرجع ترتيب اللاعب (1-10) أو -1 إذا لم يدخل القائمة
        """
        new_entry = ScoreEntry(
            player_name=player_name[:15],  # حد أقصى 15 حرف
            score=score,
            kills=kills,
            level=level
        )
        
        # إضافة وترتيب
        self.scores.append(new_entry)
        self.scores.sort(key=lambda x: x.score, reverse=True)
        
        # الاحتفاظ بأفضل 10 فقط
        if len(self.scores) > MAX_ENTRIES:
            self.scores = self.scores[:MAX_ENTRIES]
        
        # البحث عن ترتيب اللاعب
        for i, entry in enumerate(self.scores):
            if entry == new_entry:
                self.save_scores()
                return i + 1
        
        return -1
    
    def get_top_scores(self, count: int = 10) -> List[ScoreEntry]:
        """الحصول على أفضل النتائج"""
        return self.scores[:min(count, len(self.scores))]
    
    def is_high_score(self, score: int) -> bool:
        """هل هذه النتيجة تستحق الدخول للقائمة؟"""
        if len(self.scores) < MAX_ENTRIES:
            return True
        return score > self.scores[-1].score
    
    def get_rank(self, score: int) -> int:
        """الحصول على الترتيب المتوقع لنتيجة معينة"""
        rank = 1
        for entry in self.scores:
            if score > entry.score:
                return rank
            rank += 1
        return min(rank, MAX_ENTRIES + 1)

# ============== Leaderboard Screen ==============
class LeaderboardScreen:
    """شاشة عرض قائمة أفضل النتائج"""
    
    def __init__(self, screen: pygame.Surface, manager: LeaderboardManager = None):
        self.screen = screen
        self.W, self.H = screen.get_size()
        self.manager = manager or LeaderboardManager()
        
        # ألوان
        self.bg_color = (20, 25, 35)
        self.title_color = (255, 200, 50)
        self.header_color = (150, 150, 180)
        self.row_colors = [(35, 40, 55), (45, 50, 65)]
        self.text_color = (220, 220, 230)
        self.highlight_color = (255, 200, 50)
        
        # خلفية متحركة
        self.particles = self._create_particles()
        
    def _create_particles(self) -> List[dict]:
        """إنشاء جزيئات الخلفية"""
        import random
        particles = []
        for _ in range(50):
            particles.append({
                'x': random.randint(0, self.W),
                'y': random.randint(0, self.H),
                'size': random.randint(1, 3),
                'speed': random.uniform(0.3, 1.5),
                'alpha': random.randint(50, 150)
            })
        return particles
    
    def update(self, dt: float):
        """تحديث الخلفية"""
        for p in self.particles:
            p['y'] -= p['speed']
            if p['y'] < -10:
                p['y'] = self.H + 10
                import random
                p['x'] = random.randint(0, self.W)
    
    def draw(self, highlight_rank: int = -1):
        """
        رسم شاشة قائمة النتائج
        highlight_rank: ترتيب اللاعب للتمييز (1-10)
        """
        # خلفية
        self.screen.fill(self.bg_color)
        
        # جزيئات الخلفية
        for p in self.particles:
            color = (200, 180, 100, p['alpha'])
            pygame.draw.circle(self.screen, color[:3], (int(p['x']), int(p['y'])), p['size'])
        
        # العنوان
        title_font = pygame.font.Font(None, 64)
        title_surf = title_font.render("LEADERBOARD", True, self.title_color)
        title_rect = title_surf.get_rect(center=(self.W // 2, 60))
        
        # توهج العنوان
        glow_surf = title_font.render("LEADERBOARD", True, (255, 255, 200))
        for offset in [(2, 2), (-2, 2), (2, -2), (-2, -2)]:
            self.screen.blit(glow_surf, (title_rect.x + offset[0], title_rect.y + offset[1]))
        self.screen.blit(title_surf, title_rect)
        
        # الجدول
        table_x = self.W // 2 - 350
        table_y = 130
        table_width = 700
        row_height = 50
        
        # رؤوس الأعمدة
        headers = ["RANK", "PLAYER", "SCORE", "KILLS", "LEVEL", "DATE"]
        header_widths = [60, 180, 120, 80, 80, 150]
        
        header_font = pygame.font.Font(None, 24)
        x_offset = table_x
        for i, (header, width) in enumerate(zip(headers, header_widths)):
            header_surf = header_font.render(header, True, self.header_color)
            self.screen.blit(header_surf, (x_offset + 10, table_y))
            x_offset += width
        
        table_y += 35
        
        # الصفوف
        scores = self.manager.get_top_scores()
        row_font = pygame.font.Font(None, 28)
        
        for i, entry in enumerate(scores):
            row_y = table_y + i * row_height
            
            # خلفية الصف
            row_rect = pygame.Rect(table_x - 10, row_y - 5, table_width + 20, row_height - 5)
            row_color = self.row_colors[i % 2]
            
            # تمييز ترتيب اللاعب
            if i + 1 == highlight_rank:
                row_color = (80, 70, 30)
                pygame.draw.rect(self.screen, self.highlight_color, row_rect, width=2, border_radius=6)
            
            pygame.draw.rect(self.screen, row_color, row_rect, border_radius=6)
            
            # البيانات
            x_offset = table_x
            
            # الترتيب مع ميدالية
            rank_text = str(i + 1)
            if i == 0:
                rank_color = (255, 215, 0)   # ذهبي
            elif i == 1:
                rank_color = (192, 192, 192)  # فضي
            elif i == 2:
                rank_color = (205, 127, 50)   # برونزي
            else:
                rank_color = self.text_color
            
            rank_surf = row_font.render(rank_text, True, rank_color)
            self.screen.blit(rank_surf, (x_offset + 25, row_y + 8))
            x_offset += header_widths[0]
            
            # الاسم
            name_surf = row_font.render(entry.player_name, True, self.text_color)
            self.screen.blit(name_surf, (x_offset + 10, row_y + 8))
            x_offset += header_widths[1]
            
            # النقاط
            score_surf = row_font.render(str(entry.score), True, self.highlight_color)
            self.screen.blit(score_surf, (x_offset + 10, row_y + 8))
            x_offset += header_widths[2]
            
            # القتلى
            kills_surf = row_font.render(str(entry.kills), True, (200, 100, 100))
            self.screen.blit(kills_surf, (x_offset + 10, row_y + 8))
            x_offset += header_widths[3]
            
            # المستوى
            level_surf = row_font.render(str(entry.level), True, (100, 200, 100))
            self.screen.blit(level_surf, (x_offset + 10, row_y + 8))
            x_offset += header_widths[4]
            
            # التاريخ
            date_surf = row_font.render(entry.date, True, (150, 150, 150))
            self.screen.blit(date_surf, (x_offset + 10, row_y + 8))
        
        # إذا لا توجد نتائج
        if not scores:
            empty_font = pygame.font.Font(None, 36)
            empty_surf = empty_font.render("No scores yet! Be the first!", True, (150, 150, 150))
            empty_rect = empty_surf.get_rect(center=(self.W // 2, self.H // 2))
            self.screen.blit(empty_surf, empty_rect)
        
        # تعليمات
        help_font = pygame.font.Font(None, 24)
        help_surf = help_font.render("Press ESC or CLICK to return to menu", True, (150, 150, 150))
        help_rect = help_surf.get_rect(center=(self.W // 2, self.H - 40))
        self.screen.blit(help_surf, help_rect)

# ============== Name Input Dialog ==============
class NameInputDialog:
    """نافذة إدخال الاسم"""
    
    def __init__(self, screen: pygame.Surface, score: int, kills: int, level: int):
        self.screen = screen
        self.W, self.H = screen.get_size()
        self.score = score
        self.kills = kills
        self.level = level
        self.player_name = ""
        self.max_length = 15
        self.cursor_visible = True
        self.cursor_timer = 0
        
    def update(self, dt: float):
        """تحديث مؤشر الكتابة"""
        self.cursor_timer += dt
        if self.cursor_timer > 0.5:
            self.cursor_timer = 0
            self.cursor_visible = not self.cursor_visible
    
    def handle_event(self, event) -> Optional[str]:
        """
        معالجة الأحداث
        يرجع الاسم عند الضغط على Enter، None إذا لم ينته
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and self.player_name:
                return self.player_name
            elif event.key == pygame.K_BACKSPACE:
                self.player_name = self.player_name[:-1]
            elif event.key == pygame.K_ESCAPE:
                return "Player"  # اسم افتراضي
            elif len(self.player_name) < self.max_length:
                if event.unicode.isprintable() and event.unicode:
                    self.player_name += event.unicode
        
        return None
    
    def draw(self):
        """رسم نافذة الإدخال"""
        # خلفية شبه شفافة
        overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        
        # مربع الحوار
        dialog_w, dialog_h = 450, 280
        dialog_x = (self.W - dialog_w) // 2
        dialog_y = (self.H - dialog_h) // 2
        
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_w, dialog_h)
        pygame.draw.rect(self.screen, (30, 35, 50), dialog_rect, border_radius=15)
        pygame.draw.rect(self.screen, (255, 200, 50), dialog_rect, width=3, border_radius=15)
        
        # العنوان
        title_font = pygame.font.Font(None, 42)
        title_surf = title_font.render("NEW HIGH SCORE!", True, (255, 200, 50))
        title_rect = title_surf.get_rect(center=(self.W // 2, dialog_y + 40))
        self.screen.blit(title_surf, title_rect)
        
        # النتائج
        info_font = pygame.font.Font(None, 28)
        info_y = dialog_y + 85
        
        score_surf = info_font.render(f"Score: {self.score}", True, (200, 200, 100))
        self.screen.blit(score_surf, (dialog_x + 30, info_y))
        
        kills_surf = info_font.render(f"Kills: {self.kills}", True, (200, 100, 100))
        self.screen.blit(kills_surf, (dialog_x + 180, info_y))
        
        level_surf = info_font.render(f"Level: {self.level}", True, (100, 200, 100))
        self.screen.blit(level_surf, (dialog_x + 310, info_y))
        
        # تعليمات
        prompt_font = pygame.font.Font(None, 26)
        prompt_surf = prompt_font.render("Enter your name:", True, (180, 180, 180))
        self.screen.blit(prompt_surf, (dialog_x + 30, dialog_y + 130))
        
        # صندوق الإدخال
        input_rect = pygame.Rect(dialog_x + 30, dialog_y + 160, dialog_w - 60, 45)
        pygame.draw.rect(self.screen, (20, 25, 35), input_rect, border_radius=8)
        pygame.draw.rect(self.screen, (100, 100, 120), input_rect, width=2, border_radius=8)
        
        # النص المدخل
        name_font = pygame.font.Font(None, 36)
        display_text = self.player_name
        if self.cursor_visible:
            display_text += "|"
        name_surf = name_font.render(display_text, True, (255, 255, 255))
        self.screen.blit(name_surf, (input_rect.x + 15, input_rect.y + 8))
        
        # زر التأكيد
        confirm_text = "Press ENTER to confirm"
        confirm_surf = prompt_font.render(confirm_text, True, (150, 200, 150))
        confirm_rect = confirm_surf.get_rect(center=(self.W // 2, dialog_y + dialog_h - 35))
        self.screen.blit(confirm_surf, confirm_rect)

# ============== Show Leaderboard Function ==============
def show_leaderboard(screen: pygame.Surface, clock: pygame.time.Clock, 
                     highlight_rank: int = -1) -> bool:
    """
    عرض شاشة قائمة النتائج
    يرجع True للعودة للقائمة الرئيسية
    """
    leaderboard_screen = LeaderboardScreen(screen)
    
    running = True
    while running:
        dt = clock.get_time() / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return True
            if event.type == pygame.MOUSEBUTTONDOWN:
                return True
        
        leaderboard_screen.update(dt)
        leaderboard_screen.draw(highlight_rank)
        pygame.display.flip()
        clock.tick(60)
    
    return True

def show_name_input(screen: pygame.Surface, clock: pygame.time.Clock,
                    score: int, kills: int, level: int) -> str:
    """
    عرض نافذة إدخال الاسم
    يرجع اسم اللاعب
    """
    dialog = NameInputDialog(screen, score, kills, level)
    
    while True:
        dt = clock.get_time() / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "Player"
            
            result = dialog.handle_event(event)
            if result:
                return result
        
        dialog.update(dt)
        dialog.draw()
        pygame.display.flip()
        clock.tick(60)
