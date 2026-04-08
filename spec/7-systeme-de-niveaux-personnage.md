# 7 - Système de niveaux du personnage

## Contexte

Le personnage principal doit pouvoir changer d'apparence visuelle en fonction de son niveau. Les assets graphiques sont déjà organisés par type d'animation (ex: `walk.png`, `jump.png`). L'objectif est d'introduire un système de niveaux (1 à `max_level`) pour sélectionner dynamiquement les bons sprite sheets sans modifier les noms de fichiers existants. La **borne supérieure** `max_level` est définie dans `config/player_stats.toml` (clé racine `max_level`), et non plus uniquement comme constante figée dans le code.

## Objectifs

- Définir un système permettant d'associer un niveau (1 → `max_level`) du personnage à un sous-répertoire d'assets, où `max_level` est lu depuis `config/player_stats.toml`.
- Garantir que les fichiers de sprites conservent les mêmes noms (`walk.png`, `jump.png`, etc.) quel que soit le niveau.
- Intégrer ce système avec la classe `Player` et toute logique d'initialisation d'entités.
- Prévoir des mécanismes de validation (asset manquant, niveau hors bornes).
- Documenter les points d'intégration avec le système de fichiers de niveau et l'Asset Manager.
- **Ajouter un système de caractéristiques par niveau** : définir des statistiques (force, intelligence, vitesse, etc.) qui évoluent selon le niveau du personnage (1 → `max_level`).
- **Créer un format de fichier de configuration** pour spécifier les valeurs de chaque caractéristique à chaque niveau.
- **Ajouter une animation de confetti lors du passage de niveau** : utiliser le moteur de particules pour créer un effet visuel festif et coloré lors de l'augmentation du niveau du personnage. Les confettis sont émis en continu depuis les coins haut gauche et haut droit du texte de transition de niveau pendant toute la durée de l'animation, jusqu'à 1 seconde avant la fin.

## Architecture

### Structure des assets

```
sprite/
└── personnage/
    ├── 1/
    │   ├── walk.png
    │   ├── jump.png
    │   ├── climb.png
    │   └── ...
    ├── 2/
    │   ├── walk.png
    │   ├── jump.png
    │   ├── climb.png
    │   └── ...
    ├── 3/
    ├── 4/
    └── N/          # N = valeur de max_level dans player_stats.toml (ex. 5 par défaut)
```

- Les répertoires sont nommés par le niveau (`personnage/1`, `personnage/2`, …, `personnage/{max_level}`). Il doit exister un répertoire pour **chaque** entier de `1` à `max_level` inclus.
- Chaque niveau contient les mêmes fichiers que le répertoire actuel de sprites (`walk.png`, `jump.png`, `climb.png`, `idle.png`, etc.).
- Les dimensions, nombre de colonnes/lignes et structure interne restent identiques entre niveaux pour éviter de modifier la logique d'animation existante.
- **Note sur `climb.png`** : Le sprite sheet de grimpe (`climb.png`) suit le même système de niveaux que les autres sprite sheets. Si une animation de grimpe est implémentée, le fichier `climb.png` doit être présent dans chaque répertoire de niveau (`personnage/1/climb.png`, …, `personnage/{max_level}/climb.png`) et être chargé via `level_manager.get_asset_path("climb.png")` de la même manière que `walk.png` et `jump.png`.

### Référentiel des niveaux

- **Borne supérieure** : entier `max_level` défini dans `config/player_stats.toml` à la **racine** du fichier (voir ci-dessous). Si la clé est **absente**, appliquer la valeur de **rétrocompatibilité** `max_level = 5` (équivalent à l’ancienne constante `MAX_PLAYER_LEVEL` du code).
- Valeurs autorisées pour le niveau courant du personnage : `1 <= niveau <= max_level`.
- Le niveau par défaut (`DEFAULT_PLAYER_LEVEL`) reste **1**.
- Les niveaux sont des entiers ; une conversion explicite est requise si la valeur provient d'un fichier de configuration (TOML) ou de la sauvegarde.
- **Code** : `MIN_PLAYER_LEVEL` reste **1**. La borne supérieure effective utilisée par `PlayerLevelManager`, la boucle de jeu (touches `P` / confirmation level up), le préchargement des sprites joueur et la validation de `[player].level` dans les `.niveau` doit provenir de `PlayerStatsConfig.max_level` une fois les stats chargées. Tant qu’un symbole `MAX_PLAYER_LEVEL` est conservé pour compatibilité d’import, sa valeur doit refléter cette configuration après chargement (sinon repli sur **5** si le fichier stats est absent ou invalide).
- Prévoir une énumération ou des constantes documentées seulement pour les comportements qui ne dépendent pas de la config ; la liste des niveaux « disponibles » est toujours `range(1, max_level + 1)` après chargement.

### Niveau maximum dans `player_stats.toml` (`max_level`)

- **Emplacement** : clé **`max_level`** au niveau **racine** du TOML (hors des sections `[stats.*]` et `[level_up_messages]`).
- **Type** : entier ≥ 1.
- **Sémantique** : niveau maximal atteignable par le personnage ; doit être **cohérent** avec :
  - les répertoires `sprite/personnage/1` … `sprite/personnage/{max_level}` ;
  - pour chaque `[stats.<id>]`, la présence des clés numériques `level_1` … `level_{max_level}` (obligatoires) ;
  - les tooltips optionnels `tooltip_level_1` … `tooltip_level_{max_level}` si l’on souhaite un texte par niveau ;
  - les messages `[level_up_messages]` pour les passages vers les niveaux 2 … `max_level` (clés `level_2`, …, `level_{max_level}`), comme aujourd’hui pour 2–5.
- **Ordre de chargement** : le fichier `player_stats.toml` doit être chargé **avant** ou en même temps que la validation du niveau initial du joueur dans le `.niveau`, afin que `LevelLoader` puisse refuser un `[player].level` strictement supérieur à `max_level`.

### Seuil de déblocage du double saut (`double_jump_unlock_level`)

- **Emplacement** : clé **`double_jump_unlock_level`** au niveau **racine** du TOML (hors des sections `[stats.*]` et `[level_up_messages]`), à côté de `max_level`.
- **Type** : entier.
- **Sémantique** : niveau minimal du personnage (1 à `max_level`) à partir duquel le **double saut** est autorisé : la logique de saut compare `level` du personnage à ce seuil (voir spécification **6**). Ce seuil ne doit **plus** être codé en dur dans `Player`.
- **Valeur par défaut si la clé est absente** : **3** (rétrocompatibilité avec l’ancien comportement « double saut à partir du niveau 3 »).
- **Validation au chargement** : **1 ≤ double_jump_unlock_level ≤ max_level**. Hors de cet intervalle → lever `ValueError` avec un message explicite (incohérence avec `max_level`).
- **Fichier stats absent ou invalide** : même repli que pour les autres paramètres issus des stats — utiliser **3** pour le seuil de double saut si aucune config valide n’est disponible (documenter ce repli dans le code pour rester aligné avec l’ancien dur).

### Nom affiché du personnage (`display_name`)

- **Emplacement** : clé **`display_name`** au niveau **racine** du TOML (même niveau que `max_level` et `double_jump_unlock_level`, hors des sections `[stats.*]` et `[level_up_messages]`).
- **Type** : chaîne de caractères.
- **Sémantique** : texte affiché comme nom du personnage au-dessus du sprite (spécification **2**) et, pour cohérence, comme nom principal dans le titre de l’interface des statistiques « NOM (Niveau: X) » (spécification **10**). Ce texte est la **seule** source de vérité pour ce libellé : il ne doit **pas** y avoir de nom codé en dur ni de valeur par défaut dans le constructeur du `Player`.
- **Obligatoire** : **oui** — dès que le fichier `player_stats.toml` est chargé pour alimenter le jeu, la clé **`display_name` doit être présente** et sa valeur, une fois normalisée (ex. `strip()`), doit être **non vide**.
- **Erreur si absent ou vide** : lever une **`ValueError`** (ou erreur de validation équivalente au chargement) avec un **message explicite** indiquant que `display_name` est requis dans `config/player_stats.toml` (par ex. mentionner le chemin du fichier et la clé attendue). Aucun repli silencieux ni valeur par défaut du type `"Thomas"`.
- **Ordre de chargement** : `display_name` est lu en même temps que les autres clés racine ; la validation doit avoir lieu dans le chargeur (`PlayerStatsLoader` / équivalent) avant instanciation du `Player` en jeu normal.

### Présentation personnage (interface statistiques, spécification **10**)

Textes de la colonne « Origines », « Classe & Rôle » et « Traits de caractère » dans l’écran stats (`S`). **Même source** que les autres paramètres du personnage : `config/player_stats.toml`.

- **Emplacement** : table TOML **`[presentation]`** (au même niveau que les sections `[stats.*]` et `[level_up_messages]`, pas à la racine seule).
- **Clés obligatoires** (lorsque le fichier stats est chargé pour le jeu) :
  - **`origins`** : tableau de chaînes (`list[str]` après chargement).
  - **`class_role`** : tableau de chaînes.
  - **`traits`** : tableau de chaînes.
- **Uniformisation** : les trois clés ont le **même format** et le **même rendu** côté UI (une chaîne = une puce ; libellés du type `Background : …` font partie du texte si le rédacteur les inclut).
- **Pas de valeur par défaut** dans le code : absence de `[presentation]`, absence d’une des trois clés, type autre que liste de chaînes, liste **vide**, ou au moins une entrée vide après `strip()` → **`ValueError`** au chargement avec message explicite (fichier, section, clé).
- **Intégration** : exposer ces trois listes sur `PlayerStatsConfig` (champs dédiés ou sous-structure unique, ex. `presentation_origins`, `presentation_class_role`, `presentation_traits`, ou un petit `@dataclass` regroupé). `PlayerStatsDisplay` s’en sert pour alimenter le module `character_presentation` sans constante `DEFAULT_CHARACTER_PRESENTATION`.
- **Rétrocompatibilité** : les anciennes formes `origins = { background = "...", ... }` ne sont **plus** supportées une fois l’implémentation alignée ; les fichiers TOML doivent migrer vers des tableaux de chaînes.

### Système de caractéristiques par niveau

Chaque niveau du personnage est associé à des valeurs de caractéristiques (statistiques) qui influencent le gameplay. Ces caractéristiques sont définies dans un fichier de configuration TOML séparé.

#### Format de fichier de caractéristiques

Le fichier de caractéristiques utilise le format TOML et doit être nommé `player_stats.toml` (ou un nom configurable). Il est placé dans le répertoire de configuration du projet (ex: `config/` ou à la racine).

**Structure du fichier** :

```toml
# Fichier : config/player_stats.toml
# Configuration des caractéristiques du personnage par niveau
max_level = 5
double_jump_unlock_level = 3  # Niveau minimal pour autoriser le double saut (défaut 3 si absent)
display_name = "Nom affiché du personnage"  # Obligatoire : nom au-dessus du sprite et titre stats (non vide)

# Présentation colonne droite de l'écran stats (spécification 10) — obligatoire si le fichier est chargé ; pas de défaut code
[presentation]
origins = [
    "Background : …",
    "Déclic : …",
    "Mantra : …",
]
class_role = [
    "Classe : …",
    "Sous-classe : …",
    "Alignement : …",
]
traits = [
    "Trait 1 …",
    "Trait 2 …",
]

[stats.force]
name = "Force"
description = "Puissance physique du personnage"
level_1 = 10
level_2 = 20
level_3 = 35
level_4 = 55
level_5 = 80

[stats.intelligence]
name = "Intelligence"
description = "Capacité intellectuelle du personnage"
level_1 = 8
level_2 = 18
level_3 = 32
level_4 = 52
level_5 = 75

[stats.vitesse]
name = "Vitesse"
description = "Rapidité de déplacement du personnage"
level_1 = 12
level_2 = 22
level_3 = 38
level_4 = 58
level_5 = 85
# max_value = 100  # Optionnel : si non défini, max_value = level_{max_level} (ici 85)
```

**Règles de format** :
- **`max_level` (racine, recommandé)** : entier ≥ 1 ; borne supérieure du système de niveaux du personnage. Si absent, traiter comme **`max_level = 5`** pour rétrocompatibilité avec les configurations et assets existants.
- **`display_name` (racine, obligatoire lorsque le fichier est utilisé)** : chaîne non vide après normalisation ; nom affiché du personnage (voir section dédiée ci-dessus). Absence ou chaîne vide → **`ValueError`** avec message explicite.
- **`[presentation]` (obligatoire lorsque le fichier est utilisé pour le jeu)** : table avec **`origins`**, **`class_role`**, **`traits`** — chacune une liste de chaînes non vides (après normalisation), même sémantique d’affichage (spécification **10**). Aucun repli silencieux si la section ou une clé manque.
- **`double_jump_unlock_level` (racine, optionnel)** : entier avec **1 ≤ valeur ≤ `max_level`** ; seuil minimal de niveau pour le double saut. Si absent, traiter comme **`double_jump_unlock_level = 3`** pour rétrocompatibilité.
- Chaque caractéristique est définie dans une section `[stats.<nom_stat>]`.
- Le nom de la section (`<nom_stat>`) est utilisé comme identifiant unique (ex: `force`, `intelligence`, `vitesse`).
- Chaque section doit contenir :
  - `name` (obligatoire) : Nom affiché de la caractéristique (ex: "Force").
  - `description` (optionnel) : Description textuelle de la caractéristique.
  - `tooltip_level_1` à `tooltip_level_{max_level}` (optionnels) : Textes explicatifs détaillés affichés au survol de l'icône d'information dans l'interface des statistiques, un pour chaque niveau de 1 à `max_level`. Chaque tooltip peut être plus long et détaillé que la `description` et peut contenir plusieurs lignes (utiliser `\n` pour les sauts de ligne). Le tooltip affiché correspond au niveau actuel du personnage.
  - `level_1` à `level_{max_level}` (obligatoires) : Valeurs numériques (int ou float) pour chaque niveau de 1 à `max_level` inclus.
  - `max_value` (optionnel) : Valeur maximale de la caractéristique. Si non définie, la valeur maximale est automatiquement déterminée par la valeur de `level_{max_level}` (comportement par défaut pour rétrocompatibilité ; lorsque `max_level` était implicitement 5, cela correspondait à `level_5`). Si définie, cette valeur est utilisée comme maximum pour l'affichage et les calculs de pourcentage, indépendamment de la valeur de `level_{max_level}`.
- Les valeurs peuvent être des entiers ou des nombres décimaux selon les besoins du gameplay.
- Les valeurs doivent être positives (>= 0).
- La valeur `max_value` doit être positive (>= 0) et doit être supérieure ou égale à toutes les valeurs `level_1` à `level_{max_level}` (validation lors du chargement).
- Les tooltips sont optionnels : si un `tooltip_level_N` n'est pas défini pour un niveau donné, aucun tooltip ne s'affichera au survol de l'icône pour ce niveau.

#### Structure de données pour les caractéristiques

```python
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class StatDefinition:
    """Définition d'une caractéristique avec ses valeurs par niveau."""
    identifier: str  # Identifiant unique (ex: "force", "intelligence")
    name: str  # Nom affiché (ex: "Force")
    description: Optional[str] = None  # Description optionnelle
    tooltips: Dict[int, str] = None  # Dict[level, tooltip_text] pour les tooltips par niveau (optionnel)
    values: Dict[int, float] = None  # Dict[level, value] pour levels 1..max_level
    max_value: Optional[float] = None  # Valeur maximale explicite (optionnel)
    
    def __post_init__(self) -> None:
        """Initialise les dictionnaires si nécessaire."""
        if self.values is None:
            self.values = {}
        if self.tooltips is None:
            self.tooltips = {}
    
    def get_tooltip(self, level: int) -> Optional[str]:
        """Récupère le tooltip pour un niveau donné.
        
        Args:
            level: Niveau du personnage (1 à max_level du fichier de config)
            
        Returns:
            Texte du tooltip pour le niveau, ou None si non défini
        """
        return self.tooltips.get(level)
    
    def get_max_value(self, max_level: int) -> float:
        """Récupère la valeur maximale de la caractéristique.
        
        Si max_value est défini explicitement, retourne cette valeur.
        Sinon, retourne la valeur de `level_{max_level}` (comportement par défaut).
        
        Args:
            max_level: Borne supérieure issue de `PlayerStatsConfig.max_level`
        
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
    display_name: str  # Obligatoire dans player_stats.toml si le fichier est chargé (racine TOML)
    presentation_origins: list[str]  # [presentation].origins — obligatoire si fichier chargé (spéc. 10)
    presentation_class_role: list[str]  # [presentation].class_role
    presentation_traits: list[str]  # [presentation].traits
    max_level: int = 5  # Défaut si clé absente du TOML (rétrocompatibilité)
    double_jump_unlock_level: int = 3  # Défaut si clé absente (rétrocompatibilité avec l’ancien seuil code)
    
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
    
    def can_double_jump_at_level(self, level: int) -> bool:
        """Indique si le double saut est autorisé pour un niveau de personnage donné."""
        return level >= self.double_jump_unlock_level
```

#### Chargeur de caractéristiques

```python
from pathlib import Path
from typing import Dict

class PlayerStatsLoader:
    """Chargeur de fichier de caractéristiques du personnage."""
    
    def __init__(self, config_path: Path) -> None:
        """
        Args:
            config_path: Chemin vers le fichier player_stats.toml
        """
        self.config_path = config_path
    
    def load_stats(self) -> PlayerStatsConfig:
        """Charge le fichier de caractéristiques.
        
        Returns:
            Configuration des caractéristiques chargée
            
        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            ValueError: Si le format du fichier est invalide
        """
        # Implémentation : charger le TOML et valider la structure
        # Lire display_name à la racine (obligatoire) ; absent ou vide après strip -> ValueError explicite
        # Lire max_level à la racine (défaut 5 si absent)
        # Lire double_jump_unlock_level à la racine (défaut 3 si absent) et valider 1 <= valeur <= max_level
        # Lire [presentation] : origins, class_role, traits — listes de chaînes obligatoires, non vides, sans entrée vide après strip (sinon ValueError explicite — spec 10)
        # Vérifier que toutes les sections [stats.*] contiennent level_1 à level_{max_level}
        # Extraire les tooltip_level_1 à tooltip_level_{max_level} (optionnels) et les stocker dans tooltips
        # Extraire max_value (optionnel) pour chaque statistique
        # Convertir en PlayerStatsConfig
        pass
    
    def validate_stats(self, config: PlayerStatsConfig) -> None:
        """Valide la configuration des caractéristiques.
        
        Raises:
            ValueError: Si la configuration est invalide
        """
        # Vérifier que chaque stat a des valeurs pour tous les niveaux 1 à max_level
        # Vérifier que les valeurs sont positives
        # Vérifier que max_value (si défini) est positif et >= toutes les valeurs level_1 à level_{max_level}
        # Vérifier 1 <= double_jump_unlock_level <= max_level
        # Vérifier display_name non vide
        # Vérifier presentation_origins, presentation_class_role, presentation_traits (listes non vides, éléments non vides après strip)
        pass
```

### Gestionnaire de niveaux (`PlayerLevelManager`)

Créer un composant dédié pour gérer la sélection des assets :

```python
class PlayerLevelManager:
    def __init__(
        self, 
        assets_root: Path, 
        level: int,
        stats_config: Optional[PlayerStatsConfig] = None
    ) -> None: ...

    def get_asset_path(self, filename: str) -> Path: ...

    def list_available_assets(self) -> list[str]: ...

    def set_level(self, level: int) -> None: ...

    @property
    def level(self) -> int: ...
    
    def get_stat_value(self, stat_identifier: str) -> float: ...
    
    def get_stat_max_value(self, stat_identifier: str) -> float: ...
    
    def get_all_stats(self) -> Dict[str, float]: ...
    
    def get_stat_tooltip(self, stat_identifier: str) -> Optional[str]: ...
```

- `assets_root` correspond au répertoire `sprite/personnage`.
- `get_asset_path()` renvoie le chemin complet d'un fichier pour le niveau courant.
- `set_level()` valide la borne (1 → `max_level` effectif issu de `stats_config.max_level` lorsque la config est disponible, sinon repli cohérent avec le code, typiquement 5), vide le cache de surfaces si nécessaire et déclenche le rechargement des assets.
- `stats_config` (optionnel) : Configuration des caractéristiques. Si fournie, permet d'accéder aux valeurs de stats via `get_stat_value()`.
- `get_stat_value(stat_identifier)` : Récupère la valeur d'une caractéristique pour le niveau actuel (ex: `get_stat_value("force")`).
- `get_stat_max_value(stat_identifier)` : Récupère la valeur maximale d'une caractéristique. Si `max_value` est défini dans la configuration, retourne cette valeur. Sinon, retourne la valeur de `level_{max_level}` (comportement par défaut pour rétrocompatibilité).
- `get_all_stats()` : Retourne un dictionnaire de toutes les caractéristiques avec leurs valeurs pour le niveau actuel.
- `get_stat_tooltip(stat_identifier)` : Récupère le tooltip d'une caractéristique pour le niveau actuel. Retourne `None` si aucun tooltip n'est défini pour ce niveau (ex: `get_stat_tooltip("force")`).
- Optionnel : mise en cache des `pygame.Surface` pour éviter de recharger les images à chaque changement (utiliser l'Asset Manager existant si disponible).

## Intégration

### Classe `Player`

- Ajouter une propriété `level_manager: PlayerLevelManager` initialisée au démarrage.
- Paramétrer `Player` pour accepter un `player_level: int = DEFAULT_PLAYER_LEVEL` et un `stats_config: Optional[PlayerStatsConfig] = None`.
- Modifier le chargement des sprite sheets (`walk`, `jump`, etc.) pour passer par `level_manager.get_asset_path(...)`.
- Exposer une API `set_level()` qui déclenche le rechargement des assets et est utilisable par l'input runtime (touches `P`/`O`).
- **Intégrer les caractéristiques** :
  - Ajouter des propriétés pour accéder aux valeurs de stats : `force`, `intelligence`, `vitesse`, etc.
  - Utiliser les valeurs de stats pour influencer le gameplay (ex: `vitesse` modifie `speed`, `force` peut influencer les dégâts, etc.).
  - Lors d'un changement de niveau, mettre à jour automatiquement les valeurs de stats via `level_manager.get_stat_value()`.
- Lors d'un changement de niveau :
  - Mettre à jour `level_manager`.
  - Recharger les surfaces utilisées pour les animations.
  - Réinitialiser les index d'animation ou les timers pour éviter un décalage visuel.
  - **Mettre à jour les valeurs de caractéristiques** si `stats_config` est disponible.
- Factoriser la liste des assets attendus (ex: `WALK_SHEET_NAME = "walk.png"`, `JUMP_SHEET_NAME = "jump.png"`) afin d'éviter les chaînes magiques dispersées.
- **Double saut** : le seuil minimal de niveau pour autoriser le double saut provient de `stats_config.double_jump_unlock_level` lorsque `PlayerStatsConfig` est disponible ; sinon repli **3** (voir spécification **6**). Aucune comparaison en dur à `3` dans la logique de saut.

**Exemple d'utilisation des caractéristiques dans `Player`** :

```python
class Player:
    def __init__(
        self,
        x: float,
        y: float,
        player_level: int = DEFAULT_PLAYER_LEVEL,
        stats_config: Optional[PlayerStatsConfig] = None,
        ...
    ) -> None:
        # ... initialisation existante ...
        self.level_manager = PlayerLevelManager(assets_root, player_level, stats_config)
        self._base_speed = 200.0  # Vitesse de base en pixels/seconde
        self._update_stats()
    
    def _update_stats(self) -> None:
        """Met à jour les valeurs de caractéristiques selon le niveau actuel."""
        if self.level_manager.stats_config:
            # Mettre à jour la vitesse selon la stat "vitesse"
            # La stat vitesse est utilisée comme facteur d'amélioration
            # Formule: speed = base_speed * (1 + (vitesse_stat / 100))
            # Exemple: vitesse_stat = 12 → speed = 250 * 1.12 = 280 pixels/seconde
            #          vitesse_stat = 85 → speed = 250 * 1.85 = 462.5 pixels/seconde
            vitesse_stat = self.level_manager.get_stat_value("vitesse")
            self.speed = self._base_speed * (1.0 + (vitesse_stat / 100.0))
    
    def set_level(self, level: int) -> None:
        """Change le niveau du personnage."""
        self.level_manager.set_level(level)
        self._reload_assets()
        self._update_stats()  # Mettre à jour les stats après changement de niveau
    
    @property
    def force(self) -> float:
        """Retourne la valeur de force actuelle."""
        if self.level_manager.stats_config:
            return self.level_manager.get_stat_value("force")
        return 0.0
    
    @property
    def intelligence(self) -> float:
        """Retourne la valeur d'intelligence actuelle."""
        if self.level_manager.stats_config:
            return self.level_manager.get_stat_value("intelligence")
        return 0.0
    
    @property
    def vitesse(self) -> float:
        """Retourne la valeur de vitesse actuelle."""
        if self.level_manager.stats_config:
            return self.level_manager.get_stat_value("vitesse")
        return 0.0
```

### Asset Manager / système de ressources

- Étendre l'Asset Manager pour supporter les chemins fournis par `PlayerLevelManager`.
- Les sprites étant identiques par nom, privilégier une clé de cache composée (`f"player_level_{level}_{filename}"`).
- Prévoir un mécanisme de fallback : si un fichier est manquant pour un niveau donné, lever une exception claire (`MissingPlayerAssetError`).

### Fichiers de niveau (`*.niveau` / TOML)

- Ajouter une clé optionnelle dans la section joueur :

```toml
[player]
level = 3
```

- Si absente, utiliser le niveau par défaut.
- Valider lors du chargement (`LevelLoader`) que la valeur est bien entre **1** et **`max_level`** (valeur issue de `PlayerStatsConfig` après chargement de `player_stats.toml`, ou repli **5** si les stats ne sont pas disponibles — dans ce dernier cas, documenter le risque d’incohérence si `max_level` ≠ 5 dans le fichier).
- Stocker le niveau dans la configuration renvoyée afin que `main.py` ou le système d'entités puisse initialiser correctement le `Player`.

### Chargement des caractéristiques

- Le fichier `player_stats.toml` doit être chargé au démarrage du jeu (dans `main.py` ou un module d'initialisation).
- Le `PlayerStatsLoader` charge et valide le fichier de caractéristiques, y compris la clé racine **`max_level`** (défaut **5** si absente) et la cohérence des clés `level_1` … `level_{max_level}` pour chaque stat.
- La `PlayerStatsConfig` est passée au `Player` lors de son initialisation.
- Si le fichier est absent ou invalide, le jeu peut fonctionner sans caractéristiques (valeurs par défaut ou 0).
- Le chemin du fichier peut être configurable via une constante ou un paramètre (ex: `DEFAULT_STATS_CONFIG_PATH = Path("config/player_stats.toml")`).

### Sauvegarde / persistance (évolution future)

- Prévoir un point d'entrée unique pour modifier le niveau (ex: `player.set_level(new_level)`), afin d'intégrer facilement une logique d'XP plus tard.
- Lors de l'ajout d'une sauvegarde, stocker le niveau actuel et le restaurer via `PlayerLevelManager`.

### Gestion des entrées (main loop)

- Dans la boucle principale (ex: `main.py`), détecter l'appui des touches `P` (pygame.K_p) et `O` (pygame.K_o).
- `P` incrémente le niveau du joueur (`player.player_level + 1`) sans dépasser le **niveau maximum effectif** (`max_level` depuis `player_stats.toml` / `PlayerStatsConfig`, ou repli documenté côté code).
- `O` décrémente le niveau (`player.player_level - 1`) sans descendre sous `MIN_PLAYER_LEVEL` (1).
- Après changement, appeler `player.set_level(new_level)` et afficher éventuellement le niveau actuel dans la console pour debug.
- Ignorer les répétitions lorsque la touche reste enfoncée (facultatif) : possibilité de détecter l'événement `KEYDOWN` pour un changement unique.

### Animation de confetti lors du passage de niveau

Lors du passage de niveau (augmentation du niveau du personnage), une animation de confetti est déclenchée pour célébrer visuellement la progression. Cette animation utilise le moteur de particules pour créer un effet de confetti coloré et festif.

**Voir la spécification 14 - Moteur de particules, section "Animation de confetti pour le passage de niveau"** pour les détails complets de l'implémentation, incluant :
- Les caractéristiques de l'animation
- La fonction de configuration `create_confetti_config()`
- L'intégration dans la classe `Player`
- L'intégration dans la boucle de jeu
- L'intégration avec l'animation de transition de niveau
- La configuration et la gestion des erreurs
- Les optimisations

**Résumé** : La classe `Player` doit être étendue avec une propriété `particle_system` (optionnelle) et des propriétés pour gérer l'émission continue de confettis pendant l'animation de transition de niveau. L'émission de confettis est gérée **uniquement** dans `_update_level_transition()` et émet des confettis depuis les coins haut gauche et haut droit du cadre de transition en continu jusqu'à 1 seconde avant la fin de l'animation. **Aucune émission de confetti ne doit être déclenchée depuis la position du personnage** - les confettis sont émis exclusivement depuis les coins du cadre de transition. Le système de particules doit être initialisé et passé au `Player` lors de la création.

#### Comportement détaillé de l'animation de confetti

L'animation de confetti est déclenchée pendant l'animation de transition de niveau (voir spécification 11) et se comporte comme suit :

1. **Position d'émission** : Les confettis sont émis depuis deux positions distinctes, correspondant exactement aux coins arrondis visibles du cadre :
   - **Important** : Les confettis doivent être émis depuis les **coins arrondis visibles** du cadre, pas depuis les coins géométriques du rectangle. Les positions doivent tenir compte du `corner_radius` :
   - **Coin haut gauche arrondi du cadre** : Position `(frame_x + corner_radius, frame_y)` où :
     - `frame_x` et `frame_y` sont les coordonnées du coin supérieur gauche du rectangle du cadre de transition
     - `corner_radius` est le rayon des coins arrondis (converti selon le facteur d'échelle `scale_y`, doit être recalculé de la même manière que dans `start_level_transition`)
     - Cette position correspond au point sur l'arc du coin arrondi au niveau du bord supérieur (y=0 dans les coordonnées locales de la surface). Dans pygame.draw.rect avec `border_radius`, le coin arrondi est un quart de cercle, et le point sur l'arc au niveau du bord supérieur est à `corner_radius` pixels depuis le coin géométrique.
   - **Coin haut droit arrondi du cadre** : Position `(frame_x + frame_width - corner_radius, frame_y)` où :
     - `frame_width` est la largeur du cadre de transition (incluant le texte, le padding et la bordure)
     - `corner_radius` est le rayon des coins arrondis (converti selon le facteur d'échelle `scale_y`)
     - Cette position correspond au point sur l'arc du coin arrondi au niveau du bord supérieur
   - **Note** : Les confettis partent exactement depuis les coins arrondis visibles du cadre, pas depuis l'extérieur. Il n'y a pas d'offset horizontal supplémentaire pour éviter que les confettis partent de l'extérieur du cadre visible.
   - Voir spécification 11, section "Animation de transition de niveau" pour plus de détails
   
2. **Direction d'émission en cône** : Les confettis sont émis en cône directionnel pour créer un effet visuel plus spectaculaire :
   - **Coin haut gauche** : Les confettis sont émis en cône vers le haut à gauche avec :
     - Angle de direction : -135° (-3π/4 radians) - direction vers le haut à gauche
     - Dispersion : 30° (π/6 radians) - les confettis se dispersent dans un cône de 30° autour de cette direction
   - **Coin haut droit** : Les confettis sont émis en cône vers le haut à droite avec :
     - Angle de direction : -45° (-π/4 radians) - direction vers le haut à droite
     - Dispersion : 30° (π/6 radians) - les confettis se dispersent dans un cône de 30° autour de cette direction
   - Les configurations utilisent `direction_type="custom"` avec `direction_angle` et `direction_spread` pour créer ces cônes directionnels

3. **Durée et fréquence** : 
   - Les confettis sont lancés **en continu** pendant toute la durée de l'animation de transition de niveau
   - L'émission de confettis **s'arrête 1 seconde avant la fin** de l'animation de transition
   - Par exemple, si l'animation de transition dure 1.5 secondes, les confettis sont émis de 0.0 à 0.5 secondes (pendant 0.5 secondes)
   - La fréquence d'émission peut être configurée via une constante (ex: un effet de confetti toutes les 0.2 secondes)

4. **Configuration des effets** : 
   - Chaque émission crée un effet de confetti indépendant depuis chaque position (gauche et droite)
   - Les deux effets utilisent la même configuration `create_confetti_config()` mais sont créés avec des identifiants différents pour permettre le suivi
   - Les effets sont créés via `particle_system.create_effect()` avec des identifiants uniques (ex: `f"confetti_level_up_left_{timestamp}"` et `f"confetti_level_up_right_{timestamp}"`)

5. **Intégration avec l'animation de transition** :
   - L'animation de confetti est gérée dans `_update_level_transition()` de la classe `Player`
   - À chaque frame, si l'animation de transition est active et que le temps restant est supérieur à 1.0 seconde, vérifier si un nouvel effet de confetti doit être créé
   - Les positions d'émission (coins haut gauche et haut droit du cadre) sont calculées à partir des coordonnées du cadre de transition (`text_x`, `text_y`, `text_width`) où `text_x` et `text_y` sont les coordonnées du coin supérieur gauche du cadre, et `text_width` est la largeur totale du cadre
   - **Important** : Les coordonnées du cadre sont en coordonnées écran, mais le système de particules utilise des coordonnées monde. Il faut donc convertir les coordonnées écran en coordonnées monde en ajoutant `camera_x` pour la coordonnée X (la coordonnée Y reste généralement identique car il n'y a pas de décalage vertical de caméra)

6. **Variables de configuration** :
   - `CONFETTI_EMISSION_INTERVAL: float = 0.2` : Intervalle entre chaque émission de confetti en secondes (défaut: 0.2)
   - `CONFETTI_STOP_BEFORE_END: float = 1.0` : Durée avant la fin de l'animation où l'émission s'arrête en secondes (défaut: 1.0)
   - `CONFETTI_COUNT_PER_EMISSION: int = 60` : Nombre de particules par émission (défaut: 60, doublé pour plus d'effet visuel, peut être ajusté pour les performances)
   - `CONFETTI_HORIZONTAL_OFFSET: float = 80.0` : Offset horizontal en pixels pour déplacer les confettis plus loin à gauche et à droite du cadre (défaut: 80.0 pixels dans le repère de conception 1920x1080, converti automatiquement vers la résolution de rendu)
   - `CONFETTI_CONE_SPREAD: float = π/6` : Dispersion du cône en radians (défaut: π/6 = 30°). Les confettis se dispersent dans un cône de cette taille autour de la direction principale
   - `CONFETTI_LEFT_CONE_ANGLE: float = -3π/4` : Angle de direction pour le coin haut gauche en radians (défaut: -3π/4 = -135°). Direction vers le haut à gauche
   - `CONFETTI_RIGHT_CONE_ANGLE: float = -π/4` : Angle de direction pour le coin haut droit en radians (défaut: -π/4 = -45°). Direction vers le haut à droite

7. **Gestion de l'état** :
   - Ajouter des propriétés à `Player` pour gérer l'état de l'animation de confetti :
     - `_confetti_emission_timer: float = 0.0` : Timer pour gérer la fréquence d'émission
     - `_confetti_last_emission_time: float = 0.0` : Temps de la dernière émission (pour éviter les émissions multiples dans la même frame)

## Gestion des erreurs

| Cas | Gestion | Message |
| --- | --- | --- |
| Niveau < 1 ou > max_level | Lever `ValueError` | `Player level must be between 1 and {max_level} (got {level})` |
| Fichier manquant dans un niveau | Lever `MissingPlayerAssetError` | `Missing asset 'walk.png' for player level 3` |
| Niveau configuré sans répertoire correspondant | Vérifier la présence du dossier au démarrage | `Missing directory sprite/personnage/{level}` |
| Fichier `player_stats.toml` introuvable | Logger un avertissement, continuer sans stats | `Warning: Stats config file not found at {path}, continuing without stats` |
| Section `[stats.*]` manquante `level_1` à `level_{max_level}` | Lever `ValueError` lors du chargement | `Missing level_{n} in stat '{stat_identifier}'` |
| Valeur de stat négative | Lever `ValueError` lors du chargement | `Invalid stat value for '{stat_identifier}' level {level}: {value} (must be >= 0)` |
| `max_value` négatif | Lever `ValueError` lors du chargement | `Invalid max_value for '{stat_identifier}': {value} (must be >= 0)` |
| `max_value` inférieur à une valeur `level_N` | Lever `ValueError` lors du chargement | `Invalid max_value for '{stat_identifier}': {max_value} (must be >= all level values, max level value is {max_level_value})` |
| `max_level` absent ou < 1, ou incohérent avec les stats | Lever `ValueError` ou appliquer défaut 5 | Message explicite si valeur invalide ; défaut **5** uniquement si absence de clé (rétrocompatibilité) |
| `double_jump_unlock_level` hors [1, `max_level`] | Lever `ValueError` lors du chargement | Message explicite (doit être entre 1 et max_level) ; défaut **3** uniquement si absence de clé (rétrocompatibilité) |
| Identifiant de stat inexistant | Lever `KeyError` lors de l'accès | `Statistic '{stat_identifier}' not found` |
| Champ `tooltip_level_N` manquant pour un niveau | Comportement normal, aucun tooltip affiché pour ce niveau | Pas d'erreur, l'icône est affichée mais aucun tooltip au survol |

## Pièges courants

1. **Cache périmé après changement de niveau** : toujours vider/mettre à jour le cache de surfaces pour éviter d'afficher les sprites de l'ancien niveau.
2. **Dimensions divergentes entre niveaux** : vérifier que chaque fichier conserve exactement la même taille (sinon réviser les offsets et animations).
3. **Chemins relatifs/absolus** : utiliser `Path` et éviter les concaténations de chaînes (`/` avec `pathlib`).
4. **`max_level` vs assets et stats** : augmenter `max_level` impose d’ajouter les dossiers `sprite/personnage/{n}` et les clés `level_n` (et tooltips / messages si besoin) pour **tous** les `n` jusqu’à `max_level`. Ne pas se contenter de modifier le TOML sans les assets.
5. **Stats non mises à jour après changement de niveau** : s'assurer que `_update_stats()` est appelée dans `set_level()`.
6. **Dépendances circulaires** : éviter que `PlayerStatsConfig` dépende de `Player` ou vice-versa. Utiliser une approche de composition.
7. **Valeurs de stats non validées** : toujours valider que les valeurs sont positives et que tous les niveaux sont définis lors du chargement.
8. **Valeur maximale non cohérente** : si `max_value` est défini, s'assurer qu'il est supérieur ou égal à toutes les valeurs `level_1` à `level_{max_level}`. Si `max_value` n'est pas défini, utiliser la valeur de `level_{max_level}` comme maximum (comportement par défaut).
9. **Coordonnées écran vs monde pour les confettis** : Les coordonnées du texte de transition sont en coordonnées écran, mais le système de particules utilise des coordonnées monde. Il faut convertir les coordonnées écran en coordonnées monde en ajoutant `camera_x` pour la coordonnée X lors de la création des effets de particules.
10. **Synchronisation de l'émission de confettis** : L'émission de confettis doit être gérée **uniquement** dans `_update_level_transition()` pour être synchronisée avec l'animation de transition. **Ne pas créer les confettis dans `set_level()`** - aucune émission ne doit être déclenchée depuis la position du personnage. Les confettis sont émis exclusivement depuis les coins du texte de transition pendant l'animation.
11. **Émission uniquement depuis le cadre de transition** : Les confettis ne doivent jamais être émis depuis la position du personnage (`self.x`, `self.y`). L'émission se fait **uniquement** depuis les coins haut gauche et haut droit du cadre de transition de niveau. La méthode `_trigger_confetti_celebration()` ne doit plus être utilisée pour le passage de niveau et peut être supprimée ou conservée pour d'autres usages futurs si nécessaire.

## Tests

### Tests unitaires

- `test_level_manager_bounds()` : vérifier que `set_level()` accepte `1` → `max_level` (selon une config de test) et refuse en dehors des bornes.
- `test_asset_path_resolution()` : vérifier que `get_asset_path("walk.png")` renvoie bien `sprite/personnage/3/walk.png` pour le niveau 3.
- `test_level_change_reload()` : simuler un changement de niveau et valider que `Player` recharge les surfaces (mock de l'Asset Manager).
- `test_input_increments_level()` : simuler un événement `KEYDOWN` sur `K_p` / `K_o` et vérifier que le niveau appliqué reste dans les bornes.
- `test_stats_loader_load()` : vérifier que `PlayerStatsLoader.load_stats()` charge correctement un fichier TOML valide.
- `test_stats_loader_validation()` : vérifier que la validation détecte les sections manquantes, valeurs négatives, etc.
- `test_stats_get_value()` : vérifier que `get_stat_value()` retourne les bonnes valeurs pour chaque niveau.
- `test_stats_get_max_value()` : vérifier que `get_stat_max_value()` retourne la valeur `max_value` si définie, sinon la valeur de `level_{max_level}`.
- `test_stats_max_level_load()` : vérifier le chargement de `max_level` à la racine du TOML, le défaut **5** si absent, et le rejet des valeurs invalides.
- `test_double_jump_unlock_level_load()` : vérifier le chargement de `double_jump_unlock_level`, le défaut **3** si absent, la validation **1 ≤ valeur ≤ max_level**, et le rejet des valeurs hors bornes.
- `test_stats_max_value_validation()` : vérifier que la validation détecte les `max_value` invalides (négatifs ou inférieurs aux valeurs de niveau).
- `test_player_stats_integration()` : vérifier que les stats sont correctement appliquées au `Player` lors d'un changement de niveau.
- `test_stats_missing_file()` : vérifier que le jeu continue de fonctionner si le fichier de stats est absent (valeurs par défaut).
- `test_stats_presentation_load()` : vérifier le chargement de `[presentation]` (`origins`, `class_role`, `traits`) et le rejet (ValueError) si section ou clé manquante, liste vide, ou chaîne vide après `strip()`.

### Tests d'intégration

1. Lancer le jeu au niveau 1 → vérifier visuellement les sprites.
2. Modifier le niveau dans le fichier `.niveau` à `max_level` → vérifier que les sprites correspondent aux assets du répertoire `sprite/personnage/{max_level}`.
3. Test de non-régression : déclencher un changement de niveau en jeu (si fonctionnalité ultérieure) et s'assurer que les animations (marche, saut) fonctionnent.
4. En jeu, appuyer sur `P` plusieurs fois → le niveau augmente sans dépasser `max_level` et les sprites changent. Appuyer sur `O` → le niveau diminue sans descendre sous 1.
5. **Test des caractéristiques** :
   - Charger le fichier `player_stats.toml` au démarrage.
   - Vérifier que les valeurs de stats sont correctement appliquées au personnage (ex: vitesse modifie la vitesse de déplacement).
   - Changer de niveau en jeu (touches `P`/`O`) → vérifier que les stats se mettent à jour automatiquement.
   - Vérifier que le personnage se déplace plus vite/vite selon le niveau (si la stat vitesse est utilisée).

### Vérifications automatiques

- Script optionnel pour scanner `sprite/personnage/` et s'assurer que pour chaque entier de **1** à **`max_level`** (lu depuis `player_stats.toml` ou repli documenté), le répertoire correspondant possède la liste de fichiers attendus.
- Intégrer ce script dans la CI pour éviter d'introduire un niveau incomplet ou un décalage avec `max_level`.

## Évolutions futures

- Ajouter un système d'XP et de progression qui modifie automatiquement le niveau du personnage.
- **Associer des statistiques/gameplay différents par niveau** : ✅ Implémenté via le système de caractéristiques.
- Supporter des palettes de couleurs ou effets spéciaux spécifiques par niveau.
- Permettre des variations régionales (ex: `sprite/personnage/1_eu`) via un suffixe dans la configuration.
- Ajouter des effets visuels ou sonores lors du changement de niveau.
- Permettre des caractéristiques conditionnelles (ex: bonus selon l'équipement).
- Ajouter un système de progression non-linéaire (ex: choix de spécialisation qui modifie les stats).

## Exemple de fichier de caractéristiques

Un fichier d'exemple complet avec 3 caractéristiques (force, intelligence, vitesse) :

```toml
# Fichier : config/player_stats.toml
# Configuration des caractéristiques du personnage par niveau
max_level = 5
double_jump_unlock_level = 3
display_name = "Thomas Tourret"
# Chaque caractéristique définit level_1 … level_{max_level}

[presentation]
origins = [
    "Background : Chef.fe de projet technique (pas issu.e de la data)",
    "Déclic : Il y a 5 ans, découverte du machine learning.",
    "Mantra : Faire, mesurer, apprendre.",
]
class_role = [
    "Classe : Project Mage (hybride Tech/Produit)",
    "Sous-classe : Explorateur·rice ML (apprentissage accéléré)",
    "Alignement : Curiosité bienveillante",
]
traits = [
    "Bidouilleur.se empirique → en rééducation vers méthodique",
    "Pont entre métiers et data",
    "Aime prototyper vite, accepte l'itération",
]

[stats.force]
name = "Force"
description = "Puissance physique du personnage, influence les dégâts infligés"
tooltip_level_1 = "Force de base : Vous commencez votre aventure avec une force modeste. Vos attaques physiques infligent des dégâts basiques."
tooltip_level_2 = "Force améliorée : Votre entraînement porte ses fruits. Vos coups sont plus puissants et vous pouvez porter des équipements plus lourds."
tooltip_level_3 = "Force avancée : Votre force physique est remarquable. Les ennemis redoutent vos attaques dévastatrices."
tooltip_level_4 = "Force experte : Vous maîtrisez parfaitement votre force brute. Vos dégâts sont considérablement augmentés."
tooltip_level_5 = "Force maîtrisée : Vous avez atteint le summum de la puissance physique. Vos attaques peuvent terrasser les ennemis les plus résistants."
level_1 = 10
level_2 = 20
level_3 = 35
level_4 = 55
level_5 = 80

[stats.intelligence]
name = "Intelligence"
description = "Capacité intellectuelle du personnage, influence les compétences spéciales"
tooltip_level_1 = "Intelligence de base : Votre esprit est vif mais encore en développement. Vous pouvez utiliser des compétences basiques."
tooltip_level_2 = "Intelligence améliorée : Votre compréhension s'approfondit. Les compétences spéciales deviennent plus efficaces."
tooltip_level_3 = "Intelligence avancée : Votre sagesse est reconnue. Vous résolvez les énigmes avec facilité et maîtrisez des sorts puissants."
tooltip_level_4 = "Intelligence experte : Votre intellect est exceptionnel. Les compétences magiques atteignent leur plein potentiel."
tooltip_level_5 = "Intelligence maîtrisée : Votre sagesse est légendaire. Vous pouvez déchiffrer les mystères les plus complexes et utiliser les sorts les plus puissants."
level_1 = 8
level_2 = 18
level_3 = 32
level_4 = 52
level_5 = 75

[stats.vitesse]
name = "Vitesse"
description = "Rapidité de déplacement du personnage, influence la vitesse de marche"
tooltip_level_1 = "Vitesse de base : Vous vous déplacez à un rythme normal. L'agilité viendra avec l'expérience."
tooltip_level_2 = "Vitesse améliorée : Vos réflexes s'aiguisent. Vous esquivez plus facilement les attaques ennemies."
tooltip_level_3 = "Vitesse avancée : Votre agilité est remarquable. Vous vous déplacez rapidement et attaquez plus vite."
tooltip_level_4 = "Vitesse experte : Vos mouvements sont presque instantanés. Les ennemis ont du mal à vous suivre."
tooltip_level_5 = "Vitesse maîtrisée : Vous êtes d'une rapidité légendaire. Vos déplacements sont fulgurants et vos attaques sont extrêmement rapides."
level_1 = 12
level_2 = 22
level_3 = 38
level_4 = 58
level_5 = 85
max_value = 100  # Valeur maximale explicite (optionnel)
```

**Notes sur l'exemple** :
- Les valeurs sont arbitraires et peuvent être ajustées selon les besoins du gameplay.
- La progression peut être linéaire, exponentielle, ou personnalisée selon le design du jeu.
- Les valeurs peuvent être des entiers ou des nombres décimaux (ex: `level_1 = 10.5`).
- Chaque caractéristique peut avoir une progression différente (ex: force augmente plus vite que intelligence).
- Les tooltips peuvent être différents pour chaque niveau, permettant d'expliquer l'évolution de la caractéristique au fil de la progression.
- Si un `tooltip_level_N` n'est pas défini, aucun tooltip ne s'affichera pour ce niveau spécifique, mais l'icône d'information sera toujours visible.
- **Valeur maximale** : Le champ `max_value` est optionnel. S'il n'est pas défini, la valeur maximale est automatiquement déterminée par la valeur de `level_{max_level}` (comportement par défaut pour rétrocompatibilité). Si `max_value` est défini, cette valeur est utilisée comme maximum pour l'affichage et les calculs de pourcentage, indépendamment de la valeur de `level_{max_level}`. Cela permet par exemple d'avoir une statistique qui va de 0 à 100 même si la valeur au dernier niveau est inférieure (ex. `level_5 = 75` lorsque `max_level = 5`), ou d'avoir des statistiques avec des maximums différents (ex: force max = 100, intelligence max = 80).

## Structure de fichiers recommandée

```
moteur_jeu_presentation/
├── config/
│   └── player_stats.toml          # Fichier de caractéristiques
├── src/
│   └── moteur_jeu_presentation/
│       ├── entities/
│       │   ├── player.py          # Classe Player (modifiée)
│       │   └── player_level_manager.py  # PlayerLevelManager (modifié)
│       └── stats/
│           ├── __init__.py
│           ├── loader.py          # PlayerStatsLoader
│           └── config.py          # PlayerStatsConfig, StatDefinition
└── ...
```

## Cohérence avec les autres spécifications

Les spécifications **2**, **6**, **10**, **11**, **12** et **17** peuvent encore mentionner `MAX_PLAYER_LEVEL` ou le nombre **5** à titre d’exemple : le comportement effectif est **`max_level`** dans `config/player_stats.toml` (repli **5** sans fichier stats ou sans clé).

Le **seuil du double saut** n’est plus le nombre **3** figé dans le code : il est défini par **`double_jump_unlock_level`** à la racine de `config/player_stats.toml` (défaut **3** si absent), comme précisé dans la spécification **6**.

Le **nom affiché du joueur** (au-dessus du sprite, titre de l’UI stats) est défini par **`display_name`** à la racine de `config/player_stats.toml` (obligatoire, sans défaut dans `Player`) — spécifications **2** et **10**.

Les **textes de la colonne présentation** de l’UI stats (Origines, Classe & Rôle, traits) sont définis par la table **`[presentation]`** (`origins`, `class_role`, `traits` : listes de chaînes, obligatoires si le fichier est chargé — spécification **10**). Le chargeur (`loader.py`), `PlayerStatsConfig` et l’UI consomment cette section.

---

**Statut** : ✅ Implémenté
