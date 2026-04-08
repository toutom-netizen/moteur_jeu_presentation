# 8 - Système de bulles de dialogue

## Contexte

Les bulles de dialogue sont utilisées pour afficher les conversations entre le joueur et les PNJ. Elles doivent être lisibles, esthétiques et s'adapter au contenu (texte et/ou image).

## Objectifs

- Afficher du texte multi-lignes dans des bulles
- Supporter l'affichage d'images dans les bulles
- Gérer l'animation du texte (machine à écrire)
- Adapter la taille de la bulle au contenu
- **Assurer une lisibilité maximale du texte (contour)**

## Spécifications techniques

### Classe `SpeechBubble`

La classe `SpeechBubble` gère le rendu et l'animation d'une bulle de dialogue.

#### Attributs

- `text`: Texte à afficher
- `character`: Personnage associé
- `side`: Position par rapport au personnage ("left" ou "right")
- `font`: Police de caractères
- `bg_color`: Couleur de fond
- `text_color`: Couleur du texte
- `border_color`: Couleur de la bordure et de la queue
- `padding`: Marge interne
- `tail_size`: Taille de la queue

#### Rendu du texte avec contour (Amélioration de la lisibilité)

Pour améliorer la lisibilité du texte sur le fond de la bulle, un contour (outline) doit être appliqué, similaire à celui utilisé pour les noms des PNJ.

1.  **Couleur de contour** : Blanc (`(255, 255, 255)`) pour contraster avec le texte noir (ou inversement).
2.  **Épaisseur** : 2 pixels (adapté selon le facteur d'échelle).
3.  **Algorithme** : Rendre le texte en couleur de contour à 8 positions autour du centre ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)) ou plus pour un contour plus épais, puis rendre le texte principal au centre.

#### Adaptation à la résolution

Les dimensions (police, padding, queue, offsets) doivent être converties depuis le repère de conception (1920x1080) vers la résolution de rendu interne (1280x720), puis ajustées dynamiquement selon la résolution d'affichage réelle via un facteur d'échelle.

**Important :** le facteur d'échelle doit être calculé à partir de la taille **logique** de la surface de rendu (`pygame.display.get_surface().get_size()`), pas depuis la taille physique de la fenêtre. Cela garantit un comportement identique que l'application utilise un scaling matériel (Metal) ou logiciel. En cas d'indisponibilité de la surface (ex: avant `set_mode`), un fallback vers la taille de fenêtre est autorisé.

#### Positionnement

La bulle doit être positionnée au-dessus du personnage, décalée vers la droite ou la gauche selon l'attribut `side`. Elle doit rester dans les limites de l'écran. Si une image est présente, la bulle peut être centrée en haut de l'écran pour maximiser l'espace.

#### Système de cache pour les images de dialogue (voir spécification 17)

Le système de bulles de dialogue utilise un **cache global partagé** pour optimiser le chargement des images :

**Cache global `_global_image_cache`** (défini dans `ui/speech_bubble.py`) :
- **Type** : `Dict[str, pygame.Surface]`
- **Clé** : chemin absolu de l'image (str) après résolution avec `.resolve()`
- **Valeur** : Surface pygame de l'image chargée avec `convert_alpha()`
- **Portée** : Partagé entre toutes les instances de `SpeechBubble`
- **Rempli par** : 
  - `AssetPreloader._preload_dialogue_images()` au démarrage (préchargement automatique)
  - `preload_dialogue_images()` appelée manuellement si `--skip-preload`
  - `SpeechBubble._load_image()` en fallback si l'image n'est pas préchargée

**Fonction `preload_dialogue_images()`** :
```python
def preload_dialogue_images(npcs_config, assets_root: Path = Path("image")) -> None:
    """Précharge toutes les images de dialogue depuis la configuration des PNJ."""
    # Parcourt tous les blocs de dialogue et charge toutes les images
    # dans _global_image_cache
```

**Préchargement automatique** :
- Toutes les images de dialogue sont automatiquement préchargées par `AssetPreloader` avant l'affichage de l'écran d'accueil (voir spec 17)
- Le préchargement utilise un chemin absolu basé sur `project_root / "image"` pour garantir la cohérence des clés de cache
- Les dialogues utilisent le même chemin absolu via `npc.assets_root.parent / "image"` pour accéder au cache

#### Redimensionnement des images haute résolution

Pour améliorer la visibilité des images haute résolution dans les bulles de dialogue, le système utilise les optimisations suivantes :

1. **Algorithme de redimensionnement** : Utilisation de `pygame.transform.smoothscale()` au lieu de `pygame.transform.scale()` pour préserver la qualité lors du redimensionnement. L'algorithme de lissage de `smoothscale` préserve mieux les détails, particulièrement important pour les images haute résolution qui sont redimensionnées vers le bas.

2. **Espace disponible maximisé** : 
   - La marge du bas est réduite à 50 pixels (repère 1920x1080) au lieu de 100 pixels pour maximiser l'espace vertical disponible pour les images
   - Les marges latérales et supérieures sont à 0 pour utiliser toute la largeur et hauteur de l'écran
   - L'espace réservé pour le personnage en bas est de 200 pixels (repère 1920x1080)

3. **Préservation des proportions** : Les images sont redimensionnées en préservant leurs proportions originales. Le ratio de redimensionnement est calculé en prenant le minimum entre le ratio de largeur et le ratio de hauteur pour que l'image rentre entièrement dans l'espace disponible.

4. **Cache local pour images redimensionnées** : Les images redimensionnées sont mises en cache localement dans `_scaled_image_cache` pour éviter de recalculer le redimensionnement à chaque frame. Le cache est limité à 10 entrées pour éviter les fuites mémoire. Ce cache est distinct du cache global `_global_image_cache` qui contient les images originales non redimensionnées.

### Intégration

Le système de dialogue (`DialogueState`) utilise `SpeechBubble` pour chaque échange.

#### Contrainte de navigation entre les échanges

**Important** : Le passage à l'échange suivant dans un dialogue est bloqué si un événement de type `sprite_move` est en cours de déplacement.

- **Vérification** : Avant de passer à l'échange suivant (dans `DialogueState._next_exchange()`), le système doit vérifier s'il existe des mouvements de sprites en cours via le système de déclencheurs d'événements (`EventTriggerSystem`).
- **Méthode de vérification** : Le système doit interroger `EventTriggerSystem` pour déterminer si le dictionnaire `_sprite_movement_tasks` contient des tâches actives. Si des tâches sont présentes, le passage à l'échange suivant est bloqué.
- **Comportement** : 
  - Si un `sprite_move` est en cours : le clic est ignoré et l'utilisateur ne peut pas passer à l'échange suivant, même si le texte est complètement affiché.
  - Si aucun `sprite_move` n'est en cours : le comportement normal s'applique (clic pour passer à l'échange suivant lorsque le texte est complet).
- **Intégration** : Cette vérification doit être effectuée dans `DialogueState.handle_event()` avant d'appeler `_next_exchange()`. Le `DialogueState` a accès à `EventTriggerSystem` via son attribut `event_system` (passé lors de l'initialisation).
- **Méthode à ajouter** : `EventTriggerSystem` doit exposer une méthode publique (par exemple `has_active_sprite_movements() -> bool`) pour permettre au système de dialogue de vérifier l'état des mouvements en cours sans accéder directement aux attributs privés.

Cette contrainte garantit que les dialogues ne progressent pas pendant que des éléments visuels (sprites) sont en mouvement, améliorant la cohérence narrative et visuelle du jeu.

#### Contrainte de blocage du mouvement du joueur avec `set_x_position`

**Important** : Lorsqu'un échange de dialogue contient une configuration `player_animation` avec le champ `set_x_position` défini, le personnage principal doit rester à cette position tant que la bulle de dialogue n'est pas passée (c'est-à-dire tant que l'échange actuel est affiché). Les actions de déplacement du joueur sont désactivées pendant cette période.

- **Détection de la contrainte** : Lors de l'affichage d'un échange (dans `DialogueState._create_bubble_for_exchange`), le système doit vérifier si l'échange contient une configuration `player_animation` avec le champ `set_x_position` défini. Si c'est le cas, une contrainte de position est activée pour cet échange.

- **Blocage des contrôles de mouvement** : Pendant que l'échange avec `set_x_position` est actif :
  - Tous les inputs de mouvement du joueur (flèches directionnelles, touches WASD) doivent être ignorés
  - Le personnage principal doit rester à la position X définie par `set_x_position` (après conversion du repère de conception vers le repère de rendu)
  - Le système de mouvement du joueur (méthode `_handle_movement` dans `Player` ou équivalent) doit vérifier si une contrainte de position est active avant de traiter les inputs

- **Mécanisme de blocage** : 
  - Le `DialogueState` doit exposer une méthode pour vérifier si l'échange actuel impose une contrainte de position (par exemple `has_position_constraint() -> bool`)
  - Le système de mouvement du joueur doit interroger cette méthode via le `DialogueState` actif (accessible via le système de jeu principal)
  - Si une contrainte est active, le système de mouvement retourne immédiatement sans traiter les inputs, et la position X du joueur est maintenue à la valeur définie par `set_x_position`

- **Maintien de la position** : 
  - La position X du joueur doit être maintenue à la valeur définie par `set_x_position` (convertie en repère de rendu) à chaque frame tant que l'échange est actif
  - Cette vérification et correction de position doit être effectuée dans la méthode `update` du joueur ou dans la boucle principale du jeu, avant le traitement des inputs de mouvement

- **Fin de la contrainte** : La contrainte de position est levée automatiquement lorsque :
  - L'utilisateur passe à l'échange suivant (via clic lorsque le texte est complet)
  - Le dialogue se termine
  - Un nouvel échange sans `set_x_position` est affiché

- **Intégration** : Cette vérification doit être effectuée dans le système de mouvement du joueur (méthode `_handle_movement` ou équivalent dans `Player`). Le joueur doit avoir accès au `DialogueState` actif pour vérifier la présence d'une contrainte de position. Si aucun dialogue n'est actif, le comportement normal s'applique.

Cette contrainte garantit que le personnage principal reste à la position définie par `set_x_position` pendant toute la durée de l'échange de dialogue, empêchant le joueur de se déplacer et de perturber la scène narrative mise en place.

**Statut** : ✅ Implémenté

