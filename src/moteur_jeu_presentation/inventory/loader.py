"""Module de chargement de la configuration des objets d'inventaire."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

try:
    # Python 3.11+ a tomllib intégré
    import tomllib as tomli  # type: ignore
except ImportError:
    # Python < 3.11 nécessite tomli
    try:
        import tomli
    except ImportError:
        raise ImportError(
            "tomli is required for Python < 3.11. Install it with: pip install tomli"
        )

from .config import InventoryItem, InventoryItemConfig

logger = logging.getLogger(__name__)


class InventoryItemLoader:
    """Chargeur de fichier de configuration des objets d'inventaire."""

    def __init__(self, config_path: Path) -> None:
        """Initialise le chargeur de configuration.

        Args:
            config_path: Chemin vers le fichier inventory_items.toml
        """
        self.config_path = Path(config_path)

    def load_items(self) -> InventoryItemConfig:
        """Charge le fichier de configuration des objets.

        Returns:
            Configuration des objets chargée

        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            ValueError: Si le format du fichier est invalide
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Fichier de configuration d'inventaire introuvable: {self.config_path}")

        try:
            with open(self.config_path, "rb") as f:
                data = tomli.load(f)
        except Exception as e:
            raise ValueError(f"Erreur lors de la lecture du fichier TOML: {e}") from e

        items: Dict[str, InventoryItem] = {}

        # Résoudre le chemin de base (répertoire parent du fichier de config)
        # Le fichier est dans config/, donc on remonte d'un niveau pour arriver à la racine
        project_root = self.config_path.parent.parent

        # Vérifier que la section [items] existe
        if "items" not in data:
            raise ValueError("Missing [items] section in inventory configuration file")

        # Parcourir toutes les sections [items.*]
        # La structure TOML crée une clé "items" avec un dictionnaire imbriqué
        items_data = data["items"]
        for item_id, value in items_data.items():
            # Vérifier les champs obligatoires
            if "sprite_path" not in value:
                raise ValueError(f"Missing sprite_path in item '{item_id}'")
            if "cell_width" not in value:
                raise ValueError(f"Missing cell_width in item '{item_id}'")
            if "cell_height" not in value:
                raise ValueError(f"Missing cell_height in item '{item_id}'")
            if "cell_row" not in value:
                raise ValueError(f"Missing cell_row in item '{item_id}'")
            if "cell_col" not in value:
                raise ValueError(f"Missing cell_col in item '{item_id}'")

            # Récupérer les valeurs
            sprite_path_str = value["sprite_path"]
            cell_width = int(value["cell_width"])
            cell_height = int(value["cell_height"])
            cell_row = int(value["cell_row"])
            cell_col = int(value["cell_col"])
            name = value.get("name", item_id)  # Par défaut: l'ID technique
            description = value.get("description")

            # Résoudre le chemin du sprite (relatif à la racine du projet)
            sprite_path = project_root / sprite_path_str

            # Vérifier que le sprite sheet existe
            if not sprite_path.exists():
                raise FileNotFoundError(f"Sprite sheet not found for item '{item_id}': {sprite_path}")

            # Vérifier que les dimensions sont positives
            if cell_width <= 0 or cell_height <= 0:
                raise ValueError(
                    f"Invalid cell dimensions for item '{item_id}': "
                    f"cell_width={cell_width}, cell_height={cell_height} (must be > 0)"
                )

            # Vérifier que les coordonnées de cellule sont valides
            if cell_row < 0 or cell_col < 0:
                raise ValueError(
                    f"Invalid cell coordinates for item '{item_id}': "
                    f"cell_row={cell_row}, cell_col={cell_col} (must be >= 0)"
                )

            # Créer l'objet d'inventaire
            item = InventoryItem(
                item_id=item_id,
                name=name,
                description=description,
                sprite_path=sprite_path,
                cell_width=cell_width,
                cell_height=cell_height,
                cell_row=cell_row,
                cell_col=cell_col,
            )

            items[item_id] = item

        config = InventoryItemConfig(items=items)

        # Valider la configuration
        self.validate_items(config)

        return config

    def validate_items(self, config: InventoryItemConfig) -> None:
        """Valide la configuration des objets.

        Args:
            config: Configuration à valider

        Raises:
            ValueError: Si la configuration est invalide
        """
        import pygame

        # Vérifier que tous les sprite sheets existent et que les cellules sont valides
        for item_id, item in config.items.items():
            if not item.sprite_path.exists():
                raise FileNotFoundError(f"Sprite sheet not found for item '{item_id}': {item.sprite_path}")

            # Charger temporairement le sprite sheet pour valider les cellules
            try:
                sprite_sheet = pygame.image.load(str(item.sprite_path))
                sheet_width = sprite_sheet.get_width()
                sheet_height = sprite_sheet.get_height()

                # Calculer les limites de la cellule
                max_col = (sheet_width - 1) // item.cell_width
                max_row = (sheet_height - 1) // item.cell_height

                if item.cell_row > max_row or item.cell_col > max_col:
                    raise ValueError(
                        f"Cell ({item.cell_row}, {item.cell_col}) out of bounds for sprite sheet "
                        f"'{item.sprite_path}': max_row={max_row}, max_col={max_col}"
                    )
            except pygame.error as e:
                raise ValueError(f"Error loading sprite sheet for item '{item_id}': {e}") from e

