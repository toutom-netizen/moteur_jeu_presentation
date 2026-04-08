# 11 - Système de gestion de l'avancement dans le niveau

## Contexte

Le jeu nécessite un suivi précis de l'avancement horizontal du joueur dans chaque niveau. Cette information doit être visible en permanence pour fournir un retour immédiat à l'utilisateur, mais aussi être stockée de manière fiable afin de permettre l'activation future de mécaniques dépendantes de la progression (déclencheurs de dialogues, scripts de gameplay, récompenses, etc.). Cette spécification décrit un système centralisé chargé de mesurer, afficher et mémoriser la progression du joueur sur l'axe `x`.

## Objectifs

- Mesurer en temps réel le nombre de pixels horizontaux parcourus par le joueur dans le monde du niveau (coordonnée `world_x`).
- Afficher cette valeur en haut à gauche de l'interface sous forme d'overlay HUD lisible, indépendant du scrolling de la caméra (peut être masqué via l'argument `--hide-info-player`).
- Stocker l'état courant et le maximum atteint pour pouvoir être consommés par d'autres systèmes (présents ou futurs).
- Préparer une API de déclencheurs basés sur des positions `x` précises sans encore implémenter les interactions, en respectant les bonnes pratiques du projet.

## Périmètre

- Inclus :
  - Mesure continue de la progression horizontale du joueur.
  - Stockage en mémoire (durée de vie du niveau) de l'état actuel et du maximum atteint.
  - Affichage HUD localisé en haut à gauche de l'écran.
  - Interface d'enregistrement de jalons (`milestones`) pour de futures interactions.
  - **Système de déclencheurs d'événements** : Déclenchement d'événements basés sur la progression du joueur, notamment le déplacement de PNJ (voir spécification 12).
- Exclus :
  - Sauvegarde persistante inter-niveaux (sera définie ultérieurement si nécessaire).
  - Gestion des axes verticaux ou de métriques de vitesse.

## Architecture

### Composants principaux

1. `LevelProgressTracker` (nouveau module `src/moteur_jeu_presentation/game/progress.py`)
   - Source de vérité de la progression.
   - Maintient l'état courant, le maximum atteint et la liste des jalons déclarés.
2. `LevelProgressHUD`
   - Overlay responsable de l'affichage dans le coin supérieur gauche.
   - Consomme les données exposées par le tracker.
3. `EventTriggerSystem` (nouveau module `src/moteur_jeu_presentation/game/events.py`)
   - Système de gestion des déclencheurs d'événements basés sur la progression.
   - Charge les déclencheurs depuis des fichiers `.event` (format TOML).
   - Exécute les actions associées aux déclencheurs (déplacement de PNJ, etc.).
4. Intégrations :
   - `Player` (de `src/moteur_jeu_presentation/entities/player.py`) pour récupérer la position monde.
   - `GameState` de gameplay (spécification 1 & architecture principale) pour instancier et mettre à jour le tracker et l'HUD.
   - Système de niveaux (spécification 3) pour récupérer la largeur totale du niveau lorsque disponible.
   - `NPC` (de `src/moteur_jeu_presentation/entities/npc.py`) pour exécuter les actions de déplacement.

### Flux de données

1. À l'initialisation d'un niveau, le `GameState` instancie un `LevelProgressTracker` lié au joueur et au niveau courant.
2. À chaque `update(dt)`, le tracker lit `player.position_world.x` (ou l'équivalent canonique) et met à jour :
   - `current_x`
   - `max_x_reached`
   - Les jalons atteints (marqués comme déclenchés, sans encore appeler de callback).
3. L'HUD interroge le tracker à chaque `draw(surface)` et dessine la valeur formatée (`XXXX px`) en haut à gauche.
4. D'autres systèmes pourront consulter `LevelProgressTracker` via l'API exposée (`get_current_x`, `get_max_x`, `milestones`).

## Spécifications techniques

### Module `progress.py`

Créer un nouveau module `src/moteur_jeu_presentation/game/progress.py` contenant :

```python
class LevelProgressTracker:
    ...
```

#### Attributs

- `player: Player` (référence faible, ne doit pas créer de cycle fort).
- `level_width: float | None` : largeur totale du niveau en pixels si connue, sinon `None`.
- `current_x: float` : position monde courante du joueur sur l'axe horizontal.
- `max_x_reached: float` : valeur maximale atteinte depuis le début du niveau.
- `history: collections.deque[tuple[float, float]]` : optionnel, enregistre les derniers échantillons `(timestamp, x)` sur les 5 dernières secondes pour diagnostic (taille configurable).
- `milestones: dict[str, ProgressMilestone]` : jalons déclarés pour futurs déclencheurs (stockés mais non exécutés).

#### Dataclass `ProgressMilestone`

- `identifier: str` : identifiant unique (fourni par le système appelant).
- `threshold_x: float` : position monde en pixels à atteindre.
- `auto_reset: bool` : si `True`, le jalon peut se re-déclencher en cas de retour en arrière puis re-franchissement.
- `triggered: bool` : état interne mis à jour par le tracker.
- `metadata: dict[str, Any]` : informations libres (par exemple type d'interaction à déclencher plus tard).

#### Méthodes principales

- `update(dt: float) -> None` :
  - Lit `player.position_world.x` (ou `player.rect.x` converti en monde selon le système existant).
  - Normalise la valeur (arrondi `int` pour affichage mais conserve le `float` interne).
  - Met à jour `max_x_reached` si besoin.
  - Met à jour l'historique (capacité max 60 échantillons par seconde * 5 s = 300 entrées par défaut, configurable).
  - Parcourt `milestones` et marque `triggered = True` si `current_x >= threshold_x`.
- `reset(level_width: float | None = None) -> None` : remet les compteurs à zéro lors d'un changement de niveau.
- `register_milestone(milestone: ProgressMilestone) -> None` : enregistre un jalon (remplace s'il existe déjà).
- `get_current_x() -> int` : retourne la valeur arrondie pour l'affichage.
- `get_progress_ratio() -> float | None` : retourne `current_x / level_width` si `level_width` est connu.
- `get_state() -> LevelProgressState` : dataclass immuable exposant `current_x`, `max_x_reached`, `triggered_milestones`.

`LevelProgressState` doit être sérialisable simplement (types natifs), pour permettre une future persistance.

### Système de déclencheurs d'événements

Le système de déclencheurs permet d'exécuter des actions automatiques lorsque le joueur atteint certaines positions dans le niveau. Les types de déclencheurs implémentés sont : le déplacement de PNJ, le suivi du personnage principal par un PNJ, l'arrêt du suivi d'un PNJ, la téléportation magique de PNJ (disparition/réapparition), le masquage de sprites, l'affichage de sprites, le déplacement de sprites, le déplacement perpétuel de sprites, la rotation de sprites, l'ajout d'objets à l'inventaire, le retrait d'objets de l'inventaire, le level up du personnage principal, le fondu au noir de l'écran et le lancement d'effets de particules. Le lancement d'effets de particules supporte la génération dans une zone (plutôt qu'un point unique) et l'utilisation de plusieurs couleurs (chaque particule choisit aléatoirement une couleur parmi une liste).

#### Module `events.py`

Créer un nouveau module `src/moteur_jeu_presentation/game/events.py` contenant :

```python
from typing import Dict, List, Literal, Optional, Union
from pathlib import Path
from dataclasses import dataclass

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
    # Aucun champ requis : l'événement de level up est déclenché simplement pour indiquer
    # que le personnage principal a augmenté de niveau. L'affichage "level up (press u)"
    # sera automatiquement affiché au-dessus du nom du personnage principal (voir spécification 2).
    # Note importante : L'augmentation de niveau est toujours de +1 (le niveau du personnage augmente
    # de 1, sans dépasser MAX_PLAYER_LEVEL). Il n'est pas possible de configurer une augmentation
    # différente (par exemple +2 ou +3).

@dataclass
class ScreenFadeEventConfig:
    """Configuration d'un événement de fondu au noir de l'écran."""
    fade_in_duration: float = 1.0  # Durée du fondu au noir en secondes (défaut: 1.0). L'écran devient progressivement noir sur cette durée
    text_fade_in_duration: float = 0.5  # Durée de l'apparition du texte sur le fond noir en secondes (défaut: 0.5). Le texte apparaît progressivement après le fade_in. Si 0.0, le texte apparaît instantanément
    text_display_duration: float = 1.0  # Durée d'affichage du texte sur le fond noir en secondes (défaut: 1.0). Le texte reste visible à opacité maximale pendant cette durée. Si 0.0, le texte disparaît immédiatement après son apparition
    text_fade_out_duration: float = 0.5  # Durée de la disparition du texte sur le fond noir en secondes (défaut: 0.5). Le texte disparaît progressivement avant le fade_out. Si 0.0, le texte disparaît instantanément
    fade_out_duration: float = 1.0  # Durée du fondu de retour en secondes (défaut: 1.0). L'écran redevient progressivement visible sur cette durée
    text: Optional[str] = None  # Texte optionnel à afficher en blanc centré au milieu de l'écran. Le texte apparaît après le fade_in (text_fade_in), reste visible (text_display), puis disparaît (text_fade_out) avant le fade_out. Si None, aucun texte n'est affiché et les phases de texte sont ignorées

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
    generation_duration: Optional[float] = None  # Durée de génération des particules en secondes (optionnel). Si spécifié, les particules sont générées progressivement sur cette durée au lieu d'être toutes créées immédiatement. Par exemple, si count = 100 et generation_duration = 2.0, environ 50 particules par seconde seront générées pendant 2 secondes. Si None, toutes les particules sont créées immédiatement (comportement par défaut). Doit être > 0 si spécifié

@dataclass
class EventTriggerConfig:
    """Configuration d'un déclencheur d'événement."""
    identifier: str  # Identifiant unique du déclencheur
    trigger_x: Optional[float] = None  # Position X que le joueur doit atteindre pour déclencher l'événement (optionnel). Si None, l'événement ne peut être déclenché que manuellement (par exemple via les dialogues de PNJ, voir spécification 12). Les événements sans trigger_x ne sont pas pris en compte dans la vérification basée sur la position du joueur dans update()
    event_type: Literal["npc_move", "npc_follow", "npc_stop_follow", "npc_magic_move", "sprite_hide", "sprite_show", "sprite_move", "sprite_move_perpetual", "sprite_rotate", "inventory_add", "inventory_remove", "level_up", "screen_fade", "particle_effect"]  # Type d'événement ("npc_move", "npc_follow", "npc_stop_follow", "npc_magic_move", "sprite_hide", "sprite_show", "sprite_move", "sprite_move_perpetual", "sprite_rotate", "inventory_add", "inventory_remove", "level_up", "screen_fade" ou "particle_effect")
    event_data: Union[NPCMoveEventConfig, NPCFollowEventConfig, NPCStopFollowEventConfig, NPCMagicMoveEventConfig, SpriteHideEventConfig, SpriteShowEventConfig, SpriteMoveEventConfig, SpriteMovePerpetualEventConfig, SpriteRotateEventConfig, InventoryAddEventConfig, InventoryRemoveEventConfig, LevelUpEventConfig, ScreenFadeEventConfig, ParticleEffectEventConfig]  # Données spécifiques à l'événement
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
        collision_system: Optional[CollisionSystem] = None,  # Système de collisions (obligatoire pour `sprite_move`, utilisé aussi pour les fades)
        player: Optional[Player] = None,  # Instance du joueur (obligatoire pour les événements d'inventaire et de level up)
        particle_system: Optional[ParticleSystem] = None,  # Système de particules (obligatoire pour les événements particle_effect, voir spécification 14)
    ) -> None:
        """Initialise le système de déclencheurs.
        
        Args:
            progress_tracker: Système de progression pour obtenir la position du joueur
            npcs: Dictionnaire des PNJ disponibles (clé = ID technique, valeur = instance NPC)
            layers_by_tag: Dictionnaire des layers indexés par tag (retourné par LevelLoader.create_parallax_layers)
            parallax_system: Système de parallaxe contenant les layers
            collision_system: Système de collisions. Peut rester None si l'on n'utilise ni `sprite_move` ni les options de suppression/restauration de collisions, mais il est requis pour gérer les passagers des plateformes mobiles.
            player: Instance du joueur (obligatoire pour les événements d'inventaire, de level up et de suivi de PNJ)
            particle_system: Système de particules (obligatoire pour les événements particle_effect, voir spécification 14)
        
        Note:
            Le système maintient un état interne pour gérer les animations de fondu au noir :
            - `_screen_fade_timer: float` : Timer global pour suivre la progression du fondu
            - `_screen_fade_phase: Literal["fade_in", "text_fade_in", "text_display", "text_fade_out", "fade_out", "none"]` : Phase actuelle du fondu
            - `_screen_fade_config: Optional[ScreenFadeEventConfig]` : Configuration du fondu actif (None si aucun fondu n'est actif)
        """
    
    def load_events(self, events_path: Path) -> None:
        """Charge un fichier de configuration d'événements.
        
        Args:
            events_path: Chemin vers le fichier .event ou .toml
            
        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            ValueError: Si le format du fichier est invalide
        """
    
    def update(self, dt: float) -> None:
        """Met à jour le système et exécute les événements déclenchés.
        
        Gère notamment les animations de fade out pour les événements de type `sprite_hide`,
        les animations de fade in pour les événements de type `sprite_show` et `npc_magic_move`,
        les trajectoires linéaires des événements `sprite_move` et `sprite_move_perpetual`, et les animations de fondu
        au noir pour les événements de type `screen_fade`.
        Vérifie les déclencheurs basés sur la position du joueur (uniquement pour les événements
        avec un `trigger_x` défini). Les événements sans `trigger_x` ne sont pas pris en compte
        dans cette vérification et doivent être déclenchés manuellement (par exemple via les dialogues).
        
        Args:
            dt: Delta time en secondes
        """
    
    def reset(self) -> None:
        """Réinitialise l'état du système (tous les événements redeviennent disponibles).
        
        Réinitialise également les animations de fondu au noir en cours.
        """
    
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
    
    def _execute_event(self, event: EventTriggerConfig) -> None:
        """Exécute un événement déclenché.
        
        Cette méthode interne est appelée par `update()` et `trigger_event_by_identifier()`
        pour exécuter l'action associée à un événement.
        
        Args:
            event: Configuration de l'événement à exécuter
        
        Note:
            Cette méthode doit appeler la méthode d'exécution appropriée selon le type d'événement :
            - `"npc_move"` → `_execute_npc_move()`
            - `"npc_follow"` → `_execute_npc_follow()`
            - `"npc_stop_follow"` → `_execute_npc_stop_follow()`
            - `"npc_magic_move"` → `_execute_npc_magic_move()`
            - `"sprite_hide"` → `_execute_sprite_hide()`
            - `"sprite_show"` → `_execute_sprite_show()`
            - `"sprite_move"` → `_execute_sprite_move()`
            - `"sprite_move_perpetual"` → `_execute_sprite_move_perpetual()`
            - `"sprite_rotate"` → `_execute_sprite_rotate()`
            - `"inventory_add"` → `_execute_inventory_add()`
            - `"inventory_remove"` → `_execute_inventory_remove()`
            - `"level_up"` → `_execute_level_up()`
            - `"screen_fade"` → `_execute_screen_fade()`
            - `"particle_effect"` → `_execute_particle_effect()`
        """
    
    def _execute_sprite_show(self, event_data: SpriteShowEventConfig) -> None:
        """Exécute un événement d'affichage de sprite.
        
        Cette méthode initialise l'animation de fade in pour les layers
        associées au tag spécifié.
        
        Args:
            event_data: Configuration de l'événement d'affichage de sprite
        
        Raises:
            ValueError: Si le tag spécifié n'existe pas dans layers_by_tag
        """

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
    
    def _execute_level_up(self, event_data: LevelUpEventConfig) -> None:
        """Exécute un événement de level up.
        
        Cette méthode appelle `player.show_level_up()` pour activer l'affichage
        "level up (press u)" au-dessus du nom du personnage principal.
        
        Args:
            event_data: Configuration de l'événement de level up (non utilisée, mais conservée pour cohérence)
        
        Raises:
            ValueError: Si l'instance `Player` n'est pas fournie au constructeur
        """
    
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
    
    def get_screen_fade_phase(self) -> str:
        """Retourne la phase actuelle du fondu au noir.
        
        Cette méthode permet au système de dialogue de connaître la phase exacte
        du fondu pour détecter les transitions entre phases (notamment la transition
        vers fade_out pour déclencher le passage automatique à l'échange suivant).
        
        Returns:
            La phase actuelle du fondu ("fade_in", "text_fade_in", "text_display", "text_fade_out", "fade_out", ou "none")
        """
    
    def has_active_screen_fade(self) -> bool:
        """Vérifie si un fondu au noir est actuellement en cours.
        
        Cette méthode permet au système de dialogue de vérifier si un fondu au noir
        est en cours avant de permettre le passage à l'échange suivant.
        
        Returns:
            True si un fondu au noir est actuellement en cours (phase fade_in, black ou fade_out),
            False sinon (phase none ou aucun fondu actif)
        
        Note:
            Cette méthode doit être utilisée par le système de dialogue pour bloquer le passage
            manuel (clic) à l'échange suivant tant que le fondu n'est pas terminé. Voir la
            spécification 12 pour plus de détails sur l'intégration avec les dialogues.
        """
    
    def _execute_screen_fade(self, event_data: ScreenFadeEventConfig) -> None:
        """Exécute un événement de fondu au noir de l'écran.
        
        Cette méthode initialise l'animation de fondu au noir avec trois phases :
        1. Fondu au noir (fade_in_duration) : l'écran devient progressivement noir
        2. Écran noir complet (black_duration) : l'écran reste complètement noir
        3. Fondu de retour (fade_out_duration) : l'écran redevient progressivement visible
        
        Si un texte est configuré, il est affiché en blanc centré au milieu de l'écran
        pendant toute la durée du fondu (les trois phases combinées).
        
        Args:
            event_data: Configuration de l'événement de fondu au noir
        """
```

#### Format TOML du fichier d'événements

Le fichier d'événements utilise le format TOML et est nommé avec l'extension `.event` ou `.toml`. Il suit la même convention que les fichiers `.pnj` (un fichier par niveau).

```toml
# Fichier : levels/niveau_plateforme.event
# Configuration des événements pour le niveau

[[events]]
identifier = "robot_move_01"
trigger_x = 2000.0
event_type = "npc_move"

[events.event_data]
npc_id = "robot_01"
target_x = 2500.0
direction = "right"
move_speed = 300.0
move_animation_row = 0  # Optionnel : ligne du sprite sheet pour l'animation
move_animation_frames = 4  # Optionnel : nombre de frames pour l'animation

[[events]]
identifier = "marchand_retreat"
trigger_x = 1500.0
event_type = "npc_move"

[events.event_data]
npc_id = "marchand_01"
target_x = 1000.0
direction = "left"
move_speed = 250.0

[[events]]
identifier = "hide_obstacle_01"
trigger_x = 3000.0
event_type = "sprite_hide"

[events.event_data]
sprite_tag = "obstacle_removable"
fade_duration = 2.0  # Disparaît progressivement sur 2 secondes
remove_collisions = true  # Supprime les collisions une fois masqué

# Exemple d'événement d'ajout d'objet à l'inventaire
[[events]]
identifier = "give_document_etoile"
trigger_x = 1500.0
event_type = "inventory_add"

[events.event_data]
item_id = "document_etoile"
quantity = 1

# Exemple d'événement de retrait d'objet de l'inventaire
[[events]]
identifier = "remove_loupe_magique"
trigger_x = 4000.0
event_type = "inventory_remove"

[events.event_data]
item_id = "loupe_magique"
quantity = 1

# Exemple d'événement sans trigger_x (déclenché uniquement par les dialogues)
[[events]]
identifier = "hide_terrain_block_1200"
# trigger_x non spécifié : cet événement ne peut être déclenché que manuellement (par exemple via les dialogues)
event_type = "sprite_hide"

[events.event_data]
sprite_tag = "obstacle_removable"
fade_duration = 1.0
remove_collisions = true

# Exemple d'événement d'affichage de sprite
[[events]]
identifier = "show_terrain_block_1500"
trigger_x = 1500.0
event_type = "sprite_show"

[events.event_data]
sprite_tag = "obstacle_revealed"
fade_duration = 1.5  # Apparaît progressivement sur 1.5 secondes
restore_collisions = true  # Restaure les collisions une fois affiché

# Exemple d'événement de déplacement de sprite
[[events]]
identifier = "move_secret_platform"
trigger_x = 4200.0
event_type = "sprite_move"

[events.event_data]
sprite_tag = "platform_secret_tag"
move_x = 320.0   # La plateforme avance de 320 px vers la droite
move_y = -80.0   # Puis monte de 80 px
move_speed = 220.0  # Mouvement homogène à 220 px/s

# Exemple d'événement de déplacement perpétuel de sprite (plateforme qui oscille)
[[events]]
identifier = "oscillating_platform"
trigger_x = 1500.0
event_type = "sprite_move_perpetual"

[events.event_data]
sprite_tag = "oscillating_platform_tag"
move_x = 200.0   # La plateforme oscille horizontalement de 200 px (va de sa position initiale à position_initial + 200, puis revient)
move_y = 0.0     # Pas de mouvement vertical
move_speed = 150.0  # Vitesse de 150 px/s dans les deux sens

# Exemple d'événement de rotation de sprite
[[events]]
identifier = "rotate_windmill"
trigger_x = 2000.0
event_type = "sprite_rotate"

[events.event_data]
sprite_tag = "windmill_blades"
rotation_speed = 90.0  # Rotation de 90 degrés par seconde dans le sens horaire
duration = 5.0  # La rotation dure 5 secondes, puis s'arrête

# Exemple d'événement de rotation de sprite (sens antihoraire)
[[events]]
identifier = "rotate_gear_counterclockwise"
trigger_x = 3000.0
event_type = "sprite_rotate"

[events.event_data]
sprite_tag = "gear_mechanism"
rotation_speed = -45.0  # Rotation de 45 degrés par seconde dans le sens antihoraire (négatif)
duration = 10.0  # La rotation dure 10 secondes, puis s'arrête

# Exemple d'événement de level up (déclenché depuis un dialogue de PNJ)
[[events]]
identifier = "player_level_up"
# trigger_x non spécifié : cet événement ne peut être déclenché que manuellement (par exemple via les dialogues)
event_type = "level_up"
repeatable = true  # Cet événement peut être déclenché plusieurs fois (utile pour les dialogues répétés)

[events.event_data]
# Aucun champ requis pour les événements de level up
# Note : L'augmentation de niveau est toujours de +1 (le niveau du personnage augmente de 1, sans dépasser MAX_PLAYER_LEVEL)

# Exemple d'événement de suivi du personnage principal par un PNJ
[[events]]
identifier = "robot_follow_player"
trigger_x = 2500.0
event_type = "npc_follow"

[events.event_data]
npc_id = "robot_01"
follow_distance = 120.0  # Le PNJ se positionne à 120 pixels derrière le joueur
follow_speed = 180.0  # Vitesse de déplacement lors du suivi
animation_row = 1  # Optionnel : ligne du sprite sheet pour l'animation de suivi
animation_frames = 4  # Optionnel : nombre de frames pour l'animation de suivi

# Exemple d'événement d'arrêt du suivi du personnage principal par un PNJ
[[events]]
identifier = "robot_stop_follow"
trigger_x = 5000.0
event_type = "npc_stop_follow"

[events.event_data]
npc_id = "robot_01"  # Le PNJ s'arrête à sa position actuelle

# Exemple d'événement de téléportation magique de PNJ (disparition/réapparition)
[[events]]
identifier = "wizard_teleport"
trigger_x = 3500.0
event_type = "npc_magic_move"

[events.event_data]
npc_id = "wizard_01"
target_x = 4000.0  # Position X où le PNJ réapparaît
target_y = 500.0   # Position Y où le PNJ réapparaît
sprite_sheet_path = "sprite/wizard_teleport.png"  # Optionnel : nouveau sprite sheet
fade_in_duration = 1.5  # Apparition progressive sur 1.5 secondes
animation_row = 2  # Optionnel : ligne du sprite sheet à utiliser lors de la réapparition
animation_start = 0  # Optionnel : frame de départ du sprite à afficher (0-indexed)
direction = "right"  # Optionnel : direction du PNJ lors de la réapparition ("left" ou "right")

# Exemple d'événement de fondu au noir avec texte
[[events]]
identifier = "fade_to_black_chapter_2"
trigger_x = 5000.0
event_type = "screen_fade"

[events.event_data]
fade_in_duration = 1.0  # Fondu au noir sur 1 seconde
text_fade_in_duration = 0.5  # Apparition du texte sur 0.5 seconde
text_display_duration = 2.0  # Texte visible pendant 2 secondes
text_fade_out_duration = 0.5  # Disparition du texte sur 0.5 seconde
fade_out_duration = 1.0 # Fondu de retour sur 1 seconde
text = "Chapitre 2"      # Texte affiché en blanc centré (apparaît, reste visible, puis disparaît)

# Exemple d'événement de lancement d'effet de particules (point unique, couleur unique)
[[events]]
identifier = "explosion_at_checkpoint"
trigger_x = 3000.0
event_type = "particle_effect"

[events.event_data]
effect_type = "explosion"  # Type d'effet : "explosion", "confetti", "flame_explosion", "rain", "smoke" ou "sparks"
x = 3200.0  # Position X où l'effet est lancé (coordonnées monde du design 1920x1080)
y = 500.0   # Position Y où l'effet est lancé (coordonnées monde du design 1920x1080)
count = 30  # Optionnel : nombre de particules (si non spécifié, utilise la valeur par défaut du type d'effet)
speed = 350.0  # Optionnel : vitesse de base en pixels/seconde
lifetime = 0.5  # Optionnel : durée de vie en secondes
size = 18  # Optionnel : taille de base en pixels (diamètre)
color = [255, 200, 0]  # Optionnel : couleur RGB (si non spécifié, utilise la couleur par défaut). Note: ignoré pour "flame_explosion" et "confetti"

# Exemple d'événement avec plusieurs couleurs (chaque particule choisit aléatoirement une couleur)
[[events]]
identifier = "multicolor_explosion"
trigger_x = 4000.0
event_type = "particle_effect"

[events.event_data]
effect_type = "explosion"
x = 4000.0
y = 600.0
count = 40
colors = [[255, 0, 0], [255, 165, 0], [255, 255, 0], [0, 255, 0], [0, 0, 255]]  # Rouge, orange, jaune, vert, bleu
# Chaque particule choisit aléatoirement une couleur parmi cette liste

# Exemple d'événement avec zone de génération (particules générées dans une zone rectangulaire)
[[events]]
identifier = "rain_in_area"
trigger_x = 2000.0
event_type = "particle_effect"

[events.event_data]
effect_type = "rain"
spawn_area = { x_min = 2000.0, x_max = 3000.0, y_min = 0.0, y_max = 200.0 }  # Zone de génération (coordonnées monde du design 1920x1080)
count = 100  # Plus de particules pour couvrir la zone
# Les particules sont générées aléatoirement dans cette zone au lieu d'un point unique

# Exemple d'événement avec zone de génération et plusieurs couleurs
[[events]]
identifier = "multicolor_zone_explosion"
trigger_x = 6000.0
event_type = "particle_effect"

[events.event_data]
effect_type = "explosion"
spawn_area = { x_min = 6000.0, x_max = 6500.0, y_min = 400.0, y_max = 600.0 }  # Zone de génération
count = 50
colors = [[255, 100, 100], [100, 255, 100], [100, 100, 255], [255, 255, 100]]  # Rose, vert clair, bleu clair, jaune clair
# Les particules sont générées aléatoirement dans la zone et chaque particule choisit aléatoirement une couleur

# Exemple d'événement de confetti (couleur ignorée, utilise une palette prédéfinie)
[[events]]
identifier = "confetti_celebration"
trigger_x = 5000.0
event_type = "particle_effect"
repeatable = true  # Peut être déclenché plusieurs fois

[events.event_data]
effect_type = "confetti"
x = 5000.0
y = 200.0
# count, speed, lifetime, size optionnels (utilisent les valeurs par défaut)
# color et colors ignorés pour "confetti" (utilise une palette de couleurs festives prédéfinie)

# Exemple d'événement avec génération progressive (particules générées sur une durée)
[[events]]
identifier = "continuous_rain"
trigger_x = 3000.0
event_type = "particle_effect"
repeatable = true

[events.event_data]
effect_type = "rain"
spawn_area = { x_min = 3000.0, x_max = 5000.0, y_min = 0.0, y_max = 100.0 }
count = 200  # Nombre total de particules
generation_duration = 5.0  # Les particules sont générées progressivement sur 5 secondes (environ 40 particules/seconde)
# Les particules continuent d'apparaître pendant 5 secondes, créant un effet de pluie continue

# Exemple d'événement avec sprite_tag (particules générées dans la zone d'un sprite)
[[events]]
identifier = "smoke_from_chimney"
trigger_x = 4000.0
event_type = "particle_effect"
repeatable = true

[events.event_data]
effect_type = "smoke"
sprite_tag = "chimney"  # Tag du sprite (doit être défini dans le fichier .niveau)
# Les particules sont générées dans toute la zone couverte par le sprite avec ce tag
count = 30
speed = 50.0
lifetime = 3.0
# Les particules montent depuis la cheminée, créant un effet de fumée réaliste

# Exemple d'événement avec sprite_tag et spawn_edge (particules générées uniquement sur le bord supérieur)
[[events]]
identifier = "smoke_from_top"
trigger_x = 5000.0
event_type = "particle_effect"
repeatable = true

[events.event_data]
effect_type = "smoke"
sprite_tag = "machine"  # Tag du sprite
spawn_edge = "top"  # Les particules sont générées uniquement le long du bord supérieur
count = 20
speed = 40.0
lifetime = 2.5
# Les particules montent depuis le haut de la machine, créant un effet de vapeur

# Exemple d'événement avec sprite_tag et spawn_edge "bottom" (particules générées depuis le bas)
[[events]]
identifier = "rain_from_cloud"
trigger_x = 6000.0
event_type = "particle_effect"
repeatable = true

[events.event_data]
effect_type = "rain"
sprite_tag = "cloud"  # Tag du nuage
spawn_edge = "bottom"  # Les particules sont générées uniquement le long du bord inférieur
count = 100
generation_duration = 3.0  # Pluie continue pendant 3 secondes
# Les particules tombent depuis le bas du nuage, créant un effet de pluie réaliste

# Exemple d'événement avec sprite_tag et spawn_edge "left" (particules générées depuis le côté gauche)
[[events]]
identifier = "sparks_from_left"
trigger_x = 7000.0
event_type = "particle_effect"
repeatable = true

[events.event_data]
effect_type = "sparks"
sprite_tag = "generator"  # Tag de la génératrice
spawn_edge = "left"  # Les particules sont générées uniquement le long du bord gauche
count = 25
speed = 400.0
lifetime = 0.3
colors = [[255, 200, 0], [255, 100, 0], [255, 255, 255]]  # Jaune, orange, blanc
# Les étincelles partent du côté gauche de la génératrice, créant un effet de court-circuit

# Exemple d'événement avec sprite_tag et spawn_edge "right" (particules générées depuis le côté droit)
[[events]]
identifier = "flame_from_right"
trigger_x = 8000.0
event_type = "particle_effect"
repeatable = true

[events.event_data]
effect_type = "flame_explosion"
sprite_tag = "torch"  # Tag de la torche
spawn_edge = "right"  # Les particules sont générées uniquement le long du bord droit
count = 15
speed = 300.0
lifetime = 0.5
# Les flammes partent du côté droit de la torche (la palette de couleurs prédéfinie est utilisée)

# Exemple d'événement avec direction personnalisée (étincelles vers la droite)
[[events]]
identifier = "sparks_to_right"
trigger_x = 9000.0
event_type = "particle_effect"
repeatable = true

[events.event_data]
effect_type = "sparks"
x = 9000.0
y = 500.0
count = 30
speed = 400.0
lifetime = 0.3
direction_angle = 0.0  # Vers la droite (0 radians = 0°)
direction_spread = 0.5  # Dispersion de ±0.5 radians (≈±28.6°) de part et d'autre
colors = [[255, 200, 0], [255, 100, 0], [255, 255, 255]]  # Jaune, orange, blanc
# Les étincelles partent vers la droite avec une dispersion limitée, créant un effet de court-circuit horizontal

# Exemple d'événement avec direction personnalisée (pluie oblique)
[[events]]
identifier = "oblique_rain"
trigger_x = 10000.0
event_type = "particle_effect"
repeatable = true

[events.event_data]
effect_type = "rain"
spawn_area = { x_min = 10000.0, x_max = 12000.0, y_min = 0.0, y_max = 200.0 }
count = 150
speed = 250.0
lifetime = 3.0
direction_angle = 1.2  # Angle oblique vers le bas-droite (≈69°)
direction_spread = 0.3  # Dispersion limitée pour un effet de pluie oblique cohérent
# La pluie tombe en diagonale vers la droite, créant un effet de vent latéral
```

**Champs de `[[events]]`** :
- `identifier` (obligatoire) : Identifiant unique du déclencheur
- `trigger_x` (optionnel) : Position X que le joueur doit atteindre pour déclencher l'événement (en pixels, position horizontale du joueur dans le monde). Si non spécifié, l'événement ne peut être déclenché que manuellement (par exemple via les dialogues de PNJ, voir spécification 12). Les événements sans `trigger_x` ne sont pas pris en compte dans la vérification basée sur la position du joueur dans `update()`
- `event_type` (obligatoire) : Type d'événement (`"npc_move"`, `"npc_follow"`, `"npc_stop_follow"`, `"npc_magic_move"`, `"sprite_hide"`, `"sprite_show"`, `"sprite_move"`, `"sprite_move_perpetual"`, `"inventory_add"`, `"inventory_remove"`, `"level_up"`, `"screen_fade"` ou `"particle_effect"`)
- `repeatable` (optionnel, défaut: `false`) : Si `true`, l'événement peut être déclenché plusieurs fois (utile pour les événements déclenchés depuis les dialogues qui doivent pouvoir se relancer lors de conversations répétées). Si `false` (défaut), l'événement ne peut être déclenché qu'une seule fois

**Champs de `[events.event_data]` (pour `event_type = "npc_move"`)** :
- `npc_id` (obligatoire) : Identifiant technique du PNJ (doit correspondre à un PNJ défini dans le fichier `.pnj` avec le même `id`)
- `target_x` (obligatoire) : Position X vers laquelle le PNJ doit se déplacer (en pixels)
- `direction` (obligatoire) : Sens de déplacement (`"left"` ou `"right"`). Change la direction du PNJ lors du déclenchement
- `move_speed` (optionnel, défaut: 300.0) : Vitesse de déplacement en pixels par seconde
- `move_animation_row` (optionnel) : Ligne du sprite sheet à utiliser pour l'animation de déplacement. Si non spécifié, utilise l'animation actuelle du PNJ
- `move_animation_frames` (optionnel) : Nombre de frames pour l'animation de déplacement. Si non spécifié, utilise la configuration d'animation existante du PNJ

**Champs de `[events.event_data]` (pour `event_type = "npc_follow"`)** :
- `npc_id` (obligatoire) : Identifiant technique du PNJ (doit correspondre à un PNJ défini dans le fichier `.pnj` avec le même `id`)
- `follow_distance` (optionnel, défaut: 100.0) : Distance horizontale à maintenir derrière le joueur en pixels. Le PNJ se positionne à cette distance derrière le joueur (à droite si le joueur va à gauche, à gauche si le joueur va à droite)
- `follow_speed` (optionnel, défaut: 200.0) : Vitesse de déplacement lors du suivi en pixels par seconde
- `animation_row` (optionnel) : Ligne du sprite sheet à utiliser pour l'animation de suivi. Si non spécifié, utilise l'animation "walk" si disponible, sinon l'animation actuelle du PNJ
- `animation_frames` (optionnel) : Nombre de frames pour l'animation de suivi. Si non spécifié, utilise la configuration d'animation existante du PNJ

**Champs de `[events.event_data]` (pour `event_type = "npc_stop_follow"`)** :
- `npc_id` (obligatoire) : Identifiant technique du PNJ (doit correspondre à un PNJ défini dans le fichier `.pnj` avec le même `id`). Le PNJ s'arrête à sa position actuelle et reprend son comportement normal (animation idle, etc.)

**Champs de `[events.event_data]` (pour `event_type = "npc_magic_move"`)** :
- `npc_id` (obligatoire) : Identifiant technique du PNJ (doit correspondre à un PNJ défini dans le fichier `.pnj` avec le même `id`)
- `target_x` (obligatoire) : Position X où le PNJ doit réapparaître (en pixels, position monde)
- `target_y` (obligatoire) : Position Y où le PNJ doit réapparaître (en pixels, position monde)
- `sprite_sheet_path` (optionnel) : Chemin vers le sprite sheet à utiliser lors de la réapparition. Si non spécifié, utilise le sprite sheet actuel du PNJ. Le chemin est relatif au répertoire du niveau ou absolu
- `fade_in_duration` (optionnel, défaut: 1.0) : Durée de l'apparition progressive en secondes. Le PNJ apparaît progressivement (fade in) sur cette durée jusqu'à être complètement visible
- `animation_row` (optionnel) : Ligne du sprite sheet à utiliser lors de la réapparition (0-indexed). Si non spécifié, utilise l'animation actuelle du PNJ (ou la ligne 0 si aucune animation n'est active)
- `animation_start` (optionnel) : Frame de départ du sprite à afficher lors de la réapparition (0-indexed). Si non spécifié, utilise la frame actuelle du PNJ (ou la frame 0 si aucune animation n'est active). Utile pour afficher un sprite spécifique lors de la réapparition
- `direction` (optionnel) : Direction du PNJ lors de la réapparition (`"left"` ou `"right"`). Si non spécifié, conserve la direction actuelle du PNJ

**Champs de `[events.event_data]` (pour `event_type = "sprite_hide"`)** :
- `sprite_tag` (obligatoire) : Tag du sprite à masquer (doit correspondre à un tag défini dans le fichier `.niveau` avec le champ `tags`)
- `fade_duration` (optionnel, défaut: 1.0) : Durée de la disparition progressive en secondes. Le sprite disparaît progressivement (fade out) sur cette durée avant d'être complètement masqué
- `remove_collisions` (optionnel, défaut: `true`) : Si `true`, supprime les collisions du sprite une fois qu'il est complètement masqué. Si `false`, les collisions restent actives même si le sprite n'est plus visible

**Champs de `[events.event_data]` (pour `event_type = "sprite_show"`)** :
- `sprite_tag` (obligatoire) : Tag du sprite à afficher (doit correspondre à un tag défini dans le fichier `.niveau` avec le champ `tags`)
- `fade_duration` (optionnel, défaut: 1.0) : Durée de l'apparition progressive en secondes. Le sprite apparaît progressivement (fade in) sur cette durée jusqu'à être complètement visible
- `restore_collisions` (optionnel, défaut: `true`) : Si `true`, restaure les collisions du sprite une fois qu'il est complètement affiché. Si `false`, les collisions ne sont pas restaurées même si le sprite est visible

**Champs de `[events.event_data]` (pour `event_type = "sprite_move"`)** :
- `sprite_tag` (obligatoire) : Tag du sprite (ou groupe de sprites) à déplacer. Tous les layers associés à ce tag seront animés de manière synchrone
- `move_x` (obligatoire) : Déplacement horizontal en pixels. La valeur peut être positive (vers la droite) ou négative (vers la gauche). La destination X est calculée au déclenchement via `position_actuelle + move_x`
- `move_y` (obligatoire) : Déplacement vertical en pixels. Valeurs positives = descente, valeurs négatives = montée. La destination Y est `position_actuelle + move_y`
- `move_speed` (optionnel, défaut: 250.0) : Vitesse scalaire en pixels par seconde appliquée à la trajectoire. Le mouvement est homogène : la projection sur X et Y conserve un ratio constant (même temps de parcours pour les deux axes). Si `move_speed` <= 0, le sprite est repositionné instantanément sur la destination

**Champs de `[events.event_data]` (pour `event_type = "sprite_move_perpetual"`)** :
- `sprite_tag` (obligatoire) : Tag du sprite (ou groupe de sprites) à déplacer. Tous les layers associés à ce tag seront animés de manière synchrone. Le mouvement perpétuel commence dès le déclenchement de l'événement
- `move_x` (obligatoire) : Déplacement horizontal en pixels depuis la position de départ. La valeur peut être positive (vers la droite) ou négative (vers la gauche). Le sprite va de sa position initiale (capturée au déclenchement) à `position_initial + move_x`, puis revient à la position initiale, et le cycle se répète indéfiniment
- `move_y` (obligatoire) : Déplacement vertical en pixels depuis la position de départ. Valeurs positives = descente, valeurs négatives = montée. Le sprite va de sa position initiale (capturée au déclenchement) à `position_initial + move_y`, puis revient à la position initiale, et le cycle se répète indéfiniment
- `move_speed` (optionnel, défaut: 250.0) : Vitesse scalaire en pixels par seconde appliquée à la trajectoire. Le mouvement est homogène : la projection sur X et Y conserve un ratio constant (même temps de parcours pour les deux axes). Cette vitesse s'applique dans les deux sens (aller et retour). Si `move_speed` <= 0, le sprite est repositionné instantanément sur la destination et le mouvement perpétuel ne peut pas fonctionner correctement

**Champs de `[events.event_data]` (pour `event_type = "sprite_rotate"`)** :
- `sprite_tag` (obligatoire) : Tag du sprite (ou groupe de sprites) à faire tourner. Tous les layers associés à ce tag seront animés de manière synchrone. La rotation commence dès le déclenchement de l'événement
- `rotation_speed` (obligatoire) : Vitesse de rotation en degrés par seconde. Valeurs positives = sens horaire, valeurs négatives = sens antihoraire. Par exemple, `90.0` = 90 degrés par seconde dans le sens horaire, `-45.0` = 45 degrés par seconde dans le sens antihoraire
- `duration` (obligatoire) : Durée de la rotation en secondes. Après cette durée, la rotation s'arrête et le sprite reste à son angle final. Doit être > 0

**Champs de `[events.event_data]` (pour `event_type = "inventory_add"`)** :
- `item_id` (obligatoire) : ID technique de l'objet à ajouter (doit correspondre à un objet défini dans `inventory_items.toml`, voir spécification 13)
- `quantity` (optionnel, défaut: 1) : Quantité d'objets à ajouter. Doit être un entier positif

**Champs de `[events.event_data]` (pour `event_type = "inventory_remove"`)** :
- `item_id` (obligatoire) : ID technique de l'objet à retirer (doit correspondre à un objet défini dans `inventory_items.toml`, voir spécification 13)
- `quantity` (optionnel, défaut: 1) : Quantité d'objets à retirer. Doit être un entier positif. Si la quantité disponible est inférieure, l'événement échoue silencieusement (log un avertissement)

**Champs de `[events.event_data]` (pour `event_type = "level_up"`)** :
- Aucun champ requis : l'événement de level up ne nécessite pas de configuration supplémentaire. Lorsqu'il est déclenché, l'affichage "level up (press u)" apparaît automatiquement en jaune clignotant au-dessus du nom du personnage principal (voir spécification 2). Le joueur peut appuyer sur la touche `U` pour confirmer le level up et masquer l'affichage.

**Champs de `[events.event_data]` (pour `event_type = "screen_fade"`)** :
- `fade_in_duration` (optionnel, défaut: 1.0) : Durée du fondu au noir en secondes. L'écran devient progressivement noir sur cette durée (opacité passe de 0 à 255). Doit être > 0
- `text_fade_in_duration` (optionnel, défaut: 0.5) : Durée de l'apparition du texte sur le fond noir en secondes. Le texte apparaît progressivement (opacité passe de 0 à 255) après le fade_in. Si 0.0, le texte apparaît instantanément. Cette phase est ignorée si aucun texte n'est configuré. Doit être >= 0
- `text_display_duration` (optionnel, défaut: 1.0) : Durée d'affichage du texte sur le fond noir en secondes. Le texte reste visible à opacité maximale (opacité = 255) pendant cette durée. Si 0.0, le texte disparaît immédiatement après son apparition. Cette phase est ignorée si aucun texte n'est configuré. Doit être >= 0
- `text_fade_out_duration` (optionnel, défaut: 0.5) : Durée de la disparition du texte sur le fond noir en secondes. Le texte disparaît progressivement (opacité passe de 255 à 0) avant le fade_out. Si 0.0, le texte disparaît instantanément. Cette phase est ignorée si aucun texte n'est configuré. Doit être >= 0
- `fade_out_duration` (optionnel, défaut: 1.0) : Durée du fondu de retour en secondes. L'écran redevient progressivement visible sur cette durée (opacité passe de 255 à 0). Doit être > 0
- `text` (optionnel, défaut: `null`) : Texte à afficher en blanc centré au milieu de l'écran. Le texte apparaît après le fade_in (text_fade_in), reste visible (text_display), puis disparaît (text_fade_out) avant le fade_out. Si `null` ou non spécifié, aucun texte n'est affiché et les phases de texte sont ignorées. Le texte est rendu avec une police système (Arial/sans-serif) en gras, taille recommandée : 48-72 pixels dans le repère de conception 1920x1080, convertie vers la résolution de rendu

**Champs de `[events.event_data]` (pour `event_type = "particle_effect"`)** :
- `effect_type` (obligatoire) : Type d'effet de particules à lancer (`"explosion"`, `"confetti"`, `"flame_explosion"`, `"rain"`, `"smoke"` ou `"sparks"`). Voir spécification 14 pour les détails de chaque type d'effet
- `x` (optionnel) : Position X où l'effet doit être lancé (en pixels, coordonnées monde du design 1920x1080, converties automatiquement vers la résolution de rendu). Obligatoire si `spawn_area` et `sprite_tag` ne sont pas spécifiés. Si `sprite_tag` est spécifié, `x` est ignoré. Si `spawn_area` est spécifié (et `sprite_tag` n'est pas spécifié), `x` est ignoré
- `y` (optionnel) : Position Y où l'effet doit être lancé (en pixels, coordonnées monde du design 1920x1080, converties automatiquement vers la résolution de rendu). Obligatoire si `spawn_area` et `sprite_tag` ne sont pas spécifiés. Si `sprite_tag` est spécifié, `y` est ignoré. Si `spawn_area` est spécifié (et `sprite_tag` n'est pas spécifié), `y` est ignoré
- `spawn_area` (optionnel) : Zone de génération des particules. Si spécifié, les particules sont générées aléatoirement dans cette zone au lieu d'un point unique. Format : dictionnaire avec les clés `x_min`, `x_max`, `y_min`, `y_max` (en pixels, coordonnées monde du design 1920x1080). Si `sprite_tag` est spécifié, `spawn_area` est ignoré. Si `spawn_area` est spécifié (et `sprite_tag` n'est pas spécifié), `x` et `y` sont ignorés. Si `spawn_area` n'est pas spécifié et `sprite_tag` n'est pas spécifié, `x` et `y` doivent être fournis
- `sprite_tag` (optionnel) : Tag du sprite à utiliser comme zone d'émission des particules. Si spécifié, les particules sont générées dans la zone couverte par tous les sprites ayant ce tag. Le tag doit correspondre à un tag défini dans le fichier `.niveau` avec le champ `tags`. Si plusieurs sprites partagent le même tag, la zone d'émission est l'union des bounds de tous ces sprites. Si `sprite_tag` est spécifié, `spawn_area`, `x` et `y` sont ignorés. Les coordonnées sont calculées automatiquement à partir des positions et dimensions des sprites (en coordonnées monde du design 1920x1080, converties automatiquement vers la résolution de rendu)
- `spawn_edge` (optionnel) : Bord du sprite où limiter la génération des particules. Si spécifié, les particules sont générées uniquement le long du bord spécifié du sprite (ou des sprites si plusieurs partagent le tag). Valeurs possibles : `"top"` (bord supérieur, bande horizontale en haut), `"bottom"` (bord inférieur, bande horizontale en bas), `"left"` (bord gauche, bande verticale à gauche), `"right"` (bord droit, bande verticale à droite). Si `null` ou non spécifié, les particules sont générées dans toute la zone du sprite. **Nécessite que `sprite_tag` soit spécifié**, sinon est ignoré. Utile pour créer des effets spécifiques (par exemple, de la fumée qui monte depuis le haut d'un objet, de la pluie qui tombe depuis le bas d'un nuage, des étincelles qui partent des côtés d'une machine)
- `count` (optionnel) : Nombre de particules. Si `null` ou non spécifié, utilise la valeur par défaut du type d'effet (voir spécification 14)
- `speed` (optionnel) : Vitesse de base des particules en pixels/seconde. Si `null` ou non spécifié, utilise la valeur par défaut du type d'effet
- `lifetime` (optionnel) : Durée de vie des particules en secondes. Si `null` ou non spécifié, utilise la valeur par défaut du type d'effet
- `size` (optionnel) : Taille de base des particules en pixels (diamètre). Si `null` ou non spécifié, utilise la valeur par défaut du type d'effet
- `color` (optionnel, défaut: `null`, rétrocompatibilité) : Couleur de base des particules (RGB, tableau de 3 entiers `[r, g, b]`). Si `null` ou non spécifié et `colors` n'est pas spécifié, utilise la couleur par défaut du type d'effet. **Note importante** : Pour `"flame_explosion"` et `"confetti"`, la couleur est ignorée car ces effets utilisent des palettes de couleurs prédéfinies (voir spécification 14). Si `colors` est spécifié, `color` est ignoré
- `colors` (optionnel) : Liste de couleurs pour les particules (tableau de tableaux de 3 entiers `[[r, g, b], [r, g, b], ...]`). Si spécifié, chaque particule choisit aléatoirement une couleur parmi cette liste. Si `null` ou non spécifié, utilise `color` (ou la couleur par défaut du type d'effet). **Note importante** : Pour `"flame_explosion"` et `"confetti"`, `colors` est ignoré car ces effets utilisent des palettes de couleurs prédéfinies (voir spécification 14)
- `color_variation` (optionnel) : Variation de couleur (nombre décimal entre `0.0` et `1.0`). Si spécifié, chaque particule aura une variation aléatoire de couleur appliquée à sa couleur de base (ou à la couleur choisie dans la palette). `0.0` = aucune variation (couleur exacte), `1.0` = variation maximale (chaque composante RGB peut varier de ±255). Si `null` ou non spécifié, utilise la valeur par défaut du type d'effet (voir spécification 14). **Note importante** : Pour `"flame_explosion"` et `"confetti"`, `color_variation` est ignoré car ces effets utilisent des palettes de couleurs prédéfinies. Utile pour créer des effets plus naturels avec des nuances subtiles (par exemple, pour une fumée grise, mettre `color_variation = 0.0` pour éviter des couleurs indésirables)
- `generation_duration` (optionnel) : Durée de génération des particules en secondes. Si spécifié, les particules sont générées progressivement sur cette durée au lieu d'être toutes créées immédiatement. Par exemple, si `count = 100` et `generation_duration = 2.0`, environ 50 particules par seconde seront générées pendant 2 secondes. Si `null` ou non spécifié, toutes les particules sont créées immédiatement (comportement par défaut). Doit être > 0 si spécifié. Utile pour créer des effets plus fluides et naturels (pluie continue, explosion prolongée, fumée qui s'accumule progressivement)
- `direction_angle` (optionnel) : Angle de direction principal des particules en radians (nombre décimal). Si spécifié, remplace la direction par défaut du type d'effet. `0.0` = vers la droite, `π/2` (≈1.57) = vers le bas, `-π/2` (≈-1.57) = vers le haut, `π` (≈3.14) = vers la gauche. Si `null` ou non spécifié, utilise la direction par défaut du type d'effet (voir spécification 14). **Note importante** : Ce paramètre permet de personnaliser la direction des particules pour tous les types d'effets (`"explosion"`, `"rain"`, `"smoke"`, `"sparks"`, `"flame_explosion"`, `"confetti"`). Par exemple, pour des étincelles (`"sparks"`) qui partent vers la droite au lieu de vers le haut, utiliser `direction_angle = 0.0` avec `direction_spread = 0.5` pour un cône vers la droite
- `direction_spread` (optionnel) : Étalement de direction en radians (nombre décimal). Si spécifié, définit la dispersion angulaire autour de `direction_angle`. `0.0` = toutes les particules partent dans la même direction (pas de dispersion), `π/4` (≈0.79) = dispersion de 45° de part et d'autre, `2π` (≈6.28) = toutes les directions (360°). Si `null` ou non spécifié, utilise la valeur par défaut du type d'effet (voir spécification 14). **Note importante** : Ce paramètre fonctionne en combinaison avec `direction_angle` pour créer des effets directionnels personnalisés. Par exemple, pour des étincelles qui partent vers la droite avec une dispersion de 30° de part et d'autre, utiliser `direction_angle = 0.0` et `direction_spread = π/6` (≈0.52)

#### Comportement du déplacement de PNJ

Lorsqu'un événement de type `npc_move` est déclenché :

1. **Vérification** : Le système vérifie que le PNJ avec l'ID spécifié existe dans le dictionnaire des PNJ
2. **Changement de direction** : La direction du PNJ est mise à jour avec la valeur spécifiée dans `direction`
3. **Déplacement** : Le PNJ se déplace progressivement vers `target_x` à la vitesse `move_speed`
4. **Animation** : Si `move_animation_row` et `move_animation_frames` sont spécifiés, une animation temporaire est activée pendant le déplacement :
   - L'animation utilise la ligne `move_animation_row` du sprite sheet
   - L'animation contient `move_animation_frames` frames
   - L'animation est désactivée une fois que le PNJ a atteint sa destination
5. **Arrêt** : Le déplacement s'arrête lorsque le PNJ atteint `target_x` (avec une tolérance de quelques pixels pour éviter les oscillations)
6. **Rotation** : Si le PNJ atteint sa destination, une animation de rotation peut être jouée (à implémenter dans une version future)

**Important** :
- Par défaut, un événement ne peut être déclenché qu'une seule fois (pas de re-déclenchement automatique). Si le paramètre `repeatable` est défini à `true` dans le fichier `.event`, l'événement peut être déclenché plusieurs fois
- Si plusieurs événements ont le même `trigger_x`, ils sont tous déclenchés lorsque le joueur atteint cette position
- Les événements sans `trigger_x` ne sont pas pris en compte dans la vérification basée sur la position du joueur dans `update()`. Ils doivent être déclenchés manuellement via `trigger_event_by_identifier()` (par exemple depuis les dialogues de PNJ, voir spécification 12)
- Le déplacement du PNJ est indépendant de la gravité et des collisions (le PNJ se déplace horizontalement uniquement)
- Le PNJ conserve sa position Y actuelle pendant le déplacement

#### Comportement du suivi du personnage principal par un PNJ

Lorsqu'un événement de type `npc_follow` est déclenché :

1. **Vérification** : Le système vérifie que le PNJ avec l'ID spécifié existe dans le dictionnaire des PNJ et que l'instance `Player` est fournie au constructeur
2. **Démarrage du suivi** : La méthode `npc.start_following_player()` est appelée avec les paramètres de l'événement
3. **Positionnement automatique** : Le PNJ se positionne automatiquement derrière le personnage principal :
   - Si le joueur va à gauche (position X du joueur diminue), le PNJ se positionne à droite du joueur (à une distance `follow_distance` pixels)
   - Si le joueur va à droite (position X du joueur augmente), le PNJ se positionne à gauche du joueur (à une distance `follow_distance` pixels)
   - La position cible est recalculée à chaque frame en fonction de la position actuelle du joueur et de sa direction de déplacement
4. **Gestion automatique de la direction** : La direction du PNJ est automatiquement mise à jour en fonction de la direction du joueur :
   - Si le joueur va à gauche, le PNJ regarde vers la gauche (`direction = "left"`)
   - Si le joueur va à droite, le PNJ regarde vers la droite (`direction = "right"`)
   - La direction est déterminée en comparant la position X actuelle du joueur avec sa position X précédente
5. **Animation de suivi** : Si `animation_row` et `animation_frames` sont spécifiés, une animation temporaire est activée pendant le suivi. Sinon, l'animation "walk" est utilisée si disponible, ou l'animation actuelle est conservée
6. **Déplacement progressif** : Le PNJ se déplace progressivement vers sa position cible à la vitesse `follow_speed`
7. **Gravité** : La gravité s'applique en permanence au PNJ pendant le suivi. Si le PNJ se déplace au-dessus d'un vide, il tombe. Les collisions verticales sont résolues à chaque frame pour maintenir le PNJ au sol ou gérer les chutes
8. **Arrêt du suivi** : Le suivi continue jusqu'à ce qu'un événement de type `npc_follow` avec le même `npc_id` soit déclenché à nouveau (pour arrêter le suivi, il faudra implémenter un mécanisme futur) ou que la méthode `npc.stop_following_player()` soit appelée manuellement

**Important** :
- Par défaut, un événement ne peut être déclenché qu'une seule fois (pas de re-déclenchement automatique). Si le paramètre `repeatable` est défini à `true` dans le fichier `.event`, l'événement peut être déclenché plusieurs fois
- Si plusieurs événements ont le même `trigger_x`, ils sont tous déclenchés lorsque le joueur atteint cette position
- Les événements sans `trigger_x` ne sont pas pris en compte dans la vérification basée sur la position du joueur dans `update()`. Ils doivent être déclenchés manuellement via `trigger_event_by_identifier()` (par exemple depuis les dialogues de PNJ, voir spécification 12)
- Le suivi du joueur a la priorité sur les déplacements déclenchés par événements (`npc_move`). Si un PNJ suit le joueur, les déplacements déclenchés par événements sont ignorés jusqu'à ce que le suivi soit arrêté
- Le PNJ suit le joueur en permanence une fois l'événement déclenché, jusqu'à ce qu'un événement de type `npc_stop_follow` soit déclenché ou que la méthode `npc.stop_following_player()` soit appelée manuellement
- La direction du PNJ est automatiquement gérée en fonction de la direction du joueur, garantissant que le PNJ regarde toujours dans la bonne direction

#### Comportement de l'arrêt du suivi du personnage principal par un PNJ

Lorsqu'un événement de type `npc_stop_follow` est déclenché :

1. **Vérification** : Le système vérifie que le PNJ avec l'ID spécifié existe dans le dictionnaire des PNJ
2. **Arrêt du suivi** : La méthode `npc.stop_following_player()` est appelée pour arrêter le suivi automatique du personnage principal
3. **Position actuelle** : Le PNJ s'arrête à sa position actuelle (pas de déplacement supplémentaire)
4. **Comportement normal** : Le PNJ reprend son comportement normal :
   - L'animation de suivi est désactivée
   - L'animation normale reprend (idle par défaut)
   - Les propriétés de suivi sont réinitialisées
5. **Gravité** : La gravité continue de s'appliquer au PNJ comme pour toutes les entités

**Important** :
- Par défaut, un événement ne peut être déclenché qu'une seule fois (pas de re-déclenchement automatique). Si le paramètre `repeatable` est défini à `true` dans le fichier `.event`, l'événement peut être déclenché plusieurs fois
- Si plusieurs événements ont le même `trigger_x`, ils sont tous déclenchés lorsque le joueur atteint cette position
- Les événements sans `trigger_x` ne sont pas pris en compte dans la vérification basée sur la position du joueur dans `update()`. Ils doivent être déclenchés manuellement via `trigger_event_by_identifier()` (par exemple depuis les dialogues de PNJ, voir spécification 12)
- Si le PNJ n'est pas en train de suivre le joueur au moment où l'événement est déclenché, l'événement est ignoré silencieusement (log un avertissement)
- Après l'arrêt du suivi, le PNJ peut à nouveau être déplacé par des événements de type `npc_move` ou suivre à nouveau le joueur via un événement de type `npc_follow`

#### Comportement de la téléportation magique de PNJ

Lorsqu'un événement de type `npc_magic_move` est déclenché :

1. **Vérification** : Le système vérifie que le PNJ avec l'ID spécifié existe dans le dictionnaire des PNJ
2. **Disparition instantanée** : Le PNJ disparaît immédiatement (opacité mise à 0 instantanément, pas de fade out). Le PNJ devient invisible et n'est plus rendu à l'écran
3. **Désactivation temporaire** : Pendant la téléportation, la gravité et les collisions sont temporairement désactivées pour le PNJ :
   - La gravité ne s'applique pas au PNJ pendant la phase de réapparition
   - Le moteur de collision ignore le PNJ pendant cette phase
4. **Changement de sprite (optionnel)** : Si `sprite_sheet_path` est spécifié, le sprite sheet du PNJ est remplacé par le nouveau sprite sheet. Le chargement se fait immédiatement lors de la disparition
5. **Configuration de l'animation et de la direction** : 
   - Si `animation_row` est spécifié, la ligne du sprite sheet est définie pour l'affichage lors de la réapparition
   - Si `animation_start` est spécifié, la frame de départ est définie pour l'affichage lors de la réapparition
   - Si `direction` est spécifié, la direction du PNJ est mise à jour (`"left"` ou `"right"`)
   - Ces paramètres sont appliqués immédiatement lors de la disparition, avant le fade in
6. **Téléportation** : Le PNJ est repositionné instantanément à la position `(target_x, target_y)` (position monde). Le PNJ est marqué comme positionné (`_positioned = True`) et sa vélocité verticale est réinitialisée (`velocity_y = 0.0`) pour éviter que la logique d'initialisation ne le repositionne sur la mauvaise plateforme lors de la réactivation de la gravité. Si `target_y` est au-dessus d'un vide, la gravité normale fera tomber le PNJ une fois réactivée.
7. **Apparition progressive** : Le PNJ réapparaît progressivement via un fade in :
   - L'opacité commence à 0 et augmente progressivement jusqu'à 255 (complètement opaque)
   - La durée du fade in est contrôlée par `fade_in_duration` (défaut: 1.0 seconde)
   - L'opacité est mise à jour à chaque frame dans `update(dt)` : `opacity = int(255 * (1.0 - (timer / fade_in_duration)))` où `timer` décrémente de `fade_duration` à 0
8. **Réactivation de la gravité et des collisions** : Une fois que le fade in est terminé (opacité = 255) :
   - La gravité est réactivée pour le PNJ
   - Le moteur de collision reprend son rôle normal et détecte les collisions du PNJ
   - Le PNJ peut tomber si la position `target_y` est au-dessus d'un vide, ou être maintenu au sol si la position est sur une plateforme

**Note sur l'implémentation de l'opacité** :
- La classe `NPC` doit être étendue pour supporter l'opacité. Deux approches possibles :
  1. **Approche 1 (recommandée)** : Ajouter un attribut `alpha: int` (0-255) à la classe `NPC` et modifier la méthode de rendu pour appliquer l'opacité lors du dessin via `surface.set_alpha(alpha)` avant le `blit()`.
  2. **Approche 2** : Modifier directement la surface du sprite avec `set_alpha()`, mais cela nécessite de créer une copie de la surface pour éviter de modifier l'original.
- L'approche 1 est recommandée car elle permet de conserver la surface originale intacte et de gérer l'opacité de manière non destructive.
- Le système d'événements met à jour l'opacité du PNJ en cours de téléportation à chaque frame dans `update(dt)`.

**Important** :
- Par défaut, un événement ne peut être déclenché qu'une seule fois (pas de re-déclenchement automatique). Si le paramètre `repeatable` est défini à `true` dans le fichier `.event`, l'événement peut être déclenché plusieurs fois
- Si plusieurs événements ont le même `trigger_x`, ils sont tous déclenchés lorsque le joueur atteint cette position
- Les événements sans `trigger_x` ne sont pas pris en compte dans la vérification basée sur la position du joueur dans `update()`. Ils doivent être déclenchés manuellement via `trigger_event_by_identifier()` (par exemple depuis les dialogues de PNJ, voir spécification 12)
- La disparition est instantanée (pas de fade out), mais la réapparition est progressive (fade in)
- Si `sprite_sheet_path` est spécifié, le nouveau sprite sheet doit être chargé et appliqué au PNJ. Le sprite sheet doit respecter les mêmes dimensions de sprite que le sprite sheet original (même `sprite_width` et `sprite_height`) pour que les animations fonctionnent correctement
- Si `animation_row` est spécifié, le PNJ affichera les sprites de cette ligne lors de la réapparition. Si `animation_start` est également spécifié, le PNJ commencera à afficher le sprite à cette frame. Ces paramètres permettent de contrôler précisément l'apparence du PNJ lors de la réapparition
- Si `direction` est spécifié, la direction du PNJ est mise à jour immédiatement lors de la téléportation. Cela permet de faire apparaître le PNJ dans une orientation spécifique (par exemple, face au joueur)
- Si le PNJ est en train de suivre le joueur ou d'effectuer un déplacement déclenché par événement au moment où l'événement `npc_magic_move` est déclenché, ces actions sont interrompues et le PNJ est téléporté
- Une fois la téléportation terminée (fade in complété), le PNJ conserve l'animation et la direction configurées (si spécifiées), puis reprend son comportement normal (soumis à la gravité et aux collisions)

#### Comportement du déplacement de sprite

Lorsqu'un événement de type `sprite_move` est déclenché :

1. **Sélection des layers** : `layers_by_tag[sprite_tag]` est récupéré. Si aucun layer ne correspond, une erreur est loggée et l'événement est ignoré.
2. **Initialisation** :
   - Pour chaque layer, le système échantillonne immédiatement la position de départ.
   - La destination est calculée en ajoutant `move_x` / `move_y`.
   - Un `SpriteMovementTask` est créé avec : le vecteur direction, la distance restante et la vitesse `move_speed`.
3. **Mise à jour frame par frame** :
   - Chaque tâche calcule `delta_distance = min(move_speed * dt, distance_restante)`.
   - Les deltas `delta_x` et `delta_y` sont appliqués simultanément pour conserver un mouvement homogène.
   - `collision_system.on_layer_translated(layer, delta_x, delta_y)` est appelé afin de mettre à jour les structures de collision.
4. **Gestion des passagers** :
   - Dès qu'une entité (joueur ou PNJ) se trouve sur la **face supérieure** du sprite (overlap horizontal > 40% + tolérance verticale de 6 px), le collision system la marque `attached_platform = layer`.
   - Tant que l'entité est attachée :
     - **Mouvement horizontal indépendant** : Le joueur peut se déplacer horizontalement (X) en utilisant les touches de direction, même lorsqu'il est attaché à la plateforme. Le mouvement horizontal est traité normalement par le système de collisions.
     - **Mouvement de la plateforme** : Le déplacement de la plateforme (à la fois `delta_x` et `delta_y`) est appliqué à l'entité. Le joueur suit donc la plateforme en X et Y, tout en pouvant se déplacer horizontalement de manière indépendante via les touches. Cela permet au joueur de marcher sur la plateforme tout en étant transporté par elle.
   - Le détachement survient si :
     - L'entité saute / tombe (l'état `is_on_ground` passe à `False`)
     - L'overlap supérieur disparaît
     - La tâche se termine (tous les passagers restants sont relâchés)
5. **Collisions supérieures** :
   - Si le sprite vient heurter le joueur ou un PNJ par en dessous et atteint leur rectangle sur la face supérieure, l'entité est immédiatement attachée puis transportée.
   - Le sprite ne pousse pas latéralement : seules les entités situées sur la face supérieure sont verrouillées.
6. **Fin de tâche** : Une tolérance de 1 pixel est utilisée pour déterminer la fin du mouvement. Les coordonnées finales sont forcées sur la destination exacte pour éviter toute dérive.

**Contraintes** :
- `collision_system` devient obligatoire pour utiliser ce type d'événement, car il gère la détection des passagers et leur translation.
- Plusieurs layers peuvent partager le même tag : ils se déplacent en parallèle avec le même profil.
- Les déplacements sont déterministes (mêmes inputs → même trajectoire) car les deltas sont clampés par la distance restante.

#### Comportement du déplacement perpétuel de sprite

Lorsqu'un événement de type `sprite_move_perpetual` est déclenché :

1. **Sélection des layers** : `layers_by_tag[sprite_tag]` est récupéré. Si aucun layer ne correspond, une erreur est loggée et l'événement est ignoré.
2. **Initialisation** :
   - Pour chaque layer, le système échantillonne immédiatement la position de départ (position initiale).
   - La destination est calculée en ajoutant `move_x` / `move_y` à la position initiale.
   - Un `SpritePerpetualMovementTask` est créé avec : la position de départ, la position de destination, le vecteur direction, la distance totale et la vitesse `move_speed`.
   - Le mouvement commence en direction de la destination (phase "aller").
3. **Mise à jour frame par frame** :
   - Chaque tâche calcule `delta_distance = min(move_speed * dt, distance_restante)`.
   - Les deltas `delta_x` et `delta_y` sont appliqués simultanément pour conserver un mouvement homogène.
   - `collision_system.on_layer_translated(layer, delta_x, delta_y)` est appelé afin de mettre à jour les structures de collision.
   - Lorsque la destination est atteinte (avec une tolérance de 1 pixel), la direction est inversée et le sprite commence à revenir vers la position de départ (phase "retour").
   - Lorsque la position de départ est atteinte (avec une tolérance de 1 pixel), la direction est à nouveau inversée et le cycle reprend (retour à la phase "aller").
   - Le mouvement continue indéfiniment entre ces deux positions.
4. **Gestion des passagers** :
   - Dès qu'une entité (joueur ou PNJ) se trouve sur la **face supérieure** du sprite (overlap horizontal > 40% + tolérance verticale de 6 px), le collision system la marque `attached_platform = layer`.
   - Tant que l'entité est attachée :
     - **Mouvement horizontal indépendant** : Le joueur peut se déplacer horizontalement (X) en utilisant les touches de direction, même lorsqu'il est attaché à la plateforme. Le mouvement horizontal est traité normalement par le système de collisions.
     - **Mouvement de la plateforme** : Le déplacement de la plateforme (à la fois `delta_x` et `delta_y`) est appliqué à l'entité. Le joueur suit donc la plateforme en X et Y, tout en pouvant se déplacer horizontalement de manière indépendante via les touches. Cela permet au joueur de marcher sur la plateforme tout en étant transporté par elle.
   - Le détachement survient si :
     - L'entité saute / tombe (l'état `is_on_ground` passe à `False`)
     - L'overlap supérieur disparaît
     - L'événement est réinitialisé (tous les passagers restants sont relâchés)
5. **Collisions supérieures** :
   - Si le sprite vient heurter le joueur ou un PNJ par en dessous et atteint leur rectangle sur la face supérieure, l'entité est immédiatement attachée puis transportée.
   - Le sprite ne pousse pas latéralement : seules les entités situées sur la face supérieure sont verrouillées.
6. **Gestion de la fin de cycle** : Une tolérance de 1 pixel est utilisée pour déterminer l'atteinte de chaque position (départ ou destination). Les coordonnées sont forcées sur la position exacte pour éviter toute dérive avant d'inverser la direction.

**Contraintes** :
- `collision_system` devient obligatoire pour utiliser ce type d'événement, car il gère la détection des passagers et leur translation.
- Plusieurs layers peuvent partager le même tag : ils se déplacent en parallèle avec le même profil.
- Les déplacements sont déterministes (mêmes inputs → même trajectoire) car les deltas sont clampés par la distance restante.
- Le mouvement perpétuel continue indéfiniment jusqu'à ce que l'événement soit réinitialisé ou que le niveau soit rechargé.
- Si `move_speed` <= 0, le comportement est indéfini et peut causer des problèmes de performance. Il est recommandé d'utiliser une vitesse positive.

#### Comportement de la rotation de sprite

Lorsqu'un événement de type `sprite_rotate` est déclenché :

1. **Sélection des layers** : `layers_by_tag[sprite_tag]` est récupéré. Si aucun layer ne correspond, une erreur est loggée et l'événement est ignoré.
2. **Initialisation** :
   - Pour chaque layer, le système échantillonne immédiatement l'angle de rotation initial (par défaut 0.0 degrés).
   - Un `SpriteRotationTask` est créé avec : l'angle initial, la vitesse de rotation (`rotation_speed` en degrés par seconde), la durée totale (`duration` en secondes) et un timer initialisé à 0.
   - L'angle de rotation est stocké dans un attribut `rotation_angle` de la layer (en degrés, 0-360).
3. **Mise à jour frame par frame** :
   - Chaque tâche calcule l'angle de rotation à chaque frame : `rotation_angle = (rotation_angle + rotation_speed * dt) % 360.0`.
   - L'angle est mis à jour dans l'attribut `rotation_angle` de la layer.
   - Le timer est incrémenté de `dt`. Si le timer atteint `duration`, la rotation s'arrête et la tâche est supprimée.
   - La rotation est appliquée lors du rendu via `pygame.transform.rotate()` autour du centre du sprite.
4. **Rendu** :
   - Lors du rendu de la layer, si `rotation_angle != 0.0`, la surface est tournée avec `pygame.transform.rotate()`.
   - La rotation se fait autour du centre du sprite (centre de la surface originale).
   - Les coordonnées de rendu sont ajustées pour que le sprite reste à la même position visuelle (le centre reste fixe).
   - **Important** : La rotation peut modifier la taille de la surface (les coins du sprite original peuvent dépasser après rotation). Le système doit gérer cela en ajustant les coordonnées de rendu pour que le centre reste aligné.
5. **Fin de rotation** : Une fois la durée écoulée, la rotation s'arrête et le sprite reste à son angle final. L'angle final est conservé dans l'attribut `rotation_angle` de la layer.

**Note sur l'implémentation** :
- La classe `Layer` doit être étendue pour supporter la rotation :
  - Ajouter un attribut `rotation_angle: float` (en degrés, défaut: 0.0).
  - Ajouter un attribut `rotation_center: Tuple[float, float]` pour stocker le centre de rotation (calculé une fois au début : centre de la surface originale).
- Le système de parallaxe doit être modifié pour appliquer la rotation lors du rendu :
  - Dans `ParallaxSystem._get_layer_blit_commands()`, si `layer.rotation_angle != 0.0`, appliquer `pygame.transform.rotate()` avant le blit.
  - Ajuster les coordonnées de rendu pour que le centre du sprite reste à la même position visuelle.
- Un cache peut être utilisé pour éviter de recalculer la rotation à chaque frame si l'angle n'a pas changé (optimisation).
- Pour les sprites non infinis (`repeat = false`), la surface générée doit être serrée sur la boîte englobante réelle des sprites (min_x/min_y/max_x/max_y) et `world_y_offset` doit être positionné sur `min_y`. Si la surface couvre tout l'écran (ex. `screen_height`), la rotation se fera autour du centre de cette grande surface et le sprite semblera pivoter autour du centre de l'écran.

**Contraintes** :
- Plusieurs layers peuvent partager le même tag : elles tournent toutes en parallèle avec la même vitesse et durée.
- La rotation est appliquée progressivement frame par frame, créant une animation fluide.
- La vitesse de rotation peut être positive (sens horaire) ou négative (sens antihoraire).
- Une fois la durée écoulée, la rotation s'arrête et le sprite reste à son angle final.
- La rotation ne modifie pas les collisions : les rectangles de collision restent basés sur la surface originale (non tournée). Si nécessaire, les collisions peuvent être désactivées pour les sprites en rotation via un événement `sprite_hide` avec `remove_collisions = true` avant la rotation.

#### Comportement de l'ajout d'objet à l'inventaire

Lorsqu'un événement de type `inventory_add` est déclenché :

1. **Vérification** : Le système vérifie que le joueur est disponible (instance `Player` fournie au constructeur)
2. **Ajout** : L'objet est ajouté à l'inventaire du joueur via `player.inventory.add_item(item_id, quantity, animated=True)`
3. **Animation** : L'animation d'apparition progressive est automatiquement déclenchée (voir spécification 13)
4. **Gestion des erreurs** : Si l'objet n'existe pas dans la configuration d'inventaire, un avertissement est loggé et l'événement est ignoré

**Important** :
- L'événement nécessite que l'instance `Player` soit fournie au constructeur de `EventTriggerSystem`
- L'animation d'ajout est automatiquement déclenchée (paramètre `animated=True` par défaut)
- Si plusieurs événements d'ajout sont déclenchés simultanément, les objets sont ajoutés dans l'ordre de déclenchement

#### Comportement du retrait d'objet de l'inventaire

Lorsqu'un événement de type `inventory_remove` est déclenché :

1. **Vérification** : Le système vérifie que le joueur est disponible (instance `Player` fournie au constructeur)
2. **Vérification de la quantité** : Le système vérifie que l'inventaire contient suffisamment d'objets (`player.inventory.has_item(item_id, quantity)`)
3. **Retrait** : Si la quantité est suffisante, l'objet est retiré de l'inventaire via `player.inventory.remove_item(item_id, quantity, animated=True)`
4. **Animation** : L'animation de saut vers l'arrière puis disparition est automatiquement déclenchée (voir spécification 13)
5. **Gestion des erreurs** : Si la quantité est insuffisante ou si l'objet n'existe pas, un avertissement est loggé et l'événement est ignoré

**Important** :
- L'événement nécessite que l'instance `Player` soit fournie au constructeur de `EventTriggerSystem`
- L'animation de suppression est automatiquement déclenchée (paramètre `animated=True` par défaut)
- Si la quantité disponible est inférieure à la quantité demandée, l'événement échoue silencieusement (log un avertissement)

#### Comportement du fondu au noir de l'écran

Lorsqu'un événement de type `screen_fade` est déclenché :

1. **Initialisation** : Le système initialise un timer de fondu avec les phases suivantes :
   - Phase 1 (fade_in) : Durée = `fade_in_duration`, opacité de l'écran passe de 0 à 255 (écran devient progressivement noir)
   - Phase 2 (text_fade_in) : Durée = `text_fade_in_duration`, opacité du texte passe de 0 à 255 (texte apparaît progressivement sur le fond noir). Cette phase est ignorée si aucun texte n'est configuré
   - Phase 3 (text_display) : Durée = `text_display_duration`, opacité du texte reste à 255 (texte reste visible à opacité maximale). Cette phase est ignorée si aucun texte n'est configuré
   - Phase 4 (text_fade_out) : Durée = `text_fade_out_duration`, opacité du texte passe de 255 à 0 (texte disparaît progressivement). Cette phase est ignorée si aucun texte n'est configuré
   - Phase 5 (fade_out) : Durée = `fade_out_duration`, opacité de l'écran passe de 255 à 0 (écran redevient progressivement visible)
2. **Mise à jour frame par frame** : À chaque frame, dans `update(dt)` :
   - Le timer global est décrémenté de `dt`
   - L'opacité de l'écran est calculée selon la phase actuelle :
     - **Phase fade_in** : `opacity = int(255 * (1.0 - (timer / fade_in_duration)))` où `timer` décrémente de `fade_in_duration` à 0
     - **Phases text_fade_in, text_display, text_fade_out** : `opacity = 255` (écran reste complètement noir)
     - **Phase fade_out** : `opacity = int(255 * (timer / fade_out_duration))` où `timer` décrémente de `fade_out_duration` à 0
   - L'opacité du texte est calculée selon la phase actuelle (si un texte est configuré) :
     - **Phase text_fade_in** : `text_opacity = int(255 * (1.0 - (timer / text_fade_in_duration)))` où `timer` décrémente de `text_fade_in_duration` à 0
     - **Phase text_display** : `text_opacity = 255` (texte complètement visible)
     - **Phase text_fade_out** : `text_opacity = int(255 * (timer / text_fade_out_duration))` où `timer` décrémente de `text_fade_out_duration` à 0
     - **Autres phases** : `text_opacity = 0` (texte invisible)
   - Si le timer atteint 0 pour une phase, le système passe à la phase suivante
   - Si toutes les phases sont terminées, le fondu est terminé et l'opacité est fixée à 0
3. **Affichage du texte** : Si un texte est configuré (`text` n'est pas `None`), il est affiché en blanc centré au milieu de l'écran avec une opacité variable selon la phase :
   - Le texte apparaît progressivement pendant `text_fade_in_duration` (opacité passe de 0 à 255)
   - Le texte reste visible à opacité maximale pendant `text_display_duration` (opacité = 255)
   - Le texte disparaît progressivement pendant `text_fade_out_duration` (opacité passe de 255 à 0)
   - Le texte est rendu avec :
     - Police système (Arial/sans-serif) en gras
     - Taille recommandée : 48-72 pixels dans le repère de conception 1920x1080, convertie vers la résolution de rendu
     - Couleur blanche (255, 255, 255)
     - Opacité variable selon la phase (0-255)
     - Position : centré horizontalement et verticalement à l'écran (indépendamment de la position de la caméra)
4. **Rendu** : Le système de rendu doit appeler `get_screen_fade_state()` à chaque frame pour obtenir l'opacité actuelle de l'écran, le texte à afficher et l'opacité du texte. La méthode retourne un tuple `(alpha: int, text: Optional[str], text_alpha: int)`. L'overlay de fondu doit être dessiné **EN DERNIER**, après tous les autres éléments (joueur, PNJ, UI, bulles de dialogue, etc.) pour garantir que le fondu couvre l'écran entier.

**Note sur l'implémentation** :
- Le système maintient un état interne (`_screen_fade_timer`, `_screen_fade_phase`, `_screen_fade_config`) pour suivre la progression du fondu
- La méthode `get_screen_fade_state()` retourne `(alpha: int, text: Optional[str], text_alpha: int)` où :
  - `alpha` est l'opacité actuelle de l'écran (0-255), 0 signifie qu'aucun fondu n'est actif
  - `text` est le texte à afficher ou `None` si aucun texte n'est configuré ou si le fondu n'est pas actif
  - `text_alpha` est l'opacité actuelle du texte (0-255), 0 signifie que le texte est invisible
- Si plusieurs événements `screen_fade` sont déclenchés simultanément, seul le dernier déclenché est actif (les précédents sont remplacés)
- Le fondu peut être déclenché plusieurs fois si `repeatable = true` dans la configuration de l'événement
- Les phases de texte (text_fade_in, text_display, text_fade_out) sont automatiquement ignorées si aucun texte n'est configuré (`text` est `None`)

**Intégration avec le système de dialogues** :
- **Déclenchement depuis un dialogue** : Lorsqu'un événement `screen_fade` est déclenché depuis un dialogue (via `trigger_events` dans un échange), le système de dialogue doit automatiquement passer à l'échange suivant lorsque le fondu entre en phase `fade_out` (avant le fade_out). Voir la spécification 12 pour plus de détails sur l'implémentation.
- **Blocage du passage manuel** : Tant qu'un fondu au noir est en cours (vérifié via `has_active_screen_fade()`), le passage manuel à l'échange suivant (clic) est bloqué. Le clic est ignoré et l'utilisateur doit attendre la fin du fondu avant de pouvoir continuer le dialogue. Cette contrainte garantit que le fondu se termine complètement avant de permettre un nouveau passage manuel, améliorant la cohérence narrative et visuelle du jeu.
- **Passage automatique** : Lorsque le fondu entre en phase `fade_out` (détecté via `get_screen_fade_phase()`), si l'événement a été déclenché depuis un dialogue, le système de dialogue doit automatiquement passer à l'échange suivant. Le passage se fait **avant** le fade_out, permettant au nouveau dialogue de s'afficher pendant que l'écran redevient progressivement visible. Le système de dialogue doit surveiller la transition vers la phase `fade_out` (en comparant la phase actuelle avec la phase précédente) et appeler `_next_exchange()` automatiquement lors de cette transition.
- **Méthode de vérification** : Le système de dialogue doit interroger `EventTriggerSystem.has_active_screen_fade()` pour déterminer si un fondu est en cours. Cette vérification doit être effectuée dans `DialogueState.handle_event()` avant d'appeler `_next_exchange()` pour bloquer le passage manuel. Le système de dialogue doit également utiliser `EventTriggerSystem.get_screen_fade_phase()` dans `DialogueState.update()` pour détecter la transition vers la phase `fade_out` et déclencher le passage automatique.

**Important** :
- Par défaut, un événement ne peut être déclenché qu'une seule fois (pas de re-déclenchement automatique). Si le paramètre `repeatable` est défini à `true` dans le fichier `.event`, l'événement peut être déclenché plusieurs fois
- Si plusieurs événements ont le même `trigger_x`, ils sont tous déclenchés lorsque le joueur atteint cette position
- Les événements sans `trigger_x` ne sont pas pris en compte dans la vérification basée sur la position du joueur dans `update()`. Ils doivent être déclenchés manuellement via `trigger_event_by_identifier()` (par exemple depuis les dialogues de PNJ, voir spécification 12)
- Le fondu est progressif et fluide, créant un effet visuel agréable pour les transitions de scène
- Le texte est affiché pendant toute la durée du fondu (fade_in + black_duration + fade_out), permettant d'afficher des informations narratives pendant les transitions
- **Ordre de rendu (PRIORITÉ ABSOLUE)** : L'overlay de fondu doit être rendu **EN DERNIER**, après tous les autres éléments de l'interface, y compris les bulles de dialogue, l'interface des statistiques et l'animation de transition de niveau. Cela garantit que le fondu couvre l'écran entier et que le texte est toujours visible au-dessus de tous les autres éléments

#### Comportement du lancement d'effet de particules

Lorsqu'un événement de type `particle_effect` est déclenché :

1. **Vérification** : Le système vérifie que le système de particules est disponible (instance `ParticleSystem` fournie au constructeur). Si le système de particules n'est pas disponible, un avertissement est loggé et l'événement est ignoré.
2. **Détermination de la zone de génération** (priorité : `sprite_tag` > `spawn_area` > `x`/`y`) :
   - Si `sprite_tag` est spécifié : 
     - Le système récupère toutes les layers associées au tag depuis `layers_by_tag[sprite_tag]`. Si aucune layer n'est trouvée, une erreur est levée (`ValueError`) et l'événement est ignoré.
     - Pour chaque layer, le système calcule les bounds du sprite :
       - `x_min` = `layer.world_x_offset` (position horizontale de départ)
       - `x_max` = `layer.world_x_offset + layer.surface.get_width()` (ou `layer.world_x_offset + effective_width` si la layer se répète avec `infinite_offset`)
       - `y_min` = `layer.world_y_offset` (position verticale de départ, ou 0 si non défini)
       - `y_max` = `layer.world_y_offset + layer.surface.get_height()` (ou `layer.world_y_offset + layer.surface.get_height()` si `world_y_offset` est défini)
     - Si plusieurs layers partagent le même tag, l'union des bounds est calculée (min des mins, max des maxs) pour créer une zone d'émission couvrant tous les sprites.
     - Si `spawn_edge` est spécifié, la zone est limitée au bord spécifié :
       - `"top"` : `y_min` uniquement (bande horizontale de 1 pixel de hauteur en haut du sprite, largeur = `x_max - x_min`)
       - `"bottom"` : `y_max` uniquement (bande horizontale de 1 pixel de hauteur en bas du sprite, largeur = `x_max - x_min`)
       - `"left"` : `x_min` uniquement (bande verticale de 1 pixel de largeur à gauche du sprite, hauteur = `y_max - y_min`)
       - `"right"` : `x_max` uniquement (bande verticale de 1 pixel de largeur à droite du sprite, hauteur = `y_max - y_min`)
     - Les coordonnées sont en repère de conception (1920x1080) et sont converties vers le repère de rendu (1280x720) en multipliant par les facteurs d'échelle appropriés.
   - Sinon, si `spawn_area` est spécifié : Les particules sont générées aléatoirement dans la zone définie par `x_min`, `x_max`, `y_min`, `y_max` (en coordonnées monde du design 1920x1080). Chaque particule reçoit une position aléatoire dans cette zone lors de sa création. Les coordonnées de la zone sont converties du repère de conception vers le repère de rendu.
   - Sinon (point unique) : Les particules sont générées à partir du point unique défini par `x` et `y` (en coordonnées monde du design 1920x1080). Les coordonnées sont converties du repère de conception vers le repère de rendu en multipliant par le facteur d'échelle `RENDER_WIDTH / DESIGN_WIDTH = 1280 / 1920 ≈ 0.667`.
3. **Création de la configuration** : Selon le type d'effet (`effect_type`), une configuration d'effet de particules est créée :
   - Si `effect_type = "explosion"` : Utilise `create_explosion_config()` avec les paramètres optionnels fournis (ou valeurs par défaut)
   - Si `effect_type = "confetti"` : Utilise `create_confetti_config()` avec les paramètres optionnels fournis (ou valeurs par défaut). Les couleurs sont ignorées car cet effet utilise une palette de couleurs festives prédéfinie
   - Si `effect_type = "flame_explosion"` : Utilise `create_flame_explosion_config()` avec les paramètres optionnels fournis (ou valeurs par défaut). Les couleurs sont ignorées car cet effet utilise une palette de couleurs chaudes prédéfinie (rouge, orange, jaune)
   - Si `effect_type = "rain"` : Utilise `create_rain_config()` avec les paramètres optionnels fournis (ou valeurs par défaut)
   - Si `effect_type = "smoke"` : Utilise `create_smoke_config()` avec les paramètres optionnels fournis (ou valeurs par défaut)
   - Si `effect_type = "sparks"` : Utilise `create_sparks_config()` avec les paramètres optionnels fournis (ou valeurs par défaut)
4. **Application des paramètres optionnels** : Si des paramètres optionnels sont fournis (`count`, `speed`, `lifetime`, `size`), ils sont appliqués à la configuration créée. Si un paramètre n'est pas fourni, la valeur par défaut du type d'effet est utilisée (voir spécification 14 pour les valeurs par défaut de chaque type).
5. **Gestion des couleurs** :
   - Si `colors` est spécifié (et que l'effet n'est pas `"flame_explosion"` ou `"confetti"`) : La liste de couleurs est stockée et utilisée lors de la création des particules. Chaque particule choisit aléatoirement une couleur parmi cette liste lors de sa création. La configuration de base utilise la première couleur de la liste (ou la couleur par défaut si la liste est vide) pour la compatibilité avec le système de particules existant.
   - Si `colors` n'est pas spécifié mais `color` est spécifié (et que l'effet n'est pas `"flame_explosion"` ou `"confetti"`) : La couleur unique est appliquée à toutes les particules (rétrocompatibilité).
   - Si ni `colors` ni `color` ne sont spécifiés : La couleur par défaut du type d'effet est utilisée.
   - Pour `"flame_explosion"` et `"confetti"` : Les paramètres `color` et `colors` sont ignorés car ces effets utilisent des palettes de couleurs prédéfinies.
6. **Lancement de l'effet** :
   - Si `sprite_tag` est spécifié : La zone d'émission est calculée à partir des bounds des sprites avec ce tag. Si `spawn_edge` est spécifié, la zone est limitée au bord spécifié. L'effet de particules est créé avec cette zone comme `spawn_area` (convertie en repère de rendu). **Note d'implémentation** : Le système doit calculer les bounds de chaque layer associée au tag, prendre l'union si plusieurs layers partagent le tag, et limiter à un bord si `spawn_edge` est spécifié. Les coordonnées doivent être converties du repère de conception vers le repère de rendu.
   - Si `spawn_area` est spécifié (et `sprite_tag` n'est pas spécifié) : Pour chaque particule, une position aléatoire est générée dans la zone convertie. L'effet de particules est créé pour chaque particule individuellement (ou le système de particules est étendu pour supporter la génération dans une zone). **Note d'implémentation** : Le système de particules doit être étendu pour supporter la génération de particules dans une zone. Une approche possible est de modifier `ParticleEffect.__init__()` pour accepter une zone de génération et générer chaque particule à une position aléatoire dans cette zone.
   - Si ni `sprite_tag` ni `spawn_area` ne sont spécifiés (point unique) : L'effet de particules est créé et ajouté au système de particules via `particle_system.create_effect(x_render, y_render, config, effect_id=f"event_{identifier}")`. Toutes les particules sont générées au même point.
   - **Génération progressive** : Si `generation_duration` est spécifié, les particules sont générées progressivement sur cette durée au lieu d'être toutes créées immédiatement. Le système calcule le nombre de particules à générer à chaque frame en fonction du temps écoulé depuis le début de la génération. Par exemple, si `count = 100` et `generation_duration = 2.0`, le système génère environ `100 / 2.0 = 50` particules par seconde, soit environ `50 * dt` particules par frame. **Note d'implémentation** : Le système de particules doit être étendu pour supporter la génération progressive. Une approche possible est d'ajouter un attribut `generation_duration: Optional[float]` et `generation_timer: float` à `ParticleEffect`, de modifier `__init__()` pour ne pas appeler `_create_particles()` immédiatement si `generation_duration` est spécifié, et de modifier `update()` pour générer progressivement les particules restantes à chaque frame jusqu'à ce que toutes les particules soient créées ou que la durée de génération soit écoulée.
   - L'effet est immédiatement actif et les particules commencent à se déplacer selon leur configuration dès qu'elles sont créées.
7. **Gestion du cycle de vie** : Le système de particules gère automatiquement le cycle de vie des particules (mise à jour, rendu, suppression). L'effet est automatiquement supprimé lorsque toutes les particules sont mortes (durée de vie écoulée) et que la génération est terminée (si `generation_duration` est spécifié).

**Note sur l'implémentation** :
- La méthode `_execute_particle_effect()` doit être implémentée dans `EventTriggerSystem` pour gérer l'exécution de cet événement
- La méthode doit créer la configuration appropriée selon le type d'effet et appeler `particle_system.create_effect()` avec les coordonnées converties
- Les coordonnées sont converties du repère de conception vers le repère de rendu pour garantir que l'effet apparaît à la bonne position visuelle dans le jeu

**Implémentation de `_execute_particle_effect()`** :

```python
def _execute_particle_effect(self, event_data: ParticleEffectEventConfig) -> None:
    """Exécute un événement de lancement d'effet de particules."""
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
    from ..rendering.config import compute_design_scale
    
    # Déterminer la zone de génération (priorité : sprite_tag > spawn_area > x/y)
    design_scale_x, design_scale_y = compute_design_scale()
    
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
            layer_x_min = layer.world_x_offset
            layer_x_max = layer.world_x_offset + layer.surface.get_width()
            # Si la layer se répète avec infinite_offset, prendre en compte la largeur effective
            if layer.repeat and hasattr(layer, 'infinite_offset'):
                effective_width = layer.surface.get_width() + layer.infinite_offset
                if effective_width > 0:
                    layer_x_max = layer.world_x_offset + effective_width
            
            layer_y_min = getattr(layer, 'world_y_offset', 0.0)
            layer_y_max = layer_y_min + layer.surface.get_height()
            
            x_min_design = min(x_min_design, layer_x_min)
            x_max_design = max(x_max_design, layer_x_max)
            y_min_design = min(y_min_design, layer_y_min)
            y_max_design = max(y_max_design, layer_y_max)
        
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
        
        # Convertir en repère de rendu
        x_min_render = x_min_design * design_scale_x
        x_max_render = x_max_design * design_scale_x
        y_min_render = y_min_design * design_scale_y
        y_max_render = y_max_design * design_scale_y
        
        spawn_area_render = {
            "x_min": x_min_render,
            "x_max": x_max_render,
            "y_min": y_min_render,
            "y_max": y_max_render,
        }
        use_spawn_area = True
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
        use_spawn_area = True
    else:
        # Point unique : convertir les coordonnées
        if event_data.x is None or event_data.y is None:
            logger.error("particle_effect: x et y sont obligatoires si spawn_area et sprite_tag ne sont pas spécifiés")
            return
        x_render = event_data.x * design_scale_x
        y_render = event_data.y * design_scale_y
        use_spawn_area = False
    
    # Déterminer les couleurs à utiliser
    colors_to_use: Optional[List[Tuple[int, int, int]]] = None
    if event_data.effect_type not in ("flame_explosion", "confetti"):
        # Pour les effets qui supportent les couleurs personnalisées
        if event_data.colors is not None and len(event_data.colors) > 0:
            colors_to_use = event_data.colors
        elif event_data.color is not None:
            colors_to_use = [event_data.color]
        # Sinon, utiliser la couleur par défaut du type d'effet (sera géré lors de la création de la config)
    
    # Créer la configuration selon le type d'effet
    # Note: La couleur de base utilisée pour créer la config sera la première couleur de colors_to_use
    # ou color, ou la couleur par défaut. Les couleurs multiples seront appliquées lors de la création des particules.
    base_color = None
    if colors_to_use is not None and len(colors_to_use) > 0:
        base_color = colors_to_use[0]
    elif event_data.color is not None:
        base_color = event_data.color
    
    if event_data.effect_type == "explosion":
        config = create_explosion_config(
            count=event_data.count if event_data.count is not None else 24,
            speed=event_data.speed if event_data.speed is not None else 320.0,
            lifetime=event_data.lifetime if event_data.lifetime is not None else 0.4,
            size=event_data.size if event_data.size is not None else 16,
            color=base_color if base_color is not None else (255, 200, 0),
        )
    elif event_data.effect_type == "confetti":
        config = create_confetti_config(
            count=event_data.count if event_data.count is not None else 50,
            speed=event_data.speed if event_data.speed is not None else 400.0,
            lifetime=event_data.lifetime if event_data.lifetime is not None else 2.5,
            size=event_data.size if event_data.size is not None else 12,
        )
        # Les couleurs sont ignorées pour confetti (utilise une palette prédéfinie)
        colors_to_use = None
    elif event_data.effect_type == "flame_explosion":
        config = create_flame_explosion_config(
            count=event_data.count if event_data.count is not None else 24,
            speed=event_data.speed if event_data.speed is not None else 320.0,
            lifetime=event_data.lifetime if event_data.lifetime is not None else 0.4,
            size=event_data.size if event_data.size is not None else 16,
        )
        # Les couleurs sont ignorées pour flame_explosion (utilise une palette prédéfinie)
        colors_to_use = None
    elif event_data.effect_type == "rain":
        config = create_rain_config(
            count=event_data.count if event_data.count is not None else 50,
            speed=event_data.speed if event_data.speed is not None else 200.0,
            lifetime=event_data.lifetime if event_data.lifetime is not None else 2.0,
            size=event_data.size if event_data.size is not None else 4,
            color=base_color if base_color is not None else (150, 150, 255),
        )
    elif event_data.effect_type == "smoke":
        config = create_smoke_config(
            count=event_data.count if event_data.count is not None else 30,
            speed=event_data.speed if event_data.speed is not None else 50.0,
            lifetime=event_data.lifetime if event_data.lifetime is not None else 3.0,
            size=event_data.size if event_data.size is not None else 8,
            color=base_color if base_color is not None else (100, 100, 100),
        )
    elif event_data.effect_type == "sparks":
        config = create_sparks_config(
            count=event_data.count if event_data.count is not None else 15,
            speed=event_data.speed if event_data.speed is not None else 400.0,
            lifetime=event_data.lifetime if event_data.lifetime is not None else 0.3,
            size=event_data.size if event_data.size is not None else 6,
            color=base_color if base_color is not None else (255, 200, 0),
        )
    else:
        logger.error(f"Type d'effet de particules invalide: {event_data.effect_type}")
        return
    
    # Si plusieurs couleurs sont spécifiées, les stocker dans la configuration
    # Note: Le système de particules doit être étendu pour supporter les couleurs multiples.
    # Une approche possible est d'ajouter un attribut `color_palette: Optional[List[Tuple[int, int, int]]]`
    # à `ParticleEffectConfig` et de modifier `ParticleEffect._create_particles()` pour choisir
    # aléatoirement une couleur parmi la palette lors de la création de chaque particule.
    if colors_to_use is not None and len(colors_to_use) > 1:
        # Stocker la palette de couleurs dans la configuration (nécessite extension de ParticleEffectConfig)
        config.color_palette = colors_to_use  # À implémenter dans ParticleEffectConfig
    
    # Si generation_duration est spécifié, le stocker dans la configuration
    # Note: Le système de particules doit être étendu pour supporter la génération progressive.
    # Une approche possible est d'ajouter un attribut `generation_duration: Optional[float]` à `ParticleEffectConfig`,
    # d'ajouter `generation_timer: float` et `particles_created: int` à `ParticleEffect`, de modifier `__init__()`
    # pour ne pas appeler `_create_particles()` immédiatement si `generation_duration` est spécifié, et de modifier
    # `update()` pour générer progressivement les particules restantes à chaque frame.
    if event_data.generation_duration is not None:
        config.generation_duration = event_data.generation_duration  # À implémenter dans ParticleEffectConfig
    
    # Créer l'effet de particules
    if use_spawn_area:
        # Générer les particules dans une zone
        # Note: Le système de particules doit être étendu pour supporter la génération dans une zone.
        # Une approche possible est de modifier `ParticleSystem.create_effect()` pour accepter
        # un paramètre optionnel `spawn_area: Optional[Dict[str, float]]` et de modifier
        # `ParticleEffect.__init__()` pour générer chaque particule à une position aléatoire dans la zone.
        self.particle_system.create_effect(
            spawn_area_render["x_min"],  # Position de référence (coin supérieur gauche de la zone)
            spawn_area_render["y_min"],
            config,
            effect_id=f"event_particle_{id(event_data)}",
            spawn_area=spawn_area_render
        )
        if event_data.sprite_tag is not None:
            edge_info = f" (tag='{event_data.sprite_tag}'"
            if event_data.spawn_edge is not None:
                edge_info += f", edge='{event_data.spawn_edge}'"
            edge_info += ")"
            logger.info(
                f"Effet de particules '{event_data.effect_type}' lancé dans la zone du sprite{edge_info} "
                f"({spawn_area_render['x_min']:.2f}, {spawn_area_render['y_min']:.2f}) à "
                f"({spawn_area_render['x_max']:.2f}, {spawn_area_render['y_max']:.2f})"
            )
        else:
            logger.info(
                f"Effet de particules '{event_data.effect_type}' lancé dans la zone "
                f"({spawn_area_render['x_min']:.2f}, {spawn_area_render['y_min']:.2f}) à "
                f"({spawn_area_render['x_max']:.2f}, {spawn_area_render['y_max']:.2f})"
            )
    else:
        # Générer les particules à un point unique
        self.particle_system.create_effect(
            x_render,
            y_render,
            config,
            effect_id=f"event_particle_{id(event_data)}"
        )
        logger.info(f"Effet de particules '{event_data.effect_type}' lancé à ({x_render:.2f}, {y_render:.2f})")
```

**Important** :
- L'événement nécessite que l'instance `ParticleSystem` soit fournie au constructeur de `EventTriggerSystem`
- Les coordonnées `x`, `y`, les limites de `spawn_area` et les bounds des sprites (via `sprite_tag`) sont en repère de conception (1920x1080) et sont automatiquement converties vers le repère de rendu (1280x720)
- Si le système de particules n'est pas disponible, l'événement est ignoré silencieusement (log un avertissement, pas d'erreur levée)
- Les effets de particules sont gérés automatiquement par le système de particules (mise à jour, rendu, nettoyage)
- Pour `"flame_explosion"` et `"confetti"`, les paramètres `color` et `colors` sont ignorés car ces effets utilisent des palettes de couleurs prédéfinies (voir spécification 14)
- **Priorité de la zone de génération** : L'ordre de priorité est `sprite_tag` > `spawn_area` > `x`/`y`. Si `sprite_tag` est spécifié, `spawn_area`, `x` et `y` sont ignorés. Si `spawn_area` est spécifié (et `sprite_tag` n'est pas spécifié), `x` et `y` sont ignorés. Si ni `sprite_tag` ni `spawn_area` ne sont spécifiés, `x` et `y` sont obligatoires
- **Zone de génération basée sur un sprite tag** : Si `sprite_tag` est spécifié, les particules sont générées dans la zone couverte par tous les sprites ayant ce tag. Si plusieurs sprites partagent le même tag, la zone d'émission est l'union des bounds de tous ces sprites. Les bounds sont calculés à partir de `layer.world_x_offset`, `layer.world_y_offset`, `layer.surface.get_width()` et `layer.surface.get_height()`. Si la layer se répète avec `infinite_offset`, la largeur effective est utilisée. Le tag doit correspondre à un tag défini dans le fichier `.niveau` avec le champ `tags`
- **Limitation à un bord** : Si `spawn_edge` est spécifié (nécessite que `sprite_tag` soit également spécifié), les particules sont générées uniquement le long du bord spécifié :
  - `"top"` : Bande horizontale de 1 pixel de hauteur en haut du sprite (y = y_min, x de x_min à x_max)
  - `"bottom"` : Bande horizontale de 1 pixel de hauteur en bas du sprite (y = y_max, x de x_min à x_max)
  - `"left"` : Bande verticale de 1 pixel de largeur à gauche du sprite (x = x_min, y de y_min à y_max)
  - `"right"` : Bande verticale de 1 pixel de largeur à droite du sprite (x = x_max, y de y_min à y_max)
- **Zone de génération manuelle** : Si `spawn_area` est spécifié (et `sprite_tag` n'est pas spécifié), chaque particule est générée à une position aléatoire dans la zone définie. Cela permet de créer des effets plus dispersés et naturels (par exemple, une pluie sur une large zone, une explosion qui couvre une zone plutôt qu'un point unique)
- **Couleurs multiples** : Si `colors` est spécifié, chaque particule choisit aléatoirement une couleur parmi la liste lors de sa création. Cela permet de créer des effets multicolores variés (par exemple, un feu d'artifice avec plusieurs couleurs, une explosion arc-en-ciel)
- **Rétrocompatibilité** : Si `colors` n'est pas spécifié mais `color` est spécifié, toutes les particules utilisent la même couleur (comportement original)
- **Durée de génération** : Si `generation_duration` est spécifié, les particules sont générées progressivement sur cette durée au lieu d'être toutes créées immédiatement. Cela permet de créer des effets plus fluides et naturels (par exemple, une pluie continue, une explosion prolongée, une fumée qui s'accumule progressivement). Si `generation_duration` n'est pas spécifié, toutes les particules sont créées immédiatement (comportement par défaut, rétrocompatibilité)
- L'événement peut être déclenché plusieurs fois si `repeatable = true` dans la configuration, permettant de créer plusieurs effets simultanés
- Les particules sont rendues automatiquement par le système de particules dans la boucle de rendu (voir spécification 14 pour les détails d'intégration)
- **Note d'implémentation** : Le système de particules (`ParticleEffect`, `ParticleEffectConfig`, `ParticleSystem`) doit être étendu pour supporter :
  1. La génération de particules dans une zone (modifier `ParticleEffect.__init__()` pour accepter une zone de génération)
  2. Les couleurs multiples (ajouter `color_palette: Optional[List[Tuple[int, int, int]]]` à `ParticleEffectConfig` et modifier `ParticleEffect._create_particles()` pour choisir aléatoirement une couleur parmi la palette)
  3. La génération progressive (ajouter `generation_duration: Optional[float]` à `ParticleEffectConfig`, ajouter `generation_timer: float` et `particles_created: int` à `ParticleEffect`, modifier `__init__()` pour ne pas appeler `_create_particles()` immédiatement si `generation_duration` est spécifié, et modifier `update()` pour générer progressivement les particules restantes à chaque frame jusqu'à ce que toutes les particules soient créées ou que la durée de génération soit écoulée)

#### Comportement du level up

Lorsqu'un événement de type `level_up` est déclenché :

1. **Vérification** : Le système vérifie que le joueur est disponible (instance `Player` fournie au constructeur). Si le joueur n'est pas disponible, une erreur est levée (`ValueError`) et l'événement est ignoré.
2. **Exécution** : La méthode `_execute_level_up()` est appelée, qui appelle `player.show_level_up()` pour activer l'affichage.
3. **Affichage** : L'affichage "level up (press u)" apparaît automatiquement en jaune clignotant au-dessus du nom du personnage principal (voir spécification 2 pour les détails d'affichage).
4. **Confirmation** : Le joueur peut appuyer sur la touche `U` pour confirmer le level up. Lors de la confirmation :
   - Le niveau du personnage est augmenté de **+1 uniquement** (sans dépasser `MAX_PLAYER_LEVEL`) en utilisant `player.set_level(new_level)`, ce qui déclenche automatiquement le rechargement des assets et la mise à jour des statistiques (voir spécification 7)
   - **Important** : L'augmentation est toujours de +1 niveau, il n'est pas possible d'augmenter de plusieurs niveaux en une seule fois
   - L'affichage est masqué (appel de `player.hide_level_up()`)
   - Si le niveau est déjà au maximum, le niveau ne change pas mais l'affichage disparaît quand même
   - **Réinitialisation automatique** : Tous les événements de type `level_up` sont automatiquement réinitialisés (état `triggered` remis à `False`) après la confirmation, permettant ainsi de les redéclencher lors de dialogues ultérieurs. Cela permet au joueur de monter de niveau plusieurs fois via différents dialogues.
5. **Gestion de l'état** : L'état de level up est géré par la classe `Player` (voir spécification 2).

**Implémentation de `_execute_level_up()`** :

```python
def _execute_level_up(self, event_data: LevelUpEventConfig) -> None:
    """Exécute un événement de level up."""
    if self.player is None:
        logger.warning("Événement level_up ignoré : instance Player non fournie")
        raise ValueError("L'instance Player est requise pour les événements de level up")
    
    # Activer l'affichage du level up
    self.player.show_level_up()
    logger.info("Level up activé pour le joueur")
```

**Important** :
- L'événement nécessite que l'instance `Player` soit fournie au constructeur de `EventTriggerSystem`
- L'affichage "level up (press u)" est géré par la classe `Player` et apparaît automatiquement lorsque l'événement est déclenché
- L'événement peut être déclenché depuis un dialogue de PNJ en utilisant `trigger_events` dans la configuration d'un échange (voir spécification 12)
- L'affichage reste visible jusqu'à ce que le joueur appuie sur la touche `U` pour le confirmer. La confirmation augmente réellement le niveau du personnage et déclenche l'animation de transition de niveau (voir spécification 2 pour les détails de l'implémentation)
- **Réinitialisation automatique** : Après la confirmation du level up (touche `U`), tous les événements de type `level_up` sont automatiquement réinitialisés via `reset_event_by_identifier()`, permettant ainsi de les redéclencher lors de dialogues ultérieurs. Cela permet au joueur de monter de niveau plusieurs fois via différents dialogues.
- La méthode `_execute_event()` doit appeler `_execute_level_up()` lorsque `event.event_type == "level_up"`

#### Animation de transition de niveau

Lorsque le joueur appuie sur la touche `U` pour confirmer un level up, une animation de transition est déclenchée pour visualiser le changement de niveau. Cette animation combine un zoom de caméra progressif, un affichage textuel et une alternance visuelle des sprites.

##### Caractéristiques de l'animation

L'animation de transition de niveau se déroule en **trois phases séquentielles** :

1. **Phase 1 - Zoom avant** : Un zoom de caméra de 230% est appliqué progressivement sur le joueur en 1 seconde. Cette phase prépare visuellement le changement de niveau en mettant l'accent sur le personnage.

2. **Phase 2 - Affichage de transition** : Une fois le zoom terminé, l'affichage textuel et l'alternance des sprites sont déclenchés. La durée totale de cette phase est configurable via une constante ou un paramètre (défaut recommandé : 1.5 secondes). Cette durée peut être ajustée dans la configuration du jeu ou via une constante dans la classe `Player`.

3. **Phase 3 - Reset du zoom** : Une fois l'affichage de transition terminé, le zoom de caméra est réinitialisé progressivement à 100% en 1 seconde, ramenant la vue à la normale.

**Durée totale** : La durée totale de l'animation est donc de `zoom_in_duration + transition_display_duration + zoom_out_duration` (par défaut : 1.0 + 1.5 + 1.0 = 3.5 secondes).

**Phase 2 - Affichage de transition** (détails) :

2. **Affichage textuel** :
   - **Texte principal** : Affiche `"level [level actuel] -> level [nouveau level]"` (ex: "level 1 -> level 2", "level 3 -> level 4")
   - **Texte d'amélioration** : Affiche une phrase d'amélioration sous le texte principal, chargée depuis le fichier `config/player_stats.toml` (voir section "Configuration des phrases d'amélioration" ci-dessous). Cette phrase décrit les améliorations apportées par le changement de niveau.
   - **Position** : Centré horizontalement et verticalement à l'écran (indépendamment de la position de la caméra)
   - **Taille** : 
     - Texte principal : Texte en grand (taille de police recommandée : 72-96 pixels dans le repère de conception 1920x1080, convertie vers 1280x720)
     - Texte d'amélioration : Texte en taille moyenne (taille de police recommandée : 36-48 pixels dans le repère de conception 1920x1080, convertie vers 1280x720)
   - **Style** : 
     - Texte principal : Police système (Arial/sans-serif) en gras, couleur noire pour une excellente lisibilité
     - Texte d'amélioration : Police système (Arial/sans-serif) en normal (non gras), couleur gris foncé (ex: (64, 64, 64)) pour une bonne lisibilité tout en restant secondaire par rapport au texte principal
   - **Espacement** : Un espacement vertical est ajouté entre le texte principal et le texte d'amélioration (espacement recommandé : 15-25 pixels dans le repère de conception 1920x1080, converti vers 1280x720)
   - **Cadre** : Le texte est affiché dans un cadre arrondi avec :
     - **Fond** : Blanc (255, 255, 255)
     - **Bordure** : Noire (0, 0, 0), épaisseur recommandée de 4-6 pixels
     - **Coins arrondis** : Rayon d'arrondi recommandé de 15-20 pixels pour un rendu moderne et élégant
     - **Padding** : Espacement interne entre le texte et les bords du cadre (padding horizontal recommandé : 40-60 pixels, padding vertical recommandé : 20-30 pixels). Le padding doit tenir compte de la hauteur totale des deux textes (texte principal + espacement + texte d'amélioration)
   - **Visibilité** : Le texte et son cadre restent visibles pendant toute la durée de la phase 2 (affichage de transition)

3. **Alternance des sprites** :
   - Pendant toute la durée de la phase 2, le sprite du personnage alterne entre l'ancien niveau et le nouveau niveau
   - **Fréquence d'alternance** : Le sprite change toutes les 0.15-0.2 secondes (configurable, défaut recommandé : 0.2 secondes)
   - **Animation** : L'alternance se fait de manière fluide, en conservant la même frame d'animation (marche, saut, idle, etc.) pour éviter les sauts visuels
   - **Fin de l'animation** : À la fin de la phase 2, le sprite reste sur le nouveau niveau

4. **Blocage de l'utilisateur** :
   - Pendant toute la durée de la transition, l'utilisateur est complètement bloqué et ne peut effectuer aucune action
   - **Mouvement désactivé** : Tous les inputs de mouvement (flèches, touches WASD) sont ignorés pendant la transition
   - **Autres interactions désactivées** : Les autres interactions (saut, dialogue avec PNJ, etc.) sont également bloquées
   - **Position figée** : Le personnage reste à la même position (x, y) pendant toute la durée de l'animation
   - **Pas d'impact sur les collisions** : Comme le personnage ne bouge pas pendant la transition, il n'y a aucun impact sur la gestion des collisions. Le système de collisions continue de fonctionner normalement mais ne détectera aucun mouvement puisque la position du personnage reste inchangée

##### Implémentation dans la classe Player

La classe `Player` doit être étendue pour gérer cette animation :

**Nouvelles propriétés** :
- `level_transition_active: bool` : Indique si l'animation de transition est actuellement en cours (défaut: False)
- `level_transition_phase: Literal["zoom_in", "display", "zoom_out", "none"]` : Phase actuelle de l'animation (défaut: "none")
- `level_transition_zoom_in_timer: float` : Timer pour la phase de zoom avant (défaut: 0.0)
- `level_transition_zoom_in_duration: float` : Durée de la phase de zoom avant en secondes (défaut: 1.0, configurable)
- `level_transition_timer: float` : Timer pour suivre la progression de la phase d'affichage (défaut: 0.0)
- `level_transition_duration: float` : Durée totale de la phase d'affichage en secondes (défaut: 1.5, configurable)
- `level_transition_zoom_out_timer: float` : Timer pour la phase de reset du zoom (défaut: 0.0)
- `level_transition_zoom_out_duration: float` : Durée de la phase de reset du zoom en secondes (défaut: 1.0, configurable)
- `level_transition_switch_interval: float` : Intervalle entre chaque changement de sprite en secondes (défaut: 0.2, configurable)
- `level_transition_switch_timer: float` : Timer pour gérer l'alternance des sprites (défaut: 0.0)
- `level_transition_old_level: int` : Niveau précédent (avant le changement) (défaut: 1)
- `level_transition_new_level: int` : Nouveau niveau (après le changement) (défaut: 1)
- `level_transition_showing_old: bool` : Indique si le sprite de l'ancien niveau est actuellement affiché (défaut: True)
- `level_transition_old_sprite_sheet: Optional[pygame.Surface]` : Sprite sheet de l'ancien niveau (chargé temporairement pour l'animation)
- `level_transition_text_surface: Optional[pygame.Surface]` : Surface pré-rendue du texte de transition (None si l'animation n'est pas active). Cette surface contient à la fois le texte principal ("level X -> level Y") et le texte d'amélioration (si disponible).
- `level_transition_camera_zoom_controller: Optional[CameraZoomController]` : Référence au contrôleur de zoom de caméra (nécessaire pour gérer les phases de zoom)
- `level_transition_improvement_message: Optional[str]` : Phrase d'amélioration chargée depuis le fichier `player_stats.toml` pour le nouveau niveau (None si non disponible ou si le niveau est 1)

**Nouvelles méthodes** :
- `start_level_transition(old_level: int, new_level: int, camera_zoom_controller: Optional[CameraZoomController] = None) -> None` : Démarre l'animation de transition de niveau
  - Sauvegarde l'ancien niveau et le nouveau niveau
  - Stocke la référence au contrôleur de zoom de caméra
  - Charge temporairement le sprite sheet de l'ancien niveau
  - Charge la phrase d'amélioration depuis le fichier `player_stats.toml` pour le nouveau niveau (via `PlayerStatsLoader` ou `PlayerStatsConfig`). La phrase est stockée dans `level_transition_improvement_message`. Si le nouveau niveau est 1 ou si aucune phrase n'est disponible, `level_transition_improvement_message` est défini à `None`.
  - Prépare la surface de texte avec le format "level [old_level] -> level [new_level]" et, si disponible, la phrase d'amélioration en dessous avec un espacement approprié
  - Initialise les timers pour toutes les phases
  - Démarre la phase 1 (zoom avant) en appelant `camera_zoom_controller.start_zoom(230.0, duration=1.0)` si le contrôleur est disponible
  - Met `level_transition_active` à `True` et `level_transition_phase` à `"zoom_in"`
- `_update_level_transition(dt: float, camera_x: float = 0.0) -> None` : Met à jour l'animation de transition
  - Gère les transitions entre les trois phases :
    - **Phase "zoom_in"** : Vérifie si le zoom avant est terminé (via `camera_zoom_controller.is_active` ou un timer). Une fois terminé, passe à la phase "display" et démarre l'affichage textuel et l'alternance des sprites.
    - **Phase "display"** : Décrémente `level_transition_timer` de `dt`, gère l'alternance des sprites selon `level_transition_switch_interval`. Une fois terminée, passe à la phase "zoom_out" et démarre le reset du zoom.
    - **Phase "zoom_out"** : Vérifie si le reset du zoom est terminé. Une fois terminé, termine complètement l'animation.
  - Gère l'alternance des sprites selon `level_transition_switch_interval` (uniquement pendant la phase "display")
  - Gère l'émission continue de confettis depuis les coins en haut à gauche et en haut à droite du cadre de transition (voir spécification 7 et 14) - **uniquement pendant la phase "display"**
  - **Important** : Les confettis sont émis depuis les **coins arrondis visibles** du cadre, pas depuis les coins géométriques du rectangle. Les positions d'émission doivent tenir compte du `corner_radius` :
    - Coin haut gauche : `(frame_x + corner_radius, frame_y)` où `corner_radius` est le rayon des coins arrondis (converti selon le facteur d'échelle). Cette position correspond au point sur l'arc du coin arrondi au niveau du bord supérieur (y=0 dans les coordonnées locales de la surface).
    - Coin haut droit : `(frame_x + frame_width - corner_radius, frame_y)`. Cette position correspond au point sur l'arc du coin arrondi au niveau du bord supérieur.
    - `frame_x`, `frame_y` et `frame_width` sont les coordonnées et la largeur du cadre de transition (le rectangle complet incluant le texte, padding et bordure)
    - Le `corner_radius` doit être recalculé de la même manière que dans `start_level_transition` (converti selon le facteur d'échelle `scale_y`) pour garantir la cohérence avec le rendu visuel
    - **Note** : Dans pygame.draw.rect avec `border_radius`, le coin arrondi est un quart de cercle. Le centre de l'arc pour le coin haut gauche est à `(corner_radius, corner_radius)` dans les coordonnées locales. Le point sur l'arc au niveau du bord supérieur (y=0) est à `x=corner_radius` depuis le coin géométrique, ce qui donne la position d'émission exacte.
  - **Émission en cône** : Les confettis sont émis en cône directionnel :
    - **Coin haut gauche** : Cône vers le haut à gauche avec un angle de direction de -135° (-3π/4 radians) et une dispersion de 30° (π/6 radians)
    - **Coin haut droit** : Cône vers le haut à droite avec un angle de direction de -45° (-π/4 radians) et une dispersion de 30° (π/6 radians)
  - Le nombre de confettis par émission est configurable via `CONFETTI_COUNT_PER_EMISSION` (défaut: 60 particules, doublé pour plus d'effet visuel)
  - Le paramètre `camera_x` est nécessaire pour convertir les coordonnées écran du cadre en coordonnées monde pour les particules
  - **Fin de l'animation** : L'animation se termine automatiquement lorsque la phase "zoom_out" est complète. À ce moment, toutes les ressources temporaires sont libérées et l'état est réinitialisé.
- `_draw_level_transition(surface: pygame.Surface) -> None` : Dessine l'animation de transition
  - Dessine le texte centré à l'écran (indépendamment de la caméra)
  - Le sprite du personnage est géré automatiquement par `_get_current_sprite()` qui prend en compte l'état de transition
- `_get_current_sprite() -> pygame.Surface` : Modifiée pour prendre en compte l'animation de transition
  - Si `level_transition_active` est `True`, retourne le sprite de l'ancien ou du nouveau niveau selon `level_transition_showing_old`
  - Sinon, comportement normal (retourne le sprite du niveau actuel)

**Modification de la méthode `set_level()`** :
- Avant de changer le niveau, appeler `start_level_transition(old_level, new_level)` si le niveau change réellement
- L'animation se termine automatiquement après la durée configurée

**Modification de la gestion de l'input (touche U)** :
- Lorsque la touche `U` est pressée et que `level_up_active` est `True` :
  1. Calculer le nouveau niveau : `new_level = min(player.player_level + 1, MAX_PLAYER_LEVEL)`
  2. Si le nouveau niveau est différent du niveau actuel :
     - Récupérer la référence au `CameraZoomController` depuis le système de jeu (doit être accessible via le `GameState` ou injecté dans le `Player`)
     - Appeler `player.start_level_transition(player.player_level, new_level, camera_zoom_controller)` pour démarrer l'animation (cela démarre automatiquement la phase 1 - zoom avant)
     - Appeler `player.set_level(new_level)` pour changer réellement le niveau (cela déclenche le rechargement des assets) - **Note** : Le changement de niveau doit se faire après le démarrage de la transition pour que le sprite de l'ancien niveau soit correctement sauvegardé
  3. Appeler `player.hide_level_up()` pour masquer l'affichage "level up (press u)"

**Intégration dans la boucle de jeu** :
- Dans `player.update(dt, camera_x, keys)`, appeler `_update_level_transition(dt, camera_x)` si `level_transition_active` est `True`
- **Gestion du zoom de caméra** : Le `CameraZoomController` doit être mis à jour dans la boucle principale du jeu (via `camera_zoom_controller.update(dt)` ou équivalent). Pendant les phases "zoom_in" et "zoom_out", le contrôleur gère automatiquement l'interpolation du zoom. La méthode `_update_level_transition()` vérifie l'état du zoom pour déterminer quand passer d'une phase à l'autre.
- **Blocage des inputs pendant la transition** : Si `level_transition_active` est `True`, ignorer tous les inputs de mouvement et d'interaction dans `_handle_movement()` et les autres méthodes de gestion d'input. Le personnage ne doit pas bouger pendant toute la durée de l'animation (phases 1, 2 et 3).
- **Ordre de rendu (CRITIQUE)** : Dans la fonction de rendu, appeler `_draw_level_transition(surface)` **EN DERNIER**, après tous les autres éléments, y compris :
  - Les couches de parallaxe (background, gameplay, foreground)
  - Le joueur et les PNJ
  - Les bulles de dialogue (`speech_bubble` et `current_dialogue`)
  - L'interface des statistiques du joueur (`PlayerStatsDisplay`)
  - Le HUD de progression (`LevelProgressHUD`)
  - Tous les autres éléments d'interface
- Le texte de transition de niveau doit avoir la **priorité absolue** et être affiché au-dessus de tous les autres éléments pour garantir une visibilité maximale pendant l'animation
- **Gestion des collisions** : Pendant la transition, le système de collisions continue de fonctionner normalement, mais comme le personnage ne bouge pas (position figée), aucune collision ne sera détectée. Aucune modification spéciale n'est nécessaire dans le système de collisions pour gérer la transition.

##### Gestion des ressources

- **Chargement temporaire du sprite sheet** : Le sprite sheet de l'ancien niveau doit être chargé temporairement au début de l'animation et libéré à la fin
- **Cache des surfaces** : La surface de texte peut être pré-rendue une seule fois au début de l'animation pour éviter de recalculer à chaque frame
- **Nettoyage** : À la fin de l'animation, libérer les ressources temporaires (sprite sheet de l'ancien niveau, surface de texte)

##### Configuration

La durée de l'animation et la fréquence d'alternance peuvent être configurées via des constantes dans la classe `Player` ou via un fichier de configuration :

```python
# Constantes recommandées
DEFAULT_LEVEL_TRANSITION_ZOOM_IN_DURATION = 1.0  # secondes - durée de la phase de zoom avant
DEFAULT_LEVEL_TRANSITION_ZOOM_PERCENT = 230.0  # pourcentage de zoom (230% = facteur 2.3)
DEFAULT_LEVEL_TRANSITION_DURATION = 1.5  # secondes - durée de la phase d'affichage
DEFAULT_LEVEL_TRANSITION_ZOOM_OUT_DURATION = 1.0  # secondes - durée de la phase de reset du zoom
DEFAULT_LEVEL_TRANSITION_SWITCH_INTERVAL = 0.2  # secondes
LEVEL_TRANSITION_TEXT_SIZE = 72  # pixels (dans le repère de conception 1920x1080)
LEVEL_TRANSITION_IMPROVEMENT_TEXT_SIZE = 40  # pixels (dans le repère de conception 1920x1080)
LEVEL_TRANSITION_TEXT_SPACING = 20  # pixels - espacement entre le texte principal et le texte d'amélioration
LEVEL_TRANSITION_IMPROVEMENT_TEXT_COLOR = (64, 64, 64)  # Gris foncé
LEVEL_TRANSITION_FRAME_PADDING_X = 50  # pixels - padding horizontal du cadre
LEVEL_TRANSITION_FRAME_PADDING_Y = 25  # pixels - padding vertical du cadre
LEVEL_TRANSITION_FRAME_BORDER_THICKNESS = 5  # pixels - épaisseur de la bordure
LEVEL_TRANSITION_FRAME_CORNER_RADIUS = 18  # pixels - rayon des coins arrondis
LEVEL_TRANSITION_TEXT_COLOR = (0, 0, 0)  # Noir
LEVEL_TRANSITION_FRAME_BACKGROUND_COLOR = (255, 255, 255)  # Blanc
LEVEL_TRANSITION_FRAME_BORDER_COLOR = (0, 0, 0)  # Noir
```

##### Configuration des phrases d'amélioration

Les phrases d'amélioration affichées lors du changement de niveau sont configurées dans le fichier `config/player_stats.toml`. Une nouvelle section `[level_up_messages]` doit être ajoutée à ce fichier pour définir les messages pour chaque niveau.

**Structure du fichier `config/player_stats.toml`** :

```toml
# Section existante pour les statistiques
[stats.force]
# ... configuration des stats ...

# Nouvelle section pour les messages de level up
[level_up_messages]
# Messages affichés lors du passage à un niveau supérieur
# Note: level_1 n'existe pas car on ne peut pas passer du niveau 1 au niveau 1
level_2 = "Votre compétence en design de produit IA s'améliore !"
level_3 = "Vous développez une meilleure compréhension des modèles ML."
level_4 = "Votre expertise en IA générative progresse significativement."
level_5 = "Vous atteignez un niveau de maîtrise avancé en IA."
```

**Règles de configuration** :
- Les clés sont `level_2`, `level_3`, `level_4`, `level_5` (pas de `level_1` car on ne peut pas passer du niveau 1 au niveau 1)
- Chaque valeur est une chaîne de caractères (string) qui sera affichée sous le texte "level X -> level Y"
- Les messages sont optionnels : si un niveau n'a pas de message défini, seul le texte principal "level X -> level Y" sera affiché
- Les messages peuvent contenir des retours à la ligne (`\n`) pour créer des messages multi-lignes si nécessaire
- Les messages doivent être concis pour rester lisibles dans le cadre de transition

**Chargement des messages** :
- Le `PlayerStatsLoader` doit être étendu pour charger la section `[level_up_messages]` depuis le fichier `player_stats.toml`
- Les messages sont stockés dans une structure de données accessible depuis la classe `Player` (par exemple, via `PlayerStatsConfig` ou une nouvelle classe `LevelUpMessagesConfig`)
- Lors du démarrage de l'animation de transition (`start_level_transition`), le message correspondant au nouveau niveau est récupéré et stocké dans `level_transition_improvement_message`
- Si aucun message n'est disponible pour le nouveau niveau, `level_transition_improvement_message` est défini à `None` et seul le texte principal est affiché

##### Exemple d'implémentation

```python
from typing import Optional, Literal
from moteur_jeu_presentation.rendering.camera_zoom import CameraZoomController

def start_level_transition(self, old_level: int, new_level: int, camera_zoom_controller: Optional[CameraZoomController] = None) -> None:
    """Démarre l'animation de transition de niveau."""
    if old_level == new_level:
        return  # Pas de transition si le niveau ne change pas
    
    self.level_transition_active = True
    self.level_transition_phase = "zoom_in"
    self.level_transition_camera_zoom_controller = camera_zoom_controller
    
    # Initialiser les timers pour toutes les phases
    self.level_transition_zoom_in_timer = self.level_transition_zoom_in_duration
    self.level_transition_timer = self.level_transition_duration
    self.level_transition_zoom_out_timer = self.level_transition_zoom_out_duration
    self.level_transition_switch_timer = 0.0
    
    self.level_transition_old_level = old_level
    self.level_transition_new_level = new_level
    self.level_transition_showing_old = True
    
    # Démarrer la phase 1 : zoom avant sur le joueur
    if self.level_transition_camera_zoom_controller is not None:
        self.level_transition_camera_zoom_controller.start_zoom(
            zoom_percent=DEFAULT_LEVEL_TRANSITION_ZOOM_PERCENT,
            duration=self.level_transition_zoom_in_duration,
            bottom_margin_design_px=50.0,
            keep_bubbles_visible=True
        )
    
    # Charger temporairement le sprite sheet de l'ancien niveau
    old_level_manager = PlayerLevelManager(self.level_manager.assets_root, old_level)
    old_walk_path = old_level_manager.get_asset_path("walk.png")
    self.level_transition_old_sprite_sheet = pygame.image.load(str(old_walk_path)).convert_alpha()
    
    # Charger la phrase d'amélioration depuis la configuration
    improvement_message = None
    if self.level_manager.stats_config is not None:
        # Récupérer les messages de level up depuis la configuration
        # (nécessite d'étendre PlayerStatsConfig pour inclure level_up_messages)
        level_up_messages = getattr(self.level_manager.stats_config, 'level_up_messages', {})
        if new_level in level_up_messages:
            improvement_message = level_up_messages[new_level]
    
    self.level_transition_improvement_message = improvement_message
    
    # Pré-rendre le texte de transition avec cadre arrondi
    main_text = f"level {old_level} -> level {new_level}"
    main_font_size = int(LEVEL_TRANSITION_TEXT_SIZE * (RENDER_WIDTH / DESIGN_WIDTH))
    main_font = pygame.font.SysFont("arial", main_font_size, bold=True)
    main_text_color = (0, 0, 0)  # Texte principal en noir
    
    # Rendre le texte principal
    main_text_surface = main_font.render(main_text, True, main_text_color)
    
    # Rendre le texte d'amélioration si disponible
    improvement_text_surface = None
    improvement_text_height = 0
    text_spacing = int(LEVEL_TRANSITION_TEXT_SPACING * (RENDER_WIDTH / DESIGN_WIDTH))
    
    if improvement_message is not None:
        improvement_font_size = int(LEVEL_TRANSITION_IMPROVEMENT_TEXT_SIZE * (RENDER_WIDTH / DESIGN_WIDTH))
        improvement_font = pygame.font.SysFont("arial", improvement_font_size, bold=False)
        improvement_text_color = LEVEL_TRANSITION_IMPROVEMENT_TEXT_COLOR  # Gris foncé
        
        # Gérer les retours à la ligne si présents
        improvement_lines = improvement_message.split('\n')
        improvement_surfaces = []
        max_improvement_width = 0
        for line in improvement_lines:
            if line.strip():  # Ignorer les lignes vides
                line_surface = improvement_font.render(line.strip(), True, improvement_text_color)
                improvement_surfaces.append(line_surface)
                max_improvement_width = max(max_improvement_width, line_surface.get_width())
        
        if improvement_surfaces:
            # Créer une surface combinée pour toutes les lignes d'amélioration
            improvement_text_height = sum(s.get_height() for s in improvement_surfaces) + text_spacing * (len(improvement_surfaces) - 1)
            improvement_text_surface = pygame.Surface((max_improvement_width, improvement_text_height), pygame.SRCALPHA)
            current_y = 0
            for line_surface in improvement_surfaces:
                improvement_text_surface.blit(line_surface, (0, current_y))
                current_y += line_surface.get_height() + text_spacing
    
    # Calculer les dimensions du cadre (texte principal + espacement + texte d'amélioration + padding + bordure)
    content_width = max(main_text_surface.get_width(), 
                       improvement_text_surface.get_width() if improvement_text_surface else 0)
    content_height = main_text_surface.get_height()
    if improvement_text_surface:
        content_height += text_spacing + improvement_text_height
    
    background_color = (255, 255, 255)  # Fond blanc
    border_color = (0, 0, 0)  # Bordure noire
    border_thickness = 5  # Épaisseur de la bordure
    corner_radius = 18  # Rayon des coins arrondis
    padding_x = 50  # Padding horizontal
    padding_y = 25  # Padding vertical
    
    frame_width = content_width + padding_x * 2 + border_thickness * 2
    frame_height = content_height + padding_y * 2 + border_thickness * 2
    
    # Créer la surface finale avec transparence
    final_surface = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
    
    # Dessiner le rectangle de fond (blanc) avec coins arrondis
    pygame.draw.rect(final_surface, background_color, 
                     (0, 0, frame_width, frame_height), 
                     border_radius=corner_radius)
    
    # Dessiner la bordure noire (rectangle extérieur)
    pygame.draw.rect(final_surface, border_color, 
                     (0, 0, frame_width, frame_height), 
                     width=border_thickness, 
                     border_radius=corner_radius)
    
    # Calculer les positions pour centrer le contenu
    content_x = padding_x + border_thickness
    content_y = padding_y + border_thickness
    
    # Centrer horizontalement le texte principal
    main_text_x = content_x + (content_width - main_text_surface.get_width()) // 2
    main_text_y = content_y
    final_surface.blit(main_text_surface, (main_text_x, main_text_y))
    
    # Dessiner le texte d'amélioration si disponible
    if improvement_text_surface:
        improvement_text_x = content_x + (content_width - improvement_text_surface.get_width()) // 2
        improvement_text_y = content_y + main_text_surface.get_height() + text_spacing
        final_surface.blit(improvement_text_surface, (improvement_text_x, improvement_text_y))
    
    self.level_transition_text_surface = final_surface

def _update_level_transition(self, dt: float, camera_x: float = 0.0) -> None:
    """Met à jour l'animation de transition de niveau.
    
    Args:
        dt: Delta time en secondes
        camera_x: Position horizontale de la caméra (nécessaire pour l'émission de confettis)
    """
    if not self.level_transition_active:
        return
    
    # Gérer les transitions entre les phases
    if self.level_transition_phase == "zoom_in":
        # Vérifier si le zoom avant est terminé
        if self.level_transition_camera_zoom_controller is None or not self.level_transition_camera_zoom_controller.is_active:
            # Le zoom est terminé, passer à la phase d'affichage
            self.level_transition_phase = "display"
            self.level_transition_timer = self.level_transition_duration
            self.level_transition_switch_timer = 0.0
    
    elif self.level_transition_phase == "display":
        # Phase d'affichage : gérer le timer et l'alternance des sprites
        self.level_transition_timer -= dt
        self.level_transition_switch_timer += dt
        
        # Alterner les sprites
        if self.level_transition_switch_timer >= self.level_transition_switch_interval:
            self.level_transition_switch_timer = 0.0
            self.level_transition_showing_old = not self.level_transition_showing_old
        
        # Gérer l'émission de confettis (voir spécification 7 et 14 pour les détails)
        # L'émission de confettis est gérée dans cette méthode pour être synchronisée avec l'animation de transition
        
        # Vérifier si la phase d'affichage est terminée
        if self.level_transition_timer <= 0.0:
            # Passer à la phase de reset du zoom
            self.level_transition_phase = "zoom_out"
            if self.level_transition_camera_zoom_controller is not None:
                # Récupérer le rectangle de rendu du joueur pour le reset du zoom
                player_draw_rect = self._get_player_draw_rect()  # Méthode à implémenter pour obtenir le rect de rendu
                self.level_transition_camera_zoom_controller.reset_zoom(
                    duration=self.level_transition_zoom_out_duration,
                    player_draw_rect=player_draw_rect
                )
    
    elif self.level_transition_phase == "zoom_out":
        # Vérifier si le reset du zoom est terminé
        if self.level_transition_camera_zoom_controller is None or not self.level_transition_camera_zoom_controller.is_active:
            # Le reset est terminé, terminer complètement l'animation
            self.level_transition_active = False
            self.level_transition_phase = "none"
            self.level_transition_showing_old = False
            # Libérer les ressources temporaires
            self.level_transition_old_sprite_sheet = None
            self.level_transition_text_surface = None
            self.level_transition_camera_zoom_controller = None

def _handle_movement(self, keys: pygame.key.ScancodeWrapper, dt: float) -> None:
    """Gère le mouvement du personnage.
    
    Note: Si level_transition_active est True, cette méthode doit retourner
    immédiatement sans traiter les inputs pour bloquer le personnage pendant
    la transition de niveau.
    """
    # Blocage complet pendant la transition de niveau
    if self.level_transition_active:
        return  # Le personnage ne bouge pas pendant la transition
    
    # ... reste de l'implémentation normale du mouvement ...

def _draw_level_transition(self, surface: pygame.Surface) -> None:
    """Dessine l'animation de transition de niveau."""
    # N'afficher le texte que pendant la phase "display"
    if not self.level_transition_active or self.level_transition_phase != "display" or self.level_transition_text_surface is None:
        return
    
    # Centrer le texte à l'écran
    screen_width = surface.get_width()
    screen_height = surface.get_height()
    text_x = (screen_width - self.level_transition_text_surface.get_width()) // 2
    text_y = (screen_height - self.level_transition_text_surface.get_height()) // 2
    
    surface.blit(self.level_transition_text_surface, (text_x, text_y))
```

**Important** :
- L'animation de transition est déclenchée automatiquement lors de la confirmation d'un level up (touche `U`)
- L'animation bloque toute autre interaction pendant sa durée totale (le personnage ne peut pas se déplacer, etc.)
- **Blocage complet** : Pendant toute la durée de la transition (3.5 secondes par défaut : 1.0s zoom avant + 1.5s affichage + 1.0s reset zoom), l'utilisateur est complètement bloqué :
  - Tous les inputs de mouvement sont ignorés (flèches, WASD)
  - Toutes les autres interactions sont désactivées (saut, dialogue, etc.)
  - Le personnage reste à la même position (x, y) pendant toute l'animation (phases 1, 2 et 3)
- **Phases de l'animation** :
  - **Phase 1 (zoom_in)** : Zoom progressif de 230% sur le joueur en 1 seconde. Le texte de transition n'est pas encore affiché.
  - **Phase 2 (display)** : Affichage du texte "level X -> level Y" (et de la phrase d'amélioration si disponible) et alternance des sprites pendant 1.5 secondes. Le zoom reste à 230% pendant cette phase.
  - **Phase 3 (zoom_out)** : Reset progressif du zoom à 100% en 1 seconde. Le texte de transition n'est plus affiché.
- **Ordre de rendu (PRIORITÉ ABSOLUE)** : Le texte de transition de niveau doit être rendu **EN DERNIER**, après tous les autres éléments de l'interface, y compris les bulles de dialogue et l'interface des statistiques. Cela garantit que le texte "level X -> level Y" (et la phrase d'amélioration si disponible) est toujours visible au-dessus de tous les autres éléments pendant la phase d'affichage. **Note** : Le texte n'est affiché que pendant la phase "display", pas pendant les phases de zoom.
- **Intégration avec le système de zoom** : L'animation utilise le `CameraZoomController` (spécification 18) pour gérer les phases de zoom. Le contrôleur doit être accessible depuis le `Player` et mis à jour dans la boucle principale du jeu.
- **Pas d'impact sur les collisions** : Comme le personnage ne bouge pas pendant la transition, il n'y a aucun impact sur la gestion des collisions. Le système de collisions continue de fonctionner normalement mais ne détectera aucun mouvement puisque la position du personnage reste inchangée. Aucune modification spéciale n'est nécessaire dans le système de collisions.
- Si le niveau est déjà au maximum, l'animation n'est pas déclenchée (le niveau ne change pas)
- L'animation doit être fluide et ne pas causer de ralentissement du jeu

#### Comportement du masquage de sprite

Lorsqu'un événement de type `sprite_hide` est déclenché :

1. **Vérification** : Le système vérifie que le tag spécifié existe dans le dictionnaire `layers_by_tag`
2. **Récupération des layers** : Toutes les layers associées au tag sont récupérées depuis `layers_by_tag[sprite_tag]`
3. **Initialisation du fade out** : Pour chaque layer concernée :
   - L'opacité initiale est enregistrée (par défaut 255, opacité maximale)
   - Un timer de fade out est initialisé avec la durée `fade_duration`
   - La layer est marquée comme "en cours de masquage"
4. **Animation de fade out** : À chaque frame, dans `update(dt)` :
   - Le timer de fade out est décrémenté de `dt`
   - L'opacité est calculée proportionnellement : `opacity = int(255 * (timer / fade_duration))`
   - L'opacité est appliquée à la surface de la layer (via `set_alpha()` de pygame)
   - Si le timer atteint 0, l'opacité est fixée à 0 (complètement transparent)
5. **Suppression des collisions** : Une fois le fade out terminé (opacité = 0) :
   - Si `remove_collisions = true`, les collisions de la layer sont supprimées du système de collisions
   - La layer est marquée comme "masquée" et n'est plus rendue (ou rendue avec opacité 0)
   - Les rectangles de collision sont retirés du cache `_solid_rects_cache` du système de collisions
6. **Rendu** : Les layers masquées ne sont plus visibles à l'écran (opacité 0) mais continuent d'exister dans le système

**Note sur l'implémentation de l'opacité** :
- La classe `Layer` doit être étendue pour supporter l'opacité. Deux approches possibles :
  1. **Approche 1 (recommandée)** : Ajouter un attribut `alpha: int` (0-255) à la classe `Layer` et modifier la méthode `_draw_layer()` du `ParallaxSystem` pour appliquer l'opacité lors du rendu via `surface.set_alpha(alpha)` avant le `blit()`.
  2. **Approche 2** : Modifier directement la surface de la layer avec `set_alpha()`, mais cela nécessite de créer une copie de la surface pour éviter de modifier l'original.
- L'approche 1 est recommandée car elle permet de conserver la surface originale intacte et de gérer l'opacité de manière non destructive.
- Le système d'événements met à jour l'opacité des layers en cours de masquage à chaque frame dans `update(dt)`.

**Important** :
- Par défaut, un événement ne peut être déclenché qu'une seule fois (pas de re-déclenchement automatique). Si le paramètre `repeatable` est défini à `true` dans le fichier `.event`, l'événement peut être déclenché plusieurs fois
- Si plusieurs layers partagent le même tag, elles sont toutes masquées simultanément
- Le fade out est progressif et fluide, créant un effet visuel agréable
- Une fois masqué, le sprite peut être réaffiché via un événement `sprite_show`
- Si `remove_collisions = false`, les collisions restent actives même si le sprite est invisible (utile pour des obstacles invisibles)

#### Comportement de l'affichage de sprite

Lorsqu'un événement de type `sprite_show` est déclenché :

1. **Vérification** : Le système vérifie que le tag spécifié existe dans le dictionnaire `layers_by_tag`
2. **Récupération des layers** : Toutes les layers associées au tag sont récupérées depuis `layers_by_tag[sprite_tag]`
3. **Initialisation du fade in** : Pour chaque layer concernée :
   - L'opacité actuelle de la layer est enregistrée (peut être 0 si le sprite a été défini avec `initial_alpha = 0` dans le fichier `.niveau`, voir spécification 3)
   - Si l'opacité actuelle est déjà 0, le fade in commence depuis 0
   - Si l'opacité actuelle est supérieure à 0, le fade in commence depuis cette valeur (utile pour réafficher un sprite partiellement masqué)
   - Un timer de fade in est initialisé avec la durée `fade_duration`
   - La layer est marquée comme "en cours d'affichage"
4. **Animation de fade in** : À chaque frame, dans `update(dt)` :
   - Le timer de fade in est décrémenté de `dt` (le timer commence à `fade_duration` et diminue jusqu'à 0)
   - L'opacité est calculée proportionnellement : `progress = 1.0 - (timer / fade_duration)`, puis `opacity = int(initial_alpha + (255 - initial_alpha) * progress)`
   - Cette formule garantit que l'opacité passe progressivement de `initial_alpha` (opacité actuelle au moment du déclenchement) à 255 (complètement opaque)
   - L'opacité est appliquée à la surface de la layer (via `set_alpha()` de pygame)
   - Si le timer atteint 0, l'opacité est fixée à 255 (complètement opaque)
   - **Important** : L'opacité est mise à jour dans `update()` à chaque frame, garantissant que le `fade_duration` est respecté. Si une layer est en cours de fade out, elle est automatiquement retirée du timer de fade out avant d'être ajoutée au timer de fade in pour éviter les conflits.
5. **Restauration des collisions** : Une fois le fade in terminé (opacité = 255) :
   - Si `restore_collisions = true`, les collisions de la layer sont restaurées dans le système de collisions
   - La layer est marquée comme "affichée" et est rendue normalement
   - Les rectangles de collision sont recalculés et ajoutés au cache `_solid_rects_cache` du système de collisions
   - La layer est réintégrée dans la liste des layers de collision via `_get_solid_layers()`
6. **Rendu** : Les layers affichées deviennent progressivement visibles à l'écran (opacité passe de 0 à 255)

**Note sur l'implémentation de l'opacité** :
- La classe `Layer` doit être étendue pour supporter l'opacité. Deux approches possibles :
  1. **Approche 1 (recommandée)** : Ajouter un attribut `alpha: int` (0-255) à la classe `Layer` et modifier la méthode `_draw_layer()` du `ParallaxSystem` pour appliquer l'opacité lors du rendu via `surface.set_alpha(alpha)` avant le `blit()`.
  2. **Approche 2** : Modifier directement la surface de la layer avec `set_alpha()`, mais cela nécessite de créer une copie de la surface pour éviter de modifier l'original.
- L'approche 1 est recommandée car elle permet de conserver la surface originale intacte et de gérer l'opacité de manière non destructive.
- Le système d'événements met à jour l'opacité des layers en cours d'affichage à chaque frame dans `update(dt)`.

**Important** :
- Par défaut, un événement ne peut être déclenché qu'une seule fois (pas de re-déclenchement automatique). Si le paramètre `repeatable` est défini à `true` dans le fichier `.event`, l'événement peut être déclenché plusieurs fois
- Si plusieurs layers partagent le même tag, elles sont toutes affichées simultanément
- Le fade in est progressif et fluide, créant un effet visuel agréable
- Un sprite peut être masqué puis réaffiché plusieurs fois via des événements `sprite_hide` et `sprite_show` successifs
- Si `restore_collisions = false`, les collisions ne sont pas restaurées même si le sprite est visible (utile pour des décors sans collision)
- **État initial** : Les sprites qui doivent être affichés via `sprite_show` doivent initialement être masqués (opacité 0). Cela peut être fait de deux manières :
  1. En définissant `initial_alpha = 0` dans le fichier `.niveau` (voir spécification 3) - le sprite commence invisible dès le chargement du niveau
  2. Via un événement `sprite_hide` précédent - le sprite est masqué dynamiquement pendant le jeu
- Si un sprite est déjà visible (opacité > 0), un événement `sprite_show` augmentera son opacité jusqu'à 255, créant un effet de fade in depuis l'opacité actuelle
- Si un sprite a `initial_alpha = 0` dans le fichier `.niveau`, les collisions sont désactivées par défaut (même comportement qu'un sprite masqué via `sprite_hide`)

#### Intégration avec le système de progression

Le système de déclencheurs utilise `LevelProgressTracker` pour obtenir la position actuelle du joueur :

```python
# Dans EventTriggerSystem.update()
current_x = self.progress_tracker.current_x  # Utilise current_x directement (précision maximale)

# Vérifier les déclencheurs
for event in self.events:
    # Vérifier si l'événement peut être déclenché (pas encore déclenché OU répétable)
    can_trigger = (not event.triggered) or event.repeatable
    if can_trigger and event.trigger_x is not None and current_x >= event.trigger_x:
        self._execute_event(event)
        event.triggered = True  # Marquer comme déclenché (même si répétable, pour éviter les déclenchements multiples dans la même frame)
```

**Note sur `trigger_event_by_identifier()`** :
```python
# Dans EventTriggerSystem.trigger_event_by_identifier()
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
```

#### Intégration dans la boucle de jeu

```python
# Initialisation
progress_tracker = LevelProgressTracker(player)
progress_tracker.update(0.0)  # Initialiser avec la position du joueur

# Charger les PNJ et créer un dictionnaire indexé par ID
npcs_dict: Dict[str, NPC] = {}
for npc in npcs:
    npcs_dict[npc.id] = npc

# Créer le système de déclencheurs
# Note: layers_by_tag est retourné par level_loader.create_parallax_layers()
event_system = EventTriggerSystem(
    progress_tracker,
    npcs_dict,
    layers_by_tag,
    parallax_system,
    collision_system,  # Optionnel, nécessaire pour supprimer les collisions lors du masquage
    player,  # Optionnel, nécessaire pour les événements d'inventaire et de level up
    particle_system  # Optionnel, nécessaire pour les événements particle_effect
)

# Charger les événements
events_path = Path("levels/niveau_plateforme.event")
event_system.load_events(events_path)

# Dans la boucle de jeu
def update(dt: float) -> None:
    progress_tracker.update(dt)
    event_system.update(dt)  # Mettre à jour le système d'événements
    # ... autres mises à jour

def draw(screen: pygame.Surface) -> None:
    # Dessiner tous les éléments du jeu (couches, joueur, PNJ, UI, etc.)
    # ...
    
    # DERNIER : Dessiner l'overlay de fondu au noir (priorité absolue - au-dessus de TOUT)
    fade_alpha, fade_text, fade_text_alpha = event_system.get_screen_fade_state()
    if fade_alpha > 0:
        # Créer une surface noire avec l'opacité actuelle
        fade_surface = pygame.Surface((screen.get_width(), screen.get_height()))
        fade_surface.set_alpha(fade_alpha)
        fade_surface.fill((0, 0, 0))
        screen.blit(fade_surface, (0, 0))
        
        # Afficher le texte si présent et avec opacité > 0
        if fade_text and fade_text_alpha > 0:
            font_size = int(60 * (RENDER_WIDTH / DESIGN_WIDTH))  # Taille adaptée à la résolution
            font = pygame.font.SysFont("arial", font_size, bold=True)
            text_surface = font.render(fade_text, True, (255, 255, 255))
            # Appliquer l'opacité au texte
            text_surface.set_alpha(fade_text_alpha)
            text_x = (screen.get_width() - text_surface.get_width()) // 2
            text_y = (screen.get_height() - text_surface.get_height()) // 2
            screen.blit(text_surface, (text_x, text_y))
```

#### Gestion des erreurs

Le système doit gérer les erreurs suivantes :
- **Fichier introuvable** : Lever `FileNotFoundError` avec un message clair
- **Format invalide** : Lever `ValueError` avec indication de la ligne/section problématique
- **PNJ introuvable** : Si `npc_id` ne correspond à aucun PNJ chargé, lever `ValueError` avec un message indiquant l'ID manquant
- **Tag introuvable** : Si `sprite_tag` ne correspond à aucun tag défini dans le fichier `.niveau`, lever `ValueError` avec un message indiquant le tag manquant
- **Événement invalide** : Vérifier que `trigger_x` et `target_x` sont des nombres valides
- **Direction invalide** : Vérifier que `direction` est `"left"` ou `"right"`
- **Durée invalide** : Vérifier que `fade_duration` et `fade_in_duration` sont des nombres positifs
- **Position invalide** : Vérifier que `target_x` et `target_y` sont des nombres valides pour les événements `npc_magic_move`
- **Sprite sheet introuvable** : Si `sprite_sheet_path` est spécifié pour un événement `npc_magic_move`, vérifier que le fichier existe (lever `FileNotFoundError` si le fichier n'existe pas)

#### Validation

Le système doit valider :
- Que tous les champs obligatoires sont présents (`identifier`, `event_type`, `event_data`)
- Que `trigger_x` est optionnel (peut être `None` pour les événements déclenchés uniquement manuellement)
- Que `event_type` est valide (`"npc_move"`, `"npc_follow"`, `"npc_stop_follow"`, `"npc_magic_move"`, `"sprite_hide"`, `"sprite_show"`, `"sprite_move"`, `"sprite_move_perpetual"`, `"sprite_rotate"`, `"inventory_add"`, `"inventory_remove"`, `"level_up"`, `"screen_fade"` ou `"particle_effect"`)
- Que `repeatable` est un booléen si présent (défaut: `false`)
- Pour les événements de type `npc_move` :
  - Que `npc_id` est présent et correspond à un PNJ chargé
  - Que `target_x` est présent et est un nombre valide
  - Que `direction` est présent et est `"left"` ou `"right"`
  - Que `move_speed` est un nombre positif si présent
  - Que `move_animation_row` est un entier >= 0 si présent
  - Que `move_animation_frames` est un entier > 0 si présent
  - Que si `move_animation_row` est spécifié, `move_animation_frames` doit également être spécifié (et vice versa)
- Pour les événements de type `npc_follow` :
  - Que `npc_id` est présent et correspond à un PNJ chargé
  - Que `follow_distance` est un nombre positif si présent (en pixels)
  - Que `follow_speed` est un nombre positif si présent (en pixels par seconde)
  - Que `animation_row` est un entier >= 0 si présent
  - Que `animation_frames` est un entier > 0 si présent
  - Que si `animation_row` est spécifié, `animation_frames` doit également être spécifié (et vice versa)
  - Que l'instance `Player` est fournie au constructeur de `EventTriggerSystem` (sinon, l'événement ne peut pas être exécuté)
- Pour les événements de type `npc_stop_follow` :
  - Que `npc_id` est présent et correspond à un PNJ chargé
- Pour les événements de type `npc_magic_move` :
  - Que `npc_id` est présent et correspond à un PNJ chargé
  - Que `target_x` est présent et est un nombre valide (en pixels, position monde)
  - Que `target_y` est présent et est un nombre valide (en pixels, position monde)
  - Que `sprite_sheet_path` est une chaîne de caractères non vide si présent (chemin vers le sprite sheet)
  - Que `fade_in_duration` est un nombre positif si présent (en secondes)
  - Que `animation_row` est un entier >= 0 si présent (ligne du sprite sheet, 0-indexed)
  - Que `animation_start` est un entier >= 0 si présent (frame de départ, 0-indexed)
  - Que `direction` est `"left"` ou `"right"` si présent
- Pour les événements de type `sprite_hide` :
  - Que `sprite_tag` est présent et correspond à un tag défini dans le fichier `.niveau`
  - Que `fade_duration` est un nombre positif si présent (en secondes)
  - Que `remove_collisions` est un booléen si présent
- Pour les événements de type `sprite_show` :
  - Que `sprite_tag` est présent et correspond à un tag défini dans le fichier `.niveau`
  - Que `fade_duration` est un nombre positif si présent (en secondes)
  - Que `restore_collisions` est un booléen si présent
- Pour les événements de type `sprite_move` :
  - Que `sprite_tag` est présent et correspond à un tag défini dans le fichier `.niveau`
  - Que `move_x` est présent et est un nombre valide (en pixels)
  - Que `move_y` est présent et est un nombre valide (en pixels)
  - Que `move_speed` est un nombre positif si présent (en pixels par seconde)
  - Que l'instance `CollisionSystem` est fournie au constructeur de `EventTriggerSystem` (sinon, l'événement ne peut pas être exécuté correctement car il gère les passagers)
- Pour les événements de type `sprite_move_perpetual` :
  - Que `sprite_tag` est présent et correspond à un tag défini dans le fichier `.niveau`
  - Que `move_x` est présent et est un nombre valide (en pixels)
  - Que `move_y` est présent et est un nombre valide (en pixels)
  - Que `move_speed` est un nombre positif si présent (en pixels par seconde, doit être > 0 pour un mouvement perpétuel correct)
  - Que l'instance `CollisionSystem` est fournie au constructeur de `EventTriggerSystem` (sinon, l'événement ne peut pas être exécuté correctement car il gère les passagers)
- Pour les événements de type `sprite_rotate` :
  - Que `sprite_tag` est présent et correspond à un tag défini dans le fichier `.niveau`
  - Que `rotation_speed` est présent et est un nombre valide (en degrés par seconde, peut être positif ou négatif)
  - Que `duration` est présent et est un nombre positif (en secondes, doit être > 0)
- Pour les événements de type `inventory_add` :
  - Que `item_id` est présent et est une chaîne de caractères non vide
  - Que `quantity` est un entier positif si présent (>= 1)
  - Que l'instance `Player` est fournie au constructeur de `EventTriggerSystem` (sinon, l'événement ne peut pas être exécuté)
- Pour les événements de type `inventory_remove` :
  - Que `item_id` est présent et est une chaîne de caractères non vide
  - Que `quantity` est un entier positif si présent (>= 1)
  - Que l'instance `Player` est fournie au constructeur de `EventTriggerSystem` (sinon, l'événement ne peut pas être exécuté)
- Pour les événements de type `level_up` :
  - Aucune validation spécifique requise (l'événement ne nécessite pas de configuration supplémentaire)
  - Que l'instance `Player` est fournie au constructeur de `EventTriggerSystem` (sinon, l'événement ne peut pas être exécuté)
- Pour les événements de type `screen_fade` :
  - Que `fade_in_duration` est un nombre positif si présent (en secondes)
  - Que `black_duration` est un nombre positif ou nul si présent (en secondes, peut être 0.0 pour un fondu sans pause)
  - Que `fade_out_duration` est un nombre positif si présent (en secondes)
  - Que `text` est une chaîne de caractères (peut être vide) ou `null` si présent
- Pour les événements de type `particle_effect` :
  - Que `effect_type` est présent et est l'un des types valides (`"explosion"`, `"confetti"`, `"flame_explosion"`, `"rain"`, `"smoke"` ou `"sparks"`)
  - Que soit `sprite_tag` est présent, soit `spawn_area` est présent, soit `x` et `y` sont présents. Priorité : `sprite_tag` > `spawn_area` > `x`/`y`. Si `sprite_tag` est présent, `spawn_area`, `x` et `y` sont ignorés. Si `spawn_area` est présent (et `sprite_tag` n'est pas présent), `x` et `y` sont ignorés. Si ni `sprite_tag` ni `spawn_area` ne sont présents, `x` et `y` sont obligatoires
  - Que `sprite_tag` est une chaîne de caractères non vide si présent et correspond à un tag défini dans le fichier `.niveau` (doit exister dans `layers_by_tag`)
  - Que `spawn_edge` est l'un des valeurs valides (`"top"`, `"bottom"`, `"left"`, `"right"`) si présent. Si `spawn_edge` est présent, `sprite_tag` doit également être présent, sinon `spawn_edge` est ignoré
  - Que `x` est un nombre valide si présent (en pixels, coordonnées monde du design 1920x1080)
  - Que `y` est un nombre valide si présent (en pixels, coordonnées monde du design 1920x1080)
  - Que `spawn_area` est un dictionnaire avec les clés `x_min`, `x_max`, `y_min`, `y_max` si présent (en pixels, coordonnées monde du design 1920x1080). Chaque valeur doit être un nombre valide, et `x_min < x_max` et `y_min < y_max`. Si `sprite_tag` est présent, `spawn_area` est ignoré
  - Que `count` est un entier positif si présent (>= 1)
  - Que `speed` est un nombre positif si présent (en pixels/seconde)
  - Que `lifetime` est un nombre positif si présent (en secondes)
  - Que `size` est un entier positif si présent (en pixels, diamètre, >= 1)
  - Que `color` est un tableau de 3 entiers (RGB, chaque valeur entre 0 et 255) si présent, ou `null`. Si `colors` est spécifié, `color` est ignoré
  - Que `colors` est un tableau de tableaux de 3 entiers (chaque tableau représente une couleur RGB, chaque valeur entre 0 et 255) si présent, ou `null`. La liste ne doit pas être vide si spécifiée. Si `colors` est spécifié, `color` est ignoré. Pour `"flame_explosion"` et `"confetti"`, `colors` est ignoré car ces effets utilisent des palettes prédéfinies
  - Que `generation_duration` est un nombre positif si présent (en secondes, > 0). Si `null` ou non spécifié, toutes les particules sont créées immédiatement (comportement par défaut)
  - Que l'instance `ParticleSystem` est fournie au constructeur de `EventTriggerSystem` (sinon, l'événement ne peut pas être exécuté)

### `LevelProgressHUD`

- Fichier proposé : `src/moteur_jeu_presentation/game/hud/progress.py`.
- Responsabilités :
  - Charger/recevoir une police (réutiliser la police système existante si disponible).
  - Dessiner un petit panneau en haut à gauche :
    - Position fixe `(padding_x, padding_y)` (défaut 16 px de marge).
    - Fond semi-transparent `(0, 0, 0, 180)` avec coins arrondis (9 px) si le moteur HUD supporte, sinon rectangle simple.
    - Texte principal : `"{current_x:05d} px"` (chaque frame).
    - Texte secondaire optionnel : `"{ratio:.1%}"` si `level_width` connu (sous la valeur principale, police plus petite).
  - Prévoir un mode debug (activable via flag) affichant aussi `max_x_reached`.
  - S'assurer que le HUD suit les bonnes pratiques d'optimisation Pygame : surfaces pré-rendues pour le fond, re-rendu du texte uniquement lorsque la valeur change.
  - **Affichage de la distance** : Les positions du joueur et des PNJ sont stockées en repère de rendu (1280x720) dans le jeu, mais le HUD doit afficher la valeur en repère de design (1920x1080) pour correspondre aux valeurs dans les fichiers de configuration (`.pnj`, `.event`). Le HUD convertit donc la valeur avant l'affichage en multipliant par `DESIGN_WIDTH / RENDER_WIDTH = 1920 / 1280 = 1.5` : `converted_value = int(round(value * render_to_design_scale))`. Cette conversion garantit que la distance affichée correspond aux valeurs utilisées dans la configuration des niveaux et des événements.
  - **Option de masquage** : Le HUD peut être masqué via l'argument de ligne de commande `--hide-info-player`. Lorsque cette option est activée, le HUD ne doit pas être dessiné, mais le tracker continue de fonctionner normalement pour les autres systèmes qui en dépendent (déclencheurs d'événements, etc.). **Note importante** : L'option `--hide-info-player` masque également l'affichage de debug des coordonnées du joueur (`draw_debug_overlay`) qui affiche "Player X: ... Y: ..." en haut à gauche de l'écran. **Note importante** : L'option `--hide-info-player` ne cache pas le nom du joueur.

### Intégrations

1. **GameState / Loop**
   - Instancier `LevelProgressTracker` lors de l'entrée dans le niveau (`on_enter`).
   - Appeler `tracker.update(dt)` dans la boucle `update`.
   - Instancier `LevelProgressHUD` (en lui passant le tracker) et appeler `hud.draw(screen)` après le rendu principal des entités, **uniquement si l'option `--hide-info-player` n'est pas activée**.
   - **Gestion de l'argument `--hide-info-player`** :
     - Ajouter l'argument `--hide-info-player` au parser d'arguments dans `main.py` (fonction `parse_arguments()`).
     - L'argument doit être un flag booléen (`action="store_true"`).
     - Passer la valeur de cet argument à la boucle principale pour contrôler l'affichage du HUD.
     - Conditionner l'appel à `hud.draw(screen)` avec cette valeur : `if not args.hide_info_player: hud.draw(screen)`.
     - Conditionner également l'appel à `draw_debug_overlay(screen)` qui affiche les coordonnées du joueur ("Player X: ... Y: ...") : `if not args.hide_info_player: draw_debug_overlay(screen)`.
     - **Important** : Même si le HUD et l'overlay de debug sont masqués, le `LevelProgressTracker` doit continuer à fonctionner normalement (appel à `tracker.update(dt)`), car d'autres systèmes en dépendent (déclencheurs d'événements, dialogues, etc.).
     - **Important** : L'option `--hide-info-player` ne cache pas le nom du joueur. Le nom du joueur doit continuer à être affiché même lorsque cette option est activée.
2. **Player**
   - Exposer une propriété `position_world` si elle n'existe pas, ou documenter la source officielle de la coordonnée `x`.
   - Si le joueur est affecté par une caméra décalée, le tracker doit recevoir la position monde réelle (pas la position écran).
3. **Chargement de niveau**
   - Lors du chargement d'un fichier `.niveau` (spécification 3), fournir au tracker la largeur totale (`level_width`) lorsque l'information est disponible (par exemple somme des tiles horizontaux * taille tile).
4. **API de jalons**
   - Les systèmes futurs enregistreront leurs jalons via `register_milestone`.
   - Le tracker expose `get_triggered_milestones()` retournant la liste des identifiants déclenchés depuis le dernier appel (et les marque optionnellement comme consommés).
5. **Système de déclencheurs d'événements**
   - Instancier `EventTriggerSystem` lors de l'entrée dans le niveau avec :
     - Le `LevelProgressTracker`
     - Le dictionnaire des PNJ indexés par ID
     - Le dictionnaire `layers_by_tag` retourné par `LevelLoader.create_parallax_layers()`
     - Le `ParallaxSystem` pour accéder aux layers
     - Le `CollisionSystem` (optionnel, nécessaire pour supprimer les collisions lors du masquage de sprites)
     - Le `Player` (optionnel, nécessaire pour les événements d'inventaire et de level up)
     - Le `ParticleSystem` (optionnel, nécessaire pour les événements particle_effect, voir spécification 14)
   - Charger les événements depuis le fichier `.event` correspondant au niveau.
   - Appeler `event_system.update(dt)` dans la boucle `update` après `progress_tracker.update(dt)`.

### Gestion mémoire & performance

- Le tracker doit rester léger : éviter les allocations dans la boucle principale.
- L'historique est limité (par défaut 300 entrées) avec un `deque` à taille maximale.
- L'HUD ne doit pas recalculer les surfaces si la valeur `current_x` n'a pas changé depuis la frame précédente.

### Journalisation & Debug

- Ajouter un logger dédié (`logging.getLogger("moteur_jeu_presentation.progress")`).
- Niveau `DEBUG` : log lorsque `max_x_reached` augmente ou lorsqu'un jalon est franchi.
- Niveau `INFO` : log l'initialisation et la remise à zéro du tracker.

## Tests

- **Unitaires** :
  - `LevelProgressTracker` met à jour correctement `current_x` et `max_x_reached`.
  - Les jalons sont marqués `triggered` lorsque `current_x >= threshold_x`.
  - Reset remet l'état à zéro tout en conservant la configuration (`level_width`, jalons enregistrés).
- **Intégration** :
  - Simulation d'une boucle de jeu factice vérifiant que l'HUD met à jour son affichage uniquement lorsque la valeur change.
  - Vérifier la précision (arrondi) : progression arrondie à l'entier le plus proche pour l'affichage.
- **Tests visuels** :
  - Captures d'écran automatisées (si possible) pour vérifier l'overlay (position, lisibilité).

## Risques & mitigations

- **Dérive de position** : S'assurer que la position monde utilisée est cohérente avec le système de collision (spécification 4). Ajouter une assertion en mode debug si la valeur recule de plus de 500 px entre deux frames (probable téléportation).
- **Performance HUD** : Pré-rendu et caching pour éviter les re-rendu textes coûteux.
- **Évolutivité** : L'API de jalons doit rester passive pour permettre l'ajout futur de callbacks sans casser l'existant. Prévoir un champ `metadata` générique.

## Observabilité

- Exposer les valeurs dans le panneau debug général du jeu (si existant) via un hook (`DebugOverlay.register_section("progress", ...)`).
- Possibilité d'exporter l'historique en CSV via une commande debug (optionnel, documenter mais pas implémenter dans cette itération).

## Documentation

- Ajouter une section dédiée dans `README.md` résumant l'utilisation de l'API (`LevelProgressTracker`) pour les autres développeurs.
- Mettre à jour les schémas d'architecture si existants (dossier `docs/`) pour inclure ce nouveau composant.

**Statut** : ✅ Implémenté

**Modifications réalisées** :
- ✅ **Amélioration de l'animation de confettis** : Le nombre de confettis a été doublé (de 30 à 60 particules par émission) et un offset horizontal de 80 pixels a été ajouté pour déplacer les confettis plus loin à gauche et à droite du cadre, créant un effet visuel plus spectaculaire et visible
- ✅ **Émission en cône directionnel** : Les confettis sont maintenant émis en cône directionnel depuis chaque coin du cadre :
  - Coin haut gauche : cône vers le haut à gauche (-135°) avec dispersion de 30°
  - Coin haut droit : cône vers le haut à droite (-45°) avec dispersion de 30°
  - Utilisation de `direction_type="custom"` avec `direction_angle` et `direction_spread` pour créer ces cônes directionnels
- ✅ **Correction de la position d'émission des confettis** : Les confettis sont maintenant émis depuis les **coins arrondis visibles** du cadre, pas depuis les coins géométriques du rectangle ou depuis l'extérieur. Les positions d'émission tiennent compte du `corner_radius` :
  - Coin haut gauche : `frame_x + corner_radius` (point sur l'arc du coin arrondi au niveau du bord supérieur)
  - Coin haut droit : `frame_x + frame_width - corner_radius` (point sur l'arc du coin arrondi au niveau du bord supérieur)
  - Le `corner_radius` est recalculé de la même manière que dans `start_level_transition` (converti selon `scale_y`) pour garantir la cohérence avec le rendu visuel
  - **Correction importante** : L'offset horizontal (`horizontal_offset`) a été retiré car il faisait partir les confettis de l'extérieur du cadre visible. Les confettis partent maintenant exactement depuis les coins arrondis visibles du cadre.
- ✅ **Durée de transition de niveau** : Modification de la durée de l'animation de transition de niveau de 3.0 secondes à 1.5 secondes dans le code (fichier `src/moteur_jeu_presentation/entities/player.py`, ligne 258 : `self.level_transition_duration: float = 1.5`)
- ✅ Mise à jour du README.md pour refléter la nouvelle durée (1.5 secondes au lieu de 3 secondes)
- ✅ Mise à jour des exemples dans les spécifications 7 et 14 pour refléter la nouvelle durée
- ✅ Ajout des champs `direction_angle` et `direction_spread` dans la classe `ParticleEffectEventConfig` (fichier `src/moteur_jeu_presentation/game/events.py`)
- ✅ Modification de la méthode `_execute_particle_effect` pour appliquer ces paramètres à la configuration des particules pour tous les types d'effets
- ✅ Modification de la logique de calcul de direction dans `ParticleEffect._create_particles` et `ParticleEffect._create_single_particle` pour utiliser `direction_angle` et `direction_spread` lorsqu'ils sont spécifiés, même pour les types d'effets prédéfinis (`"sparks"`, `"rain"`, `"smoke"`, etc.)
- ✅ Ajout du parsing TOML pour `direction_angle` et `direction_spread` dans la méthode `load_events`
- ✅ Mise à jour du README avec documentation et exemples d'utilisation
- ✅ Correction : Les fonctions de configuration (`create_rain_config`, `create_sparks_config`, etc.) définissent maintenant explicitement toutes les valeurs par défaut (`color_variation`, `direction_spread`, etc.) pour garantir que les valeurs par défaut sont correctement utilisées même si ces paramètres ne sont pas spécifiés dans les événements. Cela évite les régressions où les valeurs par défaut de `ParticleEffectConfig` (comme `direction_spread = 2.0 * math.pi`) sont utilisées à la place des valeurs appropriées pour chaque type d'effet.
- ✅ **Mouvement horizontal indépendant sur plateformes mobiles** : Modification du système de physique pour permettre au joueur de se déplacer horizontalement (X) de manière indépendante lorsqu'il est attaché à une plateforme mobile. Le joueur suit automatiquement le mouvement de la plateforme en X et Y (`delta_x` et `delta_y`), tout en conservant le contrôle horizontal via les touches de direction. Cela permet au joueur de marcher sur la plateforme tout en étant transporté par elle. Modifications dans `main.py` (lignes 1688-1701) et `collision.py` (méthode `apply_platform_movements`, lignes 984-1006). Documentation ajoutée dans le README et les spécifications.
- ✅ **Option `--hide-info-player`** : Ajout d'un argument de ligne de commande `--hide-info-player` pour masquer les éléments de positionnement du joueur affichés en haut à gauche (HUD de progression et overlay de debug avec les coordonnées "Player X: ... Y: ..."). L'argument est ajouté dans `parse_arguments()` et l'affichage du HUD et de l'overlay de debug sont conditionnés dans `_draw_overlay_ui()`. **Important** : Même si le HUD et l'overlay de debug sont masqués, le `LevelProgressTracker` continue de fonctionner normalement pour les autres systèmes qui en dépendent (déclencheurs d'événements, dialogues, etc.). **Important** : L'option `--hide-info-player` ne cache pas le nom du joueur. Le nom du joueur doit continuer à être affiché même lorsque cette option est activée. Documentation ajoutée dans le README.
- ✅ **Animation de transition de niveau avec phases de zoom** : Modification de l'animation de transition de niveau pour inclure trois phases séquentielles :
  - **Phase 1 (zoom_in)** : Zoom progressif de 230% sur le joueur en 1 seconde avant l'affichage du texte
  - **Phase 2 (display)** : Affichage du texte "level X -> level Y" (et de la phrase d'amélioration si disponible) et alternance des sprites pendant 1.5 secondes (zoom maintenu à 230%)
  - **Phase 3 (zoom_out)** : Reset progressif du zoom à 100% en 1 seconde après l'affichage
  - Durée totale de l'animation : 3.5 secondes (1.0s + 1.5s + 1.0s)
  - Intégration avec le `CameraZoomController` (spécification 18) pour gérer les phases de zoom
  - Le texte de transition n'est affiché que pendant la phase "display"
  - Les confettis sont émis uniquement pendant la phase "display"
  - Modifications dans `src/moteur_jeu_presentation/entities/player.py` : ajout des propriétés de phase, modification de `start_level_transition()` pour accepter le `camera_zoom_controller`, modification de `_update_level_transition()` pour gérer les trois phases, modification de `_draw_level_transition()` pour n'afficher que pendant la phase "display"
  - Modification dans `src/moteur_jeu_presentation/main.py` : passage du `camera_zoom_controller` à `start_level_transition()`
  - Documentation mise à jour dans le README
  - ✅ **Modification du zoom de transition** : Le zoom de l'animation de transition de niveau a été modifié de 180% à 230% pour un effet visuel plus prononcé. La constante `DEFAULT_LEVEL_TRANSITION_ZOOM_PERCENT` dans `src/moteur_jeu_presentation/entities/player.py` a été mise à jour, ainsi que toutes les références dans la spécification et le README.
  - ✅ **Affichage des phrases d'amélioration dans le panneau de changement de niveau** : Ajout de la fonctionnalité pour afficher des phrases d'amélioration sous le texte "level X -> level Y" dans le cadre de transition de niveau. Les phrases sont configurées dans le fichier `config/player_stats.toml` dans une nouvelle section `[level_up_messages]` avec des clés `level_2`, `level_3`, `level_4`, `level_5`. Les messages sont optionnels et peuvent contenir des retours à la ligne pour des messages multi-lignes. Le texte d'amélioration est affiché en taille moyenne (40 pixels dans le repère de conception) en gris foncé (64, 64, 64) sous le texte principal. Modifications dans `src/moteur_jeu_presentation/stats/config.py` (ajout de `level_up_messages` à `PlayerStatsConfig`), `src/moteur_jeu_presentation/stats/loader.py` (chargement de la section `[level_up_messages]`), et `src/moteur_jeu_presentation/entities/player.py` (ajout des constantes `LEVEL_TRANSITION_IMPROVEMENT_TEXT_SIZE`, `LEVEL_TRANSITION_TEXT_SPACING`, `LEVEL_TRANSITION_IMPROVEMENT_TEXT_COLOR`, modification de `start_level_transition()` pour charger et afficher les messages). Documentation mise à jour dans le README.


