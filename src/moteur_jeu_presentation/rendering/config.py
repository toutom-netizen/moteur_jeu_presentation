"""Configuration centrale liée au rendu du jeu."""

from __future__ import annotations

from typing import Tuple

DESIGN_WIDTH = 1920
DESIGN_HEIGHT = 1080
RENDER_WIDTH = 1920
RENDER_HEIGHT = 1080

TARGET_ASPECT_RATIO = RENDER_WIDTH / RENDER_HEIGHT


def get_render_size() -> Tuple[int, int]:
    """Retourne la taille de rendu interne (largeur, hauteur)."""
    return RENDER_WIDTH, RENDER_HEIGHT


def get_design_size() -> Tuple[int, int]:
    """Retourne la taille de conception (largeur, hauteur) utilisée par les fichiers de configuration."""
    return DESIGN_WIDTH, DESIGN_HEIGHT


def compute_scale(display_size: Tuple[int, int]) -> float:
    """Calcule le facteur d'échelle par rapport à la résolution interne.

    Args:
        display_size: Taille réelle de la fenêtre/écran.

    Returns:
        Le plus petit facteur d'échelle à appliquer sur la surface interne
        pour préserver le ratio 16:9 sans rognage.
    """
    width_scale = display_size[0] / RENDER_WIDTH if RENDER_WIDTH else 1.0
    height_scale = display_size[1] / RENDER_HEIGHT if RENDER_HEIGHT else 1.0
    return min(width_scale, height_scale)


def compute_scaled_size(display_size: Tuple[int, int]) -> Tuple[int, int]:
    """Retourne la taille mise à l'échelle ajustée au ratio de référence."""
    scale = compute_scale(display_size)
    return int(RENDER_WIDTH * scale), int(RENDER_HEIGHT * scale)


def compute_design_scale(render_size: Tuple[int, int]) -> Tuple[float, float]:
    """Calcule les facteurs de conversion du repère de conception vers la surface de rendu interne."""
    if DESIGN_WIDTH <= 0 or DESIGN_HEIGHT <= 0:
        return 1.0, 1.0
    return render_size[0] / DESIGN_WIDTH, render_size[1] / DESIGN_HEIGHT


def letterbox_offsets(display_size: Tuple[int, int]) -> Tuple[int, int]:
    """Calcule les offsets pour centrer la surface scalée (letterboxing)."""
    scaled_width, scaled_height = compute_scaled_size(display_size)
    offset_x = (display_size[0] - scaled_width) // 2
    offset_y = (display_size[1] - scaled_height) // 2
    return offset_x, offset_y


def convert_mouse_to_internal(
    mouse_pos: Tuple[int, int], display_size: Tuple[int, int]
) -> Tuple[int, int]:
    """Convertit les coordonnées de la souris de la résolution d'affichage vers la résolution interne.
    
    Args:
        mouse_pos: Position de la souris en coordonnées d'écran réel (x, y)
        display_size: Taille réelle de la fenêtre/écran (width, height)
    
    Returns:
        Position de la souris en coordonnées de la résolution interne (1920x1080)
    """
    mouse_x, mouse_y = mouse_pos
    
    # Calculer les offsets de letterboxing
    offset_x, offset_y = letterbox_offsets(display_size)
    
    # Soustraire les offsets pour obtenir les coordonnées dans la surface redimensionnée
    scaled_x = mouse_x - offset_x
    scaled_y = mouse_y - offset_y
    
    # Calculer la taille redimensionnée
    scaled_size = compute_scaled_size(display_size)
    scaled_width, scaled_height = scaled_size
    
    # Vérifier que la souris est dans la zone de rendu (pas dans les barres noires)
    if scaled_x < 0 or scaled_x >= scaled_width or scaled_y < 0 or scaled_y >= scaled_height:
        # Retourner des coordonnées hors limites pour indiquer que la souris n'est pas sur le rendu
        return (-1, -1)
    
    # Convertir de la taille redimensionnée vers la taille interne
    # Ratio de conversion
    scale_x = RENDER_WIDTH / scaled_width if scaled_width > 0 else 1.0
    scale_y = RENDER_HEIGHT / scaled_height if scaled_height > 0 else 1.0
    
    # Appliquer la conversion
    internal_x = int(scaled_x * scale_x)
    internal_y = int(scaled_y * scale_y)
    
    return (internal_x, internal_y)


