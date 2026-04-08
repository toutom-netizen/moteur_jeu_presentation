"""Module de configuration des objets d'inventaire."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

import pygame



@dataclass
class InventoryItem:
    """Représente un objet d'inventaire avec sa configuration."""

    item_id: str  # ID technique unique
    name: str  # Nom d'affichage
    sprite_path: Path  # Chemin vers le sprite sheet
    cell_width: int  # Largeur d'une cellule en pixels
    cell_height: int  # Hauteur d'une cellule en pixels
    cell_row: int  # Numéro de ligne (index 0) de la cellule dans le sprite sheet
    cell_col: int  # Numéro de colonne (index 0) de la cellule dans le sprite sheet
    description: Optional[str] = None  # Description optionnelle
    sprite_surface: Optional[pygame.Surface] = None  # Sprite extrait et chargé (mis en cache)

    def load_sprite(self, sprite_sheet_cache: Dict[str, pygame.Surface]) -> pygame.Surface:
        """Charge et extrait le sprite de l'objet depuis le sprite sheet.

        Args:
            sprite_sheet_cache: Cache des sprite sheets chargés (clé = sprite_path, valeur = Surface)

        Returns:
            Surface pygame contenant le sprite extrait de la cellule
        """
        if self.sprite_surface is None:
            # Charger le sprite sheet depuis le cache (ou le charger si absent)
            sprite_path_str = str(self.sprite_path)
            if sprite_path_str not in sprite_sheet_cache:
                sprite_sheet_cache[sprite_path_str] = pygame.image.load(sprite_path_str).convert_alpha()

            sprite_sheet = sprite_sheet_cache[sprite_path_str]

            # Extraire la cellule du sprite sheet
            self.sprite_surface = self._extract_cell(sprite_sheet)

        return self.sprite_surface

    def _extract_cell(self, sprite_sheet: pygame.Surface) -> pygame.Surface:
        """Extrait la cellule correspondante du sprite sheet.

        Args:
            sprite_sheet: Surface du sprite sheet complet

        Returns:
            Surface pygame contenant la cellule extraite
        """
        # Calculer la position de la cellule
        x = self.cell_col * self.cell_width
        y = self.cell_row * self.cell_height

        # Valider les limites du sprite sheet
        sheet_width = sprite_sheet.get_width()
        sheet_height = sprite_sheet.get_height()

        if sheet_width <= 0 or sheet_height <= 0:
            return pygame.Surface((self.cell_width, self.cell_height), pygame.SRCALPHA)

        # S'assurer que le point d'origine reste dans les limites
        max_x = max(sheet_width - self.cell_width, 0)
        max_y = max(sheet_height - self.cell_height, 0)
        x = max(0, min(x, max_x))
        y = max(0, min(y, max_y))

        # Ajuster la taille du rectangle si nécessaire
        rect_width = min(self.cell_width, sheet_width - x)
        rect_height = min(self.cell_height, sheet_height - y)

        if rect_width <= 0 or rect_height <= 0:
            return pygame.Surface((self.cell_width, self.cell_height), pygame.SRCALPHA)

        rect = pygame.Rect(x, y, rect_width, rect_height)

        try:
            sprite = sprite_sheet.subsurface(rect).copy()
            if sprite.get_width() != self.cell_width or sprite.get_height() != self.cell_height:
                resized = pygame.Surface((self.cell_width, self.cell_height), pygame.SRCALPHA)
                resized.blit(sprite, (0, 0))
                sprite = resized
            return sprite.convert_alpha()
        except (ValueError, pygame.error):
            return pygame.Surface((self.cell_width, self.cell_height), pygame.SRCALPHA)


@dataclass
class InventoryItemConfig:
    """Configuration complète des objets d'inventaire disponibles."""

    items: Dict[str, InventoryItem] = field(default_factory=dict)  # Indexé par item_id

    def get_item(self, item_id: str) -> Optional[InventoryItem]:
        """Récupère un objet par son ID technique.

        Args:
            item_id: ID technique de l'objet

        Returns:
            L'objet correspondant, ou None si introuvable
        """
        return self.items.get(item_id)


@dataclass
class ItemAnimationState:
    """État d'animation pour un objet d'inventaire."""

    animation_type: Literal["add", "remove"]  # Type d'animation ("add" ou "remove")
    progress: float  # Progression de l'animation (0.0 à 1.0)
    offset_x: float  # Décalage horizontal pour l'animation (en pixels)
    offset_y: float  # Décalage vertical pour l'animation (en pixels)
    scale: float = 1.0  # Facteur d'échelle pour l'animation (1.0 = taille normale)
    opacity: int = 255  # Opacité de l'objet (0 à 255)
    is_complete: bool = False  # Indique si l'animation est terminée
    particle_effect_id: Optional[str] = None  # Identifiant de l'effet de particules dans le système global
    item_sprite: Optional[pygame.Surface] = None  # Sprite de l'objet (optionnel, peut être utilisé pour le rendu de l'objet pendant l'animation)
    particle_base_x: float = 0.0  # Position de base X pour les particules (en coordonnées écran, généralement le centre de l'écran)
    particle_base_y: float = 0.0  # Position de base Y pour les particules (en coordonnées écran, généralement le centre de l'écran)
    start_x: float = 0.0  # Position de départ X pour l'animation (en pixels, coordonnées écran)
    start_y: float = 0.0  # Position de départ Y pour l'animation (en pixels, coordonnées écran)
    target_x: float = 0.0  # Position cible X pour l'animation (en pixels, coordonnées écran)
    target_y: float = 0.0  # Position cible Y pour l'animation (en pixels, coordonnées écran)
    screen_center_x: float = 0.0  # Position X du centre de l'écran (en pixels, coordonnées écran)
    screen_center_y: float = 0.0  # Position Y du centre de l'écran (en pixels, coordonnées écran)

