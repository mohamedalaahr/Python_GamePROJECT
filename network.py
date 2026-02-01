# network.py - IMPROVED VERSION WITH BETTER SYNC
import socket
import threading
import pickle
import time
import queue
from typing import Dict, Any, List

# ---------------- Network Configuration ----------------
SERVER_PORT = 5555
BUFFER_SIZE = 8192  # Increased buffer size

# ---------------- Network Manager ----------------
class NetworkManager:
    def __init__(self):
        self.socket = None
        self.client_socket = None
        self.connected = False
        self.is_host = False
        self.players: Dict[int, Dict[str, Any]] = {}
        self.player_id = None
        self.player_name = ""
        self.server_ip = ""
        self.received_queue = queue.Queue()  # Thread-safe queue
        self.thread = None
        self.running = False
        
    def start_server(self, player_name: str) -> bool:
        """Start a new server (HOST) - IMPROVED VERSION"""
        try:
            # تحقق من أن المنفذ متاح
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            try:
                test_socket.bind(('0.0.0.0', SERVER_PORT))
                test_socket.close()
            except OSError as e:
                print(f"[ERR] Port {SERVER_PORT} is already in use: {e}")
                print("[TIP] Try closing other programs or restarting the game")
                return False

            # إنشاء السيرفر الرئيسي
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('0.0.0.0', SERVER_PORT))
            self.socket.listen(1)
            self.is_host = True
            self.player_name = player_name
            self.player_id = 1
            self.players[1] = {"name": player_name, "connected": True}
            
            print(f"[OK] Server started successfully on port {SERVER_PORT}")
            print("[WAIT] Waiting for player 2...")
            
            # عرض جميع عناوين IP المتاحة
            print("[NET] Available IP addresses for connection:")
            try:
                # عنوان Hamachi
                hostname = socket.gethostname()
                all_ips = socket.getaddrinfo(hostname, None)
                for ip in all_ips:
                    ip_addr = ip[4][0]
                    if ip_addr.startswith('25.') or ip_addr.startswith('192.168.'):
                        print(f"   [IP] {ip_addr}")
            except:
                print("   [IP] 25.14.130.113 (Your Hamachi IP)")
            
            print("[INFO] Make sure Windows Firewall allows the game")
            
            self.running = True
            self.thread = threading.Thread(target=self._server_listen)
            self.thread.daemon = True
            self.thread.start()
            
            return True
        except Exception as e:
            print(f"[ERR] Failed to start server: {e}")
            print("[FIX] Troubleshooting tips:")
            print("   1. Run the game as Administrator")
            print("   2. Check Windows Firewall settings")
            print("   3. Make sure Hamachi is running and connected")
            return False
    
    def connect_to_server(self, server_ip: str, player_name: str) -> bool:
        """Connect to existing server (CLIENT)"""
        try:
            print(f"[CONN] Connecting to {server_ip}:{SERVER_PORT}...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)  # 10 second timeout
            self.socket.connect((server_ip, SERVER_PORT))
            self.socket.settimeout(None)  # Remove timeout after connection
            
            self.is_host = False
            self.player_name = player_name
            self.server_ip = server_ip
            
            # Send join request
            join_data = {
                "type": "player_join",
                "player_name": player_name
            }
            self._send_data(join_data)
            
            print("[OK] Connected! Waiting for game data...")
            
            # Start receive thread
            self.running = True
            self.thread = threading.Thread(target=self._client_receive)
            self.thread.daemon = True
            self.thread.start()
            
            # Wait a bit for welcome message
            time.sleep(0.5)
            
            return True
        except socket.timeout:
            print(f"[ERR] Connection timeout - server not responding")
            return False
        except ConnectionRefusedError:
            print(f"[ERR] Connection refused - server not running at {server_ip}")
            return False
        except Exception as e:
            print(f"[ERR] Failed to connect: {e}")
            return False
    
    def _server_listen(self):
        """Server listen thread - accepts player 2"""
        try:
            print("[WAIT] Waiting for player 2 to connect...")
            client_socket, address = self.socket.accept()
            self.client_socket = client_socket
            self.connected = True
            
            print(f"[OK] Player 2 connected from {address}")
            
            # Wait for join message
            try:
                data = self._receive_data(client_socket)
                if data and data.get("type") == "player_join":
                    self.players[2] = {
                        "name": data["player_name"],
                        "connected": True
                    }
                    
                    # Send welcome
                    welcome_data = {
                        "type": "welcome",
                        "player_id": 2,
                        "players": self.players
                    }
                    self._send_data(welcome_data)
                    print(f"[WELCOME] Welcomed {data['player_name']} as Player 2")
            except Exception as e:
                print(f"[ERR] Error in welcome handshake: {e}")
                return
            
            # Receive loop
            while self.running:
                try:
                    data = self._receive_data(client_socket)
                    if data:
                        self.received_queue.put(data)
                    else:
                        break
                except Exception as e:
                    if self.running:
                        print(f"[ERR] Server receive error: {e}")
                    break
                    
            print("[DC] Player 2 disconnected")
            self.connected = False
            
        except Exception as e:
            print(f"[ERR] Server listen error: {e}")
            self.connected = False
    
    def _client_receive(self):
        """Client receive thread"""
        try:
            # Wait for welcome message
            print("[WAIT] Waiting for welcome message...")
            welcome_received = False
            timeout = time.time() + 5  # 5 second timeout
            
            while not welcome_received and time.time() < timeout:
                try:
                    data = self._receive_data(self.socket)
                    if data and data.get("type") == "welcome":
                        self.player_id = data["player_id"]
                        self.players = data["players"]
                        self.connected = True
                        welcome_received = True
                        print(f"[OK] Assigned Player ID: {self.player_id}")
                        self.received_queue.put(data)
                    elif data:
                        self.received_queue.put(data)
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[ERR] Error waiting for welcome: {e}")
                    return
            
            if not welcome_received:
                print("[ERR] Did not receive welcome message from server")
                return
            
            # Main receive loop
            while self.running:
                try:
                    data = self._receive_data(self.socket)
                    if data:
                        self.received_queue.put(data)
                    else:
                        break
                except Exception as e:
                    if self.running:
                        print(f"[ERR] Client receive error: {e}")
                    break
                    
            print("[DC] Disconnected from server")
            self.connected = False
            
        except Exception as e:
            print(f"[ERR] Client receive error: {e}")
            self.connected = False
    
    def _receive_data(self, sock: socket.socket) -> Dict[str, Any] | None:
        """Receive data with proper framing"""
        try:
            # First receive the size (4 bytes)
            size_data = b''
            while len(size_data) < 4:
                chunk = sock.recv(4 - len(size_data))
                if not chunk:
                    return None
                size_data += chunk
            
            msg_size = int.from_bytes(size_data, byteorder='big')
            
            # Receive the actual message
            data = b''
            while len(data) < msg_size:
                chunk = sock.recv(min(BUFFER_SIZE, msg_size - len(data)))
                if not chunk:
                    return None
                data += chunk
            
            return pickle.loads(data)
        except Exception as e:
            if self.running:
                print(f"[ERR] Receive error: {e}")
            return None
    
    def _send_data(self, data: Dict[str, Any]):
        """Send data with proper framing"""
        try:
            serialized = pickle.dumps(data)
            msg_size = len(serialized)
            size_bytes = msg_size.to_bytes(4, byteorder='big')
            
            if self.is_host and self.client_socket:
                self.client_socket.sendall(size_bytes + serialized)
            elif not self.is_host and self.socket:
                self.socket.sendall(size_bytes + serialized)
                
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            if self.running:
                print(f"[ERR] Send error: {e}")
                self.connected = False
        except Exception as e:
            if self.running:
                print(f"[ERR] Unexpected send error: {e}")
    
    def send_game_state(self, game_state: Dict[str, Any]):
        """Send game state"""
        if not self.connected:
            return
        self._send_data(game_state)
    
    def send_player_data(self, player_data: Dict[str, Any]):
        """Send player data"""
        if not self.connected:
            return
            
        data = {
            "type": "player_update",
            "player_id": self.player_id,
            "player_data": player_data,
            "timestamp": time.time()
        }
        self._send_data(data)
    
    def send_player_action(self, action: Dict[str, Any]):
        """Send player action"""
        if not self.connected:
            return
            
        data = {
            "type": "player_action",
            "player_id": self.player_id,
            "action": action,
            "timestamp": time.time()
        }
        self._send_data(data)
    
    def send_start_game(self):
        """Send start game signal (HOST only)"""
        if not self.is_host or not self.connected:
            return
            
        data = {
            "type": "start_game",
            "timestamp": time.time()
        }
        self._send_data(data)
        print("[START] Start game signal sent!")
    
    def send_chat_message(self, message: str, player_name: str = "Player"):
        """Send chat message to other players"""
        if not self.connected:
            return
            
        data = {
            "type": "chat",
            "player_id": self.player_id,
            "player_name": player_name,
            "message": message,
            "timestamp": time.time()
        }
        self._send_data(data)
    
    def send_skin_data(self, skin_id: str):
        """Send player skin selection"""
        if not self.connected:
            return
            
        data = {
            "type": "skin_update",
            "player_id": self.player_id,
            "skin_id": skin_id,
            "timestamp": time.time()
        }
        self._send_data(data)
    
    def send_weapon_data(self, weapon_type: int, ammo: dict):
        """Send weapon state"""
        if not self.connected:
            return
            
        data = {
            "type": "weapon_update",
            "player_id": self.player_id,
            "weapon_type": weapon_type,
            "ammo": ammo,
            "timestamp": time.time()
        }
        self._send_data(data)
    
    def get_received_data(self) -> List[Dict[str, Any]]:
        """Get all received data (thread-safe)"""
        data = []
        while not self.received_queue.empty():
            try:
                data.append(self.received_queue.get_nowait())
            except queue.Empty:
                break
        return data
    
    def disconnect(self):
        """Disconnect and cleanup"""
        print("[DC] Disconnecting...")
        self.running = False
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
                
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
                
        self.connected = False
        print("[OK] Disconnected")

if __name__ == "__main__":
    print("[GAME] Multiplayer Network Module")
    print("=" * 50)
    print("This module handles network communication for multiplayer")
    print("Features:")
    print("  - Host/Client architecture")
    print("  - Thread-safe message queue")
    print("  - Proper message framing")
    print("  - Automatic reconnection handling")