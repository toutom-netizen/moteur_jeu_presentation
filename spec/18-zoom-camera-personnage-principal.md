# 18 - Zoom caméra sur le personnage principal

## Contexte

Certaines séquences (mise en valeur, punchline, moment narratif) nécessitent un **zoom de caméra** sur le personnage principal, sans modifier la logique de gameplay (collisions, positions monde, progression du niveau).

Le zoom doit être déclenchable via le **système d’événements** (spécification 11) afin d’être pilotable depuis les fichiers `.event` (trigger par `trigger_x` ou déclenchement manuel depuis un dialogue).

## Objectifs

- Ajouter **3 événements** :
  - `camera_zoom` : applique un zoom (paramètre en **pourcentage**) de manière **progressive** sur le joueur.
  - `camera_zoom_sprite` : déclenche une transition **progressive** vers un sprite identifié par son tag, avec offsets X/Y, en déplaçant la caméra **linéairement** vers la position cible et en appliquant le zoom demandé.
  - `camera_zoom_reset` : revient au zoom initial (100%) en **dézoomant** et en ramenant la caméra vers la position **actuelle du joueur**, puis réactive le suivi.
- Le zoom “cadre” le joueur (pour `camera_zoom`) :
  - Le **bas de l’écran** doit se positionner **50 px en dessous des pieds** du personnage (donc les pieds sont à `screen_height - 50` dans le repère de rendu interne).
  - Aucun changement de “niveau affiché” en termes de monde/collisions : c’est un **post-process caméra**.
- Le zoom sur sprite (pour `camera_zoom_sprite`) :
  - La caméra se déplace **linéairement** depuis sa position courante vers la position cible du sprite (offsets X/Y appliqués), sans tenir compte des déplacements du joueur pendant la transition.
  - Une fois la transition terminée, la caméra reste **fixe** sur la position finale (elle ne suit plus le joueur) jusqu'au déclenchement d'un `camera_zoom_reset`.
  - Aucun changement de “niveau affiché” en termes de monde/collisions : c’est un **post-process caméra**.
- Si une **bulle de dialogue** est affichée, elle doit rester **entièrement visible**.
- L’UI “overlay” ne doit **pas** être impactée par le zoom :
  - **Affichage des statistiques** (spec 10) : rendu + zones de hover/clic inchangées.
  - **Popin de confirmation pour quitter** : rendu + détection souris inchangés.
- Techniquement : l’ensemble de la **scène** est calculé d’abord, puis le zoom est appliqué.
  - “Scène” = monde + PNJ + joueur + particules + textes “in-scene” (noms PNJ, bulles, etc.).
  - “Overlay UI” (stats, popin quitter, etc.) = rendu après zoom, sans transformation.

## Non-objectifs

- Modifier les collisions, la physique, ou la progression (le zoom n’a aucun effet sur le gameplay).
- Ajouter un zoom “par zone” (on zoome toujours sur la scène complète).
- Ajouter un “pan” manuel à la souris (hors périmètre).

## Architecture

### Principe de rendu (scène puis zoom)

1. Rendre la **scène** sur une surface intermédiaire `scene_surface` de taille `get_render_size()` (spec 15).
2. Appliquer un **post-process de zoom** (scale + translation) et bliter le résultat sur `internal_surface` (ou directement sur la surface finale de rendu interne).
3. Rendre les **overlays UI** (stats, popin quitter, etc.) **après** l’étape 2, sans zoom.

### Composants proposés

- `CameraZoomController`
  - Stocke l’état du zoom (zoom courant, zoom cible, timers, interpolation).
  - Stocke le mode de zoom actif (joueur ou sprite) et les informations du sprite cible si applicable.
  - Calcule la transformation `(zoom_factor, offset_x, offset_y)` à appliquer au blit de `scene_surface`.
  - Expose une API simple appelée par le système d’événements :
    - `start_zoom(target_percent, duration, ...)` : zoom sur le joueur
    - `start_zoom_sprite(sprite_tag, target_percent, offset_x, offset_y, duration, ...)` : zoom sur un sprite
    - `reset_zoom(duration, ...)` : retour au zoom initial
  - Gère l'état de suivi de la caméra : transitions **déverrouillées** et verrouillage final sur sprite, puis retour au suivi du joueur après reset.
- Intégration dans `EventTriggerSystem` (spec 11)
  - Ajout de 3 nouveaux `event_type` : `camera_zoom`, `camera_zoom_sprite`, `camera_zoom_reset`.
  - Ajout de 3 nouveaux `EventConfig` dataclasses.
  - Exécution via `_execute_camera_zoom(...)`, `_execute_camera_zoom_sprite(...)` et `_execute_camera_zoom_reset(...)`.
  - Accès à `layers_by_tag` pour localiser le sprite par son tag.

## Spécifications techniques

### Unités et repères

- Les paramètres d’événement (pourcentage, durées, marges) sont exprimés dans le repère **design 1920x1080**.
- Les calculs de rendu utilisent la surface interne `get_render_size()` (spec 15).
- La marge “50 px sous les pieds” est convertie vers le repère de rendu via `compute_design_scale()`.

### Paramètres de zoom

- **Pourcentage** :
  - `zoom_percent = 100` → pas de zoom (facteur 1.0).
  - `zoom_percent > 100` → zoom in (facteur > 1.0).
  - `zoom_percent < 100` → zoom out (facteur < 1.0) (optionnel mais supporté).
- Conversion :
  - `zoom_factor = zoom_percent / 100.0`
- Contraintes :
  - `zoom_percent` doit être strictement positif.
  - Valeurs recommandées : 75% à 200% (au-delà, risque de crop important).

### Progressivité (zoom / dezoom)

Le zoom et la position caméra doivent être interpolés à chaque frame avec `dt` :

- `t = clamp(timer / duration, 0..1)`
- **Interpolation linéaire** (règle importante) :
  - `current_zoom = lerp(start_zoom, target_zoom, t)`
  - `offset_x = lerp(start_offset_x, target_offset_x, t)`
  - `offset_y = lerp(start_offset_y, target_offset_y, t)`

### Ancrage joueur (pieds + 50 px)

On calcule la position des pieds du joueur dans la scène **avant zoom** :

- `player_feet_y_scene` = position Y (en pixels) des pieds du joueur sur `scene_surface`
  - typiquement `player_last_draw_rect.bottom` (dans le repère de rendu interne)

On impose, après transformation, la contrainte :

- `player_feet_y_screen = screen_height - bottom_margin_px`

Si on blite une version scalée de `scene_surface` avec un offset `(offset_x, offset_y)` :

- `p_screen = offset + p_scene * zoom_factor`

Donc l’offset vertical “cible” est :

- `offset_y_target = player_feet_y_screen - player_feet_y_scene * zoom_factor`

Même approche possible en X (recommandé) pour garder le joueur stable à l’écran :

- `player_anchor_x_scene` = `player_last_draw_rect.centerx`
- `player_anchor_x_screen` = `screen_width / 2`
- `offset_x_target = player_anchor_x_screen - player_anchor_x_scene * zoom_factor`

### Ancrage sprite (avec offsets X et Y)

Pour le zoom sur un sprite identifié par son tag :

1. **Localisation du sprite** :
   - Le sprite est trouvé via `layers_by_tag[sprite_tag]` (retourne une liste de `Layer`).
   - Si plusieurs layers partagent le même tag, on utilise le premier layer de la liste (ou une logique de sélection définie).
   - La position du sprite est calculée à partir des attributs de la layer :
     - `sprite_x_scene = layer.world_x_offset - layer.offset_x` (position X dans la scène)
     - `sprite_y_scene = layer.world_y_offset` (position Y dans la scène)
     - On peut utiliser le centre du sprite : `sprite_center_x = sprite_x_scene + layer.surface.get_width() / 2`
     - `sprite_center_y = sprite_y_scene + layer.surface.get_height() / 2`

2. **Application des offsets** :
   - Les offsets X et Y sont exprimés en pixels dans le repère design 1920x1080.
   - Ils sont convertis vers le repère de rendu interne via `compute_design_scale()`.
   - La position cible du sprite à l'écran est :
     - `target_x_screen = screen_width / 2 + offset_x_render`
     - `target_y_screen = screen_height / 2 + offset_y_render`

3. **Calcul de l'offset de transformation** :
   - `offset_x_target = target_x_screen - sprite_center_x_scene * zoom_factor`
   - `offset_y_target = target_y_screen - sprite_center_y_scene * zoom_factor`

4. **Transition et verrouillage** :
   - Au déclenchement, la caméra est **déverrouillée** et interpole **linéairement** depuis sa position courante vers `(offset_x_target, offset_y_target)` avec le zoom cible.
   - Pendant la transition, les déplacements du joueur ne sont **pas** pris en compte (la cible est figée au moment du déclenchement).
   - Une fois la transition terminée, la caméra devient **fixe** sur la position finale (elle ne suit plus le joueur).
   - Le suivi du joueur n'est restauré qu'après un `camera_zoom_reset`.

### États de caméra et transitions

Le contrôleur doit gérer trois états explicites :

- `follow_player` : la caméra suit le joueur (mode normal).
- `transition_to_sprite` / `transition_to_player` : la caméra est **déverrouillée** et se déplace **linéairement** entre deux positions (start → target).
- `locked_on_sprite` : la caméra est fixée sur la position finale du sprite, sans suivre le joueur.

Les transitions capturent les positions **au moment du déclenchement** pour éviter toute dépendance aux mouvements du joueur pendant l'animation.

**Note d'implémentation** :
- Le déplacement linéaire correspond au **camera_x** (position monde) interpolé entre deux positions.
- Les offsets X/Y de `camera_zoom_sprite` sont appliqués en priorité via `camera_x` (axe X) et via l'offset de zoom (axe Y, si nécessaire).
- Pour centrer un sprite après zoom, la cible `camera_x` doit tenir compte du facteur de zoom :
  - `camera_x_target = sprite_center_x_world - (screen_width / 2 + offset_x_render) / zoom_target`
- Pendant la transition vers un sprite, l'offset Y doit être recalculé avec le **zoom courant**
  (ne pas interpoler un offset Y calculé avec le zoom final).
- Pendant la transition de retour vers le joueur, si le joueur bouge, la cible `camera_x`
  peut être recalculée à chaque frame pour éviter un saut visible au relock.

### Clamp (éviter les bords vides)

Pour un zoom in (`zoom_factor >= 1.0`), la surface scalée est plus grande que l’écran. Pour éviter d’afficher du “vide”, l’offset doit respecter :

- `offset_x ∈ [screen_width - screen_width*zoom_factor, 0]`
- `offset_y ∈ [screen_height - screen_height*zoom_factor, 0]`

Le `CameraZoomController` doit :

1. Calculer `(offset_x_target, offset_y_target)` selon le mode actif :
   - Pour un zoom sur joueur : ancrage joueur (pieds + marge).
   - Pour un zoom sur sprite : ancrage sprite (centre + offsets).
2. Clamper dans les bornes ci-dessus.

### Contrainte “bulles entièrement visibles”

Si une ou plusieurs bulles de dialogue sont affichées, elles doivent rester **entièrement visibles** après zoom.

**Décision d’implémentation (anti-jitter)** :
- La caméra (offset/zoom) est calculée à partir de l'ancrage (joueur pour `camera_zoom`, sprite pour `camera_zoom_sprite`) + clamp global.
- Si `keep_bubbles_visible = True`, le zoom peut être automatiquement réduit (capped) pour garantir que toutes les bulles restent visibles.
- Les bulles sont dessinées **après** le rendu zoomé (donc après le `smoothscale`), et leur position écran est calculée via la transformation caméra.
- Si une bulle sortirait de l’écran, on **clamp la position de la bulle** (pas la caméra).

But : éviter que la caméra “suive” la taille de la bulle lorsque son contenu change (machine à écrire, image, etc.).

### UI non impactée (stats, popin quitter)

- Le zoom ne s’applique **qu’à la scène**.
- Les overlays UI sont rendus après le zoom sur la surface interne finale.
- La conversion souris “display → interne” (spec 15) reste la seule conversion nécessaire pour l’UI.
- Si des interactions “monde” utilisent la souris (clic dans la scène), elles doivent utiliser l’inverse de la transformation :
  - `mouse_scene = (mouse_internal - offset) / zoom_factor`
  - Important : ceci ne doit jamais être appliqué aux zones UI.

## Spécification des événements (`.event`)

### Nouveaux types

- `camera_zoom` : zoom sur le joueur
- `camera_zoom_sprite` : zoom sur un sprite identifié par son tag
- `camera_zoom_reset` : retour au zoom initial

Ces événements sont gérés par `EventTriggerSystem` (spec 11) :

- Étendre `EventTriggerConfig.event_type` (Literal) avec ces trois valeurs.
- Étendre `EventTriggerConfig.event_data` (Union) avec les configs ci-dessous.
- Ajouter les méthodes d’exécution correspondantes.

### `camera_zoom`

#### Données

```python
@dataclass
class CameraZoomEventConfig:
    """Configuration d'un événement de zoom caméra."""
    zoom_percent: float  # Pourcentage de zoom (100 = zoom neutre)
    duration: float = 0.8  # Durée de l'animation (secondes)
    bottom_margin: float = 50.0  # Marge sous les pieds (pixels design 1920x1080)
    keep_bubbles_visible: bool = True  # Force les bulles à rester à l'écran (cap zoom si nécessaire)
```

#### Exemple `.event`

```toml
[[events]]
identifier = "camera_zoom_01"
trigger_x = 6500.0
event_type = "camera_zoom"

[events.event_data]
zoom_percent = 160.0
duration = 0.9
bottom_margin = 50.0
keep_bubbles_visible = true
```

### `camera_zoom_sprite`

#### Données

```python
@dataclass
class CameraZoomSpriteEventConfig:
    """Configuration d'un événement de zoom caméra sur un sprite."""
    sprite_tag: str  # Tag du sprite à zoomer (doit correspondre à un tag défini dans le fichier .niveau)
    zoom_percent: float  # Pourcentage de zoom (100 = zoom neutre)
    offset_x: float = 0.0  # Offset horizontal en pixels (repère design 1920x1080, défaut: 0.0)
    offset_y: float = 0.0  # Offset vertical en pixels (repère design 1920x1080, défaut: 0.0)
    duration: float = 0.8  # Durée de l'animation (secondes)
    keep_bubbles_visible: bool = True  # Force les bulles à rester à l'écran (cap zoom si nécessaire)
```

#### Exemple `.event`

```toml
[[events]]
identifier = "camera_zoom_sprite_01"
trigger_x = 6500.0
event_type = "camera_zoom_sprite"

[events.event_data]
sprite_tag = "important_object"
zoom_percent = 180.0
offset_x = 50.0
offset_y = -30.0
duration = 1.0
keep_bubbles_visible = true
```

**Comportement** :
- Une fois l'événement déclenché, la caméra se déplace **linéairement** vers le sprite identifié par `sprite_tag` et applique le zoom demandé.
- Les offsets X et Y sont appliqués par rapport au centre de l'écran (le sprite est centré, puis décalé de `offset_x` et `offset_y`).
- Pendant la transition, la caméra ne tient **pas** compte des déplacements du joueur (la cible est figée au déclenchement).
- Une fois la transition terminée, la caméra devient **fixe** (elle ne suit plus le joueur) jusqu'au déclenchement d'un `camera_zoom_reset`.
- Si plusieurs sprites partagent le même tag, le premier sprite de la liste est utilisé.

### `camera_zoom_reset`

#### Données

```python
@dataclass
class CameraZoomResetEventConfig:
    """Configuration d'un événement de retour au zoom initial."""
    duration: float = 0.8  # Durée de l'animation (secondes)
```

#### Exemple `.event`

```toml
[[events]]
identifier = "camera_zoom_reset_01"
trigger_x = 7200.0
event_type = "camera_zoom_reset"

[events.event_data]
duration = 0.9
```

**Comportement** :
- Réinitialise le zoom à 100% de manière progressive.
- Déclenche une transition **linéaire** depuis la position caméra courante vers la position **actuelle du joueur** (cible capturée au moment du déclenchement).
- Pendant la transition, la caméra est **déverrouillée** et ne suit pas le joueur.
- Le suivi normal de la caméra sur le joueur n'est restauré qu'une fois l'animation terminée (pas pendant l'animation).
- Peut être déclenché après un `camera_zoom` ou un `camera_zoom_sprite`.

## Implémentation (indications)

### Fichiers

Proposition de structure (à adapter si un module caméra existe déjà) :

```
src/moteur_jeu_presentation/
├── rendering/
│   ├── camera_zoom.py            # CameraZoomController + maths de transformation
│   └── config.py                 # déjà existant (spec 15)
└── game/
    └── events.py                 # EventTriggerSystem (spec 11) : ajout des 2 events
```

### Points d’intégration

- `EventTriggerSystem.__init__` : injecter une référence vers `CameraZoomController` et `layers_by_tag`.
- Boucle `update(dt)` :
  - `camera_zoom.update(dt)` (même si aucun zoom n’est actif, no-op).
  - Si un zoom sur sprite est actif, la caméra ne suit plus le joueur (position fixe après transition).
  - Si une transition est active, la caméra est **déverrouillée** et interpole **linéairement** entre deux positions figées.
- Pipeline de draw du gameplay :
  - `scene_surface` est rendue normalement.
  - Si `camera_zoom.is_active` ou `camera_zoom.current_zoom != 1.0` : appliquer la transformation au blit.
    - Pour un zoom sur joueur : utiliser `compute_transform(player_draw_rect, bubble_rects)`.
    - Pour un zoom sur sprite : utiliser `compute_transform_sprite(sprite_position, offset_x, offset_y, bubble_rects)`.
  - Rendre ensuite les overlays UI (stats, popin quitter, etc.).

## Contraintes / Performance

- Le zoom implique un `smoothscale` d’une surface potentiellement grande (1920x1080). Pour limiter l’impact :
  - Ne pas scaler si `zoom_factor == 1.0`.
  - Éviter toute allocation répétée hors transform (ne pas recréer `scene_surface`).
  - Option future (si nécessaire) : basculer vers `pygame.transform.scale()` (plus rapide) si les FPS chutent.

### Hot path Python (rendu par frame)

- **Ne pas définir de fonctions dans le chemin de rendu par frame** (ex: pas de `def ...` à l'intérieur de `_full_redraw_scene()` ou de la boucle principale).
  - Raison : création de fonctions/closures à chaque frame → allocations + pression GC → baisse de FPS même quand le zoom est “inactif”.
  - Préférer : fonctions définies une fois (au niveau module ou au niveau `main()`), puis appelées à chaque frame.

### Particules “monde” vs “overlay”

Quand le zoom caméra est actif :
- Les particules **monde** (attachées au gameplay) sont rendues dans la scène et donc **zoomées**.
- Les particules **overlay** (attachées à l’écran, ex: confettis/sparkles de transition de niveau) doivent être rendues en **screen-space** (coordonnées écran) **après** le zoom, pour rester dans les coins même en mode zoomé.

**Performance particules** :
- Éviter de parcourir deux fois toutes les particules par frame (une fois pour “monde”, une fois pour “overlay”).
- Préférer une génération en **une seule passe** qui retourne deux listes (monde + overlay) à réutiliser dans le pipeline de rendu.

## Notes d'implémentation critiques

**Conversion écran → monde pendant les transitions** : Lors du calcul de la position monde du joueur (`player_center_world`) pour déterminer la cible `camera_x` pendant une transition de retour, il est **critique** d'utiliser la position RÉELLE actuelle de la caméra (qui peut être overridée), pas la position de suivi normal stockée dans `_current_camera_x`. La formule correcte est :
```python
actual_camera_x = _current_camera_x_override if _current_camera_x_override is not None else _current_camera_x
player_center_world = player_draw_rect.centerx + actual_camera_x
```
Sans cette correction, le calcul de `player_center_world` sera incorrect pendant les transitions, causant des sauts visibles lors du passage en mode suivi.

**Formule camera_x pour centrage** : La position `camera_x` pour centrer un objet monde au centre de l'écran est simplement `object_world_x - screen_w / 2.0`, **indépendamment du zoom** (car `camera_x` est en coordonnées monde, le zoom affecte seulement les offsets de transformation écran).

## Tests et validation

- **Zoom simple** : déclencher `camera_zoom` (ex: 160%) → zoom progressif + joueur cadré (pieds à `H-50`).
- **Zoom sur sprite** : déclencher `camera_zoom_sprite` avec un tag valide → zoom progressif sur le sprite avec les offsets appliqués.
- **Caméra fixe** : pendant un zoom sur sprite, déplacer le joueur → la caméra reste fixe, le zoom reste centré sur le sprite.
- **Transition linéaire** : vérifier que la caméra se déplace **linéairement** entre les positions de départ et d'arrivée (sprite ou joueur).
- **Reset** : déclencher `camera_zoom_reset` → transition linéaire vers la position **actuelle du joueur** + dézoom. Le suivi du joueur est restauré uniquement après la fin de la transition.
- **Bulle active** : pendant un dialogue, déclencher un zoom fort → la bulle reste entièrement visible (cap si nécessaire).
- **UI stats** : ouvrir l’UI stats (spec 10) pendant un zoom → rendu identique, hover/clic identiques.
- **Popin quitter** : afficher la popin quitter pendant un zoom → rendu + clics identiques.
- **Non-régression gameplay** : collisions, déplacements, triggers `.event` inchangés.
- **Tag invalide** : déclencher `camera_zoom_sprite` avec un tag inexistant → erreur claire lors du chargement de l'événement.

## Références

- Bonnes pratiques : `bonne_pratique.md`
- Événements : `spec/11-systeme-gestion-avancement-niveau.md`
- Bulles : `spec/8-systeme-de-bulles-de-dialogue.md`
- Stats UI : `spec/10-affichage-statistiques-joueur.md`
- Résolution interne : `spec/15-reduction-resolution-rendu.md`

---

**Statut** : ✅ Implémenté

