"""Module de gestion des particules."""

from .effect import ParticleEffect, ParticleEffectConfig
from .particle import Particle
from .system import ParticleSystem
from .utils import (
    create_confetti_config,
    create_explosion_config,
    create_flame_explosion_config,
    create_rain_config,
    create_smoke_config,
    create_sparks_config,
    extract_dominant_color,
)

__all__ = [
    "Particle",
    "ParticleEffect",
    "ParticleEffectConfig",
    "ParticleSystem",
    "create_confetti_config",
    "create_explosion_config",
    "create_flame_explosion_config",
    "create_rain_config",
    "create_smoke_config",
    "create_sparks_config",
    "extract_dominant_color",
]

