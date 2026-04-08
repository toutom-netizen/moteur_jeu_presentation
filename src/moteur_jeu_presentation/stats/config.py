"""Module de configuration des caractéristiques du personnage."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class StatDefinition:
    """Définition d'une caractéristique avec ses valeurs par niveau."""

    identifier: str  # Identifiant unique (ex: "force", "intelligence")
    name: str  # Nom affiché (ex: "Force")
    description: str | None = None  # Description optionnelle
    tooltips: Dict[int, str] = field(default_factory=dict)  # Dict[level, tooltip_text] pour les tooltips par niveau (optionnel)
    values: Dict[int, float] = field(default_factory=dict)  # Dict[level, value] pour levels 1..max_level
    max_value: Optional[float] = None  # Valeur maximale explicite (optionnel)
    
    def get_tooltip(self, level: int) -> str | None:
        """Récupère le tooltip pour un niveau donné.
        
        Args:
            level: Niveau du personnage (1 à max_level)
            
        Returns:
            Texte du tooltip pour le niveau, ou None si non défini
        """
        return self.tooltips.get(level)
    
    def get_max_value(self, max_level: int) -> float:
        """Récupère la valeur maximale de la caractéristique.
        
        Si max_value est défini explicitement, retourne cette valeur.
        Sinon, retourne la valeur au dernier niveau configuré (level_{max_level}).
        
        Args:
            max_level: Borne supérieure (issue de PlayerStatsConfig.max_level)
        
        Returns:
            Valeur maximale de la caractéristique
        """
        if self.max_value is not None:
            return self.max_value
        return self.values.get(max_level, 0.0)


@dataclass
class PlayerStatsConfig:
    """Configuration complète des caractéristiques du personnage."""

    stats: Dict[str, StatDefinition]  # Indexé par identifier
    display_name: str  # Nom affiché (clé racine display_name dans player_stats.toml, obligatoire)
    presentation_origins: list[str]  # [presentation].origins — UI stats, obligatoire au chargement
    presentation_class_role: list[str]  # [presentation].class_role
    presentation_traits: list[str]  # [presentation].traits
    level_up_messages: Dict[int, str] = field(default_factory=dict)  # Dict[level, message] pour les messages de level up (optionnel)
    max_level: int = 5  # Borne supérieure du niveau personnage (clé racine max_level du TOML ; défaut 5)
    double_jump_unlock_level: int = 3  # Niveau minimal pour le double saut (clé racine TOML ; défaut 3)

    def get_stat_value(self, stat_identifier: str, level: int) -> float:
        """Récupère la valeur d'une caractéristique pour un niveau donné.

        Args:
            stat_identifier: Identifiant de la caractéristique (ex: "force")
            level: Niveau du personnage (1 à max_level)

        Returns:
            Valeur de la caractéristique pour le niveau

        Raises:
            KeyError: Si la caractéristique n'existe pas
            ValueError: Si le niveau est invalide
        """
        if stat_identifier not in self.stats:
            raise KeyError(f"Statistique '{stat_identifier}' introuvable")
        if level < 1 or level > self.max_level:
            raise ValueError(
                f"Niveau invalide: {level} (doit être entre 1 et {self.max_level})"
            )
        return self.stats[stat_identifier].values.get(level, 0.0)
    
    def get_stat_max_value(self, stat_identifier: str) -> float:
        """Récupère la valeur maximale d'une caractéristique.
        
        Args:
            stat_identifier: Identifiant de la caractéristique (ex: "force")
            
        Returns:
            Valeur maximale de la caractéristique (max_value si défini, sinon level_{max_level})
            
        Raises:
            KeyError: Si la caractéristique n'existe pas
        """
        if stat_identifier not in self.stats:
            raise KeyError(f"Statistique '{stat_identifier}' introuvable")
        return self.stats[stat_identifier].get_max_value(self.max_level)
    
    def get_level_up_message(self, level: int) -> str | None:
        """Récupère le message d'amélioration pour un niveau donné.
        
        Args:
            level: Niveau du personnage (2 à max_level, car level_1 n'a pas de message)
            
        Returns:
            Message d'amélioration pour le niveau, ou None si non défini
        """
        return self.level_up_messages.get(level)

    def can_double_jump_at_level(self, level: int) -> bool:
        """Indique si le double saut est autorisé pour un niveau de personnage donné."""
        return level >= self.double_jump_unlock_level

    def get_character_presentation_dict(self) -> Dict[str, list[str]]:
        """Construit le dict attendu par l’UI stats (origins, class_role, traits → listes de chaînes)."""
        return {
            "origins": list(self.presentation_origins),
            "class_role": list(self.presentation_class_role),
            "traits": list(self.presentation_traits),
        }

