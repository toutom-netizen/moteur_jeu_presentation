"""Module de gestion des effets de particules."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple

import pygame

from .particle import Particle


@dataclass
class ParticleEffectConfig:
    """Configuration pour créer un effet de particules."""
    count: int  # Nombre de particules à créer
    speed: float  # Vitesse de base des particules (pixels/seconde)
    lifetime: float  # Durée de vie des particules (secondes)
    size: int  # Taille de base des particules (diamètre en pixels)
    color: Tuple[int, int, int]  # Couleur de base des particules (RGB)
    speed_variation: float = 0.3  # Variation de vitesse (0.0 à 1.0, ex: 0.3 = ±30%)
    lifetime_variation: float = 0.0  # Variation de durée de vie (0.0 à 1.0)
    size_variation: float = 0.0  # Variation de taille (0.0 à 1.0)
    color_variation: float = 0.0  # Variation de couleur (0.0 à 1.0, ajuste la saturation)
    color_palette: Optional[List[Tuple[int, int, int]]] = None  # Palette de couleurs (optionnel). Si spécifié, chaque particule choisit aléatoirement une couleur parmi cette liste au lieu d'utiliser color. Si None, utilise color avec color_variation
    direction_type: Literal["explosion", "rain", "smoke", "sparks", "custom"] = "explosion"
    direction_angle: float = 0.0  # Angle de direction pour "custom" (en radians, 0 = droite)
    direction_spread: float = 2.0 * math.pi  # Étalement de direction (en radians, 2π = toutes directions)
    gravity: float = 0.0  # Force de gravité appliquée (pixels/seconde², positif = vers le bas)
    friction: float = 0.0  # Coefficient de friction/décélération (0.0 à 1.0, ex: 0.95 = ralentit de 5% par seconde)
    size_shrink: bool = False  # Si True, les particules rétrécissent progressivement pendant leur durée de vie
    fade_out: bool = True  # Si True, les particules disparaissent progressivement
    generation_duration: Optional[float] = None  # Durée de génération des particules en secondes (optionnel). Si spécifié, les particules sont générées progressivement sur cette durée au lieu d'être toutes créées immédiatement. Si None, toutes les particules sont créées immédiatement (comportement par défaut)


class ParticleEffect:
    """Représente un effet de particules actif."""
    
    def __init__(
        self,
        x: float,
        y: float,
        config: ParticleEffectConfig,
        effect_id: Optional[str] = None,
        spawn_area: Optional[Dict[str, float]] = None,
        screen_space: bool = False,
    ) -> None:
        """
        Args:
            x: Position horizontale de départ (coordonnées monde). Utilisé comme position de référence si spawn_area est None, ou comme coin supérieur gauche de la zone si spawn_area est spécifié
            y: Position verticale de départ (coordonnées monde). Utilisé comme position de référence si spawn_area est None, ou comme coin supérieur gauche de la zone si spawn_area est spécifié
            config: Configuration de l'effet
            effect_id: Identifiant optionnel pour l'effet (pour le suivi)
            spawn_area: Zone de génération des particules (optionnel). Si spécifié, les particules sont générées aléatoirement dans cette zone. Format: {"x_min": float, "x_max": float, "y_min": float, "y_max": float} (en coordonnées monde). Si None, toutes les particules sont générées à la position (x, y)
        """
        self.x = x
        self.y = y
        self.config = config
        self.effect_id = effect_id
        self.spawn_area = spawn_area
        self.screen_space = screen_space
        self.particles: List[Particle] = []
        self.is_active = True
        
        # Gestion de la génération progressive
        if config.generation_duration is not None and config.generation_duration > 0:
            # Génération progressive : ne pas créer toutes les particules immédiatement
            self.generation_timer: float = config.generation_duration
            self.particles_created: int = 0
            self.total_particles_to_create: int = config.count
            self._particles_accumulator: float = 0.0
        else:
            # Génération immédiate : créer toutes les particules maintenant
            self.generation_timer: float = 0.0
            self.particles_created: int = 0
            self.total_particles_to_create: int = config.count
            self._particles_accumulator: float = 0.0
            self._create_particles()
            # Après la création immédiate, toutes les particules sont créées
            self.particles_created = config.count
    
    def _create_particles(self, count: Optional[int] = None) -> None:
        """Crée les particules selon la configuration.
        
        Args:
            count: Nombre de particules à créer. Si None, crée toutes les particules restantes.
        """
        particles_to_create = count if count is not None else self.config.count
        for _ in range(particles_to_create):
            # Déterminer la position de départ de la particule
            if self.spawn_area is not None:
                # Générer une position aléatoire dans la zone
                particle_x = random.uniform(self.spawn_area["x_min"], self.spawn_area["x_max"])
                particle_y = random.uniform(self.spawn_area["y_min"], self.spawn_area["y_max"])
            else:
                # Utiliser la position de référence
                particle_x = self.x
                particle_y = self.y
            
            # Calculer la direction selon le type
            # Si direction_type est "custom", utiliser direction_angle et direction_spread
            if self.config.direction_type == "custom":
                angle = self.config.direction_angle + random.uniform(
                    -self.config.direction_spread / 2,
                    self.config.direction_spread / 2
                )
            elif self.config.direction_type == "explosion":
                # Pour explosion, direction_spread peut être utilisé pour limiter la dispersion
                if self.config.direction_spread < 2.0 * math.pi:
                    # Si direction_spread est limité, utiliser direction_angle comme centre (ou 0 par défaut)
                    base_angle = self.config.direction_angle
                    angle = base_angle + random.uniform(
                        -self.config.direction_spread / 2,
                        self.config.direction_spread / 2
                    )
                else:
                    # Comportement par défaut : toutes les directions
                    angle = random.uniform(0, 2 * math.pi)
            elif self.config.direction_type == "rain":
                # Pour rain, direction_spread peut être utilisé pour créer une pluie oblique
                base_angle = math.pi / 2  # Vers le bas par défaut
                if self.config.direction_spread > 0:
                    angle = base_angle + random.uniform(
                        -self.config.direction_spread / 2,
                        self.config.direction_spread / 2
                    )
                else:
                    angle = base_angle  # Direction fixe vers le bas
            elif self.config.direction_type == "smoke":
                # Pour smoke, direction_spread peut être utilisé pour ajuster la dispersion
                base_angle = -math.pi / 2  # Vers le haut par défaut
                if self.config.direction_spread > 0:
                    angle = base_angle + random.uniform(
                        -self.config.direction_spread / 2,
                        self.config.direction_spread / 2
                    )
                else:
                    angle = base_angle  # Direction fixe vers le haut
            elif self.config.direction_type == "sparks":
                # Pour sparks, direction_spread peut être utilisé pour ajuster la dispersion
                base_angle = 0.0  # Direction par défaut (vers le haut avec variation de -π/4 à π/4)
                if self.config.direction_spread < math.pi / 2:
                    # Si direction_spread est limité, utiliser direction_angle comme centre (ou 0 par défaut)
                    base_angle = self.config.direction_angle
                    angle = base_angle + random.uniform(
                        -self.config.direction_spread / 2,
                        self.config.direction_spread / 2
                    )
                else:
                    # Comportement par défaut : vers le haut avec variation
                    angle = random.uniform(-math.pi / 4, math.pi / 4)
            else:
                # Type inconnu, utiliser custom par défaut
                angle = self.config.direction_angle + random.uniform(
                    -self.config.direction_spread / 2,
                    self.config.direction_spread / 2
                )
            
            # Calculer la vitesse avec variation
            speed = self.config.speed * random.uniform(
                1.0 - self.config.speed_variation,
                1.0 + self.config.speed_variation
            )
            
            velocity_x = math.cos(angle) * speed
            velocity_y = math.sin(angle) * speed
            
            # Calculer la durée de vie avec variation
            lifetime = self.config.lifetime * random.uniform(
                1.0 - self.config.lifetime_variation,
                1.0 + self.config.lifetime_variation
            )
            
            # Calculer la taille avec variation
            size = int(self.config.size * random.uniform(
                1.0 - self.config.size_variation,
                1.0 + self.config.size_variation
            ))
            size = max(1, size)  # Taille minimale de 1 pixel
            
            # Calculer la couleur
            if self.config.color_palette is not None and len(self.config.color_palette) > 0:
                # Choisir aléatoirement une couleur parmi la palette
                base_color = random.choice(self.config.color_palette)
                # Appliquer la variation de couleur si configurée
                color = self._apply_color_variation(base_color, self.config.color_variation)
            else:
                # Utiliser la couleur de base avec variation
                color = self._apply_color_variation(self.config.color, self.config.color_variation)
            
            particle = Particle(
                x=particle_x,
                y=particle_y,
                velocity_x=velocity_x,
                velocity_y=velocity_y,
                color=color,
                lifetime=lifetime,
                max_lifetime=lifetime,
                size=size
            )
            self.particles.append(particle)
    
    def _create_single_particle(self) -> None:
        """Crée une seule particule selon la configuration.
        
        Cette méthode est utilisée pour la génération progressive des particules.
        """
        # Déterminer la position de départ de la particule
        if self.spawn_area is not None:
            # Générer une position aléatoire dans la zone
            particle_x = random.uniform(self.spawn_area["x_min"], self.spawn_area["x_max"])
            particle_y = random.uniform(self.spawn_area["y_min"], self.spawn_area["y_max"])
        else:
            # Utiliser la position de référence
            particle_x = self.x
            particle_y = self.y
        
        # Calculer la direction selon le type
        # Si direction_type est "custom", utiliser direction_angle et direction_spread
        if self.config.direction_type == "custom":
            angle = self.config.direction_angle + random.uniform(
                -self.config.direction_spread / 2,
                self.config.direction_spread / 2
            )
        elif self.config.direction_type == "explosion":
            # Pour explosion, direction_spread peut être utilisé pour limiter la dispersion
            if self.config.direction_spread < 2.0 * math.pi:
                # Si direction_spread est limité, utiliser direction_angle comme centre (ou 0 par défaut)
                base_angle = self.config.direction_angle
                angle = base_angle + random.uniform(
                    -self.config.direction_spread / 2,
                    self.config.direction_spread / 2
                )
            else:
                # Comportement par défaut : toutes les directions
                angle = random.uniform(0, 2 * math.pi)
        elif self.config.direction_type == "rain":
            # Pour rain, direction_spread peut être utilisé pour créer une pluie oblique
            base_angle = math.pi / 2  # Vers le bas par défaut
            if self.config.direction_spread > 0:
                angle = base_angle + random.uniform(
                    -self.config.direction_spread / 2,
                    self.config.direction_spread / 2
                )
            else:
                angle = base_angle  # Direction fixe vers le bas
        elif self.config.direction_type == "smoke":
            # Pour smoke, direction_spread peut être utilisé pour ajuster la dispersion
            base_angle = -math.pi / 2  # Vers le haut par défaut
            if self.config.direction_spread > 0:
                angle = base_angle + random.uniform(
                    -self.config.direction_spread / 2,
                    self.config.direction_spread / 2
                )
            else:
                angle = base_angle  # Direction fixe vers le haut
        elif self.config.direction_type == "sparks":
            # Pour sparks, direction_spread peut être utilisé pour ajuster la dispersion
            base_angle = 0.0  # Direction par défaut (vers le haut avec variation de -π/4 à π/4)
            if self.config.direction_spread < math.pi / 2:
                # Si direction_spread est limité, utiliser direction_angle comme centre (ou 0 par défaut)
                base_angle = self.config.direction_angle
                angle = base_angle + random.uniform(
                    -self.config.direction_spread / 2,
                    self.config.direction_spread / 2
                )
            else:
                # Comportement par défaut : vers le haut avec variation
                angle = random.uniform(-math.pi / 4, math.pi / 4)
        else:
            # Type inconnu, utiliser custom par défaut
            angle = self.config.direction_angle + random.uniform(
                -self.config.direction_spread / 2,
                self.config.direction_spread / 2
            )
        
        # Calculer la vitesse avec variation
        speed = self.config.speed * random.uniform(
            1.0 - self.config.speed_variation,
            1.0 + self.config.speed_variation
        )
        
        velocity_x = math.cos(angle) * speed
        velocity_y = math.sin(angle) * speed
        
        # Calculer la durée de vie avec variation
        lifetime = self.config.lifetime * random.uniform(
            1.0 - self.config.lifetime_variation,
            1.0 + self.config.lifetime_variation
        )
        
        # Calculer la taille avec variation
        size = int(self.config.size * random.uniform(
            1.0 - self.config.size_variation,
            1.0 + self.config.size_variation
        ))
        size = max(1, size)  # Taille minimale de 1 pixel
        
        # Calculer la couleur
        if self.config.color_palette is not None and len(self.config.color_palette) > 0:
            # Choisir aléatoirement une couleur parmi la palette
            base_color = random.choice(self.config.color_palette)
            # Appliquer la variation de couleur si configurée
            color = self._apply_color_variation(base_color, self.config.color_variation)
        else:
            # Utiliser la couleur de base avec variation
            color = self._apply_color_variation(self.config.color, self.config.color_variation)
        
        particle = Particle(
            x=particle_x,
            y=particle_y,
            velocity_x=velocity_x,
            velocity_y=velocity_y,
            color=color,
            lifetime=lifetime,
            max_lifetime=lifetime,
            size=size
        )
        self.particles.append(particle)
    
    def _apply_color_variation(self, base_color: Tuple[int, int, int], variation: float) -> Tuple[int, int, int]:
        """Applique une variation de couleur.
        
        Args:
            base_color: Couleur de base (RGB)
            variation: Niveau de variation (0.0 à 1.0)
            
        Returns:
            Couleur avec variation appliquée
        """
        if variation <= 0.0:
            return base_color
        
        r, g, b = base_color
        variation_amount = int(255 * variation)
        
        r = max(0, min(255, r + random.randint(-variation_amount, variation_amount)))
        g = max(0, min(255, g + random.randint(-variation_amount, variation_amount)))
        b = max(0, min(255, b + random.randint(-variation_amount, variation_amount)))
        
        return (r, g, b)
    
    def update(self, dt: float, camera_x: float = 0.0, screen_width: int = 1920, screen_height: int = 1080, margin: int = 200) -> None:
        """Met à jour toutes les particules de l'effet.
        
        OPTIMISATION: Ne met à jour que les particules visibles ou proches de l'écran.
        Les particules hors écran voient uniquement leur durée de vie décrémentée
        (pas de calcul de position/physique) pour économiser les calculs.
        
        Args:
            dt: Delta time en secondes
            camera_x: Position horizontale de la caméra (pour le culling, optionnel)
            screen_width: Largeur de l'écran pour le culling (défaut: 1920)
            screen_height: Hauteur de l'écran pour le culling (défaut: 1080)
            margin: Marge en pixels pour le culling hors écran (défaut: 200)
        """
        # Gérer la génération progressive des particules (toujours actif)
        if self.config.generation_duration is not None and self.config.generation_duration > 0:
            if self.particles_created < self.total_particles_to_create and self.generation_timer > 0:
                # Calculer le nombre de particules à générer cette frame
                particles_per_second = self.total_particles_to_create / self.config.generation_duration
                particles_to_create_this_frame = particles_per_second * dt
                
                self._particles_accumulator += particles_to_create_this_frame
                
                particles_to_create_now = int(self._particles_accumulator)
                if particles_to_create_now > 0:
                    remaining_particles = self.total_particles_to_create - self.particles_created
                    particles_to_create_now = min(particles_to_create_now, remaining_particles)
                    
                    if particles_to_create_now > 0:
                        for _ in range(particles_to_create_now):
                            self._create_single_particle()
                        self.particles_created += particles_to_create_now
                        self._particles_accumulator -= particles_to_create_now
                
                self.generation_timer -= dt
                if self.generation_timer <= 0:
                    remaining_particles = self.total_particles_to_create - self.particles_created
                    if remaining_particles > 0:
                        for _ in range(remaining_particles):
                            self._create_single_particle()
                        self.particles_created = self.total_particles_to_create
        
        # OPTIMISATION: Pré-calculer les valeurs constantes par effet une seule fois
        gravity_dt = self.config.gravity * dt if self.config.gravity != 0.0 else 0.0
        friction_factor = self.config.friction ** dt if self.config.friction > 0.0 else 1.0
        has_gravity = self.config.gravity != 0.0
        has_friction = self.config.friction > 0.0
        
        for particle in list(self.particles):
            # OPTIMISATION: Vérifier si la particule est visible avant de la mettre à jour
            particle_x_screen = particle.x if self.screen_space else (particle.x - camera_x)
            
            # Si la particule est hors écran (avec marge), on ne la met pas à jour complètement
            if (particle_x_screen + particle.size < -margin or
                particle_x_screen > screen_width + margin or
                particle.y + particle.size < -margin or
                particle.y > screen_height + margin):
                # Particule hors écran : on met à jour uniquement la durée de vie pour qu'elle meure correctement
                particle.lifetime -= dt
                if not particle.is_alive():
                    self.particles.remove(particle)
                continue  # Skip les calculs de position, gravité, friction, etc.
            
            # Particule visible : mise à jour complète
            # OPTIMISATION: Appliquer la gravité si configurée (gravity_dt pré-calculé)
            if has_gravity:
                particle.velocity_y += gravity_dt
            
            # OPTIMISATION: Appliquer la friction/décélération si configurée (friction_factor pré-calculé)
            if has_friction:
                particle.velocity_x *= friction_factor
                particle.velocity_y *= friction_factor
            
            # Mettre à jour la particule
            particle.update(dt)
            
            # Supprimer les particules mortes
            if not particle.is_alive():
                self.particles.remove(particle)
        
        # Désactiver l'effet si toutes les particules sont mortes et que la génération est terminée
        if len(self.particles) == 0:
            # Vérifier si la génération est terminée
            generation_finished = True
            if self.config.generation_duration is not None and self.config.generation_duration > 0:
                generation_finished = (self.particles_created >= self.total_particles_to_create and self.generation_timer <= 0)
            else:
                generation_finished = True  # Pas de génération progressive, donc terminée
            
            if generation_finished:
                self.is_active = False
    
    def has_particles(self) -> bool:
        """Vérifie si l'effet contient encore des particules vivantes.
        
        Returns:
            True si l'effet contient des particules, False sinon
        """
        return len(self.particles) > 0

