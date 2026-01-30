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
    """Enhanced Multiplayer menu with Hamachi IP detection"""
    from util import Button, draw_text, draw_shadow_text
    
    network = NetworkManager()
    selected_option = None
    server_ip = ""
    input_active = False
    status_message = ""
    status_color = (255, 255, 255)
    
    # Detect IPs
    hamachi_ip = get_hamachi_ip()
    local_ip = get_local_ip()
    
    print("=" * 60)
    print("🌐 Network Information:")
    print(f"   Hamachi IP: {hamachi_ip or 'Not detected'}")
    print(f"   Local IP: {local_ip}")
    print("=" * 60)
    
    # Buttons
    host_btn = Button(pygame.Rect(WINDOW_W//2 - 120, WINDOW_H//2 - 60, 240, 44), "Host Game (Player 1)")
    join_btn = Button(pygame.Rect(WINDOW_W//2 - 120, WINDOW_H//2, 240, 44), "Join Game (Player 2)")
    back_btn = Button(pygame.Rect(WINDOW_W//2 - 120, WINDOW_H//2 + 140, 240, 44), "Back to Menu")
    
    # IP input field
    ip_input_rect = pygame.Rect(WINDOW_W//2 - 150, WINDOW_H//2 + 70, 300, 40)
    
    font = pygame.font.Font(None, 32)
    small_font = pygame.font.Font(None, 20)
    
    while True:
        screen.fill((40, 40, 80))
        
        # Title
        title = "Multiplayer Mode - Hamachi"
        draw_shadow_text(screen, title, (WINDOW_W//2 - 220, 50), size=42, color=(255, 255, 255))
        
        # Show detected Hamachi IP
        if hamachi_ip:
            ip_box = pygame.Rect(WINDOW_W//2 - 200, 120, 400, 80)
            pygame.draw.rect(screen, (20, 60, 20, 180), ip_box, border_radius=10)
            pygame.draw.rect(screen, (0, 255, 0), ip_box, width=2, border_radius=10)
            
            draw_text(screen, "✓ Hamachi Detected!", (WINDOW_W//2 - 100, 130), 
                     size=24, color=(0, 255, 0))
            draw_text(screen, f"Your Hamachi IP: {hamachi_ip}", (WINDOW_W//2 - 150, 160), 
                     size=28, color=(255, 255, 255))
            
            # Copy button hint
            draw_text(screen, "(Share this with Player 2)", (WINDOW_W//2 - 110, 185), 
                     size=18, color=(200, 200, 200))
        else:
            ip_box = pygame.Rect(WINDOW_W//2 - 200, 120, 400, 80)
            pygame.draw.rect(screen, (60, 20, 20, 180), ip_box, border_radius=10)
            pygame.draw.rect(screen, (255, 100, 0), ip_box, width=2, border_radius=10)
            
            draw_text(screen, "⚠ Hamachi Not Detected", (WINDOW_W//2 - 120, 130), 
                     size=24, color=(255, 200, 0))
            draw_text(screen, "Make sure Hamachi is ON", (WINDOW_W//2 - 110, 160), 
                     size=22, color=(255, 255, 255))
            draw_text(screen, f"Local IP: {local_ip}", (WINDOW_W//2 - 80, 185), 
                     size=18, color=(200, 200, 200))
        
        # Instructions
        instruction_y = 220
        instructions = [
            "HOW TO CONNECT:",
            "1. Both players: Open Hamachi and join same network",
            "2. Player 1: Click 'Host Game' below",
            "3. Player 2: Enter HOST's IP and click 'Join Game'",
            "4. Player 1: Press SPACE to start when connected"
        ]
        
        for i, instruction in enumerate(instructions):
            color = (255, 255, 100) if i == 0 else (220, 220, 220)
            size = 22 if i == 0 else 18
            draw_text(screen, instruction, (WINDOW_W//2 - 280, instruction_y + i * 25), 
                     size=size, color=color)
        
        # Buttons
        host_btn.draw(screen)
        join_btn.draw(screen)
        
        # IP input field (for joining)
        draw_text(screen, "Enter Host IP:", (ip_input_rect.x, ip_input_rect.y - 25), 
                 size=20, color=(200, 200, 200))
        
        pygame.draw.rect(screen, (60, 60, 90), ip_input_rect, border_radius=8)
        border_color = (100, 200, 255) if input_active else (80, 80, 120)
        pygame.draw.rect(screen, border_color, ip_input_rect, width=2, border_radius=8)
        
        # IP text
        ip_display = server_ip if server_ip else "25.x.x.x"
        ip_color = (255, 255, 255) if server_ip else (120, 120, 120)
        ip_text = font.render(ip_display, True, ip_color)
        screen.blit(ip_text, (ip_input_rect.x + 10, ip_input_rect.y + 8))
        
        # Auto-fill hint
        if hamachi_ip and not server_ip:
            draw_text(screen, f"💡 TIP: Host IP is usually {hamachi_ip}", 
                     (ip_input_rect.x, ip_input_rect.y + 45), 
                     size=16, color=(200, 200, 100))
        
        back_btn.draw(screen)
        
        # Status message
        if status_message:
            msg_box = pygame.Rect(WINDOW_W//2 - 250, WINDOW_H - 120, 500, 40)
            pygame.draw.rect(screen, (0, 0, 0, 180), msg_box, border_radius=8)
            draw_text(screen, status_message, (WINDOW_W//2 - 240, WINDOW_H - 110), 
                     size=20, color=status_color)
        
        # Connection status
        if network.connected:
            conn_color = (0, 255, 0)
            conn_text = f"✓ Connected - Players: {len(network.players)}"
        else:
            conn_color = (255, 100, 100)
            conn_text = "○ Not Connected"
        
        draw_text(screen, conn_text, (20, WINDOW_H - 40), size=20, color=conn_color)
        
        # Hamachi check reminder
        draw_text(screen, "⚠ Using Hamachi? Make sure both see GREEN dots in Hamachi!", 
                 (WINDOW_W//2 - 280, WINDOW_H - 40), size=18, color=(255, 200, 100))
        
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
                            
                            print(f"🎮 Joining game as Player 2 at {server_ip}...")
                            if network.connect_to_server(server_ip, "Player 2"):
                                selected_option = "join"
                                status_message = "Connected! Waiting for host to start..."
                                status_color = (0, 255, 0)
                                break
                            else:
                                status_message = "❌ Connection failed - Check IP and Hamachi"
                                status_color = (255, 0, 0)
                        else:
                            status_message = "Please enter server IP address"
                            status_color = (255, 200, 0)
                    elif len(server_ip) < 20:
                        # Only allow valid IP characters
                        if event.unicode in '0123456789.':
                            server_ip += event.unicode
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if ip_input_rect.collidepoint(event.pos):
                    input_active = True
                else:
                    input_active = False
                    
                if host_btn.hit(event.pos):
                    status_message = "Starting server as Player 1..."
                    status_color = (255, 255, 0)
                    pygame.display.flip()
                    
                    print("🎮 Hosting game as Player 1...")
                    print(f"📡 Your Hamachi IP: {hamachi_ip or 'Not detected'}")
                    print(f"📡 Your Local IP: {local_ip}")
                    
                    if network.start_server("Player 1"):
                        selected_option = "host"
                        status_message = "Server started! Share your IP with Player 2..."
                        status_color = (0, 255, 0)
                        break
                    else:
                        status_message = "Failed to start server - Check firewall"
                        status_color = (255, 0, 0)
                        
                elif join_btn.hit(event.pos):
                    if server_ip.strip():
                        status_message = f"Connecting to {server_ip}..."
                        status_color = (255, 255, 0)
                        pygame.display.flip()
                        
                        print(f"🎮 Joining game as Player 2 at {server_ip}...")
                        if network.connect_to_server(server_ip, "Player 2"):
                            selected_option = "join"
                            status_message = "Connected! Waiting for host..."
                            status_color = (0, 255, 0)
                            break
                        else:
                            status_message = "❌ Connection failed - Check IP and Hamachi"
                            status_color = (255, 0, 0)
                    else:
                        status_message = "Please enter server IP address"
                        status_color = (255, 200, 0)
                        
                elif back_btn.hit(event.pos):
                    network.disconnect()
                    return "menu"
        
        pygame.display.flip()
        clock.tick(FPS)
        
        if selected_option:
            pygame.time.wait(500)
            break
    
    # Start multiplayer game
    if selected_option in ["host", "join"]:
        player_id = network.player_id
        print(f"🚀 Starting multiplayer as Player {player_id}")
        
        result = run_multiplayer_game(screen, clock, network, player_id, version)
        network.disconnect()
        return result
    
    network.disconnect()
    return "menu"

def main():
    """Main game loop"""
    version = "v1.0 - Multiplayer"
    current_screen = "menu"
    
    print("=" * 60)
    print("🎮 ZOMBIE SHOOTER - Starting Game...")
    print("=" * 60)
    print("📁 Make sure all game files are in the same folder")
    print("🌐 For multiplayer: Both players need Hamachi")
    print("=" * 60)
    
    while True:
        try:
            if current_screen == "menu":
                print("\n🏠 Main Menu")
                result = main_menu(screen, clock, version)
                if result == "start":
                    current_screen = "single_player"
                    print("🎯 Starting Single Player...")
                elif result == "multiplayer":
                    current_screen = "multiplayer_menu"
                    print("👥 Opening Multiplayer Menu...")
                elif result == "leaderboard":
                    current_screen = "leaderboard"
                    print("🏆 Opening Leaderboard...")
                elif result is None:
                    print("👋 Exiting game...")
                    break
                    
            elif current_screen == "single_player":
                print("🎮 Single Player Mode Started")
                result = run_game(screen, clock, version)
                if result == "menu":
                    current_screen = "menu"
                    print("🏠 Returning to Main Menu")
                elif result is None:
                    print("👋 Exiting game...")
                    break
                    
            elif current_screen == "multiplayer_menu":
                print("👥 Multiplayer Menu Started")
                result = multiplayer_menu(screen, clock, version)
                if result == "menu":
                    current_screen = "menu"
                    print("🏠 Returning to Main Menu")
                elif result is None:
                    print("👋 Exiting game...")
                    break
            
            elif current_screen == "leaderboard":
                print("🏆 Showing Leaderboard")
                show_leaderboard(screen, clock)
                current_screen = "menu"
                print("🏠 Returning to Main Menu")
                    
        except Exception as e:
            print(f"❌ Error in game: {e}")
            import traceback
            traceback.print_exc()
            # Try to return to main menu
            try:
                current_screen = "menu"
                print("🔄 Restarting to main menu due to error...")
            except:
                print("❌ Critical error - exiting...")
                break
    
    print("\n" + "=" * 60)
    print("👋 Thanks for playing Zombie Shooter!")
    print("=" * 60)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()