# 6 - Système de saut avec animations

## Contexte

Cette spécification définit l'implémentation du système de saut pour le personnage principal. Le joueur doit pouvoir sauter avec la touche haut, déclencher une animation appropriée selon la direction, et le saut doit être géré naturellement avec la gravité et les collisions.

## Objectifs

- Permettre au joueur de sauter avec la touche haut (flèche haut / W)
- Implémenter un système d'animation de saut basé sur un sprite sheet
- Gérer les animations de saut pour les directions gauche et droite
- Intégrer le saut avec le système de gravité existant
- Gérer les collisions pendant le saut
- Assurer un saut naturel et fluide
- **Permettre un double saut à partir d’un seuil de niveau configurable** : le niveau minimal est défini dans `config/player_stats.toml` (clé racine `double_jump_unlock_level`, défaut **3** si absent — comportement identique à l’ancien seuil code). Le joueur peut déclencher un deuxième saut en l'air après avoir relâché la touche de saut, relançant un nouveau saut depuis sa position actuelle

## Architecture

### Sprite Sheet

Le sprite sheet `jump.png` contient les animations de saut du personnage :
- **Dimensions** : 320x256 pixels (5 colonnes × 4 lignes × 64x64 pixels par sprite)
- **Structure** : Grille de 4 lignes et 5 colonnes
- **Taille d'un sprite** : 64x64 pixels

### Mapping des lignes

Selon les spécifications utilisateur :
- **Ligne 2** (en partant du haut, index 1) : Animation de saut vers la **gauche**
- **Ligne 4** (en partant du haut, index 3) : Animation de saut vers la **droite**

**Note** : Les lignes 1 et 3 (index 0 et 2) peuvent contenir d'autres animations (marche, idle) et ne sont pas utilisées pour le saut.

### Séquence d'animation de saut

Chaque ligne de saut contient 5 frames (colonnes 0 à 4) :
- **Frame 0** : Position de départ / préparation (debout ou légère flexion)
- **Frame 1** : Début du saut / impulsion
- **Frame 2** : Phase ascendante / décollage
- **Frame 3** : Phase aérienne / apogée du saut
- **Frame 4** : Phase descendante / atterrissage

### Adaptation à la résolution

Les sprite sheets et paramètres de saut (positions, vitesses, offsets) sont définis dans le repère de conception 1920x1080. Lors du démarrage, le moteur applique la résolution interne 1280x720 via `get_render_size()` et convertit toutes les valeurs d’affichage (taille du sprite, position écran, vitesse apparente) grâce au facteur `compute_scale(display_size)` afin de conserver un comportement homogène quelle que soit la résolution effective de la fenêtre.

### Système d'animation

- **Frame rate d'animation** : 12-15 FPS (frames par seconde) pour les animations de saut
- **Nombre de frames** : 5 frames par direction (selon les colonnes du sprite sheet)
- **Boucle d'animation** : L'animation de saut se joue une fois par saut, puis revient à l'animation de marche/idle
- **Transition** : Transition fluide entre l'animation de saut et l'animation de marche/idle

## Spécifications techniques

### Structure des données

#### Classe `Player` (extension)

**Nouvelles propriétés** :
- `jump_sprite_sheet: pygame.Surface` : Surface contenant le sprite sheet de saut
- `jump_velocity: float` : Vitesse initiale de saut (en pixels par seconde, négative vers le haut, par défaut: -400.0)
- `is_jumping: bool` : Indique si le personnage est en train de sauter
- `jump_frame: int` : Index de la frame d'animation de saut actuelle (0-4)
- `jump_animation_timer: float` : Timer pour gérer la vitesse d'animation de saut
- `jump_animation_speed: float` : Vitesse d'animation de saut en FPS (par défaut: 12.0)
- `can_jump: bool` : Indique si le personnage peut sauter (doit être au sol)
- `jump_sprite_width: int` : Largeur d'un sprite de saut (64 pixels)
- `jump_sprite_height: int` : Hauteur d'un sprite de saut (64 pixels)
- `_was_on_ground: bool` : Flag pour détecter l'atterrissage (passage de False à True pour `is_on_ground`)
- `_jump_key_pressed: bool` : Flag pour détecter si la touche de saut est actuellement pressée (pour gérer le double saut)
- `_has_double_jump: bool` : Indique si le personnage a encore son double saut disponible (uniquement si `level >= double_jump_unlock_level` effectif, issu de `PlayerStatsConfig` ou repli **3**)
- `_double_jump_used: bool` : Indique si le double saut a été utilisé pendant le saut actuel

**Nouvelles méthodes** :
- `jump() -> None` : Déclenche un saut si le personnage est au sol
- `double_jump() -> None` : Déclenche un double saut si le personnage est en l'air et a encore son double saut disponible (niveau ≥ seuil configuré)
- `_update_jump_animation(dt: float) -> None` : Met à jour l'animation de saut
- `_get_jump_sprite() -> Optional[pygame.Surface]` : Récupère le sprite de saut actuel à afficher
- `_get_sprite_at_jump(row: int, col: int) -> pygame.Surface` : Extrait un sprite de saut à la position (row, col) du sprite sheet
- `_handle_jump_input(keys: pygame.key.ScancodeWrapper) -> None` : Gère l'input de saut (saut normal et double saut)

### Mapping des directions de saut

```python
# Mapping des lignes du sprite sheet de saut selon spécification utilisateur
JUMP_DIRECTION_TO_ROW = {
    "left": 1,   # Ligne 2 (index 1)
    "right": 3,  # Ligne 4 (index 3)
}
```

### Contrôles

- **Flèche haut / Touche W** : Déclenche un saut (si le personnage est au sol) ou un double saut (si le personnage est en l'air, `level >= double_jump_unlock_level` effectif, et a relâché puis réappuyé sur la touche)
- **Note** : Le saut normal ne peut être déclenché que lorsque `is_on_ground == True`
- **Note double saut** : Le double saut est disponible uniquement à partir du niveau minimal lu dans `config/player_stats.toml` (`double_jump_unlock_level`, défaut **3**). Il nécessite que le joueur ait relâché la touche de saut après le premier saut, puis réappuie sur la touche pour déclencher le deuxième saut

### Mécanique de saut

#### Principe

Le saut fonctionne en appliquant une vitesse verticale initiale négative (vers le haut) au personnage. Cette vitesse est ensuite modifiée par la gravité, créant un mouvement parabolique naturel.

#### Implémentation

1. **Déclenchement du saut normal** :
   - Le joueur appuie sur la touche haut
   - Vérifier que `is_on_ground == True`
   - Si oui, déclencher le saut :
     - Mettre `is_jumping = True`
     - Mettre `can_jump = False` (empêcher les sauts multiples)
     - Appliquer `velocity_y = jump_velocity` (vitesse initiale négative)
     - Réinitialiser `jump_frame = 0`
     - Réinitialiser `jump_animation_timer = 0.0`
     - Mettre `_jump_key_pressed = True`
     - Si `level >=` seuil effectif de double saut : mettre `_has_double_jump = True` et `_double_jump_used = False`

2. **Pendant le saut** :
   - La gravité continue de s'appliquer (via `apply_gravity()`)
   - L'animation de saut progresse selon `jump_animation_speed`
   - La direction de saut est déterminée par `current_direction` (gauche ou droite)
   - **Gestion du double saut (uniquement si niveau ≥ seuil configuré)** :
     - Détecter le relâchement de la touche de saut : si la touche n'est plus pressée et que `_jump_key_pressed == True`, mettre `_jump_key_pressed = False`
     - Si le joueur réappuie sur la touche de saut (`_jump_key_pressed == False` puis la touche est pressée) et que `_has_double_jump == True` et `_double_jump_used == False` :
       - Déclencher le double saut via `double_jump()`

3. **Déclenchement du double saut** :
   - Vérifier que le personnage est en l'air (`is_on_ground == False`)
   - Vérifier que le niveau atteint le seuil (via `level_manager.level >= self._double_jump_unlock_level`, où `_double_jump_unlock_level` provient de `PlayerStatsConfig.double_jump_unlock_level` ou vaut **3** en repli si pas de stats)
   - Vérifier que `_has_double_jump == True` et `_double_jump_used == False`
   - Vérifier que la touche de saut a été relâchée puis réappuyée (`_jump_key_pressed == False` puis la touche est pressée)
   - Si toutes les conditions sont remplies :
     - Appliquer `velocity_y = jump_velocity` (vitesse initiale négative, relançant le saut)
     - Mettre `_double_jump_used = True`
     - Mettre `_has_double_jump = False`
     - Réinitialiser `jump_frame = 0` (optionnel : peut continuer l'animation ou la relancer)
     - Réinitialiser `jump_animation_timer = 0.0` (optionnel)
     - Mettre `_jump_key_pressed = True`

4. **Fin du saut** :
   - Le saut se termine lorsque le personnage touche le sol (`is_on_ground == True`)
   - Lorsque le personnage atterrit :
     - Mettre `is_jumping = False`
     - Mettre `can_jump = True`
     - Réinitialiser `jump_frame = 0`
     - Réinitialiser `_jump_key_pressed = False`
     - Réinitialiser `_has_double_jump = False` (sera réinitialisé au prochain saut si le niveau est encore ≥ au seuil)
     - Réinitialiser `_double_jump_used = False`
     - Revenir à l'animation de marche/idle

#### Gestion de l'animation

1. **État en saut** : Afficher les frames 0-4 de la ligne de saut correspondant à la direction
2. **État au sol** : Afficher l'animation de marche/idle normale
3. **Transition** : Transition fluide entre les animations

### Intégration avec la gravité

Le saut s'intègre naturellement avec le système de gravité existant :

- **Phase ascendante** : La vitesse initiale négative (`jump_velocity`) fait monter le personnage, mais la gravité la réduit progressivement
- **Apogée** : Lorsque `velocity_y` atteint 0, le personnage est à l'apogée du saut
- **Phase descendante** : La gravité accélère le personnage vers le bas jusqu'à l'atterrissage
- **Atterrissage** : Le système de collisions détecte le contact avec le sol et réinitialise l'état

### Intégration avec les collisions

Le système de collisions existant gère automatiquement le saut :

- **Collision par le bas (atterrissage)** : Lorsque le personnage atterrit, `is_on_ground` devient `True`, ce qui termine le saut
- **Collision par le haut (plafond)** : Si le personnage touche un plafond pendant le saut, `velocity_y` est réinitialisée à 0, interrompant le saut
- **Collisions latérales** : Les collisions latérales n'affectent pas le saut, mais empêchent le personnage de traverser les murs

## Implémentation

### Structure de fichiers

```
src/moteur_jeu_presentation/
├── entities/
│   ├── __init__.py
│   └── player.py          # Classe Player (extension)
```

### Modifications de la classe `Player`

#### Initialisation

**Note importante** : Le chargement du sprite sheet de saut doit utiliser le système de niveaux via `PlayerLevelManager` (voir spécification 7). Le sprite sheet `jump.png` doit être chargé via `level_manager.get_asset_path("jump.png")` pour garantir que le bon sprite sheet est utilisé selon le niveau actuel du joueur.

```python
def __init__(
    self,
    x: float,
    y: float,
    sprite_sheet_path: str,
    sprite_width: int = 64,
    sprite_height: int = 64,
    animation_speed: float = 10.0,
    jump_sprite_sheet_path: Optional[str] = None,
    player_level: int = DEFAULT_PLAYER_LEVEL,
    assets_root: Optional[Path] = None,
    stats_config: Optional[PlayerStatsConfig] = None,
) -> None:
    # ... code existant ...
    
    # Initialiser le PlayerLevelManager (voir spécification 7)
    self.level_manager = PlayerLevelManager(assets_root, player_level, stats_config)
    
    # Charger le sprite sheet de saut via le système de niveaux
    if jump_sprite_sheet_path is None:
        # Utiliser le PlayerLevelManager pour obtenir le chemin selon le niveau
        jump_path = self.level_manager.get_asset_path("jump.png")
    else:
        jump_path = Path(jump_sprite_sheet_path)
        if not jump_path.is_absolute():
            project_root = Path(__file__).parent.parent.parent.parent
            jump_path = project_root / jump_sprite_sheet_path
    
    self.jump_sprite_sheet = pygame.image.load(str(jump_path)).convert_alpha()
    self.jump_sprite_width = 64
    self.jump_sprite_height = 64
    
    # Propriétés de saut
    self.jump_velocity: float = -400.0  # Vitesse initiale de saut (négative = vers le haut)
    self.is_jumping: bool = False
    self.jump_frame: int = 0
    self.jump_animation_timer: float = 0.0
    self.jump_animation_speed: float = 12.0  # FPS
    self.can_jump: bool = True
    self._was_on_ground: bool = False  # Pour détecter l'atterrissage
    self._jump_key_pressed: bool = False  # Pour détecter le relâchement de la touche (double saut)
    self._has_double_jump: bool = False  # Indique si le double saut est disponible
    self._double_jump_used: bool = False  # Indique si le double saut a été utilisé
    # Seuil minimal pour le double saut : stats_config.double_jump_unlock_level si disponible, sinon 3
    self._double_jump_unlock_level: int = (
        stats_config.double_jump_unlock_level if stats_config is not None else 3
    )
```

**Rechargement lors du changement de niveau** : Lors d'un changement de niveau du joueur (via `player.set_level(niveau)`), le sprite sheet de saut doit être rechargé depuis le nouveau répertoire de niveau. Voir la spécification 7 pour plus de détails sur le système de rechargement des assets.

#### Méthode de saut

```python
def jump(self) -> None:
    """Déclenche un saut si le personnage est au sol.
    
    Le saut applique une vitesse verticale initiale négative qui sera
    modifiée par la gravité pour créer un mouvement parabolique naturel.
    """
    if self.is_on_ground and self.can_jump:
        self.is_jumping = True
        self.can_jump = False
        self.velocity_y = self.jump_velocity
        self.jump_frame = 0
        self.jump_animation_timer = 0.0
        # Marquer qu'on était au sol au moment du saut pour éviter l'annulation immédiate
        self._was_on_ground = True
        # Initialiser le double saut si le niveau atteint le seuil configuré
        if self.level_manager.level >= self._double_jump_unlock_level:
            self._has_double_jump = True
            self._double_jump_used = False

def double_jump(self) -> None:
    """Déclenche un double saut si le personnage est en l'air et a encore son double saut disponible.
    
    Le double saut est disponible à partir du seuil `double_jump_unlock_level` (TOML, défaut 3).
    Il nécessite que le joueur ait relâché la touche de saut après le premier saut,
    puis réappuie sur la touche pour déclencher le deuxième saut.
    Le double saut relance un nouveau saut depuis la position actuelle du personnage.
    """
    if (not self.is_on_ground and 
        self.level_manager.level >= self._double_jump_unlock_level and
        self._has_double_jump and 
        not self._double_jump_used):
        # Appliquer la vitesse de saut (relancer le saut)
        self.velocity_y = self.jump_velocity
        self._double_jump_used = True
        self._has_double_jump = False
        # Optionnel : réinitialiser l'animation pour un effet visuel
        # self.jump_frame = 0
        # self.jump_animation_timer = 0.0
```

#### Gestion de l'input

```python
def _handle_jump_input(self, keys: pygame.key.ScancodeWrapper) -> None:
    """Gère l'input de saut (saut normal et double saut).
    
    Args:
        keys: Objet ScancodeWrapper retourné par pygame.key.get_pressed()
    """
    jump_key_pressed = keys[pygame.K_UP] or keys[pygame.K_w]
    
    # Gestion du saut normal (au sol) - priorité sur le double saut
    # Cette vérification doit être faite en premier pour éviter que le double saut interfère
    if jump_key_pressed and self.is_on_ground and self.can_jump:
        self.jump()
        self._jump_key_pressed = True
    
    # Gestion du relâchement de la touche (pour permettre le double saut)
    # Détecte le passage de pressé à relâché
    elif not jump_key_pressed and self._jump_key_pressed:
        # La touche vient d'être relâchée
        self._jump_key_pressed = False
    
    # Gestion du double saut (en l'air, niveau >= seuil configuré)
    # Ne peut se déclencher que si :
    # - La touche est pressée
    # - Le personnage est en l'air
    # - La touche a été relâchée puis réappuyée (détecté par _jump_key_pressed == False puis la touche est pressée)
    # - Le niveau >= _double_jump_unlock_level
    # - Le double saut est disponible et n'a pas été utilisé
    # - Le personnage est en train de sauter (is_jumping == True) pour éviter les déclenchements accidentels
    elif (jump_key_pressed and 
          not self.is_on_ground and 
          self.is_jumping and  # Le personnage doit être en train de sauter
          not self._jump_key_pressed and  # La touche a été relâchée puis réappuyée
          self.level_manager.level >= self._double_jump_unlock_level and
          self._has_double_jump and 
          not self._double_jump_used):
        self.double_jump()
        self._jump_key_pressed = True
```

#### Mise à jour de l'animation de saut

```python
def _update_jump_animation(self, dt: float) -> None:
    """Met à jour l'animation de saut.
    
    Args:
        dt: Delta time en secondes
    """
    if self.is_jumping:
        # Incrémenter le timer d'animation
        self.jump_animation_timer += dt
        
        # Calculer le temps entre chaque frame
        frame_duration = 1.0 / self.jump_animation_speed
        
        # Avancer à la frame suivante si nécessaire
        if self.jump_animation_timer >= frame_duration:
            self.jump_frame += 1
            self.jump_animation_timer = 0.0
            
            # Si on a atteint la dernière frame, on peut continuer à afficher la dernière frame
            # ou revenir à l'animation de marche/idle selon le contexte
            if self.jump_frame >= 5:
                # Garder la dernière frame pendant le saut
                self.jump_frame = 4
    else:
        # Réinitialiser l'animation de saut si on n'est plus en saut
        self.jump_frame = 0
        self.jump_animation_timer = 0.0
```

#### Récupération du sprite de saut

```python
def _get_jump_sprite(self) -> Optional[pygame.Surface]:
    """Récupère le sprite de saut actuel à afficher.
    
    Returns:
        Surface pygame contenant le sprite de saut, ou None si pas en saut
    """
    if not self.is_jumping:
        return None
    
    row = self.JUMP_DIRECTION_TO_ROW.get(self.current_direction, 3)
    return self._get_sprite_at_jump(row, self.jump_frame)

def _extract_sprite(self, sheet: pygame.Surface, width: int, height: int, row: int, col: int) -> pygame.Surface:
    """Extrait une frame en vérifiant que le rectangle reste dans les limites du sprite sheet."""
    sheet_width = sheet.get_width()
    sheet_height = sheet.get_height()
    
    if sheet_width <= 0 or sheet_height <= 0:
        return pygame.Surface((width, height), pygame.SRCALPHA)
    
    x = col * width
    y = row * height
    
    max_x = max(sheet_width - width, 0)
    max_y = max(sheet_height - height, 0)
    x = max(0, min(x, max_x))
    y = max(0, min(y, max_y))
    
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

def _get_sprite_at_jump(self, row: int, col: int) -> pygame.Surface:
    """Extrait un sprite de saut à la position (row, col) du sprite sheet."""
    return self._extract_sprite(self.jump_sprite_sheet, self.jump_sprite_width, self.jump_sprite_height, row, col)
```

#### Modification de `_get_current_sprite()`

```python
def _get_current_sprite(self) -> pygame.Surface:
    """Récupère le sprite actuel à afficher.
    
    Returns:
        Surface pygame contenant le sprite actuel
    """
    # Si on est en saut, utiliser l'animation de saut
    jump_sprite = self._get_jump_sprite()
    if jump_sprite is not None:
        return jump_sprite
    
    # Sinon, utiliser l'animation de marche/idle normale
    row = self.DIRECTION_TO_ROW.get(self.current_direction, 3)
    return self._get_sprite_at(row, self.current_frame)
```

#### Modification de `update()`

```python
def update(self, dt: float, keys: pygame.key.ScancodeWrapper) -> None:
    """Met à jour la position et l'animation du personnage.
    
    Args:
        dt: Delta time en secondes
        keys: Objet ScancodeWrapper retourné par pygame.key.get_pressed()
    """
    # Gérer l'input de saut
    self._handle_jump_input(keys)
    
    # Gérer le mouvement (pour l'animation uniquement)
    self._handle_movement(keys, dt)
    
    # Mettre à jour les animations
    self._update_animation(dt)
    self._update_jump_animation(dt)
    
    # Gérer la fin du saut : détecter l'atterrissage (passage de False à True pour is_on_ground)
    # On ne met pas is_jumping à False si le personnage est au sol au moment du saut,
    # mais seulement s'il vient d'atterrir (était en l'air et est maintenant au sol)
    if self.is_jumping and self.is_on_ground and not self._was_on_ground:
        # Le personnage vient d'atterrir
        self.is_jumping = False
        self.can_jump = True
        self.jump_frame = 0
        self.jump_animation_timer = 0.0
        # Réinitialiser les flags de double saut
        self._jump_key_pressed = False
        self._has_double_jump = False
        self._double_jump_used = False
    
    # Mettre à jour le flag pour la prochaine frame
    self._was_on_ground = self.is_on_ground
```

**Note importante** : La vérification `if self.is_jumping and self.is_on_ground and not self._was_on_ground` est cruciale pour éviter que `is_jumping` soit mis à `False` immédiatement après le saut. Sans cette vérification, si le personnage est encore au sol dans la même frame (avant que le déplacement vertical ne soit appliqué), l'animation de saut ne se déclencherait pas.

### Intégration dans `main.py`

Le système de saut s'intègre avec le système de gravité et de collisions existant. **IMPORTANT** : La méthode `player.update(dt, keys)` doit être appelée dans la boucle principale, et **AVANT** le calcul du déplacement vertical pour que le saut puisse modifier `velocity_y` correctement.

**Ordre des opérations dans la boucle principale :**

1. **Appeler `player.update(dt, keys)`** : Gère le saut (modifie `velocity_y` si la touche est pressée) et les animations
2. **Appliquer la gravité** : Si le personnage n'est pas au sol, appliquer la gravité
3. **Calculer le déplacement vertical** : Utiliser `velocity_y` pour calculer `dy`
4. **Résoudre les collisions** : Utiliser le système de collisions
5. **Appliquer le déplacement** : Mettre à jour la position du personnage

**Exemple de code dans `main.py` :**

```python
# Dans la boucle principale
keys = pygame.key.get_pressed()

# IMPORTANT: Appeler player.update() AVANT le calcul du déplacement vertical
# pour que le saut puisse modifier velocity_y
player.update(dt, keys)

# Appliquer la gravité (si le personnage n'est pas au sol)
if not player.is_on_ground:
    player.apply_gravity(dt)

# Calculer le déplacement prévu
dx = 0.0
if keys[pygame.K_LEFT] or keys[pygame.K_a]:
    dx -= player.speed * dt
if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
    dx += player.speed * dt

# Le déplacement vertical est géré par la gravité (et le saut qui modifie velocity_y)
dy = player.velocity_y * dt

# Résoudre les collisions
player_rect = player.get_collision_rect()
corrected_dx, corrected_dy, is_on_ground = collision_system.resolve_collision(
    player_rect, dx, dy, player, camera_x
)

# Mettre à jour l'état au sol
player.is_on_ground = is_on_ground

# Appliquer le déplacement corrigé
player.x += corrected_dx
player.y += corrected_dy
```

**Note importante** : Ne pas appeler `player._handle_movement()` et `player._update_animation()` séparément. Utiliser uniquement `player.update(dt, keys)` qui gère tout, y compris le saut.

### Exemple d'utilisation

```python
from entities.player import Player
import pygame

# Initialisation
player = Player(
    x=640.0,
    y=360.0,
    sprite_sheet_path="sprite/walk.png",
    sprite_width=64,
    sprite_height=64,
    animation_speed=10.0,
    jump_sprite_sheet_path="sprite/jump.png",  # Optionnel, par défaut cherche jump.png
)

# Configuration
player.speed = 250.0  # pixels par seconde
player.jump_velocity = -400.0  # Vitesse initiale de saut
player.jump_animation_speed = 12.0  # FPS

# Dans la boucle de jeu
def update(dt: float) -> None:
    keys = pygame.key.get_pressed()
    player.update(dt, keys)  # Le saut est géré automatiquement

def draw(screen: pygame.Surface, camera_x: float) -> None:
    player.draw(screen, camera_x)  # L'animation de saut est affichée automatiquement
```

## Gestion des erreurs

Le système doit gérer les erreurs suivantes :

- **Fichier jump.png introuvable** : Si le fichier n'existe pas, afficher un message d'erreur et continuer sans animation de saut (ou utiliser l'animation de marche)
- **Dimensions incorrectes** : Vérifier que le sprite sheet a les bonnes dimensions (320x256 pour 5×4 sprites de 64x64)
- **Saut impossible** : Si le personnage n'est pas au sol, le saut ne doit pas être déclenché

## Double saut (seuil configurable)

### Configuration (`player_stats.toml`)

- **Clé racine** : `double_jump_unlock_level` (voir spécification **7** : format, validation **1 ≤ valeur ≤ max_level**, défaut **3** si absent).
- **Code** : le `Player` conserve `_double_jump_unlock_level` (entier), initialisé depuis `PlayerStatsConfig.double_jump_unlock_level` ou **3** si pas de stats.

### Principe

À partir du niveau du personnage **≥ `double_jump_unlock_level` effectif**, le joueur peut effectuer un double saut. Le double saut permet de déclencher un deuxième saut en l'air après le premier saut, relançant un nouveau saut depuis la position actuelle du personnage.

### Mécanique

1. **Condition d'activation** : Le double saut est disponible uniquement si `level_manager.level >= _double_jump_unlock_level`.

2. **Déclenchement du premier saut** :
   - Le joueur appuie sur la touche de saut alors qu'il est au sol
   - Le saut normal se déclenche
   - Si `level >= _double_jump_unlock_level`, `_has_double_jump` est mis à `True` et `_double_jump_used` est mis à `False`

3. **Relâchement de la touche** :
   - Le joueur doit **relâcher** la touche de saut après le premier saut
   - Le système détecte le relâchement via `_jump_key_pressed` (passe de `True` à `False`)
   - **Important** : Le double saut ne peut pas être déclenché tant que la touche n'a pas été relâchée puis réappuyée

4. **Déclenchement du double saut** :
   - Le joueur **réappuie** sur la touche de saut alors qu'il est en l'air
   - Le système vérifie que :
     - Le personnage est en l'air (`is_on_ground == False`)
     - `level >= _double_jump_unlock_level`
     - `_has_double_jump == True` et `_double_jump_used == False`
     - La touche a été relâchée puis réappuyée (`_jump_key_pressed == False` puis la touche est pressée)
   - Si toutes les conditions sont remplies, le double saut se déclenche :
     - `velocity_y` est réinitialisé à `jump_velocity` (relançant le saut)
     - `_double_jump_used` est mis à `True`
     - `_has_double_jump` est mis à `False`

5. **Réinitialisation** :
   - Lors de l'atterrissage, tous les flags de double saut sont réinitialisés
   - Le double saut sera à nouveau disponible au prochain saut (si le niveau est encore ≥ au seuil)

### Protection du saut normal

**Important** : Le double saut ne doit **jamais** interférer avec le déclenchement du saut normal. Le saut normal fonctionne exactement comme avant :
- Il se déclenche uniquement si le personnage est au sol (`is_on_ground == True`)
- Il ne nécessite pas de relâchement préalable de la touche
- Le double saut ne peut être déclenché qu'en l'air, donc il ne peut pas interférer avec le saut normal

### Exemple de séquence

1. **Niveau strictement inférieur au seuil** : Le joueur saute → atterrit → peut sauter à nouveau (comportement normal, pas de double saut)
2. **Niveau ≥ seuil** (ex. défaut 3) :
   - Le joueur appuie sur la touche de saut (au sol) → premier saut se déclenche
   - Le joueur relâche la touche de saut (en l'air) → système détecte le relâchement
   - Le joueur réappuie sur la touche de saut (en l'air) → double saut se déclenche
   - Le joueur atterrit → tous les flags sont réinitialisés

### Intégration avec le système de niveaux

Le double saut est conditionné par le niveau du personnage et le seuil lu dans `PlayerStatsConfig` (voir spécification 7). Lors d'un changement de niveau :
- Si le niveau passe d’**en dessous** du seuil à **au‑dessus ou égal** : le double saut devient disponible au prochain saut
- Si le niveau passe **sous** le seuil : le double saut n'est plus disponible (mais n'affecte pas les sauts en cours)

## Pièges courants

### Le saut ne fonctionne pas

**Problème** : Le personnage ne saute pas quand on appuie sur la touche haut.

**Causes possibles** :

1. **`player.update(dt, keys)` n'est pas appelé** : La méthode `update()` doit être appelée dans la boucle principale pour que le saut soit géré.
2. **`player.update()` est appelé après le calcul du déplacement vertical** : Si `player.update()` est appelé après avoir calculé `dy = player.velocity_y * dt`, le saut ne pourra pas modifier `velocity_y` avant le calcul du déplacement. **Solution** : Appeler `player.update(dt, keys)` AVANT le calcul du déplacement vertical.
3. **Appels séparés à `_handle_movement()` et `_update_animation()`** : Ne pas appeler ces méthodes séparément. Utiliser uniquement `player.update(dt, keys)` qui gère tout, y compris le saut.
4. **Le personnage n'est pas au sol** : Le saut ne peut être déclenché que si `is_on_ground == True`. Vérifier que le personnage a bien atterri sur une plateforme.

**Solution recommandée** : Suivre l'ordre des opérations décrit dans la section "Intégration dans `main.py`".

### L'animation de saut ne se déclenche pas

**Problème** : Le personnage saute (se déplace verticalement) mais l'animation de saut ne s'affiche pas.

**Cause** : La vérification de fin de saut dans `update()` utilise `if self.is_jumping and self.is_on_ground`, ce qui peut mettre `is_jumping` à `False` immédiatement après le saut si le personnage est encore au sol dans la même frame (avant que le déplacement vertical ne soit appliqué).

**Solution** : Utiliser un flag `_was_on_ground` pour détecter l'atterrissage réel (passage de `False` à `True` pour `is_on_ground`), plutôt que de simplement vérifier si le personnage est au sol pendant le saut.

**Implémentation** :
- Ajouter `self._was_on_ground: bool = False` dans `__init__()`
- Dans `jump()`, mettre `self._was_on_ground = True` au moment du saut
- Dans `update()`, vérifier `if self.is_jumping and self.is_on_ground and not self._was_on_ground` pour détecter l'atterrissage
- À la fin de `update()`, mettre à jour `self._was_on_ground = self.is_on_ground` pour la prochaine frame

Cela garantit que `is_jumping` reste `True` pendant tout le saut et n'est mis à `False` que lors de l'atterrissage réel.

### Le double saut ne fonctionne pas

**Problème** : Le double saut ne se déclenche pas alors que le niveau du personnage semble suffisant.

**Causes possibles** :

1. **Le niveau est sous le seuil** : Vérifier `level_manager.level >= self._double_jump_unlock_level` et la valeur de `double_jump_unlock_level` dans `config/player_stats.toml`.
2. **La touche n'a pas été relâchée** : Le double saut nécessite que le joueur relâche puis réappuie sur la touche. Si la touche reste pressée, le double saut ne peut pas se déclencher.
3. **Le double saut a déjà été utilisé** : Le double saut n'est disponible qu'une seule fois par saut (du premier saut jusqu'à l'atterrissage). Vérifier que `_double_jump_used == False`.
4. **Le personnage est au sol** : Le double saut ne peut être déclenché qu'en l'air. Vérifier que `is_on_ground == False`.

**Solution recommandée** : Suivre la logique décrite dans la section "Double saut (seuil configurable)" et s'assurer que toutes les conditions sont vérifiées dans `_handle_jump_input()`.

### Le double saut interfère avec le saut normal

**Problème** : Le saut normal ne se déclenche plus correctement après l'ajout du double saut.

**Cause** : La logique de double saut peut interférer avec la détection du saut normal si les conditions ne sont pas correctement ordonnées.

**Solution** : Toujours vérifier le saut normal **en premier** dans `_handle_jump_input()`, avant de vérifier le double saut. Le saut normal a la priorité et ne nécessite pas de conditions de relâchement de touche.

## Performance

### Optimisations

- **Chargement unique** : Le sprite sheet de saut est chargé une seule fois au démarrage
- **Extraction à la volée** : Les sprites sont extraits à la volée (ou mis en cache si nécessaire)
- **Pas de calculs supplémentaires** : Le saut utilise le système de gravité et de collisions existant, donc pas de surcharge de performance

### Métriques de performance

- **Temps de chargement** : < 5ms pour charger le sprite sheet de saut
- **Temps d'extraction** : < 0.1ms par frame (identique à l'extraction de marche)
- **Impact sur FPS** : Négligeable (< 0.1% de surcharge)

## Tests

### Tests unitaires à implémenter

1. **Test d'initialisation** : Vérifier que le sprite sheet de saut est correctement chargé
2. **Test de déclenchement** : Vérifier que le saut se déclenche uniquement quand le personnage est au sol
3. **Test de vitesse** : Vérifier que la vitesse initiale de saut est correctement appliquée
4. **Test d'animation** : Vérifier que l'animation de saut progresse correctement
5. **Test de direction** : Vérifier que l'animation de saut correspond à la direction du personnage
6. **Test d'atterrissage** : Vérifier que le saut se termine correctement à l'atterrissage
7. **Test de collision** : Vérifier que les collisions fonctionnent correctement pendant le saut
8. **Test de double saut (niveau ≥ seuil)** : Vérifier que le double saut se déclenche uniquement si :
   - `level >= double_jump_unlock_level` (avec une config de test explicite, pas seulement le défaut 3)
   - Le personnage est en l'air
   - La touche a été relâchée puis réappuyée
   - Le double saut n'a pas encore été utilisé
9. **Test de double saut (niveau < seuil)** : Vérifier que le double saut ne se déclenche pas si `level < double_jump_unlock_level`
10. **Test seuil TOML** : avec `double_jump_unlock_level = 2` (dans une config de test), vérifier le double saut dès le niveau 2 ; avec un seuil élevé, vérifier l’absence de double saut en dessous
11. **Test de relâchement de touche** : Vérifier que le double saut nécessite le relâchement puis la réappui de la touche
12. **Test de non-interférence** : Vérifier que le double saut n'interfère pas avec le saut normal
13. **Test de réinitialisation** : Vérifier que les flags de double saut sont correctement réinitialisés à l'atterrissage

### Exemple de test

```python
import pygame
from unittest.mock import MagicMock

def test_jump_initialization():
    """Test que le saut est correctement initialisé."""
    pygame.init()
    player = Player(100.0, 100.0, "sprite/walk.png", jump_sprite_sheet_path="sprite/jump.png")
    
    assert player.jump_velocity == -400.0
    assert player.is_jumping == False
    assert player.can_jump == True
    assert player.jump_frame == 0

def test_jump_trigger():
    """Test que le saut se déclenche correctement."""
    pygame.init()
    player = Player(100.0, 100.0, "sprite/walk.png", jump_sprite_sheet_path="sprite/jump.png")
    player.is_on_ground = True
    
    # Créer un mock pour pygame.key.get_pressed()
    keys = MagicMock()
    keys.__getitem__ = lambda self, key: key == pygame.K_UP
    
    player.update(0.1, keys)
    
    assert player.is_jumping == True
    assert player.velocity_y < 0  # Vitesse vers le haut
    assert player.can_jump == False

def test_jump_animation():
    """Test que l'animation de saut progresse correctement."""
    pygame.init()
    player = Player(100.0, 100.0, "sprite/walk.png", jump_sprite_sheet_path="sprite/jump.png")
    player.is_jumping = True
    player.current_direction = "right"
    
    initial_frame = player.jump_frame
    player._update_jump_animation(0.1)  # dt = 0.1 secondes
    
    # L'animation devrait avoir progressé (ou être à la même frame si le timer n'a pas dépassé le seuil)
    assert player.jump_frame >= initial_frame

def test_double_jump_at_unlock_level():
    """Test que le double saut fonctionne au niveau == double_jump_unlock_level (ex. 3 par défaut)."""
    pygame.init()
    # Fournir une PlayerStatsConfig de test avec double_jump_unlock_level = 3 si le constructeur l'exige
    player = Player(100.0, 100.0, "sprite/walk.png", jump_sprite_sheet_path="sprite/jump.png", player_level=3)
    player.is_on_ground = True
    
    # Premier saut
    keys = MagicMock()
    keys.__getitem__ = lambda self, key: key == pygame.K_UP
    player.update(0.1, keys)
    
    assert player.is_jumping == True
    assert player._has_double_jump == True
    assert player._double_jump_used == False
    
    # Simuler le fait d'être en l'air
    player.is_on_ground = False
    initial_velocity = player.velocity_y
    
    # Simuler le relâchement puis la réappui de la touche
    keys.__getitem__ = lambda self, key: False  # Touche relâchée
    player.update(0.1, keys)
    assert player._jump_key_pressed == False
    
    keys.__getitem__ = lambda self, key: key == pygame.K_UP  # Touche réappuyée
    player.update(0.1, keys)
    
    # Le double saut devrait s'être déclenché
    assert player._double_jump_used == True
    assert player._has_double_jump == False
    assert player.velocity_y == player.jump_velocity  # Vitesse réinitialisée

def test_double_jump_below_unlock_level():
    """Test que le double saut ne fonctionne pas si level < double_jump_unlock_level (ex. niveau 2 avec seuil 3)."""
    pygame.init()
    player = Player(100.0, 100.0, "sprite/walk.png", jump_sprite_sheet_path="sprite/jump.png", player_level=2)
    player.is_on_ground = True
    
    # Premier saut
    keys = MagicMock()
    keys.__getitem__ = lambda self, key: key == pygame.K_UP
    player.update(0.1, keys)
    
    assert player.is_jumping == True
    assert player._has_double_jump == False  # Pas de double saut sous le seuil (ex. 2 < 3)
    
    # Simuler le fait d'être en l'air et réappuyer sur la touche
    player.is_on_ground = False
    keys.__getitem__ = lambda self, key: False  # Touche relâchée
    player.update(0.1, keys)
    keys.__getitem__ = lambda self, key: key == pygame.K_UP  # Touche réappuyée
    player.update(0.1, keys)
    
    # Le double saut ne devrait pas s'être déclenché
    assert player._double_jump_used == False
```

## Contraintes et considérations

### Validation des limites du sprite sheet

**Important** : La méthode `_get_sprite_at_jump` doit valider que le rectangle d'extraction est dans les limites du sprite sheet avant d'extraire le sprite. Si le rectangle sort des limites (par exemple, si le sprite sheet a des dimensions différentes selon le niveau du personnage), cela peut causer des erreurs silencieuses ou des sprites vides/transparents, ce qui fait disparaître le personnage.

**Solution implémentée** :
- Vérifier les dimensions du sprite sheet avant l'extraction
- Clamper les coordonnées du rectangle pour qu'elles restent dans les limites
- Utiliser `subsurface()` au lieu de `blit()` avec un rectangle, car `subsurface()` lève une exception si le rectangle est invalide
- Retourner une surface transparente si l'extraction échoue, plutôt que de lever une exception qui pourrait faire planter le jeu

Cette validation est particulièrement importante pour les différents niveaux du personnage, car les sprite sheets peuvent avoir des dimensions légèrement différentes.

### Limitations

- **Saut unique (niveau < seuil)** : Le personnage ne peut sauter qu'une seule fois jusqu'à l'atterrissage
- **Double saut (niveau ≥ seuil)** : Le personnage peut effectuer un deuxième saut en l'air après avoir relâché puis réappuyé sur la touche de saut. Le double saut n'est disponible qu'une seule fois par saut (du premier saut jusqu'à l'atterrissage). Le seuil est lu dans `player_stats.toml` (`double_jump_unlock_level`, défaut **3**)
- **Direction fixe** : La direction de saut est déterminée par la dernière direction de mouvement
- **Animation linéaire** : L'animation de saut se joue linéairement, sans adaptation à la hauteur réelle du saut

### Évolutions futures possibles

- **Double saut** : seuil minimal piloté par `double_jump_unlock_level` dans `config/player_stats.toml` (défaut 3)
- **Saut variable** : Permettre des sauts de hauteur variable selon la durée d'appui sur la touche
- **Saut latéral** : Permettre des sauts avec impulsion horizontale
- **Animations adaptatives** : Adapter l'animation à la hauteur réelle du saut
- **Effets sonores** : Ajouter des sons de saut et d'atterrissage
- **Particules** : Ajouter des effets de particules lors du saut et de l'atterrissage
- **Saut sur murs** : Permettre de sauter le long des murs (wall jump)
- **Triple saut ou plus** : Permettre des sauts multiples supplémentaires à des niveaux plus élevés

## Références

- Bonnes pratiques : `bonne_pratique.md`
- Spécification personnage principal : `spec/2-personnage-principal.md`
- Spécification système de physique : `spec/4-systeme-de-physique-collisions.md`
- Spécification système de niveaux : `spec/7-systeme-de-niveaux-personnage.md` (clé racine `double_jump_unlock_level` pour le seuil du double saut)
- Documentation Pygame : [pygame.Surface](https://www.pygame.org/docs/ref/surface.html)
- Sprite sheet : `sprite/jump.png`

---

**Date de création** : 2024  
**Statut** : ✅ Implémenté

