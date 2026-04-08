"""Module de rendu pour le système de parallaxe."""

from .config import (
    TARGET_ASPECT_RATIO,
    compute_design_scale,
    DESIGN_HEIGHT,
    DESIGN_WIDTH,
    compute_scale,
    compute_scaled_size,
    get_design_size,
    get_render_size,
    letterbox_offsets,
)
from .layer import Layer
from .parallax import ParallaxSystem
from .camera_zoom import CameraZoomController, CameraZoomTransform

__all__ = [
    "Layer",
    "ParallaxSystem",
    "CameraZoomController",
    "CameraZoomTransform",
    "get_render_size",
    "get_design_size",
    "compute_scale",
    "compute_scaled_size",
    "compute_design_scale",
    "letterbox_offsets",
    "TARGET_ASPECT_RATIO",
    "DESIGN_WIDTH",
    "DESIGN_HEIGHT",
]

