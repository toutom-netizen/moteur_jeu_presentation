"""Module de configuration des niveaux."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

from ..entities.player_level_manager import DEFAULT_PLAYER_LEVEL


@dataclass
class SpriteSheetConfig:
    """Décrit un sprite sheet exploitable par le niveau."""

    name: str  # Identifiant unique (clé utilisée dans le fichier .niveau)
    path: Path  # Chemin vers le fichier sprite sheet
    sprite_width: int  # Largeur d'un sprite individuel
    sprite_height: int  # Hauteur d'un sprite individuel
    spacing: float = 0.0  # Espacement horizontal par défaut appliqué aux couches utilisant ce sheet


@dataclass
class RowMapping:
    """Représente le mapping d'une ligne d'un sprite sheet vers une couche."""

    sheet: str  # Nom du sprite sheet déclaré dans [sprite_sheets]
    row: int  # Ligne dans le sprite sheet (0-indexed)
    depth: int  # Profondeur de la couche (0-3)
    spacing: float = 0.0  # Espacement horizontal entre les sprites lors de la concaténation (en pixels, optionnel)
    is_infinite: bool = True  # Si True, la couche se répète horizontalement à l'infini (optionnel, défaut: True)
    is_background: bool = False  # Si True, la couche s'affiche derrière le joueur et n'a pas de collision (optionnel, défaut: False). Uniquement applicable pour depth 2.
    is_foreground: bool = False  # Si True, la couche s'affiche devant les autres éléments de depth 2 et n'a pas de collision (optionnel, défaut: False). Uniquement applicable pour depth 2.
    is_climbable: bool = False  # Si True, la couche peut être grimpée par le joueur (optionnel, défaut: False). Uniquement applicable pour depth 2 avec is_background = true. Quand le joueur est sur un bloc grimpable, la flèche du haut permet de grimper au lieu de sauter.
    initial_alpha: int = 255  # Opacité initiale de la couche (0-255, optionnel, défaut: 255 = complètement opaque). Permet de définir une couche qui commence invisible (0) et peut être affichée via un événement sprite_show.
    tags: Optional[List[str]] = None  # Liste de tags pour identifier cette couche (optionnel, défaut: liste vide)


@dataclass
class SpriteMapping:
    """Représente le mapping d'un sprite unique vers une couche."""

    sheet: str  # Nom du sprite sheet déclaré dans [sprite_sheets]
    row: int  # Ligne dans le sprite sheet (0-indexed)
    col: int  # Colonne dans le sprite sheet (0-indexed)
    depth: int  # Profondeur de la couche (0-3)
    count_x: int  # Nombre de répétitions du sprite horizontalement
    first_sprite_row: Optional[int] = None  # Ligne du sprite sheet pour le premier sprite (0-indexed, optionnel, uniquement si count_x > 3)
    first_sprite_col: Optional[int] = None  # Colonne du sprite sheet pour le premier sprite (0-indexed, optionnel, uniquement si count_x > 3)
    last_sprite_row: Optional[int] = None  # Ligne du sprite sheet pour le dernier sprite (0-indexed, optionnel, uniquement si count_x > 3)
    last_sprite_col: Optional[int] = None  # Colonne du sprite sheet pour le dernier sprite (0-indexed, optionnel, uniquement si count_x > 3)
    count_y: int = 1  # Nombre de répétitions du sprite verticalement vers le haut (optionnel, défaut: 1)
    y_offset: float = 0.0  # Position verticale du sprite le plus bas (en pixels depuis le haut de l'écran)
    x_offset: float = 0.0  # Offset horizontal pour corriger le spacing (en pixels, optionnel)
    spacing: float = 0.0  # Espacement horizontal entre chaque répétition du sprite (en pixels, optionnel)
    spacing_y: float = 0.0  # Espacement vertical entre chaque répétition du sprite vers le haut (en pixels, optionnel, défaut: 0.0)
    infinite_offset: float = 0.0  # Distance entre chaque répétition infinie (en pixels, optionnel, uniquement si is_infinite = true)
    is_infinite: bool = True  # Si True, la couche se répète horizontalement à l'infini (optionnel, défaut: True)
    scale: float = 1.0  # Facteur de redimensionnement du sprite (en pourcentage, optionnel, défaut: 1.0 = 100%)
    is_background: bool = False  # Si True, la couche s'affiche derrière le joueur et n'a pas de collision (optionnel, défaut: False). Uniquement applicable pour depth 2.
    is_foreground: bool = False  # Si True, la couche s'affiche devant les autres éléments de depth 2 et n'a pas de collision (optionnel, défaut: False). Uniquement applicable pour depth 2.
    is_climbable: bool = False  # Si True, la couche peut être grimpée par le joueur (optionnel, défaut: False). Uniquement applicable pour depth 2 avec is_background = true. Quand le joueur est sur un bloc grimpable, la flèche du haut permet de grimper au lieu de sauter.
    initial_alpha: int = 255  # Opacité initiale du sprite (0-255, optionnel, défaut: 255 = complètement opaque). Permet de définir un sprite qui commence invisible (0) et peut être affiché via un événement sprite_show.
    tags: Optional[List[str]] = None  # Liste de tags pour identifier cette couche (optionnel, défaut: liste vide)


@dataclass
class LevelConfig:
    """Configuration complète d'un niveau."""

    sprite_sheets: Dict[str, SpriteSheetConfig]  # Sprite sheets disponibles indexés par nom
    rows: List[RowMapping]  # Liste des lignes et leur profondeur associée
    sprites: List[SpriteMapping]  # Liste des sprites individuels et leur configuration
    player_level: int = DEFAULT_PLAYER_LEVEL


@dataclass
class AnimationConfig:
    """Configuration d'une animation pour un PNJ."""

    row: int  # Ligne dans le sprite sheet (0-indexed)
    num_frames: int  # Nombre de frames dans l'animation
    animation_speed: float  # Vitesse d'animation en frames par seconde
    loop: bool = True  # Si l'animation se répète en boucle


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
    set_x_position: Optional[float] = None  # Position X cible pour le personnage principal (en pixels dans le repère de conception 1920x1080). Si définie, le personnage est déplacé vers cette position lors du déclenchement de l'animation et la caméra est recentrée de la même manière que durant le gameplay normal.


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
    trigger_events: Optional[List[str]] = None  # Liste des identifiants d'événements à déclencher lorsque cet échange est affiché (optionnel). Les événements doivent être définis dans le fichier .event du niveau (voir spécification 11). Les événements sont déclenchés lors de l'affichage de l'échange, avant que la bulle ne soit créée. Si un événement n'existe pas ou a déjà été déclenché, il est ignoré silencieusement.
    add_items: Optional[Dict[str, int]] = None  # Dictionnaire des objets à ajouter à l'inventaire du joueur (optionnel). Clé = item_id (ID technique de l'objet), valeur = quantité. Les objets sont ajoutés lors de l'affichage de l'échange, avec animation d'apparition progressive (voir spécification 13). Les objets doivent être définis dans inventory_items.toml.
    remove_items: Optional[Dict[str, int]] = None  # Dictionnaire des objets à retirer de l'inventaire du joueur (optionnel). Clé = item_id (ID technique de l'objet), valeur = quantité. Les objets sont retirés lors de l'affichage de l'échange, avec animation de saut vers l'arrière puis disparition (voir spécification 13). Si la quantité disponible est insuffisante, l'opération échoue silencieusement (log un avertissement).
    player_animation: Optional[PlayerAnimationConfig] = None  # Animation du personnage principal pendant cet échange (optionnel). L'animation est déclenchée lorsque l'échange est affiché et s'arrête lorsque l'échange se termine ou que le dialogue passe à l'échange suivant.


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


@dataclass
class NPCConfig:
    """Configuration d'un PNJ individuel."""

    id: str  # Identifiant technique unique du PNJ (utilisé pour les déclencheurs d'événements)
    name: str  # Nom du PNJ (affiché au-dessus de sa tête)
    x: float  # Position horizontale dans l'espace du monde
    sprite_sheet_path: str  # Chemin vers le fichier sprite sheet du PNJ
    sprite_width: int  # Largeur d'un sprite individuel
    sprite_height: int  # Hauteur d'un sprite individuel
    sprite_scale: float = 2.0  # Facteur d'échelle pour l'affichage du sprite (défaut: 2.0 = 200%, double la taille)
    direction: Literal["left", "right"] = "right"  # Orientation initiale du PNJ (peut être modifiée dynamiquement)
    y: Optional[float] = None  # Position verticale d'apparition initiale (optionnel, en pixels). Si défini, le PNJ commence à cette position Y, puis la gravité le fait tomber vers le sol en dessous (y plus grand dans le repère existant). Si non défini, le PNJ commence à y=0.0 (en haut de l'écran) puis tombe jusqu'au premier bloc de depth 2.
    animations: Optional[Dict[str, AnimationConfig]] = None  # Animations du PNJ (optionnel)
    font_path: Optional[str] = None  # Police pour le nom (optionnel, utilise celle du joueur par défaut)
    font_size: int = 36  # Taille de la police pour le nom
    name_color: Tuple[int, int, int] = (255, 255, 255)  # Couleur du nom
    name_outline_color: Tuple[int, int, int] = (0, 0, 0)  # Couleur du contour du nom
    name_offset_y: float = -4.0  # Décalage vertical du nom par rapport au haut du sprite
    dialogue_blocks: Optional[List[DialogueBlockConfig]] = None  # Liste des blocs de dialogue du PNJ (optionnel)


@dataclass
class NPCsConfig:
    """Configuration complète des PNJ pour un niveau."""

    npcs: List[NPCConfig]  # Liste des PNJ

