"""Module d'affichage des statistiques du joueur."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import pygame

from ..rendering.config import get_render_size, get_design_size, compute_design_scale
from .text_utils import render_text, wrap_text
from .animated_sprite import AnimatedSpriteManager
from .stat_bar import get_bar_color, has_stat_progressed, draw_progression_indicator
from .stat_tooltip import create_tooltip, get_tooltip_position, check_icon_hover
from .character_presentation import draw_character_name, draw_character_presentation, draw_presentation_section

if TYPE_CHECKING:
    from ..entities.player import Player

logger = logging.getLogger(__name__)


class PlayerStatsDisplay:
    """Interface d'affichage des statistiques du joueur."""

    def __init__(
        self,
        player: "Player",
        screen_width: int,
        screen_height: int,
        font: Optional[pygame.font.Font] = None,
        font_size: int = 28,  # Augmenté de 1/3 (21 * 4/3 = 28)
        title_font_size: int = 37,
        panel_width: int = 600,
        panel_height: int = 400,
        padding: int = 20,
        stat_bar_width: int = 200,
        stat_bar_height: int = 19,
        overlay_alpha: int = 180,
        bg_color: Tuple[int, int, int] = (40, 40, 50),
        border_color: Tuple[int, int, int] = (200, 200, 200),
        border_width: int = 3,
        title_color: Tuple[int, int, int] = (255, 255, 255),
        stat_name_color: Tuple[int, int, int] = (240, 240, 240),
        stat_value_color: Tuple[int, int, int] = (255, 255, 255),
        level_color: Tuple[int, int, int] = (255, 215, 0),
        sprite_scale: float = 4.0,
        rotation_speed: float = 0.5,
        info_icon_size: int = 32,  # Augmenté par 2 (16 * 2 = 32)
        info_icon_color: Tuple[int, int, int] = (200, 200, 200),
        tooltip_bg_color: Tuple[int, int, int, int] = (30, 30, 40, 240),
        tooltip_border_color: Tuple[int, int, int] = (200, 200, 200),
        tooltip_text_color: Tuple[int, int, int] = (255, 255, 255),
        tooltip_padding: int = 7,
        tooltip_max_width: int = 600,
        tooltip_font_size: int = 21,
        character_presentation: Optional[Dict[str, Any]] = None,
        presentation_name_font_size: int = 32,
        presentation_section_font_size: int = 16,
        presentation_text_font_size: int = 18,
        presentation_name_color: Tuple[int, int, int] = (255, 215, 0),
        presentation_section_color: Tuple[int, int, int] = (200, 200, 200),
        presentation_text_color: Tuple[int, int, int] = (240, 240, 240),
        presentation_padding: int = 17,
        presentation_section_spacing: int = 12,
        background_image_path: Optional[str] = None,
        fonts_dir: Optional[str] = None,
        title_panel_rect: Optional[Tuple[int, int, int, int]] = None,
        main_panel_rect: Optional[Tuple[int, int, int, int]] = None,
        offset_x: int = 70,
        offset_y: int = 10,
    ) -> None:
        """Initialise l'interface d'affichage des statistiques.

        Args:
            player: Instance du joueur dont on affiche les statistiques
            screen_width: Largeur de l'écran
            screen_height: Hauteur de l'écran
            font: Police à utiliser pour le texte (optionnel)
            font_size: Taille de la police pour les statistiques (défaut: 28 pixels dans le repère 1280x720)
            title_font_size: Taille de la police pour le titre (défaut: 37 pixels dans le repère 1280x720)
            panel_width: Largeur du panneau principal
            panel_height: Hauteur du panneau principal
            padding: Espacement interne du panneau
            stat_bar_width: Largeur des jauges de statistiques
            stat_bar_height: Hauteur des jauges de statistiques (défaut: 19 pixels dans le repère 1280x720)
            overlay_alpha: Transparence de l'overlay (0-255)
            bg_color: Couleur de fond du panneau (RGB)
            border_color: Couleur de la bordure du panneau (RGB)
            border_width: Épaisseur de la bordure
            title_color: Couleur du titre (RGB)
            stat_name_color: Couleur des noms de statistiques (RGB)
            stat_value_color: Couleur des valeurs de statistiques (RGB)
            level_color: Couleur de l'affichage du niveau (RGB)
            sprite_scale: Facteur d'échelle pour le sprite du joueur (défaut: 4.0 = 400%)
            rotation_speed: Durée en secondes pour afficher chaque sprite de la rotation (défaut: 0.5)
            info_icon_size: Taille de l'icône d'information en pixels (défaut: 32 dans le repère 1280x720)
            tooltip_font_size: Taille de la police du tooltip en pixels (défaut: 21 dans le repère 1280x720)
            info_icon_color: Couleur de l'icône d'information (RGB, défaut: (200, 200, 200))
            tooltip_bg_color: Couleur de fond du tooltip avec alpha (RGBA, défaut: (30, 30, 40, 240))
            tooltip_border_color: Couleur de la bordure du tooltip (RGB, défaut: (200, 200, 200))
            tooltip_text_color: Couleur du texte du tooltip (RGB, défaut: (255, 255, 255))
            tooltip_padding: Espacement interne du tooltip en pixels (défaut: 7 dans le repère 1280x720)
            tooltip_max_width: Largeur maximale du tooltip en pixels (défaut: 600 dans le repère 1280x720)
            character_presentation: Surcharge pour tests ; si None, listes lues depuis stats_config ([presentation] dans player_stats.toml)
            presentation_name_font_size: Taille de la police pour le nom du personnage (défaut: 32 dans le repère 1280x720)
            presentation_section_font_size: Taille de la police pour les titres de section (défaut: 16 dans le repère 1280x720)
            presentation_text_font_size: Taille de la police pour le texte de présentation (défaut: 18 dans le repère 1280x720)
            presentation_name_color: Couleur du nom du personnage (RGB, défaut: (255, 215, 0) = doré)
            presentation_section_color: Couleur des titres de section (RGB, défaut: (200, 200, 200))
            presentation_text_color: Couleur du texte de présentation (RGB, défaut: (240, 240, 240))
            presentation_padding: Espacement horizontal de la section de présentation (défaut: 17 dans le repère 1280x720)
            presentation_section_spacing: Espacement vertical entre les sections (défaut: 12 dans le repère 1280x720)
            background_image_path: Chemin vers l'image de fond du panneau (défaut: "sprite/interface/affichage_personnage.png")
            fonts_dir: Répertoire contenant les fichiers de polices (défaut: "fonts/" ou répertoire système)
            title_panel_rect: Rectangle du panneau rectangulaire supérieur (x, y, width, height) en coordonnées relatives à l'image originale. Si None, les coordonnées sont détectées automatiquement ou utilisent des valeurs par défaut
            main_panel_rect: Rectangle du panneau central principal (x, y, width, height) en coordonnées relatives à l'image originale. Si None, les coordonnées sont détectées automatiquement ou utilisent des valeurs par défaut
            offset_x: Décalage horizontal en pixels pour le sprite, la présentation et les statistiques (défaut: 70 dans le repère 1280x720)
            offset_y: Décalage vertical en pixels pour le sprite, la présentation et les statistiques (défaut: 0 dans le repère 1280x720)
        """
        self.player = player
        lm_stats = player.level_manager.stats_config
        if lm_stats is None:
            raise ValueError(
                "PlayerStatsDisplay exige player.level_manager.stats_config "
                "(display_name depuis config/player_stats.toml)."
            )
        self.character_display_name = lm_stats.display_name
        self.is_visible = False
        
        # Obtenir les résolutions de design et de rendu
        design_width, design_height = get_design_size()  # 1920x1080
        render_width, render_height = get_render_size()  # 1920x1080
        self.screen_width = render_width
        self.screen_height = render_height
        
        # Calculer le facteur d'échelle pour convertir du repère de design vers la résolution de rendu
        scale_x, scale_y = compute_design_scale((render_width, render_height))
        # Actuellement, design et render sont identiques, donc scale_x = scale_y = 1.0
        # Mais on utilise cette fonction pour être compatible avec d'éventuels changements futurs
        self._design_scale_x = scale_x
        self._design_scale_y = scale_y
        
        # Toutes les valeurs de base sont définies dans le repère de design (1920x1080)
        # Le panneau prend tout l'écran avec un padding réduit (45px en 1920x1080 = 30px * 1.5)
        base_panel_padding_design = 45  # 30 * 1.5 (converti de 1280x720 vers 1920x1080)
        self.panel_padding = int(base_panel_padding_design * scale_x)
        self.panel_width = self.screen_width - (self.panel_padding * 2)
        self.panel_height = self.screen_height - (self.panel_padding * 2)
        
        # Convertir les valeurs des paramètres du repère de design vers la résolution de rendu
        # Les valeurs par défaut sont en 1280x720, donc on les convertit d'abord vers 1920x1080
        base_padding_design = int(padding * 1.5) if padding == 20 else padding  # 20 * 1.5 = 30
        self.padding = int(base_padding_design * scale_x)
        
        # La largeur des barres est calculée dynamiquement pour utiliser l'espace disponible
        base_stat_bar_width_design = int(stat_bar_width * 1.5) if stat_bar_width == 200 else stat_bar_width
        base_stat_bar_height_design = int(stat_bar_height * 1.5) if stat_bar_height == 19 else stat_bar_height
        self.stat_bar_width = int(base_stat_bar_width_design * scale_x)
        self.stat_bar_height = int(base_stat_bar_height_design * scale_y)
        self.font_size = font_size  # Stocker font_size pour l'utiliser dans _create_panel
        self.title_font_size = title_font_size  # Stocker title_font_size pour l'utiliser dans _create_panel
        self.overlay_alpha = overlay_alpha
        self.bg_color = bg_color
        self.border_color = border_color
        self.border_width = border_width
        self.title_color = title_color
        self.stat_name_color = stat_name_color
        self.stat_value_color = stat_value_color
        self.level_color = level_color
        self.rotation_speed = rotation_speed
        # Convertir info_icon_size du repère de design vers la résolution de rendu
        base_info_icon_size_design = int(info_icon_size * 1.5) if info_icon_size == 32 else info_icon_size  # 32 * 1.5 = 48
        self.info_icon_size = int(base_info_icon_size_design * scale_x)
        self.info_icon_color = info_icon_color
        self.tooltip_bg_color = tooltip_bg_color
        self.tooltip_border_color = tooltip_border_color
        self.tooltip_text_color = tooltip_text_color
        self.tooltip_padding = tooltip_padding
        self.tooltip_max_width = tooltip_max_width
        self.tooltip_font_size = tooltip_font_size

        # Section de présentation du personnage
        self.character_presentation = (
            character_presentation
            if character_presentation is not None
            else lm_stats.get_character_presentation_dict()
        )
        self.presentation_name_font_size = presentation_name_font_size
        self.presentation_section_font_size = presentation_section_font_size
        self.presentation_text_font_size = presentation_text_font_size
        self.presentation_name_color = presentation_name_color
        self.presentation_section_color = presentation_section_color
        self.presentation_text_color = presentation_text_color
        self.presentation_padding = presentation_padding
        self.presentation_section_spacing = presentation_section_spacing

        # Image de fond et panneaux
        # Résoudre le chemin du projet (depuis src/moteur_jeu_presentation/ui/player_stats_display.py)
        self._project_root = Path(__file__).parent.parent.parent.parent
        self.background_image_path = background_image_path or "sprite/interface/affichage_personnage.png"
        self.fonts_dir = fonts_dir or "fonts"
        self.title_panel_rect_original = title_panel_rect
        self.main_panel_rect_original = main_panel_rect
        
        # Convertir les offsets du repère de design vers la résolution de rendu
        # Les valeurs par défaut sont en 1280x720, donc on les convertit d'abord vers 1920x1080
        base_offset_x_design = int(offset_x * 1.5) if offset_x == 70 else offset_x  # 70 * 1.5 = 105
        base_offset_y_design = int(offset_y * 1.5) if offset_y == 10 else offset_y  # 10 * 1.5 = 15
        self.offset_x = int(base_offset_x_design * scale_x)
        self.offset_y = int(base_offset_y_design * scale_y)
        
        # Image de fond et rectangles des panneaux
        self.background_image: Optional[pygame.Surface] = None
        self.background_image_scaled: Optional[pygame.Surface] = None
        self.title_panel_rect: Optional[pygame.Rect] = None
        self.main_panel_rect: Optional[pygame.Rect] = None
        self._cached_panel_size: Optional[Tuple[int, int]] = None

        # Mise en page dynamique (calculée lors de la création du panneau)
        self._sprite_frame_rect: Optional[pygame.Rect] = None


        # Gestion du tooltip
        self.hovered_stat_identifier: Optional[str] = None
        self.tooltip_surface: Optional[pygame.Surface] = None
        self.tooltip_rect: Optional[pygame.Rect] = None
        self.icon_rects: Dict[str, pygame.Rect] = {}  # Stocke les rectangles des icônes par stat_identifier

        # Charger l'image de fond
        self.background_image = self._load_background_image()
        
        # Détecter les rectangles des panneaux
        if self.background_image is not None:
            title_rect, main_rect = self._detect_panel_rects()
            if title_rect is not None:
                self.title_panel_rect_original = (title_rect[0], title_rect[1], title_rect[2], title_rect[3])
            if main_rect is not None:
                self.main_panel_rect_original = (main_rect[0], main_rect[1], main_rect[2], main_rect[3])

        # Initialiser les polices pixel art avec fallback
        # Les polices seront recréées avec la bonne taille lors de la création du panneau
        # Ici on initialise juste les polices de base
        self.presentation_name_font: Optional[pygame.font.Font] = None
        self.presentation_section_font: Optional[pygame.font.Font] = None
        self.presentation_text_font: Optional[pygame.font.Font] = None
        self.stat_font: Optional[pygame.font.Font] = None
        self.tooltip_font: Optional[pygame.font.Font] = None
        self.info_icon_font: Optional[pygame.font.Font] = None
        
        # Toutes les valeurs de base sont maintenant définies dans le repère de design (1920x1080)
        # Convertir les valeurs de 1280x720 vers 1920x1080 (multiplier par 1.5)
        # Les valeurs par défaut des paramètres sont déjà en 1280x720, donc on les convertit
        self._base_font_size = int(font_size * 1.5)  # 28 * 1.5 = 42
        self._base_title_font_size = int(title_font_size * 1.5)  # 37 * 1.5 = 55.5 -> 55
        self._base_tooltip_font_size = int(tooltip_font_size * 1.5)  # 21 * 1.5 = 31.5 -> 31
        self._base_presentation_name_font_size = int(presentation_name_font_size * 1.5)  # 32 * 1.5 = 48
        self._base_presentation_section_font_size = int(presentation_section_font_size * 1.5)  # 16 * 1.5 = 24
        self._base_presentation_text_font_size = int(presentation_text_font_size * 1.5)  # 18 * 1.5 = 27
        # Espacements de présentation
        self._base_presentation_padding = int(presentation_padding * 1.5)  # 17 * 1.5 = 25.5 -> 25
        self._base_presentation_section_spacing = int(presentation_section_spacing * 1.5)  # 12 * 1.5 = 18
        # Autres espacements hardcodés de la présentation (définis dans le repère de design 1920x1080)
        # Ces valeurs sont utilisées dans _draw_presentation_section, _draw_character_presentation et _create_panel
        self._base_presentation_name_spacing = int(13 * 1.5)  # 19.5 -> 19
        self._base_presentation_bullet_spacing = int(8 * 1.5)  # 12
        self._base_presentation_title_spacing = int(5 * 1.5)  # 7.5 -> 7
        self._base_presentation_item_spacing = int(3 * 1.5)  # 4.5 -> 4
        # Valeurs pour le positionnement de la section de présentation
        self._base_sprite_frame_width = int(267 * 1.5)  # 400.5 -> 400
        self._base_sprite_frame_padding = int(13 * 1.5)  # 19.5 -> 19
        self._base_sprite_frame_height = int(133 * 1.5)  # 199.5 -> 199
        self._base_spacing_between = int(21 * 1.5)  # 31.5 -> 31
        self._base_presentation_min_width = int(213 * 1.5)  # 319.5 -> 319
        self._base_section_top_y_fallback = int(67 * 1.5)  # 100.5 -> 100
        self._base_section_bottom_spacing = int(20 * 1.5)  # 30
        # Autres valeurs hardcodées converties de 1280x720 vers 1920x1080
        self._base_reserved_space_for_stats = int(180 * 1.5)  # 270 (espace réservé pour les statistiques)
        self._base_column_spacing = int(10 * 1.5)  # 15 (espacement entre les colonnes de stats)
        
        # Convertir les valeurs vers la résolution de rendu en utilisant compute_design_scale
        self.font_size = int(self._base_font_size * scale_x)
        self.title_font_size = int(self._base_title_font_size * scale_x)
        self.tooltip_font_size = int(self._base_tooltip_font_size * scale_x)
        self.presentation_name_font_size = int(self._base_presentation_name_font_size * scale_x)
        self.presentation_section_font_size = int(self._base_presentation_section_font_size * scale_x)
        self.presentation_text_font_size = int(self._base_presentation_text_font_size * scale_x)
        self.presentation_padding = int(self._base_presentation_padding * scale_x)
        self.presentation_section_spacing = int(self._base_presentation_section_spacing * scale_y)
        
        # Initialiser les polices de base (seront remplacées par les polices pixel art lors du rendu)
        if font is None:
            try:
                self.font = pygame.font.SysFont("arial", self._base_font_size, bold=False)
                self.title_font = pygame.font.SysFont("arial", self._base_title_font_size, bold=True)
            except pygame.error:
                self.font = pygame.font.SysFont("sans-serif", self._base_font_size, bold=False)
                self.title_font = pygame.font.SysFont("sans-serif", self._base_title_font_size, bold=True)
        else:
            self.font = font
            # Créer une version bold pour le titre
            try:
                self.title_font = pygame.font.SysFont(font.get_fonts()[0] if hasattr(font, "get_fonts") else "arial", self._base_title_font_size, bold=True)
            except (pygame.error, AttributeError):
                self.title_font = self.font

        # Surfaces mises en cache
        self.overlay_surface: Optional[pygame.Surface] = None
        self.panel_surface: Optional[pygame.Surface] = None
        self._cached_screen_size: Optional[Tuple[int, int]] = None  # Taille d'écran mise en cache
        
        # Gestionnaire de sprites animés
        self.sprite_manager = AnimatedSpriteManager(
            player=player,
            sprite_scale=sprite_scale,
            rotation_speed=rotation_speed,
        )

    def toggle(self) -> None:
        """Bascule l'affichage (affiche si masqué, masque si affiché)."""
        self.is_visible = not self.is_visible
        if self.is_visible:
            # Invalider le cache pour forcer la régénération
            self._invalidate_cache()
            # Réinitialiser l'animation de rotation
            self.sprite_manager.invalidate_cache()

    def show(self) -> None:
        """Affiche l'interface."""
        self.is_visible = True
        self._invalidate_cache()
        # Réinitialiser l'animation de rotation
        self.sprite_manager.invalidate_cache()

    def hide(self) -> None:
        """Masque l'interface."""
        self.is_visible = False
        # Réinitialiser le tooltip
        self.hovered_stat_identifier = None
        self.tooltip_surface = None
        self.tooltip_rect = None

    def handle_mouse_event(self, event: pygame.event.Event) -> None:
        """Gère les événements de souris (MOUSEMOTION) pour détecter le survol des icônes.

        Args:
            event: Événement pygame de type MOUSEMOTION
        """
        if event.type != pygame.MOUSEMOTION:
            return

        mouse_pos = event.pos
        hovered_stat = check_icon_hover(mouse_pos, self.icon_rects, self.panel_padding)

        if hovered_stat != self.hovered_stat_identifier:
            self.hovered_stat_identifier = hovered_stat
            # Recréer le tooltip si nécessaire
            if hovered_stat is not None:
                current_level = self.player.level_manager.level
                self.tooltip_surface = create_tooltip(
                    self.player,
                    hovered_stat,
                    self.tooltip_font,
                    self.tooltip_font_size,
                    self.tooltip_max_width,
                    self.tooltip_padding,
                    self.tooltip_bg_color,
                    self.tooltip_border_color,
                    self.tooltip_text_color,
                    1.0,
                )
                if self.tooltip_surface is not None and hovered_stat in self.icon_rects:
                    icon_rect = self.icon_rects[hovered_stat]
                    # Convertir le rectangle de l'icône en coordonnées écran
                    # Le panneau est positionné avec un padding adaptatif
                    panel_x = self.panel_padding
                    panel_y = self.panel_padding
                    screen_icon_rect = pygame.Rect(
                        panel_x + icon_rect.x,
                        panel_y + icon_rect.y,
                        icon_rect.width,
                        icon_rect.height
                    )
                    tooltip_pos = get_tooltip_position(
                        self.tooltip_surface,
                        screen_icon_rect,
                        self.screen_width,
                        self.screen_height,
                    )
                    self.tooltip_rect = pygame.Rect(
                        tooltip_pos[0],
                        tooltip_pos[1],
                        self.tooltip_surface.get_width(),
                        self.tooltip_surface.get_height()
                    )
            else:
                self.tooltip_surface = None
                self.tooltip_rect = None

    def draw(self, surface: pygame.Surface, dt: float = 0.0) -> None:
        """Dessine l'interface sur la surface (si visible) et met à jour l'animation de rotation.

        Args:
            surface: Surface pygame sur laquelle dessiner
            dt: Delta time en secondes pour l'animation de rotation
        """
        if not self.is_visible:
            return

        # Mettre à jour l'animation de rotation
        self.sprite_manager.update_rotation(dt)

        # Utiliser le facteur d'échelle de design pour garder le même affichage
        scale_factor = self._design_scale_x  # Utiliser scale_x pour la cohérence (actuellement 1.0)
        scale_changed = False

        # Créer l'overlay si nécessaire
        if self.overlay_surface is None:
            self.overlay_surface = self._create_overlay()

        # Créer le panneau si nécessaire (ou si le niveau a changé, ou si l'échelle a changé)
        current_level = self.player.level_manager.level
        level_changed = self.sprite_manager._cached_level != current_level
        if self.panel_surface is None or level_changed or scale_changed:
            # Extraire les sprites si le niveau a changé
            if level_changed:
                self.sprite_manager.extract_player_sprites()
            self.panel_surface = self._create_panel()
            
            # Si le niveau a changé et qu'une icône est survolée, recréer le tooltip
            if level_changed and self.hovered_stat_identifier is not None:
                # Recréer le tooltip avec le nouveau niveau
                self.tooltip_surface = create_tooltip(
                    self.player,
                    self.hovered_stat_identifier,
                    self.tooltip_font,
                    self.tooltip_font_size,
                    self.tooltip_max_width,
                    self.tooltip_padding,
                    self.tooltip_bg_color,
                    self.tooltip_border_color,
                    self.tooltip_text_color,
                    1.0,
                )
                if self.tooltip_surface is not None and self.hovered_stat_identifier in self.icon_rects:
                    icon_rect = self.icon_rects[self.hovered_stat_identifier]
                    # Convertir le rectangle de l'icône en coordonnées écran
                    # Le panneau est positionné avec un padding adaptatif
                    panel_x = self.panel_padding
                    panel_y = self.panel_padding
                    screen_icon_rect = pygame.Rect(
                        panel_x + icon_rect.x,
                        panel_y + icon_rect.y,
                        icon_rect.width,
                        icon_rect.height
                    )
                    tooltip_pos = get_tooltip_position(
                        self.tooltip_surface,
                        screen_icon_rect,
                        self.screen_width,
                        self.screen_height,
                    )
                    self.tooltip_rect = pygame.Rect(
                        tooltip_pos[0],
                        tooltip_pos[1],
                        self.tooltip_surface.get_width(),
                        self.tooltip_surface.get_height()
                    )
                else:
                    self.tooltip_rect = None

        # Dessiner l'overlay (toujours en 1280×720)
        surface.blit(self.overlay_surface, (0, 0))

        # Dessiner le panneau (toujours en 1280×720 avec padding de 30px)
        # Le panneau est positionné avec un padding de 30px
        panel_x = self.panel_padding
        panel_y = self.panel_padding
        surface.blit(self.panel_surface, (panel_x, panel_y))

        # Dessiner le sprite du joueur animé (au-dessus du panneau)
        self._draw_animated_sprite(surface, panel_x, panel_y)

        # Dessiner le tooltip si nécessaire (au-dessus de tout)
        if self.tooltip_surface is not None and self.tooltip_rect is not None:
            surface.blit(self.tooltip_surface, self.tooltip_rect)

    def _invalidate_cache(self) -> None:
        """Invalide le cache des surfaces."""
        self.overlay_surface = None
        self.panel_surface = None
        self._cached_screen_size = None
        self.background_image_scaled = None
        self._cached_panel_size = None
        self.sprite_manager.invalidate_cache()
    
    def _load_background_image(self) -> Optional[pygame.Surface]:
        """Charge l'image de fond depuis le chemin spécifié.
        
        Returns:
            Surface de l'image de fond, ou None si l'image n'est pas trouvée
        """
        try:
            image_path = Path(self.background_image_path)
            if not image_path.is_absolute():
                image_path = self._project_root / image_path
            
            if not image_path.exists():
                logger.warning(f"Image de fond introuvable: {image_path}")
                return None
            
            image = pygame.image.load(str(image_path)).convert_alpha()
            return image
        except Exception as e:
            logger.warning(f"Erreur lors du chargement de l'image de fond: {e}")
            return None

    def _scale_background_image(self, width: int, height: int) -> Optional[pygame.Surface]:
        """Redimensionne l'image de fond pour s'adapter aux dimensions du panneau.
        
        Args:
            width: Largeur cible
            height: Hauteur cible
            
        Returns:
            Surface de l'image redimensionnée, ou None si l'image n'est pas chargée
        """
        if self.background_image is None:
            return None
        
        # Vérifier si l'image est déjà en cache pour cette taille
        if self.background_image_scaled is not None:
            if self._cached_panel_size == (width, height):
                return self.background_image_scaled
        
        # Calculer les nouvelles dimensions en conservant les proportions
        img_width = self.background_image.get_width()
        img_height = self.background_image.get_height()
        
        # Calculer le ratio pour remplir le panneau (utiliser le ratio maximum pour agrandir l'image)
        # Cela permet d'avoir un panneau central plus grand pour contenir tout le texte
        width_ratio = width / img_width
        height_ratio = height / img_height
        ratio = max(width_ratio, height_ratio)  # Utiliser le ratio le plus grand pour agrandir l'image et remplir le panneau
        
        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)
        
        # OPTIMISATION: Éviter smoothscale si la taille cible est identique à la taille originale
        target_size = (new_width, new_height)
        if self.background_image.get_size() == target_size:
            # Pas besoin de redimensionner, utiliser directement l'image
            scaled_image = self.background_image
        else:
            # Redimensionner l'image
            scaled_image = pygame.transform.smoothscale(self.background_image, target_size)
        
        # Mettre en cache
        self.background_image_scaled = scaled_image
        self._cached_panel_size = (width, height)
        
        return scaled_image

    def _detect_panel_rects(self) -> Tuple[Optional[Tuple[int, int, int, int]], Optional[Tuple[int, int, int, int]]]:
        """Détecte ou calcule les rectangles des panneaux depuis l'image.
        
        Returns:
            Tuple contenant (title_panel_rect, main_panel_rect) en coordonnées relatives à l'image originale
        """
        if self.background_image is None:
            return None, None
        
        # Si les rectangles sont déjà définis manuellement, les utiliser
        if self.title_panel_rect_original is not None and self.main_panel_rect_original is not None:
            return self.title_panel_rect_original, self.main_panel_rect_original
        
        img_width = self.background_image.get_width()
        img_height = self.background_image.get_height()
        
        # Valeurs par défaut basées sur des proportions typiques de l'image
        # Ces valeurs peuvent être ajustées selon la structure réelle de l'image
        # Panneau rectangulaire supérieur : environ 60% de la largeur, 15% de la hauteur, centré horizontalement
        title_panel_width = int(img_width * 0.6)
        title_panel_height = int(img_height * 0.15)
        title_panel_x = (img_width - title_panel_width) // 2
        title_panel_y = int(img_height * 0.05)  # 5% du haut
        
        # Panneau central principal : environ 90% de la largeur, 70% de la hauteur, centré horizontalement
        main_panel_width = int(img_width * 0.9)
        main_panel_height = int(img_height * 0.7)
        main_panel_x = (img_width - main_panel_width) // 2
        main_panel_y = int(img_height * 0.2)  # 20% du haut
        
        title_rect = (title_panel_x, title_panel_y, title_panel_width, title_panel_height)
        main_rect = (main_panel_x, main_panel_y, main_panel_width, main_panel_height)
        
        return title_rect, main_rect

    def _update_panel_rects(self, panel_width: int, panel_height: int) -> None:
        """Met à jour les rectangles des panneaux en fonction de la taille de l'image redimensionnée.
        
        Args:
            panel_width: Largeur du panneau
            panel_height: Hauteur du panneau
        """
        if self.background_image is None or self.background_image_scaled is None:
            return
        
        # Obtenir les rectangles originaux
        title_rect_orig, main_rect_orig = self._detect_panel_rects()
        if title_rect_orig is None or main_rect_orig is None:
            return
        
        # Calculer le ratio de redimensionnement
        orig_width = self.background_image.get_width()
        orig_height = self.background_image.get_height()
        scaled_width = self.background_image_scaled.get_width()
        scaled_height = self.background_image_scaled.get_height()
        
        width_ratio = scaled_width / orig_width
        height_ratio = scaled_height / orig_height
        
        # Mettre à l'échelle les rectangles
        title_x = int(title_rect_orig[0] * width_ratio)
        title_y = int(title_rect_orig[1] * height_ratio)
        title_w = int(title_rect_orig[2] * width_ratio)
        title_h = int(title_rect_orig[3] * height_ratio)
        
        main_x = int(main_rect_orig[0] * width_ratio)
        main_y = int(main_rect_orig[1] * height_ratio)
        main_w = int(main_rect_orig[2] * width_ratio)
        main_h = int(main_rect_orig[3] * height_ratio)
        
        # Centrer l'image dans le panneau si nécessaire
        offset_x = (panel_width - scaled_width) // 2
        offset_y = (panel_height - scaled_height) // 2
        
        self.title_panel_rect = pygame.Rect(
            offset_x + title_x,
            offset_y + title_y,
            title_w,
            title_h
        )
        
        self.main_panel_rect = pygame.Rect(
            offset_x + main_x,
            offset_y + main_y,
            main_w,
            main_h
        )

    def _load_font(self, font_name: str, font_size: int, fallback_fonts: Optional[List[str]] = None) -> pygame.font.Font:
        """Charge une police depuis le répertoire des polices avec système de fallback.
        
        Args:
            font_name: Nom de la police (sans extension)
            font_size: Taille de la police
            fallback_fonts: Liste des noms de polices de fallback (optionnel)
            
        Returns:
            Police pygame chargée
        """
        if fallback_fonts is None:
            fallback_fonts = ["arial", "sans-serif"]
        
        # Noms de fichiers possibles pour la police
        font_files = [
            f"{font_name}-Regular.ttf",
            f"{font_name}.ttf",
            f"{font_name}-Regular.otf",
            f"{font_name}.otf",
        ]
        
        # Essayer de charger depuis le répertoire des polices
        fonts_dir_path = Path(self.fonts_dir)
        if not fonts_dir_path.is_absolute():
            fonts_dir_path = self._project_root / fonts_dir_path
        
        for font_file in font_files:
            font_path = fonts_dir_path / font_file
            if font_path.exists():
                try:
                    return pygame.font.Font(str(font_path), font_size)
                except pygame.error as e:
                    logger.warning(f"Erreur lors du chargement de la police {font_path}: {e}")
                    continue
        
        # Essayer de charger depuis le répertoire système (selon l'OS)
        # Sur macOS: /Library/Fonts, /System/Library/Fonts, ~/Library/Fonts
        # Sur Linux: /usr/share/fonts, ~/.fonts
        # Sur Windows: C:\Windows\Fonts
        import platform
        system_font_dirs = []
        if platform.system() == "Darwin":  # macOS
            system_font_dirs = [
                Path("/Library/Fonts"),
                Path("/System/Library/Fonts"),
                Path.home() / "Library/Fonts",
            ]
        elif platform.system() == "Linux":
            system_font_dirs = [
                Path("/usr/share/fonts"),
                Path.home() / ".fonts",
            ]
        elif platform.system() == "Windows":
            system_font_dirs = [
                Path("C:/Windows/Fonts"),
            ]
        
        for font_dir in system_font_dirs:
            for font_file in font_files:
                font_path = font_dir / font_file
                if font_path.exists():
                    try:
                        return pygame.font.Font(str(font_path), font_size)
                    except pygame.error:
                        continue
        
        # Fallback vers une police système
        logger.warning(f"Police {font_name} introuvable, utilisation d'une police système par défaut")
        for fallback in fallback_fonts:
            try:
                return pygame.font.SysFont(fallback, font_size)
            except pygame.error:
                continue
        
        # Dernier recours
        return pygame.font.Font(None, font_size)

    def _create_overlay(self) -> pygame.Surface:
        """Crée la surface de l'overlay semi-transparent.

        L'overlay est toujours créé en 1280×720 (résolution de référence).

        Returns:
            Surface de l'overlay (1280×720)
        """
        # Toujours créer l'overlay en 1280×720
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(self.overlay_alpha)
        return overlay

    def _create_panel(self) -> pygame.Surface:
        """Crée la surface du panneau principal.

        Returns:
            Surface du panneau
        """
        # Le panneau est créé dans la résolution de rendu
        # Utiliser directement les dimensions calculées lors de l'initialisation
        panel_width = self.panel_width
        panel_height = self.panel_height
        
        # Utiliser le facteur d'échelle de design pour garder le même affichage
        scale_factor = self._design_scale_x  # Utiliser scale_x pour la cohérence (actuellement 1.0)
        scaled_padding = int(self.padding * scale_factor)  # = self.padding
        # Taille des polices utilisée directement (pas de scaling)
        scaled_font_size = int(self.font_size * scale_factor)  # = self.font_size
        scaled_stat_bar_height = int(self.stat_bar_height * scale_factor)  # = self.stat_bar_height
        scaled_info_icon_size = int(self.info_icon_size * scale_factor)  # = self.info_icon_size

        # Recréer les polices avec la taille adaptée
        try:
            scaled_font = pygame.font.SysFont("arial", scaled_font_size, bold=False)
        except pygame.error:
            scaled_font = pygame.font.SysFont("sans-serif", scaled_font_size, bold=False)

        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)

        # Dessiner l'image de fond si disponible
        background_scaled = self._scale_background_image(panel_width, panel_height)
        if background_scaled is not None:
            # Centrer l'image dans le panneau
            bg_x = (panel_width - background_scaled.get_width()) // 2
            bg_y = (panel_height - background_scaled.get_height()) // 2
            panel.blit(background_scaled, (bg_x, bg_y))
            
            # Mettre à jour les rectangles des panneaux
            self._update_panel_rects(panel_width, panel_height)
        else:
            # Fallback : dessiner le fond de couleur unie
            scaled_border_width = max(1, int(self.border_width * scale_factor))
            pygame.draw.rect(panel, self.bg_color, (0, 0, panel_width, panel_height))
            pygame.draw.rect(
                panel,
                self.border_color,
                (0, 0, panel_width, panel_height),
                scaled_border_width,
            )

        # Charger les polices pixel art avec la taille adaptée
        # Utiliser directement les valeurs en 1280x720
        scaled_name_font_size = int(self.presentation_name_font_size * scale_factor)
        scaled_section_font_size = int(self.presentation_section_font_size * scale_factor)
        scaled_text_font_size = int(self.presentation_text_font_size * scale_factor)
        scaled_stat_font_size = int(self.font_size * scale_factor)
        scaled_tooltip_font_size = int(self.tooltip_font_size * scale_factor)
        # Calculer la taille de la police de l'icône en fonction de la taille de l'icône
        # La police doit être adaptée à la taille de l'icône (environ 70-80% de la taille de l'icône)
        scaled_info_icon_font_size = max(10, int(self.info_icon_size * 0.75 * scale_factor))
        
        # Charger les polices pixel art
        self.presentation_name_font = self._load_font("VT323", scaled_name_font_size, ["arial", "sans-serif"])
        self.presentation_section_font = self._load_font("Silkscreen", scaled_section_font_size, ["arial", "sans-serif"])
        self.presentation_text_font = self._load_font("VT323", scaled_text_font_size, ["arial", "sans-serif"])
        self.stat_font = self._load_font("VT323", scaled_stat_font_size, ["arial", "sans-serif"])
        self.tooltip_font = self._load_font("VT323", scaled_tooltip_font_size, ["arial", "sans-serif"])
        self.info_icon_font = self._load_font("VT323", scaled_info_icon_font_size, ["arial", "sans-serif"])
        
        # Utiliser les polices pixel art pour les statistiques
        scaled_font = self.stat_font

        # Réinitialiser la position du cadre du sprite
        self._sprite_frame_rect = None

        # Section titre : nom du personnage dans le panneau rectangulaire supérieur
        name_height = draw_character_name(
            panel,
            self.title_panel_rect,
            self.presentation_name_font,
            self.presentation_name_color,
            self.player.level_manager.level,
            self.character_display_name,
        )

        # Section supérieure : sprite à gauche, présentation à droite, dans le panneau central principal
        # Si le panneau central principal est défini, utiliser ses coordonnées
        if self.main_panel_rect is not None:
            section_top_y = self.main_panel_rect.y
            available_width = self.main_panel_rect.width
            main_panel_x = self.main_panel_rect.x
        else:
            # Fallback si le panneau central n'est pas défini
            # Utiliser directement la valeur en 1280x720
            scaled_section_top_y_fallback = int(self._base_section_top_y_fallback * scale_factor)
            section_top_y = scaled_padding + (name_height if name_height > 0 else scaled_section_top_y_fallback)
            available_width = panel_width - scaled_padding * 2
            main_panel_x = scaled_padding
        # Utiliser directement les valeurs en 1280x720
        spacing_between = int(self._base_spacing_between * scale_factor)
        
        # Dimensions du cadre sprite (largeur adaptée pour sprite 4x, hauteur adaptée)
        # Utiliser directement les valeurs en 1280x720
        sprite_frame_width = int(self._base_sprite_frame_width * scale_factor)  # Largeur adaptée pour sprite 4x
        sprite_frame_padding = int(self._base_sprite_frame_padding * scale_factor)  # Padding interne du cadre
        
        # Calculer la hauteur du sprite redimensionné pour dimensionner le cadre
        # On doit extraire les sprites pour connaître leur taille
        sprites = self.sprite_manager.extract_player_sprites()
        if sprites:
            sprite_height = sprites[0].get_height()
            sprite_frame_height = sprite_height + sprite_frame_padding * 2
        else:
            # Valeur par défaut si les sprites ne sont pas disponibles
            # Utiliser directement la valeur en 1280x720
            sprite_frame_height = int(self._base_sprite_frame_height * scale_factor)
        max_presentation_space = max(1, available_width - sprite_frame_width - spacing_between)
        presentation_width = min(int(available_width * 0.6), max_presentation_space)
        # Utiliser directement la valeur en 1280x720
        scaled_presentation_min_width = int(self._base_presentation_min_width * scale_factor)
        presentation_width = max(scaled_presentation_min_width, presentation_width)
        presentation_width = min(presentation_width, max_presentation_space)

        combined_width = sprite_frame_width + spacing_between + presentation_width
        if self.main_panel_rect is not None:
            top_start_x = main_panel_x + max(0, (available_width - combined_width) // 2)
        else:
            top_start_x = scaled_padding + max(0, (available_width - combined_width) // 2)

        # Décaler le sprite et la présentation avec les offsets
        sprite_frame_x = top_start_x + self.offset_x
        presentation_x = sprite_frame_x + sprite_frame_width + spacing_between
        presentation_y = section_top_y + self.offset_y
        
        # Dessiner la présentation (sans le nom qui est déjà dessiné en haut)
        # Calculer l'espace disponible pour la présentation (réserver de l'espace pour les stats)
        # Utiliser la valeur de base dans le repère de design
        reserved_space_for_stats = int(self._base_reserved_space_for_stats * scale_factor)  # Espace réservé pour les statistiques
        max_presentation_height = panel_height - section_top_y - reserved_space_for_stats
        
        # Créer une surface de clipping pour la présentation si nécessaire
        presentation_surface = pygame.Surface((presentation_width, max_presentation_height), pygame.SRCALPHA)
        presentation_height = draw_character_presentation(
            presentation_surface,
            0,
            0,
            presentation_width,
            self.character_presentation,
            self.presentation_name_font,
            self.presentation_section_font,
            self.presentation_text_font,
            self.presentation_name_color,
            self.presentation_section_color,
            self.presentation_text_color,
            self.presentation_padding,
            self.presentation_section_spacing,
            self._base_presentation_name_spacing,
            self._base_presentation_bullet_spacing,
            self._base_presentation_title_spacing,
            self._base_presentation_item_spacing,
            scale_factor,
            display_name="",
            include_name=False,
        )
        
        # Si la présentation dépasse, elle sera automatiquement coupée par le clipping
        if presentation_height > max_presentation_height:
            presentation_height = max_presentation_height
        
        # Dessiner la surface de présentation sur le panneau principal
        panel.blit(presentation_surface, (presentation_x, presentation_y))

        # Centrer verticalement le sprite par rapport à la présentation
        # Le sprite doit être aligné avec le centre vertical de la présentation
        presentation_center_y = presentation_y + presentation_height // 2
        sprite_frame_y = presentation_center_y - sprite_frame_height // 2
        
        # S'assurer que le sprite ne dépasse pas du panneau
        if sprite_frame_y < section_top_y:
            sprite_frame_y = section_top_y
        if sprite_frame_y + sprite_frame_height > panel_height:
            sprite_frame_y = panel_height - sprite_frame_height

        self._sprite_frame_rect = pygame.Rect(sprite_frame_x, sprite_frame_y, sprite_frame_width, sprite_frame_height)

        # Vérifier si les stats sont disponibles
        if self.player.level_manager.stats_config is None:
            no_stats_text = render_text(
                "Statistiques non disponibles", scaled_font, self.stat_name_color
            )
            no_stats_x = (panel_width - no_stats_text.get_width()) // 2
            no_stats_y = panel_height // 2
            panel.blit(no_stats_text, (no_stats_x, no_stats_y))
            return panel

        # Section inférieure : Statistiques en 2 colonnes dans le panneau central principal
        # Zone de contenu (sous la section supérieure)
        # Utiliser directement la valeur en 1280x720
        scaled_section_bottom_spacing = int(self._base_section_bottom_spacing * scale_factor)
        section_bottom_y = max(sprite_frame_y + sprite_frame_height, presentation_y + presentation_height) + scaled_section_bottom_spacing  # Espacement après la section supérieure
        
        # S'assurer que les statistiques ne dépassent pas du panneau
        max_stats_y = panel_height - int(20 * scale_factor)  # Réserver un petit espace en bas
        if section_bottom_y > max_stats_y:
            section_bottom_y = max_stats_y
        
        # Si le panneau central principal est défini, ajuster la largeur disponible pour les stats
        # Réduire la largeur disponible pour que les jauges rentrent bien dans le panneau central
        # Décaler les statistiques avec les offsets (comme le sprite et la présentation)
        if self.main_panel_rect is not None:
            # Réduire la largeur disponible avec un padding supplémentaire pour que les jauges rentrent dans le panneau
            stats_padding = int(20 * scale_factor)  # Padding supplémentaire pour les stats
            available_stats_width = self.main_panel_rect.width - (stats_padding * 2)
            stats_start_x = self.main_panel_rect.x + stats_padding + self.offset_x
        else:
            available_stats_width = panel_width - scaled_padding * 2
            stats_start_x = scaled_padding + self.offset_x

        # Position de départ des statistiques avec offset_y
        stats_start_y = section_bottom_y + self.offset_y

        # Section inférieure : Statistiques en 2 colonnes
        stats_data: List[Dict[str, Any]] = []
        max_value_width = 0
        try:
            stats_config = self.player.level_manager.stats_config
            for stat_identifier in stats_config.stats.keys():
                stat_def = stats_config.stats[stat_identifier]
                current_value = self.player.level_manager.get_stat_value(stat_identifier)
                max_value = stats_config.get_stat_max_value(stat_identifier)
                value_text = f"{int(current_value)}/{int(max_value)}"
                value_width = scaled_font.size(value_text)[0]
                max_value_width = max(max_value_width, value_width)
                stats_data.append(
                    {
                        "identifier": stat_identifier,
                        "name": stat_def.name,
                        "current": current_value,
                        "max": max_value,
                    }
                )
        except (KeyError, AttributeError) as e:
            logger.warning(f"Erreur lors de l'affichage des statistiques: {e}")

        # Calculer la largeur des colonnes (2 colonnes égales)
        column_spacing = int(self._base_column_spacing * scale_factor)  # Espacement entre les colonnes
        column_width = (available_stats_width - column_spacing) // 2
        
        # Calculer la largeur des barres pour chaque colonne
        # Réduire la largeur des jauges de 1/3 pour qu'elles rentrent mieux dans le panneau central
        scaled_value_spacing = int(8 * scale_factor)
        scaled_icon_spacing = int(5 * scale_factor)
        value_icon_space = max_value_width + scaled_value_spacing + scaled_icon_spacing + scaled_info_icon_size
        base_stat_bar_width = max(
            50,
            column_width - value_icon_space,
        )
        # Réduire de 1/3 (multiplier par 2/3)
        scaled_stat_bar_width = int(base_stat_bar_width * 2 / 3)
        
        # Calculer la hauteur totale du contenu des statistiques
        stat_name_height = scaled_font.get_height()
        scaled_stat_bar_spacing = int(8 * scale_factor)  # Espacement entre le nom et la jauge
        additional_spacing = int(40 * scale_factor)  # Espacement vertical entre les stats

        # Réinitialiser les rectangles des icônes
        self.icon_rects = {}
        
        # Dessiner les statistiques en 2 colonnes
        try:
            # Répartir les stats entre les 2 colonnes
            num_stats = len(stats_data)
            stats_per_column = (num_stats + 1) // 2  # Arrondir vers le haut pour la première colonne
            
            # Colonne gauche
            col1_x = stats_start_x
            col1_y = stats_start_y
            col1_stats = stats_data[:stats_per_column]
            
            # Colonne droite
            col2_x = stats_start_x + column_width + column_spacing
            col2_y = stats_start_y
            col2_stats = stats_data[stats_per_column:]
            
            # Dessiner la colonne gauche
            current_y = col1_y
            last_bottom_y = col1_y
            for stat in col1_stats:
                icon_rect, stat_height = self._draw_stat_bar(
                    panel,
                    col1_x,
                    current_y,
                    stat["name"],
                    stat["current"],
                    stat["max"],
                    stat["identifier"],
                    scale_factor,
                    scaled_font,
                    scaled_stat_bar_width,
                    scaled_stat_bar_height,
                    scaled_info_icon_size,
                )
                if icon_rect is not None:
                    self.icon_rects[stat["identifier"]] = icon_rect
                last_bottom_y = current_y + stat_height
                current_y = last_bottom_y + additional_spacing
            
            # Dessiner la colonne droite
            current_y = col2_y
            for stat in col2_stats:
                icon_rect, stat_height = self._draw_stat_bar(
                    panel,
                    col2_x,
                    current_y,
                    stat["name"],
                    stat["current"],
                    stat["max"],
                    stat["identifier"],
                    scale_factor,
                    scaled_font,
                    scaled_stat_bar_width,
                    scaled_stat_bar_height,
                    scaled_info_icon_size,
                )
                if icon_rect is not None:
                    self.icon_rects[stat["identifier"]] = icon_rect
                last_bottom_y = max(last_bottom_y, current_y + stat_height)
                current_y = current_y + stat_height + additional_spacing
        except (KeyError, AttributeError) as e:
            logger.warning(f"Erreur lors de l'affichage des statistiques: {e}")

        # Note: Le niveau est maintenant affiché dans le titre avec le nom du personnage, plus besoin de l'afficher séparément

        # Note: Le sprite du joueur animé est dessiné directement dans draw() pour permettre l'animation

        return panel

    def _draw_animated_sprite(self, surface: pygame.Surface, panel_x: int, panel_y: int) -> None:
        """Dessine le sprite du joueur animé centré dans le bloc de gauche du panneau.

        Args:
            surface: Surface sur laquelle dessiner
            panel_x: Position X du panneau
            panel_y: Position Y du panneau
        """
        # Récupérer le sprite actuel selon l'animation de rotation
        current_sprite = self.sprite_manager.get_current_sprite()
        
        if current_sprite is None:
            return

        # Calculer la position du sprite centré dans le bloc de gauche défini lors de la création du panneau
        scale_factor = self._design_scale_x  # Utiliser scale_x pour la cohérence (actuellement 1.0)
        if self._sprite_frame_rect is not None:
            sprite_frame_x = panel_x + self._sprite_frame_rect.x
            sprite_frame_y = panel_y + self._sprite_frame_rect.y
            sprite_frame_width = self._sprite_frame_rect.width
            sprite_frame_height = self._sprite_frame_rect.height
        else:
            scaled_padding = int(self.padding * scale_factor)
            # Utiliser les valeurs de base dans le repère de design
            sprite_frame_width = int(self._base_sprite_frame_width * scale_factor)
            scaled_sprite_frame_padding = int(self._base_sprite_frame_padding * scale_factor)
            sprite_frame_height = current_sprite.get_height() + scaled_sprite_frame_padding * 2
            sprite_frame_x = panel_x + scaled_padding
            sprite_frame_y = panel_y + scaled_padding
            self._sprite_frame_rect = pygame.Rect(
                sprite_frame_x - panel_x,
                sprite_frame_y - panel_y,
                sprite_frame_width,
                sprite_frame_height,
            )
        
        # Centrer le sprite horizontalement et verticalement dans le bloc de gauche (sans cadre)
        sprite_x = sprite_frame_x + (sprite_frame_width - current_sprite.get_width()) // 2
        sprite_y = sprite_frame_y + (sprite_frame_height - current_sprite.get_height()) // 2

        # Dessiner le sprite directement (sans cadre)
        surface.blit(current_sprite, (sprite_x, sprite_y))
    
    def _draw_stat_bar(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        stat_name: str,
        current_value: float,
        max_value: float,
        stat_identifier: str,
        scale_factor: float = 1.0,
        font: Optional[pygame.font.Font] = None,
        stat_bar_width: Optional[int] = None,
        stat_bar_height: Optional[int] = None,
        info_icon_size: Optional[int] = None,
    ) -> Tuple[Optional[pygame.Rect], int]:
        """Dessine une jauge de statistique avec son icône d'information.

        Args:
            surface: Surface sur laquelle dessiner
            x: Position horizontale
            y: Position verticale
            stat_name: Nom de la statistique
            current_value: Valeur actuelle
            max_value: Valeur maximale
            stat_identifier: Identifiant de la statistique
            scale_factor: Facteur d'échelle à appliquer
            font: Police à utiliser (si None, utilise self.font)
            stat_bar_width: Largeur de la barre (si None, utilise self.stat_bar_width)
            stat_bar_height: Hauteur de la barre (si None, utilise self.stat_bar_height)
            info_icon_size: Taille de l'icône (si None, utilise self.info_icon_size)

        Returns:
            Tuple contenant le rectangle de l'icône d'information (ou None si l'icône n'a pas été dessinée)
            et la hauteur totale utilisée par la statistique
        """
        # Utiliser les valeurs par défaut si non fournies
        if font is None:
            font = self.font
        if stat_bar_width is None:
            stat_bar_width = self.stat_bar_width
        if stat_bar_height is None:
            stat_bar_height = self.stat_bar_height
        if info_icon_size is None:
            info_icon_size = self.info_icon_size
        
        # Calculer le pourcentage de remplissage
        if max_value > 0:
            fill_percentage = (current_value / max_value) * 100.0
        else:
            fill_percentage = 0.0

        # Dessiner le nom de la statistique
        name_surface = render_text(stat_name, font, self.stat_name_color)
        surface.blit(name_surface, (x, y))

        # Dessiner l'indicateur de progression si la statistique a progressé
        indicator_width = 0
        if has_stat_progressed(self.player, stat_identifier):
            scaled_indicator_spacing = int(6 * scale_factor)  # Espacement entre le nom et l'indicateur (5-8 pixels)
            indicator_x = x + name_surface.get_width() + scaled_indicator_spacing
            indicator_y = y  # Aligné verticalement avec le nom
            indicator_width = draw_progression_indicator(
                surface, indicator_x, indicator_y, font, scale_factor
            )

        # Position de la jauge (sous le nom)
        scaled_bar_spacing = int(8 * scale_factor)  # Espacement pour améliorer la lisibilité
        stat_height = name_surface.get_height() + scaled_bar_spacing + stat_bar_height
        bar_y = y + name_surface.get_height() + scaled_bar_spacing

        # Dessiner le fond de la jauge (gris plus clair pour meilleur contraste)
        bar_bg_rect = pygame.Rect(x, bar_y, stat_bar_width, stat_bar_height)
        pygame.draw.rect(surface, (80, 80, 80), bar_bg_rect)  # Gris plus clair pour meilleur contraste

        # Dessiner le remplissage de la jauge
        fill_width = int((fill_percentage / 100.0) * stat_bar_width)
        if fill_width > 0:
            fill_color = get_bar_color(fill_percentage)
            fill_rect = pygame.Rect(x, bar_y, fill_width, stat_bar_height)
            pygame.draw.rect(surface, fill_color, fill_rect)

        # Dessiner la bordure de la jauge (plus épaisse pour meilleure visibilité)
        scaled_border_width = max(2, int(2 * scale_factor))
        pygame.draw.rect(surface, (180, 180, 180), bar_bg_rect, scaled_border_width)  # Bordure plus claire et plus épaisse

        # Dessiner la valeur (à droite de la jauge)
        value_text = f"{int(current_value)}/{int(max_value)}"
        value_surface = render_text(value_text, font, self.stat_value_color)
        scaled_value_spacing = int(8 * scale_factor)  # Espacement entre jauge et valeur
        scaled_icon_spacing = int(5 * scale_factor)
        value_x = x + stat_bar_width + scaled_value_spacing
        value_y = bar_y + (stat_bar_height - value_surface.get_height()) // 2
        max_value_x_allowed = surface.get_width() - value_surface.get_width() - info_icon_size - scaled_icon_spacing - int(6 * scale_factor)
        if value_x > max_value_x_allowed:
            value_x = max_value_x_allowed
        surface.blit(value_surface, (value_x, value_y))

        # Dessiner l'icône d'information (à droite de la valeur)
        icon_x = value_x + value_surface.get_width() + scaled_icon_spacing
        icon_y = bar_y + (stat_bar_height - info_icon_size) // 2
        icon_x = min(icon_x, surface.get_width() - info_icon_size)
        icon_rect = self._draw_info_icon(surface, icon_x, icon_y, stat_identifier, scale_factor, font, info_icon_size)
        return icon_rect, stat_height

    def _draw_info_icon(
        self, 
        surface: pygame.Surface, 
        x: int, 
        y: int, 
        stat_identifier: str,
        scale_factor: float = 1.0,
        font: Optional[pygame.font.Font] = None,
        info_icon_size: Optional[int] = None,
    ) -> pygame.Rect:
        """Dessine l'icône "I" dans un cercle et retourne son rectangle pour la détection de survol.

        Args:
            surface: Surface sur laquelle dessiner
            x: Position horizontale
            y: Position verticale
            stat_identifier: Identifiant de la statistique
            scale_factor: Facteur d'échelle à appliquer
            font: Police de base (utilisée pour calculer la taille de l'icône si nécessaire)
            info_icon_size: Taille de l'icône (si None, utilise self.info_icon_size)

        Returns:
            Rectangle de l'icône
        """
        if info_icon_size is None:
            info_icon_size = self.info_icon_size
        
        # Dessiner le cercle
        icon_rect = pygame.Rect(x, y, info_icon_size, info_icon_size)
        scaled_border_width = max(1, int(2 * scale_factor))
        pygame.draw.circle(
            surface,
            self.info_icon_color,
            (x + info_icon_size // 2, y + info_icon_size // 2),
            info_icon_size // 2,
            scaled_border_width,  # Épaisseur de la bordure
        )

        # Dessiner le "I" au centre
        # Utiliser la police pixel art chargée (VT323)
        # Si la police n'est pas chargée, calculer une taille adaptée à l'icône
        if self.info_icon_font is not None:
            icon_font = self.info_icon_font
        else:
            # Calculer la taille de la police en fonction de la taille de l'icône (environ 70-80%)
            icon_font_size = max(int(10 * scale_factor), int(info_icon_size * 0.75 * scale_factor))
            try:
                icon_font = pygame.font.SysFont("arial", icon_font_size, bold=True)
            except pygame.error:
                icon_font = pygame.font.SysFont("sans-serif", icon_font_size, bold=True)

        i_text = icon_font.render("I", True, self.info_icon_color)
        i_x = x + (info_icon_size - i_text.get_width()) // 2
        i_y = y + (info_icon_size - i_text.get_height()) // 2
        surface.blit(i_text, (i_x, i_y))

        return icon_rect

    def _draw_character_presentation(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        width: int,
        scale_factor: float,
        include_name: bool = True,
    ) -> int:
        """Dessine la section de présentation du personnage et retourne la hauteur totale utilisée.

        Args:
            surface: Surface sur laquelle dessiner
            x: Position horizontale de départ
            y: Position verticale de départ
            width: Largeur disponible pour la présentation
            scale_factor: Facteur d'échelle à appliquer
            include_name: Si True, dessine le nom du personnage (défaut: True)

        Returns:
            Hauteur totale utilisée par la présentation
        """
        # Utiliser directement les valeurs en 1280x720
        # puis ajuster avec le facteur d'échelle pour la résolution d'affichage réelle
        scaled_padding = int(self.presentation_padding * scale_factor)
        scaled_section_spacing = int(self.presentation_section_spacing * scale_factor)

        # Utiliser les polices pixel art chargées
        if self.presentation_name_font is not None:
            name_font = self.presentation_name_font
        else:
            # Utiliser directement la valeur en 1280x720
            scaled_name_font_size = int(self.presentation_name_font_size * scale_factor)
            try:
                name_font = pygame.font.SysFont("arial", scaled_name_font_size, bold=True)
            except pygame.error:
                name_font = pygame.font.SysFont("sans-serif", scaled_name_font_size, bold=True)
        
        if self.presentation_section_font is not None:
            section_font = self.presentation_section_font
        else:
            # Utiliser directement la valeur en 1280x720
            scaled_section_font_size = int(self.presentation_section_font_size * scale_factor)
            try:
                section_font = pygame.font.SysFont("arial", scaled_section_font_size, bold=True)
            except pygame.error:
                section_font = pygame.font.SysFont("sans-serif", scaled_section_font_size, bold=True)
        
        if self.presentation_text_font is not None:
            text_font = self.presentation_text_font
        else:
            # Utiliser directement la valeur en 1280x720
            scaled_text_font_size = int(self.presentation_text_font_size * scale_factor)
            try:
                text_font = pygame.font.SysFont("arial", scaled_text_font_size, bold=False)
            except pygame.error:
                text_font = pygame.font.SysFont("sans-serif", scaled_text_font_size, bold=False)

        current_y = y

        # Dessiner le nom du personnage (centré) si demandé
        if include_name:
            name_text = self.character_display_name
            if name_text:
                name_surface = render_text(name_text, name_font, self.presentation_name_color)
                name_x = x + (width - name_surface.get_width()) // 2
                surface.blit(name_surface, (name_x, current_y))
                # Utiliser directement la valeur en 1280x720
                scaled_name_spacing = int(self._base_presentation_name_spacing * scale_factor)
                current_y += name_surface.get_height() + scaled_name_spacing

        section_specs: tuple[tuple[str, str], ...] = (
            ("origins", "Origines"),
            ("class_role", "Classe & Rôle"),
            ("traits", "Traits de caractère"),
        )
        bullet = int(self._base_presentation_bullet_spacing * scale_factor)
        title_sp = int(self._base_presentation_title_spacing * scale_factor)
        item_sp = int(self._base_presentation_item_spacing * scale_factor)
        first_section = True
        for key, section_title in section_specs:
            raw = self.character_presentation.get(key, [])
            if not isinstance(raw, list) or not raw:
                continue
            lines = [s for s in (t.strip() if isinstance(t, str) else "" for t in raw) if s]
            if not lines:
                continue
            if not first_section:
                current_y += scaled_section_spacing
            first_section = False
            section_height = draw_presentation_section(
                surface, x, current_y, width, section_title, lines,
                section_font, text_font, self.presentation_section_color, self.presentation_text_color,
                scaled_padding, scaled_section_spacing, bullet, title_sp, item_sp,
            )
            current_y += section_height

        return current_y - y

