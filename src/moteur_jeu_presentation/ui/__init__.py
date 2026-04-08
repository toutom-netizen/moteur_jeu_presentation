"""Module de gestion de l'interface utilisateur."""

from .player_stats_display import PlayerStatsDisplay
from .quit_confirmation import QuitConfirmationDialog
from .speech_bubble import SpeechBubble, show_speech_bubble
from .splash_screen import SplashScreen

__all__ = [
    "PlayerStatsDisplay",
    "QuitConfirmationDialog",
    "SpeechBubble",
    "show_speech_bubble",
    "SplashScreen",
]

