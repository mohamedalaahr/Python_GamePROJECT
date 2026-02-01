# settings.py
"""
Game Settings Module
Manages game settings including volume, resolution, and key bindings.
Settings are persisted to settings.json.
"""
import os
import json
import pygame

# Default settings
DEFAULT_SETTINGS = {
    "music_volume": 0.3,
    "sfx_volume": 0.5,
    "resolution": [1280, 720],
    "key_bindings": {
        "move_up": [pygame.K_w, pygame.K_z, pygame.K_UP],
        "move_down": [pygame.K_s, pygame.K_DOWN],
        "move_left": [pygame.K_a, pygame.K_q, pygame.K_LEFT],
        "move_right": [pygame.K_d, pygame.K_RIGHT],
        "shoot": [pygame.K_SPACE],
        "weapon_1": [pygame.K_1],
        "weapon_2": [pygame.K_2],
        "weapon_3": [pygame.K_3],
    }
}

# Available resolutions
AVAILABLE_RESOLUTIONS = [
    (1024, 768),
    (1280, 720),
    (1600, 900),
    (1920, 1080),
]

SETTINGS_FILE = "settings.json"


class GameSettings:
    """Manages all game settings with save/load functionality."""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern - only one settings instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # Initialize with defaults
        self.music_volume = DEFAULT_SETTINGS["music_volume"]
        self.sfx_volume = DEFAULT_SETTINGS["sfx_volume"]
        self.resolution = tuple(DEFAULT_SETTINGS["resolution"])
        self.key_bindings = dict(DEFAULT_SETTINGS["key_bindings"])
        
        # Load saved settings if they exist
        self.load()
    
    def save(self):
        """Save settings to JSON file."""
        data = {
            "music_volume": self.music_volume,
            "sfx_volume": self.sfx_volume,
            "resolution": list(self.resolution),
            "key_bindings": self.key_bindings,
        }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def load(self):
        """Load settings from JSON file."""
        if not os.path.isfile(SETTINGS_FILE):
            return
        
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.music_volume = float(data.get("music_volume", self.music_volume))
            self.sfx_volume = float(data.get("sfx_volume", self.sfx_volume))
            
            res = data.get("resolution", list(self.resolution))
            if isinstance(res, list) and len(res) == 2:
                self.resolution = tuple(res)
            
            if "key_bindings" in data:
                self.key_bindings = data["key_bindings"]
                
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def set_music_volume(self, volume: float):
        """Set music volume (0.0 to 1.0) and apply immediately."""
        self.music_volume = max(0.0, min(1.0, volume))
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.set_volume(self.music_volume)
        except Exception:
            pass
    
    def set_sfx_volume(self, volume: float):
        """Set sound effects volume (0.0 to 1.0)."""
        self.sfx_volume = max(0.0, min(1.0, volume))
    
    def set_resolution(self, width: int, height: int):
        """Set game resolution."""
        if (width, height) in AVAILABLE_RESOLUTIONS:
            self.resolution = (width, height)
    
    def get_resolution_index(self) -> int:
        """Get current resolution index in AVAILABLE_RESOLUTIONS."""
        try:
            return AVAILABLE_RESOLUTIONS.index(self.resolution)
        except ValueError:
            return 1  # Default to 1280x720
    
    def apply_resolution(self, screen: pygame.Surface) -> pygame.Surface:
        """Apply resolution and return new screen surface."""
        try:
            new_screen = pygame.display.set_mode(self.resolution)
            return new_screen
        except Exception as e:
            print(f"Error applying resolution: {e}")
            return screen
    
    def is_key_for_action(self, key: int, action: str) -> bool:
        """Check if a key is bound to an action."""
        if action in self.key_bindings:
            return key in self.key_bindings[action]
        return False
    
    def get_key_name(self, action: str) -> str:
        """Get display name for key binding."""
        if action not in self.key_bindings:
            return "?"
        keys = self.key_bindings[action]
        if not keys:
            return "?"
        # Return first key name
        return pygame.key.name(keys[0]).upper()


# Global settings instance
game_settings = GameSettings()
