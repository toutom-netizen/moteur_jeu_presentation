"""Post-process camera zoom controller.

This module implements a "camera zoom" effect as a post-process:
- Render the scene on a surface of size get_render_size()
- Apply a scale + translation (blit transform) to "zoom" without affecting gameplay coordinates

The controller computes a transform that can be applied to any surface rendered in internal
resolution coordinates (1920x1080 by default).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Sequence, Tuple

import pygame

from .config import compute_design_scale, get_render_size


@dataclass(frozen=True)
class CameraZoomTransform:
    """Transform to apply to a full-scene surface."""

    zoom: float
    offset_x: int
    offset_y: int
    scaled_size: tuple[int, int]


def _clamp(value: float, low: float, high: float) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


class CameraZoomController:
    """Controls a progressive zoom for the gameplay scene."""

    def __init__(self) -> None:
        self._current_zoom: float = 1.0
        self._start_zoom: float = 1.0
        self._target_zoom: float = 1.0

        self._current_offset_x: float = 0.0
        self._current_offset_y: float = 0.0
        self._start_offset_x: float = 0.0
        self._start_offset_y: float = 0.0
        self._target_offset_x: float = 0.0
        self._target_offset_y: float = 0.0

        self._timer: float = 0.0
        self._duration: float = 0.0
        self._is_animating: bool = False
        self._transition_t: float = 0.0

        # Bottom margin under player's feet (in INTERNAL render coordinates)
        self._bottom_margin_px: int = self._convert_design_y_to_render(50.0)
        self._keep_bubbles_visible: bool = True

        self._camera_state: Literal[
            "follow_player",
            "transition_to_sprite",
            "locked_on_sprite",
            "transition_to_player",
        ] = "follow_player"

        # Sprite zoom data
        self._sprite_tag: Optional[str] = None  # Tag of the sprite to zoom on
        self._sprite_offset_x_render: float = 0.0  # Offset X in render coordinates
        self._sprite_offset_y_render: float = 0.0  # Offset Y in render coordinates
        self._sprite_center_x: Optional[float] = None
        self._sprite_center_y: Optional[float] = None

        self._last_player_draw_rect: Optional[pygame.Rect] = None
        self._current_camera_x: float = 0.0
        self._current_camera_x_override: Optional[float] = None
        self._start_camera_x: float = 0.0
        self._target_camera_x: float = 0.0

    @staticmethod
    def _convert_design_y_to_render(value_design_px: float) -> int:
        render_w, render_h = get_render_size()
        _, scale_y = compute_design_scale((render_w, render_h))
        return int(round(value_design_px * scale_y))

    @property
    def current_zoom(self) -> float:
        return self._current_zoom

    @property
    def is_active(self) -> bool:
        # Active if currently animating or the zoom is not neutral
        return (
            self._is_animating
            or abs(self._current_zoom - 1.0) > 1e-4
            or self._camera_state != "follow_player"
        )

    @property
    def is_camera_fixed(self) -> bool:
        """Returns True if the camera should be fixed (not follow player)."""
        return self._camera_state != "follow_player"

    def set_current_camera_x(self, camera_x: float) -> None:
        """Sync current camera_x (world) for transition computations."""
        self._current_camera_x = camera_x

    def get_camera_x_override(self) -> Optional[float]:
        """Returns a camera_x override when a transition/lock is active."""
        return self._current_camera_x_override

    def start_zoom(
        self,
        zoom_percent: float,
        duration: float = 0.8,
        bottom_margin_design_px: float = 50.0,
        keep_bubbles_visible: bool = True,
    ) -> None:
        """Start a progressive zoom to zoom_percent (100 => neutral) on the player."""
        if zoom_percent <= 0:
            raise ValueError("zoom_percent must be > 0")
        if duration < 0:
            raise ValueError("duration must be >= 0")

        self._camera_state = "follow_player"
        self._keep_bubbles_visible = keep_bubbles_visible
        self._bottom_margin_px = self._convert_design_y_to_render(bottom_margin_design_px)
        if self._bottom_margin_px < 0:
            self._bottom_margin_px = 0

        self._start_zoom = self._current_zoom
        self._target_zoom = zoom_percent / 100.0
        self._timer = 0.0
        self._duration = float(duration)
        self._transition_t = 0.0
        self._is_animating = self._duration > 0.0

        if not self._is_animating:
            self._current_zoom = self._target_zoom

    def start_zoom_sprite(
        self,
        sprite_tag: str,
        zoom_percent: float,
        offset_x_design_px: float = 0.0,
        offset_y_design_px: float = 0.0,
        duration: float = 0.8,
        keep_bubbles_visible: bool = True,
        layers_by_tag: Optional[Dict[str, List]] = None,
    ) -> None:
        """Start a progressive zoom to zoom_percent (100 => neutral) on a sprite.
        
        Args:
            sprite_tag: Tag of the sprite to zoom on
            zoom_percent: Zoom percentage (100 = neutral)
            offset_x_design_px: Horizontal offset in design pixels (1920x1080)
            offset_y_design_px: Vertical offset in design pixels (1920x1080)
            duration: Animation duration in seconds
            keep_bubbles_visible: Whether to cap zoom to keep bubbles visible
            layers_by_tag: Dictionary of layers indexed by tag (required to locate sprite)
        """
        if zoom_percent <= 0:
            raise ValueError("zoom_percent must be > 0")
        if duration < 0:
            raise ValueError("duration must be >= 0")
        if layers_by_tag is None:
            raise ValueError("layers_by_tag is required for sprite zoom")

        self._sprite_tag = sprite_tag
        self._keep_bubbles_visible = keep_bubbles_visible

        # Convert offsets from design space to render space
        render_w, render_h = get_render_size()
        scale_x, scale_y = compute_design_scale((render_w, render_h))
        self._sprite_offset_x_render = offset_x_design_px * scale_x
        self._sprite_offset_y_render = offset_y_design_px * scale_y

        sprite_center = self._get_sprite_center(layers_by_tag, sprite_tag)
        if sprite_center is None:
            raise ValueError(f"Sprite tag introuvable: {sprite_tag}")
        self._sprite_center_x, self._sprite_center_y = sprite_center

        self._start_zoom = self._current_zoom
        self._target_zoom = zoom_percent / 100.0
        self._timer = 0.0
        self._duration = float(duration)
        self._transition_t = 0.0
        self._is_animating = self._duration > 0.0

        self._start_offset_x = 0.0
        self._target_offset_x = 0.0
        self._start_offset_y = self._current_offset_y
        self._target_offset_y = self._compute_sprite_offset_y(
            zoom=self._target_zoom,
            sprite_center_y=self._sprite_center_y,
        )

        self._start_camera_x = self._current_camera_x
        self._target_camera_x = self._compute_sprite_camera_x(self._target_zoom)
        self._current_camera_x_override = self._start_camera_x
        self._camera_state = "transition_to_sprite"

        if not self._is_animating:
            self._current_zoom = self._target_zoom
            self._current_offset_x = 0.0
            self._current_offset_y = self._target_offset_y
            self._current_camera_x_override = self._target_camera_x
            self._camera_state = "locked_on_sprite"

    def reset_zoom(self, duration: float = 0.8, player_draw_rect: Optional[pygame.Rect] = None) -> None:
        """Reset zoom back to 100% progressively.
        
        If currently in sprite zoom mode, the camera remains fixed during the dezoom animation
        and only switches back to player follow mode once the animation is complete.
        """
        if duration < 0:
            raise ValueError("duration must be >= 0")
        if self._camera_state in ("locked_on_sprite", "transition_to_sprite"):
            if player_draw_rect is not None:
                self._last_player_draw_rect = player_draw_rect
            self._start_offset_x = self._current_offset_x
            self._start_offset_y = self._current_offset_y
            self._target_offset_x = 0.0
            self._target_offset_y = 0.0
            # IMPORTANT: use _current_camera_x_override (actual locked position) as start
            # not _current_camera_x (which may contain stale/different value)
            self._start_camera_x = self._current_camera_x_override if self._current_camera_x_override is not None else self._current_camera_x
            self._target_camera_x = self._compute_player_camera_x(self._last_player_draw_rect, self._target_zoom)
            self._current_camera_x_override = self._start_camera_x
            self._camera_state = "transition_to_player"
            self._transition_t = 0.0

        self._start_zoom = self._current_zoom
        self._target_zoom = 1.0
        self._timer = 0.0
        self._duration = float(duration)
        self._is_animating = self._duration > 0.0
        if not self._is_animating:
            # Animation instantanée : reset immédiat
            self._current_zoom = 1.0
            self._camera_state = "follow_player"
            self._sprite_tag = None
            self._sprite_offset_x_render = 0.0
            self._sprite_offset_y_render = 0.0
            self._sprite_center_x = None
            self._sprite_center_y = None
            self._current_offset_x = 0.0
            self._current_offset_y = 0.0
            self._current_camera_x_override = None

    def update(self, dt: float) -> None:
        if not self._is_animating:
            return

        if dt < 0:
            dt = 0.0

        self._timer += dt
        t = _clamp(self._timer / self._duration, 0.0, 1.0)
        self._transition_t = t
        self._current_zoom = self._start_zoom + (self._target_zoom - self._start_zoom) * t
        if self._camera_state in ("transition_to_sprite", "transition_to_player"):
            if self._camera_state == "transition_to_player" and self._last_player_draw_rect is not None:
                self._target_camera_x = self._compute_player_camera_x(
                    self._last_player_draw_rect,
                    self._target_zoom,
                )
            self._current_camera_x_override = (
                self._start_camera_x + (self._target_camera_x - self._start_camera_x) * t
            )

        if t >= 1.0:
            self._current_zoom = self._target_zoom
            self._is_animating = False
            if self._camera_state == "transition_to_sprite":
                self._camera_state = "locked_on_sprite"
                self._current_offset_x = self._target_offset_x
                self._current_offset_y = self._target_offset_y
                self._current_camera_x_override = self._target_camera_x
            elif self._camera_state == "transition_to_player":
                self._camera_state = "follow_player"
                self._sprite_tag = None
                self._sprite_offset_x_render = 0.0
                self._sprite_offset_y_render = 0.0
                self._sprite_center_x = None
                self._sprite_center_y = None
                self._current_offset_x = 0.0
                self._current_offset_y = 0.0
                self._current_camera_x_override = None

    def compute_transform(
        self,
        player_draw_rect: pygame.Rect,
        bubble_rects: Optional[Sequence[pygame.Rect]] = None,
        layers_by_tag: Optional[Dict[str, List]] = None,
    ) -> CameraZoomTransform:
        """Compute the transform to apply for current zoom.

        Args:
            player_draw_rect: Player draw rect in internal surface coordinates (pre-zoom).
            bubble_rects: Rectangles for active speech bubbles in internal coordinates (pre-zoom).
            layers_by_tag: Dictionary of layers indexed by tag (required for sprite zoom mode).
        """
        self._last_player_draw_rect = player_draw_rect
        if self._camera_state in ("transition_to_sprite", "transition_to_player"):
            return self._compute_transform_transition(bubble_rects)
        if self._camera_state == "locked_on_sprite":
            return self._compute_transform_locked(bubble_rects)
        return self._compute_transform_player(player_draw_rect, bubble_rects)

    def _compute_transform_player(
        self,
        player_draw_rect: pygame.Rect,
        bubble_rects: Optional[Sequence[pygame.Rect]] = None,
    ) -> CameraZoomTransform:
        """Compute the transform for player zoom mode."""
        screen_w, screen_h = get_render_size()
        zoom = self._current_zoom

        # Bubble union (if any)
        bubbles_union: Optional[pygame.Rect] = None
        if bubble_rects:
            for r in bubble_rects:
                if r.width <= 0 or r.height <= 0:
                    continue
                bubbles_union = r.copy() if bubbles_union is None else bubbles_union.union(r)

        # If requested, cap the zoom so bubbles can fit on screen.
        if self._keep_bubbles_visible and bubbles_union is not None and bubbles_union.width > 0 and bubbles_union.height > 0:
            max_zoom_w = screen_w / float(bubbles_union.width)
            max_zoom_h = screen_h / float(bubbles_union.height)
            max_zoom = min(max_zoom_w, max_zoom_h)
            if max_zoom > 0:
                zoom = min(zoom, max_zoom)

        # Scaled surface size (scene surface is screen-sized)
        scaled_w = max(1, int(round(screen_w * zoom)))
        scaled_h = max(1, int(round(screen_h * zoom)))

        # Anchor: keep player horizontally centered and keep feet at (H - bottom_margin)
        player_anchor_x_scene = player_draw_rect.centerx
        player_feet_y_scene = player_draw_rect.bottom
        target_x_screen = screen_w / 2.0
        target_feet_y_screen = float(screen_h - self._bottom_margin_px)

        offset_x_target = target_x_screen - player_anchor_x_scene * zoom
        offset_y_target = target_feet_y_screen - player_feet_y_scene * zoom

        # Global bounds (avoid empty space when zooming in; for zoom out, keep within screen)
        if scaled_w >= screen_w:
            global_min_x = screen_w - scaled_w
            global_max_x = 0
        else:
            global_min_x = 0
            global_max_x = screen_w - scaled_w

        if scaled_h >= screen_h:
            global_min_y = screen_h - scaled_h
            global_max_y = 0
        else:
            global_min_y = 0
            global_max_y = screen_h - scaled_h

        min_x = float(global_min_x)
        max_x = float(global_max_x)
        min_y = float(global_min_y)
        max_y = float(global_max_y)

        # Bubble visibility bounds
        if self._keep_bubbles_visible and bubbles_union is not None and bubbles_union.width > 0 and bubbles_union.height > 0:
            bubble_min_x = -bubbles_union.left * zoom
            bubble_max_x = screen_w - bubbles_union.right * zoom
            bubble_min_y = -bubbles_union.top * zoom
            bubble_max_y = screen_h - bubbles_union.bottom * zoom

            min_x = max(min_x, bubble_min_x)
            max_x = min(max_x, bubble_max_x)
            min_y = max(min_y, bubble_min_y)
            max_y = min(max_y, bubble_max_y)

        # If constraints are inconsistent, fall back to global bounds.
        if min_x > max_x:
            min_x, max_x = float(global_min_x), float(global_max_x)
        if min_y > max_y:
            min_y, max_y = float(global_min_y), float(global_max_y)

        offset_x = float(_clamp(offset_x_target, min_x, max_x))
        offset_y = float(_clamp(offset_y_target, min_y, max_y))

        self._current_offset_x = offset_x
        self._current_offset_y = offset_y

        return CameraZoomTransform(
            zoom=zoom,
            offset_x=int(round(offset_x)),
            offset_y=int(round(offset_y)),
            scaled_size=(scaled_w, scaled_h),
        )

    def _compute_transform_transition(
        self,
        bubble_rects: Optional[Sequence[pygame.Rect]] = None,
    ) -> CameraZoomTransform:
        """Compute transform while transitioning between two fixed positions."""
        screen_w, screen_h = get_render_size()
        zoom = self._current_zoom

        scaled_w = max(1, int(round(screen_w * zoom)))
        scaled_h = max(1, int(round(screen_h * zoom)))

        offset_x = self._start_offset_x + (self._target_offset_x - self._start_offset_x) * self._transition_t
        if self._camera_state == "transition_to_sprite" and self._sprite_center_y is not None:
            offset_y = self._compute_sprite_offset_y(
                zoom=zoom,
                sprite_center_y=self._sprite_center_y,
            )
        else:
            offset_y = self._start_offset_y + (self._target_offset_y - self._start_offset_y) * self._transition_t

        offset_x, offset_y = self._clamp_offsets(
            offset_x,
            offset_y,
            zoom,
            bubble_rects,
        )

        self._current_offset_x = offset_x
        self._current_offset_y = offset_y

        return CameraZoomTransform(
            zoom=zoom,
            offset_x=int(round(offset_x)),
            offset_y=int(round(offset_y)),
            scaled_size=(scaled_w, scaled_h),
        )

    def _compute_transform_locked(
        self,
        bubble_rects: Optional[Sequence[pygame.Rect]] = None,
    ) -> CameraZoomTransform:
        """Compute transform while camera is locked on a sprite."""
        screen_w, screen_h = get_render_size()
        zoom = self._current_zoom
        scaled_w = max(1, int(round(screen_w * zoom)))
        scaled_h = max(1, int(round(screen_h * zoom)))

        offset_x, offset_y = self._clamp_offsets(
            self._current_offset_x,
            self._current_offset_y,
            zoom,
            bubble_rects,
        )
        self._current_offset_x = offset_x
        self._current_offset_y = offset_y

        return CameraZoomTransform(
            zoom=zoom,
            offset_x=int(round(offset_x)),
            offset_y=int(round(offset_y)),
            scaled_size=(scaled_w, scaled_h),
        )

    def _get_sprite_center(
        self,
        layers_by_tag: Dict[str, List],
        sprite_tag: str,
    ) -> Optional[tuple[float, float]]:
        layers = layers_by_tag.get(sprite_tag, [])
        if not layers:
            return None
        layer = layers[0]
        sprite_center_x = layer.world_x_offset + layer.surface.get_width() / 2.0
        sprite_center_y = layer.world_y_offset + layer.surface.get_height() / 2.0
        return sprite_center_x, sprite_center_y

    def _compute_sprite_offset(
        self,
        *,
        zoom: float,
        sprite_center: float,
        sprite_center_y: float,
        bubble_rects: Optional[Sequence[pygame.Rect]],
    ) -> tuple[float, float]:
        screen_w, screen_h = get_render_size()
        target_x_screen = screen_w / 2.0 + self._sprite_offset_x_render
        target_y_screen = screen_h / 2.0 + self._sprite_offset_y_render
        offset_x_target = target_x_screen - sprite_center * zoom
        offset_y_target = target_y_screen - sprite_center_y * zoom
        return self._clamp_offsets(offset_x_target, offset_y_target, zoom, bubble_rects)

    def _compute_player_camera_x(
        self,
        player_draw_rect: Optional[pygame.Rect],
        zoom: float,
    ) -> float:
        if player_draw_rect is None:
            return self._current_camera_x
        screen_w, _ = get_render_size()
        # IMPORTANT: use actual camera position for world conversion
        # During transitions, _current_camera_x_override contains the real camera position
        actual_camera_x = self._current_camera_x_override if self._current_camera_x_override is not None else self._current_camera_x
        player_center_world = player_draw_rect.centerx + actual_camera_x
        # For neutral zoom (1.0), camera_x = player_world - screen_w/2 to center player
        # The formula doesn't need zoom adjustment since camera_x is in world space
        return player_center_world - screen_w / 2.0

    def _compute_sprite_camera_x(self, zoom: float) -> float:
        if self._sprite_center_x is None:
            return self._current_camera_x
        screen_w, _ = get_render_size()
        if zoom <= 0:
            return self._sprite_center_x - screen_w / 2.0 - self._sprite_offset_x_render
        target_x_screen = screen_w / 2.0 + self._sprite_offset_x_render
        return self._sprite_center_x - target_x_screen / zoom

    def _compute_sprite_offset_y(self, *, zoom: float, sprite_center_y: Optional[float]) -> float:
        if sprite_center_y is None:
            return 0.0
        screen_w, screen_h = get_render_size()
        target_y_screen = screen_h / 2.0 + self._sprite_offset_y_render
        offset_y_target = target_y_screen - sprite_center_y * zoom
        _, offset_y = self._clamp_offsets(0.0, offset_y_target, zoom, None)
        return offset_y

    def _clamp_offsets(
        self,
        offset_x: float,
        offset_y: float,
        zoom: float,
        bubble_rects: Optional[Sequence[pygame.Rect]],
    ) -> tuple[float, float]:
        screen_w, screen_h = get_render_size()
        scaled_w = max(1, int(round(screen_w * zoom)))
        scaled_h = max(1, int(round(screen_h * zoom)))

        if scaled_w >= screen_w:
            global_min_x = screen_w - scaled_w
            global_max_x = 0
        else:
            global_min_x = 0
            global_max_x = screen_w - scaled_w

        if scaled_h >= screen_h:
            global_min_y = screen_h - scaled_h
            global_max_y = 0
        else:
            global_min_y = 0
            global_max_y = screen_h - scaled_h

        min_x = float(global_min_x)
        max_x = float(global_max_x)
        min_y = float(global_min_y)
        max_y = float(global_max_y)

        bubbles_union: Optional[pygame.Rect] = None
        if self._keep_bubbles_visible and bubble_rects:
            for r in bubble_rects:
                if r.width <= 0 or r.height <= 0:
                    continue
                bubbles_union = r.copy() if bubbles_union is None else bubbles_union.union(r)

        if self._keep_bubbles_visible and bubbles_union is not None:
            bubble_min_x = -bubbles_union.left * zoom
            bubble_max_x = screen_w - bubbles_union.right * zoom
            bubble_min_y = -bubbles_union.top * zoom
            bubble_max_y = screen_h - bubbles_union.bottom * zoom

            min_x = max(min_x, bubble_min_x)
            max_x = min(max_x, bubble_max_x)
            min_y = max(min_y, bubble_min_y)
            max_y = min(max_y, bubble_max_y)

        if min_x > max_x:
            min_x, max_x = float(global_min_x), float(global_max_x)
        if min_y > max_y:
            min_y, max_y = float(global_min_y), float(global_max_y)

        return _clamp(offset_x, min_x, max_x), _clamp(offset_y, min_y, max_y)
