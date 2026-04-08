"""Module de base pour les entités du jeu."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

import pygame

if TYPE_CHECKING:
    pass


class Entity(ABC):
    """Classe de base abstraite pour toutes les entités du jeu (joueur, PNJ, etc.)."""

    def __init__(
        self,
        x: float,
        y: float,
        sprite_width: int,
        sprite_height: int,
    ) -> None:
        """Initialise une entité.

        Args:
            x: Position horizontale initiale
            y: Position verticale initiale
            sprite_width: Largeur d'un sprite
            sprite_height: Hauteur d'un sprite
        """
        self.x = x
        self.y = y
        self.sprite_width = sprite_width
        self.sprite_height = sprite_height

        # Dimensions d'affichage (peuvent être redéfinies par les sous-classes)
        self.display_width: float = float(sprite_width)
        self.display_height: float = float(sprite_height)

        # Propriétés de collision (seront synchronisées avec la taille affichée)
        self.collision_width: float = float(sprite_width) - 40.0
        self.collision_height: float = float(sprite_height) - 6.0
        self.collision_offset_x: float = 10.0
        self.collision_offset_y: float = -4.0

        # Propriétés de gravité
        self.velocity_y: float = 0.0
        self.gravity: float = 800.0
        self.max_fall_speed: float = 500.0
        self.is_on_ground: bool = False
        
        # Propriété pour les plateformes mobiles
        self.attached_platform: Optional[object] = None  # Layer à laquelle l'entité est attachée

        # Optimisation : réutiliser un seul pygame.Rect au lieu d'en créer un nouveau à chaque frame
        self._collision_rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)

        # Synchroniser les dimensions de collision avec la taille affichée par défaut
        self._update_collision_dimensions_for_display()

    def _update_collision_dimensions_for_display(self) -> None:
        """Met à jour les dimensions de collision en fonction de la taille affichée.

        Conserve une marge horizontale de 20 pixels de chaque côté et une marge verticale de 6 pixels
        en haut, quel que soit le facteur d'échelle appliqué au sprite.
        """

        self.collision_width = max(self.display_width - 40.0, 1.0)
        self.collision_height = max(self.display_height - 6.0, 1.0)

    def get_collision_rect(self) -> pygame.Rect:
        """Récupère le rectangle de collision de l'entité.

        Returns:
            Rectangle de collision dans l'espace du monde
        """
        # Le sprite est centré sur (x, y), donc le bas du sprite est à y + sprite_height/2
        # Le rectangle de collision doit avoir son bas à la même position
        collision_x = self.x - self.collision_width / 2 + self.collision_offset_x
        collision_y = (
            self.y
            + self.sprite_height / 2
            - self.collision_height
            + self.collision_offset_y
        )

        # Optimisation : réutiliser le même Rect au lieu d'en créer un nouveau
        # Utiliser round() au lieu de int() pour un arrondi plus précis
        self._collision_rect.x = round(collision_x)
        self._collision_rect.y = round(collision_y)
        self._collision_rect.width = round(self.collision_width)
        self._collision_rect.height = round(self.collision_height)
        
        return self._collision_rect

    @abstractmethod
    def update(self, dt: float, camera_x: float) -> None:
        """Met à jour l'entité.

        Args:
            dt: Delta time en secondes
            camera_x: Position horizontale de la caméra
        """
        pass

    @abstractmethod
    def draw(self, surface: pygame.Surface, camera_x: float) -> None:
        """Dessine l'entité sur la surface.

        Args:
            surface: Surface pygame sur laquelle dessiner
            camera_x: Position horizontale de la caméra
        """
        pass

