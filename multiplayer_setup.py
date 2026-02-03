# multiplayer_setup.py - Enhanced with Skin Selection
import pygame
from network import NetworkManager

# استيراد نظام المظاهر
from skins import SKINS, SKIN_ORDER, DEFAULT_SKIN, get_skin_data, draw_skin_preview

def draw_text(screen, text, pos, size=24, color=(255, 255, 255), center=False):
    """رسم نص على الشاشة - نسخة متوافقة"""
    try:
        font = pygame.font.Font(None, size)
        text_surface = font.render(text, True, color)
        
        if center:
            text_rect = text_surface.get_rect(center=pos)
        else:
            text_rect = text_surface.get_rect(topleft=pos)
        
        screen.blit(text_surface, text_rect)
        return text_rect
    except Exception as e:
        print(f"Error drawing text: {e}")
        return pygame.Rect(0, 0, 0, 0)

class Button:
    def __init__(self, rect, text, color=(80, 80, 120)):
        self.rect = rect
        self.text = text
        self.color = color
        self.hover_color = tuple(min(255, c + 30) for c in color)
        self.text_color = (255, 255, 255)
        self.hovered = False
        
    def hit(self, pos):
        return self.rect.collidepoint(pos)
    
    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)
        
    def draw(self, screen):
        color = self.hover_color if self.hovered else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        pygame.draw.rect(screen, (200, 200, 200), self.rect, width=2, border_radius=8)
        draw_text(screen, self.text, self.rect.center, size=28, color=self.text_color, center=True)

class SkinButton:
    """زر اختيار المظهر"""
    def __init__(self, x, y, skin_id, size=50):
        self.x = x
        self.y = y
        self.skin_id = skin_id
        self.size = size
        self.rect = pygame.Rect(x - 5, y - 5, size + 10, size + 35)
        self.selected = False
        
    def hit(self, pos):
        return self.rect.collidepoint(pos)
    
    def draw(self, screen):
        skin_data = get_skin_data(self.skin_id)
        color = skin_data["color"]
        
        # خلفية
        bg_color = (60, 60, 80) if self.selected else (40, 40, 50)
        border_color = (255, 200, 50) if self.selected else (100, 100, 100)
        pygame.draw.rect(screen, bg_color, self.rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.rect, width=3 if self.selected else 1, border_radius=8)
        
        # دائرة الشخصية
        cx = self.x + self.size // 2
        cy = self.y + self.size // 2
        pygame.draw.circle(screen, color, (cx, cy), self.size // 2)
        
        # الاسم
        font = pygame.font.Font(None, 16)
        name_surf = font.render(skin_data["name"], True, (255, 255, 255))
        name_rect = name_surf.get_rect(center=(cx, self.y + self.size + 12))
        screen.blit(name_surf, name_rect)

def multiplayer_setup_screen(screen, clock):
    """شاشة إعداد Multiplayer محسنة مع اختيار المظهر"""
    WINDOW_W, WINDOW_H = screen.get_size()
    network = NetworkManager()
    current_mode = "menu"
    host_ip = "localhost"
    player_name = "Player"
    selected_skin = DEFAULT_SKIN
    status_msg = ""
    
    # الأزرار الرئيسية
    # الأزرار الرئيسية - تم تعديل المواقع لتوزيع أفضل
    host_btn = Button(pygame.Rect(WINDOW_W//2-150, 160, 300, 50), "Create Room", (60, 120, 80))
    join_btn = Button(pygame.Rect(WINDOW_W//2-150, 230, 300, 50), "Join Room", (80, 80, 120))
    back_btn = Button(pygame.Rect(WINDOW_W//2-150, 300, 300, 50), "Back to Menu", (100, 60, 60))
    start_btn = Button(pygame.Rect(WINDOW_W//2-150, 230, 300, 50), "Start Game", (60, 150, 60))
    
    # أزرار المظاهر
    skin_buttons = []
    skin_start_x = WINDOW_W//2 - (len(SKIN_ORDER) * 65) // 2
    for i, skin_id in enumerate(SKIN_ORDER):
        btn = SkinButton(skin_start_x + i * 65, 380, skin_id, 50)
        if skin_id == selected_skin:
            btn.selected = True
        skin_buttons.append(btn)
    
    # Multiplayer always uses "player" (Classic) character
    selected_char = "player"
    
    running = True
    result = ("menu", None, None, None, None)  # (action, network, player_id, skin, char_type)
    
    while running:
        mouse_pos = pygame.mouse.get_pos()
        screen.fill((25, 28, 38))
        
        # تحديث الأزرار
        for btn in [host_btn, join_btn, back_btn, start_btn]:
            btn.update(mouse_pos)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                result = (None, None, None, None, None)
                
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if current_mode != "menu":
                        current_mode = "menu"
                        network.disconnect()
                        status_msg = "Disconnected"
                    else:
                        running = False
                        
                elif current_mode == "join" and event.key == pygame.K_RETURN:
                    if network.connect_to_server(host_ip, player_name):
                        current_mode = "connected"
                        status_msg = "Connected! Waiting for host..."
                        # 🔥 إرسال المظهر والشخصية (متعدد المرات للتأكد)
                        network.send_skin_data(selected_skin)
                        if hasattr(network, 'send_character_type'):
                            network.send_character_type(selected_char)
                        network.send_player_data({"character_type": selected_char, "sprite_prefix": selected_char})
                        print(f"[SETUP] Sent character type: {selected_char}")
                    else:
                        status_msg = "Connection failed!"
                        
                elif current_mode == "join" and event.key == pygame.K_BACKSPACE:
                    host_ip = host_ip[:-1]
                elif current_mode == "join" and len(host_ip) < 20:
                    if event.unicode.isprintable() and event.unicode:
                        host_ip += event.unicode
                    
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # اختيار المظهر
                for btn in skin_buttons:
                    if btn.hit(event.pos):
                        for b in skin_buttons:
                            b.selected = False
                        btn.selected = True
                        selected_skin = btn.skin_id
                        # إرسال المظهر عبر الشبكة إذا كنا متصلين
                        if network.connected:
                            network.send_skin_data(selected_skin)
                
                if current_mode == "menu":
                    if host_btn.hit(event.pos):
                        if network.start_server(player_name):
                            current_mode = "host_waiting"
                            status_msg = "Waiting for player 2..."
                            # Send host character info essentially by just being ready
                        else:
                            status_msg = "Failed to start server!"
                    elif join_btn.hit(event.pos):
                        current_mode = "join"
                        status_msg = "Enter server IP and press ENTER"
                    elif back_btn.hit(event.pos):
                        running = False
                        
                elif current_mode == "host_waiting" and network.connected:
                    if start_btn.hit(event.pos):
                        network.send_start_game()
                        print("🚀 Starting multiplayer game...")
                        result = ("multiplayer_game", network, 1, selected_skin, selected_char)
                        running = False
                        
                elif current_mode == "connected":
                    pass
        
        # التحقق من اتصال اللاعب الثاني
        if current_mode == "host_waiting" and network.connected:
            status_msg = "Player 2 connected! Click Start Game"
            # Host also sends their character info continuously or once connected
            # For simplicity, we assume client will request or we send periodically? 
            # Actually, `run_multiplayer_game` will handle the reliable sync.
        
        # استقبال إشارة البدء (للعميل)
        if current_mode == "connected":
            received = network.get_received_data()
            for data in received:
                if data.get("type") == "start_game":
                    result = ("multiplayer_game", network, 2, selected_skin, selected_char)
                    running = False
        
        # === الرسم ===
        
        # العنوان
        draw_text(screen, "MULTIPLAYER MODE", (WINDOW_W//2, 60), size=52, color=(255, 200, 50), center=True)
        draw_text(screen, "Choose your character & skin!", (WINDOW_W//2, 100), size=24, color=(180, 180, 180), center=True)
        
        if current_mode == "menu":
            host_btn.draw(screen)
            join_btn.draw(screen)
            back_btn.draw(screen)
            
        elif current_mode == "host_waiting":
            # حالة الانتظار
            draw_text(screen, status_msg, (WINDOW_W//2, 170), size=32, color=(255, 255, 100), center=True)
            
            if network.connected:
                start_btn.draw(screen)
                draw_text(screen, "✓ Player 2 is ready!", (WINDOW_W//2, 200), size=28, color=(100, 255, 100), center=True)
            else:
                # عرض عنوان IP
                draw_text(screen, "Share this IP with your friend:", (WINDOW_W//2, 220), size=24, color=(200, 200, 200), center=True)
                
                # محاولة الحصول على IP
                try:
                    import socket
                    hostname = socket.gethostname()
                    local_ip = socket.gethostbyname(hostname)
                    draw_text(screen, local_ip, (WINDOW_W//2, 250), size=36, color=(100, 200, 255), center=True)
                except:
                    draw_text(screen, "localhost", (WINDOW_W//2, 250), size=36, color=(100, 200, 255), center=True)
            
            back_btn.draw(screen)
                
        elif current_mode == "join":
            draw_text(screen, "Enter Server IP:", (WINDOW_W//2, 160), size=32, color=(255, 255, 255), center=True)
            
            # صندوق الإدخال
            input_rect = pygame.Rect(WINDOW_W//2 - 150, 200, 300, 50)
            pygame.draw.rect(screen, (40, 45, 60), input_rect, border_radius=8)
            pygame.draw.rect(screen, (100, 150, 255), input_rect, width=2, border_radius=8)
            draw_text(screen, host_ip + "|", (WINDOW_W//2, 225), size=32, color=(255, 255, 255), center=True)
            
            draw_text(screen, "Press ENTER to connect", (WINDOW_W//2, 265), size=24, color=(200, 200, 200), center=True)
            back_btn.draw(screen)
            
        elif current_mode == "connected":
            draw_text(screen, "✓ Connected!", (WINDOW_W//2, 180), size=36, color=(100, 255, 100), center=True)
            draw_text(screen, "Waiting for host to start...", (WINDOW_W//2, 220), size=28, color=(255, 255, 150), center=True)
            
            # مؤشر تحميل
            dots = "." * (int(pygame.time.get_ticks() / 500) % 4)
            draw_text(screen, dots, (WINDOW_W//2, 260), size=36, color=(200, 200, 200), center=True)
        
        # === قسم اختيار المظهر ===
        draw_text(screen, "SELECT SKIN COLOR", (WINDOW_W//2, 320), size=24, color=(180, 180, 180), center=True)
        
        for btn in skin_buttons:
            btn.draw(screen)
        
        # رسالة الحالة
        if status_msg and current_mode not in ["host_waiting", "connected"]:
            draw_text(screen, status_msg, (WINDOW_W//2, 550), size=24, color=(255, 200, 100), center=True)
        
        # تعليمات
        draw_text(screen, "Press ESC to go back", (WINDOW_W//2, WINDOW_H - 30), size=20, color=(100, 100, 100), center=True)
            
        pygame.display.flip()
        clock.tick(60)
    
    if result[0] != "multiplayer_game":
        network.disconnect()
        
    return result