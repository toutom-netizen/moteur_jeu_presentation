"""Module de gestion des déclencheurs d'événements basés sur la progression."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Literal, Optional, Tuple, Union
import math

try:
    # Python 3.11+ a tomllib intégré
    import tomllib as tomli  # type: ignore
except ImportError:
    # Python < 3.11 nécessite tomli
    try:
        import tomli  # type: ignore[import-not-found]
    except ImportError:
        raise ImportError(
            "tomli is required for Python < 3.11. Install it with: pip install tomli"
        )

from ..entities.npc import NPC
from ..rendering.config import compute_design_scale
from .progress import LevelProgressTracker

if TYPE_CHECKING:
    from ..entities.player import Player
    from ..rendering.parallax import ParallaxSystem
    from ..rendering.layer import Layer
    from ..rendering.camera_zoom import CameraZoomController
    from ..physics.collision import CollisionSystem
    from ..particles import ParticleSystem
else:
    from ..rendering.parallax import ParallaxSystem
    from ..rendering.layer import Layer
    from ..physics.collision import CollisionSystem

logger = logging.getLogger("moteur_jeu_presentation.events")


@dataclass
class SpriteMovementTask:
    """Tâche de mouvement pour un sprite."""
    
    layer: Layer
    start_x: float  # Position X de départ
    start_y: float  # Position Y de départ
    target_x: float  # Position X de destination
    target_y: float  # Position Y de destination
    move_speed: float  # Vitesse en pixels par seconde
    remaining_distance: float  # Distance restante à parcourir
    direction_x: float  # Direction normalisée X
    direction_y: float  # Direction normalisée Y


@dataclass
class NPCMoveEventConfig:
    """Configuration d'un événement de déplacement de PNJ."""

    npc_id: str  # Identifiant technique du PNJ (doit correspondre à un PNJ chargé)
    target_x: float  # Position X vers laquelle le PNJ doit se déplacer
    direction: Literal["left", "right"]  # Sens de déplacement (change la direction du PNJ)
    move_animation_row: Optional[int] = None  # Ligne du sprite sheet pour l'animation de déplacement (optionnel)
    move_animation_frames: Optional[int] = None  # Nombre de frames pour l'animation de déplacement (optionnel)
    move_speed: float = 300.0  # Vitesse de déplacement en pixels par seconde (défaut: 300.0)


@dataclass
class NPCFollowEventConfig:
    """Configuration d'un événement de suivi du personnage principal par un PNJ."""

    npc_id: str  # Identifiant technique du PNJ (doit correspondre à un PNJ chargé)
    follow_distance: float = 100.0  # Distance horizontale à maintenir derrière le joueur en pixels (défaut: 100.0)
    follow_speed: float = 200.0  # Vitesse de déplacement lors du suivi en pixels par seconde (défaut: 200.0)
    animation_row: Optional[int] = None  # Ligne du sprite sheet pour l'animation de suivi (optionnel). Si non spécifié, utilise l'animation "walk" si disponible
    animation_frames: Optional[int] = None  # Nombre de frames pour l'animation de suivi (optionnel). Si non spécifié, utilise la configuration d'animation existante


@dataclass
class NPCStopFollowEventConfig:
    """Configuration d'un événement d'arrêt du suivi du personnage principal par un PNJ."""

    npc_id: str  # Identifiant technique du PNJ (doit correspondre à un PNJ chargé). Le PNJ s'arrête à sa position actuelle


@dataclass
class NPCMagicMoveEventConfig:
    """Configuration d'un événement de téléportation magique de PNJ (disparition/réapparition)."""

    npc_id: str  # Identifiant technique du PNJ (doit correspondre à un PNJ chargé)
    target_x: float  # Position X où le PNJ doit réapparaître (en pixels, position monde)
    target_y: float  # Position Y où le PNJ doit réapparaître (en pixels, position monde)
    sprite_sheet_path: Optional[str] = None  # Chemin vers le sprite sheet à utiliser lors de la réapparition (optionnel). Si None, utilise le sprite sheet actuel du PNJ
    fade_in_duration: float = 1.0  # Durée de l'apparition progressive en secondes (défaut: 1.0). Le PNJ apparaît progressivement (fade in) sur cette durée
    animation_row: Optional[int] = None  # Ligne du sprite sheet à utiliser lors de la réapparition (optionnel). Si non spécifié, utilise l'animation actuelle du PNJ
    animation_start: Optional[int] = None  # Frame de départ du sprite à afficher lors de la réapparition (optionnel, 0-indexed). Si non spécifié, utilise la frame actuelle ou la frame 0
    direction: Optional[Literal["left", "right"]] = None  # Direction du PNJ lors de la réapparition (optionnel). Si non spécifié, conserve la direction actuelle du PNJ


@dataclass
class SpriteHideEventConfig:
    """Configuration d'un événement de masquage de sprite."""

    sprite_tag: str  # Tag du sprite à masquer (doit correspondre à un tag défini dans le fichier .niveau)
    fade_duration: float = 1.0  # Durée de la disparition progressive en secondes (défaut: 1.0)
    remove_collisions: bool = True  # Si True, supprime les collisions une fois le sprite complètement masqué (défaut: True)


@dataclass
class SpriteShowEventConfig:
    """Configuration d'un événement d'affichage de sprite."""

    sprite_tag: str  # Tag du sprite à afficher (doit correspondre à un tag défini dans le fichier .niveau)
    fade_duration: float = 1.0  # Durée de l'apparition progressive en secondes (défaut: 1.0)
    restore_collisions: bool = True  # Si True, restaure les collisions une fois le sprite complètement affiché (défaut: True)


@dataclass
class SpriteMoveEventConfig:
    """Configuration d'un événement de déplacement de sprite."""

    sprite_tag: str  # Tag du sprite à déplacer (doit correspondre à un tag défini dans le fichier .niveau)
    move_x: float  # Déplacement horizontal en pixels (peut être négatif)
    move_y: float  # Déplacement vertical en pixels (peut être négatif)
    move_speed: float = 250.0  # Vitesse de déplacement en pixels par seconde (défaut: 250.0)


@dataclass
class SpriteMovePerpetualEventConfig:
    """Configuration d'un événement de déplacement perpétuel de sprite."""

    sprite_tag: str  # Tag du sprite à déplacer (doit correspondre à un tag défini dans le fichier .niveau)
    move_x: float  # Déplacement horizontal en pixels depuis la position de départ (peut être négatif). Le sprite va de sa position initiale à position_initial + move_x, puis revient, indéfiniment
    move_y: float  # Déplacement vertical en pixels depuis la position de départ (peut être négatif). Le sprite va de sa position initiale à position_initial + move_y, puis revient, indéfiniment
    move_speed: float = 250.0  # Vitesse de déplacement en pixels par seconde (défaut: 250.0). Le mouvement est homogène : la projection sur X et Y conserve un ratio constant


@dataclass
class SpriteRotateEventConfig:
    """Configuration d'un événement de rotation de sprite."""

    sprite_tag: str  # Tag du sprite à faire tourner (doit correspondre à un tag défini dans le fichier .niveau)
    rotation_speed: float  # Vitesse de rotation en degrés par seconde (positive = sens horaire, négative = sens antihoraire)
    duration: float  # Durée de la rotation en secondes. Après cette durée, la rotation s'arrête et le sprite reste à son angle final


@dataclass
class SpritePerpetualMovementTask:
    """Tâche de mouvement perpétuel pour un sprite."""
    
    layer: "Layer"
    start_x: float  # Position X de départ (capturée au déclenchement)
    start_y: float  # Position Y de départ (capturée au déclenchement)
    target_x: float  # Position X de destination (start_x + move_x)
    target_y: float  # Position Y de destination (start_y + move_y)
    move_speed: float  # Vitesse en pixels par seconde
    remaining_distance: float  # Distance restante à parcourir
    direction_x: float  # Direction normalisée X
    direction_y: float  # Direction normalisée Y
    going_to_target: bool  # True si on va vers la destination, False si on revient vers le départ


@dataclass
class SpriteRotationTask:
    """Tâche de rotation pour un sprite."""
    
    layer: "Layer"
    initial_angle: float  # Angle de rotation initial en degrés (défaut: 0.0)
    rotation_speed: float  # Vitesse de rotation en degrés par seconde (positive = horaire, négative = antihoraire)
    duration: float  # Durée totale de la rotation en secondes
    elapsed_time: float  # Temps écoulé depuis le début de la rotation (initialisé à 0.0)


@dataclass
class InventoryAddEventConfig:
    """Configuration d'un événement d'ajout d'objet à l'inventaire."""

    item_id: str  # ID technique de l'objet à ajouter (doit correspondre à un objet défini dans inventory_items.toml)
    quantity: int = 1  # Quantité d'objets à ajouter (défaut: 1)


@dataclass
class InventoryRemoveEventConfig:
    """Configuration d'un événement de retrait d'objet de l'inventaire."""

    item_id: str  # ID technique de l'objet à retirer (doit correspondre à un objet défini dans inventory_items.toml)
    quantity: int = 1  # Quantité d'objets à retirer (défaut: 1)


@dataclass
class LevelUpEventConfig:
    """Configuration d'un événement de level up du personnage principal."""
    # Aucun champ requis : l'événement de level up ne nécessite pas de configuration supplémentaire.
    # Lorsqu'il est déclenché, l'affichage "level up (press u)" sera automatiquement affiché
    # au-dessus du nom du personnage principal (voir spécification 2).


@dataclass
class ScreenFadeEventConfig:
    """Configuration d'un événement de fondu au noir de l'écran."""
    fade_in_duration: float = 1.0  # Durée du fondu au noir en secondes (défaut: 1.0). L'écran devient progressivement noir sur cette durée
    text_fade_in_duration: float = 0.5  # Durée de l'apparition du texte sur le fond noir en secondes (défaut: 0.5). Le texte apparaît progressivement après le fade_in
    text_display_duration: float = 1.0  # Durée d'affichage du texte sur le fond noir en secondes (défaut: 1.0). Le texte reste visible à opacité maximale pendant cette durée
    text_fade_out_duration: float = 0.5  # Durée de la disparition du texte sur le fond noir en secondes (défaut: 0.5). Le texte disparaît progressivement avant le fade_out
    fade_out_duration: float = 1.0  # Durée du fondu de retour en secondes (défaut: 1.0). L'écran redevient progressivement visible sur cette durée
    text: Optional[str] = None  # Texte optionnel à afficher en blanc centré au milieu de l'écran. Le texte apparaît après le fade_in, reste visible, puis disparaît avant le fade_out. Si None, aucun texte n'est affiché


@dataclass
class CameraZoomEventConfig:
    """Configuration d'un événement de zoom caméra (post-process)."""

    zoom_percent: float  # Pourcentage de zoom (100 = zoom neutre)
    duration: float = 0.8  # Durée de l'animation (secondes)
    bottom_margin: float = 50.0  # Marge sous les pieds (pixels design 1920x1080)
    keep_bubbles_visible: bool = True  # Force les bulles à rester à l'écran (cap zoom si nécessaire)


@dataclass
class CameraZoomResetEventConfig:
    """Configuration d'un événement de retour au zoom initial (post-process)."""

    duration: float = 0.8  # Durée de l'animation (secondes)


@dataclass
class CameraZoomSpriteEventConfig:
    """Configuration d'un événement de zoom caméra sur un sprite."""

    sprite_tag: str  # Tag du sprite à zoomer (doit correspondre à un tag défini dans le fichier .niveau)
    zoom_percent: float  # Pourcentage de zoom (100 = zoom neutre)
    offset_x: float = 0.0  # Offset horizontal en pixels (repère design 1920x1080, défaut: 0.0)
    offset_y: float = 0.0  # Offset vertical en pixels (repère design 1920x1080, défaut: 0.0)
    duration: float = 0.8  # Durée de l'animation (secondes)
    keep_bubbles_visible: bool = True  # Force les bulles à rester à l'écran (cap zoom si nécessaire)


@dataclass
class ParticleEffectEventConfig:
    """Configuration d'un événement de lancement d'effet de particules."""
    effect_type: Literal["explosion", "confetti", "flame_explosion", "rain", "smoke", "sparks"]  # Type d'effet de particules à lancer (voir spécification 14 pour les détails de chaque type)
    x: Optional[float] = None  # Position X où l'effet doit être lancé (en pixels, coordonnées monde du design 1920x1080, converties automatiquement vers la résolution de rendu). Optionnel si spawn_area ou sprite_tag est spécifié
    y: Optional[float] = None  # Position Y où l'effet doit être lancé (en pixels, coordonnées monde du design 1920x1080, converties automatiquement vers la résolution de rendu). Optionnel si spawn_area ou sprite_tag est spécifié
    spawn_area: Optional[Dict[str, float]] = None  # Zone de génération des particules (optionnel). Si spécifié, les particules sont générées aléatoirement dans cette zone au lieu d'un point unique. Format: {"x_min": float, "x_max": float, "y_min": float, "y_max": float} (en pixels, coordonnées monde du design 1920x1080). Si None, utilise x et y comme point unique. Si sprite_tag est spécifié, spawn_area est ignoré. Si spawn_area est spécifié, x et y sont ignorés
    sprite_tag: Optional[str] = None  # Tag du sprite à utiliser comme zone d'émission (optionnel). Si spécifié, les particules sont générées dans la zone couverte par tous les sprites ayant ce tag. Le tag doit correspondre à un tag défini dans le fichier .niveau. Si sprite_tag est spécifié, spawn_area, x et y sont ignorés. La zone est calculée en prenant l'union des bounds de tous les sprites avec ce tag
    spawn_edge: Optional[Literal["top", "bottom", "left", "right"]] = None  # Bord du sprite où limiter la génération des particules (optionnel). Si spécifié, les particules sont générées uniquement le long du bord spécifié du sprite (ou des sprites si plusieurs partagent le tag). "top" = bord supérieur (bande horizontale en haut), "bottom" = bord inférieur (bande horizontale en bas), "left" = bord gauche (bande verticale à gauche), "right" = bord droit (bande verticale à droite). Si None, les particules sont générées dans toute la zone du sprite. Nécessite que sprite_tag soit spécifié, sinon est ignoré
    count: Optional[int] = None  # Nombre de particules (optionnel). Si None, utilise la valeur par défaut du type d'effet (voir spécification 14)
    speed: Optional[float] = None  # Vitesse de base des particules en pixels/seconde (optionnel). Si None, utilise la valeur par défaut du type d'effet
    lifetime: Optional[float] = None  # Durée de vie des particules en secondes (optionnel). Si None, utilise la valeur par défaut du type d'effet
    size: Optional[int] = None  # Taille de base des particules en pixels (diamètre, optionnel). Si None, utilise la valeur par défaut du type d'effet
    color: Optional[Tuple[int, int, int]] = None  # Couleur de base des particules (RGB, optionnel, rétrocompatibilité). Si None et colors n'est pas spécifié, utilise la couleur par défaut du type d'effet. Note: Pour "flame_explosion" et "confetti", la couleur est ignorée car ces effets utilisent des palettes de couleurs prédéfinies. Si colors est spécifié, color est ignoré
    colors: Optional[List[Tuple[int, int, int]]] = None  # Liste de couleurs pour les particules (RGB, optionnel). Si spécifié, chaque particule choisit aléatoirement une couleur parmi cette liste. Si None, utilise color (ou la couleur par défaut du type d'effet). Note: Pour "flame_explosion" et "confetti", colors est ignoré car ces effets utilisent des palettes de couleurs prédéfinies
    color_variation: Optional[float] = None  # Variation de couleur (0.0 à 1.0, optionnel). Si spécifié, chaque particule aura une variation aléatoire de couleur appliquée. 0.0 = aucune variation, 1.0 = variation maximale. Si None, utilise la valeur par défaut du type d'effet. Note: Pour "flame_explosion" et "confetti", color_variation est ignoré car ces effets utilisent des palettes de couleurs prédéfinies
    generation_duration: Optional[float] = None  # Durée de génération des particules en secondes (optionnel). Si spécifié, les particules sont générées progressivement sur cette durée au lieu d'être toutes créées immédiatement. Par exemple, si count = 100 et generation_duration = 2.0, environ 50 particules par seconde seront générées pendant 2 secondes. Si None, toutes les particules sont créées immédiatement (comportement par défaut). Doit être > 0 si spécifié
    direction_angle: Optional[float] = None  # Angle de direction principal des particules en radians (optionnel). Si spécifié, remplace la direction par défaut du type d'effet. 0.0 = vers la droite, π/2 (≈1.57) = vers le bas, -π/2 (≈-1.57) = vers le haut, π (≈3.14) = vers la gauche. Si None, utilise la direction par défaut du type d'effet
    direction_spread: Optional[float] = None  # Étalement de direction en radians (optionnel). Si spécifié, définit la dispersion angulaire autour de direction_angle. 0.0 = toutes les particules partent dans la même direction, π/4 (≈0.79) = dispersion de 45° de part et d'autre, 2π (≈6.28) = toutes les directions. Si None, utilise la valeur par défaut du type d'effet

@dataclass
class EventTriggerConfig:
    """Configuration d'un déclencheur d'événement."""

    identifier: str  # Identifiant unique du déclencheur
    event_type: Literal[
        "npc_move",
        "npc_follow",
        "npc_stop_follow",
        "npc_magic_move",
        "sprite_hide",
        "sprite_show",
        "sprite_move",
        "sprite_move_perpetual",
        "sprite_rotate",
        "inventory_add",
        "inventory_remove",
        "level_up",
        "screen_fade",
        "particle_effect",
        "camera_zoom",
        "camera_zoom_sprite",
        "camera_zoom_reset",
    ]  # Type d'événement
    event_data: Union[
        NPCMoveEventConfig,
        NPCFollowEventConfig,
        NPCStopFollowEventConfig,
        NPCMagicMoveEventConfig,
        SpriteHideEventConfig,
        SpriteShowEventConfig,
        SpriteMoveEventConfig,
        SpriteMovePerpetualEventConfig,
        SpriteRotateEventConfig,
        InventoryAddEventConfig,
        InventoryRemoveEventConfig,
        LevelUpEventConfig,
        ScreenFadeEventConfig,
        ParticleEffectEventConfig,
        CameraZoomEventConfig,
        CameraZoomSpriteEventConfig,
        CameraZoomResetEventConfig,
    ]  # Données spécifiques à l'événement
    trigger_x: Optional[float] = None  # Position X que le joueur doit atteindre pour déclencher l'événement (optionnel). Si None, l'événement ne peut être déclenché que manuellement (par exemple via les dialogues de PNJ)
    triggered: bool = False  # Indique si l'événement a déjà été déclenché
    repeatable: bool = False  # Si True, l'événement peut être déclenché plusieurs fois (par défaut: False). Si False, l'événement ne peut être déclenché qu'une seule fois


@dataclass
class EventsConfig:
    """Configuration complète des événements pour un niveau."""

    events: List[EventTriggerConfig]  # Liste des déclencheurs d'événements


class EventTriggerSystem:
    """Système de gestion des déclencheurs d'événements basés sur la progression."""

    def __init__(
        self,
        progress_tracker: LevelProgressTracker,
        npcs: Dict[str, NPC],  # Dictionnaire des PNJ indexés par leur ID technique
        layers_by_tag: Dict[str, List[Layer]],  # Dictionnaire des layers indexés par tag
        parallax_system: ParallaxSystem,  # Système de parallaxe pour accéder aux layers
        collision_system: Optional[CollisionSystem] = None,  # Système de collisions (optionnel, pour supprimer les collisions)
        player: Optional["Player"] = None,  # Instance du joueur (obligatoire pour les événements d'inventaire et de level up)
        particle_system: Optional["ParticleSystem"] = None,  # Système de particules (obligatoire pour les événements particle_effect)
        camera_zoom: Optional["CameraZoomController"] = None,  # Contrôleur de zoom caméra (optionnel)
    ) -> None:
        """Initialise le système de déclencheurs.

        Args:
            progress_tracker: Système de progression pour obtenir la position du joueur
            npcs: Dictionnaire des PNJ disponibles (clé = ID technique, valeur = instance NPC)
            layers_by_tag: Dictionnaire des layers indexés par tag (retourné par LevelLoader.create_parallax_layers)
            parallax_system: Système de parallaxe contenant les layers
            collision_system: Système de collisions (optionnel, nécessaire pour supprimer les collisions lors du masquage de sprites)
            player: Instance du joueur (obligatoire pour les événements d'inventaire et de level up)
            particle_system: Système de particules (obligatoire pour les événements particle_effect, voir spécification 14)
        """
        self.progress_tracker = progress_tracker
        self.npcs = npcs
        self.layers_by_tag = layers_by_tag
        self.parallax_system = parallax_system
        self.collision_system = collision_system
        self.player = player
        self.particle_system = particle_system
        self.camera_zoom = camera_zoom
        self.events: List[EventTriggerConfig] = []
        # Dictionnaire pour suivre les animations de fade out en cours : {layer: (fade_timer, fade_duration, initial_alpha)}
        self._fade_out_timers: Dict[Layer, tuple[float, float, int]] = {}
        # Dictionnaire pour suivre les animations de fade in en cours : {layer: (fade_timer, fade_duration, initial_alpha)}
        self._fade_in_timers: Dict[Layer, tuple[float, float, int]] = {}
        # Dictionnaire pour suivre les animations de fade in des NPCs en cours : {npc: (fade_timer, fade_duration)}
        self._npc_fade_in_timers: Dict[NPC, tuple[float, float]] = {}
        # Liste des tâches de mouvement de sprites en cours : {layer: SpriteMovementTask}
        self._sprite_movement_tasks: Dict[Layer, SpriteMovementTask] = {}
        # Liste des tâches de mouvement perpétuel de sprites en cours : {layer: SpritePerpetualMovementTask}
        self._sprite_perpetual_movement_tasks: Dict[Layer, SpritePerpetualMovementTask] = {}
        # Liste des tâches de rotation de sprites en cours : {layer: SpriteRotationTask}
        self._sprite_rotation_tasks: Dict[Layer, SpriteRotationTask] = {}
        # État du fondu au noir de l'écran
        self._screen_fade_timer: float = 0.0  # Timer global pour suivre la progression du fondu
        self._screen_fade_phase: Literal["fade_in", "text_fade_in", "text_display", "text_fade_out", "fade_out", "none"] = "none"  # Phase actuelle du fondu
        self._screen_fade_config: Optional[ScreenFadeEventConfig] = None  # Configuration du fondu actif (None si aucun fondu n'est actif)
        self._design_scale_x, self._design_scale_y = compute_design_scale(
            (parallax_system.screen_width, parallax_system.screen_height)
        )
        logger.info("EventTriggerSystem initialisé avec %d PNJ", len(npcs))

    def load_events(self, events_path: Path) -> None:
        """Charge un fichier de configuration d'événements.

        Args:
            events_path: Chemin vers le fichier .event ou .toml

        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            ValueError: Si le format du fichier est invalide
        """
        events_path = Path(events_path)

        if not events_path.exists():
            raise FileNotFoundError(f"Fichier d'événements introuvable: {events_path}")

        try:
            with open(events_path, "rb") as f:
                data = tomli.load(f)
        except Exception as e:
            raise ValueError(f"Erreur lors du parsing du fichier TOML: {e}") from e

        # Valider et extraire la configuration des événements
        if "events" not in data:
            raise ValueError("Section [events] manquante dans le fichier de configuration")

        events_data = data["events"]
        if not isinstance(events_data, list):
            raise ValueError("Section [events] doit être une liste")

        events: List[EventTriggerConfig] = []

        for event_data in events_data:
            if not isinstance(event_data, dict):
                raise ValueError("Chaque élément de [events] doit être un dictionnaire")

            # Champs obligatoires
            required_fields = ["identifier", "event_type", "event_data"]
            for field in required_fields:
                if field not in event_data:
                    raise ValueError(f"Champ '{field}' manquant dans la configuration d'un événement")

            identifier = str(event_data["identifier"])
            # trigger_x est optionnel (peut être None si l'événement est déclenché uniquement par les dialogues)
            trigger_x = event_data.get("trigger_x")
            if trigger_x is not None:
                trigger_x = float(trigger_x) * self._design_scale_x
            # repeatable est optionnel (défaut: False)
            repeatable = event_data.get("repeatable", False)
            if not isinstance(repeatable, bool):
                raise ValueError(
                    f"repeatable doit être un booléen pour l'événement '{identifier}', "
                    f"reçu: {type(repeatable).__name__}"
                )
            event_type_str = str(event_data["event_type"])

            if event_type_str not in (
                "npc_move",
                "npc_follow",
                "npc_stop_follow",
                "npc_magic_move",
                "sprite_hide",
                "sprite_show",
                "sprite_move",
                "sprite_move_perpetual",
                "sprite_rotate",
                "inventory_add",
                "inventory_remove",
                "level_up",
                "screen_fade",
                "particle_effect",
                "camera_zoom",
                "camera_zoom_sprite",
                "camera_zoom_reset",
            ):
                raise ValueError(
                    f"Type d'événement invalide '{event_type_str}'. "
                    "Types supportés: 'npc_move', 'npc_follow', 'npc_stop_follow', 'npc_magic_move', 'sprite_hide', 'sprite_show', 'sprite_move', 'sprite_move_perpetual', 'sprite_rotate', 'inventory_add', 'inventory_remove', 'level_up', 'screen_fade', 'particle_effect', 'camera_zoom', 'camera_zoom_sprite', 'camera_zoom_reset'"
                )
            event_type: Literal[
                "npc_move",
                "npc_follow",
                "npc_stop_follow",
                "npc_magic_move",
                "sprite_hide",
                "sprite_show",
                "sprite_move",
                "sprite_move_perpetual",
                "sprite_rotate",
                "inventory_add",
                "inventory_remove",
                "level_up",
                "screen_fade",
                "particle_effect",
                "camera_zoom",
                "camera_zoom_sprite",
                "camera_zoom_reset",
            ] = event_type_str  # type: ignore

            # Charger les données de l'événement
            event_data_dict = event_data["event_data"]
            if not isinstance(event_data_dict, dict):
                raise ValueError(
                    f"Section 'event_data' doit être un dictionnaire pour l'événement '{identifier}'"
                )

            if event_type_str == "npc_move":
                # Champs obligatoires pour npc_move
                required_npc_move_fields = ["npc_id", "target_x", "direction"]
                for field in required_npc_move_fields:
                    if field not in event_data_dict:
                        raise ValueError(
                            f"Champ '{field}' manquant dans event_data pour l'événement '{identifier}'"
                        )

                npc_id = str(event_data_dict["npc_id"])
                target_x = float(event_data_dict["target_x"]) * self._design_scale_x
                direction_str = str(event_data_dict["direction"])

                if direction_str not in ("left", "right"):
                    raise ValueError(
                        f"direction doit être 'left' ou 'right' pour l'événement '{identifier}', "
                        f"reçu: '{direction_str}'"
                    )
                direction: Literal["left", "right"] = direction_str  # type: ignore

                # Vérifier que le PNJ existe
                if npc_id not in self.npcs:
                    raise ValueError(
                        f"PNJ avec l'ID '{npc_id}' introuvable pour l'événement '{identifier}'. "
                        f"PNJ disponibles: {list(self.npcs.keys())}"
                    )

                # Champs optionnels
                move_speed = float(event_data_dict.get("move_speed", 300.0))
                if move_speed <= 0:
                    raise ValueError(
                        f"move_speed doit être positif pour l'événement '{identifier}'"
                    )
                move_speed *= self._design_scale_x

                move_animation_row = event_data_dict.get("move_animation_row")
                move_animation_frames = event_data_dict.get("move_animation_frames")

                # Valider que si l'un est spécifié, l'autre doit l'être aussi
                if (move_animation_row is not None) != (move_animation_frames is not None):
                    raise ValueError(
                        f"move_animation_row et move_animation_frames doivent être spécifiés ensemble "
                        f"pour l'événement '{identifier}'"
                    )

                if move_animation_row is not None:
                    move_animation_row = int(move_animation_row)
                    if move_animation_row < 0:
                        raise ValueError(
                            f"move_animation_row doit être >= 0 pour l'événement '{identifier}'"
                        )

                if move_animation_frames is not None:
                    move_animation_frames = int(move_animation_frames)
                    if move_animation_frames <= 0:
                        raise ValueError(
                            f"move_animation_frames doit être > 0 pour l'événement '{identifier}'"
                        )

                npc_move_config = NPCMoveEventConfig(
                    npc_id=npc_id,
                    target_x=target_x,
                    direction=direction,
                    move_animation_row=move_animation_row,
                    move_animation_frames=move_animation_frames,
                    move_speed=move_speed,
                )

                event_config = EventTriggerConfig(
                    identifier=identifier,
                    trigger_x=trigger_x,
                    event_type=event_type,
                    event_data=npc_move_config,
                    triggered=False,
                    repeatable=repeatable,
                )

                events.append(event_config)
            elif event_type_str == "npc_follow":
                # Champs obligatoires pour npc_follow
                if "npc_id" not in event_data_dict:
                    raise ValueError(
                        f"Champ 'npc_id' manquant dans event_data pour l'événement '{identifier}'"
                    )

                npc_id = str(event_data_dict["npc_id"])

                # Vérifier que le PNJ existe
                if npc_id not in self.npcs:
                    raise ValueError(
                        f"PNJ avec l'ID '{npc_id}' introuvable pour l'événement '{identifier}'. "
                        f"PNJ disponibles: {list(self.npcs.keys())}"
                    )

                # Vérifier que player est fourni
                if self.player is None:
                    raise ValueError(
                        f"L'instance Player est requise pour les événements npc_follow (événement '{identifier}')"
                    )

                # Champs optionnels
                follow_distance = float(event_data_dict.get("follow_distance", 100.0))
                if follow_distance <= 0:
                    raise ValueError(
                        f"follow_distance doit être positif pour l'événement '{identifier}'"
                    )
                follow_distance *= self._design_scale_x

                follow_speed = float(event_data_dict.get("follow_speed", 200.0))
                if follow_speed <= 0:
                    raise ValueError(
                        f"follow_speed doit être positif pour l'événement '{identifier}'"
                    )
                follow_speed *= self._design_scale_x

                animation_row = event_data_dict.get("animation_row")
                animation_frames = event_data_dict.get("animation_frames")

                # Valider que si l'un est spécifié, l'autre doit l'être aussi
                if (animation_row is not None) != (animation_frames is not None):
                    raise ValueError(
                        f"animation_row et animation_frames doivent être spécifiés ensemble "
                        f"pour l'événement '{identifier}'"
                    )

                if animation_row is not None:
                    animation_row = int(animation_row)
                    if animation_row < 0:
                        raise ValueError(
                            f"animation_row doit être >= 0 pour l'événement '{identifier}'"
                        )

                if animation_frames is not None:
                    animation_frames = int(animation_frames)
                    if animation_frames <= 0:
                        raise ValueError(
                            f"animation_frames doit être > 0 pour l'événement '{identifier}'"
                        )

                npc_follow_config = NPCFollowEventConfig(
                    npc_id=npc_id,
                    follow_distance=follow_distance,
                    follow_speed=follow_speed,
                    animation_row=animation_row,
                    animation_frames=animation_frames,
                )

                event_config = EventTriggerConfig(
                    identifier=identifier,
                    trigger_x=trigger_x,
                    event_type=event_type,
                    event_data=npc_follow_config,
                    triggered=False,
                    repeatable=repeatable,
                )

                events.append(event_config)
            elif event_type_str == "npc_stop_follow":
                # Champs obligatoires pour npc_stop_follow
                if "npc_id" not in event_data_dict:
                    raise ValueError(
                        f"Champ 'npc_id' manquant dans event_data pour l'événement '{identifier}'"
                    )

                npc_id = str(event_data_dict["npc_id"])

                # Vérifier que le PNJ existe
                if npc_id not in self.npcs:
                    raise ValueError(
                        f"PNJ avec l'ID '{npc_id}' introuvable pour l'événement '{identifier}'. "
                        f"PNJ disponibles: {list(self.npcs.keys())}"
                    )

                npc_stop_follow_config = NPCStopFollowEventConfig(
                    npc_id=npc_id,
                )

                event_config = EventTriggerConfig(
                    identifier=identifier,
                    trigger_x=trigger_x,
                    event_type=event_type,
                    event_data=npc_stop_follow_config,
                    triggered=False,
                    repeatable=repeatable,
                )

                events.append(event_config)
            elif event_type_str == "npc_magic_move":
                # Champs obligatoires pour npc_magic_move
                required_npc_magic_move_fields = ["npc_id", "target_x", "target_y"]
                for field in required_npc_magic_move_fields:
                    if field not in event_data_dict:
                        raise ValueError(
                            f"Champ '{field}' manquant dans event_data pour l'événement '{identifier}'"
                        )

                npc_id = str(event_data_dict["npc_id"])
                target_x = float(event_data_dict["target_x"]) * self._design_scale_x
                target_y = float(event_data_dict["target_y"]) * self._design_scale_y

                # Vérifier que le PNJ existe
                if npc_id not in self.npcs:
                    raise ValueError(
                        f"PNJ avec l'ID '{npc_id}' introuvable pour l'événement '{identifier}'. "
                        f"PNJ disponibles: {list(self.npcs.keys())}"
                    )

                # Champs optionnels
                sprite_sheet_path = event_data_dict.get("sprite_sheet_path")
                if sprite_sheet_path is not None:
                    sprite_sheet_path = str(sprite_sheet_path)
                    # Vérifier que le fichier existe si le chemin est absolu
                    sprite_path = Path(sprite_sheet_path)
                    if sprite_path.is_absolute() and not sprite_path.exists():
                        raise FileNotFoundError(
                            f"Sprite sheet introuvable pour l'événement '{identifier}': {sprite_sheet_path}"
                        )

                fade_in_duration = float(event_data_dict.get("fade_in_duration", 1.0))
                if fade_in_duration <= 0:
                    raise ValueError(
                        f"fade_in_duration doit être positif pour l'événement '{identifier}'"
                    )

                # Champs optionnels pour l'animation et la direction
                animation_row = event_data_dict.get("animation_row")
                if animation_row is not None:
                    animation_row = int(animation_row)
                    if animation_row < 0:
                        raise ValueError(
                            f"animation_row doit être >= 0 pour l'événement '{identifier}'"
                        )

                animation_start = event_data_dict.get("animation_start")
                if animation_start is not None:
                    animation_start = int(animation_start)
                    if animation_start < 0:
                        raise ValueError(
                            f"animation_start doit être >= 0 pour l'événement '{identifier}'"
                        )

                direction = event_data_dict.get("direction")
                if direction is not None:
                    direction_str = str(direction)
                    if direction_str not in ("left", "right"):
                        raise ValueError(
                            f"direction doit être 'left' ou 'right' pour l'événement '{identifier}', "
                            f"reçu: '{direction_str}'"
                        )
                    direction: Literal["left", "right"] = direction_str  # type: ignore
                else:
                    direction = None

                npc_magic_move_config = NPCMagicMoveEventConfig(
                    npc_id=npc_id,
                    target_x=target_x,
                    target_y=target_y,
                    sprite_sheet_path=sprite_sheet_path,
                    fade_in_duration=fade_in_duration,
                    animation_row=animation_row,
                    animation_start=animation_start,
                    direction=direction,
                )

                event_config = EventTriggerConfig(
                    identifier=identifier,
                    trigger_x=trigger_x,
                    event_type=event_type,
                    event_data=npc_magic_move_config,
                    triggered=False,
                    repeatable=repeatable,
                )

                events.append(event_config)
            elif event_type_str == "sprite_hide":
                # Champs obligatoires pour sprite_hide
                if "sprite_tag" not in event_data_dict:
                    raise ValueError(
                        f"Champ 'sprite_tag' manquant dans event_data pour l'événement '{identifier}'"
                    )

                sprite_tag = str(event_data_dict["sprite_tag"])

                # Vérifier que le tag existe
                if sprite_tag not in self.layers_by_tag:
                    raise ValueError(
                        f"Tag '{sprite_tag}' introuvable pour l'événement '{identifier}'. "
                        f"Tags disponibles: {list(self.layers_by_tag.keys())}"
                    )

                # Champs optionnels
                fade_duration = float(event_data_dict.get("fade_duration", 1.0))
                if fade_duration <= 0:
                    raise ValueError(
                        f"fade_duration doit être positif pour l'événement '{identifier}'"
                    )

                remove_collisions = event_data_dict.get("remove_collisions", True)
                if not isinstance(remove_collisions, bool):
                    raise ValueError(
                        f"remove_collisions doit être un booléen pour l'événement '{identifier}'"
                    )

                sprite_hide_config = SpriteHideEventConfig(
                    sprite_tag=sprite_tag,
                    fade_duration=fade_duration,
                    remove_collisions=remove_collisions,
                )

                event_config = EventTriggerConfig(
                    identifier=identifier,
                    trigger_x=trigger_x,
                    event_type=event_type,
                    event_data=sprite_hide_config,
                    triggered=False,
                    repeatable=repeatable,
                )

                events.append(event_config)
            elif event_type_str == "sprite_show":
                # Champs obligatoires pour sprite_show
                if "sprite_tag" not in event_data_dict:
                    raise ValueError(
                        f"Champ 'sprite_tag' manquant dans event_data pour l'événement '{identifier}'"
                    )

                sprite_tag = str(event_data_dict["sprite_tag"])

                # Vérifier que le tag existe
                if sprite_tag not in self.layers_by_tag:
                    raise ValueError(
                        f"Tag '{sprite_tag}' introuvable pour l'événement '{identifier}'. "
                        f"Tags disponibles: {list(self.layers_by_tag.keys())}"
                    )

                # Champs optionnels
                fade_duration = float(event_data_dict.get("fade_duration", 1.0))
                if fade_duration <= 0:
                    raise ValueError(
                        f"fade_duration doit être positif pour l'événement '{identifier}'"
                    )

                restore_collisions = event_data_dict.get("restore_collisions", True)
                if not isinstance(restore_collisions, bool):
                    raise ValueError(
                        f"restore_collisions doit être un booléen pour l'événement '{identifier}'"
                    )

                sprite_show_config = SpriteShowEventConfig(
                    sprite_tag=sprite_tag,
                    fade_duration=fade_duration,
                    restore_collisions=restore_collisions,
                )

                event_config = EventTriggerConfig(
                    identifier=identifier,
                    trigger_x=trigger_x,
                    event_type=event_type,
                    event_data=sprite_show_config,
                    triggered=False,
                    repeatable=repeatable,
                )

                events.append(event_config)
            elif event_type_str == "sprite_move":
                # Champs obligatoires pour sprite_move
                required_sprite_move_fields = ["sprite_tag", "move_x", "move_y"]
                for field in required_sprite_move_fields:
                    if field not in event_data_dict:
                        raise ValueError(
                            f"Champ '{field}' manquant dans event_data pour l'événement '{identifier}'"
                        )

                sprite_tag = str(event_data_dict["sprite_tag"])

                # Vérifier que le tag existe
                if sprite_tag not in self.layers_by_tag:
                    raise ValueError(
                        f"Tag '{sprite_tag}' introuvable pour l'événement '{identifier}'. "
                        f"Tags disponibles: {list(self.layers_by_tag.keys())}"
                    )

                # Vérifier que collision_system est fourni
                if self.collision_system is None:
                    raise ValueError(
                        f"collision_system est requis pour les événements sprite_move (événement '{identifier}')"
                    )

                move_x = float(event_data_dict["move_x"]) * self._design_scale_x
                move_y = float(event_data_dict["move_y"]) * self._design_scale_y

                # Champs optionnels
                move_speed = float(event_data_dict.get("move_speed", 250.0))
                if move_speed <= 0:
                    raise ValueError(
                        f"move_speed doit être positif pour l'événement '{identifier}'"
                    )
                move_speed *= self._design_scale_x  # Vitesse en pixels par seconde dans le repère de rendu

                sprite_move_config = SpriteMoveEventConfig(
                    sprite_tag=sprite_tag,
                    move_x=move_x,
                    move_y=move_y,
                    move_speed=move_speed,
                )

                event_config = EventTriggerConfig(
                    identifier=identifier,
                    trigger_x=trigger_x,
                    event_type=event_type,
                    event_data=sprite_move_config,
                    triggered=False,
                    repeatable=repeatable,
                )

                events.append(event_config)
            elif event_type_str == "sprite_rotate":
                # Champs obligatoires pour sprite_rotate
                required_sprite_rotate_fields = ["sprite_tag", "rotation_speed", "duration"]
                for field in required_sprite_rotate_fields:
                    if field not in event_data_dict:
                        raise ValueError(
                            f"Champ '{field}' manquant dans event_data pour l'événement '{identifier}'"
                        )

                sprite_tag = str(event_data_dict["sprite_tag"])

                # Vérifier que le tag existe
                if sprite_tag not in self.layers_by_tag:
                    raise ValueError(
                        f"Tag '{sprite_tag}' introuvable pour l'événement '{identifier}'. "
                        f"Tags disponibles: {list(self.layers_by_tag.keys())}"
                    )

                rotation_speed = float(event_data_dict["rotation_speed"])
                duration = float(event_data_dict["duration"])
                if duration <= 0:
                    raise ValueError(
                        f"duration doit être positif pour l'événement '{identifier}'"
                    )

                sprite_rotate_config = SpriteRotateEventConfig(
                    sprite_tag=sprite_tag,
                    rotation_speed=rotation_speed,
                    duration=duration,
                )

                event_config = EventTriggerConfig(
                    identifier=identifier,
                    trigger_x=trigger_x,
                    event_type=event_type,
                    event_data=sprite_rotate_config,
                    triggered=False,
                    repeatable=repeatable,
                )

                events.append(event_config)
            elif event_type_str == "sprite_move_perpetual":
                # Champs obligatoires pour sprite_move_perpetual
                required_sprite_move_perpetual_fields = ["sprite_tag", "move_x", "move_y"]
                for field in required_sprite_move_perpetual_fields:
                    if field not in event_data_dict:
                        raise ValueError(
                            f"Champ '{field}' manquant dans event_data pour l'événement '{identifier}'"
                        )

                sprite_tag = str(event_data_dict["sprite_tag"])

                # Vérifier que le tag existe
                if sprite_tag not in self.layers_by_tag:
                    raise ValueError(
                        f"Tag '{sprite_tag}' introuvable pour l'événement '{identifier}'. "
                        f"Tags disponibles: {list(self.layers_by_tag.keys())}"
                    )

                # Vérifier que collision_system est fourni
                if self.collision_system is None:
                    raise ValueError(
                        f"collision_system est requis pour les événements sprite_move_perpetual (événement '{identifier}')"
                    )

                move_x = float(event_data_dict["move_x"]) * self._design_scale_x
                move_y = float(event_data_dict["move_y"]) * self._design_scale_y

                # Champs optionnels
                move_speed = float(event_data_dict.get("move_speed", 250.0))
                if move_speed <= 0:
                    raise ValueError(
                        f"move_speed doit être positif pour l'événement '{identifier}' (mouvement perpétuel)"
                    )
                move_speed *= self._design_scale_x  # Vitesse en pixels par seconde dans le repère de rendu

                sprite_move_perpetual_config = SpriteMovePerpetualEventConfig(
                    sprite_tag=sprite_tag,
                    move_x=move_x,
                    move_y=move_y,
                    move_speed=move_speed,
                )

                event_config = EventTriggerConfig(
                    identifier=identifier,
                    trigger_x=trigger_x,
                    event_type=event_type,
                    event_data=sprite_move_perpetual_config,
                    triggered=False,
                    repeatable=repeatable,
                )

                events.append(event_config)
            elif event_type_str == "inventory_add":
                # Champs obligatoires pour inventory_add
                if "item_id" not in event_data_dict:
                    raise ValueError(
                        f"Champ 'item_id' manquant dans event_data pour l'événement '{identifier}'"
                    )

                item_id = str(event_data_dict["item_id"])
                quantity = int(event_data_dict.get("quantity", 1))

                if quantity <= 0:
                    raise ValueError(
                        f"quantity doit être > 0 pour l'événement '{identifier}', reçu: {quantity}"
                    )

                inventory_add_config = InventoryAddEventConfig(
                    item_id=item_id,
                    quantity=quantity,
                )

                event_config = EventTriggerConfig(
                    identifier=identifier,
                    trigger_x=trigger_x,
                    event_type=event_type,
                    event_data=inventory_add_config,
                    triggered=False,
                    repeatable=repeatable,
                )

                events.append(event_config)
            elif event_type_str == "inventory_remove":
                # Champs obligatoires pour inventory_remove
                if "item_id" not in event_data_dict:
                    raise ValueError(
                        f"Champ 'item_id' manquant dans event_data pour l'événement '{identifier}'"
                    )

                item_id = str(event_data_dict["item_id"])
                quantity = int(event_data_dict.get("quantity", 1))

                if quantity <= 0:
                    raise ValueError(
                        f"quantity doit être > 0 pour l'événement '{identifier}', reçu: {quantity}"
                    )

                inventory_remove_config = InventoryRemoveEventConfig(
                    item_id=item_id,
                    quantity=quantity,
                )

                event_config = EventTriggerConfig(
                    identifier=identifier,
                    trigger_x=trigger_x,
                    event_type=event_type,
                    event_data=inventory_remove_config,
                    triggered=False,
                    repeatable=repeatable,
                )

                events.append(event_config)
            elif event_type_str == "level_up":
                # Aucun champ requis pour les événements de level up
                level_up_config = LevelUpEventConfig()

                event_config = EventTriggerConfig(
                    identifier=identifier,
                    trigger_x=trigger_x,
                    event_type=event_type,
                    event_data=level_up_config,
                    triggered=False,
                    repeatable=repeatable,
                )

                events.append(event_config)
            elif event_type_str == "screen_fade":
                # Champs optionnels pour screen_fade
                fade_in_duration = float(event_data_dict.get("fade_in_duration", 1.0))
                if fade_in_duration <= 0:
                    raise ValueError(
                        f"fade_in_duration doit être positif pour l'événement '{identifier}'"
                    )

                text_fade_in_duration = float(event_data_dict.get("text_fade_in_duration", 0.5))
                if text_fade_in_duration < 0:
                    raise ValueError(
                        f"text_fade_in_duration doit être positif ou nul pour l'événement '{identifier}'"
                    )

                text_display_duration = float(event_data_dict.get("text_display_duration", 1.0))
                if text_display_duration < 0:
                    raise ValueError(
                        f"text_display_duration doit être positif ou nul pour l'événement '{identifier}'"
                    )

                text_fade_out_duration = float(event_data_dict.get("text_fade_out_duration", 0.5))
                if text_fade_out_duration < 0:
                    raise ValueError(
                        f"text_fade_out_duration doit être positif ou nul pour l'événement '{identifier}'"
                    )

                fade_out_duration = float(event_data_dict.get("fade_out_duration", 1.0))
                if fade_out_duration <= 0:
                    raise ValueError(
                        f"fade_out_duration doit être positif pour l'événement '{identifier}'"
                    )

                text = event_data_dict.get("text")
                if text is not None:
                    text = str(text)

                screen_fade_config = ScreenFadeEventConfig(
                    fade_in_duration=fade_in_duration,
                    text_fade_in_duration=text_fade_in_duration,
                    text_display_duration=text_display_duration,
                    text_fade_out_duration=text_fade_out_duration,
                    fade_out_duration=fade_out_duration,
                    text=text,
                )

                event_config = EventTriggerConfig(
                    identifier=identifier,
                    trigger_x=trigger_x,
                    event_type=event_type,
                    event_data=screen_fade_config,
                    triggered=False,
                    repeatable=repeatable,
                )

                events.append(event_config)
            elif event_type_str == "particle_effect":
                # Champs obligatoires pour particle_effect
                if "effect_type" not in event_data_dict:
                        raise ValueError(
                        f"Champ 'effect_type' manquant dans event_data pour l'événement '{identifier}'"
                        )

                effect_type_str = str(event_data_dict["effect_type"])
                if effect_type_str not in ("explosion", "confetti", "flame_explosion", "rain", "smoke", "sparks"):
                    raise ValueError(
                        f"effect_type invalide '{effect_type_str}' pour l'événement '{identifier}'. "
                        "Types supportés: 'explosion', 'confetti', 'flame_explosion', 'rain', 'smoke', 'sparks'"
                    )
                effect_type: Literal["explosion", "confetti", "flame_explosion", "rain", "smoke", "sparks"] = effect_type_str  # type: ignore

                # Vérifier que particle_system est fourni (avertir seulement, ne pas lever d'erreur)
                if self.particle_system is None:
                    logger.warning(
                        f"L'instance ParticleSystem n'est pas fournie pour l'événement particle_effect '{identifier}'. "
                        f"L'événement sera ignoré lors de son déclenchement."
                    )
                    # Continuer le chargement même si particle_system n'est pas fourni
                    # L'événement sera simplement ignoré lors de son exécution

                # Vérifier la priorité : sprite_tag > spawn_area > x/y
                has_sprite_tag = "sprite_tag" in event_data_dict
                has_spawn_area = "spawn_area" in event_data_dict
                has_x_y = "x" in event_data_dict and "y" in event_data_dict
                
                # Vérifier qu'au moins une méthode de positionnement est spécifiée
                if not has_sprite_tag and not has_spawn_area and not has_x_y:
                    raise ValueError(
                        f"Pour l'événement '{identifier}': soit 'sprite_tag', soit 'spawn_area', "
                        f"soit 'x' et 'y' doivent être présents"
                    )
                
                # Avertir sur les conflits (priorité : sprite_tag > spawn_area > x/y)
                if has_sprite_tag and (has_spawn_area or has_x_y):
                    logger.warning(
                        f"Pour l'événement '{identifier}': 'sprite_tag' est spécifié. "
                        f"'spawn_area' et 'x'/'y' seront ignorés."
                    )
                elif has_spawn_area and has_x_y:
                    logger.warning(
                        f"Pour l'événement '{identifier}': 'spawn_area' et 'x'/'y' sont tous deux spécifiés. "
                        f"'spawn_area' sera utilisé et 'x'/'y' seront ignorés."
                    )

                # Charger spawn_area si présent
                spawn_area = None
                if has_spawn_area:
                    spawn_area_data = event_data_dict["spawn_area"]
                    if not isinstance(spawn_area_data, dict):
                        raise ValueError(
                            f"spawn_area doit être un dictionnaire pour l'événement '{identifier}'"
                        )
                    required_spawn_area_keys = ["x_min", "x_max", "y_min", "y_max"]
                    for key in required_spawn_area_keys:
                        if key not in spawn_area_data:
                            raise ValueError(
                                f"spawn_area doit contenir la clé '{key}' pour l'événement '{identifier}'"
                    )
                    try:
                        x_min = float(spawn_area_data["x_min"])
                        x_max = float(spawn_area_data["x_max"])
                        y_min = float(spawn_area_data["y_min"])
                        y_max = float(spawn_area_data["y_max"])
                        if x_min >= x_max:
                            raise ValueError(
                                f"spawn_area: x_min ({x_min}) doit être < x_max ({x_max}) pour l'événement '{identifier}'"
                            )
                        if y_min >= y_max:
                            raise ValueError(
                                f"spawn_area: y_min ({y_min}) doit être < y_max ({y_max}) pour l'événement '{identifier}'"
                            )
                        spawn_area = {
                            "x_min": x_min,
                            "x_max": x_max,
                            "y_min": y_min,
                            "y_max": y_max,
                        }
                    except (ValueError, TypeError) as e:
                        raise ValueError(
                            f"spawn_area invalide pour l'événement '{identifier}': {e}"
                        ) from e

                # Charger x et y si présents (seront ignorés si spawn_area est présent)
                x = None
                y = None
                if has_x_y:
                    try:
                        x = float(event_data_dict["x"])
                        y = float(event_data_dict["y"])
                    except (ValueError, TypeError) as e:
                        raise ValueError(
                            f"x ou y invalide pour l'événement '{identifier}': {e}"
                        ) from e

                # Champs optionnels
                count = event_data_dict.get("count")
                if count is not None:
                    count = int(count)
                    if count <= 0:
                        raise ValueError(
                            f"count doit être > 0 pour l'événement '{identifier}', reçu: {count}"
                        )

                speed = event_data_dict.get("speed")
                if speed is not None:
                    speed = float(speed)
                    if speed <= 0:
                        raise ValueError(
                            f"speed doit être positif pour l'événement '{identifier}'"
                        )
                    # Note: La vitesse sera convertie lors de l'exécution si nécessaire

                lifetime = event_data_dict.get("lifetime")
                if lifetime is not None:
                    lifetime = float(lifetime)
                    if lifetime <= 0:
                        raise ValueError(
                            f"lifetime doit être positif pour l'événement '{identifier}'"
                        )

                size = event_data_dict.get("size")
                if size is not None:
                    size = int(size)
                    if size <= 0:
                        raise ValueError(
                            f"size doit être > 0 pour l'événement '{identifier}', reçu: {size}"
                        )

                color = None
                if "color" in event_data_dict:
                    color_data = event_data_dict["color"]
                    if color_data is not None:
                        if not isinstance(color_data, list) or len(color_data) != 3:
                            raise ValueError(
                                f"color doit être un tableau de 3 entiers [r, g, b] pour l'événement '{identifier}'"
                            )
                        try:
                            r = int(color_data[0])
                            g = int(color_data[1])
                            b = int(color_data[2])
                            if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
                                raise ValueError(
                                    f"Les valeurs de couleur doivent être entre 0 et 255 pour l'événement '{identifier}'"
                                )
                            color = (r, g, b)
                        except (ValueError, TypeError) as e:
                            raise ValueError(
                                f"color invalide pour l'événement '{identifier}': {e}"
                            ) from e

                colors = None
                if "colors" in event_data_dict:
                    colors_data = event_data_dict["colors"]
                    if colors_data is not None:
                        if not isinstance(colors_data, list):
                            raise ValueError(
                                f"colors doit être un tableau de tableaux de 3 entiers pour l'événement '{identifier}'"
                            )
                        if len(colors_data) == 0:
                            raise ValueError(
                                f"colors ne doit pas être vide pour l'événement '{identifier}'"
                            )
                        try:
                            colors_list: List[Tuple[int, int, int]] = []
                            for i, color_item in enumerate(colors_data):
                                if not isinstance(color_item, list) or len(color_item) != 3:
                                    raise ValueError(
                                        f"colors[{i}] doit être un tableau de 3 entiers [r, g, b] pour l'événement '{identifier}'"
                                    )
                                r = int(color_item[0])
                                g = int(color_item[1])
                                b = int(color_item[2])
                                if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
                                    raise ValueError(
                                        f"Les valeurs de couleur dans colors[{i}] doivent être entre 0 et 255 pour l'événement '{identifier}'"
                                    )
                                colors_list.append((r, g, b))
                            colors = colors_list
                        except (ValueError, TypeError) as e:
                            raise ValueError(
                                f"colors invalide pour l'événement '{identifier}': {e}"
                            ) from e

                color_variation = None
                if "color_variation" in event_data_dict:
                    color_variation_data = event_data_dict["color_variation"]
                    if color_variation_data is not None:
                        try:
                            color_variation = float(color_variation_data)
                            if not (0.0 <= color_variation <= 1.0):
                                raise ValueError(
                                    f"color_variation doit être entre 0.0 et 1.0 pour l'événement '{identifier}', reçu: {color_variation}"
                                )
                        except (ValueError, TypeError) as e:
                            raise ValueError(
                                f"color_variation invalide pour l'événement '{identifier}': {e}"
                            ) from e

                generation_duration = None
                if "generation_duration" in event_data_dict:
                    generation_duration_data = event_data_dict["generation_duration"]
                    if generation_duration_data is not None:
                        try:
                            generation_duration = float(generation_duration_data)
                            if generation_duration <= 0:
                                raise ValueError(
                                    f"generation_duration doit être > 0 pour l'événement '{identifier}', reçu: {generation_duration}"
                                )
                        except (ValueError, TypeError) as e:
                            raise ValueError(
                                f"generation_duration invalide pour l'événement '{identifier}': {e}"
                            ) from e

                # Charger direction_angle si présent
                direction_angle = None
                if "direction_angle" in event_data_dict:
                    direction_angle_data = event_data_dict["direction_angle"]
                    if direction_angle_data is not None:
                        try:
                            direction_angle = float(direction_angle_data)
                        except (ValueError, TypeError) as e:
                            raise ValueError(
                                f"direction_angle invalide pour l'événement '{identifier}': {e}"
                            ) from e

                # Charger direction_spread si présent
                direction_spread = None
                if "direction_spread" in event_data_dict:
                    direction_spread_data = event_data_dict["direction_spread"]
                    if direction_spread_data is not None:
                        try:
                            direction_spread = float(direction_spread_data)
                            if direction_spread < 0:
                                raise ValueError(
                                    f"direction_spread doit être >= 0 pour l'événement '{identifier}', reçu: {direction_spread}"
                                )
                        except (ValueError, TypeError) as e:
                            raise ValueError(
                                f"direction_spread invalide pour l'événement '{identifier}': {e}"
                            ) from e

                # Charger sprite_tag si présent
                sprite_tag = None
                if has_sprite_tag:
                    sprite_tag_data = event_data_dict.get("sprite_tag")
                    if sprite_tag_data is not None:
                        sprite_tag = str(sprite_tag_data)
                        if not sprite_tag:
                            raise ValueError(
                                f"sprite_tag ne doit pas être vide pour l'événement '{identifier}'"
                            )
                        # Vérifier que le tag existe dans layers_by_tag
                        if sprite_tag not in self.layers_by_tag:
                            raise ValueError(
                                f"Tag '{sprite_tag}' introuvable pour l'événement '{identifier}'. "
                                f"Tags disponibles: {list(self.layers_by_tag.keys())}"
                            )

                # Charger spawn_edge si présent
                spawn_edge = None
                if "spawn_edge" in event_data_dict:
                    spawn_edge_data = event_data_dict["spawn_edge"]
                    if spawn_edge_data is not None:
                        spawn_edge_str = str(spawn_edge_data)
                        if spawn_edge_str not in ("top", "bottom", "left", "right"):
                            raise ValueError(
                                f"spawn_edge doit être 'top', 'bottom', 'left' ou 'right' pour l'événement '{identifier}', "
                                f"reçu: '{spawn_edge_str}'"
                            )
                        spawn_edge: Literal["top", "bottom", "left", "right"] = spawn_edge_str  # type: ignore
                        # Vérifier que sprite_tag est également spécifié
                        if sprite_tag is None:
                            logger.warning(
                                f"Pour l'événement '{identifier}': 'spawn_edge' est spécifié mais 'sprite_tag' n'est pas présent. "
                                f"'spawn_edge' sera ignoré."
                            )
                            spawn_edge = None

                particle_effect_config = ParticleEffectEventConfig(
                    effect_type=effect_type,
                    x=x,
                    y=y,
                    spawn_area=spawn_area,
                    sprite_tag=sprite_tag,
                    spawn_edge=spawn_edge,
                    count=count,
                    speed=speed,
                    lifetime=lifetime,
                    size=size,
                    color=color,
                    colors=colors,
                    color_variation=color_variation,
                    generation_duration=generation_duration,
                    direction_angle=direction_angle,
                    direction_spread=direction_spread,
                )

                event_config = EventTriggerConfig(
                    identifier=identifier,
                    trigger_x=trigger_x,
                    event_type=event_type,
                    event_data=particle_effect_config,
                    triggered=False,
                    repeatable=repeatable,
                )

                events.append(event_config)
            elif event_type_str == "camera_zoom":
                if "zoom_percent" not in event_data_dict:
                    raise ValueError(
                        f"Champ 'zoom_percent' manquant dans event_data pour l'événement '{identifier}'"
                    )

                zoom_percent = float(event_data_dict["zoom_percent"])
                if zoom_percent <= 0:
                    raise ValueError(
                        f"zoom_percent doit être > 0 pour l'événement '{identifier}', reçu: {zoom_percent}"
                    )

                duration = float(event_data_dict.get("duration", 0.8))
                if duration < 0:
                    raise ValueError(
                        f"duration doit être >= 0 pour l'événement '{identifier}', reçu: {duration}"
                    )

                bottom_margin = float(event_data_dict.get("bottom_margin", 50.0))
                if bottom_margin < 0:
                    raise ValueError(
                        f"bottom_margin doit être >= 0 pour l'événement '{identifier}', reçu: {bottom_margin}"
                    )

                keep_bubbles_visible = event_data_dict.get("keep_bubbles_visible", True)
                if not isinstance(keep_bubbles_visible, bool):
                    raise ValueError(
                        f"keep_bubbles_visible doit être un booléen pour l'événement '{identifier}', "
                        f"reçu: {type(keep_bubbles_visible).__name__}"
                    )

                camera_zoom_config = CameraZoomEventConfig(
                    zoom_percent=zoom_percent,
                    duration=duration,
                    bottom_margin=bottom_margin,
                    keep_bubbles_visible=keep_bubbles_visible,
                )

                event_config = EventTriggerConfig(
                    identifier=identifier,
                    trigger_x=trigger_x,
                    event_type=event_type,
                    event_data=camera_zoom_config,
                    triggered=False,
                    repeatable=repeatable,
                )

                events.append(event_config)
            elif event_type_str == "camera_zoom_sprite":
                if "sprite_tag" not in event_data_dict:
                    raise ValueError(
                        f"Champ 'sprite_tag' manquant dans event_data pour l'événement '{identifier}'"
                    )
                if "zoom_percent" not in event_data_dict:
                    raise ValueError(
                        f"Champ 'zoom_percent' manquant dans event_data pour l'événement '{identifier}'"
                    )

                sprite_tag = str(event_data_dict["sprite_tag"])
                if not sprite_tag:
                    raise ValueError(
                        f"sprite_tag ne doit pas être vide pour l'événement '{identifier}'"
                    )
                # Vérifier que le tag existe dans layers_by_tag
                if sprite_tag not in self.layers_by_tag:
                    raise ValueError(
                        f"Tag '{sprite_tag}' introuvable pour l'événement '{identifier}'. "
                        f"Tags disponibles: {list(self.layers_by_tag.keys())}"
                    )

                zoom_percent = float(event_data_dict["zoom_percent"])
                if zoom_percent <= 0:
                    raise ValueError(
                        f"zoom_percent doit être > 0 pour l'événement '{identifier}', reçu: {zoom_percent}"
                    )

                offset_x = float(event_data_dict.get("offset_x", 0.0))
                offset_y = float(event_data_dict.get("offset_y", 0.0))

                duration = float(event_data_dict.get("duration", 0.8))
                if duration < 0:
                    raise ValueError(
                        f"duration doit être >= 0 pour l'événement '{identifier}', reçu: {duration}"
                    )

                keep_bubbles_visible = event_data_dict.get("keep_bubbles_visible", True)
                if not isinstance(keep_bubbles_visible, bool):
                    raise ValueError(
                        f"keep_bubbles_visible doit être un booléen pour l'événement '{identifier}', reçu: {keep_bubbles_visible}"
                    )

                camera_zoom_sprite_config = CameraZoomSpriteEventConfig(
                    sprite_tag=sprite_tag,
                    zoom_percent=zoom_percent,
                    offset_x=offset_x,
                    offset_y=offset_y,
                    duration=duration,
                    keep_bubbles_visible=keep_bubbles_visible,
                )

                event_config = EventTriggerConfig(
                    identifier=identifier,
                    trigger_x=trigger_x,
                    event_type=event_type,
                    event_data=camera_zoom_sprite_config,
                    triggered=False,
                    repeatable=repeatable,
                )

                events.append(event_config)
            elif event_type_str == "camera_zoom_reset":
                duration = float(event_data_dict.get("duration", 0.8))
                if duration < 0:
                    raise ValueError(
                        f"duration doit être >= 0 pour l'événement '{identifier}', reçu: {duration}"
                    )

                camera_zoom_reset_config = CameraZoomResetEventConfig(duration=duration)

                event_config = EventTriggerConfig(
                    identifier=identifier,
                    trigger_x=trigger_x,
                    event_type=event_type,
                    event_data=camera_zoom_reset_config,
                    triggered=False,
                    repeatable=repeatable,
                )

                events.append(event_config)

        self.events = events
        logger.info("EventTriggerSystem: %d événements chargés depuis %s", len(events), events_path)

    def update(self, dt: float) -> None:
        """Met à jour le système et exécute les événements déclenchés.
        
        Gère notamment les animations de fade out pour les événements de type `sprite_hide`
        et les animations de fade in pour les événements de type `sprite_show`.

        Args:
            dt: Delta time en secondes
        """
        # Mettre à jour les animations de fade out en cours
        layers_to_remove_fade_out: List[Layer] = []
        for layer, (fade_timer, fade_duration, initial_alpha) in list(self._fade_out_timers.items()):
            fade_timer -= dt
            if fade_timer <= 0:
                # Le fade out est terminé
                layer.alpha = 0
                layer.is_hidden = True
                layers_to_remove_fade_out.append(layer)
                
                # Supprimer les collisions si nécessaire
                if self.collision_system:
                    # Trouver la configuration de l'événement qui a déclenché ce fade out
                    # On cherche dans les événements déclenchés pour trouver remove_collisions
                    for event in self.events:
                        if (event.triggered and 
                            event.event_type == "sprite_hide" and
                            isinstance(event.event_data, SpriteHideEventConfig)):
                            hide_config = event.event_data
                            if layer in self.layers_by_tag.get(hide_config.sprite_tag, []):
                                if hide_config.remove_collisions:
                                    self.collision_system.remove_layer_collisions(layer.name)
                                    self.collision_system.remove_layer_from_collisions(layer)
                                break
            else:
                # Calculer l'opacité proportionnellement
                # timer commence à fade_duration et diminue jusqu'à 0
                opacity = int(initial_alpha * (fade_timer / fade_duration))
                layer.alpha = max(0, opacity)
                # Mettre à jour le timer dans le dictionnaire
                self._fade_out_timers[layer] = (fade_timer, fade_duration, initial_alpha)
        
        # Retirer les layers terminées du dictionnaire
        for layer in layers_to_remove_fade_out:
            del self._fade_out_timers[layer]

        # Mettre à jour les animations de fade in en cours
        layers_to_remove_fade_in: List[Layer] = []
        for layer, (fade_timer, fade_duration, initial_alpha) in list(self._fade_in_timers.items()):
            fade_timer -= dt
            if fade_timer <= 0:
                # Le fade in est terminé
                layer.alpha = 255
                layer.is_hidden = False
                layers_to_remove_fade_in.append(layer)
                
                # Restaurer les collisions si nécessaire
                if self.collision_system:
                    # Trouver la configuration de l'événement qui a déclenché ce fade in
                    for event in self.events:
                        if (event.triggered and 
                            event.event_type == "sprite_show" and
                            isinstance(event.event_data, SpriteShowEventConfig)):
                            show_config = event.event_data
                            if layer in self.layers_by_tag.get(show_config.sprite_tag, []):
                                if show_config.restore_collisions:
                                    self.collision_system.restore_layer_collisions(layer)
                                    self.collision_system.add_layer_to_collisions(layer)
                                break
            else:
                # Calculer l'opacité proportionnellement
                # timer commence à fade_duration et diminue jusqu'à 0
                # opacity = initial_alpha + (255 - initial_alpha) * (1.0 - (timer / fade_duration))
                progress = 1.0 - (fade_timer / fade_duration)
                opacity = int(initial_alpha + (255 - initial_alpha) * progress)
                layer.alpha = min(255, opacity)
                # Mettre à jour le timer dans le dictionnaire
                self._fade_in_timers[layer] = (fade_timer, fade_duration, initial_alpha)
        
        # Retirer les layers terminées du dictionnaire
        for layer in layers_to_remove_fade_in:
            del self._fade_in_timers[layer]

        # Mettre à jour les animations de fade in des NPCs en cours
        npcs_to_remove_fade_in: List[NPC] = []
        for npc, (fade_timer, fade_duration) in list(self._npc_fade_in_timers.items()):
            fade_timer -= dt
            if fade_timer <= 0:
                # Le fade in est terminé
                npc.set_alpha(255)
                npcs_to_remove_fade_in.append(npc)
                
                # Réactiver la gravité et les collisions
                npc.set_gravity_enabled(True)
                npc.set_collisions_enabled(True)
                
                # Réinitialiser les animations temporaires de téléportation magique
                npc._magic_move_animation_row = None
                npc._magic_move_animation_start = None
                
                logger.debug(
                    "Fade in terminé pour NPC '%s', gravité et collisions réactivées",
                    npc.id
                )
            else:
                # Calculer l'opacité proportionnellement
                # timer commence à fade_duration et diminue jusqu'à 0
                # opacity = 255 * (1.0 - (timer / fade_duration))
                progress = 1.0 - (fade_timer / fade_duration)
                opacity = int(255 * progress)
                npc.set_alpha(opacity)
                # Mettre à jour le timer dans le dictionnaire
                self._npc_fade_in_timers[npc] = (fade_timer, fade_duration)
        
        # Retirer les NPCs terminés du dictionnaire
        for npc in npcs_to_remove_fade_in:
            del self._npc_fade_in_timers[npc]

        # Mettre à jour les mouvements de sprites en cours
        tasks_to_remove: List[Layer] = []
        for layer, task in list(self._sprite_movement_tasks.items()):
            # Calculer la distance à parcourir cette frame
            delta_distance = min(task.move_speed * dt, task.remaining_distance)
            
            if delta_distance > 0:
                # Calculer les deltas X et Y proportionnels
                delta_x = task.direction_x * delta_distance
                delta_y = task.direction_y * delta_distance
                
                # Appliquer le déplacement
                layer.world_x_offset += delta_x
                layer.world_y_offset += delta_y
                
                # Mettre à jour la distance restante
                task.remaining_distance -= delta_distance
                
                # Notifier le système de collisions
                if self.collision_system:
                    self.collision_system.on_layer_translated(layer, delta_x, delta_y)
                
                # Si le mouvement est terminé, forcer la position finale exacte
                if task.remaining_distance <= 1.0:  # Tolérance de 1 pixel
                    layer.world_x_offset = task.target_x
                    layer.world_y_offset = task.target_y
                    tasks_to_remove.append(layer)
                    logger.debug("Mouvement de sprite terminé pour layer '%s'", layer.name)
            else:
                # Mouvement terminé
                tasks_to_remove.append(layer)
        
        # Retirer les tâches terminées
        for layer in tasks_to_remove:
            if layer in self._sprite_movement_tasks:
                del self._sprite_movement_tasks[layer]
                # Relâcher tous les passagers restants
                if self.collision_system:
                    self.collision_system.release_passengers_from_layer(layer)

        # Mettre à jour les mouvements perpétuels de sprites en cours
        for layer, task in list(self._sprite_perpetual_movement_tasks.items()):
            # Calculer la distance à parcourir cette frame
            delta_distance = min(task.move_speed * dt, task.remaining_distance)
            
            if delta_distance > 0:
                # Calculer les deltas X et Y proportionnels
                delta_x = task.direction_x * delta_distance
                delta_y = task.direction_y * delta_distance
                
                # Appliquer le déplacement
                layer.world_x_offset += delta_x
                layer.world_y_offset += delta_y
                
                # Mettre à jour la distance restante
                task.remaining_distance -= delta_distance
                
                # Notifier le système de collisions
                if self.collision_system:
                    self.collision_system.on_layer_translated(layer, delta_x, delta_y)
                
                # Si on a atteint la destination (avec tolérance de 1 pixel)
                if task.remaining_distance <= 1.0:
                    # Forcer la position exacte
                    if task.going_to_target:
                        # On était en train d'aller vers la destination, on l'a atteinte
                        layer.world_x_offset = task.target_x
                        layer.world_y_offset = task.target_y
                        # Inverser la direction pour revenir au départ
                        task.going_to_target = False
                        task.remaining_distance = math.sqrt(
                            (task.target_x - task.start_x) ** 2 + 
                            (task.target_y - task.start_y) ** 2
                        )
                        # Inverser la direction
                        task.direction_x = -task.direction_x
                        task.direction_y = -task.direction_y
                        logger.debug(
                            "Mouvement perpétuel: layer '%s' a atteint la destination, retour au départ",
                            layer.name
                        )
                    else:
                        # On était en train de revenir au départ, on l'a atteint
                        layer.world_x_offset = task.start_x
                        layer.world_y_offset = task.start_y
                        # Inverser la direction pour retourner vers la destination
                        task.going_to_target = True
                        task.remaining_distance = math.sqrt(
                            (task.target_x - task.start_x) ** 2 + 
                            (task.target_y - task.start_y) ** 2
                        )
                        # Inverser la direction
                        task.direction_x = -task.direction_x
                        task.direction_y = -task.direction_y
                        logger.debug(
                            "Mouvement perpétuel: layer '%s' a atteint le départ, retour vers la destination",
                            layer.name
                        )

        # Mettre à jour les tâches de rotation en cours
        layers_to_remove_rotation: List[Layer] = []
        for layer, task in list(self._sprite_rotation_tasks.items()):
            # Incrémenter le temps écoulé
            task.elapsed_time += dt
            
            # Calculer l'angle de rotation actuel
            # L'angle augmente progressivement : initial_angle + rotation_speed * elapsed_time
            current_angle = task.initial_angle + (task.rotation_speed * task.elapsed_time)
            # Normaliser l'angle entre 0 et 360 degrés
            layer.rotation_angle = current_angle % 360.0
            
            # Vérifier si la durée est écoulée
            if task.elapsed_time >= task.duration:
                # La rotation est terminée, conserver l'angle final
                layers_to_remove_rotation.append(layer)
                logger.debug(
                    "Rotation terminée: layer '%s' (angle final=%.2f degrés)",
                    layer.name, layer.rotation_angle
                )
        
        # Retirer les tâches terminées
        for layer in layers_to_remove_rotation:
            del self._sprite_rotation_tasks[layer]

        # Mettre à jour l'animation de fondu au noir de l'écran
        if self._screen_fade_phase != "none" and self._screen_fade_config is not None:
            self._screen_fade_timer -= dt
            
            if self._screen_fade_phase == "fade_in":
                if self._screen_fade_timer <= 0:
                    # Passer à la phase text_fade_in si un texte est configuré, sinon directement à fade_out
                    if self._screen_fade_config.text is not None:
                        self._screen_fade_phase = "text_fade_in"
                        self._screen_fade_timer = self._screen_fade_config.text_fade_in_duration
                        if self._screen_fade_timer <= 0:
                            # Si text_fade_in_duration est 0, passer directement à text_display
                            self._screen_fade_phase = "text_display"
                            self._screen_fade_timer = self._screen_fade_config.text_display_duration
                            if self._screen_fade_timer <= 0:
                                # Si text_display_duration est 0, passer directement à text_fade_out
                                self._screen_fade_phase = "text_fade_out"
                                self._screen_fade_timer = self._screen_fade_config.text_fade_out_duration
                                if self._screen_fade_timer <= 0:
                                    # Si text_fade_out_duration est 0, passer directement à fade_out
                                    self._screen_fade_phase = "fade_out"
                                    self._screen_fade_timer = self._screen_fade_config.fade_out_duration
                                    if self._screen_fade_timer <= 0:
                                        # Si fade_out_duration est aussi 0, terminer le fondu
                                        self._screen_fade_phase = "none"
                                        self._screen_fade_config = None
                                        self._screen_fade_timer = 0.0
                    else:
                        # Pas de texte, passer directement à fade_out
                        self._screen_fade_phase = "fade_out"
                        self._screen_fade_timer = self._screen_fade_config.fade_out_duration
                        if self._screen_fade_timer <= 0:
                            # Si fade_out_duration est aussi 0, terminer le fondu
                            self._screen_fade_phase = "none"
                            self._screen_fade_config = None
                            self._screen_fade_timer = 0.0
            elif self._screen_fade_phase == "text_fade_in":
                if self._screen_fade_timer <= 0:
                    # Passer à la phase text_display
                    self._screen_fade_phase = "text_display"
                    self._screen_fade_timer = self._screen_fade_config.text_display_duration
                    if self._screen_fade_timer <= 0:
                        # Si text_display_duration est 0, passer directement à text_fade_out
                        self._screen_fade_phase = "text_fade_out"
                        self._screen_fade_timer = self._screen_fade_config.text_fade_out_duration
                        if self._screen_fade_timer <= 0:
                            # Si text_fade_out_duration est 0, passer directement à fade_out
                            self._screen_fade_phase = "fade_out"
                            self._screen_fade_timer = self._screen_fade_config.fade_out_duration
                            if self._screen_fade_timer <= 0:
                                # Si fade_out_duration est aussi 0, terminer le fondu
                                self._screen_fade_phase = "none"
                                self._screen_fade_config = None
                                self._screen_fade_timer = 0.0
            elif self._screen_fade_phase == "text_display":
                if self._screen_fade_timer <= 0:
                    # Passer à la phase text_fade_out
                    self._screen_fade_phase = "text_fade_out"
                    self._screen_fade_timer = self._screen_fade_config.text_fade_out_duration
                    if self._screen_fade_timer <= 0:
                        # Si text_fade_out_duration est 0, passer directement à fade_out
                        self._screen_fade_phase = "fade_out"
                        self._screen_fade_timer = self._screen_fade_config.fade_out_duration
                        if self._screen_fade_timer <= 0:
                            # Si fade_out_duration est aussi 0, terminer le fondu
                            self._screen_fade_phase = "none"
                            self._screen_fade_config = None
                            self._screen_fade_timer = 0.0
            elif self._screen_fade_phase == "text_fade_out":
                if self._screen_fade_timer <= 0:
                    # Passer à la phase fade_out
                    self._screen_fade_phase = "fade_out"
                    self._screen_fade_timer = self._screen_fade_config.fade_out_duration
                    if self._screen_fade_timer <= 0:
                        # Si fade_out_duration est 0, terminer le fondu
                        self._screen_fade_phase = "none"
                        self._screen_fade_config = None
                        self._screen_fade_timer = 0.0
            elif self._screen_fade_phase == "fade_out":
                if self._screen_fade_timer <= 0:
                    # Le fondu est terminé
                    self._screen_fade_phase = "none"
                    self._screen_fade_config = None
                    self._screen_fade_timer = 0.0

        # Obtenir la position actuelle du joueur
        current_x = self.progress_tracker.current_x

        # Vérifier les déclencheurs basés sur la position (ignorer les événements sans trigger_x)
        for event in self.events:
            # Vérifier si l'événement peut être déclenché (pas encore déclenché OU répétable)
            can_trigger = (not event.triggered) or event.repeatable
            # Ne vérifier que les événements avec un trigger_x défini
            if can_trigger and event.trigger_x is not None and current_x >= event.trigger_x:
                self._execute_event(event)
                event.triggered = True  # Marquer comme déclenché (même si répétable, pour éviter les déclenchements multiples dans la même frame)
                logger.debug("Événement déclenché: %s (trigger_x=%.2f, current_x=%.2f)", event.identifier, event.trigger_x, current_x)

    def _execute_event(self, event: EventTriggerConfig) -> None:
        """Exécute un événement déclenché.

        Args:
            event: Configuration de l'événement à exécuter
        """
        if event.event_type == "npc_move":
            self._execute_npc_move(event.event_data)
        elif event.event_type == "npc_follow":
            self._execute_npc_follow(event.event_data)
        elif event.event_type == "npc_stop_follow":
            self._execute_npc_stop_follow(event.event_data)
        elif event.event_type == "npc_magic_move":
            self._execute_npc_magic_move(event.event_data)
        elif event.event_type == "sprite_hide":
            self._execute_sprite_hide(event.event_data)
        elif event.event_type == "sprite_show":
            self._execute_sprite_show(event.event_data)
        elif event.event_type == "sprite_move":
            self._execute_sprite_move(event.event_data)
        elif event.event_type == "sprite_move_perpetual":
            self._execute_sprite_move_perpetual(event.event_data)
        elif event.event_type == "sprite_rotate":
            self._execute_sprite_rotate(event.event_data)
        elif event.event_type == "inventory_add":
            self._execute_inventory_add(event.event_data)
        elif event.event_type == "inventory_remove":
            self._execute_inventory_remove(event.event_data)
        elif event.event_type == "level_up":
            self._execute_level_up(event.event_data)
        elif event.event_type == "screen_fade":
            self._execute_screen_fade(event.event_data)
        elif event.event_type == "particle_effect":
            self._execute_particle_effect(event.event_data)
        elif event.event_type == "camera_zoom":
            self._execute_camera_zoom(event.event_data)
        elif event.event_type == "camera_zoom_sprite":
            self._execute_camera_zoom_sprite(event.event_data)
        elif event.event_type == "camera_zoom_reset":
            self._execute_camera_zoom_reset(event.event_data)
        else:
            logger.warning("Type d'événement non supporté: %s", event.event_type)

    def _execute_camera_zoom(self, event_data: CameraZoomEventConfig) -> None:
        """Exécute un événement de zoom caméra (post-process)."""
        if self.camera_zoom is None:
            logger.warning(
                "CameraZoomController manquant: événement camera_zoom ignoré (zoom_percent=%.2f)",
                event_data.zoom_percent,
            )
            return

        try:
            self.camera_zoom.start_zoom(
                zoom_percent=event_data.zoom_percent,
                duration=event_data.duration,
                bottom_margin_design_px=event_data.bottom_margin,
                keep_bubbles_visible=event_data.keep_bubbles_visible,
            )
        except Exception as e:
            logger.warning("Erreur lors de l'exécution camera_zoom: %s", e)

    def _execute_camera_zoom_sprite(self, event_data: CameraZoomSpriteEventConfig) -> None:
        """Exécute un événement de zoom caméra sur un sprite (post-process)."""
        if self.camera_zoom is None:
            logger.warning(
                "CameraZoomController manquant: événement camera_zoom_sprite ignoré (sprite_tag=%s, zoom_percent=%.2f)",
                event_data.sprite_tag,
                event_data.zoom_percent,
            )
            return

        try:
            self.camera_zoom.start_zoom_sprite(
                sprite_tag=event_data.sprite_tag,
                zoom_percent=event_data.zoom_percent,
                offset_x_design_px=event_data.offset_x,
                offset_y_design_px=event_data.offset_y,
                duration=event_data.duration,
                keep_bubbles_visible=event_data.keep_bubbles_visible,
                layers_by_tag=self.layers_by_tag,
            )
            logger.info(
                "Zoom sur sprite activé: tag=%s, zoom=%.2f%%, offset=(%.2f, %.2f)",
                event_data.sprite_tag,
                event_data.zoom_percent,
                event_data.offset_x,
                event_data.offset_y,
            )
        except Exception as e:
            logger.warning("Erreur lors de l'exécution camera_zoom_sprite: %s", e)

    def _execute_camera_zoom_reset(self, event_data: CameraZoomResetEventConfig) -> None:
        """Exécute un événement de reset du zoom caméra (post-process)."""
        if self.camera_zoom is None:
            logger.warning("CameraZoomController manquant: événement camera_zoom_reset ignoré")
            return
        try:
            self.camera_zoom.reset_zoom(duration=event_data.duration)
        except Exception as e:
            logger.warning("Erreur lors de l'exécution camera_zoom_reset: %s", e)

    def _execute_npc_move(self, event_data: NPCMoveEventConfig) -> None:
        """Exécute un événement de déplacement de PNJ.

        Args:
            event_data: Configuration de l'événement de déplacement
        """
        npc = self.npcs.get(event_data.npc_id)
        if npc is None:
            logger.error("PNJ introuvable pour l'événement: %s", event_data.npc_id)
            return

        # Déclencher le déplacement
        npc.start_movement(
            target_x=event_data.target_x,
            speed=event_data.move_speed,
            direction=event_data.direction,
            animation_row=event_data.move_animation_row,
            animation_frames=event_data.move_animation_frames,
        )
        logger.info(
            "Déplacement de PNJ déclenché: %s vers x=%.2f (direction=%s, speed=%.2f)",
            event_data.npc_id,
            event_data.target_x,
            event_data.direction,
            event_data.move_speed,
        )

    def _execute_npc_follow(self, event_data: NPCFollowEventConfig) -> None:
        """Exécute un événement de suivi du personnage principal par un PNJ.
        
        Cette méthode appelle `npc.start_following_player()` pour activer le suivi
        automatique du personnage principal. Le PNJ se positionne automatiquement
        derrière le joueur (à droite si le joueur va à gauche, à gauche si le joueur
        va à droite) et maintient une distance constante.
        
        Args:
            event_data: Configuration de l'événement de suivi de PNJ
        
        Raises:
            ValueError: Si le PNJ avec l'ID spécifié n'existe pas ou si l'instance
                       `Player` n'est pas fournie au constructeur
        """
        npc = self.npcs.get(event_data.npc_id)
        if npc is None:
            logger.error("PNJ introuvable pour l'événement: %s", event_data.npc_id)
            raise ValueError(f"PNJ avec l'ID '{event_data.npc_id}' introuvable")
        
        if self.player is None:
            logger.error("Événement npc_follow ignoré : instance Player non fournie")
            raise ValueError("L'instance Player est requise pour les événements npc_follow")
        
        # Déclencher le suivi
        npc.start_following_player(
            player=self.player,
            follow_distance=event_data.follow_distance,
            follow_speed=event_data.follow_speed,
            animation_row=event_data.animation_row,
            animation_frames=event_data.animation_frames,
        )
        logger.info(
            "Suivi du joueur activé pour PNJ: %s (distance=%.2f, speed=%.2f)",
            event_data.npc_id,
            event_data.follow_distance,
            event_data.follow_speed,
        )

    def _execute_npc_stop_follow(self, event_data: NPCStopFollowEventConfig) -> None:
        """Exécute un événement d'arrêt du suivi du personnage principal par un PNJ.
        
        Cette méthode appelle `npc.stop_following_player()` pour arrêter le suivi
        automatique du personnage principal. Le PNJ s'arrête à sa position actuelle
        et reprend son comportement normal (animation idle, etc.).
        
        Args:
            event_data: Configuration de l'événement d'arrêt de suivi de PNJ
        
        Raises:
            ValueError: Si le PNJ avec l'ID spécifié n'existe pas
        """
        npc = self.npcs.get(event_data.npc_id)
        if npc is None:
            logger.error("PNJ introuvable pour l'événement: %s", event_data.npc_id)
            raise ValueError(f"PNJ avec l'ID '{event_data.npc_id}' introuvable")
        
        # Vérifier si le PNJ suit actuellement le joueur
        if not npc.is_following_player():
            logger.warning(
                "PNJ '%s' n'est pas en train de suivre le joueur, l'événement est ignoré",
                event_data.npc_id
            )
            return
        
        # Arrêter le suivi
        npc.stop_following_player()
        logger.info(
            "Arrêt du suivi du joueur pour PNJ: %s",
            event_data.npc_id,
        )

    def _execute_npc_magic_move(self, event_data: NPCMagicMoveEventConfig) -> None:
        """Exécute un événement de téléportation magique de PNJ (disparition/réapparition).
        
        Cette méthode fait disparaître instantanément le PNJ, puis le fait réapparaître
        progressivement à une position définie. Une fois réapparu, la gravité et les collisions
        sont réactivées.
        
        Args:
            event_data: Configuration de l'événement de téléportation magique de PNJ
        
        Raises:
            ValueError: Si le PNJ avec l'ID spécifié n'existe pas
        """
        npc = self.npcs.get(event_data.npc_id)
        if npc is None:
            logger.error("PNJ introuvable pour l'événement: %s", event_data.npc_id)
            raise ValueError(f"PNJ avec l'ID '{event_data.npc_id}' introuvable")
        
        # Interrompre les actions en cours (suivi, déplacement)
        if npc.is_following_player():
            npc.stop_following_player()
        npc.stop_movement()
        
        # Disparition instantanée (opacité = 0)
        npc.set_alpha(0)
        
        # Désactiver temporairement la gravité et les collisions
        npc.set_gravity_enabled(False)
        npc.set_collisions_enabled(False)
        
        # Changer le sprite sheet si spécifié
        if event_data.sprite_sheet_path is not None:
            npc.change_sprite_sheet(event_data.sprite_sheet_path)
        
        # Configurer l'animation et la direction si spécifiées
        if event_data.animation_row is not None:
            npc._magic_move_animation_row = event_data.animation_row
        if event_data.animation_start is not None:
            npc._magic_move_animation_start = event_data.animation_start
            npc.current_frame = event_data.animation_start
        
        if event_data.direction is not None:
            npc.direction = event_data.direction
        
        # Téléporter le PNJ à la nouvelle position
        npc.x = event_data.target_x
        npc.y = event_data.target_y
        
        # Marquer le PNJ comme positionné pour éviter que la logique d'initialisation
        # ne le repositionne sur la mauvaise plateforme lors de la réactivation de la gravité.
        # Le PNJ est déjà à la position target_y spécifiée, donc on le marque comme positionné.
        # Si target_y est au-dessus d'un vide, la gravité normale le fera tomber une fois réactivée.
        npc._positioned = True
        npc.velocity_y = 0.0
        # Ne pas forcer is_on_ground = True car le PNJ pourrait être au-dessus d'un vide
        # La gravité normale déterminera si le PNJ est au sol une fois réactivée
        
        # Initialiser le fade in
        self._npc_fade_in_timers[npc] = (event_data.fade_in_duration, event_data.fade_in_duration)
        
        logger.info(
            "Téléportation magique déclenchée pour PNJ: %s (target=(%.2f, %.2f), fade_duration=%.2fs, animation_row=%s, animation_start=%s, direction=%s)",
            event_data.npc_id,
            event_data.target_x,
            event_data.target_y,
            event_data.fade_in_duration,
            event_data.animation_row,
            event_data.animation_start,
            event_data.direction,
        )

    def _execute_sprite_hide(self, event_data: SpriteHideEventConfig) -> None:
        """Exécute un événement de masquage de sprite.

        Args:
            event_data: Configuration de l'événement de masquage
        """
        # Récupérer toutes les layers associées au tag
        layers = self.layers_by_tag.get(event_data.sprite_tag, [])
        if not layers:
            logger.warning("Aucune layer trouvée pour le tag '%s'", event_data.sprite_tag)
            return

        # Initialiser le fade out pour chaque layer
        for layer in layers:
            # Enregistrer l'opacité initiale avant le fade out
            initial_alpha = layer.alpha
            # Enregistrer le timer de fade out avec la durée totale
            # Le timer commence à fade_duration et diminue jusqu'à 0
            self._fade_out_timers[layer] = (event_data.fade_duration, event_data.fade_duration, initial_alpha)
            # L'opacité sera mise à jour dans update()
            logger.debug(
                "Fade out initialisé pour layer '%s' (tag='%s', durée=%.2fs, alpha_initial=%d)",
                layer.name,
                event_data.sprite_tag,
                event_data.fade_duration,
                initial_alpha,
            )

        logger.info(
            "Masquage de sprite déclenché: tag='%s' (%d layers, durée=%.2fs, remove_collisions=%s)",
            event_data.sprite_tag,
            len(layers),
            event_data.fade_duration,
            event_data.remove_collisions,
        )

    def _execute_sprite_show(self, event_data: SpriteShowEventConfig) -> None:
        """Exécute un événement d'affichage de sprite.
        
        Cette méthode initialise l'animation de fade in pour les layers
        associées au tag spécifié.
        
        Args:
            event_data: Configuration de l'événement d'affichage de sprite
        
        Raises:
            ValueError: Si le tag spécifié n'existe pas dans layers_by_tag
        """
        # Récupérer toutes les layers associées au tag
        layers = self.layers_by_tag.get(event_data.sprite_tag, [])
        if not layers:
            logger.warning("Aucune layer trouvée pour le tag '%s'", event_data.sprite_tag)
            return

        # Initialiser le fade in pour chaque layer
        for layer in layers:
            # Si la layer est en cours de fade out, la retirer du timer de fade out
            if layer in self._fade_out_timers:
                del self._fade_out_timers[layer]
                logger.debug(
                    "Layer '%s' retirée du fade out pour commencer le fade in",
                    layer.name,
                )
            
            # Enregistrer l'opacité actuelle (peut être 0 si initial_alpha = 0 ou si masqué précédemment)
            initial_alpha = layer.alpha
            # Enregistrer le timer de fade in avec la durée totale
            # Le timer commence à fade_duration et diminue jusqu'à 0
            # IMPORTANT: Ne pas mettre à jour l'opacité ici, elle sera mise à jour dans update()
            # lors de la première frame pour garantir que le fade_duration est respecté
            self._fade_in_timers[layer] = (event_data.fade_duration, event_data.fade_duration, initial_alpha)
            layer.is_hidden = False  # Marquer comme non masquée (important pour le rendu)
            # Invalider le cache d'opacité pour forcer la recréation de la surface avec la nouvelle opacité
            layer._alpha_surface_cache.clear()
            logger.debug(
                "Fade in initialisé pour layer '%s' (tag='%s', durée=%.2fs, alpha_initial=%d)",
                layer.name,
                event_data.sprite_tag,
                event_data.fade_duration,
                initial_alpha,
            )

        logger.info(
            "Affichage de sprite déclenché: tag='%s' (%d layers, durée=%.2fs, restore_collisions=%s)",
            event_data.sprite_tag,
            len(layers),
            event_data.fade_duration,
            event_data.restore_collisions,
        )

    def _execute_sprite_move(self, event_data: SpriteMoveEventConfig) -> None:
        """Exécute un événement de déplacement de sprite.
        
        Initialise un `SpriteMovementTask` pour chaque layer associé au tag
        cible, calcule la destination locale (`current_position + move_x/move_y`)
        et enregistre la vitesse uniforme à appliquer. Cette méthode notifie le
        `collision_system` afin qu'il puisse verrouiller les entités situées sur
        la face supérieure du sprite et les déplacer du même delta à chaque
        frame.
        
        Args:
            event_data: Configuration de l'événement de déplacement de sprite
        
        Raises:
            ValueError: Si le tag spécifié n'existe pas ou si `collision_system`
                n'est pas fourni (car indispensable pour gérer les passagers)
        """
        # Récupérer toutes les layers associées au tag
        layers = self.layers_by_tag.get(event_data.sprite_tag, [])
        if not layers:
            logger.warning("Aucune layer trouvée pour le tag '%s'", event_data.sprite_tag)
            return
        
        # Vérifier que collision_system est disponible
        if self.collision_system is None:
            raise ValueError(
                "collision_system est requis pour les événements sprite_move "
                f"(tag='{event_data.sprite_tag}')"
            )
        
        # Initialiser une tâche de mouvement pour chaque layer
        for layer in layers:
            # Échantillonner la position de départ
            start_x = layer.world_x_offset
            start_y = getattr(layer, 'world_y_offset', 0.0)
            
            # Calculer la destination
            target_x = start_x + event_data.move_x
            target_y = start_y + event_data.move_y
            
            # Calculer la distance totale et la direction
            dx = target_x - start_x
            dy = target_y - start_y
            distance = math.sqrt(dx * dx + dy * dy)
            
            if distance <= 0:
                # Si move_speed <= 0 ou distance nulle, repositionner instantanément
                layer.world_x_offset = target_x
                layer.world_y_offset = target_y
                logger.debug(
                    "Sprite repositionné instantanément: layer='%s' (x=%.2f, y=%.2f)",
                    layer.name, target_x, target_y
                )
                continue
            
            # Normaliser la direction
            direction_x = dx / distance
            direction_y = dy / distance
            
            # Créer la tâche de mouvement
            task = SpriteMovementTask(
                layer=layer,
                start_x=start_x,
                start_y=start_y,
                target_x=target_x,
                target_y=target_y,
                move_speed=event_data.move_speed,
                remaining_distance=distance,
                direction_x=direction_x,
                direction_y=direction_y,
            )
            
            self._sprite_movement_tasks[layer] = task
            logger.debug(
                "Tâche de mouvement initialisée: layer='%s' (start=(%.2f, %.2f), target=(%.2f, %.2f), speed=%.2f)",
                layer.name, start_x, start_y, target_x, target_y, event_data.move_speed
            )
        
        logger.info(
            "Déplacement de sprite déclenché: tag='%s' (%d layers, move_x=%.2f, move_y=%.2f, speed=%.2f)",
            event_data.sprite_tag,
            len(layers),
            event_data.move_x,
            event_data.move_y,
            event_data.move_speed,
        )

    def _execute_sprite_move_perpetual(self, event_data: SpriteMovePerpetualEventConfig) -> None:
        """Exécute un événement de déplacement perpétuel de sprite.
        
        Initialise un `SpritePerpetualMovementTask` pour chaque layer associé au tag
        cible. Le sprite se déplace de manière perpétuelle entre sa position de départ
        (capturée au déclenchement de l'événement) et la position d'arrivée (position_depart + move_x/move_y).
        Une fois la destination atteinte, le sprite revient à sa position de départ, et le cycle
        se répète indéfiniment. Cette méthode notifie le `collision_system` afin qu'il puisse
        verrouiller les entités situées sur la face supérieure du sprite et les déplacer du même
        delta à chaque frame.
        
        Args:
            event_data: Configuration de l'événement de déplacement perpétuel de sprite
        
        Raises:
            ValueError: Si le tag spécifié n'existe pas ou si `collision_system`
                n'est pas fourni (car indispensable pour gérer les passagers)
        """
        # Récupérer toutes les layers associées au tag
        layers = self.layers_by_tag.get(event_data.sprite_tag, [])
        if not layers:
            logger.warning("Aucune layer trouvée pour le tag '%s'", event_data.sprite_tag)
            return
        
        # Vérifier que collision_system est disponible
        if self.collision_system is None:
            raise ValueError(
                "collision_system est requis pour les événements sprite_move_perpetual "
                f"(tag='{event_data.sprite_tag}')"
            )
        
        # Initialiser une tâche de mouvement perpétuel pour chaque layer
        for layer in layers:
            # Échantillonner la position de départ (capturée au déclenchement)
            start_x = layer.world_x_offset
            start_y = getattr(layer, 'world_y_offset', 0.0)
            
            # Calculer la destination
            target_x = start_x + event_data.move_x
            target_y = start_y + event_data.move_y
            
            # Calculer la distance totale et la direction
            dx = target_x - start_x
            dy = target_y - start_y
            distance = math.sqrt(dx * dx + dy * dy)
            
            if distance <= 0:
                logger.warning(
                    "Distance nulle pour le mouvement perpétuel: layer='%s' (move_x=%.2f, move_y=%.2f)",
                    layer.name, event_data.move_x, event_data.move_y
                )
                continue
            
            # Normaliser la direction
            direction_x = dx / distance
            direction_y = dy / distance
            
            # Créer la tâche de mouvement perpétuel (commence en allant vers la destination)
            task = SpritePerpetualMovementTask(
                layer=layer,
                start_x=start_x,
                start_y=start_y,
                target_x=target_x,
                target_y=target_y,
                move_speed=event_data.move_speed,
                remaining_distance=distance,
                direction_x=direction_x,
                direction_y=direction_y,
                going_to_target=True,  # Commence en allant vers la destination
            )
            
            self._sprite_perpetual_movement_tasks[layer] = task
            logger.debug(
                "Tâche de mouvement perpétuel initialisée: layer='%s' (start=(%.2f, %.2f), target=(%.2f, %.2f), speed=%.2f)",
                layer.name, start_x, start_y, target_x, target_y, event_data.move_speed
            )
        
        logger.info(
            "Déplacement perpétuel de sprite déclenché: tag='%s' (%d layers, move_x=%.2f, move_y=%.2f, speed=%.2f)",
            event_data.sprite_tag,
            len(layers),
            event_data.move_x,
            event_data.move_y,
            event_data.move_speed,
        )

    def _execute_sprite_rotate(self, event_data: SpriteRotateEventConfig) -> None:
        """Exécute un événement de rotation de sprite.
        
        Initialise un `SpriteRotationTask` pour chaque layer associé au tag
        cible. Le sprite tourne progressivement autour de son centre à la vitesse
        spécifiée pendant la durée configurée. La rotation est appliquée lors du
        rendu via `pygame.transform.rotate()` autour du centre du sprite.
        
        Args:
            event_data: Configuration de l'événement de rotation de sprite
        
        Raises:
            ValueError: Si le tag spécifié n'existe pas dans layers_by_tag
        """
        # Récupérer toutes les layers associées au tag
        layers = self.layers_by_tag.get(event_data.sprite_tag, [])
        if not layers:
            logger.warning("Aucune layer trouvée pour le tag '%s'", event_data.sprite_tag)
            return
        
        # Initialiser une tâche de rotation pour chaque layer
        for layer in layers:
            # Échantillonner l'angle initial (par défaut 0.0 si pas déjà défini)
            initial_angle = getattr(layer, 'rotation_angle', 0.0)
            
            # Créer la tâche de rotation
            task = SpriteRotationTask(
                layer=layer,
                initial_angle=initial_angle,
                rotation_speed=event_data.rotation_speed,
                duration=event_data.duration,
                elapsed_time=0.0,
            )
            
            self._sprite_rotation_tasks[layer] = task
            logger.debug(
                "Tâche de rotation initialisée: layer='%s' (initial_angle=%.2f, rotation_speed=%.2f deg/s, duration=%.2f s)",
                layer.name, initial_angle, event_data.rotation_speed, event_data.duration
            )
        
        logger.info(
            "Rotation de sprite déclenché: tag='%s' (%d layers, rotation_speed=%.2f deg/s, duration=%.2f s)",
            event_data.sprite_tag,
            len(layers),
            event_data.rotation_speed,
            event_data.duration,
        )

    def _execute_inventory_add(self, event_data: InventoryAddEventConfig) -> None:
        """Exécute un événement d'ajout d'objet à l'inventaire.

        Args:
            event_data: Configuration de l'événement d'ajout
        """
        if self.player is None or self.player.inventory is None:
            logger.warning(
                "Impossible d'exécuter l'événement inventory_add: instance Player non fournie"
            )
            return

        # Ajouter l'objet avec animation
        self.player.inventory.add_item(event_data.item_id, event_data.quantity, animated=True)
        logger.info(
            "Ajout d'objet à l'inventaire: item_id='%s', quantity=%d",
            event_data.item_id,
            event_data.quantity,
        )

    def _execute_inventory_remove(self, event_data: InventoryRemoveEventConfig) -> None:
        """Exécute un événement de retrait d'objet de l'inventaire.

        Args:
            event_data: Configuration de l'événement de retrait
        """
        if self.player is None or self.player.inventory is None:
            logger.warning(
                "Impossible d'exécuter l'événement inventory_remove: instance Player non fournie"
            )
            return

        # Vérifier que l'inventaire contient suffisamment d'objets
        if not self.player.inventory.has_item(event_data.item_id, event_data.quantity):
            logger.warning(
                "Impossible de retirer l'objet '%s' (quantity=%d): quantité insuffisante",
                event_data.item_id,
                event_data.quantity,
            )
            return

        # Retirer l'objet avec animation
        success = self.player.inventory.remove_item(
            event_data.item_id, event_data.quantity, animated=True
        )
        if success:
            logger.info(
                "Retrait d'objet de l'inventaire: item_id='%s', quantity=%d",
                event_data.item_id,
                event_data.quantity,
            )
        else:
            logger.warning(
                "Échec du retrait d'objet: item_id='%s', quantity=%d",
                event_data.item_id,
                event_data.quantity,
            )

    def _execute_level_up(self, event_data: LevelUpEventConfig) -> None:
        """Exécute un événement de level up.
        
        Cette méthode appelle `player.show_level_up()` pour activer l'affichage
        "level up (press u)" au-dessus du nom du personnage principal.
        
        Args:
            event_data: Configuration de l'événement de level up (non utilisée, mais conservée pour cohérence)
        
        Raises:
            ValueError: Si l'instance `Player` n'est pas fournie au constructeur
        """
        if self.player is None:
            logger.warning("Événement level_up ignoré : instance Player non fournie")
            raise ValueError("L'instance Player est requise pour les événements de level up")
        
        # Activer l'affichage du level up
        self.player.show_level_up()
        logger.info("Level up activé pour le joueur")

    def _execute_particle_effect(self, event_data: ParticleEffectEventConfig) -> None:
        """Exécute un événement de lancement d'effet de particules.
        
        Cette méthode crée un effet de particules à la position spécifiée ou dans une zone
        en utilisant le système de particules global. L'effet est créé immédiatement et géré
        automatiquement par le système de particules.
        
        Args:
            event_data: Configuration de l'événement d'effet de particules
        
        Note:
            Si le système de particules n'est pas disponible, l'événement est ignoré
            silencieusement (log un avertissement, pas d'erreur levée).
        """
        if self.particle_system is None:
            logger.warning("Événement particle_effect ignoré : système de particules non fourni")
            return  # Ignorer silencieusement si le système de particules n'est pas disponible
        
        import random
        from ..particles import (
            create_explosion_config,
            create_confetti_config,
            create_flame_explosion_config,
            create_rain_config,
            create_smoke_config,
            create_sparks_config,
        )
        
        # Utiliser les facteurs d'échelle déjà calculés dans __init__
        design_scale_x = self._design_scale_x
        design_scale_y = self._design_scale_y
        
        spawn_area_render: Optional[Dict[str, float]] = None
        x_render: Optional[float] = None
        y_render: Optional[float] = None
        
        # Déterminer la zone de génération (priorité : sprite_tag > spawn_area > x/y)
        if event_data.sprite_tag is not None:
            # Zone de génération basée sur un sprite tag
            layers = self.layers_by_tag.get(event_data.sprite_tag, [])
            if not layers:
                logger.error(f"particle_effect: tag '{event_data.sprite_tag}' introuvable dans layers_by_tag")
                raise ValueError(f"Tag '{event_data.sprite_tag}' introuvable pour l'événement particle_effect")
            
            # Calculer l'union des bounds de toutes les layers avec ce tag
            x_min_design = float('inf')
            x_max_design = float('-inf')
            y_min_design = float('inf')
            y_max_design = float('-inf')
            
            for layer in layers:
                # Utiliser le bounding box réel (non transparent) du sprite pour éviter de prendre toute la surface 1920x1080
                layer_rect = layer.surface.get_bounding_rect()
                if layer_rect.width <= 0 or layer_rect.height <= 0:
                    logger.warning(
                        "particle_effect: layer '%s' a un bounding box vide (rect=%s), ignorée pour le calcul de zone",
                        layer.name,
                        layer_rect,
                    )
                    continue

                layer_x_min = layer.world_x_offset + layer_rect.x
                layer_x_max = layer_x_min + layer_rect.width

                # Si la layer se répète avec infinite_offset, prendre en compte la largeur effective
                if layer.repeat and hasattr(layer, 'infinite_offset'):
                    effective_width = layer_rect.width + layer.infinite_offset
                    if effective_width > 0:
                        layer_x_max = layer.world_x_offset + layer_rect.x + effective_width
                
                layer_y_min = getattr(layer, 'world_y_offset', 0.0) + layer_rect.y
                layer_y_max = layer_y_min + layer_rect.height
                
                logger.debug(
                    f"particle_effect: layer '{layer.name}' bounds (non transparent): "
                    f"x=[{layer_x_min:.2f}, {layer_x_max:.2f}], y=[{layer_y_min:.2f}, {layer_y_max:.2f}], "
                    f"surface_size=({layer.surface.get_width()}, {layer.surface.get_height()}), rect={layer_rect}"
                )
                
                x_min_design = min(x_min_design, layer_x_min)
                x_max_design = max(x_max_design, layer_x_max)
                y_min_design = min(y_min_design, layer_y_min)
                y_max_design = max(y_max_design, layer_y_max)
            
            # Vérifier que des bounds valides ont été calculés
            if x_min_design == float('inf') or x_max_design == float('-inf') or \
               y_min_design == float('inf') or y_max_design == float('-inf'):
                logger.error(
                    f"particle_effect: impossible de calculer les bounds pour tag '{event_data.sprite_tag}'. "
                    f"Aucune layer valide trouvée."
                )
                return
            
            # Limiter à un bord si spawn_edge est spécifié
            if event_data.spawn_edge == "top":
                # Bande horizontale en haut (1 pixel de hauteur)
                y_max_design = y_min_design + 1.0
            elif event_data.spawn_edge == "bottom":
                # Bande horizontale en bas (1 pixel de hauteur)
                y_min_design = y_max_design - 1.0
            elif event_data.spawn_edge == "left":
                # Bande verticale à gauche (1 pixel de largeur)
                x_max_design = x_min_design + 1.0
            elif event_data.spawn_edge == "right":
                # Bande verticale à droite (1 pixel de largeur)
                x_min_design = x_max_design - 1.0
            
            # Valider que la zone calculée est valide
            if x_min_design >= x_max_design:
                logger.error(
                    f"particle_effect: zone invalide pour tag '{event_data.sprite_tag}' (x_min={x_min_design:.2f} >= x_max={x_max_design:.2f}). "
                    f"Vérifiez que le sprite existe et a une largeur valide. "
                    f"Nombre de layers trouvées: {len(layers)}"
                )
                return
            if y_min_design >= y_max_design:
                logger.error(
                    f"particle_effect: zone invalide pour tag '{event_data.sprite_tag}' (y_min={y_min_design:.2f} >= y_max={y_max_design:.2f}). "
                    f"Vérifiez que le sprite existe et a une hauteur valide. "
                    f"Nombre de layers trouvées: {len(layers)}"
                )
                return
            
            # Vérifier que la zone a une taille minimale (au moins 1 pixel)
            if (x_max_design - x_min_design) < 1.0:
                logger.warning(
                    f"particle_effect: zone très petite pour tag '{event_data.sprite_tag}' "
                    f"(largeur={x_max_design - x_min_design:.2f} pixels). "
                    f"Les particules pourraient ne pas être visibles."
                )
            if (y_max_design - y_min_design) < 1.0:
                logger.warning(
                    f"particle_effect: zone très petite pour tag '{event_data.sprite_tag}' "
                    f"(hauteur={y_max_design - y_min_design:.2f} pixels). "
                    f"Les particules pourraient ne pas être visibles."
                )
            
            # Les bounds des layers viennent du LevelLoader qui a déjà converti les positions
            # en repère de rendu (world_x_offset, layer_rect, etc. sont en render space).
            # Ne pas multiplier par design_scale pour éviter un double scale (spec 15).
            x_min_render = x_min_design
            x_max_render = x_max_design
            y_min_render = y_min_design
            y_max_render = y_max_design
            
            spawn_area_render = {
                "x_min": x_min_render,
                "x_max": x_max_render,
                "y_min": y_min_render,
                "y_max": y_max_render,
            }
            
            # Log de débogage pour vérifier les valeurs calculées
            logger.debug(
                f"particle_effect: zone calculée pour tag '{event_data.sprite_tag}' "
                f"(render: x=[{x_min_render:.2f}, {x_max_render:.2f}], y=[{y_min_render:.2f}, {y_max_render:.2f}])"
            )
            # Utiliser le coin supérieur gauche comme position de référence
            x_render = x_min_render
            y_render = y_min_render
        elif event_data.spawn_area is not None:
            # Zone de génération : convertir les limites de la zone
            x_min_render = event_data.spawn_area["x_min"] * design_scale_x
            x_max_render = event_data.spawn_area["x_max"] * design_scale_x
            y_min_render = event_data.spawn_area["y_min"] * design_scale_y
            y_max_render = event_data.spawn_area["y_max"] * design_scale_y
            spawn_area_render = {
                "x_min": x_min_render,
                "x_max": x_max_render,
                "y_min": y_min_render,
                "y_max": y_max_render,
            }
            # Utiliser le coin supérieur gauche comme position de référence
            x_render = x_min_render
            y_render = y_min_render
        else:
            # Point unique : convertir les coordonnées
            if event_data.x is None or event_data.y is None:
                logger.error("particle_effect: x et y sont obligatoires si spawn_area et sprite_tag ne sont pas spécifiés")
                return
            x_render = event_data.x * design_scale_x
            y_render = event_data.y * design_scale_y
        
        # Déterminer les couleurs à utiliser
        colors_to_use: Optional[List[Tuple[int, int, int]]] = None
        if event_data.effect_type not in ("flame_explosion", "confetti"):
            # Pour les effets qui supportent les couleurs personnalisées
            if event_data.colors is not None and len(event_data.colors) > 0:
                colors_to_use = event_data.colors
            elif event_data.color is not None:
                colors_to_use = [event_data.color]
            # Sinon, utiliser la couleur par défaut du type d'effet (sera géré lors de la création de la config)
        
        # Sélectionner la fonction de configuration selon le type d'effet
        config_functions = {
            "explosion": create_explosion_config,
            "confetti": create_confetti_config,
            "flame_explosion": create_flame_explosion_config,
            "rain": create_rain_config,
            "smoke": create_smoke_config,
            "sparks": create_sparks_config,
        }
        
        if event_data.effect_type not in config_functions:
            raise ValueError(f"Type d'effet invalide : {event_data.effect_type}")
        
        # Créer la configuration de base
        base_config = config_functions[event_data.effect_type]()
        
        # Personnaliser la configuration avec les paramètres optionnels
        if event_data.count is not None:
            base_config.count = event_data.count
        if event_data.speed is not None:
            # Convertir la vitesse du repère de design vers le repère de rendu
            base_config.speed = event_data.speed * design_scale_x
        if event_data.lifetime is not None:
            base_config.lifetime = event_data.lifetime
        if event_data.size is not None:
            # Convertir la taille du repère de design vers le repère de rendu
            base_config.size = int(event_data.size * design_scale_x)
        
        # Gérer les couleurs
        if event_data.effect_type not in ("flame_explosion", "confetti"):
            # Pour les effets qui supportent les couleurs personnalisées
            if colors_to_use is not None and len(colors_to_use) > 1:
                # Plusieurs couleurs : utiliser la palette
                base_config.color_palette = colors_to_use
                # Utiliser la première couleur comme couleur de base (pour compatibilité)
                base_config.color = colors_to_use[0]
            elif colors_to_use is not None and len(colors_to_use) == 1:
                # Une seule couleur : utiliser color normalement
                base_config.color = colors_to_use[0]
            elif event_data.color is not None:
                # Rétrocompatibilité : utiliser color
                base_config.color = event_data.color
            # Sinon, utiliser la couleur par défaut du type d'effet (déjà dans base_config)
        
        # Gérer la variation de couleur
        if event_data.effect_type not in ("flame_explosion", "confetti"):
            # Pour les effets qui supportent la variation de couleur personnalisée
            if event_data.color_variation is not None:
                base_config.color_variation = event_data.color_variation
            # Sinon, utiliser la valeur par défaut du type d'effet (déjà dans base_config)
        
        # Si generation_duration est spécifié, le stocker dans la configuration
        if event_data.generation_duration is not None:
            base_config.generation_duration = event_data.generation_duration
        
        # Gérer la direction personnalisée si spécifiée
        if event_data.direction_angle is not None:
            # Si direction_angle est spécifié, utiliser le type "custom" pour permettre la personnalisation
            base_config.direction_type = "custom"
            base_config.direction_angle = event_data.direction_angle
            # Si direction_spread est également spécifié, l'utiliser, sinon utiliser une dispersion par défaut raisonnable
            if event_data.direction_spread is not None:
                base_config.direction_spread = event_data.direction_spread
            # Si direction_spread n'est pas spécifié mais direction_angle l'est, utiliser une dispersion par défaut raisonnable
            elif base_config.direction_spread == 2.0 * math.pi:
                # Si la dispersion par défaut est 2π (toutes directions), utiliser une dispersion plus limitée
                base_config.direction_spread = math.pi / 6  # 30° de dispersion par défaut
        elif event_data.direction_spread is not None:
            # Si seulement direction_spread est spécifié (sans direction_angle), ajuster la dispersion du type actuel
            # La logique dans ParticleEffect utilisera direction_spread pour ajuster la dispersion autour de la direction par défaut
            base_config.direction_spread = event_data.direction_spread
            # Pour que direction_spread soit utilisé, on doit aussi définir direction_angle à la direction par défaut du type
            # Cela permet à la logique dans ParticleEffect d'utiliser direction_spread même pour les types prédéfinis
            if base_config.direction_type == "rain":
                base_config.direction_angle = math.pi / 2  # Vers le bas
            elif base_config.direction_type == "smoke":
                base_config.direction_angle = -math.pi / 2  # Vers le haut
            elif base_config.direction_type == "sparks":
                base_config.direction_angle = 0.0  # Direction par défaut (vers le haut avec variation)
            elif base_config.direction_type == "explosion":
                base_config.direction_angle = 0.0  # Direction par défaut (toutes directions)
            # Note: Pour que direction_spread soit utilisé, on change aussi direction_type en "custom"
            # car la logique dans ParticleEffect utilise direction_spread uniquement pour "custom"
            base_config.direction_type = "custom"
        
        # Générer un identifiant unique pour l'effet
        import time
        effect_id = f"event_particle_{int(time.time() * 1000)}"
        
        # Créer l'effet de particules
        self.particle_system.create_effect(
            x_render,
            y_render,
            base_config,
            effect_id=effect_id,
            spawn_area=spawn_area_render,
        )
        
        if spawn_area_render is not None:
            if event_data.sprite_tag is not None:
                edge_info = f" (tag='{event_data.sprite_tag}'"
                if event_data.spawn_edge is not None:
                    edge_info += f", edge='{event_data.spawn_edge}'"
                edge_info += ")"
                logger.info(
                    "Effet de particules créé : %s dans la zone du sprite%s (%.2f, %.2f) à (%.2f, %.2f)",
                    event_data.effect_type,
                    edge_info,
                    spawn_area_render["x_min"],
                    spawn_area_render["y_min"],
                    spawn_area_render["x_max"],
                    spawn_area_render["y_max"],
                )
            else:
                logger.info(
                    "Effet de particules créé : %s dans la zone (%.2f, %.2f) à (%.2f, %.2f)",
                    event_data.effect_type,
                    spawn_area_render["x_min"],
                    spawn_area_render["y_min"],
                    spawn_area_render["x_max"],
                    spawn_area_render["y_max"],
                )
        else:
            logger.info(
                "Effet de particules créé : %s à (%.2f, %.2f)",
                event_data.effect_type,
                x_render,
                y_render,
            )

    def get_screen_fade_state(self) -> tuple[int, Optional[str], int]:
        """Retourne l'état actuel du fondu au noir de l'écran.
        
        Cette méthode permet au système de rendu d'obtenir l'opacité actuelle du fondu,
        le texte à afficher (si présent) et l'opacité du texte pour dessiner l'overlay de fondu.
        
        Returns:
            Tuple contenant :
            - `alpha` (int) : Opacité actuelle du fondu (0-255), où 0 = transparent (pas de fondu) et 255 = complètement noir
            - `text` (Optional[str]) : Texte à afficher en blanc centré au milieu de l'écran, ou None si aucun texte n'est configuré ou si le fondu n'est pas actif
            - `text_alpha` (int) : Opacité actuelle du texte (0-255), où 0 = transparent et 255 = complètement opaque. Si aucun texte n'est configuré, retourne 0
        
        Note:
            Cette méthode doit être appelée à chaque frame dans la boucle de rendu pour obtenir
            l'état actuel du fondu. L'opacité est calculée automatiquement par le système en fonction
            de la phase actuelle du fondu (fade_in, text_fade_in, text_display, text_fade_out, fade_out).
        """
        if self._screen_fade_phase == "none" or self._screen_fade_config is None:
            return (0, None, 0)
        
        config = self._screen_fade_config
        
        # Calculer l'opacité du fond (écran noir)
        if self._screen_fade_phase == "fade_in":
            # Opacité passe de 0 à 255 pendant fade_in_duration
            progress = 1.0 - (self._screen_fade_timer / config.fade_in_duration)
            alpha = int(255 * progress)
        elif self._screen_fade_phase in ("text_fade_in", "text_display", "text_fade_out"):
            # Opacité reste à 255 pendant les phases de texte
            alpha = 255
        elif self._screen_fade_phase == "fade_out":
            # Opacité passe de 255 à 0 pendant fade_out_duration
            progress = self._screen_fade_timer / config.fade_out_duration
            alpha = int(255 * progress)
        else:
            alpha = 0
        
        # Clamper l'opacité entre 0 et 255
        alpha = max(0, min(255, alpha))
        
        # Calculer l'opacité du texte
        text_alpha = 0
        if config.text is not None:
            if self._screen_fade_phase == "text_fade_in":
                # Texte apparaît progressivement
                progress = 1.0 - (self._screen_fade_timer / config.text_fade_in_duration)
                text_alpha = int(255 * progress)
            elif self._screen_fade_phase == "text_display":
                # Texte complètement visible
                text_alpha = 255
            elif self._screen_fade_phase == "text_fade_out":
                # Texte disparaît progressivement
                progress = self._screen_fade_timer / config.text_fade_out_duration
                text_alpha = int(255 * progress)
            elif self._screen_fade_phase == "fade_out":
                # Texte complètement invisible pendant fade_out
                text_alpha = 0
        
        # Clamper l'opacité du texte entre 0 et 255
        text_alpha = max(0, min(255, text_alpha))
        
        # Retourner l'opacité, le texte et l'opacité du texte
        return (alpha, config.text, text_alpha)

    def has_active_screen_fade(self) -> bool:
        """Vérifie si un fondu au noir est actuellement en cours.
        
        Cette méthode permet au système de dialogue de vérifier si un fondu au noir
        est en cours avant de permettre le passage à l'échange suivant.
        
        Returns:
            True si un fondu au noir est actuellement en cours (phase fade_in, text_fade_in, text_display, text_fade_out ou fade_out),
            False sinon (phase none ou aucun fondu actif)
        
        Note:
            Cette méthode doit être utilisée par le système de dialogue pour bloquer le passage
            manuel (clic) à l'échange suivant tant que le fondu n'est pas terminé. Voir la
            spécification 12 pour plus de détails sur l'intégration avec les dialogues.
        """
        return self._screen_fade_phase != "none" and self._screen_fade_config is not None
    
    def is_screen_fade_in_fade_out(self) -> bool:
        """Vérifie si le fondu au noir est actuellement en phase fade_out.
        
        Cette méthode permet au système de dialogue de détecter quand le fondu entre
        en phase fade_out, moment où le passage automatique à l'échange suivant doit
        se produire (si le fondu a été déclenché depuis un dialogue).
        
        Returns:
            True si le fondu est en phase fade_out, False sinon
        """
        return self._screen_fade_phase == "fade_out"
    
    def get_screen_fade_phase(self) -> str:
        """Retourne la phase actuelle du fondu au noir.
        
        Cette méthode permet au système de dialogue de connaître la phase exacte
        du fondu pour détecter les transitions entre phases.
        
        Returns:
            La phase actuelle du fondu ("fade_in", "text_fade_in", "text_display", "text_fade_out", "fade_out", ou "none")
        """
        return self._screen_fade_phase

    def _execute_screen_fade(self, event_data: ScreenFadeEventConfig) -> None:
        """Exécute un événement de fondu au noir de l'écran.
        
        Cette méthode initialise l'animation de fondu au noir avec les phases suivantes :
        1. Fondu au noir (fade_in_duration) : l'écran devient progressivement noir
        2. Apparition du texte (text_fade_in_duration) : le texte apparaît progressivement sur le fond noir (si texte configuré)
        3. Affichage du texte (text_display_duration) : le texte reste visible à opacité maximale (si texte configuré)
        4. Disparition du texte (text_fade_out_duration) : le texte disparaît progressivement (si texte configuré)
        5. Fondu de retour (fade_out_duration) : l'écran redevient progressivement visible
        
        Si un texte est configuré, il est affiché en blanc centré au milieu de l'écran
        avec une opacité qui varie selon la phase (apparition, affichage, disparition).
        
        Args:
            event_data: Configuration de l'événement de fondu au noir
        """
        # Initialiser le fondu
        self._screen_fade_config = event_data
        self._screen_fade_phase = "fade_in"
        self._screen_fade_timer = event_data.fade_in_duration
        
        # Si fade_in_duration est 0, passer directement à la phase suivante
        if self._screen_fade_timer <= 0:
            if event_data.text is not None:
                # Passer à text_fade_in
                self._screen_fade_phase = "text_fade_in"
                self._screen_fade_timer = event_data.text_fade_in_duration
                if self._screen_fade_timer <= 0:
                    # Si text_fade_in_duration est 0, passer à text_display
                    self._screen_fade_phase = "text_display"
                    self._screen_fade_timer = event_data.text_display_duration
                    if self._screen_fade_timer <= 0:
                        # Si text_display_duration est 0, passer à text_fade_out
                        self._screen_fade_phase = "text_fade_out"
                        self._screen_fade_timer = event_data.text_fade_out_duration
                        if self._screen_fade_timer <= 0:
                            # Si text_fade_out_duration est 0, passer à fade_out
                            self._screen_fade_phase = "fade_out"
                            self._screen_fade_timer = event_data.fade_out_duration
                            if self._screen_fade_timer <= 0:
                                # Si fade_out_duration est aussi 0, terminer immédiatement
                                self._screen_fade_phase = "none"
                                self._screen_fade_config = None
                                self._screen_fade_timer = 0.0
            else:
                # Pas de texte, passer directement à fade_out
                self._screen_fade_phase = "fade_out"
                self._screen_fade_timer = event_data.fade_out_duration
                if self._screen_fade_timer <= 0:
                    # Si fade_out_duration est aussi 0, terminer immédiatement
                    self._screen_fade_phase = "none"
                    self._screen_fade_config = None
                    self._screen_fade_timer = 0.0
        
        logger.info(
            "Fondu au noir déclenché: fade_in=%.2fs, text_fade_in=%.2fs, text_display=%.2fs, text_fade_out=%.2fs, fade_out=%.2fs, text=%s",
            event_data.fade_in_duration,
            event_data.text_fade_in_duration,
            event_data.text_display_duration,
            event_data.text_fade_out_duration,
            event_data.fade_out_duration,
            event_data.text if event_data.text else "None",
        )

    def reset(self) -> None:
        """Réinitialise l'état du système (tous les événements redeviennent disponibles)."""
        for event in self.events:
            event.triggered = False
        # Réinitialiser les animations de fade out et fade in
        self._fade_out_timers.clear()
        self._fade_in_timers.clear()
        # Réinitialiser les animations de fade in des NPCs
        self._npc_fade_in_timers.clear()
        # Réinitialiser les tâches de mouvement
        self._sprite_movement_tasks.clear()
        # Réinitialiser les tâches de mouvement perpétuel
        self._sprite_perpetual_movement_tasks.clear()
        # Réinitialiser le fondu au noir
        self._screen_fade_timer = 0.0
        self._screen_fade_phase = "none"
        self._screen_fade_config = None
        logger.info("EventTriggerSystem réinitialisé")
    
    def has_active_sprite_movements(self) -> bool:
        """Vérifie s'il existe des mouvements de sprites en cours.
        
        Returns:
            True si au moins un mouvement de sprite est en cours, False sinon
        """
        return len(self._sprite_movement_tasks) > 0
    
    def reset_event_by_identifier(self, identifier: str) -> bool:
        """Réinitialise un événement spécifique par son identifiant.
        
        Cette méthode permet de réinitialiser l'état `triggered` d'un événement,
        permettant ainsi de le redéclencher. Utile notamment pour les événements
        de type `level_up` qui doivent pouvoir être déclenchés plusieurs fois.
        
        Args:
            identifier: Identifiant unique de l'événement à réinitialiser
        
        Returns:
            True si l'événement a été trouvé et réinitialisé, False sinon
        """
        for event in self.events:
            if event.identifier == identifier:
                event.triggered = False
                logger.debug("Événement '%s' réinitialisé", identifier)
                return True
        
        logger.debug("Événement '%s' introuvable pour réinitialisation", identifier)
        return False

    def trigger_event_by_identifier(self, identifier: str) -> bool:
        """Déclenche un événement par son identifiant.
        
        Cette méthode permet de déclencher manuellement un événement depuis un autre système
        (par exemple, lors du lancement d'un dialogue de PNJ). L'événement est déclenché
        immédiatement, même si la condition de position n'est pas remplie.
        
        Args:
            identifier: Identifiant unique de l'événement à déclencher
        
        Returns:
            True si l'événement a été trouvé et déclenché, False sinon (événement introuvable
            ou déjà déclenché et non répétable)
        
        Note:
            Si l'événement a déjà été déclenché et que `repeatable` est `False`, cette méthode
            retourne False sans lever d'erreur. Si `repeatable` est `True`, l'événement peut
            être déclenché plusieurs fois, même s'il a déjà été déclenché précédemment.
            Cela permet aux systèmes appelants (comme le système de dialogues) de déclencher
            des événements sans avoir à vérifier leur état au préalable.
        """
        # Chercher l'événement par son identifiant
        for event in self.events:
            if event.identifier == identifier:
                # Vérifier si l'événement peut être déclenché (pas encore déclenché OU répétable)
                if event.triggered and not event.repeatable:
                    logger.debug("Événement '%s' déjà déclenché et non répétable, ignoré", identifier)
                    return False
                
                # Déclencher l'événement
                self._execute_event(event)
                event.triggered = True
                logger.info("Événement déclenché manuellement: %s", identifier)
                return True
        
        # Événement introuvable
        logger.debug("Événement '%s' introuvable, ignoré", identifier)
        return False
    
    def get_event_type_by_identifier(self, identifier: str) -> Optional[str]:
        """Retourne le type d'un événement par son identifiant.
        
        Cette méthode permet de vérifier le type d'un événement sans le déclencher,
        utile pour déterminer si un événement est de type `screen_fade` par exemple.
        
        Args:
            identifier: Identifiant unique de l'événement
        
        Returns:
            Le type de l'événement (par exemple "screen_fade", "npc_move", etc.) si trouvé,
            None sinon
        """
        for event in self.events:
            if event.identifier == identifier:
                return event.event_type
        
        return None

