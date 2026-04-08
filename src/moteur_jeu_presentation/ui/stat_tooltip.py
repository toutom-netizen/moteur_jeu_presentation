"""Module de gestion des tooltips pour les statistiques."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional, Tuple

import pygame

from .text_utils import render_text, wrap_text

if TYPE_CHECKING:
    from ..entities.player import Player


def create_tooltip(
    player: "Player",
    stat_identifier: str,
    tooltip_font: Optional[pygame.font.Font],
    tooltip_font_size: int,
    tooltip_max_width: int,
    tooltip_padding: int,
    tooltip_bg_color: Tuple[int, int, int, int],
    tooltip_border_color: Tuple[int, int, int],
    tooltip_text_color: Tuple[int, int, int],
    scale_factor: float = 1.0,
) -> Optional[pygame.Surface]:
    """Crée la surface du tooltip pour une statistique donnée.

    Args:
        player: Instance du joueur
        stat_identifier: Identifiant de la statistique
        tooltip_font: Police à utiliser pour le tooltip (peut être None)
        tooltip_font_size: Taille de la police du tooltip
        tooltip_max_width: Largeur maximale du tooltip
        tooltip_padding: Padding interne du tooltip
        tooltip_bg_color: Couleur de fond du tooltip (RGBA)
        tooltip_border_color: Couleur de la bordure du tooltip (RGB)
        tooltip_text_color: Couleur du texte du tooltip (RGB)
        scale_factor: Facteur d'échelle (défaut: 1.0)

    Returns:
        Surface du tooltip, ou None si aucun tooltip n'est défini
    """
    try:
        tooltip_text = player.level_manager.get_stat_tooltip(stat_identifier)
        if tooltip_text is None:
            return None
    except (KeyError, AttributeError):
        return None

    # Diviser le texte en lignes (gérer les \n)
    lines = tooltip_text.split("\n")

    # Calculer les dimensions adaptées à la résolution pour le tooltip
    scaled_tooltip_max_width = int(tooltip_max_width * scale_factor)
    scaled_tooltip_padding = int(tooltip_padding * scale_factor)
    
    # Utiliser la police fournie ou créer une nouvelle
    if tooltip_font is not None:
        scaled_font = tooltip_font
    else:
        scaled_tooltip_font_size = int(tooltip_font_size * scale_factor)
        try:
            scaled_font = pygame.font.SysFont("arial", scaled_tooltip_font_size, bold=False)
        except pygame.error:
            scaled_font = pygame.font.SysFont("sans-serif", scaled_tooltip_font_size, bold=False)

    # Largeur maximale disponible pour le texte (sans le padding)
    text_max_width = scaled_tooltip_max_width

    # Appliquer le word wrapping à chaque ligne et créer les surfaces
    final_line_surfaces = []
    total_height = 0
    line_height = scaled_font.get_height()
    scaled_line_spacing = int(2 * scale_factor)  # Espacement entre les lignes

    for line in lines:
        if line.strip():  # Ignorer les lignes vides
            # Appliquer le word wrapping à la ligne (utiliser la police adaptée)
            wrapped_lines = wrap_text(line, text_max_width, scaled_font)
            for wrapped_line in wrapped_lines:
                line_surf = render_text(wrapped_line, scaled_font, tooltip_text_color)
                final_line_surfaces.append(line_surf)
                total_height += line_height + scaled_line_spacing
        else:
            # Ligne vide : ajouter un espacement
            final_line_surfaces.append(None)
            total_height += int(5 * scale_factor)

    if not final_line_surfaces:
        return None

    # Calculer la largeur maximale réelle (après wrapping)
    max_width = max(
        (surf.get_width() for surf in final_line_surfaces if surf is not None),
        default=0
    )
    max_width = min(max_width, text_max_width)

    # Créer la surface du tooltip avec transparence
    tooltip_width = max_width + scaled_tooltip_padding * 2
    tooltip_height = total_height + scaled_tooltip_padding * 2
    tooltip_surface = pygame.Surface((tooltip_width, tooltip_height), pygame.SRCALPHA)

    # Dessiner le fond avec alpha
    bg_rect = pygame.Rect(0, 0, tooltip_width, tooltip_height)
    bg_surface = pygame.Surface((tooltip_width, tooltip_height), pygame.SRCALPHA)
    bg_color_rgba = (
        tooltip_bg_color[0],
        tooltip_bg_color[1],
        tooltip_bg_color[2],
        tooltip_bg_color[3],
    )
    pygame.draw.rect(bg_surface, bg_color_rgba, bg_rect)
    tooltip_surface.blit(bg_surface, (0, 0))

    # Dessiner la bordure
    scaled_tooltip_border_width = max(1, int(2 * scale_factor))
    pygame.draw.rect(
        tooltip_surface,
        tooltip_border_color,
        bg_rect,
        scaled_tooltip_border_width,
    )

    # Dessiner les lignes de texte
    y_offset = scaled_tooltip_padding
    for line_surf in final_line_surfaces:
        if line_surf is not None:
            x_offset = scaled_tooltip_padding
            tooltip_surface.blit(line_surf, (x_offset, y_offset))
            y_offset += line_surf.get_height() + scaled_line_spacing
        else:
            y_offset += int(5 * scale_factor)

    return tooltip_surface


def get_tooltip_position(
    tooltip_surface: Optional[pygame.Surface],
    icon_rect: pygame.Rect,
    screen_width: int,
    screen_height: int,
) -> Tuple[int, int]:
    """Calcule la position du tooltip par rapport à l'icône, en évitant de sortir de l'écran.

    Args:
        tooltip_surface: Surface du tooltip (peut être None)
        icon_rect: Rectangle de l'icône en coordonnées écran
        screen_width: Largeur de l'écran
        screen_height: Hauteur de l'écran

    Returns:
        Position (x, y) du tooltip
    """
    if tooltip_surface is None:
        return (0, 0)

    tooltip_width = tooltip_surface.get_width()
    tooltip_height = tooltip_surface.get_height()

    # Position par défaut : au-dessus de l'icône, centré horizontalement
    x = icon_rect.centerx - tooltip_width // 2
    y = icon_rect.y - tooltip_height - 5  # 5 pixels d'espacement

    # Vérifier les bords de l'écran et ajuster si nécessaire
    if x < 0:
        x = 5
    elif x + tooltip_width > screen_width:
        x = screen_width - tooltip_width - 5

    if y < 0:
        # Si le tooltip sort en haut, le placer en dessous de l'icône
        y = icon_rect.bottom + 5
        if y + tooltip_height > screen_height:
            y = screen_height - tooltip_height - 5

    return (x, y)


def check_icon_hover(
    mouse_pos: Tuple[int, int],
    icon_rects: Dict[str, pygame.Rect],
    panel_padding: int,
) -> Optional[str]:
    """Vérifie si la souris survole une icône et retourne l'identifiant de la statistique correspondante.

    Args:
        mouse_pos: Position de la souris (x, y) en coordonnées de la résolution interne (1280x720)
        icon_rects: Dictionnaire des rectangles des icônes par stat_identifier
        panel_padding: Padding du panneau

    Returns:
        Identifiant de la statistique survolée, ou None si aucune
    """
    # Vérifier si la souris est hors limites
    mouse_x, mouse_y = mouse_pos
    if mouse_x < 0 or mouse_y < 0:
        return None

    # Convertir la position de la souris en coordonnées relatives au panneau
    panel_x = panel_padding
    panel_y = panel_padding

    panel_mouse_x = mouse_x - panel_x
    panel_mouse_y = mouse_y - panel_y

    # Vérifier chaque icône
    for stat_identifier, icon_rect in icon_rects.items():
        if icon_rect.collidepoint(panel_mouse_x, panel_mouse_y):
            return stat_identifier

    return None

