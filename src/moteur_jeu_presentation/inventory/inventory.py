"""Module de gestion de l'inventaire du joueur."""

from __future__ import annotations

import logging
import math
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pygame

from .config import InventoryItemConfig, ItemAnimationState
from ..particles import ParticleSystem, create_flame_explosion_config

logger = logging.getLogger(__name__)

# Variables globales pour les durées d'animation
INVENTORY_ADD_ANIMATION_DURATION: float = 0.6  # Durée en secondes (augmentée pour l'effet d'agrandissement)
INVENTORY_ADD_SCALE_FACTOR: float = 10.0  # Facteur d'agrandissement initial (10x la taille normale)
INVENTORY_REMOVE_ANIMATION_DURATION: float = 0.7  # Durée en secondes (augmentée pour l'effet d'agrandissement et d'explosion)
INVENTORY_REMOVE_SCALE_FACTOR: float = 10.0  # Facteur d'agrandissement final (10x la taille normale)
INVENTORY_REMOVE_PARTICLES_COUNT: int = 24  # Nombre de particules dans l'explosion (configurable pour ajuster les performances et l'effet visuel)
INVENTORY_REMOVE_PARTICLES_SPEED: float = 320.0  # Vitesse de base des particules en pixels/seconde (augmentée pour que les particules partent plus loin)
INVENTORY_REMOVE_PARTICLES_LIFETIME: float = 0.4  # Durée de vie des particules en secondes
INVENTORY_REMOVE_PARTICLES_SIZE: int = 16  # Taille de base des particules en pixels (diamètre, sera multipliée par INVENTORY_REMOVE_SCALE_FACTOR)
INVENTORY_REMOVE_EXPLOSION_START: float = 0.8  # Moment où l'explosion commence (0.0 à 1.0, 0.8 = 80% de l'animation, quand l'objet est proche du centre)


class Inventory:
    """Gestionnaire d'inventaire pour le personnage principal."""

    def __init__(
        self,
        item_config: Optional[InventoryItemConfig] = None,
        item_spacing: int = 6,
        item_scale: float = 1.0,
        display_offset_y: float = -8.0,
        particle_system: Optional[ParticleSystem] = None,
    ) -> None:
        """Initialise l'inventaire.

        Args:
            item_config: Configuration des objets disponibles (optionnel)
            item_spacing: Espacement horizontal entre les objets en pixels (défaut: 6)
            item_scale: Facteur d'échelle pour l'affichage des objets (défaut: 1.0 = taille native)
            display_offset_y: Offset vertical pour positionner l'inventaire au-dessus du prénom (défaut: -8.0)
            particle_system: Référence au système de particules global (optionnel, nécessaire pour les animations de suppression)
        """
        self.items: Dict[str, int] = {}  # Dictionnaire des objets (clé = item_id, valeur = quantité)
        self.item_config = item_config
        self.item_spacing = item_spacing
        self.item_scale = item_scale
        self.display_offset_y = display_offset_y
        self.particle_system = particle_system

        # Utiliser les caches globaux au lieu de caches locaux
        from ..assets.preloader import _global_inventory_sprite_sheet_cache, _global_inventory_cached_surfaces
        
        # Références aux caches globaux (pour compatibilité avec le code existant)
        self._sprite_sheet_cache: Dict[str, pygame.Surface] = _global_inventory_sprite_sheet_cache
        self._cached_surfaces: Dict[str, pygame.Surface] = _global_inventory_cached_surfaces
        
        # État des animations pour chaque objet (clé = item_id, valeur = état d'animation)
        self._item_animations: Dict[str, ItemAnimationState] = {}
        # Cache des surfaces redimensionnées avec opacité (clé: (sprite_id, final_scale, opacity))
        # Évite de recalculer smoothscale et les copies pour l'opacité à chaque frame
        self._scaled_alpha_surface_cache: Dict[Tuple[int, float, int], pygame.Surface] = {}

    def add_item(self, item_id: str, quantity: int = 1, animated: bool = True) -> None:
        """Ajoute un ou plusieurs exemplaires d'un objet à l'inventaire.

        Args:
            item_id: ID technique de l'objet
            quantity: Quantité à ajouter (défaut: 1)
            animated: Si True, déclenche une animation d'apparition progressive (défaut: True)

        Raises:
            ValueError: Si la quantité est négative
        """
        if quantity < 0:
            raise ValueError(f"Quantity must be positive (got {quantity})")

        if quantity == 0:
            return

        # Vérifier que l'objet existe dans la configuration
        if self.item_config is None:
            logger.warning(f"Unknown item ID '{item_id}', ignoring (no item config)")
            return

        item = self.item_config.get_item(item_id)
        if item is None:
            logger.warning(f"Unknown item ID '{item_id}', ignoring")
            return

        # Ajouter l'objet à l'inventaire
        if item_id in self.items:
            self.items[item_id] += quantity
        else:
            self.items[item_id] = quantity

        # Charger le sprite si nécessaire
        if item_id not in self._cached_surfaces:
            sprite = item.load_sprite(self._sprite_sheet_cache)
            self._cached_surfaces[item_id] = sprite

        # Déclencher l'animation d'ajout si demandé
        # Note: Les positions (target_x, target_y, screen_center_x, screen_center_y) seront
        # initialisées dans get_display_commands lors du premier rendu
        if animated:
            self._item_animations[item_id] = ItemAnimationState(
                animation_type="add",
                progress=0.0,
                offset_x=0.0,
                offset_y=0.0,
                scale=INVENTORY_ADD_SCALE_FACTOR,  # Commence à 10x
                opacity=0,
                is_complete=False,
            )

    def remove_item(self, item_id: str, quantity: int = 1, animated: bool = True) -> bool:
        """Retire un ou plusieurs exemplaires d'un objet de l'inventaire.

        Args:
            item_id: ID technique de l'objet
            quantity: Quantité à retirer (défaut: 1)
            animated: Si True, déclenche une animation de saut vers l'arrière puis disparition (défaut: True)

        Returns:
            True si l'opération a réussi, False si la quantité est insuffisante
        """
        if item_id not in self.items:
            logger.warning(f"Cannot remove item '{item_id}': not in inventory")
            return False

        current_quantity = self.items[item_id]
        if current_quantity < quantity:
            logger.warning(
                f"Cannot remove {quantity} of '{item_id}': only {current_quantity} available"
            )
            return False

        # Récupérer le sprite de l'objet pour l'animation (avant de retirer l'objet)
        sprite = self._load_item_sprite(item_id)
        
        # Déclencher l'animation de suppression si demandé (avant de retirer l'objet)
        # Note: Les positions (start_x, start_y, screen_center_x, screen_center_y) seront
        # initialisées dans get_display_commands lors du premier rendu
        if animated:
            self._item_animations[item_id] = ItemAnimationState(
                animation_type="remove",
                progress=0.0,
                offset_x=0.0,
                offset_y=0.0,
                scale=1.0,  # Commence à 1x
                opacity=255,
                is_complete=False,
                item_sprite=sprite,
                particle_base_x=0.0,
                particle_base_y=0.0,
            )

        self.items[item_id] -= quantity

        # Si la quantité atteint 0, retirer l'objet de l'inventaire
        # Mais garder l'animation active pour l'affichage
        if self.items[item_id] <= 0:
            del self.items[item_id]

        return True

    def has_item(self, item_id: str, quantity: int = 1) -> bool:
        """Vérifie si l'inventaire contient au moins quantity exemplaires de l'objet.

        Args:
            item_id: ID technique de l'objet
            quantity: Quantité minimale requise (défaut: 1)

        Returns:
            True si l'inventaire contient au moins quantity exemplaires, False sinon
        """
        return self.get_quantity(item_id) >= quantity

    def get_quantity(self, item_id: str) -> int:
        """Retourne la quantité d'un objet dans l'inventaire.

        Args:
            item_id: ID technique de l'objet

        Returns:
            Quantité de l'objet (0 si absent)
        """
        return self.items.get(item_id, 0)

    def get_all_items(self) -> Dict[str, int]:
        """Retourne une copie du dictionnaire des objets.

        Returns:
            Dictionnaire des objets (clé = item_id, valeur = quantité)
        """
        return self.items.copy()

    def clear(self) -> None:
        """Vide complètement l'inventaire."""
        self.items.clear()
        self._item_animations.clear()

    def set_particle_system(self, particle_system: ParticleSystem) -> None:
        """Définit la référence au système de particules global.
        
        Args:
            particle_system: Référence au système de particules global
        """
        self.particle_system = particle_system

    def update_animations(self, dt: float, camera_x: float = 0.0) -> None:
        """Met à jour les animations d'ajout et de suppression des objets.

        Args:
            dt: Delta time en secondes
            camera_x: Position horizontale de la caméra (nécessaire pour convertir les coordonnées écran en coordonnées monde lors de la création des particules)
        """
        # Parcourir toutes les animations en cours
        for item_id, animation_state in list(self._item_animations.items()):
            # Mettre à jour la progression
            if animation_state.animation_type == "add":
                duration = INVENTORY_ADD_ANIMATION_DURATION
            else:  # "remove"
                duration = INVENTORY_REMOVE_ANIMATION_DURATION

            old_progress = animation_state.progress
            animation_state.progress += dt / duration

            # Limiter la progression à 1.0
            if animation_state.progress >= 1.0:
                animation_state.progress = 1.0
                animation_state.is_complete = True

            # Calculer l'opacité, les décalages et l'échelle
            if animation_state.animation_type == "add":
                # Animation d'ajout : du centre de l'écran (10x) vers la position finale (1x)
                animation_state.opacity = int(255 * animation_state.progress)
                # Interpolation de position : du centre de l'écran vers la position cible
                # offset_x et offset_y seront calculés dans get_display_commands car ils dépendent
                # de screen_center_x, screen_center_y, target_x, target_y qui sont calculés là-bas
                # Interpolation d'échelle : de 10x à 1x
                animation_state.scale = INVENTORY_ADD_SCALE_FACTOR - (INVENTORY_ADD_SCALE_FACTOR - 1.0) * animation_state.progress
            else:  # "remove"
                # Animation de suppression : de la position actuelle (1x) vers le centre de l'écran (10x)
                animation_state.opacity = int(255 * (1 - animation_state.progress))
                # Interpolation de position : de la position de départ vers le centre de l'écran
                # offset_x et offset_y seront calculés dans get_display_commands car ils dépendent
                # de start_x, start_y, screen_center_x, screen_center_y qui sont calculés là-bas
                # Interpolation d'échelle : de 1x à 10x
                animation_state.scale = 1.0 + (INVENTORY_REMOVE_SCALE_FACTOR - 1.0) * animation_state.progress
                
                # Générer les particules d'explosion au bon moment
                # Note: L'implémentation utilise le système de particules global (spec 14)
                if (old_progress < INVENTORY_REMOVE_EXPLOSION_START and 
                    animation_state.progress >= INVENTORY_REMOVE_EXPLOSION_START and
                    animation_state.particle_effect_id is None):
                    # Mettre à jour la position de base des particules au centre de l'écran
                    animation_state.particle_base_x = animation_state.screen_center_x
                    animation_state.particle_base_y = animation_state.screen_center_y
                    # Créer les particules d'explosion via le système de particules global
                    # camera_x est passé en paramètre à update_animations()
                    self._create_explosion_particles(animation_state, item_id, camera_x)

            # Si l'animation est terminée, supprimer l'état
            # Note: Les particules sont gérées par le système de particules global,
            # elles seront automatiquement nettoyées une fois leur durée de vie écoulée
            if animation_state.is_complete:
                del self._item_animations[item_id]

    def preload_all_sprites(self) -> None:
        """Précharge tous les sprites des objets définis dans la configuration."""
        if self.item_config is None:
            return

        for item_id, item in self.item_config.items.items():
            if item_id not in self._cached_surfaces:
                sprite = item.load_sprite(self._sprite_sheet_cache)
                self._cached_surfaces[item_id] = sprite

    def _load_item_sprite(self, item_id: str) -> Optional[pygame.Surface]:
        """Charge et extrait le sprite d'un objet depuis le sprite sheet.

        Args:
            item_id: ID technique de l'objet

        Returns:
            Surface pygame du sprite, ou None si l'objet n'existe pas
        """
        if self.item_config is None:
            return None

        item = self.item_config.get_item(item_id)
        if item is None:
            return None

        if item_id not in self._cached_surfaces:
            sprite = item.load_sprite(self._sprite_sheet_cache)
            self._cached_surfaces[item_id] = sprite

        return self._cached_surfaces.get(item_id)

    def _create_explosion_particles(self, animation_state: ItemAnimationState, item_id: str, camera_x: float) -> None:
        """Crée les particules d'explosion de flamme pour une animation de suppression.
        
        Cette méthode utilise le système de particules global (spécification 14) pour créer
        et gérer les effets de particules. L'explosion utilise une palette de couleurs chaudes
        (rouge, orange, jaune) pour créer un effet de flamme colorée et dynamique, indépendamment
        de la couleur de l'objet.
        
        Args:
            animation_state: État d'animation pour lequel créer les particules
            item_id: Identifiant de l'objet (utilisé pour créer un identifiant unique pour l'effet)
            camera_x: Position horizontale de la caméra (nécessaire pour convertir les coordonnées écran en coordonnées monde)
        
        Note:
            Si le système de particules n'est pas disponible, la méthode retourne silencieusement
            sans créer d'effet (pas d'erreur levée pour permettre le fonctionnement sans particules).
        """
        if self.particle_system is None:
            # Si le système de particules n'est pas disponible, ignorer silencieusement
            # (pas d'erreur levée pour permettre le fonctionnement sans particules)
            return
        
        # Créer la configuration d'explosion de flamme
        # La taille des particules est multipliée par le facteur d'agrandissement pour correspondre à la taille de l'objet
        config = create_flame_explosion_config(
            count=INVENTORY_REMOVE_PARTICLES_COUNT,
            speed=INVENTORY_REMOVE_PARTICLES_SPEED,
            lifetime=INVENTORY_REMOVE_PARTICLES_LIFETIME,
            size=int(INVENTORY_REMOVE_PARTICLES_SIZE * INVENTORY_REMOVE_SCALE_FACTOR),  # Taille agrandie
        )
        
        # Créer l'effet de particules via le système global
        # Note: Le centre de l'écran est en coordonnées écran, mais le système de particules
        # utilise des coordonnées monde. Il faut convertir les coordonnées écran en coordonnées monde
        # en ajoutant la position de la caméra (camera_x) pour la coordonnée X.
        # Pour la coordonnée Y, le centre de l'écran en coordonnées écran correspond directement
        # à la coordonnée Y en coordonnées monde (pas de décalage vertical de caméra dans ce jeu).
        # 
        # Conversion: world_x = screen_x + camera_x, world_y = screen_y
        effect_id = f"inventory_remove_{item_id}"
        
        # Convertir les coordonnées écran en coordonnées monde
        # particle_base_x et particle_base_y sont en coordonnées écran (centre de l'écran)
        world_x = animation_state.particle_base_x + camera_x  # Conversion: screen_x + camera_x
        world_y = animation_state.particle_base_y  # Généralement identique en coordonnées monde (pas de décalage vertical)
        
        self.particle_system.create_effect(
            world_x,
            world_y,
            config,
            effect_id=effect_id
        )
        
        # Enregistrer l'identifiant de l'effet pour pouvoir le suivre si nécessaire
        animation_state.particle_effect_id = effect_id

    def get_display_commands(
        self,
        camera_x: float,
        player_x: float,
        player_y: float,
        name_y: float,
        screen_width: int,
        screen_height: int,
    ) -> List[Tuple[pygame.Surface, Tuple[int, int]]]:
        """Génère les commandes de dessin pour afficher l'inventaire au-dessus du prénom.

        Prend en compte les animations en cours (opacité, position, échelle, etc.).

        Args:
            camera_x: Position horizontale de la caméra
            player_x: Position horizontale du joueur dans le monde
            player_y: Position verticale du joueur dans le monde
            name_y: Position verticale du prénom à l'écran
            screen_width: Largeur de l'écran en pixels
            screen_height: Hauteur de l'écran en pixels

        Returns:
            Liste des commandes de dessin (surface, position)
        """
        # Calculer le centre de l'écran
        screen_center_x = screen_width / 2.0
        screen_center_y = screen_height / 2.0

        # Récupérer tous les item_ids à afficher (items + animations de suppression en cours)
        item_ids_to_display = set(self.items.keys())
        # Ajouter les objets en cours d'animation de suppression (même s'ils ne sont plus dans items)
        # Ajouter aussi les objets en cours d'animation d'ajout (pour les afficher pendant l'animation)
        for item_id in self._item_animations.keys():
            item_ids_to_display.add(item_id)

        if not item_ids_to_display:
            return []

        commands: List[Tuple[pygame.Surface, Tuple[int, int]]] = []

        # Calculer la largeur totale des objets (avec espacement) - sans tenir compte de l'échelle d'animation
        # car on va calculer les positions cibles d'abord
        total_width = 0
        item_surfaces: List[Tuple[pygame.Surface, str, Optional[ItemAnimationState], int, int]] = []  # (sprite, item_id, animation_state, sprite_width, sprite_height)

        # Parcourir les objets dans l'ordre d'ajout (ordre du dictionnaire)
        # Pour les animations de suppression, utiliser l'ordre des animations
        ordered_item_ids = list(self.items.keys()) + [
            item_id
            for item_id in self._item_animations.keys()
            if item_id not in self.items
        ]

        for item_id in ordered_item_ids:
            if item_id not in item_ids_to_display:
                continue

            sprite = self._load_item_sprite(item_id)
            if sprite is None:
                continue

            # Récupérer l'état d'animation si présent
            animation_state = self._item_animations.get(item_id)

            # Stocker les dimensions originales du sprite
            original_width = sprite.get_width()
            original_height = sprite.get_height()

            item_surfaces.append((sprite, item_id, animation_state, original_width, original_height))
            # Pour le calcul de la largeur totale, utiliser la taille normale (sans échelle d'animation)
            # car on calcule la position cible normale
            total_width += original_width * self.item_scale
            if len(item_surfaces) > 1:
                total_width += self.item_spacing

        # Calculer la position de départ (centrée horizontalement par rapport au joueur)
        screen_x = player_x - camera_x
        inventory_start_x = screen_x - (total_width / 2) if item_surfaces else screen_x

        # Calculer la position verticale (au-dessus du prénom)
        # Utiliser la hauteur du premier sprite pour le calcul, ou une valeur par défaut
        if item_surfaces:
            first_sprite, _, _, _, first_height = item_surfaces[0]
            inventory_y = name_y + self.display_offset_y - (first_height * self.item_scale)
        else:
            # Si aucun objet n'est affiché, utiliser une position par défaut
            inventory_y = name_y + self.display_offset_y - 32  # 32 pixels par défaut

        # Initialiser les positions pour les animations et calculer les positions cibles
        current_x = inventory_start_x
        for sprite, item_id, animation_state, sprite_width, sprite_height in item_surfaces:
            # Calculer la position cible normale de l'objet dans l'inventaire (sans animation)
            target_x = current_x
            target_y = inventory_y

            # Initialiser les positions pour les animations si nécessaire
            if animation_state is not None:
                # Initialiser le centre de l'écran si pas encore fait
                if animation_state.screen_center_x == 0.0:
                    animation_state.screen_center_x = screen_center_x
                if animation_state.screen_center_y == 0.0:
                    animation_state.screen_center_y = screen_center_y

                if animation_state.animation_type == "add":
                    # Pour l'animation d'ajout, initialiser la position cible
                    if animation_state.target_x == 0.0:
                        animation_state.target_x = target_x
                    if animation_state.target_y == 0.0:
                        animation_state.target_y = target_y
                    
                    # Calculer l'offset pour interpoler entre le centre de l'écran et la position cible
                    current_anim_x = animation_state.screen_center_x + (animation_state.target_x - animation_state.screen_center_x) * animation_state.progress
                    current_anim_y = animation_state.screen_center_y + (animation_state.target_y - animation_state.screen_center_y) * animation_state.progress
                    animation_state.offset_x = current_anim_x - target_x
                    animation_state.offset_y = current_anim_y - target_y
                else:  # "remove"
                    # Pour l'animation de suppression, initialiser la position de départ
                    if animation_state.start_x == 0.0:
                        animation_state.start_x = target_x
                    if animation_state.start_y == 0.0:
                        animation_state.start_y = target_y
                    
                    # Calculer l'offset pour interpoler entre la position de départ et le centre de l'écran
                    current_anim_x = animation_state.start_x + (animation_state.screen_center_x - animation_state.start_x) * animation_state.progress
                    current_anim_y = animation_state.start_y + (animation_state.screen_center_y - animation_state.start_y) * animation_state.progress
                    animation_state.offset_x = current_anim_x - target_x
                    animation_state.offset_y = current_anim_y - target_y

            current_x += sprite_width * self.item_scale + self.item_spacing

        # Générer les commandes de dessin avec les décalages d'animation et l'échelle
        current_x = inventory_start_x
        for sprite, item_id, animation_state, sprite_width, sprite_height in item_surfaces:
            # Calculer la position cible normale
            target_x = current_x
            target_y = inventory_y

            # Récupérer l'échelle d'animation si présente
            anim_scale = animation_state.scale if animation_state else 1.0
            
            # Calculer la taille finale du sprite (item_scale * anim_scale)
            final_scale = self.item_scale * anim_scale
            scaled_width = int(sprite_width * final_scale)
            scaled_height = int(sprite_height * final_scale)

            # Récupérer l'opacité si une animation est en cours
            opacity = animation_state.opacity if animation_state is not None else 255

            # OPTIMISATION: Utiliser le cache pour les surfaces redimensionnées avec opacité
            sprite_id = id(sprite)
            cache_key = (sprite_id, final_scale, opacity)
            
            if cache_key in self._scaled_alpha_surface_cache:
                scaled_sprite = self._scaled_alpha_surface_cache[cache_key]
            else:
                # Redimensionner le sprite
                if final_scale != 1.0:
                    scaled_sprite = pygame.transform.smoothscale(sprite, (scaled_width, scaled_height))
                else:
                    scaled_sprite = sprite

                # Appliquer l'opacité si nécessaire
                if animation_state is not None and opacity < 255:
                    # Créer une copie de la surface pour appliquer l'opacité
                    sprite_with_alpha = scaled_sprite.copy()
                    sprite_with_alpha.set_alpha(opacity)
                    scaled_sprite = sprite_with_alpha
                elif animation_state is not None and opacity == 255:
                    # Pas besoin de copie si l'opacité est à 255
                    pass

                # Mettre en cache (limiter la taille du cache pour éviter les fuites mémoire)
                if len(self._scaled_alpha_surface_cache) > 100:
                    # Nettoyer le cache si trop d'entrées (garder seulement les 50 plus récentes)
                    keys_to_remove = list(self._scaled_alpha_surface_cache.keys())[:-50]
                    for key in keys_to_remove:
                        del self._scaled_alpha_surface_cache[key]
                
                self._scaled_alpha_surface_cache[cache_key] = scaled_sprite

            # Calculer la position de rendu avec les offsets d'animation
            offset_x = animation_state.offset_x if animation_state else 0.0
            offset_y = animation_state.offset_y if animation_state else 0.0

            # Ajuster la position pour centrer correctement l'objet redimensionné
            # Si l'objet est agrandi, on doit soustraire la moitié de l'augmentation de taille
            center_offset_x = (scaled_width - sprite_width * self.item_scale) / 2.0
            center_offset_y = (scaled_height - sprite_height * self.item_scale) / 2.0

            pos_x = round(target_x + offset_x - center_offset_x)
            pos_y = round(target_y + offset_y - center_offset_y)

            commands.append((scaled_sprite, (pos_x, pos_y)))
            
            current_x += sprite_width * self.item_scale + self.item_spacing

        # Note: Les particules d'explosion sont gérées et rendues séparément par le système de particules global
        # via particle_system.get_display_commands(camera_x) dans la boucle principale

        return commands

