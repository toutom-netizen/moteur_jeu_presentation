"""Module de chargement des fichiers de niveau."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pygame

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

from .config import LevelConfig, RowMapping, SpriteMapping, SpriteSheetConfig
from ..rendering.config import compute_design_scale
from ..entities.player_level_manager import (
    DEFAULT_PLAYER_LEVEL,
    MAX_PLAYER_LEVEL,
    MIN_PLAYER_LEVEL,
)

if TYPE_CHECKING:
    from ..rendering.parallax import ParallaxSystem

# Vitesses de défilement par défaut selon la profondeur
DEFAULT_SCROLL_SPEEDS = {
    0: 0.2,  # Background
    1: 0.5,  # Premier fond
    2: 1.0,  # Gameplay
    3: 1.3,  # Foreground
}


class LevelLoader:
    """Chargeur de fichiers de niveau."""

    def __init__(self, assets_dir: Path) -> None:
        """Initialise le chargeur de niveau.

        Args:
            assets_dir: Répertoire de base pour les ressources
        """
        self.assets_dir = Path(assets_dir)

    def load_level(
        self,
        level_path: Path,
        *,
        max_player_level: int | None = None,
    ) -> LevelConfig:
        """Charge un fichier de niveau.

        Args:
            level_path: Chemin vers le fichier .niveau ou .toml
            max_player_level: Borne supérieure pour ``[player].level`` (défaut: ``MAX_PLAYER_LEVEL``)

        Returns:
            Configuration du niveau chargée

        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            ValueError: Si le format du fichier est invalide
        """
        player_cap = max_player_level if max_player_level is not None else MAX_PLAYER_LEVEL
        level_path = Path(level_path)

        if not level_path.exists():
            raise FileNotFoundError(f"Fichier de niveau introuvable: {level_path}")

        try:
            with open(level_path, "rb") as f:
                data = tomli.load(f)
        except Exception as e:
            raise ValueError(f"Erreur lors du parsing du fichier TOML: {e}") from e

        # Valider et extraire la configuration des sprite sheets
        sprite_sheets: dict[str, SpriteSheetConfig] = {}
        
        # Support du nouveau format [sprite_sheets] (pluriel)
        if "sprite_sheets" in data:
            sprite_sheets_data = data["sprite_sheets"]
            if not isinstance(sprite_sheets_data, dict):
                raise ValueError("Section [sprite_sheets] doit être un dictionnaire")
            
            for sheet_name, sheet_data in sprite_sheets_data.items():
                if not isinstance(sheet_data, dict):
                    raise ValueError(f"Configuration du sprite sheet '{sheet_name}' doit être un dictionnaire")
                
                required_fields = ["path", "sprite_width", "sprite_height"]
                for field in required_fields:
                    if field not in sheet_data:
                        raise ValueError(f"Champ '{field}' manquant dans [sprite_sheets.{sheet_name}]")
                
                sheet_path = Path(sheet_data["path"])
                if not sheet_path.is_absolute():
                    sheet_path = Path.cwd() / sheet_path
                
                sprite_width = sheet_data["sprite_width"]
                sprite_height = sheet_data["sprite_height"]
                spacing = sheet_data.get("spacing", 0.0)
                
                if sprite_width <= 0 or sprite_height <= 0:
                    raise ValueError(f"sprite_width et sprite_height doivent être positifs pour '{sheet_name}'")
                
                if not isinstance(spacing, (int, float)):
                    raise ValueError(f"spacing dans [sprite_sheets.{sheet_name}] doit être un nombre: {spacing}")
                
                sprite_sheets[sheet_name] = SpriteSheetConfig(
                    name=sheet_name,
                    path=sheet_path,
                    sprite_width=int(sprite_width),
                    sprite_height=int(sprite_height),
                    spacing=float(spacing),
                )
        
        # Support du format rétrocompatible [sprite_sheet] (singulier)
        elif "sprite_sheet" in data:
            sprite_sheet_data = data["sprite_sheet"]
            required_fields = ["path", "sprite_width", "sprite_height"]
            for field in required_fields:
                if field not in sprite_sheet_data:
                    raise ValueError(f"Champ '{field}' manquant dans [sprite_sheet]")
            
            sprite_sheet_path = Path(sprite_sheet_data["path"])
            if not sprite_sheet_path.is_absolute():
                sprite_sheet_path = Path.cwd() / sprite_sheet_path
            
            sprite_width = sprite_sheet_data["sprite_width"]
            sprite_height = sprite_sheet_data["sprite_height"]
            default_spacing = sprite_sheet_data.get("spacing", 0.0)
            
            if sprite_width <= 0 or sprite_height <= 0:
                raise ValueError("sprite_width et sprite_height doivent être positifs")
            
            if not isinstance(default_spacing, (int, float)):
                raise ValueError(f"spacing dans [sprite_sheet] doit être un nombre: {default_spacing}")
            
            # Créer un sprite sheet par défaut nommé "default"
            sprite_sheets["default"] = SpriteSheetConfig(
                name="default",
                path=sprite_sheet_path,
                sprite_width=int(sprite_width),
                sprite_height=int(sprite_height),
                spacing=float(default_spacing),
            )
        else:
            raise ValueError("Section [sprite_sheet] ou [sprite_sheets] manquante dans le fichier de niveau")
        
        # Déterminer le sprite sheet par défaut (le premier ou "default" s'il existe)
        default_sheet_name = "default" if "default" in sprite_sheets else next(iter(sprite_sheets.keys()))

        # Valider et extraire les mappings de lignes (optionnel)
        rows: list[RowMapping] = []
        if "layers" in data:
            layers_data = data["layers"]
            # Support du nouveau format [[layers]] (liste de dictionnaires)
            if isinstance(layers_data, list):
                for layer_data in layers_data:
                    if not isinstance(layer_data, dict):
                        raise ValueError("Chaque entrée de [[layers]] doit être un dictionnaire")
                    
                    # Le champ sheet est optionnel si un seul sprite sheet existe
                    sheet_name = layer_data.get("sheet", default_sheet_name)
                    if sheet_name not in sprite_sheets:
                        raise ValueError(f"Sprite sheet '{sheet_name}' référencé dans [[layers]] n'existe pas")
                    
                    if "row" not in layer_data:
                        raise ValueError("Champ 'row' manquant dans [[layers]]")
                    if "depth" not in layer_data:
                        raise ValueError("Champ 'depth' manquant dans [[layers]]")
                    
                    row = layer_data["row"]
                    depth = layer_data["depth"]
                    sheet_config = sprite_sheets[sheet_name]
                    spacing = layer_data.get("spacing", sheet_config.spacing)
                    # Support de is_infinite (nouveau) avec rétrocompatibilité pour repeat (ancien)
                    is_infinite = layer_data.get("is_infinite")
                    if is_infinite is None:
                        # Rétrocompatibilité : si is_infinite n'est pas présent, utiliser repeat
                        is_infinite = layer_data.get("repeat", True)
                    else:
                        # Si is_infinite est présent, vérifier qu'il n'y a pas aussi repeat (conflit)
                        if "repeat" in layer_data:
                            raise ValueError("Ne peut pas utiliser à la fois 'repeat' et 'is_infinite'. Utilisez uniquement 'is_infinite'.")
                    
                    if not isinstance(row, int):
                        raise ValueError(f"row doit être un entier: {row}")
                    if not isinstance(depth, int):
                        raise ValueError(f"Profondeur invalide: {depth}")
                    if depth < 0 or depth > 3:
                        raise ValueError(f"Profondeur invalide: {depth} (doit être entre 0 et 3)")
                    if not isinstance(spacing, (int, float)):
                        raise ValueError(f"spacing doit être un nombre: {spacing}")
                    if not isinstance(is_infinite, bool):
                        raise ValueError(f"is_infinite doit être un booléen: {is_infinite}")
                    
                    # Charger is_background (optionnel)
                    is_background = layer_data.get("is_background", False)
                    if not isinstance(is_background, bool):
                        raise ValueError(f"is_background doit être un booléen: {is_background}")
                    
                    # Charger is_foreground (optionnel)
                    is_foreground = layer_data.get("is_foreground", False)
                    if not isinstance(is_foreground, bool):
                        raise ValueError(f"is_foreground doit être un booléen: {is_foreground}")
                    
                    # Charger is_climbable (optionnel)
                    is_climbable = layer_data.get("is_climbable", False)
                    if not isinstance(is_climbable, bool):
                        raise ValueError(f"is_climbable doit être un booléen: {is_climbable}")
                    
                    # Charger initial_alpha (optionnel)
                    initial_alpha = layer_data.get("initial_alpha", 255)
                    if not isinstance(initial_alpha, int):
                        raise ValueError(f"initial_alpha doit être un entier pour la ligne {row}: {initial_alpha}")
                    if initial_alpha < 0 or initial_alpha > 255:
                        raise ValueError(f"initial_alpha doit être entre 0 et 255 pour la ligne {row}: {initial_alpha}")
                    
                    # Charger les tags (optionnel)
                    tags = layer_data.get("tags")
                    if tags is not None:
                        if not isinstance(tags, list):
                            raise ValueError(f"tags doit être une liste pour la ligne {row}")
                        if not all(isinstance(tag, str) for tag in tags):
                            raise ValueError(f"Tous les tags doivent être des chaînes de caractères pour la ligne {row}")
                    
                    rows.append(RowMapping(
                        sheet=sheet_name,
                        row=row,
                        depth=depth,
                        spacing=float(spacing),
                        is_infinite=is_infinite,
                        is_background=is_background,
                        is_foreground=is_foreground,
                        is_climbable=is_climbable,
                        initial_alpha=initial_alpha,
                        tags=tags if tags is not None else None,
                    ))
            # Support du format rétrocompatible [layers] (dictionnaire)
            elif isinstance(layers_data, dict):
                for row_str, layer_value in layers_data.items():
                    try:
                        row = int(row_str)
                    except ValueError:
                        raise ValueError(f"Numéro de ligne invalide: {row_str}")

                    # Support du format simplifié (0 = 0) et du format étendu (0 = { depth = 0, spacing = 0.0 })
                    if isinstance(layer_value, int):
                        depth = layer_value
                        sheet_config = sprite_sheets[default_sheet_name]
                        spacing = sheet_config.spacing
                        is_infinite = True
                    elif isinstance(layer_value, dict):
                        if "depth" not in layer_value:
                            raise ValueError(f"Champ 'depth' manquant pour la ligne {row}")
                        depth = layer_value["depth"]
                        sheet_config = sprite_sheets[default_sheet_name]
                        spacing = layer_value.get("spacing", sheet_config.spacing)
                        # Support de is_infinite (nouveau) avec rétrocompatibilité pour repeat (ancien)
                        is_infinite = layer_value.get("is_infinite")
                        if is_infinite is None:
                            # Rétrocompatibilité : si is_infinite n'est pas présent, utiliser repeat
                            is_infinite = layer_value.get("repeat", True)
                        else:
                            # Si is_infinite est présent, vérifier qu'il n'y a pas aussi repeat (conflit)
                            if "repeat" in layer_value:
                                raise ValueError(f"Ne peut pas utiliser à la fois 'repeat' et 'is_infinite' pour la ligne {row}. Utilisez uniquement 'is_infinite'.")
                    else:
                        raise ValueError(f"Format invalide pour la ligne {row}: {layer_value}")

                    if not isinstance(depth, int):
                        raise ValueError(f"Profondeur invalide pour la ligne {row}: {depth}")

                    if depth < 0 or depth > 3:
                        raise ValueError(f"Profondeur invalide: {depth} (doit être entre 0 et 3)")

                    if not isinstance(spacing, (int, float)):
                        raise ValueError(f"spacing doit être un nombre pour la ligne {row}: {spacing}")

                    if not isinstance(is_infinite, bool):
                        raise ValueError(f"is_infinite doit être un booléen pour la ligne {row}: {is_infinite}")

                    # Charger is_background (optionnel)
                    is_background = layer_value.get("is_background", False) if isinstance(layer_value, dict) else False
                    if not isinstance(is_background, bool):
                        raise ValueError(f"is_background doit être un booléen pour la ligne {row}: {is_background}")

                    # Charger is_foreground (optionnel)
                    is_foreground = layer_value.get("is_foreground", False) if isinstance(layer_value, dict) else False
                    if not isinstance(is_foreground, bool):
                        raise ValueError(f"is_foreground doit être un booléen pour la ligne {row}: {is_foreground}")

                    # Charger is_climbable (optionnel)
                    is_climbable = layer_value.get("is_climbable", False) if isinstance(layer_value, dict) else False
                    if not isinstance(is_climbable, bool):
                        raise ValueError(f"is_climbable doit être un booléen pour la ligne {row}: {is_climbable}")

                    # Charger initial_alpha (optionnel)
                    initial_alpha = layer_value.get("initial_alpha", 255) if isinstance(layer_value, dict) else 255
                    if not isinstance(initial_alpha, int):
                        raise ValueError(f"initial_alpha doit être un entier pour la ligne {row}: {initial_alpha}")
                    if initial_alpha < 0 or initial_alpha > 255:
                        raise ValueError(f"initial_alpha doit être entre 0 et 255 pour la ligne {row}: {initial_alpha}")
                    
                    # Charger les tags (optionnel)
                    tags = layer_value.get("tags") if isinstance(layer_value, dict) else None
                    if tags is not None:
                        if not isinstance(tags, list):
                            raise ValueError(f"tags doit être une liste pour la ligne {row}")
                        if not all(isinstance(tag, str) for tag in tags):
                            raise ValueError(f"Tous les tags doivent être des chaînes de caractères pour la ligne {row}")

                    rows.append(RowMapping(
                        sheet=default_sheet_name,
                        row=row,
                        depth=depth,
                        spacing=float(spacing),
                        is_infinite=is_infinite,
                        is_background=is_background,
                        is_foreground=is_foreground,
                        is_climbable=is_climbable,
                        initial_alpha=initial_alpha,
                        tags=tags if tags is not None else None,
                    ))
            else:
                raise ValueError("Section [layers] doit être une liste ou un dictionnaire")

        # Valider et extraire les mappings de sprites individuels (optionnel)
        sprites: list[SpriteMapping] = []
        if "sprites" in data:
            sprites_data = data["sprites"]
            if not isinstance(sprites_data, list):
                raise ValueError("Section [sprites] doit être une liste")

            for sprite_data in sprites_data:
                required_fields = ["row", "col", "depth"]
                for field in required_fields:
                    if field not in sprite_data:
                        raise ValueError(f"Champ '{field}' manquant dans un sprite")

                # Le champ sheet est optionnel si un seul sprite sheet existe
                sheet_name = sprite_data.get("sheet", default_sheet_name)
                if sheet_name not in sprite_sheets:
                    raise ValueError(f"Sprite sheet '{sheet_name}' référencé dans [[sprites]] n'existe pas")
                
                sheet_config = sprite_sheets[sheet_name]

                row = sprite_data["row"]
                col = sprite_data["col"]
                depth = sprite_data["depth"]
                
                # Support de count_x (nouveau) avec rétrocompatibilité pour repeat_count (ancien)
                count_x = sprite_data.get("count_x")
                if count_x is None:
                    # Rétrocompatibilité : si count_x n'est pas présent, utiliser repeat_count
                    count_x = sprite_data.get("repeat_count", 1)
                else:
                    # Si count_x est présent, vérifier qu'il n'y a pas aussi repeat_count (conflit)
                    if "repeat_count" in sprite_data:
                        raise ValueError("Ne peut pas utiliser à la fois 'repeat_count' et 'count_x' dans un sprite. Utilisez uniquement 'count_x'.")
                
                # Support de count_y (optionnel, défaut: 1)
                count_y = sprite_data.get("count_y", 1)
                
                y_offset = sprite_data.get("y_offset", 0.0)
                x_offset = sprite_data.get("x_offset", 0.0)
                # Si spacing n'est pas spécifié, utilise le spacing du sprite sheet
                spacing = sprite_data.get("spacing", sheet_config.spacing)
                
                # Support de spacing_y (optionnel, défaut: 0.0)
                spacing_y = sprite_data.get("spacing_y", 0.0)
                
                # Support de infinite_offset (nouveau) avec rétrocompatibilité pour repeat_x_offset (ancien)
                infinite_offset = sprite_data.get("infinite_offset")
                if infinite_offset is None:
                    # Rétrocompatibilité : si infinite_offset n'est pas présent, utiliser repeat_x_offset
                    infinite_offset = sprite_data.get("repeat_x_offset", 0.0)
                else:
                    # Si infinite_offset est présent, vérifier qu'il n'y a pas aussi repeat_x_offset (conflit)
                    if "repeat_x_offset" in sprite_data:
                        raise ValueError("Ne peut pas utiliser à la fois 'repeat_x_offset' et 'infinite_offset' dans un sprite. Utilisez uniquement 'infinite_offset'.")
                
                # Support de is_infinite (nouveau) avec rétrocompatibilité pour repeat (ancien)
                is_infinite = sprite_data.get("is_infinite")
                if is_infinite is None:
                    # Rétrocompatibilité : si is_infinite n'est pas présent, utiliser repeat
                    is_infinite = sprite_data.get("repeat", True)
                else:
                    # Si is_infinite est présent, vérifier qu'il n'y a pas aussi repeat (conflit)
                    if "repeat" in sprite_data:
                        raise ValueError("Ne peut pas utiliser à la fois 'repeat' et 'is_infinite' dans un sprite. Utilisez uniquement 'is_infinite'.")
                
                # Support du paramètre scale (redimensionnement)
                scale = sprite_data.get("scale", 1.0)

                if not isinstance(row, int) or not isinstance(col, int):
                    raise ValueError(f"row et col doivent être des entiers pour le sprite")

                if not isinstance(depth, int):
                    raise ValueError(f"Profondeur invalide pour le sprite: {depth}")

                if depth < 0 or depth > 3:
                    raise ValueError(f"Profondeur invalide: {depth} (doit être entre 0 et 3)")

                if not isinstance(count_x, int) or count_x < 1:
                    raise ValueError(f"count_x doit être un entier positif: {count_x}")

                if not isinstance(count_y, int) or count_y < 1:
                    raise ValueError(f"count_y doit être un entier positif: {count_y}")

                if not isinstance(y_offset, (int, float)):
                    raise ValueError(f"y_offset doit être un nombre: {y_offset}")

                if not isinstance(x_offset, (int, float)):
                    raise ValueError(f"x_offset doit être un nombre: {x_offset}")

                if not isinstance(spacing, (int, float)):
                    raise ValueError(f"spacing doit être un nombre: {spacing}")

                if not isinstance(spacing_y, (int, float)):
                    raise ValueError(f"spacing_y doit être un nombre: {spacing_y}")

                if not isinstance(infinite_offset, (int, float)):
                    raise ValueError(f"infinite_offset doit être un nombre: {infinite_offset}")

                if not isinstance(is_infinite, bool):
                    raise ValueError(f"is_infinite doit être un booléen: {is_infinite}")
                
                if not isinstance(scale, (int, float)):
                    raise ValueError(f"scale doit être un nombre: {scale}")
                
                if scale <= 0:
                    raise ValueError(f"scale doit être un nombre positif: {scale}")

                # Charger is_background (optionnel)
                is_background = sprite_data.get("is_background", False)
                if not isinstance(is_background, bool):
                    raise ValueError(f"is_background doit être un booléen: {is_background}")

                # Charger is_foreground (optionnel)
                is_foreground = sprite_data.get("is_foreground", False)
                if not isinstance(is_foreground, bool):
                    raise ValueError(f"is_foreground doit être un booléen: {is_foreground}")

                # Charger is_climbable (optionnel)
                is_climbable = sprite_data.get("is_climbable", False)
                if not isinstance(is_climbable, bool):
                    raise ValueError(f"is_climbable doit être un booléen: {is_climbable}")

                # Charger initial_alpha (optionnel)
                initial_alpha = sprite_data.get("initial_alpha", 255)
                if not isinstance(initial_alpha, int):
                    raise ValueError(f"initial_alpha doit être un entier pour le sprite: {initial_alpha}")
                if initial_alpha < 0 or initial_alpha > 255:
                    raise ValueError(f"initial_alpha doit être entre 0 et 255 pour le sprite: {initial_alpha}")

                # Charger les tags (optionnel)
                tags = sprite_data.get("tags")
                if tags is not None:
                    if not isinstance(tags, list):
                        raise ValueError(f"tags doit être une liste pour le sprite (row={row}, col={col})")
                    if not all(isinstance(tag, str) for tag in tags):
                        raise ValueError(f"Tous les tags doivent être des chaînes de caractères pour le sprite (row={row}, col={col})")

                # Charger first_sprite_row et first_sprite_col (optionnel, uniquement si count_x > 3)
                first_sprite_row = sprite_data.get("first_sprite_row")
                first_sprite_col = sprite_data.get("first_sprite_col")
                if first_sprite_row is not None:
                    if not isinstance(first_sprite_row, int):
                        raise ValueError(f"first_sprite_row doit être un entier pour le sprite (row={row}, col={col})")
                    if count_x <= 3:
                        raise ValueError(f"first_sprite_row ne peut être utilisé que si count_x > 3 (count_x={count_x})")
                if first_sprite_col is not None:
                    if not isinstance(first_sprite_col, int):
                        raise ValueError(f"first_sprite_col doit être un entier pour le sprite (row={row}, col={col})")
                    if count_x <= 3:
                        raise ValueError(f"first_sprite_col ne peut être utilisé que si count_x > 3 (count_x={count_x})")

                # Charger last_sprite_row et last_sprite_col (optionnel, uniquement si count_x > 3)
                last_sprite_row = sprite_data.get("last_sprite_row")
                last_sprite_col = sprite_data.get("last_sprite_col")
                if last_sprite_row is not None:
                    if not isinstance(last_sprite_row, int):
                        raise ValueError(f"last_sprite_row doit être un entier pour le sprite (row={row}, col={col})")
                    if count_x <= 3:
                        raise ValueError(f"last_sprite_row ne peut être utilisé que si count_x > 3 (count_x={count_x})")
                if last_sprite_col is not None:
                    if not isinstance(last_sprite_col, int):
                        raise ValueError(f"last_sprite_col doit être un entier pour le sprite (row={row}, col={col})")
                    if count_x <= 3:
                        raise ValueError(f"last_sprite_col ne peut être utilisé que si count_x > 3 (count_x={count_x})")

                sprites.append(
                    SpriteMapping(
                        sheet=sheet_name,
                        row=row,
                        col=col,
                        depth=depth,
                        count_x=count_x,
                        first_sprite_row=first_sprite_row,
                        first_sprite_col=first_sprite_col,
                        last_sprite_row=last_sprite_row,
                        last_sprite_col=last_sprite_col,
                        count_y=count_y,
                        y_offset=float(y_offset),
                        x_offset=float(x_offset),
                        spacing=float(spacing),
                        spacing_y=float(spacing_y),
                        infinite_offset=float(infinite_offset),
                        is_infinite=is_infinite,
                        scale=float(scale),
                        is_background=is_background,
                        is_foreground=is_foreground,
                        is_climbable=is_climbable,
                        initial_alpha=initial_alpha,
                        tags=tags if tags is not None else None,
                    )
                )

        # Vérifier qu'au moins une section est présente
        if not rows and not sprites:
            raise ValueError("Au moins une section [layers] ou [sprites] doit être présente")

        player_level = DEFAULT_PLAYER_LEVEL
        if "player" in data:
            player_section = data["player"]
            if not isinstance(player_section, dict):
                raise ValueError("La section [player] doit être un dictionnaire")

            level_value = player_section.get("level", DEFAULT_PLAYER_LEVEL)
            if not isinstance(level_value, int):
                try:
                    level_value = int(level_value)
                except (TypeError, ValueError) as exc:
                    raise ValueError("La valeur 'level' dans [player] doit être un entier") from exc

            if level_value < MIN_PLAYER_LEVEL or level_value > player_cap:
                raise ValueError(
                    f"Le niveau du joueur doit être compris entre {MIN_PLAYER_LEVEL} et {player_cap} (reçu {level_value})"
                )

            assets_dir = self.assets_dir if self.assets_dir.is_absolute() else (Path.cwd() / self.assets_dir)
            player_assets_dir = assets_dir / "personnage" / str(level_value)
            if not player_assets_dir.exists():
                raise FileNotFoundError(
                    f"Le répertoire d'assets du joueur {player_assets_dir} est introuvable"
                )

            player_level = level_value

        return LevelConfig(
            sprite_sheets=sprite_sheets,
            rows=rows,
            sprites=sprites,
            player_level=player_level,
        )

    def create_parallax_layers(
        self,
        level_config: LevelConfig,
        screen_width: int,
        screen_height: int,
    ) -> tuple[ParallaxSystem, dict[str, list]]:
        """Crée un système de parallaxe à partir d'une configuration de niveau.

        Pour chaque ligne définie dans la config, extrait tous les sprites de la ligne,
        les concatène horizontalement et crée une Layer avec la profondeur associée.

        Pour chaque sprite individuel défini, extrait le sprite spécifique et le répète
        le nombre de fois indiqué pour créer une Layer.

        Crée également un dictionnaire de mapping par tag permettant de récupérer les
        couches associées à un tag donné. Ce mapping est utilisé par le système d'événements
        pour localiser et manipuler les sprites (par exemple, les masquer).

        Args:
            level_config: Configuration du niveau
            screen_width: Largeur de l'écran
            screen_height: Hauteur de l'écran

        Returns:
            Tuple contenant :
            - Système de parallaxe configuré avec les couches du niveau
            - Dictionnaire de mapping par tag : {tag: [liste des layers avec ce tag]}

        Raises:
            FileNotFoundError: Si un sprite sheet n'existe pas
            ValueError: Si les coordonnées de ligne sont invalides
        """
        from ..rendering.layer import Layer
        from ..rendering.parallax import ParallaxSystem

        # Utiliser le cache global si disponible, sinon créer un cache local
        from ..assets.preloader import (
            _global_level_sprite_sheet_cache,
            _global_level_scaled_sprite_cache,
        )
        
        sprite_sheet_cache: dict[str, pygame.Surface] = {}
        sprite_sheet_info: dict[str, tuple[int, int]] = {}  # (num_rows, num_cols)
        
        for sheet_name, sheet_config in level_config.sprite_sheets.items():
            # Vérifier d'abord le cache global
            if sheet_name in _global_level_sprite_sheet_cache:
                sprite_sheet = _global_level_sprite_sheet_cache[sheet_name]
            else:
                # Charger depuis le disque si pas en cache
                if not sheet_config.path.exists():
                    raise FileNotFoundError(
                        f"Sprite sheet '{sheet_name}' introuvable: {sheet_config.path}"
                    )
                
                sprite_sheet = pygame.image.load(str(sheet_config.path)).convert_alpha()
            
            sheet_width = sprite_sheet.get_width()
            sheet_height = sprite_sheet.get_height()
            
            num_rows = sheet_height // sheet_config.sprite_height
            num_cols = sheet_width // sheet_config.sprite_width
            
            sprite_sheet_cache[sheet_name] = sprite_sheet
            sprite_sheet_info[sheet_name] = (num_rows, num_cols)

        # Créer le système de parallaxe
        parallax_system = ParallaxSystem(screen_width, screen_height)

        # Facteurs de conversion du repère de conception (1920x1080) vers la surface de rendu interne
        scale_x, scale_y = compute_design_scale((screen_width, screen_height))

        # Dictionnaire de mapping par tag : {tag: [liste des layers avec ce tag]}
        layers_by_tag: dict[str, list] = {}

        # Cache pour les sprites redimensionnés (évite les redimensionnements multiples)
        # Clé : (sheet_name, row, col, scale) -> sprite redimensionné
        scaled_sprite_cache: dict[tuple[str, int, int, float], pygame.Surface] = {}

        layer_index = 0

        # Pour chaque ligne définie dans la config
        for row_mapping in level_config.rows:
            sheet_name = row_mapping.sheet
            row = row_mapping.row
            depth = row_mapping.depth
            spacing = row_mapping.spacing * scale_x
            is_infinite = row_mapping.is_infinite

            # Récupérer le sprite sheet et ses informations
            if sheet_name not in sprite_sheet_cache:
                raise ValueError(f"Sprite sheet '{sheet_name}' non trouvé dans le cache")
            
            sprite_sheet = sprite_sheet_cache[sheet_name]
            sheet_config = level_config.sprite_sheets[sheet_name]
            num_rows, num_cols = sprite_sheet_info[sheet_name]

            # Valider que la ligne existe dans le sprite sheet
            if row < 0 or row >= num_rows:
                raise ValueError(
                    f"Ligne {row} invalide dans sprite sheet '{sheet_name}' "
                    f"(sprite sheet a {num_rows} lignes, index 0-{num_rows - 1})"
                )

            # Extraire tous les sprites de la ligne et les concaténer
            row_sprites: list[pygame.Surface] = []
            for col in range(num_cols):
                x = col * sheet_config.sprite_width
                y = row * sheet_config.sprite_height

                # Extraire le sprite
                rect = pygame.Rect(x, y, sheet_config.sprite_width, sheet_config.sprite_height)
                sprite = pygame.Surface(
                    (sheet_config.sprite_width, sheet_config.sprite_height), pygame.SRCALPHA
                )
                sprite.blit(sprite_sheet, (0, 0), rect)
                row_sprites.append(sprite)

            # Calculer la largeur de la couche en tenant compte du spacing
            # Si spacing est négatif, les sprites se chevauchent
            if num_cols > 0:
                layer_width = int(
                    num_cols * sheet_config.sprite_width + (num_cols - 1) * spacing
                )
            else:
                layer_width = 0

            layer_surface = pygame.Surface((layer_width, sheet_config.sprite_height), pygame.SRCALPHA)

            # Concaténer tous les sprites horizontalement en appliquant le spacing
            x_pos = 0.0
            for sprite in row_sprites:
                layer_surface.blit(sprite, (int(x_pos), 0))
                x_pos += sheet_config.sprite_width + spacing

            # Créer la couche avec la vitesse de défilement par défaut
            scroll_speed = DEFAULT_SCROLL_SPEEDS[depth]

            # Mapper is_infinite vers repeat pour la classe Layer
            # Passer is_background, is_foreground et is_climbable à la Layer
            # Note: is_background et is_foreground sont mutuellement exclusifs, is_background a la priorité
            layer = Layer(
                name=f"layer_depth_{depth}_row_{row}_{layer_index}",
                depth=depth,
                scroll_speed=scroll_speed,
                surface=layer_surface,
                repeat=is_infinite,  # is_infinite est mappé vers repeat
                is_background=row_mapping.is_background,
                is_foreground=row_mapping.is_foreground if not row_mapping.is_background else False,
                is_climbable=row_mapping.is_climbable,
            )
            # Définir l'opacité initiale
            layer.alpha = row_mapping.initial_alpha
            # Si initial_alpha = 0, désactiver les collisions par défaut
            if row_mapping.initial_alpha == 0:
                layer.is_hidden = True

            parallax_system.add_layer(layer)
            
            # Ajouter la layer au mapping par tag si des tags sont définis
            if row_mapping.tags:
                for tag in row_mapping.tags:
                    if tag not in layers_by_tag:
                        layers_by_tag[tag] = []
                    layers_by_tag[tag].append(layer)
            
            layer_index += 1

        # Fonction helper pour déterminer le sprite à utiliser selon l'index horizontal
        def get_sprite_coords(sprite_mapping: SpriteMapping, index: int) -> tuple[int, int]:
            """Détermine les coordonnées (row, col) du sprite à utiliser selon l'index horizontal.
            
            Args:
                sprite_mapping: Configuration du sprite
                index: Index horizontal (0 = premier, count_x-1 = dernier)
            
            Returns:
                Tuple (row, col) des coordonnées du sprite à utiliser
            """
            if sprite_mapping.count_x <= 3:
                # Si count_x <= 3, toujours utiliser le sprite de base
                return (sprite_mapping.row, sprite_mapping.col)
            
            # Si count_x > 3, vérifier si on est au premier ou dernier sprite
            if index == 0:
                # Premier sprite
                if sprite_mapping.first_sprite_row is not None and sprite_mapping.first_sprite_col is not None:
                    return (sprite_mapping.first_sprite_row, sprite_mapping.first_sprite_col)
                else:
                    return (sprite_mapping.row, sprite_mapping.col)
            elif index == sprite_mapping.count_x - 1:
                # Dernier sprite
                if sprite_mapping.last_sprite_row is not None and sprite_mapping.last_sprite_col is not None:
                    return (sprite_mapping.last_sprite_row, sprite_mapping.last_sprite_col)
                else:
                    return (sprite_mapping.row, sprite_mapping.col)
            else:
                # Sprites intermédiaires : toujours utiliser le sprite de base
                return (sprite_mapping.row, sprite_mapping.col)

        # Pour chaque sprite individuel défini dans la config
        for sprite_mapping in level_config.sprites:
            sheet_name = sprite_mapping.sheet
            row = sprite_mapping.row
            col = sprite_mapping.col
            depth = sprite_mapping.depth
            count_x = sprite_mapping.count_x
            is_infinite = sprite_mapping.is_infinite
            # Note: infinite_offset sera ajusté par le scale plus tard dans le code

            # Récupérer le sprite sheet et ses informations
            if sheet_name not in sprite_sheet_cache:
                raise ValueError(f"Sprite sheet '{sheet_name}' non trouvé dans le cache")
            
            sprite_sheet = sprite_sheet_cache[sheet_name]
            sheet_config = level_config.sprite_sheets[sheet_name]
            num_rows, num_cols = sprite_sheet_info[sheet_name]

            # Valider que les coordonnées de base sont valides
            if row < 0 or row >= num_rows:
                raise ValueError(
                    f"Ligne {row} invalide dans sprite sheet '{sheet_name}' "
                    f"(sprite sheet a {num_rows} lignes, index 0-{num_rows - 1})"
                )
            if col < 0 or col >= num_cols:
                raise ValueError(
                    f"Colonne {col} invalide dans sprite sheet '{sheet_name}' "
                    f"(sprite sheet a {num_cols} colonnes, index 0-{num_cols - 1})"
                )

            # Valider les coordonnées des sprites personnalisés si définis
            if sprite_mapping.first_sprite_row is not None:
                if sprite_mapping.first_sprite_row < 0 or sprite_mapping.first_sprite_row >= num_rows:
                    raise ValueError(
                        f"first_sprite_row {sprite_mapping.first_sprite_row} invalide dans sprite sheet '{sheet_name}' "
                        f"(sprite sheet a {num_rows} lignes, index 0-{num_rows - 1})"
                    )
            if sprite_mapping.first_sprite_col is not None:
                if sprite_mapping.first_sprite_col < 0 or sprite_mapping.first_sprite_col >= num_cols:
                    raise ValueError(
                        f"first_sprite_col {sprite_mapping.first_sprite_col} invalide dans sprite sheet '{sheet_name}' "
                        f"(sprite sheet a {num_cols} colonnes, index 0-{num_cols - 1})"
                    )
            if sprite_mapping.last_sprite_row is not None:
                if sprite_mapping.last_sprite_row < 0 or sprite_mapping.last_sprite_row >= num_rows:
                    raise ValueError(
                        f"last_sprite_row {sprite_mapping.last_sprite_row} invalide dans sprite sheet '{sheet_name}' "
                        f"(sprite sheet a {num_rows} lignes, index 0-{num_rows - 1})"
                    )
            if sprite_mapping.last_sprite_col is not None:
                if sprite_mapping.last_sprite_col < 0 or sprite_mapping.last_sprite_col >= num_cols:
                    raise ValueError(
                        f"last_sprite_col {sprite_mapping.last_sprite_col} invalide dans sprite sheet '{sheet_name}' "
                        f"(sprite sheet a {num_cols} colonnes, index 0-{num_cols - 1})"
                    )

            # Appliquer le redimensionnement si scale != 1.0
            scale = sprite_mapping.scale
            original_width = sheet_config.sprite_width
            original_height = sheet_config.sprite_height
            
            # Fonction helper pour extraire et mettre en cache un sprite
            def get_scaled_sprite(sprite_row: int, sprite_col: int) -> tuple[pygame.Surface, int, int]:
                """Extrait et redimensionne un sprite, en utilisant le cache si disponible.
                
                Returns:
                    Tuple (sprite, new_width, new_height)
                """
                cache_key = (sheet_name, sprite_row, sprite_col, scale)
                
                # Vérifier d'abord le cache global (préchargement)
                if cache_key in _global_level_scaled_sprite_cache:
                    sprite = _global_level_scaled_sprite_cache[cache_key]
                    return (sprite, sprite.get_width(), sprite.get_height())
                
                # Sinon, vérifier le cache local
                if cache_key in scaled_sprite_cache:
                    sprite = scaled_sprite_cache[cache_key]
                    return (sprite, sprite.get_width(), sprite.get_height())
                
                # Extraire le sprite
                x = sprite_col * sheet_config.sprite_width
                y = sprite_row * sheet_config.sprite_height
                rect = pygame.Rect(x, y, sheet_config.sprite_width, sheet_config.sprite_height)
                sprite = pygame.Surface(
                    (sheet_config.sprite_width, sheet_config.sprite_height), pygame.SRCALPHA
                )
                sprite.blit(sprite_sheet, (0, 0), rect)
                
                # Appliquer le redimensionnement
                # IMPORTANT : Le scale du sprite doit être appliqué DANS le repère de conception (1920x1080),
                # puis on convertit le résultat vers la résolution interne (1280x720).
                # Étape 1 : Appliquer le scale dans le repère 1920x1080
                scaled_width_in_design = original_width * scale
                scaled_height_in_design = original_height * scale
                # Étape 2 : Convertir vers la résolution interne 1280x720
                new_width = int(scaled_width_in_design * scale_x)
                new_height = int(scaled_height_in_design * scale_y)
                
                # Redimensionner le sprite seulement si nécessaire
                if new_width != original_width or new_height != original_height:
                    # Utiliser smoothscale pour une meilleure qualité (redimensionnement fait une seule fois au chargement)
                    sprite = pygame.transform.smoothscale(sprite, (new_width, new_height))
                # Convertir pour optimiser le rendu
                sprite = sprite.convert_alpha()
                
                # Mettre en cache le sprite redimensionné
                scaled_sprite_cache[cache_key] = sprite
                
                return (sprite, new_width, new_height)
            
            # Extraire le sprite de base pour obtenir les dimensions (tous les sprites ont la même taille)
            base_sprite, new_width, new_height = get_scaled_sprite(row, col)
            sprite_width_used = new_width
            sprite_height_used = new_height

            # Calculer la position verticale finale.
            # Les fichiers de niveau continuent d'exprimer y_offset comme la position du haut du sprite.
            # IMPORTANT : Le scale du sprite doit être appliqué DANS le repère de conception (1920x1080),
            # puis on convertit le résultat vers la résolution interne (1280x720).
            
            # Étape 1 : Appliquer le scale du sprite dans le repère de conception (1920x1080)
            scaled_y_offset = sprite_mapping.y_offset
            scaled_x_offset = sprite_mapping.x_offset
            scaled_spacing = sprite_mapping.spacing * scale  # Scale appliqué dans le repère 1920x1080
            scaled_spacing_y = sprite_mapping.spacing_y * scale  # Scale appliqué dans le repère 1920x1080
            scaled_infinite_offset = sprite_mapping.infinite_offset * scale  # Scale appliqué dans le repère 1920x1080
            
            # Calculer la hauteur du sprite après application du scale (dans le repère 1920x1080)
            scaled_sprite_height = original_height * scale if scale != 1.0 else original_height
            
            # Étape 2 : Convertir les valeurs du repère de conception (1920x1080) vers la résolution interne (1280x720)
            y_offset_converted = scaled_y_offset * scale_y
            x_offset = scaled_x_offset * scale_x
            spacing = scaled_spacing * scale_x
            spacing_y = scaled_spacing_y * scale_y
            infinite_offset = scaled_infinite_offset * scale_x
            
            # Calculer la position verticale finale en tenant compte du scale
            # Le y_offset représente la position du haut du sprite le plus bas dans le repère 1920x1080
            # Pour count_y > 1, on veut que y_offset représente toujours la position du haut
            # Pour count_y = 1, on peut ajuster pour conserver la position du bas (rétrocompatibilité)
            if scale != 1.0 and sprite_mapping.count_y == 1:
                # Rétrocompatibilité : pour count_y = 1, ajuster pour conserver la position du bas
                # Dans le repère 1920x1080 : bas original = y_offset + original_height
                # Après scale : nouveau haut = y_offset + original_height - (original_height * scale)
                scaled_y_offset_in_design = sprite_mapping.y_offset + original_height * (1.0 - scale)
                # Convertir vers 1280x720
                sprite_top = scaled_y_offset_in_design * scale_y
            else:
                # Pour count_y > 1 ou scale = 1.0, y_offset représente la position du haut
                sprite_top = y_offset_converted
            sprite_top_int = int(sprite_top)
            
            # Récupérer count_y depuis sprite_mapping
            count_y = sprite_mapping.count_y

            if is_infinite:
                # Si is_infinite = true : Créer la couche de base avec count_x sprites
                # Le infinite_offset sera géré par le système de parallaxe lors du rendu
                # Calculer la boîte englobante réelle (pas de pré-remplissage de vide)
                start_x = x_offset
                end_x = (
                    x_offset + (count_x - 1) * (sprite_width_used + spacing) + sprite_width_used
                    if count_x > 0
                    else x_offset
                )
                min_x = start_x
                max_x = end_x
                layer_width = int(max_x - min_x) if count_x > 0 else sprite_width_used
                layer_surface = pygame.Surface((layer_width, screen_height), pygame.SRCALPHA)

                # Répéter horizontalement et verticalement
                for i in range(count_x):
                    # Déterminer le sprite à utiliser selon l'index
                    sprite_row, sprite_col = get_sprite_coords(sprite_mapping, i)
                    sprite, _, _ = get_scaled_sprite(sprite_row, sprite_col)
                    
                    for j in range(count_y):
                        # Position horizontale : x_offset + i * (sprite_width + spacing)
                        x_pos = x_offset + i * (sprite_width_used + spacing)
                        x_pos_adjusted = x_pos - min_x
                        
                        # Position verticale : y_offset_final - j * (hauteur_effective + spacing_y_final)
                        # j=0 est le sprite le plus bas, j=count_y-1 est le sprite le plus haut
                        y_pos = sprite_top_int - j * (sprite_height_used + spacing_y)
                        
                        layer_surface.blit(sprite, (int(x_pos_adjusted), int(y_pos)))
            else:
                # Si is_infinite = false : Répéter le sprite count_x fois avec spacing
                # infinite_offset est ignoré dans ce cas
                # Calculer la position de départ (avec x_offset)
                start_x = x_offset

                # Calculer la position de fin
                # Note: spacing, infinite_offset et x_offset ont été convertis dans le repère de rendu
                if count_x > 0:
                    # Position du dernier sprite : x_offset + (count_x - 1) * (sprite_width + spacing) + sprite_width
                    last_sprite_x = x_offset + (count_x - 1) * (sprite_width_used + spacing)
                    end_x = last_sprite_x + sprite_width_used
                else:
                    end_x = x_offset

                min_x = start_x
                max_x = end_x
                layer_width = int(max_x - min_x) if count_x > 0 else sprite_width_used

                # Calculer une boîte englobante serrée pour éviter que la rotation ne pivote au centre de l'écran
                y_positions = [
                    sprite_top_int - j * (sprite_height_used + spacing_y) for j in range(count_y)
                ] if count_y > 0 else [sprite_top_int]
                min_y = min(y_positions)
                max_y = max(y_positions) + sprite_height_used
                layer_height = int(max(1, max_y - min_y))

                layer_surface = pygame.Surface((layer_width, layer_height), pygame.SRCALPHA)

                # Répéter horizontalement et verticalement
                for i in range(count_x):
                    # Déterminer le sprite à utiliser selon l'index
                    sprite_row, sprite_col = get_sprite_coords(sprite_mapping, i)
                    sprite, _, _ = get_scaled_sprite(sprite_row, sprite_col)
                    
                    for j in range(count_y):
                        # Position horizontale : x_offset + i * (sprite_width + spacing)
                        x_pos = x_offset + i * (sprite_width_used + spacing)
                        x_pos_adjusted = x_pos - min_x
                        
                        # Position verticale : y_offset_final - j * (hauteur_effective + spacing_y_final)
                        # j=0 est le sprite le plus bas, j=count_y-1 est le sprite le plus haut
                        y_pos = sprite_top_int - j * (sprite_height_used + spacing_y)
                        
                        # Décaler pour dessiner dans la surface serrée
                        layer_surface.blit(sprite, (int(x_pos_adjusted), int(y_pos - min_y)))

            # Créer la couche avec la vitesse de défilement par défaut
            scroll_speed = DEFAULT_SCROLL_SPEEDS[depth]

            # Mapper is_infinite vers repeat pour la classe Layer
            # Passer infinite_offset, is_background, is_foreground et is_climbable à la Layer pour qu'elle puisse les utiliser lors du rendu
            # Note: is_background et is_foreground sont mutuellement exclusifs, is_background a la priorité
            layer = Layer(
                name=f"layer_depth_{depth}_sprite_{row}_{col}_{layer_index}",
                depth=depth,
                scroll_speed=scroll_speed,
                surface=layer_surface,
                repeat=is_infinite,  # is_infinite est mappé vers repeat
                world_x_offset=min_x,  # Stocker le min_x pour positionner la couche sans surface vide
                infinite_offset=infinite_offset if is_infinite else 0.0,  # Passer infinite_offset uniquement si is_infinite
                is_background=sprite_mapping.is_background,
                is_foreground=sprite_mapping.is_foreground if not sprite_mapping.is_background else False,
                is_climbable=sprite_mapping.is_climbable,
            )
            # Stocker l'offset vertical réel pour que la rotation se fasse autour du sprite
            if not is_infinite:
                layer.world_y_offset = min_y
            # Définir l'opacité initiale
            layer.alpha = sprite_mapping.initial_alpha
            # Si initial_alpha = 0, désactiver les collisions par défaut
            if sprite_mapping.initial_alpha == 0:
                layer.is_hidden = True

            parallax_system.add_layer(layer)
            
            # Ajouter la layer au mapping par tag si des tags sont définis
            if sprite_mapping.tags:
                for tag in sprite_mapping.tags:
                    if tag not in layers_by_tag:
                        layers_by_tag[tag] = []
                    layers_by_tag[tag].append(layer)
            
            layer_index += 1

        return parallax_system, layers_by_tag

