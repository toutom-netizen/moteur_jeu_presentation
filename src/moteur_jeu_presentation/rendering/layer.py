"""Module de gestion des couches de rendu pour le système de parallaxe."""

from __future__ import annotations

from typing import Optional

import pygame


class Layer:
    """Représente une couche de rendu dans le système de parallaxe."""

    def __init__(
        self,
        name: str,
        depth: int,
        scroll_speed: float,
        surface: pygame.Surface,
        repeat: bool = True,
        world_x_offset: float = 0.0,
        infinite_offset: float = 0.0,
        is_background: bool = False,
        is_foreground: bool = False,
        is_climbable: bool = False,
    ) -> None:
        """Initialise une couche de parallaxe.

        Args:
            name: Nom identifiant de la couche
            depth: Profondeur de la couche (0 = background, 3 = foreground)
            scroll_speed: Multiplicateur de vitesse de défilement (0.0 à 1.0+)
            surface: Surface pygame contenant l'image de la couche
            repeat: Si True, la couche se répète horizontalement
            world_x_offset: Offset horizontal dans l'espace du monde (pour les sprites avec x_offset négatif)
            infinite_offset: Distance entre chaque répétition infinie (en pixels, utilisé uniquement si repeat=True)
            is_background: Si True, la couche s'affiche derrière le joueur et n'a pas de collision (uniquement applicable pour depth 2)
            is_foreground: Si True, la couche s'affiche devant les autres éléments de depth 2 et n'a pas de collision (uniquement applicable pour depth 2)
            is_climbable: Si True, la couche peut être grimpée par le joueur (uniquement applicable pour depth 2 avec is_background = true)
        """
        self.name = name
        self.depth = depth
        self.scroll_speed = scroll_speed
        # Optimiser les surfaces : convert_alpha() pour transparence, convert() sinon
        # Utiliser convert() avec la surface d'affichage pour de meilleures performances
        if surface.get_flags() & pygame.SRCALPHA:
            self.surface = surface.convert_alpha()
        else:
            self.surface = surface.convert()
        self.repeat = repeat
        self.offset_x = 0.0
        self.world_x_offset = world_x_offset  # Offset horizontal dans l'espace du monde
        self.world_y_offset = 0.0  # Offset vertical dans l'espace du monde (pour les plateformes mobiles)
        self.infinite_offset = infinite_offset  # Distance entre chaque répétition infinie
        self.alpha = 255  # Opacité de la couche (0-255, défaut: 255 = opaque). Utilisé pour le masquage progressif de sprites via le système d'événements
        self.is_hidden = False  # Indique si la couche est masquée (défaut: False). Utilisé par le système d'événements pour marquer les layers complètement masquées
        self.rotation_angle = 0.0  # Angle de rotation en degrés (0-360, défaut: 0.0 = pas de rotation). Utilisé pour la rotation de sprites via le système d'événements
        self.is_background = is_background  # Si True, la couche s'affiche derrière le joueur et n'a pas de collision (uniquement applicable pour depth 2)
        self.is_foreground = is_foreground  # Si True, la couche s'affiche devant les autres éléments de depth 2 et n'a pas de collision (uniquement applicable pour depth 2)
        self.is_climbable = is_climbable  # Si True, la couche peut être grimpée par le joueur (uniquement applicable pour depth 2 avec is_background = true)
        
        # Cache pour les valeurs statiques (évite les recalculs à chaque frame)
        self._cached_width = surface.get_width()
        self._cached_height = surface.get_height()
        self._cached_effective_width = self._cached_width + infinite_offset if repeat else self._cached_width
        # Cache pour le nombre de répétitions nécessaires (calculé lors de l'ajout au système)
        self._cached_num_repeats: Optional[int] = None
        # Cache pour les surfaces avec opacité (évite de recréer les surfaces à chaque frame)
        # Clé: alpha, Valeur: surface avec opacité appliquée
        self._alpha_surface_cache: dict[int, pygame.Surface] = {}
        self._last_alpha: int = 255  # Dernière valeur d'opacité utilisée pour le cache

    def update(self, camera_x: float, dt: float) -> None:
        """Met à jour la position de défilement de la couche.

        Args:
            camera_x: Position horizontale de la caméra
            dt: Delta time en secondes (non utilisé actuellement mais disponible pour animations futures)
        """
        self.offset_x = camera_x * self.scroll_speed

