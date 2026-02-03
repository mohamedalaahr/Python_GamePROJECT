# main.py - COMPLETE VERSION WITH HAMACHI SUPPORT
import pygame
import sys
import os
import socket
import subprocess
import re

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from game import main_menu, run_game
from multiplayer_game import run_multiplayer_game
from network import NetworkManager
from skins import draw_skin_selector, get_clicked_skin, DEFAULT_SKIN

# Import leaderboard
try:
    from leaderboard import show_leaderboard
except ImportError:
    def show_leaderboard(screen, clock, highlight_rank=-1):
        print("Leaderboard module not found")
        return True

# Initialize Pygame
pygame.init()

# Window setup
WINDOW_W, WINDOW_H = 1280, 720
screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
pygame.display.set_caption("Zombie Shooter")
clock = pygame.time.Clock()
FPS = 60

# Set window icon
try:
    icon_path = os.path.join("images", "heart.png")
    if os.path.isfile(icon_path):
        icon = pygame.image.load(icon_path).convert_alpha()
        pygame.display.set_icon(icon)
except Exception:
    pass

def get_hamachi_ip():
    """Try to automatically detect Hamachi IP address"""
    try:
        # Method 1: Check for Hamachi network adapter (Windows)
        if os.name == 'nt':  # Windows
            # Try to get IP from ipconfig
            result = subprocess.run(['ipconfig'], capture_output=True, text=True)
            output = result.stdout
            
            # Look for Hamachi adapter section
            hamachi_section = False
            for line in output.split('\n'):
                if 'Hamachi' in line or 'LogMeIn' in line:
                    hamachi_section = True
                elif hamachi_section and 'IPv4' in line:
                    # Extract IP address
                    match = re.search(r'25\.\d{1,3}\.\d{1,3}\.\d{1,3}', line)
                    if match:
                        return match.group(0)
        
        # Method 2: Check all network interfaces for Hamachi IP range (25.x.x.x)
        hostname = socket.gethostname()
        ip_list = socket.getaddrinfo(hostname, None)
        
        for ip_info in ip_list:
            ip = ip_info[4][0]
            if ip.startswith('25.'):
                return ip
        
        return None
    except Exception as e:
        print(f"Could not detect Hamachi IP: {e}")
        return None

def get_local_ip():
    """Get local network IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "Unknown"

def multiplayer_menu(screen, clock, version=""):
    """Enhanced Multiplayer menu with Hamachi IP detection and Skin Selection"""
    from util import Button, draw_text, draw_shadow_text
    
    network = NetworkManager()
    selected_option = None
    server_ip = ""
    input_active = False
    status_message = ""
    status_color = (255, 255, 255)
    selected_skin = DEFAULT_SKIN
    
    # Detect IPs
    hamachi_ip = get_hamachi_ip()
    local_ip = get_local_ip()
    
    print("=" * 60)
    print("[NET] Network Information:")
    print(f"   Hamachi IP: {hamachi_ip or 'Not detected'}")
    print(f"   Local IP: {local_ip}")
    print("=" * 60)
    
    # Buttons
    start_y = 200
    # Buttons (Adjusted Positions & Width)
    btn_w, btn_h = 300, 50  # Increased width
    host_btn = Button(pygame.Rect(WINDOW_W//2 - btn_w//2, start_y, btn_w, btn_h), "Host Game (P1)")
    join_btn = Button(pygame.Rect(WINDOW_W//2 - btn_w//2, start_y + 70, btn_w, btn_h), "Join Game (P2)")
    back_btn = Button(pygame.Rect(WINDOW_W//2 - btn_w//2, WINDOW_H - 90, btn_w, btn_h), "Back to Menu")
    
    # IP input field
    ip_input_rect = pygame.Rect(WINDOW_W//2 - 150, start_y + 150, 300, 40)
    
    font = pygame.font.Font(None, 32)
    small_font = pygame.font.Font(None, 20)
    
    # === SKIN SELECTOR ===
    selector_y = WINDOW_H - 180
    
    # Instructions list
    instructions = [
        "How to Play:",
        "1. P1: Click 'Host Game'",
        "2. P2: Enter P1's IP",
        "3. P2: Click 'Join Game'",
        "4. P1: Wait for P2",
        "5. Game starts!"
    ]
    
    while True:
        # 🔥 HORROR THEME ...
        screen.fill((15, 5, 8))
        
        # ... (Draw title, Hamachi info, etc - kept same) ...
        title = "Multiplayer Mode - Hamachi"
        draw_shadow_text(screen, title, (WINDOW_W//2 - 220, 30), size=42, color=(180, 30, 30))
        
        # Show detected Hamachi IP
        if hamachi_ip:
            ip_box = pygame.Rect(WINDOW_W//2 - 200, 80, 400, 70)
            pygame.draw.rect(screen, (20, 60, 20, 180), ip_box, border_radius=10)
            pygame.draw.rect(screen, (0, 255, 0), ip_box, width=2, border_radius=10)
            
            draw_text(screen, "✓ Hamachi Detected!", (WINDOW_W//2 - 100, 90),
                     size=24, color=(0, 255, 0))
            draw_text(screen, f"Your IP: {hamachi_ip}", (WINDOW_W//2 - 80, 120),
                     size=24, color=(255, 255, 255))
        else:
            ip_box = pygame.Rect(WINDOW_W//2 - 200, 80, 400, 70)
            pygame.draw.rect(screen, (60, 20, 20, 180), ip_box, border_radius=10)
            pygame.draw.rect(screen, (255, 100, 0), ip_box, width=2, border_radius=10)
            
            draw_text(screen, "⚠ Hamachi Not Detected", (WINDOW_W//2 - 120, 90),
                     size=24, color=(255, 200, 0))
            draw_text(screen, f"Local IP: {local_ip}", (WINDOW_W//2 - 80, 120),
                     size=20, color=(200, 200, 200))
        
        # Draw instructions panel
        inst_rect = pygame.Rect(50, 180, 300, 200)
        pygame.draw.rect(screen, (0, 0, 0, 100), inst_rect, border_radius=10)
        pygame.draw.rect(screen, (100, 100, 150), inst_rect, width=1, border_radius=10)
        
        for i, instruction in enumerate(instructions):
            color = (255, 255, 100) if i == 0 else (220, 220, 220)
            draw_text(screen, instruction, (60, 190 + i * 30), size=20, color=color)
        
        # Buttons
        host_btn.draw(screen)
        join_btn.draw(screen)
        
        # IP input field
        draw_text(screen, "Enter Host IP (for P2):", (ip_input_rect.x, ip_input_rect.y - 25), 
                 size=20, color=(200, 200, 200))
        
        pygame.draw.rect(screen, (60, 60, 90), ip_input_rect, border_radius=8)
        border_color = (100, 200, 255) if input_active else (80, 80, 120)
        pygame.draw.rect(screen, border_color, ip_input_rect, width=2, border_radius=8)
        
        ip_display = server_ip if server_ip else "25.x.x.x"
        ip_color = (255, 255, 255) if server_ip else (120, 120, 120)
        ip_text = font.render(ip_display, True, ip_color)
        screen.blit(ip_text, (ip_input_rect.x + 10, ip_input_rect.y + 8))
        
        # === SKIN SELECTOR ===
        selector_y = WINDOW_H - 180
        draw_skin_selector(screen, selected_skin, WINDOW_W//2, selector_y)
        
        back_btn.draw(screen)
        
        # Status message
        if status_message:
            msg_box = pygame.Rect(WINDOW_W//2 - 250, WINDOW_H - 130, 500, 40)
            pygame.draw.rect(screen, (0, 0, 0, 180), msg_box, border_radius=8)
            draw_text(screen, status_message, (WINDOW_W//2 - 240, WINDOW_H - 120), 
                     size=20, color=status_color)
        
        # Connection status
        conn_text = f"Players: {len(network.players)}" if network.connected else "Not Connected"
        conn_color = (0, 255, 0) if network.connected else (150, 150, 150)
        draw_text(screen, conn_text, (20, WINDOW_H - 30), size=18, color=conn_color)
        
        # Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                network.disconnect()
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    network.disconnect()
                    return "menu"
                
                if input_active:
                    if event.key == pygame.K_BACKSPACE:
                        server_ip = server_ip[:-1]
                    elif event.key == pygame.K_RETURN:
                        if server_ip.strip():
                            status_message = f"Connecting to {server_ip}..."
                            status_color = (255, 255, 0)
                            pygame.display.flip()
                            
                            print(f"[JOIN] Joining game as Player 2 at {server_ip}...")
                            if network.connect_to_server(server_ip, "Player 2"):
                                selected_option = "join"
                                status_message = "Connected! Waiting for host to start..."
                                status_color = (0, 255, 0)
                                # Data will be sent in run_multiplayer_game
                                break
                            else:
                                status_message = "❌ Connection failed - Check IP and Hamachi"
                                status_color = (255, 0, 0)
                    elif len(server_ip) < 20:
                        if event.unicode in '0123456789.':
                            server_ip += event.unicode
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Skin Selection
                clicked_skin = get_clicked_skin(event.pos, WINDOW_W//2, selector_y)
                if clicked_skin:
                    selected_skin = clicked_skin
                    if network.connected:
                        network.send_skin_data(selected_skin)
                
                if ip_input_rect.collidepoint(event.pos):
                    input_active = True
                else:
                    input_active = False
                    
                if host_btn.hit(event.pos):
                    status_message = "Starting server as Player 1..."
                    status_color = (255, 255, 0)
                    pygame.display.flip()
                    
                    if network.start_server("Player 1"):
                        selected_option = "host"
                        status_message = "Server started! Share your IP with Player 2..."
                        status_color = (0, 255, 0)
                        # Data will be sent in run_multiplayer_game
                        break
                    else:
                        status_message = "Failed to start server - Check firewall"
                        status_color = (255, 0, 0)
                        
                elif join_btn.hit(event.pos):
                    if server_ip.strip():
                        status_message = f"Connecting to {server_ip}..."
                        status_color = (255, 255, 0)
                        pygame.display.flip()
                        
                        if network.connect_to_server(server_ip, "Player 2"):
                            selected_option = "join"
                            status_message = "Connected! Waiting for host..."
                            status_color = (0, 255, 0)
                            network.send_skin_data(selected_skin) # Send my skin immediately
                            network.send_player_data({"character_type": "player"})
                            break
                        else:
                            status_message = "❌ Connection failed - Check IP and Hamachi"
                            status_color = (255, 0, 0)
                        
                elif back_btn.hit(event.pos):
                    network.disconnect()
                    return "menu"
        
        pygame.display.flip()
        clock.tick(60)
        
        if selected_option:
            pygame.time.wait(500)
            break
    
    # Start multiplayer game
    if selected_option in ["host", "join"]:
        player_id = network.player_id
        print(f"[START] Starting multiplayer as Player {player_id} | Skin: {selected_skin}")
        
        result = run_multiplayer_game(screen, clock, network, player_id, version, selected_skin, character_type="player")
        network.disconnect()
        return result
    
    network.disconnect()
    return "menu"

def main():
    """Main game loop"""
    version = "v1.0 - Multiplayer"
    current_screen = "menu"
    
    print("=" * 60)
    print("[GAME] ZOMBIE SHOOTER - Starting Game...")
    print("=" * 60)
    print("[INFO] Make sure all game files are in the same folder")
    print("[NET] For multiplayer: Both players need Hamachi")
    print("=" * 60)
    
    while True:
        try:
            if current_screen == "menu":
                print("\n[MENU] Main Menu")
                result = main_menu(screen, clock, version)
                if result == "start":
                    current_screen = "single_player"
                    print("[START] Starting Single Player...")
                elif result == "multiplayer":
                    current_screen = "multiplayer_menu"
                    print("[MP] Opening Multiplayer Menu...")
                elif result == "leaderboard":
                    current_screen = "leaderboard"
                    print("[LEAD] Opening Leaderboard...")
                elif result is None:
                    print("[EXIT] Exiting game...")
                    break
                    
            elif current_screen == "single_player":
                print("[PLAY] Single Player Mode Started")
                # شاشة اختيار بسيطة للشخصية (Classic vs Commando)
                selected_char = show_character_select(screen, clock)
                result = run_game(screen, clock, version, character=selected_char)
                if result == "menu":
                    current_screen = "menu"
                    print("[MENU] Returning to Main Menu")
                elif result is None:
                    print("[EXIT] Exiting game...")
                    break
                    
            elif current_screen == "multiplayer_menu":
                print("[MP] Multiplayer Menu Started")
                result = multiplayer_menu(screen, clock, version)
                if result == "menu":
                    current_screen = "menu"
                    print("[MENU] Returning to Main Menu")
                elif result is None:
                    print("[EXIT] Exiting game...")
                    break
            
            elif current_screen == "leaderboard":
                print("[LEAD] Showing Leaderboard")
                show_leaderboard(screen, clock)
                current_screen = "menu"
                print("[MENU] Returning to Main Menu")
                    
        except Exception as e:
            print(f"[ERROR] Error in game: {e}")
            import traceback
            traceback.print_exc()
            # Try to return to main menu
            try:
                current_screen = "menu"
                print("[RESTART] Restarting to main menu due to error...")
            except:
                print("[CRITICAL] Critical error - exiting...")
                break
    
    print("\n" + "=" * 60)
    print("[BYE] Thanks for playing Zombie Shooter!")
    print("=" * 60)
    
    pygame.quit()
    sys.exit()

# شاشة اختيار شخصية بسيطة قبل الدخول للوضع الفردي

def show_character_select(screen: pygame.Surface, clock: pygame.time.Clock) -> str:
    from util import Button, draw_text
    W, H = screen.get_size()
    cx, cy = W // 2, H // 2
    # زرين للاختيار
    btn_w, btn_h = 220, 60
    classic_btn = Button(pygame.Rect(cx - btn_w - 20, cy - 30, btn_w, btn_h), "Classic")
    commando_btn = Button(pygame.Rect(cx + 20, cy - 30, btn_w, btn_h), "Commando")
    # تلميح
    tip_font = pygame.font.Font(None, 32)

    selected = None
    while selected is None:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return "player"
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return "player"
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if classic_btn.hit(e.pos):
                    selected = "player"
                elif commando_btn.hit(e.pos):
                    selected = "commando"
        # خلفية وبسيطة
        screen.fill((18, 10, 12))
        title = pygame.font.Font(None, 56).render("Choose Character", True, (255, 200, 200))
        screen.blit(title, title.get_rect(center=(cx, cy - 110)))
        # رسم الأزرار
        classic_btn.draw(screen)
        commando_btn.draw(screen)
        # تلميح
        tip = tip_font.render("ESC to cancel (Classic)", True, (180, 160, 160))
        screen.blit(tip, tip.get_rect(center=(cx, cy + 60)))
        pygame.display.flip()
        clock.tick(60)
    return selected

if __name__ == "__main__":
    main()