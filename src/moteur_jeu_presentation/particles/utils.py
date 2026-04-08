"""Utilitaires pour le moteur de particules."""

from __future__ import annotations

import math
import random
from typing import Optional, Tuple

import pygame

from .effect import ParticleEffectConfig


def extract_dominant_color(
    sprite: Optional[pygame.Surface],
    sample_count: int = 100,
    default_color: Tuple[int, int, int] = (255, 200, 0),
) -> Tuple[int, int, int]:
    """Extrait la couleur dominante d'un sprite.
    
    Args:
        sprite: Surface du sprite (peut être None)
        sample_count: Nombre de pixels à échantillonner (défaut: 100)
        default_color: Couleur par défaut si le sprite est None ou invalide
        
    Returns:
        Couleur RGB dominante, ou couleur par défaut
    """
    if sprite is None:
        return default_color
    
    width = sprite.get_width()
    height = sprite.get_height()
    
    if width <= 0 or height <= 0:
        return default_color
    
    # Échantillonner quelques pixels (pas tous pour la performance)
    sample_count = min(sample_count, width * height)
    r_sum, g_sum, b_sum, count = 0, 0, 0, 0
    
    for _ in range(sample_count):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        color = sprite.get_at((x, y))
        
        # Ignorer les pixels transparents
        if color[3] > 128:  # Alpha > 128
            r_sum += color[0]
            g_sum += color[1]
            b_sum += color[2]
            count += 1
    
    if count > 0:
        return (r_sum // count, g_sum // count, b_sum // count)
    else:
        return default_color


def create_explosion_config(
    count: int = 24,
    speed: float = 320.0,
    lifetime: float = 0.4,
    size: int = 16,
    color: Tuple[int, int, int] = (255, 200, 0),
) -> ParticleEffectConfig:
    """Crée une configuration d'effet d'explosion.
    
    Args:
        count: Nombre de particules
        speed: Vitesse de base (pixels/seconde)
        lifetime: Durée de vie (secondes)
        size: Taille des particules (diamètre en pixels)
        color: Couleur de base (RGB)
        
    Returns:
        Configuration d'effet d'explosion
    """
    return ParticleEffectConfig(
        count=count,
        speed=speed,
        speed_variation=0.4,
        lifetime=lifetime,
        lifetime_variation=0.2,
        size=size,
        size_variation=0.5,
        color=color,
        color_variation=0.3,
        direction_type="explosion",
        gravity=400.0,
        friction=0.92,
        size_shrink=True,
        fade_out=True,
    )


def create_rain_config(
    count: int = 100,
    speed: float = 200.0,
    lifetime: float = 2.0,
    size: int = 4,
    color: Tuple[int, int, int] = (150, 150, 200),
) -> ParticleEffectConfig:
    """Crée une configuration d'effet de pluie.
    
    Args:
        count: Nombre de particules
        speed: Vitesse de chute (pixels/seconde)
        lifetime: Durée de vie (secondes)
        size: Taille des particules (diamètre en pixels)
        color: Couleur de base (RGB)
        
    Returns:
        Configuration d'effet de pluie
    """
    return ParticleEffectConfig(
        count=count,
        speed=speed,
        speed_variation=0.2,
        lifetime=lifetime,
        size=size,
        color=color,
        color_variation=0.0,  # Pas de variation de couleur par défaut pour rain
        direction_type="rain",
        direction_angle=0.0,  # Non utilisé pour rain, mais défini explicitement pour clarté
        direction_spread=0.0,  # Direction fixe vers le bas (pas de dispersion)
        gravity=100.0,
        fade_out=False,
    )


def create_smoke_config(
    count: int = 30,
    speed: float = 50.0,
    lifetime: float = 3.0,
    size: int = 8,
    color: Tuple[int, int, int] = (100, 100, 100),
) -> ParticleEffectConfig:
    """Crée une configuration d'effet de fumée.
    
    Args:
        count: Nombre de particules
        speed: Vitesse de montée (pixels/seconde)
        lifetime: Durée de vie (secondes)
        size: Taille de base des particules (diamètre en pixels)
        color: Couleur de base (RGB)
        
    Returns:
        Configuration d'effet de fumée
    """
    return ParticleEffectConfig(
        count=count,
        speed=speed,
        speed_variation=0.4,
        lifetime=lifetime,
        lifetime_variation=0.3,
        size=size,
        size_variation=0.5,
        color=color,
        color_variation=0.2,
        direction_type="smoke",
        direction_spread=math.pi / 4,
        gravity=-20.0,
        fade_out=True,
    )


def create_sparks_config(
    count: int = 15,
    speed: float = 400.0,
    lifetime: float = 0.3,
    size: int = 6,
    color: Tuple[int, int, int] = (255, 200, 0),
) -> ParticleEffectConfig:
    """Crée une configuration d'effet d'étincelles.
    
    Args:
        count: Nombre de particules
        speed: Vitesse de base (pixels/seconde)
        lifetime: Durée de vie (secondes)
        size: Taille des particules (diamètre en pixels)
        color: Couleur de base (RGB)
        
    Returns:
        Configuration d'effet d'étincelles
    """
    return ParticleEffectConfig(
        count=count,
        speed=speed,
        speed_variation=0.5,
        lifetime=lifetime,
        size=size,
        color=color,
        color_variation=0.0,  # Pas de variation de couleur par défaut pour sparks
        direction_type="sparks",
        direction_angle=0.0,  # Non utilisé pour sparks par défaut, mais défini explicitement pour clarté
        direction_spread=math.pi / 2,  # Dispersion par défaut pour sparks (variation de -π/4 à π/4)
        gravity=200.0,
        fade_out=True,
    )


def create_flame_explosion_config(
    count: int = 24,
    speed: float = 320.0,
    lifetime: float = 0.4,
    size: int = 16,
) -> ParticleEffectConfig:
    """Crée une configuration d'effet d'explosion de flamme colorée et dynamique.
    
    L'effet d'explosion de flamme est conçu pour ressembler à une explosion de feu :
    - Les particules se dispersent dans toutes les directions
    - Les particules ralentissent progressivement (friction)
    - Les particules tombent sous l'effet de la gravité
    - Les particules utilisent une palette de couleurs chaudes (rouge, orange, jaune) avec une variation importante
    - Les particules varient en taille pour un effet plus riche
    - Les particules rétrécissent progressivement pendant leur durée de vie
    - Les particules disparaissent progressivement (fade-out)
    
    Args:
        count: Nombre de particules (défaut: 24)
        speed: Vitesse de base (pixels/seconde, défaut: 320.0)
        lifetime: Durée de vie (secondes, défaut: 0.4)
        size: Taille de base des particules (diamètre en pixels, défaut: 16)
        
    Returns:
        Configuration d'effet d'explosion de flamme avec friction, gravité et variations de couleur importantes
    """
    return ParticleEffectConfig(
        count=count,
        speed=speed,
        speed_variation=0.4,
        lifetime=lifetime,
        lifetime_variation=0.2,
        size=size,
        size_variation=0.5,
        color=(255, 100, 0),  # Couleur de base orange/rouge vif pour l'effet de flamme
        color_variation=0.6,  # Variation de couleur importante (60%) pour créer un effet de flamme colorée
        direction_type="explosion",
        direction_spread=2.0 * math.pi,
        gravity=400.0,
        friction=0.92,
        size_shrink=True,
        fade_out=True,
    )


def create_confetti_config(
    count: int = 50,
    speed: float = 400.0,
    lifetime: float = 2.5,
    size: int = 12,
) -> ParticleEffectConfig:
    """Crée une configuration d'effet de confetti festif.
    
    L'effet de confetti est conçu pour célébrer des événements comme le passage de niveau :
    - Les particules se dispersent dans toutes les directions
    - Les particules utilisent une palette de couleurs vives et variées
    - Les particules ralentissent progressivement (friction)
    - Les particules tombent sous l'effet de la gravité
    - Les particules varient en taille, vitesse et couleur pour un effet dynamique
    - Les particules rétrécissent progressivement pendant leur durée de vie
    - Les particules disparaissent progressivement (fade-out)
    
    Args:
        count: Nombre de particules (défaut: 50)
        speed: Vitesse de base (pixels/seconde, défaut: 400.0)
        lifetime: Durée de vie (secondes, défaut: 2.5)
        size: Taille de base des particules (diamètre en pixels, défaut: 12)
        
    Returns:
        Configuration d'effet de confetti avec friction, gravité et variations de couleur importantes
    """
    base_color = (255, 100, 100)  # Couleur de base (rose/rouge) avec variation importante
    
    return ParticleEffectConfig(
        count=count,
        speed=speed,
        speed_variation=0.5,
        lifetime=lifetime,
        lifetime_variation=0.3,
        size=size,
        size_variation=0.6,
        color=base_color,
        color_variation=0.8,  # Variation de couleur très importante (80%) pour créer une palette colorée et festive
        direction_type="explosion",
        direction_spread=2.0 * math.pi,
        gravity=500.0,
        friction=0.90,
        size_shrink=True,
        fade_out=True,
    )

