# 3 - Système de fichier niveau pour positionnement du décor

## Contexte

Cette spécification définit un système de fichier de niveau permettant de configurer le décor d'un niveau de jeu. Le système permet de spécifier **plusieurs fichiers de sprite sources** dans un même niveau et d'associer chaque sprite à une couche de profondeur du système de parallaxe existant. Chaque ligne ou sprite individuel peut référencer le sprite sheet à utiliser, permettant une grande flexibilité dans la composition des niveaux.

## Objectifs

- Créer un format de fichier de niveau pour définir la configuration du décor
- Permettre de spécifier **plusieurs fichiers de sprite sources** dans un même niveau
- Permettre de référencer le sprite sheet à utiliser pour chaque ligne ou sprite individuel
- Associer chaque sprite du fichier source à une couche de profondeur (depth)
- Charger et interpréter les fichiers de niveau pour initialiser le système de parallaxe
- Faciliter la création et la modification des niveaux sans modifier le code

## Architecture

### Format de fichier

Le fichier de niveau utilise le format **TOML** (Tom's Obvious Minimal Language) pour sa lisibilité et sa facilité d'édition. Le fichier sera nommé avec l'extension `.niveau` ou `.toml`.

### Structure du fichier simplifiée

Un fichier de niveau contient :
- **Déclaration des sprite sheets** : une collection nommée de sprite sheets exploitables par le niveau
- **Mapping des lignes** (optionnel) : association entre chaque ligne d’un sprite sheet déclaré et une couche de profondeur
- **Mapping des sprites individuels** (optionnel) : association d'un sprite spécifique (sheet, row, col) avec répétition à une couche de profondeur

**Principe de simplicité** : 
- Chaque ligne du sprite sheet peut être associée à une profondeur. Tous les sprites d'une même ligne sont utilisés pour créer une couche de parallaxe (qui peut se répéter horizontalement selon le paramètre `is_infinite`).
- Un sprite individuel peut être spécifié avec ses coordonnées (row, col) et répété un nombre de fois défini pour créer des plateformes ou éléments spécifiques.

### Intégration avec le système de parallaxe

Le système de niveau s'intègre avec le `ParallaxSystem` existant :
- Chaque ligne du sprite sheet ou sprite individuel défini dans le fichier de niveau est chargé et ajouté comme une `Layer`
- Les couches sont automatiquement configurées avec leur profondeur (depth) et vitesse de défilement (scroll_speed) selon des valeurs par défaut
- Le système respecte les 4 niveaux de profondeur définis dans la spécification 1
- Les sprites individuels peuvent être répétés pour créer des plateformes ou éléments de décor spécifiques
- **Ordre de rendu** : Les couches de depth 0 et 1 sont rendues derrière le joueur, tandis que les couches de depth 2 et 3 sont rendues devant le joueur (voir section "Ordre de rendu par rapport au joueur")

## Spécifications techniques

### Structure des données

#### Classe `SpriteSheetConfig`

```python
@dataclass
class SpriteSheetConfig:
    """Décrit un sprite sheet exploitable par le niveau."""
    name: str  # Identifiant unique (clé utilisée dans le fichier .niveau)
    path: Path  # Chemin vers le fichier sprite sheet
    sprite_width: int  # Largeur d'un sprite individuel
    sprite_height: int  # Hauteur d'un sprite individuel
    spacing: float = 0.0  # Espacement horizontal par défaut appliqué aux couches utilisant ce sheet
```

#### Classe `LevelConfig`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

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
    initial_alpha: int = 255  # Opacité initiale de la couche (0-255, optionnel, défaut: 255 = complètement opaque). Permet de définir une couche qui commence invisible (0) et peut être affichée via un événement sprite_show (voir spécification 11).
    tags: List[str] = None  # Liste de tags pour identifier cette couche (optionnel, défaut: liste vide)

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
    initial_alpha: int = 255  # Opacité initiale du sprite (0-255, optionnel, défaut: 255 = complètement opaque). Permet de définir un sprite qui commence invisible (0) et peut être affiché via un événement sprite_show (voir spécification 11).
    tags: List[str] = None  # Liste de tags pour identifier cette couche (optionnel, défaut: liste vide)

@dataclass
class LevelConfig:
    """Configuration complète d'un niveau."""
    sprite_sheets: Dict[str, SpriteSheetConfig]  # Sprite sheets disponibles indexés par nom
    rows: List[RowMapping]  # Liste des lignes et leur profondeur associée
    sprites: List[SpriteMapping]  # Liste des sprites individuels et leur configuration
```

#### Classe `LevelLoader`

```python
class LevelLoader:
    """Chargeur de fichiers de niveau."""
    
    def __init__(self, assets_dir: Path) -> None:
        """
        Args:
            assets_dir: Répertoire de base pour les ressources
        """
    
    def load_level(self, level_path: Path) -> LevelConfig:
        """Charge un fichier de niveau.
        
        Args:
            level_path: Chemin vers le fichier .niveau ou .toml
            
        Returns:
            Configuration du niveau chargée
            
        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            ValueError: Si le format du fichier est invalide
        """
    
    def create_parallax_layers(
        self,
        level_config: LevelConfig,
        screen_width: int,
        screen_height: int
    ) -> tuple[ParallaxSystem, Dict[str, List[Layer]]]:
        """Crée un système de parallaxe à partir d'une configuration de niveau.
        
        Pour chaque ligne définie dans la config, extrait tous les sprites de la ligne,
        les concatène horizontalement et crée une Layer avec la profondeur associée.
        
        Pour chaque sprite individuel défini, extrait le sprite spécifique et le répète
        le nombre de fois indiqué pour créer une Layer.
        
        Crée également un dictionnaire de mapping par tag permettant de récupérer les
        couches associées à un tag donné. Ce mapping est utilisé par le système d'événements
        pour localiser et manipuler les sprites (par exemple, les masquer, les afficher
        ou déclencher un déplacement `sprite_move`).
        
        Args:
            level_config: Configuration du niveau
            screen_width: Largeur de l'écran
            screen_height: Hauteur de l'écran
            
        Returns:
            Tuple contenant :
            - Système de parallaxe configuré avec les couches du niveau
            - Dictionnaire de mapping par tag : {tag: [liste des layers avec ce tag]}
        """

### Règles de construction des surfaces (perf)

- Les surfaces générées pour une layer sont **serrées autour de leurs sprites** : on ne préremplit plus de grands rectangles transparents pour atteindre `x_offset`.  
- La position monde réelle est stockée dans `world_x_offset` (et appliquée aussi aux layers répétées) ; la largeur de la surface correspond uniquement au bounding box des sprites.  
- But : éviter de bliter, dès x=0, des surfaces géantes contenant surtout du vide pour des décors lointains (x >> 0), ce qui dégradait les FPS en début de niveau.
- Pour les couches répétées (`repeat/is_infinite`), l'ancrage tient compte de `world_x_offset` : le motif est positionné en monde via `(world_x_offset - offset_x) % effective_width - effective_width` afin d'éviter les gaps et les disparitions/flash visuels en bord d'écran.
```

### Format TOML du fichier de niveau

#### Déclaration des sprite sheets

Les sprite sheets sont déclarés dans la section `[sprite_sheets]`. Chaque sprite sheet a un nom unique qui sera utilisé pour le référencer dans les définitions de `[layers]` et `[[sprites]]`.

```toml
# Déclaration de plusieurs sprite sheets
[sprite_sheets.ground]
path = "sprite/terrain-montage.png"
sprite_width = 64
sprite_height = 64
spacing = -20  # Espacement par défaut pour ce sprite sheet

[sprite_sheets.decor]
path = "sprite/decor-complements.png"
sprite_width = 128
sprite_height = 128
spacing = 0.0  # Espacement par défaut pour ce sprite sheet

[sprite_sheets.clouds]
path = "sprite/nuage.png"
sprite_width = 64
sprite_height = 64
spacing = 0.0
```

**Champs de `[sprite_sheets.<nom>]`** :
- `path` (obligatoire) : Chemin vers le fichier sprite sheet (relatif à la racine du projet ou absolu)
- `sprite_width` (obligatoire) : Largeur d'un sprite individuel en pixels
- `sprite_height` (obligatoire) : Hauteur d'un sprite individuel en pixels
- `spacing` (optionnel, défaut: 0.0) : Espacement horizontal par défaut appliqué aux couches utilisant ce sprite sheet

#### Format avec lignes complètes

```toml
# Déclaration des sprite sheets
[sprite_sheets.ground]
path = "sprite/terrain-montage.png"
sprite_width = 64
sprite_height = 64
spacing = -20

[sprite_sheets.decor]
path = "sprite/decor-complements.png"
sprite_width = 128
sprite_height = 128

# Définition des couches avec référence au sprite sheet
[[layers]]
sheet = "ground"  # Référence au sprite sheet "ground"
row = 0
depth = 0
spacing = 0.0
is_infinite = false

[[layers]]
sheet = "ground"
row = 1
depth = 1

[[layers]]
sheet = "decor"
row = 2
depth = 3
spacing = -4.0
```

#### Format avec sprites individuels

```toml
# Déclaration des sprite sheets
[sprite_sheets.ground]
path = "sprite/terrain-montage.png"
sprite_width = 64
sprite_height = 64
spacing = -20

[sprite_sheets.decor]
path = "sprite/decor-complements.png"
sprite_width = 128
sprite_height = 128

# Définition des sprites avec référence au sprite sheet
[[sprites]]
sheet = "ground"  # Identifiant du sprite sheet à utiliser
row = 2
col = 2
depth = 2
count_x = 30
y_offset = 600.0
x_offset = 0.0
spacing = 0.0
infinite_offset = 0.0
is_infinite = false

[[sprites]]
sheet = "decor"
row = 0
col = 1
depth = 3
count_x = 1
y_offset = 420.0
x_offset = -32.0
infinite_offset = 0.0
is_infinite = false
```

#### Format de compatibilité (un seul sprite sheet)

Pour la rétrocompatibilité, le format avec un seul sprite sheet est toujours supporté :

```toml
# Format simplifié pour un seul sprite sheet (rétrocompatibilité)
[sprite_sheet]
path = "sprite/terrain-montage.png"
sprite_width = 64
sprite_height = 64
spacing = -20

# Dans ce cas, le sprite sheet par défaut est utilisé automatiquement
[[sprites]]
row = 1
col = 1
depth = 2
count_x = 30
y_offset = 600.0
```

**Note** : Si `[sprite_sheet]` (singulier) est utilisé au lieu de `[sprite_sheets]` (pluriel), le système crée automatiquement un sprite sheet nommé `"default"` qui est utilisé par défaut pour toutes les définitions qui ne spécifient pas de `sheet`.

**Explication** :

**Ordre de rendu** : Les couches de depth 0 et 1 sont rendues **derrière le joueur**, tandis que les couches de depth 2 et 3 sont rendues **devant le joueur**. Cela permet de créer un effet de profondeur où certains éléments de décor passent devant le personnage.

- La section `[sprite_sheets]` (pluriel) permet de déclarer plusieurs sprite sheets avec des noms uniques
  - Chaque sprite sheet est déclaré avec `[sprite_sheets.<nom>]` où `<nom>` est un identifiant unique
  - Chaque sprite sheet définit :
    - `path` (obligatoire) : Chemin vers le fichier image
    - `sprite_width` (obligatoire) : Largeur d'un sprite individuel
    - `sprite_height` (obligatoire) : Hauteur d'un sprite individuel
    - `spacing` (optionnel, défaut: 0.0) : Espacement par défaut appliqué aux couches utilisant ce sprite sheet
      - Valeur négative (ex: `-20`) : Fait chevaucher les sprites pour masquer les bordures/lignes noires
      - Valeur positive : Ajoute de l'espace entre les sprites
      - Ce spacing peut être surchargé par le `spacing` spécifique défini dans `[[layers]]` ou `[[sprites]]`
- La section `[sprite_sheet]` (singulier, rétrocompatibilité) permet de définir un seul sprite sheet par défaut
  - Si cette section est utilisée, un sprite sheet nommé `"default"` est créé automatiquement
  - Toutes les définitions de `[[layers]]` et `[[sprites]]` qui ne spécifient pas de `sheet` utilisent ce sprite sheet par défaut
- La section `[[layers]]` (optionnelle) permet de définir des couches à partir de lignes complètes
  - Chaque entrée doit spécifier :
    - `sheet` (obligatoire si plusieurs sprite sheets sont déclarés) : Nom du sprite sheet à utiliser
    - `row` (obligatoire) : Numéro de ligne dans le sprite sheet (0-indexed)
    - `depth` (obligatoire) : Profondeur de la couche (0-3)
    - `spacing` (optionnel) : Espacement horizontal entre les sprites lors de la concaténation
      - Si non spécifié, utilise le `spacing` défini dans le sprite sheet
    - `is_infinite` (optionnel, défaut: `true`) : Si la couche se répète horizontalement à l'infini
    - `is_background` (optionnel, défaut: `false`) : Si `true`, la couche s'affiche derrière le joueur et n'a pas de collision. **Uniquement applicable pour depth 2**. Permet de créer des décors à depth 2 qui ne bloquent pas le joueur et s'affichent derrière lui, tout en conservant la même vitesse de défilement que les autres éléments de depth 2 (scroll_speed = 1.0).
    - `is_foreground` (optionnel, défaut: `false`) : Si `true`, la couche s'affiche devant les autres éléments de depth 2 et n'a pas de collision. **Uniquement applicable pour depth 2**. Permet de créer des décors à depth 2 qui passent devant les plateformes de depth 2 mais restent devant le joueur, tout en conservant la même vitesse de défilement que les autres éléments de depth 2 (scroll_speed = 1.0).
    - `is_climbable` (optionnel, défaut: `false`) : Si `true`, la couche peut être grimpée par le joueur. **Uniquement applicable pour depth 2 avec `is_background = true`**. Quand le joueur est sur un bloc grimpable, la flèche du haut permet de grimper verticalement au lieu de sauter. Le joueur peut grimper jusqu'à ce qu'il soit sorti du bloc grimpable. S'applique à tous les types de sprites (quand on utilise `count_x` et `count_y`).
    - `initial_alpha` (optionnel, défaut: `255`) : Opacité initiale de la couche (0-255)
      - `255` : Complètement opaque (visible par défaut)
      - `0` : Complètement transparent (invisible par défaut)
      - Valeurs intermédiaires : Opacité partielle (ex: `128` = 50% d'opacité)
      - Permet de définir une couche qui commence invisible et peut être affichée via un événement `sprite_show` (voir spécification 11)
      - Si `initial_alpha = 0`, les collisions sont désactivées par défaut (même comportement qu'une couche masquée via `sprite_hide`)
      - L'opacité peut être modifiée dynamiquement via les événements `sprite_hide` et `sprite_show`
    - `tags` (optionnel) : Liste de tags pour identifier cette couche (utilisé par le système d'événements)
      - Format : `tags = ["tag1", "tag2"]` ou `tags = ["tag1"]`
      - Permet de regrouper plusieurs couches sous un même tag pour les manipuler ensemble
      - Exemple : `tags = ["obstacle", "removable"]` pour marquer un obstacle qui peut être supprimé
      - Ces tags sont exploités pour déclencher `sprite_hide`, `sprite_show` ou encore les déplacements `sprite_move` (plateformes mobiles)
  - Tous les sprites d'une ligne sont concaténés horizontalement pour créer une couche
- La section `[[sprites]]` (optionnelle) permet de définir des sprites individuels
  - Chaque entrée doit spécifier :
    - `sheet` (obligatoire si plusieurs sprite sheets sont déclarés) : Nom du sprite sheet à utiliser
    - `row` (obligatoire) : Numéro de ligne dans le sprite sheet (0-indexed)
    - `col` (obligatoire) : Numéro de colonne dans le sprite sheet (0-indexed)
    - `depth` (obligatoire) : Profondeur de la couche (0-3)
    - `count_x` (obligatoire) : Nombre de répétitions du sprite horizontalement
    - `first_sprite_row` (optionnel) : Ligne du sprite sheet pour le premier sprite (0-indexed). **Uniquement applicable lorsque `count_x > 3`**. Si non spécifié, utilise le `row` de base. Permet de définir un sprite différent pour le premier élément de la séquence horizontale.
    - `first_sprite_col` (optionnel) : Colonne du sprite sheet pour le premier sprite (0-indexed). **Uniquement applicable lorsque `count_x > 3`**. Si non spécifié, utilise le `col` de base. Permet de définir un sprite différent pour le premier élément de la séquence horizontale.
    - `last_sprite_row` (optionnel) : Ligne du sprite sheet pour le dernier sprite (0-indexed). **Uniquement applicable lorsque `count_x > 3`**. Si non spécifié, utilise le `row` de base. Permet de définir un sprite différent pour le dernier élément de la séquence horizontale.
    - `last_sprite_col` (optionnel) : Colonne du sprite sheet pour le dernier sprite (0-indexed). **Uniquement applicable lorsque `count_x > 3`**. Si non spécifié, utilise le `col` de base. Permet de définir un sprite différent pour le dernier élément de la séquence horizontale.
    - `count_y` (optionnel, défaut: 1) : Nombre de répétitions du sprite verticalement vers le haut. Le sprite le plus bas est positionné à `y_offset`, et les sprites suivants sont empilés vers le haut avec un espacement de `spacing_y` entre chaque répétition.
    - `y_offset` (optionnel, défaut: 0.0) : Position verticale du sprite le plus bas en pixels depuis le haut de l'écran. Si `count_y > 1`, les sprites suivants sont empilés vers le haut.
    - `x_offset` (optionnel, défaut: 0.0) : Offset horizontal pour corriger le spacing
    - `spacing` (optionnel) : Espacement horizontal entre chaque sprite lors de la répétition initiale
      - Si non spécifié, utilise le `spacing` défini dans le sprite sheet
      - Utilisé pour l'espacement entre les `count_x` sprites de la couche de base
      - Si `is_infinite = false` : Utilisé pour l'espacement entre les `count_x` répétitions du sprite
      - Si `is_infinite = true` : Utilisé pour l'espacement entre les `count_x` sprites de la couche de base (avant la répétition infinie)
    - `spacing_y` (optionnel, défaut: 0.0) : Espacement vertical entre chaque répétition du sprite vers le haut (en pixels)
      - **Ajustement par le scale** : Le `spacing_y` est d'abord multiplié par le `scale` du sprite dans le repère 1920x1080, puis converti vers 1280x720 : `spacing_y_final = (spacing_y * scale) * scale_y`
      - Si `spacing_y = 0.0` : les sprites sont empilés verticalement sans espacement (collés les uns aux autres)
      - Si `spacing_y > 0.0` : un espace de `spacing_y_final` pixels est ajouté entre chaque sprite verticalement
      - Si `spacing_y < 0.0` : les sprites se chevauchent verticalement de `|spacing_y_final|` pixels (utile pour masquer les lignes noires/bordures du sprite sheet)
      - La position verticale de chaque sprite répété est : `y_offset_final - j * (hauteur_effective + spacing_y_final)` où `j` va de 0 (sprite le plus bas) à `count_y - 1` (sprite le plus haut)
    - `infinite_offset` (optionnel, défaut: 0.0) : Distance entre chaque répétition infinie (en pixels)
      - **Uniquement applicable lorsque `is_infinite = true`** : Définit la distance entre chaque répétition de la couche infinie
      - Si `is_infinite = true` : La couche se répète à l'infini avec un espacement de `infinite_offset` pixels entre chaque répétition
      - Si `is_infinite = false` : Ce paramètre est ignoré, la répétition est gérée par `count_x` et `spacing`
      - Utile pour créer des couches infinies avec un espacement personnalisé entre les répétitions
    - `is_infinite` (optionnel, défaut: `true`) : Si la couche se répète horizontalement à l'infini
    - `scale` (optionnel, défaut: 1.0) : Facteur de redimensionnement du sprite (en pourcentage)
      - `scale = 1.0` : Taille originale (100%)
      - `scale = 0.5` : Taille réduite à 50%
      - `scale = 1.5` : Taille agrandie à 150%
      - Le redimensionnement est appliqué proportionnellement (largeur et hauteur)
      - Lorsqu'un redimensionnement est appliqué, le système ajuste automatiquement la position verticale pour conserver la même position du bas que la taille originale (`y_offset` continue de représenter la position du haut du sprite)
      - **Ajustement des espacements** : Le `spacing` et `infinite_offset` sont automatiquement multipliés par le `scale` pour maintenir les proportions visuelles. Le `x_offset` n'est PAS ajusté car c'est un décalage absolu en pixels. Par exemple, si `spacing = -20` dans le sprite_sheet et `scale = 0.5`, le spacing effectif sera `-10` pixels.
    - `is_background` (optionnel, défaut: `false`) : Si `true`, la couche s'affiche derrière le joueur et n'a pas de collision. **Uniquement applicable pour depth 2**. Permet de créer des décors à depth 2 qui ne bloquent pas le joueur et s'affichent derrière lui, tout en conservant la même vitesse de défilement que les autres éléments de depth 2 (scroll_speed = 1.0).
    - `is_foreground` (optionnel, défaut: `false`) : Si `true`, la couche s'affiche devant les autres éléments de depth 2 et n'a pas de collision. **Uniquement applicable pour depth 2**. Permet de créer des décors à depth 2 qui passent devant les plateformes de depth 2 mais restent devant le joueur, tout en conservant la même vitesse de défilement que les autres éléments de depth 2 (scroll_speed = 1.0).
    - `is_climbable` (optionnel, défaut: `false`) : Si `true`, la couche peut être grimpée par le joueur. **Uniquement applicable pour depth 2 avec `is_background = true`**. Quand le joueur est sur un bloc grimpable, la flèche du haut permet de grimper verticalement au lieu de sauter. Le joueur peut grimper jusqu'à ce qu'il soit sorti du bloc grimpable. S'applique à tous les types de sprites (quand on utilise `count_x` et `count_y`).
    - `initial_alpha` (optionnel, défaut: `255`) : Opacité initiale de la couche (0-255)
      - `255` : Complètement opaque (visible par défaut)
      - `0` : Complètement transparent (invisible par défaut)
      - Valeurs intermédiaires : Opacité partielle (ex: `128` = 50% d'opacité)
      - Permet de définir un sprite qui commence invisible et peut être affiché via un événement `sprite_show` (voir spécification 11)
      - Si `initial_alpha = 0`, les collisions sont désactivées par défaut (même comportement qu'un sprite masqué via `sprite_hide`)
      - L'opacité peut être modifiée dynamiquement via les événements `sprite_hide` et `sprite_show`
    - `tags` (optionnel) : Liste de tags pour identifier cette couche (utilisé par le système d'événements)
      - Format : `tags = ["tag1", "tag2"]` ou `tags = ["tag1"]`
      - Permet de regrouper plusieurs couches sous un même tag pour les manipuler ensemble
      - Exemple : `tags = ["obstacle", "removable"]` pour marquer un obstacle qui peut être supprimé
      - Les tags sont utilisés par le système d'événements pour localiser et manipuler les sprites (par exemple, les masquer via un événement `sprite_hide`, les afficher via `sprite_show` ou les déplacer via `sprite_move`)
- Au moins une des sections `[[layers]]` ou `[[sprites]]` doit être présente
- Les vitesses de défilement sont automatiques selon la profondeur (voir tableau ci-dessous)

### Vitesses de défilement automatiques

Les vitesses de défilement sont automatiquement définies selon la profondeur :

| Depth | Scroll Speed | Description | Ordre de rendu |
|-------|--------------|-------------|----------------|
| 0 (Background) | 0.2 | Défile très lentement | **Derrière le joueur** |
| 1 (Premier fond) | 0.5 | Défile lentement | **Derrière le joueur** |
| 2 (Gameplay) | 1.0 | Défile à la vitesse de la caméra | **Devant le joueur** |
| 3 (Foreground) | 1.3 | Défile plus vite | **Devant le joueur** |

### Ordre de rendu par rapport au joueur

**Important** : L'ordre de rendu des couches par rapport au joueur est le suivant :

1. **Couches derrière le joueur** (rendues en premier) :
   - Depth 0 (Background) : Couche la plus éloignée, rendue en premier
   - Depth 1 (Premier fond) : Couche intermédiaire arrière, rendue après depth 0
   - **Depth 2 avec `is_background = true`** : Décors à depth 2 qui s'affichent derrière le joueur (rendus après depth 1, avant le joueur)

2. **Joueur** (rendu au milieu) :
   - Le personnage principal est rendu après les couches de depth 0, 1 et les couches de depth 2 avec `is_background = true`

3. **Couches devant le joueur** (rendues en dernier) :
   - **Depth 2 avec `is_background = false` et `is_foreground = false` (ou omis)** : Éléments de gameplay (plateformes, obstacles) qui passent devant le joueur et ont des collisions
   - **Depth 2 avec `is_foreground = true`** : Décors à depth 2 qui passent devant les autres éléments de depth 2 mais restent devant le joueur, sans collision (rendus après les plateformes normales)
   - **Depth 3** : Éléments de foreground qui passent devant le joueur (rendus en dernier)

**Note sur `is_background`** : Le paramètre `is_background` permet de créer des décors à depth 2 qui :
- S'affichent **derrière le joueur** (comme les couches de depth 0 et 1)
- N'ont **pas de collision** (le joueur peut les traverser)
- Conservent la **même vitesse de défilement** que les autres éléments de depth 2 (scroll_speed = 1.0)

**Note sur `is_foreground`** : Le paramètre `is_foreground` permet de créer des décors à depth 2 qui :
- S'affichent **devant les autres éléments de depth 2** (plateformes, obstacles normaux)
- Restent **devant le joueur** (comme tous les éléments de depth 2 sans `is_background`)
- N'ont **pas de collision** (le joueur peut les traverser)
- Conservent la **même vitesse de défilement** que les autres éléments de depth 2 (scroll_speed = 1.0)

Cet ordre permet de créer un effet de profondeur réaliste où certains éléments de décor passent devant le joueur, créant une sensation de profondeur et d'immersion, tout en permettant d'avoir des décors à depth 2 qui peuvent être derrière le joueur (`is_background = true`), devant le joueur comme plateformes normales (`is_background = false` et `is_foreground = false`), ou devant les plateformes mais toujours devant le joueur (`is_foreground = true`).

### Construction des couches

#### Pour les lignes complètes (`[[layers]]`) :
1. Identifier le sprite sheet à utiliser via le champ `sheet` (ou utiliser le sprite sheet par défaut si non spécifié)
2. Extraire tous les sprites de la ligne (de gauche à droite) depuis le sprite sheet identifié
3. Les concaténer horizontalement en appliquant le `spacing` entre chaque sprite
   - Si un `spacing` est défini dans la configuration de la ligne, il est utilisé (surcharge le spacing par défaut)
   - Sinon, le `spacing` défini dans le sprite sheet est utilisé (par défaut: 0.0)
   - Si `spacing = 0.0` : les sprites sont collés les uns aux autres
   - Si `spacing > 0.0` : un espace de `spacing` pixels est ajouté entre chaque sprite
   - Si `spacing < 0.0` : les sprites se chevauchent de `|spacing|` pixels (utile pour masquer les lignes noires/bordures du sprite sheet)
4. Créer une `Layer` avec cette image, la profondeur associée et la vitesse de défilement correspondante
   - Le paramètre `is_infinite` est mappé vers le paramètre `repeat` de la classe `Layer` (définie dans la spécification 1)
   - **Gestion de `initial_alpha`** : Si la ligne définit `initial_alpha`, la couche créée reçoit un attribut `alpha` initialisé à cette valeur (0-255). Si `initial_alpha = 0`, la couche commence invisible et les collisions sont désactivées par défaut (même comportement qu'une couche masquée via `sprite_hide`). Si `initial_alpha` n'est pas spécifié, la valeur par défaut est `255` (complètement opaque). L'opacité peut être modifiée dynamiquement via les événements `sprite_hide` et `sprite_show` (voir spécification 11).
5. La couche se répète horizontalement selon le paramètre `is_infinite` (défaut: `True`)
   - Si `is_infinite = true` : La couche se répète horizontalement à l'infini
   - Si `is_infinite = false` : La couche ne se répète pas, elle s'affiche une seule fois

#### Pour les sprites individuels (`[[sprites]]`) :
1. Identifier le sprite sheet à utiliser via le champ `sheet` (ou utiliser le sprite sheet par défaut si non spécifié)
2. Extraire le sprite spécifique aux coordonnées (row, col) depuis le sprite sheet identifié
3. Appliquer le redimensionnement si `scale` est différent de 1.0 :
   - **IMPORTANT** : Le scale doit être appliqué DANS le repère de conception (1920x1080), puis le résultat est converti vers la résolution interne (1280x720).
   - **Étape 1 - Application du scale dans le repère 1920x1080** :
     - Calculer la nouvelle taille dans le repère 1920x1080 : `scaled_width = sprite_width * scale`, `scaled_height = sprite_height * scale`
     - Ajuster les valeurs d'espacement par le scale : `spacing_scaled = spacing * scale`, `infinite_offset_scaled = infinite_offset * scale`
     - Le `x_offset` : **N'est PAS ajusté par le scale** - c'est un décalage absolu en pixels dans l'espace du monde
     - Calculer la nouvelle position du haut pour conserver la même position du bas : `scaled_y_offset = y_offset + sprite_height - scaled_height`
   - **Étape 2 - Conversion vers la résolution interne 1280x720** :
     - Convertir les dimensions : `new_width = int(scaled_width * scale_x)`, `new_height = int(scaled_height * scale_y)`
     - Convertir les positions et espacements : `spacing_final = spacing_scaled * scale_x`, `infinite_offset_final = infinite_offset_scaled * scale_x`, `y_offset_final = scaled_y_offset * scale_y`
     - Redimensionner le sprite avec `pygame.transform.smoothscale()` en utilisant `new_width` et `new_height`
   - Le `y_offset` continue de représenter la position du **haut** du sprite dans le repère 1920x1080, mais est ajusté pour conserver la position du bas lors de l'application du scale.
4. Répéter le sprite verticalement selon `count_y` :
   - Le sprite le plus bas est positionné à `y_offset` (converti vers la résolution interne)
   - Les sprites suivants sont empilés vers le haut avec un espacement de `spacing_y` entre chaque répétition
   - **Ajustement par le scale** : Le `spacing_y` est d'abord multiplié par le `scale` du sprite dans le repère 1920x1080, puis converti vers 1280x720 : `spacing_y_final = (spacing_y * scale) * scale_y`
   - La hauteur effective utilisée dans les calculs est `(sprite_height * scale) * scale_y`
   - Pour chaque répétition verticale `j` (de 0 à `count_y - 1`, où 0 est le sprite le plus bas) :
     - Position verticale : `y_offset_final - j * (hauteur_effective + spacing_y_final)`
     - Le sprite le plus bas (`j = 0`) est à `y_offset_final`
     - Les sprites suivants sont empilés vers le haut, chaque sprite étant positionné `(hauteur_effective + spacing_y_final)` pixels au-dessus du précédent
   - **Gestion des collisions** : Chaque sprite répété verticalement génère ses propres rectangles de collision. Le système de collisions détecte et résout les collisions avec tous les sprites répétés verticalement, permettant au joueur d'interagir avec chaque bloc individuellement (par exemple, marcher sur le bloc du bas, sauter sur le bloc du milieu, etc.)

5. Répéter le sprite horizontalement selon `count_x` et `is_infinite` :
   
   **Si `is_infinite = false`** :
   - Répéter le sprite `count_x` fois en appliquant le `spacing` entre chaque répétition
   - Si un `spacing` est défini dans la configuration du sprite, il est utilisé (surcharge le spacing par défaut)
   - Sinon, le `spacing` défini dans le sprite sheet est utilisé (par défaut: 0.0)
   - **Ajustement par le scale** : Le `spacing` est d'abord multiplié par le `scale` du sprite dans le repère 1920x1080, puis converti vers 1280x720 : `spacing_final = (spacing * scale) * scale_x`
   - Si `spacing_final = 0.0` : les sprites sont collés les uns aux autres
   - Si `spacing_final > 0.0` : un espace de `spacing_final` pixels est ajouté entre chaque sprite
   - Si `spacing_final < 0.0` : les sprites se chevauchent de `|spacing_final|` pixels (utile pour masquer les lignes noires/bordures du sprite sheet)
   - La position finale de chaque sprite répété est : `x_offset_final + i * (largeur_effective + spacing_final)`
     - Le `x_offset_final` est calculé comme `x_offset * scale_x` (décalage uniforme de tous les sprites, converti vers 1280x720, non ajusté par le scale du sprite)
     - Le `spacing_final` ajuste l'espacement fixe entre chaque sprite (ajusté par le scale puis converti)
     - **Note** : la largeur effective utilisée dans les calculs est `(sprite_width * scale) * scale_x`. Ainsi, lorsque `scale > 1.0`, la surface allouée et les positions tiennent compte de la taille agrandie pour éviter toute coupure du sprite. Le `spacing_final` est calculé proportionnellement au scale dans le repère 1920x1080, puis converti vers 1280x720, tandis que `x_offset` reste un décalage absolu converti directement.
   - Le `infinite_offset` est ignoré dans ce cas
   
   **Si `is_infinite = true`** :
   - Créer une surface avec le sprite répété `count_x` fois en appliquant le `spacing` entre chaque sprite (pour créer la largeur de base de la couche)
   - Le `spacing` est utilisé pour l'espacement entre les `count_x` sprites de la couche de base
   - **Ajustement par le scale** : Le `spacing` est d'abord multiplié par le `scale` du sprite dans le repère 1920x1080, puis converti vers 1280x720 : `spacing_final = (spacing * scale) * scale_x`
   - **Note** : la largeur effective utilisée dans les répétitions est `(sprite_width * scale) * scale_x`. Cela garantit que les sprites agrandis disposent de suffisamment d'espace sur la surface et ne sont pas coupés. Le `spacing_final` est calculé proportionnellement au scale dans le repère 1920x1080, puis converti vers 1280x720.
   - La couche de base (composée de `count_x` sprites avec `spacing_final` entre eux) se répète horizontalement à l'infini
   - Le `infinite_offset` définit la distance entre chaque répétition infinie de la couche de base
   - **Ajustement par le scale** : Le `infinite_offset` est d'abord multiplié par le `scale` du sprite dans le repère 1920x1080, puis converti vers 1280x720 : `infinite_offset_final = (infinite_offset * scale) * scale_x`
   - Si `infinite_offset_final = 0.0` : Les répétitions infinies de la couche de base sont collées les unes aux autres
   - Si `infinite_offset_final > 0.0` : Un espace de `infinite_offset_final` pixels est ajouté entre chaque répétition infinie de la couche de base
   - Si `infinite_offset_final < 0.0` : Les répétitions infinies de la couche de base se chevauchent de `|infinite_offset_final|` pixels
   
6. Créer une surface de la hauteur de l'écran et placer les sprites répétés aux positions calculées
   - Pour chaque répétition horizontale `i` (de 0 à `count_x - 1`) et chaque répétition verticale `j` (de 0 à `count_y - 1`) :
     - **Sélection du sprite à utiliser** (uniquement pour la répétition horizontale) :
       - Si `count_x > 3` :
         - Pour le premier sprite (`i = 0`) : Utiliser `first_sprite_row` et `first_sprite_col` si définis, sinon `row` et `col` de base
         - Pour les sprites intermédiaires (`1 <= i <= count_x - 2`) : Toujours utiliser `row` et `col` de base
         - Pour le dernier sprite (`i = count_x - 1`) : Utiliser `last_sprite_row` et `last_sprite_col` si définis, sinon `row` et `col` de base
       - Si `count_x <= 3` : Tous les sprites utilisent `row` et `col` de base (les paramètres `first_sprite_row/col` et `last_sprite_row/col` sont ignorés)
     - Position horizontale : `x_offset_final + i * (largeur_effective + spacing_final)`
     - Position verticale : `y_offset_final - j * (hauteur_effective + spacing_y_final)`
     - Extraire le sprite approprié du sprite sheet selon les coordonnées déterminées ci-dessus
     - Dessiner le sprite à cette position dans la surface de la couche
7. Créer une `Layer` avec cette image, la profondeur associée et la vitesse de défilement correspondante
   - Chaque layer générée reçoit un nom **unique** (index incrémental) afin de garantir que les caches internes (`_solid_rects_cache`) ne soient jamais partagés entre deux couches différentes, même si elles proviennent du même sprite (`row`/`col`). Cela évite que les rectangles de collision d'une plateforme réutilisent ceux d'une autre plateforme placée ailleurs.
   - Lorsqu'un sprite définit un `x_offset` négatif, le chargeur enregistre également un `world_x_offset` associé à la couche. Ce décalage est réutilisé par le système de collisions et de rendu pour positionner correctement les rectangles dans l'espace du monde au moment de la détection.
   - Le paramètre `is_infinite` est mappé vers le paramètre `repeat` de la classe `Layer` (définie dans la spécification 1)
   - Le paramètre `infinite_offset` est utilisé par le système de parallaxe pour gérer l'espacement entre les répétitions infinies
   - Le système de collisions réutilise également `infinite_offset` afin de positionner correctement les rectangles solides lors des répétitions infinies et éviter tout espace traversable
   - **Gestion de `is_background`** : Si le sprite définit `is_background = true`, la couche créée reçoit un attribut `is_background = True`. Ce flag est utilisé par le système de rendu pour déterminer l'ordre d'affichage (derrière ou devant le joueur) et par le système de collisions pour exclure ces couches des détections de collision. **Important** : `is_background` n'est applicable que pour depth 2. Pour les autres depths, ce paramètre est ignoré.
   - **Gestion de `is_foreground`** : Si le sprite définit `is_foreground = true`, la couche créée reçoit un attribut `is_foreground = True`. Ce flag est utilisé par le système de rendu pour déterminer l'ordre d'affichage (devant les autres éléments de depth 2) et par le système de collisions pour exclure ces couches des détections de collision. **Important** : `is_foreground` n'est applicable que pour depth 2. Pour les autres depths, ce paramètre est ignoré. **Note** : `is_background` et `is_foreground` sont mutuellement exclusifs pour depth 2. Si les deux sont définis à `true`, `is_background` a la priorité.
   - **Gestion de `is_climbable`** : Si le sprite définit `is_climbable = true`, la couche créée reçoit un attribut `is_climbable = True`. Ce flag est utilisé par le système de collisions pour détecter si le joueur est sur un bloc grimpable, et par le système de contrôle du joueur pour permettre la grimpe au lieu du saut. **Important** : `is_climbable` n'est applicable que pour depth 2 avec `is_background = true`. Pour les autres configurations, ce paramètre est ignoré. Si `is_background = false`, `is_climbable` est ignoré même s'il est défini à `true`.
   - **Gestion des tags** : Si le sprite définit des `tags`, la couche créée est enregistrée dans un dictionnaire de mapping par tag. Ce mapping permet au système d'événements de localiser rapidement toutes les couches associées à un tag donné (par exemple, pour les masquer via un événement `sprite_hide`, les afficher via `sprite_show` ou les déplacer via `sprite_move`).
   - **Gestion de `initial_alpha`** : Si le sprite définit `initial_alpha`, la couche créée reçoit un attribut `alpha` initialisé à cette valeur (0-255). Si `initial_alpha = 0`, la couche commence invisible et les collisions sont désactivées par défaut (même comportement qu'un sprite masqué via `sprite_hide`). Si `initial_alpha` n'est pas spécifié, la valeur par défaut est `255` (complètement opaque). L'opacité peut être modifiée dynamiquement via les événements `sprite_hide` et `sprite_show` (voir spécification 11).
8. La couche se répète horizontalement selon le paramètre `is_infinite` (défaut: `True`)
   - Si `is_infinite = true` : La couche se répète horizontalement à l'infini avec un espacement de `infinite_offset` pixels entre chaque répétition
   - Si `is_infinite = false` : La couche ne se répète pas, elle s'affiche une seule fois avec `count_x` répétitions du sprite

### Adaptation à la résolution interne

- Les fichiers `.niveau` restent exprimés dans le repère historique **1920x1080** (valeurs `x_offset`, `y_offset`, `spacing`, `spacing_y`, `infinite_offset`, etc.).
- Les fichiers `.pnj` (positions `x` des PNJ, `position_min` et `position_max` des blocs de dialogue) et `.event` (`trigger_x`, `target_x`, `move_speed`) sont également exprimés dans le repère **1920x1080**.
- Lors du chargement, le moteur convertit toutes ces valeurs vers la surface de rendu interne **1280x720** en appliquant les facteurs issus de `compute_design_scale()`.
- **Ordre d'application du scale des sprites** : Le paramètre `scale` des sprites doit être appliqué **DANS le repère de conception (1920x1080)**, puis le résultat est converti vers la résolution interne (1280x720). Cela signifie :
  1. **Étape 1** : Appliquer le `scale` du sprite dans le repère 1920x1080 (ex: `spacing_scaled = spacing * scale`)
  2. **Étape 2** : Convertir le résultat vers la résolution interne 1280x720 (ex: `spacing_final = spacing_scaled * scale_x`)
  3. Le sprite lui-même est redimensionné avec le facteur combiné : `scale * scale_x/scale_y`
- Cette conversion garantit que les positions, espacements et collisions demeurent cohérents quelle que soit la résolution réelle de la fenêtre.

#### Création du mapping par tag

Lors de la création des couches, le chargeur construit également un dictionnaire de mapping par tag :

- Pour chaque sprite ou layer défini avec des `tags`, chaque tag est ajouté au dictionnaire
- Le dictionnaire a la structure : `{tag: [liste des layers avec ce tag]}`
- Une même couche peut être associée à plusieurs tags (elle apparaîtra dans plusieurs listes)
- Ce mapping est retourné par `create_parallax_layers()` et utilisé par le système d'événements pour localiser les sprites à manipuler

## Implémentation

### Structure de fichiers

```
src/moteur_jeu_presentation/
├── levels/
│   ├── __init__.py
│   ├── loader.py          # Classe LevelLoader
│   └── config.py          # Classes LevelConfig et SpriteMapping
├── levels/                # Répertoire des fichiers de niveau
│   ├── niveau_montagne.niveau
│   └── niveau_plateforme.niveau
```

### Dépendances

Le système nécessite une bibliothèque TOML pour Python :
- `tomli` pour Python < 3.11
- `tomllib` (intégré) pour Python >= 3.11

**Note** : Pour la compatibilité, utiliser `tomli` qui fonctionne sur toutes les versions Python supportées.

### Exemple d'utilisation

```python
from pathlib import Path
from levels.loader import LevelLoader
from rendering.parallax import ParallaxSystem

# Initialisation
assets_dir = Path("sprite")
level_loader = LevelLoader(assets_dir)

# Charger un niveau
level_path = Path("levels/niveau_montagne.niveau")
level_config = level_loader.load_level(level_path)

# Créer le système de parallaxe et le mapping par tag
screen_width = 1280
screen_height = 720
parallax_system, layers_by_tag = level_loader.create_parallax_layers(
    level_config,
    screen_width,
    screen_height
)

# Dans la boucle de jeu
def update(dt: float, camera_x: float) -> None:
    parallax_system.update(camera_x, dt)

def draw(screen: pygame.Surface) -> None:
    screen.fill((0, 0, 0))
    
    # Dessiner les couches derrière le joueur (depth 0, 1, et depth 2 avec is_background = true)
    for layer in parallax_system._layers:
        if layer.depth <= 1 or (layer.depth == 2 and getattr(layer, 'is_background', False)):
            parallax_system._draw_layer(screen, layer)
    
    # Dessiner le joueur
    player.draw(screen, camera_x)
    
    # Dessiner les couches devant le joueur (depth 2 sans is_background ni is_foreground, puis depth 2 avec is_foreground, puis depth 3)
    for layer in parallax_system._layers:
        if layer.depth == 2 and not getattr(layer, 'is_background', False) and not getattr(layer, 'is_foreground', False):
            parallax_system._draw_layer(screen, layer)
    
    for layer in parallax_system._layers:
        if layer.depth == 2 and getattr(layer, 'is_foreground', False):
            parallax_system._draw_layer(screen, layer)
    
    for layer in parallax_system._layers:
        if layer.depth == 3:
            parallax_system._draw_layer(screen, layer)
```

### Gestion des erreurs

Le système doit gérer les erreurs suivantes :
- **Fichier introuvable** : Lever `FileNotFoundError` avec un message clair
- **Format invalide** : Lever `ValueError` avec indication de la ligne/section problématique
- **Sprite sheet introuvable** : Lever `FileNotFoundError` si le fichier image n'existe pas
- **Ligne invalide** : Vérifier que les numéros de ligne sont valides pour le sprite sheet
- **Depth invalide** : Vérifier que `depth` est entre 0 et 3

### Validation

Le système doit valider :
- Qu'au moins une section `[sprite_sheet]` ou `[sprite_sheets]` est présente
- Pour chaque sprite sheet déclaré :
  - Que tous les champs obligatoires sont présents (`path`, `sprite_width`, `sprite_height`)
  - Que `sprite_width` et `sprite_height` sont positifs
  - Que `spacing` est un nombre (int ou float) si présent
- Qu'au moins une section `[[layers]]` ou `[[sprites]]` est présente
- Pour chaque définition de `[[layers]]` :
  - Que `sheet` est présent si plusieurs sprite sheets sont déclarés (ou utilise le sprite sheet par défaut)
  - Que le `sheet` référencé existe dans les sprite sheets déclarés
  - Que `row` est présent et valide (>= 0 et < nombre de lignes dans le sprite sheet référencé)
  - Que `depth` est entre 0 et 3
  - Que `spacing` est un nombre (int ou float) si présent
  - Que `is_infinite` est un booléen si présent
  - Que `is_background` est un booléen si présent (uniquement applicable pour depth 2, ignoré pour les autres depths)
  - Que `is_foreground` est un booléen si présent (uniquement applicable pour depth 2, ignoré pour les autres depths)
  - Que `is_climbable` est un booléen si présent (uniquement applicable pour depth 2 avec `is_background = true`, ignoré pour les autres configurations)
  - Que `initial_alpha` est un entier entre 0 et 255 si présent (défaut: 255)
  - Que `tags` est une liste de chaînes de caractères si présent
- Pour chaque définition de `[[sprites]]` :
  - Que `sheet` est présent si plusieurs sprite sheets sont déclarés (ou utilise le sprite sheet par défaut)
  - Que le `sheet` référencé existe dans les sprite sheets déclarés
  - Que `row` et `col` sont présents et valides (>= 0 et < nombre de lignes/colonnes dans le sprite sheet référencé)
  - Que `depth` est entre 0 et 3
  - Que `count_x` est un entier positif
  - Que `count_y` est un entier positif si présent (défaut: 1)
  - Que `y_offset` est un nombre (int ou float) si présent
  - Que `x_offset` est un nombre (int ou float) si présent
  - Que `spacing` est un nombre (int ou float) si présent (utilisé pour l'espacement entre les `count_x` sprites de la couche de base)
  - Que `spacing_y` est un nombre (int ou float) si présent (utilisé pour l'espacement vertical entre les `count_y` répétitions du sprite)
  - Que `infinite_offset` est un nombre (int ou float) si présent (utilisé uniquement si `is_infinite = true` pour l'espacement entre les répétitions infinies)
  - Que `is_infinite` est un booléen si présent
  - Que `scale` est un nombre (int ou float) positif si présent (facteur de redimensionnement, doit être > 0)
  - Que `is_background` est un booléen si présent (uniquement applicable pour depth 2, ignoré pour les autres depths)
  - Que `is_foreground` est un booléen si présent (uniquement applicable pour depth 2, ignoré pour les autres depths)
  - Que `is_climbable` est un booléen si présent (uniquement applicable pour depth 2 avec `is_background = true`, ignoré pour les autres configurations)
  - Que `initial_alpha` est un entier entre 0 et 255 si présent (défaut: 255)
  - Que `tags` est une liste de chaînes de caractères si présent

**Messages d'erreur** : Le système affiche des messages d'erreur clairs indiquant :
- Le nombre de lignes/colonnes disponibles dans le sprite sheet
- Les indices valides (0 à n-1)
- La coordonnée invalide qui a été fournie

**Exemple d'erreur** : Si on essaie d'utiliser `row = 2` sur un sprite sheet avec 2 lignes :
```
ValueError: Ligne 2 invalide (sprite sheet a 2 lignes, index 0-1)
```

## Contraintes et considérations

### Performance et système de cache (voir spécification 17)

Le système de niveaux utilise une architecture de cache à deux niveaux pour optimiser les performances :

#### Cache global pour les sprite sheets

**`_global_level_sprite_sheet_cache`** (défini dans `assets/preloader.py`) :
- **Type** : `Dict[str, pygame.Surface]`
- **Clé** : nom du sprite sheet (str) tel que défini dans la configuration du niveau (ex: `"terrain"`, `"background"`)
- **Valeur** : Surface pygame du sprite sheet complet chargé avec `convert_alpha()`
- **Portée** : Partagé globalement, réutilisé pour tous les niveaux
- **Rempli par** : 
  - `AssetPreloader._preload_level_sprites()` au démarrage (préchargement automatique)
  - `LevelLoader.create_parallax_layers()` en fallback si le sprite sheet n'est pas préchargé
- **Utilisé par** : `LevelLoader.create_parallax_layers()` vérifie d'abord ce cache avant de charger depuis le disque

#### Cache local pour les sprites extraits et redimensionnés

**`scaled_sprite_cache`** (local à `create_parallax_layers()`) :
- **Type** : `Dict[Tuple[str, int, int, float], pygame.Surface]`
- **Clé** : `(sheet_name, row, col, scale)` pour identifier uniquement chaque sprite redimensionné
- **Valeur** : Surface pygame du sprite extrait et redimensionné
- **Portée** : Local au chargement d'un niveau (créé à chaque appel de `create_parallax_layers()`)
- **Utilité** : Évite les redimensionnements multiples du même sprite lors de la création des layers

#### Optimisations du chargement

- **Sprite sheets** : Chargés une seule fois via le cache global et réutilisés pour tous les sprites
- **Extraction** : Les sprites sont extraits une fois du sprite sheet lors du chargement du niveau
- **Redimensionnement** : Utilise `pygame.transform.smoothscale()` pour une meilleure qualité visuelle
- **Cache de redimensionnement** : Si plusieurs sprites utilisent le même `(sheet, row, col, scale)`, le redimensionnement n'est effectué qu'une seule fois
- **Conversion optimale** : Après le redimensionnement, les sprites sont convertis avec `convert_alpha()` pour optimiser le rendu pendant le jeu
- **Configurations** : Les configurations de niveau chargées peuvent être mises en cache si nécessaire

**Avantages** :
- ✅ Sprite sheets partagés globalement (pas de rechargement entre niveaux)
- ✅ Préchargement automatique via `AssetPreloader` (voir spec 17)
- ✅ Redimensionnement optimisé avec cache local
- ✅ Fallback transparent si le préchargement est désactivé

### Organisation des fichiers

- Les fichiers de niveau doivent être dans un répertoire dédié (ex: `levels/`)
- Les chemins dans les fichiers de niveau sont relatifs à la racine du projet (répertoire de travail courant)
- Les chemins absolus sont également supportés
- Recommandation : utiliser des chemins relatifs à la racine du projet pour la portabilité
- Exemple : `path = "sprite/terrain-montage.png"` résout vers `<racine_projet>/sprite/terrain-montage.png`

### Dimensions des sprites

- Tous les sprites d'un niveau doivent avoir les mêmes dimensions (`sprite_width x sprite_height`)
- Les sprites doivent être alignés sur une grille régulière dans le sprite sheet
- La hauteur des sprites (`sprite_height`) doit être >= `screen_height` pour les couches qui couvrent toute la hauteur
- Les sprites d'une même ligne sont automatiquement concaténés horizontalement pour former la couche

**Important** : Les coordonnées `row` et `col` dans les fichiers de niveau sont 0-indexées. Il faut vérifier les dimensions réelles du sprite sheet :
- Nombre de lignes = `hauteur_image / sprite_height`
- Nombre de colonnes = `largeur_image / sprite_width`
- Les indices valides vont de 0 à (nombre - 1)

**Exemple** : Si le sprite sheet fait 191x128 pixels avec des sprites de 64x64 :
- Nombre de lignes = 128 / 64 = 2 (indices valides : 0, 1)
- Nombre de colonnes = 191 / 64 = 2 (indices valides : 0, 1)
- Les coordonnées valides sont donc : row ∈ [0, 1] et col ∈ [0, 1]

**Note** : Le sprite sheet `terrain-montage.png` fait 191x128 pixels, donc avec des sprites de 64x64, il y a 2 lignes et 2 colonnes.

### Gestion mémoire

- Ne pas charger plusieurs fois le même sprite sheet
- Réutiliser les surfaces extraites pour les couches
- Libérer les ressources lors du changement de niveau

## Exemple de fichier de niveau complet

### Exemple avec plusieurs sprite sheets

```toml
# Fichier : levels/niveau_complet.niveau
# Niveau utilisant plusieurs sprite sheets

# Déclaration des sprite sheets
[sprite_sheets.ground]
path = "sprite/terrain-montage.png"
sprite_width = 64
sprite_height = 64
spacing = -20

[sprite_sheets.decor]
path = "sprite/decor-complements.png"
sprite_width = 128
sprite_height = 128
spacing = 0.0

[sprite_sheets.clouds]
path = "sprite/nuage.png"
sprite_width = 64
sprite_height = 64
spacing = 0.0

# Définition des couches avec référence aux sprite sheets
[[layers]]
sheet = "ground"
row = 0
depth = 0
spacing = 0.0
is_infinite = false

[[layers]]
sheet = "ground"
row = 1
depth = 1
is_infinite = false

[[layers]]
sheet = "clouds"
row = 0
depth = 0
is_infinite = true

# Définition des sprites individuels
[[sprites]]
sheet = "ground"
row = 1
col = 1
depth = 2
count_x = 70
y_offset = 600.0
spacing = 0.0
is_infinite = false

[[sprites]]
sheet = "decor"
row = 0
col = 1
depth = 3
count_x = 1
y_offset = 420.0
x_offset = -32.0
spacing = 0.0
is_infinite = false
```

### Exemple avec format simplifié (rétrocompatibilité)

```toml
# Fichier : levels/niveau_montagne.niveau
# Format simplifié avec un seul sprite sheet

[sprite_sheet]
path = "sprite/terrain-montage.png"
sprite_width = 64
sprite_height = 64

# Dans ce format, le sprite sheet par défaut est utilisé automatiquement
# Les définitions de layers et sprites n'ont pas besoin de spécifier "sheet"
[[layers]]
row = 0
depth = 0
spacing = 0.0
is_infinite = false

[[layers]]
row = 1
depth = 1

[[layers]]
row = 3
depth = 3
```

**Note** : La ligne 2 n'est pas définie car elle correspond à la couche de gameplay (depth 2) qui est généralement gérée séparément avec les entités du jeu (personnage, etc.).

### Exemple avec sprite individuel (plateforme)

```toml
# Fichier : levels/niveau_plateforme.niveau
# Niveau avec une plateforme devant le joueur (depth 2)

# Format simplifié avec un seul sprite sheet
[sprite_sheet]
path = "sprite/terrain-montage.png"
sprite_width = 64
sprite_height = 64
spacing = -20  # Espacement par défaut pour compenser les lignes noires du sprite sheet (optionnel, défaut: 0.0)
# Note: Utilisez une valeur négative (ex: -20) pour faire chevaucher les sprites et masquer les lignes noires/bordures

# Sprite unique répété 30 fois pour créer une plateforme
# Sprite à la colonne 1, ligne 1 (0-indexed, donc col=1, row=1)
# Note: Le sprite sheet terrain-montage.png fait 191x128 pixels
# Avec des sprites de 64x64: 2 lignes (0-1) et 2 colonnes (0-1)
# Profondeur 2 = couche de gameplay (devant le joueur, voir section "Ordre de rendu par rapport au joueur")
# y_offset = 600 pour positionner la plateforme en bas de l'écran (720px de hauteur)
# x_offset = 0.0 pour corriger le spacing horizontal si nécessaire
# Le spacing défini dans [sprite_sheet] s'applique automatiquement, mais peut être surchargé ici
# is_infinite = false pour que la plateforme ne se répète pas horizontalement (affiche count_x répétitions)
[[sprites]]
row = 1
col = 1
depth = 2
count_x = 30
y_offset = 600.0
x_offset = 0.0  # Offset horizontal optionnel pour corriger le spacing
# spacing = -20  # Optionnel : surcharge le spacing du sprite_sheet si nécessaire (utilisé uniquement si is_infinite = false)
is_infinite = false  # Optionnel : désactive la répétition horizontale infinie (défaut: true)
# scale = 1.0  # Optionnel : facteur de redimensionnement (1.0 = 100%, 0.5 = 50%, 1.5 = 150%, défaut: 1.0)
```

**Note** : Ce format permet de créer des plateformes ou éléments de décor spécifiques en répétant un sprite unique. La plateforme sera rendue à la profondeur 2 (couche de gameplay) et passera **devant le joueur** lors du rendu (voir section "Ordre de rendu par rapport au joueur"). Pour créer des plateformes sur lesquelles le joueur marche, utilisez plutôt la profondeur 1 (derrière le joueur) ou gérez les collisions séparément.

### Exemple avec répétition verticale (count_y)

```toml
# Fichier : levels/niveau_plateforme_verticale.niveau
# Exemple d'utilisation du paramètre count_y pour répéter un sprite verticalement

[sprite_sheet]
path = "sprite/terrain-montage.png"
sprite_width = 64
sprite_height = 64
spacing = -20

# Mur vertical : 5 blocs empilés vers le haut
# Le sprite le plus bas est à y_offset = 600, les suivants sont empilés vers le haut
[[sprites]]
row = 1
col = 1
depth = 2
count_x = 1
count_y = 5  # 5 blocs empilés verticalement
y_offset = 600.0  # Position du bloc le plus bas
spacing_y = 0.0  # Pas d'espacement vertical (blocs collés)
is_infinite = false

# Colonne de blocs avec espacement vertical
[[sprites]]
row = 1
col = 1
depth = 2
count_x = 1
count_y = 3  # 3 blocs empilés verticalement
y_offset = 500.0  # Position du bloc le plus bas
x_offset = 200.0
spacing_y = 10.0  # 10 pixels d'espacement entre chaque bloc
is_infinite = false

# Mur horizontal et vertical : 10 blocs horizontalement, 3 blocs verticalement
# Crée une structure en forme de L ou de mur
[[sprites]]
row = 1
col = 1
depth = 2
count_x = 10  # 10 blocs horizontalement
count_y = 3  # 3 blocs verticalement (empilés vers le haut)
y_offset = 600.0  # Position du bloc le plus bas
spacing = 0.0  # Pas d'espacement horizontal
spacing_y = 0.0  # Pas d'espacement vertical
is_infinite = false
```

**Explication de `count_y`** :
- Le paramètre `count_y` permet de répéter un sprite verticalement vers le haut
- Le sprite le plus bas est positionné à `y_offset` (dans le repère 1920x1080, converti vers 1280x720)
- Les sprites suivants sont empilés vers le haut avec un espacement de `spacing_y` entre chaque répétition
- **Gestion des collisions** : Chaque sprite répété verticalement génère ses propres rectangles de collision. Le joueur peut interagir avec chaque bloc individuellement (marcher sur le bloc du bas, sauter sur le bloc du milieu, etc.)
- **Combinaison avec `count_x`** : `count_y` peut être combiné avec `count_x` pour créer des structures 2D (murs, colonnes, plateformes empilées, etc.)
- **Ajustement par le scale** : Le `spacing_y` est automatiquement ajusté par le `scale` du sprite pour maintenir les proportions visuelles

### Exemple avec sprites personnalisés pour count_x > 3

```toml
# Fichier : levels/niveau_plateforme_extremites.niveau
# Exemple d'utilisation des paramètres first_sprite_row/col et last_sprite_row/col
# pour définir des extrémités différentes du corps de la plateforme

[sprite_sheet]
path = "sprite/terrain-montage.png"
sprite_width = 64
sprite_height = 64
spacing = -20

# Plateforme avec extrémités personnalisées
# Le premier sprite utilise row=1, col=0 (extrémité gauche)
# Les sprites intermédiaires utilisent row=1, col=1 (corps de la plateforme)
# Le dernier sprite utilise row=1, col=2 (extrémité droite)
[[sprites]]
row = 1        # Sprite de base pour le corps de la plateforme
col = 1
depth = 2
count_x = 10   # 10 sprites horizontalement (count_x > 3, donc les paramètres personnalisés sont applicables)
first_sprite_row = 1  # Extrémité gauche personnalisée
first_sprite_col = 0
last_sprite_row = 1   # Extrémité droite personnalisée
last_sprite_col = 2
y_offset = 600.0
is_infinite = false
```

**Explication des sprites personnalisés** :
- Les paramètres `first_sprite_row`, `first_sprite_col`, `last_sprite_row`, `last_sprite_col` sont **uniquement applicables lorsque `count_x > 3`**
- Si `count_x <= 3`, ces paramètres sont ignorés et tous les sprites utilisent `row` et `col` de base
- Le **premier sprite** (index 0) utilise `first_sprite_row` et `first_sprite_col` si définis, sinon `row` et `col` de base
- Les **sprites intermédiaires** (index 1 à `count_x - 2`) utilisent toujours `row` et `col` de base
- Le **dernier sprite** (index `count_x - 1`) utilise `last_sprite_row` et `last_sprite_col` si définis, sinon `row` et `col` de base
- Cette fonctionnalité permet de créer des structures visuellement plus variées, comme des plateformes avec des extrémités différentes du corps central
- Les sprites personnalisés doivent exister dans le même sprite sheet que le sprite de base
- Le `spacing` et les autres paramètres de positionnement s'appliquent de la même manière, indépendamment du sprite utilisé

### Exemple avec redimensionnement (scale)

```toml
# Fichier : levels/niveau_plateforme_redimensionnee.niveau
# Exemple d'utilisation du paramètre scale pour redimensionner un sprite

[sprite_sheet]
path = "sprite/terrain-montage.png"
sprite_width = 64
sprite_height = 64
spacing = -20

# Plateforme redimensionnée à 50% de sa taille originale
# Le bas du sprite reste à y_offset = 600, mais le sprite est plus petit
[[sprites]]
row = 1
col = 1
depth = 2
count_x = 30
y_offset = 600.0  # Le bas du sprite est à 600px du haut de l'écran
scale = 0.5  # Redimensionné à 50% (32x32 pixels au lieu de 64x64)
is_infinite = false

# Plateforme redimensionnée à 150% de sa taille originale
# Le bas du sprite reste à y_offset = 600, mais le sprite est plus grand
[[sprites]]
row = 1
col = 1
depth = 2
count_x = 20
y_offset = 600.0  # Le bas du sprite est à 600px du haut de l'écran
scale = 1.5  # Redimensionné à 150% (96x96 pixels au lieu de 64x64)
is_infinite = false
```

**Explication du redimensionnement** :
- Le paramètre `scale` permet de redimensionner le sprite proportionnellement
- `scale = 1.0` : Taille originale (100%)
- `scale = 0.5` : Taille réduite à 50% (largeur et hauteur divisées par 2)
- `scale = 1.5` : Taille agrandie à 150% (largeur et hauteur multipliées par 1.5)
- Le `y_offset` continue de représenter la position du **haut** du sprite dans le fichier de niveau
  - Si le sprite original fait 64px de haut et `y_offset = 600`, le bas est à `600 + 64 = 664px`
  - Si `scale = 0.5` (`new_height = 32`), l'implémentation positionne automatiquement le sprite pour conserver le bas à 664px (`haut = 664 - 32 = 632px`)
  - Si `scale = 1.5` (`new_height = 96`), le bas reste à 664px (`haut = 664 - 96 = 568px`)
- **Ajustement des espacements par le scale** : Lorsqu'un sprite est redimensionné (`scale != 1.0`), les valeurs d'espacement relatives sont automatiquement ajustées pour maintenir les proportions visuelles :
  - `spacing_effectif = spacing * scale` (où `spacing` vient du sprite ou du sprite_sheet par défaut)
  - `x_offset` : **N'est PAS ajusté par le scale** - c'est un décalage absolu en pixels dans l'espace du monde, utilisé pour positionner précisément les sprites à une position fixe
  - `infinite_offset_effectif = infinite_offset * scale`
  - Cela garantit que les espacements relatifs (`spacing`, `infinite_offset`) restent proportionnels à la taille du sprite redimensionné, tandis que le décalage absolu (`x_offset`) reste fixe pour permettre un positionnement précis
  - Exemple : Si `spacing = -20` dans le sprite_sheet et `scale = 0.5`, le spacing effectif sera `-10` pixels, ce qui maintient la même proportion visuelle de chevauchement
  - Exemple : Si `x_offset = 3300.0` et `scale = 1.7`, le x_offset reste `3300.0` pixels (non ajusté), permettant de positionner le sprite à une position absolue précise dans l'espace du monde
  - Le `spacing_effectif` s'ajoute à la largeur effective (`sprite_width * scale`). Lorsqu'un sprite est redimensionné, la surface générée tient compte de cette largeur agrandie, puis applique les espacements ajustés, ce qui évite que le sprite soit coupé tout en maintenant les proportions visuelles.

### Exemple avec infinite_offset (couche infinie avec espacement)

```toml
# Fichier : levels/niveau_infini.niveau
# Exemple d'utilisation de infinite_offset pour créer une couche infinie avec espacement

[sprite_sheet]
path = "sprite/terrain-montage.png"
sprite_width = 64
sprite_height = 64

# Créer une couche infinie avec un espacement de 100 pixels entre chaque répétition
# La couche se répète à l'infini avec un espacement personnalisé
[[sprites]]
row = 1
col = 1
depth = 2
count_x = 5  # 5 sprites pour créer la largeur de base de la couche
y_offset = 600.0
x_offset = 0.0
spacing = 0.0  # Espacement entre les 5 sprites de la couche de base
infinite_offset = 100.0  # Distance de 100 pixels entre chaque répétition infinie de la couche de base
is_infinite = true  # La couche se répète à l'infini

# Créer une couche infinie sans espacement (répétitions collées)
[[sprites]]
row = 0
col = 0
depth = 0
count_x = 3  # 3 sprites pour créer la largeur de base de la couche
y_offset = 0.0
x_offset = 0.0
spacing = 0.0  # Espacement entre les 3 sprites de la couche de base
infinite_offset = 0.0  # Pas d'espacement entre les répétitions infinies de la couche de base
is_infinite = true  # La couche se répète à l'infini
```

**Explication du infinite_offset** :
- Le `infinite_offset` est utilisé uniquement lorsque `is_infinite = true`
- Il définit la distance entre chaque répétition infinie de la couche de base
- La couche de base est créée en répétant le sprite `count_x` fois avec `spacing` entre chaque sprite
- Avec `infinite_offset = 100.0` et `is_infinite = true` :
  - La couche de base (composée de `count_x` sprites avec `spacing` entre eux) se répète à l'infini
  - Chaque répétition de la couche de base est espacée de 100 pixels de la précédente
  - Utile pour créer des couches infinies avec des espaces entre les répétitions
- Avec `infinite_offset = 0.0` et `is_infinite = true` :
  - Les répétitions infinies de la couche de base sont collées les unes aux autres (pas d'espacement)
  - Comportement par défaut pour les couches infinies continues
- **Important** : Le `spacing` est utilisé pour l'espacement entre les `count_x` sprites de la couche de base, tandis que `infinite_offset` est utilisé pour l'espacement entre les répétitions infinies de cette couche de base

**Positionnement vertical** : Le paramètre `y_offset` permet de positionner le sprite verticalement :
- `y_offset = 0.0` : Le sprite est positionné en haut de l'écran
- `y_offset = 600.0` : Le sprite est positionné à 600 pixels du haut (utile pour une plateforme en bas d'un écran de 720px)
- `y_offset` peut être négatif pour positionner le sprite partiellement hors écran en haut
- La valeur est en pixels depuis le haut de l'écran

### Exemple avec tags (système d'événements)

```toml
# Fichier : levels/niveau_avec_tags.niveau
# Exemple d'utilisation des tags pour permettre la manipulation des sprites via les événements

[sprite_sheet]
path = "sprite/terrain-montage.png"
sprite_width = 64
sprite_height = 64
spacing = -20

# Obstacle qui peut être supprimé via un événement
[[sprites]]
row = 1
col = 1
depth = 2
count_x = 5
y_offset = 600.0
x_offset = 2000.0
tags = ["obstacle", "removable"]  # Tag pour identifier cet obstacle

# Autre obstacle avec le même tag (sera supprimé en même temps)
[[sprites]]
row = 1
col = 1
depth = 2
count_x = 3
y_offset = 500.0
x_offset = 2500.0
tags = ["obstacle", "removable"]  # Même tag, sera supprimé avec le premier

# Élément décoratif qui peut être masqué
[[sprites]]
row = 0
col = 0
depth = 3
count_x = 1
y_offset = 200.0
x_offset = 3000.0
tags = ["decor", "hideable"]  # Tag pour masquer cet élément décoratif
```

**Explication des tags** :
- Les tags permettent de regrouper plusieurs sprites sous un même identifiant
- Un sprite peut avoir plusieurs tags (ex: `["obstacle", "removable"]`)
- Les tags sont utilisés par le système d'événements (spécification 11) pour localiser et manipuler les sprites
- Dans l'exemple ci-dessus, un événement `sprite_hide` avec `sprite_tag = "removable"` masquera les deux obstacles, car ils partagent tous les deux ce tag. De même, un événement `sprite_show` avec le même tag les affichera simultanément, et un événement `sprite_move` appliqué sur un tag partagé permettra de déplacer toutes les plateformes correspondantes (plateforme mobile synchronisée).
- Les tags sont optionnels : si un sprite n'a pas de tag, il ne peut pas être manipulé via les événements

### Exemple : Préparer une plateforme mobile (`sprite_move`)

```toml
[[sprites]]
row = 2
col = 4
depth = 2
count_x = 2
y_offset = 520.0
x_offset = 3800.0
tags = ["platform_mobile_secret"]  # Ciblé par l'événement sprite_move correspondant
```

- Ce tag `platform_mobile_secret` pourra être référencé depuis le fichier `.event` du niveau pour appliquer un déplacement `sprite_move`.
- Le sprite devient automatiquement détectable par le `collision_system`, qui pourra verrouiller le joueur/PNJ sur sa face supérieure pendant le mouvement (voir spécifications 4 et 11).

### Exemple avec initial_alpha (sprites invisibles par défaut)

```toml
# Fichier : levels/niveau_avec_sprites_invisibles.niveau
# Exemple d'utilisation de initial_alpha pour créer des sprites qui commencent invisibles

[sprite_sheet]
path = "sprite/terrain-montage.png"
sprite_width = 64
sprite_height = 64
spacing = -20

# Obstacle qui commence invisible et peut être affiché via un événement sprite_show
[[sprites]]
row = 1
col = 1
depth = 2
count_x = 5
y_offset = 600.0
x_offset = 2000.0
initial_alpha = 0  # Commence invisible (opacité 0)
tags = ["obstacle_revealed"]  # Tag pour l'événement sprite_show

# Plateforme normale (visible par défaut)
[[sprites]]
row = 1
col = 0
depth = 2
count_x = 10
y_offset = 800.0
x_offset = 0.0
# initial_alpha non spécifié : utilise la valeur par défaut (255 = complètement opaque)
```

**Explication de `initial_alpha`** :
- `initial_alpha = 0` : Le sprite commence complètement invisible (opacité 0)
- `initial_alpha = 255` : Le sprite commence complètement visible (opacité maximale, valeur par défaut)
- Valeurs intermédiaires : Permet d'avoir une opacité partielle (ex: `128` = 50% d'opacité)
- Si `initial_alpha = 0`, les collisions sont désactivées par défaut (même comportement qu'un sprite masqué via `sprite_hide`)
- L'opacité peut être modifiée dynamiquement via les événements `sprite_hide` et `sprite_show` (voir spécification 11)
- Utile pour créer des éléments qui apparaissent progressivement au cours du niveau (ex: obstacles révélés, portes qui s'ouvrent, etc.)

### Exemple avec is_background (décors à depth 2 sans collision)

```toml
# Fichier : levels/niveau_avec_decors_background.niveau
# Exemple d'utilisation de is_background pour créer des décors à depth 2 qui s'affichent derrière le joueur

[sprite_sheet]
path = "sprite/terrain-montage.png"
sprite_width = 64
sprite_height = 64
spacing = -20

# Plateforme solide à depth 2 (comportement normal : devant le joueur, avec collision)
[[sprites]]
row = 1
col = 1
depth = 2
count_x = 30
y_offset = 1040.0
is_background = false  # Ou omis (défaut: false)
is_infinite = true

# Décors à depth 2 qui s'affichent derrière le joueur et n'ont pas de collision
# Ces décors défilent à la même vitesse que les plateformes (scroll_speed = 1.0)
# mais s'affichent derrière le joueur et peuvent être traversés
[[sprites]]
row = 0
col = 0
depth = 2
count_x = 5
y_offset = 500.0
x_offset = 200.0
is_background = true  # S'affiche derrière le joueur, pas de collision
is_infinite = false

# Autre décor à depth 2 en arrière-plan
[[sprites]]
row = 0
col = 1
depth = 2
count_x = 3
y_offset = 300.0
x_offset = 800.0
is_background = true  # S'affiche derrière le joueur, pas de collision
is_infinite = true
infinite_offset = 200.0
```

**Explication de `is_background`** :
- Le paramètre `is_background` permet de créer des décors à depth 2 qui :
  - S'affichent **derrière le joueur** (comme les couches de depth 0 et 1)
  - N'ont **pas de collision** (le joueur peut les traverser)
  - Conservent la **même vitesse de défilement** que les autres éléments de depth 2 (scroll_speed = 1.0)
- Utile pour créer des décors qui doivent défilement à la même vitesse que les plateformes mais qui ne doivent pas bloquer le joueur
- **Uniquement applicable pour depth 2** : Pour les autres depths, ce paramètre est ignoré (depth 0 et 1 sont toujours derrière, depth 3 est toujours devant)
- Permet de mélanger des plateformes solides (`is_background = false`) et des décors (`is_background = true`) à la même profondeur

### Exemple avec is_foreground (décors à depth 2 devant les autres éléments de depth 2)

```toml
# Fichier : levels/niveau_avec_decors_foreground.niveau
# Exemple d'utilisation de is_foreground pour créer des décors à depth 2 qui passent devant les autres éléments de depth 2

[sprite_sheet]
path = "sprite/terrain-montage.png"
sprite_width = 64
sprite_height = 64
spacing = -20

# Plateforme solide à depth 2 (comportement normal : devant le joueur, avec collision)
[[sprites]]
row = 1
col = 1
depth = 2
count_x = 30
y_offset = 600.0
is_background = false  # Ou omis (défaut: false)
is_foreground = false  # Ou omis (défaut: false)
is_infinite = true

# Décors à depth 2 qui passent devant les autres éléments de depth 2 mais restent devant le joueur
# Ces décors défilent à la même vitesse que les autres éléments de depth 2 (scroll_speed = 1.0)
# mais passent devant les plateformes de depth 2 et n'ont pas de collision
[[sprites]]
row = 0
col = 1
depth = 2
count_x = 5
y_offset = 500.0
x_offset = 200.0
is_background = false  # Devant le joueur
is_foreground = true  # Passe devant les autres éléments de depth 2, pas de collision
is_infinite = false

# Autre décor à depth 2 en avant-plan
[[sprites]]
row = 0
col = 0
depth = 2
count_x = 3
y_offset = 300.0
x_offset = 800.0
is_background = false  # Devant le joueur
is_foreground = true  # Passe devant les autres éléments de depth 2, pas de collision
is_infinite = true
infinite_offset = 200.0

# Élément de foreground normal à depth 3 (comportement normal : devant le joueur)
[[sprites]]
row = 0
col = 0
depth = 3
count_x = 1
y_offset = 400.0
x_offset = 1000.0
is_infinite = false
```

**Explication de `is_foreground`** :
- Le paramètre `is_foreground` permet de créer des décors à depth 2 qui :
  - S'affichent **devant les autres éléments de depth 2** (plateformes, obstacles normaux)
  - Restent **devant le joueur** (comme tous les éléments de depth 2 sans `is_background`)
  - N'ont **pas de collision** (le joueur peut les traverser)
  - Conservent la **même vitesse de défilement** que les autres éléments de depth 2 (scroll_speed = 1.0)
- Utile pour créer des décors à depth 2 qui doivent passer devant les plateformes mais qui ne doivent pas bloquer le joueur
- **Uniquement applicable pour depth 2** : Pour les autres depths, ce paramètre est ignoré (depth 0 et 1 sont toujours derrière, depth 3 est toujours devant)
- Permet de mélanger des plateformes normales (`is_background = false` et `is_foreground = false`), des décors derrière le joueur (`is_background = true`), et des décors devant les plateformes (`is_foreground = true`) à la même profondeur
- **Note** : `is_background` et `is_foreground` sont mutuellement exclusifs. Si les deux sont définis à `true`, `is_background` a la priorité.

**Correction du spacing horizontal et vertical** : Les paramètres `x_offset`, `spacing`, `spacing_y` et `infinite_offset` permettent de corriger les problèmes d'espacement :
- `spacing` : Espacement horizontal entre chaque sprite lors de la répétition initiale
  - **Dans `[sprite_sheet]`** : Espacement par défaut appliqué à tous les sprites/layers pour compenser les bordures ou lignes noires incluses dans le sprite sheet
    - `spacing = -20` : Fait chevaucher les sprites de 20 pixels pour masquer les lignes noires/bordures du sprite sheet
    - Utile quand le sprite sheet contient des bordures ou lignes noires entre les sprites
  - **Dans `[layers]`** : Espacement entre chaque sprite de la ligne lors de la concaténation (surcharge le spacing par défaut)
    - **Note** : Pour les `[[layers]]`, le spacing n'est pas ajusté par un scale car les layers n'ont pas de paramètre `scale`
  - **Dans `[[sprites]]`** : Espacement entre chaque sprite lors de la répétition initiale de `count_x` sprites
    - Si `is_infinite = false` : Utilisé pour l'espacement entre les `count_x` répétitions du sprite
    - Si `is_infinite = true` : Utilisé pour l'espacement entre les `count_x` sprites de la couche de base (avant la répétition infinie)
    - **Ajustement par le scale** : Le `spacing` (qu'il vienne du sprite_sheet par défaut ou soit défini explicitement dans le sprite) est automatiquement multiplié par le `scale` du sprite pour maintenir les proportions visuelles
      - Exemple : Si `spacing = -20` dans le sprite_sheet et `scale = 0.5` dans le sprite, le spacing effectif sera `-20 * 0.5 = -10` pixels
      - Exemple : Si `spacing = 10` dans le sprite et `scale = 2.0`, le spacing effectif sera `10 * 2.0 = 20` pixels
    - `spacing = 0.0` : Les sprites sont collés les uns aux autres (même après ajustement par le scale)
    - `spacing = 1.0` : Ajoute 1 pixel d'espace entre chaque sprite (ajusté par le scale si applicable)
    - `spacing = -20.0` : Réduit l'espacement de 20 pixels (les sprites se chevauchent), **particulièrement utile pour compenser les bordures ou lignes noires incluses dans les sprites du sprite sheet** (ajusté par le scale si applicable)
    - **Note** : `spacing` est toujours utilisé pour l'espacement entre les `count_x` sprites de la couche de base. Si `is_infinite = true`, utilisez `infinite_offset` pour l'espacement entre les répétitions infinies de la couche de base.
- `x_offset` : Décalage horizontal absolu appliqué à tous les sprites répétés d'un sprite individuel (uniquement pour `[[sprites]]`)
  - `x_offset = 0.0` : Pas de décalage (défaut)
  - `x_offset = 2.0` : Décale tous les sprites de 2 pixels vers la droite
  - `x_offset = -1.0` : Décale tous les sprites de 1 pixel vers la gauche
  - `x_offset = 3300.0` : Positionne les sprites à 3300 pixels du bord gauche de l'espace du monde
  - **Important : `x_offset` n'est PAS ajusté par le scale** : C'est un décalage absolu en pixels dans l'espace du monde, utilisé pour positionner précisément les sprites à une position fixe, indépendamment du redimensionnement
    - Exemple : Si `x_offset = 3300.0` et `scale = 1.7`, le x_offset reste `3300.0` pixels (non ajusté)
    - Cela permet de positionner des éléments à des positions absolues précises dans le niveau, même lorsque le sprite est redimensionné
  - Utile pour aligner correctement les sprites répétés lorsque le sprite sheet a des problèmes de spacing, ou pour positionner des éléments à des positions absolues précises dans le niveau
  - Note : `x_offset` décale tous les sprites uniformément, tandis que `spacing` ajuste l'espacement entre chaque sprite (si `is_infinite = false`)
- `infinite_offset` : Distance entre chaque répétition infinie (uniquement pour `[[sprites]]` avec `is_infinite = true`)
  - `infinite_offset = 0.0` : Pas d'espacement entre les répétitions infinies (défaut, répétitions collées)
  - `infinite_offset = 100.0` : Un espace de 100 pixels est ajouté entre chaque répétition infinie de la couche
  - `infinite_offset = -20.0` : Les répétitions infinies se chevauchent de 20 pixels
  - **Ajustement par le scale** : Le `infinite_offset` est automatiquement multiplié par le `scale` du sprite pour maintenir les proportions visuelles
    - Exemple : Si `infinite_offset = 100` et `scale = 0.5`, l'infinite_offset effectif sera `100 * 0.5 = 50` pixels
  - Utile pour créer des couches infinies avec un espacement personnalisé entre les répétitions
  - **Note** : `infinite_offset` est utilisé uniquement lorsque `is_infinite = true`. Si `is_infinite = false`, utilisez `spacing` pour l'espacement entre les répétitions.
  - **Comportement** : La couche de base (composée de `count_x` sprites) se répète à l'infini avec un espacement de `infinite_offset_effectif` pixels entre chaque répétition (ajusté par le scale)
- `spacing_y` : Espacement vertical entre chaque répétition du sprite vers le haut (uniquement pour `[[sprites]]` avec `count_y > 1`)
  - `spacing_y = 0.0` : Pas d'espacement vertical entre les sprites (défaut, sprites collés verticalement)
  - `spacing_y = 10.0` : Un espace de 10 pixels est ajouté entre chaque sprite verticalement
  - `spacing_y = -20.0` : Les sprites se chevauchent verticalement de 20 pixels
  - **Ajustement par le scale** : Le `spacing_y` est automatiquement multiplié par le `scale` du sprite pour maintenir les proportions visuelles
    - Exemple : Si `spacing_y = 10` et `scale = 0.5`, le spacing_y effectif sera `10 * 0.5 = 5` pixels
  - Utile pour créer des structures verticales (murs, colonnes) avec un espacement personnalisé entre les blocs
  - **Comportement** : Les sprites sont empilés vers le haut à partir de `y_offset`, chaque sprite étant positionné `(hauteur_effective + spacing_y_effectif)` pixels au-dessus du précédent

## Tests

### Tests unitaires à implémenter

1. **Test de chargement de niveau** : Vérifier qu'un fichier de niveau valide est correctement chargé
2. **Test de validation** : Vérifier que les erreurs de format sont détectées
3. **Test d'extraction de sprites** : Vérifier que les sprites sont correctement extraits du sprite sheet
4. **Test de création de couches** : Vérifier que les couches sont créées avec les bons paramètres
5. **Test de valeurs par défaut** : Vérifier que les valeurs par défaut sont appliquées correctement
6. **Test de gestion d'erreurs** : Vérifier que les erreurs sont gérées proprement

### Exemple de test

```python
import pytest
from pathlib import Path
from levels.loader import LevelLoader
from levels.config import LevelConfig, RowMapping, SpriteMapping

def test_load_level():
    """Test le chargement d'un fichier de niveau."""
    assets_dir = Path("sprite")
    loader = LevelLoader(assets_dir)
    
    level_path = Path("levels/test_level.niveau")
    config = loader.load_level(level_path)
    
    assert config.sprite_sheet_path == Path("sprite/test.png")
    assert config.sprite_width == 64
    assert config.sprite_height == 64
    assert len(config.rows) > 0
    assert all(0 <= row.depth <= 3 for row in config.rows)

def test_create_parallax_layers():
    """Test la création du système de parallaxe depuis une config."""
    assets_dir = Path("sprite")
    loader = LevelLoader(assets_dir)
    
    config = loader.load_level(Path("levels/test_level.niveau"))
    parallax, layers_by_tag = loader.create_parallax_layers(config, 1280, 720)
    
    assert parallax is not None
    assert len(parallax._layers) == len(config.rows)
    # Vérifier que les couches sont triées par depth
    depths = [layer.depth for layer in parallax._layers]
    assert depths == sorted(depths)
```

## Initialisation du premier niveau

Le système de fichiers de niveau peut être utilisé pour initialiser le premier niveau du jeu. Le fichier `levels/niveau_plateforme.niveau` fournit un exemple de niveau avec une plateforme de base.

### Exemple d'intégration dans le jeu principal

```python
from pathlib import Path
import pygame
from moteur_jeu_presentation.entities import Player
from moteur_jeu_presentation.levels import LevelLoader

def main() -> None:
    """Point d'entrée principal du jeu."""
    pygame.init()
    
    SCREEN_WIDTH = 1280
    SCREEN_HEIGHT = 720
    FPS = 60
    
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Présentation")
    clock = pygame.time.Clock()
    
    # Charger le niveau depuis le fichier
    assets_dir = Path("sprite")
    level_loader = LevelLoader(assets_dir)
    level_path = Path("levels/niveau_plateforme.niveau")
    level_config = level_loader.load_level(level_path)
    
    # Créer le système de parallaxe depuis le niveau et récupérer le mapping par tag
    parallax_system, layers_by_tag = level_loader.create_parallax_layers(
        level_config,
        SCREEN_WIDTH,
        SCREEN_HEIGHT
    )
    
    # Initialiser le personnage
    player = Player(
        x=SCREEN_WIDTH / 2,
        y=SCREEN_HEIGHT / 2,
        sprite_sheet_path="sprite/walk.png",
        sprite_width=64,
        sprite_height=64,
        animation_speed=10.0,
    )
    
    camera_x = 0.0
    running = True
    
    while running:
        dt = clock.tick(FPS) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
        
        keys = pygame.key.get_pressed()
        player.update(dt, keys)
        
        # Mettre à jour la caméra pour suivre le personnage
        camera_x = player.x - SCREEN_WIDTH / 2
        
        # Mettre à jour le système de parallaxe
        parallax_system.update(camera_x, dt)
        
        # Dessiner
        screen.fill((30, 30, 30))
        
        # Dessiner les couches derrière le joueur (depth 0, 1, et depth 2 avec is_background = true)
        for layer in parallax_system._layers:
            if layer.depth <= 1 or (layer.depth == 2 and getattr(layer, 'is_background', False)):
                parallax_system._draw_layer(screen, layer)
        
        # Dessiner le personnage (couche gameplay, depth 2)
        player.draw(screen, camera_x)
        
        # Dessiner les couches devant le joueur (depth 2 sans is_background ni is_foreground, puis depth 2 avec is_foreground, puis depth 3)
        for layer in parallax_system._layers:
            if layer.depth == 2 and not getattr(layer, 'is_background', False) and not getattr(layer, 'is_foreground', False):
                parallax_system._draw_layer(screen, layer)
        
        for layer in parallax_system._layers:
            if layer.depth == 2 and getattr(layer, 'is_foreground', False):
                parallax_system._draw_layer(screen, layer)
        
        for layer in parallax_system._layers:
            if layer.depth == 3:
                parallax_system._draw_layer(screen, layer)
        
        pygame.display.flip()
    
    pygame.quit()
```

### Fichier de niveau recommandé pour le premier niveau

Le fichier `levels/niveau_plateforme.niveau` est conçu comme un niveau de départ avec :
- Un élément de background (sprite col=1, row=1) répété 2 fois à la profondeur 0 (derrière le joueur)
- Une plateforme de base (sprite col=1, row=1) répétée 70 fois à la profondeur 2 (devant le joueur)
- Format simple et extensible pour ajouter d'autres éléments

Ce fichier peut être utilisé tel quel ou modifié selon les besoins du jeu.

## Évolutions futures possibles

- Support de plusieurs sprite sheets par niveau ✅
- Sprites animés dans les couches
- Personnalisation des vitesses de défilement par ligne/sprite
- Support de sprites de différentes tailles
- Éditeur visuel de niveaux
- Support de métadonnées optionnelles (nom, description)
- Positionnement vertical des sprites (y_offset) ✅
- Correction du spacing horizontal (x_offset, spacing) ✅
- Distance entre répétitions infinies (infinite_offset) ✅
- Répétition verticale des sprites (count_y, spacing_y) ✅
- Support de couches dynamiques (ajout/suppression en runtime)

## Références

- Bonnes pratiques : `bonne_pratique.md`
- Spécification système de couches : `spec/1-systeme-de-couches-2d.md`
- Spécification personnage principal : `spec/2-personnage-principal.md`
- Documentation TOML : [TOML Specification](https://toml.io/)
- Bibliothèque tomli : [tomli on PyPI](https://pypi.org/project/tomli/)

---

**Date de création** : 2024  
**Statut** : ✅ Implémenté

