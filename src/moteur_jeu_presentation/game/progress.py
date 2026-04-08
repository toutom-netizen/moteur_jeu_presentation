"""Gestion de la progression horizontale du joueur dans un niveau."""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger("moteur_jeu_presentation.progress")


@dataclass(frozen=True)
class LevelProgressState:
    """Instantané immuable de l'état de progression."""

    current_x: float
    max_x_reached: float
    triggered_milestones: Tuple[str, ...]


@dataclass
class ProgressMilestone:
    """Représente un jalon de progression le long de l'axe X."""

    identifier: str
    threshold_x: float
    auto_reset: bool = False
    triggered: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class _MilestoneState:
    """État interne d'un jalon utilisé par le tracker."""

    active: bool = False
    newly_triggered: bool = False


class LevelProgressTracker:
    """Système centralisé de suivi de la progression horizontale du joueur."""

    def __init__(
        self,
        player: Any,
        level_width: Optional[float] = None,
        *,
        history_window_seconds: float = 5.0,
        history_sample_rate: int = 60,
    ) -> None:
        """Initialise le tracker de progression.

        Args:
            player: Instance du joueur (doit exposer `position_world` ou `x`).
            level_width: Largeur totale du niveau en pixels si connue.
            history_window_seconds: Fenêtre temporelle de l'historique (par défaut 5s).
            history_sample_rate: Taux d'échantillonnage pour l'historique (par défaut 60 Hz).
        """
        self.player = player
        self.level_width = level_width if level_width and level_width > 0 else None

        self.current_x: float = 0.0
        self.max_x_reached: float = 0.0
        self._elapsed_time: float = 0.0

        history_capacity = max(1, int(history_window_seconds * history_sample_rate))
        self.history: Deque[Tuple[float, float]] = deque(maxlen=history_capacity)

        self.milestones: Dict[str, ProgressMilestone] = {}
        self._milestone_states: Dict[str, _MilestoneState] = {}

        logger.info("LevelProgressTracker initialisé (level_width=%s)", self.level_width)

    def reset(self, level_width: Optional[float] = None) -> None:
        """Réinitialise l'état du tracker (changement de niveau, respawn, etc.)."""
        self.level_width = level_width if level_width and level_width > 0 else None
        self.current_x = 0.0
        self.max_x_reached = 0.0
        self._elapsed_time = 0.0
        self.history.clear()
        for milestone in self.milestones.values():
            milestone.triggered = False
        for state in self._milestone_states.values():
            state.active = False
            state.newly_triggered = False
        logger.info("LevelProgressTracker réinitialisé (level_width=%s)", self.level_width)

    def update(self, dt: float) -> None:
        """Met à jour la progression à partir de la position du joueur."""
        self._elapsed_time += max(dt, 0.0)
        player_x = self._resolve_player_world_x()

        self.current_x = player_x
        if player_x > self.max_x_reached:
            old_max = self.max_x_reached
            self.max_x_reached = player_x
            logger.debug(
                "Nouveau max_x atteint: %.2f (précédent: %.2f)",
                self.max_x_reached,
                old_max,
            )

        self.history.append((self._elapsed_time, self.current_x))
        self._update_milestones()

    def get_current_x(self) -> int:
        """Retourne la progression actuelle arrondie pour l'affichage."""
        return int(round(self.current_x))

    def get_max_x(self) -> int:
        """Retourne la progression maximale atteinte arrondie."""
        return int(round(self.max_x_reached))

    def get_progress_ratio(self) -> Optional[float]:
        """Retourne le ratio de progression (0.0-1.0) si la largeur est connue."""
        if self.level_width is None or self.level_width <= 0.0:
            return None
        return max(0.0, min(self.current_x / self.level_width, 1.0))

    def get_state(self) -> LevelProgressState:
        """Retourne un instantané immuable de l'état courant."""
        triggered_ids = tuple(
            identifier for identifier, milestone in self.milestones.items() if milestone.triggered
        )
        return LevelProgressState(
            current_x=self.current_x,
            max_x_reached=self.max_x_reached,
            triggered_milestones=triggered_ids,
        )

    def register_milestone(self, milestone: ProgressMilestone) -> None:
        """Enregistre (ou remplace) un jalon de progression."""
        if milestone.threshold_x < 0:
            raise ValueError("threshold_x doit être positif")
        self.milestones[milestone.identifier] = milestone
        self._milestone_states[milestone.identifier] = _MilestoneState()
        logger.debug(
            "Milestone enregistré: %s (threshold=%.2f, auto_reset=%s)",
            milestone.identifier,
            milestone.threshold_x,
            milestone.auto_reset,
        )

    def register_milestones(self, milestones: Iterable[ProgressMilestone]) -> None:
        """Ajoute plusieurs jalons en une seule opération."""
        for milestone in milestones:
            self.register_milestone(milestone)

    def get_triggered_milestones(self, *, consume: bool = True) -> List[ProgressMilestone]:
        """Retourne la liste des jalons déclenchés depuis le dernier appel."""
        triggered: List[ProgressMilestone] = []
        for identifier, state in self._milestone_states.items():
            if state.newly_triggered:
                milestone = self.milestones[identifier]
                triggered.append(milestone)
                if consume:
                    state.newly_triggered = False
                    if milestone.auto_reset:
                        milestone.triggered = True
        return triggered

    def _resolve_player_world_x(self) -> float:
        """Récupère la position monde du joueur sur l'axe X."""
        if hasattr(self.player, "position_world"):
            position = self.player.position_world  # type: ignore[attr-defined]
            if hasattr(position, "x"):
                return float(position.x)  # type: ignore[call-arg]
            if isinstance(position, (tuple, list)) and position:
                return float(position[0])
        if hasattr(self.player, "x"):
            return float(self.player.x)  # type: ignore[attr-defined]
        raise AttributeError("Le joueur doit exposer position_world ou x pour le suivi de progression.")

    def _update_milestones(self) -> None:
        """Met à jour l'état des jalons enregistrés."""
        for identifier, milestone in self.milestones.items():
            state = self._milestone_states.setdefault(identifier, _MilestoneState())
            has_crossed = self.current_x >= milestone.threshold_x

            if milestone.auto_reset:
                if has_crossed and not state.active:
                    state.active = True
                    state.newly_triggered = True
                    milestone.triggered = True
                    logger.debug("Milestone déclenché (auto_reset): %s", identifier)
                elif not has_crossed and state.active:
                    state.active = False
                    milestone.triggered = False
            else:
                if has_crossed and not milestone.triggered:
                    milestone.triggered = True
                    state.active = True
                    state.newly_triggered = True
                    logger.debug("Milestone déclenché: %s", identifier)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<LevelProgressTracker current_x={self.current_x:.2f} "
            f"max_x={self.max_x_reached:.2f} level_width={self.level_width}>"
        )


