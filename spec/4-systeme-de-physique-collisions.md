# 4 - Système de physique et collisions

## Contexte

Cette spécification définit un système de physique et de collisions pour empêcher le personnage principal de traverser les tiles de niveau de profondeur 2 (depth 2). Les tiles de depth 2 représentent les éléments de gameplay (plateformes, obstacles) qui sont rendus devant le joueur et doivent agir comme des obstacles solides. Ces tiles sont **non traversables de tous les côtés** : le personnage ne peut pas les traverser par le haut, le bas, la gauche ou la droite.

## Objectifs

- Implémenter un système de détection de collisions entre le personnage et les tiles de depth 2
- Empêcher le personnage de traverser les tiles solides de tous les côtés (haut, bas, gauche, droite)
- Gérer les collisions verticales (haut/bas) et horizontales (gauche/droite) de manière efficace
- Gérer les collisions de manière efficace et performante
- Intégrer le système de collisions avec le système de parallaxe existant
- Permettre la détection de collisions avec les tiles définis dans les fichiers de niveau

## Architecture

### Principe de fonctionnement

Le système de collisions fonctionne en deux étapes :

1. **Détection** : Vérifier si le personnage entre en collision avec les tiles de depth 2
2. **Résolution** : Empêcher le personnage de traverser les tiles en corrigeant sa position

### Tiles solides

- **Profondeur 2 (depth 2)** : Les tiles de cette profondeur sont considérés comme solides, **sauf ceux avec `is_background = true`**
- **Exclusion des décors** : Les tiles de depth 2 avec `is_background = true` sont **exclus des collisions** et peuvent être traversés par le joueur. Ces tiles s'affichent derrière le joueur et n'ont pas de collision (voir spécification 3 pour plus de détails sur `is_background`).
- **Solidité complète** : Les tiles de depth 2 sans `is_background` (ou avec `is_background = false`) sont **non traversables de tous les côtés** :
  - **Par le haut** : Le personnage ne peut pas monter à travers un tile (collision avec le plafond)
  - **Par le bas** : Le personnage ne peut pas tomber à travers un tile (collision avec le sol/plateforme)
  - **Par la gauche** : Le personnage ne peut pas traverser un tile en se déplaçant vers la gauche
  - **Par la droite** : Le personnage ne peut pas traverser un tile en se déplaçant vers la droite
- Les tiles peuvent être définis via :
  - Des lignes complètes dans la section `[layers]` du fichier de niveau
  - Des sprites individuels dans la section `[[sprites]]` du fichier de niveau
- Les tiles sont positionnés dans l'espace du monde (coordonnées absolues), pas dans l'espace de l'écran

### Zone de collision du personnage

Le personnage a une zone de collision rectangulaire (hitbox) :
- **Position** : Le rectangle de collision est aligné pour que son **bas** corresponde au **bas du sprite visuel**
- **Ancrage du sprite** : Le sprite est centré sur la position (`x`, `y`), donc son bas est à `y + sprite_height/2`
- **Alignement** : Le bas du rectangle de collision est positionné à `y + sprite_height/2` pour correspondre au bas du sprite
- **Dimensions** :
  - **Hauteur** : réduite de 6 pixels par rapport à la hauteur affichée (`display_height - 6`) afin de conserver la même marge supérieure quel que soit le facteur d’échelle appliqué au sprite.
  - **Largeur** : réduite de 40 pixels (`display_width - 40`) pour maintenir une marge latérale constante de 20 pixels de chaque côté. Ainsi, même si le sprite est redimensionné (par exemple `scale = 2.0`), la hitbox couvre toujours la majorité du personnage et empêche de traverser les tiles solides.
- **Ajustement optionnel** : Possibilité de définir une hitbox plus petite que le sprite pour un gameplay plus fluide via `collision_width` et `collision_height`
- **Pas d'espace vertical** : Grâce à l'offset vertical, les pieds restent visuellement ancrés dans le sol sans lévitation
- **Réduction en haut** : La réduction de 6 pixels en hauteur permet d'éviter que la collision avec le plafond se déclenche trop tôt, donnant une sensation de gameplay plus naturelle. Cette valeur peut être ajustée selon les besoins visuels.
- **Offset vertical** : `collision_offset_y = -4` pour que le bas de la hitbox soit 4 pixels au-dessus du bas du sprite, ce qui réduit l'impression de flottement tout en évitant de traverser les tiles.
- **Tolérance dynamique des tiles** : Pour éviter qu'un personnage agrandi avec une hitbox réduite ne se glisse entre des tiles adjacentes, le moteur élargit **uniquement la largeur** des rectangles de collision des tiles. L'élargissement est **dynamique** selon l'état du mouvement :
  - ⚠️ **Important** : Seule la **largeur** est élargie (en ajoutant `width_expand / 2` de chaque côté), **jamais la hauteur**, pour éviter des collisions verticales incorrectes (exemple : un personnage qui saute au-dessus d'un bloc doit pouvoir passer au-dessus, sans être bloqué par un rectangle élargi verticalement).
  - **Au sol et en mouvement horizontal** (`is_on_ground = True` et `dx != 0`) : élargissement **désactivé** (`width_expand = 0.0`) pour éviter les retours en arrière indésirables.
  - **En chute ou déplacement vertical nul** (`velocity_y >= 0`) : élargissement **réduit** à `(display_width - collision_width) * 0.1`, limité à 4 pixels, pour garder une tolérance minimale sans provoquer de poussées latérales.
  - **En phase ascendante (saut)** (`velocity_y < 0`) : élargissement **standard réduit** à `(display_width - collision_width) * 0.3`, limité à 6 pixels, pour combler les micro-gaps tout en conservant la précision des collisions.
  - Cette compensation horizontale dynamique garantit un gameplay fluide : tolérance minimale pendant les déplacements au sol, protection contre les gaps lors des sauts ou des collisions complexes.

### Gravité

Le personnage est soumis à la gravité et tombe vers le bas :
- **Force de gravité** : Constante appliquée verticalement vers le bas (en pixels par seconde²)
- **Vitesse de chute** : La vitesse verticale augmente avec le temps sous l'effet de la gravité
- **Vitesse maximale de chute** : Limite la vitesse de chute pour éviter des chutes trop rapides
- **État au sol** : Le personnage est considéré "au sol" lorsqu'il est en collision avec un tile par le bas
- **Saut** : (Évolution future) Le personnage pourra sauter pour contrer la gravité

## Spécifications techniques

### Structure des données

#### Classe `CollisionSystem`

```python
class CollisionSystem:
    """Système de gestion des collisions entre le personnage et les tiles."""
    
    def __init__(
        self,
        parallax_system: ParallaxSystem,
        screen_width: int,
        screen_height: int
    ) -> None:
        """
        Args:
            parallax_system: Système de parallaxe contenant les couches
            screen_width: Largeur de l'écran
            screen_height: Hauteur de l'écran
        """
```

**Propriétés** :
- `parallax_system: ParallaxSystem` : Référence au système de parallaxe
- `screen_width: int` : Largeur de l'écran
- `screen_height: int` : Hauteur de l'écran
- `_collision_layers: List[Layer]` : Liste mise en cache des couches de depth 2 (tiles solides)
- `_solid_rects_cache: Dict[str, List[pygame.Rect]]` : Cache des rectangles de collision par layer (évite de recalculer à chaque frame)

**Méthodes principales** :
- `check_collision(player_rect: pygame.Rect, camera_x: float) -> Optional[pygame.Rect]` : Vérifie si le personnage entre en collision avec un tile
- `resolve_collision(player_rect: pygame.Rect, dx: float, dy: float, player: Player, camera_x: float) -> Tuple[float, float, bool]` : Résout la collision en ajustant la position du personnage et retourne l'état au sol
- `check_climbable_collision(player_rect: pygame.Rect, camera_x: float) -> bool` : Vérifie si le personnage est en collision avec un bloc grimpable et met à jour `player.is_on_climbable`
- `get_collision_rects(camera_x: float) -> List[pygame.Rect]` : Récupère tous les rectangles de collision des tiles de depth 2 visibles (utilise le cache)
- `get_climbable_rects(camera_x: float) -> List[pygame.Rect]` : Récupère tous les rectangles de collision des blocs grimpables (couches avec `is_background = true` et `is_climbable = true`)
- `remove_layer_collisions(layer_name: str) -> None` : Supprime les rectangles de collision d'une layer du cache (utilisé par le système d'événements lors du masquage de sprites)
- `remove_layer_from_collisions(layer: Layer) -> None` : Retire une layer de la liste des layers de collision (utilisé par le système d'événements)
- `_extract_solid_rects_from_surface(surface: pygame.Surface, layer_name: str, tile_size: int = 64) -> List[pygame.Rect]` : Extrait les rectangles de collision depuis une surface (avec cache)
- `_has_solid_pixels(surface: pygame.Surface, rect: pygame.Rect) -> bool` : Vérifie si une zone rectangulaire contient des pixels solides (non transparents)

#### Classe `Player` (extension)

**Nouvelles propriétés** :
- `collision_width: float` : Largeur de la zone de collision (par défaut: `sprite_width - 40.0` pour offrir une marge latérale de 20 pixels de chaque côté)
- `collision_height: float` : Hauteur de la zone de collision (par défaut: `sprite_height - 6.0` pour éviter les collisions prématurées avec le plafond)
- `collision_offset_x: float` : Offset horizontal de la zone de collision par rapport au centre (par défaut: 0.0)
- `collision_offset_y: float` : Offset vertical de la zone de collision (par défaut: `-4.0` pour que le bas de la hitbox soit légèrement au-dessus du bas du sprite)
- `velocity_y: float` : Vitesse verticale du personnage (en pixels par seconde, positive vers le bas)
- `gravity: float` : Force de gravité (en pixels par seconde², par défaut: 800.0)
- `max_fall_speed: float` : Vitesse maximale de chute (en pixels par seconde, par défaut: 500.0)
- `is_on_ground: bool` : Indique si le personnage est au sol (en collision avec un tile par le bas)

**Nouvelles méthodes** :
- `get_collision_rect() -> pygame.Rect` : Retourne le rectangle de collision du personnage, aligné pour que son bas corresponde au bas du sprite visuel
- `set_position(x: float, y: float) -> None` : Définit la position du personnage (utilisé pour la résolution de collision)
- `apply_gravity(dt: float) -> None` : Applique la gravité au personnage
- `reset_velocity_y() -> None` : Réinitialise la vitesse verticale (utilisé lors d'une collision par le bas)

### Détection de collisions

#### Méthode de détection

Le système utilise une détection de collision par rectangles (AABB - Axis-Aligned Bounding Box) :

1. **Récupération des tiles solides** : Extraire toutes les couches de depth 2 du système de parallaxe, en excluant celles avec `is_background = true`
2. **Conversion en rectangles de collision** : Pour chaque tile visible, créer un rectangle de collision basé sur :
   - La position du tile dans l'espace du monde (en tenant compte de `offset_x` de la couche)
   - Les dimensions du sprite (64x64 pixels par défaut) et le facteur `scale`
   - **Extraction pixel-perfect** : Utiliser `pygame.mask.from_surface()` pour obtenir des rectangles englobants précis des zones non transparentes. Cela garantit que les collisions respectent exactement la position réelle des sprites, même lorsqu'ils sont décalés (ex: `x_offset = 3300`) ou redimensionnés (`scale = 2`).
   - **Fallback robuste** : Si la génération du mask échoue (surface vide, erreur Pygame), une stratégie d'échantillonnage colonne par colonne se déclenche automatiquement. Cette stratégie ajuste désormais finement `first_solid_x` / `last_solid_x` pour garantir une largeur alignée sur les pixels non-transparents.
   - Les rectangles sont mis en cache pour éviter les recalculs à chaque frame
3. **Test de collision** : Vérifier si le rectangle de collision du personnage intersecte avec un rectangle de tile

#### Optimisations

- **Culling spatial** : Ne vérifier que les tiles visibles à l'écran (avec une marge de sécurité)
- **Mise en cache des couches** : Mettre en cache la liste des couches de depth 2 qui sont solides (excluant celles avec `is_background = true`)
- **Mise en cache des rectangles de collision** : Les rectangles de collision sont calculés une seule fois par layer et mis en cache dans `_solid_rects_cache`. Cela évite de recalculer les rectangles à chaque frame, ce qui améliore significativement les performances.
- **Extraction optimisée** : L'extraction des rectangles de collision utilise un échantillonnage (tous les 8 pixels verticalement) pour trouver rapidement la position exacte des sprites, puis une recherche fine pour déterminer la position précise du premier pixel solide.
- **Calculs optimisés** : Utiliser les rectangles pygame pour des tests de collision rapides

### Gravité

#### Principe

Le personnage est constamment soumis à la gravité qui l'attire vers le bas. La gravité s'applique à chaque frame et augmente la vitesse verticale du personnage.

#### Application de la gravité

```python
def apply_gravity(dt: float) -> None:
    """Applique la gravité au personnage.
    
    Args:
        dt: Delta time en secondes
    """
    # Augmenter la vitesse verticale avec la gravité
    self.velocity_y += self.gravity * dt
    
    # Limiter la vitesse de chute
    if self.velocity_y > self.max_fall_speed:
        self.velocity_y = self.max_fall_speed
```

#### Interaction avec les collisions

- **Collision par le bas** : Lorsque le personnage entre en collision avec un tile par le bas, il est considéré "au sol" :
  - La vitesse verticale est réinitialisée à 0
  - Le flag `is_on_ground` est mis à `True`
  - La gravité ne s'applique plus tant que le personnage reste au sol
  - Le personnage est empêché de continuer à descendre

- **Collision par le haut** : Lorsque le personnage entre en collision avec un tile par le haut (plafond) :
  - La vitesse verticale est réinitialisée à 0
  - Le personnage ne peut pas continuer à monter
  - Le personnage est empêché de traverser le tile par le haut

- **Collision par la gauche** : Lorsque le personnage entre en collision avec un tile par la gauche :
  - Le déplacement horizontal vers la gauche est bloqué
  - Le personnage est positionné juste à droite du tile
  - Le personnage ne peut pas traverser le tile en se déplaçant vers la gauche

- **Collision par la droite** : Lorsque le personnage entre en collision avec un tile par la droite :
  - Le déplacement horizontal vers la droite est bloqué
  - Le personnage est positionné juste à gauche du tile
  - Le personnage ne peut pas traverser le tile en se déplaçant vers la droite

- **Pas de collision** : Si le personnage n'est pas au sol, la gravité continue de s'appliquer

### Résolution de collisions

#### Principe

Lorsqu'une collision est détectée, le système doit empêcher le personnage de traverser le tile en corrigeant sa position et en gérant la vitesse verticale.

#### Méthode de résolution

1. **Détection de collision améliorée** : Le système doit détecter non seulement les chevauchements directs, mais aussi les **traversées complètes** qui peuvent se produire à grande vitesse. Cette détection est critique pour empêcher le personnage de passer à travers un tile en une seule frame lorsque la vitesse est très élevée :
   - **Cas 1 : Chevauchement direct** : Utiliser `colliderect()` pour détecter les collisions classiques où le rectangle du joueur chevauche le rectangle du tile
   - **Cas 2 : Traversée complète vers le bas** (`dy > 0`) : Si le joueur était au-dessus du tile (`player_rect.bottom <= tile_rect.top`) avant le déplacement et se trouve maintenant en dessous (`new_rect.top >= tile_rect.bottom`) après le déplacement, avec un chevauchement horizontal, alors une collision est détectée. Cela empêche le personnage de tomber à travers un tile même avec une vitesse de chute très élevée.
   - **Cas 3 : Traversée complète vers le haut** (`dy < 0`) : Si le joueur était en dessous du tile (`player_rect.top >= tile_rect.bottom`) avant le déplacement et se trouve maintenant au-dessus (`new_rect.bottom <= tile_rect.top`) après le déplacement, avec un chevauchement horizontal, alors une collision est détectée. Cela empêche le personnage de sauter à travers un plafond même avec une vitesse de saut très élevée.
   - ⚠️ **Critique pour les grandes vitesses** : Sans cette détection de traversée complète, un personnage avec une vitesse très élevée (par exemple `dy > 64` pixels par frame pour un tile de 64 pixels) peut traverser complètement un tile sans que `colliderect()` ne détecte de collision, car il n'y a plus de chevauchement après le déplacement. Cette protection garantit qu'**il est impossible, même avec une grande vitesse, pour le joueur d'avoir une collision qui entraîne un positionnement en bas du sprite collisionné** (y plus grand que le bas du tile).
2. **Détection de la direction de collision** : Déterminer de quel côté le personnage entre en collision (haut, bas, gauche, droite) en analysant la direction du déplacement prévu (`dx`, `dy`)
3. **Correction de position** : Ajuster la position du personnage pour qu'il soit juste à côté du tile, empêchant toute traversée :
   - **Collision par le haut** : Positionner le personnage au-dessus du tile (`new_rect.top = tile_rect.bottom`) et réinitialiser `velocity_y` à 0. Le personnage ne peut pas traverser le tile par le haut.
   - **Collision par le bas** : Positionner le bas du rectangle de collision exactement au-dessus du tile (`new_rect.bottom = tile_rect.top`), réinitialiser `velocity_y` à 0, et mettre `is_on_ground = True`. Grâce à l'alignement du rectangle de collision avec le bas du sprite, cela garantit qu'il n'y a **pas d'espace vertical** entre le sprite et le tile. Le personnage ne peut pas traverser le tile par le bas.
   - **Collision par la gauche** : Positionner le personnage à gauche du tile (`new_rect.right = tile_rect.left`). Le déplacement horizontal vers la gauche est bloqué, empêchant le personnage de traverser le tile.
   - **Collision par la droite** : Positionner le personnage à droite du tile (`new_rect.left = tile_rect.right`). Le déplacement horizontal vers la droite est bloqué, empêchant le personnage de traverser le tile.
   - **Détection des plafonds lors des collisions de coin** : Lorsque le joueur se déplace vers le haut (`dy < 0`) et qu'il passe sous le coin avant d'un tile (chevauchement horizontal minimal), le moteur compare la position verticale **avant** et **après** le déplacement. Si le `player_rect.top` se trouvait sous `tile_rect.bottom` et que `new_rect.top` le dépasse, la collision est toujours considérée comme **verticale**. Le joueur est alors repositionné sur le bas du tile le plus haut intersecté à cette abscisse (`new_rect.top = min(tile_rect.bottom)`), et `velocity_y` est remise à `0`. Cette règle empêche les disparitions lorsqu'un coin avant est percuté depuis le dessous : même si le chevauchement horizontal est très faible, le plafond reste infranchissable.
4. **Résolution séparée sur X et Y** : Les collisions horizontales et verticales sont résolues indépendamment pour permettre un mouvement fluide le long des surfaces
5. **Résolution itérative** : L'algorithme utilise une approche itérative pour gérer les collisions multiples. Si plusieurs tiles sont impliqués dans une collision, la boucle itère jusqu'à ce que toutes les collisions soient résolues, avec une limite de sécurité pour éviter les boucles infinies
6. **Gestion de l'état au sol** : Si le personnage n'est plus en collision par le bas, mettre `is_on_ground = False`
7. **Filtrage directionnel des collisions** : 
   - La résolution **horizontale** ne corrige que les collisions où `overlap_horizontal < overlap_vertical` (collision principalement horizontale)
   - La résolution **verticale** ne corrige que les collisions où `overlap_vertical <= overlap_horizontal` (collision principalement verticale)
   - ⚠️ **Important pour les coins** : Cette distinction empêche les corrections incorrectes lors de collisions de coin. Par exemple, quand un joueur saute sur le coin d'un bloc, la résolution horizontale ajuste d'abord la position latérale, puis la résolution verticale vérifie que la collision restante est bien verticale avant d'appliquer une correction. Cela évite que le joueur "disparaisse sous la carte" en cas de collision de coin ambiguë.
8. **Vérification de position après correction horizontale** :
   - Après la résolution horizontale, si le centre du joueur est clairement à gauche ou à droite du tile (avec une tolérance de 2 pixels), la résolution verticale ignore cette collision.
   - ⚠️ **Critique pour les coins** : Cette vérification empêche les corrections verticales incorrectes après qu'une correction horizontale ait poussé le joueur sur le côté d'un tile. Sans cette vérification, le joueur pourrait être poussé vers le bas alors qu'il devrait simplement continuer son saut après avoir été repoussé latéralement par le coin.
9. **Filtrage des collisions arrière** :
   - Les collisions avec des tiles situés à l'arrière du joueur (par rapport à sa direction de regard) sont **ignorées** pour éviter que le joueur soit bloqué par des obstacles derrière lui.
   - **Direction du joueur** : La direction est déterminée par la propriété `current_direction` du joueur (`"left"` ou `"right"`).
   - **Collision arrière à droite** : Si le joueur regarde vers la gauche (`current_direction == "left"`), les collisions avec des tiles situés à droite du centre du joueur sont ignorées.
   - **Collision arrière à gauche** : Si le joueur regarde vers la droite (`current_direction == "right"`), les collisions avec des tiles situés à gauche du centre du joueur sont ignorées.
   - **Détection** : Pour déterminer si un tile est à l'arrière, comparer la position horizontale du centre du tile avec le centre horizontal du rectangle de collision du joueur :
     - Si `current_direction == "left"` et `tile_center_x > player_center_x` → collision arrière, ignorer
     - Si `current_direction == "right"` et `tile_center_x < player_center_x` → collision arrière, ignorer
   - **Application** : Ce filtrage s'applique uniquement aux **collisions horizontales** (pas aux collisions verticales comme le sol ou le plafond) pour permettre au joueur de se déplacer librement sans être bloqué par des obstacles derrière lui.

#### Algorithme de résolution

```python
def resolve_collision(
    player_rect: pygame.Rect,
    dx: float,
    dy: float,
    player: Player,
    camera_x: float
) -> Tuple[float, float, bool]:
    """Résout une collision en ajustant le déplacement.
    
    Args:
        player_rect: Rectangle de collision du personnage dans l'espace du monde
        dx: Déplacement horizontal prévu
        dy: Déplacement vertical prévu
        player: Référence au personnage pour gérer la vitesse verticale
        camera_x: Position horizontale de la caméra
        
    Returns:
        Tuple (dx_corrected, dy_corrected, is_on_ground) avec les déplacements corrigés
        et l'état au sol
    """
    is_on_ground = False
    
    # Récupérer tous les rectangles de collision autour de la caméra actuelle
    collision_rects = self.get_collision_rects(camera_x)

    # Anticiper les déplacements rapides : calculer la caméra future potentielle
    future_camera_x = player.x + dx - (self.screen_width / 2)
    if abs(future_camera_x - camera_x) > (self.screen_width * 0.25):
        future_rects = self.get_collision_rects(future_camera_x)
        # Fusionner sans dupliquer les rectangles pour couvrir les deux zones
        seen = {(rect.x, rect.y, rect.width, rect.height) for rect in collision_rects}
        for rect in future_rects:
            key = (rect.x, rect.y, rect.width, rect.height)
            if key not in seen:
                collision_rects.append(rect)
                seen.add(key)
    
    # Résoudre d'abord horizontalement, puis verticalement
    # Cela permet de gérer correctement les collisions avec plusieurs tiles
    
    # Limite de sécurité pour les boucles itératives
    max_iterations = 10
    
    # Résolution horizontale (empêche la traversée latérale)
    # D'abord, vérifier si le personnage est déjà en collision et le sortir si nécessaire
    new_rect_x = player_rect.copy()
    
    # Vérifier les collisions horizontales existantes et sortir le personnage si nécessaire
    # On itère pour gérer plusieurs collisions simultanées
    # IMPORTANT: On ne sort que des collisions HORIZONTALES, pas des collisions verticales
    iteration_pre = 0
    while iteration_pre < max_iterations:
        collision_found_pre = False
        for tile_rect in collision_rects:
            if new_rect_x.colliderect(tile_rect):
                # Vérifier si c'est une collision principalement horizontale ou verticale
                overlap_left = new_rect_x.right - tile_rect.left
                overlap_right = tile_rect.right - new_rect_x.left
                overlap_top = new_rect_x.bottom - tile_rect.top
                overlap_bottom = tile_rect.bottom - new_rect_x.top
                
                # Calculer les overlaps horizontaux et verticaux
                overlap_horizontal = min(overlap_left, overlap_right)
                overlap_vertical = min(overlap_top, overlap_bottom)
                
                # FILTRAGE DES COLLISIONS ARRIÈRE : Ignorer les collisions avec des tiles
                # situés à l'arrière du joueur par rapport à sa direction de regard
                player_center_x = new_rect_x.x + new_rect_x.width / 2
                tile_center_x = tile_rect.x + tile_rect.width / 2
                is_back_collision = False
                
                if hasattr(player, 'current_direction'):
                    if player.current_direction == "left" and tile_center_x > player_center_x:
                        # Le joueur regarde vers la gauche, le tile est à droite (arrière)
                        is_back_collision = True
                    elif player.current_direction == "right" and tile_center_x < player_center_x:
                        # Le joueur regarde vers la droite, le tile est à gauche (arrière)
                        is_back_collision = True
                
                # Si c'est une collision principalement horizontale (pas verticale)
                # On sort le personnage horizontalement
                # SAUF si c'est une collision arrière (qui est ignorée)
                if overlap_horizontal < overlap_vertical and not is_back_collision:
                    collision_found_pre = True
                    if overlap_left < overlap_right:
                        # Plus proche du côté gauche, sortir par la gauche
                        new_rect_x.right = tile_rect.left
                    else:
                        # Plus proche du côté droit, sortir par la droite
                        new_rect_x.left = tile_rect.right
                    break  # Corriger une collision à la fois
        
        if not collision_found_pre:
            break
        iteration_pre += 1
    
    # Maintenant appliquer le déplacement horizontal
    new_rect_x.x += dx
    
    # Vérifier les collisions horizontales et corriger
    # On doit itérer jusqu'à ce qu'il n'y ait plus de collisions
    # pour gérer les cas où plusieurs tiles sont impliqués
    iteration = 0
    while iteration < max_iterations:
        collision_found = False
        for tile_rect in collision_rects:
            if new_rect_x.colliderect(tile_rect):
                # Vérifier si c'est une collision principalement horizontale
                # On ne corrige que les collisions horizontales, pas les verticales
                overlap_left = new_rect_x.right - tile_rect.left
                overlap_right = tile_rect.right - new_rect_x.left
                overlap_top = new_rect_x.bottom - tile_rect.top
                overlap_bottom = tile_rect.bottom - new_rect_x.top
                
                # Calculer les overlaps horizontaux et verticaux
                overlap_horizontal = min(overlap_left, overlap_right)
                overlap_vertical = min(overlap_top, overlap_bottom)
                
                # FILTRAGE DES COLLISIONS ARRIÈRE : Ignorer les collisions avec des tiles
                # situés à l'arrière du joueur par rapport à sa direction de regard
                player_center_x = new_rect_x.x + new_rect_x.width / 2
                tile_center_x = tile_rect.x + tile_rect.width / 2
                is_back_collision = False
                
                if hasattr(player, 'current_direction'):
                    if player.current_direction == "left" and tile_center_x > player_center_x:
                        # Le joueur regarde vers la gauche, le tile est à droite (arrière)
                        is_back_collision = True
                    elif player.current_direction == "right" and tile_center_x < player_center_x:
                        # Le joueur regarde vers la droite, le tile est à gauche (arrière)
                        is_back_collision = True
                
                # Si c'est une collision principalement horizontale, on la corrige
                # SAUF si c'est une collision arrière (qui est ignorée)
                if overlap_horizontal < overlap_vertical and not is_back_collision:
                    collision_found = True
                    # Déterminer la direction de la collision en fonction de la position relative
                    # et de la direction du mouvement
                    
                    # Si on se déplace vers la droite, on doit être bloqué à gauche du tile
                    if dx > 0:
                        # Bloquer à gauche du tile
                        new_rect_x.right = tile_rect.left
                    # Si on se déplace vers la gauche, on doit être bloqué à droite du tile
                    elif dx < 0:
                        # Bloquer à droite du tile
                        new_rect_x.left = tile_rect.right
                    else:
                        # Si dx == 0 après correction, déterminer la direction de sortie
                        # en fonction de la position relative
                        if overlap_left < overlap_right:
                            # Plus proche du côté gauche, sortir par la gauche
                            new_rect_x.right = tile_rect.left
                        else:
                            # Plus proche du côté droit, sortir par la droite
                            new_rect_x.left = tile_rect.right
                    break  # Corriger une collision à la fois
        
        if not collision_found:
            break
        iteration += 1
    
    # Résolution verticale (avec le rectangle horizontalement corrigé)
    # Empêche la traversée verticale
    new_rect = new_rect_x.copy()
    new_rect.y += dy
    
    # Vérifier les collisions verticales et corriger
    iteration = 0
    while iteration < max_iterations:
        collision_found = False
        for tile_rect in collision_rects:
            # DÉTECTION AMÉLIORÉE : Vérifier non seulement le chevauchement,
            # mais aussi si le joueur a traversé le tile pendant le déplacement
            has_collision = False
            
            # Cas 1 : Chevauchement direct (détection classique)
            if new_rect.colliderect(tile_rect):
                has_collision = True
            # Cas 2 : Traversée complète vers le bas (dy > 0)
            # Le joueur était au-dessus et est maintenant en dessous
            elif dy > 0:
                # Vérifier si le joueur a traversé le tile verticalement
                # Position avant : joueur au-dessus ou chevauchant le haut du tile
                # Position après : joueur en dessous ou chevauchant le bas du tile
                player_was_above = player_rect.bottom <= tile_rect.top
                player_is_below = new_rect.top >= tile_rect.bottom
                # Vérifier aussi le chevauchement horizontal
                horizontal_overlap = (
                    new_rect.right > tile_rect.left and 
                    new_rect.left < tile_rect.right
                )
                if player_was_above and player_is_below and horizontal_overlap:
                    has_collision = True
            # Cas 3 : Traversée complète vers le haut (dy < 0)
            # Le joueur était en dessous et est maintenant au-dessus
            elif dy < 0:
                player_was_below = player_rect.top >= tile_rect.bottom
                player_is_above = new_rect.bottom <= tile_rect.top
                horizontal_overlap = (
                    new_rect.right > tile_rect.left and 
                    new_rect.left < tile_rect.right
                )
                if player_was_below and player_is_above and horizontal_overlap:
                    has_collision = True
            
            if has_collision:
                collision_found = True
                if dy > 0:  # Déplacement vers le bas (chute)
                    # Bloquer au-dessus du tile
                    # Placer le bas du rectangle de collision exactement au-dessus du tile
                    # Cela garantit qu'il n'y a pas d'espace entre le joueur et le tile
                    # et que le joueur ne peut JAMAIS se retrouver en dessous du tile
                    new_rect.bottom = tile_rect.top
                    player.velocity_y = 0.0  # Réinitialiser la vitesse verticale
                    is_on_ground = True  # Le personnage est au sol
                elif dy < 0:  # Déplacement vers le haut
                    # Bloquer en dessous du tile
                    new_rect.top = tile_rect.bottom
                    player.velocity_y = 0.0  # Réinitialiser la vitesse verticale
                break  # Corriger une collision à la fois
        
        if not collision_found:
            break
        iteration += 1
    
    # Retourner les déplacements corrigés
    corrected_dx = new_rect.x - player_rect.x
    corrected_dy = new_rect.y - player_rect.y
    return (corrected_dx, corrected_dy, is_on_ground)
```

**Note importante** : L'algorithme utilise une approche itérative pour résoudre les collisions multiples. Cela garantit que même si plusieurs tiles sont impliqués dans une collision (par exemple, le personnage entre en collision avec plusieurs tiles en même temps), toutes les collisions sont correctement résolues. La boucle itère jusqu'à ce qu'il n'y ait plus de collisions détectées, avec une limite de sécurité pour éviter les boucles infinies.

**Détection de traversée complète et collisions de coin** : La détection de traversée complète (Cas 2 et Cas 3) est compatible avec la détection de coin existante (`entered_from_below`). La détection de traversée complète est plus générale et couvre tous les cas de traversée, y compris les cas de coin. La détection de coin spécifique peut être utilisée pour gérer les cas où plusieurs tiles sont impliqués (par exemple, trouver le plafond le plus haut parmi plusieurs tiles). Les deux détections peuvent coexister dans le code, la détection de traversée complète garantissant qu'aucune traversée n'est manquée, même à grande vitesse.

**⚠️ IMPORTANT - Implémentation critique** : La détection de traversée complète (Cas 2 et Cas 3) est **OBLIGATOIRE** et doit être implémentée dans le code. Sans cette détection, le personnage peut traverser les tiles à grande vitesse (notamment au niveau 5 avec une vitesse de 462.5 pixels/seconde), causant des bugs critiques où le personnage disparaît sous le sol. Cette fonctionnalité est implémentée dans `src/moteur_jeu_presentation/physics/collision.py` dans la méthode `resolve_collision()` (section de résolution verticale). **Ne jamais supprimer ou désactiver cette détection**, même si elle semble redondante avec `colliderect()`. Elle est essentielle pour gérer les cas où le déplacement vertical (`dy`) dépasse la hauteur d'un tile en une seule frame.

**Gestion des collisions existantes** : Avant d'appliquer le déplacement, l'algorithme vérifie si le personnage est déjà en collision avec un tile. Si c'est le cas, il détermine si la collision est principalement horizontale ou verticale en comparant les overlaps. Il ne sort le personnage que des collisions **principalement horizontales**, pas des collisions verticales légitimes (comme être au sol). 

**Filtrage directionnel des corrections horizontales** : Pour éviter les retours en arrière indésirables, les corrections horizontales (pré-correction ET correction post-déplacement) sont filtrées en fonction de la direction du mouvement quand le joueur est au sol :

- **Pré-correction** : Désactivée complètement quand le joueur est au sol (`is_on_ground = True`) ET se déplace horizontalement (`dx != 0`)
- **Correction post-déplacement** : Quand le joueur est au sol ET en mouvement horizontal :
  - **Approche "STEP UP"** (Solution naturelle et fluide) : Au lieu de bloquer ou d'ignorer les collisions avec les bords de plateforme, le système applique un **ajustement vertical automatique** qui fait "monter" le joueur sur le bord. Cette technique, classique dans les jeux de plateforme, élimine les retours en arrière et rend le mouvement beaucoup plus fluide et naturel.
  - **Détection du bord de plateforme** : Utiliser la position du joueur **AVANT** d'appliquer le déplacement horizontal (`dx`) :
    - Comparer le bas du rectangle de collision **AVANT déplacement** (`player_rect_before.bottom`) avec le haut du tile (`tile_top`)
    - Si `player_bottom_before <= tile_top + 12` → le joueur est près du bord d'une plateforme
    - **Tolérance de 12 pixels** : Compense l'offset de collision (`collision_offset_y = -4px`) + marge de sécurité
  - **Application du "step up"** :
    - Calculer le montant nécessaire : `step_up_amount = tile_top - new_rect_x.bottom + 1`
    - Si `0 < step_up_amount <= 5` pixels → appliquer le step up en montant le rectangle : `new_rect_x.y += step_up_amount`
    - **Limite de 5 pixels** : Évite les sauts verticaux trop importants qui sembleraient artificiels
    - Une fois le step up appliqué → **ne pas corriger horizontalement** (le joueur passe au-dessus du bord)
  - **Sinon** (pas de step up possible) → c'est un vrai mur vertical → **bloquer horizontalement normalement**
  - **⚠️ AVANTAGES du "step up"** :
    - ✅ **Mouvement fluide** : Le joueur "monte" naturellement sur les petits obstacles au lieu d'être bloqué
    - ✅ **Élimine les retours en arrière** : Plus besoin d'ignorer les collisions, on les résout intelligemment
    - ✅ **Gameplay naturel** : Comportement attendu dans les jeux de plateforme modernes
    - ✅ **Symétrique** : Fonctionne identiquement à gauche et à droite
    - ✅ **Robuste** : Utilise la position AVANT déplacement, donc non faussé par la vitesse

**Pourquoi une approche triple critère avec tolérances généreuses** : Le `collision_offset_y` (par défaut -4 pixels), l'élargissement dynamique des rectangles de collision, et surtout **la vitesse du personnage** rendent difficile l'utilisation d'un seul critère fiable. Quand le joueur se déplace vite, le déplacement `dx` est grand, et le rectangle peut pénétrer profondément dans un tile adjacent, ce qui fausse les calculs. La combinaison de trois tests indépendants avec des tolérances généreuses garantit une détection robuste :
- **Critère 1 (bas)** : Détecte directement si le joueur est posé sur le tile, même avec l'offset. Tolérance de 10px pour absorber les pénétrations dues aux vitesses élevées.
- **Critère 2 (centre)** : Détecte les cas où le joueur est clairement posé sur la plateforme (son centre est au-dessus du centre du tile). Tolérance de 10px pour les cas de vitesse élevée.
- **Critère 3 (overlap)** : Détecte les cas où le chevauchement vertical est important (>50% de la hauteur), indépendamment de la vitesse.
- **OR logique triple** : Il suffit qu'UN seul des trois critères soit vrai pour identifier une plateforme, ce qui rend la détection très permissive et élimine les faux négatifs (retours en arrière), même à haute vitesse.

Exemples :
- **Plateforme sous les pieds (vitesse normale)** : Le joueur marche dessus → bas proche du haut OU centre au-dessus OU overlap > 50% → collision ignorée ✓
- **Plateforme sous les pieds (vitesse élevée)** : Le joueur avance vite → pénètre dans tile adjacent, mais bas toujours proche OU overlap toujours > 50% → collision ignorée ✓
- **Mur latéral** : Le joueur heurte un mur → bas loin du haut ET centre à côté ET overlap < 50% → collision corrigée ✓

La correction reste appliquée normalement dans les cas suivants :
- Le joueur n'est pas au sol (en l'air) : utile pour corriger les collisions pendant le saut
- Le joueur est au sol mais ne se déplace pas (`dx == 0`) : utiliser la logique originale (sortir par le côté le plus proche)

Cela garantit que :
- Le personnage ne reste pas coincé dans un tile horizontalement quand il est en l'air
- Les collisions latérales sont correctement gérées pendant le saut
- **Le personnage ne recule JAMAIS en arrière quand il avance sur un bloc** : le filtrage basé sur le chevauchement vertical distingue robustement les plateformes des murs, indépendamment des offsets de collision
- Le personnage peut rester au sol (collision verticale) tout en se déplaçant horizontalement sans traverser les blocs
- Les corrections horizontales ne sont appliquées que pour les vrais murs (chevauchement vertical < 70% de la hauteur)

**Distinction horizontale/verticale** : Pour déterminer si une collision est principalement horizontale ou verticale, l'algorithme calcule les overlaps dans les deux directions et compare `min(overlap_left, overlap_right)` avec `min(overlap_top, overlap_bottom)`. Si l'overlap horizontal est plus petit que l'overlap vertical, la collision est considérée comme principalement horizontale et est corrigée horizontalement. Sinon, elle est laissée à la phase de résolution verticale.

**Filtrage des collisions arrière** : Pour améliorer le gameplay et éviter que le joueur soit bloqué par des obstacles situés derrière lui, les collisions horizontales avec des tiles à l'arrière du joueur (par rapport à sa direction de regard) sont ignorées. Cette logique s'applique uniquement aux collisions horizontales, pas aux collisions verticales (sol/plafond), pour garantir que le joueur peut toujours atterrir sur les plateformes et être bloqué par les plafonds, indépendamment de sa direction. La direction du joueur est déterminée par la propriété `current_direction` (`"left"` ou `"right"`), et la position relative du tile est comparée au centre horizontal du rectangle de collision du joueur pour déterminer si le tile est à l'arrière.

### Détection des blocs grimpables

Le système de collisions doit également détecter si le joueur est en collision avec un bloc grimpable (couche avec `is_background = true` et `is_climbable = true`) et mettre à jour la propriété `is_on_climbable` du joueur.

#### Récupération des blocs grimpables

```python
def _get_climbable_layers(self) -> List[Layer]:
    """Récupère toutes les couches grimpables (depth 2 avec is_background = true et is_climbable = true).
    
    Returns:
        Liste des couches grimpables
    """
    return [
        layer for layer in self.parallax_system._layers
        if layer.depth == 2
        and (not hasattr(layer, 'alpha') or layer.alpha > 0)
        and (not hasattr(layer, 'is_hidden') or not layer.is_hidden)
        and hasattr(layer, 'is_background') and layer.is_background
        and hasattr(layer, 'is_climbable') and layer.is_climbable
    ]

def get_climbable_rects(self, camera_x: float) -> List[pygame.Rect]:
    """Récupère tous les rectangles de collision des blocs grimpables visibles.
    
    Args:
        camera_x: Position horizontale de la caméra
        
    Returns:
        Liste des rectangles de collision des blocs grimpables
    """
    climbable_layers = self._get_climbable_layers()
    climbable_rects = []
    
    for layer in climbable_layers:
        # Utiliser la même logique que get_collision_rects() pour extraire les rectangles
        # mais uniquement pour les couches grimpables
        layer_rects = self._extract_solid_rects_from_surface(
            layer.surface, layer.name, tile_size=64
        )
        
        # Convertir les rectangles en coordonnées monde
        for rect in layer_rects:
            world_x = rect.x + camera_x * (1.0 - layer.scroll_speed)
            world_rect = pygame.Rect(world_x, rect.y, rect.width, rect.height)
            climbable_rects.append(world_rect)
    
    return climbable_rects
```

#### Détection de collision avec un bloc grimpable

```python
def check_climbable_collision(self, player_rect: pygame.Rect, camera_x: float, player: Player) -> bool:
    """Vérifie si le personnage est en collision avec un bloc grimpable.
    
    Met à jour player.is_on_climbable en fonction du résultat.
    
    Args:
        player_rect: Rectangle de collision du personnage dans l'espace du monde
        camera_x: Position horizontale de la caméra
        player: Référence au personnage pour mettre à jour is_on_climbable
        
    Returns:
        True si le personnage est en collision avec un bloc grimpable, False sinon
    """
    climbable_rects = self.get_climbable_rects(camera_x)
    
    # Vérifier si le joueur intersecte avec un bloc grimpable
    is_on_climbable = False
    for climbable_rect in climbable_rects:
        if player_rect.colliderect(climbable_rect):
            is_on_climbable = True
            break
    
    # Mettre à jour la propriété du joueur
    player.is_on_climbable = is_on_climbable
    
    return is_on_climbable
```

#### Intégration dans la boucle principale

Dans `main.py`, la détection des blocs grimpables doit être effectuée à chaque frame, après la résolution des collisions :

```python
# Dans la boucle principale
player_rect = player.get_collision_rect()

# Résoudre les collisions normales
corrected_dx, corrected_dy, is_on_ground = collision_system.resolve_collision(
    player_rect, dx, dy, player, camera_x
)

# Vérifier si le joueur est sur un bloc grimpable
collision_system.check_climbable_collision(player_rect, camera_x, player)

# Mettre à jour l'état au sol
player.is_on_ground = is_on_ground
```

### Intégration avec le système de parallaxe

#### Récupération des tiles solides

Le système de collisions doit accéder aux couches de depth 2 du `ParallaxSystem` :

```python
def _get_solid_layers(self) -> List[Layer]:
    """Récupère toutes les couches de depth 2 (tiles solides).
    
    Exclut les layers masquées (opacité = 0 ou attribut is_hidden = True)
    et les layers avec is_background = True pour éviter de vérifier les collisions
    avec des sprites invisibles ou des décors non solides.
    
    Returns:
        Liste des couches de depth 2 qui ne sont pas masquées et qui sont solides
    """
    if not self._collision_layers:
        # Filtrer les layers de depth 2 qui ne sont pas masquées et qui sont solides
        self._collision_layers = [
            layer for layer in self.parallax_system._layers
            if layer.depth == 2
            and (not hasattr(layer, 'alpha') or layer.alpha > 0)
            and (not hasattr(layer, 'is_hidden') or not layer.is_hidden)
            and (not hasattr(layer, 'is_background') or not layer.is_background)
        ]
    return self._collision_layers
```

#### Conversion des couches en rectangles de collision

Pour chaque couche de depth 2 :

1. **Extraction des rectangles de collision** :
   - Les rectangles sont extraits depuis la surface de la layer en analysant les pixels non-transparents
   - L'algorithme trouve la **position exacte** des sprites (pas alignée sur des multiples de tile_size) pour éviter les décalages visuels
   - Pour chaque colonne de `tile_size` pixels, l'algorithme :
     - Échantillonne tous les 8 pixels verticalement pour trouver rapidement la zone contenant des pixels solides
     - Effectue une recherche fine pour trouver le premier pixel solide exact
     - Crée un rectangle de collision de `tile_size x tile_size` à cette position exacte
   - Les rectangles sont mis en cache par layer pour éviter les recalculs

2. **Pour les lignes complètes (`[layers]`)** :
   - La couche couvre toute la hauteur de l'écran
   - La position horizontale dépend de `layer.offset_x` (position de défilement)
   - La largeur est `layer.surface.get_width()`
   - Si `repeat = True`, la couche se répète horizontalement

3. **Pour les sprites individuels (`[[sprites]]`)** :
   - La position verticale est définie par `y_offset` (en pixels depuis le haut de l'écran)
   - La position horizontale dépend de `layer.offset_x` et de la position du sprite dans la séquence répétée
   - Les dimensions sont celles du sprite (64x64 par défaut)
   - Si `repeat = True`, le sprite se répète horizontalement
   - **Important** : Les rectangles de collision sont créés à la position exacte où se trouvent les sprites dans la surface (y_offset), pas alignés sur des multiples de 64

#### Gestion du défilement

Les tiles se déplacent avec la caméra selon leur `scroll_speed`. La position dans l'espace du monde est calculée comme suit :

```python
world_x = tile_screen_x + camera_x * (1.0 - layer.scroll_speed)
```

Pour depth 2, `scroll_speed = 1.0`, donc les tiles se déplacent à la même vitesse que la caméra (position fixe dans l'espace du monde).

#### Suppression dynamique des collisions

Le système de collisions doit supporter la suppression dynamique des collisions lorsqu'un sprite est masqué via le système d'événements (spécification 11). Lorsqu'un événement `sprite_hide` est déclenché et que `remove_collisions = true`, le système d'événements appelle les méthodes suivantes :

1. **`remove_layer_collisions(layer_name: str) -> None`** :
   - Supprime les rectangles de collision d'une layer spécifique du cache `_solid_rects_cache`
   - Si la layer n'existe pas dans le cache, la méthode ne fait rien (pas d'erreur)
   - Cette méthode est appelée une fois que le fade out est terminé (opacité = 0)

2. **`remove_layer_from_collisions(layer: Layer) -> None`** :
   - Retire une layer de la liste mise en cache `_collision_layers`
   - Réinitialise le cache `_collision_layers` pour forcer un recalcul lors du prochain appel à `_get_solid_layers()`
   - Cette méthode garantit que la layer masquée ne sera plus considérée comme solide lors des prochaines détections de collision

**Implémentation** :

```python
def remove_layer_collisions(self, layer_name: str) -> None:
    """Supprime les rectangles de collision d'une layer du cache.
    
    Utilisé par le système d'événements lors du masquage de sprites
    pour retirer les collisions d'une layer qui n'est plus visible.
    
    Args:
        layer_name: Nom de la layer dont les collisions doivent être supprimées
    """
    if layer_name in self._solid_rects_cache:
        del self._solid_rects_cache[layer_name]

def remove_layer_from_collisions(self, layer: Layer) -> None:
    """Retire une layer de la liste des layers de collision.
    
    Utilisé par le système d'événements lors du masquage de sprites
    pour exclure une layer des détections de collision futures.
    
    Args:
        layer: La layer à retirer des collisions
    """
    # Réinitialiser le cache pour forcer un recalcul
    self._collision_layers = []
    # La prochaine fois que _get_solid_layers() sera appelée,
    # elle recalculera la liste sans la layer masquée
```

**Intégration avec le système d'événements** :

Lorsqu'un événement `sprite_hide` est déclenché et que le fade out est terminé :
1. Le système d'événements appelle `collision_system.remove_layer_collisions(layer.name)` pour chaque layer masquée
2. Le système d'événements appelle `collision_system.remove_layer_from_collisions(layer)` pour retirer la layer de la liste des layers de collision
3. Les prochaines détections de collision n'incluront plus cette layer, permettant au joueur de traverser l'emplacement où se trouvait le sprite

**Note importante** : La suppression des collisions peut être inversée via un événement `sprite_show` (voir spécification 11). Une fois qu'une layer est retirée des collisions, elle peut être réintégrée si un événement `sprite_show` avec `restore_collisions = true` est déclenché.

#### Restauration dynamique des collisions

Le système de collisions doit supporter la restauration dynamique des collisions lorsqu'un sprite est affiché via le système d'événements (spécification 11). Lorsqu'un événement `sprite_show` est déclenché et que `restore_collisions = true`, le système d'événements appelle les méthodes suivantes :

1. **`restore_layer_collisions(layer: Layer) -> None`** :
   - Recalcule les rectangles de collision de la layer et les ajoute au cache `_solid_rects_cache`
   - Si la layer existe déjà dans le cache, elle est mise à jour avec les nouveaux rectangles
   - Cette méthode est appelée une fois que le fade in est terminé (opacité = 255)
   - Utilise la même logique d'extraction que lors du chargement initial du niveau

2. **`add_layer_to_collisions(layer: Layer) -> None`** :
   - Réintègre une layer dans la liste mise en cache `_collision_layers`
   - Réinitialise le cache `_collision_layers` pour forcer un recalcul lors du prochain appel à `_get_solid_layers()`
   - Cette méthode garantit que la layer affichée sera considérée comme solide lors des prochaines détections de collision

**Implémentation** :

```python
def restore_layer_collisions(self, layer: Layer) -> None:
    """Restaure les rectangles de collision d'une layer dans le cache.
    
    Utilisé par le système d'événements lors de l'affichage de sprites
    pour réintégrer les collisions d'une layer qui redevient visible.
    
    Args:
        layer: La layer dont les collisions doivent être restaurées
    """
    # Recalculer les rectangles de collision (même logique que lors du chargement)
    solid_rects = self._extract_solid_rects(layer)
    self._solid_rects_cache[layer.name] = solid_rects

def add_layer_to_collisions(self, layer: Layer) -> None:
    """Réintègre une layer dans la liste des layers de collision.
    
    Utilisé par le système d'événements lors de l'affichage de sprites
    pour inclure une layer dans les détections de collision futures.
    
    Args:
        layer: La layer à réintégrer dans les collisions
    """
    # Réinitialiser le cache pour forcer un recalcul
    self._collision_layers = []
    # La prochaine fois que _get_solid_layers() sera appelée,
    # elle recalculera la liste avec la layer restaurée
```

**Intégration avec le système d'événements** :

Lorsqu'un événement `sprite_show` est déclenché et que le fade in est terminé :
1. Le système d'événements appelle `collision_system.restore_layer_collisions(layer)` pour chaque layer affichée
2. Le système d'événements appelle `collision_system.add_layer_to_collisions(layer)` pour réintégrer la layer dans la liste des layers de collision
3. Les prochaines détections de collision incluront à nouveau cette layer, permettant au joueur d'interagir avec le sprite restauré

**Note importante** : La restauration des collisions nécessite que la layer soit toujours présente dans le système (elle n'a pas été supprimée, seulement masquée). Si une layer a été complètement supprimée du système, elle ne peut pas être restaurée via `sprite_show`.

#### Extraction optimisée des rectangles de collision

L'extraction des rectangles de collision depuis les surfaces des layers est optimisée pour les performances :

1. **Cache** : Les rectangles sont calculés une seule fois par layer et mis en cache dans `_solid_rects_cache`, indexé par le nom de la layer.

2. **Algorithme d'extraction** :
   - Pour chaque colonne de `tile_size` pixels (64x64 par défaut) :
     - Échantillonne tous les 8 pixels verticalement pour trouver rapidement la zone contenant des pixels solides
     - Effectue une recherche fine (pixel par pixel) dans la zone trouvée pour déterminer la position exacte du premier pixel solide
     - Crée un rectangle de collision de `tile_size x tile_size` à cette position exacte
   - Cette approche garantit que les rectangles sont positionnés exactement où se trouvent les sprites (y_offset), évitant les décalages visuels

3. **Performance** : L'échantillonnage réduit significativement le nombre de pixels à analyser, et le cache évite tout recalcul après la première extraction.

4. **Invalidation du cache** : Le cache peut être invalidé dynamiquement lorsque des sprites sont masqués ou affichés via le système d'événements. Les rectangles de collision d'une layer masquée sont retirés du cache via `remove_layer_collisions()`, et la layer est exclue des détections futures via `remove_layer_from_collisions()`. Lorsqu'une layer est affichée via `sprite_show`, les collisions sont restaurées via `restore_layer_collisions()` et la layer est réintégrée via `add_layer_to_collisions()`.

## Implémentation

### Structure de fichiers

```
src/moteur_jeu_presentation/
├── physics/
│   ├── __init__.py
│   └── collision.py          # Classe CollisionSystem
```

### Dépendances

Aucune nouvelle dépendance n'est requise. Le système utilise :
- `pygame` (déjà présent)
- `moteur_jeu_presentation.rendering.parallax.ParallaxSystem` (existant)
- `moteur_jeu_presentation.entities.player.Player` (existant)

### Exemple d'utilisation

```python
from moteur_jeu_presentation.physics import CollisionSystem
from moteur_jeu_presentation.entities import Player
from moteur_jeu_presentation.levels import LevelLoader

# Initialisation
level_loader = LevelLoader(Path("sprite"))
level_config = level_loader.load_level(Path("levels/niveau_plateforme.niveau"))
parallax_system, layers_by_tag = level_loader.create_parallax_layers(
    level_config,
    SCREEN_WIDTH,
    SCREEN_HEIGHT
)

# Créer le système de collisions
collision_system = CollisionSystem(parallax_system, SCREEN_WIDTH, SCREEN_HEIGHT)

# Initialiser le personnage
player = Player(
    x=SCREEN_WIDTH / 2,
    y=SCREEN_HEIGHT / 2,
    sprite_sheet_path="sprite/walk.png",
    sprite_width=64,
    sprite_height=64,
    animation_speed=10.0,
)

# Dans la boucle de jeu
def update(dt: float, camera_x: float) -> None:
    keys = pygame.key.get_pressed()
    
    # Appliquer la gravité (si le personnage n'est pas au sol)
    if not player.is_on_ground:
        player.apply_gravity(dt)
    
    # Calculer le déplacement prévu
    dx = 0.0
    dy = 0.0
    
    # Déplacement horizontal (contrôlé par le joueur)
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        dx -= player.speed * dt
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        dx += player.speed * dt
    
    # Déplacement vertical (gravité + contrôle optionnel)
    dy = player.velocity_y * dt  # La gravité a déjà été appliquée à velocity_y
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        # Saut ou mouvement vers le haut (si au sol)
        if player.is_on_ground:
            # TODO: Implémenter le saut dans une évolution future
            pass
    
    # Obtenir le rectangle de collision du personnage
    player_rect = player.get_collision_rect()
    
    # Résoudre les collisions
    corrected_dx, corrected_dy, is_on_ground = collision_system.resolve_collision(
        player_rect, dx, dy, player, camera_x
    )
    
    # Mettre à jour l'état au sol
    player.is_on_ground = is_on_ground
    
    # Appliquer le déplacement corrigé
    player.x += corrected_dx
    player.y += corrected_dy
    
    # Mettre à jour l'animation
    player._handle_movement(keys, dt)  # Pour l'animation uniquement
    player._update_animation(dt)
```

### Intégration dans `main.py`

```python
# Créer le système de collisions après le système de parallaxe
collision_system = CollisionSystem(parallax_system, SCREEN_WIDTH, SCREEN_HEIGHT)

# Dans la boucle de jeu, modifier la méthode update du joueur
# pour intégrer les collisions et la gravité
def update_game(dt: float, camera_x: float) -> None:
    keys = pygame.key.get_pressed()
    
    # Appliquer la gravité (si le personnage n'est pas au sol)
    if not player.is_on_ground:
        player.apply_gravity(dt)
    
    # Calculer le déplacement prévu
    dx = 0.0
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        dx -= player.speed * dt
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        dx += player.speed * dt
    
    # Le déplacement vertical est géré par la gravité
    dy = player.velocity_y * dt
    
    # Résoudre les collisions
    player_rect = player.get_collision_rect()
    corrected_dx, corrected_dy, is_on_ground = collision_system.resolve_collision(
        player_rect, dx, dy, player, camera_x
    )
    
    # Mettre à jour l'état au sol
    player.is_on_ground = is_on_ground
    
    # Appliquer le déplacement
    player.x += corrected_dx
    player.y += corrected_dy
    
    # Mettre à jour l'animation
    player._update_animation(dt)
    
    # Mettre à jour la caméra
    camera_x = player.x - SCREEN_WIDTH / 2
    parallax_system.update(camera_x, dt)
```

## Gestion des erreurs

Le système doit gérer les erreurs suivantes :

- **ParallaxSystem invalide** : Vérifier que le système de parallaxe contient des couches
- **Dimensions invalides** : Vérifier que les dimensions de collision sont positives
- **Position hors limites** : Gérer les cas où le personnage sort des limites du monde
- **Layer introuvable dans le cache** : Lors de la suppression des collisions, si une layer n'existe pas dans le cache, la méthode `remove_layer_collisions()` ne doit pas lever d'erreur (comportement silencieux)

## Performance

### Optimisations implémentées

1. **Culling spatial** : Ne vérifier que les tiles visibles à l'écran (avec une marge de sécurité)
2. **Mise en cache des couches** : Mettre en cache la liste des couches de depth 2 dans `_collision_layers`
3. **Mise en cache des rectangles de collision** : Les rectangles de collision sont calculés une seule fois par layer et stockés dans `_solid_rects_cache`. Le cache est indexé par le nom de la layer, ce qui permet de réutiliser les rectangles calculés sans recalcul.
4. **Extraction optimisée** : L'extraction des rectangles utilise un échantillonnage (tous les 8 pixels verticalement) pour trouver rapidement les zones contenant des pixels solides, puis une recherche fine pour déterminer la position exacte. Cela évite de scanner tous les pixels de la surface.
5. **Calculs optimisés** : Utiliser les méthodes natives de pygame pour les tests de collision (AABB)
6. **Suppression dynamique des collisions** : Les collisions peuvent être supprimées dynamiquement lors du masquage de sprites, évitant de vérifier des collisions inutiles pour des sprites qui ne sont plus visibles

### Métriques de performance

- **Temps d'extraction initial** : ~2-3ms pour une surface complète (une seule fois grâce au cache)
- **Temps de récupération depuis le cache** : < 0.1ms pour récupérer les rectangles mis en cache
- **Temps de détection** : < 0.1ms pour un niveau avec 100 tiles (grâce au cache)
- **Temps de résolution** : < 0.5ms par collision

## Tests

### Tests unitaires à implémenter

1. **Test de détection de collision** : Vérifier que les collisions sont correctement détectées
2. **Test de résolution de collision** : Vérifier que les collisions sont correctement résolues
3. **Test de collisions latérales** : Vérifier que le personnage ne peut pas traverser les tiles par la gauche ou la droite
4. **Test de collisions verticales** : Vérifier que le personnage ne peut pas traverser les tiles par le haut ou le bas
5. **Test avec tiles répétés** : Vérifier le comportement avec des tiles qui se répètent
6. **Test avec sprites individuels** : Vérifier le comportement avec des sprites individuels positionnés
7. **Test de performance** : Vérifier que les performances sont acceptables

### Exemple de test

```python
import pytest
import pygame
from moteur_jeu_presentation.physics import CollisionSystem
from moteur_jeu_presentation.rendering import ParallaxSystem, Layer

@pytest.fixture
def pygame_init():
    """Initialise pygame pour les tests."""
    pygame.init()
    yield
    pygame.quit()

def test_collision_detection(pygame_init):
    """Test la détection de collision."""
    # Créer un système de parallaxe avec une couche de depth 2
    parallax = ParallaxSystem(1280, 720)
    
    # Créer une surface de tile solide
    tile_surface = pygame.Surface((64, 64))
    tile_surface.fill((255, 255, 255))  # Tile blanc (solide)
    
    # Créer une couche de depth 2
    layer = Layer(
        name="test_tile",
        depth=2,
        scroll_speed=1.0,
        surface=tile_surface,
        repeat=False
    )
    parallax.add_layer(layer)
    
    # Créer le système de collisions
    collision_system = CollisionSystem(parallax, 1280, 720)
    
    # Créer un rectangle de personnage qui entre en collision
    player_rect = pygame.Rect(32, 32, 64, 64)
    
    # Vérifier la collision
    collision = collision_system.check_collision(player_rect, 0.0)
    assert collision is not None
```

## Contraintes et considérations

### Limitations

- **Collisions rectangulaires uniquement** : Le système utilise des rectangles AABB, pas de collisions pixel-perfect
- **Tiles de depth 2 uniquement** : Seuls les tiles de depth 2 sont considérés comme solides, à l'exception de ceux avec `is_background = true` qui sont exclus des collisions
- **Gravité simple** : La gravité est constante et unidirectionnelle (vers le bas uniquement)

### Pièges courants

#### La collision avec le plafond se déclenche trop tôt

**Problème** : Le personnage est détecté en collision avec le plafond un peu trop tôt, avant que le sprite visuel ne touche réellement le plafond.

**Cause** : Le rectangle de collision a la même hauteur que le sprite, ce qui peut causer des collisions prématurées si le sprite a des éléments qui dépassent en haut (comme des cheveux) ou si le rectangle de collision n'est pas parfaitement aligné.

**Solution** : Réduire légèrement la hauteur du rectangle de collision (par exemple de 4 pixels) pour éviter les collisions prématurées. Le bas du rectangle de collision doit rester aligné avec le bas du sprite pour maintenir la cohérence visuelle.

**Implémentation** :
- Définir `collision_height = sprite_height - 6.0` dans `__init__()` (valeur ajustable selon les besoins)
- Définir `collision_width = sprite_width - 40.0` pour créer une marge horizontale de 20 pixels de chaque côté (suffisante pour l’alignement avec les tiles de depth 2)
- Définir `collision_offset_y = -4.0` pour que le bas de la hitbox soit légèrement au-dessus du bas du sprite (pieds visuellement plus proches du sol)
- La formule dans `get_collision_rect()` garantit que le bas reste aligné : `collision_y = y + sprite_height/2 - collision_height - 4`
- Utiliser `round()` au lieu de `int()` pour l'arrondi dans `get_collision_rect()` pour éviter les décalages dus à l'arrondi
- **IMPORTANT** : Utiliser `round()` de manière cohérente pour TOUS les rectangles de collision (joueur ET tiles) dans `get_collision_rects()` pour éviter les décalages dus à des arrondis incohérents

**Note** : Si le décalage persiste, ajuster la valeur de réduction (par exemple 4, 6, ou 8 pixels) selon les besoins visuels et la taille des sprites.

Cela permet au personnage de s'approcher un peu plus du plafond avant que la collision ne se déclenche, donnant une sensation de gameplay plus naturelle.

#### Décalage dû à des arrondis incohérents

**Problème** : Il y a un décalage visuel entre le sprite du joueur et les tiles, même après avoir ajusté la hauteur du rectangle de collision.

**Cause** : Les rectangles de collision des tiles utilisent `int()` pour l'arrondi alors que le rectangle du joueur utilise `round()`. Cette incohérence peut créer des décalages d'un pixel.

**Solution** : Utiliser `round()` de manière cohérente pour TOUS les rectangles de collision, à la fois pour le joueur et pour les tiles.

**Implémentation** :
- Dans `get_collision_rect()` du joueur : utiliser `round()` pour toutes les coordonnées, appliquer `collision_offset_y = -4.0` et `collision_width = sprite_width - 40.0`

### Plateformes mobiles déclenchées par `sprite_move`

L'événement `sprite_move` (voir spécification 11) anime certaines couches de depth 2. Le système de collisions doit intégrer ces translations afin de transporter correctement le joueur et les PNJ.

#### Flux de données

1. `EventTriggerSystem` appelle `collision_system.on_layer_translated(layer, delta_x, delta_y)` à chaque frame déplacée.
2. `collision_system` maintient une liste `moving_platforms` contenant :
   - `layer_id` ainsi que la référence directe à la `Layer` déplacée (pour recalculer les rectangles à la demande)
   - `rect` mis à jour après translation
   - `frame_delta` (float tuple)
   - `passengers` actuellement attachés

#### Détection des passagers

- Un passager potentiel est toute entité avec un rectangle de collision détecté **sur la face supérieure** de la plateforme :
- Condition verticale : `-4 <= entity_rect.bottom - platform_rect.top <= 12` (tolérance suffisamment large pour absorber les arrondis sans accrocher des entités éloignées)
- Condition horizontale : overlap horizontal ≥ 25% de la largeur de l'entité (permet de détecter rapidement les pieds même s'ils ne couvrent pas tout le bloc)
  - Condition de vitesse : `entity.velocity_y >= 0` (l'entité n'est pas en train de sauter vers le haut)
- **Compensation du delta** : Lors de la détection, la plateforme a déjà été déplacée (`world_x/y_offset` mis à jour par `EventTriggerSystem`) mais l'entité n'a pas encore reçu le delta. Le système **soustrait le `frame_delta`** des coordonnées de la plateforme pour détecter si l'entité était sur la plateforme **avant** le déplacement de cette frame. Cela garantit que les entités immobiles sont correctement attachées dès le début du mouvement.
- Dès que ces conditions sont vraies, l'entité est marquée `attached_platform = layer_id` et `passengers[layer_id]` est mis à jour.
- La vérification est relancée à **chaque frame** pour toutes les plateformes en mouvement : même si l'entité est immobile (pas de déplacement vertical), le moteur détecte qu'elle repose déjà sur la plateforme et l'attache immédiatement lorsque le `sprite_move` démarre. Cette attache ne dépend pas d'un flag `is_on_ground` préexistant : le moteur force `is_on_ground = True` pour chaque passager fixé afin d'empêcher la gravité de le faire chuter.

#### Application du déplacement

- Tant que `attached_platform` est défini :
  - **Mouvement horizontal indépendant** : Le joueur peut se déplacer horizontalement (X) en utilisant les touches de direction, même lorsqu'il est attaché à une plateforme mobile. Le mouvement horizontal du joueur est traité normalement par le système de collisions.
  - **Mouvement de la plateforme** : Le déplacement de la plateforme (à la fois `delta_x` et `delta_y`) est appliqué à l'entité attachée. Le joueur suit donc la plateforme en X et Y, tout en pouvant se déplacer horizontalement de manière indépendante via les touches. Cela permet au joueur de marcher sur la plateforme tout en étant transporté par elle.
  - Le déplacement de la plateforme est ajouté après la résolution classique des collisions : `entity.x += delta_x` et `entity.y += delta_y`
  - `is_on_ground` reste `True` pendant toute la durée du mouvement pour éviter que la gravité ne fasse chuter l'entité.
- La même translation (X et Y) est appliquée à tous les passagers de la plateforme durant la frame, tout en leur permettant de se déplacer horizontalement de manière indépendante.

#### Détachement et blocage

- Une entité est relâchée lorsque :
  - Le mouvement est terminé (`remaining_distance <= 0`)
  - L'entité saute (`velocity_y < 0`) ou quitte la zone d'overlap
  - Une collision externe (mur, autre plateforme) empêche l'application complète du delta (dans ce cas, la composante bloquée est annulée et l'entité reste attachée si l'overlap supérieur existe encore).
- **Cohérence avec la détection** : La vérification de détachement doit utiliser les **mêmes tolérances** et la **même compensation du delta** que la détection initiale (`_is_entity_on_platform_surface` + ajustement des coordonnées). Sinon, l'entité serait attachée puis immédiatement détachée.
- Dès le détachement, le contrôle standard est rendu (entrées réactivées) et `attached_platform` est remis à `None`.

#### Collisions forcées

- Si la plateforme remonte sous une entité immobile, la détection d'overlap supérieur la capture et l'attache immédiatement : la règle “ne peut plus bouger et suit le même déplacement que le sprite” est donc respectée même si le joueur n'était pas déjà sur la plateforme.
- Les plateformes mobiles n'affectent pas les entités situées sur leurs faces latérales ou inférieures : seules les collisions sur la face supérieure déclenchent le verrouillage.

### Évolutions futures possibles

- Support de collisions pixel-perfect pour des formes complexes
- Support de tiles solides à d'autres profondeurs
- **Ajout du saut** : Permettre au personnage de sauter pour contrer la gravité
- Support de pentes et de surfaces inclinées
- Système de physique plus avancé (impulsions, forces, etc.)
- Collisions entre entités (joueur, ennemis, objets)
- Gravité variable selon les zones du niveau

## Références

- Bonnes pratiques : `bonne_pratique.md`
- Spécification système de couches : `spec/1-systeme-de-couches-2d.md`
- Spécification personnage principal : `spec/2-personnage-principal.md`
- Spécification système de fichier niveau : `spec/3-systeme-de-fichier-niveau.md`
- Spécification système de gestion de l'avancement : `spec/11-systeme-gestion-avancement-niveau.md` (pour l'intégration avec le système d'événements)
- Documentation Pygame : [Pygame Rect](https://www.pygame.org/docs/ref/rect.html)

---

**Date de création** : 2024  
**Statut** : ✅ Implémenté

