"""Module de gestion de la présentation du personnage pour l'interface."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pygame

from .text_utils import render_text, wrap_text


def draw_character_name(
    surface: pygame.Surface,
    title_panel_rect: Optional[pygame.Rect],
    name_font: Optional[pygame.font.Font],
    name_color: Tuple[int, int, int],
    current_level: int,
    display_name: str,
) -> int:
    """Dessine le nom du personnage dans le panneau rectangulaire supérieur, centré horizontalement et verticalement.

    Args:
        surface: Surface sur laquelle dessiner
        title_panel_rect: Rectangle du panneau supérieur
        name_font: Police à utiliser pour le nom
        name_color: Couleur du nom
        current_level: Niveau actuel du personnage
        display_name: Texte du nom (ex. depuis player_stats.toml)

    Returns:
        Hauteur totale utilisée par le nom (0 si le panneau n'est pas défini)
    """
    # Utiliser le panneau rectangulaire supérieur si disponible
    if title_panel_rect is None:
        return 0
    
    # Utiliser la police fournie
    if name_font is None:
        return 0

    # Dessiner le nom du personnage avec le niveau entre parenthèses
    name_text = display_name.strip() if display_name else ""
    if name_text:
        # Ajouter le niveau entre parenthèses
        name_with_level = f"{name_text} (Niveau: {current_level})"
        name_surface = render_text(name_with_level, name_font, name_color)
        
        # Centrer horizontalement et verticalement dans le panneau rectangulaire supérieur
        name_x = title_panel_rect.x + (title_panel_rect.width - name_surface.get_width()) // 2
        name_y = title_panel_rect.y + (title_panel_rect.height - name_surface.get_height()) // 2
        
        surface.blit(name_surface, (name_x, name_y))
        return title_panel_rect.height
    return 0


def draw_character_presentation(
    surface: pygame.Surface,
    x: int,
    y: int,
    width: int,
    character_presentation: Dict[str, Any],
    name_font: Optional[pygame.font.Font],
    section_font: Optional[pygame.font.Font],
    text_font: Optional[pygame.font.Font],
    name_color: Tuple[int, int, int],
    section_color: Tuple[int, int, int],
    text_color: Tuple[int, int, int],
    padding: int,
    section_spacing: int,
    name_spacing: int,
    bullet_spacing: int,
    title_spacing: int,
    item_spacing: int,
    scale_factor: float = 1.0,
    display_name: str = "",
    include_name: bool = True,
) -> int:
    """Dessine la section de présentation du personnage et retourne la hauteur totale utilisée.

    Args:
        surface: Surface sur laquelle dessiner
        x: Position horizontale de départ
        y: Position verticale de départ
        width: Largeur disponible pour la présentation
        character_presentation: Dictionnaire contenant les informations de présentation
        name_font: Police pour le nom
        section_font: Police pour les titres de section
        text_font: Police pour le texte
        name_color: Couleur du nom
        section_color: Couleur des titres de section
        text_color: Couleur du texte
        padding: Padding horizontal
        section_spacing: Espacement vertical entre les sections
        name_spacing: Espacement après le nom
        bullet_spacing: Espacement entre la puce et le texte
        title_spacing: Espacement après le titre de section
        item_spacing: Espacement entre les items
        scale_factor: Facteur d'échelle (défaut: 1.0)
        display_name: Nom affiché si include_name (ex. depuis player_stats.toml)
        include_name: Si True, dessine le nom du personnage (défaut: True)

    Returns:
        Hauteur totale utilisée par la présentation
    """
    scaled_padding = int(padding * scale_factor)
    scaled_section_spacing = int(section_spacing * scale_factor)
    scaled_name_spacing = int(name_spacing * scale_factor)
    scaled_bullet_spacing = int(bullet_spacing * scale_factor)
    scaled_title_spacing = int(title_spacing * scale_factor)
    scaled_item_spacing = int(item_spacing * scale_factor)

    if name_font is None or section_font is None or text_font is None:
        return 0

    current_y = y

    # Dessiner le nom du personnage (centré) si demandé
    if include_name:
        name_text = display_name.strip() if display_name else ""
        if name_text:
            name_surface = render_text(name_text, name_font, name_color)
            name_x = x + (width - name_surface.get_width()) // 2
            surface.blit(name_surface, (name_x, current_y))
            current_y += name_surface.get_height() + scaled_name_spacing

    # Dessiner les sections (origins, class_role, traits : listes de chaînes — player_stats.toml [presentation])
    section_specs: tuple[tuple[str, str], ...] = (
        ("origins", "Origines"),
        ("class_role", "Classe & Rôle"),
        ("traits", "Traits de caractère"),
    )
    first_section = True
    for key, section_title in section_specs:
        raw = character_presentation.get(key, [])
        if not isinstance(raw, list) or not raw:
            continue
        lines: List[str] = []
        for item in raw:
            if isinstance(item, str) and item.strip():
                lines.append(item.strip())
        if not lines:
            continue
        if not first_section:
            current_y += scaled_section_spacing
        first_section = False
        section_height = draw_presentation_section(
            surface, x, current_y, width, section_title, lines,
            section_font, text_font, section_color, text_color,
            scaled_padding, scaled_section_spacing, scaled_bullet_spacing,
            scaled_title_spacing, scaled_item_spacing,
        )
        current_y += section_height

    return current_y - y


def draw_presentation_section(
    surface: pygame.Surface,
    x: int,
    y: int,
    width: int,
    title: str,
    items: List[str],
    section_font: pygame.font.Font,
    text_font: pygame.font.Font,
    section_color: Tuple[int, int, int],
    text_color: Tuple[int, int, int],
    padding: int,
    section_spacing: int,
    bullet_spacing: int,
    title_spacing: int,
    item_spacing: int,
) -> int:
    """Dessine une section de présentation (Origines, Classe & Rôle, Traits) et retourne la hauteur utilisée.

    Args:
        surface: Surface sur laquelle dessiner
        x: Position horizontale de départ
        y: Position verticale de départ
        width: Largeur disponible
        title: Titre de la section
        items: Liste des éléments à afficher (avec puces si nécessaire)
        section_font: Police pour le titre de section
        text_font: Police pour le texte
        section_color: Couleur des titres de section
        text_color: Couleur du texte
        padding: Padding horizontal
        section_spacing: Espacement vertical entre les sections
        bullet_spacing: Espacement entre la puce et le texte
        title_spacing: Espacement après le titre de section
        item_spacing: Espacement entre les items

    Returns:
        Hauteur totale utilisée par la section
    """
    current_y = y

    # Dessiner le titre de section
    title_surface = render_text(title, section_font, section_color)
    surface.blit(title_surface, (x + padding, current_y))
    current_y += title_surface.get_height() + title_spacing

    # Dessiner les items avec word wrapping
    # Calculer la largeur disponible pour le texte (largeur totale moins padding et espace pour la puce)
    text_available_width = width - padding * 2 - bullet_spacing
    
    for item in items:
        # Vérifier si l'item commence déjà par une puce
        if item.startswith("•"):
            # L'item a déjà une puce, l'afficher tel quel
            item_text = item
        else:
            # Ajouter une puce
            item_text = f"• {item}"
        
        # Utiliser le word wrapping pour diviser le texte en plusieurs lignes si nécessaire
        wrapped_lines = wrap_text(item_text, text_available_width, text_font)
        
        # Dessiner chaque ligne du texte enveloppé
        for line in wrapped_lines:
            line_surface = render_text(line, text_font, text_color)
            surface.blit(line_surface, (x + padding + bullet_spacing, current_y))
            current_y += line_surface.get_height() + item_spacing

    return current_y - y

