# 9 - Accélération graphique MPS (macOS)

## Contexte

Cette spécification définit l'implémentation de l'accélération graphique via Metal Performance Shaders (MPS) sur macOS. Pygame utilise SDL2 en arrière-plan, qui peut utiliser Metal pour l'accélération GPU sur macOS. Cette fonctionnalité permet d'améliorer les performances de rendu, notamment en déléguant la mise à l'échelle (scaling) de l'image au GPU.

## Objectifs

- Permettre l'activation de l'accélération GPU Metal via une option en ligne de commande
- **Déléguer la mise à l'échelle de l'image au GPU (Hardware Scaling)** pour supprimer le coût CPU de `smoothscale`
- Maintenir la compatibilité avec les autres plateformes (l'option est ignorée sur non-macOS)
- Fournir un fallback automatique si l'accélération Metal n'est pas disponible

## Architecture

### SDL2 et Metal sur macOS

Pygame utilise SDL2. Sur macOS, SDL2 peut utiliser le driver `cocoa` et le renderer `metal`. L'optimisation principale consiste à utiliser le système de "Logical Size" de SDL2. Au lieu de calculer le scaling manuellement en Python (lent), on demande à SDL de présenter une surface logique (ex: 1920x1080) et de la mettre à l'échelle sur l'écran physique (ex: 2560x1440) en utilisant le GPU.

### Variables d'environnement SDL2 et Hints

Pour activer ce comportement, les variables et hints suivants sont utilisés :

1.  **Drivers** :
    -   `SDL_VIDEODRIVER=cocoa`
    -   `SDL_RENDER_DRIVER=metal`

2.  **Pipeline de Rendu** :
    -   `SDL_HINT_RENDER_BATCHING=1` : Regroupe les appels de dessin.
    -   `SDL_HINT_RENDER_VSYNC=1` : Synchronisation verticale GPU.

3.  **Mise à l'échelle (Nouveau - Décembre 2025)** :
    -   `SDL_HINT_RENDER_SCALE_QUALITY=2` (ou "best") : Utilise un filtrage de haute qualité (bicubique/linéaire) géré par le GPU lors de l'agrandissement. **Note** : le code utilise `os.environ.setdefault(...)` pour ne pas écraser une valeur déjà fournie par l'environnement.

## Spécifications techniques

### Détection de la plateforme

(Inchangé) Vérification via `sys.platform == "darwin"`.

### Activation de l'accélération

L'activation se fait en deux temps : configuration des variables d'environnement *avant* `pygame.init()`, et configuration du mode d'affichage.

```python
def enable_metal_acceleration() -> None:
    if is_macos():
        os.environ["SDL_VIDEODRIVER"] = "cocoa"
        os.environ["SDL_RENDER_DRIVER"] = "metal"
        os.environ["SDL_HINT_RENDER_BATCHING"] = "1"
        os.environ["SDL_HINT_RENDER_VSYNC"] = "1"
        os.environ.setdefault("SDL_HINT_RENDER_SCALE_QUALITY", "2")
        # Note: SDL_HINT_RENDER_LOGICAL_SIZE_MODE n'est pas exposé directement
        # via env var dans toutes les versions, mais géré via pygame.display.set_mode
        # avec les flags SCALED.
```

### Stratégie de Rendu : Hardware Scaling vs Software Scaling

#### Ancien chemin (Software Scaling - Obsolète pour Metal)
1.  Rendu sur `internal_surface` (1920x1080).
2.  Calcul du ratio et offsets.
3.  `pygame.transform.smoothscale(internal_surface, scaled_size)` (CPU intensif).
4.  `screen.blit(scaled_surface, offsets)`.

#### Nouveau chemin (Hardware Scaling - Metal)
1.  Initialisation de la fenêtre avec `pygame.SCALED` et la résolution *logique* cible (1920x1080).
  ```python
    screen = pygame.display.set_mode((1920, 1080), pygame.FULLSCREEN | pygame.SCALED | pygame.DOUBLEBUF, vsync=1)
    ```
2.  SDL/Pygame détecte `SCALED` et configure la fenêtre système à la résolution native de l'écran, mais expose une surface `screen` de 1920x1080 à l'application.
3.  **Rendu direct** : L'application dessine directement sur `screen` (qui fait 1920x1080).
4.  **Flip** : Lors du `pygame.display.flip()`, SDL/Metal prend le buffer 1920x1080 et le met à l'échelle sur le GPU pour remplir l'écran, en appliquant le letterboxing (bandes noires) automatiquement pour préserver le ratio.

**Avantages** :
-   0 coût CPU pour le scaling.
-   0 allocation mémoire pour les surfaces intermédiaires (`cached_scaled_surface`).
-   Simplification de la boucle de rendu.

### Affichage du FPS

L'affichage du FPS reste géré manuellement en haut à droite si `--profiling-metal` est activé. Le calcul doit utiliser un compteur de frames sur 0.5s pour plus de stabilité.

### Intégration dans `main.py`

La boucle de rendu doit être adaptée pour supporter les deux modes ou basculer entièrement sur le mode Hardware Scaling si SDL2 le supporte bien sur toutes les plateformes cibles (ce qui est le cas avec Pygame CE ou Pygame 2+ récent).

Si Metal est activé :
1.  Ignorer la détection de la résolution native de l'écran pour la création de la fenêtre.
2.  Demander explicitement `set_mode((RENDER_WIDTH, RENDER_HEIGHT), ... | pygame.SCALED)`.
3.  Utiliser `screen` directement comme surface de rendu (plus besoin de `internal_surface` distincte si on veut économiser une copie, ou continuer d'utiliser `internal_surface` et faire un simple blit 1:1 vers `screen`).

*Note : Pour garder la compatibilité avec les effets de shader ou post-processing futurs, conserver `internal_surface` et faire un blit final sur `screen` est acceptable car `screen` a maintenant la même taille que `internal_surface`.*

### Gestion des Entrées (Souris)

Lorsque le Hardware Scaling est activé, `pygame.mouse.get_pos()` et les événements de souris (`MOUSEMOTION`, `MOUSEBUTTONDOWN`, etc.) retournent des coordonnées dans l'espace **logique** (résolution interne, ex: 1920x1080) et non physique.

Cela signifie que :
1.  Les coordonnées d'entrée **ne doivent plus être converties** en utilisant la taille physique de la fenêtre.
2.  La fonction `convert_mouse_to_internal` doit être utilisée avec la **taille logique** (résolution interne, ex: 1920x1080) comme référence de taille d'écran, ce qui revient à une conversion d'identité (si le ratio est respecté) ou une simple suppression des bandes noires logiques si SDL ne les gère pas déjà dans les coordonnées.
3.  Dans `main.py`, la variable `display_size` passée aux fonctions de conversion d'input doit être forcée à `(RENDER_WIDTH, RENDER_HEIGHT)` lorsque Metal est activé, au lieu d'utiliser `pygame.display.get_window_size()` (qui retourne la taille physique).

### Gestion des erreurs

Si l'initialisation avec Metal échoue, le fallback désactive les variables d'environnement et continue sur le chemin de rendu standard (sans relancer `pygame.init()`).

## Optimisations de performance supplémentaires

### Optimisation 1 : Format de pixel des surfaces

**Problème** : Les surfaces pygame créées sans conversion explicite peuvent utiliser un format de pixel sous-optimal, ce qui ralentit les opérations de blitting.

**Solution** : Toutes les surfaces critiques (caches de texte, surfaces de rendu) sont optimisées pour correspondre au format de pixel de la surface d'affichage principale.

**Implémentation** :
- Fonction utilitaire `optimize_surface_format()` qui convertit les surfaces avec `.convert()` ou `.convert_alpha()` en utilisant la surface d'affichage comme référence.
- Application automatique aux surfaces de cache (FPS, debug) après leur création.
- Les surfaces principales (`internal_surface`, `cached_scaled_surface`) utilisent déjà `.convert(screen)` lors de leur création.

**Impact estimé** : +5-10% FPS

### Optimisation 2 : Système de dirty rectangles

**Problème** : Le rendu redessine l'écran entier chaque frame, même si seule une petite partie a changé.

**Solution** : Système de dirty rectangles pour ne redessiner que les zones modifiées.

**Implémentation** :
- Système de tracking des zones modifiées basé sur les mouvements de la caméra et du joueur.
- Fonction `redraw_scene()` modifiée pour accepter une liste optionnelle de rectangles à redessiner.
- Support de `pygame.display.update(dirty_rects)` au lieu de `flip()` pour les mises à jour partielles.

**État actuel** : 
- Infrastructure implémentée mais désactivée par défaut (`_use_dirty_rects = False`).
- Complexe à implémenter correctement avec le scrolling de caméra.
- Peut être activé pour des scènes statiques ou des UI qui changent peu.

**Impact estimé** : +10-20% FPS (quand activé et bien configuré)

**Note** : Pour les jeux avec scrolling continu, le système de dirty rectangles est moins efficace car la caméra bouge constamment, nécessitant un redessin complet. L'optimisation est plus pertinente pour les interfaces utilisateur statiques.

### Optimisation 3 : Éviter smoothscale inutile

**Problème** : `pygame.transform.smoothscale()` est appelé même quand le facteur d'échelle est 1.0 (pas de redimensionnement nécessaire), ce qui consomme du CPU inutilement.

**Solution** : Vérifier si la taille cible est identique à la taille originale avant d'appeler `smoothscale()`. Si c'est le cas, utiliser directement la surface originale sans transformation.

**Implémentation** :
- Dans `main.py` : Vérifier si `scaled_size == internal_surface.get_size()` avant d'appeler `smoothscale()` pour le scaling de la surface interne.
- Dans `main.py` : Vérifier si `scaled_size == src.get_size()` avant d'appeler `smoothscale()` pour le zoom caméra.
- Dans `player.py` : Vérifier si `(display_width, display_height) == sprite.get_size()` avant d'appeler `smoothscale()` pour les sprites de marche, saut, grimpe et dialogue.
- Dans `npc.py` : Vérifier si `(display_width, display_height) == sprite.get_size()` avant d'appeler `smoothscale()` pour les sprites normaux et inversés.
- Dans les modules UI (`speech_bubble.py`, `animated_sprite.py`, `splash_screen.py`, `player_stats_display.py`) : Vérifier si la taille cible est identique avant d'appeler `smoothscale()`.

**Impact estimé** : +3-5% FPS

**Fichiers modifiés** :
- `src/moteur_jeu_presentation/main.py` (2 occurrences)
- `src/moteur_jeu_presentation/entities/player.py` (4 occurrences)
- `src/moteur_jeu_presentation/entities/npc.py` (2 occurrences)
- `src/moteur_jeu_presentation/ui/speech_bubble.py` (1 occurrence)
- `src/moteur_jeu_presentation/ui/animated_sprite.py` (1 occurrence)
- `src/moteur_jeu_presentation/ui/splash_screen.py` (1 occurrence)
- `src/moteur_jeu_presentation/ui/player_stats_display.py` (1 occurrence)

### Optimisation 4 : Optimisation du système de particules

**Problème** : Calculs répétitifs pour chaque particule dans les boucles de rendu et de mise à jour, notamment :
- Appels répétés à `getattr(effect, "screen_space", False)` pour chaque effet
- Calculs de `friction_factor = config.friction ** dt` pour chaque particule visible
- Calculs de `gravity * dt` pour chaque particule visible
- Calculs de `current_size // 2` répétés pour chaque particule
- Calculs de `min/max` sur toutes les particules à chaque vérification de visibilité

**Solution** : Pré-calculer les valeurs constantes par effet avant les boucles de particules, et optimiser les calculs répétitifs.

**Implémentation** :
- Dans `system.py` :
  - Pré-calculer `is_screen_space` une fois par effet au lieu d'utiliser `getattr` à chaque fois
  - Pré-calculer `camera_x_for_particles`, `size_shrink`, `fade_out` une fois par effet
  - Pré-calculer `half_size = current_size // 2` une seule fois par particule au lieu de plusieurs fois
  - Optimiser `_is_effect_visible` pour calculer min/max en une seule passe au lieu d'utiliser `min()/max()` sur générateurs
  
- Dans `effect.py` :
  - Pré-calculer `gravity_dt = gravity * dt` une fois par effet au lieu de pour chaque particule
  - Pré-calculer `friction_factor = friction ** dt` une fois par effet au lieu de pour chaque particule
  - Pré-calculer les flags `has_gravity` et `has_friction` pour éviter les vérifications répétées

**Impact estimé** : +5-10% FPS

**Fichiers modifiés** :
- `src/moteur_jeu_presentation/particles/system.py` (optimisations dans `get_display_commands`, `get_display_commands_split`, `_is_effect_visible`)
- `src/moteur_jeu_presentation/particles/effect.py` (optimisations dans `update`)

## Tests de validation

1.  Lancer avec `--mps`.
2.  Vérifier visuellement la qualité du scaling (doit être lisse, pas pixelisé, grâce à `scale_quality=2`).
3.  Vérifier les performances (FPS stable 60, charge CPU réduite).
4.  Vérifier le respect du ratio d'aspect (bandes noires si écran ultra-wide ou 16:10).
5.  Vérifier que les optimisations de format de surface sont appliquées (surfaces de cache optimisées).
