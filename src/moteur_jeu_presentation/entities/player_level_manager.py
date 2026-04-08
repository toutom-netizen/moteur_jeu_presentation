"""Gestionnaire de niveaux pour les assets du personnage principal."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional

if TYPE_CHECKING:
    from ..stats.config import PlayerStatsConfig

MIN_PLAYER_LEVEL = 1
# Borne supérieure par défaut lorsque les stats (player_stats.toml) ne sont pas chargées
MAX_PLAYER_LEVEL = 5
DEFAULT_PLAYER_LEVEL = 1


class MissingPlayerAssetError(FileNotFoundError):
    """Exception levée lorsqu'un asset est manquant pour un niveau donné."""


@dataclass
class PlayerLevelManager:
    """Gestionnaire des assets liés au niveau du personnage."""

    assets_root: Path
    _level: int = DEFAULT_PLAYER_LEVEL
    stats_config: Optional["PlayerStatsConfig"] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.assets_root.is_absolute():
            self.assets_root = self.assets_root.resolve()
        self.set_level(self._level)

    @property
    def level(self) -> int:
        """Retourne le niveau courant."""

        return self._level

    @property
    def max_player_level(self) -> int:
        """Borne supérieure du niveau (depuis player_stats.toml ou MAX_PLAYER_LEVEL)."""
        if self.stats_config is not None:
            return self.stats_config.max_level
        return MAX_PLAYER_LEVEL

    def set_level(self, level: int) -> None:
        """Modifie le niveau du personnage après validation."""

        cap = self.max_player_level
        if level < MIN_PLAYER_LEVEL or level > cap:
            raise ValueError(
                f"Player level must be between {MIN_PLAYER_LEVEL} and {cap} (got {level})"
            )

        level_dir = self.assets_root / str(level)
        if not level_dir.exists():
            raise MissingPlayerAssetError(
                f"Missing directory {level_dir} for player assets"
            )

        self._level = level

    def get_asset_path(self, filename: str, *, must_exist: bool = True) -> Path:
        """Retourne le chemin complet d'un asset pour le niveau courant."""

        asset_path = self.assets_root / str(self._level) / filename
        if must_exist and not asset_path.exists():
            raise MissingPlayerAssetError(
                f"Missing asset '{filename}' for player level {self._level}"
            )
        return asset_path

    def list_available_assets(self, level: int | None = None) -> List[str]:
        """Liste les assets disponibles pour un niveau donné."""

        target_level = level if level is not None else self._level
        level_dir = self.assets_root / str(target_level)
        if not level_dir.exists():
            return []
        return sorted(item.name for item in level_dir.iterdir() if item.is_file())

    def ensure_assets(self, filenames: Iterable[str]) -> None:
        """Vérifie que les assets listés sont disponibles pour le niveau courant."""

        missing = []
        for name in filenames:
            path = self.get_asset_path(name, must_exist=False)
            if not path.exists():
                missing.append(name)

        if missing:
            raise MissingPlayerAssetError(
                f"Missing assets {missing} for player level {self._level}"
            )

    def get_stat_value(self, stat_identifier: str) -> float:
        """Récupère la valeur d'une caractéristique pour le niveau actuel.

        Args:
            stat_identifier: Identifiant de la caractéristique (ex: "force")

        Returns:
            Valeur de la caractéristique pour le niveau actuel

        Raises:
            KeyError: Si la caractéristique n'existe pas ou si stats_config n'est pas défini
        """
        if self.stats_config is None:
            raise KeyError(
                f"Stats config non disponible. Impossible de récupérer la statistique '{stat_identifier}'"
            )
        return self.stats_config.get_stat_value(stat_identifier, self._level)

    def get_stat_max_value(self, stat_identifier: str) -> float:
        """Récupère la valeur maximale d'une caractéristique.

        Args:
            stat_identifier: Identifiant de la caractéristique (ex: "force")

        Returns:
            Valeur maximale de la caractéristique (max_value si défini, sinon level_5)

        Raises:
            KeyError: Si la caractéristique n'existe pas ou si stats_config n'est pas défini
        """
        if self.stats_config is None:
            raise KeyError(
                f"Stats config non disponible. Impossible de récupérer la valeur maximale de '{stat_identifier}'"
            )
        return self.stats_config.get_stat_max_value(stat_identifier)

    def get_all_stats(self) -> Dict[str, float]:
        """Retourne un dictionnaire de toutes les caractéristiques avec leurs valeurs pour le niveau actuel.

        Returns:
            Dictionnaire {stat_identifier: value} pour le niveau actuel

        Raises:
            KeyError: Si stats_config n'est pas défini
        """
        if self.stats_config is None:
            raise KeyError("Stats config non disponible. Impossible de récupérer les statistiques")
        return {
            stat_identifier: self.stats_config.get_stat_value(stat_identifier, self._level)
            for stat_identifier in self.stats_config.stats.keys()
        }

    def get_stat_tooltip(self, stat_identifier: str) -> Optional[str]:
        """Récupère le tooltip d'une caractéristique pour le niveau actuel.

        Args:
            stat_identifier: Identifiant de la caractéristique (ex: "force")

        Returns:
            Texte du tooltip pour le niveau actuel, ou None si non défini

        Raises:
            KeyError: Si la caractéristique n'existe pas ou si stats_config n'est pas défini
        """
        if self.stats_config is None:
            raise KeyError(
                f"Stats config non disponible. Impossible de récupérer le tooltip de '{stat_identifier}'"
            )
        if stat_identifier not in self.stats_config.stats:
            raise KeyError(f"Statistique '{stat_identifier}' introuvable")
        stat_def = self.stats_config.stats[stat_identifier]
        return stat_def.get_tooltip(self._level)
