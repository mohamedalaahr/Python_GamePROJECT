# chat.py - Text Chat System for Multiplayer Zombie Shooter
"""
نظام الدردشة النصية:
- إرسال واستقبال الرسائل بين اللاعبين
- واجهة رسومية متكاملة
- تاريخ الرسائل
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import time
import pygame

# ============== Constants ==============
MAX_MESSAGES = 8          # عدد الرسائل المعروضة
MAX_MESSAGE_LENGTH = 100  # طول الرسالة الأقصى
MESSAGE_LIFETIME = 15.0   # مدة عرض الرسالة (ثواني)
CHAT_KEY = pygame.K_t     # مفتاح فتح الدردشة

# ============== Chat Message ==============
@dataclass
class ChatMessage:
    """رسالة دردشة واحدة"""
    player_id: int
    player_name: str
    content: str
    timestamp: float = field(default_factory=time.time)
    color: Tuple[int, int, int] = (255, 255, 255)
    
    def get_age(self) -> float:
        """عمر الرسالة بالثواني"""
        return time.time() - self.timestamp
    
    def is_expired(self) -> bool:
        """هل انتهت صلاحية الرسالة؟"""
        return self.get_age() > MESSAGE_LIFETIME
    
    def get_alpha(self) -> int:
        """شفافية الرسالة (تتلاشى مع الوقت)"""
        age = self.get_age()
        if age < MESSAGE_LIFETIME - 3:
            return 255
        else:
            fade_progress = (age - (MESSAGE_LIFETIME - 3)) / 3
            return max(0, int(255 * (1 - fade_progress)))
    
    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "content": self.content,
            "timestamp": self.timestamp,
            "color": self.color,
        }
    
    @staticmethod
    def from_dict(data: dict) -> "ChatMessage":
        return ChatMessage(
            player_id=data.get("player_id", 0),
            player_name=data.get("player_name", "Unknown"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", time.time()),
            color=tuple(data.get("color", (255, 255, 255))),
        )

# ============== Chat System ==============
class ChatSystem:
    """نظام الدردشة الكامل"""
    
    def __init__(self, screen_width: int, screen_height: int, player_id: int = 0, player_name: str = "Player"):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.player_id = player_id
        self.player_name = player_name
        
        # الرسائل
        self.messages: List[ChatMessage] = []
        
        # حالة الإدخال
        self.input_active = False
        self.current_input = ""
        self.cursor_visible = True
        self.cursor_timer = 0.0
        
        # ألوان اللاعبين
        self.player_colors = {
            1: (100, 200, 255),   # أزرق فاتح
            2: (255, 150, 100),   # برتقالي
            3: (100, 255, 150),   # أخضر فاتح
            4: (255, 100, 200),   # وردي
        }
        
        # موقع الدردشة
        self.chat_x = 16
        self.chat_y = screen_height - 300
        self.chat_width = 400
        self.input_height = 35
        
        # قائمة الرسائل المعلقة للإرسال
        self.pending_messages: List[dict] = []
    
    def set_player_info(self, player_id: int, player_name: str):
        """تحديث معلومات اللاعب"""
        self.player_id = player_id
        self.player_name = player_name
    
    def get_player_color(self, player_id: int) -> Tuple[int, int, int]:
        """الحصول على لون اللاعب"""
        return self.player_colors.get(player_id, (200, 200, 200))
    
    def add_message(self, message: ChatMessage):
        """إضافة رسالة جديدة"""
        # تعيين اللون حسب اللاعب
        message.color = self.get_player_color(message.player_id)
        self.messages.append(message)
        
        # الاحتفاظ بآخر N رسائل فقط
        if len(self.messages) > MAX_MESSAGES * 2:
            self.messages = self.messages[-MAX_MESSAGES * 2:]
    
    def add_system_message(self, content: str):
        """إضافة رسالة نظام"""
        self.add_message(ChatMessage(
            player_id=0,
            player_name="System",
            content=content,
            color=(255, 255, 100),
        ))
    
    def send_message(self, content: str) -> Optional[dict]:
        """
        إرسال رسالة جديدة
        يرجع البيانات للإرسال عبر الشبكة
        """
        if not content or len(content) > MAX_MESSAGE_LENGTH:
            return None
        
        message = ChatMessage(
            player_id=self.player_id,
            player_name=self.player_name,
            content=content,
        )
        
        # إضافة للقائمة المحلية
        self.add_message(message)
        
        # إرجاع البيانات للإرسال
        return {
            "type": "chat",
            "message": message.to_dict(),
        }
    
    def receive_message(self, data: dict):
        """استقبال رسالة من الشبكة"""
        if "message" in data:
            message = ChatMessage.from_dict(data["message"])
            # تجنب تكرار الرسائل الخاصة بنا
            if message.player_id != self.player_id:
                self.add_message(message)
    
    def get_pending_messages(self) -> List[dict]:
        """الحصول على الرسائل المعلقة للإرسال"""
        pending = self.pending_messages.copy()
        self.pending_messages.clear()
        return pending
    
    def toggle_input(self):
        """تبديل وضع الإدخال"""
        self.input_active = not self.input_active
        if self.input_active:
            self.current_input = ""
    
    def handle_event(self, event) -> Optional[dict]:
        """
        معالجة الأحداث
        يرجع بيانات الرسالة للإرسال أو None
        """
        if event.type == pygame.KEYDOWN:
            # فتح الدردشة
            if event.key == CHAT_KEY and not self.input_active:
                self.toggle_input()
                return None
            
            if self.input_active:
                if event.key == pygame.K_RETURN:
                    # إرسال الرسالة
                    if self.current_input.strip():
                        result = self.send_message(self.current_input.strip())
                        self.current_input = ""
                        self.input_active = False
                        return result
                    else:
                        self.input_active = False
                        
                elif event.key == pygame.K_ESCAPE:
                    # إلغاء
                    self.current_input = ""
                    self.input_active = False
                    
                elif event.key == pygame.K_BACKSPACE:
                    # حذف حرف
                    self.current_input = self.current_input[:-1]
                    
                elif len(self.current_input) < MAX_MESSAGE_LENGTH:
                    # إضافة حرف
                    if event.unicode and event.unicode.isprintable():
                        self.current_input += event.unicode
        
        return None
    
    def update(self, dt: float):
        """تحديث النظام"""
        # تحديث مؤشر الكتابة
        self.cursor_timer += dt
        if self.cursor_timer > 0.5:
            self.cursor_timer = 0
            self.cursor_visible = not self.cursor_visible
        
        # إزالة الرسائل المنتهية
        self.messages = [m for m in self.messages if not m.is_expired()]
    
    def is_typing(self) -> bool:
        """هل اللاعب يكتب حالياً؟"""
        return self.input_active
    
    def draw(self, screen: pygame.Surface):
        """رسم واجهة الدردشة"""
        # الرسائل المعروضة (آخر N رسائل غير منتهية)
        visible_messages = [m for m in self.messages if not m.is_expired()][-MAX_MESSAGES:]
        
        # رسم الرسائل
        message_font = pygame.font.Font(None, 22)
        y = self.chat_y
        
        for msg in visible_messages:
            alpha = msg.get_alpha()
            
            # خلفية الرسالة
            name_text = f"[{msg.player_name}]: "
            content_text = msg.content
            
            name_surf = message_font.render(name_text, True, msg.color)
            content_surf = message_font.render(content_text, True, (255, 255, 255))
            
            total_width = name_surf.get_width() + content_surf.get_width() + 16
            
            # خلفية شبه شفافة
            bg_rect = pygame.Rect(self.chat_x - 4, y - 2, total_width, 22)
            bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            bg_surf.fill((0, 0, 0, int(150 * alpha / 255)))
            screen.blit(bg_surf, bg_rect.topleft)
            
            # تطبيق الشفافية
            name_surf.set_alpha(alpha)
            content_surf.set_alpha(alpha)
            
            # رسم النص
            screen.blit(name_surf, (self.chat_x, y))
            screen.blit(content_surf, (self.chat_x + name_surf.get_width(), y))
            
            y += 24
        
        # صندوق الإدخال (إذا كان نشطاً)
        if self.input_active:
            input_y = self.chat_y + MAX_MESSAGES * 24 + 10
            input_rect = pygame.Rect(self.chat_x, input_y, self.chat_width, self.input_height)
            
            # خلفية
            pygame.draw.rect(screen, (20, 25, 35, 220), input_rect, border_radius=6)
            pygame.draw.rect(screen, (100, 150, 255), input_rect, width=2, border_radius=6)
            
            # النص المدخل مع المؤشر
            input_font = pygame.font.Font(None, 24)
            display_text = self.current_input
            if self.cursor_visible:
                display_text += "|"
            
            input_surf = input_font.render(display_text, True, (255, 255, 255))
            screen.blit(input_surf, (input_rect.x + 10, input_rect.y + 8))
            
            # تعليمات
            help_font = pygame.font.Font(None, 18)
            help_surf = help_font.render("Press ENTER to send, ESC to cancel", True, (150, 150, 150))
            screen.blit(help_surf, (input_rect.x, input_rect.bottom + 5))
        else:
            # تعليمات لفتح الدردشة
            if len(visible_messages) == 0:
                hint_font = pygame.font.Font(None, 20)
                hint_surf = hint_font.render("Press T to chat", True, (100, 100, 100))
                screen.blit(hint_surf, (self.chat_x, self.chat_y))
    
    def draw_indicator(self, screen: pygame.Surface, x: int, y: int):
        """رسم مؤشر الكتابة فوق رأس اللاعب"""
        if self.input_active:
            font = pygame.font.Font(None, 18)
            text_surf = font.render("Typing...", True, (100, 200, 255))
            text_rect = text_surf.get_rect(center=(x, y - 15))
            
            bg_rect = text_rect.inflate(8, 4)
            pygame.draw.rect(screen, (0, 0, 0, 180), bg_rect, border_radius=4)
            screen.blit(text_surf, text_rect)