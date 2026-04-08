"""Module de gestion des particules individuelles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class Particle:
    """Représente une particule individuelle."""

    x: float  # Position horizontale (en pixels, coordonnées monde)
    y: float  # Position verticale (en pixels, coordonnées monde)
    velocity_x: float  # Vitesse horizontale (en pixels/seconde)
    velocity_y: float  # Vitesse verticale (en pixels/seconde)
    color: Tuple[int, int, int]  # Couleur RGB de la particule
    lifetime: float  # Durée de vie restante (en secondes)
    max_lifetime: float  # Durée de vie maximale (en secondes)
    size: int  # Taille de la particule (diamètre en pixels)

    def update(self, dt: float) -> None:
        """Met à jour la position et la durée de vie de la particule.

        Args:
            dt: Delta time en secondes
        """
        self.x += self.velocity_x * dt
        self.y += self.velocity_y * dt
        self.lifetime -= dt

    def is_alive(self) -> bool:
        """Vérifie si la particule est encore vivante.

        Returns:
            True si la particule est encore vivante, False sinon
        """
        return self.lifetime > 0.0

    def get_opacity(self) -> int:
        """Calcule l'opacité de la particule basée sur sa durée de vie.

        Returns:
            Opacité de 0 à 255
        """
        if self.max_lifetime <= 0:
            return 255
        progress = self.lifetime / self.max_lifetime
        return int(255 * progress)

    def get_size(self, size_shrink: bool = False) -> int:
        """Calcule la taille actuelle de la particule.

        Si size_shrink est True, la taille diminue progressivement de la taille initiale à 0.

        Args:
            size_shrink: Si True, la taille diminue avec la durée de vie

        Returns:
            Taille actuelle de la particule en pixels
        """
        if not size_shrink or self.max_lifetime <= 0:
            return self.size
        progress = self.lifetime / self.max_lifetime
        return int(self.size * progress)

