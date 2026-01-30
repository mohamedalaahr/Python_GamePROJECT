# weapons.py - Advanced Weapons System for Zombie Shooter
"""
نظام الأسلحة المتقدم:
- Pistol: سلاح افتراضي، ذخيرة لا نهائية
- Shotgun: 5 رصاصات متفرقة، ضرر عالي
- Grenade: قنبلة انفجارية، ضرر منطقة
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple
import math
import random
import pygame

# ============== Weapon Types ==============
class WeaponType(Enum):
    PISTOL = 1
    SHOTGUN = 2
    GRENADE = 3

# ============== Weapon Data ==============
WEAPON_STATS = {
    WeaponType.PISTOL: {
        "name": "Pistol",
        "name_ar": "مسدس",
        "damage": 1,
        "fire_rate": 0.25,      # ثواني بين الطلقات
        "ammo": -1,             # -1 = ذخيرة لا نهائية
        "max_ammo": -1,
        "spread": 0.0,          # لا انتشار
        "bullet_speed": 500,
        "bullet_count": 1,
        "bullet_color": (255, 220, 50),
        "sound": "pistol_shot.wav",
    },
    WeaponType.SHOTGUN: {
        "name": "Shotgun",
        "name_ar": "شوتجن",
        "damage": 2,
        "fire_rate": 0.7,
        "ammo": 30,
        "max_ammo": 30,
        "spread": 0.35,         # زاوية الانتشار (راديان)
        "bullet_speed": 400,
        "bullet_count": 5,      # 5 رصاصات في الطلقة الواحدة
        "bullet_color": (255, 100, 50),
        "sound": "shotgun_shot.wav",
    },
    WeaponType.GRENADE: {
        "name": "Grenade",
        "name_ar": "قنبلة",
        "damage": 8,
        "fire_rate": 1.5,
        "ammo": 5,
        "max_ammo": 5,
        "spread": 0.0,
        "bullet_speed": 250,
        "bullet_count": 1,
        "bullet_color": (100, 200, 100),
        "explosion_radius": 120,
        "fuse_time": 1.2,       # وقت الانفجار
        "sound": "grenade_throw.wav",
    },
}

# ============== Weapon Bullet Class ==============
@dataclass
class WeaponBullet:
    """رصاصة متقدمة مع دعم أنواع مختلفة"""
    x: float
    y: float
    vx: float
    vy: float
    weapon_type: WeaponType
    speed: float = 500.0
    lifetime: float = 1.5
    alive: bool = True
    damage: int = 1
    radius: int = 5
    color: Tuple[int, int, int] = (255, 220, 50)
    owner_id: int = 0
    
    # للقنابل فقط
    is_grenade: bool = False
    fuse_time: float = 0.0
    explosion_radius: int = 0
    exploded: bool = False
    
    def update(self, dt: float) -> bool:
        """تحديث الرصاصة، يرجع True إذا انفجرت قنبلة"""
        if not self.alive:
            return False
            
        if self.is_grenade:
            self.fuse_time -= dt
            if self.fuse_time <= 0:
                self.alive = False
                self.exploded = True
                return True  # انفجرت!
            # القنبلة تتباطأ
            self.speed *= 0.98
        
        self.x += self.vx * self.speed * dt
        self.y += self.vy * self.speed * dt
        self.lifetime -= dt
        
        if self.lifetime <= 0:
            self.alive = False
            
        return False
    
    def rect(self) -> pygame.Rect:
        r = self.radius
        return pygame.Rect(int(self.x - r), int(self.y - r), 2*r, 2*r)
    
    def draw(self, screen: pygame.Surface, cam_offset: Tuple[int, int] = (0, 0)):
        if not self.alive:
            return
            
        draw_x = int(self.x - cam_offset[0])
        draw_y = int(self.y - cam_offset[1])
        
        if self.is_grenade:
            # 🔥 رسم قنبلة احترافية
            # جسم القنبلة المعدني
            grenade_body_color = (60, 70, 60)  # أخضر داكن معدني
            grenade_highlight = (90, 105, 85)  # لمعان
            grenade_shadow = (35, 45, 35)  # ظل
            
            # الجسم الرئيسي (شكل بيضاوي)
            body_w = self.radius * 2 + 4
            body_h = self.radius * 2 + 8
            body_rect = pygame.Rect(draw_x - body_w//2, draw_y - body_h//2, body_w, body_h)
            
            # ظل القنبلة
            shadow_rect = body_rect.move(3, 3)
            pygame.draw.ellipse(screen, (20, 20, 20, 100), shadow_rect)
            
            # جسم القنبلة
            pygame.draw.ellipse(screen, grenade_body_color, body_rect)
            # لمعان على الجانب
            highlight_rect = pygame.Rect(draw_x - body_w//4, draw_y - body_h//2 + 2, body_w//3, body_h - 4)
            pygame.draw.ellipse(screen, grenade_highlight, highlight_rect)
            
            # الحلقة العلوية (مقبض)
            pygame.draw.rect(screen, (80, 80, 80), (draw_x - 4, draw_y - body_h//2 - 6, 8, 8))
            pygame.draw.rect(screen, (100, 100, 100), (draw_x - 3, draw_y - body_h//2 - 5, 6, 6))
            
            # الرافعة (lever)
            lever_color = (140, 140, 130)
            pygame.draw.rect(screen, lever_color, (draw_x + 2, draw_y - body_h//2 - 4, 3, body_h//2 + 4))
            
            # خطوط التفاصيل على الجسم
            for i in range(3):
                line_y = draw_y - body_h//4 + i * 6
                pygame.draw.line(screen, grenade_shadow, (draw_x - body_w//3, line_y), (draw_x + body_w//3, line_y), 1)
            
            # 🔥 مؤشر الفتيل المتوهج
            fuse_ratio = max(0, self.fuse_time / 1.2)
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.015)) * 0.5 + 0.5
            
            # توهج حول القنبلة قبل الانفجار
            if fuse_ratio < 0.5:
                glow_intensity = int((1 - fuse_ratio * 2) * 150 * pulse)
                glow_size = int(self.radius * 2 * (1 + (1 - fuse_ratio) * 0.5))
                glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (255, 100, 0, glow_intensity), (glow_size, glow_size), glow_size)
                screen.blit(glow_surf, (draw_x - glow_size, draw_y - glow_size))
            
            # ضوء الفتيل العلوي
            fuse_glow = int(255 * pulse * (1 - fuse_ratio * 0.7))
            fuse_color_inner = (255, min(255, 100 + fuse_glow), 0)
            fuse_color_outer = (255, 50, 0)
            pygame.draw.circle(screen, fuse_color_outer, (draw_x, draw_y - body_h//2 - 2), 5)
            pygame.draw.circle(screen, fuse_color_inner, (draw_x, draw_y - body_h//2 - 2), 3)
            
            # شرارات صغيرة
            if fuse_ratio < 0.7:
                for _ in range(2):
                    spark_x = draw_x + random.randint(-6, 6)
                    spark_y = draw_y - body_h//2 - 2 + random.randint(-4, 4)
                    pygame.draw.circle(screen, (255, 255, 150), (spark_x, spark_y), 1)
        else:
            # رصاصة عادية مع ذيل
            pygame.draw.circle(screen, self.color, (draw_x, draw_y), self.radius)
            # ذيل الرصاصة
            tail_x = draw_x - int(self.vx * 8)
            tail_y = draw_y - int(self.vy * 8)
            pygame.draw.line(screen, self.color, (draw_x, draw_y), (tail_x, tail_y), 2)

# ============== Explosion Effect ==============
class ExplosionEffect:
    """تأثير انفجار احترافي متعدد الطبقات"""
    def __init__(self, x: float, y: float, radius: int):
        self.x = x
        self.y = y
        self.max_radius = radius
        self.current_radius = 0
        self.alpha = 255
        self.alive = True
        self.time = 0.0
        self.duration = 0.8  # مدة الانفجار
        
        # جزيئات متعددة الأنواع
        self.fire_particles: List[dict] = []
        self.smoke_particles: List[dict] = []
        self.spark_particles: List[dict] = []
        self.shockwave_rings: List[dict] = []
        self.debris_particles: List[dict] = []
        
        self._create_all_particles()
        
    def _create_all_particles(self):
        """إنشاء جميع أنواع الجزيئات"""
        # 🔥 جزيئات النار (اللب الحار)
        for _ in range(45):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(150, 400)
            self.fire_particles.append({
                'x': self.x,
                'y': self.y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'size': random.randint(6, 14),
                'color_phase': random.uniform(0, 1),  # لاختيار لون من التدرج
                'life': random.uniform(0.2, 0.5),
                'max_life': random.uniform(0.2, 0.5),
            })
        
        # 💨 جزيئات الدخان (تصعد للأعلى)
        for _ in range(25):
            angle = random.uniform(-math.pi * 0.8, -math.pi * 0.2)  # في الغالب للأعلى
            speed = random.uniform(40, 120)
            self.smoke_particles.append({
                'x': self.x + random.uniform(-20, 20),
                'y': self.y + random.uniform(-10, 10),
                'vx': math.cos(angle) * speed * 0.3,
                'vy': -abs(math.sin(angle) * speed),  # دائماً للأعلى
                'size': random.randint(15, 35),
                'alpha': 180,
                'life': random.uniform(0.6, 1.2),
                'max_life': random.uniform(0.6, 1.2),
                'gray': random.randint(40, 80),
            })
        
        # ✨ الشرارات المتطايرة
        for _ in range(60):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(200, 600)
            self.spark_particles.append({
                'x': self.x,
                'y': self.y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed - random.uniform(50, 150),  # جاذبية خفيفة
                'life': random.uniform(0.1, 0.4),
                'color': random.choice([(255, 255, 200), (255, 200, 100), (255, 150, 50)]),
            })
        
        # 🔴 حلقات الصدمة (Shockwave)
        for i in range(3):
            self.shockwave_rings.append({
                'radius': 0,
                'max_radius': self.max_radius * (1.2 + i * 0.4),
                'alpha': 200 - i * 50,
                'thickness': 4 - i,
                'delay': i * 0.08,
                'started': False,
            })
        
        # 🧱 الحطام المتطاير
        for _ in range(15):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(100, 300)
            self.debris_particles.append({
                'x': self.x,
                'y': self.y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'gravity': random.uniform(300, 500),
                'size': random.randint(2, 5),
                'life': random.uniform(0.4, 0.8),
                'color': random.choice([(80, 60, 40), (60, 50, 35), (100, 80, 50)]),
            })
    
    def update(self, dt: float):
        if not self.alive:
            return
        
        self.time += dt
        
        # توسيع الانفجار الرئيسي
        if self.current_radius < self.max_radius:
            self.current_radius += dt * self.max_radius * 6  # أسرع
        
        # تلاشي تدريجي
        progress = self.time / self.duration
        self.alpha = int(255 * (1 - progress * progress))  # تلاشي تربيعي
        
        if self.time >= self.duration:
            self.alive = False
            
        # تحديث جزيئات النار
        for p in self.fire_particles:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['vx'] *= 0.92
            p['vy'] *= 0.92
            p['life'] -= dt
            p['size'] = max(1, int(p['size'] * 0.95))
        
        # تحديث الدخان (يصعد للأعلى)
        for p in self.smoke_particles:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['vy'] -= 30 * dt  # صعود تدريجي
            p['vx'] *= 0.98
            p['life'] -= dt
            p['size'] = int(p['size'] * 1.02)  # يتوسع الدخان
            p['alpha'] = max(0, p['alpha'] - dt * 150)
        
        # تحديث الشرارات
        for p in self.spark_particles:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['vy'] += 400 * dt  # جاذبية
            p['vx'] *= 0.98
            p['life'] -= dt
        
        # تحديث حلقات الصدمة
        for ring in self.shockwave_rings:
            if self.time >= ring['delay']:
                ring['started'] = True
            if ring['started'] and ring['radius'] < ring['max_radius']:
                ring['radius'] += dt * ring['max_radius'] * 5
                ring['alpha'] = max(0, ring['alpha'] - dt * 400)
        
        # تحديث الحطام
        for p in self.debris_particles:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['vy'] += p['gravity'] * dt  # جاذبية
            p['vx'] *= 0.99
            p['life'] -= dt
            
    def draw(self, screen: pygame.Surface, cam_offset: Tuple[int, int] = (0, 0)):
        if not self.alive:
            return
            
        draw_x = int(self.x - cam_offset[0])
        draw_y = int(self.y - cam_offset[1])
        
        # 1️⃣ رسم حلقات الصدمة أولاً (في الخلفية)
        for ring in self.shockwave_rings:
            if ring['started'] and ring['radius'] > 0 and ring['alpha'] > 0:
                ring_radius = max(1, int(ring['radius']))
                surf_size = max(10, ring_radius * 2 + 10)
                ring_surf = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
                center = surf_size // 2
                safe_radius = min(ring_radius, center - 2)
                if safe_radius > 0:
                    pygame.draw.circle(ring_surf, (255, 200, 100, int(ring['alpha'])), 
                                     (center, center), safe_radius, max(1, int(ring['thickness'])))
                    screen.blit(ring_surf, (draw_x - center, draw_y - center))
        
        # 2️⃣ رسم الانفجار الرئيسي (كرات نار متعددة الطبقات)
        if self.current_radius > 0 and self.alpha > 10:
            # حجم السطح
            surf_size = max(10, int(self.current_radius * 2.5))
            explosion_surf = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
            center = surf_size // 2
            
            # طبقة خارجية - برتقالي داكن
            outer_alpha = int(self.alpha * 0.4)
            outer_radius = min(center - 1, max(1, int(self.current_radius * 1.1)))
            pygame.draw.circle(explosion_surf, (200, 60, 0, outer_alpha), 
                             (center, center), outer_radius)
            
            # طبقة وسطى - برتقالي
            mid_alpha = int(self.alpha * 0.6)
            mid_radius = min(center - 1, max(1, int(self.current_radius * 0.8)))
            pygame.draw.circle(explosion_surf, (255, 120, 20, mid_alpha), 
                             (center, center), mid_radius)
            
            # طبقة داخلية - أصفر
            inner_alpha = int(self.alpha * 0.8)
            inner_radius = min(center - 1, max(1, int(self.current_radius * 0.5)))
            pygame.draw.circle(explosion_surf, (255, 200, 50, inner_alpha), 
                             (center, center), inner_radius)
            
            # اللب - أبيض ساخن
            core_alpha = int(self.alpha * 0.9)
            core_radius = min(center - 1, max(1, int(self.current_radius * 0.25)))
            pygame.draw.circle(explosion_surf, (255, 255, 200, core_alpha), 
                             (center, center), core_radius)
            
            screen.blit(explosion_surf, (draw_x - center, draw_y - center))
        
        # 3️⃣ رسم جزيئات النار
        for p in self.fire_particles:
            if p['life'] > 0 and p['size'] > 0:
                px = int(p['x'] - cam_offset[0])
                py = int(p['y'] - cam_offset[1])
                life_ratio = max(0.0, min(1.0, p['life'] / max(0.001, p['max_life'])))
                
                # تدرج من الأبيض للأصفر للبرتقالي للأحمر
                phase = p['color_phase']
                if life_ratio > 0.7:
                    color = (255, 255, int(200 * phase))
                elif life_ratio > 0.4:
                    color = (255, int(150 + 100 * phase), 0)
                else:
                    color = (int(200 + 55 * phase), int(50 * phase), 0)
                
                alpha = min(255, max(0, int(255 * life_ratio)))
                size = max(1, int(p['size']))
                
                if size > 0 and alpha > 0:
                    particle_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                    pygame.draw.circle(particle_surf, (*color, alpha), (size, size), size)
                    screen.blit(particle_surf, (px - size, py - size))
        
        # 4️⃣ رسم الشرارات
        for p in self.spark_particles:
            if p['life'] > 0:
                px = int(p['x'] - cam_offset[0])
                py = int(p['y'] - cam_offset[1])
                # نقطة صغيرة بدلاً من خط لتجنب مشاكل السطح
                alpha = min(255, int(255 * (p['life'] / 0.4)))
                if alpha > 0:
                    spark_size = max(2, int(3 * (p['life'] / 0.4)))
                    spark_surf = pygame.Surface((spark_size * 2, spark_size * 2), pygame.SRCALPHA)
                    color = (*p['color'][:3], alpha)
                    pygame.draw.circle(spark_surf, color, (spark_size, spark_size), spark_size)
                    screen.blit(spark_surf, (px - spark_size, py - spark_size))

        
        # 5️⃣ رسم الحطام
        for p in self.debris_particles:
            if p['life'] > 0:
                px = int(p['x'] - cam_offset[0])
                py = int(p['y'] - cam_offset[1])
                alpha = int(255 * (p['life'] / 0.8))
                color = (*p['color'], alpha)
                size = p['size']
                debris_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.rect(debris_surf, color, (0, 0, size * 2, size * 2))
                screen.blit(debris_surf, (px - size, py - size))
        
        # 6️⃣ رسم الدخان (في المقدمة)
        for p in self.smoke_particles:
            if p['life'] > 0 and p['alpha'] > 5 and p['size'] > 0:
                px = int(p['x'] - cam_offset[0])
                py = int(p['y'] - cam_offset[1])
                gray = max(0, min(255, int(p['gray'])))
                alpha = max(0, min(255, int(p['alpha'])))
                size = max(1, int(p['size']))
                
                if size > 0 and alpha > 0:
                    smoke_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                    pygame.draw.circle(smoke_surf, (gray, gray, gray, alpha), (size, size), size)
                    screen.blit(smoke_surf, (px - size, py - size))

# ============== Weapon Manager ==============
class WeaponManager:
    """مدير الأسلحة الرئيسي"""
    def __init__(self, player_id: int = 0):
        self.player_id = player_id
        self.current_weapon = WeaponType.PISTOL
        self.ammo = {
            WeaponType.PISTOL: -1,   # لا نهائي
            WeaponType.SHOTGUN: 30,
            WeaponType.GRENADE: 5,
        }
        self.cooldowns = {
            WeaponType.PISTOL: 0.0,
            WeaponType.SHOTGUN: 0.0,
            WeaponType.GRENADE: 0.0,
        }
        self.bullets: List[WeaponBullet] = []
        self.explosions: List[ExplosionEffect] = []
        
    def switch_weapon(self, weapon_type: WeaponType) -> bool:
        """تبديل السلاح"""
        if weapon_type in WeaponType:
            self.current_weapon = weapon_type
            return True
        return False
    
    def switch_by_key(self, key: int) -> bool:
        """تبديل السلاح بالمفتاح (1, 2, 3)"""
        key_map = {
            pygame.K_1: WeaponType.PISTOL,
            pygame.K_2: WeaponType.SHOTGUN,
            pygame.K_3: WeaponType.GRENADE,
        }
        if key in key_map:
            return self.switch_weapon(key_map[key])
        return False
    
    def can_fire(self) -> bool:
        """هل يمكن إطلاق النار الآن؟"""
        weapon = self.current_weapon
        stats = WEAPON_STATS[weapon]
        
        # تحقق من وقت الانتظار
        if self.cooldowns[weapon] > 0:
            return False
            
        # تحقق من الذخيرة
        if stats["ammo"] != -1 and self.ammo[weapon] <= 0:
            return False
            
        return True
    
    def fire(self, start_x: float, start_y: float, target_x: float, target_y: float) -> List[WeaponBullet]:
        """إطلاق النار، يرجع قائمة الرصاصات الجديدة"""
        if not self.can_fire():
            return []
            
        weapon = self.current_weapon
        stats = WEAPON_STATS[weapon]
        
        # حساب الاتجاه
        dx = target_x - start_x
        dy = target_y - start_y
        distance = math.hypot(dx, dy) or 1.0
        base_vx = dx / distance
        base_vy = dy / distance
        
        new_bullets = []
        
        # إنشاء الرصاصات
        for i in range(stats["bullet_count"]):
            # إضافة الانتشار
            spread = stats["spread"]
            if spread > 0 and stats["bullet_count"] > 1:
                # توزيع متساوي للشوتجن
                angle_offset = spread * (i - (stats["bullet_count"] - 1) / 2) / (stats["bullet_count"] - 1)
            else:
                angle_offset = random.uniform(-spread/4, spread/4) if spread > 0 else 0
            
            # تطبيق الانتشار
            cos_a = math.cos(angle_offset)
            sin_a = math.sin(angle_offset)
            vx = base_vx * cos_a - base_vy * sin_a
            vy = base_vx * sin_a + base_vy * cos_a
            
            bullet = WeaponBullet(
                x=start_x,
                y=start_y,
                vx=vx,
                vy=vy,
                weapon_type=weapon,
                speed=stats["bullet_speed"],
                damage=stats["damage"],
                color=stats["bullet_color"],
                owner_id=self.player_id,
                is_grenade=(weapon == WeaponType.GRENADE),
                fuse_time=stats.get("fuse_time", 0),
                explosion_radius=stats.get("explosion_radius", 0),
            )
            
            if weapon == WeaponType.GRENADE:
                bullet.radius = 10
                bullet.lifetime = 3.0
            elif weapon == WeaponType.SHOTGUN:
                bullet.radius = 4
                bullet.lifetime = 0.8
            else:
                bullet.radius = 5
                bullet.lifetime = 1.2
                
            new_bullets.append(bullet)
        
        # تحديث الذخيرة والانتظار
        if stats["ammo"] != -1:
            self.ammo[weapon] -= 1
        self.cooldowns[weapon] = stats["fire_rate"]
        
        self.bullets.extend(new_bullets)
        return new_bullets
    
    def add_ammo(self, weapon_type: WeaponType, amount: int):
        """إضافة ذخيرة"""
        if weapon_type in self.ammo and WEAPON_STATS[weapon_type]["max_ammo"] != -1:
            max_ammo = WEAPON_STATS[weapon_type]["max_ammo"]
            self.ammo[weapon_type] = min(max_ammo, self.ammo[weapon_type] + amount)
    
    def update(self, dt: float) -> List[Tuple[float, float, int, int]]:
        """
        تحديث جميع الرصاصات والانفجارات
        يرجع قائمة الانفجارات الجديدة: [(x, y, radius, damage), ...]
        """
        explosions_data = []
        
        # تحديث فترات الانتظار
        for weapon in self.cooldowns:
            if self.cooldowns[weapon] > 0:
                self.cooldowns[weapon] -= dt
        
        # تحديث الرصاصات
        for bullet in self.bullets[:]:
            exploded = bullet.update(dt)
            if exploded:
                # قنبلة انفجرت!
                self.explosions.append(ExplosionEffect(
                    bullet.x, bullet.y, bullet.explosion_radius
                ))
                explosions_data.append((
                    bullet.x, bullet.y, 
                    bullet.explosion_radius, 
                    bullet.damage
                ))
            if not bullet.alive:
                self.bullets.remove(bullet)
        
        # تحديث تأثيرات الانفجار
        for exp in self.explosions[:]:
            exp.update(dt)
            if not exp.alive:
                self.explosions.remove(exp)
        
        return explosions_data
    
    def draw_bullets(self, screen: pygame.Surface, cam_offset: Tuple[int, int] = (0, 0)):
        """رسم جميع الرصاصات"""
        for bullet in self.bullets:
            bullet.draw(screen, cam_offset)
    
    def draw_explosions(self, screen: pygame.Surface, cam_offset: Tuple[int, int] = (0, 0)):
        """رسم تأثيرات الانفجار"""
        for exp in self.explosions:
            exp.draw(screen, cam_offset)
    
    def draw_hud(self, screen: pygame.Surface, x: int, y: int):
        """رسم واجهة السلاح"""
        stats = WEAPON_STATS[self.current_weapon]
        
        # خلفية
        hud_rect = pygame.Rect(x, y, 200, 60)
        pygame.draw.rect(screen, (0, 0, 0, 180), hud_rect, border_radius=8)
        pygame.draw.rect(screen, (100, 100, 100), hud_rect, width=2, border_radius=8)
        
        # اسم السلاح
        font = pygame.font.Font(None, 28)
        name_surf = font.render(stats["name"], True, (255, 255, 255))
        screen.blit(name_surf, (x + 10, y + 8))
        
        # الذخيرة
        ammo_font = pygame.font.Font(None, 24)
        if stats["ammo"] == -1:
            ammo_text = "∞"
        else:
            ammo_text = f"{self.ammo[self.current_weapon]} / {stats['max_ammo']}"
        ammo_surf = ammo_font.render(ammo_text, True, (200, 200, 100))
        screen.blit(ammo_surf, (x + 10, y + 35))
        
        # مؤشر السلاح الحالي (1, 2, 3)
        keys = {WeaponType.PISTOL: "1", WeaponType.SHOTGUN: "2", WeaponType.GRENADE: "3"}
        for i, (wtype, key) in enumerate(keys.items()):
            indicator_x = x + 130 + i * 25
            indicator_y = y + 10
            color = (255, 200, 50) if wtype == self.current_weapon else (100, 100, 100)
            pygame.draw.rect(screen, color, (indicator_x, indicator_y, 20, 20), border_radius=4)
            key_surf = ammo_font.render(key, True, (0, 0, 0))
            screen.blit(key_surf, (indicator_x + 5, indicator_y + 2))
    
    def to_dict(self) -> dict:
        """تحويل لإرسال عبر الشبكة"""
        return {
            "current_weapon": self.current_weapon.value,
            "ammo": {k.value: v for k, v in self.ammo.items()},
            "bullets": [
                {
                    "x": b.x, "y": b.y, "vx": b.vx, "vy": b.vy,
                    "weapon_type": b.weapon_type.value,
                    "damage": b.damage, "is_grenade": b.is_grenade,
                    "fuse_time": b.fuse_time, "explosion_radius": b.explosion_radius,
                }
                for b in self.bullets
            ]
        }
    
    @staticmethod
    def from_dict(data: dict, player_id: int = 0) -> "WeaponManager":
        """إنشاء من بيانات الشبكة"""
        wm = WeaponManager(player_id)
        wm.current_weapon = WeaponType(data.get("current_weapon", 1))
        for k, v in data.get("ammo", {}).items():
            wm.ammo[WeaponType(int(k))] = v
        return wm


# ============== Ammo Pickup ==============
@dataclass
class AmmoPickup:
    """التقاط الذخيرة"""
    x: float
    y: float
    weapon_type: WeaponType
    amount: int
    alive: bool = True
    pickup_id: int = 0
    
    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), 32, 32)
    
    def draw(self, screen: pygame.Surface, cam_offset: Tuple[int, int] = (0, 0)):
        if not self.alive:
            return
            
        draw_x = int(self.x - cam_offset[0])
        draw_y = int(self.y - cam_offset[1])
        
        # حركة طفو بسيطة
        t = pygame.time.get_ticks() / 1000.0
        float_offset = math.sin(t * 3) * 3
        draw_y += float_offset
        
        # إعدادات الألوان والأيقونات حسب النوع
        if self.weapon_type == WeaponType.SHOTGUN:
            main_color = (180, 40, 40)      # أحمر للخرطوش
            light_color = (220, 60, 60)
            dark_color = (120, 30, 30)
            icon_color = (255, 200, 50)     # ذهبي
            label = "SHELLS"
        elif self.weapon_type == WeaponType.GRENADE:
            main_color = (50, 80, 50)       # أخضر عسكري
            light_color = (70, 100, 70)
            dark_color = (30, 50, 30)
            icon_color = (200, 200, 200)    # فضي
            label = "NADES"
        else:
            main_color = (100, 100, 100)
            light_color = (130, 130, 130)
            dark_color = (60, 60, 60)
            icon_color = (255, 255, 255)
            label = "AMMO"

        # رسم صندوق 3D
        w, h = 36, 28
        
        # الظل على الأرض
        shadow_width = w + int(math.sin(t*3)*2)
        pygame.draw.ellipse(screen, (0, 0, 0, 80), 
                          (draw_x + (32-shadow_width)//2, draw_y + h + 5 - float_offset, shadow_width, 10))

        # الوجه الخلفي (للعمق)
        pygame.draw.rect(screen, dark_color, (draw_x + 4, draw_y - 4, w, h), border_radius=4)
        
        # الوجه الأمامي
        rect = pygame.Rect(draw_x, draw_y, w, h)
        pygame.draw.rect(screen, main_color, rect, border_radius=4)
        
        # تفاصيل الإطار (Highlight)
        pygame.draw.rect(screen, light_color, rect, width=2, border_radius=4)
        
        # زوايا معدنية
        corner_len = 8
        corner_color = (180, 180, 180)
        # أعلى يسار
        pygame.draw.line(screen, corner_color, (draw_x, draw_y), (draw_x + corner_len, draw_y), 2)
        pygame.draw.line(screen, corner_color, (draw_x, draw_y), (draw_x, draw_y + corner_len), 2)
        # أسفل يمين
        pygame.draw.line(screen, corner_color, (draw_x + w, draw_y + h), (draw_x + w - corner_len, draw_y + h), 2)
        pygame.draw.line(screen, corner_color, (draw_x + w, draw_y + h), (draw_x + w, draw_y + h - corner_len), 2)
        
        # الرمز/الأيقونة في المنتصف
        font = pygame.font.SysFont("arial", 10, bold=True)
        text_surf = font.render(label, True, icon_color)
        text_rect = text_surf.get_rect(center=rect.center)
        
        # خلفية سوداء صغيرة للنص
        bg_text_rect = text_rect.inflate(4, 2)
        pygame.draw.rect(screen, (0, 0, 0, 100), bg_text_rect, border_radius=2)
        screen.blit(text_surf, text_rect)
        
        # رسم ذخيرة صغيرة فوق الصندوق كتوضيح
        if self.weapon_type == WeaponType.SHOTGUN:
            # رسم خرطوشتين
            for i in range(2):
                sx = draw_x + 10 + i * 12
                sy = draw_y - 6
                pygame.draw.rect(screen, (200, 50, 50), (sx, sy, 8, 12)) # جسم احمر
                pygame.draw.rect(screen, (255, 215, 0), (sx, sy + 8, 8, 4)) # قاعدة ذهبية
        elif self.weapon_type == WeaponType.GRENADE:
            # رسم قنبلة صغيرة
            pygame.draw.circle(screen, (40, 60, 40), (draw_x + w//2, draw_y - 4), 6)
            pygame.draw.line(screen, (200, 200, 200), (draw_x + w//2, draw_y - 8), (draw_x + w//2 + 3, draw_y - 12), 2)
    
    def to_dict(self) -> dict:
        return {
            "id": self.pickup_id,
            "x": self.x, "y": self.y,
            "weapon_type": self.weapon_type.value,
            "amount": self.amount,
            "alive": self.alive,
        }
    
    @staticmethod
    def from_dict(data: dict) -> "AmmoPickup":
        pickup = AmmoPickup(
            x=data["x"],
            y=data["y"],
            weapon_type=WeaponType(data["weapon_type"]),
            amount=data["amount"],
            pickup_id=data.get("id", 0),
        )
        pickup.alive = data.get("alive", True)
        return pickup
