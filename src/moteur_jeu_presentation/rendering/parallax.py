"""Module de gestion du système de parallaxe multi-couches."""

from __future__ import annotations

import math
from typing import Optional

import pygame

from .layer import Layer


class ParallaxSystem:
    """Gestionnaire du système de parallaxe multi-couches."""

    def __init__(self, screen_width: int, screen_height: int) -> None:
        """Initialise le système de parallaxe.

        Args:
            screen_width: Largeur de l'écran de rendu
            screen_height: Hauteur de l'écran de rendu
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self._layers: list[Layer] = []

    def add_layer(self, layer: Layer) -> None:
        """Ajoute une couche au système.

        Les couches sont automatiquement triées par profondeur (depth) pour
        garantir le bon ordre de rendu.

        Args:
            layer: La couche à ajouter
        """
        # Optimisation : pré-calculer le nombre de répétitions nécessaires si la couche est répétable
        if layer.repeat and layer._cached_effective_width > 0:
            # Calculer une seule fois le nombre de répétitions nécessaires
            layer._cached_num_repeats = math.ceil(self.screen_width / layer._cached_effective_width) + 2
        
        self._layers.append(layer)
        # Trier les couches par profondeur (du plus éloigné au plus proche)
        self._layers.sort(key=lambda l: l.depth)

    def update(self, camera_x: float, dt: float) -> None:
        """Met à jour les positions de toutes les couches.

        Args:
            camera_x: Position horizontale de la caméra
            dt: Delta time en secondes
        """
        for layer in self._layers:
            layer.update(camera_x, dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Dessine toutes les couches dans l'ordre de profondeur.

        Les couches sont rendues du fond vers l'avant (depth 0 à 3).
        Les couches avec repeat=True sont répétées horizontalement pour
        créer un défilement infini.
        
        OPTIMISATION CRITIQUE: Toutes les commandes de dessin sont accumulées
        et envoyées en un seul appel blits() pour maximiser les performances.
        Cela réduit drastiquement le nombre d'appels système et améliore le FPS.

        Args:
            surface: Surface pygame sur laquelle dessiner les couches
        """
        # Accumuler toutes les commandes de dessin pour un seul appel blits()
        # C'est l'optimisation la plus importante pour le FPS
        all_blit_commands: list[tuple[pygame.Surface, tuple[int, int]]] = []
        
        for layer in self._layers:
            layer_commands = self._get_layer_blit_commands(layer)
            all_blit_commands.extend(layer_commands)
        
        # UN SEUL appel blits() pour toutes les couches - gain de performance massif
        if all_blit_commands:
            surface.blits(all_blit_commands, False)

    def _get_layer_blit_commands(self, layer: Layer) -> list[tuple[pygame.Surface, tuple[int, int]]]:
        """Génère les commandes de dessin pour une couche individuelle.

        Gère le rendu d'une couche avec support de la répétition horizontale
        pour créer un défilement infini. Utilise le clipping pour optimiser
        les performances en ne dessinant que les parties visibles.
        
        IMPORTANT : Les positions sont arrondies à des entiers pour éviter
        les saccades visuelles causées par l'arrondi automatique de pygame.
        
        OPTIMISATION: Retourne une liste de commandes au lieu de dessiner directement,
        permettant de batcher tous les appels blits() en un seul.

        Args:
            layer: La couche à dessiner
            
        Returns:
            Liste de tuples (surface, position) pour blits()
        """
        blit_commands: list[tuple[pygame.Surface, tuple[int, int]]] = []
        # Utiliser les valeurs en cache pour éviter les recalculs
        layer_width = layer._cached_width
        effective_width = layer._cached_effective_width
        
        # Obtenir la surface avec transformations appliquées
        needs_rotation = layer.rotation_angle != 0.0
        if needs_rotation:
            # Appliquer la rotation (pygame.transform.rotate tourne dans le sens antihoraire, donc on inverse)
            transformed_surface = pygame.transform.rotate(layer.surface, -layer.rotation_angle)
            transformed_width = transformed_surface.get_width()
            transformed_height = transformed_surface.get_height()
            # Calculer le décalage pour centrer la rotation
            # Le centre de la surface originale doit rester au même endroit après rotation
            rotation_offset_x = (transformed_width - layer_width) // 2
            rotation_offset_y = (transformed_height - layer._cached_height) // 2
        else:
            transformed_surface = layer.surface
            transformed_width = layer_width
            transformed_height = layer._cached_height
            rotation_offset_x = 0
            rotation_offset_y = 0
        
        # Appliquer l'opacité si nécessaire
        if layer.alpha < 255:
            if needs_rotation:
                # La surface est déjà transformée par la rotation, créer une copie pour l'opacité
                transformed_surface = transformed_surface.copy()
                transformed_surface.set_alpha(int(layer.alpha))
            else:
                # Utiliser le cache pour éviter de recréer la surface à chaque frame
                alpha_int = int(layer.alpha)
                if alpha_int not in layer._alpha_surface_cache:
                    # Créer une copie de la surface avec l'opacité et la mettre en cache
                    temp_surface = layer.surface.copy()
                    temp_surface.set_alpha(alpha_int)
                    layer._alpha_surface_cache[alpha_int] = temp_surface
                transformed_surface = layer._alpha_surface_cache[alpha_int]

        if layer.repeat:
            # Optimisation : utiliser le nombre de répétitions mis en cache si disponible
            # Sinon, le calculer (fallback pour compatibilité)
            if layer._cached_num_repeats is not None:
                num_repeats = layer._cached_num_repeats
            else:
                # Calculer le nombre de répétitions nécessaires
                # On ajoute 2 répétitions supplémentaires pour couvrir les bords
                num_repeats = math.ceil(self.screen_width / effective_width) + 2

            # Calculer la position de départ en tenant compte de l'offset
            # Utiliser effective_width au lieu de layer_width pour tenir compte de l'espacement
            # world_x_offset ancre la couche dans le repère du niveau ; offset_x est le défilement caméra
            # On place la première répétition avant l'écran pour éviter les gaps sur la gauche.
            start_offset = ((layer.world_x_offset - layer.offset_x) % effective_width) - effective_width

            # Dessiner chaque répétition avec l'espacement
            # Optimisation : ne dessiner que les répétitions visibles
            if layer.is_hidden or layer.alpha <= 0:
                return  # Ne pas dessiner si complètement masquée
            
            for i in range(num_repeats):
                x_float = start_offset + (i * effective_width) - rotation_offset_x
                x = int(round(x_float))  # Arrondir à l'entier le plus proche
                # Ne dessiner que si la répétition est visible à l'écran
                # Prendre en compte world_y_offset pour les plateformes mobiles
                world_y_offset = getattr(layer, 'world_y_offset', 0.0)
                y = int(round(world_y_offset - rotation_offset_y))
                if x + transformed_width >= 0 and x < self.screen_width:
                    blit_commands.append((transformed_surface, (x, y)))
        else:
            # Couche non répétable : dessiner une seule fois
            # Tenir compte du world_x_offset pour les sprites avec x_offset négatif
            # Optimisation : world_x_offset est toujours un attribut de Layer, pas besoin de hasattr()
            if layer.is_hidden or layer.alpha <= 0:
                return blit_commands  # Ne pas dessiner si complètement masquée
            
            world_x_offset = layer.world_x_offset
            x_float = -layer.offset_x + world_x_offset - rotation_offset_x
            x = int(round(x_float))  # Arrondir à l'entier le plus proche pour éviter les saccades
            # Ne dessiner que si la couche est visible
            # Prendre en compte world_y_offset pour les plateformes mobiles
            world_y_offset = getattr(layer, 'world_y_offset', 0.0)
            y = int(round(world_y_offset - rotation_offset_y))
            if x + transformed_width >= 0 and x < self.screen_width:
                blit_commands.append((transformed_surface, (x, y)))
        
        return blit_commands

    def get_layer_by_name(self, name: str) -> Optional[Layer]:
        """Récupère une couche par son nom.

        Args:
            name: Le nom de la couche à rechercher

        Returns:
            La couche trouvée, ou None si aucune couche ne correspond
        """
        for layer in self._layers:
            if layer.name == name:
                return layer
        return None

