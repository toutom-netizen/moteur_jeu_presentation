"""Module de gestion des personnages non joueurs."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Optional, Tuple

import pygame

from ..rendering.config import RENDER_WIDTH, compute_design_scale, get_render_size

logger = logging.getLogger("moteur_jeu_presentation.npc")

if TYPE_CHECKING:
    from ..game.events import EventTriggerSystem
    from ..game.progress import LevelProgressTracker
    from ..levels.config import (
        AnimationConfig,
        DialogueBlockConfig,
        DialogueExchangeConfig,
        NPCConfig,
    )
    from ..physics.collision import CollisionSystem
    from ..ui.speech_bubble import SpeechBubble
    from .player import Player

from .entity import Entity


class NPC(Entity):
    """Représente un personnage non joueur."""

    def __init__(
        self,
        config: NPCConfig,
        collision_system: CollisionSystem,
        assets_root: Optional[Path] = None,
    ) -> None:
        """Initialise un PNJ.

        Args:
            config: Configuration du PNJ
            collision_system: Système de collisions pour le positionnement par gravité
            assets_root: Répertoire de base pour les ressources
        """
        # Initialiser la classe de base
        # Si y est défini dans la config, utiliser cette valeur, sinon commencer en haut (y=0.0)
        initial_y = config.y if config.y is not None else 0.0
        super().__init__(config.x, initial_y, config.sprite_width, config.sprite_height)
        
        self.config = config
        self.collision_system = collision_system
        self.assets_root = Path(assets_root) if assets_root else Path.cwd()

        # ID technique unique du PNJ
        self.id = config.id

        self._positioned: bool = False  # Indique si le PNJ a été positionné par la gravité

        # Propriétés pour le déplacement déclenché par événements
        self._move_target_x: Optional[float] = None  # Position X cible pour le déplacement
        self._move_speed: float = 0.0  # Vitesse de déplacement horizontal
        self._move_animation_row: Optional[int] = None  # Ligne du sprite sheet pour l'animation temporaire
        self._move_animation_frames: Optional[int] = None  # Nombre de frames pour l'animation temporaire
        self._original_animation: Optional[str] = None  # Animation originale à restaurer après le déplacement

        # Propriétés pour le suivi du personnage principal
        self._is_following_player: bool = False  # Indique si le PNJ suit actuellement le personnage principal
        self._follow_player: Optional["Player"] = None  # Référence au personnage principal à suivre
        self._follow_distance: float = 100.0  # Distance horizontale à maintenir derrière le joueur en pixels
        self._follow_speed: float = 200.0  # Vitesse de déplacement lors du suivi en pixels par seconde
        self._follow_animation_row: Optional[int] = None  # Ligne du sprite sheet pour l'animation de suivi
        self._follow_animation_frames: Optional[int] = None  # Nombre de frames pour l'animation de suivi
        self._player_last_x: float = 0.0  # Position X précédente du joueur (pour détecter les changements de direction)

        # Propriétés pour la téléportation magique
        self._magic_move_animation_row: Optional[int] = None  # Ligne du sprite sheet pour l'animation lors de la réapparition
        self._magic_move_animation_start: Optional[int] = None  # Frame de départ pour l'animation lors de la réapparition

        # Charger le sprite sheet (utiliser le cache global si disponible)
        from ..assets.preloader import _global_npc_sprite_sheet_cache
        
        sprite_path = Path(config.sprite_sheet_path)
        if not sprite_path.is_absolute():
            sprite_path = self.assets_root.parent / sprite_path
        
        sprite_path_key = str(sprite_path.resolve())
        
        # Vérifier d'abord le cache global
        if sprite_path_key in _global_npc_sprite_sheet_cache:
            self.sprite_sheet = _global_npc_sprite_sheet_cache[sprite_path_key]
        else:
            # Charger depuis le disque si pas en cache
            if not sprite_path.exists():
                raise FileNotFoundError(f"Sprite sheet introuvable: {sprite_path}")
            self.sprite_sheet = pygame.image.load(str(sprite_path)).convert_alpha()

        # Direction (initialisée depuis la configuration, peut être modifiée dynamiquement)
        self.direction: Literal["left", "right"] = config.direction

        # Facteur d'échelle pour l'affichage des sprites
        self.sprite_scale = config.sprite_scale
        # Dimensions d'affichage (calculées à partir de la taille du sprite sheet et du facteur d'échelle)
        # IMPORTANT : Le sprite_scale est appliqué DANS le repère de conception (1920x1080),
        # puis on convertit le résultat vers la résolution interne (1280x720)
        render_width, render_height = get_render_size()
        scale_x, scale_y = compute_design_scale((render_width, render_height))
        # Étape 1 : Appliquer le sprite_scale dans le repère 1920x1080
        scaled_width_in_design = config.sprite_width * config.sprite_scale
        scaled_height_in_design = config.sprite_height * config.sprite_scale
        # Étape 2 : Convertir vers la résolution interne 1280x720
        self.display_width = int(scaled_width_in_design * scale_x)
        self.display_height = int(scaled_height_in_design * scale_y)

        # Adapter la hitbox à la taille affichée
        self._update_collision_dimensions_for_display()

        # Animations
        self.animations = config.animations or {}
        self._frame_cache: dict[tuple[int, int], pygame.Surface] = {}
        self._flipped_frame_cache: dict[tuple[int, int], pygame.Surface] = {}
        # Caches pour les sprites redimensionnés (normal et flip)
        self._scaled_frame_cache: dict[tuple[int, int, int, int], pygame.Surface] = {}
        self._scaled_flipped_frame_cache: dict[tuple[int, int, int, int], pygame.Surface] = {}
        self._sheet_columns: int = max(1, self.sprite_sheet.get_width() // self.sprite_width)
        self._sheet_rows: int = max(1, self.sprite_sheet.get_height() // self.sprite_height)
        self.current_animation: Optional[str] = None
        self.current_frame: int = 0
        self.animation_timer: float = 0.0
        # Optimisation : pré-calculer frame_duration pour chaque animation
        self._animation_frame_durations: dict[str, float] = {
            anim_name: 1.0 / anim_config.animation_speed if anim_config.animation_speed > 0 else 0.0
            for anim_name, anim_config in self.animations.items()
        }

        # Définir l'animation par défaut (idle si disponible, sinon première animation)
        if "idle" in self.animations:
            self.current_animation = "idle"
        elif len(self.animations) > 0:
            self.current_animation = list(self.animations.keys())[0]

        # Nom
        self.name = config.name
        self.name_color = config.name_color
        self.name_outline_color = config.name_outline_color
        self.name_offset_y = config.name_offset_y
        self.name_surface: Optional[pygame.Surface] = None
        self.name_rect: Optional[pygame.Rect] = None

        # Convertir la taille de police du repère de conception (1920x1080) vers la résolution interne (1280x720)
        render_width, render_height = get_render_size()
        _, scale_y = compute_design_scale((render_width, render_height))
        converted_font_size = int(config.font_size * scale_y)
        
        # Charger la police avec la taille convertie
        self.font = self._load_font(config.font_path, converted_font_size)

        # Rendre le nom une première fois
        self._render_name()

        # Blocs de dialogue
        self.dialogue_blocks = config.dialogue_blocks

        # Opacité pour les effets de fade in/out (0-255, 255 = complètement opaque)
        self.alpha: int = 255

        # Contrôle de la gravité et des collisions (pour la téléportation magique)
        self._gravity_enabled: bool = True
        self._collisions_enabled: bool = True

    def _load_font(self, font_path: Optional[str], font_size: int) -> pygame.font.Font:
        """Charge une police pour le nom.

        Args:
            font_path: Chemin vers le fichier de police (optionnel)
            font_size: Taille de la police

        Returns:
            Police pygame chargée
        """
        if font_path:
            font_file = Path(font_path)
            if not font_file.is_absolute():
                font_file = self.assets_root.parent / font_file
            if font_file.exists():
                try:
                    return pygame.font.Font(str(font_file), font_size)
                except pygame.error:
                    pass

        # Fallback vers police système
        try:
            return pygame.font.SysFont("arial", font_size, bold=True)
        except pygame.error:
            return pygame.font.SysFont("sans-serif", font_size, bold=True)

    def _render_name(self) -> None:
        """Génère la surface contenant le nom avec contour."""
        if not self.name:
            self.name_surface = None
            self.name_rect = None
            return

        # Rendre le texte principal avec anti-aliasing
        text_surface = self.font.render(self.name, True, self.name_color)

        # Créer une surface plus grande pour le contour
        outline_thickness = 2
        outline_width = text_surface.get_width() + (outline_thickness * 2)
        outline_height = text_surface.get_height() + (outline_thickness * 2)
        self.name_surface = pygame.Surface((outline_width, outline_height), pygame.SRCALPHA)

        # Dessiner le contour
        for layer in range(outline_thickness):
            offset = layer + 1
            for dx in [-offset, 0, offset]:
                for dy in [-offset, 0, offset]:
                    if dx != 0 or dy != 0:
                        outline_text = self.font.render(self.name, True, self.name_outline_color)
                        self.name_surface.blit(
                            outline_text, (outline_thickness + dx, outline_thickness + dy)
                        )

        # Dessiner le texte principal par-dessus le contour
        self.name_surface.blit(text_surface, (outline_thickness, outline_thickness))

        # Calculer le rectangle pour le centrage
        self.name_rect = self.name_surface.get_rect()


    def _get_current_sprite(self) -> pygame.Surface:
        """Récupère le sprite actuel à afficher.

        Returns:
            Surface pygame contenant le sprite actuel
        """
        if self.current_animation and self.current_animation in self.animations:
            anim_config = self.animations[self.current_animation]
            row = anim_config.row
            col = self.current_frame
        else:
            # Pas d'animation : afficher la première frame de la première ligne
            row = 0
            col = 0
        
        return self._get_sprite_at(row, col)

    def _get_sprite_at(self, row: int, col: int) -> pygame.Surface:
        """Extrait un sprite à la position (row, col) du sprite sheet.

        Args:
            row: Index de la ligne (0-based)
            col: Index de la colonne (0-based)

        Returns:
            Surface pygame contenant le sprite extrait (redimensionné selon sprite_scale)
        """
        # Valider et garantir que les coordonnées restent dans les bornes du sprite sheet
        safe_row = max(0, min(row, self._sheet_rows - 1)) if self._sheet_rows > 0 else 0
        safe_col = col % self._sheet_columns if self._sheet_columns > 0 else col
        
        # Si le sprite doit être redimensionné, vérifier d'abord le cache global préchargé
        if self.sprite_scale != 1.0:
            from ..assets.preloader import _global_npc_scaled_sprite_cache
            
            # Construire la clé pour le cache global (même format que dans le préchargement)
            sprite_path = Path(self.config.sprite_sheet_path)
            if not sprite_path.is_absolute():
                sprite_path = self.assets_root.parent / sprite_path
            sprite_path_key = str(sprite_path.resolve())
            
            global_cache_key = (sprite_path_key, safe_row, safe_col, int(self.display_width), int(self.display_height))
            
            # Vérifier le cache global préchargé
            if global_cache_key in _global_npc_scaled_sprite_cache:
                return _global_npc_scaled_sprite_cache[global_cache_key]
            
            # Fallback : vérifier le cache local
            scaled_key = (safe_row, safe_col, int(self.display_width), int(self.display_height))
            if scaled_key in self._scaled_frame_cache:
                return self._scaled_frame_cache[scaled_key]
        
        # Extraire le sprite non redimensionné (pour cache local ou si sprite_scale == 1.0)
        cache_key = (safe_row, safe_col)

        if cache_key in self._frame_cache:
            sprite = self._frame_cache[cache_key]
        else:
            # Calculer les coordonnées d'extraction
            x = safe_col * self.sprite_width
            y = safe_row * self.sprite_height
            
            # Valider que le rectangle d'extraction reste dans les limites du sprite sheet
            sheet_width = self.sprite_sheet.get_width()
            sheet_height = self.sprite_sheet.get_height()
            
            # S'assurer que le point d'origine reste dans les limites
            max_x = max(sheet_width - self.sprite_width, 0)
            max_y = max(sheet_height - self.sprite_height, 0)
            x = max(0, min(x, max_x))
            y = max(0, min(y, max_y))
            
            # Ajuster la taille du rectangle si nécessaire
            rect_width = min(self.sprite_width, sheet_width - x)
            rect_height = min(self.sprite_height, sheet_height - y)
            
            if rect_width <= 0 or rect_height <= 0:
                sprite = pygame.Surface((self.sprite_width, self.sprite_height), pygame.SRCALPHA)
                self._frame_cache[cache_key] = sprite
                if self.sprite_scale == 1.0:
                    return sprite
            else:
                rect = pygame.Rect(x, y, rect_width, rect_height)
                
                try:
                    sprite = self.sprite_sheet.subsurface(rect).copy()
                    if sprite.get_width() != self.sprite_width or sprite.get_height() != self.sprite_height:
                        resized = pygame.Surface((self.sprite_width, self.sprite_height), pygame.SRCALPHA)
                        resized.blit(sprite, (0, 0))
                        sprite = resized
                    sprite = sprite.convert_alpha()
                except (ValueError, pygame.error):
                    sprite = pygame.Surface((self.sprite_width, self.sprite_height), pygame.SRCALPHA)
                    self._frame_cache[cache_key] = sprite
                    if self.sprite_scale == 1.0:
                        return sprite
            
            self._frame_cache[cache_key] = sprite

        if self.sprite_scale == 1.0:
            return sprite

        # Redimensionner le sprite (fallback si pas dans le cache global)
        scaled_key = (safe_row, safe_col, int(self.display_width), int(self.display_height))
        if scaled_key in self._scaled_frame_cache:
            return self._scaled_frame_cache[scaled_key]

        # OPTIMISATION: Éviter smoothscale si la taille cible est identique à la taille originale
        target_size = (int(self.display_width), int(self.display_height))
        if sprite.get_size() == target_size:
            # Pas besoin de redimensionner, mettre en cache directement
            scaled_sprite = sprite.convert_alpha()
            self._scaled_frame_cache[scaled_key] = scaled_sprite
            return scaled_sprite

        scaled_sprite = pygame.transform.smoothscale(
            sprite, target_size
        )
        scaled_sprite = scaled_sprite.convert_alpha()
        self._scaled_frame_cache[scaled_key] = scaled_sprite
        return scaled_sprite

    def _get_flipped_sprite(self, row: int, col: int) -> pygame.Surface:
        """Récupère la version inversée horizontalement d'un sprite (avec cache).

        Args:
            row: Index de la ligne (0-based)
            col: Index de la colonne (0-based)

        Returns:
            Sprite inversé horizontalement (depuis le cache si disponible)
        """
        # Utiliser la même validation que _get_sprite_at pour le cache
        safe_row = max(0, min(row, self._sheet_rows - 1)) if self._sheet_rows > 0 else 0
        safe_col = col % self._sheet_columns if self._sheet_columns > 0 else col

        # Si le sprite doit être redimensionné, vérifier d'abord le cache global préchargé
        if self.sprite_scale != 1.0:
            from ..assets.preloader import _global_npc_scaled_flipped_sprite_cache
            
            # Construire la clé pour le cache global (même format que dans le préchargement)
            sprite_path = Path(self.config.sprite_sheet_path)
            if not sprite_path.is_absolute():
                sprite_path = self.assets_root.parent / sprite_path
            sprite_path_key = str(sprite_path.resolve())
            
            global_cache_key = (sprite_path_key, safe_row, safe_col, int(self.display_width), int(self.display_height))
            
            # Vérifier le cache global préchargé
            if global_cache_key in _global_npc_scaled_flipped_sprite_cache:
                return _global_npc_scaled_flipped_sprite_cache[global_cache_key]
            
            # Fallback : vérifier le cache local
            scaled_key = (safe_row, safe_col, int(self.display_width), int(self.display_height))
            if scaled_key in self._scaled_flipped_frame_cache:
                return self._scaled_flipped_frame_cache[scaled_key]

        # Extraire le sprite non redimensionné (pour cache local ou si sprite_scale == 1.0)
        cache_key = (safe_row, safe_col)

        # Vérifier le cache (mais on doit quand même redimensionner)
        # Note: Le cache stocke les sprites non redimensionnés, on les redimensionne à la volée
        if cache_key in self._flipped_frame_cache:
            flipped_sprite = self._flipped_frame_cache[cache_key]
        else:
            # Récupérer le sprite original (sans redimensionnement pour éviter la double mise à l'échelle)
            if cache_key in self._frame_cache:
                original_sprite = self._frame_cache[cache_key]
            else:
                x = safe_col * self.sprite_width
                y = safe_row * self.sprite_height
                original_sprite = pygame.Surface((self.sprite_width, self.sprite_height), pygame.SRCALPHA)
                original_sprite.blit(self.sprite_sheet, (0, 0), (x, y, self.sprite_width, self.sprite_height))
                original_sprite = original_sprite.convert_alpha()
                self._frame_cache[cache_key] = original_sprite

            # Inverser horizontalement le sprite
            flipped_sprite = pygame.transform.flip(original_sprite, True, False)
            flipped_sprite = flipped_sprite.convert_alpha()

            self._flipped_frame_cache[cache_key] = flipped_sprite

        if self.sprite_scale == 1.0:
            return flipped_sprite

        # Redimensionner le sprite (fallback si pas dans le cache global)
        scaled_key = (safe_row, safe_col, int(self.display_width), int(self.display_height))
        if scaled_key in self._scaled_flipped_frame_cache:
            return self._scaled_flipped_frame_cache[scaled_key]

        # OPTIMISATION: Éviter smoothscale si la taille cible est identique à la taille originale
        target_size = (int(self.display_width), int(self.display_height))
        if flipped_sprite.get_size() == target_size:
            # Pas besoin de redimensionner, mettre en cache directement
            scaled_sprite = flipped_sprite.convert_alpha()
            self._scaled_flipped_frame_cache[scaled_key] = scaled_sprite
            return scaled_sprite

        scaled_sprite = pygame.transform.smoothscale(
            flipped_sprite, target_size
        )
        scaled_sprite = scaled_sprite.convert_alpha()

        self._scaled_flipped_frame_cache[scaled_key] = scaled_sprite
        return scaled_sprite

    def _update_animation(self, dt: float) -> None:
        """Met à jour l'animation du PNJ.

        Args:
            dt: Delta time en secondes
        """
        if not self.current_animation or self.current_animation not in self.animations:
            return

        anim_config = self.animations[self.current_animation]

        # Si la vitesse est nulle ou qu'il n'y a qu'une seule frame, rester sur la première frame
        if anim_config.animation_speed <= 0.0 or anim_config.num_frames <= 1:
            self.current_frame = min(self.current_frame, max(anim_config.num_frames - 1, 0))
            return

        # Incrémenter le timer d'animation
        self.animation_timer += dt

        # Optimisation : utiliser frame_duration pré-calculé au lieu de division à chaque frame
        frame_duration = self._animation_frame_durations.get(self.current_animation, 0.0)

        # Avancer à la frame suivante si nécessaire
        if frame_duration > 0 and self.animation_timer >= frame_duration:
            self.current_frame += 1
            if self.current_frame >= anim_config.num_frames:
                if anim_config.loop:
                    self.current_frame = 0
                else:
                    self.current_frame = anim_config.num_frames - 1
            self.animation_timer = 0.0

    def _apply_gravity(self, dt: float, camera_x: float) -> None:
        """Applique la gravité et résout les collisions verticales.
        
        Cette méthode est appelée en permanence à chaque frame, pas seulement lors du positionnement initial.
        Elle applique la gravité et résout les collisions verticales pour maintenir le PNJ au sol
        ou gérer les chutes, même pendant les déplacements horizontaux.

        Args:
            dt: Delta time en secondes
            camera_x: Position horizontale de la caméra
        """
        # Si la gravité est désactivée, ne rien faire
        if not self._gravity_enabled:
            return
        
        if self._positioned:
            # Le PNJ est déjà positionné, appliquer la gravité normalement
            # La gravité s'applique même si le PNJ est au sol (pour maintenir le contact)
            if not self.is_on_ground:
                self.velocity_y += self.gravity * dt
                if self.velocity_y > self.max_fall_speed:
                    self.velocity_y = self.max_fall_speed

            # Calculer le déplacement vertical prévu
            dy = self.velocity_y * dt
            
            # Résoudre les collisions verticales (dx=0.0 car on ne gère que les collisions verticales ici)
            # Si les collisions sont désactivées, ne pas résoudre les collisions
            if self._collisions_enabled:
                player_rect = self.get_collision_rect()
                _, corrected_dy, is_on_ground = self.collision_system.resolve_collision(
                    player_rect, 0.0, dy, self, camera_x
                )
            else:
                # Si les collisions sont désactivées, appliquer le déplacement sans résolution
                corrected_dy = dy
                is_on_ground = False
            
            # Mettre à jour la position Y et l'état au sol
            self.is_on_ground = is_on_ground
            self.y += corrected_dy

            if is_on_ground:
                self.velocity_y = 0.0
            return

        # Le PNJ n'est pas encore positionné, le faire tomber jusqu'au premier bloc
        # Pour le positionnement initial, utiliser une caméra calculée à partir de la position du PNJ
        # avec une marge très large pour s'assurer que tous les rectangles de collision sont détectés
        # Utiliser une marge de 2000 pixels pour couvrir une large zone autour du PNJ
        initial_camera_x = self.x - (RENDER_WIDTH / 2)  # Approximer la caméra (centre de l'écran)
        
        # Si y est défini dans la config, laisser la gravité normale faire tomber le PNJ
        # depuis la position Y initiale jusqu'à ce qu'il rencontre un bloc
        # Sinon, chercher directement le bloc le plus haut pour un positionnement immédiat
        initial_y_from_config = self.config.y if self.config.y is not None else None
        
        if initial_y_from_config is not None:
            # y est défini : laisser la gravité normale faire tomber le PNJ
            # Le PNJ commence à la position Y spécifiée et la gravité le fait tomber
            # jusqu'à ce qu'il rencontre un bloc (via la méthode de chute progressive ci-dessous)
            # Ne pas chercher de bloc immédiatement, laisser la gravité faire son travail
            found_block = False
        else:
            # y n'est pas défini : chercher directement le bloc le plus haut pour un positionnement immédiat
            # Récupérer tous les rectangles de collision dans une large zone autour du PNJ
            # Pour le positionnement initial, on veut tous les rectangles, pas seulement ceux visibles
            all_collision_rects = self.collision_system.get_collision_rects(initial_camera_x)
            
            # Position X du centre du PNJ
            npc_center_x = self.x
            
            # Trouver le premier bloc de depth 2 à la position X du PNJ
            # On cherche le bloc le plus haut (y le plus petit) à la position X du PNJ
            min_y = float('inf')
            found_block = False
            
            # Vérifier tous les rectangles de collision pour trouver celui qui est à la position X du PNJ
            # Pour les couches répétables, il peut y avoir plusieurs répétitions, donc on doit vérifier toutes
            for tile_rect in all_collision_rects:
                # Vérifier si le tile est à la même position X (le centre du PNJ doit être dans le tile)
                # Utiliser une tolérance pour gérer les cas où le centre est exactement sur le bord
                if npc_center_x >= tile_rect.left - 1 and npc_center_x <= tile_rect.right + 1:
                    # Ce tile est à la position X du PNJ
                    # On cherche le tile le plus haut (y le plus petit) pour positionner le PNJ dessus
                    if tile_rect.top < min_y:
                        min_y = tile_rect.top
                        found_block = True
        
        if found_block:
            # Positionner le PNJ sur le bloc trouvé (uniquement si y n'était pas défini)
            # Le bas du rectangle de collision doit être au-dessus du tile
            # collision_y + collision_height = min_y
            # collision_y = min_y - collision_height
            # Et collision_y = y + sprite_height/2 - collision_height + collision_offset_y
            # Donc: y + sprite_height/2 - collision_height + collision_offset_y = min_y - collision_height
            # y + sprite_height/2 + collision_offset_y = min_y
            # y = min_y - sprite_height/2 - collision_offset_y
            self.y = min_y - self.sprite_height / 2 - self.collision_offset_y
            self.is_on_ground = True
            self.velocity_y = 0.0
            self._positioned = True
        else:
            # Si aucun bloc n'est trouvé (ou si y était défini), utiliser la méthode de chute progressive
            # On applique la gravité progressivement jusqu'à trouver un bloc
            max_frames = 60  # Limite de sécurité (1 seconde à 60 FPS)
            frame = 0

            while not self._positioned and frame < max_frames:
                frame += 1

                # Appliquer la gravité avec un dt plus grand pour accélérer le positionnement
                # Utiliser un dt de 0.016 (60 FPS) pour simuler plusieurs frames rapidement
                sim_dt = 0.016
                self.velocity_y += self.gravity * sim_dt
                if self.velocity_y > self.max_fall_speed:
                    self.velocity_y = self.max_fall_speed

                dy = self.velocity_y * sim_dt
                player_rect = self.get_collision_rect()

                # Pour le positionnement initial, utiliser la caméra calculée
                _, corrected_dy, is_on_ground = self.collision_system.resolve_collision(
                    player_rect, 0.0, dy, self, initial_camera_x
                )

                self.y += corrected_dy

                if is_on_ground:
                    self.is_on_ground = True
                    self.velocity_y = 0.0
                    self._positioned = True
                    break

            # Si on n'a pas trouvé de bloc, positionner à une hauteur par défaut
            if not self._positioned:
                self.y = 600.0  # Position par défaut
                self.is_on_ground = True
                self.velocity_y = 0.0
                self._positioned = True

    def update(self, dt: float, camera_x: float) -> None:
        """Met à jour le PNJ (gravité, collisions, animations, déplacements).
        
        La gravité s'applique en permanence au PNJ, même pendant les déplacements
        déclenchés par événements. Les collisions sont résolues à chaque frame pour
        maintenir le PNJ au sol ou gérer les chutes.

        Args:
            dt: Delta time en secondes
            camera_x: Position horizontale de la caméra
        """
        # Gérer le suivi du personnage principal (priorité sur les déplacements déclenchés par événements)
        if self._is_following_player and self._follow_player is not None:
            player = self._follow_player
            player_current_x = player.x
            
            # Calculer la position cible derrière le joueur (sans changer la direction immédiatement)
            if player_current_x < self._player_last_x:
                # Le joueur va à gauche, le PNJ doit être à droite du joueur
                target_x = player_current_x + self._follow_distance
            elif player_current_x > self._player_last_x:
                # Le joueur va à droite, le PNJ doit être à gauche du joueur
                target_x = player_current_x - self._follow_distance
            else:
                # Le joueur ne bouge pas, calculer la position cible en fonction de la position relative actuelle
                # Le PNJ doit toujours se rapprocher de sa position cible derrière le joueur
                # Déterminer de quel côté du joueur le PNJ doit être en fonction de sa position actuelle
                npc_to_player_distance = self.x - player_current_x
                
                if abs(npc_to_player_distance) < self._follow_distance:
                    # Le PNJ est trop proche ou à la bonne distance, se positionner derrière selon la dernière direction
                    # Si le PNJ est à gauche du joueur, se positionner à gauche (derrière si le joueur allait à droite)
                    # Si le PNJ est à droite du joueur, se positionner à droite (derrière si le joueur allait à gauche)
                    if npc_to_player_distance < 0:
                        # PNJ à gauche du joueur, se positionner à gauche (joueur allait probablement à droite)
                        target_x = player_current_x - self._follow_distance
                    else:
                        # PNJ à droite du joueur, se positionner à droite (joueur allait probablement à gauche)
                        target_x = player_current_x + self._follow_distance
                else:
                    # Le PNJ est loin, se rapprocher activement
                    # Calculer la position cible la plus proche derrière le joueur
                    target_x_left = player_current_x - self._follow_distance
                    target_x_right = player_current_x + self._follow_distance
                    
                    # Choisir la position cible la plus proche
                    distance_to_left = abs(self.x - target_x_left)
                    distance_to_right = abs(self.x - target_x_right)
                    
                    if distance_to_left < distance_to_right:
                        target_x = target_x_left
                    else:
                        target_x = target_x_right
            
            # Mettre à jour la position précédente du joueur
            self._player_last_x = player_current_x
            
            # Se déplacer vers la position cible (toujours, même si le joueur ne bouge pas)
            distance = target_x - self.x
            move_distance = self._follow_speed * dt
            
            if abs(distance) > 2.0:  # Tolérance de 2 pixels
                if abs(distance) < move_distance:
                    # On est proche, aller directement à la cible
                    self.x = target_x
                else:
                    # Se déplacer dans la direction appropriée
                    if distance > 0:
                        self.x += move_distance
                    else:
                        self.x -= move_distance
                
                # Mettre à jour la direction du PNJ en fonction de la direction de son mouvement
                # (pas en fonction de la direction du joueur, pour éviter que le PNJ se retourne immédiatement)
                if distance > 0:
                    # Le PNJ se déplace vers la droite
                    self.direction = "right"
                else:
                    # Le PNJ se déplace vers la gauche
                    self.direction = "left"
                
                # Gérer l'animation de suivi
                if self._follow_animation_row is not None and self._follow_animation_frames is not None:
                    # Utiliser l'animation de suivi spécifiée
                    anim_duration = 1.0 / 10.0  # 10 FPS par défaut pour l'animation de suivi
                    self.animation_timer += dt
                    frame_index = int((self.animation_timer / anim_duration) % self._follow_animation_frames)
                    self.current_frame = frame_index
                elif "walk" in self.animations:
                    # Utiliser l'animation walk si disponible
                    self._update_animation(dt)
        
        # Gérer le déplacement déclenché par événements (seulement si le PNJ ne suit pas le joueur)
        elif self._move_target_x is not None:
            # Calculer la distance restante
            distance = self._move_target_x - self.x
            move_distance = self._move_speed * dt
            
            # Vérifier si on a atteint la destination (tolérance de 2 pixels)
            if abs(distance) <= 2.0:
                # Arrêter le déplacement
                self.x = self._move_target_x
                self._move_target_x = None
                self._move_speed = 0.0
                
                # Restaurer l'animation originale
                if self._original_animation is not None:
                    self.current_animation = self._original_animation
                    self.current_frame = 0
                    self.animation_timer = 0.0
                    self._original_animation = None
                
                # Désactiver l'animation temporaire
                self._move_animation_row = None
                self._move_animation_frames = None
            else:
                # Se déplacer vers la cible
                if abs(distance) < move_distance:
                    # On est proche, aller directement à la cible
                    self.x = self._move_target_x
                else:
                    # Se déplacer dans la direction appropriée
                    if distance > 0:
                        self.x += move_distance
                    else:
                        self.x -= move_distance
                
                # Gérer l'animation temporaire si elle est activée
                if self._move_animation_row is not None and self._move_animation_frames is not None:
                    # Utiliser l'animation temporaire
                    # Calculer la frame basée sur le temps
                    anim_duration = 1.0 / 10.0  # 10 FPS par défaut pour l'animation de déplacement
                    self.animation_timer += dt
                    frame_index = int((self.animation_timer / anim_duration) % self._move_animation_frames)
                    self.current_frame = frame_index
        
        # Appliquer la gravité en permanence (même pendant les déplacements et le suivi)
        # Cela garantit que le PNJ reste au sol ou tombe s'il se déplace au-dessus d'un vide
        self._apply_gravity(dt, camera_x)

        # Mettre à jour l'animation (si pas d'animation temporaire de déplacement ou de suivi)
        if (self._move_target_x is None or (self._move_animation_row is None and self._move_animation_frames is None)) and \
           (not self._is_following_player or (self._follow_animation_row is None and self._follow_animation_frames is None)):
            self._update_animation(dt)

    def get_draw_command(self, camera_x: float) -> tuple[pygame.Surface, tuple[int, int]]:
        """Construit la commande de dessin pour le sprite courant en appliquant l'orientation."""
        # Déterminer la position du sprite dans le sprite sheet
        # Priorité à l'animation temporaire de téléportation magique si elle est active
        # (utilisée pendant le fade in de la téléportation)
        if self._magic_move_animation_row is not None:
            row = self._magic_move_animation_row
            if self._magic_move_animation_start is not None:
                col = self._magic_move_animation_start
            else:
                # Si animation_start n'est pas spécifié, utiliser current_frame ou 0
                col = self.current_frame if self.current_frame >= 0 else 0
        # Priorité à l'animation temporaire de suivi si elle est active
        elif self._is_following_player and self._follow_animation_row is not None and self._follow_animation_frames is not None:
            row = self._follow_animation_row
            col = self.current_frame % self._follow_animation_frames
        # Priorité à l'animation temporaire de déplacement si elle est active
        elif self._move_animation_row is not None and self._move_animation_frames is not None:
            row = self._move_animation_row
            col = self.current_frame % self._move_animation_frames
        elif self.current_animation and self.current_animation in self.animations:
            anim_config = self.animations[self.current_animation]
            row = anim_config.row
            col = self.current_frame
        else:
            row = 0
            col = 0

        # Récupérer le sprite avec l'orientation appropriée
        # Flip horizontal si direction == "left" (le sprite est inversé pour regarder vers la gauche)
        # Pas de flip si direction == "right" (le sprite est affiché tel quel pour regarder vers la droite)
        if self.direction == "left":
            sprite = self._get_flipped_sprite(row, col)
        elif self.direction == "right":
            sprite = self._get_sprite_at(row, col)
        else:
            # Par défaut, afficher le sprite tel quel
            sprite = self._get_sprite_at(row, col)

        # Calculer la position à l'écran en tenant compte de la caméra
        screen_x = self.x - camera_x
        screen_y = self.y

        # Aligner le bas du sprite affiché sur le bas du sprite natif (et donc sur la hitbox)
        bottom_y = screen_y + self.sprite_height / 2

        draw_x = round(screen_x - self.display_width / 2)
        draw_y = round(bottom_y - self.display_height)

        # Appliquer l'opacité si nécessaire
        if self.alpha < 255:
            sprite = sprite.copy()  # Créer une copie pour ne pas modifier l'original
            sprite.set_alpha(self.alpha)

        return sprite, (draw_x, draw_y)

    def draw(self, surface: pygame.Surface, camera_x: float) -> None:
        """Dessine le PNJ sur la surface."""
        surface.blits([self.get_draw_command(camera_x)], False)

    def get_name_draw_command(self, camera_x: float) -> Optional[tuple[pygame.Surface, tuple[int, int]]]:
        """Construit la commande de dessin pour le nom du PNJ."""
        if self.name_surface is None or self.name_rect is None:
            self._render_name()

        if self.name_surface is None or self.name_rect is None:
            return None

        # Calculer la position à l'écran en tenant compte de la caméra
        screen_x = self.x - camera_x
        screen_y = self.y

        name_x = round(screen_x - self.name_rect.width / 2)
        bottom_y = screen_y + self.sprite_height / 2
        top_of_sprite = bottom_y - self.display_height
        base_name_y = top_of_sprite - self.name_rect.height
        name_y = round(base_name_y + self.name_offset_y)

        return self.name_surface, (name_x, name_y)

    def draw_name(self, surface: pygame.Surface, camera_x: float) -> None:
        """Dessine le nom du PNJ au-dessus de sa tête."""
        command = self.get_name_draw_command(camera_x)
        if command is not None:
            surface.blits([command], False)

    def start_movement(
        self,
        target_x: float,
        speed: float,
        direction: Literal["left", "right"],
        animation_row: Optional[int] = None,
        animation_frames: Optional[int] = None,
    ) -> None:
        """Démarre un déplacement horizontal du PNJ vers une position cible.
        
        Cette méthode est appelée par le système de déclencheurs d'événements
        (voir spécification 11) pour déplacer le PNJ automatiquement.
        
        Args:
            target_x: Position X cible vers laquelle se déplacer
            speed: Vitesse de déplacement en pixels par seconde
            direction: Direction du déplacement ("left" ou "right")
            animation_row: Ligne du sprite sheet pour l'animation temporaire (optionnel)
            animation_frames: Nombre de frames pour l'animation temporaire (optionnel)
        """
        self._move_target_x = target_x
        self._move_speed = speed
        self.direction = direction
        
        # Sauvegarder l'animation actuelle pour la restaurer après le déplacement
        self._original_animation = self.current_animation
        
        # Configurer l'animation temporaire si spécifiée
        if animation_row is not None and animation_frames is not None:
            self._move_animation_row = animation_row
            self._move_animation_frames = animation_frames
            self.current_frame = 0
            self.animation_timer = 0.0
        else:
            self._move_animation_row = None
            self._move_animation_frames = None

    def is_moving(self) -> bool:
        """Vérifie si le PNJ est actuellement en déplacement.
        
        Returns:
            True si le PNJ est en déplacement, False sinon
        """
        return self._move_target_x is not None

    def start_following_player(
        self,
        player: "Player",
        follow_distance: float = 100.0,
        follow_speed: float = 200.0,
        animation_row: Optional[int] = None,
        animation_frames: Optional[int] = None,
    ) -> None:
        """Démarre le suivi du personnage principal.
        
        Le PNJ se positionne automatiquement derrière le joueur (à droite si le joueur
        va à gauche, à gauche si le joueur va à droite) et maintient une distance constante.
        La direction du PNJ est automatiquement gérée en fonction de la direction du joueur.
        
        Args:
            player: Instance du personnage principal à suivre (obligatoire)
            follow_distance: Distance horizontale à maintenir derrière le joueur en pixels (défaut: 100.0)
            follow_speed: Vitesse de déplacement lors du suivi en pixels par seconde (défaut: 200.0)
            animation_row: Ligne du sprite sheet pour l'animation de suivi (optionnel). Si non spécifié, utilise l'animation "walk" si disponible
            animation_frames: Nombre de frames pour l'animation de suivi (optionnel). Si non spécifié, utilise la configuration d'animation existante
        """
        self._is_following_player = True
        self._follow_player = player
        self._follow_distance = follow_distance
        self._follow_speed = follow_speed
        self._player_last_x = player.x
        
        # Sauvegarder l'animation actuelle pour la restaurer après l'arrêt du suivi
        self._original_animation = self.current_animation
        
        # Configurer l'animation de suivi
        if animation_row is not None and animation_frames is not None:
            # Utiliser l'animation spécifiée
            self._follow_animation_row = animation_row
            self._follow_animation_frames = animation_frames
            self.current_frame = 0
            self.animation_timer = 0.0
        elif "walk" in self.animations:
            # Utiliser l'animation "walk" si disponible
            walk_config = self.animations["walk"]
            self._follow_animation_row = walk_config.row
            self._follow_animation_frames = walk_config.num_frames
            self.current_animation = "walk"
            self.current_frame = 0
            self.animation_timer = 0.0
        else:
            # Conserver l'animation actuelle
            self._follow_animation_row = None
            self._follow_animation_frames = None
        
        # Arrêter tout déplacement en cours (le suivi a la priorité)
        self._move_target_x = None
        self._move_speed = 0.0

    def stop_following_player(self) -> None:
        """Arrête le suivi du personnage principal.
        
        Le PNJ reprend son comportement normal (animation idle, etc.).
        """
        self._is_following_player = False
        self._follow_player = None
        self._follow_distance = 100.0
        self._follow_speed = 200.0
        self._follow_animation_row = None
        self._follow_animation_frames = None
        self._player_last_x = 0.0
        
        # Restaurer l'animation originale
        if self._original_animation is not None:
            self.current_animation = self._original_animation
            self.current_frame = 0
            self.animation_timer = 0.0
            self._original_animation = None

    def is_following_player(self) -> bool:
        """Vérifie si le PNJ suit actuellement le personnage principal.
        
        Returns:
            True si le PNJ suit le joueur, False sinon
        """
        return self._is_following_player

    def get_dialogue_block_for_position(
        self, player_position: float
    ) -> Optional["DialogueBlockConfig"]:
        """Retourne le bloc de dialogue correspondant à la position du joueur donnée.

        La position est fournie en paramètre par le système (via le système de gestion
        de l'avancement dans le niveau, voir spécification 11) et n'est pas calculée
        par cette méthode. La méthode parcourt les blocs de dialogue dans l'ordre de
        définition et retourne le premier bloc dont la plage de position correspond.

        Args:
            player_position: Position horizontale du joueur dans le monde en pixels (fournie par le système via LevelProgressTracker.get_current_x())

        Returns:
            Configuration du bloc de dialogue correspondant, ou None si aucun bloc ne correspond
        """
        if not self.dialogue_blocks:
            return None

        for block in self.dialogue_blocks:
            if block.position_min <= player_position <= block.position_max:
                return block

        return None

    def get_dialogue_type_for_position(
        self, player_position: float
    ) -> Optional[Literal["normal", "quête", "discution", "ecoute", "regarder", "enseigner", "reflexion"]]:
        """Retourne le type de dialogue du bloc correspondant à la position du joueur donnée.

        Utilise `get_dialogue_block_for_position()` pour obtenir le bloc, puis retourne
        son `dialogue_type`. Cette méthode est utilisée par le système d'interaction
        pour déterminer quel indicateur afficher (voir spécification 2).

        Args:
            player_position: Position horizontale du joueur dans le monde en pixels (fournie par le système via LevelProgressTracker.get_current_x())

        Returns:
            Type de dialogue ("normal", "quête", "discution", "ecoute", "regarder", "enseigner" ou "reflexion"), ou None si aucun bloc ne correspond à la position
        """
        block = self.get_dialogue_block_for_position(player_position)
        if block is None:
            return None
        return block.dialogue_type

    def set_alpha(self, alpha: int) -> None:
        """Définit l'opacité du PNJ.
        
        Args:
            alpha: Opacité (0-255, 255 = complètement opaque)
        """
        self.alpha = max(0, min(255, alpha))

    def set_gravity_enabled(self, enabled: bool) -> None:
        """Active ou désactive la gravité pour le PNJ.
        
        Args:
            enabled: True pour activer la gravité, False pour la désactiver
        """
        self._gravity_enabled = enabled

    def set_collisions_enabled(self, enabled: bool) -> None:
        """Active ou désactive les collisions pour le PNJ.
        
        Args:
            enabled: True pour activer les collisions, False pour les désactiver
        """
        self._collisions_enabled = enabled

    def change_sprite_sheet(self, sprite_sheet_path: str) -> None:
        """Change le sprite sheet du PNJ.
        
        Args:
            sprite_sheet_path: Chemin vers le nouveau sprite sheet (relatif au répertoire du niveau ou absolu)
        
        Raises:
            FileNotFoundError: Si le fichier sprite sheet n'existe pas
        """
        from ..assets.preloader import _global_npc_sprite_sheet_cache
        
        sprite_path = Path(sprite_sheet_path)
        if not sprite_path.is_absolute():
            sprite_path = self.assets_root.parent / sprite_path
        
        sprite_path_key = str(sprite_path.resolve())
        
        # Vérifier d'abord le cache global
        if sprite_path_key in _global_npc_sprite_sheet_cache:
            self.sprite_sheet = _global_npc_sprite_sheet_cache[sprite_path_key]
        else:
            # Charger depuis le disque si pas en cache
            if not sprite_path.exists():
                raise FileNotFoundError(f"Sprite sheet introuvable: {sprite_path}")
            self.sprite_sheet = pygame.image.load(str(sprite_path)).convert_alpha()
        
        # Réinitialiser les caches
        self._frame_cache.clear()
        self._flipped_frame_cache.clear()
        self._scaled_frame_cache.clear()
        self._scaled_flipped_frame_cache.clear()
        
        # Recalculer les dimensions du sprite sheet
        self._sheet_columns = max(1, self.sprite_sheet.get_width() // self.sprite_width)
        self._sheet_rows = max(1, self.sprite_sheet.get_height() // self.sprite_height)
        
        logger.debug(
            "Sprite sheet changé pour NPC '%s': %s (columns=%d, rows=%d)",
            self.id,
            sprite_sheet_path,
            self._sheet_columns,
            self._sheet_rows,
        )

    def stop_movement(self) -> None:
        """Arrête le déplacement déclenché par événements."""
        self._move_target_x = None
        self._move_speed = 0.0
        self._move_animation_row = None
        self._move_animation_frames = None
        if self._original_animation is not None:
            self.current_animation = self._original_animation
            self.current_frame = 0
            self.animation_timer = 0.0
            self._original_animation = None


class DialogueState:
    """Gère l'état d'un dialogue en cours avec un PNJ.
    
    Cette classe gère l'affichage séquentiel des échanges d'un bloc de dialogue,
    en utilisant le système de bulles de dialogue (SpeechBubble) pour chaque échange.
    
    **Déclenchement d'événements** : Les événements associés à chaque échange sont déclenchés
    lorsque l'échange est affiché (dans `_create_bubble_for_exchange`), pas lors de la création
    du DialogueState. Cela permet de déclencher des événements à des moments précis de la conversation.
    """
    
    def __init__(
        self,
        npc: NPC,
        player: Player,
        dialogue_block: DialogueBlockConfig,
        event_system: Optional["EventTriggerSystem"] = None,
    ) -> None:
        """Initialise un état de dialogue.
        
        Args:
            npc: Le PNJ avec qui le dialogue a lieu
            player: Le joueur participant au dialogue
            dialogue_block: Le bloc de dialogue à afficher
            event_system: Système de déclencheurs d'événements (optionnel). Si fourni, les événements
                         référencés dans les échanges seront déclenchés lors de l'affichage de chaque échange.
        """
        self.npc = npc
        self.player = player
        self.dialogue_block = dialogue_block
        self.event_system = event_system
        self.current_exchange_index: int = 0
        self.current_bubble: Optional[SpeechBubble] = None
        self.is_active: bool = True
        self._screen_fade_triggered_from_dialogue: bool = False  # Flag pour suivre si un fondu a été déclenché depuis ce dialogue
        self._screen_fade_previous_phase: Optional[str] = None  # Phase précédente du fondu pour détecter les transitions
        
        # Calculer le chemin absolu vers le répertoire image
        # npc.assets_root est généralement le répertoire "sprite", donc le parent contient "image"
        image_assets_root = npc.assets_root.parent / "image"
        
        # Créer la première bulle
        if dialogue_block.exchanges:
            self._create_bubble_for_exchange(dialogue_block.exchanges[0], assets_root=image_assets_root)
    
    def update(self, camera_x: float, dt: float) -> None:
        """Met à jour l'état du dialogue (position de la bulle, animation du texte).
        
        Args:
            camera_x: Position horizontale de la caméra
            dt: Delta time en secondes
        """
        if self.current_bubble is not None:
            self.current_bubble.update(camera_x, dt)
        
        # Vérifier si un fondu déclenché depuis ce dialogue entre en phase fade_out
        # Si oui, passer automatiquement à l'échange suivant (avant le fade_out)
        if self._screen_fade_triggered_from_dialogue:
            if self.event_system is not None:
                # Obtenir la phase actuelle du fondu
                current_phase = self.event_system.get_screen_fade_phase()
                
                # Détecter la transition vers fade_out : phase précédente n'était pas fade_out, phase actuelle est fade_out
                if current_phase == "fade_out" and self._screen_fade_previous_phase != "fade_out":
                    # Le fondu vient d'entrer en phase fade_out, vérifier que le texte est complètement affiché
                    if self.current_bubble is not None and self.current_bubble._text_complete:
                        # Passer à l'échange suivant avant le fade_out (une seule fois)
                        # Vérifier qu'il y a encore des échanges à afficher
                        if self.current_exchange_index < len(self.dialogue_block.exchanges) - 1:
                            self._next_exchange()
                
                # Mettre à jour la phase précédente pour la prochaine frame
                self._screen_fade_previous_phase = current_phase
                
                # Si le fondu est terminé, réinitialiser
                if not self.event_system.has_active_screen_fade():
                    self._screen_fade_triggered_from_dialogue = False
                    self._screen_fade_previous_phase = None
    
    def handle_event(self, event: pygame.event.Event, camera_x: float) -> bool:
        """Gère les événements (clic n'importe où sur l'écran pour passer à l'échange suivant).
        
        Args:
            event: Événement pygame à traiter
            camera_x: Position horizontale de la caméra (non utilisée, conservée pour compatibilité)
        
        Returns:
            True si l'événement a été traité, False sinon
        
        Note:
            Le clic peut être effectué n'importe où sur l'écran, pas seulement sur la bulle.
            Si le texte n'est pas complètement affiché, le clic accélère l'affichage.
            Si le texte est complètement affiché, le clic passe à l'échange suivant.
            Le passage à l'échange suivant est bloqué si un événement sprite_move est en cours.
        """
        if self.current_bubble is None:
            return False
        
        # Vérifier si le texte est complètement affiché avant le clic
        text_was_complete = self.current_bubble._text_complete
        
        # Vérifier si c'est un clic (n'importe où sur l'écran)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if text_was_complete:
                # Le texte est complet, vérifier s'il y a des mouvements de sprites en cours
                if self.event_system is not None and self.event_system.has_active_sprite_movements():
                    # Un sprite_move est en cours, ignorer le clic
                    return False
                # Vérifier s'il y a un fondu au noir en cours
                if self.event_system is not None and self.event_system.has_active_screen_fade():
                    # Un screen_fade est en cours, ignorer le clic
                    return False
                # Aucun sprite_move ni screen_fade en cours, passer à l'échange suivant
                self._next_exchange()
                return True
            else:
                # Le texte n'est pas complet, accélérer l'affichage
                self.current_bubble.skip_animation()
                return True
        
        return False
    
    def draw(self, surface: pygame.Surface, camera_x: float) -> None:
        """Dessine la bulle de dialogue actuelle.
        
        Args:
            surface: Surface pygame sur laquelle dessiner
            camera_x: Position horizontale de la caméra
        """
        if self.current_bubble is not None:
            # Utiliser dt=0.0 car l'animation est gérée dans update()
            self.current_bubble.draw(surface, camera_x, dt=0.0)
    
    def is_complete(self) -> bool:
        """Vérifie si le dialogue est terminé (tous les échanges ont été affichés).
        
        Returns:
            True si le dialogue est terminé, False sinon
        """
        return not self.is_active or (
            self.current_exchange_index >= len(self.dialogue_block.exchanges)
            and (self.current_bubble is None or self.current_bubble._text_complete)
        )
    
    def has_position_constraint(self) -> bool:
        """Vérifie si l'échange actuel impose une contrainte de position.
        
        Returns:
            True si l'échange actuel contient un `set_x_position`, False sinon
        """
        if not self.is_active or self.current_exchange_index >= len(self.dialogue_block.exchanges):
            return False
        
        current_exchange = self.dialogue_block.exchanges[self.current_exchange_index]
        if current_exchange.player_animation is None:
            return False
        
        return current_exchange.player_animation.set_x_position is not None
    
    def get_constrained_x_position(self) -> Optional[float]:
        """Obtient la position X contrainte de l'échange actuel (en repère de rendu).
        
        Returns:
            La position X contrainte en repère de rendu si une contrainte est active,
            None sinon
        """
        if not self.has_position_constraint():
            return None
        
        current_exchange = self.dialogue_block.exchanges[self.current_exchange_index]
        if current_exchange.player_animation is None:
            return None
        
        set_x_position = current_exchange.player_animation.set_x_position
        if set_x_position is None:
            return None
        
        # Convertir du repère de conception vers le repère de rendu
        # Utilise les valeurs du module config pour s'adapter à la résolution de rendu
        render_width, render_height = get_render_size()
        scale_x, _ = compute_design_scale((render_width, render_height))
        return set_x_position * scale_x
    
    def _next_exchange(self) -> None:
        """Passe à l'échange suivant (appelé après un clic lorsque le texte est complet)."""
        # Arrêter l'animation de dialogue de l'échange actuel si elle existe
        if self.current_exchange_index < len(self.dialogue_block.exchanges):
            current_exchange = self.dialogue_block.exchanges[self.current_exchange_index]
            if current_exchange.player_animation is not None:
                self.player.stop_dialogue_animation()
        
        self.current_exchange_index += 1
        
        if self.current_exchange_index < len(self.dialogue_block.exchanges):
            # Créer la bulle pour le prochain échange
            # Utiliser le même chemin absolu que lors de la création de la première bulle
            image_assets_root = self.npc.assets_root.parent / "image"
            exchange = self.dialogue_block.exchanges[self.current_exchange_index]
            self._create_bubble_for_exchange(exchange, assets_root=image_assets_root)
        else:
            # Tous les échanges ont été affichés
            # Arrêter l'animation de dialogue si elle existe
            self.player.stop_dialogue_animation()
            self.current_bubble = None
            self.is_active = False
            # Réinitialiser les flags de fondu
            self._screen_fade_triggered_from_dialogue = False
            self._screen_fade_previous_phase = None
    
    def _create_bubble_for_exchange(self, exchange: DialogueExchangeConfig, assets_root: Optional[Path] = None) -> None:
        """Crée une bulle pour un échange donné.
        
        Args:
            exchange: Configuration de l'échange à afficher
            assets_root: Répertoire de base pour résoudre les chemins d'images relatifs (optionnel, par défaut Path("image"))
        """
        from ..ui.speech_bubble import SpeechBubble
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Déclencher les événements associés à cet échange si configurés
        if self.event_system is not None and exchange.trigger_events:
            for event_identifier in exchange.trigger_events:
                # Vérifier si l'événement est de type screen_fade avant de le déclencher
                event_type = self.event_system.get_event_type_by_identifier(event_identifier)
                if event_type == "screen_fade":
                    # Marquer le flag avant de déclencher l'événement
                    self._screen_fade_triggered_from_dialogue = True
                    self._screen_fade_previous_phase = None  # Réinitialiser pour détecter la transition vers fade_out
                
                # Déclencher l'événement
                self.event_system.trigger_event_by_identifier(event_identifier)
        
        # Ajouter les objets à l'inventaire si configurés
        if exchange.add_items and self.player.inventory is not None:
            for item_id, quantity in exchange.add_items.items():
                self.player.inventory.add_item(item_id, quantity, animated=True)
                logger.debug(
                    "Objet ajouté à l'inventaire via dialogue: item_id='%s', quantity=%d",
                    item_id,
                    quantity,
                )
        
        # Retirer les objets de l'inventaire si configurés
        if exchange.remove_items and self.player.inventory is not None:
            for item_id, quantity in exchange.remove_items.items():
                if self.player.inventory.has_item(item_id, quantity):
                    self.player.inventory.remove_item(item_id, quantity, animated=True)
                    logger.debug(
                        "Objet retiré de l'inventaire via dialogue: item_id='%s', quantity=%d",
                        item_id,
                        quantity,
                    )
                else:
                    logger.warning(
                        "Impossible de retirer l'objet '%s' (quantity=%d) via dialogue: quantité insuffisante",
                        item_id,
                        quantity,
                    )
        
        # Déterminer le personnage qui parle
        if exchange.speaker == "npc":
            character = self.npc
            side = "right"  # NPC parle à droite
        else:  # exchange.speaker == "player"
            character = self.player
            side = "left"  # Joueur parle à gauche
        
        # Utiliser les valeurs de l'échange (qui ont déjà les valeurs par défaut du bloc si non surchargées)
        font_size = exchange.font_size
        text_speed = exchange.text_speed
        
        # Utiliser assets_root fourni ou Path("image") par défaut pour les images de dialogue
        if assets_root is None:
            assets_root = Path("image")
        
        self.current_bubble = SpeechBubble(
            text=exchange.text,
            character=character,
            side=side,
            font_size=font_size,
            text_speed=text_speed,
            image_path=exchange.image_path,
            assets_root=assets_root,
        )
        
        # Déclencher l'animation du personnage principal si configurée
        # L'animation peut être déclenchée sur n'importe quel échange (même si le NPC parle)
        # pour montrer la réaction du joueur
        if exchange.player_animation is not None:
            self.player.start_dialogue_animation(
                sprite_sheet_path=exchange.player_animation.sprite_sheet_path,
                row=exchange.player_animation.row,
                num_frames=exchange.player_animation.num_frames,
                animation_speed=exchange.player_animation.animation_speed,
                animation_type=exchange.player_animation.animation_type,
                start_sprite=exchange.player_animation.start_sprite,
                offset_y=exchange.player_animation.offset_y,
                set_x_position=exchange.player_animation.set_x_position,
            )


def start_dialogue(
    npc: NPC,
    progress_tracker: LevelProgressTracker,
    event_system: Optional["EventTriggerSystem"] = None,
) -> Optional[DialogueState]:
    """Démarre un dialogue avec un PNJ en fonction de la position du joueur.
    
    Cette fonction obtient la position actuelle du joueur via le système de progression,
    sélectionne le bloc de dialogue approprié, et crée un DialogueState pour gérer l'affichage.
    
    Args:
        npc: Le PNJ avec qui démarrer le dialogue
        progress_tracker: Système de progression pour obtenir la position du joueur.
                         Doit être fourni (obligatoire).
        event_system: Système de déclencheurs d'événements (optionnel). Si fourni, les événements
                     référencés dans les échanges seront déclenchés lors de l'affichage de chaque échange.
    
    Returns:
        DialogueState si un bloc de dialogue correspond à la position, None sinon
    
    Note:
        Les événements référencés dans `trigger_events` de chaque échange sont déclenchés
        lorsque l'échange est affiché (dans `DialogueState._create_bubble_for_exchange`),
        pas lors du lancement du dialogue. Cela permet de déclencher des événements à des
        moments précis de la conversation. Si un événement n'existe pas ou a déjà été déclenché,
        il est ignoré silencieusement.
    """
    # Import conditionnel pour éviter les imports circulaires
    if not TYPE_CHECKING:
        from ..game.events import EventTriggerSystem
    
    # Obtenir la position actuelle du joueur
    # Utiliser current_x directement (float) au lieu de get_current_x() (int arrondi)
    # pour une précision maximale dans la sélection du bloc
    player_position = progress_tracker.current_x
    
    # Obtenir le bloc de dialogue approprié
    dialogue_block = npc.get_dialogue_block_for_position(player_position)
    
    if dialogue_block is None:
        return None
    
    # Obtenir le joueur depuis le progress_tracker
    player = progress_tracker.player
    
    # Créer et retourner l'état du dialogue (event_system est passé pour déclencher les événements lors de l'affichage des échanges)
    return DialogueState(npc, player, dialogue_block, event_system)

