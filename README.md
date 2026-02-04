# 🧟 Zombie Shooter - Multiplayer Co-op Game

A feature-rich 2D top-down zombie survival shooter built with Python and Pygame, featuring both single-player and online multiplayer co-op modes via Hamachi.

## 🎮 Game Overview

Zombie Shooter is an action-packed survival game where players fight through 6 progressively challenging levels filled with zombies. Fight alone in single-player mode or team up with a friend in online co-op multiplayer with real-time chat!

### ✨ Key Features

#### **Game Modes**
- **Single Player**: Solo survival experience with 6 distinct levels
- **Multiplayer Co-op**: Online 2-player cooperative gameplay via Hamachi network
  - Host/Client architecture with authoritative server
  - Real-time player synchronization
  - **In-game Chat System**: Send messages with Enter key
  - Per-player kill & score tracking
  - Shared level progression
  - Spectator mode when dead (watch your teammate)
  - Respawn system when teammate is alive

#### **Combat System**
- **Triple Weapon System**:
  - **Pistol**: Unlimited ammo, moderate fire rate, accurate shots
  - **Shotgun**: Limited ammo, spread shot (5 pellets), high close-range damage
  - **Grenade**: Explosive projectile with area damage, ammo-based, screen shake on impact
- **Dynamic Zombie AI**:
  - Pathfinding and obstacle avoidance
  - Line-of-sight detection with raycasting
  - Progressive difficulty scaling per level
  - Visible level indicators (LVL1, LVL2, etc.) above zombies
  - Speed increases with each level (1.55x → 3.30x)

- **Damage System**: Accurate hit detection with per-player attribution for competitive scoring

#### **Chat System**
- Real-time messaging between players
- Press **Enter** to open chat, type message, **Enter** to send
- Visual chat history display with player names
- Chat messages synchronized over network
- Press **ESC** to close chat without sending

#### **Level System**
- **6 Unique Levels** with distinct themes and color schemes:
  1. **Desert**: Sandy brown environment
  2. **Urban**: Concrete gray cityscape
  3. **Forest**: Dark moss green vegetation
  4. **Night**: Deep blue nighttime setting
  5. **Volcano**: Burning red magma landscape
  6. **Abyss**: Final dark showdown
- **Portal Door System**: Beautifully animated portal that appears when level objective is completed
- **Progressive Difficulty**: Each level introduces faster, stronger zombies

#### **Visual Effects & Polish**
- **Enhanced Game Over Screen**:
  - Animated blood particles
  - Falling skull effects
  - Glowing interactive buttons
  - Screen shake on death
  - Different messages for solo vs co-op play
- Door Effects:
  - Active: Glowing blue portal with particles
  - Inactive: Detailed wooden door
- Camera System:
  - Smooth camera following
  - Screen shake effects (weapons, explosions)
  - Spectator camera in multiplayer
- HUD Elements:
  - Health hearts display
  - Kill counter (total + per-player in multiplayer)
  - Score tracking (per-player attribution)
  - Ammo counters (Shotgun + Grenade)
  - Multiplayer status (Host/Client indicator)
  - Player connection indicators

#### **Power-ups & Items**
- **Medkit**: Restore 50 HP (health capped at 100)
- **Shotgun Ammo**: Replenish shotgun ammunition (+15 shells)
- **Grenade Ammo**: Add grenade ammunition (+3 grenades)
- **Speed Crates**: Temporary 50% movement speed boost for 5 seconds
- Random spawn system with crate destruction mechanics

#### **Network Features**
- **Hamachi Integration**:
  - Automatic Hamachi IP detection
  - Connection status indicators
  - Helpful setup instructions
- **Robust Networking**:
  - Thread-safe message queuing
  - Proper data framing (4-byte headers)
  - 8KB buffer size for smooth data transfer
  - Automatic disconnection handling

## 📋 Requirements

### System Requirements
- **OS**: Windows (primary), Linux/Mac (untested but should work)
- **Python**: 3.7+
- **Network**: Hamachi (for multiplayer)

### Python Dependencies
```
pygame==2.6.1
```

## 🚀 Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Verify Assets
Ensure the following directories exist with assets:
- `images/` - Player sprites, zombie sprites, items, backgrounds
- `sounds/` - Sound effects and background music

### 3. (Multiplayer Only) Install Hamachi
1. Download and install [LogMeIn Hamachi](https://www.vpn.net/)
2. Create or join a Hamachi network
3. Both players must be in the same Hamachi network (green dots in Hamachi)

## 🎯 How to Play

### Starting the Game
```bash
python main.py
```

### Single Player Controls
- **Movement**: WASD or Arrow keys
- **Shoot Pistol**: Left Click or Spacebar
- **Shoot Shotgun**: Right Click
- **Throw Grenade**: G key
- **Toggle HUD**: H key
- **Pause/Menu**: ESC

### Multiplayer Controls
Same as single-player, plus:
- **Open/Close Chat**: Enter key
- **Switch Spectate Target** (when dead): TAB
- **Respawn** (when available): R key

### Multiplayer Setup
1. **Host** (Player 1):
   - Click "Multiplayer"
   - Click "Host Game"
   - Share your Hamachi IP with Player 2
   - Wait for Player 2 to connect
   - Press SPACE to start game

2. **Client** (Player 2):
   - Click "Multiplayer"
   - Enter Host's Hamachi IP
   - Click "Join Game"
   - Wait for Host to start

## 🏗️ Project Structure

```
python_learnfullversion/
├── main.py                 # Entry point, menu system, Hamachi integration
├── game.py                 # Single-player game logic, camera, scenes
├── multiplayer_game.py     # Multiplayer co-op logic, state sync, game loop
├── network.py              # NetworkManager: threading, sockets, serialization
├── multiplayer_setup.py    # Multiplayer lobby and setup screens
├── chat.py                 # ChatSystem: messages, input, rendering, network
├── weapons.py              # WeaponManager: pistol, shotgun, grenade logic
├── characters.py           # Player and Enemy classes with AI
├── bullet.py               # Bullet physics, collision, rendering
├── walls.py                # Wall generation and collision detection
├── util.py                 # Utility functions (draw, load, buttons)
├── requirements.txt        # Python dependencies
├── images/                 # All game sprites and backgrounds
│   ├── player_*.png        # Player sprites (4 directions, 2 skins)
│   ├── zombie_*.png        # Zombie sprites (4 directions)
│   ├── chest_*.png         # Crate sprites
│   ├── door_*.png          # Door/portal sprites
│   └── *.jpg               # Background images
└── sounds/                 # Sound effects and music
    ├── background_music.wav
    ├── shotgun-146188.mp3
    ├── explosion.wav
    ├── zombie_*.wav
    └── *.wav               # Various sound effects
```

## 🎨 Technical Highlights

### Game Architecture
- **Modular Design**: Separate modules for game logic, networking, rendering
- **Component-Based**: Entities like Zombie, Bullet, Crate use shared interfaces
- **Event-Driven**: Pygame event loop with fixed timestep (60 FPS)

### Multiplayer Implementation
- **Client-Server Model**: One player hosts, other joins
- **State Synchronization**:
  - Player positions and actions
  - Enemy states (position, health, level)
  - Item pickups and crate states
  - Door activation status
- **Latency Handling**:
  - Lerp interpolation for smooth enemy movement
  - Client prediction for local player
  - 100ms update interval

### Performance Optimizations
- **Efficient Rendering**:
  - Simplified door graphics (reduced from ~100 draw calls to ~10)
  - Cached font surfaces
  - Sprite batching where possible
- **Smart Collision Detection**:
  - Raycast optimization for zombie line-of-sight
  - Spatial partitioning for large game worlds (3200x2400)
- **Memory Management**:
  - Bullet cleanup when off-screen or expired
  - Zombie removal on death
  - Resource pooling for particles

## 🐛 Known Issues & Solutions

### Multiplayer
- **Issue**: Connection fails
  - **Solution**: Ensure both players have green dots in Hamachi, check firewall settings
  
- **Issue**: Lag or desync
  - **Solution**: Verify network connection, both players should have stable ping in Hamachi

### Performance
- **Issue**: Low FPS
  - **Solution**: Game has been optimized for 60 FPS; ensure your system meets requirements

## 🎓 Development Notes

### Recent Improvements
1. **Per-Player Score Tracking**: Accurate kill attribution with `owner_id` system
2. **Grenade Weapon**: Added explosive weapon with area damage and visual effects
3. **Chat System**: Full in-game messaging with network synchronization
4. **Game State Optimization**: Throttled updates to eliminate host FPS drops
5. **Weapon System Refactor**: Centralized in `weapons.py` with clean OOP design
6. **Explosion Effects**: Screen shake, particle effects, area damage

### Code Quality
- **Documentation**: Extensive inline documentation in Arabic and English
- **Error Handling**: Try-catch blocks for asset loading and network operations
- **Debug Logging**: Conditional console output controlled by flags
- **Type Hints**: Used throughout for IDE support and clarity
- **Consistent Naming**: snake_case for functions/variables, PascalCase for classes

## 🤝 Credits

### Assets Used
- **Sprites**: Player and zombie character sprites
- **Sounds**: Various zombie, weapon, and ambient sounds
- **Backgrounds**: Post-apocalyptic themed images

### Libraries
- **Pygame 2.6.1**: Core game framework
- **Python Standard Library**: socket, threading, pickle, queue



### 🎮 Enjoy the game and survive the zombie apocalypse! 🧟‍♂️

**Tips for Success:**
- **Keep moving** to avoid getting surrounded by zombies
- **Save shotgun ammo** for tight situations and groups
- **Use grenades** for crowd control and high-level zombies
- **Collect medkits** before engaging large zombie groups
- **In multiplayer**: Communication is key! Use chat (Enter) to coordinate
- **Watch your teammate's back** in co-op mode

---

*Last Updated: 2026 | Version with Grenades, Chat & Per-Player Scoring*
