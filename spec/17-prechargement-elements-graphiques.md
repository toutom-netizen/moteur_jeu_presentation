# 17 - Préchargement des éléments graphiques

## Contexte

Cette spécification définit un système de préchargement complet de tous les éléments graphiques du jeu avant l'affichage de l'écran d'accueil. Le préchargement permet d'éviter les freezes et les ralentissements lors du premier affichage des sprites, en mettant en cache tous les éléments graphiques nécessaires au démarrage du jeu. Une barre de chargement visuelle et des logs détaillés dans la console permettent de suivre la progression du chargement.

## Objectifs

- Précharger tous les éléments graphiques du jeu avant l'écran d'accueil
- Afficher une barre de chargement montrant l'évolution du préchargement
- Afficher des logs détaillés dans la console pour chaque catégorie d'éléments chargés
- Éviter les freezes et ralentissements lors du premier affichage des sprites
- Optimiser les performances en mettant en cache tous les sprites nécessaires
- Permettre de sauter le préchargement via un paramètre en ligne de commande (utile pour le développement)

## Architecture

### Ordre de préchargement

Le préchargement suit un ordre logique pour optimiser l'expérience utilisateur :

1. **Sprites de niveau** : Tous les sprite sheets et sprites extraits des layers du niveau
2. **Sprites du joueur** : Toutes les frames de toutes les animations du joueur (walk, jump, climb, dialogue)
3. **Sprites des PNJ** : Tous les sprite sheets et frames des PNJ du niveau
4. **Sprites d'inventaire** : Tous les sprite sheets et sprites extraits des objets d'inventaire
5. **Images de dialogue** : Toutes les images utilisées dans les dialogues des PNJ
6. **Autres éléments graphiques** : Tous les autres éléments graphiques (particules, UI, etc.)

### Barre de chargement

La barre de chargement doit :
- S'afficher sur un écran noir ou avec un fond simple
- Montrer la progression globale du chargement (0% à 100%)
- Afficher le nom de la catégorie en cours de chargement
- Afficher le nombre d'éléments chargés sur le total (ex: "Chargement des sprites du joueur... 45/64")
- **Être mise à jour de manière continue et progressive pendant le chargement de chaque catégorie** (après chaque élément chargé : sprite sheet, sprite extrait, frame, etc.)
- Utiliser un style visuel cohérent avec le jeu

**Important** : La progression doit être mise à jour **après chaque élément chargé**, pas uniquement à la fin d'une catégorie. Cela permet d'avoir un feedback visuel en temps réel et une progression fluide de la barre de chargement.

### Logs dans la console

Pour chaque catégorie d'éléments chargés, des logs détaillés doivent apparaître dans la console :

```
[Préchargement] Début du préchargement des éléments graphiques...
[Préchargement] Chargement des sprites de niveau...
[Préchargement]   - Sprite sheet 'terrain' : 1 image chargée
[Préchargement]   - Sprite sheet 'background' : 1 image chargée
[Préchargement]   - Sprites extraits : 156 images chargées
[Préchargement]   - Sprites redimensionnés préchargés : 42 images
[Préchargement] Sprites de niveau chargés : 200 images au total
[Préchargement] Chargement des sprites du joueur...
[Préchargement]   - Niveau 1 : 64 frames chargées (walk: 32, jump: 16, climb: 16) avec scaling 2.0x -> 85x85
[Préchargement]   - Niveau 2 : 64 frames chargées (walk: 32, jump: 16, climb: 16) avec scaling 2.0x -> 85x85
[Préchargement]   - Niveau 3 : 64 frames chargées (walk: 32, jump: 16, climb: 16) avec scaling 2.0x -> 85x85
[Préchargement]   - Niveau 4 : 64 frames chargées (walk: 32, jump: 16, climb: 16) avec scaling 2.0x -> 85x85
[Préchargement]   - Niveau 5 : 64 frames chargées (walk: 32, jump: 16, climb: 16) avec scaling 2.0x -> 85x85
[Préchargement] Sprites du joueur chargés : 320 frames au total
[Préchargement] Chargement des sprites des PNJ...
[Préchargement]   - PNJ 'npc_1' : 1 sprite sheet + 24 frames chargées
[Préchargement]   - PNJ 'npc_2' : 1 sprite sheet + 16 frames chargées
[Préchargement] Sprites des PNJ chargés : 2 sprite sheets + 40 frames au total
[Préchargement] Chargement des sprites d'inventaire...
[Préchargement]   - Sprite sheet 'outils_niveau_decouverte.png' : 1 image chargée
[Préchargement]   - Sprites extraits : 8 images chargées
[Préchargement] Sprites d'inventaire chargés : 9 images au total
[Préchargement] Chargement des images de dialogue...
[Préchargement]   - 12 images de dialogue chargées
[Préchargement] Images de dialogue chargées : 12 images au total
[Préchargement] Préchargement terminé : 541 images chargées au total
```

## Spécifications techniques

### Caches globaux partagés

Pour éviter de recharger les mêmes assets plusieurs fois et garantir que le préchargement est effectivement utilisé par les composants, le système utilise des **caches globaux partagés** définis dans `src/moteur_jeu_presentation/assets/preloader.py`.

#### Caches disponibles

**`_global_level_sprite_sheet_cache: Dict[str, pygame.Surface]`**
- Cache global pour les sprite sheets de niveau
- **Clé** : nom du sprite sheet (str) tel que défini dans la configuration du niveau
- **Valeur** : Surface pygame du sprite sheet chargé
- **Utilisé par** : `LevelLoader.create_parallax_layers()`
- **Rempli par** : `AssetPreloader._preload_level_sprites()`

**`_global_level_scaled_sprite_cache: Dict[tuple[str, int, int, float], pygame.Surface]`**
- Cache global pour les sprites de niveau redimensionnés (avec scaling appliqué)
- **Clé** : tuple `(sheet_name, row, col, scale)` où :
  - `sheet_name` : nom du sprite sheet (str)
  - `row` : ligne du sprite dans le sprite sheet (int)
  - `col` : colonne du sprite dans le sprite sheet (int)
  - `scale` : facteur de redimensionnement (float)
- **Valeur** : Surface pygame du sprite extrait et redimensionné
- **Utilisé par** : `LevelLoader.create_parallax_layers()` (fonction `get_scaled_sprite`)
- **Rempli par** : `AssetPreloader._preload_level_sprites()` (précharge tous les sprites individuels avec leur scaling)
- **Note** : Le scaling est appliqué selon la même logique que dans `loader.py` : d'abord dans le repère de conception (1920x1080), puis conversion vers la résolution interne (1280x720)

**`_global_inventory_sprite_sheet_cache: Dict[str, pygame.Surface]`**
- Cache global pour les sprite sheets d'inventaire
- **Clé** : chemin absolu du sprite sheet (str)
- **Valeur** : Surface pygame du sprite sheet chargé
- **Utilisé par** : `Inventory` (via référence directe dans `__init__`)
- **Rempli par** : `AssetPreloader._preload_inventory_sprites()`

**`_global_inventory_cached_surfaces: Dict[str, pygame.Surface]`**
- Cache global pour les sprites extraits d'inventaire
- **Clé** : item_id (str)
- **Valeur** : Surface pygame du sprite extrait
- **Utilisé par** : `Inventory` (via référence directe dans `__init__`)
- **Rempli par** : `AssetPreloader._preload_inventory_sprites()`

**`_global_npc_sprite_sheet_cache: Dict[str, pygame.Surface]`**
- Cache global pour les sprite sheets des PNJ
- **Clé** : chemin absolu du sprite sheet (str)
- **Valeur** : Surface pygame du sprite sheet chargé
- **Utilisé par** : `NPC.__init__()` et `NPC.change_sprite_sheet()`
- **Rempli par** : `AssetPreloader._preload_npc_sprites()`

**`_global_npc_scaled_sprite_cache: Dict[tuple[str, int, int, int, int], pygame.Surface]`**
- Cache global pour les sprites des PNJ redimensionnés (avec scaling appliqué)
- **Clé** : tuple `(sprite_path_key, row, col, display_width, display_height)` où :
  - `sprite_path_key` : chemin absolu du sprite sheet (str)
  - `row` : ligne du sprite dans le sprite sheet (0-based)
  - `col` : colonne du sprite dans le sprite sheet (0-based)
  - `display_width` : largeur d'affichage après scaling (int)
  - `display_height` : hauteur d'affichage après scaling (int)
- **Valeur** : Surface pygame du sprite extrait et redimensionné
- **Utilisé par** : `NPC._get_sprite_at()`
- **Rempli par** : `AssetPreloader._preload_npc_sprites()` (précharge tous les sprites utilisés par les animations avec scaling appliqué)
- **Note** : Le scaling est appliqué selon la même logique que dans `NPC.__init__` : d'abord dans le repère de conception (1920x1080), puis conversion vers la résolution interne (1280x720)

**`_global_npc_scaled_flipped_sprite_cache: Dict[tuple[str, int, int, int, int], pygame.Surface]`**
- Cache global pour les sprites des PNJ redimensionnés et retournés horizontalement
- **Clé** : même format que `_global_npc_scaled_sprite_cache`
- **Valeur** : Surface pygame du sprite extrait, redimensionné et retourné horizontalement
- **Utilisé par** : `NPC._get_flipped_sprite()`
- **Rempli par** : `AssetPreloader._preload_npc_sprites()` (précharge tous les sprites utilisés par les animations avec scaling et flip appliqués)
- **Note** : Permet d'éviter le flip à la volée lors de l'affichage des NPC orientés vers la gauche

**`_global_image_cache: Dict[str, pygame.Surface]`** (défini dans `ui/speech_bubble.py`)
- Cache global pour les images de dialogue
- **Clé** : chemin absolu de l'image (str)
- **Valeur** : Surface pygame de l'image chargée
- **Utilisé par** : `SpeechBubble._load_image()`
- **Rempli par** : `preload_dialogue_images()` (appelée par `AssetPreloader._preload_dialogue_images()`)

**`_global_player_sprite_sheet_cache: Dict[str, pygame.Surface]`**
- Cache global pour les sprite sheets du joueur
- **Clé** : chemin absolu du sprite sheet (str)
- **Valeur** : Surface pygame du sprite sheet chargé
- **Utilisé par** : `Player._reload_assets()` (pour walk.png, jump.png, climb.png)
- **Rempli par** : `AssetPreloader._preload_player_sprites()`
- **Note** : Permet d'éviter de recharger les sprite sheets depuis le disque lors de l'initialisation du Player

**`_global_player_scaled_sprite_cache: Dict[tuple[int, str, int, int, int, int], pygame.Surface]`**
- Cache global pour les sprites du joueur redimensionnés (avec scaling appliqué)
- **Clé** : tuple `(level, animation_type, row, col, display_width, display_height)` où :
  - `level` : niveau du joueur (1-5)
  - `animation_type` : type d'animation ("walk", "jump", "climb")
  - `row` : ligne du sprite dans le sprite sheet (0-based)
  - `col` : colonne du sprite dans le sprite sheet (0-based)
  - `display_width` : largeur d'affichage après scaling (int)
  - `display_height` : hauteur d'affichage après scaling (int)
- **Valeur** : Surface pygame du sprite extrait et redimensionné
- **Utilisé par** : `Player._get_sprite_at()`, `Player._get_sprite_at_jump()`, `Player._get_sprite_at_climb()`
- **Rempli par** : `AssetPreloader._preload_player_sprites()` (précharge tous les sprites avec scaling appliqué)
- **Note** : Le scaling est appliqué selon la même logique que dans `Player.__init__` : d'abord dans le repère de conception (1920x1080), puis conversion vers la résolution interne (1280x720)

#### Fonctionnement des caches partagés

1. **Lors du préchargement** : L'`AssetPreloader` remplit tous les caches globaux en chargeant les assets depuis le disque et en appliquant les transformations nécessaires (redimensionnement, extraction, etc.)
2. **Lors de l'utilisation** : Les composants (`LevelLoader`, `Player`, `Inventory`, `NPC`, `SpeechBubble`) vérifient d'abord le cache global avant de charger depuis le disque ou d'effectuer des transformations coûteuses
3. **Fallback** : Si un asset n'est pas dans le cache (par exemple si `--skip-preload` est utilisé), il est chargé depuis le disque de manière traditionnelle et les transformations sont effectuées à la volée

**Exemple de code (NPC - sprite sheets)** :

```python
# Dans NPC.__init__
from ..assets.preloader import _global_npc_sprite_sheet_cache

sprite_path_key = str(sprite_path.resolve())

# Vérifier d'abord le cache global
if sprite_path_key in _global_npc_sprite_sheet_cache:
    self.sprite_sheet = _global_npc_sprite_sheet_cache[sprite_path_key]
else:
    # Charger depuis le disque si pas en cache
    self.sprite_sheet = pygame.image.load(str(sprite_path)).convert_alpha()
```

**Exemple de code (NPC - sprites redimensionnés)** :

```python
# Dans NPC._get_sprite_at
from ..assets.preloader import _global_npc_scaled_sprite_cache

# Si le sprite doit être redimensionné, vérifier d'abord le cache global préchargé
if self.sprite_scale != 1.0:
    sprite_path_key = str(sprite_path.resolve())
    global_cache_key = (sprite_path_key, safe_row, safe_col, int(self.display_width), int(self.display_height))
    
    # Vérifier le cache global préchargé
    if global_cache_key in _global_npc_scaled_sprite_cache:
        return _global_npc_scaled_sprite_cache[global_cache_key]
    
    # Fallback : redimensionner à la volée et mettre en cache localement
    # ...
```

**Exemple de code (NPC - sprites retournés)** :

```python
# Dans NPC._get_flipped_sprite
from ..assets.preloader import _global_npc_scaled_flipped_sprite_cache

# Si le sprite doit être redimensionné, vérifier d'abord le cache global préchargé
if self.sprite_scale != 1.0:
    sprite_path_key = str(sprite_path.resolve())
    global_cache_key = (sprite_path_key, safe_row, safe_col, int(self.display_width), int(self.display_height))
    
    # Vérifier le cache global préchargé
    if global_cache_key in _global_npc_scaled_flipped_sprite_cache:
        return _global_npc_scaled_flipped_sprite_cache[global_cache_key]
    
    # Fallback : retourner et redimensionner à la volée et mettre en cache localement
    # ...
```

**Exemple de code (LevelLoader - sprites redimensionnés)** :

```python
# Dans LevelLoader.create_parallax_layers
from ..assets.preloader import _global_level_scaled_sprite_cache

def get_scaled_sprite(sprite_row: int, sprite_col: int) -> tuple[pygame.Surface, int, int]:
    cache_key = (sheet_name, sprite_row, sprite_col, scale)
    
    # Vérifier d'abord le cache global (préchargement)
    if cache_key in _global_level_scaled_sprite_cache:
        sprite = _global_level_scaled_sprite_cache[cache_key]
        return (sprite, sprite.get_width(), sprite.get_height())
    
    # Sinon, extraire et redimensionner à la volée
    # ...
```

**Exemple de code (Player - sprite sheets)** :

```python
# Dans Player._reload_assets
from ..assets.preloader import _global_player_sprite_sheet_cache

walk_path = self._resolve_asset_path(self._walk_override_path, self.WALK_SHEET_NAME)
walk_path_key = str(walk_path.resolve())

# Vérifier d'abord le cache global (préchargement)
if walk_path_key in _global_player_sprite_sheet_cache:
    self.sprite_sheet = _global_player_sprite_sheet_cache[walk_path_key]
else:
    # Charger depuis le disque si pas en cache
    self.sprite_sheet = pygame.image.load(str(walk_path)).convert_alpha()
```

**Exemple de code (Player - sprites redimensionnés)** :

```python
# Dans Player._get_sprite_at
from ..assets.preloader import _global_player_scaled_sprite_cache

# Vérifier d'abord le cache global des sprites redimensionnés (préchargement)
if self.sprite_scale != 1.0:
    global_cache_key = (
        self.player_level, "walk", row, col,
        int(self.display_width), int(self.display_height)
    )
    if global_cache_key in _global_player_scaled_sprite_cache:
        return _global_player_scaled_sprite_cache[global_cache_key]

# Sinon, utiliser le cache local ou redimensionner à la volée
# ...
```

**Avantages** :
- Garantit que le préchargement est effectivement utilisé
- Évite les rechargements multiples du même asset
- Permet un fallback transparent si le préchargement est désactivé
- Partage automatique des caches entre toutes les instances (plusieurs inventaires, plusieurs PNJ, etc.)

### Structure des données

#### Classe `AssetPreloader`

```python
class AssetPreloader:
    """Gère le préchargement de tous les éléments graphiques du jeu."""
    
    def __init__(
        self,
        screen: pygame.Surface,
        screen_width: int,
        screen_height: int,
        project_root: Path,
    ) -> None:
        """
        Args:
            screen: Surface pygame pour afficher la barre de chargement
            screen_width: Largeur de l'écran de rendu
            screen_height: Hauteur de l'écran de rendu
            project_root: Chemin racine du projet
        """
```

**Propriétés** :
- `screen: pygame.Surface` : Surface pour afficher la barre de chargement
- `screen_width: int` : Largeur de l'écran
- `screen_height: int` : Hauteur de l'écran
- `project_root: Path` : Chemin racine du projet
- `progress: float` : Progression actuelle (0.0 à 1.0)
- `current_category: str` : Nom de la catégorie en cours de chargement
- `current_count: int` : Nombre d'éléments chargés dans la catégorie actuelle
- `current_total: int` : Nombre total d'éléments dans la catégorie actuelle
- `total_loaded: int` : Nombre total d'éléments chargés
- `total_to_load: int` : Nombre total d'éléments à charger
- `loading_stats: Dict[str, int]` : Statistiques de chargement par catégorie

**Méthodes principales** :
- `preload_all_assets(level_config, npcs_config, inventory_config, stats_config, player_level) -> Dict[str, Any]` : Précharge tous les éléments graphiques
- `_preload_level_sprites(level_config) -> int` : Précharge les sprites de niveau
- `_preload_player_sprites(stats_config, player_level) -> int` : Précharge les sprites du joueur
- `_preload_npc_sprites(npcs_config) -> int` : Précharge les sprites des PNJ
- `_preload_inventory_sprites(inventory_config) -> int` : Précharge les sprites d'inventaire
- `_preload_dialogue_images(npcs_config) -> int` : Précharge les images de dialogue
- `_update_progress(category: str, current: int, total: int) -> None` : Met à jour la progression et redessine la barre de chargement
- `_estimate_total_items(level_config, npcs_config, inventory_config, stats_config) -> int` : Estime le nombre total d'éléments à charger
- `_log_category_start(category: str) -> None` : Log le début d'une catégorie
- `_log_category_end(category: str, count: int) -> None` : Log la fin d'une catégorie
- `_log_total() -> None` : Log le total final

**Règle importante** : Chaque méthode de préchargement (`_preload_*`) doit :
1. **Calculer le nombre total d'éléments à charger** avant de commencer (ou utiliser une estimation précise)
2. **Appeler `_update_progress()` après chaque élément chargé** (sprite sheet, sprite extrait, frame, etc.)
3. **Appeler `pygame.event.pump()` après chaque mise à jour** pour éviter que la fenêtre soit marquée comme "non répondante"
4. **Mettre à jour `self.total_loaded`** au fur et à mesure pour calculer la progression globale

#### Classe `LoadingBar`

```python
class LoadingBar:
    """Gère l'affichage de la barre de chargement."""
    
    def __init__(
        self,
        screen: pygame.Surface,
        screen_width: int,
        screen_height: int,
    ) -> None:
        """
        Args:
            screen: Surface pygame pour dessiner la barre
            screen_width: Largeur de l'écran
            screen_height: Hauteur de l'écran
        """
```

**Propriétés** :
- `screen: pygame.Surface` : Surface pour dessiner
- `screen_width: int` : Largeur de l'écran
- `screen_height: int` : Hauteur de l'écran
- `bar_width: int` : Largeur de la barre de progression (défaut: 600 pixels)
- `bar_height: int` : Hauteur de la barre de progression (défaut: 30 pixels)
- `bar_x: int` : Position X de la barre (centrée)
- `bar_y: int` : Position Y de la barre (centrée verticalement)
- `bar_color: Tuple[int, int, int]` : Couleur de la barre de progression (défaut: (74, 149, 172))
- `bar_bg_color: Tuple[int, int, int]` : Couleur de fond de la barre (défaut: (50, 50, 50))
- `text_color: Tuple[int, int, int]` : Couleur du texte (défaut: (255, 255, 255))
- `font: pygame.font.Font` : Police pour le texte

**Méthodes principales** :
- `draw(progress: float, category: str, current: int, total: int) -> None` : Dessine la barre de chargement
- `_draw_bar_background() -> None` : Dessine le fond de la barre
- `_draw_bar_progress(progress: float) -> None` : Dessine la progression
- `_draw_text(category: str, current: int, total: int) -> None` : Dessine le texte

### Préchargement des sprites de niveau

Le préchargement des sprites de niveau doit :
- **Calculer le nombre total d'éléments à charger** avant de commencer (sprite sheets + sprites extraits + sprites redimensionnés)
- Charger tous les sprite sheets définis dans la configuration du niveau
- **Mettre à jour la progression après chaque sprite sheet chargé**
- Extraire tous les sprites utilisés dans les layers du niveau
- **Précharger tous les sprites individuels avec leur scaling appliqué** (nouveau)
- **Mettre à jour la progression après chaque sprite redimensionné préchargé**
- Mettre en cache tous les sprites redimensionnés dans `_global_level_scaled_sprite_cache`
- Compter et logger chaque sprite sheet et sprite extrait

**Important** : Le préchargement prend maintenant en compte le scaling défini pour chaque sprite individuel (`scale` dans `SpriteMapping`). Les sprites sont redimensionnés selon la même logique que dans `loader.py` :
1. Application du scale dans le repère de conception (1920x1080)
2. Conversion vers la résolution interne (1280x720)
3. Redimensionnement avec `pygame.transform.smoothscale()` si nécessaire

**Progression continue** : La méthode doit appeler `_update_progress()` après chaque élément chargé :
- Après chaque sprite sheet chargé
- Après chaque sprite redimensionné préchargé
- Appeler `pygame.event.pump()` après chaque mise à jour pour maintenir la réactivité de la fenêtre

```python
def _preload_level_sprites(self, level_config: LevelConfig) -> int:
    """Précharge tous les sprites de niveau.
    
    Args:
        level_config: Configuration du niveau
        
    Returns:
        Nombre total d'images chargées (sprite sheets + sprites extraits)
    """
    from ..rendering.config import compute_design_scale
    
    count = 0
    
    # Calculer les facteurs de conversion (même logique que dans loader.py)
    scale_x, scale_y = compute_design_scale((self.screen_width, self.screen_height))
    
    # Charger tous les sprite sheets
    for sheet_name, sheet_config in level_config.sprite_sheets.items():
        if not sheet_config.path.exists():
            continue
        
        sprite_sheet = pygame.image.load(str(sheet_config.path)).convert_alpha()
        _global_level_sprite_sheet_cache[sheet_name] = sprite_sheet
        count += 1
        print(f"[Préchargement]   - Sprite sheet '{sheet_name}' : 1 image chargée")
    
    # Précharger tous les sprites individuels avec leur scaling appliqué
    for sprite_mapping in level_config.sprites:
        sheet_name = sprite_mapping.sheet
        scale = sprite_mapping.scale
        
        # Extraire et redimensionner le sprite selon le scale
        # (même logique que dans loader.py)
        # ...
        
        # Mettre en cache dans _global_level_scaled_sprite_cache
        cache_key = (sheet_name, row, col, scale)
        _global_level_scaled_sprite_cache[cache_key] = scaled_sprite
        count += 1
    
    return count
```

### Préchargement des sprites du joueur

Le préchargement des sprites du joueur doit :
- **Calculer le nombre total de frames à charger** avant de commencer (5 niveaux × 3 animations × ~32 frames = ~480 frames)
- Précharger les sprites pour tous les niveaux du joueur (1 à 5)
- Précharger toutes les frames de toutes les animations (walk, jump, climb, dialogue)
- **Mettre à jour la progression après chaque frame chargée et redimensionnée** (ou par petits lots pour éviter trop de mises à jour)
- **Précharger les sprites redimensionnés avec le scaling défini** (sprite_scale = 2.0 par défaut)
- **Mettre en cache les sprite sheets dans `_global_player_sprite_sheet_cache`**
- **Mettre en cache les sprites redimensionnés dans `_global_player_scaled_sprite_cache`**
- Compter et logger les frames par niveau et par animation

**Important** : Le préchargement applique le même scaling que la classe `Player` :
1. Calcul des dimensions d'affichage avec `sprite_scale = 2.0` (défaut)
2. Application du scale dans le repère de conception (1920x1080)
3. Conversion vers la résolution interne (1280x720)
4. Redimensionnement de toutes les frames avec `pygame.transform.smoothscale()`

**Utilisation du cache** : Le `Player` vérifie d'abord les caches globaux avant de charger depuis le disque ou de redimensionner à la volée :
- `Player._reload_assets()` utilise `_global_player_sprite_sheet_cache` pour éviter de recharger les sprite sheets
- `Player._get_sprite_at()`, `Player._get_sprite_at_jump()`, `Player._get_sprite_at_climb()` utilisent `_global_player_scaled_sprite_cache` pour éviter de redimensionner les sprites à chaque frame

**Progression continue** : La méthode doit appeler `_update_progress()` régulièrement pendant le chargement :
- Après chaque sprite sheet chargé (walk.png, jump.png, climb.png)
- Après chaque batch de frames chargées (par exemple, après chaque ligne ou colonne complète, ou après chaque animation complète)
- Appeler `pygame.event.pump()` après chaque mise à jour pour maintenir la réactivité de la fenêtre

```python
def _preload_player_sprites(
    self,
    stats_config: Optional[PlayerStatsConfig],
    player_level: int,
) -> int:
    """Précharge tous les sprites du joueur.
    
    Args:
        stats_config: Configuration des stats du joueur
        player_level: Niveau initial du joueur
        
    Returns:
        Nombre total de frames chargées
    """
    from ..rendering.config import compute_design_scale, get_render_size
    
    # Calculer le scaling (même logique que dans Player.__init__)
    render_width, render_height = get_render_size()
    scale_x, scale_y = compute_design_scale((render_width, render_height))
    
    # Utiliser le même sprite_scale que Player (défaut: 2.0)
    sprite_scale = 2.0
    sprite_width = 64
    sprite_height = 64
    
    # Calculer les dimensions d'affichage (même logique que dans Player.__init__)
    scaled_width_in_design = sprite_width * sprite_scale
    scaled_height_in_design = sprite_height * sprite_scale
    display_width = int(scaled_width_in_design * scale_x)
    display_height = int(scaled_height_in_design * scale_y)
    
    total_frames = 0
    
    # Précharger pour tous les niveaux (1 à 5)
    for level in range(1, 6):
        # Charger les sprite sheets du niveau
        walk_sheet = self._load_player_sprite_sheet(level, "walk.png")
        jump_sheet = self._load_player_sprite_sheet(level, "jump.png")
        climb_sheet = self._load_player_sprite_sheet(level, "climb.png")
        
        # Extraire toutes les frames de chaque animation
        walk_frames = self._extract_all_frames(walk_sheet, 64, 64, 4, 8)
        jump_frames = self._extract_all_frames(jump_sheet, 64, 64, 4, 8)
        climb_frames = self._extract_all_frames(climb_sheet, 64, 64, 4, 8)
        
        # Extraire toutes les frames et les redimensionner, puis mettre en cache global
        for row in range(4):
            for col in range(8):
                # Extraire la frame
                x = col * 64
                y = row * 64
                rect = pygame.Rect(x, y, 64, 64)
                frame = walk_sheet.subsurface(rect).copy()
                frame = frame.convert_alpha()
                
                # Redimensionner avec le scaling
                scaled_frame = pygame.transform.smoothscale(
                    frame, (display_width, display_height)
                )
                scaled_frame = scaled_frame.convert_alpha()
                
                # Mettre en cache global
                cache_key = (level, "walk", row, col, display_width, display_height)
                _global_player_scaled_sprite_cache[cache_key] = scaled_frame
        
        # Même logique pour jump.png et climb.png
        # ...
        
        # Mettre en cache les sprite sheets
        walk_path_key = str(Path(walk_path).resolve())
        _global_player_sprite_sheet_cache[walk_path_key] = walk_sheet
        
        level_total = len(walk_frames) + len(jump_frames) + len(climb_frames)
        total_frames += level_total
        
        print(
            f"[Préchargement]   - Niveau {level} : {level_total} frames chargées "
            f"(walk: {len(walk_frames)}, jump: {len(jump_frames)}, climb: {len(climb_frames)}) "
            f"avec scaling {sprite_scale}x -> {display_width}x{display_height}"
        )
    
    return total_frames
```

### Préchargement des sprites des PNJ

Le préchargement des sprites des PNJ doit :
- **Calculer le nombre total d'éléments à charger** avant de commencer (sprite sheets + sprites redimensionnés pour chaque PNJ)
- Charger tous les sprite sheets des PNJ définis dans la configuration
- **Mettre à jour la progression après chaque sprite sheet chargé**
- Extraire toutes les frames utilisées par chaque PNJ
- **Mettre à jour la progression après chaque sprite redimensionné préchargé** (ou par petits lots)
- Mettre en cache les sprites redimensionnés
- Compter et logger les sprite sheets et frames par PNJ

**Progression continue** : La méthode doit appeler `_update_progress()` après chaque élément chargé :
- Après chaque sprite sheet chargé
- Après chaque sprite redimensionné préchargé (ou après chaque animation complète pour éviter trop de mises à jour)
- Appeler `pygame.event.pump()` après chaque mise à jour pour maintenir la réactivité de la fenêtre

```python
def _preload_npc_sprites(self, npcs_config: NPCsConfig) -> int:
    """Précharge tous les sprites des PNJ.
    
    Args:
        npcs_config: Configuration des PNJ
        
    Returns:
        Nombre total d'images chargées (sprite sheets + frames extraites)
    """
    total_count = 0
    
    for npc_config in npcs_config.npcs:
        # Charger le sprite sheet du PNJ
        sprite_path = Path(npc_config.sprite_sheet_path)
        if not sprite_path.is_absolute():
            sprite_path = self.project_root / sprite_path
        
        if sprite_path.exists():
            sprite_sheet = pygame.image.load(str(sprite_path)).convert_alpha()
            total_count += 1
            
            # Extraire toutes les frames utilisées par les animations
            frames_count = self._extract_npc_frames(npc_config, sprite_sheet)
            total_count += frames_count
            
            print(
                f"[Préchargement]   - PNJ '{npc_config.id}' : "
                f"1 sprite sheet + {frames_count} frames chargées"
            )
    
    return total_count
```

### Préchargement des sprites d'inventaire

Le préchargement des sprites d'inventaire doit :
- **Calculer le nombre total d'éléments à charger** avant de commencer (sprite sheets + sprites extraits)
- Charger tous les sprite sheets et extraire tous les sprites
- **Mettre à jour la progression après chaque objet d'inventaire traité** (sprite sheet + sprite extrait)
- Logger le nombre de sprite sheets et de sprites extraits

**Progression continue** : La méthode doit appeler `_update_progress()` après chaque objet d'inventaire traité :
- Après chaque sprite sheet chargé (si nouveau)
- Après chaque sprite extrait et mis en cache
- Appeler `pygame.event.pump()` après chaque mise à jour pour maintenir la réactivité de la fenêtre

```python
def _preload_inventory_sprites(
    self,
    inventory_config: Optional[InventoryItemConfig],
) -> int:
    """Précharge tous les sprites d'inventaire.
    
    Args:
        inventory_config: Configuration des objets d'inventaire
        
    Returns:
        Nombre total d'images chargées (sprite sheets + sprites extraits)
    """
    if inventory_config is None:
        return 0
    
    # Créer un inventaire temporaire pour le préchargement
    from moteur_jeu_presentation.inventory import Inventory
    temp_inventory = Inventory(item_config=inventory_config)
    temp_inventory.preload_all_sprites()
    
    # Compter les sprite sheets et les sprites extraits
    sprite_sheets_count = len(temp_inventory._sprite_sheet_cache)
    sprites_count = len(temp_inventory._cached_surfaces)
    
    print(
        f"[Préchargement]   - Sprite sheets : {sprite_sheets_count} images chargées"
    )
    print(
        f"[Préchargement]   - Sprites extraits : {sprites_count} images chargées"
    )
    
    return sprite_sheets_count + sprites_count
```

### Préchargement des images de dialogue

Le préchargement des images de dialogue doit :
- **Calculer le nombre total d'images à charger** avant de commencer (en parcourant tous les dialogues de tous les PNJ)
- Utiliser la fonction `preload_dialogue_images()` existante (ou la modifier pour permettre une progression continue)
- **Mettre à jour la progression après chaque image chargée**
- Logger le nombre d'images chargées

**Progression continue** : La méthode doit appeler `_update_progress()` après chaque image chargée :
- Après chaque image de dialogue chargée et mise en cache
- Appeler `pygame.event.pump()` après chaque mise à jour pour maintenir la réactivité de la fenêtre

**Note** : Si `preload_dialogue_images()` ne permet pas une progression continue, il faudra soit la modifier pour accepter un callback de progression, soit réimplémenter la logique dans `_preload_dialogue_images()` pour charger les images une par une avec mise à jour de la progression.

```python
def _preload_dialogue_images(self, npcs_config: NPCsConfig) -> int:
    """Précharge toutes les images de dialogue.
    
    Args:
        npcs_config: Configuration des PNJ
        
    Returns:
        Nombre total d'images chargées
    """
    from moteur_jeu_presentation.ui.speech_bubble import preload_dialogue_images, _global_image_cache
    
    # Sauvegarder le nombre d'images avant le préchargement
    before_count = len(_global_image_cache)
    
    # Précharger les images
    image_assets_root = self.project_root / "image"
    preload_dialogue_images(npcs_config, assets_root=image_assets_root)
    
    # Compter les nouvelles images chargées
    after_count = len(_global_image_cache)
    count = after_count - before_count
    
    print(f"[Préchargement]   - {count} images de dialogue chargées")
    
    return count
```

### Barre de chargement

La barre de chargement doit être dessinée à chaque frame pendant le préchargement :

```python
def _draw_loading_bar(self) -> None:
    """Dessine la barre de chargement."""
    # Fond noir
    self.screen.fill((0, 0, 0))
    
    # Dessiner la barre de progression
    bar_width = 600
    bar_height = 30
    bar_x = (self.screen_width - bar_width) // 2
    bar_y = (self.screen_height - bar_height) // 2
    
    # Fond de la barre
    pygame.draw.rect(
        self.screen,
        (50, 50, 50),
        (bar_x, bar_y, bar_width, bar_height),
    )
    
    # Barre de progression
    progress_width = int(bar_width * self.progress)
    pygame.draw.rect(
        self.screen,
        (74, 149, 172),  # Couleur principale du jeu
        (bar_x, bar_y, progress_width, bar_height),
    )
    
    # Texte de progression
    font = pygame.font.SysFont("arial", 24, bold=True)
    if self.current_total > 0:
        text = f"{self.current_category}... {self.current_count}/{self.current_total}"
    else:
        text = f"{self.current_category}..."
    
    text_surface = font.render(text, True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=(self.screen_width // 2, bar_y - 40))
    self.screen.blit(text_surface, text_rect)
    
    # Pourcentage
    percent_text = f"{int(self.progress * 100)}%"
    percent_surface = font.render(percent_text, True, (255, 255, 255))
    percent_rect = percent_surface.get_rect(center=(self.screen_width // 2, bar_y + bar_height + 20))
    self.screen.blit(percent_surface, percent_rect)
    
    pygame.display.flip()
```

## Implémentation

### Structure de fichiers

```
src/moteur_jeu_presentation/
├── assets/
│   ├── __init__.py
│   └── preloader.py          # Classe AssetPreloader et LoadingBar
├── main.py                     # Modification pour intégrer le préchargement
```

### Modifications dans `main.py`

La fonction `main()` doit être modifiée pour :
1. Ajouter un argument en ligne de commande pour sauter le préchargement
2. Créer et exécuter le préchargement avant l'écran d'accueil (sauf si l'argument est activé)
3. Passer les résultats du préchargement au reste du jeu

#### Ajout de l'argument en ligne de commande

```python
def parse_arguments() -> argparse.Namespace:
    """Parse les arguments de la ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Présentation - Jeu de plateforme",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    # ... autres arguments existants ...
    
    parser.add_argument(
        "--skip-preload",
        action="store_true",
        dest="skip_preload",
        help="Passe le préchargement des éléments graphiques (utile pour le développement)",
    )
    
    return parser.parse_args()
```

#### Intégration dans la fonction `main()`

```python
from moteur_jeu_presentation.assets.preloader import AssetPreloader

def main() -> None:
    """Point d'entrée principal du jeu."""
    # Parser les arguments de la ligne de commande
    args = parse_arguments()
    
    # ... initialisation pygame et fenêtre ...
    
    # Précharger tous les éléments graphiques (sauf si --skip-preload est activé)
    if not args.skip_preload:
        print("[Préchargement] Début du préchargement des éléments graphiques...")
        
        # Créer le préchargeur
        preloader = AssetPreloader(
            screen=screen,
            screen_width=render_width,
            screen_height=render_height,
            project_root=project_root,
        )
        
        # Précharger tous les éléments
        preloader.preload_all_assets(
            level_config=level_config,
            npcs_config=npcs_config,
            inventory_config=inventory_config,
            stats_config=stats_config,
            player_level=level_config.player_level,
        )
        
        print("[Préchargement] Préchargement terminé.")
    
    # ... reste du code pour l'écran d'accueil et le jeu ...
```

### Module `assets/preloader.py`

Créer un nouveau module `src/moteur_jeu_presentation/assets/preloader.py` :

```python
"""Module de préchargement des éléments graphiques."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

import pygame

if TYPE_CHECKING:
    from ..inventory.config import InventoryItemConfig
    from ..levels.config import LevelConfig, NPCsConfig
    from ..stats.config import PlayerStatsConfig

logger = logging.getLogger("moteur_jeu_presentation.preloader")


class LoadingBar:
    """Gère l'affichage de la barre de chargement."""
    
    def __init__(
        self,
        screen: pygame.Surface,
        screen_width: int,
        screen_height: int,
    ) -> None:
        """Initialise la barre de chargement.
        
        Args:
            screen: Surface pygame pour dessiner la barre
            screen_width: Largeur de l'écran
            screen_height: Hauteur de l'écran
        """
        self.screen = screen
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Dimensions de la barre
        self.bar_width = 600
        self.bar_height = 30
        self.bar_x = (screen_width - self.bar_width) // 2
        self.bar_y = (screen_height - self.bar_height) // 2
        
        # Couleurs
        self.bar_color = (74, 149, 172)  # Couleur principale du jeu
        self.bar_bg_color = (50, 50, 50)
        self.text_color = (255, 255, 255)
        
        # Police
        try:
            self.font = pygame.font.SysFont("arial", 24, bold=True)
        except pygame.error:
            self.font = pygame.font.SysFont("sans-serif", 24, bold=True)
    
    def draw(
        self,
        progress: float,
        category: str,
        current: int,
        total: int,
    ) -> None:
        """Dessine la barre de chargement.
        
        Args:
            progress: Progression actuelle (0.0 à 1.0)
            category: Nom de la catégorie en cours de chargement
            current: Nombre d'éléments chargés dans la catégorie actuelle
            total: Nombre total d'éléments dans la catégorie actuelle
        """
        # Fond noir
        self.screen.fill((0, 0, 0))
        
        # Fond de la barre
        pygame.draw.rect(
            self.screen,
            self.bar_bg_color,
            (self.bar_x, self.bar_y, self.bar_width, self.bar_height),
        )
        
        # Barre de progression
        progress_width = int(self.bar_width * progress)
        pygame.draw.rect(
            self.screen,
            self.bar_color,
            (self.bar_x, self.bar_y, progress_width, self.bar_height),
        )
        
        # Texte de progression
        if total > 0:
            text = f"{category}... {current}/{total}"
        else:
            text = f"{category}..."
        
        text_surface = self.font.render(text, True, self.text_color)
        text_rect = text_surface.get_rect(center=(self.screen_width // 2, self.bar_y - 40))
        self.screen.blit(text_surface, text_rect)
        
        # Pourcentage
        percent_text = f"{int(progress * 100)}%"
        percent_surface = self.font.render(percent_text, True, self.text_color)
        percent_rect = percent_surface.get_rect(
            center=(self.screen_width // 2, self.bar_y + self.bar_height + 20)
        )
        self.screen.blit(percent_surface, percent_rect)
        
        pygame.display.flip()


class AssetPreloader:
    """Gère le préchargement de tous les éléments graphiques du jeu."""
    
    def __init__(
        self,
        screen: pygame.Surface,
        screen_width: int,
        screen_height: int,
        project_root: Path,
    ) -> None:
        """Initialise le préchargeur.
        
        Args:
            screen: Surface pygame pour afficher la barre de chargement
            screen_width: Largeur de l'écran de rendu
            screen_height: Hauteur de l'écran de rendu
            project_root: Chemin racine du projet
        """
        self.screen = screen
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.project_root = project_root
        
        # Barre de chargement
        self.loading_bar = LoadingBar(screen, screen_width, screen_height)
        
        # État de progression
        self.progress = 0.0
        self.current_category = ""
        self.current_count = 0
        self.current_total = 0
        self.total_loaded = 0
        self.total_to_load = 0
        
        # Statistiques
        self.loading_stats: Dict[str, int] = {}
    
    def preload_all_assets(
        self,
        level_config: LevelConfig,
        npcs_config: Optional[NPCsConfig],
        inventory_config: Optional[InventoryItemConfig],
        stats_config: Optional[PlayerStatsConfig],
        player_level: int,
    ) -> Dict[str, Any]:
        """Précharge tous les éléments graphiques.
        
        Args:
            level_config: Configuration du niveau
            npcs_config: Configuration des PNJ
            inventory_config: Configuration des objets d'inventaire
            stats_config: Configuration des stats du joueur
            player_level: Niveau initial du joueur
            
        Returns:
            Dictionnaire contenant les statistiques de chargement
        """
        # Estimer le nombre total d'éléments à charger de manière plus précise
        self.total_to_load = self._estimate_total_items(
            level_config, npcs_config, inventory_config, stats_config
        )
        
        # Initialiser la progression
        self.total_loaded = 0
        self._update_progress("Initialisation...", 0, self.total_to_load)
        
        # Catégories de chargement
        categories = [
            ("Sprites de niveau", self._preload_level_sprites, (level_config,)),
            ("Sprites du joueur", self._preload_player_sprites, (stats_config, player_level)),
            ("Sprites des PNJ", self._preload_npc_sprites, (npcs_config,)),
            ("Sprites d'inventaire", self._preload_inventory_sprites, (inventory_config,)),
            ("Images de dialogue", self._preload_dialogue_images, (npcs_config,)),
        ]
        
        # Précharger chaque catégorie
        for category_name, preload_func, args in categories:
            if args[0] is None and category_name in ("Sprites des PNJ", "Images de dialogue"):
                continue  # Ignorer si npcs_config est None
            
            self._log_category_start(category_name)
            count = preload_func(*args)
            self.loading_stats[category_name] = count
            # Note: self.total_loaded est mis à jour dans les méthodes _preload_* au fur et à mesure
            self._log_category_end(category_name, count)
        
        # Afficher le total final
        self._log_total()
        
        # Afficher 100% à la fin
        self._update_progress("Terminé", self.total_loaded, self.total_loaded)
        
        return {
            "total_loaded": self.total_loaded,
            "stats": self.loading_stats,
        }
    
    def _estimate_total_items(
        self,
        level_config: LevelConfig,
        npcs_config: Optional[NPCsConfig],
        inventory_config: Optional[InventoryItemConfig],
        stats_config: Optional[PlayerStatsConfig],
    ) -> int:
        """Estime le nombre total d'éléments à charger.
        
        Args:
            level_config: Configuration du niveau
            npcs_config: Configuration des PNJ
            inventory_config: Configuration des objets d'inventaire
            stats_config: Configuration des stats du joueur
            
        Returns:
            Estimation du nombre total d'éléments à charger
        """
        total = 0
        
        # Sprites de niveau : sprite sheets + sprites extraits + sprites redimensionnés
        total += len(level_config.sprite_sheets)  # Sprite sheets
        total += len(level_config.sprites) * 3  # Sprites redimensionnés (estimation)
        
        # Sprites du joueur : ~480 frames (5 niveaux × 3 animations × ~32 frames)
        total += 5 * 3 * 32  # Estimation
        
        # Sprites des PNJ
        if npcs_config:
            for npc_config in npcs_config.npcs:
                total += 1  # Sprite sheet
                # Estimer le nombre de frames (dépend des animations)
                if npc_config.animations:
                    for anim_config in npc_config.animations.values():
                        total += anim_config.num_frames * 2  # Normal + flipped
        
        # Sprites d'inventaire
        if inventory_config:
            total += len(inventory_config.items) * 2  # Sprite sheet + sprite extrait (estimation)
        
        # Images de dialogue
        if npcs_config:
            # Estimer en parcourant les dialogues
            for npc_config in npcs_config.npcs:
                if npc_config.dialogue:
                    for exchange in npc_config.dialogue.exchanges:
                        if exchange.image:
                            total += 1
        
        return total
    
    def _preload_level_sprites(self, level_config: LevelConfig) -> int:
        """Précharge tous les sprites de niveau."""
        # Implémentation détaillée (voir section "Préchargement des sprites de niveau")
        # ...
        return 0
    
    def _preload_player_sprites(
        self,
        stats_config: Optional[PlayerStatsConfig],
        player_level: int,
    ) -> int:
        """Précharge tous les sprites du joueur."""
        # Implémentation détaillée (voir section "Préchargement des sprites du joueur")
        # ...
        return 0
    
    def _preload_npc_sprites(self, npcs_config: NPCsConfig) -> int:
        """Précharge tous les sprites des PNJ."""
        # Implémentation détaillée (voir section "Préchargement des sprites des PNJ")
        # ...
        return 0
    
    def _preload_inventory_sprites(
        self,
        inventory_config: Optional[InventoryItemConfig],
    ) -> int:
        """Précharge tous les sprites d'inventaire."""
        # Implémentation détaillée (voir section "Préchargement des sprites d'inventaire")
        # ...
        return 0
    
    def _preload_dialogue_images(self, npcs_config: NPCsConfig) -> int:
        """Précharge toutes les images de dialogue."""
        # Implémentation détaillée (voir section "Préchargement des images de dialogue")
        # ...
        return 0
    
    def _update_progress(self, category: str, current: int, total: int) -> None:
        """Met à jour la progression et redessine la barre de chargement.
        
        Cette méthode doit être appelée régulièrement pendant le chargement de chaque catégorie,
        après chaque élément chargé (sprite sheet, sprite extrait, frame, etc.).
        
        Args:
            category: Nom de la catégorie en cours
            current: Nombre d'éléments chargés dans la catégorie actuelle
            total: Nombre total d'éléments dans la catégorie actuelle
        """
        self.current_category = category
        self.current_count = current
        self.current_total = total
        
        # Calculer la progression globale basée sur le nombre total d'éléments chargés
        # La progression globale prend en compte toutes les catégories
        if self.total_to_load > 0:
            self.progress = min(self.total_loaded / self.total_to_load, 1.0)
        else:
            self.progress = 0.0
        
        # Redessiner la barre de chargement
        self.loading_bar.draw(
            self.progress,
            self.current_category,
            self.current_count,
            self.current_total,
        )
        
        # Important : Appeler pygame.event.pump() pour maintenir la réactivité de la fenêtre
        # Cette méthode est appelée depuis les méthodes _preload_* qui doivent aussi appeler
        # pygame.event.pump() après chaque mise à jour
    
    def _log_category_start(self, category: str) -> None:
        """Log le début d'une catégorie."""
        print(f"[Préchargement] Chargement des {category.lower()}...")
    
    def _log_category_end(self, category: str, count: int) -> None:
        """Log la fin d'une catégorie."""
        print(f"[Préchargement] {category} chargés : {count} images au total")
    
    def _log_total(self) -> None:
        """Log le total final."""
        print(f"[Préchargement] Préchargement terminé : {self.total_loaded} images chargées au total")
```

### Mise à jour de `assets/__init__.py`

Créer ou mettre à jour `src/moteur_jeu_presentation/assets/__init__.py` :

```python
from moteur_jeu_presentation.assets.preloader import AssetPreloader, LoadingBar

__all__ = [
    "AssetPreloader",
    "LoadingBar",
]
```

## Contraintes et considérations

### Performance

- Le préchargement doit être effectué de manière efficace pour ne pas bloquer le démarrage du jeu trop longtemps
- Les opérations de chargement doivent être effectuées par petits lots pour permettre la mise à jour de la barre de chargement
- Utiliser `pygame.event.pump()` après chaque mise à jour de la progression pour éviter que la fenêtre ne soit marquée comme "non répondante" par le système d'exploitation
- **Progression continue** : La barre de chargement doit être mise à jour après chaque élément chargé, pas uniquement à la fin d'une catégorie. Cela permet un feedback visuel en temps réel et une progression fluide.

### Progression continue pendant le chargement

**Principe** : Chaque méthode de préchargement (`_preload_*`) doit mettre à jour la progression de manière continue pendant le chargement, pas uniquement à la fin.

**Règles à suivre** :

1. **Calculer le total avant de commencer** : Chaque méthode doit calculer (ou estimer précisément) le nombre total d'éléments à charger dans sa catégorie avant de commencer.

2. **Mettre à jour après chaque élément** : Appeler `_update_progress()` après chaque élément chargé :
   - Après chaque sprite sheet chargé
   - Après chaque sprite extrait
   - Après chaque frame chargée et redimensionnée (ou par petits lots pour éviter trop de mises à jour)
   - Après chaque image de dialogue chargée

3. **Maintenir la réactivité** : Appeler `pygame.event.pump()` après chaque mise à jour de la progression pour maintenir la réactivité de la fenêtre.

4. **Mettre à jour `self.total_loaded`** : Incrémenter `self.total_loaded` au fur et à mesure pour que la progression globale soit calculée correctement.

**Exemple d'implémentation** :

```python
def _preload_level_sprites(self, level_config: LevelConfig) -> int:
    """Précharge tous les sprites de niveau avec progression continue."""
    # 1. Calculer le total avant de commencer
    total_sprite_sheets = len(level_config.sprite_sheets)
    total_scaled_sprites = len(level_config.sprites) * 3  # Estimation
    total_items = total_sprite_sheets + total_scaled_sprites
    
    count = 0
    
    # 2. Charger les sprite sheets avec mise à jour de progression
    for sheet_name, sheet_config in level_config.sprite_sheets.items():
        if not sheet_config.path.exists():
            continue
        
        sprite_sheet = pygame.image.load(str(sheet_config.path)).convert_alpha()
        _global_level_sprite_sheet_cache[sheet_name] = sprite_sheet
        count += 1
        
        # Mettre à jour la progression après chaque sprite sheet
        self.total_loaded += 1
        self._update_progress("Sprites de niveau", count, total_items)
        pygame.event.pump()
    
    # 3. Précharger les sprites redimensionnés avec mise à jour de progression
    for sprite_mapping in level_config.sprites:
        # ... précharger le sprite ...
        count += 1
        
        # Mettre à jour la progression après chaque sprite
        self.total_loaded += 1
        self._update_progress("Sprites de niveau", count, total_items)
        pygame.event.pump()
    
    return count
```

**Optimisation** : Pour éviter trop de mises à jour (qui peuvent ralentir le chargement), on peut mettre à jour la progression par petits lots plutôt qu'après chaque élément. Par exemple, pour les frames du joueur, mettre à jour après chaque animation complète plutôt qu'après chaque frame.

### Gestion des erreurs

- Si un sprite sheet est introuvable, logger un avertissement mais continuer le chargement
- Si une erreur survient lors du chargement d'une catégorie, logger l'erreur et continuer avec les autres catégories
- Ne pas faire planter le jeu si le préchargement échoue partiellement

### Expérience utilisateur

- La barre de chargement doit être mise à jour régulièrement pour donner un feedback visuel
- Les logs doivent être clairs et informatifs pour le débogage
- Le préchargement ne doit pas prendre plus de quelques secondes (optimiser si nécessaire)

### Compatibilité

- Le préchargement doit fonctionner avec tous les systèmes existants (inventaire, PNJ, niveaux, etc.)
- Ne pas modifier le comportement des systèmes existants, seulement précharger leurs ressources
- Permettre de sauter le préchargement pour le développement et les tests

### Cohérence des chemins et clés de cache (CRITIQUE)

**IMPORTANT** : Pour que les caches globaux soient utilisés correctement, les chemins et les clés doivent être cohérents entre le préchargement et l'utilisation.

#### Pour les images de dialogue

- **Préchargement** : Utiliser des chemins absolus basés sur `project_root` (ex: `project_root / "image"`)
- **Utilisation** : Utiliser les mêmes chemins absolus dans `DialogueState`, `SpeechBubble`, etc.
- **Clé de cache** : La clé est `str(image_full_path.resolve())`, donc le chemin absolu doit être identique

**Exemple** :
```python
# ❌ INCORRECT - Produit des clés de cache différentes
# Préchargement : project_root / "image" / "epilogue-jeux.png"
#   → /Users/.../image/epilogue-jeux.png
# Utilisation : Path("image") / "epilogue-jeux.png"
#   → /current/dir/image/epilogue-jeux.png

# ✅ CORRECT - Même clé de cache
# Préchargement : project_root / "image"
# Utilisation : npc.assets_root.parent / "image"
#   (où npc.assets_root.parent == project_root)
```

**Dans le code** :
- `DialogueState.__init__()` : Calculer `image_assets_root = npc.assets_root.parent / "image"`
- `DialogueState.next_exchange()` : Réutiliser `image_assets_root = self.npc.assets_root.parent / "image"`
- `main.py` (fallback si skip_preload) : Utiliser `project_root / "image"`, pas `Path("image")`

#### Pour les sprite sheets de niveau

- **Clé de cache** : Nom du sprite sheet (str) tel que défini dans la configuration du niveau
- **Exemple** : `"terrain"`, `"background"`, etc.
- Les clés sont simples et cohérentes car elles proviennent directement de la configuration

#### Pour les sprite sheets d'inventaire

- **Clé de cache** : Chemin absolu du sprite sheet (str)
- **Utilisation** : `str(item.sprite_path)` pour les sprite sheets
- **Clé des sprites extraits** : `item_id` (str) pour les sprites extraits

#### Pour les sprite sheets des PNJ

- **Clé de cache** : Chemin absolu du sprite sheet résolu (str)
- **Exemple** : `str(sprite_path.resolve())`
- **Utilisation** : Même clé dans `NPC.__init__()` et `NPC.change_sprite_sheet()`

**Note** : Grâce aux caches globaux partagés, il n'est plus nécessaire de partager manuellement les caches entre les instances. Le partage est automatique.

## Tests

### Tests à effectuer

1. **Test de préchargement complet** : Vérifier que tous les éléments graphiques sont préchargés
2. **Test de la barre de chargement** : Vérifier que la barre s'affiche et se met à jour correctement
3. **Test des logs** : Vérifier que les logs apparaissent correctement dans la console
4. **Test de l'option --skip-preload** : Vérifier que le préchargement peut être sauté
5. **Test de performance** : Vérifier que le préchargement ne prend pas trop de temps
6. **Test avec éléments manquants** : Vérifier que le préchargement continue même si certains éléments sont introuvables

## Évolutions futures possibles

- **Préchargement asynchrone** : Charger les éléments en arrière-plan pendant le jeu
- **Préchargement progressif** : Charger les éléments les plus importants en premier
- **Cache persistant** : Sauvegarder les sprites préchargés sur disque pour accélérer les chargements suivants
- **Estimation du temps restant** : Afficher une estimation du temps restant pour le chargement
- **Animation de la barre de chargement** : Ajouter des effets visuels à la barre de chargement

## Références

- Bonnes pratiques : `bonne_pratique.md`
- Spécification écran d'accueil : `spec/16-ecran-d-accueil.md`
- Spécification inventaire : `spec/13-systeme-d-inventaire.md`
- Spécification PNJ : `spec/12-systeme-de-personnage-non-joueur.md`
- Code existant : `src/moteur_jeu_presentation/main.py`
- Code existant : `src/moteur_jeu_presentation/inventory/inventory.py`
- Code existant : `src/moteur_jeu_presentation/ui/speech_bubble.py`

---

**Date de création** : 2024  
**Statut** : ✅ Implémenté
