# 2 - Personnage principal avec animations de marche

## Contexte

Cette spécification définit l'intégration du personnage principal du jeu avec son système d'animation de marche. Le personnage doit pouvoir se déplacer dans les quatre directions cardinales avec des animations appropriées basées sur un sprite sheet.

## Objectifs

- Intégrer le personnage principal dans le jeu
- Implémenter un système d'animation basé sur un sprite sheet
- Gérer les animations de marche pour les directions gauche et droite
- Permettre le contrôle du personnage via le clavier
- Intégrer le personnage dans la couche de gameplay (depth 2) du système de parallaxe
- Afficher le **nom affiché** du personnage (chaîne **`display_name`** dans `config/player_stats.toml`, spécification **7**) centré au-dessus de la tête du personnage, synchronisé avec ses mouvements — **aucune** valeur par défaut dans le code du `Player` ; absence ou valeur vide de `display_name` dans le TOML → erreur explicite au chargement de la configuration
- **Système d'interaction avec les PNJ** : Afficher une indication visuelle lorsque le joueur est à proximité d'un PNJ (distance <= 200 pixels) et permettre de lancer un dialogue avec la touche 'T'
- **Système de level up** : Afficher "level up (press u)" en jaune clignotant au-dessus du nom du personnage principal lorsque l'événement de level up est déclenché (voir spécification 11). Le joueur peut appuyer sur la touche 'U' pour confirmer le level up, ce qui augmente réellement le niveau du personnage de **+1 uniquement** (sans dépasser `MAX_PLAYER_LEVEL`) en utilisant les mécanismes existants (`player.set_level()`), puis masque l'affichage. L'augmentation est toujours de +1 niveau, il n'est pas possible d'augmenter de plusieurs niveaux en une seule fois.
- **Position initiale personnalisable** : Permettre de définir la position X initiale du personnage principal via un argument de ligne de commande (utile pour le développement, les tests et le débogage)

## Architecture

### Sprite Sheets

Le personnage utilise plusieurs sprite sheets selon son état, tous organisés par niveau (voir spécification 7) :

#### Sprite sheet de marche (`walk.png`)
Le sprite sheet `walk.png` contient les animations de marche du personnage :
- **Dimensions** : 512x256 pixels
- **Structure** : Grille de 4 lignes et 8 colonnes (selon spécification utilisateur)
- **Taille d'un sprite** : 64x64 pixels
- **Note** : Le fichier image réel contient 4 lignes et 8 colonnes, chaque sprite individuel fait 64x64 pixels
- **Système de niveaux** : Le sprite sheet est chargé via `level_manager.get_asset_path("walk.png")` et doit être présent dans chaque répertoire de niveau (`sprite/personnage/{niveau}/walk.png`)

#### Sprite sheet de saut (`jump.png`)
Le sprite sheet `jump.png` contient les animations de saut du personnage (voir spécification 6) :
- **Système de niveaux** : Le sprite sheet est chargé via `level_manager.get_asset_path("jump.png")` et doit être présent dans chaque répertoire de niveau (`sprite/personnage/{niveau}/jump.png`)

#### Sprite sheet de grimpe (`climb.png`) - Optionnel
Si une animation de grimpe est implémentée, le sprite sheet `climb.png` peut être utilisé :
- **Système de niveaux** : Le sprite sheet doit être chargé via `level_manager.get_asset_path("climb.png")` et doit être présent dans chaque répertoire de niveau (`sprite/personnage/{niveau}/climb.png`)
- **Note** : L'animation de grimpe est optionnelle. Si le fichier `climb.png` n'existe pas pour un niveau donné, la grimpe fonctionnera sans animation spécifique (le personnage utilisera l'animation de marche/idle pendant la grimpe)

### Mapping des lignes

Selon les spécifications utilisateur :
- **Ligne 2** (en partant du haut, index 1) : Animations de marche vers la **gauche**
- **Ligne 4** (en partant du haut, index 3) : Animations de marche vers la **droite**

**Note** : D'après l'analyse du sprite sheet, les lignes correspondent généralement à :
- Ligne 1 (index 0) : Marche vers le haut
- Ligne 2 (index 1) : Marche vers le bas
- Ligne 3 (index 2) : Marche vers la gauche
- Ligne 4 (index 3) : Marche vers la droite

Cependant, la spécification utilisateur indique d'utiliser la ligne 2 pour gauche et la ligne 4 pour droite, ce qui sera respecté dans l'implémentation.

### Système d'animation

- **Frame rate d'animation** : 8-12 FPS (frames par seconde) pour les animations de marche
- **Nombre de frames** : 8 frames par direction (selon les colonnes du sprite sheet)
- **Boucle d'animation** : Les animations se répètent en boucle pendant le mouvement
- **Affichage du nom** : Utiliser une police lisible (par ex. `PressStart2P-Regular.ttf` si disponible, sinon police système Arial/sans-serif en gras, 36 px par défaut) pour écrire le texte **`stats_config.display_name`** (issu de `config/player_stats.toml`) juste au-dessus de la tête du personnage (alignement automatique au sommet du sprite avec un léger espace configurable).
- **Positionnement du prénom** : Texte centré horizontalement par rapport au sprite, avec un offset vertical configurable (~12 px) pour le placer juste au-dessus de la tête.
- **Référence d'affichage** : Le calcul de la position du prénom utilise `display_width` et `display_height` (et non `sprite_width`/`sprite_height`) afin de rester aligné lorsque le sprite est redimensionné.
- **Suivi du mouvement** : Le texte se déplace et s'anime en même temps que le personnage (caméra incluse).
- **Couleur** : Texte blanc avec contour noir épais (2 px) pour garantir une excellente lisibilité sur tous les fonds, même complexes.
- **Rendu** : Utiliser l'anti-aliasing pour un rendu plus lisse et lisible du texte. Le texte utilise une surface `pygame.font.Font` rendue une fois lors de l'initialisation.

## Spécifications techniques

### Structure des données

#### Classe `Player`

```python
class Player:
    """Représente le personnage principal du jeu."""
    
    def __init__(
        self,
        x: float,
        y: float,
        sprite_sheet_path: str,
        sprite_width: int = 64,
        sprite_height: int = 64,
        animation_speed: float = 10.0,
        sprite_scale: float = 2.0,
        stats_config: "PlayerStatsConfig",
        font_path: Optional[str] = None,
        font_size: int = 28,
        name_color: Tuple[int, int, int] = (255, 255, 255),
        name_outline_color: Tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        """
        Args:
            x: Position horizontale initiale
            y: Position verticale initiale
            sprite_sheet_path: Chemin vers le fichier sprite sheet
            sprite_width: Largeur d'un sprite individuel dans le sprite sheet (64 pixels)
            sprite_height: Hauteur d'un sprite individuel dans le sprite sheet (64 pixels)
            animation_speed: Vitesse d'animation en frames par seconde
            sprite_scale: Facteur d'échelle pour l'affichage du sprite (défaut: 2.0 = 200%, double la taille)
            stats_config: Configuration des stats ; doit fournir display_name (non vide) pour le nom au-dessus du sprite
            font_path: Police à utiliser pour la bannière du nom (fallback sur `PressStart2P-Regular.ttf`)
            font_size: Taille de la police (en px, définie dans le repère de conception 1920x1080, convertie vers 1280x720 lors de l'initialisation)
            name_color: Couleur du texte principal
            name_outline_color: Couleur du contour du texte
        """
```

**Nom affiché** : aucun paramètre `name=` avec valeur par défaut. Le texte au-dessus du sprite est **`stats_config.display_name`**, lu depuis la racine de `config/player_stats.toml` (obligatoire, non vide — voir spécification **7**). En jeu normal, `stats_config` est toujours fourni après chargement du TOML.

**Propriétés** :
- `x: float` : Position horizontale du personnage
- `y: float` : Position verticale du personnage
- `speed: float` : Vitesse de déplacement en pixels par seconde (recommandé : 200-300)
- `sprite_sheet: pygame.Surface` : Surface contenant le sprite sheet complet
- `sprite_width: int` : Largeur d'un sprite dans le sprite sheet (64 pixels)
- `sprite_height: int` : Hauteur d'un sprite dans le sprite sheet (64 pixels)
- `sprite_scale: float` : Facteur d'échelle pour l'affichage du sprite (défaut: 2.0 = 200%, double la taille)
- `display_width: int` : Largeur d'affichage du sprite (sprite_width * sprite_scale)
- `display_height: int` : Hauteur d'affichage du sprite (sprite_height * sprite_scale)
- `current_direction: str` : Direction actuelle ("left", "right", "idle")
- `current_frame: int` : Index de la frame d'animation actuelle (0-7)
- `animation_timer: float` : Timer pour gérer la vitesse d'animation
- `animation_speed: float` : Vitesse d'animation en FPS
- `is_moving: bool` : Indique si le personnage est en mouvement
- `name_surface: pygame.Surface` : Surface contenant le prénom rendu
- `name_rect: pygame.Rect` : Rect calculé pour positionner le prénom
- `name_offset_y: float` : Décalage vertical appliqué après calcul automatique pour placer le prénom juste au-dessus du sprite (défaut : `-4.0` pour conserver un léger espace).
- `font: pygame.font.Font` : Police utilisée pour le prénom
- `name: str` : Texte du nom affiché au-dessus du sprite ; **identique** à `stats_config.display_name` en jeu normal (**aucun** défaut type `"Thomas"` dans le constructeur)
- `level_up_active: bool` : Indique si l'affichage de level up est actuellement visible (défaut: False)
- `level_up_text: str` : Texte à afficher pour le level up (défaut: "level up (press u)")
- `level_up_blink_timer: float` : Timer pour l'animation de clignotement du texte de level up (défaut: 0.0)
- `level_up_blink_speed: float` : Vitesse de clignotement en secondes (défaut: 0.5, clignote toutes les 0.5 secondes)
- `level_up_visible: bool` : Indique si le texte de level up est actuellement visible (pour l'animation de clignotement, défaut: True)
- `is_on_climbable: bool` : Indique si le personnage est sur un bloc grimpable (défaut: False)
- `climb_speed: float` : Vitesse de grimpe en pixels par seconde (défaut: 200.0)
- `is_climbing: bool` : Indique si le personnage est en train de grimper (défaut: False)
- `climb_frame: int` : Frame actuelle de l'animation de grimpe (défaut: 0)
- `climb_animation_timer: float` : Timer pour l'animation de grimpe (défaut: 0.0)
- `climb_animation_speed: float` : Vitesse d'animation de grimpe en FPS (défaut: 10.0)
- `climb_sprite_sheet: Optional[pygame.Surface]` : Sprite sheet de grimpe chargé (None si non disponible)

**Méthodes principales** :
- `update(dt: float, keys: pygame.key.ScancodeWrapper) -> None` : Met à jour la position et l'animation
- `draw(surface: pygame.Surface, camera_x: float) -> None` : Dessine le personnage (avec redimensionnement selon sprite_scale)
- `_get_current_sprite() -> pygame.Surface` : Récupère le sprite actuel à afficher (redimensionné selon sprite_scale). Vérifie dans l'ordre : animation de dialogue, animation de grimpe, animation de saut, animation de marche/idle
- `_scale_sprite(sprite: pygame.Surface) -> pygame.Surface` : Redimensionne un sprite selon le facteur d'échelle sprite_scale
- `_update_animation(dt: float) -> None` : Met à jour l'animation de marche/idle
- `_update_climb_animation(dt: float) -> None` : Met à jour l'animation de grimpe (si `is_climbing = True`)
- `_update_jump_animation(dt: float) -> None` : Met à jour l'animation de saut (si `is_jumping = True`)
- `_get_climb_sprite() -> Optional[pygame.Surface]` : Récupère le sprite de grimpe actuel à afficher (retourne None si pas en train de grimper ou sprite sheet non chargé)
- `_get_jump_sprite() -> Optional[pygame.Surface]` : Récupère le sprite de saut actuel à afficher (retourne None si pas en saut)
- `_handle_movement(keys: pygame.key.ScancodeWrapper, dt: float) -> None` : Gère le mouvement du personnage. Si `level_transition_active` est `True`, cette méthode doit retourner immédiatement sans traiter les inputs (le personnage est bloqué pendant la transition de niveau, voir spécification 11)
- `_handle_climb_input(keys: pygame.key.ScancodeWrapper, dt: float) -> float` : Gère l'input de grimpe et retourne le déplacement vertical (retourne 0.0 si pas de grimpe)
- `_render_name() -> None` : Génère la surface contenant le nom (`display_name`) avec contour
- `_draw_name(surface: pygame.Surface, camera_x: float) -> None` : Dessine le prénom au-dessus du personnage
- `show_level_up() -> None` : Active l'affichage du level up (appelé par le système d'événements, voir spécification 11)
- `hide_level_up() -> None` : Désactive l'affichage du level up (appelé lorsque le joueur appuie sur 'U')
- `_update_level_up_animation(dt: float) -> None` : Met à jour l'animation de clignotement du texte de level up
- `_draw_level_up(surface: pygame.Surface, camera_x: float) -> None` : Dessine le texte "level up (press u)" en jaune clignotant au-dessus du nom du personnage

### Mapping des directions

```python
# Mapping des lignes du sprite sheet selon spécification utilisateur
DIRECTION_TO_ROW = {
    "left": 1,   # Ligne 2 (index 1)
    "right": 3,  # Ligne 4 (index 3)
}
```

### Contrôles

- **Flèche gauche / Touche A** : Déplacement vers la gauche
- **Flèche droite / Touche D** : Déplacement vers la droite
- **Flèche haut / Touche W** : 
  - Si le personnage est sur un bloc grimpable (`is_on_climbable = True`) : Grimpe verticalement vers le haut (au lieu de sauter)
  - Sinon : Déclenche un saut (si le personnage est au sol)
- **Flèche bas / Touche S** : Déplacement vers le bas (si nécessaire)
- **Touche T** : Lancer un dialogue avec le PNJ le plus proche (si à moins de 200 pixels et qu'aucun dialogue n'est en cours)
- **Touche U** : Confirmer le level up en augmentant réellement le niveau du personnage de **+1 uniquement** (sans dépasser `MAX_PLAYER_LEVEL`) et masquer l'affichage "level up (press u)" (uniquement si l'affichage de level up est visible). L'augmentation du niveau utilise les mécanismes existants (`player.set_level(new_level)`) qui rechargent automatiquement les assets et mettent à jour les statistiques. L'augmentation est toujours de +1 niveau, il n'est pas possible d'augmenter de plusieurs niveaux en une seule fois. La confirmation déclenche également une animation de transition de niveau (voir spécification 11 pour les détails).

**Note importante** : `pygame.key.get_pressed()` retourne un objet `ScancodeWrapper` qui est indexable (comme une liste), pas un dictionnaire. Il faut donc utiliser l'indexation `keys[pygame.K_LEFT]` plutôt que `keys.get(pygame.K_LEFT)`.

### Argument de ligne de commande pour la position X initiale

Le jeu doit accepter un argument de ligne de commande `--player-x` (ou `--start-x`) pour définir la position X initiale du personnage principal au démarrage du jeu. Cet argument est utile pour le développement, les tests et le débogage.

#### Spécification de l'argument

- **Nom de l'argument** : `--player-x` (alias : `--start-x`)
- **Type** : Nombre flottant (float)
- **Valeur par défaut** : `None` (utilise la valeur par défaut : `render_width / 2`, c'est-à-dire le centre de l'écran dans le repère de rendu)
- **Description** : Position horizontale initiale du personnage principal en pixels **dans le repère de conception (1920x1080)**. Cette valeur est automatiquement convertie vers le repère de rendu interne (1280x720) lors de l'initialisation.
- **Validation** : La valeur doit être un nombre valide (positif ou négatif). Aucune validation de limites n'est effectuée (le personnage peut être positionné en dehors de l'écran visible)
- **Conversion** : La position fournie est multipliée par le facteur de conversion `scale_x = RENDER_WIDTH / DESIGN_WIDTH = 1280 / 1920 ≈ 0.6667` pour obtenir la position dans le repère de rendu interne

#### Implémentation dans `parse_arguments()`

L'argument doit être ajouté dans la fonction `parse_arguments()` de `main.py` :

```python
def parse_arguments() -> argparse.Namespace:
    """Parse les arguments de la ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Présentation- Jeu de plateforme",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    # ... autres arguments existants ...
    
    parser.add_argument(
        "--player-x",
        "--start-x",
        type=float,
        default=None,
        dest="player_x",
        help="Position X initiale du personnage principal en pixels (défaut: centre de l'écran)",
    )
    
    return parser.parse_args()
```

#### Utilisation dans l'initialisation du personnage

Dans la fonction `main()`, la position X initiale doit être déterminée en fonction de l'argument et convertie du repère de conception vers le repère de rendu :

```python
# Initialiser le personnage
# IMPORTANT : L'argument --player-x est dans le repère de conception (1920x1080)
# Il doit être converti vers le repère de rendu (1280x720)
from moteur_jeu_presentation.rendering.config import compute_design_scale

if args.player_x is not None:
    # Convertir la position X du repère de design (1920x1080) vers le repère de rendu (1280x720)
    scale_x, _ = compute_design_scale((render_width, render_height))
    initial_x = args.player_x * scale_x
else:
    # Position par défaut : centre de l'écran dans le repère de rendu
    initial_x = render_width / 2

player = Player(
    x=initial_x,  # Position X dans le repère de rendu (1280x720)
    y=100.0,  # Position initiale en haut pour tester la gravité
    sprite_width=64,
    sprite_height=64,
    animation_speed=10.0,
    player_level=level_config.player_level,
    stats_config=stats_config,  # display_name lu depuis player_stats.toml (obligatoire)
    inventory_config=inventory_config,
)
```

#### Exemples d'utilisation

**Note** : Les valeurs de position X sont dans le repère de conception (1920x1080). Elles sont automatiquement converties vers le repère de rendu (1280x720).

```bash
# Lancer le jeu avec le personnage au centre (comportement par défaut)
python -m moteur_jeu_presentation.main

# Lancer le jeu avec le personnage à la position X = 960 pixels (centre dans le repère 1920x1080)
python -m moteur_jeu_presentation.main --player-x 960

# Lancer le jeu avec le personnage à la position X = 0 (début du niveau dans le repère 1920x1080)
python -m moteur_jeu_presentation.main --start-x 0

# Lancer le jeu avec le personnage à la position X = 1920 (fin de l'écran dans le repère 1920x1080)
python -m moteur_jeu_presentation.main --player-x 1920

# Combiner avec d'autres arguments
python -m moteur_jeu_presentation.main --player-x 1000 --skip-splash --mps
```

#### Notes importantes

- **Repère de conception** : **IMPORTANT** - L'argument `--player-x` accepte des valeurs dans le **repère de conception (1920x1080)**, pas dans le repère de rendu (1280x720). La conversion est effectuée automatiquement lors de l'initialisation en multipliant la valeur par `scale_x = RENDER_WIDTH / DESIGN_WIDTH = 1280 / 1920 ≈ 0.6667`. Cette convention est cohérente avec les fichiers de configuration de niveau qui utilisent également le repère de conception.
- **Caméra** : La caméra suit automatiquement le personnage, donc si le personnage est positionné à une position X différente, la caméra s'ajustera en conséquence au démarrage
- **Collisions** : Le personnage peut être positionné en dehors de l'écran visible ou dans une zone avec des collisions. Aucune validation n'est effectuée pour vérifier que la position est valide
- **Progression** : Le système de progression (`LevelProgressTracker`) s'initialise avec la position initiale du joueur, donc la position X spécifiée sera prise en compte pour le suivi de progression
- **Compatibilité** : Cet argument est compatible avec tous les autres arguments existants (`--mps`, `--skip-splash`, `--profile`, etc.)

### Gestion de l'animation

1. **État idle** : Afficher la première frame (frame 0) de la dernière direction
2. **État en mouvement** : Animer les frames 0-7 en boucle
3. **Changement de direction** : Réinitialiser l'animation à la frame 0

### Calcul de la frame

Pour extraire un sprite du sprite sheet :
```python
def _extract_sprite(self, sheet: pygame.Surface, width: int, height: int, row: int, col: int) -> pygame.Surface:
    """Extrait une frame en s'assurant que le rectangle reste dans les limites du sprite sheet."""
    sheet_width = sheet.get_width()
    sheet_height = sheet.get_height()
    
    if sheet_width <= 0 or sheet_height <= 0:
        return pygame.Surface((width, height), pygame.SRCALPHA)
    
    x = max(0, min(col * width, max(sheet_width - width, 0)))
    y = max(0, min(row * height, max(sheet_height - height, 0)))
    
    rect_width = min(width, sheet_width - x)
    rect_height = min(height, sheet_height - y)
    if rect_width <= 0 or rect_height <= 0:
        return pygame.Surface((width, height), pygame.SRCALPHA)
    
    rect = pygame.Rect(x, y, rect_width, rect_height)
    try:
        sprite = sheet.subsurface(rect).copy()
    except (ValueError, pygame.error):
        return pygame.Surface((width, height), pygame.SRCALPHA)
    
    if sprite.get_width() != width or sprite.get_height() != height:
        resized = pygame.Surface((width, height), pygame.SRCALPHA)
        resized.blit(sprite, (0, 0))
        sprite = resized
    
    return sprite.convert_alpha()

def _get_sprite_at(self, row: int, col: int) -> pygame.Surface:
    """Extrait un sprite à la position (row, col) du sprite sheet."""
    sprite = self._extract_sprite(self.sprite_sheet, self.sprite_width, self.sprite_height, row, col)
    return self._scale_sprite(sprite)

def _scale_sprite(self, sprite: pygame.Surface) -> pygame.Surface:
    """Redimensionne un sprite selon le facteur d'échelle sprite_scale.
    
    Les sprites redimensionnés sont mis en cache pour éviter de recalculer
    le redimensionnement à chaque frame.
    
    Args:
        sprite: Sprite à redimensionner
        
    Returns:
        Sprite redimensionné selon sprite_scale
    """
    # Calculer les dimensions d'affichage
    display_width = int(self.sprite_width * self.sprite_scale)
    display_height = int(self.sprite_height * self.sprite_scale)
    
    # Si le facteur d'échelle est 1.0, retourner le sprite tel quel
    if self.sprite_scale == 1.0:
        return sprite
    
    # Vérifier le cache
    cache_key = (sprite.get_width(), sprite.get_height(), display_width, display_height)
    if cache_key in self._scaled_sprite_cache:
        return self._scaled_sprite_cache[cache_key]
    
    # Redimensionner avec smoothscale pour une meilleure qualité
    scaled_sprite = pygame.transform.smoothscale(sprite, (display_width, display_height))
    scaled_sprite = scaled_sprite.convert_alpha()
    
    # Mettre en cache
    self._scaled_sprite_cache[cache_key] = scaled_sprite
    
    return scaled_sprite
```

### Système d'interaction avec les PNJ

Le système d'interaction permet au joueur de détecter et d'interagir avec les PNJ à proximité :

1. **Détection de proximité** : À chaque frame, le système calcule la distance horizontale et verticale entre le joueur et chaque PNJ dans le monde
2. **Distance d'interaction** : Un PNJ est considéré comme "interactif" si **deux conditions sont remplies** :
   - La distance horizontale (X) est inférieure ou égale à 200 pixels (`abs(player.x - npc.x) <= INTERACTION_DISTANCE`)
   - La différence de hauteur (Y) est inférieure ou égale à 100 pixels (`abs(player.y - npc.y) <= INTERACTION_Y_THRESHOLD`)
   Cette vérification garantit que le dialogue ne peut être déclenché que si le joueur et le PNJ sont sur le même niveau ou des niveaux très proches (par exemple, sur la même plateforme ou des plateformes adjacentes).
3. **Sélection du PNJ le plus proche** : Si plusieurs PNJ sont à portée (respectant les deux conditions), seul le PNJ le plus proche horizontalement est sélectionné pour l'interaction
4. **Indication visuelle** : Lorsqu'un PNJ est à portée, une indication visuelle est affichée au-dessus du PNJ pour signaler qu'une interaction est possible
5. **Déclenchement du dialogue** : La touche 'T' permet de lancer le dialogue avec le PNJ sélectionné (si aucun dialogue n'est déjà en cours)

#### Indication visuelle d'interaction

L'indication visuelle est affichée au-dessus du nom du PNJ (donc au-dessus de la tête du PNJ) et son contenu dépend du type de dialogue du bloc correspondant à la position actuelle du joueur :

- **Type "normal"** (par défaut) :
  - **Texte** : "Appuyez sur T pour parler" (ou variante courte : "T pour parler")
  - **Style** : Texte de couleur distincte (jaune/cyan) avec contour noir épais (2 pixels) pour une excellente lisibilité et pour se différencier visuellement des noms des PNJ (qui sont en blanc)
  - **Couleur** : Couleur jaune (255, 255, 0) ou cyan (0, 255, 255) pour attirer l'attention et se distinguer clairement des noms des PNJ qui sont en blanc (255, 255, 255)
  - **Police** : Police système (Arial/sans-serif) en gras, taille 28-32 pixels (doublée par rapport à la version précédente pour améliorer la visibilité)
  
- **Type "quête"** :
  - **Texte** : "!" (point d'exclamation), similaire aux MMO RPG, pour indiquer qu'une quête est disponible
  - **Taille** : Le "!" est **3 fois plus gros** que le texte "T pour parler" pour attirer davantage l'attention (par exemple, si "T pour parler" utilise une police de 28 pixels, le "!" utilise une police de 84 pixels)
  - **Style** : Texte de couleur distincte (jaune/cyan) avec contour noir épais (proportionnel à la taille, environ 6 pixels pour le "!" agrandi) pour une excellente lisibilité et pour se différencier visuellement des noms des PNJ (qui sont en blanc)
  - **Couleur** : Couleur jaune (255, 255, 0) ou cyan (0, 255, 255) pour attirer l'attention et se distinguer clairement des noms des PNJ qui sont en blanc (255, 255, 255)
  - **Police** : Police système (Arial/sans-serif) en gras, taille calculée automatiquement (3x la taille de base utilisée pour "T pour parler")

- **Type "discution"** :
  - **Texte** : "T pour ecouter et donner son avis"
  - **Style** : Texte de couleur distincte (jaune/cyan) avec contour noir épais (2 pixels) pour une excellente lisibilité et pour se différencier visuellement des noms des PNJ (qui sont en blanc)
  - **Couleur** : Couleur jaune (255, 255, 0) ou cyan (0, 255, 255) pour attirer l'attention et se distinguer clairement des noms des PNJ qui sont en blanc (255, 255, 255)
  - **Police** : Police système (Arial/sans-serif) en gras, taille 28-32 pixels (doublée par rapport à la version précédente pour améliorer la visibilité)
  - **Signification** : Ce type indique que le dialogue est une discussion où le joueur peut écouter et donner son avis

- **Type "ecoute"** :
  - **Texte** : "T pour écouter"
  - **Style** : Texte de couleur distincte (jaune/cyan) avec contour noir épais (2 pixels) pour une excellente lisibilité et pour se différencier visuellement des noms des PNJ (qui sont en blanc)
  - **Couleur** : Couleur jaune (255, 255, 0) ou cyan (0, 255, 255) pour attirer l'attention et se distinguer clairement des noms des PNJ qui sont en blanc (255, 255, 255)
  - **Police** : Police système (Arial/sans-serif) en gras, taille 28-32 pixels (doublée par rapport à la version précédente pour améliorer la visibilité)
  - **Signification** : Ce type indique que le dialogue est une écoute où le joueur peut simplement écouter sans donner son avis

- **Type "regarder"** :
  - **Texte** : "T pour regarder ce que c'est"
  - **Style** : Texte de couleur distincte (jaune/cyan) avec contour noir épais (2 pixels) pour une excellente lisibilité et pour se différencier visuellement des noms des PNJ (qui sont en blanc)
  - **Couleur** : Couleur jaune (255, 255, 0) ou cyan (0, 255, 255) pour attirer l'attention et se distinguer clairement des noms des PNJ qui sont en blanc (255, 255, 255)
  - **Police** : Police système (Arial/sans-serif) en gras, taille 28-32 pixels (doublée par rapport à la version précédente pour améliorer la visibilité)
  - **Signification** : Ce type indique que le dialogue permet au joueur d'examiner quelque chose

- **Type "enseigner"** :
  - **Texte** : "T pour former"
  - **Style** : Texte de couleur distincte (jaune/cyan) avec contour noir épais (2 pixels) pour une excellente lisibilité et pour se différencier visuellement des noms des PNJ (qui sont en blanc)
  - **Couleur** : Couleur jaune (255, 255, 0) ou cyan (0, 255, 255) pour attirer l'attention et se distinguer clairement des noms des PNJ qui sont en blanc (255, 255, 255)
  - **Police** : Police système (Arial/sans-serif) en gras, taille 28-32 pixels (doublée par rapport à la version précédente pour améliorer la visibilité)
  - **Signification** : Ce type indique que le dialogue est une formation où le joueur peut apprendre quelque chose

- **Type "reflexion"** :
  - **Texte** : "T pour reflechir"
  - **Style** : Texte de couleur distincte (jaune/cyan) avec contour noir épais (2 pixels) pour une excellente lisibilité et pour se différencier visuellement des noms des PNJ (qui sont en blanc)
  - **Couleur** : Couleur jaune (255, 255, 0) ou cyan (0, 255, 255) pour attirer l'attention et se distinguer clairement des noms des PNJ qui sont en blanc (255, 255, 255)
  - **Police** : Police système (Arial/sans-serif) en gras, taille 28-32 pixels (doublée par rapport à la version précédente pour améliorer la visibilité)
  - **Signification** : Ce type indique que le dialogue permet au joueur de réfléchir sur quelque chose

- **Position** : Centré horizontalement au-dessus du nom du PNJ, avec un offset vertical configurable (~8-12 pixels au-dessus du nom)
- **Animation** : Optionnellement, une légère animation de pulsation ou de fade pour attirer l'attention (opacité variant entre 0.7 et 1.0 sur un cycle de 1-2 secondes)
- **Détermination du type** : Le type de dialogue est déterminé en appelant `npc.get_dialogue_type_for_position(player_position)` avec la position actuelle du joueur (voir spécification 12 pour plus de détails sur les types de dialogue)
- **Visibilité** : L'indication n'est affichée que si **toutes** les conditions suivantes sont remplies :
  - Le PNJ est à moins de 200 pixels horizontalement du joueur (`abs(player.x - npc.x) <= INTERACTION_DISTANCE`)
  - Le joueur et le PNJ sont à peu près à la même hauteur (`abs(player.y - npc.y) <= INTERACTION_Y_THRESHOLD`, où `INTERACTION_Y_THRESHOLD` est une constante configurable, par défaut 100 pixels)
  - Aucun dialogue n'est actuellement en cours (`current_dialogue is None`)
  - **Le PNJ a un bloc de dialogue disponible à la position actuelle du joueur** : Il doit exister un bloc de dialogue dont la plage de position (`position_min` <= `player_position` <= `position_max`) correspond à la position actuelle du joueur. Si aucun bloc de dialogue ne correspond à la position actuelle, l'indication n'est pas affichée, même si le PNJ a d'autres blocs de dialogue configurés pour d'autres positions. Cette vérification est effectuée en appelant `npc.get_dialogue_block_for_position(player_position)` et en vérifiant que le résultat n'est pas `None`

#### Calcul de la distance

**IMPORTANT** : Pour qu'un PNJ soit considéré comme interactif, **deux conditions doivent être remplies** :

1. **Distance horizontale (X)** : Le PNJ doit être à moins de 200 pixels horizontalement du joueur :
```python
distance_x = abs(player.x - npc.x)
if distance_x > INTERACTION_DISTANCE:  # INTERACTION_DISTANCE = 200 pixels par défaut
    # Le PNJ est trop loin horizontalement
    return None
```

2. **Distance verticale (Y)** : Le joueur et le PNJ doivent être à peu près à la même hauteur. La différence de position Y ne doit pas dépasser un seuil configurable :
```python
distance_y = abs(player.y - npc.y)
if distance_y > INTERACTION_Y_THRESHOLD:  # INTERACTION_Y_THRESHOLD = 100 pixels par défaut
    # Le joueur et le PNJ ne sont pas à la même hauteur
    return None
```

**Vérification de la position Y** : Cette vérification garantit que le dialogue ne peut être déclenché que si le joueur et le PNJ sont sur le même niveau ou des niveaux très proches (par exemple, sur la même plateforme ou des plateformes adjacentes). Cela évite que le joueur puisse interagir avec un PNJ qui est sur une plateforme au-dessus ou en-dessous, même s'il est proche horizontalement.

Un PNJ est considéré comme interactif si et seulement si :
- La distance horizontale est inférieure ou égale à `INTERACTION_DISTANCE` (200 pixels par défaut)
- **ET** la différence de position Y est inférieure ou égale à `INTERACTION_Y_THRESHOLD` (100 pixels par défaut)
- **ET** le PNJ a un bloc de dialogue disponible à la position actuelle du joueur

Cette approche permet d'interagir avec les PNJ uniquement lorsqu'ils sont sur le même niveau ou des niveaux très proches, rendant l'interaction plus réaliste et évitant les interactions avec des PNJ sur des plateformes éloignées verticalement.

#### Gestion du dialogue

Lorsque la touche 'T' est pressée :
1. Vérifier qu'aucun dialogue n'est en cours (`current_dialogue is None`)
2. Trouver le PNJ le plus proche qui respecte les conditions d'interaction :
   - Distance horizontale <= `INTERACTION_DISTANCE` (200 pixels par défaut)
   - Distance verticale <= `INTERACTION_Y_THRESHOLD` (100 pixels par défaut)
   - Le PNJ a un bloc de dialogue disponible à la position actuelle du joueur
3. Si un PNJ est trouvé, appeler `start_dialogue(npc, progress_tracker)` (voir spécification 12)
4. Si un dialogue est créé avec succès, l'afficher et gérer son cycle de vie

**Note** : Le code de test qui cherchait spécifiquement le PNJ nommé "Robot" doit être supprimé et remplacé par ce système de détection de proximité.

### Système de grimpe

Le système de grimpe permet au joueur de grimper sur des blocs grimpables (échelles) définis dans les fichiers de niveau avec `is_climbable = true` et `is_background = true`.

**Intégration avec le système de niveaux** : Si une animation de grimpe est implémentée avec un sprite sheet `climb.png`, celui-ci doit suivre le même système de niveaux que `walk.png` et `jump.png` (voir spécification 7). Le sprite sheet de grimpe doit être chargé via `level_manager.get_asset_path("climb.png")` et être présent dans chaque répertoire de niveau (`sprite/personnage/{niveau}/climb.png`). Lors d'un changement de niveau du joueur, le sprite sheet de grimpe doit être rechargé de la même manière que les autres sprite sheets.

#### Détection des blocs grimpables

Le système de collisions (spécification 4) détecte si le joueur est en collision avec un bloc grimpable et met à jour la propriété `is_on_climbable` du joueur :
- **Détection** : Le système de collisions vérifie si le rectangle de collision du joueur intersecte avec un rectangle de bloc grimpable (couche avec `is_background = true` et `is_climbable = true`)
- **Mise à jour** : La propriété `player.is_on_climbable` est mise à jour à chaque frame par le système de collisions
- **Position** : Le joueur est considéré "sur" un bloc grimpable si son rectangle de collision intersecte avec le rectangle du bloc grimpable, même partiellement

#### Comportement de grimpe

Quand le joueur est sur un bloc grimpable (`is_on_climbable = True`) :
1. **Touche haut pressée** : Au lieu de déclencher un saut, la touche haut permet de grimper verticalement vers le haut
2. **Vitesse de grimpe** : Le joueur se déplace verticalement vers le haut à la vitesse `climb_speed` (par défaut: 200.0 pixels par seconde)
3. **État de grimpe** : La propriété `is_climbing` est mise à `True` pendant la grimpe
4. **Gravité désactivée** : Pendant la grimpe, la gravité ne s'applique pas (le joueur peut rester en l'air en grimpant)
5. **Réinitialisation de la vitesse verticale** : 
   - **Au début de la grimpe** : La vitesse verticale (`velocity_y`) est réinitialisée à 0.0 pour éviter que la vitesse accumulée avant la grimpe (chute, saut) ne s'applique pendant ou après la grimpe
   - **À la fin de la grimpe** : La vitesse verticale (`velocity_y`) est réinitialisée à 0.0 pour éviter une chute accélérée due à la vitesse accumulée pendant la transition
   - Cette réinitialisation garantit une transition fluide entre la grimpe et la chute normale
6. **Fin de grimpe** : La grimpe se termine lorsque :
   - Le joueur n'est plus sur un bloc grimpable (sorti du bloc)
   - La touche haut n'est plus pressée
   - Le joueur atteint le sommet du bloc grimpable

#### Animation de grimpe

Si un sprite sheet `climb.png` est disponible, l'animation de grimpe est automatiquement utilisée lorsque `is_climbing = True`. L'animation suit le même système que l'animation de saut :

- **Mapping des lignes** : Utilise `CLIMB_DIRECTION_TO_ROW` (identique à `JUMP_DIRECTION_TO_ROW`) pour déterminer la ligne selon la direction
- **Animation en boucle** : L'animation boucle de la frame 0 à la frame 7 (8 frames au total)
- **Priorité d'affichage** : L'animation de grimpe a la priorité sur l'animation de saut et de marche dans `_get_current_sprite()`
- **Gestion gracieuse** : Si le sprite sheet `climb.png` n'est pas disponible, le personnage utilise l'animation de marche/idle pendant la grimpe

#### Implémentation de la grimpe

```python
def _handle_climb_input(self, keys: pygame.key.ScancodeWrapper, dt: float) -> float:
    """Gère l'input de grimpe et retourne le déplacement vertical.
    
    Args:
        keys: Objet ScancodeWrapper retourné par pygame.key.get_pressed()
        dt: Delta time en secondes
        
    Returns:
        Déplacement vertical en pixels (négatif = vers le haut, positif = vers le bas)
        Retourne 0.0 si pas de grimpe
    """
    # Suivre l'état précédent de grimpe pour détecter les transitions
    was_climbing = self.is_climbing
    
    if self.is_on_climbable and (keys[pygame.K_UP] or keys[pygame.K_w]):
        # Le joueur est sur un bloc grimpable et appuie sur haut
        self.is_climbing = True
        # Réinitialiser la vitesse verticale quand on commence à grimper
        # pour éviter que la vitesse accumulée avant la grimpe ne s'applique après
        if not was_climbing:
            self.velocity_y = 0.0
        # Retourner un déplacement vertical négatif (vers le haut)
        return -self.climb_speed * dt
    else:
        # Pas de grimpe
        # Réinitialiser la vitesse verticale quand on arrête de grimper
        # pour éviter une chute accélérée due à la vitesse accumulée
        if was_climbing:
            self.velocity_y = 0.0
        self.is_climbing = False
        return 0.0
```

#### Intégration avec le système de saut

Le système de grimpe a la priorité sur le système de saut :
- Si `is_on_climbable = True` et que la touche haut est pressée → Grimpe (pas de saut)
- Si `is_on_climbable = False` et que la touche haut est pressée → Saut normal (si au sol)

#### Intégration dans la boucle principale

Dans `main.py`, la grimpe doit être gérée avant le saut :

```python
# Dans la boucle principale
keys = pygame.key.get_pressed()

# Gérer la grimpe (prioritaire sur le saut)
climb_dy = player._handle_climb_input(keys, dt)

if climb_dy != 0.0:
    # Le joueur est en train de grimper
    # Appliquer le déplacement vertical de grimpe
    dy = climb_dy
    # Désactiver la gravité pendant la grimpe
    # (ne pas appeler player.apply_gravity())
else:
    # Pas de grimpe, comportement normal
    # Gérer le saut
    player._handle_jump_input(keys)
    
    # Appliquer la gravité (si le personnage n'est pas au sol)
    if not player.is_on_ground:
        player.apply_gravity(dt)
    
    # Calculer le déplacement vertical normal
    dy = player.velocity_y * dt
```

#### Détection de sortie du bloc grimpable

Le système de collisions doit détecter quand le joueur sort d'un bloc grimpable :
- **Vérification continue** : À chaque frame, le système de collisions vérifie si le joueur est encore en collision avec un bloc grimpable
- **Mise à jour de `is_on_climbable`** : Si le joueur n'est plus en collision avec aucun bloc grimpable, `is_on_climbable` est mis à `False`
- **Fin de grimpe** : Quand `is_on_climbable` devient `False`, la grimpe s'arrête automatiquement (même si la touche haut est encore pressée)

### Système d'affichage du level up

Lorsqu'un événement de type `level_up` est déclenché (voir spécification 11), l'affichage "level up (press u)" apparaît automatiquement en jaune clignotant au-dessus du nom du personnage principal.

#### Caractéristiques de l'affichage

- **Texte** : "level up (press u)" (configurable via `level_up_text`)
- **Couleur** : Jaune `(255, 255, 0)` pour attirer l'attention
- **Position** : 
  - Si l'inventaire contient des objets : Au-dessus de l'inventaire avec un espacement de 8 pixels
  - Si l'inventaire est vide ou n'existe pas : Au-dessus du nom du personnage principal avec une marge de 20 pixels entre le bas de l'indicateur de level up et le haut de l'emplacement du nom
- **Animation** : Clignotement continu (le texte apparaît et disparaît toutes les 0.5 secondes par défaut)
- **Police** : Même police que le nom du personnage, avec une taille similaire (36px par défaut)
- **Contour** : Contour noir épais (2 pixels) pour améliorer la lisibilité, similaire au nom du personnage
- **Visibilité** : L'affichage reste visible jusqu'à ce que le joueur appuie sur la touche `U` pour le confirmer

#### Gestion de l'état

- **Activation** : L'affichage est activé via `player.show_level_up()`, appelé automatiquement par le système d'événements lorsque l'événement `level_up` est déclenché
- **Désactivation** : L'affichage est désactivé via `player.hide_level_up()`, appelé lorsque le joueur appuie sur la touche `U`. Avant de masquer l'affichage, le niveau du personnage est augmenté de **+1 uniquement** (sans dépasser `MAX_PLAYER_LEVEL`) en utilisant `player.set_level(new_level)`, ce qui déclenche automatiquement le rechargement des assets et la mise à jour des statistiques (voir spécification 7). L'augmentation est toujours de +1 niveau, il n'est pas possible d'augmenter de plusieurs niveaux en une seule fois.
- **Animation** : L'animation de clignotement est mise à jour dans `_update_level_up_animation(dt)` à chaque frame si `level_up_active` est `True`

#### Implémentation de l'animation de clignotement

```python
def _update_level_up_animation(self, dt: float) -> None:
    """Met à jour l'animation de clignotement du texte de level up."""
    if not self.level_up_active:
        return
    
    self.level_up_blink_timer += dt
    
    # Basculer la visibilité toutes les level_up_blink_speed secondes
    if self.level_up_blink_timer >= self.level_up_blink_speed:
        self.level_up_blink_timer = 0.0
        self.level_up_visible = not self.level_up_visible
```

#### Implémentation du rendu

```python
def _draw_level_up(self, surface: pygame.Surface, camera_x: float) -> None:
    """Dessine le texte "level up (press u)" en jaune clignotant au-dessus de l'inventaire."""
    if not self.level_up_active or not self.level_up_visible:
        return
    
    # Calculer la position à l'écran
    screen_x = self.x - camera_x
    screen_y = self.y
    
    # Positionner le texte au-dessus de l'inventaire
    # Si l'inventaire existe et a des objets, utiliser sa position
    # Sinon, utiliser la position du nom comme fallback avec une marge de 20 pixels
    inventory_y = None
    use_name_position = False
    if self.inventory is not None:
        # Récupérer les commandes de dessin de l'inventaire pour obtenir sa position Y
        inventory_commands = self.get_inventory_draw_commands(
            camera_x, surface.get_width(), surface.get_height()
        )
        if inventory_commands:
            # La position Y de l'inventaire est celle du premier objet (le plus haut)
            _, (_, first_item_y) = inventory_commands[0]
            inventory_y = float(first_item_y)
    
    # Si l'inventaire n'existe pas ou est vide, utiliser la position du nom comme fallback
    name_y = None
    if inventory_y is None:
        use_name_position = True
        # Calculer la position Y du haut du nom (identique à get_name_draw_command)
        bottom_y = screen_y + self.sprite_height / 2
        top_of_sprite = bottom_y - self.display_height
        base_name_y = top_of_sprite - (self.name_rect.height if self.name_rect else 0)
        name_y = base_name_y + self.name_offset_y
    
    # Calculer la position Y selon qu'on utilise l'inventaire ou le nom
    if use_name_position and name_y is not None:
        # Si on utilise la position du nom, le bas de l'indicateur doit être à 20 pixels du haut du nom
        # Le haut de l'indicateur est donc à : name_y - 20 - hauteur_du_texte
        level_up_spacing_from_name = 20.0
        text_y = round(name_y - level_up_spacing_from_name - text_surface.get_height())
    else:
        # Si on utilise l'inventaire, espacement de 8 pixels
        level_up_spacing = 8.0
        level_up_y = inventory_y - level_up_spacing
        text_y = round(level_up_y - text_surface.get_height())
    
    # Rendre le texte avec la même police que le nom
    text_color = (255, 255, 0)  # Jaune
    outline_color = (0, 0, 0)  # Noir
    outline_thickness = 2
    
    # Rendre le texte avec contour (même méthode que pour le nom)
    text_surface = self.font.render(self.level_up_text, True, text_color)
    
    # Calculer la position centrée horizontalement
    text_x = round(screen_x - text_surface.get_width() / 2)
    text_y = round(level_up_y - text_surface.get_height())
    
    # Dessiner le contour
    outline_surface = self.font.render(self.level_up_text, True, outline_color)
    for dx in range(-outline_thickness, outline_thickness + 1):
        for dy in range(-outline_thickness, outline_thickness + 1):
            if dx != 0 or dy != 0:
                surface.blit(outline_surface, (text_x + dx, text_y + dy))
    
    # Dessiner le texte principal
    surface.blit(text_surface, (text_x, text_y))
```

#### Intégration dans la boucle de jeu

**Dans la méthode `update()` de la classe `Player`** :
- Appeler `_update_level_up_animation(dt)` pour mettre à jour l'animation de clignotement du texte de level up (si `level_up_active` est `True`)
- Appeler `_update_level_transition(dt, camera_x)` pour mettre à jour l'animation de transition de niveau (si `level_transition_active` est `True`, voir spécification 11). Le paramètre `camera_x` est nécessaire pour l'émission de confettis depuis les coins du texte de transition (voir spécification 7 et 14).
- **Blocage des inputs pendant la transition** : Si `level_transition_active` est `True`, ignorer tous les inputs de mouvement et d'interaction. Le personnage ne doit pas bouger pendant la transition (position figée). Aucune modification n'est nécessaire dans le système de collisions car le personnage ne bouge pas (voir spécification 11)

**Dans la méthode `draw()` ou dans la boucle principale** :
- L'ordre d'affichage doit être : nom, puis inventaire, puis level up
- Appeler `_draw_level_up(surface, camera_x)` après `draw_inventory()` pour afficher le texte de level up au-dessus de l'inventaire (si `level_up_active` est `True`)
- **Ordre de rendu (PRIORITÉ ABSOLUE)** : Appeler `_draw_level_transition(surface)` **EN DERNIER**, après tous les autres éléments de l'interface (y compris les bulles de dialogue et l'interface des statistiques), pour afficher l'animation de transition (si `level_transition_active` est `True`, voir spécification 11). Le texte de transition de niveau doit être affiché au-dessus de tous les autres éléments.

**Dans la gestion des événements** :
- Détecter l'appui sur la touche `U` (événement `KEYDOWN` avec `event.key == pygame.K_u`)
- Si `player.level_up_active` est `True` :
  1. Calculer le nouveau niveau : `new_level = min(player.player_level + 1, MAX_PLAYER_LEVEL)` (l'augmentation est toujours de +1 uniquement)
  2. Si le nouveau niveau est différent du niveau actuel (c'est-à-dire que le niveau n'est pas déjà au maximum) :
     - Appeler `player.start_level_transition(player.player_level, new_level)` pour démarrer l'animation de transition (voir spécification 11)
     - Appeler `player.set_level(new_level)` pour augmenter le niveau de +1 (cela déclenche automatiquement le rechargement des assets et la mise à jour des statistiques, voir spécification 7)
  3. Appeler `player.hide_level_up()` pour masquer l'affichage
  4. **Réinitialiser les événements de level up** : Réinitialiser tous les événements de type `level_up` via `event_system.reset_event_by_identifier()` pour permettre de les redéclencher lors de dialogues ultérieurs (voir spécification 11)

#### Intégration avec le système d'événements

Le système d'événements (spécification 11) appelle automatiquement `player.show_level_up()` lorsque l'événement de type `level_up` est déclenché. L'événement peut être déclenché depuis un dialogue de PNJ en utilisant `trigger_events` dans la configuration d'un échange (voir spécification 12).

### Debug : affichage de la position

Pour faciliter le débogage, la position du joueur (coordonnées `x`, `y` en pixels monde) est affichée en permanence dans le coin supérieur gauche de l'écran. Ce texte utilise une police système (`pygame.font.Font(None, 18)`) et est mis à jour uniquement lorsque la position change, afin de limiter les allocations inutiles. Cette superposition n'interfère pas avec le reste de l'interface et reste visible quel que soit le niveau du personnage.

## Implémentation

### Structure de fichiers

```
src/moteur_jeu_presentation/
├── entities/
│   ├── __init__.py
│   └── player.py          # Classe Player
```

### Exemple d'utilisation

```python
from entities.player import Player
from entities.npc import NPC, start_dialogue
from entities import MAX_PLAYER_LEVEL
from game.progress import LevelProgressTracker
import argparse
import pygame

def parse_arguments() -> argparse.Namespace:
    """Parse les arguments de la ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Présentation - Jeu de plateforme",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--player-x",
        "--start-x",
        type=float,
        default=None,
        dest="player_x",
        help="Position X initiale du personnage principal en pixels (défaut: centre de l'écran)",
    )
    
    return parser.parse_args()

# Parser les arguments de la ligne de commande
args = parse_arguments()

# Déterminer la position X initiale (depuis l'argument ou valeur par défaut)
# IMPORTANT : L'argument --player-x est dans le repère de conception (1920x1080)
# Il doit être converti vers le repère de rendu (1280x720)
from moteur_jeu_presentation.rendering.config import compute_design_scale, get_render_size

render_width, render_height = get_render_size()  # Largeur de rendu interne (1280x720)

if args.player_x is not None:
    # Convertir la position X du repère de design (1920x1080) vers le repère de rendu (1280x720)
    scale_x, _ = compute_design_scale((render_width, render_height))
    initial_x = args.player_x * scale_x
else:
    # Position par défaut : centre de l'écran dans le repère de rendu
    initial_x = render_width / 2

# Initialisation
player = Player(
    x=initial_x,  # Position X dans le repère de rendu (1280x720)
    y=360.0,  # Centre de l'écran (720 / 2)
    sprite_sheet_path="sprite/walk.png",
    sprite_width=64,
    sprite_height=64,
    animation_speed=10.0,
    sprite_scale=2.0  # Double la taille d'affichage (128x128 pixels)
)

# Configuration
player.speed = 250.0  # pixels par seconde

# Créer le système de progression
progress_tracker = LevelProgressTracker(player)
progress_tracker.update(0.0)  # Initialiser avec la position du joueur

# Liste des PNJ
npcs: List[NPC] = []  # Chargée depuis la configuration

# État du dialogue en cours
current_dialogue: Optional[DialogueState] = None

# Distance d'interaction avec les PNJ
# Deux conditions doivent être remplies : distance horizontale ET distance verticale
INTERACTION_DISTANCE = 200.0  # pixels (distance horizontale maximale)
INTERACTION_Y_THRESHOLD = 100.0  # pixels (différence de hauteur maximale entre le joueur et le PNJ)

def find_nearest_interactable_npc(
    player_x: float, 
    player_y: float, 
    npcs: List[NPC], 
    player_position: float
) -> Optional[NPC]:
    """Trouve le PNJ le plus proche à portée d'interaction.
    
    Pour qu'un PNJ soit considéré comme interactif, deux conditions doivent être remplies :
    1. La distance horizontale (X) doit être <= INTERACTION_DISTANCE
    2. La différence de hauteur (Y) doit être <= INTERACTION_Y_THRESHOLD
    
    Args:
        player_x: Position X du joueur dans l'espace du monde
        player_y: Position Y du joueur dans l'espace du monde
        npcs: Liste des PNJ à vérifier
        player_position: Position horizontale du joueur dans le monde (utilisée pour vérifier les blocs de dialogue disponibles)
    
    Returns:
        Le PNJ le plus proche qui respecte toutes les conditions, ou None si aucun PNJ n'est à portée
    """
    nearest_npc = None
    min_distance = INTERACTION_DISTANCE
    
    for npc in npcs:
        # Vérifier que le PNJ a un bloc de dialogue disponible à la position actuelle du joueur
        # (pas seulement qu'il a des blocs configurés, mais qu'il y en a un qui correspond à cette position)
        dialogue_block = npc.get_dialogue_block_for_position(player_position)
        if dialogue_block is None:
            continue
        
        # Calculer la distance horizontale
        distance_x = abs(player_x - npc.x)
        
        # Vérifier que le PNJ est à portée horizontalement
        if distance_x > INTERACTION_DISTANCE:
            continue
        
        # Calculer la différence de hauteur
        distance_y = abs(player_y - npc.y)
        
        # Vérifier que le joueur et le PNJ sont à peu près à la même hauteur
        if distance_y > INTERACTION_Y_THRESHOLD:
            continue
        
        # Si toutes les conditions sont remplies, vérifier si c'est le PNJ le plus proche
        if distance_x < min_distance:
            min_distance = distance_x
            nearest_npc = npc
    
    return nearest_npc

def draw_interaction_indicator(
    surface: pygame.Surface,
    npc: NPC,
    camera_x: float,
    font: pygame.font.Font,
    player_position: float,
    base_font_size: int = 28,
    alpha: float = 1.0
) -> None:
    """Dessine l'indication d'interaction au-dessus du PNJ.
    
    Le type d'indicateur dépend du type de dialogue du bloc correspondant
    à la position actuelle du joueur (voir spécification 12).
    
    Args:
        base_font_size: Taille de base de la police en pixels (utilisée pour calculer la taille du "!")
    """
    # Calculer la position à l'écran
    screen_x = npc.x - camera_x
    screen_y = npc.y
    
    # Déterminer le type de dialogue pour cette position
    dialogue_type = npc.get_dialogue_type_for_position(player_position)
    
    # Choisir le texte selon le type de dialogue
    if dialogue_type == "quête":
        text = "!"  # Point d'exclamation pour les quêtes
        # Le "!" est 3 fois plus gros que le texte normal
        quest_font_size = int(base_font_size * 3)  # 3 fois plus gros
        # Créer une nouvelle police pour le "!" avec la taille agrandie
        try:
            quest_font = pygame.font.SysFont("arial", quest_font_size, bold=True)
        except pygame.error:
            quest_font = pygame.font.SysFont("sans-serif", quest_font_size, bold=True)
        display_font = quest_font
    elif dialogue_type == "discution":
        text = "T pour ecouter et donner son avis"  # Texte pour les discussions
        display_font = font
    elif dialogue_type == "ecoute":
        text = "T pour écouter"  # Texte pour les écoutes
        display_font = font
    elif dialogue_type == "regarder":
        text = "T pour regarder ce que c'est"  # Texte pour examiner quelque chose
        display_font = font
    elif dialogue_type == "enseigner":
        text = "T pour former"  # Texte pour les formations
        display_font = font
    elif dialogue_type == "reflexion":
        text = "T pour reflechir"  # Texte pour les réflexions
        display_font = font
    else:
        text = "T pour parler"  # Texte par défaut pour les dialogues normaux
        display_font = font
    
    # Couleur jaune pour se distinguer des noms des PNJ (qui sont en blanc)
    text_color = (255, 255, 0)  # Jaune
    text_surface = display_font.render(text, True, text_color)
    
    # Appliquer l'opacité si nécessaire
    if alpha < 1.0:
        text_surface.set_alpha(int(255 * alpha))
    
    # Centrer horizontalement
    text_x = round(screen_x - text_surface.get_width() / 2)
    # Positionner au-dessus du nom (le nom est à environ -sprite_height/2 - name_height - offset)
    # On ajoute un offset supplémentaire de ~30-40 pixels au-dessus du nom
    name_y = screen_y - npc.sprite_height / 2 - (npc.name_rect.height if npc.name_rect else 0) - 4.0
    text_y = round(name_y - text_surface.get_height() - 12)
    
    # Dessiner le contour (noir, épaisseur proportionnelle à la taille)
    # Pour le "!", utiliser une épaisseur de contour proportionnelle à la taille
    # Pour "discution", "ecoute" et "normal", utiliser une épaisseur standard de 2 pixels
    outline_thickness = 2 if dialogue_type != "quête" else 6  # Contour plus épais pour le "!" plus gros
    outline_surface = display_font.render(text, True, (0, 0, 0))
    for dx in range(-outline_thickness, outline_thickness + 1):
        for dy in range(-outline_thickness, outline_thickness + 1):
            if dx != 0 or dy != 0:
                surface.blit(outline_surface, (text_x + dx, text_y + dy))
    
    # Dessiner le texte principal
    surface.blit(text_surface, (text_x, text_y))

# Dans la boucle de jeu
def handle_events(events: List[pygame.event.Event], camera_x: float) -> None:
    global current_dialogue
    
    for event in events:
        if event.type == pygame.QUIT:
            # Gérer la fermeture
            pass
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_t:
                # Lancer le dialogue avec le PNJ le plus proche
                if current_dialogue is None:
                    # Obtenir la position actuelle du joueur pour vérifier les blocs de dialogue disponibles
                    player_position = progress_tracker.get_current_x()
                    nearest_npc = find_nearest_interactable_npc(player.x, player.y, npcs, player_position)
                    if nearest_npc:
                        current_dialogue = start_dialogue(nearest_npc, progress_tracker)
            elif event.key == pygame.K_u:
                # Confirmer le level up en augmentant le niveau de +1 et masquer l'affichage
                if player.level_up_active:
                    # Calculer le nouveau niveau (augmentation de +1 uniquement, sans dépasser MAX_PLAYER_LEVEL)
                    new_level = min(player.player_level + 1, MAX_PLAYER_LEVEL)
                    # Augmenter le niveau si possible (utilise les mécanismes existants)
                    # Note : L'augmentation est toujours de +1 niveau, il n'est pas possible d'augmenter de plusieurs niveaux
                    if new_level != player.player_level:
                        # Démarrer l'animation de transition de niveau (voir spécification 11)
                        player.start_level_transition(player.player_level, new_level)
                        player.set_level(new_level)
                        print(f"Niveau du joueur augmenté à {new_level}")
                    # Masquer l'affichage de level up
                    player.hide_level_up()
                    # Réinitialiser tous les événements de type level_up pour permettre de les redéclencher
                    if event_system is not None:
                        for event_config in event_system.events:
                            if event_config.event_type == "level_up":
                                event_system.reset_event_by_identifier(event_config.identifier)
        
        # Transmettre les événements au dialogue en cours
        if current_dialogue is not None:
            if current_dialogue.handle_event(event, camera_x):
                if current_dialogue.is_complete():
                    current_dialogue = None

def update(dt: float, camera_x: float) -> None:
    keys = pygame.key.get_pressed()
    player.update(dt, keys)
    
    # Mettre à jour le système de progression
    progress_tracker.update(dt)
    
    # Mettre à jour les PNJ
    for npc in npcs:
        npc.update(dt, camera_x)
    
    # Mettre à jour le dialogue en cours
    if current_dialogue is not None:
        current_dialogue.update(camera_x, dt)
        if current_dialogue.is_complete():
            current_dialogue = None

def draw(screen: pygame.Surface, camera_x: float, dt: float) -> None:
    # Dessiner les couches de parallaxe d'abord
    parallax_system.draw(screen)
    
    # Dessiner le personnage (couche gameplay, depth 2)
    player.draw(screen, camera_x)
    player.draw_name(screen, camera_x)
    # Dessiner l'inventaire au-dessus du nom
    player.draw_inventory(screen, camera_x, screen_width, screen_height)
    # Dessiner l'affichage de level up si actif (au-dessus de l'inventaire)
    player._draw_level_up(screen, camera_x)
    # Dessiner l'animation de transition de niveau si active (voir spécification 11)
    player._draw_level_transition(screen)
    
    # Dessiner les PNJ
    for npc in npcs:
        npc.draw(screen, camera_x)
        npc.draw_name(screen, camera_x)
    
    # Dessiner l'indication d'interaction si un PNJ est à portée
    if current_dialogue is None:
        # Obtenir la position actuelle du joueur pour vérifier les blocs de dialogue disponibles
        player_position = progress_tracker.get_current_x()
        nearest_npc = find_nearest_interactable_npc(player.x, player.y, npcs, player_position)
        if nearest_npc:
            # Vérifier qu'il y a bien un bloc de dialogue disponible à cette position
            # (find_nearest_interactable_npc le vérifie déjà, mais on peut le vérifier à nouveau pour la sécurité)
            dialogue_block = nearest_npc.get_dialogue_block_for_position(player_position)
            if dialogue_block is not None:
                # Animation de pulsation (opacité variant entre 0.7 et 1.0)
                import math
                pulse = 0.7 + 0.3 * (math.sin(pygame.time.get_ticks() / 500.0) * 0.5 + 0.5)
                # Taille doublée (28-32 pixels) pour améliorer la visibilité
                interaction_font = pygame.font.SysFont("arial", 28, bold=True)
                interaction_font_size = 28  # Taille de base de la police
                draw_interaction_indicator(screen, nearest_npc, camera_x, interaction_font, player_position, interaction_font_size, pulse)
    
    # Dessiner le dialogue en cours (au-dessus de tout)
    if current_dialogue is not None:
        current_dialogue.draw(screen, camera_x)
```

### Intégration avec le système de parallaxe

Le personnage doit être rendu dans la couche de gameplay (depth 2) :
- Le personnage se déplace indépendamment de la caméra
- La position de rendu doit tenir compte de la position de la caméra
- Calcul : `screen_x = player.x - camera_x`

### Intégration avec le système de niveaux

Le personnage utilise le système de niveaux (spécification 7) pour charger les sprite sheets appropriés selon son niveau actuel :
- **Chargement des sprite sheets** : Tous les sprite sheets (`walk.png`, `jump.png`, `climb.png` si implémenté) sont chargés via `level_manager.get_asset_path(filename)` pour garantir que le bon sprite sheet est utilisé selon le niveau actuel
- **Changement de niveau** : Lors d'un changement de niveau (via `player.set_level(niveau)`), tous les sprite sheets doivent être rechargés depuis le nouveau répertoire de niveau
- **Rechargement des animations** : Lors du rechargement, les caches d'animation doivent être vidés pour éviter d'utiliser des sprites du niveau précédent
- **Gestion des assets manquants** : Si un sprite sheet est manquant pour un niveau donné (ex: `climb.png`), le système doit gérer gracieusement l'absence (afficher un avertissement et continuer sans animation spécifique)

### Gestion des limites

- Le personnage ne doit pas sortir des limites du monde de jeu
- Vérifier les collisions avec les bords (à implémenter dans une spécification future)

## Contraintes et considérations

### Pièges courants

#### Le texte du prénom n'est pas assez lisible

**Problème** : Le prénom affiché au-dessus du personnage est difficile à lire, surtout sur des fonds complexes ou clairs.

**Cause** : Plusieurs facteurs peuvent affecter la lisibilité :
- Taille de police trop petite (moins de 32-36px)
- Contour trop fin (1 pixel) qui ne se distingue pas assez du fond
- Police pixel art trop stylisée qui peut être difficile à lire
- Absence d'anti-aliasing

**Solution** :
- Utiliser une taille de police d'au moins 36px par défaut
- Créer un contour épais (2 pixels) en dessinant plusieurs couches autour du texte
- Préférer une police système lisible (Arial, sans-serif) en gras plutôt qu'une police pixel art si la lisibilité est prioritaire
- Utiliser l'anti-aliasing lors du rendu du texte (`render(..., True)` pour activer l'anti-aliasing)
- Tester la lisibilité sur différents fonds (clair, sombre, complexe)

**Implémentation** :
```python
# Taille de police recommandée
font_size = 36  # Doublée pour améliorer la lisibilité

# Contour épais (2 pixels)
outline_thickness = 2
for layer in range(outline_thickness):
    offset = layer + 1
    # Dessiner le contour sur plusieurs couches

# Police système lisible avec fallback
try:
    font = pygame.font.SysFont("arial", font_size, bold=True)
except pygame.error:
    font = pygame.font.SysFont("sans-serif", font_size, bold=True)
```

### Performance

- Charger le sprite sheet une seule fois au démarrage
- Utiliser `convert_alpha()` pour optimiser le rendu des sprites avec transparence
- Mettre en cache les sprites extraits si nécessaire (ou les extraire à la volée)
- Limiter les calculs de position à chaque frame

### Dimensions et proportions

- **Taille d'affichage** : Les sprites sont affichés à **200% de leur taille originale** (facteur d'échelle de 2.0 par défaut)
  - Sprites 64x64 pixels dans le sprite sheet → affichage à 128x128 pixels
  - Le facteur d'échelle est configurable via le paramètre `sprite_scale` (défaut: 2.0)
- **Redimensionnement** : Les sprites sont redimensionnés lors de l'extraction/affichage en utilisant `pygame.transform.smoothscale()` pour une meilleure qualité visuelle
- **Adaptation à la résolution interne** : Le `sprite_scale` est appliqué DANS le repère de conception (1920x1080), puis le résultat est converti vers la résolution interne (1280x720) : `display_width = (sprite_width * sprite_scale) * scale_x`, `display_height = (sprite_height * sprite_scale) * scale_y`. Cela garantit que le personnage est correctement dimensionné quelle que soit la résolution réelle de la fenêtre.
- **Mise en cache** : Les sprites redimensionnés sont mis en cache pour éviter de recalculer le redimensionnement à chaque frame
- **Clé de cache** : Les caches de sprites redimensionnés doivent inclure au minimum `(row, col, display_width, display_height)` pour garantir qu'une frame animée ne remplace pas une autre lorsque la taille d'affichage change (sinon l'animation afficherait toujours la même frame)
- Le personnage doit être centré sur sa position (x, y) représente le centre du sprite affiché (après redimensionnement)
- **Calculs de position d'affichage** : Les calculs de position pour le dessin (`get_draw_command`) doivent tenir compte de la taille d'affichage (`display_width` et `display_height`) et non de la taille du sprite sheet
- **Calculs de collision** : Les calculs de collision (`get_collision_rect`) s'alignent sur la taille affichée (`display_width` et `display_height`). Une marge constante de 20 px de chaque côté et 6 px en haut est conservée afin que la hitbox reste cohérente, même lorsque le sprite est redimensionné.
- **Éléments d'interface** : Le prénom, les bulles de dialogue et toute logique de visibilité/culling doivent utiliser `display_width` / `display_height` pour rester synchronisés avec la taille affichée du personnage.
- Gérer correctement la transparence du fond noir du sprite sheet

### Gestion mémoire

- Charger le sprite sheet via `AssetManager` (si disponible) ou directement avec `pygame.image.load()`
- Ne pas créer de nouvelles surfaces à chaque frame pour extraire les sprites
- Réutiliser les surfaces de sprite extraites

### Animation

- Utiliser le delta time pour une animation fluide indépendante du FPS
- Gérer correctement le timer d'animation pour éviter les sauts de frames
- Assurer une transition fluide entre les états idle et en mouvement
- Mettre à jour la position du prénom (name_rect) à chaque frame.
- Optimiser le rendu du texte : ne recalculer la surface que si le texte ou la police change.

## Tests

### Tests unitaires à implémenter

1. **Test d'initialisation** : Vérifier que le personnage est correctement initialisé
2. **Test de mouvement** : Vérifier que le personnage se déplace correctement
3. **Test d'animation** : Vérifier que l'animation change correctement selon la direction
4. **Test d'extraction de sprite** : Vérifier que les sprites sont correctement extraits du sprite sheet
5. **Test de limites** : Vérifier que le personnage ne sort pas des limites du monde
6. **Test du prénom** : Vérifier que la surface du prénom est générée, centrée et suit la position du joueur
7. **Test de détection de proximité PNJ** : Vérifier que le système détecte correctement les PNJ à moins de 200 pixels
8. **Test de sélection du PNJ le plus proche** : Vérifier que lorsqu'il y a plusieurs PNJ à portée, le plus proche est sélectionné
9. **Test d'affichage de l'indication** : Vérifier que l'indication n'est affichée que lorsque les conditions sont remplies (distance <= 200px, aucun dialogue en cours, PNJ avec dialogues configurés)
10. **Test de déclenchement du dialogue** : Vérifier que la touche 'T' lance correctement le dialogue avec le PNJ le plus proche
11. **Test d'affichage du level up** : Vérifier que l'affichage "level up (press u)" apparaît lorsque `show_level_up()` est appelé
12. **Test d'animation de clignotement** : Vérifier que le texte de level up clignote correctement (apparaît et disparaît toutes les 0.5 secondes)
13. **Test de confirmation du level up** : Vérifier que lorsque le joueur appuie sur la touche 'U' :
    - Le niveau du personnage est augmenté de **+1 uniquement** (sans dépasser `MAX_PLAYER_LEVEL`)
    - L'augmentation est toujours de +1 niveau, même si plusieurs événements de level up sont déclenchés (vérifier qu'il n'est pas possible d'augmenter de plusieurs niveaux en une seule fois)
    - L'animation de transition de niveau est déclenchée (vérifier que `level_transition_active` devient `True`, voir spécification 11)
    - Les assets sont rechargés (vérifier que les sprite sheets correspondent au nouveau niveau)
    - Les statistiques sont mises à jour (vérifier que les valeurs de stats correspondent au nouveau niveau)
    - L'affichage disparaît (vérifier que `level_up_active` devient `False`)
    - Si le niveau est déjà au maximum, le niveau ne change pas mais l'affichage disparaît quand même
14. **Test de l'animation de transition de niveau** : Vérifier que l'animation de transition fonctionne correctement (voir spécification 11 pour les détails)
15. **Test d'intégration avec les événements** : Vérifier que l'événement `level_up` déclenche correctement l'affichage via le système d'événements
16. **Test de l'argument --player-x** : Vérifier que :
    - Le personnage est initialisé à la position X spécifiée lorsque `--player-x` est fourni
    - Le personnage est initialisé au centre de l'écran (valeur par défaut) lorsque `--player-x` n'est pas fourni
    - L'alias `--start-x` fonctionne de la même manière que `--player-x`
    - La caméra s'ajuste correctement à la position initiale du personnage
    - Le système de progression s'initialise avec la position X spécifiée

### Exemple de test

```python
import pygame
from unittest.mock import MagicMock

def test_player_movement():
    """Test que le personnage se déplace correctement."""
    pygame.init()
    player = Player(100.0, 100.0, "sprite/walk.png")
    
    # Créer un mock pour pygame.key.get_pressed()
    keys = MagicMock()
    keys.__getitem__ = lambda self, key: key == pygame.K_RIGHT
    
    initial_x = player.x
    player.update(0.1, keys)  # dt = 0.1 secondes
    
    assert player.x > initial_x
    assert player.current_direction == "right"
    assert player.is_moving == True

def test_player_animation():
    """Test que l'animation progresse correctement."""
    pygame.init()
    player = Player(100.0, 100.0, "sprite/walk.png")
    
    # Créer un mock pour pygame.key.get_pressed()
    keys = MagicMock()
    keys.__getitem__ = lambda self, key: key == pygame.K_LEFT
    
    initial_frame = player.current_frame
    player.update(0.1, keys)
    
    # L'animation devrait avoir progressé
    assert player.current_frame != initial_frame or player.animation_timer > 0

def test_player_name_rendering():
    pygame.init()
    # Fournir un stats_config minimal avec display_name (conforme spécification 7)
    stats_config = make_minimal_stats_config(display_name="Test")
    player = Player(100.0, 100.0, "sprite/walk.png", stats_config=stats_config)
    assert player.name == stats_config.display_name
    assert player.name_surface is not None
    w = player.name_surface.get_width()
    assert w > 0
```

**Note** : Pour les tests, il est recommandé d'utiliser `unittest.mock.MagicMock` pour simuler l'objet `ScancodeWrapper` retourné par `pygame.key.get_pressed()`, ou d'utiliser directement `pygame.key.get_pressed()` dans un contexte de test avec pygame initialisé.

## Évolutions futures possibles

- Ajout des animations pour les directions haut et bas
- Système d'états plus complexe (saut, course, attaque)
- Support de plusieurs sprite sheets (animations différentes)
- Système de collision avec l'environnement
- Gestion de la gravité et de la physique
- Animations d'idle différentes selon la direction
- Support de l'échelle/zoom du personnage
- Effets visuels (ombres, particules) - **Note** : Pour les effets de particules, utiliser le moteur de particules (spécification 14)

## Références

- Bonnes pratiques : `bonne_pratique.md`
- Spécification système de couches : `spec/1-systeme-de-couches-2d.md`
- Spécification système de niveaux du personnage : `spec/7-systeme-de-niveaux-personnage.md` (pour le chargement des sprite sheets par niveau et la clé racine **`display_name`** du nom affiché)
- Spécification système de saut : `spec/6-systeme-de-saut.md` (pour les animations de saut)
- Spécification système de personnage non joueur : `spec/12-systeme-de-personnage-non-joueur.md`
- Spécification système de physique et collisions : `spec/4-systeme-de-physique-collisions.md` (pour la détection des blocs grimpables)
- Spécification système de gestion de l'avancement dans le niveau : `spec/11-systeme-gestion-avancement-niveau.md` (pour le système d'événements, le déclenchement du level up et l'animation de transition de niveau)
- **Spécification moteur de particules** : `spec/14-moteur-de-particules.md` (pour les effets de particules)
- Documentation Pygame : [pygame.Surface](https://www.pygame.org/docs/ref/surface.html)
- Sprite sheets : `sprite/personnage/{niveau}/walk.png`, `sprite/personnage/{niveau}/jump.png`, `sprite/personnage/{niveau}/climb.png` (optionnel)

---

**Date de création** : 2024  
**Statut** : ✅ Implémenté

