"""Overlay d'interface affichant la progression horizontale du joueur."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import pygame

from ..progress import LevelProgressTracker
from ...rendering.config import DESIGN_WIDTH, RENDER_WIDTH, compute_scale


@dataclass
class _HudCache:
    """Cache interne pour éviter les re-rendus coûteux."""

    value: Optional[int] = None
    ratio: Optional[float] = None
    max_value: Optional[int] = None
    surface: Optional[pygame.Surface] = None
    rect: Optional[pygame.Rect] = None


class LevelProgressHUD:
    """Overlay HUD affichant la progression du joueur."""

    def __init__(
        self,
        tracker: LevelProgressTracker,
        *,
        font: Optional[pygame.font.Font] = None,
        value_font_size: int = 22,
        secondary_font_size: int = 16,
        position: Tuple[int, int] = (16, 16),
        padding: Tuple[int, int] = (14, 12),
        background_color: Tuple[int, int, int, int] = (0, 0, 0, 180),
        border_radius: int = 9,
        value_color: Tuple[int, int, int] = (255, 255, 255),
        secondary_color: Tuple[int, int, int] = (200, 200, 200),
        debug_mode: bool = False,
    ) -> None:
        """Initialise l'overlay de progression."""
        self.tracker = tracker
        self.position = position
        self.padding = padding
        self.background_color = background_color
        self.border_radius = border_radius
        self.value_color = value_color
        self.secondary_color = secondary_color
        self.debug_mode = debug_mode

        self._cache = _HudCache()

        self._font_overridden = font is not None
        self._base_value_font_size = value_font_size
        self._base_secondary_font_size = secondary_font_size
        self._base_position = position
        self._base_padding = padding
        self._cached_scale = 0.0
        
        # Facteur de conversion du repère de rendu (1280x720) vers le repère de design (1920x1080)
        # Les positions du joueur et des PNJ sont stockées en repère de rendu, mais on veut afficher en repère de design
        self._render_to_design_scale = DESIGN_WIDTH / RENDER_WIDTH if RENDER_WIDTH > 0 else 1.0

        # Préparer les polices utilisées
        if font is not None:
            self.value_font = font
            self.secondary_font = font
        else:
            self.value_font = pygame.font.Font(None, value_font_size)
            self.secondary_font = pygame.font.Font(None, secondary_font_size)

        if not self._font_overridden:
            self._update_scale_dependant_values(force=True)

    def draw(self, surface: pygame.Surface) -> None:
        """Dessine le HUD sur la surface fournie."""
        if not self._font_overridden:
            self._update_scale_dependant_values()

        current_value = self.tracker.get_current_x()
        ratio = self.tracker.get_progress_ratio()
        max_value = self.tracker.get_max_x() if self.debug_mode else None

        if self._needs_rerender(current_value, ratio, max_value):
            self._rerender_panel(current_value, ratio, max_value)

        if self._cache.surface is None or self._cache.rect is None:
            return

        surface.blit(self._cache.surface, self._cache.rect)

    def _needs_rerender(
        self, value: int, ratio: Optional[float], max_value: Optional[int]
    ) -> bool:
        """Détermine si un re-rendu du HUD est nécessaire."""
        cache = self._cache
        if cache.surface is None or cache.rect is None:
            return True

        if cache.value != value:
            return True

        if (cache.ratio is None) != (ratio is None):
            return True
        if ratio is not None and cache.ratio is not None:
            # Comparer avec une tolérance pour éviter les re-rendus inutiles
            if abs(cache.ratio - ratio) >= 0.001:
                return True

        if self.debug_mode and cache.max_value != max_value:
            return True

        return False

    def _rerender_panel(
        self, value: int, ratio: Optional[float], max_value: Optional[int]
    ) -> None:
        """Regénère les surfaces du HUD."""
        # Convertir la valeur du repère de rendu (1280x720) vers le repère de design (1920x1080)
        # Les positions du joueur et des PNJ sont stockées en repère de rendu, mais on veut afficher en repère de design
        # pour correspondre aux valeurs dans les fichiers de configuration (.pnj, .event)
        converted_value = int(round(value * self._render_to_design_scale))
        converted_max_value = int(round(max_value * self._render_to_design_scale)) if max_value is not None else None
        
        lines: list[tuple[pygame.font.Font, str, Tuple[int, int, int]]] = []
        lines.append((self.value_font, f"{converted_value:05d} px", self.value_color))

        if ratio is not None:
            ratio_text = f"{ratio:.1%}"
            lines.append((self.secondary_font, ratio_text, self.secondary_color))

        if self.debug_mode and converted_max_value is not None:
            lines.append((self.secondary_font, f"Max {converted_max_value:05d} px", self.secondary_color))

        rendered_lines = [self._render_text(font, text, color) for font, text, color in lines]
        width = max(line.get_width() for line in rendered_lines) if rendered_lines else 0
        height = sum(line.get_height() for line in rendered_lines)
        # Convertir l'espacement entre lignes du repère de conception (1920x1080) vers la résolution interne (1280x720)
        from ...rendering.config import compute_design_scale, get_render_size
        render_width, render_height = get_render_size()
        _, scale_y = compute_design_scale((render_width, render_height))
        line_spacing_design = 4  # Espacement entre lignes dans le repère 1920x1080
        converted_line_spacing = int(line_spacing_design * scale_y)
        line_spacing = converted_line_spacing if len(rendered_lines) > 1 else 0
        total_height = height + line_spacing * (len(rendered_lines) - 1)

        panel_width = width + self.padding[0] * 2
        panel_height = total_height + self.padding[1] * 2

        panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(
            panel_surface,
            self.background_color,
            panel_surface.get_rect(),
            border_radius=self.border_radius,
        )

        current_y = self.padding[1]
        for line_surface in rendered_lines:
            line_rect = line_surface.get_rect()
            line_rect.topleft = (self.padding[0], current_y)
            panel_surface.blit(line_surface, line_rect)
            current_y += line_surface.get_height() + line_spacing

        panel_rect = panel_surface.get_rect()
        panel_rect.topleft = self.position

        self._cache = _HudCache(
            value=value,
            ratio=ratio,
            max_value=max_value,
            surface=panel_surface,
            rect=panel_rect,
        )

    def _render_text(
        self,
        font: pygame.font.Font,
        text: str,
        color: Tuple[int, int, int],
    ) -> pygame.Surface:
        """Rend une ligne de texte."""
        return font.render(text, True, color)

    def _determine_scale(self) -> float:
        """Retourne le facteur d'échelle basé sur la fenêtre courante."""
        display_size = None
        try:
            display_size = pygame.display.get_window_size()
        except (pygame.error, AttributeError):
            display_size = None

        if not display_size or display_size[0] <= 0 or display_size[1] <= 0:
            try:
                surface = pygame.display.get_surface()
                if surface is not None:
                    display_size = surface.get_size()
            except (pygame.error, AttributeError):
                display_size = None

        if not display_size or display_size[0] <= 0 or display_size[1] <= 0:
            return 1.0

        scale = compute_scale(display_size)
        return max(0.5, min(2.0, scale))

    def _update_scale_dependant_values(self, force: bool = False) -> None:
        """Met à jour les polices, padding et position selon le facteur d'échelle."""
        scale = self._determine_scale()
        if not force and abs(scale - self._cached_scale) < 0.05:
            return

        self._cached_scale = scale

        scaled_value_size = max(12, int(self._base_value_font_size * scale))
        scaled_secondary_size = max(10, int(self._base_secondary_font_size * scale))
        self.value_font = pygame.font.Font(None, scaled_value_size)
        self.secondary_font = pygame.font.Font(None, scaled_secondary_size)

        new_padding = (
            max(6, int(self._base_padding[0] * scale)),
            max(6, int(self._base_padding[1] * scale)),
        )
        if new_padding != self.padding:
            self.padding = new_padding

        new_position = (
            int(self._base_position[0] * scale),
            int(self._base_position[1] * scale),
        )
        if new_position != self.position:
            self.position = new_position

        # Invalider le cache car les dimensions changent avec l'échelle
        self._cache = _HudCache()


