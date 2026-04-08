# 12 - Système de personnage non joueur

## Contexte

Cette spécification définit un système de personnages non joueurs (PNJ) pour le jeu. Les PNJ sont des entités positionnées sur la route du joueur, soumises à la gravité comme le joueur, et peuvent avoir des animations et un nom affiché. Le système utilise une configuration séparée de la configuration du niveau, permettant de placer facilement des PNJ à des positions spécifiques dans le monde.

## Objectifs

- Créer un système de configuration pour les PNJ séparé de la configuration du niveau
- Permettre le positionnement des PNJ en spécifiant uniquement leur coordonnée X
- Utiliser le moteur de gravité pour positionner automatiquement les PNJ sur le premier bloc de depth 2
- Gérer les fichiers de sprite et les animations pour les PNJ
- Afficher le nom des PNJ de la même manière que le nom du joueur
- Intégrer les PNJ dans le système de rendu et de physique existant
- **Système de dialogues** : Permettre de configurer des blocs de dialogue pour les PNJ. Chaque bloc de dialogue définit une plage de distance du joueur et contient une série d'échanges conversationnels entre le joueur et le PNJ. Le déclenchement des dialogues sera implémenté dans de futurs développements.

## Architecture

### Principe de fonctionnement

Le système de PNJ fonctionne en plusieurs étapes :

1. **Chargement de la configuration** : Charger la configuration des PNJ depuis un fichier séparé
2. **Positionnement initial** : Positionner le PNJ à la coordonnée X spécifiée
3. **Application de la gravité** : Utiliser le système de gravité pour faire tomber le PNJ jusqu'à ce qu'il rencontre le premier bloc de depth 2
4. **Gestion des animations** : Gérer les animations du PNJ selon sa configuration
5. **Affichage** : Rendre le PNJ et son nom dans la couche de gameplay (depth 2)
6. **Configuration des blocs de dialogue** : Charger les configurations de blocs de dialogue depuis le fichier TOML. Chaque bloc contient des échanges entre le joueur et le PNJ (le déclenchement sera implémenté dans de futurs développements)

### Configuration séparée

La configuration des PNJ est séparée de la configuration du niveau :
- **Fichier de niveau** (`.niveau`) : Définit le décor, les plateformes, etc.
- **Fichier de PNJ** (`.pnj` ou `.toml`) : Définit les PNJ présents dans le niveau

Cette séparation permet :
- De modifier les PNJ sans toucher à la configuration du niveau
- De réutiliser la même configuration de niveau avec différents PNJ
- De faciliter la gestion et l'édition des PNJ

### Positionnement automatique par gravité

Le positionnement vertical des PNJ est automatique :
- L'utilisateur spécifie la coordonnée X du PNJ (obligatoire)
- L'utilisateur peut optionnellement spécifier la coordonnée Y d'apparition initiale (`y` optionnel)
- Si `y` est défini : le PNJ commence à cette position Y, puis la gravité le fait tomber vers le sol en dessous (y plus grand dans le repère existant)
- Si `y` n'est pas défini : le PNJ commence à y=0.0 (en haut de l'écran), puis la gravité le fait tomber jusqu'à ce qu'il rencontre le premier bloc de depth 2
- Le PNJ s'arrête automatiquement sur le premier bloc solide rencontré
- Cela garantit que les PNJ sont toujours positionnés correctement sur les plateformes

## Spécifications techniques

### Structure des données

#### Classe `NPCConfig`

```python
@dataclass
class NPCConfig:
    """Configuration d'un PNJ individuel."""
    id: str  # Identifiant technique unique du PNJ (utilisé pour les déclencheurs d'événements, voir spécification 11)
    name: str  # Nom du PNJ (affiché au-dessus de sa tête)
    x: float  # Position horizontale dans l'espace du monde
    y: Optional[float] = None  # Position verticale d'apparition initiale (optionnel, en pixels). Si défini, le PNJ commence à cette position Y, puis la gravité le fait tomber vers le sol en dessous (y plus grand dans le repère existant). Si non défini, le PNJ commence à y=0.0 (en haut de l'écran) puis tombe jusqu'au premier bloc de depth 2.
    direction: Literal["left", "right"] = "right"  # Orientation initiale du PNJ (peut être modifiée dynamiquement)
    sprite_sheet_path: str  # Chemin vers le fichier sprite sheet du PNJ
    sprite_width: int  # Largeur d'un sprite individuel
    sprite_height: int  # Hauteur d'un sprite individuel
    sprite_scale: float = 2.0  # Facteur d'échelle pour l'affichage du sprite (défaut: 2.0 = 200%, double la taille)
    animations: Optional[Dict[str, AnimationConfig]] = None  # Animations du PNJ (optionnel)
    font_path: Optional[str] = None  # Police pour le nom (optionnel, utilise celle du joueur par défaut)
    font_size: int = 36  # Taille de la police pour le nom (définie dans le repère de conception 1920x1080, convertie vers 1280x720 lors de l'initialisation)
    name_color: Tuple[int, int, int] = (255, 255, 255)  # Couleur du nom
    name_outline_color: Tuple[int, int, int] = (0, 0, 0)  # Couleur du contour du nom
    name_offset_y: float = -4.0  # Décalage vertical du nom par rapport au haut du sprite
    dialogue_blocks: Optional[List[DialogueBlockConfig]] = None  # Liste des blocs de dialogue du PNJ (optionnel)
```

#### Classe `AnimationConfig`

```python
@dataclass
class AnimationConfig:
    """Configuration d'une animation pour un PNJ."""
    row: int  # Ligne dans le sprite sheet (0-indexed)
    num_frames: int  # Nombre de frames dans l'animation
    animation_speed: float  # Vitesse d'animation en frames par seconde
    loop: bool = True  # Si l'animation se répète en boucle
```

#### Classe `PlayerAnimationConfig`

```python
@dataclass
class PlayerAnimationConfig:
    """Configuration d'une animation du personnage principal pendant un dialogue.
    
    Cette configuration permet de déclencher une animation spécifique du personnage
    principal pendant qu'une bulle de dialogue est affichée. L'animation est automatiquement
    arrêtée lorsque la bulle est fermée ou que le dialogue passe à l'échange suivant.
    """
    
    sprite_sheet_path: str  # Chemin vers la planche de sprite à utiliser (relatif au répertoire du niveau du personnage, généralement dans sprite/personnage/{niveau}/)
    row: int  # Ligne du sprite sheet à utiliser pour l'animation (0-indexed)
    num_frames: int  # Nombre de frames dans l'animation
    animation_speed: float  # Vitesse d'animation en frames par seconde (FPS)
    animation_type: Literal["simple", "loop", "pingpong"] = "simple"  # Type d'animation :
    #   - "simple" : L'animation se joue une seule fois puis reste sur la dernière frame
    #   - "loop" : L'animation se répète en boucle indéfiniment
    #   - "pingpong" : L'animation va de la première à la dernière frame, puis revient en arrière, et ainsi de suite
    start_sprite: int = 0  # Premier sprite à afficher dans la séquence d'animation (0-indexed, par défaut: 0). Permet de commencer l'animation à un sprite spécifique au lieu de toujours commencer au premier sprite.
    offset_y: float = 0.0  # Offset vertical à appliquer à l'animation (en pixels, par défaut: 0.0). Cet offset est appliqué pendant toute la durée de l'animation pour ajuster la position verticale du personnage pendant l'animation de dialogue.
    set_x_position: Optional[float] = None  # Position X à définir pour le personnage principal (optionnel, en pixels dans le repère de conception 1920x1080). Si présent, déplace le personnage principal à cette position lors de l'affichage de l'échange. La caméra est automatiquement déplacée de la même façon pour maintenir la visibilité du sprite (la caméra suit le personnage selon la formule `camera_x = player.x - render_width / 2`). La valeur est convertie automatiquement du repère de conception vers le repère de rendu interne (1280x720) lors de l'application.
```

#### Classe `DialogueExchangeConfig`

```python
@dataclass
class DialogueExchangeConfig:
    """Configuration d'un échange dans un bloc de dialogue.
    
    Un échange représente une réplique d'un personnage (NPC ou joueur) dans une conversation.
    Chaque échange indique qui parle, le texte correspondant, et optionnellement une image.
    
    **Déclenchement d'événements** : Chaque échange peut déclencher des événements du système
    de déclencheurs d'événements (voir spécification 11). Les événements sont déclenchés
    lorsque l'échange est affiché (lors de la création de la bulle de dialogue pour cet échange).
    """

    speaker: Literal["npc", "player"]  # Personnage qui parle dans cet échange ("npc" ou "player")
    text: str  # Texte de l'échange (peut contenir des \n pour les retours à la ligne, peut être vide si une image est présente)
    font_size: int = 32  # Taille de la police pour cet échange (optionnel, peut être surchargée par le bloc)
    text_speed: float = 30.0  # Vitesse d'affichage du texte en caractères par seconde (optionnel, peut être surchargée par le bloc)
    image_path: Optional[str] = None  # Chemin vers l'image à afficher dans la bulle (optionnel, relatif au répertoire `image` du projet)
    trigger_events: Optional[List[str]] = None  # Liste des identifiants d'événements à déclencher lorsque cet échange est affiché (optionnel). Les événements doivent être définis dans le fichier .event du niveau (voir spécification 11). Les événements sont déclenchés lors de l'affichage de l'échange, avant que la bulle ne soit créée. Si un événement n'existe pas ou a déjà été déclenché (et n'est pas marqué comme `repeatable`), il est ignoré silencieusement. Les types d'événements supportés incluent : "npc_move", "npc_follow", "npc_stop_follow", "sprite_hide", "sprite_show", "sprite_move", "inventory_add", "inventory_remove" et "level_up" (voir spécification 11 pour plus de détails). Pour permettre à un événement d'être déclenché plusieurs fois lors de conversations répétées, définir `repeatable = true` dans le fichier .event (voir spécification 11).
    add_items: Optional[Dict[str, int]] = None  # Dictionnaire des objets à ajouter à l'inventaire du joueur (optionnel). Clé = item_id (ID technique de l'objet), valeur = quantité. Les objets sont ajoutés lors de l'affichage de l'échange, avec animation d'apparition progressive (voir spécification 13). Les objets doivent être définis dans inventory_items.toml.
    remove_items: Optional[Dict[str, int]] = None  # Dictionnaire des objets à retirer de l'inventaire du joueur (optionnel). Clé = item_id (ID technique de l'objet), valeur = quantité. Les objets sont retirés lors de l'affichage de l'échange, avec animation de saut vers l'arrière puis disparition (voir spécification 13). Si la quantité disponible est insuffisante, l'opération échoue silencieusement (log un avertissement).
    player_animation: Optional[PlayerAnimationConfig] = None  # Animation du personnage principal pendant cet échange (optionnel). L'animation est déclenchée lorsque l'échange est affiché et s'arrête lorsque l'échange se termine ou que le dialogue passe à l'échange suivant. Si `set_x_position` est défini dans la configuration d'animation, le personnage principal est déplacé à cette position lors de l'affichage de l'échange, et la caméra est automatiquement ajustée pour maintenir la visibilité.
```

#### Classe `DialogueBlockConfig`

```python
@dataclass
class DialogueBlockConfig:
    """Configuration d'un bloc de dialogue pour un PNJ.
    
    Un bloc de dialogue est déclenché selon la position du joueur dans le monde et contient
    une série d'échanges conversationnels entre le PNJ et le joueur.
    
    **Mécanisme de sélection** : La plage de position (`position_min` et `position_max`)
    est utilisée pour déterminer quel bloc de dialogue sera lancé. Lorsqu'une interaction
    est déclenchée, le système fournit la position horizontale du joueur dans le monde
    (obtenue via le système de gestion de l'avancement dans le niveau via `LevelProgressTracker.get_current_x()`,
    voir spécification 11), puis sélectionne le premier bloc dont la plage correspond à cette position.
    
    **Type de dialogue** : Le champ `dialogue_type` détermine l'affichage de l'indicateur d'interaction
    au-dessus du PNJ. Si le type est "quête", un "!" est affiché au lieu de "T pour parler".
    Si le type est "discution", l'indicateur affiche "T pour ecouter et donner son avis".
    Si le type est "ecoute", l'indicateur affiche "T pour écouter".
    Si le type est "regarder", l'indicateur affiche "T pour regarder ce que c'est".
    Si le type est "enseigner", l'indicateur affiche "T pour former".
    Si le type est "reflexion", l'indicateur affiche "T pour reflechir".
    
    **Note** : Le déclenchement d'événements est géré au niveau des échanges individuels
    (voir `DialogueExchangeConfig.trigger_events`), pas au niveau du bloc.
    """

    position_min: float  # Position minimale en pixels (position horizontale du joueur dans le monde) - inclus. OBLIGATOIRE : utilisé pour sélectionner le bloc de dialogue à déclencher
    position_max: float  # Position maximale en pixels (position horizontale du joueur dans le monde) - inclus. OBLIGATOIRE : utilisé pour sélectionner le bloc de dialogue à déclencher
    exchanges: List[DialogueExchangeConfig]  # Liste des échanges du bloc (au moins un échange requis, pas de limite supérieure)
    dialogue_type: Literal["normal", "quête", "discution", "ecoute", "regarder", "enseigner", "reflexion"] = "normal"  # Type de dialogue (optionnel, défaut: "normal"). Si "quête", l'indicateur d'interaction affiche un "!" au lieu de "T pour parler". Si "discution", l'indicateur affiche "T pour ecouter et donner son avis". Si "ecoute", l'indicateur affiche "T pour écouter". Si "regarder", l'indicateur affiche "T pour regarder ce que c'est". Si "enseigner", l'indicateur affiche "T pour former". Si "reflexion", l'indicateur affiche "T pour reflechir"
    font_size: int = 32  # Taille de la police pour les dialogues (optionnel, peut être surchargée par chaque échange)
    text_speed: float = 30.0  # Vitesse d'affichage du texte en caractères par seconde (optionnel, peut être surchargée par chaque échange)
```

#### Classe `NPCsConfig`

```python
@dataclass
class NPCsConfig:
    """Configuration complète des PNJ pour un niveau."""
    npcs: List[NPCConfig]  # Liste des PNJ
```

#### Classe `Entity` (classe abstraite de base)

```python
class Entity(ABC):
    """Classe de base abstraite pour toutes les entités du jeu (joueur, PNJ, etc.)."""
    
    def __init__(
        self,
        x: float,
        y: float,
        sprite_width: int,
        sprite_height: int,
    ) -> None:
        """Initialise une entité.
        
        Args:
            x: Position horizontale initiale
            y: Position verticale initiale
            sprite_width: Largeur d'un sprite
            sprite_height: Hauteur d'un sprite
        """
    
    def get_collision_rect(self) -> pygame.Rect:
        """Récupère le rectangle de collision de l'entité.
        
        Returns:
            Rectangle de collision dans l'espace du monde
        """
    
    @abstractmethod
    def update(self, dt: float, camera_x: float) -> None:
        """Met à jour l'entité."""
    
    @abstractmethod
    def draw(self, surface: pygame.Surface, camera_x: float) -> None:
        """Dessine l'entité sur la surface."""
```

**Propriétés communes** :
- `x: float` : Position horizontale
- `y: float` : Position verticale
- `sprite_width: int` : Largeur d'un sprite
- `sprite_height: int` : Hauteur d'un sprite
- `collision_width: float` : Largeur du rectangle de collision
- `collision_height: float` : Hauteur du rectangle de collision
- `collision_offset_x: float` : Offset horizontal du rectangle de collision
- `collision_offset_y: float` : Offset vertical du rectangle de collision
- `velocity_y: float` : Vitesse verticale (pour la gravité)
- `gravity: float` : Force de gravité
- `max_fall_speed: float` : Vitesse maximale de chute
- `is_on_ground: bool` : Indique si l'entité est au sol

**Note** : La classe `Entity` fournit une interface commune pour le système de collisions. Le système de collisions accepte maintenant une `Entity` au lieu d'un `Player` spécifique, permettant une meilleure réutilisabilité du code.

#### Classe `NPC`

```python
class NPC(Entity):
    """Représente un personnage non joueur."""
    
    def __init__(
        self,
        config: NPCConfig,
        collision_system: CollisionSystem,
        assets_root: Optional[Path] = None
    ) -> None:
        """
        Args:
            config: Configuration du PNJ
            collision_system: Système de collisions pour le positionnement par gravité
            assets_root: Répertoire de base pour les ressources
        """
    
    def update(self, dt: float, camera_x: float) -> None:
        """Met à jour le PNJ (gravité, collisions, animations, déplacements).
        
        La gravité s'applique en permanence au PNJ, même pendant les déplacements
        déclenchés par événements. Les collisions sont résolues à chaque frame pour
        maintenir le PNJ au sol ou gérer les chutes.
        
        Args:
            dt: Delta time en secondes
            camera_x: Position horizontale de la caméra
        """
    
    def draw(self, surface: pygame.Surface, camera_x: float) -> None:
        """Dessine le PNJ sur la surface.
        
        Args:
            surface: Surface pygame sur laquelle dessiner
            camera_x: Position horizontale de la caméra
        """
    
    def draw_name(self, surface: pygame.Surface, camera_x: float) -> None:
        """Dessine le nom du PNJ au-dessus de sa tête.
        
        Args:
            surface: Surface pygame sur laquelle dessiner
            camera_x: Position horizontale de la caméra
        """
```

**Propriétés** (héritées de `Entity` + spécifiques au PNJ) :
- Propriétés héritées de `Entity` : `x`, `y`, `sprite_width`, `sprite_height`, `collision_width`, `collision_height`, `collision_offset_x`, `collision_offset_y`, `velocity_y`, `gravity`, `max_fall_speed`, `is_on_ground`
- `id: str` : Identifiant technique unique du PNJ (utilisé pour les déclencheurs d'événements, voir spécification 11)
- `direction: Literal["left", "right"]` : Orientation actuelle du PNJ (initialisée depuis la configuration, peut être modifiée dynamiquement pour des mouvements futurs)
- `sprite_sheet: pygame.Surface` : Surface contenant le sprite sheet complet
- `sprite_scale: float` : Facteur d'échelle pour l'affichage du sprite (défaut: 2.0 = 200%, double la taille)
- `display_width: int` : Largeur d'affichage du sprite (sprite_width * sprite_scale)
- `display_height: int` : Hauteur d'affichage du sprite (sprite_height * sprite_scale)
- `current_animation: Optional[str]` : Nom de l'animation actuelle (None si aucune animation)
- `current_frame: int` : Index de la frame d'animation actuelle
- `animation_timer: float` : Timer pour gérer la vitesse d'animation
- `name_surface: Optional[pygame.Surface]` : Surface contenant le nom rendu
- `name_rect: Optional[pygame.Rect]` : Rectangle pour positionner le nom
- `font: pygame.font.Font` : Police utilisée pour le nom
- `name: str` : Nom du PNJ
- `_positioned: bool` : Indique si le PNJ a été positionné par la gravité
- `dialogue_blocks: Optional[List[DialogueBlockConfig]]` : Liste des blocs de dialogue configurés pour ce PNJ
- `_move_target_x: Optional[float]` : Position X cible pour le déplacement (None si aucun déplacement en cours)
- `_move_speed: float` : Vitesse de déplacement horizontal en pixels par seconde (utilisée lors des déplacements déclenchés par événements)
- `_move_animation_row: Optional[int]` : Ligne du sprite sheet pour l'animation de déplacement temporaire (None si aucune animation temporaire)
- `_move_animation_frames: Optional[int]` : Nombre de frames pour l'animation de déplacement temporaire (None si aucune animation temporaire)
- `_is_following_player: bool` : Indique si le PNJ suit actuellement le personnage principal (défaut: False)
- `_follow_player: Optional[Player]` : Référence au personnage principal à suivre (None si le PNJ ne suit pas)
- `_follow_distance: float` : Distance horizontale à maintenir derrière le personnage principal en pixels (défaut: 100.0)
- `_follow_speed: float` : Vitesse de déplacement lors du suivi en pixels par seconde (défaut: 200.0)
- `_follow_animation_row: Optional[int]` : Ligne du sprite sheet pour l'animation de suivi (None si aucune animation spécifique)
- `_follow_animation_frames: Optional[int]` : Nombre de frames pour l'animation de suivi (None si aucune animation spécifique)
- `_player_last_x: float` : Position X précédente du joueur (utilisée pour détecter les changements de direction lors du suivi, initialisée à 0.0)

**Méthodes principales** :
- `update(dt: float, camera_x: float) -> None` : Met à jour la position et l'animation (implémente la méthode abstraite de `Entity`)
- `draw(surface: pygame.Surface, camera_x: float) -> None` : Dessine le PNJ en appliquant l'orientation (flip horizontal si `direction == "left"`) (implémente la méthode abstraite de `Entity`)
- `draw_name(surface: pygame.Surface, camera_x: float) -> None` : Dessine le nom
- `get_collision_rect() -> pygame.Rect` : Récupère le rectangle de collision (héritée de `Entity`)
- `_get_current_sprite() -> pygame.Surface` : Récupère le sprite actuel à afficher
- `_update_animation(dt: float) -> None` : Met à jour l'animation
- `_apply_gravity(dt: float, camera_x: float) -> None` : Applique la gravité et résout les collisions verticales. Cette méthode est appelée en permanence à chaque frame, pas seulement lors du positionnement initial.
- `_render_name() -> None` : Génère la surface contenant le nom avec contour
- `get_dialogue_block_for_position(player_position: float) -> Optional[DialogueBlockConfig]` : Retourne le bloc de dialogue correspondant à la position du joueur donnée. **La position est fournie en paramètre par le système** (via le système de gestion de l'avancement dans le niveau, voir spécification 11) et n'est pas calculée par cette méthode. La méthode parcourt les blocs de dialogue dans l'ordre de définition et retourne le **premier bloc dont la plage de position correspond** (`position_min <= player_position <= position_max`). Retourne `None` si aucun bloc ne correspond à la position fournie.
- `get_dialogue_type_for_position(player_position: float) -> Optional[Literal["normal", "quête", "discution", "ecoute", "regarder", "enseigner", "reflexion"]]` : Retourne le type de dialogue du bloc correspondant à la position du joueur donnée. Utilise `get_dialogue_block_for_position()` pour obtenir le bloc, puis retourne son `dialogue_type`. Retourne `None` si aucun bloc ne correspond à la position. Cette méthode est utilisée par le système d'interaction pour déterminer quel indicateur afficher (voir spécification 2).
- `start_movement(target_x: float, speed: float, direction: Literal["left", "right"], animation_row: Optional[int] = None, animation_frames: Optional[int] = None) -> None` : Démarre un déplacement horizontal du PNJ vers `target_x` à la vitesse `speed`. Change la direction du PNJ et active une animation temporaire si spécifiée. Cette méthode est appelée par le système de déclencheurs d'événements (voir spécification 11).
- `is_moving() -> bool` : Retourne `True` si le PNJ est actuellement en déplacement (utilisé par le système de déclencheurs pour vérifier l'état).
- `start_following_player(player: Player, follow_distance: float = 100.0, follow_speed: float = 200.0, animation_row: Optional[int] = None, animation_frames: Optional[int] = None) -> None` : Démarre le suivi du personnage principal. Le PNJ se positionne automatiquement derrière le joueur (à droite si le joueur va à gauche, à gauche si le joueur va à droite) et maintient une distance constante. La direction du PNJ est automatiquement gérée en fonction de la direction du joueur. Cette méthode est appelée par le système de déclencheurs d'événements (voir spécification 11).
- `stop_following_player() -> None` : Arrête le suivi du personnage principal. Le PNJ reprend son comportement normal (animation idle, etc.).
- `is_following_player() -> bool` : Retourne `True` si le PNJ suit actuellement le personnage principal.

#### Classe `DialogueState`

```python
class DialogueState:
    """Gère l'état d'un dialogue en cours avec un PNJ.
    
    Cette classe gère l'affichage séquentiel des échanges d'un bloc de dialogue,
    en utilisant le système de bulles de dialogue (SpeechBubble) pour chaque échange.
    
    **Déclenchement d'événements** : Les événements associés à chaque échange sont déclenchés
    lorsque l'échange est affiché (dans `_create_bubble_for_exchange`), pas lors de la création
    du DialogueState. Cela permet de déclencher des événements à des moments précis de la conversation.
    """
    
    def __init__(
        self,
        npc: NPC,
        player: Player,
        dialogue_block: DialogueBlockConfig,
        event_system: Optional[EventTriggerSystem] = None,
    ) -> None:
        """
        Args:
            npc: Le PNJ avec qui le dialogue a lieu
            player: Le joueur participant au dialogue (obligatoire, utilisé pour les opérations d'inventaire)
            dialogue_block: Le bloc de dialogue à afficher
            event_system: Système de déclencheurs d'événements (optionnel). Si fourni, les événements
                         référencés dans les échanges seront déclenchés lors de l'affichage de chaque échange.
        """
    
    def update(self, camera_x: float, dt: float) -> None:
        """Met à jour l'état du dialogue (position de la bulle, animation du texte).
        
        Args:
            camera_x: Position horizontale de la caméra
            dt: Delta time en secondes
        """
    
    def handle_event(self, event: pygame.event.Event, camera_x: float) -> bool:
        """Gère les événements (clic n'importe où sur l'écran pour passer à l'échange suivant).
        
        Args:
            event: Événement pygame à traiter
            camera_x: Position horizontale de la caméra (non utilisée, conservée pour compatibilité)
        
        Returns:
            True si l'événement a été traité, False sinon
        
        Note:
            Le clic peut être effectué n'importe où sur l'écran, pas seulement sur la bulle.
            Si le texte n'est pas complètement affiché, le clic accélère l'affichage.
            Si le texte est complètement affiché, le clic passe à l'échange suivant.
        """
    
    def draw(self, surface: pygame.Surface, camera_x: float) -> None:
        """Dessine la bulle de dialogue actuelle.
        
        Args:
            surface: Surface pygame sur laquelle dessiner
            camera_x: Position horizontale de la caméra
        """
    
    def is_complete(self) -> bool:
        """Vérifie si le dialogue est terminé (tous les échanges ont été affichés).
        
        Returns:
            True si le dialogue est terminé, False sinon
        """
```

**Propriétés** :
- `npc: NPC` : Le PNJ avec qui le dialogue a lieu
- `player: Player` : Le joueur participant au dialogue
- `dialogue_block: DialogueBlockConfig` : Le bloc de dialogue en cours
- `event_system: Optional[EventTriggerSystem]` : Système de déclencheurs d'événements (optionnel)
- `current_exchange_index: int` : Index de l'échange actuellement affiché (commence à 0)
- `current_bubble: Optional[SpeechBubble]` : Bulle de dialogue actuelle (None si le dialogue est terminé)
- `is_active: bool` : Indique si le dialogue est actif (en cours)

**Méthodes principales** :
- `update(camera_x: float, dt: float) -> None` : Met à jour la bulle actuelle et vérifie si le dialogue est terminé
- `handle_event(event: pygame.event.Event, camera_x: float) -> bool` : Gère les clics (n'importe où sur l'écran) pour passer à l'échange suivant
- `draw(surface: pygame.Surface, camera_x: float) -> None` : Dessine la bulle actuelle
- `is_complete() -> bool` : Retourne True si tous les échanges ont été affichés
- `_next_exchange() -> None` : Passe à l'échange suivant (appelé après un clic lorsque le texte est complet)
- `_create_bubble_for_exchange(exchange: DialogueExchangeConfig, assets_root: Optional[Path] = None) -> SpeechBubble` : Crée une bulle pour un échange donné (avec texte et/ou image). Le paramètre `assets_root` est utilisé pour résoudre les chemins d'images relatifs. Si `exchange.image_path` est présent, il est passé à `SpeechBubble` avec `assets_root`. Par défaut, `assets_root` doit être `Path("image")` car les images de dialogue doivent être placées dans le répertoire `image` du projet. **IMPORTANT** : Cette méthode déclenche les événements associés à l'échange (si `event_system` est fourni et que `exchange.trigger_events` est défini) avant de créer la bulle. Cette méthode ajoute également les objets à l'inventaire (si `exchange.add_items` est défini) et retire les objets de l'inventaire (si `exchange.remove_items` est défini) avec animations (voir spécification 13).

**Comportement** :
- Au démarrage, affiche le premier échange du bloc (les événements associés au premier échange sont déclenchés lors de son affichage)
- Chaque échange est affiché via une `SpeechBubble` associée au personnage qui parle (NPC ou joueur)
- **Déclenchement d'événements** : Lorsqu'un échange est affiché (dans `_create_bubble_for_exchange`), si `event_system` est fourni et que l'échange contient `trigger_events`, les événements référencés sont déclenchés avant la création de la bulle
- **Ajout d'objets à l'inventaire** : Lorsqu'un échange est affiché (dans `_create_bubble_for_exchange`), si `player` est fourni et que l'échange contient `add_items`, les objets sont ajoutés à l'inventaire du joueur avec animation d'apparition progressive (voir spécification 13). Les objets sont ajoutés via `player.inventory.add_item(item_id, quantity, animated=True)` pour chaque entrée du dictionnaire.
- **Retrait d'objets de l'inventaire** : Lorsqu'un échange est affiché (dans `_create_bubble_for_exchange`), si `player` est fourni et que l'échange contient `remove_items`, les objets sont retirés de l'inventaire du joueur avec animation de saut vers l'arrière puis disparition (voir spécification 13). Les objets sont retirés via `player.inventory.remove_item(item_id, quantity, animated=True)` pour chaque entrée du dictionnaire. Si la quantité disponible est insuffisante, l'opération échoue silencieusement (log un avertissement).
- Le clic n'importe où sur l'écran accélère l'affichage du texte si celui-ci n'est pas complet
- Une fois le texte complètement affiché, un nouveau clic (n'importe où sur l'écran) passe à l'échange suivant (les événements du nouvel échange sont déclenchés lors de son affichage)
- Quand tous les échanges ont été affichés, le dialogue se termine (`is_complete()` retourne True)

#### Fonction `start_dialogue()`

```python
def start_dialogue(
    npc: NPC,
    progress_tracker: LevelProgressTracker,
    event_system: Optional[EventTriggerSystem] = None,
) -> Optional[DialogueState]:
    """Démarre un dialogue avec un PNJ en fonction de la position du joueur.
    
    Cette fonction obtient la position actuelle du joueur via le système de progression,
    sélectionne le bloc de dialogue approprié, et crée un DialogueState pour gérer l'affichage.
    
    Args:
        npc: Le PNJ avec qui démarrer le dialogue
        progress_tracker: Système de progression pour obtenir la position du joueur.
                         Doit être fourni (obligatoire).
        event_system: Système de déclencheurs d'événements (optionnel). Si fourni, les événements
                     référencés dans les échanges seront déclenchés lors de l'affichage de chaque échange.
    
    Returns:
        DialogueState si un bloc de dialogue correspond à la position, None sinon
    
    Note:
        Les événements référencés dans `trigger_events` de chaque échange sont déclenchés
        lorsque l'échange est affiché (dans `DialogueState._create_bubble_for_exchange`),
        pas lors du lancement du dialogue. Cela permet de déclencher des événements à des
        moments précis de la conversation. Si un événement n'existe pas ou a déjà été déclenché
        (et n'est pas marqué comme `repeatable` dans le fichier .event), il est ignoré silencieusement.
        Pour permettre à un événement d'être déclenché plusieurs fois lors de conversations répétées,
        définir `repeatable = true` dans le fichier .event (voir spécification 11).
    """
```

**Comportement** :
- Obtient la position actuelle du joueur : `player_position = progress_tracker.current_x` (utilise `current_x` directement pour une précision maximale, pas `get_current_x()` qui arrondit)
- Appelle `npc.get_dialogue_block_for_position(player_position)` pour obtenir le bloc approprié
- Si un bloc est trouvé :
  - Crée et retourne un `DialogueState` en passant `event_system` au constructeur
- Si aucun bloc ne correspond, retourne `None`

**Note sur le déclenchement des événements** :
- Les événements ne sont **pas** déclenchés dans cette fonction
- Les événements sont déclenchés au niveau des échanges individuels, lors de leur affichage (dans `DialogueState._create_bubble_for_exchange`)
- Le `event_system` est passé au `DialogueState` pour permettre le déclenchement des événements lors de l'affichage de chaque échange

**Note importante** : Le `LevelProgressTracker` doit être initialisé avec la position initiale du joueur en appelant `progress_tracker.update(0.0)` après sa création, afin que `current_x` reflète immédiatement la position du joueur et que les dialogues puissent être déclenchés dès le début du jeu.

#### Classe `NPCLoader`

```python
class NPCLoader:
    """Chargeur de fichiers de configuration de PNJ."""
    
    def __init__(self, assets_dir: Path) -> None:
        """
        Args:
            assets_dir: Répertoire de base pour les ressources
        """
    
    def load_npcs(self, npcs_path: Path) -> NPCsConfig:
        """Charge un fichier de configuration de PNJ.
        
        Args:
            npcs_path: Chemin vers le fichier .pnj ou .toml
            
        Returns:
            Configuration des PNJ chargée
            
        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            ValueError: Si le format du fichier est invalide
        """
```

### Format TOML du fichier de PNJ

Le fichier de PNJ utilise le format TOML pour sa lisibilité et sa facilité d'édition. Le fichier sera nommé avec l'extension `.pnj` ou `.toml`.

#### Structure du fichier

```toml
# Fichier : levels/niveau_plateforme.pnj
# Configuration des PNJ pour le niveau

[[npcs]]
id = "robot_01"  # Identifiant technique unique (obligatoire)
name = "Robot"
x = 500.0
# y = 400.0  # Optionnel : position verticale d'apparition initiale. Si défini, le PNJ commence à cette position Y puis tombe vers le sol.
direction = "right"
sprite_sheet_path = "sprite/robot.png"
sprite_width = 44
sprite_height = 64

# Animations optionnelles
[npcs.animations.idle]
row = 0
num_frames = 4
animation_speed = 8.0
loop = true

[npcs.animations.walk]
row = 0
num_frames = 4
animation_speed = 10.0
loop = true

# Configuration du nom (optionnel)
npcs.font_size = 36
npcs.name_color = [255, 255, 255]
npcs.name_outline_color = [0, 0, 0]
npcs.name_offset_y = -4.0

# Blocs de dialogue optionnels
[[npcs.dialogue_blocks]]
distance_min = 0.0
distance_max = 100.0

[[npcs.dialogue_blocks.exchanges]]
speaker = "npc"
text = "Bonjour !\nJe suis un robot."

[[npcs.dialogue_blocks.exchanges]]
speaker = "player"
text = "Regardez cette image !"
image_path = "dialogue_image.png"  # Image dans le répertoire "image"

[[npcs.dialogue_blocks.exchanges]]
speaker = "npc"
text = ""  # Texte vide, seule l'image sera affichée
image_path = "npc_response.png"  # Image dans le répertoire "image"

[[npcs.dialogue_blocks]]
distance_min = 100.0
distance_max = 200.0

[[npcs.dialogue_blocks.exchanges]]
speaker = "npc"
text = "Approchez-vous pour mieux m'entendre !"

[[npcs.dialogue_blocks.exchanges]]
speaker = "player"
text = "D'accord, je m'approche."

[[npcs]]
id = "marchand_01"  # Identifiant technique unique (obligatoire)
name = "Marchand"
x = 1200.0
direction = "left"
sprite_sheet_path = "sprite/marchand.png"
sprite_width = 64
sprite_height = 64

[npcs.animations.idle]
row = 0
num_frames = 2
animation_speed = 5.0
loop = true

# Blocs de dialogue optionnels
[[npcs.dialogue_blocks]]
distance_min = 0.0
distance_max = 150.0

[[npcs.dialogue_blocks.exchanges]]
speaker = "npc"
text = "Bienvenue dans ma boutique !"

[[npcs.dialogue_blocks.exchanges]]
speaker = "player"
text = "Merci !"
```

**Champs de `[[npcs]]`** :
- `id` (obligatoire) : Identifiant technique unique du PNJ (chaîne de caractères). Cet identifiant est utilisé pour référencer le PNJ dans les fichiers de déclencheurs d'événements (voir spécification 11). L'identifiant doit être unique au sein d'un même niveau.
- `name` (obligatoire) : Nom du PNJ affiché au-dessus de sa tête
- `x` (obligatoire) : Position horizontale dans l'espace du monde (en pixels)
- `y` (optionnel) : Position verticale d'apparition initiale (en pixels). Si défini, le PNJ commence à cette position Y, puis la gravité le fait tomber vers le sol en dessous (y plus grand dans le repère existant). Si non défini, le PNJ commence à y=0.0 (en haut de l'écran) puis tombe jusqu'au premier bloc de depth 2.
- `direction` (optionnel, défaut: `"right"`) : Orientation initiale du PNJ définie dans le fichier de configuration (`"right"` affiche le sprite tel quel, `"left"` affiche le sprite inversé horizontalement). Cette valeur peut être modifiée dynamiquement par la suite (par exemple lors de l'implémentation de mouvements ou de comportements d'IA)
- `sprite_sheet_path` (obligatoire) : Chemin vers le fichier sprite sheet (relatif à la racine du projet ou absolu)
- `sprite_width` (obligatoire) : Largeur d'un sprite individuel dans le sprite sheet (en pixels)
- `sprite_height` (obligatoire) : Hauteur d'un sprite individuel dans le sprite sheet (en pixels)
- `sprite_scale` (optionnel, défaut: 2.0) : Facteur d'échelle pour l'affichage du sprite (2.0 = 200%, double la taille d'affichage)
- `animations` (optionnel) : Section contenant les animations du PNJ
- `font_path` (optionnel) : Chemin vers un fichier de police personnalisé (utilise la police du joueur par défaut)
- `font_size` (optionnel, défaut: 36) : Taille de la police pour le nom (définie dans le repère de conception 1920x1080, convertie vers 1280x720 lors de l'initialisation)
- `name_color` (optionnel, défaut: [255, 255, 255]) : Couleur du nom (RGB)
- `name_outline_color` (optionnel, défaut: [0, 0, 0]) : Couleur du contour du nom (RGB)
- `name_offset_y` (optionnel, défaut: -4.0) : Décalage vertical du nom par rapport au haut du sprite (en pixels)

**Champs de `[npcs.animations.<nom>]`** :
- `row` (obligatoire) : Ligne dans le sprite sheet (0-indexed)
- `num_frames` (obligatoire) : Nombre de frames dans l'animation. **IMPORTANT** : Doit être strictement positif (>= 1). Une valeur de 0 provoquera une erreur de validation. Pour une animation statique (sans mouvement), utiliser `num_frames = 1`.
- `animation_speed` (obligatoire) : Vitesse d'animation en frames par seconde
- `loop` (optionnel, défaut: true) : Si l'animation se répète en boucle

**Note** : Si aucune animation n'est spécifiée, le PNJ affiche la première frame (frame 0) de la première ligne (row 0) du sprite sheet.

**Validations importantes pour les dimensions de sprite** :
- `sprite_width` et `sprite_height` doivent correspondre exactement aux dimensions réelles des sprites dans le sprite sheet.
- Le sprite sheet doit être divisible exactement par ces dimensions : `sprite_sheet_width % sprite_width == 0` et `sprite_sheet_height % sprite_height == 0`.
- Si le reste de la division n'est pas zéro, cela indique que les dimensions sont incorrectes et provoquera des erreurs d'affichage.
- Exemple : Pour un sprite sheet de 576x256 pixels, les dimensions valides peuvent être 48x64 (12 colonnes x 4 lignes), 64x64 (9 colonnes x 4 lignes), 72x64 (8 colonnes x 4 lignes), etc., mais pas 44x64 (reste de 4 pixels).

### Système de blocs de dialogue

Les PNJ peuvent avoir plusieurs blocs de dialogue définis dans le fichier de configuration TOML. Chaque bloc de dialogue définit une plage de position du joueur dans le monde (position minimale et maximale) et contient une série d'échanges conversationnels entre le PNJ et le joueur.

**Principe de fonctionnement** :
1. **Configuration** : Les blocs de dialogue sont définis dans le fichier de configuration TOML pour chaque PNJ
2. **Plage de position (OBLIGATOIRE)** : Chaque bloc **DOIT** définir une plage de position (`position_min` et `position_max`) en pixels horizontaux correspondant à la position du joueur dans le monde. Cette plage est le mécanisme principal de sélection du bloc de dialogue à déclencher.
3. **Fourniture de la position** : La position horizontale du joueur dans le monde est **fournie par le système** (via le système de gestion de l'avancement dans le niveau, voir spécification 11). Le NPC et le système de dialogue **ne calculent pas** la position eux-mêmes. Le système de déclenchement fournira la position au NPC lors de l'interaction via `LevelProgressTracker.get_current_x()`.
4. **Déclenchement du dialogue** : Une fonction `start_dialogue(npc: NPC, progress_tracker: LevelProgressTracker) -> Optional[DialogueState]` permet de démarrer un dialogue avec un PNJ. Cette fonction :
   - Obtient la position actuelle du joueur : `player_position = progress_tracker.get_current_x()`
   - Appelle `npc.get_dialogue_block_for_position(player_position)` pour obtenir le bloc de dialogue approprié
   - Si un bloc est trouvé, crée un `DialogueState` pour gérer l'affichage séquentiel des échanges
   - Retourne le `DialogueState` créé, ou `None` si aucun bloc ne correspond
5. **Affichage séquentiel des échanges** : Le bloc sélectionné contient une série d'échanges. Les échanges sont affichés **un par un** dans l'ordre défini :
   - Le premier échange est affiché immédiatement via une `SpeechBubble`
   - Chaque échange indique qui parle (`speaker`: "npc" ou "player") et le texte correspondant
   - La bulle est positionnée selon le personnage qui parle (NPC ou joueur)
6. **Navigation entre les échanges** : 
   - L'utilisateur doit cliquer sur la bulle **lorsque tout le texte est affiché** pour passer à l'échange suivant
   - Si le texte n'est pas complètement affiché, le clic accélère l'affichage (comportement standard de `SpeechBubble`)
   - Une fois le texte complètement affiché, un nouveau clic passe à l'échange suivant
   - **Contrainte importante** : Le passage à l'échange suivant est **bloqué** si un événement de type `sprite_move` est en cours de déplacement (voir spécification 8 et 11). Dans ce cas, le clic est ignoré et l'utilisateur doit attendre la fin du mouvement du sprite avant de pouvoir continuer le dialogue.
   - **Contrainte importante** : Le passage à l'échange suivant est également **bloqué** si un événement de type `screen_fade` est en cours (voir spécification 11). Dans ce cas, le clic est ignoré et l'utilisateur doit attendre la fin du fondu avant de pouvoir continuer le dialogue. **Cependant**, si l'événement `screen_fade` a été déclenché depuis un dialogue, le passage à l'échange suivant se fait automatiquement une fois que le fondu est terminé, sans nécessiter de clic de l'utilisateur.
   - Quand il n'y a plus d'échanges, le dialogue se termine automatiquement
7. **Bulles de dialogue** : Chaque échange utilise le système `SpeechBubble` (voir spécification 8) pour afficher le texte avec animation progressive

**Position fournie par le système et sélection du bloc** :
- **Source de la position** : La position horizontale du joueur dans le monde est obtenue via le système de gestion de l'avancement dans le niveau (spécification 11) via `LevelProgressTracker.get_current_x()`. Le NPC reçoit cette position en paramètre et ne la calcule pas lui-même.
- **Format de la position** : La position est fournie en pixels horizontaux (position X du joueur dans l'espace du monde, obtenue via `progress_tracker.get_current_x()`).
- **Condition de sélection** : Un bloc de dialogue est sélectionné si et seulement si : `position_min <= player_position <= position_max` (où `player_position` est la valeur fournie par le système de progression)
- **Ordre de sélection** : Si plusieurs blocs correspondent à la position, le premier bloc défini dans le fichier TOML (dans l'ordre de déclaration) est sélectionné
- **Bloc unique par position** : Il est recommandé de définir des plages non chevauchantes pour garantir qu'un seul bloc soit sélectionné à la fois

**Gestion des plages** :
- Les plages de position peuvent se chevaucher. Dans ce cas, le premier bloc dont la plage correspond à la position sera sélectionné (ordre de définition dans le fichier TOML)
- Il est recommandé de définir des plages non chevauchantes pour un comportement prévisible

**Structure d'un bloc de dialogue** :
- Un bloc de dialogue contient **au moins un échange** (pas de limite supérieure)
- Chaque échange indique qui parle (`speaker`: "npc" ou "player") et le texte correspondant
- Les échanges sont affichés séquentiellement dans l'ordre défini dans la configuration
- **Nombre d'échanges** : Un bloc peut contenir **autant d'échanges que nécessaire** (2, 3, 4, 10, etc.). Il n'y a pas de limite supérieure au nombre d'échanges dans un bloc
- La liste d'échanges peut contenir plusieurs répliques consécutives du même personnage (par exemple, le NPC peut parler plusieurs fois de suite, puis le joueur répond)
- La navigation entre les échanges sera gérée par l'utilisateur (clic pour passer à l'échange suivant)

**Format TOML des blocs de dialogue** :

```toml
# Bloc de dialogue 1 : position du joueur entre 0 et 3000 pixels
[[npcs.dialogue_blocks]]
position_min = 0.0
position_max = 3000.0
font_size = 32  # Optionnel : taille par défaut pour tous les échanges du bloc
text_speed = 30.0  # Optionnel : vitesse par défaut pour tous les échanges du bloc

# Premier échange du bloc : le NPC parle
[[npcs.dialogue_blocks.exchanges]]
speaker = "npc"
text = "Bonjour ! Je suis ChatGPT.\nMon apparition dans ce monde marque une nouvelle ère."

# Deuxième échange du bloc : le joueur répond
[[npcs.dialogue_blocks.exchanges]]
speaker = "player"
text = "Enchanté de vous rencontrer !"

# Troisième échange du bloc : le NPC parle à nouveau et déclenche un événement
[[npcs.dialogue_blocks.exchanges]]
speaker = "npc"
text = "Lorsque j'ai été créé, personne ne s'attendait à l'impact que j'aurais."
trigger_events = ["robot_move_01"]  # Optionnel : événements à déclencher lorsque cet échange est affiché
add_items = {document_etoile = 1}  # Optionnel : ajouter un objet à l'inventaire du joueur avec animation

# Quatrième échange du bloc : le joueur répond
[[npcs.dialogue_blocks.exchanges]]
speaker = "player"
text = "C'est fascinant ! Pouvez-vous m'en dire plus ?"

# Cinquième échange du bloc : le NPC continue et déclenche un autre événement
[[npcs.dialogue_blocks.exchanges]]
speaker = "npc"
text = "Je peux vous en dire beaucoup plus si vous le souhaitez."
trigger_events = ["hide_obstacle_01"]  # Optionnel : événements à déclencher lorsque cet échange est affiché
remove_items = {document_etoile = 1}  # Optionnel : retirer un objet de l'inventaire du joueur avec animation

# Sixième échange du bloc : le NPC annonce un level up du personnage principal
[[npcs.dialogue_blocks.exchanges]]
speaker = "npc"
text = "Félicitations ! Vous avez gagné un niveau !"
trigger_events = ["player_level_up"]  # Déclenche l'événement de level up (voir spécification 11)
# L'affichage "level up (press u)" apparaîtra automatiquement au-dessus du nom du personnage principal
# Le joueur devra appuyer sur la touche 'U' pour confirmer le level up (voir spécification 2)
# Note : L'augmentation de niveau est toujours de +1 (le niveau du personnage augmente de 1, sans dépasser MAX_PLAYER_LEVEL)

# Note : Ce bloc contient 6 échanges, mais on peut en ajouter autant que nécessaire (7, 8, 10, etc.)
# Chaque échange peut déclencher ses propres événements au moment où il est affiché

# Bloc de dialogue 2 : position du joueur entre 3000 et 6000 pixels
[[npcs.dialogue_blocks]]
position_min = 3000.0
position_max = 6000.0

# Premier échange : le NPC parle
[[npcs.dialogue_blocks.exchanges]]
speaker = "npc"
text = "Je représente l'évolution de la conversation entre l'homme et la machine."

# Deuxième échange : le joueur répond
[[npcs.dialogue_blocks.exchanges]]
speaker = "player"
text = "C'est impressionnant !"

# Bloc de dialogue 3 : type "quête" - affiche un "!" au-dessus du PNJ
[[npcs.dialogue_blocks]]
position_min = 6000.0
position_max = 9000.0
dialogue_type = "quête"  # Type "quête" : affiche un "!" au lieu de "T pour parler"

# Premier échange : le NPC propose une quête
[[npcs.dialogue_blocks.exchanges]]
speaker = "npc"
text = "J'ai une mission importante pour vous !"

# Deuxième échange : le joueur répond
[[npcs.dialogue_blocks.exchanges]]
speaker = "player"
text = "Je suis prêt à vous aider !"

# Bloc de dialogue 4 : type "discution" - affiche "T pour ecouter et donner son avis"
[[npcs.dialogue_blocks]]
position_min = 9000.0
position_max = 12000.0
dialogue_type = "discution"  # Type "discution" : affiche "T pour ecouter et donner son avis"

# Premier échange : le NPC commence une discussion
[[npcs.dialogue_blocks.exchanges]]
speaker = "npc"
text = "Qu'en pensez-vous de cette situation ?"

# Bloc de dialogue 5 : type "regarder" - affiche "T pour regarder ce que c'est"
[[npcs.dialogue_blocks]]
position_min = 12000.0
position_max = 15000.0
dialogue_type = "regarder"  # Type "regarder" : affiche "T pour regarder ce que c'est"

# Premier échange : le joueur examine quelque chose
[[npcs.dialogue_blocks.exchanges]]
speaker = "player"
text = "Qu'est-ce que c'est que ça ?"
image_path = "objet_mystere.png"

# Bloc de dialogue 6 : type "enseigner" - affiche "T pour former"
[[npcs.dialogue_blocks]]
position_min = 15000.0
position_max = 18000.0
dialogue_type = "enseigner"  # Type "enseigner" : affiche "T pour former"

# Premier échange : le NPC enseigne quelque chose
[[npcs.dialogue_blocks.exchanges]]
speaker = "npc"
text = "Laissez-moi vous expliquer comment cela fonctionne..."

# Deuxième échange : le joueur donne son avis
[[npcs.dialogue_blocks.exchanges]]
speaker = "player"

# Bloc de dialogue 7 : type "reflexion" - affiche "T pour reflechir"
[[npcs.dialogue_blocks]]
position_min = 18000.0
position_max = 21000.0
dialogue_type = "reflexion"  # Type "reflexion" : affiche "T pour reflechir"

# Premier échange : le joueur réfléchit sur quelque chose
[[npcs.dialogue_blocks.exchanges]]
speaker = "player"
text = "Je pense que c'est une bonne idée !"

# Bloc de dialogue 5 : exemple avec animation du joueur et déplacement de position
[[npcs.dialogue_blocks]]
position_min = 12000.0
position_max = 15000.0

# Premier échange : le NPC parle
[[npcs.dialogue_blocks.exchanges]]
speaker = "npc"
text = "Venez ici, je dois vous montrer quelque chose d'important !"

# Deuxième échange : le joueur se déplace et réagit avec une animation
[[npcs.dialogue_blocks.exchanges]]
speaker = "player"
text = "D'accord, je viens !"
# Animation du joueur avec déplacement de position
[npcs.dialogue_blocks.exchanges.player_animation]
sprite_sheet_path = "walk.png"
row = 3  # Ligne pour la marche vers la droite
num_frames = 8
animation_speed = 10.0
animation_type = "loop"
set_x_position = 5000.0  # Déplace le joueur à la position X = 5000 pixels (repère de conception 1920x1080)
# La caméra suivra automatiquement le joueur pour maintenir la visibilité
```

**Champs de `[[npcs.dialogue_blocks]]`** :
- `position_min` (obligatoire) : Position minimale en pixels (position horizontale du joueur dans le monde) - inclus. Doit être >= 0. **Ce champ est utilisé pour déterminer quel bloc de dialogue sera lancé** : le système vérifie si la position du joueur fournie (par le système de progression via `LevelProgressTracker.get_current_x()`, voir spécification 11) est dans la plage `[position_min, position_max]` pour sélectionner le bloc approprié.
- `position_max` (obligatoire) : Position maximale en pixels (position horizontale du joueur dans le monde) - inclus. Doit être >= `position_min`. **Ce champ est utilisé pour déterminer quel bloc de dialogue sera lancé** : le système vérifie si la position du joueur fournie (par le système de progression via `LevelProgressTracker.get_current_x()`, voir spécification 11) est dans la plage `[position_min, position_max]` pour sélectionner le bloc approprié.
- `exchanges` (obligatoire) : Liste des échanges du bloc (au moins un échange requis, **pas de limite supérieure**). Ces échanges seront affichés lorsque le bloc est sélectionné selon la plage de position du joueur. Un bloc peut contenir 2, 3, 4, 10 échanges ou plus selon les besoins de la conversation.
- `dialogue_type` (optionnel, défaut: `"normal"`) : Type de dialogue (`"normal"`, `"quête"`, `"discution"`, `"ecoute"`, `"regarder"`, `"enseigner"` ou `"reflexion"`). Si le type est `"quête"`, l'indicateur d'interaction affiché au-dessus du PNJ sera un "!" au lieu de "T pour parler". Si le type est `"discution"`, l'indicateur affiche "T pour ecouter et donner son avis". Si le type est `"ecoute"`, l'indicateur affiche "T pour écouter". Si le type est `"regarder"`, l'indicateur affiche "T pour regarder ce que c'est". Si le type est `"enseigner"`, l'indicateur affiche "T pour former". Si le type est `"reflexion"`, l'indicateur affiche "T pour reflechir" (voir spécification 2 pour plus de détails sur l'indicateur d'interaction).
- `font_size` (optionnel, défaut: 32) : Taille de la police pour les dialogues du bloc (définie dans le repère de conception 1920x1080, convertie vers 1280x720 lors de l'initialisation, peut être surchargée par chaque échange)
- `text_speed` (optionnel, défaut: 30.0) : Vitesse d'affichage du texte en caractères par seconde pour le bloc (peut être surchargée par chaque échange)

**Champs de `[[npcs.dialogue_blocks.exchanges]]`** :
- `speaker` (obligatoire) : Personnage qui parle dans cet échange (`"npc"` ou `"player"`)
- `text` (obligatoire) : Texte de l'échange (peut contenir des `\n` pour les retours à la ligne, peut être vide `""` si une image est présente)
- `image_path` (optionnel) : Chemin vers l'image à afficher dans la bulle (relatif au répertoire `image` du projet, par exemple `"dialogue_image.png"`). Les images de dialogue doivent être placées dans le répertoire `image`. L'image est affichée en entier dans la bulle.
- `font_size` (optionnel) : Taille de la police pour cet échange (surcharge la valeur du bloc si spécifiée)
- `text_speed` (optionnel) : Vitesse d'affichage du texte pour cet échange (surcharge la valeur du bloc si spécifiée)
- `trigger_events` (optionnel) : Liste des identifiants d'événements à déclencher lorsque cet échange est affiché. Les identifiants doivent correspondre aux `identifier` des événements définis dans le fichier `.event` du niveau (voir spécification 11). Les événements sont déclenchés lors de l'affichage de l'échange (dans `DialogueState._create_bubble_for_exchange`), avant que la bulle ne soit créée. Si un événement n'existe pas ou a déjà été déclenché (et n'est pas marqué comme `repeatable`), il est ignoré silencieusement. Pour permettre à un événement d'être déclenché plusieurs fois lors de conversations répétées, définir `repeatable = true` dans le fichier .event (voir spécification 11).
- `add_items` (optionnel) : Dictionnaire des objets à ajouter à l'inventaire du joueur. Format : `{item_id = quantity}`. Les objets sont ajoutés lors de l'affichage de l'échange, avec animation d'apparition progressive (voir spécification 13). Les objets doivent être définis dans `inventory_items.toml`. Exemple : `add_items = {document_etoile = 1, loupe_magique = 2}`
- `remove_items` (optionnel) : Dictionnaire des objets à retirer de l'inventaire du joueur. Format : `{item_id = quantity}`. Les objets sont retirés lors de l'affichage de l'échange, avec animation de saut vers l'arrière puis disparition (voir spécification 13). Si la quantité disponible est insuffisante, l'opération échoue silencieusement (log un avertissement). Exemple : `remove_items = {document_etoile = 1}`
- `player_animation` (optionnel) : Configuration d'une animation du personnage principal pendant cet échange. Format : `[npcs.dialogue_blocks.exchanges.player_animation]` avec les champs suivants :
  - `sprite_sheet_path` (obligatoire) : Chemin vers la planche de sprite à utiliser (relatif au répertoire du niveau du personnage, généralement dans `sprite/personnage/{niveau}/`)
  - `row` (obligatoire) : Ligne du sprite sheet à utiliser pour l'animation (0-indexed)
  - `num_frames` (obligatoire) : Nombre de frames dans l'animation
  - `animation_speed` (obligatoire) : Vitesse d'animation en frames par seconde (FPS)
  - `animation_type` (optionnel, défaut: `"simple"`) : Type d'animation (`"simple"`, `"loop"` ou `"pingpong"`)
  - `start_sprite` (optionnel, défaut: 0) : Premier sprite à afficher dans la séquence d'animation (0-indexed)
  - `offset_y` (optionnel, défaut: 0.0) : Offset vertical à appliquer à l'animation (en pixels)
  - `set_x_position` (optionnel) : Position X à définir pour le personnage principal (en pixels dans le repère de conception 1920x1080). Si présent, déplace le personnage principal à cette position lors de l'affichage de l'échange. La caméra est automatiquement déplacée de la même façon pour maintenir la visibilité du sprite (la caméra suit le personnage selon la formule `camera_x = player.x - render_width / 2`). La valeur est convertie automatiquement du repère de conception vers le repère de rendu interne (1280x720) lors de l'application. **IMPORTANT** : Le déplacement du personnage et de la caméra se fait de manière synchrone pour éviter les problèmes de visibilité de sprite.

**Gestion du déplacement du personnage principal via `set_x_position`** :

Lorsqu'un échange contient une configuration `player_animation` avec le champ `set_x_position` défini, le personnage principal est déplacé à la position X spécifiée lors de l'affichage de l'échange :

1. **Conversion de repère** : La valeur `set_x_position` est fournie dans le repère de conception (1920x1080) et est automatiquement convertie vers le repère de rendu interne en utilisant `compute_design_scale()` du module `rendering.config`. **IMPORTANT** : Ne jamais hardcoder les valeurs de résolution dans cette conversion. Utiliser toujours `get_render_size()` et `compute_design_scale()` pour garantir la compatibilité avec toute résolution de rendu.

2. **Déplacement du personnage** : Le personnage principal est déplacé à la nouvelle position X (dans le repère de rendu) : `player.x = set_x_position * scale_x`.

3. **Déplacement de la caméra** : La caméra est automatiquement ajustée pour suivre le personnage selon la formule standard : `camera_x = player.x - render_width / 2`. Cela garantit que le personnage reste visible à l'écran et évite les problèmes de visibilité de sprite.

4. **Moment du déplacement** : Le déplacement se produit lors de l'affichage de l'échange (dans `DialogueState._create_bubble_for_exchange`), au même moment où l'animation du joueur est déclenchée.

5. **Synchronisation** : Le déplacement du personnage et de la caméra se fait de manière synchrone dans la même frame pour garantir qu'il n'y a pas de décalage visuel.

6. **Persistence** : La nouvelle position du personnage persiste après la fin de l'échange et du dialogue, sauf si un autre mécanisme (comme un événement de déplacement) modifie la position.

7. **Blocage du mouvement** : Pendant que l'échange avec `set_x_position` est affiché, le personnage principal est bloqué à cette position et les actions de déplacement du joueur sont désactivées. Le joueur ne peut pas se déplacer tant que la bulle de dialogue n'est pas passée. Voir la spécification 8 pour plus de détails sur cette contrainte.

**Intégration avec le système de bulles de dialogue** :
- Les dialogues utilisent le système `SpeechBubble` existant (voir spécification 8)
- Pour chaque échange, une bulle est créée pour le personnage qui parle (NPC ou joueur) selon le champ `speaker`
- Les bulles suivent automatiquement leur personnage respectif et s'adaptent à la caméra
- **Support des images** : Si un échange contient un `image_path`, celui-ci est passé à `SpeechBubble` lors de la création de la bulle. Le `assets_root` doit être fourni pour résoudre les chemins relatifs (généralement `Path("image")` pour les images de dialogue, car elles doivent être placées dans le répertoire `image` du projet)
- **Affichage séquentiel** : Un seul échange est affiché à la fois. L'échange suivant n'est affiché qu'après validation de l'échange actuel
- **Gestion des événements de clic** :
  - Le clic peut être effectué n'importe où sur l'écran, pas seulement sur la bulle
  - Si le texte n'est pas complètement affiché : le clic accélère l'affichage (affiche immédiatement tout le texte restant)
  - Si le texte est complètement affiché : le clic passe à l'échange suivant **uniquement si aucun événement `sprite_move` n'est en cours de déplacement ET si aucun événement `screen_fade` n'est en cours** (voir spécification 8 et 11 pour plus de détails)
  - Si un `sprite_move` est en cours : le clic est ignoré et l'utilisateur ne peut pas passer à l'échange suivant, même si le texte est complet
  - Si un `screen_fade` est en cours : le clic est ignoré et l'utilisateur ne peut pas passer à l'échange suivant, même si le texte est complet. Le passage à l'échange suivant se fera automatiquement une fois que le fondu est terminé (voir ci-dessous)
  - Si c'est le dernier échange et que le texte est complet : le clic termine le dialogue (sous réserve qu'aucun `sprite_move` ni `screen_fade` ne soit en cours)
- **Intégration avec les événements `screen_fade`** :
  - **Déclenchement depuis un dialogue** : Lorsqu'un événement `screen_fade` est déclenché depuis un dialogue (via `trigger_events` dans un échange), le système de dialogue doit automatiquement passer à l'échange suivant une fois que le fondu est terminé
  - **Blocage du passage manuel** : Tant qu'un fondu au noir est en cours (vérifié via `EventTriggerSystem.has_active_screen_fade()`), le passage manuel à l'échange suivant (clic) est bloqué. Le clic est ignoré et l'utilisateur doit attendre la fin du fondu avant de pouvoir continuer le dialogue
  - **Passage automatique** : Lorsque le fondu se termine (phase `none`), si l'événement a été déclenché depuis un dialogue, le système de dialogue doit automatiquement passer à l'échange suivant. Le système de dialogue doit surveiller la fin du fondu (via `has_active_screen_fade()`) dans `DialogueState.update()` et appeler `_next_exchange()` automatiquement lorsque le fondu se termine
  - **Méthode de vérification** : Le système de dialogue doit interroger `EventTriggerSystem.has_active_screen_fade()` pour déterminer si un fondu est en cours. Cette vérification doit être effectuée :
    - Dans `DialogueState.handle_event()` avant d'appeler `_next_exchange()` pour bloquer le passage manuel
    - Dans `DialogueState.update()` pour détecter la fin du fondu et déclencher le passage automatique
  - **Comportement** : Cette contrainte garantit que le fondu se termine complètement avant de passer à l'échange suivant, améliorant la cohérence narrative et visuelle du jeu. Le fondu au noir peut ainsi être utilisé pour créer des transitions de scène pendant les dialogues, avec un passage automatique à l'échange suivant une fois la transition terminée
- **Navigation séquentielle** : Les échanges sont affichés dans l'ordre défini dans la configuration. L'utilisateur doit valider chaque échange (clic) avant de passer au suivant
- **Flexibilité des échanges** : La liste d'échanges peut contenir plusieurs répliques consécutives du même personnage, permettant des conversations plus naturelles (par exemple, le NPC peut faire plusieurs remarques avant que le joueur ne réponde)
- **Fin du dialogue** : Quand tous les échanges ont été affichés et validés, le dialogue se termine automatiquement (`DialogueState.is_complete()` retourne True)
- **Gestion des limites d'écran (CRITIQUE)** : Les bulles de dialogue restent attachées au personnage qui parle. **Aucun repositionnement automatique** ne doit être appliqué (ni horizontal, ni vertical), même si la bulle sort partiellement de l'écran. **IMPORTANT** : Cela évite qu'une bulle de PNJ \"s'accroche\" au joueur quand on se déplace. Voir la spécification 8 pour les règles détaillées.
- **Mise à jour du dialogue indépendante (CRITIQUE)** : Le dialogue doit être mis à jour **indépendamment** de l'interface des stats. Si la mise à jour du dialogue est à l'intérieur du bloc `if not stats_display.is_visible:`, le dialogue ne sera pas mis à jour quand l'interface des stats est affichée, ce qui peut le rendre invisible. La mise à jour du dialogue doit être déplacée **en dehors** de ce bloc conditionnel.

**Déclenchement du dialogue** :
- Le système de déclenchement des dialogues est géré par le système d'interaction avec les PNJ (voir spécification 2)
- La touche **'T'** permet de lancer un dialogue avec le PNJ le plus proche. Pour qu'un dialogue puisse être déclenché, **deux conditions doivent être remplies** :
  1. **Distance horizontale (X)** : Le PNJ doit être à moins de 200 pixels horizontalement du joueur (`abs(player.x - npc.x) <= INTERACTION_DISTANCE`)
  2. **Distance verticale (Y)** : Le joueur et le PNJ doivent être à peu près à la même hauteur. La différence de position Y entre le joueur et le PNJ ne doit pas dépasser un seuil configurable (par défaut, environ 50-100 pixels). Cette vérification garantit que le dialogue ne peut être déclenché que si le joueur et le PNJ sont sur le même niveau ou des niveaux très proches (par exemple, sur la même plateforme ou des plateformes adjacentes). La vérification est effectuée en calculant `abs(player.y - npc.y) <= INTERACTION_Y_THRESHOLD` où `INTERACTION_Y_THRESHOLD` est une constante configurable (par défaut, 100 pixels).
- Le dialogue ne peut être déclenché que s'il n'y a pas déjà un dialogue en cours (`current_dialogue is None`)
- **Indication visuelle** : Une indication visuelle est affichée au-dessus du PNJ lorsqu'il est à portée d'interaction. **IMPORTANT** : L'indication n'est affichée que si **toutes** les conditions suivantes sont remplies :
  1. Le PNJ est à moins de 200 pixels horizontalement du joueur (`abs(player.x - npc.x) <= INTERACTION_DISTANCE`)
  2. Le joueur et le PNJ sont à peu près à la même hauteur (`abs(player.y - npc.y) <= INTERACTION_Y_THRESHOLD`)
  3. Le PNJ a un bloc de dialogue disponible à la position actuelle du joueur (c'est-à-dire qu'il existe un bloc de dialogue dont la plage de position correspond à la position actuelle du joueur). Si aucun bloc de dialogue ne correspond à la position actuelle, l'indication n'est pas affichée, même si le PNJ a d'autres blocs de dialogue configurés pour d'autres positions.
  
  Le type d'indicateur dépend du type de dialogue du bloc correspondant à la position actuelle du joueur :
  - **Type "normal"** (par défaut) : Affiche "T pour parler" avec une taille de police doublée (28-32 pixels) et une couleur distincte (jaune ou cyan) pour se différencier clairement des noms des PNJ
  - **Type "quête"** : Affiche un "!" (point d'exclamation) au-dessus du PNJ, similaire aux MMO RPG, pour indiquer qu'une quête est disponible. Le "!" est **3 fois plus gros** que le texte "T pour parler" (par exemple, si "T pour parler" utilise une police de 28 pixels, le "!" utilise une police de 84 pixels) et utilise une couleur distincte (jaune ou cyan) pour attirer l'attention. Le contour est également proportionnellement plus épais (environ 6 pixels) pour maintenir une bonne lisibilité
  - **Type "discution"** : Affiche "T pour ecouter et donner son avis" avec une taille de police doublée (28-32 pixels) et une couleur distincte (jaune ou cyan) pour se différencier clairement des noms des PNJ. Ce type indique que le dialogue est une discussion où le joueur peut écouter et donner son avis
  - **Type "ecoute"** : Affiche "T pour écouter" avec une taille de police doublée (28-32 pixels) et une couleur distincte (jaune ou cyan) pour se différencier clairement des noms des PNJ. Ce type indique que le dialogue est une écoute où le joueur peut simplement écouter sans donner son avis
  - **Type "regarder"** : Affiche "T pour regarder ce que c'est" avec une taille de police doublée (28-32 pixels) et une couleur distincte (jaune ou cyan) pour se différencier clairement des noms des PNJ. Ce type indique que le dialogue permet au joueur d'examiner quelque chose
  - **Type "enseigner"** : Affiche "T pour former" avec une taille de police doublée (28-32 pixels) et une couleur distincte (jaune ou cyan) pour se différencier clairement des noms des PNJ. Ce type indique que le dialogue est une formation où le joueur peut apprendre quelque chose
  - **Type "reflexion"** : Affiche "T pour reflechir" avec une taille de police doublée (28-32 pixels) et une couleur distincte (jaune ou cyan) pour se différencier clairement des noms des PNJ. Ce type indique que le dialogue permet au joueur de réfléchir sur quelque chose
  - Le type de dialogue est déterminé en appelant `npc.get_dialogue_type_for_position(player_position)` avec la position actuelle du joueur. Si cette méthode retourne `None` (aucun bloc de dialogue disponible à cette position), l'indication n'est pas affichée (voir spécification 2 pour plus de détails sur l'indicateur d'interaction)

**Optimisations de performance pour l'affichage des indicateurs d'interaction** :
- **Cache de polices** : Les polices utilisées pour afficher les indicateurs d'interaction sont mises en cache pour éviter de les recréer à chaque frame. Un dictionnaire `font_cache: Dict[int, pygame.font.Font]` est utilisé pour stocker les polices par taille. Si une police de la taille requise existe déjà dans le cache, elle est réutilisée au lieu d'être recréée.
- **Gestion d'erreur robuste** : Toutes les opérations critiques (récupération du type de dialogue, création de polices, rendu de surfaces, blit) sont enveloppées dans des blocs try/except pour éviter que le jeu ne se bloque en cas d'erreur. En cas d'erreur, l'indicateur n'est simplement pas affiché plutôt que de bloquer le jeu.
- **Éviter les appels redondants** : La fonction `find_nearest_interactable_npc()` vérifie déjà qu'un bloc de dialogue est disponible à la position du joueur. Il n'est donc pas nécessaire de vérifier à nouveau `get_dialogue_block_for_position()` avant d'appeler `draw_interaction_indicator()`. Cette optimisation évite un appel redondant à chaque frame.
- **Cache de surfaces** : Les surfaces d'indicateurs pré-rendues sont mises en cache dans `indicator_cache` pour éviter de recréer les surfaces à chaque frame. Le cache utilise une clé basée sur le type de dialogue et la taille de police.
- **Initialisation des variables** : Toutes les variables locales utilisées dans des blocs conditionnels doivent être initialisées au début de la fonction pour éviter les erreurs `UnboundLocalError`. Par exemple, `display_font` doit être initialisé à `None` au début de `draw_interaction_indicator()` avant d'être utilisé dans les blocs conditionnels.

- **Note** : Le code de test qui cherchait spécifiquement le PNJ nommé "Robot" doit être supprimé et remplacé par le système de détection de proximité décrit dans la spécification 2

### Gravité et positionnement

Les PNJ sont soumis à la gravité en permanence, comme le joueur :

1. **Position initiale** : 
   - Si `y` est défini dans la configuration : le PNJ est positionné à `(x, y)` où `y` est la position verticale d'apparition initiale spécifiée
   - Si `y` n'est pas défini : le PNJ est positionné à `(x, 0)` (en haut de l'écran)
2. **Application de la gravité** : Le moteur de gravité fait tomber le PNJ vers le bas (vers les y plus grands dans le repère existant)
3. **Détection de collision** : Le système de collisions détecte quand le PNJ entre en collision avec un bloc de depth 2
4. **Arrêt** : Le PNJ s'arrête sur le premier bloc solide rencontré
5. **Gravité permanente** : La gravité continue de s'appliquer à chaque frame, même après le positionnement initial. Cela garantit que :
   - Le PNJ reste au sol (la gravité maintient le contact avec le sol via les collisions)
   - Si le PNJ se déplace horizontalement et qu'il n'y a plus de sol sous lui, il tombe
   - Les déplacements déclenchés par événements sont soumis à la gravité (le PNJ peut tomber s'il se déplace au-dessus d'un vide)

**Implémentation** :
- Utiliser le même système de gravité que le joueur (800 pixels/s² par défaut)
- Utiliser le même système de collisions pour détecter les blocs de depth 2
- Le PNJ a une hitbox similaire au joueur (réduite pour éviter les collisions prématurées)
- **Gravité permanente** : La gravité s'applique à chaque frame dans la méthode `update()`, pas seulement lors du positionnement initial. La méthode `_apply_gravity()` doit :
  1. Appliquer la gravité en augmentant `velocity_y` si le PNJ n'est pas au sol
  2. Calculer le déplacement vertical prévu (`dy = velocity_y * dt`)
  3. Résoudre les collisions verticales en utilisant le système de collisions
  4. Mettre à jour la position Y du PNJ et l'état `is_on_ground`
- **Positionnement initial** : Pour le positionnement initial :
  - Si `y` est défini dans la configuration : le PNJ est créé avec `y = config.y` (position d'apparition initiale spécifiée), puis la gravité le fait tomber vers le sol en dessous (y plus grand). Le système utilise **uniquement** la méthode de chute progressive pour simuler la gravité jusqu'à ce que le PNJ rencontre un bloc. Aucune recherche de bloc immédiate n'est effectuée, garantissant que le PNJ tombe depuis sa position Y initiale jusqu'au premier bloc rencontré (le sol le plus bas), et non sur une plateforme intermédiaire.
  - Si `y` n'est pas défini : le PNJ est créé avec `y=0.0` (en haut de l'écran), puis le système doit :
    1. Calculer une caméra initiale à partir de la position X du PNJ (`initial_camera_x = self.x - 640.0`)
    2. Récupérer tous les rectangles de collision dans une large zone autour du PNJ
    3. Chercher directement tous les blocs à la position X du PNJ (ne pas utiliser le rectangle de collision actuel car `y=0.0` est trop haut)
    4. Trouver le bloc le plus haut (y le plus petit) à la position X du PNJ
    5. Positionner le PNJ de manière à ce que le bas de son rectangle de collision soit au-dessus du haut du bloc : `self.y = min_y - self.sprite_height / 2 - self.collision_offset_y`
  - Si aucun bloc n'est trouvé avec cette méthode (cas où `y` n'est pas défini), utiliser la méthode de chute progressive comme fallback
- **Intégration avec les déplacements** : Pendant les déplacements déclenchés par événements, la gravité continue de s'appliquer. La méthode `update()` doit :
  1. Gérer le déplacement horizontal vers `target_x`
  2. **Appeler `_apply_gravity()` à chaque frame** pour appliquer la gravité et résoudre les collisions verticales
  3. Cela garantit que le PNJ reste au sol pendant le déplacement ou tombe s'il se déplace au-dessus d'un vide

### Système de cache pour les PNJ (voir spécification 17)

Le système de PNJ utilise une architecture de cache à trois niveaux pour optimiser les performances :

**1. Cache global pour les sprite sheets `_global_npc_sprite_sheet_cache`** (défini dans `assets/preloader.py`) :
- **Type** : `Dict[str, pygame.Surface]`
- **Clé** : chemin absolu du sprite sheet (str) après résolution avec `.resolve()`
- **Valeur** : Surface pygame du sprite sheet complet chargé avec `convert_alpha()`
- **Portée** : Partagé entre tous les PNJ utilisant le même sprite sheet
- **Rempli par** : 
  - `AssetPreloader._preload_npc_sprites()` au démarrage (préchargement automatique)
  - `NPC.__init__()` en fallback si le sprite sheet n'est pas préchargé
- **Utilisé par** : `NPC.__init__()` et `NPC.change_sprite_sheet()` vérifient d'abord ce cache avant de charger depuis le disque

**2. Caches globaux pour les sprites redimensionnés** (définis dans `assets/preloader.py`) :
- `_global_npc_scaled_sprite_cache: Dict[tuple[str, int, int, int, int], pygame.Surface]` : Sprites redimensionnés
  - **Clé** : `(sprite_path_key, row, col, display_width, display_height)`
    - `sprite_path_key` : chemin absolu du sprite sheet (str)
    - `row` : ligne du sprite dans le sprite sheet (0-based)
    - `col` : colonne du sprite dans le sprite sheet (0-based)
    - `display_width` : largeur d'affichage après scaling (int)
    - `display_height` : hauteur d'affichage après scaling (int)
  - **Valeur** : Surface pygame du sprite extrait et redimensionné
- `_global_npc_scaled_flipped_sprite_cache: Dict[tuple[str, int, int, int, int], pygame.Surface]` : Sprites redimensionnés et retournés horizontalement
  - **Clé** : même format que `_global_npc_scaled_sprite_cache`
  - **Valeur** : Surface pygame du sprite extrait, redimensionné et retourné
- **Portée** : Partagé entre tous les PNJ utilisant le même sprite sheet avec les mêmes dimensions d'affichage
- **Rempli par** : `AssetPreloader._preload_npc_sprites()` au démarrage (précharge tous les sprites utilisés par les animations avec scaling appliqué)
- **Utilisé par** : `NPC._get_sprite_at()` et `NPC._get_flipped_sprite()` vérifient d'abord ces caches avant de faire le scaling à la volée

**3. Caches locaux pour les frames** (spécifiques à chaque instance de NPC, utilisés en fallback) :
- `_frame_cache: Dict[Tuple[int, int], pygame.Surface]` : Frames extraites non redimensionnées (clé: `(row, col)`)
- `_flipped_frame_cache: Dict[Tuple[int, int], pygame.Surface]` : Frames retournées horizontalement
- `_scaled_frame_cache: Dict[Tuple[int, int, int, int], pygame.Surface]` : Frames redimensionnées (clé: `(row, col, width, height)`)
- `_scaled_flipped_frame_cache: Dict[Tuple[int, int, int, int], pygame.Surface]` : Frames redimensionnées et retournées

**Fonctionnement** :
1. Au démarrage, `AssetPreloader` précharge tous les sprite sheets des PNJ dans `_global_npc_sprite_sheet_cache`
2. Au démarrage, `AssetPreloader` précharge également tous les sprites redimensionnés utilisés par les animations dans `_global_npc_scaled_sprite_cache` et `_global_npc_scaled_flipped_sprite_cache`
3. Lors de la création d'un NPC, `NPC.__init__()` vérifie d'abord le cache global des sprite sheets
4. Si le sprite sheet est en cache, il est réutilisé directement (pas de rechargement depuis le disque)
5. Lors de l'affichage d'un sprite, `NPC._get_sprite_at()` et `NPC._get_flipped_sprite()` vérifient d'abord les caches globaux des sprites redimensionnés
6. Si le sprite redimensionné est en cache global, il est réutilisé directement (pas de scaling à la volée)
7. Si le sprite n'est pas dans le cache global, il est extrait et redimensionné à la demande, puis mis en cache localement
8. Cette architecture permet de partager les sprite sheets lourds et les sprites redimensionnés tout en gardant les frames spécifiques à chaque NPC en fallback

**Optimisation FPS** : Les sprites redimensionnés sont préchargés au démarrage pour éviter le scaling à la volée lors du premier affichage. Les frames extraites sont mises en cache pour éviter de recréer des surfaces à chaque frame. Les surfaces mises en cache sont converties via `convert_alpha()` pour conserver le format optimisé tout en exploitant l'accélération GPU Metal.

### Redimensionnement des sprites

Les sprites des PNJ sont affichés à **200% de leur taille originale** (facteur d'échelle de 2.0 par défaut) :
- **Taille d'affichage** : Les sprites sont redimensionnés lors de l'extraction/affichage
  - Sprites 44x64 pixels dans le sprite sheet → affichage à 88x128 pixels
  - Sprites 64x64 pixels dans le sprite sheet → affichage à 128x128 pixels
  - Le facteur d'échelle est configurable via le paramètre `sprite_scale` (défaut: 2.0)
- **Redimensionnement** : Les sprites sont redimensionnés en utilisant `pygame.transform.smoothscale()` pour une meilleure qualité visuelle
- **Adaptation à la résolution interne** : Le `sprite_scale` est appliqué DANS le repère de conception (1920x1080), puis le résultat est converti vers la résolution interne (1280x720) : `display_width = (sprite_width * sprite_scale) * scale_x`, `display_height = (sprite_height * sprite_scale) * scale_y`. Cela garantit que les PNJ sont correctement dimensionnés quelle que soit la résolution réelle de la fenêtre.
- **Mise en cache locale** : Les sprites redimensionnés sont mis en cache localement dans `_scaled_frame_cache` pour éviter de recalculer le redimensionnement à chaque frame
- **Calculs de position d'affichage** : Les calculs de position pour le dessin (`get_draw_command`) doivent tenir compte de la taille d'affichage (`display_width` et `display_height`) et non de la taille du sprite sheet
- **Calculs de collision** : Les calculs de collision (`get_collision_rect`) s'alignent sur la taille affichée (`display_width` et `display_height`) tout en conservant une marge constante (20 px latéraux, 6 px en haut) pour garantir une hitbox cohérente lorsque les sprites sont redimensionnés.
- **Méthode `_scale_sprite()`** : Une méthode similaire à celle du joueur doit être implémentée pour redimensionner les sprites selon le facteur d'échelle
- **Clés de cache locaux** : Les caches locaux de sprites redimensionnés utilisent `(row, col, display_width, display_height)` comme clé (et une variante pour les sprites retournés) afin d'éviter qu'une frame animée ne remplace toutes les autres lorsque la taille d'affichage change.

### Gestion des dimensions de sprite

**IMPORTANT** : Les valeurs de `sprite_width` et `sprite_height` configurées pour un PNJ **DOIVENT** correspondre exactement aux dimensions réelles des sprites dans le sprite sheet. Cela est **CRITIQUE** pour l'affichage correct des sprites, en particulier pour les animations idle.

**Validation obligatoire** :
- Le sprite sheet doit être divisible exactement par `sprite_width` et `sprite_height`
- Lors du chargement de la configuration d'un PNJ, le système doit vérifier que :
  - `sprite_sheet_width % sprite_width == 0` (le nombre de colonnes est un entier)
  - `sprite_sheet_height % sprite_height == 0` (le nombre de lignes est un entier)
- Si ces conditions ne sont pas respectées, une erreur doit être levée avec un message clair indiquant les dimensions incompatibles

**Exemple de validation** :
```python
sheet_width = sprite_sheet.get_width()
sheet_height = sprite_sheet.get_height()

if sheet_width % sprite_width != 0:
    raise ValueError(
        f"sprite_width {sprite_width} n'est pas compatible avec le sprite sheet "
        f"(largeur {sheet_width}). La largeur du sprite sheet doit être divisible exactement par sprite_width."
    )

if sheet_height % sprite_height != 0:
    raise ValueError(
        f"sprite_height {sprite_height} n'est pas compatible avec le sprite sheet "
        f"(hauteur {sheet_height}). La hauteur du sprite sheet doit être divisible exactement par sprite_height."
    )
```

**Impact sur l'affichage idle** :
- Une animation idle utilise les dimensions `sprite_width` et `sprite_height` pour extraire le sprite correct du sprite sheet
- Si les dimensions sont incorrectes, le sprite extrait sera mal positionné ou mal dimensionné
- C'est pourquoi cette validation est CRITIQUE pour garantir l'affichage correct de toutes les animations, en particulier les animations statiques (idle)

### Gestion des animations

Les animations des PNJ sont gérées de manière similaire au joueur :

1. **Configuration** : Les animations sont définies dans le fichier de configuration
2. **Animation par défaut** : Si aucune animation n'est spécifiée, le PNJ affiche la première frame (frame 0) de la première ligne (row 0)
3. **Animation active** : Le PNJ peut avoir une animation active (par exemple "idle", "walk")
4. **Boucle** : Les animations peuvent se répéter en boucle ou s'arrêter à la dernière frame
5. **Vitesse** : Chaque animation a sa propre vitesse (frames par seconde)
6. **Animation de déplacement temporaire** : Lorsqu'un déplacement est déclenché par un événement (voir spécification 11), une animation temporaire peut être activée. Cette animation prend le dessus sur l'animation normale pendant le déplacement et est désactivée une fois le déplacement terminé.

### Gestion du déplacement déclenché par événements

Le PNJ peut être déplacé horizontalement par le système de déclencheurs d'événements (voir spécification 11). Le déplacement est géré dans la méthode `update()` :

1. **Démarrage du déplacement** : La méthode `start_movement()` est appelée par le système de déclencheurs avec les paramètres suivants :
   - `target_x` : Position X cible
   - `speed` : Vitesse de déplacement en pixels par seconde
   - `direction` : Direction du déplacement ("left" ou "right")
   - `animation_row` (optionnel) : Ligne du sprite sheet pour l'animation
   - `animation_frames` (optionnel) : Nombre de frames pour l'animation

2. **Pendant le déplacement** :
   - La direction du PNJ est mise à jour avec la valeur spécifiée (`self.direction = direction`)
   - L'orientation du sprite est appliquée immédiatement : si `direction == "left"`, le sprite est inversé horizontalement via `_get_flipped_sprite()`, sinon le sprite normal est utilisé via `_get_sprite_at()`
   - Si une animation temporaire est spécifiée, elle est activée et remplace l'animation normale
   - Le PNJ se déplace horizontalement vers `target_x` à la vitesse `speed`
   - **La gravité s'applique en permanence** : Le PNJ est soumis à la gravité même pendant le déplacement. Si le PNJ se déplace au-dessus d'un vide, il tombe. Les collisions verticales sont résolues à chaque frame pour maintenir le PNJ au sol ou gérer les chutes.

3. **Arrêt du déplacement** :
   - Le déplacement s'arrête lorsque le PNJ atteint `target_x` (avec une tolérance de quelques pixels pour éviter les oscillations)
   - L'animation temporaire est désactivée et l'animation normale reprend
   - Les propriétés `_move_target_x`, `_move_speed`, `_move_animation_row` et `_move_animation_frames` sont réinitialisées

4. **Vérification de l'état** : La méthode `is_moving()` retourne `True` si `_move_target_x` n'est pas `None`, indiquant qu'un déplacement est en cours.

### Gestion du suivi du personnage principal

Le PNJ peut suivre automatiquement le personnage principal via un événement déclenché par le système de déclencheurs (voir spécification 11). Le suivi est géré dans la méthode `update()` :

1. **Démarrage du suivi** : La méthode `start_following_player()` est appelée par le système de déclencheurs avec les paramètres suivants :
   - `player` : Instance du personnage principal à suivre (obligatoire)
   - `follow_distance` (optionnel, défaut: 100.0) : Distance horizontale à maintenir derrière le joueur en pixels
   - `follow_speed` (optionnel, défaut: 200.0) : Vitesse de déplacement lors du suivi en pixels par seconde
   - `animation_row` (optionnel) : Ligne du sprite sheet pour l'animation de suivi. Si non spécifié, utilise l'animation "walk" si disponible, sinon l'animation actuelle
   - `animation_frames` (optionnel) : Nombre de frames pour l'animation de suivi. Si non spécifié, utilise la configuration d'animation existante

2. **Pendant le suivi** :
   - **Positionnement automatique** : Le PNJ se positionne automatiquement derrière le personnage principal :
     - Si le joueur va à gauche (position X du joueur diminue), le PNJ se positionne à droite du joueur (à une distance `follow_distance` pixels)
     - Si le joueur va à droite (position X du joueur augmente), le PNJ se positionne à gauche du joueur (à une distance `follow_distance` pixels)
     - Si le joueur ne bouge pas horizontalement, le PNJ maintient sa position relative actuelle
   - **Gestion automatique de la direction** : La direction du PNJ est automatiquement mise à jour en fonction de la direction de son **mouvement vers sa position cible**, pas en fonction de la direction du joueur. Cela garantit que le PNJ se déplace d'abord vers sa nouvelle position avant de changer de direction visuelle :
     - Si le PNJ se déplace vers la droite pour atteindre sa position cible, il regarde vers la droite (`direction = "right"`)
     - Si le PNJ se déplace vers la gauche pour atteindre sa position cible, il regarde vers la gauche (`direction = "left"`)
     - **IMPORTANT** : La direction est déterminée par la direction du mouvement du PNJ (`target_x - self.x`), pas par la direction du joueur. Cela évite que le PNJ se retourne immédiatement quand le joueur change de direction, et garantit qu'il se déplace d'abord vers sa nouvelle position cible avant de changer de direction visuelle.
   - **Animation de suivi** : Si une animation de suivi est spécifiée (`animation_row` et `animation_frames`), elle est activée et remplace l'animation normale. Sinon, l'animation "walk" est utilisée si disponible, ou l'animation actuelle est conservée.
   - **Déplacement progressif** : Le PNJ se déplace progressivement vers sa position cible à la vitesse `follow_speed`. La position cible est calculée à chaque frame en fonction de la position actuelle du joueur et de sa direction de déplacement.
   - **La gravité s'applique en permanence** : Le PNJ est soumis à la gravité même pendant le suivi. Si le PNJ se déplace au-dessus d'un vide, il tombe. Les collisions verticales sont résolues à chaque frame pour maintenir le PNJ au sol ou gérer les chutes.

3. **Arrêt du suivi** :
   - Le suivi s'arrête lorsque la méthode `stop_following_player()` est appelée (par exemple via un événement de déclencheurs)
   - L'animation de suivi est désactivée et l'animation normale reprend (idle par défaut)
   - Les propriétés `_is_following_player`, `_follow_player`, `_follow_distance`, `_follow_speed`, `_follow_animation_row` et `_follow_animation_frames` sont réinitialisées

4. **Vérification de l'état** : La méthode `is_following_player()` retourne `True` si `_is_following_player` est `True`, indiquant qu'un suivi est en cours.

**Calcul de la position cible** :
- La position cible est calculée à chaque frame dans `update()` :
  - Si le joueur se déplace vers la gauche (`player.x < _player_last_x`), la position cible est `player.x + follow_distance` (PNJ à droite du joueur)
  - Si le joueur se déplace vers la droite (`player.x > _player_last_x`), la position cible est `player.x - follow_distance` (PNJ à gauche du joueur)
  - Si le joueur ne bouge pas (`player.x == _player_last_x`), la position cible est calculée en fonction de la position relative actuelle du PNJ :
    - Si le PNJ est trop proche du joueur (distance < `follow_distance`), la position cible est déterminée en fonction de la position relative (PNJ à gauche → se positionner à gauche, PNJ à droite → se positionner à droite)
    - Si le PNJ est loin du joueur, la position cible est la position la plus proche derrière le joueur (à gauche ou à droite selon la distance)
- **IMPORTANT** : Le PNJ se déplace **toujours** activement vers sa position cible à la vitesse `follow_speed`, même si le joueur ne bouge pas. Le PNJ ne doit jamais attendre passivement le déplacement du joueur, il doit se rapprocher au maximum de sa position cible derrière le joueur.
- La position précédente du joueur (`_player_last_x`) est mise à jour à chaque frame pour détecter les changements de direction

**Priorité des comportements** :
- Le suivi du joueur a la priorité sur les déplacements déclenchés par événements (`start_movement()`). Si un PNJ suit le joueur, les déplacements déclenchés par événements sont ignorés jusqu'à ce que le suivi soit arrêté.
- Si un PNJ suit le joueur et qu'un déplacement est déclenché, le suivi est automatiquement arrêté et le déplacement prend le dessus.

**Format du sprite sheet** :
- Les animations sont organisées en lignes dans le sprite sheet
- Chaque ligne contient les frames d'une animation
- Les frames sont lues de gauche à droite
- Le nombre de frames est spécifié dans la configuration
- **Validation des limites** :
  - Le système calcule automatiquement le nombre de lignes (`_sheet_rows`) et de colonnes (`_sheet_columns`) du sprite sheet lors de l'initialisation
  - Lors de l'extraction d'un sprite (`_get_sprite_at`), les coordonnées `row` et `col` sont validées :
    - La ligne (`row`) est limitée entre 0 et `_sheet_rows - 1` (clampée si hors limites)
    - La colonne (`col`) utilise un modulo pour rester dans les limites (`col % _sheet_columns`)
  - Avant d'extraire un sprite avec `subsurface`, le système vérifie que le rectangle d'extraction reste dans les limites du sprite sheet
  - Si les coordonnées sont invalides ou si l'extraction échoue, une surface transparente est retournée pour éviter les erreurs d'affichage
  - Cette validation garantit que les animations temporaires de déplacement ne causent pas d'erreurs même si les paramètres `move_animation_row` ou `move_animation_frames` sont incorrects
- **Performance & sécurité** :
  - `animation_speed` doit être `>= 0`. Une valeur strictement positive active l'animation dynamique. Une valeur `0` indique une animation statique : la première frame de la ligne est affichée en continu sans mise à jour.
  - `num_frames` doit être `>= 1`. Si `num_frames <= 1`, la première frame de la ligne est affichée et aucune mise à jour d'animation n'est effectuée.

### Orientation du sprite

- Le champ `direction` contrôle la façon dont le sprite est affiché :
  - `direction = "right"` : le sprite est rendu tel quel.
  - `direction = "left"` : le sprite est inversé **horizontalement** (`pygame.transform.flip(sprite, True, False)`), ce qui permet d'obtenir un personnage "mirroir" vers la gauche conformément à la demande.
  
**Note importante** : Pour inverser un sprite vers la gauche, on utilise un flip **horizontal** (axe vertical), pas vertical. La fonction `pygame.transform.flip(sprite, True, False)` inverse horizontalement (premier paramètre `True` = flip horizontal, deuxième paramètre `False` = pas de flip vertical).

- **Initialisation** : La direction est initialisée depuis le fichier de configuration TOML lors de la création du PNJ. Si non spécifiée, la valeur par défaut est `"right"`.

- **Modification dynamique** : La valeur de `direction` peut être modifiée dynamiquement après l'initialisation. Cela permettra, dans des développements futurs, de changer l'orientation du PNJ en fonction de ses mouvements (par exemple, un PNJ qui se déplace vers la gauche changera automatiquement sa direction vers `"left"`). La méthode `draw` doit donc appliquer le flip à chaque frame en fonction de la valeur actuelle de `direction` plutôt que de précalculer une seule fois.

- **Implémentation** :
  - L'orientation doit être appliquée au moment du dessin (`get_draw_command`). L'animation et le cache de frames restent communs : on applique le flip sur la frame courante juste avant de la blitter.
  - La méthode `get_draw_command()` vérifie `self.direction` et appelle :
    - `_get_flipped_sprite()` si `direction == "left"` (inverse horizontalement le sprite pour regarder vers la gauche)
    - `_get_sprite_at()` si `direction == "right"` (affiche le sprite tel quel pour regarder vers la droite)
  - Les méthodes `_get_sprite_at()` et `_get_flipped_sprite()` doivent appeler `_scale_sprite()` pour redimensionner les sprites selon le facteur d'échelle
  - Les calculs de position dans `get_draw_command()` doivent utiliser `display_width` et `display_height` au lieu de `sprite_width` et `sprite_height`
  - Cette logique s'applique à la fois pour les animations normales et pour les animations temporaires de déplacement, garantissant que la direction est toujours prise en compte.
  - Pour éviter les allocations inutiles :
    - Utiliser un cache secondaire (`_flipped_frame_cache`) pour stocker les versions inversées horizontalement des frames déjà extraites.
    - La méthode `_get_flipped_sprite()` utilise la même validation de limites que `_get_sprite_at()` pour garantir la cohérence du cache.
    - Invalider ce cache en même temps que `_frame_cache` si le sprite sheet change.
  - **Important** : Lors des déplacements déclenchés par événements, la direction est mise à jour dans `start_movement()` et le flip est appliqué correctement à chaque frame pendant le déplacement.

### Affichage du nom

Le nom des PNJ est affiché de la même manière que le nom du joueur :

1. **Position** : Le nom est centré horizontalement au-dessus de la tête du PNJ
2. **Style** : Texte blanc avec contour noir épais (2 pixels) pour une excellente lisibilité
3. **Police** : Utilise la même police que le joueur par défaut (ou une police personnalisée si spécifiée)
4. **Taille** : Taille configurable (36px par défaut)
5. **Décalage** : Décalage vertical configurable pour positionner le nom juste au-dessus du sprite
6. **Suivi** : Le nom suit le mouvement du PNJ (caméra incluse)
7. **Référence d'affichage** : Les calculs de position du nom et des bulles utilisent `display_width` / `display_height` pour rester alignés lorsque les sprites sont redimensionnés.

**Implémentation** :
- Utiliser la même méthode `_render_name()` que le joueur
- Utiliser la même méthode `draw_name()` que le joueur
- Le nom est rendu dans la couche de gameplay (depth 2), après le PNJ

#### Centrage horizontal du nom

Le calcul de position horizontale du nom doit garantir un centrage parfait par rapport au sprite affiché. Le problème de centrage provient du fait que le calcul de position du nom doit utiliser exactement la même logique que le calcul de position du sprite pour garantir un alignement parfait.

**Principe de fonctionnement** :

- **Position du sprite** : Le sprite est dessiné avec `draw_x = round(screen_x - self.display_width / 2)`, ce qui centre le sprite sur `screen_x`.
- **Position du nom** : Le nom doit être positionné avec `name_x = round(screen_x - self.name_rect.width / 2)`, ce qui centre le nom sur `screen_x` également.
- **Cohérence** : Les deux méthodes (`get_draw_command()` et `get_name_draw_command()`) doivent utiliser exactement la même valeur de `screen_x` calculée de la même manière : `screen_x = self.x - camera_x`.

**Méthode `get_name_draw_command()` de la classe `NPC`** :

La méthode `get_name_draw_command()` doit être implémentée pour garantir un centrage parfait du nom par rapport au sprite affiché.

**Code recommandé** :
```python
def get_name_draw_command(self, camera_x: float) -> Optional[tuple[pygame.Surface, tuple[int, int]]]:
    """Construit la commande de dessin pour le nom du PNJ."""
    if self.name_surface is None:
        return None
    
    # Calculer la position à l'écran en tenant compte de la caméra
    screen_x = self.x - camera_x
    screen_y = self.y
    
    # Centrer le nom sur screen_x (qui correspond au centre du sprite)
    # Utiliser la même logique que get_draw_command() pour garantir la cohérence
    name_x = round(screen_x - self.name_rect.width / 2)
    
    # Position verticale : au-dessus du sprite avec le décalage configuré
    name_y = round(screen_y - self.sprite_height / 2 + self.name_offset_y - self.name_rect.height)
    
    return self.name_surface, (name_x, name_y)
```

**Vérification de cohérence** :

Pour garantir que le nom est correctement centré, il faut s'assurer que :

1. **Le sprite est centré sur `screen_x`** : Dans `get_draw_command()`, `draw_x = round(screen_x - self.display_width / 2)` centre le sprite sur `screen_x`.
2. **Le nom est centré sur `screen_x`** : Dans `get_name_draw_command()`, `name_x = round(screen_x - self.name_rect.width / 2)` centre le nom sur `screen_x`.
3. **Cohérence des calculs** : Les deux méthodes utilisent la même valeur de `screen_x` calculée de la même manière : `screen_x = self.x - camera_x`.

**Gestion des sprites redimensionnés** :

Le système doit fonctionner correctement avec les sprites redimensionnés (facteur d'échelle) :

- **`display_width` et `display_height`** : Ces valeurs sont calculées en appliquant d'abord le `sprite_scale` dans le repère de conception (1920x1080), puis en convertissant vers la résolution interne (1280x720) : `display_width = (sprite_width * sprite_scale) * scale_x`, `display_height = (sprite_height * sprite_scale) * scale_y`.
- **Centrage du sprite** : Le sprite est centré en utilisant `display_width` dans `get_draw_command()`.
- **Centrage du nom** : Le nom doit être centré en utilisant `screen_x`, qui correspond au centre du sprite affiché, indépendamment du facteur d'échelle.

**Code de référence** :

Pour référence, voici le code de `get_draw_command()` qui calcule correctement la position du sprite :

```python
def get_draw_command(self, camera_x: float) -> tuple[pygame.Surface, tuple[int, int]]:
    """Construit la commande de dessin pour le sprite courant en appliquant l'orientation."""
    # ... (récupération du sprite) ...
    
    # Calculer la position à l'écran en tenant compte de la caméra
    screen_x = self.x - camera_x
    screen_y = self.y

    # Aligner le bas du sprite affiché sur le bas du sprite natif (et donc sur la hitbox)
    bottom_y = screen_y + self.sprite_height / 2

    draw_x = round(screen_x - self.display_width / 2)
    draw_y = round(bottom_y - self.display_height)

    return sprite, (draw_x, draw_y)
```

Le calcul de `name_x` dans `get_name_draw_command()` doit utiliser la même valeur de `screen_x` pour garantir l'alignement.

**Note importante** : Si le problème de centrage persiste après cette modification, il peut être nécessaire de vérifier que `self.x` représente bien le centre du sprite dans l'espace du monde. Le calcul doit être identique à celui utilisé dans `get_draw_command()`.

**Cohérence avec le joueur** :

- Le système d'affichage du nom du joueur doit être vérifié pour s'assurer qu'il utilise la même logique.
- Si le joueur a le même problème, la même correction doit être appliquée.

## Implémentation

### Structure de fichiers

```
src/moteur_jeu_presentation/
├── entities/
│   ├── __init__.py
│   ├── entity.py          # Classe Entity (classe abstraite de base)
│   ├── player.py          # Classe Player (hérite de Entity)
│   └── npc.py             # Classe NPC (hérite de Entity)
├── levels/
│   ├── __init__.py
│   ├── loader.py          # Classe LevelLoader (existant)
│   ├── config.py          # Classes LevelConfig (existant)
│   └── npc_loader.py      # Classe NPCLoader
├── levels/                # Répertoire des fichiers de niveau
│   ├── niveau_plateforme.niveau
│   └── niveau_plateforme.pnj
```

### Dépendances

Le système nécessite :
- Le système de collisions existant (`CollisionSystem`)
- Le système de parallaxe existant (`ParallaxSystem`)
- Le système de gestion de l'avancement dans le niveau (`LevelProgressTracker`, voir spécification 11) pour fournir la position du joueur dans le monde (obligatoire, via `get_current_x()`)
- Le système de bulles de dialogue (`SpeechBubble`, voir spécification 8) pour afficher les échanges
- Une bibliothèque TOML pour Python (`tomli`)

### Intégration avec le système de progression

Le système de dialogues des PNJ s'intègre avec le système de gestion de l'avancement dans le niveau (spécification 11) :

- **Fourniture de la position** : Le système de déclenchement des dialogues utilise le `LevelProgressTracker` pour obtenir la position actuelle du joueur dans le monde via `get_current_x()`
- **Calcul centralisé** : La position du joueur est suivie en continu par le système de progression, puis fournie aux NPCs lors des interactions. Cela évite les calculs redondants et garantit la cohérence
- **API de position** : Le système de déclenchement appellera `get_dialogue_block_for_position(player_position)` en passant la position obtenue via `progress_tracker.get_current_x()`

### Exemple d'utilisation

```python
from pathlib import Path
from entities.npc import NPC, NPCsConfig
from entities.player import Player
from levels.npc_loader import NPCLoader
from physics.collision import CollisionSystem
from game.progress import LevelProgressTracker
from entities.npc import start_dialogue, DialogueState
import pygame

# Initialisation
assets_dir = Path("sprite")
npc_loader = NPCLoader(assets_dir)

# Charger la configuration des PNJ
npcs_path = Path("levels/niveau_plateforme.pnj")
npcs_config = npc_loader.load_npcs(npcs_path)

# Créer les instances de PNJ
npcs: List[NPC] = []
for npc_config in npcs_config.npcs:
    npc = NPC(npc_config, collision_system, assets_dir)
    npcs.append(npc)

# Créer le système de progression (fournit la position du joueur)
progress_tracker = LevelProgressTracker(player)
# IMPORTANT : Initialiser current_x avec la position initiale du joueur
# pour que les dialogues puissent être déclenchés immédiatement
progress_tracker.update(0.0)

# État du dialogue en cours
current_dialogue: Optional[DialogueState] = None

# IMPORTANT : Dans la boucle principale, le dialogue DOIT être mis à jour
# INDÉPENDAMMENT de l'interface des stats. C'est-à-dire, le dialogue doit
# continuer à être mis à jour même si l'interface des stats est affichée.

# Dans la boucle de jeu
def handle_events(events: List[pygame.event.Event], camera_x: float) -> None:
    global current_dialogue
    
    for event in events:
        if event.type == pygame.QUIT:
            # Gérer la fermeture
            pass
        elif event.type == pygame.KEYDOWN:
            # Déclenchement du dialogue avec le PNJ le plus proche (voir spécification 2)
            if event.key == pygame.K_t:
                if current_dialogue is None:
                    # Trouver le PNJ le plus proche à portée d'interaction (voir spécification 2)
                    # Obtenir la position actuelle du joueur pour vérifier les blocs de dialogue disponibles
                    player_position = progress_tracker.get_current_x()
                    nearest_npc = find_nearest_interactable_npc(player.x, player.y, npcs, player_position)
                    if nearest_npc:
                        # Démarrer le dialogue (la position du joueur est obtenue via progress_tracker)
                        # Les événements associés aux échanges seront déclenchés automatiquement lors de l'affichage de chaque échange
                        current_dialogue = start_dialogue(nearest_npc, progress_tracker, event_system)
        
        # Transmettre les événements au dialogue en cours
        if current_dialogue is not None:
            if current_dialogue.handle_event(event, camera_x):
                # Si le dialogue est terminé, le nettoyer
                if current_dialogue.is_complete():
                    current_dialogue = None

def update(dt: float, camera_x: float) -> None:
    # Mettre à jour le système de progression
    progress_tracker.update(dt)
    
    # Mettre à jour les PNJ
    for npc in npcs:
        npc.update(dt, camera_x)
    
    # Mettre à jour le dialogue en cours
    if current_dialogue is not None:
        current_dialogue.update(camera_x, dt)
        # Vérifier si le dialogue est terminé
        if current_dialogue.is_complete():
            current_dialogue = None

def draw(screen: pygame.Surface, camera_x: float) -> None:
    # Dessiner les couches derrière le joueur (depth 0 et 1)
    for layer in parallax_system._layers:
        if layer.depth <= 1:
            parallax_system._draw_layer(screen, layer)
    
    # Dessiner le joueur
    player.draw(screen, camera_x)
    player.draw_name(screen, camera_x)
    
    # Dessiner les PNJ
    for npc in npcs:
        npc.draw(screen, camera_x)
        npc.draw_name(screen, camera_x)
    
    # Dessiner le dialogue en cours (au-dessus des PNJ)
    if current_dialogue is not None:
        current_dialogue.draw(screen, camera_x)
    
    # Dessiner les couches devant le joueur (depth 2 et 3)
    for layer in parallax_system._layers:
        if layer.depth >= 2:
            parallax_system._draw_layer(screen, layer)
```

### Gestion des erreurs

Le système doit gérer les erreurs suivantes :
- **Fichier introuvable** : Lever `FileNotFoundError` avec un message clair
- **Format invalide** : Lever `ValueError` avec indication de la ligne/section problématique
- **Sprite sheet introuvable** : Lever `FileNotFoundError` si le fichier image n'existe pas
- **Animation invalide** : Vérifier que les numéros de ligne sont valides pour le sprite sheet
- **Position invalide** : Vérifier que la coordonnée X est valide

### Validation

Le système doit valider :
- Que tous les champs obligatoires sont présents (`id`, `name`, `x`, `sprite_sheet_path`, `sprite_width`, `sprite_height`)
- Que `id` est une chaîne de caractères non vide et unique au sein du niveau
- Que `sprite_width` et `sprite_height` sont positifs
- **Que le sprite_width et sprite_height sont compatibles avec le sprite sheet** : 
  - Le sprite sheet doit être divisible exactement par `sprite_width` et `sprite_height`
  - Si `sprite_sheet_width % sprite_width != 0` ou `sprite_sheet_height % sprite_height != 0`, une erreur doit être levée
  - Le message d'erreur doit indiquer les dimensions réelles du sprite sheet et suggérer des dimensions valides
- Que `x` est un nombre valide
- Pour chaque animation :
  - Que `row` est présent et valide (>= 0 et < nombre de lignes dans le sprite sheet)
  - Que `num_frames` est un entier positif
  - Que `animation_speed` est un nombre positif
  - Que `loop` est un booléen si présent
- Pour chaque bloc de dialogue :
  - Que `position_min` est présent et est un nombre >= 0 (OBLIGATOIRE : utilisé pour sélectionner le bloc à déclencher)
  - Que `position_max` est présent et est un nombre >= `position_min` (OBLIGATOIRE : utilisé pour sélectionner le bloc à déclencher)
  - Que `exchanges` est présent et est une liste non vide
  - Que `dialogue_type` est `"normal"`, `"quête"`, `"discution"`, `"ecoute"`, `"regarder"`, `"enseigner"` ou `"reflexion"` si présent (défaut: `"normal"`)
  - Que `font_size` est un entier positif si présent
  - Que `text_speed` est un nombre positif si présent
  - **Validation de la plage de position** : Vérifier que la plage `[position_min, position_max]` est valide et cohérente (position_max >= position_min, position_min >= 0). Cette plage sera utilisée pour déterminer quel bloc de dialogue sera lancé lors d'une interaction en fonction de la position du joueur.
  - Pour chaque échange dans un bloc :
    - Que `speaker` est présent et est "npc" ou "player"
    - Que `text` est présent et est une chaîne (peut être vide si `image_path` est présent)
    - Que `image_path` est une chaîne valide si présent (chemin relatif ou absolu vers un fichier image)
    - Que au moins `text` ou `image_path` est présent (un échange doit avoir au moins du texte ou une image)
    - Que `font_size` est un entier positif si présent
    - Que `text_speed` est un nombre positif si présent
    - Que `trigger_events` est une liste de chaînes de caractères si présent (chaque élément doit être un identifiant d'événement valide)
    - **Note sur les événements** : Les identifiants dans `trigger_events` ne sont pas validés lors du chargement de la configuration des PNJ, car les événements sont chargés séparément. Si un identifiant d'événement n'existe pas, il sera ignoré silencieusement lors du déclenchement de l'échange.
    - Que `add_items` est un dictionnaire si présent (clé = item_id, valeur = quantité). Chaque `item_id` doit correspondre à un objet défini dans `inventory_items.toml` (voir spécification 13). Les quantités doivent être des entiers positifs.
    - Que `remove_items` est un dictionnaire si présent (clé = item_id, valeur = quantité). Chaque `item_id` doit correspondre à un objet défini dans `inventory_items.toml` (voir spécification 13). Les quantités doivent être des entiers positifs. Si la quantité disponible est insuffisante, l'opération échoue silencieusement lors de l'affichage de l'échange.
    - Que `player_animation` est un dictionnaire si présent, avec les champs suivants :
      - Que `sprite_sheet_path` est présent et est une chaîne valide
      - Que `row` est présent et est un entier >= 0
      - Que `num_frames` est présent et est un entier positif (>= 1)
      - Que `animation_speed` est présent et est un nombre positif (>= 0)
      - Que `animation_type` est `"simple"`, `"loop"` ou `"pingpong"` si présent (défaut: `"simple"`)
      - Que `start_sprite` est un entier >= 0 si présent (défaut: 0)
      - Que `offset_y` est un nombre si présent (défaut: 0.0)
      - Que `set_x_position` est un nombre valide si présent (optionnel, en pixels dans le repère de conception 1920x1080). Aucune validation de limites n'est effectuée (le personnage peut être positionné en dehors de l'écran visible). La valeur est automatiquement convertie du repère de conception vers le repère de rendu interne (1280x720) lors de l'application.
- Que les chemins de fichiers sont valides

## Contraintes et considérations

### Architecture : Classe abstraite Entity

**Important** : Le système utilise une classe abstraite `Entity` comme base commune pour `Player` et `NPC`. Cette architecture offre plusieurs avantages :

1. **Réutilisabilité** : Les propriétés communes (position, collision, gravité) sont définies une seule fois dans `Entity`
2. **Cohérence** : Le système de collisions peut accepter n'importe quelle `Entity`, garantissant un comportement cohérent
3. **Maintenabilité** : Les modifications aux propriétés communes n'ont besoin d'être faites qu'une seule fois
4. **Synchronisation** : Le système de collisions modifie directement `entity.velocity_y` lors de la résolution des collisions. En passant l'entité directement (au lieu d'un adaptateur), on garantit que les modifications sont correctement synchronisées.

**Piège à éviter** : Ne pas utiliser d'adaptateur ou de wrapper pour passer une entité au système de collisions. Le système modifie directement les propriétés de l'entité (notamment `velocity_y`), donc l'entité doit être passée directement pour que les modifications soient persistées.

### Performance

- Charger le sprite sheet une seule fois au démarrage
- Utiliser `convert_alpha()` pour optimiser le rendu des sprites avec transparence
- Mettre en cache les surfaces de nom rendues
- Limiter les calculs de position à chaque frame
- **Gravité permanente** : La gravité s'applique à chaque frame, pas seulement lors de l'initialisation. Le positionnement initial par gravité permet de placer le PNJ sur le sol au démarrage, puis la gravité continue de s'appliquer pour maintenir le PNJ au sol ou gérer les chutes.

### Dimensions et proportions

- Les dimensions des sprites doivent être cohérentes avec le sprite sheet
- Le PNJ doit être centré sur sa position (x, y représente le centre du sprite)
- La hitbox du PNJ doit être similaire à celle du joueur pour un comportement cohérent

### Gestion mémoire

- Charger les sprite sheets via `AssetManager` (si disponible) ou directement avec `pygame.image.load()`
- Ne pas créer de nouvelles surfaces à chaque frame pour extraire les sprites
- Réutiliser les surfaces de sprite extraites
- Libérer les ressources lors du changement de niveau

### Gravité et collisions

- Utiliser le même système de gravité que le joueur (800 pixels/s² par défaut)
- Utiliser le même système de collisions pour détecter les blocs de depth 2
- Le PNJ doit avoir une hitbox similaire au joueur (réduite pour éviter les collisions prématurées)
- **Gravité permanente** : La gravité s'applique en permanence aux PNJ, à chaque frame, même pendant les déplacements déclenchés par événements. Cela garantit un comportement cohérent avec le joueur et permet aux PNJ de tomber s'ils se déplacent au-dessus d'un vide.
- Le positionnement par gravité doit être robuste et gérer les cas limites (pas de bloc solide, bloc trop haut, etc.)
- **Important** : Le PNJ hérite de la classe `Entity` qui fournit les propriétés communes (position, collision, gravité). Le système de collisions accepte une `Entity` directement, ce qui évite d'avoir besoin d'un adaptateur et garantit que les modifications de `velocity_y` sont correctement synchronisées.
- **Résolution des collisions** : Les collisions verticales sont résolues à chaque frame via `_apply_gravity()`, qui utilise le système de collisions pour maintenir le PNJ au sol ou gérer les chutes. Les collisions horizontales peuvent également être résolues si nécessaire lors des déplacements.

### Animation

- Utiliser le delta time pour une animation fluide indépendante du FPS
- Gérer correctement le timer d'animation pour éviter les sauts de frames
- Assurer une transition fluide entre les animations si nécessaire
- Mettre à jour la position du nom (name_rect) à chaque frame
- Optimiser le rendu du texte : ne recalculer la surface que si le texte ou la police change

### Ordre de rendu

Les PNJ sont rendus dans la couche de gameplay (depth 2) :
- **Ordre de rendu (CRITIQUE pour les dialogues)** :
  1. Couches derrière le joueur (depth 0 et 1)
  2. Joueur et son nom
  3. PNJ et leurs noms
  4. Couches devant le joueur (depth 2 et 3) - FOREGROUND
  5. **Bulles de dialogue et dialogues des PNJ (DOIT être après le foreground pour rester visible)**
  6. Interface des statistiques

**IMPORTANT - Ordre critique** : Les bulles de dialogue (`speech_bubble`) et les dialogues des PNJ (`current_dialogue`) DOIVENT être dessinés **APRÈS** les couches de foreground (depth 2-3) pour rester visibles et ne pas être cachés par les décors. C'est l'ordre inverse de la profondeur normale car les bulles et dialogues sont des éléments UI qui doivent toujours être visibles au premier plan, au-dessus des décors.

**Note** : Les PNJ sont rendus après le joueur mais avant les couches de depth 2 et 3, ce qui permet aux éléments de décor de passer devant les PNJ si nécessaire.

## Tests

### Tests unitaires à implémenter

1. **Test de chargement de configuration** : Vérifier qu'un fichier de PNJ valide est correctement chargé
2. **Test de validation** : Vérifier que les erreurs de format sont détectées
3. **Test de positionnement par gravité** : Vérifier que le PNJ se positionne correctement sur le premier bloc de depth 2
4. **Test d'animation** : Vérifier que les animations fonctionnent correctement
5. **Test d'affichage du nom** : Vérifier que le nom est correctement affiché
6. **Test d'orientation** : Vérifier que `direction = "left"` inverse bien le sprite horizontalement et que `direction = "right"` laisse le sprite intact
7. **Test de gestion d'erreurs** : Vérifier que les erreurs sont gérées proprement
8. **Test de chargement des blocs de dialogue** : Vérifier que les configurations de blocs de dialogue sont correctement chargées depuis le fichier TOML
9. **Test de sélection de bloc de dialogue par position** : Vérifier que la méthode `get_dialogue_block_for_position()` retourne le bon bloc selon la position du joueur (obtenue via `LevelProgressTracker.get_current_x()`)
10. **Test de structure des échanges** : Vérifier que chaque bloc contient au moins un échange et que chaque échange contient un `speaker` valide ("npc" ou "player") et un texte non vide
11. **Test de centrage du nom** : Vérifier que le nom d'un PNJ est correctement centré au-dessus de son sprite
12. **Test de centrage avec différents facteurs d'échelle** : Tester avec `sprite_scale = 1.0`, `2.0`, `1.5`, etc., et vérifier que le nom reste centré
13. **Test de centrage avec différentes tailles de sprites** : Tester avec des sprites de différentes tailles (44x64, 64x64, 32x48, etc.) et vérifier que le nom reste centré
14. **Test de centrage avec différentes directions** : Tester avec `direction = "left"` et `direction = "right"` et vérifier que le nom reste centré dans les deux cas
15. **Test de centrage avec la caméra** : Tester en déplaçant la caméra et vérifier que le nom reste centré lorsque le PNJ est visible à l'écran

### Exemple de test

```python
import pytest
from pathlib import Path
from entities.npc import NPC
from levels.npc_loader import NPCLoader
from physics.collision import CollisionSystem

def test_load_npcs():
    """Test le chargement d'un fichier de PNJ."""
    assets_dir = Path("sprite")
    loader = NPCLoader(assets_dir)
    
    npcs_path = Path("levels/test_npcs.pnj")
    config = loader.load_npcs(npcs_path)
    
    assert len(config.npcs) > 0
    assert all(npc.name for npc in config.npcs)
    assert all(npc.x >= 0 for npc in config.npcs)

def test_npc_gravity_positioning():
    """Test que le PNJ se positionne correctement par gravité."""
    pygame.init()
    
    # Créer un système de collisions mock
    collision_system = MagicMock()
    collision_system.resolve_collision.return_value = (0.0, 0.0, True)
    
    # Créer un PNJ
    config = NPCConfig(
        name="Test NPC",
        x=500.0,
        sprite_sheet_path="sprite/robot.png",
        sprite_width=44,
        sprite_height=64
    )
    npc = NPC(config, collision_system)
    
    # Simuler la gravité
    npc.update(0.1, 0.0)
    
    # Vérifier que le PNJ est positionné
    assert npc._positioned == True
    assert npc.is_on_ground == True

def test_npc_name_centering():
    """Test que le nom du PNJ est correctement centré."""
    pygame.init()
    
    # Créer un PNJ avec un nom visible
    config = NPCConfig(
        id="test_npc",
        name="Test NPC",
        x=500.0,
        sprite_sheet_path="sprite/robot.png",
        sprite_width=44,
        sprite_height=64,
        sprite_scale=2.0
    )
    
    # Créer un système de collisions mock
    collision_system = MagicMock()
    collision_system.resolve_collision.return_value = (0.0, 0.0, True)
    
    npc = NPC(config, collision_system)
    
    # Obtenir la commande de dessin du nom
    camera_x = 0.0
    name_command = npc.get_name_draw_command(camera_x)
    
    # Vérifier que le nom est centré
    # Le nom doit être centré sur screen_x (qui correspond au centre du sprite)
    screen_x = npc.x - camera_x
    expected_name_x = round(screen_x - npc.name_rect.width / 2)
    
    assert name_command is not None
    name_surface, (name_x, name_y) = name_command
    assert name_x == expected_name_x
```

## Évolutions futures possibles

- **Système de déclenchement automatique** : Déclenchement automatique des dialogues lorsque le joueur s'approche d'un PNJ (au lieu d'une touche de test)
- **Système d'interaction** : Le déclenchement des dialogues est géré par le système d'interaction avec les PNJ (voir spécification 2). Le code de test qui cherchait spécifiquement le PNJ "Robot" doit être supprimé et remplacé par le système de détection de proximité.
- Interactions avancées avec les PNJ (quêtes, choix multiples, etc.)
- Comportements intelligents (mouvement, patrouille, etc.)
- **Mouvements et changement de direction** : Implémentation de mouvements pour les PNJ (déplacement horizontal, patrouille, etc.) qui modifieront automatiquement la direction du PNJ en fonction de son mouvement (par exemple, un PNJ qui se déplace vers la gauche changera `direction` vers `"left"`)
- Animations conditionnelles (selon l'état du PNJ)
- Support de plusieurs animations simultanées
- Éditeur visuel de PNJ
- Support de métadonnées optionnelles (description, quêtes, etc.)
- Système de détection de proximité (le PNJ réagit quand le joueur s'approche)
- Animations de transition entre états

## Références

- Bonnes pratiques : `bonne_pratique.md`
- Spécification personnage principal : `spec/2-personnage-principal.md`
- Spécification système de physique : `spec/4-systeme-de-physique-collisions.md`
- Spécification système de fichier niveau : `spec/3-systeme-de-fichier-niveau.md`
- Spécification système de bulles de dialogue : `spec/8-systeme-de-bulles-de-dialogue.md`
- Spécification système de gestion de l'avancement dans le niveau : `spec/11-systeme-gestion-avancement-niveau.md` (fournit la distance entre le joueur et les PNJ)
- Documentation TOML : [TOML Specification](https://toml.io/)
- Bibliothèque tomli : [tomli on PyPI](https://pypi.org/project/tomli/)

---

**Date de création** : 2024  
**Statut** : ✅ Implémenté

**Modifications récentes** :
- ✅ Ajout du type de dialogue "reflexion" : Le système supporte maintenant un nouveau type de dialogue "reflexion" qui affiche "T pour reflechir" comme indicateur d'interaction. Ce type permet au joueur de réfléchir sur quelque chose. Cette modification a été implémentée :
  - ✅ Mise à jour de `DialogueBlockConfig` dans `config.py` pour inclure "reflexion" dans le Literal
  - ✅ Mise à jour de `get_dialogue_type_for_position()` dans `npc.py` pour retourner le nouveau type
  - ✅ Mise à jour de la validation dans `npc_loader.py` pour accepter le nouveau type
  - ✅ Ajout de la gestion du nouveau type dans `main.py` pour l'affichage de l'indicateur "T pour reflechir"
  - ✅ Mise à jour de la documentation dans le README avec un exemple d'utilisation
- ✅ Ajout des types de dialogue "regarder" et "enseigner" : Le système supporte maintenant deux nouveaux types de dialogue pour enrichir les interactions avec les PNJ. Le type "regarder" affiche "T pour regarder ce que c'est" et permet au joueur d'examiner quelque chose. Le type "enseigner" affiche "T pour former" et indique une formation où le joueur peut apprendre quelque chose. Cette modification a été implémentée :
  - ✅ Mise à jour de `DialogueBlockConfig` dans `config.py` pour inclure les nouveaux types dans le Literal
  - ✅ Mise à jour de `get_dialogue_type_for_position()` dans `npc.py` pour retourner les nouveaux types
  - ✅ Mise à jour de la validation dans `npc_loader.py` pour accepter les nouveaux types
  - ✅ Ajout de la gestion des nouveaux types dans `main.py` pour l'affichage des indicateurs
  - ✅ Mise à jour de la documentation dans le README avec des exemples d'utilisation
- ✅ Ajout du champ `y` optionnel pour définir la position verticale d'apparition initiale des PNJ : Le système permet maintenant de définir un `y` optionnel dans la configuration d'un PNJ. Si défini, le PNJ commence à cette position Y, puis la gravité le fait tomber vers le sol en dessous (y plus grand dans le repère existant). Si non défini, le comportement actuel est conservé (y=0.0 puis chute jusqu'au premier bloc de depth 2). Cette modification a été implémentée :
  - ✅ Ajout du champ `y: Optional[float] = None` dans la classe `NPCConfig` (placé après les champs obligatoires pour respecter les règles des dataclasses)
  - ✅ Modification du chargement TOML pour lire le champ `y` optionnel avec conversion du repère de conception vers le repère de rendu interne
  - ✅ Modification de l'initialisation du PNJ pour utiliser `config.y` si défini, sinon utiliser `y=0.0`
  - ✅ Mise à jour de la documentation TOML avec le champ `y` optionnel
  - ✅ Mise à jour du README pour documenter la nouvelle fonctionnalité
- ✅ Ajout de la vérification de position Y dans la détection de dialogue : Le système de détection de dialogue prend maintenant en compte la position Y du personnage principal et du PNJ. Un dialogue ne peut être déclenché que si le joueur et le PNJ sont à peu près à la même hauteur (différence de Y <= INTERACTION_Y_THRESHOLD, par défaut 100 pixels). Cette modification a été implémentée :
  - ✅ Ajout de la constante `INTERACTION_Y_THRESHOLD = 100.0` (pixels) dans `main.py`
  - ✅ Modification de la fonction `find_nearest_interactable_npc()` pour accepter `player_y` en paramètre et vérifier la distance verticale
  - ✅ Mise à jour de tous les appels à `find_nearest_interactable_npc()` pour inclure `player.y`
  - ✅ Mise à jour de la logique d'affichage de l'indicateur d'interaction pour vérifier également la position Y

