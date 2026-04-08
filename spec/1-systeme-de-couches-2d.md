# 1 - Système de couches 2D pour jeu de plateforme

## Contexte

Cette spécification définit l'architecture technique pour un système de rendu multi-couches (parallax scrolling) pour un jeu de plateforme 2D en vue de profil (side-scrolling).

## Objectifs

- Implémenter un système de 4 couches de profondeur pour créer un effet de parallaxe
- Gérer le rendu des différentes couches dans le bon ordre
- Permettre le défilement indépendant de chaque couche pour un effet de profondeur
- Optimiser les performances de rendu

## Architecture

### Couches de profondeur

Le jeu utilise 4 couches distinctes, du plus éloigné au plus proche :

1. **Background (Arrière-plan)** : Couche la plus éloignée, défile le plus lentement
2. **Premier fond** : Couche intermédiaire arrière, défile à vitesse moyenne-lente
3. **Éléments de gameplay** : Couche principale où évolue le personnage, défile à la vitesse de la caméra
4. **Premier plan (Foreground)** : Couche la plus proche, défile le plus rapidement

### Vue du jeu

- **Type de vue** : Vue de profil (side-scrolling)
- **Orientation** : Défilement horizontal principal
- **Perspective** : 2D plate, pas de perspective 3D

## Spécifications techniques

### Structure des données

#### Classe `Layer`

```python
class Layer:
    """Représente une couche de rendu dans le système de parallaxe."""
    
    def __init__(
        self,
        name: str,
        depth: int,
        scroll_speed: float,
        surface: pygame.Surface,
        repeat: bool = True,
        world_x_offset: float = 0.0,
    ) -> None:
        """
        Args:
            name: Nom identifiant de la couche
            depth: Profondeur de la couche (0 = background, 3 = foreground)
            scroll_speed: Multiplicateur de vitesse de défilement (0.0 à 1.0+)
            surface: Surface pygame contenant l'image de la couche
            repeat: Si True, la couche se répète horizontalement
            world_x_offset: Offset horizontal dans l'espace du monde (utile pour les sprites avec x_offset négatif)
        """
```

**Propriétés** :
- `name: str` : Identifiant unique de la couche
- `depth: int` : Profondeur (0=background, 1=premier fond, 2=gameplay, 3=foreground)
- `scroll_speed: float` : Multiplicateur de vitesse (ex: 0.2 pour background, 1.0 pour gameplay)
- `surface: pygame.Surface` : Image de la couche
- `repeat: bool` : Répétition horizontale pour les couches décoratives
- `offset_x: float` : Position de défilement actuelle
- `world_x_offset: float` : Offset horizontal de la surface dans l'espace du monde (permet de positionner correctement les couches dont les sprites ont un `x_offset` négatif)
- `alpha: int` : Opacité de la couche (0-255, défaut: 255 = opaque). Utilisé pour le masquage progressif de sprites via le système d'événements (spécification 11)
- `is_hidden: bool` : Indique si la couche est masquée (défaut: False). Utilisé par le système d'événements pour marquer les layers complètement masquées

#### Classe `ParallaxSystem`

```python
class ParallaxSystem:
    """Gestionnaire du système de parallaxe multi-couches."""
    
    def __init__(self, screen_width: int, screen_height: int) -> None:
        """
        Args:
            screen_width: Largeur de l'écran de rendu
            screen_height: Hauteur de l'écran de rendu
        """
```

**Méthodes principales** :
- `add_layer(layer: Layer) -> None` : Ajoute une couche au système
- `update(camera_x: float, dt: float) -> None` : Met à jour les positions des couches
- `draw(surface: pygame.Surface) -> None` : Dessine toutes les couches dans l'ordre
- `get_layer_by_name(name: str) -> Optional[Layer]` : Récupère une couche par son nom

**Note sur l'opacité** : La classe `Layer` doit supporter l'opacité pour permettre le masquage progressif de sprites via le système d'événements (spécification 11). L'opacité est appliquée lors du rendu via `surface.set_alpha(alpha)` avant le `blit()`. Les layers avec `alpha = 0` ou `is_hidden = True` sont considérées comme masquées et leurs collisions peuvent être supprimées (spécification 4).

### Vitesses de défilement recommandées

| Couche | Depth | Scroll Speed | Description |
|--------|-------|--------------|-------------|
| Background | 0 | 0.1 - 0.3 | Défile très lentement pour effet de lointain |
| Premier fond | 1 | 0.4 - 0.6 | Défile lentement, légèrement plus rapide que background |
| Gameplay | 2 | 1.0 | Défile à la vitesse de la caméra (référence) |
| Foreground | 3 | 1.2 - 1.5 | Défile plus vite pour effet de proximité |

### Ordre de rendu

Les couches doivent être rendues dans l'ordre suivant (du fond vers l'avant) :

1. Background (depth 0)
2. Premier fond (depth 1)
3. Éléments de gameplay (depth 2)
4. Foreground (depth 3)

### Gestion de la caméra

- La couche "gameplay" (depth 2) suit directement la position de la caméra
- Les autres couches utilisent un multiplicateur basé sur leur `scroll_speed`
- Calcul de position : `layer_offset = camera_x * layer.scroll_speed`

### Répétition des couches

Pour les couches décoratives (background, premier fond, foreground) :
- Si `repeat = True`, la couche se répète horizontalement
- Calculer le nombre de répétitions nécessaires : `ceil(screen_width / layer_width) + 2`
- Gérer le wrapping pour un défilement infini

## Implémentation

### Structure de fichiers

```
src/moteur_jeu_presentation/
├── rendering/
│   ├── __init__.py
│   ├── layer.py          # Classe Layer
│   └── parallax.py       # Classe ParallaxSystem
```

### Exemple d'utilisation

```python
from rendering.parallax import ParallaxSystem, Layer
import pygame

# Initialisation
parallax = ParallaxSystem(screen_width=1280, screen_height=720)

# Charger les images
bg_image = asset_manager.load_image("background.png")
first_bg_image = asset_manager.load_image("first_background.png")
fg_image = asset_manager.load_image("foreground.png")

# Créer les couches
background = Layer(
    name="background",
    depth=0,
    scroll_speed=0.2,
    surface=bg_image,
    repeat=True
)

first_background = Layer(
    name="first_background",
    depth=1,
    scroll_speed=0.5,
    surface=first_bg_image,
    repeat=True
)

foreground = Layer(
    name="foreground",
    depth=3,
    scroll_speed=1.3,
    surface=fg_image,
    repeat=True
)

# Ajouter les couches
parallax.add_layer(background)
parallax.add_layer(first_background)
parallax.add_layer(foreground)

# Dans la boucle de jeu
def update(dt: float, camera_x: float) -> None:
    parallax.update(camera_x, dt)

def draw(screen: pygame.Surface) -> None:
    screen.fill((0, 0, 0))  # Couleur de fond
    parallax.draw(screen)
    # Dessiner ensuite les éléments de gameplay (depth 2)
    game_entities.draw(screen)
```

## Contraintes et considérations

### Performance

- Utiliser `pygame.Surface.convert()` ou `convert_alpha()` pour optimiser le rendu
- Limiter le nombre de couches actives simultanément
- Utiliser le clipping pour éviter de dessiner hors écran
- Mettre en cache les surfaces répétées
- Pré-calculer les sous-listes de couches par profondeur (par exemple `layers_back` pour depth ≤ 1 et `layers_front` pour depth ≥ 2) juste après le chargement du niveau, afin d'éviter de filtrer les couches à chaque frame.
- **IMPORTANT - Anti-saccades** : Arrondir toutes les positions de rendu à des entiers avant d'appeler `blit()`. Pygame attend des entiers pour les positions, et l'arrondi automatique peut causer des saccades visuelles. Utiliser `int(round(x_float))` pour convertir les positions flottantes en entiers.
- Mettre en cache les valeurs statiques (largeurs, hauteurs, offsets) dans la classe `Layer` pour éviter les recalculs à chaque frame. Ces valeurs ne changent jamais après l'initialisation.

### Dimensions des images

- Les images de couches doivent avoir une hauteur >= `screen_height`
- Pour les couches répétables, la largeur peut être modulaire (tileable)
- Format recommandé : PNG avec transparence pour les couches avant-plan

### Gestion mémoire

- Charger les images une seule fois via `AssetManager`
- Réutiliser les surfaces pour les répétitions
- Ne pas créer de nouvelles surfaces à chaque frame

## Tests

### Tests unitaires à implémenter

1. **Test d'ajout de couches** : Vérifier que les couches sont ajoutées dans le bon ordre
2. **Test de défilement** : Vérifier que chaque couche défile à la bonne vitesse
3. **Test de rendu** : Vérifier que les couches sont rendues dans le bon ordre
4. **Test de répétition** : Vérifier que les couches répétables se répètent correctement
5. **Test de limites** : Vérifier le comportement aux limites de la caméra

### Exemple de test

```python
def test_layer_scrolling():
    """Test que les couches défilent à la bonne vitesse."""
    layer = Layer("test", depth=0, scroll_speed=0.5, surface=test_surface)
    camera_x = 100.0
    
    layer.update(camera_x, 1.0)
    assert layer.offset_x == 50.0  # 100 * 0.5
```

## Sprites personnalisés pour count_x > 3

### Fonctionnalité

Pour les sprites avec `count_x > 3`, il est possible de définir optionnellement le premier et le dernier sprite différemment du sprite de base (défini par `row` et `col`). Cette fonctionnalité permet de créer des structures plus variées visuellement, par exemple des plateformes avec des extrémités différentes du corps central.

### Paramètres optionnels

Les paramètres suivants sont disponibles uniquement lorsque `count_x > 3` :

- `first_sprite_row: Optional[int]` : Ligne du sprite sheet pour le premier sprite (0-indexed, optionnel)
  - Si non spécifié, utilise le `row` de base
  - S'applique uniquement au premier sprite de la séquence horizontale
  
- `first_sprite_col: Optional[int]` : Colonne du sprite sheet pour le premier sprite (0-indexed, optionnel)
  - Si non spécifié, utilise le `col` de base
  - S'applique uniquement au premier sprite de la séquence horizontale

- `last_sprite_row: Optional[int]` : Ligne du sprite sheet pour le dernier sprite (0-indexed, optionnel)
  - Si non spécifié, utilise le `row` de base
  - S'applique uniquement au dernier sprite de la séquence horizontale
  
- `last_sprite_col: Optional[int]` : Colonne du sprite sheet pour le dernier sprite (0-indexed, optionnel)
  - Si non spécifié, utilise le `col` de base
  - S'applique uniquement au dernier sprite de la séquence horizontale

### Comportement

Lors du rendu d'un sprite avec `count_x > 3` :
1. Le **premier sprite** (index 0) utilise :
   - `first_sprite_row` et `first_sprite_col` si définis
   - Sinon, `row` et `col` de base
   
2. Les **sprites intermédiaires** (index 1 à `count_x - 2`) utilisent toujours :
   - `row` et `col` de base
   
3. Le **dernier sprite** (index `count_x - 1`) utilise :
   - `last_sprite_row` et `last_sprite_col` si définis
   - Sinon, `row` et `col` de base

### Exemple d'utilisation

```toml
# Plateforme avec extrémités personnalisées
[[sprites]]
row = 1        # Sprite de base pour le corps de la plateforme
col = 1
depth = 2
count_x = 10   # 10 sprites horizontalement
first_sprite_row = 1  # Extrémité gauche personnalisée
first_sprite_col = 0
last_sprite_row = 1   # Extrémité droite personnalisée
last_sprite_col = 2
y_offset = 600.0
is_infinite = false
```

Dans cet exemple :
- Le premier sprite (index 0) utilise le sprite à `row=1, col=0`
- Les sprites intermédiaires (index 1 à 8) utilisent le sprite à `row=1, col=1`
- Le dernier sprite (index 9) utilise le sprite à `row=1, col=2`

### Contraintes

- Cette fonctionnalité s'applique uniquement lorsque `count_x > 3`
- Si `count_x <= 3`, les paramètres `first_sprite_row`, `first_sprite_col`, `last_sprite_row`, `last_sprite_col` sont ignorés
- Les sprites personnalisés doivent exister dans le même sprite sheet que le sprite de base
- Le `spacing` et les autres paramètres de positionnement s'appliquent de la même manière, indépendamment du sprite utilisé

### Intégration avec le système de fichier niveau

Cette fonctionnalité est intégrée dans la classe `SpriteMapping` de la spécification 3 (système de fichier niveau). Les paramètres peuvent être définis dans les fichiers `.niveau` au format TOML.

## Évolutions futures possibles

- Support du défilement vertical
- Couches animées (sprites animés)
- Effets de particules par couche - **Note** : Utiliser le moteur de particules (spécification 14) pour créer des effets de particules attachés aux couches
- Couches dynamiques (ajout/suppression en runtime)
- Support de plusieurs images par couche (variations)

## Références

- Bonnes pratiques : `bonne_pratique.md`
- **Spécification moteur de particules** : `spec/14-moteur-de-particules.md` (pour les effets de particules par couche)
- Documentation Pygame : [pygame.Surface](https://www.pygame.org/docs/ref/surface.html)
- Pattern Parallax Scrolling : Technique classique de jeu 2D

---

**Date de création** : 2024  
**Statut** : ✅ Implémenté

