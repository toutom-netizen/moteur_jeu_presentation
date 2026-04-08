"""Module de gestion du personnage principal."""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Optional, Tuple

import pygame

if TYPE_CHECKING:
    from ..inventory.config import InventoryItemConfig
    from ..particles import ParticleSystem
    from ..rendering.camera_zoom import CameraZoomController
    from ..stats.config import PlayerStatsConfig

from .entity import Entity
from .player_level_manager import (
    DEFAULT_PLAYER_LEVEL,
    MissingPlayerAssetError,
    PlayerLevelManager,
)
from ..rendering.config import compute_design_scale, get_render_size

# Import conditionnel pour éviter les dépendances circulaires
try:
    from ..inventory import Inventory
except ImportError:
    Inventory = None  # type: ignore


class Player(Entity):
    """Représente le personnage principal du jeu."""

    # Mapping des lignes du sprite sheet selon spécification utilisateur
    DIRECTION_TO_ROW = {
        "left": 1,  # Ligne 2 (index 1)
        "right": 3,  # Ligne 4 (index 3)
    }

    # Mapping des lignes du sprite sheet de saut selon spécification utilisateur
    JUMP_DIRECTION_TO_ROW = {
        "left": 1,  # Ligne 2 (index 1)
        "right": 3,  # Ligne 4 (index 3)
    }

    # Mapping des lignes du sprite sheet de grimpe selon spécification utilisateur
    CLIMB_DIRECTION_TO_ROW = {
        "left": 1,  # Ligne 2 (index 1)
        "right": 3,  # Ligne 4 (index 3)
    }

    WALK_SHEET_NAME = "walk.png"
    JUMP_SHEET_NAME = "jump.png"
    CLIMB_SHEET_NAME = "climb.png"
    
    # Constantes de configuration pour l'animation de confetti
    CONFETTI_EMISSION_INTERVAL: float = 0.2  # Intervalle entre chaque émission en secondes
    CONFETTI_STOP_BEFORE_END: float = 1.0  # Durée avant la fin où l'émission s'arrête en secondes
    CONFETTI_COUNT_PER_EMISSION: int = 60  # Nombre de particules par émission (doublé pour plus d'effet)
    CONFETTI_HORIZONTAL_OFFSET: float = 80.0  # Offset horizontal en pixels pour déplacer les confettis plus loin à gauche et à droite
    CONFETTI_CONE_SPREAD: float = math.pi / 6  # Dispersion du cône en radians (30°)
    CONFETTI_LEFT_CONE_ANGLE: float = -3 * math.pi / 4  # Angle de direction pour le coin haut gauche (-135°)
    CONFETTI_RIGHT_CONE_ANGLE: float = -math.pi / 4  # Angle de direction pour le coin haut droit (-45°)
    
    # Constantes de configuration pour l'animation de transition de niveau
    DEFAULT_LEVEL_TRANSITION_ZOOM_IN_DURATION = 1.0  # secondes - durée de la phase de zoom avant
    DEFAULT_LEVEL_TRANSITION_ZOOM_PERCENT = 230.0  # pourcentage de zoom (230% = facteur 2.3)
    LEVEL_TRANSITION_TEXT_SIZE = 72  # pixels (dans le repère de conception 1920x1080)
    LEVEL_TRANSITION_IMPROVEMENT_TEXT_SIZE = 40  # pixels (dans le repère de conception 1920x1080)
    LEVEL_TRANSITION_TEXT_SPACING = 20  # pixels - espacement entre le texte principal et le texte d'amélioration
    LEVEL_TRANSITION_IMPROVEMENT_TEXT_COLOR = (64, 64, 64)  # Gris foncé
    LEVEL_TRANSITION_FRAME_PADDING_X = 50  # pixels - padding horizontal du cadre
    LEVEL_TRANSITION_FRAME_PADDING_Y = 25  # pixels - padding vertical du cadre
    LEVEL_TRANSITION_FRAME_BORDER_THICKNESS = 5  # pixels - épaisseur de la bordure
    LEVEL_TRANSITION_FRAME_CORNER_RADIUS = 18  # pixels - rayon des coins arrondis
    LEVEL_TRANSITION_TEXT_COLOR = (0, 0, 0)  # Noir
    LEVEL_TRANSITION_FRAME_BACKGROUND_COLOR = (255, 255, 255)  # Blanc
    LEVEL_TRANSITION_FRAME_BORDER_COLOR = (0, 0, 0)  # Noir

    def __init__(
        self,
        x: float,
        y: float,
        sprite_sheet_path: Optional[str] = None,
        sprite_width: int = 64,
        sprite_height: int = 64,
        animation_speed: float = 10.0,
        sprite_scale: float = 2.0,
        jump_sprite_sheet_path: Optional[str] = None,
        player_level: int = DEFAULT_PLAYER_LEVEL,
        assets_root: Optional[Path] = None,
        stats_config: Optional["PlayerStatsConfig"] = None,
        inventory_config: Optional["InventoryItemConfig"] = None,
        font_path: Optional[str] = None,
        font_size: int = 36,
        name_color: Tuple[int, int, int] = (255, 255, 255),
        name_outline_color: Tuple[int, int, int] = (0, 0, 0),
        name_offset_y: float = -4.0,
    ) -> None:
        """Initialise le personnage principal.

        Args:
            x: Position horizontale initiale
            y: Position verticale initiale
            sprite_sheet_path: Chemin vers le fichier sprite sheet (optionnel, utilisé pour compatibilité)
            sprite_width: Largeur d'un sprite individuel dans le sprite sheet (64 pixels)
            sprite_height: Hauteur d'un sprite individuel dans le sprite sheet (64 pixels)
            animation_speed: Vitesse d'animation en frames par seconde
            sprite_scale: Facteur d'échelle pour l'affichage du sprite (défaut: 2.0 = 200%, double la taille)
            jump_sprite_sheet_path: Chemin vers le fichier sprite sheet de saut (optionnel)
            player_level: Niveau initial du personnage (1 à 5)
            assets_root: Répertoire racine des assets des niveaux (`sprite/personnage` par défaut)
            stats_config: Configuration des caractéristiques du personnage (obligatoire) ; fournit display_name
            inventory_config: Configuration des objets d'inventaire (optionnel)
            font_path: Chemin vers la police à utiliser pour le nom affiché (optionnel)
            font_size: Taille de la police en pixels (défaut: 36 pour meilleure lisibilité)
            name_color: Couleur du texte (défaut: blanc)
            name_outline_color: Couleur du contour du texte (défaut: noir)
            name_offset_y: Offset vertical pour placer le nom au-dessus du sprite (défaut: -12)
        """
        if stats_config is None:
            raise ValueError(
                "Player requiert stats_config : chargez config/player_stats.toml via PlayerStatsLoader "
                "(clé racine 'display_name' obligatoire et non vide)."
            )
        # Initialiser la classe de base
        super().__init__(x, y, sprite_width, sprite_height)
        
        self.animation_speed = animation_speed
        # Optimisation : pré-calculer frame_duration pour éviter la division à chaque frame
        self._frame_duration = 1.0 / animation_speed if animation_speed > 0 else 0.0

        # Calculer les facteurs d'échelle tôt pour pouvoir initialiser les vitesses
        render_width, render_height = get_render_size()
        scale_x, scale_y = compute_design_scale((render_width, render_height))
        self._design_scale_x = scale_x
        self._design_scale_y = scale_y
        self._render_width = render_width
        
        # IMPORTANT : Convertir les vitesses du repère de conception (1920x1080) vers le repère de rendu (1280x720)
        # Les vitesses sont définies dans le repère de conception et doivent être ajustées selon le ratio
        # pour conserver les vitesses actuelles (250.0, -400.0, 200.0, 800.0, 500.0)
        # Vitesse de base (mouvement horizontal) : multipliée par scale_x
        base_speed_design = 375.0  # Vitesse de base dans le repère de conception (375.0 * 2/3 = 250.0)
        self._base_speed = base_speed_design * scale_x
        self.speed = self._base_speed  # Vitesse actuelle (peut être modifiée par les stats)
        
        # Gravité et vitesse de chute (mouvement vertical) : multipliées par scale_y
        gravity_design = 1200.0  # Gravité dans le repère de conception (1200.0 * 2/3 = 800.0)
        max_fall_speed_design = 750.0  # Vitesse de chute max dans le repère de conception (750.0 * 2/3 = 500.0)
        self.gravity = gravity_design * scale_y
        self.max_fall_speed = max_fall_speed_design * scale_y

        # Gestion du niveau et des assets associés
        self._project_root = Path(__file__).parent.parent.parent.parent
        self._assets_root = self._resolve_assets_root(assets_root)
        self.level_manager = PlayerLevelManager(self._assets_root, player_level, stats_config)

        # Mettre à jour les stats après l'initialisation du level_manager
        self._update_stats()

        self._double_jump_unlock_level = stats_config.double_jump_unlock_level

        self._walk_override_path = self._coerce_to_path(sprite_sheet_path) if sprite_sheet_path else None
        if jump_sprite_sheet_path is None and self._walk_override_path is not None:
            jump_sprite_sheet_path = str((self._walk_override_path.parent / self.JUMP_SHEET_NAME))
        self._jump_override_path = (
            self._coerce_to_path(jump_sprite_sheet_path) if jump_sprite_sheet_path else None
        )

        # Dimensions des sprites de saut (identiques à ceux de marche par défaut)
        self.jump_sprite_width = sprite_width
        self.jump_sprite_height = sprite_height

        # Facteur d'échelle pour l'affichage des sprites
        self.sprite_scale = sprite_scale
        # Dimensions d'affichage (calculées à partir de la taille du sprite sheet et du facteur d'échelle)
        # IMPORTANT : Le sprite_scale est appliqué DANS le repère de conception (1920x1080),
        # puis on convertit le résultat vers la résolution interne (1280x720)
        # (scale_x et scale_y sont déjà calculés plus haut)
        # Étape 1 : Appliquer le sprite_scale dans le repère 1920x1080
        scaled_width_in_design = sprite_width * sprite_scale
        scaled_height_in_design = sprite_height * sprite_scale
        # Étape 2 : Convertir vers la résolution interne 1280x720
        self.display_width = int(scaled_width_in_design * scale_x)
        self.display_height = int(scaled_height_in_design * scale_y)

        # Adapter la hitbox à la taille affichée
        self._update_collision_dimensions_for_display()

        # Cache pour les sprites extraits (évite les extractions répétées)
        # IMPORTANT: Initialiser AVANT _reload_assets() car cette méthode peut les utiliser
        # Clé: (row, col) pour les sprites de marche (taille native)
        self._walk_frame_cache: dict[tuple[int, int], pygame.Surface] = {}
        # Clé: (row, col) pour les sprites de marche redimensionnés
        self._scaled_walk_frame_cache: dict[tuple[int, int, int, int], pygame.Surface] = {}
        # Clé: (row, col) pour les sprites de saut (taille native)
        self._jump_frame_cache: dict[tuple[int, int], pygame.Surface] = {}
        # Clé: (row, col) pour les sprites de saut redimensionnés
        self._scaled_jump_frame_cache: dict[tuple[int, int, int, int], pygame.Surface] = {}
        # Clé: (row, col) pour les sprites de grimpe (taille native)
        self._climb_frame_cache: dict[tuple[int, int], pygame.Surface] = {}
        # Clé: (row, col) pour les sprites de grimpe redimensionnés
        self._scaled_climb_frame_cache: dict[tuple[int, int, int, int], pygame.Surface] = {}
        # Clé: (row, col) pour les sprites d'animation de dialogue (taille native)
        self._dialogue_frame_cache: dict[tuple[int, int], pygame.Surface] = {}
        # Clé: (row, col) pour les sprites d'animation de dialogue redimensionnés
        self._scaled_dialogue_frame_cache: dict[tuple[int, int, int, int], pygame.Surface] = {}

        # Charger les assets associés au niveau actuel
        self._reload_assets()

        # Propriétés de saut
        jump_velocity_design = -600.0  # Vitesse initiale de saut dans le repère de conception (-600.0 * 2/3 = -400.0)
        self.jump_velocity: float = jump_velocity_design * scale_y  # Convertie vers le repère de rendu
        self.is_jumping: bool = False
        self.jump_frame: int = 0
        self.jump_animation_timer: float = 0.0
        self.jump_animation_speed: float = 12.0  # FPS
        # Optimisation : pré-calculer jump_frame_duration pour éviter la division à chaque frame
        self._jump_frame_duration = 1.0 / self.jump_animation_speed if self.jump_animation_speed > 0 else 0.0
        self.can_jump: bool = True
        self._was_on_ground: bool = False  # Pour détecter l'atterrissage
        # Propriétés pour le double saut (seuil : player_stats.toml double_jump_unlock_level, défaut 3)
        self._jump_key_pressed: bool = False  # Pour détecter le relâchement de la touche (double saut)
        self._has_double_jump: bool = False  # Indique si le double saut est disponible
        self._double_jump_used: bool = False  # Indique si le double saut a été utilisé

        # Propriétés de grimpe
        self.is_on_climbable: bool = False  # Indique si le personnage est sur un bloc grimpable
        climb_speed_design = 300.0  # Vitesse de grimpe dans le repère de conception (300.0 * 2/3 = 200.0)
        self.climb_speed: float = climb_speed_design * scale_y  # Convertie vers le repère de rendu
        self.is_climbing: bool = False  # Indique si le personnage est en train de grimper
        self.climb_frame: int = 0
        self.climb_animation_timer: float = 0.0
        self.climb_animation_speed: float = 10.0  # FPS
        # Optimisation : pré-calculer climb_frame_duration pour éviter la division à chaque frame
        self._climb_frame_duration = 1.0 / self.climb_animation_speed if self.climb_animation_speed > 0 else 0.0

        # État de l'animation
        self.current_direction: str = "right"  # Direction par défaut
        self.current_frame: int = 0
        self.animation_timer: float = 0.0
        self.is_moving: bool = False

        # Nombre de frames par direction (8 colonnes)
        self.num_frames = 8

        # Propriétés pour l'animation de dialogue
        self._dialogue_animation_active: bool = False
        self._dialogue_animation_sprite_sheet: Optional[pygame.Surface] = None
        self._dialogue_animation_row: int = 0
        self._dialogue_animation_num_frames: int = 0
        self._dialogue_animation_speed: float = 10.0
        self._dialogue_animation_type: str = "simple"
        self._dialogue_animation_frame: int = 0
        self._dialogue_animation_timer: float = 0.0
        self._dialogue_animation_direction: int = 1  # 1 = avant, -1 = arrière (pour pingpong)
        self._dialogue_animation_start_sprite: int = 0
        self._dialogue_animation_offset_y: float = 0.0
        self._saved_direction: Optional[str] = None
        self._saved_is_moving: bool = False
        self._camera_snap_requested: bool = False

        # Propriétés pour l'affichage du nom (display_name dans player_stats.toml)
        self.name = stats_config.display_name
        self.name_color = name_color
        self.name_outline_color = name_outline_color
        self.name_offset_y = name_offset_y
        self.name_surface: Optional[pygame.Surface] = None
        self.name_rect: Optional[pygame.Rect] = None

        # Propriétés pour l'affichage du level up
        self.level_up_active: bool = False
        self.level_up_text: str = "level up (press u)"
        self.level_up_blink_timer: float = 0.0
        self.level_up_blink_speed: float = 0.5  # Clignote toutes les 0.5 secondes
        self.level_up_visible: bool = True

        # Propriétés pour l'animation de transition de niveau
        self.level_transition_active: bool = False
        self.level_transition_phase: Literal["zoom_in", "display", "zoom_out", "none"] = "none"
        self.level_transition_zoom_in_timer: float = 0.0
        self.level_transition_zoom_in_duration: float = 1.0  # Durée de la phase de zoom avant en secondes
        self.level_transition_timer: float = 0.0
        self.level_transition_duration: float = 1.5  # Durée de la phase d'affichage en secondes
        self.level_transition_zoom_out_timer: float = 0.0
        self.level_transition_zoom_out_duration: float = 1.0  # Durée de la phase de reset du zoom en secondes
        self.level_transition_switch_interval: float = 0.2  # Intervalle entre chaque changement de sprite en secondes
        self.level_transition_switch_timer: float = 0.0
        self.level_transition_old_level: int = 1
        self.level_transition_new_level: int = 1
        self.level_transition_showing_old: bool = True
        self.level_transition_old_sprite_sheet: Optional[pygame.Surface] = None
        self.level_transition_text_surface: Optional[pygame.Surface] = None
        self.level_transition_camera_zoom_controller: Optional["CameraZoomController"] = None
        self.level_transition_improvement_message: Optional[str] = None  # Phrase d'amélioration pour le nouveau niveau

        # Convertir la taille de police du repère de conception (1920x1080) vers la résolution interne (1280x720)
        render_width, render_height = get_render_size()
        _, scale_y = compute_design_scale((render_width, render_height))
        converted_font_size = int(font_size * scale_y)
        
        # Charger la police pour le prénom avec la taille convertie
        self.font = self._load_font(font_path, converted_font_size)

        # Rendre le prénom une première fois
        self._render_name()

        # Initialiser l'inventaire
        if Inventory is not None:
            self.inventory = Inventory(item_config=inventory_config)
        else:
            self.inventory = None  # type: ignore
        
        # Référence au système de particules global (optionnel, nécessaire pour l'animation de confetti)
        self.particle_system: Optional["ParticleSystem"] = None
        
        # Propriétés pour gérer l'émission de confettis pendant l'animation de transition
        self._confetti_emission_timer: float = 0.0
        self._confetti_last_emission_time: float = 0.0

    def update(self, dt: float, camera_x: float = 0.0, keys: Optional[pygame.key.ScancodeWrapper] = None, has_position_constraint: bool = False) -> None:
        """Met à jour la position et l'animation du personnage.

        Args:
            dt: Delta time en secondes
            camera_x: Position horizontale de la caméra (non utilisée pour le joueur)
            keys: Objet ScancodeWrapper retourné par pygame.key.get_pressed()
            has_position_constraint: Si True, bloque les animations de mouvement (pour les dialogues avec set_x_position)
        """
        if keys is None:
            keys = pygame.key.get_pressed()
        # Gérer l'input de saut
        self._handle_jump_input(keys)

        # Gérer le mouvement (pour l'animation uniquement)
        self._handle_movement(keys, dt, has_position_constraint)

        # Mettre à jour les animations
        self._update_animation(dt)
        self._update_climb_animation(dt)
        self._update_jump_animation(dt)
        self._update_level_up_animation(dt)
        self._update_level_transition(dt, camera_x)

        # Gérer la fin du saut : détecter l'atterrissage (passage de False à True pour is_on_ground)
        # On ne met pas is_jumping à False si le personnage est au sol au moment du saut,
        # mais seulement s'il vient d'atterrir (était en l'air et est maintenant au sol)
        if self.is_jumping and self.is_on_ground and not self._was_on_ground:
            # Le personnage vient d'atterrir
            self.is_jumping = False
            self.can_jump = True
            self.jump_frame = 0
            self.jump_animation_timer = 0.0
            # Réinitialiser les flags de double saut
            self._jump_key_pressed = False
            self._has_double_jump = False
            self._double_jump_used = False

        # Mettre à jour le flag pour la prochaine frame
        self._was_on_ground = self.is_on_ground

    def get_draw_command(self, camera_x: float) -> tuple[pygame.Surface, tuple[int, int]]:
        """Construit la commande de dessin pour le sprite courant."""
        sprite = self._get_current_sprite()

        # Calculer la position à l'écran en tenant compte de la caméra
        screen_x = self.x - camera_x
        screen_y = self.y
        if self._dialogue_animation_active:
            screen_y += self._dialogue_animation_offset_y

        # Aligner le bas du sprite affiché sur le bas du sprite natif (et donc sur la hitbox)
        bottom_y = screen_y + self.sprite_height / 2

        draw_x = round(screen_x - self.display_width / 2)
        draw_y = round(bottom_y - self.display_height)

        return sprite, (draw_x, draw_y)

    def draw(self, surface: pygame.Surface, camera_x: float) -> None:
        """Dessine le personnage sur la surface."""
        surface.blits([self.get_draw_command(camera_x)], False)

    def _get_current_sprite(self) -> pygame.Surface:
        """Récupère le sprite actuel à afficher.

        Returns:
            Surface pygame contenant le sprite actuel
        """
        # Si une animation de transition de niveau est active, alterner entre l'ancien et le nouveau niveau
        if self.level_transition_active:
            row = self.DIRECTION_TO_ROW.get(self.current_direction, 3)
            if self.level_transition_showing_old and self.level_transition_old_sprite_sheet is not None:
                # Afficher le sprite de l'ancien niveau
                sprite = self._extract_sprite(
                    self.level_transition_old_sprite_sheet,
                    self.sprite_width,
                    self.sprite_height,
                    row,
                    self.current_frame
                )
                # Redimensionner si nécessaire
                if self.sprite_scale != 1.0:
                    sprite = pygame.transform.smoothscale(
                        sprite, (int(self.display_width), int(self.display_height))
                    )
                    sprite = sprite.convert_alpha()
                return sprite
            else:
                # Afficher le sprite du nouveau niveau (comportement normal)
                return self._get_sprite_at(row, self.current_frame)
        
        # Si une animation de dialogue est active, utiliser cette animation
        if self._dialogue_animation_active and self._dialogue_animation_sprite_sheet is not None:
            return self._get_dialogue_sprite_at(self._dialogue_animation_row, self._dialogue_animation_frame)
        
        # Si on est en train de grimper, utiliser l'animation de grimpe
        if self.is_climbing:
            climb_sprite = self._get_climb_sprite()
            if climb_sprite is not None:
                return climb_sprite
        
        # Si on est en saut, utiliser l'animation de saut
        jump_sprite = self._get_jump_sprite()
        if jump_sprite is not None:
            return jump_sprite

        # Sinon, utiliser l'animation de marche/idle normale
        row = self.DIRECTION_TO_ROW.get(self.current_direction, 3)
        return self._get_sprite_at(row, self.current_frame)

    def _extract_sprite(
        self,
        sheet: pygame.Surface,
        sprite_width: int,
        sprite_height: int,
        row: int,
        col: int,
    ) -> pygame.Surface:
        """Extrait une frame depuis un sprite sheet en toute sécurité.

        Cette méthode vérifie que le rectangle d'extraction reste dans les limites du sprite sheet
        pour éviter de retourner une surface vide ou transparente lorsque le nombre de frames réelles
        diffère de celui attendu.
        """
        sheet_width = sheet.get_width()
        sheet_height = sheet.get_height()

        if sheet_width <= 0 or sheet_height <= 0:
            return pygame.Surface((sprite_width, sprite_height), pygame.SRCALPHA)

        x = col * sprite_width
        y = row * sprite_height

        # S'assurer que le point d'origine reste dans les limites du sprite sheet
        max_x = max(sheet_width - sprite_width, 0)
        max_y = max(sheet_height - sprite_height, 0)
        x = max(0, min(x, max_x))
        y = max(0, min(y, max_y))

        # Ajuster la taille du rectangle si le sprite sheet est plus petit que prévu
        rect_width = min(sprite_width, sheet_width - x)
        rect_height = min(sprite_height, sheet_height - y)

        if rect_width <= 0 or rect_height <= 0:
            return pygame.Surface((sprite_width, sprite_height), pygame.SRCALPHA)

        rect = pygame.Rect(x, y, rect_width, rect_height)

        try:
            sprite = sheet.subsurface(rect).copy()
        except (ValueError, pygame.error):
            return pygame.Surface((sprite_width, sprite_height), pygame.SRCALPHA)

        if sprite.get_width() != sprite_width or sprite.get_height() != sprite_height:
            resized = pygame.Surface((sprite_width, sprite_height), pygame.SRCALPHA)
            resized.blit(sprite, (0, 0))
            sprite = resized

        return sprite.convert_alpha()

    def _get_sprite_at(self, row: int, col: int) -> pygame.Surface:
        """Extrait un sprite à la position (row, col) du sprite sheet (avec cache).
        
        Args:
            row: Index de la ligne (0-based)
            col: Index de la colonne (0-based)
            
        Returns:
            Surface pygame contenant le sprite extrait (depuis le cache si disponible)
        """
        # Vérifier d'abord le cache global des sprites redimensionnés (préchargement)
        from ..assets.preloader import _global_player_scaled_sprite_cache
        
        if self.sprite_scale != 1.0:
            global_cache_key = (
                self.player_level, "walk", row, col,
                int(self.display_width), int(self.display_height)
            )
            if global_cache_key in _global_player_scaled_sprite_cache:
                return _global_player_scaled_sprite_cache[global_cache_key]
        
        # Sinon, utiliser le cache local ou extraire
        cache_key = (row, col)
        
        # Vérifier le cache local (mais on doit quand même redimensionner)
        # Note: Le cache stocke les sprites non redimensionnés, on les redimensionne à la volée
        if cache_key in self._walk_frame_cache:
            sprite = self._walk_frame_cache[cache_key]
        else:
            sprite = self._extract_sprite(
                self.sprite_sheet, self.sprite_width, self.sprite_height, row, col
            )
            self._walk_frame_cache[cache_key] = sprite

        if self.sprite_scale == 1.0:
            return sprite

        # Vérifier le cache local des sprites redimensionnés
        scaled_key = (row, col, int(self.display_width), int(self.display_height))
        if scaled_key in self._scaled_walk_frame_cache:
            return self._scaled_walk_frame_cache[scaled_key]

        # OPTIMISATION: Éviter smoothscale si la taille cible est identique à la taille originale
        target_size = (int(self.display_width), int(self.display_height))
        if sprite.get_size() == target_size:
            # Pas besoin de redimensionner, mettre en cache directement
            scaled_sprite = sprite.convert_alpha()
            self._scaled_walk_frame_cache[scaled_key] = scaled_sprite
            return scaled_sprite

        # Redimensionner et mettre en cache local
        scaled_sprite = pygame.transform.smoothscale(
            sprite, target_size
        )
        scaled_sprite = scaled_sprite.convert_alpha()
        self._scaled_walk_frame_cache[scaled_key] = scaled_sprite
        return scaled_sprite

    def _update_animation(self, dt: float) -> None:
        """Met à jour l'animation du personnage.

        Args:
            dt: Delta time en secondes
        """
        # Si une animation de dialogue est active, mettre à jour cette animation
        if self._dialogue_animation_active:
            self._update_dialogue_animation(dt)
            return
        
        # Sinon, mettre à jour l'animation normale
        if self.is_moving:
            # Incrémenter le timer d'animation
            self.animation_timer += dt

            # Optimisation : utiliser frame_duration pré-calculé au lieu de division à chaque frame
            # Avancer à la frame suivante si nécessaire
            if self.animation_timer >= self._frame_duration:
                self.current_frame = (self.current_frame + 1) % self.num_frames
                self.animation_timer = 0.0
        else:
            # État idle : afficher la première frame
            self.current_frame = 0
            self.animation_timer = 0.0

    def _handle_movement(self, keys: pygame.key.ScancodeWrapper, dt: float, has_position_constraint: bool = False) -> None:
        """Gère le mouvement du personnage (pour l'animation uniquement).

        Note: Le mouvement réel est maintenant géré par le système de collisions dans main.py.
        Si level_transition_active est True, cette méthode retourne immédiatement sans traiter
        les inputs pour bloquer le personnage pendant la transition de niveau.

        Args:
            keys: Objet ScancodeWrapper retourné par pygame.key.get_pressed()
            dt: Delta time en secondes
            has_position_constraint: Si True, bloque les animations de mouvement (pour les dialogues avec set_x_position)
        """
        # Blocage complet pendant la transition de niveau
        if self.level_transition_active:
            return  # Le personnage ne bouge pas pendant la transition
        
        # Blocage des animations de mouvement si une contrainte de position est active
        if has_position_constraint:
            self.is_moving = False
            return
        
        # Détecter les touches de mouvement pour l'animation
        move_left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        move_right = keys[pygame.K_RIGHT] or keys[pygame.K_d]

        # Mettre à jour la direction et l'animation
        if move_left:
            if self.current_direction != "left":
                self.current_direction = "left"
                self.current_frame = 0  # Réinitialiser l'animation
                self.animation_timer = 0.0
            self.is_moving = True
        elif move_right:
            if self.current_direction != "right":
                self.current_direction = "right"
                self.current_frame = 0  # Réinitialiser l'animation
                self.animation_timer = 0.0
            self.is_moving = True
        else:
            self.is_moving = False


    @property
    def player_level(self) -> int:
        """Retourne le niveau courant du personnage."""

        return self.level_manager.level

    @property
    def max_player_level(self) -> int:
        """Niveau maximum (``max_level`` dans ``player_stats.toml``, ou 5 sans stats)."""
        return self.level_manager.max_player_level

    def set_level(self, level: int) -> None:
        """Met à jour le niveau du personnage et recharge les assets associés."""
        self.level_manager.set_level(level)
        self._reload_assets()
        # Mettre à jour les stats après changement de niveau
        self._update_stats()
        # Réinitialiser les animations pour éviter les incohérences visuelles
        self.current_frame = 0
        self.animation_timer = 0.0
        self.jump_frame = 0
        self.jump_animation_timer = 0.0
    
    def set_particle_system(self, particle_system: "ParticleSystem") -> None:
        """Définit la référence au système de particules global.
        
        Args:
            particle_system: Référence au système de particules global
        """
        self.particle_system = particle_system
        # Passer aussi la référence à l'inventaire si disponible
        if self.inventory is not None:
            self.inventory.set_particle_system(particle_system)
    
    def _trigger_confetti_celebration(self) -> None:
        """Déclenche l'animation de confetti pour célébrer le passage de niveau."""
        if self.particle_system is None:
            return  # Pas de système de particules disponible, ignorer silencieusement
        
        from moteur_jeu_presentation.particles import create_confetti_config
        
        # Obtenir la position du personnage dans le monde
        # Player hérite de Entity qui utilise self.x et self.y directement
        world_x = self.x
        world_y = self.y
        
        # Créer la configuration de confetti
        config = create_confetti_config(
            count=50,
            speed=400.0,
            lifetime=2.5,
            size=12,
        )
        
        # Créer l'effet de particules
        self.particle_system.create_effect(
            world_x,
            world_y,
            config,
            effect_id=f"confetti_level_up_{self.level_manager.level}"
        )

    def _update_stats(self) -> None:
        """Met à jour les valeurs de caractéristiques selon le niveau actuel."""
        if self.level_manager.stats_config:
            try:
                # Mettre à jour la vitesse selon la stat "vitesse"
                # La stat vitesse est utilisée comme facteur d'amélioration
                # Formule: speed = base_speed * (1 + (vitesse_stat / 100))
                # Exemple: vitesse_stat = 12 → speed = 250 * 1.12 = 280 pixels/seconde
                #          vitesse_stat = 85 → speed = 250 * 1.85 = 462.5 pixels/seconde
                vitesse_stat = self.level_manager.get_stat_value("vitesse")
                self.speed = self._base_speed * (1.0 + (vitesse_stat / 100.0))
            except KeyError:
                # Si la stat "vitesse" n'existe pas, utiliser la vitesse de base
                self.speed = self._base_speed

    @property
    def force(self) -> float:
        """Retourne la valeur de force actuelle."""
        if self.level_manager.stats_config:
            try:
                return self.level_manager.get_stat_value("force")
            except KeyError:
                return 0.0
        return 0.0

    @property
    def intelligence(self) -> float:
        """Retourne la valeur d'intelligence actuelle."""
        if self.level_manager.stats_config:
            try:
                return self.level_manager.get_stat_value("intelligence")
            except KeyError:
                return 0.0
        return 0.0

    @property
    def vitesse(self) -> float:
        """Retourne la valeur de vitesse actuelle."""
        if self.level_manager.stats_config:
            try:
                return self.level_manager.get_stat_value("vitesse")
            except KeyError:
                return 0.0
        return 0.0

    def set_position(self, x: float, y: float) -> None:
        """Définit la position du personnage.

        Args:
            x: Position horizontale
            y: Position verticale
        """
        self.x = x
        self.y = y

    def apply_gravity(self, dt: float) -> None:
        """Applique la gravité au personnage.

        Args:
            dt: Delta time en secondes
        """
        # Augmenter la vitesse verticale avec la gravité
        self.velocity_y += self.gravity * dt

        # Limiter la vitesse de chute
        if self.velocity_y > self.max_fall_speed:
            self.velocity_y = self.max_fall_speed

    def reset_velocity_y(self) -> None:
        """Réinitialise la vitesse verticale."""
        self.velocity_y = 0.0

    def double_jump(self) -> None:
        """Déclenche un double saut si le personnage est en l'air et a encore son double saut disponible.
        
        Le double saut est disponible à partir du seuil configuré dans player_stats.toml
        (double_jump_unlock_level, défaut 3).
        Il nécessite que le joueur ait relâché la touche de saut après le premier saut,
        puis réappuie sur la touche pour déclencher le deuxième saut.
        Le double saut relance un nouveau saut depuis la position actuelle du personnage.
        """
        if (not self.is_on_ground and 
            self.level_manager.level >= self._double_jump_unlock_level and
            self._has_double_jump and 
            not self._double_jump_used):
            # Appliquer la vitesse de saut (relancer le saut)
            self.velocity_y = self.jump_velocity
            self._double_jump_used = True
            self._has_double_jump = False
            # Optionnel : réinitialiser l'animation pour un effet visuel
            # self.jump_frame = 0
            # self.jump_animation_timer = 0.0

    def jump(self) -> None:
        """Déclenche un saut si le personnage est au sol.

        Le saut applique une vitesse verticale initiale négative qui sera
        modifiée par la gravité pour créer un mouvement parabolique naturel.
        À partir du seuil double_jump_unlock_level, le personnage peut effectuer un double saut en l'air.
        """
        if self.is_on_ground and self.can_jump:
            self.is_jumping = True
            self.can_jump = False
            self.velocity_y = self.jump_velocity
            self.jump_frame = 0
            self.jump_animation_timer = 0.0
            # Marquer qu'on était au sol au moment du saut pour éviter l'annulation immédiate
            self._was_on_ground = True
            # Initialiser le double saut si le niveau atteint le seuil configuré
            if self.level_manager.level >= self._double_jump_unlock_level:
                self._has_double_jump = True
                self._double_jump_used = False

    def _handle_climb_input(self, keys: pygame.key.ScancodeWrapper, dt: float) -> float:
        """Gère l'input de grimpe et retourne le déplacement vertical.
        
        Args:
            keys: Objet ScancodeWrapper retourné par pygame.key.get_pressed()
            dt: Delta time en secondes
            
        Returns:
            Déplacement vertical en pixels (négatif = vers le haut, positif = vers le bas)
            Retourne 0.0 si pas de grimpe
        """
        # Blocage pendant la transition de niveau
        if self.level_transition_active:
            self.is_climbing = False
            return 0.0
        
        # Suivre l'état précédent de grimpe pour détecter les transitions
        was_climbing = self.is_climbing
        
        if self.is_on_climbable and (keys[pygame.K_UP] or keys[pygame.K_w]):
            # Le joueur est sur un bloc grimpable et appuie sur haut
            self.is_climbing = True
            # Réinitialiser la vitesse verticale quand on commence à grimper
            # pour éviter que la vitesse accumulée avant la grimpe ne s'applique après
            if not was_climbing:
                self.velocity_y = 0.0
            # Retourner un déplacement vertical négatif (vers le haut)
            return -self.climb_speed * dt
        else:
            # Pas de grimpe
            # Réinitialiser la vitesse verticale quand on arrête de grimper
            # pour éviter une chute accélérée due à la vitesse accumulée
            if was_climbing:
                self.velocity_y = 0.0
            self.is_climbing = False
            return 0.0

    def _handle_jump_input(self, keys: pygame.key.ScancodeWrapper) -> None:
        """Gère l'input de saut (saut normal et double saut).

        Args:
            keys: Objet ScancodeWrapper retourné par pygame.key.get_pressed()
        """
        # Blocage pendant la transition de niveau
        if self.level_transition_active:
            return
        
        # Ne pas sauter si on est en train de grimper
        if self.is_climbing:
            return
        
        jump_key_pressed = keys[pygame.K_UP] or keys[pygame.K_w]
        
        # Gestion du saut normal (au sol) - priorité sur le double saut
        # Cette vérification doit être faite en premier pour éviter que le double saut interfère
        if jump_key_pressed and self.is_on_ground and self.can_jump:
            self.jump()
            self._jump_key_pressed = True
        
        # Gestion du relâchement de la touche (pour permettre le double saut)
        # Détecte le passage de pressé à relâché
        elif not jump_key_pressed and self._jump_key_pressed:
            # La touche vient d'être relâchée
            self._jump_key_pressed = False
        
        # Gestion du double saut (en l'air, niveau >= double_jump_unlock_level)
        # Ne peut se déclencher que si :
        # - La touche est pressée
        # - Le personnage est en l'air
        # - La touche a été relâchée puis réappuyée (détecté par _jump_key_pressed == False puis la touche est pressée)
        # - Le niveau >= seuil configuré (_double_jump_unlock_level)
        # - Le double saut est disponible et n'a pas été utilisé
        # - Le personnage est en train de sauter (is_jumping == True) pour éviter les déclenchements accidentels
        elif (jump_key_pressed and 
              not self.is_on_ground and 
              self.is_jumping and  # Le personnage doit être en train de sauter
              not self._jump_key_pressed and  # La touche a été relâchée puis réappuyée
              self.level_manager.level >= self._double_jump_unlock_level and
              self._has_double_jump and 
              not self._double_jump_used):
            self.double_jump()
            self._jump_key_pressed = True

    def _update_jump_animation(self, dt: float) -> None:
        """Met à jour l'animation de saut.

        Args:
            dt: Delta time en secondes
        """
        if self.is_jumping:
            # Incrémenter le timer d'animation
            self.jump_animation_timer += dt

            # Optimisation : utiliser jump_frame_duration pré-calculé au lieu de division à chaque frame
            # Avancer à la frame suivante si nécessaire
            if self.jump_animation_timer >= self._jump_frame_duration:
                self.jump_frame += 1
                self.jump_animation_timer = 0.0

                # Si on a atteint la dernière frame, garder la dernière frame pendant le saut
                if self.jump_frame >= 5:
                    self.jump_frame = 4
        else:
            # Réinitialiser l'animation de saut si on n'est plus en saut
            self.jump_frame = 0
            self.jump_animation_timer = 0.0

    def _update_climb_animation(self, dt: float) -> None:
        """Met à jour l'animation de grimpe.

        Args:
            dt: Delta time en secondes
        """
        if self.is_climbing:
            # Incrémenter le timer d'animation
            self.climb_animation_timer += dt

            # Optimisation : utiliser climb_frame_duration pré-calculé au lieu de division à chaque frame
            # Avancer à la frame suivante si nécessaire
            if self.climb_animation_timer >= self._climb_frame_duration:
                self.climb_frame += 1
                self.climb_animation_timer = 0.0

                # Si on a atteint la dernière frame, boucler
                if self.climb_frame >= 8:
                    self.climb_frame = 0
        else:
            # Réinitialiser l'animation de grimpe si on n'est plus en train de grimper
            self.climb_frame = 0
            self.climb_animation_timer = 0.0

    def _get_climb_sprite(self) -> Optional[pygame.Surface]:
        """Récupère le sprite de grimpe actuel à afficher.

        Returns:
            Surface pygame contenant le sprite de grimpe, ou None si pas en train de grimper ou sprite sheet non chargé
        """
        if not self.is_climbing:
            return None
        
        if not hasattr(self, 'climb_sprite_sheet') or self.climb_sprite_sheet is None:
            return None

        row = self.CLIMB_DIRECTION_TO_ROW.get(self.current_direction, 3)
        return self._get_sprite_at_climb(row, self.climb_frame)

    def _get_sprite_at_climb(self, row: int, col: int) -> pygame.Surface:
        """Extrait un sprite de grimpe à la position (row, col) du sprite sheet (avec cache).
        
        Args:
            row: Index de la ligne (0-based)
            col: Index de la colonne (0-based)
            
        Returns:
            Surface pygame contenant le sprite extrait (depuis le cache si disponible)
        """
        # Vérifier d'abord le cache global des sprites redimensionnés (préchargement)
        from ..assets.preloader import _global_player_scaled_sprite_cache
        
        if self.sprite_scale != 1.0:
            global_cache_key = (
                self.player_level, "climb", row, col,
                int(self.display_width), int(self.display_height)
            )
            if global_cache_key in _global_player_scaled_sprite_cache:
                return _global_player_scaled_sprite_cache[global_cache_key]
        
        # Sinon, utiliser le cache local ou extraire
        cache_key = (row, col)
        
        # Vérifier le cache local (mais on doit quand même redimensionner)
        # Note: Le cache stocke les sprites non redimensionnés, on les redimensionne à la volée
        if cache_key in self._climb_frame_cache:
            sprite = self._climb_frame_cache[cache_key]
        else:
            sprite = self._extract_sprite(
                self.climb_sprite_sheet,
                self.sprite_width,
                self.sprite_height,
                row,
                col,
            )
            self._climb_frame_cache[cache_key] = sprite

        if self.sprite_scale == 1.0:
            return sprite

        # Vérifier le cache local des sprites redimensionnés
        scaled_key = (row, col, int(self.display_width), int(self.display_height))
        if scaled_key in self._scaled_climb_frame_cache:
            return self._scaled_climb_frame_cache[scaled_key]

        # OPTIMISATION: Éviter smoothscale si la taille cible est identique à la taille originale
        target_size = (int(self.display_width), int(self.display_height))
        if sprite.get_size() == target_size:
            # Pas besoin de redimensionner, mettre en cache directement
            scaled_sprite = sprite.convert_alpha()
            self._scaled_climb_frame_cache[scaled_key] = scaled_sprite
            return scaled_sprite

        # Redimensionner et mettre en cache local
        scaled_sprite = pygame.transform.smoothscale(
            sprite, target_size
        )
        scaled_sprite = scaled_sprite.convert_alpha()
        self._scaled_climb_frame_cache[scaled_key] = scaled_sprite
        return scaled_sprite

    def _get_jump_sprite(self) -> Optional[pygame.Surface]:
        """Récupère le sprite de saut actuel à afficher.

        Returns:
            Surface pygame contenant le sprite de saut, ou None si pas en saut
        """
        if not self.is_jumping:
            return None

        row = self.JUMP_DIRECTION_TO_ROW.get(self.current_direction, 3)
        return self._get_sprite_at_jump(row, self.jump_frame)

    def _get_sprite_at_jump(self, row: int, col: int) -> pygame.Surface:
        """Extrait un sprite de saut à la position (row, col) du sprite sheet (avec cache).
        
        Args:
            row: Index de la ligne (0-based)
            col: Index de la colonne (0-based)
            
        Returns:
            Surface pygame contenant le sprite extrait (depuis le cache si disponible)
        """
        # Vérifier d'abord le cache global des sprites redimensionnés (préchargement)
        from ..assets.preloader import _global_player_scaled_sprite_cache
        
        if self.sprite_scale != 1.0:
            global_cache_key = (
                self.player_level, "jump", row, col,
                int(self.display_width), int(self.display_height)
            )
            if global_cache_key in _global_player_scaled_sprite_cache:
                return _global_player_scaled_sprite_cache[global_cache_key]
        
        # Sinon, utiliser le cache local ou extraire
        cache_key = (row, col)
        
        # Vérifier le cache local (mais on doit quand même redimensionner)
        # Note: Le cache stocke les sprites non redimensionnés, on les redimensionne à la volée
        if cache_key in self._jump_frame_cache:
            sprite = self._jump_frame_cache[cache_key]
        else:
            sprite = self._extract_sprite(
                self.jump_sprite_sheet,
                self.jump_sprite_width,
                self.jump_sprite_height,
                row,
                col,
            )
            self._jump_frame_cache[cache_key] = sprite

        if self.sprite_scale == 1.0:
            return sprite

        # Vérifier le cache local des sprites redimensionnés
        scaled_key = (row, col, int(self.display_width), int(self.display_height))
        if scaled_key in self._scaled_jump_frame_cache:
            return self._scaled_jump_frame_cache[scaled_key]

        # OPTIMISATION: Éviter smoothscale si la taille cible est identique à la taille originale
        target_size = (int(self.display_width), int(self.display_height))
        if sprite.get_size() == target_size:
            # Pas besoin de redimensionner, mettre en cache directement
            scaled_sprite = sprite.convert_alpha()
            self._scaled_jump_frame_cache[scaled_key] = scaled_sprite
            return scaled_sprite

        # Redimensionner et mettre en cache local
        scaled_sprite = pygame.transform.smoothscale(
            sprite, target_size
        )
        scaled_sprite = scaled_sprite.convert_alpha()
        self._scaled_jump_frame_cache[scaled_key] = scaled_sprite
        return scaled_sprite

    def _reload_assets(self) -> None:
        """Charge (ou recharge) les sprite sheets associés au niveau courant."""
        
        # Invalider les caches locaux lors du rechargement des assets
        # (les caches globaux restent valides)
        self._walk_frame_cache.clear()
        self._scaled_walk_frame_cache.clear()
        self._jump_frame_cache.clear()
        self._scaled_jump_frame_cache.clear()
        self._climb_frame_cache.clear()
        self._scaled_climb_frame_cache.clear()
        self._dialogue_frame_cache.clear()
        self._scaled_dialogue_frame_cache.clear()

        # Charger walk.png (utiliser le cache global si disponible)
        from ..assets.preloader import _global_player_sprite_sheet_cache
        
        walk_path = self._resolve_asset_path(self._walk_override_path, self.WALK_SHEET_NAME)
        walk_path_key = str(walk_path.resolve())
        
        # Vérifier d'abord le cache global
        if walk_path_key in _global_player_sprite_sheet_cache:
            self.sprite_sheet = _global_player_sprite_sheet_cache[walk_path_key]
        else:
            # Charger depuis le disque si pas en cache
            try:
                self.sprite_sheet = pygame.image.load(str(walk_path)).convert_alpha()
            except FileNotFoundError as exc:
                raise MissingPlayerAssetError(
                    f"Unable to load walk sprite sheet at {walk_path}"
                ) from exc

        jump_override = self._jump_override_path
        if jump_override is None and self._walk_override_path is not None:
            jump_override = self._walk_override_path.parent / self.JUMP_SHEET_NAME

        jump_path = self._resolve_asset_path(jump_override, self.JUMP_SHEET_NAME)
        jump_path_key = str(jump_path.resolve())
        
        # Vérifier d'abord le cache global
        if jump_path_key in _global_player_sprite_sheet_cache:
            self.jump_sprite_sheet = _global_player_sprite_sheet_cache[jump_path_key]
        else:
            # Charger depuis le disque si pas en cache
            try:
                self.jump_sprite_sheet = pygame.image.load(str(jump_path)).convert_alpha()
            except FileNotFoundError:
                print(
                    f"Attention: Fichier {jump_path} introuvable. Le saut fonctionnera sans animation."
                )
                self.jump_sprite_sheet = pygame.Surface(
                    (self.jump_sprite_width * 5, self.jump_sprite_height * 4), pygame.SRCALPHA
                )

        # Charger le sprite sheet de grimpe (optionnel, utiliser le cache global si disponible)
        climb_path = self._resolve_asset_path(None, self.CLIMB_SHEET_NAME)
        climb_path_key = str(climb_path.resolve())
        
        # Vérifier d'abord le cache global
        if climb_path_key in _global_player_sprite_sheet_cache:
            self.climb_sprite_sheet = _global_player_sprite_sheet_cache[climb_path_key]
        else:
            # Charger depuis le disque si pas en cache
            try:
                self.climb_sprite_sheet = pygame.image.load(str(climb_path)).convert_alpha()
            except FileNotFoundError:
                print(
                    f"Attention: Fichier {climb_path} introuvable. La grimpe fonctionnera sans animation spécifique."
                )
                self.climb_sprite_sheet = None


    def _resolve_asset_path(self, override_path: Optional[Path], default_filename: str) -> Path:
        """Calcule le chemin absolu d'un asset en tenant compte du niveau."""

        if override_path is not None:
            return override_path
        return self.level_manager.get_asset_path(default_filename)

    def _resolve_assets_root(self, assets_root: Optional[Path]) -> Path:
        """Résout le répertoire racine contenant les assets du personnage."""

        if assets_root is None:
            return (self._project_root / "sprite" / "personnage").resolve()

        resolved = Path(assets_root)
        if not resolved.is_absolute():
            resolved = (self._project_root / resolved).resolve()
        return resolved

    def _coerce_to_path(self, path_like: str | Path) -> Path:
        """Convertit un chemin (relatif ou absolu) en `Path` absolu."""

        candidate = Path(path_like)
        if not candidate.is_absolute():
            candidate = (self._project_root / candidate).resolve()
        return candidate

    def _load_font(self, font_path: Optional[str], font_size: int) -> pygame.font.Font:
        """Charge la police pour l'affichage du prénom avec fallback."""

        if font_path:
            font_file = Path(font_path)
            if not font_file.is_absolute():
                font_file = (self._project_root / font_file).resolve()
            if font_file.exists():
                try:
                    return pygame.font.Font(str(font_file), font_size)
                except pygame.error:
                    pass

        # Essayer de charger PressStart2P depuis un répertoire fonts/ typique
        press_start_path = self._project_root / "fonts" / "PressStart2P-Regular.ttf"
        if press_start_path.exists():
            try:
                return pygame.font.Font(str(press_start_path), font_size)
            except pygame.error:
                pass

        # Fallback vers une police système lisible (sans-serif avec bold pour meilleure lisibilité)
        try:
            return pygame.font.SysFont("arial", font_size, bold=True)
        except pygame.error:
            try:
                return pygame.font.SysFont("sans-serif", font_size, bold=True)
            except pygame.error:
                # Dernier recours : monospace
                return pygame.font.SysFont("monospace", font_size, bold=True)

    def _render_name(self) -> None:
        """Génère la surface contenant le prénom avec contour."""

        if not self.name:
            self.name_surface = None
            self.name_rect = None
            return

        # Rendre le texte principal avec anti-aliasing pour meilleure lisibilité
        text_surface = self.font.render(self.name, True, self.name_color)

        # Créer une surface plus grande pour le contour (2 pixels de chaque côté pour un contour plus épais)
        outline_thickness = 2
        outline_width = text_surface.get_width() + (outline_thickness * 2)
        outline_height = text_surface.get_height() + (outline_thickness * 2)
        self.name_surface = pygame.Surface((outline_width, outline_height), pygame.SRCALPHA)

        # Dessiner le contour plus épais (2 pixels) pour meilleure lisibilité
        # On dessine plusieurs couches pour créer un contour plus visible
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

    def get_name_draw_command(self, camera_x: float) -> Optional[tuple[pygame.Surface, tuple[int, int]]]:
        """Construit la commande de dessin pour le prénom au-dessus du personnage."""
        if self.name_surface is None or self.name_rect is None:
            self._render_name()

        if self.name_surface is None or self.name_rect is None:
            return None

        # Calculer la position à l'écran en tenant compte de la caméra
        screen_x = self.x - camera_x
        screen_y = self.y

        # Positionner le prénom centré horizontalement et juste au-dessus du sprite
        name_x = round(screen_x - self.name_rect.width / 2)
        bottom_y = screen_y + self.sprite_height / 2
        top_of_sprite = bottom_y - self.display_height
        base_name_y = top_of_sprite - self.name_rect.height
        name_y = round(base_name_y + self.name_offset_y)

        return self.name_surface, (name_x, name_y)

    def draw_name(self, surface: pygame.Surface, camera_x: float) -> None:
        """Dessine le prénom au-dessus du personnage."""
        command = self.get_name_draw_command(camera_x)
        if command is not None:
            surface.blits([command], False)

    def get_inventory_draw_commands(
        self, camera_x: float, screen_width: int, screen_height: int
    ) -> list[tuple[pygame.Surface, tuple[int, int]]]:
        """Génère les commandes de dessin pour l'inventaire.

        Args:
            camera_x: Position horizontale de la caméra
            screen_width: Largeur de l'écran en pixels
            screen_height: Hauteur de l'écran en pixels

        Returns:
            Liste des commandes de dessin (surface, position)
        """
        if self.inventory is None:
            return []

        # Récupérer la position du prénom
        name_command = self.get_name_draw_command(camera_x)
        if name_command is None:
            return []

        name_surface, (name_x, name_y) = name_command

        # Calculer la position de l'inventaire au-dessus du prénom
        return self.inventory.get_display_commands(
            camera_x=camera_x,
            player_x=self.x,
            player_y=self.y,
            name_y=name_y,
            screen_width=screen_width,
            screen_height=screen_height,
        )

    def draw_inventory(self, surface: pygame.Surface, camera_x: float, screen_width: int, screen_height: int) -> None:
        """Dessine l'inventaire au-dessus du prénom.
        
        Args:
            surface: Surface pygame sur laquelle dessiner
            camera_x: Position horizontale de la caméra
            screen_width: Largeur de l'écran en pixels
            screen_height: Hauteur de l'écran en pixels
        """
        commands = self.get_inventory_draw_commands(camera_x, screen_width, screen_height)
        if commands:
            surface.blits(commands, False)

    def request_camera_snap(self) -> None:
        """Demande un recentrage immédiat de la caméra sur la position actuelle du joueur."""
        self._camera_snap_requested = True

    def consume_camera_snap_request(self) -> bool:
        """Consomme une éventuelle demande de recentrage caméra.

        Returns:
            True si un recentrage doit être appliqué, False sinon.
        """
        if self._camera_snap_requested:
            self._camera_snap_requested = False
            return True
        return False

    def _apply_design_space_snap(self, design_x: float) -> float:
        """Déplace le joueur vers une position X exprimée dans le repère de conception (1920x1080).

        Args:
            design_x: Position X dans le repère de conception.

        Returns:
            Position X convertie dans le repère de rendu (1280x720).
        """
        render_x = float(design_x) * self._design_scale_x
        self.x = render_x
        self.attached_platform = None
        self.velocity_y = 0.0
        self.request_camera_snap()
        return render_x

    def start_dialogue_animation(
        self,
        sprite_sheet_path: str,
        row: int,
        num_frames: int,
        animation_speed: float,
        animation_type: str = "simple",
        start_sprite: int = 0,
        offset_y: float = 0.0,
        set_x_position: Optional[float] = None,
    ) -> None:
        """Démarre une animation du personnage principal pour un dialogue.
        
        Cette méthode remplace temporairement l'animation normale du personnage
        par une animation spécifique définie dans la configuration du dialogue.
        
        Args:
            sprite_sheet_path: Chemin vers la planche de sprite à utiliser (relatif au répertoire du niveau)
            row: Ligne du sprite sheet à utiliser (0-indexed)
            num_frames: Nombre de frames dans l'animation
            animation_speed: Vitesse d'animation en FPS
            animation_type: Type d'animation ("simple", "loop", ou "pingpong")
            start_sprite: Premier sprite à afficher dans la séquence (0-indexed, défaut: 0)
            offset_y: Offset vertical (en pixels dans le repère de conception) appliqué pendant toute l'animation.
            set_x_position: Position X (repère de conception 1920x1080) vers laquelle déplacer immédiatement le joueur.
        """
        if set_x_position is not None:
            self._apply_design_space_snap(set_x_position)

        self._dialogue_animation_start_sprite = max(0, int(start_sprite))
        self._dialogue_animation_offset_y = float(offset_y) * self._design_scale_y

        # Sauvegarder l'état d'animation actuel pour le restaurer plus tard
        self._saved_direction = self.current_direction
        self._saved_is_moving = self.is_moving
        
        # Charger le nouveau sprite sheet
        try:
            sprite_path = self.level_manager.get_asset_path(sprite_sheet_path)
            self._dialogue_animation_sprite_sheet = pygame.image.load(str(sprite_path)).convert_alpha()
        except (FileNotFoundError, pygame.error) as e:
            print(f"Warning: Impossible de charger le sprite sheet d'animation de dialogue {sprite_sheet_path}: {e}")
            # Si le chargement échoue, ne pas activer l'animation
            return
        
        # Initialiser l'animation avec les paramètres fournis
        self._dialogue_animation_active = True
        self._dialogue_animation_row = row
        self._dialogue_animation_num_frames = num_frames
        self._dialogue_animation_speed = animation_speed
        self._dialogue_animation_type = animation_type
        self._dialogue_animation_frame = 0
        self._dialogue_animation_timer = 0.0
        self._dialogue_animation_direction = 1  # Commencer en avant pour pingpong
        
        # Invalider le cache d'animation de dialogue
        self._dialogue_frame_cache.clear()
        self._scaled_dialogue_frame_cache.clear()

    def stop_dialogue_animation(self) -> None:
        """Arrête l'animation de dialogue et restaure l'animation normale du personnage.
        
        Cette méthode est appelée lorsque le dialogue se termine ou passe à un échange
        sans animation. Elle restaure l'état d'animation précédent du personnage.
        """
        if not self._dialogue_animation_active:
            return
        
        # Restaurer l'animation normale
        if self._saved_direction is not None:
            self.current_direction = self._saved_direction
        self.is_moving = self._saved_is_moving
        
        # Nettoyer les ressources temporaires
        self._dialogue_animation_active = False
        self._dialogue_animation_sprite_sheet = None
        self._dialogue_animation_row = 0
        self._dialogue_animation_num_frames = 0
        self._dialogue_animation_speed = 10.0
        self._dialogue_animation_type = "simple"
        self._dialogue_animation_frame = 0
        self._dialogue_animation_timer = 0.0
        self._dialogue_animation_direction = 1
        self._dialogue_animation_start_sprite = 0
        self._dialogue_animation_offset_y = 0.0
        self._saved_direction = None
        self._saved_is_moving = False
        
        # Nettoyer le cache (optionnel, mais peut libérer de la mémoire)
        # self._dialogue_frame_cache.clear()
        # self._scaled_dialogue_frame_cache.clear()

    def _update_dialogue_animation(self, dt: float) -> None:
        """Met à jour l'animation de dialogue du personnage.
        
        Args:
            dt: Delta time en secondes
        """
        if not self._dialogue_animation_active or self._dialogue_animation_sprite_sheet is None:
            return
        
        self._dialogue_animation_timer += dt
        frame_duration = 1.0 / self._dialogue_animation_speed if self._dialogue_animation_speed > 0 else 0.0
        
        if frame_duration > 0 and self._dialogue_animation_timer >= frame_duration:
            self._dialogue_animation_timer = 0.0
            
            if self._dialogue_animation_type == "simple":
                # Animation simple : avancer jusqu'à la dernière frame puis s'arrêter
                if self._dialogue_animation_frame < self._dialogue_animation_num_frames - 1:
                    self._dialogue_animation_frame += 1
            elif self._dialogue_animation_type == "loop":
                # Animation en boucle : revenir à la première frame après la dernière
                self._dialogue_animation_frame = (self._dialogue_animation_frame + 1) % self._dialogue_animation_num_frames
            elif self._dialogue_animation_type == "pingpong":
                # Animation aller-retour : avancer puis reculer
                self._dialogue_animation_frame += self._dialogue_animation_direction
                if self._dialogue_animation_frame >= self._dialogue_animation_num_frames - 1:
                    self._dialogue_animation_frame = self._dialogue_animation_num_frames - 1
                    self._dialogue_animation_direction = -1
                elif self._dialogue_animation_frame <= 0:
                    self._dialogue_animation_frame = 0
                    self._dialogue_animation_direction = 1

    def _get_dialogue_sprite_at(self, row: int, col: int) -> pygame.Surface:
        """Extrait un sprite d'animation de dialogue à la position (row, col) du sprite sheet (avec cache).
        
        Args:
            row: Index de la ligne (0-based)
            col: Index de la colonne (0-based)
            
        Returns:
            Surface pygame contenant le sprite extrait (depuis le cache si disponible)
        """
        if self._dialogue_animation_sprite_sheet is None:
            # Retourner un sprite vide si le sprite sheet n'est pas chargé
            return pygame.Surface((self.sprite_width, self.sprite_height), pygame.SRCALPHA)
        adjusted_col = col
        if self._dialogue_animation_active:
            adjusted_col = self._dialogue_animation_start_sprite + col
        
        cache_key = (row, adjusted_col)
        
        # Vérifier le cache
        if cache_key in self._dialogue_frame_cache:
            sprite = self._dialogue_frame_cache[cache_key]
        else:
            sprite = self._extract_sprite(
                self._dialogue_animation_sprite_sheet,
                self.sprite_width,
                self.sprite_height,
                row,
                adjusted_col,
            )
            self._dialogue_frame_cache[cache_key] = sprite

        if self.sprite_scale == 1.0:
            return sprite

        scaled_key = (row, adjusted_col, int(self.display_width), int(self.display_height))
        if scaled_key in self._scaled_dialogue_frame_cache:
            return self._scaled_dialogue_frame_cache[scaled_key]

        # OPTIMISATION: Éviter smoothscale si la taille cible est identique à la taille originale
        target_size = (int(self.display_width), int(self.display_height))
        if sprite.get_size() == target_size:
            # Pas besoin de redimensionner, mettre en cache directement
            scaled_sprite = sprite.convert_alpha()
            self._scaled_dialogue_frame_cache[scaled_key] = scaled_sprite
            return scaled_sprite

        scaled_sprite = pygame.transform.smoothscale(
            sprite, target_size
        )
        scaled_sprite = scaled_sprite.convert_alpha()
        self._scaled_dialogue_frame_cache[scaled_key] = scaled_sprite
        return scaled_sprite

    def show_level_up(self) -> None:
        """Active l'affichage du level up.
        
        Cette méthode est appelée par le système d'événements lorsque l'événement
        de type `level_up` est déclenché (voir spécification 11).
        """
        self.level_up_active = True
        self.level_up_visible = True
        self.level_up_blink_timer = 0.0

    def hide_level_up(self) -> None:
        """Désactive l'affichage du level up.
        
        Cette méthode est appelée lorsque le joueur appuie sur la touche 'U'
        pour confirmer le level up.
        """
        self.level_up_active = False
        self.level_up_visible = False
        self.level_up_blink_timer = 0.0

    def _update_level_up_animation(self, dt: float) -> None:
        """Met à jour l'animation de clignotement du texte de level up.
        
        Args:
            dt: Delta time en secondes
        """
        if not self.level_up_active:
            return
        
        self.level_up_blink_timer += dt
        
        # Basculer la visibilité toutes les level_up_blink_speed secondes
        if self.level_up_blink_timer >= self.level_up_blink_speed:
            self.level_up_blink_timer = 0.0
            self.level_up_visible = not self.level_up_visible

    def _draw_level_up(self, surface: pygame.Surface, camera_x: float) -> None:
        """Dessine le texte "level up (press u)" en jaune clignotant au-dessus de l'inventaire.
        
        Args:
            surface: Surface pygame sur laquelle dessiner
            camera_x: Position horizontale de la caméra
        """
        if not self.level_up_active or not self.level_up_visible:
            return
        
        # Calculer la position à l'écran
        screen_x = self.x - camera_x
        screen_y = self.y
        
        # Positionner le texte au-dessus de l'inventaire
        # Si l'inventaire existe et a des objets, utiliser sa position
        # Sinon, utiliser la position du nom comme fallback avec une marge de 20 pixels
        inventory_y = None
        use_name_position = False
        if self.inventory is not None:
            # Récupérer les commandes de dessin de l'inventaire pour obtenir sa position Y
            inventory_commands = self.get_inventory_draw_commands(
                camera_x, surface.get_width(), surface.get_height()
            )
            if inventory_commands:
                # La position Y de l'inventaire est celle du premier objet (le plus haut)
                _, (_, first_item_y) = inventory_commands[0]
                inventory_y = float(first_item_y)
        
        # Si l'inventaire n'existe pas ou est vide, utiliser la position du nom comme fallback
        name_y = None
        if inventory_y is None:
            use_name_position = True
            # Calculer la position Y du haut du nom (identique à get_name_draw_command)
            bottom_y = screen_y + self.sprite_height / 2
            top_of_sprite = bottom_y - self.display_height
            base_name_y = top_of_sprite - (self.name_rect.height if self.name_rect else 0)
            name_y = base_name_y + self.name_offset_y
        
        # Rendre le texte avec la même police que le nom
        text_color = (255, 255, 0)  # Jaune
        outline_color = (0, 0, 0)  # Noir
        outline_thickness = 2
        
        # Rendre le texte avec contour (même méthode que pour le nom)
        text_surface = self.font.render(self.level_up_text, True, text_color)
        
        # Calculer la position Y selon qu'on utilise l'inventaire ou le nom
        if use_name_position and name_y is not None:
            # Si on utilise la position du nom, le bas de l'indicateur doit être à 20 pixels du haut du nom
            # Le haut de l'indicateur est donc à : name_y - 20 - hauteur_du_texte
            level_up_spacing_from_name = 20.0
            text_y = round(name_y - level_up_spacing_from_name - text_surface.get_height())
        else:
            # Si on utilise l'inventaire, espacement de 8 pixels
            level_up_spacing = 8.0
            level_up_y = inventory_y - level_up_spacing
            text_y = round(level_up_y - text_surface.get_height())
        
        # Calculer la position centrée horizontalement
        text_x = round(screen_x - text_surface.get_width() / 2)
        
        # Dessiner le contour
        outline_surface = self.font.render(self.level_up_text, True, outline_color)
        for dx in range(-outline_thickness, outline_thickness + 1):
            for dy in range(-outline_thickness, outline_thickness + 1):
                if dx != 0 or dy != 0:
                    surface.blit(outline_surface, (text_x + dx, text_y + dy))
        
        # Dessiner le texte principal
        surface.blit(text_surface, (text_x, text_y))

    def start_level_transition(
        self, 
        old_level: int, 
        new_level: int, 
        camera_zoom_controller: Optional["CameraZoomController"] = None
    ) -> None:
        """Démarre l'animation de transition de niveau.
        
        Args:
            old_level: Niveau précédent (avant le changement)
            new_level: Nouveau niveau (après le changement)
            camera_zoom_controller: Contrôleur de zoom de caméra (optionnel)
        """
        if old_level == new_level:
            return  # Pas de transition si le niveau ne change pas
        
        self.level_transition_active = True
        self.level_transition_phase = "zoom_in"
        self.level_transition_camera_zoom_controller = camera_zoom_controller
        
        # Initialiser les timers pour toutes les phases
        self.level_transition_zoom_in_timer = self.level_transition_zoom_in_duration
        self.level_transition_timer = self.level_transition_duration
        self.level_transition_zoom_out_timer = self.level_transition_zoom_out_duration
        self.level_transition_switch_timer = 0.0
        
        self.level_transition_old_level = old_level
        self.level_transition_new_level = new_level
        self.level_transition_showing_old = True
        
        # Démarrer la phase 1 : zoom avant sur le joueur
        if self.level_transition_camera_zoom_controller is not None:
            self.level_transition_camera_zoom_controller.start_zoom(
                zoom_percent=self.DEFAULT_LEVEL_TRANSITION_ZOOM_PERCENT,
                duration=self.level_transition_zoom_in_duration,
                bottom_margin_design_px=50.0,
                keep_bubbles_visible=True
            )
        
        # Charger temporairement le sprite sheet de l'ancien niveau
        old_level_manager = PlayerLevelManager(self._assets_root, old_level, self.level_manager.stats_config)
        old_walk_path = old_level_manager.get_asset_path("walk.png")
        try:
            self.level_transition_old_sprite_sheet = pygame.image.load(str(old_walk_path)).convert_alpha()
        except FileNotFoundError:
            # Si le sprite sheet de l'ancien niveau n'existe pas, utiliser le sprite sheet actuel
            self.level_transition_old_sprite_sheet = self.sprite_sheet
        
        # Charger la phrase d'amélioration depuis la configuration
        improvement_message = None
        if self.level_manager.stats_config is not None:
            improvement_message = self.level_manager.stats_config.get_level_up_message(new_level)
        
        self.level_transition_improvement_message = improvement_message
        
        # Pré-rendre le texte de transition avec cadre arrondi
        main_text = f"level {old_level} -> level {new_level}"
        render_width, render_height = get_render_size()
        scale_x, scale_y = compute_design_scale((render_width, render_height))
        main_font_size = int(self.LEVEL_TRANSITION_TEXT_SIZE * scale_y)
        main_font = self._load_font(None, main_font_size)
        main_text_color = self.LEVEL_TRANSITION_TEXT_COLOR  # Texte principal en noir
        
        # Rendre le texte principal
        main_text_surface = main_font.render(main_text, True, main_text_color)
        
        # Rendre le texte d'amélioration si disponible
        improvement_text_surface = None
        improvement_text_height = 0
        text_spacing = int(self.LEVEL_TRANSITION_TEXT_SPACING * scale_y)
        
        if improvement_message is not None:
            improvement_font_size = int(self.LEVEL_TRANSITION_IMPROVEMENT_TEXT_SIZE * scale_y)
            improvement_font = self._load_font(None, improvement_font_size)
            improvement_text_color = self.LEVEL_TRANSITION_IMPROVEMENT_TEXT_COLOR  # Gris foncé
            
            # Gérer les retours à la ligne si présents
            improvement_lines = improvement_message.split('\n')
            improvement_surfaces = []
            max_improvement_width = 0
            for line in improvement_lines:
                if line.strip():  # Ignorer les lignes vides
                    line_surface = improvement_font.render(line.strip(), True, improvement_text_color)
                    improvement_surfaces.append(line_surface)
                    max_improvement_width = max(max_improvement_width, line_surface.get_width())
            
            if improvement_surfaces:
                # Créer une surface combinée pour toutes les lignes d'amélioration
                improvement_text_height = sum(s.get_height() for s in improvement_surfaces) + text_spacing * (len(improvement_surfaces) - 1)
                improvement_text_surface = pygame.Surface((max_improvement_width, improvement_text_height), pygame.SRCALPHA)
                current_y = 0
                for line_surface in improvement_surfaces:
                    improvement_text_surface.blit(line_surface, (0, current_y))
                    current_y += line_surface.get_height() + text_spacing
        
        # Calculer les dimensions du cadre (texte principal + espacement + texte d'amélioration + padding + bordure)
        content_width = max(main_text_surface.get_width(), 
                           improvement_text_surface.get_width() if improvement_text_surface else 0)
        content_height = main_text_surface.get_height()
        if improvement_text_surface:
            content_height += text_spacing + improvement_text_height
        
        background_color = self.LEVEL_TRANSITION_FRAME_BACKGROUND_COLOR  # Fond blanc
        border_color = self.LEVEL_TRANSITION_FRAME_BORDER_COLOR  # Bordure noire
        border_thickness = int(self.LEVEL_TRANSITION_FRAME_BORDER_THICKNESS * scale_y)
        corner_radius = int(self.LEVEL_TRANSITION_FRAME_CORNER_RADIUS * scale_y)
        padding_x = int(self.LEVEL_TRANSITION_FRAME_PADDING_X * scale_x)
        padding_y = int(self.LEVEL_TRANSITION_FRAME_PADDING_Y * scale_y)
        
        frame_width = content_width + padding_x * 2 + border_thickness * 2
        frame_height = content_height + padding_y * 2 + border_thickness * 2
        
        # Créer la surface finale avec transparence
        final_surface = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
        
        # Dessiner le rectangle de fond (blanc) avec coins arrondis
        pygame.draw.rect(
            final_surface,
            background_color,
            (0, 0, frame_width, frame_height),
            border_radius=corner_radius
        )
        
        # Dessiner la bordure noire (rectangle extérieur)
        pygame.draw.rect(
            final_surface,
            border_color,
            (0, 0, frame_width, frame_height),
            width=border_thickness,
            border_radius=corner_radius
        )
        
        # Calculer les positions pour centrer le contenu
        content_x = padding_x + border_thickness
        content_y = padding_y + border_thickness
        
        # Centrer horizontalement le texte principal
        main_text_x = content_x + (content_width - main_text_surface.get_width()) // 2
        main_text_y = content_y
        final_surface.blit(main_text_surface, (main_text_x, main_text_y))
        
        # Dessiner le texte d'amélioration si disponible
        if improvement_text_surface:
            improvement_text_x = content_x + (content_width - improvement_text_surface.get_width()) // 2
            improvement_text_y = content_y + main_text_surface.get_height() + text_spacing
            final_surface.blit(improvement_text_surface, (improvement_text_x, improvement_text_y))
        
        self.level_transition_text_surface = final_surface

    def _get_player_draw_rect(self, camera_x: float = 0.0) -> pygame.Rect:
        """Obtient le rectangle de rendu du joueur pour le reset du zoom.
        
        Args:
            camera_x: Position horizontale de la caméra
            
        Returns:
            Rectangle pygame représentant la position et la taille du joueur à l'écran
        """
        screen_x = self.x - camera_x
        screen_y = self.y
        if self._dialogue_animation_active:
            screen_y += self._dialogue_animation_offset_y
        
        # Aligner le bas du sprite affiché sur le bas du sprite natif (et donc sur la hitbox)
        bottom_y = screen_y + self.sprite_height / 2
        
        draw_x = round(screen_x - self.display_width / 2)
        draw_y = round(bottom_y - self.display_height)
        
        return pygame.Rect(draw_x, draw_y, self.display_width, self.display_height)

    def _update_level_transition(self, dt: float, camera_x: float = 0.0) -> None:
        """Met à jour l'animation de transition de niveau et l'émission de confettis.
        
        Args:
            dt: Delta time en secondes
            camera_x: Position horizontale de la caméra (pour convertir les coordonnées écran en monde)
        """
        if not self.level_transition_active:
            return
        
        # Gérer les transitions entre les phases
        if self.level_transition_phase == "zoom_in":
            # Vérifier si le zoom avant est terminé
            # Le zoom est terminé quand le zoom actuel est proche du zoom cible (230%)
            if self.level_transition_camera_zoom_controller is None:
                # Pas de contrôleur, passer directement à la phase d'affichage
                self.level_transition_phase = "display"
                self.level_transition_timer = self.level_transition_duration
                self.level_transition_switch_timer = 0.0
            else:
                current_zoom = self.level_transition_camera_zoom_controller.current_zoom
                target_zoom = self.DEFAULT_LEVEL_TRANSITION_ZOOM_PERCENT / 100.0
                # Vérifier si le zoom est proche du zoom cible (tolérance de 0.01)
                if abs(current_zoom - target_zoom) < 0.01:
                    # Le zoom est terminé, passer à la phase d'affichage
                    self.level_transition_phase = "display"
                    self.level_transition_timer = self.level_transition_duration
                    self.level_transition_switch_timer = 0.0
        
        elif self.level_transition_phase == "display":
            # Phase d'affichage : gérer le timer et l'alternance des sprites
            self.level_transition_timer -= dt
            self.level_transition_switch_timer += dt
            
            # Gérer l'alternance des sprites
            if self.level_transition_switch_timer >= self.level_transition_switch_interval:
                self.level_transition_switch_timer = 0.0
                self.level_transition_showing_old = not self.level_transition_showing_old
            
            # Gérer l'émission de confettis
            # Les confettis sont émis en continu jusqu'à 1 seconde avant la fin
            if self.particle_system is not None:
                time_remaining = self.level_transition_timer
                if time_remaining > self.CONFETTI_STOP_BEFORE_END:
                    # Mettre à jour le timer d'émission
                    self._confetti_emission_timer += dt
                    
                    # Vérifier si une nouvelle émission doit être créée
                    if self._confetti_emission_timer >= self.CONFETTI_EMISSION_INTERVAL:
                        self._confetti_emission_timer = 0.0
                        self._emit_confetti_from_text_corners(camera_x)
            
            # Vérifier si la phase d'affichage est terminée
            if self.level_transition_timer <= 0.0:
                # Passer à la phase de reset du zoom
                self.level_transition_phase = "zoom_out"
                if self.level_transition_camera_zoom_controller is not None:
                    # Récupérer le rectangle de rendu du joueur pour le reset du zoom
                    player_draw_rect = self._get_player_draw_rect(camera_x)
                    self.level_transition_camera_zoom_controller.reset_zoom(
                        duration=self.level_transition_zoom_out_duration,
                        player_draw_rect=player_draw_rect
                    )
        
        elif self.level_transition_phase == "zoom_out":
            # Vérifier si le reset du zoom est terminé
            # Le reset est terminé quand le zoom actuel est proche de 1.0 (100%)
            if self.level_transition_camera_zoom_controller is None:
                # Pas de contrôleur, terminer directement l'animation
                self.level_transition_active = False
                self.level_transition_phase = "none"
                self.level_transition_showing_old = False
                # Libérer les ressources temporaires
                self.level_transition_old_sprite_sheet = None
                self.level_transition_text_surface = None
                self.level_transition_camera_zoom_controller = None
                # Réinitialiser le timer de confettis
                self._confetti_emission_timer = 0.0
                self._confetti_last_emission_time = 0.0
            else:
                current_zoom = self.level_transition_camera_zoom_controller.current_zoom
                # Vérifier si le zoom est proche de 1.0 (tolérance de 0.01)
                if abs(current_zoom - 1.0) < 0.01:
                    # Le reset est terminé, terminer complètement l'animation
                    self.level_transition_active = False
                    self.level_transition_phase = "none"
                    self.level_transition_showing_old = False
                    # Libérer les ressources temporaires
                    self.level_transition_old_sprite_sheet = None
                    self.level_transition_text_surface = None
                    self.level_transition_camera_zoom_controller = None
                    # Réinitialiser le timer de confettis
                    self._confetti_emission_timer = 0.0
                    self._confetti_last_emission_time = 0.0

    def _emit_confetti_from_text_corners(self, camera_x: float) -> None:
        """Émet des confettis depuis les coins haut gauche et haut droit du cadre de transition.
        
        Les confettis sont émis depuis les coins arrondis visibles du cadre (incluant padding et bordure),
        pas depuis les coins géométriques du rectangle. Les positions tiennent compte du corner_radius
        pour garantir que l'émission se fait depuis les coins arrondis visibles.
        
        Args:
            camera_x: Position horizontale de la caméra (pour convertir les coordonnées écran en monde)
        """
        if self.particle_system is None or self.level_transition_text_surface is None:
            return
        
        from moteur_jeu_presentation.particles import create_confetti_config
        import time
        
        # Calculer les coordonnées du cadre (en coordonnées écran)
        # Ces coordonnées sont calculées de la même manière que dans _draw_level_transition()
        # level_transition_text_surface contient maintenant le cadre complet (texte + padding + bordure)
        from ..rendering.config import RENDER_WIDTH, RENDER_HEIGHT
        screen_width = RENDER_WIDTH
        screen_height = RENDER_HEIGHT
        frame_width = self.level_transition_text_surface.get_width()
        frame_height = self.level_transition_text_surface.get_height()
        frame_x = (screen_width - frame_width) // 2
        frame_y = (screen_height - frame_height) // 2
        
        # Recalculer le corner_radius de la même manière que dans start_level_transition
        # pour obtenir la position exacte des coins arrondis visibles
        render_width, render_height = get_render_size()
        scale_x, scale_y = compute_design_scale((render_width, render_height))
        corner_radius = int(self.LEVEL_TRANSITION_FRAME_CORNER_RADIUS * scale_y)
        
        # Position du coin haut gauche arrondi du cadre (en coordonnées écran)
        # Dans pygame.draw.rect avec border_radius, le coin arrondi est un quart de cercle.
        # Le centre de l'arc pour le coin haut gauche est à (corner_radius, corner_radius) dans les coordonnées locales.
        # Pour émettre depuis le coin arrondi visible, on utilise le point sur l'arc au niveau du bord supérieur.
        # À y=0 (bord supérieur), le point sur l'arc est à x=corner_radius depuis le coin géométrique.
        # Donc dans les coordonnées écran : frame_x + corner_radius
        left_x_screen = frame_x + corner_radius
        left_y_screen = frame_y
        
        # Position du coin haut droit arrondi du cadre (en coordonnées écran)
        # Pour le coin haut droit, le centre de l'arc est à (frame_width - corner_radius, corner_radius) dans les coordonnées locales.
        # À y=0 (bord supérieur), le point sur l'arc est à x=frame_width - corner_radius depuis le coin géométrique.
        # Donc dans les coordonnées écran : frame_x + frame_width - corner_radius
        right_x_screen = frame_x + frame_width - corner_radius
        right_y_screen = frame_y
        
        # IMPORTANT (zoom caméra):
        # Les confettis de transition de niveau doivent rester attachés aux coins du cadre,
        # qui est un overlay écran. On crée donc ces particules en "screen-space" (coordonnées écran),
        # et elles seront rendues sans être affectées par camera_x/zoom.
        left_x_world = left_x_screen
        left_y_world = left_y_screen
        right_x_world = right_x_screen
        right_y_world = right_y_screen
        
        # Créer les configurations de confetti avec directions en cône
        # Configuration pour le coin haut gauche : cône vers le haut à gauche
        # Angle vers le haut à gauche = -3π/4 radians (-135°)
        # Spread de 30° = π/6 radians
        config_left = create_confetti_config(
            count=self.CONFETTI_COUNT_PER_EMISSION,
            speed=400.0,
            lifetime=2.5,
            size=12,
        )
        # Modifier la direction pour créer un cône vers le haut à gauche
        config_left.direction_type = "custom"
        config_left.direction_angle = self.CONFETTI_LEFT_CONE_ANGLE  # -135° (haut à gauche)
        config_left.direction_spread = self.CONFETTI_CONE_SPREAD  # 30° de dispersion
        
        # Configuration pour le coin haut droit : cône vers le haut à droite
        # Angle vers le haut à droite = -π/4 radians (-45°)
        # Spread de 30° = π/6 radians
        config_right = create_confetti_config(
            count=self.CONFETTI_COUNT_PER_EMISSION,
            speed=400.0,
            lifetime=2.5,
            size=12,
        )
        # Modifier la direction pour créer un cône vers le haut à droite
        config_right.direction_type = "custom"
        config_right.direction_angle = self.CONFETTI_RIGHT_CONE_ANGLE  # -45° (haut à droite)
        config_right.direction_spread = self.CONFETTI_CONE_SPREAD  # 30° de dispersion
        
        # Créer un timestamp unique pour les identifiants
        timestamp = time.time()
        
        # Créer les effets de particules depuis les deux positions avec leurs configurations respectives
        self.particle_system.create_effect(
            left_x_world,
            left_y_world,
            config_left,
            effect_id=f"confetti_level_up_left_{timestamp}",
            screen_space=True,
        )
        
        self.particle_system.create_effect(
            right_x_world,
            right_y_world,
            config_right,
            effect_id=f"confetti_level_up_right_{timestamp}",
            screen_space=True,
        )

    def _draw_level_transition(self, surface: pygame.Surface) -> None:
        """Dessine l'animation de transition de niveau.
        
        Args:
            surface: Surface pygame sur laquelle dessiner
        """
        # N'afficher le texte que pendant la phase "display"
        if not self.level_transition_active or self.level_transition_phase != "display" or self.level_transition_text_surface is None:
            return
        
        # Centrer le texte à l'écran
        screen_width = surface.get_width()
        screen_height = surface.get_height()
        text_x = (screen_width - self.level_transition_text_surface.get_width()) // 2
        text_y = (screen_height - self.level_transition_text_surface.get_height()) // 2
        
        surface.blit(self.level_transition_text_surface, (text_x, text_y))

    @property
    def position_world(self) -> pygame.math.Vector2:
        """Position du joueur dans l'espace du monde."""

        return pygame.math.Vector2(self.x, self.y)

