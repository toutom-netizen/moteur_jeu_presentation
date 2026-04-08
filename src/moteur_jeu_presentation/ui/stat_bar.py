"""Module de gestion des barres de statistiques pour l'interface."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

import pygame

from .text_utils import render_text

if TYPE_CHECKING:
    from ..entities.player import Player


def get_bar_color(fill_percentage: float) -> Tuple[int, int, int]:
    """Retourne la couleur de la jauge selon le pourcentage.

    Args:
        fill_percentage: Pourcentage de remplissage (0-100)

    Returns:
        Couleur RGB de la jauge
    """
    if fill_percentage <= 33:
        # Rouge (faible)
        return (220, 50, 50)
    elif fill_percentage <= 66:
        # Orange (moyen)
        return (255, 165, 0)
    else:
        # Vert (élevé)
        return (50, 220, 50)


def has_stat_progressed(player: "Player", stat_identifier: str) -> bool:
    """Vérifie si une statistique a progressé par rapport au niveau précédent.

    Args:
        player: Instance du joueur
        stat_identifier: Identifiant de la statistique (ex: "force", "vitesse")

    Returns:
        True si la statistique a progressé, False sinon
    """
    current_level = player.level_manager.level
    if current_level <= 1:
        return False  # Pas de niveau précédent

    if not player.level_manager.stats_config:
        return False  # Pas de configuration de stats

    try:
        current_value = player.level_manager.get_stat_value(stat_identifier)
        previous_value = player.level_manager.stats_config.get_stat_value(
            stat_identifier, current_level - 1
        )
        return current_value > previous_value
    except (KeyError, ValueError):
        return False  # Statistique inexistante ou niveau invalide


def draw_progression_indicator(
    surface: pygame.Surface,
    x: int,
    y: int,
    font: pygame.font.Font,
    scale_factor: float = 1.0,
) -> int:
    """Dessine l'indicateur de progression "^" en jaune.

    Args:
        surface: Surface sur laquelle dessiner
        x: Position horizontale
        y: Position verticale
        font: Police à utiliser
        scale_factor: Facteur d'échelle à appliquer

    Returns:
        Largeur utilisée par l'indicateur (pour le positionnement des éléments suivants)
    """
    # Couleur jaune pour l'indicateur
    indicator_color = (255, 215, 0)  # Jaune doré
    indicator_text = "^"

    # Rendre le texte de l'indicateur
    indicator_surface = render_text(indicator_text, font, indicator_color)
    surface.blit(indicator_surface, (x, y))

    return indicator_surface.get_width()

