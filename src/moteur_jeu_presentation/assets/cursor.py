"""Gestion du curseur personnalisé (spec 19)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

import pygame

logger = logging.getLogger("moteur_jeu_presentation.cursor")

# Fichier curseur par défaut dans sprite/cursor/
DEFAULT_CURSOR_FILENAME = "cursor.png"

# Hotspot par défaut : coin supérieur gauche (point de clic au bout du pointeur)
DEFAULT_HOTSPOT = (0, 0)


def load_cursor_surface(project_root: Path) -> Optional[pygame.Surface]:
    """Charge l'image du curseur depuis sprite/cursor/.

    Args:
        project_root: Racine du projet (répertoire contenant sprite/).

    Returns:
        Surface pygame avec transparence, ou None en cas d'échec.
    """
    cursor_path = project_root / "sprite" / "cursor" / DEFAULT_CURSOR_FILENAME
    if not cursor_path.exists():
        return None
    try:
        surface = pygame.image.load(str(cursor_path)).convert_alpha()
        return surface
    except pygame.error as e:
        logger.warning("Impossible de charger le curseur %s : %s", cursor_path, e)
        return None


def set_custom_cursor(
    project_root: Path,
    hotspot: Tuple[int, int] = DEFAULT_HOTSPOT,
) -> None:
    """Applique le curseur personnalisé depuis sprite/cursor/ (spec 19).

    Charge l'image (ex. cursor.png), crée un pygame.cursors.Cursor avec le
    hotspot donné et appelle pygame.mouse.set_cursor(). En cas d'échec,
    le curseur système reste affiché (fallback gracieux).

    Args:
        project_root: Racine du projet.
        hotspot: Point de clic (x, y) dans l'image. Par défaut (0, 0).
    """
    surface = load_cursor_surface(project_root)
    if surface is None:
        return
    w, h = surface.get_size()
    hx, hy = hotspot
    if not (0 <= hx < w and 0 <= hy < h):
        logger.warning(
            "Hotspot (%d, %d) hors bornes de l'image curseur %dx%d, utilisation (0, 0)",
            hx, hy, w, h,
        )
        hotspot = (0, 0)
    try:
        cursor = pygame.cursors.Cursor(hotspot, surface)
        pygame.mouse.set_cursor(cursor)
        logger.debug("Curseur personnalisé appliqué depuis sprite/cursor/%s", DEFAULT_CURSOR_FILENAME)
    except pygame.error as e:
        logger.warning("Impossible d'appliquer le curseur personnalisé : %s", e)
