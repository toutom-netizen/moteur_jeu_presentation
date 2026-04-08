# 13 - Système d'inventaire

## Contexte

Cette spécification définit un système d'inventaire pour le personnage principal. L'inventaire permet au joueur de collecter et de conserver des objets représentés par des sprites avec un identifiant technique unique. Les objets de l'inventaire sont affichés visuellement au-dessus du **nom affiché** du joueur (même texte que `display_name` dans `player_stats.toml`, voir spécifications **2** et **7**) et ne sont pas liés à la physique du jeu (pas de collisions, pas de gravité).

## Objectifs

- Créer un système d'inventaire lié au personnage principal
- Permettre l'ajout, la suppression et la gestion d'objets dans l'inventaire
- Afficher visuellement tous les objets de l'inventaire au-dessus du nom affiché du joueur
- Définir un format de configuration pour les objets (sprites et identifiants techniques)
- Assurer que les objets de l'inventaire ne sont pas affectés par la physique du jeu
- Permettre la persistance de l'inventaire (sauvegarde/chargement)

## Architecture

### Structure des objets d'inventaire

Chaque objet d'inventaire est défini par :
- **ID technique** : Identifiant unique permettant de référencer l'objet (ex: `"cle_rouge"`, `"gemme_bleue"`, `"potion_vie"`)
- **Sprite** : Image représentant l'objet (fichier PNG)
- **Nom d'affichage** (optionnel) : Nom lisible de l'objet pour l'interface utilisateur
- **Description** (optionnel) : Description textuelle de l'objet

### Format de configuration des objets

Les objets d'inventaire sont définis dans un fichier de configuration TOML séparé, permettant de centraliser la définition de tous les objets disponibles dans le jeu. Les objets utilisent des **sprite sheets** (feuilles de sprites) avec un système de cellules, similaire au système utilisé pour le personnage principal et les PNJ.

**Structure du fichier** :

```toml
# Fichier : config/inventory_items.toml
# Configuration des objets d'inventaire disponibles dans le jeu
# Les objets sont définis à partir de sprite sheets avec un système de cellules

[items.document_etoile]
name = "Document avec étoile"
description = "Un document important marqué d'une étoile dorée"
sprite_path = "sprite/items/outils_niveau_decouverte.png"
cell_width = 64
cell_height = 64
cell_row = 0
cell_col = 0

[items.loupe_magique]
name = "Loupe magique"
description = "Une loupe magique avec un orbe lumineux qui émet des particules"
sprite_path = "sprite/items/outils_niveau_decouverte.png"
cell_width = 64
cell_height = 64
cell_row = 0
cell_col = 1
```

**Règles de format** :
- Chaque objet est défini dans une section `[items.<id_technique>]`
- Le nom de la section (`<id_technique>`) est utilisé comme identifiant unique et permet de référencer l'objet dans le code
- Chaque section doit contenir :
  - `sprite_path` (obligatoire) : Chemin relatif vers le **sprite sheet** (fichier PNG) depuis la racine du projet. Plusieurs objets peuvent partager le même sprite sheet.
  - `cell_width` (obligatoire) : Largeur d'une cellule dans le sprite sheet en pixels
  - `cell_height` (obligatoire) : Hauteur d'une cellule dans le sprite sheet en pixels
  - `cell_row` (obligatoire) : Numéro de ligne (index 0) de la cellule contenant l'objet dans le sprite sheet
  - `cell_col` (obligatoire) : Numéro de colonne (index 0) de la cellule contenant l'objet dans le sprite sheet
  - `name` (optionnel) : Nom d'affichage de l'objet (par défaut : l'ID technique)
  - `description` (optionnel) : Description textuelle de l'objet

**Extraction des cellules** :
- Les objets sont extraits du sprite sheet en utilisant la méthode `_extract_sprite()` similaire à celle utilisée pour le personnage (spécification 2)
- La position de la cellule est calculée comme : `x = cell_col * cell_width`, `y = cell_row * cell_height`
- Le rectangle d'extraction est : `pygame.Rect(x, y, cell_width, cell_height)`
- Les cellules sont extraites avec validation des limites du sprite sheet pour éviter les erreurs

### Affichage de l'inventaire

L'inventaire est affiché visuellement au-dessus du **nom affiché** du joueur (`display_name` dans `config/player_stats.toml`, spécifications **2** et **7**) :

```
┌─────────────────────┐
│                     │
│   [Sprite] [Sprite] │  ← Objets d'inventaire (au-dessus du nom affiché)
│                     │
│   {display_name}    │  ← Nom affiché du joueur (config)
│                     │
│    [Personnage]     │  ← Sprite du personnage
│                     │
└─────────────────────┘
```

**Caractéristiques de l'affichage** :
- **Position** : Les objets sont affichés au-dessus du nom affiché du joueur, centrés horizontalement par rapport au personnage
- **Espacement** : Les objets sont espacés horizontalement avec un espacement configurable (défaut : 4-8 pixels entre chaque objet)
- **Taille** : Les sprites sont affichés à leur taille native (selon `cell_width` et `cell_height` du fichier de configuration) ou avec un facteur d'échelle optionnel
- **Ordre** : Les objets sont affichés dans l'ordre d'ajout à l'inventaire (premier ajouté = le plus à gauche)
- **Alignement** : Les objets sont alignés horizontalement sur une ligne unique
- **Limite visuelle** : Si l'inventaire contient trop d'objets, ils peuvent déborder visuellement (pas de limite stricte, mais un système de pagination ou de scroll peut être ajouté dans une évolution future)

**Calcul de la position** :
- La position verticale est calculée comme : `position_nom_affiché.y - hauteur_objets - espacement`
- La position horizontale est centrée par rapport au personnage : `personnage.x - (largeur_totale_objets / 2)`
- Les objets suivent le mouvement du personnage et de la caméra (comme le prénom)

### Système d'inventaire

L'inventaire est une collection d'objets liée au personnage principal. Chaque objet peut être présent en plusieurs exemplaires (quantité).

## Spécifications techniques

### Structure des données

#### Classe `InventoryItem`

```python
@dataclass
class InventoryItem:
    """Représente un objet d'inventaire avec sa configuration."""
    item_id: str  # ID technique unique
    name: str  # Nom d'affichage
    description: Optional[str] = None  # Description optionnelle
    sprite_path: Path  # Chemin vers le sprite sheet
    cell_width: int  # Largeur d'une cellule en pixels
    cell_height: int  # Hauteur d'une cellule en pixels
    cell_row: int  # Numéro de ligne (index 0) de la cellule dans le sprite sheet
    cell_col: int  # Numéro de colonne (index 0) de la cellule dans le sprite sheet
    sprite_surface: Optional[pygame.Surface] = None  # Sprite extrait et chargé (mis en cache)
    
    def load_sprite(self, sprite_sheet_cache: Dict[str, pygame.Surface]) -> pygame.Surface:
        """Charge et extrait le sprite de l'objet depuis le sprite sheet.
        
        Args:
            sprite_sheet_cache: Cache des sprite sheets chargés (clé = sprite_path, valeur = Surface)
            
        Returns:
            Surface pygame contenant le sprite extrait de la cellule
        """
        if self.sprite_surface is None:
            # Charger le sprite sheet depuis le cache (ou le charger si absent)
            sprite_path_str = str(self.sprite_path)
            if sprite_path_str not in sprite_sheet_cache:
                sprite_sheet_cache[sprite_path_str] = pygame.image.load(sprite_path_str).convert_alpha()
            
            sprite_sheet = sprite_sheet_cache[sprite_path_str]
            
            # Extraire la cellule du sprite sheet
            self.sprite_surface = self._extract_cell(sprite_sheet)
        
        return self.sprite_surface
    
    def _extract_cell(self, sprite_sheet: pygame.Surface) -> pygame.Surface:
        """Extrait la cellule correspondante du sprite sheet.
        
        Args:
            sprite_sheet: Surface du sprite sheet complet
            
        Returns:
            Surface pygame contenant la cellule extraite
        """
        # Calculer la position de la cellule
        x = self.cell_col * self.cell_width
        y = self.cell_row * self.cell_height
        
        # Valider les limites du sprite sheet
        sheet_width = sprite_sheet.get_width()
        sheet_height = sprite_sheet.get_height()
        
        if sheet_width <= 0 or sheet_height <= 0:
            return pygame.Surface((self.cell_width, self.cell_height), pygame.SRCALPHA)
        
        # S'assurer que le point d'origine reste dans les limites
        max_x = max(sheet_width - self.cell_width, 0)
        max_y = max(sheet_height - self.cell_height, 0)
        x = max(0, min(x, max_x))
        y = max(0, min(y, max_y))
        
        # Ajuster la taille du rectangle si nécessaire
        rect_width = min(self.cell_width, sheet_width - x)
        rect_height = min(self.cell_height, sheet_height - y)
        
        if rect_width <= 0 or rect_height <= 0:
            return pygame.Surface((self.cell_width, self.cell_height), pygame.SRCALPHA)
        
        rect = pygame.Rect(x, y, rect_width, rect_height)
        
        try:
            sprite = sprite_sheet.subsurface(rect).copy()
            if sprite.get_width() != self.cell_width or sprite.get_height() != self.cell_height:
                resized = pygame.Surface((self.cell_width, self.cell_height), pygame.SRCALPHA)
                resized.blit(sprite, (0, 0))
                sprite = resized
            return sprite.convert_alpha()
        except (ValueError, pygame.error):
            return pygame.Surface((self.cell_width, self.cell_height), pygame.SRCALPHA)
```

#### Classe `InventoryItemConfig`

```python
@dataclass
class InventoryItemConfig:
    """Configuration complète des objets d'inventaire disponibles."""
    items: Dict[str, InventoryItem]  # Indexé par item_id
    
    def get_item(self, item_id: str) -> Optional[InventoryItem]:
        """Récupère un objet par son ID technique.
        
        Args:
            item_id: ID technique de l'objet
            
        Returns:
            L'objet correspondant, ou None si introuvable
        """
        return self.items.get(item_id)
```

#### Classe `Inventory`

```python
class Inventory:
    """Gestionnaire d'inventaire pour le personnage principal."""
    
    def __init__(
        self,
        item_config: Optional[InventoryItemConfig] = None,
        item_spacing: int = 6,
        item_scale: float = 1.0,
        display_offset_y: float = -8.0,
        particle_system: Optional[ParticleSystem] = None,
    ) -> None:
        """
        Args:
            item_config: Configuration des objets disponibles (optionnel)
            item_spacing: Espacement horizontal entre les objets en pixels (défaut: 6)
            item_scale: Facteur d'échelle pour l'affichage des objets (défaut: 1.0 = taille native)
            display_offset_y: Offset vertical pour positionner l'inventaire au-dessus du prénom (défaut: -8.0)
            particle_system: Référence au système de particules global (optionnel, nécessaire pour les animations de suppression)
        """
```

**Propriétés** :
- `items: Dict[str, int]` : Dictionnaire des objets dans l'inventaire (clé = item_id, valeur = quantité)
- `item_config: Optional[InventoryItemConfig]` : Configuration des objets disponibles
- `item_spacing: int` : Espacement horizontal entre les objets en pixels
- `item_scale: float` : Facteur d'échelle pour l'affichage des objets
- `display_offset_y: float` : Offset vertical pour positionner l'inventaire au-dessus du prénom
- `particle_system: Optional[ParticleSystem]` : Référence au système de particules global (optionnel, nécessaire pour les animations de suppression avec particules)
- `_sprite_sheet_cache: Dict[str, pygame.Surface]` : Cache des sprite sheets chargés (clé = sprite_path, valeur = Surface du sprite sheet complet). Ce cache est partagé entre tous les objets utilisant le même sprite sheet.
- `_cached_surfaces: Dict[str, pygame.Surface]` : Cache des sprites extraits (clé = item_id, valeur = Surface de la cellule extraite)
- `_item_animations: Dict[str, ItemAnimationState]` : État des animations pour chaque objet (clé = item_id, valeur = état d'animation). Gère les animations d'ajout (apparition au centre de l'écran à 10x puis réduction et déplacement vers la position finale) et de suppression (déplacement vers le centre de l'écran avec agrandissement de 1x à 10x puis explosion avec particules agrandies). Les particules d'explosion sont gérées par le système de particules global.

**Méthodes principales** :
- `add_item(item_id: str, quantity: int = 1, animated: bool = True) -> None` : Ajoute un ou plusieurs exemplaires d'un objet à l'inventaire. Charge automatiquement le sprite si nécessaire. Si `animated=True`, déclenche une animation d'apparition au centre de l'écran (10x) qui se réduit et se déplace vers la position finale. Lors de la création de l'animation, la position cible de l'objet dans l'inventaire et le centre de l'écran sont enregistrés dans l'état d'animation.
- `remove_item(item_id: str, quantity: int = 1, animated: bool = True) -> bool` : Retire un ou plusieurs exemplaires d'un objet de l'inventaire. Retourne `True` si l'opération a réussi, `False` si la quantité est insuffisante. Si `animated=True`, déclenche une animation de déplacement vers le centre de l'écran avec agrandissement (1x à 10x) puis explosion avec particules agrandies via le système de particules global. Lors de la création de l'animation, la position de départ de l'objet et le centre de l'écran sont enregistrés pour positionner l'animation et les particules. Les particules utilisent une palette de couleurs chaudes (rouge, orange, jaune) indépendamment de la couleur de l'objet.
- `has_item(item_id: str, quantity: int = 1) -> bool` : Vérifie si l'inventaire contient au moins `quantity` exemplaires de l'objet
- `get_quantity(item_id: str) -> int` : Retourne la quantité d'un objet dans l'inventaire (0 si absent)
- `get_all_items() -> Dict[str, int]` : Retourne une copie du dictionnaire des objets
- `clear() -> None` : Vide complètement l'inventaire
- `update_animations(dt: float, camera_x: float = 0.0) -> None` : Met à jour les animations d'ajout et de suppression des objets. Doit être appelé à chaque frame dans la boucle principale. Le paramètre `camera_x` est nécessaire pour convertir les coordonnées écran en coordonnées monde lors de la création des particules d'explosion.
- `get_display_commands(camera_x: float, player_x: float, player_y: float, name_y: float, screen_width: int, screen_height: int) -> List[Tuple[pygame.Surface, Tuple[int, int]]]` : Génère les commandes de dessin pour afficher l'inventaire au-dessus du prénom. Prend en compte les animations en cours (opacité, position, échelle, etc.). Les particules d'explosion sont gérées et rendues séparément par le système de particules global. Les paramètres `screen_width` et `screen_height` sont nécessaires pour calculer le centre de l'écran lors des animations.
- `_load_item_sprite(item_id: str) -> Optional[pygame.Surface]` : Charge et extrait le sprite d'un objet depuis le sprite sheet (avec mise en cache)
- `preload_all_sprites() -> None` : Précharge tous les sprites des objets définis dans la configuration au démarrage de l'application
- `set_particle_system(particle_system: ParticleSystem) -> None` : Définit la référence au système de particules global
- `_create_explosion_particles(animation_state: ItemAnimationState, item_id: str, camera_x: float) -> None` : Crée les particules d'explosion de flamme pour une animation de suppression en utilisant le système de particules global (utilise une palette de couleurs chaudes, indépendamment de la couleur de l'objet). Convertit les coordonnées écran en coordonnées monde en utilisant `camera_x`.

### Chargeur de configuration

```python
class InventoryItemLoader:
    """Chargeur de fichier de configuration des objets d'inventaire."""
    
    def __init__(self, config_path: Path) -> None:
        """
        Args:
            config_path: Chemin vers le fichier inventory_items.toml
        """
        self.config_path = config_path
    
    def load_items(self) -> InventoryItemConfig:
        """Charge le fichier de configuration des objets.
        
        Returns:
            Configuration des objets chargée
            
        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            ValueError: Si le format du fichier est invalide
        """
        # Implémentation : charger le TOML et valider la structure
        # Vérifier que toutes les sections [items.*] contiennent :
        #   - sprite_path (obligatoire)
        #   - cell_width, cell_height (obligatoires)
        #   - cell_row, cell_col (obligatoires)
        # Convertir en InventoryItemConfig
        pass
    
    def validate_items(self, config: InventoryItemConfig) -> None:
        """Valide la configuration des objets.
        
        Raises:
            ValueError: Si la configuration est invalide
        """
        # Vérifier que tous les sprite sheets existent
        # Vérifier que les dimensions de cellules sont positives
        # Vérifier que les cellules (row, col) sont valides pour chaque sprite sheet
        pass
```

### Mécanisme de cache global (voir spécification 17)

**Préchargement automatique des sprites** : Pour optimiser les performances, tous les sprites des objets définis dans la configuration sont automatiquement préchargés au démarrage de l'application par le système de préchargement centralisé (`AssetPreloader`), avant l'affichage de l'écran d'accueil. Cela évite les ralentissements lors de l'ajout d'objets à l'inventaire pendant le gameplay.

**Implémentation avec caches globaux** :
- **Caches globaux partagés** : L'inventaire utilise deux caches globaux définis dans `src/moteur_jeu_presentation/assets/preloader.py` :
  - `_global_inventory_sprite_sheet_cache: Dict[str, pygame.Surface]` : Cache des sprite sheets complets (clé = chemin absolu du sprite sheet)
  - `_global_inventory_cached_surfaces: Dict[str, pygame.Surface]` : Cache des sprites extraits (clé = item_id)
- **Références automatiques** : Dans `Inventory.__init__()`, les attributs `_sprite_sheet_cache` et `_cached_surfaces` sont automatiquement des références vers les caches globaux, garantissant le partage entre toutes les instances
- **Préchargement centralisé** : Le préchargement est géré par `AssetPreloader._preload_inventory_sprites()` qui remplit les caches globaux
- **Fallback transparent** : Si le préchargement est désactivé (`--skip-preload`), la méthode `inventory.preload_all_sprites()` peut être appelée manuellement pour remplir les caches globaux
- **Partage automatique** : Toutes les instances d'inventaire (inventaire temporaire, inventaire du joueur, etc.) partagent automatiquement les mêmes caches globaux sans configuration manuelle

**Avantages** :
- ✅ Aucun préchargement manuel requis
- ✅ Partage automatique entre toutes les instances
- ✅ Évite les rechargements multiples du même sprite sheet
- ✅ Intégration transparente avec le système de préchargement global (spec 17)

### Système d'animations d'inventaire

Le système d'inventaire gère des animations visuelles pour l'ajout et la suppression d'objets, offrant un retour visuel clair au joueur.

**Note** : Le système d'inventaire utilise le **système de particules global** (spécification 14) pour créer et gérer les effets de particules lors de la suppression d'objets. Les particules sont créées via `particle_system.create_effect()` et gérées automatiquement par le système de particules global. Pour les détails d'implémentation des particules, voir la spécification 14.

#### Classe `ItemAnimationState`

```python
@dataclass
class ItemAnimationState:
    """État d'animation pour un objet d'inventaire."""
    animation_type: Literal["add", "remove"]  # Type d'animation ("add" ou "remove")
    progress: float  # Progression de l'animation (0.0 à 1.0)
    offset_x: float  # Décalage horizontal pour l'animation (en pixels)
    offset_y: float  # Décalage vertical pour l'animation (en pixels)
    scale: float  # Facteur d'échelle pour l'animation (1.0 = taille normale)
    opacity: int  # Opacité de l'objet (0 à 255)
    is_complete: bool  # Indique si l'animation est terminée
    particle_effect_id: Optional[str] = None  # Identifiant de l'effet de particules dans le système global (None si les particules n'ont pas encore été créées). Note: Les particules sont gérées par le système de particules global (spec 14)
    item_sprite: Optional[pygame.Surface] = None  # Sprite de l'objet (optionnel, peut être utilisé pour le rendu de l'objet pendant l'animation). Note: La couleur des particules n'est plus extraite de ce sprite - les explosions utilisent une palette de couleurs chaudes (rouge, orange, jaune)
    particle_base_x: float = 0.0  # Position de base X pour les particules (en coordonnées écran, généralement le centre de l'écran). Sera convertie en coordonnées monde lors de la création des particules.
    particle_base_y: float = 0.0  # Position de base Y pour les particules (en coordonnées écran, généralement le centre de l'écran). Généralement identique en coordonnées monde (pas de décalage vertical de caméra).
    start_x: float = 0.0  # Position de départ X pour l'animation (en pixels, coordonnées écran)
    start_y: float = 0.0  # Position de départ Y pour l'animation (en pixels, coordonnées écran)
    target_x: float = 0.0  # Position cible X pour l'animation (en pixels, coordonnées écran)
    target_y: float = 0.0  # Position cible Y pour l'animation (en pixels, coordonnées écran)
    screen_center_x: float = 0.0  # Position X du centre de l'écran (en pixels, coordonnées écran)
    screen_center_y: float = 0.0  # Position Y du centre de l'écran (en pixels, coordonnées écran)
```

#### Animation d'ajout (agrandissement au centre puis réduction vers la position finale)

**Comportement** :
- Lorsqu'un objet est ajouté avec `animated=True`, une animation d'apparition spectaculaire est déclenchée
- **Durée** : La durée de l'animation est définie par une variable globale `INVENTORY_ADD_ANIMATION_DURATION` (défaut : 0.6 secondes)
- **Effet visuel** :
  - L'objet apparaît au **centre de l'écran** à une taille **10 fois plus grande** que sa taille normale
  - L'objet diminue progressivement de taille (de 10x à 1x) tout en se déplaçant vers sa position finale dans l'inventaire
  - L'objet apparaît progressivement avec un effet de fade-in (opacité de 0 à 255)
- **Progression** : L'animation progresse de 0.0 à 1.0 sur la durée définie
- **Position** : 
  - Au début (`progress = 0.0`) : L'objet est affiché au centre de l'écran (`screen_center_x`, `screen_center_y`)
  - À la fin (`progress = 1.0`) : L'objet est affiché à sa position normale dans l'inventaire (`target_x`, `target_y`)
  - Interpolation : La position est interpolée linéairement entre le centre de l'écran et la position finale : `current_x = screen_center_x + (target_x - screen_center_x) * progress`, `current_y = screen_center_y + (target_y - screen_center_y) * progress`
- **Échelle** : 
  - Au début (`progress = 0.0`) : `scale = 10.0` (10 fois plus grand)
  - À la fin (`progress = 1.0`) : `scale = 1.0` (taille normale)
  - Interpolation : L'échelle diminue progressivement : `scale = 10.0 - (10.0 - 1.0) * progress = 10.0 - 9.0 * progress`
- **Opacité** : Calculée comme `opacity = int(255 * progress)` où `progress` va de 0.0 à 1.0
- **Fin de l'animation** : Une fois l'animation terminée (`progress >= 1.0`), l'objet est affiché normalement (opacité 255, scale 1.0, position finale) et l'état d'animation est supprimé

**Variable globale** :
```python
# Dans le module inventory.py ou dans un module de configuration
INVENTORY_ADD_ANIMATION_DURATION: float = 0.6  # Durée en secondes (augmentée pour l'effet d'agrandissement)
INVENTORY_ADD_SCALE_FACTOR: float = 10.0  # Facteur d'agrandissement initial (10x la taille normale)
```

#### Animation de suppression (déplacement vers le centre avec agrandissement puis explosion)

**Comportement** :
- Lorsqu'un objet est retiré avec `animated=True`, une animation spectaculaire est déclenchée pour rendre la disparition plus voyante
- **Durée** : La durée de l'animation est définie par une variable globale `INVENTORY_REMOVE_ANIMATION_DURATION` (défaut : 0.7 secondes)
- **Effet visuel** :
  - L'objet part de sa position actuelle dans l'inventaire et se déplace vers le **centre de l'écran**
  - Pendant le déplacement, l'objet **augmente progressivement de taille** (de 1x à 10x)
  - L'objet disparaît progressivement avec un effet de fade-out (opacité de 255 à 0)
  - **Explosion de particules** : Au moment où l'objet atteint le centre de l'écran (vers la fin de l'animation), des particules colorées explosent depuis le centre de l'écran. Les particules sont également **agrandies d'un facteur 10** pour correspondre à la taille de l'objet au moment de l'explosion. L'effet utilise le **système de particules global** (spécification 14) avec une configuration d'explosion de flamme (`create_flame_explosion_config()`).
- **Progression** : L'animation progresse de 0.0 à 1.0 sur la durée définie
- **Position** : 
  - Au début (`progress = 0.0`) : L'objet est affiché à sa position normale dans l'inventaire (`start_x`, `start_y`)
  - À la fin (`progress = 1.0`) : L'objet est affiché au centre de l'écran (`screen_center_x`, `screen_center_y`)
  - Interpolation : La position est interpolée linéairement entre la position de départ et le centre de l'écran : `current_x = start_x + (screen_center_x - start_x) * progress`, `current_y = start_y + (screen_center_y - start_y) * progress`
- **Échelle** : 
  - Au début (`progress = 0.0`) : `scale = 1.0` (taille normale)
  - À la fin (`progress = 1.0`) : `scale = 10.0` (10 fois plus grand)
  - Interpolation : L'échelle augmente progressivement : `scale = 1.0 + (10.0 - 1.0) * progress = 1.0 + 9.0 * progress`
- **Opacité** : Calculée comme `opacity = int(255 * (1 - progress))` où `progress` va de 0.0 à 1.0
- **Explosion de particules** :
  - Les particules sont générées au moment où l'objet atteint le centre de l'écran (quand `progress >= INVENTORY_REMOVE_EXPLOSION_START`, pour que l'objet soit encore visible au début de l'explosion)
  - L'effet utilise le **système de particules global** (spécification 14) avec une configuration de type "explosion de flamme" (fonction `create_flame_explosion_config()`)
  - Les particules sont créées via `particle_system.create_effect()` et gérées automatiquement par le système de particules global
  - Les particules se dispersent dans toutes les directions depuis le centre de l'écran
  - La couleur des particules utilise une palette de couleurs chaudes (rouge, orange, jaune) avec une variation importante pour créer un effet d'explosion de flamme colorée et dynamique. **La couleur n'est pas liée à la couleur de l'objet** - toutes les explosions d'inventaire utilisent le même effet de flamme spectaculaire
  - **Taille des particules** : Les particules sont créées avec une taille multipliée par le facteur d'agrandissement (`INVENTORY_REMOVE_PARTICLES_SIZE * INVENTORY_REMOVE_SCALE_FACTOR`) pour correspondre à la taille de l'objet au moment de l'explosion
  - Les paramètres de l'effet (nombre, vitesse, taille, durée de vie) sont configurables via les variables globales ci-dessous
- **Rendu** : Pendant l'animation, l'objet est rendu avec opacité réduite, échelle augmentée et position interpolée. Les particules d'explosion sont rendues via le système de particules global dans la boucle principale du jeu (`particle_system.get_display_commands(camera_x)`). Une fois l'animation terminée (`progress >= 1.0`), l'objet n'est plus rendu et l'état d'animation est supprimé. Les particules continuent d'exister et sont automatiquement nettoyées par le système de particules global une fois leur durée de vie écoulée

**Variables globales** :
```python
# Dans le module inventory.py ou dans un module de configuration
INVENTORY_REMOVE_ANIMATION_DURATION: float = 0.7  # Durée en secondes (augmentée pour l'effet d'agrandissement et d'explosion)
INVENTORY_REMOVE_SCALE_FACTOR: float = 10.0  # Facteur d'agrandissement final (10x la taille normale)
INVENTORY_REMOVE_PARTICLES_COUNT: int = 24  # Nombre de particules dans l'explosion (configurable pour ajuster les performances et l'effet visuel)
INVENTORY_REMOVE_PARTICLES_SPEED: float = 320.0  # Vitesse de base des particules en pixels/seconde (augmentée pour que les particules partent plus loin)
INVENTORY_REMOVE_PARTICLES_LIFETIME: float = 0.4  # Durée de vie des particules en secondes
INVENTORY_REMOVE_PARTICLES_SIZE: int = 16  # Taille de base des particules en pixels (diamètre, sera multipliée par INVENTORY_REMOVE_SCALE_FACTOR)
INVENTORY_REMOVE_EXPLOSION_START: float = 0.8  # Moment où l'explosion commence (0.0 à 1.0, 0.8 = 80% de l'animation, quand l'objet est proche du centre)
```

**Note sur la configuration du nombre de particules** :
- La variable `INVENTORY_REMOVE_PARTICLES_COUNT` permet de configurer facilement le nombre de particules dans l'explosion
- **Valeur recommandée** : 8-16 particules pour un bon équilibre entre effet visuel et performance
- **Performance** : Réduire ce nombre (ex: 6-8) sur des systèmes moins puissants ou si plusieurs objets sont supprimés simultanément
- **Effet visuel** : Augmenter ce nombre (ex: 16-24) pour un effet plus spectaculaire, mais attention à l'impact sur les performances

#### Mise à jour des animations

La méthode `update_animations(dt: float, camera_x: float = 0.0)` doit être appelée à chaque frame dans la boucle principale du jeu. Le paramètre `camera_x` est nécessaire pour convertir les coordonnées écran en coordonnées monde lors de la création des particules d'explosion :

```python
def update_animations(self, dt: float, camera_x: float = 0.0) -> None:
    """Met à jour les animations d'ajout et de suppression des objets.
    
    Args:
        dt: Delta time en secondes
        camera_x: Position horizontale de la caméra (nécessaire pour convertir les coordonnées écran en coordonnées monde lors de la création des particules)
    """
    import math
    import random
    
    # Parcourir toutes les animations en cours
    for item_id, animation_state in list(self._item_animations.items()):
        # Mettre à jour la progression
        if animation_state.animation_type == "add":
            duration = INVENTORY_ADD_ANIMATION_DURATION
        else:  # "remove"
            duration = INVENTORY_REMOVE_ANIMATION_DURATION
        
        old_progress = animation_state.progress
        animation_state.progress += dt / duration
        
        # Limiter la progression à 1.0
        if animation_state.progress >= 1.0:
            animation_state.progress = 1.0
            animation_state.is_complete = True
        
        # Calculer l'opacité, les décalages et l'échelle
        if animation_state.animation_type == "add":
            # Animation d'ajout : du centre de l'écran (10x) vers la position finale (1x)
            animation_state.opacity = int(255 * animation_state.progress)
            # Interpolation de position : du centre de l'écran vers la position cible
            animation_state.offset_x = animation_state.screen_center_x + (animation_state.target_x - animation_state.screen_center_x) * animation_state.progress - animation_state.target_x
            animation_state.offset_y = animation_state.screen_center_y + (animation_state.target_y - animation_state.screen_center_y) * animation_state.progress - animation_state.target_y
            # Interpolation d'échelle : de 10x à 1x
            animation_state.scale = INVENTORY_ADD_SCALE_FACTOR - (INVENTORY_ADD_SCALE_FACTOR - 1.0) * animation_state.progress
        else:  # "remove"
            # Animation de suppression : de la position actuelle (1x) vers le centre de l'écran (10x)
            animation_state.opacity = int(255 * (1 - animation_state.progress))
            # Interpolation de position : de la position de départ vers le centre de l'écran
            animation_state.offset_x = animation_state.start_x + (animation_state.screen_center_x - animation_state.start_x) * animation_state.progress - animation_state.start_x
            animation_state.offset_y = animation_state.start_y + (animation_state.screen_center_y - animation_state.start_y) * animation_state.progress - animation_state.start_y
            # Interpolation d'échelle : de 1x à 10x
            animation_state.scale = 1.0 + (INVENTORY_REMOVE_SCALE_FACTOR - 1.0) * animation_state.progress
            
            # Générer les particules d'explosion au bon moment
            # Note: L'implémentation utilise le système de particules global (spec 14)
            if (old_progress < INVENTORY_REMOVE_EXPLOSION_START and 
                animation_state.progress >= INVENTORY_REMOVE_EXPLOSION_START and
                animation_state.particle_effect_id is None):
                # Mettre à jour la position de base des particules au centre de l'écran
                animation_state.particle_base_x = animation_state.screen_center_x
                animation_state.particle_base_y = animation_state.screen_center_y
                # Créer les particules d'explosion via le système de particules global
                # camera_x est passé en paramètre à update_animations()
                self._create_explosion_particles(animation_state, item_id, camera_x)
        
        # Si l'animation est terminée, supprimer l'état
        # Note: Les particules sont gérées par le système de particules global,
        # elles seront automatiquement nettoyées une fois leur durée de vie écoulée
        if animation_state.is_complete:
            del self._item_animations[item_id]

def _create_explosion_particles(self, animation_state: ItemAnimationState, item_id: str, camera_x: float) -> None:
    """Crée les particules d'explosion de flamme pour une animation de suppression.
    
    Cette méthode utilise le système de particules global (spécification 14) pour créer
    et gérer les effets de particules. L'explosion utilise une palette de couleurs chaudes
    (rouge, orange, jaune) pour créer un effet de flamme colorée et dynamique, indépendamment
    de la couleur de l'objet.
    
    Args:
        animation_state: État d'animation pour lequel créer les particules
        item_id: Identifiant de l'objet (utilisé pour créer un identifiant unique pour l'effet)
        camera_x: Position horizontale de la caméra (nécessaire pour convertir les coordonnées écran en coordonnées monde)
    
    Note:
        Si le système de particules n'est pas disponible, la méthode retourne silencieusement
        sans créer d'effet (pas d'erreur levée pour permettre le fonctionnement sans particules).
    """
    if self.particle_system is None:
        # Si le système de particules n'est pas disponible, ignorer silencieusement
        # (pas d'erreur levée pour permettre le fonctionnement sans particules)
        return
    
    from moteur_jeu_presentation.particles import create_flame_explosion_config
    
    # Créer la configuration d'explosion de flamme
    # La taille des particules est multipliée par le facteur d'agrandissement pour correspondre à la taille de l'objet
    config = create_flame_explosion_config(
        count=INVENTORY_REMOVE_PARTICLES_COUNT,
        speed=INVENTORY_REMOVE_PARTICLES_SPEED,
        lifetime=INVENTORY_REMOVE_PARTICLES_LIFETIME,
        size=int(INVENTORY_REMOVE_PARTICLES_SIZE * INVENTORY_REMOVE_SCALE_FACTOR),  # Taille agrandie
    )
    
    # Créer l'effet de particules via le système global
    # Note: Le centre de l'écran est en coordonnées écran, mais le système de particules
    # utilise des coordonnées monde. Il faut convertir les coordonnées écran en coordonnées monde
    # en ajoutant la position de la caméra (camera_x) pour la coordonnée X.
    # Pour la coordonnée Y, le centre de l'écran en coordonnées écran correspond directement
    # à la coordonnée Y en coordonnées monde (pas de décalage vertical de caméra dans ce jeu).
    # 
    # Conversion: world_x = screen_x + camera_x, world_y = screen_y
    effect_id = f"inventory_remove_{item_id}"
    
    # Convertir les coordonnées écran en coordonnées monde
    # particle_base_x et particle_base_y sont en coordonnées écran (centre de l'écran)
    world_x = animation_state.particle_base_x + camera_x  # Conversion: screen_x + camera_x
    world_y = animation_state.particle_base_y  # Généralement identique en coordonnées monde (pas de décalage vertical)
    
    self.particle_system.create_effect(
        world_x,
        world_y,
        config,
        effect_id=effect_id
    )
    
    # Enregistrer l'identifiant de l'effet pour pouvoir le suivre si nécessaire
    animation_state.particle_effect_id = effect_id
```

#### Intégration dans le rendu

La méthode `get_display_commands()` doit prendre en compte les animations en cours :

- **Pour les objets avec animation d'ajout** : 
  - Appliquer l'opacité calculée (`set_alpha()` sur la surface avant le blit)
  - Appliquer l'échelle calculée (`pygame.transform.scale()` ou `pygame.transform.smoothscale()` pour redimensionner la surface)
  - Appliquer le décalage de position (position ajustée avec `offset_x` et `offset_y` pour interpoler entre le centre de l'écran et la position finale)
- **Pour les objets avec animation de suppression** : 
  - Appliquer l'opacité calculée (`set_alpha()` sur la surface avant le blit)
  - Appliquer l'échelle calculée (`pygame.transform.scale()` ou `pygame.transform.smoothscale()` pour redimensionner la surface)
  - Appliquer le décalage de position (position ajustée avec `offset_x` et `offset_y` pour interpoler entre la position de départ et le centre de l'écran)
  - **Note** : Les particules d'explosion sont gérées et rendues séparément par le système de particules global via `particle_system.get_display_commands(camera_x)` dans la boucle principale
- **Pour les objets sans animation** : Affichage normal (opacité 255, scale 1.0, pas de décalage)

**Note importante sur le rendu avec échelle** :
- Lors du redimensionnement avec `pygame.transform.scale()`, la position de rendu doit être ajustée pour que l'objet reste centré sur sa position cible. Par exemple, si l'objet fait 64x64 pixels normalement et est redimensionné à 640x640 pixels (scale 10.0), il faut soustraire `(640 - 64) / 2 = 288` pixels à la position X et Y pour centrer correctement l'objet.
- La formule de centrage : `rendered_x = target_x - (sprite_width * (scale - 1.0) / 2.0)`, `rendered_y = target_y - (sprite_height * (scale - 1.0) / 2.0)`

**Rendu des particules** :
- Les particules sont rendues via le système de particules global (spécification 14)
- Les particules sont rendues via `particle_system.get_display_commands(camera_x)` dans la boucle principale du jeu
- Les particules sont rendues après l'objet (au-dessus) pour un effet visuel optimal
- Le système de particules global gère automatiquement la mise à jour, le nettoyage et le rendu des particules

**Note importante** : Les objets en cours d'animation de suppression doivent toujours être rendus tant que l'animation n'est pas terminée (y compris les particules), même si leur quantité dans `self.items` est déjà à 0. Cela permet d'afficher l'animation de disparition complète avant de retirer complètement l'objet de l'affichage.

**Intégration avec le système de particules global** :
- L'inventaire **doit** utiliser le système de particules global (spécification 14) pour créer et gérer les effets de particules lors de la destruction d'objets
- Les particules sont créées via `particle_system.create_effect()` avec une configuration d'explosion de flamme (`create_flame_explosion_config()`)
- **La couleur des particules n'est pas extraite de l'objet** - toutes les explosions utilisent une palette de couleurs chaudes (rouge, orange, jaune) pour créer un effet de flamme colorée et dynamique
- Le rendu utilise `particle_system.get_display_commands(camera_x)` dans la boucle principale pour obtenir les commandes de dessin
- Le système de particules global gère automatiquement la mise à jour, le nettoyage et le rendu des particules

**Optimisations de performance** :
- **Cache de surface de particules** : Le système de particules global gère automatiquement le cache de surfaces (voir spécification 14)
- **Limitation du nombre de particules** : Le nombre de particules est configurable via `INVENTORY_REMOVE_PARTICLES_COUNT` pour ajuster les performances selon les besoins
- **Couleur des particules** : Les particules utilisent une palette de couleurs chaudes prédéfinie (rouge, orange, jaune) - pas d'extraction de couleur nécessaire, ce qui améliore les performances
- **Nettoyage automatique** : Les particules mortes sont automatiquement supprimées par le système de particules global

## Intégration

### Classe `Player`

L'inventaire est intégré directement dans la classe `Player` :

```python
class Player(Entity):
    def __init__(
        self,
        ...
        inventory_config: Optional[InventoryItemConfig] = None,
    ) -> None:
        # ... initialisation existante ...
        self.inventory = Inventory(item_config=inventory_config)
    
    def get_inventory_draw_commands(
        self, 
        camera_x: float
    ) -> List[Tuple[pygame.Surface, Tuple[int, int]]]:
        """Génère les commandes de dessin pour l'inventaire.
        
        Args:
            camera_x: Position horizontale de la caméra
            
        Returns:
            Liste des commandes de dessin (surface, position)
        """
        # Récupérer la position du prénom
        name_command = self.get_name_draw_command(camera_x)
        if name_command is None:
            return []
        
        name_surface, (name_x, name_y) = name_command
        
        # Calculer la position de l'inventaire au-dessus du prénom
        # Note: screen_width et screen_height doivent être récupérés depuis la surface d'affichage ou passés en paramètre
        screen_width = 1280  # À récupérer depuis la configuration ou la surface d'affichage
        screen_height = 720  # À récupérer depuis la configuration ou la surface d'affichage
        return self.inventory.get_display_commands(
            camera_x=camera_x,
            player_x=self.x,
            player_y=self.y,
            name_y=name_y,
            screen_width=screen_width,
            screen_height=screen_height
        )
    
    def draw_inventory(self, surface: pygame.Surface, camera_x: float) -> None:
        """Dessine l'inventaire au-dessus du prénom."""
        commands = self.get_inventory_draw_commands(camera_x)
        if commands:
            surface.blits(commands, False)
```

### Boucle principale (`main.py`)

Dans la boucle principale du jeu :

1. **Chargement de la configuration** :
   ```python
   from moteur_jeu_presentation.inventory import InventoryItemLoader, InventoryItemConfig
   
   # Charger la configuration des objets d'inventaire (optionnel)
   inventory_config = None
   inventory_config_path = Path("config/inventory_items.toml")
   if inventory_config_path.exists():
       try:
           item_loader = InventoryItemLoader(inventory_config_path)
           inventory_config = item_loader.load_items()
           print(f"Configuration d'inventaire chargée : {len(inventory_config.items)} objets")
       except Exception as e:
           print(f"Warning: Impossible de charger la configuration d'inventaire : {e}")
   ```
   
2. **Initialisation du système de particules** :
   ```python
   # Créer le système de particules global
   from moteur_jeu_presentation.particles import ParticleSystem
   
   particle_system = ParticleSystem()
   ```

3. **Préchargement automatique des sprites (géré par AssetPreloader)** :
   ```python
   # Le préchargement est maintenant géré automatiquement par AssetPreloader
   # avant l'affichage de l'écran d'accueil (voir spécification 17).
   # Les caches globaux sont automatiquement remplis :
   # - _global_inventory_sprite_sheet_cache
   # - _global_inventory_cached_surfaces
   
   # Si le préchargement est désactivé (--skip-preload), un fallback est disponible :
   if args.skip_preload:
       inventory = Inventory(item_config=inventory_config)
       inventory.preload_all_sprites()  # Remplit les caches globaux
   ```

4. **Initialisation de l'inventaire et du joueur** :
   ```python
   # Créer l'inventaire (les caches globaux sont déjà remplis par AssetPreloader)
   inventory = Inventory(
       item_config=inventory_config,
       particle_system=particle_system  # Passer la référence au système de particules global
   )
   
   # Initialiser le joueur
   player = Player(
       x=640.0,
       y=360.0,
       ...
       inventory_config=inventory_config,
   )
   
   # Passer la référence au système de particules global à l'inventaire du joueur
   player.inventory.set_particle_system(particle_system)
   
   # Note: Les caches sont maintenant partagés automatiquement via les caches globaux
   # définis dans assets.preloader, donc il n'est plus nécessaire de partager
   # manuellement les caches (_sprite_sheet_cache) entre les instances.
   ```

5. **Mise à jour des animations et du système de particules** :
   ```python
   def update(dt: float, camera_x: float) -> None:
       # ... autres mises à jour ...
       
       # Mettre à jour le système de particules global
       particle_system.update(dt)
       
       # Mettre à jour les animations d'inventaire (passer camera_x pour la conversion des coordonnées)
       player.inventory.update_animations(dt, camera_x)
   ```

6. **Rendu** :
   ```python
   def draw_entities(surface: pygame.Surface, camera_x: float) -> None:
       # Dessiner le personnage
       player.draw(surface, camera_x)
       
       # Dessiner l'inventaire (au-dessus du prénom)
       player.draw_inventory(surface, camera_x)
       
       # Dessiner le prénom (au-dessus du personnage)
       player.draw_name(surface, camera_x)
       
       # Rendre les particules (y compris celles de l'inventaire)
       particle_commands = particle_system.get_display_commands(camera_x)
       if particle_commands:
           surface.blits(particle_commands, False)
   ```

### Ajout/suppression d'objets

Les objets peuvent être ajoutés ou retirés de l'inventaire via l'API de la classe `Inventory`. Les objets sont référencés par leur **ID technique** défini dans le fichier de configuration :

```python
# Ajouter un objet (utiliser l'ID technique défini dans inventory_items.toml)
player.inventory.add_item("document_etoile", quantity=1)
player.inventory.add_item("loupe_magique", quantity=1)

# Vérifier si un objet est présent
if player.inventory.has_item("document_etoile"):
    print("Le joueur possède un document avec étoile")

# Retirer un objet
player.inventory.remove_item("document_etoile", quantity=1)

# Obtenir la quantité d'un objet
quantity = player.inventory.get_quantity("loupe_magique")
```

### Intégration avec le système d'événements

L'inventaire est intégré avec le système d'événements (spécification 11) pour :
- Ajouter des objets lors de la progression dans le niveau (via des événements de type `inventory_add`)
- Retirer des objets lors de la progression dans le niveau (via des événements de type `inventory_remove`)
- Les animations d'ajout et de suppression sont automatiquement déclenchées lors de ces événements

### Intégration avec les PNJ et dialogues

L'inventaire est intégré avec le système de PNJ (spécification 12) pour :
- Recevoir des objets des PNJ lors de dialogues (via le champ `add_items` dans les échanges de dialogue)
- Donner des objets aux PNJ lors de dialogues (via le champ `remove_items` dans les échanges de dialogue)
- Les animations d'ajout et de suppression sont automatiquement déclenchées lors de ces actions dans les dialogues
- Vérifier la présence d'objets pour débloquer des dialogues conditionnels (évolution future)

## Gestion des erreurs

| Cas | Gestion | Message |
| --- | --- | --- |
| Fichier `inventory_items.toml` introuvable | Logger un avertissement, continuer sans configuration | `Warning: Inventory config file not found at {path}, continuing without item definitions` |
| Section `[items.*]` manquante `sprite_path` | Lever `ValueError` lors du chargement | `Missing sprite_path in item '{item_id}'` |
| Section `[items.*]` manquante `cell_width`, `cell_height`, `cell_row`, `cell_col` | Lever `ValueError` lors du chargement | `Missing cell_width/cell_height/cell_row/cell_col in item '{item_id}'` |
| Sprite sheet introuvable | Lever `FileNotFoundError` lors du chargement | `Sprite sheet not found for item '{item_id}': {sprite_path}` |
| Cellule hors limites du sprite sheet | Lever `ValueError` lors du chargement | `Cell ({cell_row}, {cell_col}) out of bounds for sprite sheet '{sprite_path}'` |
| ID d'objet inexistant lors de l'ajout | Logger un avertissement, ignorer l'ajout | `Warning: Unknown item ID '{item_id}', ignoring` |
| Quantité négative lors de l'ajout | Lever `ValueError` | `Quantity must be positive (got {quantity})` |
| Retrait d'un objet absent | Retourner `False`, logger un avertissement | `Warning: Cannot remove item '{item_id}': not in inventory` |
| Retrait d'une quantité supérieure à la quantité disponible | Retourner `False`, logger un avertissement | `Warning: Cannot remove {quantity} of '{item_id}': only {available} available` |

## Pièges courants

1. **Ordre des champs dans les dataclasses** : Dans les dataclasses Python, tous les champs avec des valeurs par défaut doivent être placés après les champs sans valeurs par défaut. Sinon, Python lève une `TypeError: non-default argument follows default argument`. Par exemple, dans `InventoryItem`, les champs obligatoires (`item_id`, `name`, `sprite_path`, `cell_width`, etc.) doivent venir avant les champs optionnels (`description`, `sprite_surface`).
2. **Caches globaux** : Les caches `_sprite_sheet_cache` et `_cached_surfaces` sont maintenant des références vers les caches globaux définis dans `assets.preloader`. Ne pas créer de nouveaux dictionnaires locaux, utiliser les références aux caches globaux.
3. **Extraction de cellules incorrecte** : Vérifier que les coordonnées de cellule (`cell_row`, `cell_col`) correspondent bien à la position de l'objet dans le sprite sheet. Les indices commencent à 0 (première ligne/colonne = 0)
4. **Dimensions de cellules incorrectes** : S'assurer que `cell_width` et `cell_height` correspondent exactement à la taille des cellules dans le sprite sheet. Une erreur de dimension entraînera un décalage lors de l'extraction
5. **Préchargement** : Le préchargement est maintenant géré automatiquement par `AssetPreloader` (spec 17). Ne pas appeler manuellement `preload_all_sprites()` sauf si `--skip-preload` est utilisé
6. **Position incorrecte** : Vérifier que la position de l'inventaire est calculée correctement par rapport au prénom et au personnage
7. **Cache non vidé** : Si les sprite sheets sont modifiés pendant le développement, redémarrer l'application pour vider les caches globaux
8. **Ordre d'affichage** : S'assurer que l'inventaire est dessiné avant le prénom pour que le prénom soit au-dessus (ou après, selon l'ordre souhaité)
9. **Performance avec beaucoup d'objets** : Les surfaces des objets extraits sont déjà mises en cache dans les caches globaux. Utiliser `blits()` pour dessiner plusieurs objets en une seule opération
10. **Coordonnées de caméra** : S'assurer que les coordonnées de l'inventaire sont correctement ajustées avec la caméra (comme pour le prénom)
11. **Configuration manquante** : Gérer le cas où `inventory_config` est `None` (afficher les objets même sans configuration, en utilisant l'ID technique comme nom)
12. **Cellules hors limites** : Valider que les cellules (`cell_row`, `cell_col`) sont dans les limites du sprite sheet lors du chargement de la configuration pour éviter des erreurs à l'exécution
13. **Particules d'explosion** : S'assurer que les particules sont correctement initialisées lors de la création de l'animation de suppression (position de base enregistrée). Les particules sont gérées par le système de particules global et sont automatiquement mises à jour et rendues. La position des particules doit être correctement ajustée avec la caméra lors du rendu. **Note** : Voir la spécification 14 (moteur de particules) pour les détails d'implémentation des particules. **La couleur des particules n'est pas extraite de l'objet** - toutes les explosions utilisent une palette de couleurs chaudes (rouge, orange, jaune) pour créer un effet de flamme colorée.
14. **Intégration avec le système de particules global** : 
    - **Utilisation obligatoire** : L'inventaire **doit** utiliser le système de particules global (spécification 14) pour créer et gérer les effets de particules lors de la destruction d'objets
    - **Initialisation** : Le système de particules global doit être initialisé et passé à l'inventaire via le constructeur ou `set_particle_system()`
    - **Configuration** : Utiliser `create_flame_explosion_config()` du système de particules global avec les variables globales de l'inventaire pour créer la configuration d'explosion de flamme
    - **Couleur des particules** : **Ne pas extraire la couleur de l'objet** - utiliser `create_flame_explosion_config()` qui génère automatiquement une palette de couleurs chaudes (rouge, orange, jaune) avec une variation importante pour créer un effet de flamme colorée et dynamique
    - **Rendu** : Les particules sont rendues via `particle_system.get_display_commands(camera_x)` dans la boucle principale du jeu
    - **Performance** : Le système de particules global gère automatiquement le cache de surfaces, le nettoyage et les optimisations
    - **Coordonnées** : Attention à la conversion entre coordonnées écran et coordonnées monde lors de la création des particules (le centre de l'écran est en coordonnées écran, mais le système de particules utilise des coordonnées monde)
15. **Timing de création des particules** : 
    - **Problème** : Les particules sont créées dans `update_animations()` quand `progress >= INVENTORY_REMOVE_EXPLOSION_START`, mais la position de base (`particle_base_x`, `particle_base_y`) doit être définie au centre de l'écran. Si `update_animations()` est appelé avant `get_display_commands()` dans la boucle principale, les particules seront créées avec position 0.0 et se déplaceront depuis cette position incorrecte.
    - **Solution** : Mettre à jour la position de base des particules au centre de l'écran (`screen_center_x`, `screen_center_y`) juste avant de créer les particules dans `update_animations()`. S'assurer que `screen_center_x` et `screen_center_y` sont correctement initialisés lors de la création de l'animation de suppression.
    - **Mise à jour de la position de base** : S'assurer que la position de base est mise à jour pour tous les objets en animation de suppression, même ceux qui ne sont pas dans `item_surfaces` (par exemple, si le sprite n'a pas pu être chargé). Utiliser une position approximative basée sur la position de l'inventaire si nécessaire.
16. **Animation d'ajout - Position et échelle** :
    - **Position du centre de l'écran** : Lors de la création de l'animation d'ajout, s'assurer que `screen_center_x` et `screen_center_y` sont correctement calculés à partir de `screen_width` et `screen_height` (généralement `screen_center_x = screen_width / 2`, `screen_center_y = screen_height / 2`).
    - **Position cible** : La position cible (`target_x`, `target_y`) doit être calculée dans `get_display_commands()` avant de créer l'animation, car elle dépend de la position de l'objet dans l'inventaire (qui peut changer si d'autres objets sont ajoutés/supprimés).
    - **Interpolation de position** : L'interpolation de position doit se faire en coordonnées écran (pas en coordonnées monde), car le centre de l'écran est une position fixe à l'écran, indépendante de la caméra.
    - **Centrage avec échelle** : Lors du rendu avec échelle, ajuster la position de rendu pour centrer correctement l'objet. Si l'objet fait `w x h` pixels et est redimensionné à `w * scale x h * scale`, soustraire `(w * (scale - 1.0) / 2.0)` à la position X et `(h * (scale - 1.0) / 2.0)` à la position Y.
17. **Animation de suppression - Position et échelle** :
    - **Position de départ** : Lors de la création de l'animation de suppression, enregistrer la position actuelle de l'objet dans l'inventaire (`start_x`, `start_y`) en coordonnées écran.
    - **Position du centre de l'écran** : S'assurer que `screen_center_x` et `screen_center_y` sont correctement calculés et enregistrés lors de la création de l'animation.
    - **Interpolation de position** : L'interpolation de position doit se faire en coordonnées écran, de la position de départ vers le centre de l'écran.
    - **Particules agrandies** : Les particules doivent être créées avec une taille multipliée par `INVENTORY_REMOVE_SCALE_FACTOR` pour correspondre à la taille de l'objet au moment de l'explosion. Attention : cela peut créer des particules très grandes (ex: 16 * 10 = 160 pixels), ce qui peut impacter les performances. Considérer l'utilisation d'un facteur d'agrandissement plus modéré pour les particules si nécessaire.
18. **Performance avec échelle** :
    - **Redimensionnement de surfaces** : Le redimensionnement avec `pygame.transform.scale()` ou `pygame.transform.smoothscale()` peut être coûteux en performance, surtout pour des objets agrandis 10 fois. Considérer la mise en cache des surfaces redimensionnées si plusieurs objets utilisent la même animation simultanément.
    - **Taille des particules** : Les particules agrandies (10x) peuvent être très grandes et impacter les performances. Surveiller le nombre de particules et leur taille, et ajuster `INVENTORY_REMOVE_PARTICLES_COUNT` et `INVENTORY_REMOVE_PARTICLES_SIZE` si nécessaire.

## Tests

### Tests unitaires

- `test_inventory_add_item()` : Vérifier que `add_item()` ajoute correctement un objet
- `test_inventory_remove_item()` : Vérifier que `remove_item()` retire correctement un objet
- `test_inventory_has_item()` : Vérifier que `has_item()` retourne les bonnes valeurs
- `test_inventory_quantity()` : Vérifier que `get_quantity()` retourne les bonnes quantités
- `test_inventory_loader_load()` : Vérifier que `InventoryItemLoader.load_items()` charge correctement un fichier TOML valide avec sprite sheets
- `test_inventory_loader_validation()` : Vérifier que la validation détecte les sections manquantes, sprite sheets introuvables, cellules hors limites, etc.
- `test_inventory_cell_extraction()` : Vérifier que l'extraction de cellules depuis un sprite sheet fonctionne correctement avec les bonnes coordonnées (cell_row, cell_col)
- `test_inventory_global_cache()` : Vérifier que les caches globaux `_global_inventory_sprite_sheet_cache` et `_global_inventory_cached_surfaces` sont correctement utilisés et partagés entre les instances
- `test_inventory_preload_all_sprites()` : Vérifier que `preload_all_sprites()` remplit les caches globaux correctement (utilisé comme fallback si `--skip-preload`)
- `test_inventory_display_commands()` : Vérifier que `get_display_commands()` génère les bonnes commandes de dessin
- `test_inventory_positioning()` : Vérifier que l'inventaire est positionné correctement au-dessus du prénom
- `test_inventory_add_animation_scale_and_position()` : Vérifier que l'animation d'ajout affiche l'objet au centre de l'écran à 10x, puis le réduit et le déplace vers la position finale
- `test_inventory_remove_animation_scale_and_position()` : Vérifier que l'animation de suppression déplace l'objet de sa position actuelle vers le centre de l'écran en l'agrandissant de 1x à 10x
- `test_inventory_remove_animation_particles()` : Vérifier que les particules d'explosion de flamme sont créées au centre de l'écran lors de l'animation de suppression via le système de particules global, qu'elles sont agrandies d'un facteur 10, qu'elles se déplacent correctement et disparaissent après leur durée de vie
- `test_inventory_particle_flame_colors()` : Vérifier que les particules utilisent une palette de couleurs chaudes (rouge, orange, jaune) avec variation via `create_flame_explosion_config()`, et non la couleur de l'objet
- `test_inventory_particle_system_integration()` : Vérifier que l'inventaire utilise bien le système de particules global pour créer les effets de particules lors de la destruction d'objets
- `test_inventory_particle_count_configurable()` : Vérifier que le nombre de particules peut être configuré via `INVENTORY_REMOVE_PARTICLES_COUNT` et que cela affecte bien le nombre de particules créées dans le système de particules global
- `test_inventory_animation_screen_center_calculation()` : Vérifier que le centre de l'écran est correctement calculé à partir de `screen_width` et `screen_height`

### Tests d'intégration

1. Lancer le jeu → vérifier que l'inventaire est vide initialement
2. Vérifier que les sprites sont préchargés au démarrage (vérifier les logs de préchargement)
3. Ajouter un objet via `player.inventory.add_item("document_etoile")` → vérifier que l'objet apparaît au centre de l'écran à 10x, puis se réduit et se déplace vers sa position finale dans l'inventaire au-dessus du prénom
4. Ajouter plusieurs objets (`document_etoile`, `loupe_magique`) → vérifier qu'ils sont tous affichés avec le bon espacement, et que chaque ajout déclenche l'animation d'apparition au centre de l'écran
5. Vérifier que les deux objets utilisent le même sprite sheet mais des cellules différentes
6. Retirer un objet → vérifier qu'il se déplace de sa position actuelle vers le centre de l'écran en s'agrandissant (1x à 10x), puis explose avec des particules agrandies au centre de l'écran
7. Déplacer le personnage → vérifier que l'inventaire suit le mouvement
8. Changer de niveau (si applicable) → vérifier que l'inventaire persiste

### Vérifications visuelles

- L'inventaire est affiché au-dessus du prénom du joueur
- Les objets sont correctement espacés horizontalement
- Les objets sont centrés par rapport au personnage
- Les objets suivent le mouvement du personnage et de la caméra
- Les sprites sont correctement chargés et affichés
- L'inventaire ne gêne pas la lecture du prénom
- **Lors de l'ajout d'un objet** :
  - L'objet apparaît au centre de l'écran à une taille 10 fois plus grande que la normale
  - L'objet diminue progressivement de taille (de 10x à 1x) tout en se déplaçant vers sa position finale dans l'inventaire
  - L'animation est fluide et spectaculaire
- **Lors de la suppression d'un objet** :
  - L'objet part de sa position actuelle dans l'inventaire et se déplace vers le centre de l'écran
  - L'objet augmente progressivement de taille (de 1x à 10x) pendant le déplacement
  - Les particules d'explosion de flamme apparaissent au centre de l'écran au moment où l'objet atteint le centre
  - Les particules sont agrandies d'un facteur 10 pour correspondre à la taille de l'objet
  - Les particules se dispersent dans toutes les directions depuis le centre de l'écran
  - Les particules utilisent une palette de couleurs chaudes (rouge, orange, jaune) avec une variation importante pour créer un effet de flamme colorée et dynamique, indépendamment de la couleur de l'objet
  - Les particules disparaissent progressivement avec un effet de fade-out
  - L'animation complète (déplacement + agrandissement + explosion) est voyante et attire l'attention du joueur

## Évolutions futures

- **Système de quantité** : Afficher le nombre d'exemplaires d'un objet si la quantité > 1 (badge numérique)
- **Interface d'inventaire complète** : Créer une interface dédiée (touche `I` pour ouvrir) avec liste détaillée des objets, descriptions, etc.
- **Objets utilisables** : Permettre d'utiliser des objets depuis l'inventaire (potions, clés, etc.)
- **Objets empilables/non-empilables** : Définir si un objet peut être présent en plusieurs exemplaires ou non
- **Objets rares/communs** : Système de rareté pour les objets
- **Système de quêtes** : Intégrer l'inventaire avec un système de quêtes (collecter X objets, donner Y objets à un PNJ)
- **Sauvegarde/chargement** : Persister l'inventaire dans un fichier de sauvegarde
- **Limite d'inventaire** : Implémenter une limite de poids ou de nombre d'objets
- **Tri et organisation** : Permettre de trier les objets par type, rareté, etc.
- **Recherche** : Permettre de rechercher un objet dans l'inventaire
- **Objets équipables** : Système d'équipement (armes, armures, etc.) séparé de l'inventaire général

## Références

- Bonnes pratiques : `bonne_pratique.md`
- Spécification personnage principal : `spec/2-personnage-principal.md`
- Spécification système de niveaux : `spec/7-systeme-de-niveaux-personnage.md`
- Spécification système d'événements : `spec/11-systeme-gestion-avancement-niveau.md`
- Spécification système de PNJ : `spec/12-systeme-de-personnage-non-joueur.md`
- **Spécification moteur de particules** : `spec/14-moteur-de-particules.md` (utilisé pour les effets de particules lors de la suppression d'objets)
- Documentation Pygame : [pygame.Surface](https://www.pygame.org/docs/ref/surface.html)

## Structure de fichiers recommandée

```
moteur_jeu_presentation/
├── config/
│   └── inventory_items.toml          # Fichier de configuration des objets (voir exemple ci-dessous)
├── sprite/
│   └── items/                        # Répertoire des sprite sheets d'objets d'inventaire
│       ├── outils_niveau_decouverte.png  # Sprite sheet contenant les objets d'inventaire
│       └── ...
├── src/
│   └── moteur_jeu_presentation/
│       ├── entities/
│       │   └── player.py             # Classe Player (modifiée)
│       └── inventory/
│           ├── __init__.py
│           ├── config.py             # InventoryItem, InventoryItemConfig
│           ├── loader.py             # InventoryItemLoader
│           └── inventory.py          # Inventory
└── ...
```

### Fichier d'exemple de configuration

Le fichier `config/inventory_items.toml` suivant est un exemple complet utilisant le sprite sheet `outils_niveau_decouverte.png` :

```toml
# Fichier : config/inventory_items.toml
# Configuration des objets d'inventaire disponibles dans le jeu
# Les objets sont définis à partir de sprite sheets avec un système de cellules

# Document avec étoile (premier objet, cellule 0,0)
[items.document_etoile]
name = "Document avec étoile"
description = "Un document important marqué d'une étoile dorée"
sprite_path = "sprite/items/outils_niveau_decouverte.png"
cell_width = 64
cell_height = 64
cell_row = 0
cell_col = 0

# Loupe magique (deuxième objet, cellule 0,1)
[items.loupe_magique]
name = "Loupe magique"
description = "Une loupe magique avec un orbe lumineux qui émet des particules"
sprite_path = "sprite/items/outils_niveau_decouverte.png"
cell_width = 64
cell_height = 64
cell_row = 0
cell_col = 1
```

**Note** : Ce fichier d'exemple utilise le sprite sheet `sprite/items/outils_niveau_decouverte.png` qui contient 2 objets côte à côte (128x64 pixels, 2 cellules de 64x64 pixels). Les objets sont référencés par leur ID technique (`document_etoile` et `loupe_magique`) dans le code du jeu.

---

**Date de création** : 2024  
**Statut** : ✅ Implémenté

