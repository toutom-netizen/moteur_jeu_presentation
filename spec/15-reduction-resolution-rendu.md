# 15 - Configuration de la résolution de rendu interne

## Contexte

Le système de rendu utilise deux résolutions distinctes : une résolution de conception (design) et une résolution de rendu interne (render). Actuellement, la résolution de rendu interne est fixée à **1920x1080**, identique à la résolution de conception. Cette configuration garantit une excellente qualité d'image. Le principe de séparation entre résolution de conception et résolution de rendu est conservé pour permettre des évolutions futures, même si les deux résolutions sont actuellement identiques.

## Objectifs

- Maintenir la surface de rendu interne à 1920x1080 pour une qualité d'image optimale.
- Conserver le principe de deux résolutions (design et render) même si elles sont identiques, permettant des ajustements futurs sans modification de l'architecture.
- Maintenir la fidélité visuelle via une mise à l'échelle bilinéaire + options Metal quand disponible.
- Garantir que tous les systèmes dépendants de la résolution (HUD, dialogues, caméras, collisions, particules) restent cohérents.
- Centraliser la configuration de la résolution de référence pour éviter les « magic numbers » et simplifier les évolutions futures.

## Périmètre et dépendances

- Spécification `5 - Mode plein écran` : doit être alignée sur la nouvelle résolution interne.
- Spécification `1 - Système de couches 2D`, `4 - Collisions`, `8 - Bulles de dialogue`, `10 - Statistiques joueur`, `12 - PNJ`, `14 - Particules` : toutes utilisent la résolution de référence pour positionner/échelonner le rendu et doivent lire la configuration centralisée.
- Code impacté : `src/moteur_jeu_presentation/main.py`, `rendering/`, `ui/`, `game/hud/`, `stats/`, `particles/`, `levels/loader.py` (clamp caméra), ainsi que les assets et niveaux dont les coordonnées supposent 1920 de largeur visible.

## Décisions et principes directeurs

- **Résolution interne fixe 1920x1080** ; ratio 16:9 inchangé.
- **Résolution de conception 1920x1080** : identique à la résolution de rendu pour l'instant, mais le principe de séparation est conservé pour permettre des ajustements futurs.
- **Surface d'affichage** : continue d'utiliser `pygame.FULLSCREEN | pygame.SCALED | pygame.DOUBLEBUF` pour exploiter les résolutions natives supérieures.
- **Mise à l'échelle fiable** : un facteur d'échelle float est calculé dynamiquement à chaque frame via la taille de la fenêtre réelle. Les systèmes UI/HUD doivent dériver leurs tailles de police/positions à partir de ce facteur.
- **Centralisation** : le module de configuration `src/moteur_jeu_presentation/rendering/config.py` exporte les constantes et helpers liés au rendu.
- **Compatibilité Metal** : la résolution de rendu est compatible avec le backend Metal. Le flag `SDL_HINT_RENDER_SCALE_QUALITY` doit être forcé à `2` (best) pour limiter les artefacts.
- **Fallback** : si l'écran natif est plus petit que 1920x1080, basculer automatiquement en mode fenêtré à la plus grande résolution disponible ≤ 1920x1080.

## Spécifications techniques

### Paramètres globaux de rendu

- Créer `src/moteur_jeu_presentation/rendering/config.py` :

```python
from __future__ import annotations

DESIGN_WIDTH = 1920
DESIGN_HEIGHT = 1080
RENDER_WIDTH = 1920
RENDER_HEIGHT = 1080
TARGET_ASPECT_RATIO = RENDER_WIDTH / RENDER_HEIGHT  # 16 / 9

def get_render_size() -> tuple[int, int]:
    return RENDER_WIDTH, RENDER_HEIGHT

def get_design_size() -> tuple[int, int]:
    return DESIGN_WIDTH, DESIGN_HEIGHT

def compute_scale(display_size: tuple[int, int]) -> float:
    width_scale = display_size[0] / RENDER_WIDTH
    height_scale = display_size[1] / RENDER_HEIGHT
    return min(width_scale, height_scale)

def compute_design_scale(render_size: tuple[int, int]) -> tuple[float, float]:
    """Calcule les facteurs de conversion du repère de conception vers la surface de rendu interne."""
    return render_size[0] / DESIGN_WIDTH, render_size[1] / DESIGN_HEIGHT
```

- Remplacer toute utilisation directe de `1920`, `1080` dans le code par `get_render_size()`, `get_design_size()`, `RENDER_WIDTH/RENDER_HEIGHT`, `DESIGN_WIDTH/DESIGN_HEIGHT`, ou les fonctions `compute_design_scale()` et `compute_scale()` du module `rendering.config`.
- **IMPORTANT** : Ne jamais hardcoder les valeurs de résolution (1920, 1080) dans les calculs de conversion. Toujours utiliser les fonctions du module `rendering.config` :
  - Pour obtenir la taille de rendu : `get_render_size()` → `(RENDER_WIDTH, RENDER_HEIGHT)`
  - Pour obtenir la taille de design : `get_design_size()` → `(DESIGN_WIDTH, DESIGN_HEIGHT)`
  - Pour convertir du repère de design vers le repère de rendu : `compute_design_scale((render_width, render_height))` → `(scale_x, scale_y)` (actuellement retourne (1.0, 1.0) car les résolutions sont identiques)
  - Pour calculer le facteur d'échelle d'affichage : `compute_scale(display_size)` → `float`

### Création de la surface interne (`main.py`)

- Initialiser `internal_surface = pygame.Surface(get_render_size())`.
- La surface d'affichage (`screen`) reste à la taille native de l'écran ; supprimer les suppositions sur 1920x1080.
- Lors de la boucle de jeu :
  1. Dessiner sur `internal_surface`.
  2. Récupérer `display_width, display_height = pygame.display.get_window_size()` (fallback `screen.get_size()`).
  3. Calculer `scale = compute_scale((display_width, display_height))`.
  4. Obtenir la taille cible `scaled_size = (int(RENDER_WIDTH * scale), int(RENDER_HEIGHT * scale))`.
  5. Créer une surface mise à l'échelle via `pygame.transform.smoothscale`.
  6. Centrer le rendu si l'écran a un ratio différent (letterboxing noir via `screen.fill((0, 0, 0))` avant le blit).

### Gestion de la caméra et du parallaxe

- `ParallaxSystem` (`src/moteur_jeu_presentation/rendering/parallax.py`) : utiliser `RENDER_WIDTH` pour calculer les limites visibles et la vitesse de défilement (spécification 1).
- Le clamp de caméra dans `game/game.py` (ou module équivalent) doit utiliser la largeur visible 1920.
- Le culling (`is_entity_visible`, etc.) doit prendre en compte la largeur/hauteur de rendu (déjà paramétrables via arguments).

### Vitesses de mouvement et physique

- **IMPORTANT** : Toutes les vitesses de mouvement (déplacement horizontal, saut, grimpe, gravité, vitesse de chute) doivent être définies dans le repère de conception (1920x1080) et converties vers le repère de rendu (1920x1080) lors de l'initialisation. Actuellement, comme les deux résolutions sont identiques, `compute_design_scale()` retourne (1.0, 1.0), donc aucune conversion n'est appliquée. Le principe est conservé pour permettre des ajustements futurs.
- **Vitesse de déplacement horizontal** (`_base_speed`) : Définie dans le repère de conception et multipliée par `scale_x` lors de l'initialisation.
- **Vitesses verticales** (saut, grimpe, gravité, vitesse de chute max) : Définies dans le repère de conception et multipliées par `scale_y` lors de l'initialisation.
- **Implémentation** : Dans `Player.__init__()`, calculer `scale_x, scale_y = compute_design_scale((render_width, render_height))` puis appliquer ces facteurs aux vitesses :
  ```python
  base_speed_design = 250.0  # Vitesse dans le repère de conception
  self._base_speed = base_speed_design * scale_x  # Convertie vers le repère de rendu (actuellement identique)
  
  jump_velocity_design = -600.0  # Vitesse de saut dans le repère de conception
  self.jump_velocity = jump_velocity_design * scale_y  # Convertie vers le repère de rendu (actuellement identique)
  
  gravity_design = 1200.0  # Gravité dans le repère de conception
  self.gravity = gravity_design * scale_y  # Convertie vers le repère de rendu (actuellement identique)
  ```

### UI, HUD, statistiques, dialogues

- `ui/player_stats_display.py`, `ui/speech_bubble.py`, `game/hud/progress.py`, `stats/player_stats_display` : exposer un `render_scale` dérivé de `compute_scale`.
- **Tailles de police** : Les tailles de police sont définies dans le repère de conception (1920x1080) et doivent être converties vers la résolution interne (1920x1080) lors de l'initialisation : `converted_font_size = int(base_font_size * scale_y)` où `scale_y` vient de `compute_design_scale()`. Actuellement, comme les résolutions sont identiques, `scale_y = 1.0`, donc aucune conversion n'est appliquée. Ensuite, elles peuvent être ajustées avec `compute_scale()` pour s'adapter à la résolution d'affichage réelle.
- Les positions/calques qui utilisaient `1920` pour centrer doivent appeler `RENDER_WIDTH`.
- **Noms des personnages** : Les tailles de police pour les noms du joueur et des PNJ sont converties du repère 1920x1080 vers 1920x1080 lors de l'initialisation (actuellement identique).
- **Bulles de dialogue** : Les tailles de police, padding, tail_size, etc. sont convertis du repère 1920x1080 vers la résolution interne (1920x1080) et utilisés directement **sans** facteur d'échelle supplémentaire. **IMPORTANT** : Les bulles sont rendues sur la surface interne qui sera automatiquement mise à l'échelle vers l'écran réel lors du blit. Appliquer un facteur d'échelle supplémentaire basé sur `compute_scale()` (qui dépend de `RENDER_WIDTH`) créerait une double mise à l'échelle et rendrait le texte plus petit quand on augmente la résolution de rendu, ce qui est incorrect.
- **Interface de présentation du joueur** : Toutes les tailles de police (font_size, title_font_size, tooltip_font_size, presentation_name_font_size, etc.) et toutes les valeurs de positionnement (padding, offsets, espacements) sont définies dans le repère de design (1920x1080). Les valeurs historiques en 1280x720 sont converties vers 1920x1080 en multipliant par 1.5 lors de l'initialisation. Ensuite, toutes ces valeurs sont converties du repère de design vers la résolution de rendu en utilisant `compute_design_scale()`. **IMPORTANT** : Le facteur d'échelle utilisé partout dans le code est `self._design_scale_x` (ou `self._design_scale_y` pour les valeurs verticales) calculé via `compute_design_scale()`, et non plus une valeur hardcodée à 1.0. Cela garantit que l'interface s'adapte correctement si la résolution de rendu change dans le futur.
- **Indicateurs d'interaction** : La taille de police de base (28 pixels dans le repère 1920x1080) est convertie vers 1920x1080 lors de l'affichage (actuellement identique). **IMPORTANT** : Toutes les valeurs hardcodées utilisées pour le positionnement (offsets verticaux, espacements) doivent également être converties du repère de conception vers la résolution interne :
  - Offset pour positionner le nom : `4.0` pixels (repère 1920x1080) → converti avec `scale_y` (actuellement 1.0)
  - Espacement entre le nom et l'indicateur : `12` pixels (repère 1920x1080) → converti avec `scale_y` (actuellement 1.0)
  - Offset vertical supplémentaire : `60` pixels (repère 1920x1080) → converti avec `scale_y` (actuellement 1.0)
- **Bulles de dialogue - positionnement** : Toutes les valeurs hardcodées pour le positionnement des bulles doivent être converties :
  - Offset horizontal pour positionner la bulle : `10` pixels (repère 1920x1080) → converti avec `scale_y` (actuellement 1.0)
  - Marge d'écran pour éviter que la bulle sorte : `10` pixels (repère 1920x1080) → converti avec `scale_y` (actuellement 1.0)
  - Marges pour bulles avec image : `200` et `100` pixels (repère 1920x1080) → convertis avec `scale_y` (actuellement 1.0)
- **HUD de progression** : L'espacement entre lignes (`line_spacing`) doit être converti : `4` pixels (repère 1920x1080) → converti avec `scale_y` (actuellement 1.0)
- **Affichage FPS et debug** : Les positions et paddings hardcodés doivent être convertis :
  - Padding FPS : `10` pixels (repère 1920x1080) → converti avec `scale_y` (actuellement 1.0)
  - Position debug rect : `(10, 10)` pixels (repère 1920x1080) → converti avec `scale_y` (actuellement 1.0)
- **Conversion des coordonnées de la souris** : Les événements de souris (`MOUSEMOTION`, `MOUSEBUTTONDOWN`, etc.) fournissent des coordonnées en résolution d'affichage réelle, mais les interfaces UI sont rendues en résolution interne (1920x1080). Il faut donc convertir les coordonnées de la souris avant de les utiliser pour la détection de survol ou de clic. Utiliser la fonction `convert_mouse_to_internal(mouse_pos, display_size)` de `rendering.config` pour effectuer cette conversion. Cette fonction prend en compte le letterboxing et le scaling appliqués lors de l'affichage.
- **Règle générale** : Toute valeur hardcodée en pixels utilisée pour le positionnement, les espacements, les marges ou les paddings dans les éléments UI doit être considérée comme étant dans le repère de conception (1920x1080) et convertie vers la résolution interne (1920x1080) en utilisant `compute_design_scale()` avant utilisation. Actuellement, comme les résolutions sont identiques, cette conversion retourne (1.0, 1.0), mais le principe est conservé pour permettre des ajustements futurs.
- Mettre à jour `spec/8`, `spec/10`, `spec/12` pour documenter la dépendance au facteur d'échelle (voir section suivante).

### Système de création de niveau et référentiels monde

- `levels/loader.py` et la spécification `3 - Système de fichier niveau` doivent expliciter que :
  - Les largeurs/hauteurs passées au `ParallaxSystem` proviennent de `get_render_size()` au lancement.
  - Les offsets, espacements et valeurs positionnelles du format `.niveau` restent définis pour la résolution de conception 1920x1080, mais sont convertis dynamiquement via `compute_scale(display_size)` pour l’affichage et les collisions.
  - Les champs `x_offset`, `y_offset`, `spacing`, `infinite_offset` et `count_x` sont redimensionnés par le moteur lors de la création des couches pour respecter la résolution interne, y compris après application d’un `scale` spécifique au sprite.
  - La documentation des exemples TOML rappelle le repère 1920x1080 et indique comment le moteur applique le facteur d’échelle à l’exécution.

### Personnage principal, PNJ et progression/événements

- `spec/2 - Personnage principal` : préciser que le sprite est configuré pour 1920x1080 mais que `sprite_scale`, le centrage du nom, l'indicateur d'interaction et les positions initiales sont adaptés au lancement à l'aide de `compute_scale(display_size)` et `get_render_size()`.
  - Le `sprite_scale` du personnage principal est appliqué DANS le repère de conception (1920x1080), puis le résultat est converti vers la résolution interne (1920x1080) : `display_width = (sprite_width * sprite_scale) * scale_x`, `display_height = (sprite_height * sprite_scale) * scale_y`. Actuellement, `scale_x = scale_y = 1.0`, donc aucune conversion n'est appliquée.
- `spec/12 - Système de personnage non joueur` : clarifier que les distances, le centrage des noms et le positionnement des bulles s'appuient sur les valeurs de configuration 1920x1080 mais sont convertis au runtime via la même logique d'échelle que pour le joueur.
  - Les positions `x` des PNJ définies dans les fichiers `.pnj` sont converties du repère 1920x1080 vers la résolution interne 1920x1080 lors du chargement via `compute_design_scale()`. Actuellement, cette conversion retourne (1.0, 1.0), donc aucune conversion n'est appliquée.
  - Les plages de dialogue (`position_min` et `position_max`) sont également converties du repère 1920x1080 vers la résolution interne lors du chargement (actuellement identique).
  - Le `sprite_scale` des PNJ est appliqué DANS le repère de conception (1920x1080), puis le résultat est converti vers la résolution interne (1920x1080) : `display_width = (sprite_width * sprite_scale) * scale_x`, `display_height = (sprite_height * sprite_scale) * scale_y`. Actuellement, `scale_x = scale_y = 1.0`, donc aucune conversion n'est appliquée.
- Mettre en avant que toute nouvelle configuration (PNJ, inventaire, stats) doit continuer à utiliser les valeurs de référence 1920x1080, le moteur assurant la mise à l’échelle lors du démarrage.
- `spec/11 - Système de gestion de l'avancement` : mettre à jour la description du `LevelProgressTracker`, du `LevelProgressHUD` et du `EventTriggerSystem` pour préciser que :
  - Les positions monde (`current_x`, `trigger_x`, `target_x`) sont toujours renseignées en repère 1920x1080 dans les fichiers `.event`.
  - Le HUD calcule son facteur d’échelle via `compute_scale(display_size)` avant de rendre le panneau.
  - Les actions déclenchées (`npc_move`, `sprite_hide`, `sprite_show`, `inventory_add/remove`) convertissent les positions/offsets configurés en repère interne via `get_render_size()` pour rester cohérents avec le rendu 1920x1080.

### Particules et systèmes dépendant du viewport

- `particles/system.py` : les commandes de rendu doivent référencer `RENDER_WIDTH`/`RENDER_HEIGHT` pour le clipping (spécification 14).
- **Événements `particle_effect` avec `sprite_tag`** : les bounds des layers (world_x_offset, surface, etc.) sont déjà en **repère de rendu** car le LevelLoader convertit les positions avec `compute_design_scale()` à la création des couches. Lors du calcul de la zone de spawn pour un `sprite_tag`, ne pas appliquer à nouveau `design_scale_x`/`design_scale_y` sur ces bounds, sous peine de double mise à l'échelle et particules mal positionnées quand RENDER > DESIGN.
- Ajuster les buffers internes éventuels (si pré-alloués à 1920x1080).

### Physique et collisions

- Le système de collisions (`physics/collision.py`) travaille en coordonnées monde ; aucune modification de logique, mais les tests visuels doivent valider que le clipping caméra reste cohérent avec le viewport réduit.

### Gestion des assets

- Les assets existants (fonds 1920px de large) sont utilisés directement sans mise à l'échelle, car la résolution de rendu correspond à la résolution de conception.
- Les nouvelles créations graphiques doivent cibler 1920x1080 comme base, correspondant à la résolution de rendu actuelle.

### Accélération Metal et qualité de scaling

- S'assurer que `enable_metal_acceleration()` continue de définir :
  - `SDL_HINT_RENDER_SCALE_QUALITY = "2"` (ou `"1"` si non supporté, log de fallback).
- Documenter que l'utilisation de `smoothscale` + Metal offre un rendu de qualité pour les écrans haute résolution.

## Mise à jour des autres spécifications

- `5 - Mode plein écran` : mettre à jour pour refléter que la résolution interne est 1920x1080 et décrire le letterboxing pour les écrans haute résolution.
- `1 - Système de couches 2D` : préciser que les vitesses de défilement et clamps utilisent `RENDER_WIDTH`.
- `3 - Système de fichier niveau` : rappeler que les fichiers sont exprimés pour 1920x1080 et documenter que la conversion automatique au lancement (positions, spacing, `is_infinite`) via `compute_design_scale()` retourne actuellement (1.0, 1.0) car les résolutions sont identiques.
- `2 - Personnage principal avec animations` : documenter l'utilisation du facteur d'échelle runtime (`render_scale`) pour le sprite, le nom et l'indicateur d'interaction, ainsi que l'initialisation à partir de `get_render_size()`.
- `8 - Système de bulles de dialogue`, `10 - Affichage statistiques joueur`, `12 - Système de PNJ` : mentionner le facteur d'échelle dynamique et son application aux polices, positions et distances d’interaction.
- `11 - Système de gestion de l'avancement` : détailler la reliance au repère 1920x1080 pour les fichiers `.event` et au facteur d’échelle calculé au lancement pour le HUD et les déclencheurs.
- `9 - Accélération graphique MPS/Metal` : ajouter une note sur la qualité de scaling et la compatibilité avec la résolution de rendu.
- `14 - Moteur de particules` : ajuster la référence au viewport (1920x1080).

## Plan de migration

1. Introduire `rendering/config.py` et remplacer les constantes statiques.
2. Mettre à jour `main.py` et toutes les surfaces pour utiliser `compute_scale`.
3. Adapter les modules UI/HUD/Dialogue/Stats pour recalculer les tailles et positions via `render_scale`.
4. Vérifier les niveaux et triggers (fichiers `.niveau`, `.event`, `.pnj`) pour des valeurs dépendant de la largeur visible ; ajuster si des offsets statiques supposent 1920.
5. Mettre à jour la documentation technique (`README.md`, spécifications listées ci-dessus).
6. Effectuer une passe de tests de régression visuelle.

## Tests et validation

- **Performance** : mesurer FPS moyen sur un niveau dense (profiling Metal activé et désactivé) pour valider les performances avec la résolution 1920x1080.
- **Tests fonctionnels** :
  - Interaction PNJ (bulles, dialogues, HUD) sur différentes résolutions d'écran (1080p, 1440p, 4K).
  - Rendu des couches parallaxe et collision avec culling.
  - Transition plein écran ↔ fenêtré (si supportée) pour vérifier la re-création des surfaces.
- **Tests automatisés** : ajuster/ajouter tests unitaires qui valident des positions dépendantes de la résolution de rendu (1920x1080).

## Risques et mitigations

- **Performance** : la résolution 1920x1080 peut être plus exigeante en termes de performance que 1280x720. Utiliser `smoothscale` + `SDL_HINT_RENDER_SCALE_QUALITY` pour optimiser le rendu. Le principe de séparation design/render permet de réduire la résolution de rendu si nécessaire sans modifier l'architecture.
- **Régressions UI** : appliquer un audit visuel complet et ajouter des assertions sur les tailles de polices minimales.
- **Letterboxing** : s'assurer que le fond écran noir ne masque pas les HUD ; tolérance configurable via `config.py`.


## Statut

✅ Implémenté


