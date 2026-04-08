"""Module de chargement des caractéristiques du personnage."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

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

from .config import PlayerStatsConfig, StatDefinition

logger = logging.getLogger(__name__)


def _parse_presentation_string_list(
    raw: object, label: str, config_path: Path
) -> List[str]:
    """Valide une liste de chaînes non vides pour [presentation].*."""
    if not isinstance(raw, list):
        raise ValueError(
            f"{label} dans {config_path} doit être une liste de chaînes (tableau TOML)"
        )
    if len(raw) == 0:
        raise ValueError(f"{label} dans {config_path} ne peut pas être une liste vide")
    out: List[str] = []
    for i, item in enumerate(raw):
        if not isinstance(item, str):
            raise ValueError(
                f"{label}[{i}] dans {config_path} doit être une chaîne de caractères"
            )
        stripped = item.strip()
        if not stripped:
            raise ValueError(
                f"{label}[{i}] dans {config_path} ne peut pas être vide "
                "(ou uniquement des espaces)"
            )
        out.append(stripped)
    return out


def _load_presentation_lists(data: dict, config_path: Path) -> tuple[List[str], List[str], List[str]]:
    """Lit et valide [presentation] (origins, class_role, traits)."""
    if "presentation" not in data:
        raise ValueError(
            f"Section [presentation] manquante dans {config_path} "
            "(obligatoire : origins, class_role, traits — listes de chaînes non vides)"
        )
    pres = data["presentation"]
    if not isinstance(pres, dict):
        raise ValueError(
            f"La clé 'presentation' dans {config_path} doit être une table TOML [presentation]"
        )
    missing = [k for k in ("origins", "class_role", "traits") if k not in pres]
    if missing:
        raise ValueError(
            f"Clés manquantes dans [presentation] de {config_path}: {', '.join(missing)} "
            "(obligatoires : origins, class_role, traits)"
        )
    origins = _parse_presentation_string_list(
        pres["origins"], "presentation.origins", config_path
    )
    class_role = _parse_presentation_string_list(
        pres["class_role"], "presentation.class_role", config_path
    )
    traits = _parse_presentation_string_list(
        pres["traits"], "presentation.traits", config_path
    )
    return origins, class_role, traits


class PlayerStatsLoader:
    """Chargeur de fichier de caractéristiques du personnage."""

    def __init__(self, config_path: Path) -> None:
        """Initialise le chargeur de caractéristiques.

        Args:
            config_path: Chemin vers le fichier player_stats.toml
        """
        self.config_path = Path(config_path)

    def load_stats(self) -> PlayerStatsConfig:
        """Charge le fichier de caractéristiques.

        Returns:
            Configuration des caractéristiques chargée

        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            ValueError: Si le format du fichier est invalide
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Fichier de caractéristiques introuvable: {self.config_path}")

        try:
            with open(self.config_path, "rb") as f:
                data = tomli.load(f)
        except Exception as e:
            raise ValueError(f"Erreur lors du parsing du fichier TOML: {e}") from e

        max_level_raw = data.get("max_level", 5)
        if not isinstance(max_level_raw, int):
            try:
                max_level = int(max_level_raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "La clé racine 'max_level' doit être un entier >= 1"
                ) from exc
        else:
            max_level = max_level_raw
        if max_level < 1:
            raise ValueError(f"Valeur invalide pour 'max_level': {max_level} (doit être >= 1)")

        dj_raw = data.get("double_jump_unlock_level", 3)
        if not isinstance(dj_raw, int):
            try:
                double_jump_unlock_level = int(dj_raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "La clé racine 'double_jump_unlock_level' doit être un entier"
                ) from exc
        else:
            double_jump_unlock_level = dj_raw
        if double_jump_unlock_level < 1 or double_jump_unlock_level > max_level:
            raise ValueError(
                f"Valeur invalide pour 'double_jump_unlock_level': {double_jump_unlock_level} "
                f"(doit être entre 1 et {max_level})"
            )

        if "display_name" not in data:
            raise ValueError(
                f"Clé racine 'display_name' manquante dans {self.config_path} "
                "(obligatoire : nom affiché du personnage, chaîne non vide)"
            )
        display_name_raw = data["display_name"]
        if not isinstance(display_name_raw, str):
            raise ValueError(
                f"La clé racine 'display_name' doit être une chaîne de caractères dans {self.config_path}"
            )
        display_name = display_name_raw.strip()
        if not display_name:
            raise ValueError(
                f"La clé racine 'display_name' ne peut pas être vide dans {self.config_path}"
            )

        presentation_origins, presentation_class_role, presentation_traits = (
            _load_presentation_lists(data, self.config_path)
        )

        # Extraire les sections [stats.*]
        stats: Dict[str, StatDefinition] = {}

        if "stats" not in data:
            raise ValueError("Section [stats] introuvable dans le fichier de caractéristiques")

        stats_data = data["stats"]
        if not isinstance(stats_data, dict):
            raise ValueError("Section [stats] doit être un dictionnaire")

        for stat_identifier, stat_data in stats_data.items():
            if not isinstance(stat_data, dict):
                raise ValueError(
                    f"Configuration de la statistique '{stat_identifier}' doit être un dictionnaire"
                )

            # Vérifier les champs obligatoires
            if "name" not in stat_data:
                raise ValueError(f"Champ 'name' manquant dans [stats.{stat_identifier}]")

            name = stat_data["name"]
            description = stat_data.get("description")

            # Extraire les valeurs pour chaque niveau (1 à max_level)
            values: Dict[int, float] = {}
            for level in range(1, max_level + 1):
                level_key = f"level_{level}"
                if level_key not in stat_data:
                    raise ValueError(
                        f"Champ '{level_key}' manquant dans [stats.{stat_identifier}]"
                    )

                value = stat_data[level_key]
                if not isinstance(value, (int, float)):
                    raise ValueError(
                        f"Valeur de '{level_key}' dans [stats.{stat_identifier}] doit être un nombre"
                    )

                # Valider que la valeur est positive
                if value < 0:
                    raise ValueError(
                        f"Valeur invalide pour '{level_key}' dans [stats.{stat_identifier}]: "
                        f"{value} (doit être >= 0)"
                    )

                values[level] = float(value)

            # Extraire les tooltips pour chaque niveau (1 à max_level) - optionnels
            tooltips: Dict[int, str] = {}
            for level in range(1, max_level + 1):
                tooltip_key = f"tooltip_level_{level}"
                if tooltip_key in stat_data:
                    tooltip_value = stat_data[tooltip_key]
                    if not isinstance(tooltip_value, str):
                        raise ValueError(
                            f"Valeur de '{tooltip_key}' dans [stats.{stat_identifier}] doit être une chaîne de caractères"
                        )
                    tooltips[level] = tooltip_value

            # Extraire max_value (optionnel)
            max_value = None
            if "max_value" in stat_data:
                max_value_raw = stat_data["max_value"]
                if not isinstance(max_value_raw, (int, float)):
                    raise ValueError(
                        f"Valeur de 'max_value' dans [stats.{stat_identifier}] doit être un nombre"
                    )
                max_value = float(max_value_raw)

            stats[stat_identifier] = StatDefinition(
                identifier=stat_identifier,
                name=name,
                description=description,
                tooltips=tooltips,
                values=values,
                max_value=max_value,
            )

        # Extraire la section [level_up_messages] (optionnelle)
        level_up_messages: Dict[int, str] = {}
        if "level_up_messages" in data:
            level_up_messages_data = data["level_up_messages"]
            if not isinstance(level_up_messages_data, dict):
                raise ValueError("Section [level_up_messages] doit être un dictionnaire")
            
            for level_key, message in level_up_messages_data.items():
                # Valider que la clé est de la forme "level_X" où X est 2-5
                if not level_key.startswith("level_"):
                    logger.warning(f"Clé invalide dans [level_up_messages]: '{level_key}' (ignorée)")
                    continue
                
                try:
                    level = int(level_key.split("_")[1])
                    if level < 2 or level > max_level:
                        logger.warning(
                            f"Niveau invalide dans [level_up_messages]: '{level_key}' "
                            f"(doit être entre 2 et {max_level}, ignorée)"
                        )
                        continue
                except (ValueError, IndexError):
                    logger.warning(f"Format de clé invalide dans [level_up_messages]: '{level_key}' (ignorée)")
                    continue
                
                if not isinstance(message, str):
                    raise ValueError(
                        f"Valeur de '{level_key}' dans [level_up_messages] doit être une chaîne de caractères"
                    )
                
                level_up_messages[level] = message

        config = PlayerStatsConfig(
            stats=stats,
            display_name=display_name,
            presentation_origins=presentation_origins,
            presentation_class_role=presentation_class_role,
            presentation_traits=presentation_traits,
            level_up_messages=level_up_messages,
            max_level=max_level,
            double_jump_unlock_level=double_jump_unlock_level,
        )
        self.validate_stats(config)
        return config

    def validate_stats(self, config: PlayerStatsConfig) -> None:
        """Valide la configuration des caractéristiques.

        Args:
            config: Configuration à valider

        Raises:
            ValueError: Si la configuration est invalide
        """
        if not (1 <= config.double_jump_unlock_level <= config.max_level):
            raise ValueError(
                f"double_jump_unlock_level invalide: {config.double_jump_unlock_level} "
                f"(doit être entre 1 et {config.max_level})"
            )

        if not (config.display_name and str(config.display_name).strip()):
            raise ValueError("display_name doit être une chaîne non vide")

        for label, lst in (
            ("presentation_origins", config.presentation_origins),
            ("presentation_class_role", config.presentation_class_role),
            ("presentation_traits", config.presentation_traits),
        ):
            if not lst:
                raise ValueError(f"{label} ne peut pas être vide")
            for i, line in enumerate(lst):
                if not str(line).strip():
                    raise ValueError(f"{label}[{i}] ne peut pas être vide")

        for stat_identifier, stat_def in config.stats.items():
            # Vérifier que tous les niveaux sont présents
            for level in range(1, config.max_level + 1):
                if level not in stat_def.values:
                    raise ValueError(
                        f"Valeur manquante pour le niveau {level} dans la statistique '{stat_identifier}'"
                    )

                # Vérifier que les valeurs sont positives
                if stat_def.values[level] < 0:
                    raise ValueError(
                        f"Valeur invalide pour le niveau {level} dans la statistique '{stat_identifier}': "
                        f"{stat_def.values[level]} (doit être >= 0)"
                    )

            # Vérifier max_value si défini
            if stat_def.max_value is not None:
                # Vérifier que max_value est positif
                if stat_def.max_value < 0:
                    raise ValueError(
                        f"Valeur invalide pour 'max_value' dans la statistique '{stat_identifier}': "
                        f"{stat_def.max_value} (doit être >= 0)"
                    )
                # Vérifier que max_value est >= toutes les valeurs level_1 à level_{max_level}
                max_level_value = max(stat_def.values.values())
                if stat_def.max_value < max_level_value:
                    raise ValueError(
                        f"Valeur invalide pour 'max_value' dans la statistique '{stat_identifier}': "
                        f"{stat_def.max_value} (doit être >= toutes les valeurs de niveau, "
                        f"valeur maximale de niveau est {max_level_value})"
                    )

