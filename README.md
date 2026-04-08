# Moteur jeu présentation

**Moteur de jeu** de plateforme 2D développé avec Pygame (package Python **`moteur_jeu_presentation`**). Ce dépôt a notamment servi de support visuel à une **conférence**  : le contenu fourni (niveau d’exemple, assets, textes) illustre ce cadre, mais l’intérêt principal du projet est le **moteur** et ses formats de données documentés.

Lien de la conférence : https://www.youtube.com/watch?v=_bmrNjfNRew

## Description

Le moteur propose un jeu de plateforme 2D en vue de profil (side-scrolling) avec un système de rendu multi-couches (parallax scrolling) pour créer un effet de profondeur, ainsi que des systèmes de personnage, PNJ, événements, inventaire et dialogues. Le comportement attendu et la structure des fichiers de données sont décrits dans le dossier [`spec/`](spec/).

## Créer votre propre jeu

Pour décrire un jeu en s’appuyant sur les spécifications plutôt que sur le code, parcourir le répertoire [`spec/`](spec/) : chaque fichier numéroté documente un sous-système (syntaxe TOML, champs obligatoires, valeurs par défaut, interactions entre systèmes).

### Fichiers de niveau (`levels/`)

| Fichier | Rôle | Spécification de référence |
|---------|------|----------------------------|
| `*.niveau` | Décor : sprite sheets, couches de parallaxe, plateformes, collisions | [`spec/3-systeme-de-fichier-niveau.md`](spec/3-systeme-de-fichier-niveau.md) |
| `*.pnj` | Personnages non joueurs, blocs de dialogue | [`spec/12-systeme-de-personnage-non-joueur.md`](spec/12-systeme-de-personnage-non-joueur.md) |
| `*.event` | Déclencheurs d’événements selon la progression et actions associées | [`spec/11-systeme-gestion-avancement-niveau.md`](spec/11-systeme-gestion-avancement-niveau.md) |

Les positions et dimensions pertinentes restent exprimées dans le **repère de conception 1920×1080** (voir notamment les sections « Mode plein écran » et options de lancement ci-dessous).

### Fichiers de configuration (`config/`)

| Fichier | Rôle | Spécification de référence |
|---------|------|----------------------------|
| `player_stats.toml` | Niveau max, **`display_name`**, table **`[presentation]`** (listes `origins`, `class_role`, `traits` pour l’écran stats, obligatoires), stats par niveau, double saut, messages de transition | [`spec/7-systeme-de-niveaux-personnage.md`](spec/7-systeme-de-niveaux-personnage.md) |
| `inventory_items.toml` | Objets collectables, grilles de sprites, animations | [`spec/13-systeme-d-inventaire.md`](spec/13-systeme-d-inventaire.md) |

### Poursuivre avec les autres specs

Selon les besoins : personnage ([`spec/2-personnage-principal.md`](spec/2-personnage-principal.md)), bulles ([`spec/8-systeme-de-bulles-de-dialogue.md`](spec/8-systeme-de-bulles-de-dialogue.md)), physique et collisions ([`spec/4-systeme-de-physique-collisions.md`](spec/4-systeme-de-physique-collisions.md)), écran d’accueil ([`spec/16-ecran-d-accueil.md`](spec/16-ecran-d-accueil.md)), préchargement ([`spec/17-prechargement-elements-graphiques.md`](spec/17-prechargement-elements-graphiques.md)), particules ([`spec/14-moteur-de-particules.md`](spec/14-moteur-de-particules.md)), etc. Pour assembler un niveau jouable à partir des données, les specs **3**, **7**, **11**, **12** et **13** forment une base cohérente.

### Fichiers chargés au démarrage

Dans l’état actuel du dépôt, le point d’entrée référence explicitement les fichiers d’exemple `levels/niveau_plateforme.niveau`, `levels/niveau_plateforme.pnj` et `levels/niveau_plateforme.event` (voir `src/moteur_jeu_presentation/main.py`). Pour un autre jeu, réutiliser ces noms dans `levels/` ou adapter ces chemins dans le code.

## Prérequis

- Python >= 3.10
- [uv](https://github.com/astral-sh/uv) (gestionnaire de paquets Python)

### Compatibilité

Le projet n’a été **testé que sous macOS**. Linux ou Windows peuvent convenir (Python, Pygame, SDL), mais aucune validation systématique n’a été faite sur ces plateformes.

### Installation de uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Installation

1. Cloner le dépôt (ou naviguer vers le répertoire du projet)

2. Créer un environnement virtuel et installer les dépendances :

```bash
uv venv
source .venv/bin/activate  # Sur macOS/Linux
# ou
.venv\Scripts\activate  # Sur Windows

# Installer les dépendances
uv pip install -e .

# Installer les dépendances de développement (optionnel)
uv pip install -e ".[dev]"
```

## Lancement

Pour lancer le jeu avec uv :

```bash
uv run python -m moteur_jeu_presentation.main
```

Ou si un point d'entrée est configuré dans `pyproject.toml` :

```bash
uv run moteur_jeu_presentation
```

**Note** : Le jeu se lance automatiquement en mode plein écran. Un écran d'accueil s'affiche au démarrage avec l'image d'introduction. Cliquez sur le bouton "START" ou appuyez sur **Entrée** ou **Espace** pour lancer le niveau. Appuyez sur **ESC** pour afficher une boîte de confirmation avant de quitter le jeu.

### Options de lancement

#### Passer l'écran d'accueil

Pour le développement, vous pouvez sauter l'écran d'accueil et lancer directement le niveau :

```bash
uv run python -m moteur_jeu_presentation.main --skip-splash
```

Cette option est utile pour accélérer le développement en évitant d'avoir à cliquer sur le bouton START à chaque lancement.

#### Passer le préchargement des éléments graphiques

Pour le développement, vous pouvez sauter le préchargement des éléments graphiques (sprites, images, etc.) :

```bash
uv run python -m moteur_jeu_presentation.main --skip-preload
```

Cette option est utile pour accélérer le développement. **Note** : Sans le préchargement, les sprites seront chargés à la demande lors de leur premier affichage, ce qui peut causer de légers freezes.

### Préchargement des éléments graphiques

Le jeu inclut un système de préchargement complet de tous les éléments graphiques avant l'affichage de l'écran d'accueil :

- **Barre de progression** : Une barre de chargement s'affiche avec la progression globale (0% à 100%) et le nombre d'éléments chargés par catégorie
- **Progression continue** : La progression est mise à jour de manière continue pendant le chargement de chaque catégorie (après chaque élément chargé : sprite sheet, sprite extrait, frame, etc.), offrant un feedback visuel en temps réel
- **Catégories préchargées** :
  1. Sprites de niveau (sprite sheets + sprites redimensionnés)
  2. Sprites du joueur (toutes les frames de toutes les animations pour tous les niveaux)
  3. Sprites des PNJ (sprite sheets + sprites redimensionnés)
  4. Sprites d'inventaire (sprite sheets + sprites extraits)
  5. Images de dialogue
- **Optimisation** : Tous les éléments sont mis en cache dans des caches globaux partagés pour éviter les rechargements et garantir des performances optimales
- **Logs détaillés** : Des logs détaillés apparaissent dans la console pour chaque catégorie d'éléments chargés
- **Option de développement** : Utilisez `--skip-preload` pour sauter le préchargement (utile pour itérer rapidement)

#### Curseur personnalisé

Le jeu affiche un curseur personnalisé chargé depuis le dossier `sprite/cursor/` (par défaut `cursor.png`). L’image est utilisée via l’API Pygame (`pygame.mouse.set_cursor`). La taille de l’image est libre ; en cas d’absence du fichier, le curseur système est conservé.

#### Masquer les informations de position du joueur

Pour masquer les éléments de positionnement du joueur affichés en haut à gauche (HUD de progression) :

```bash
uv run python -m moteur_jeu_presentation.main --hide-info-player
```

Cette option masque le HUD de progression qui affiche la position horizontale du joueur et le pourcentage de progression dans le niveau. **Note** : Même si le HUD est masqué, le système de suivi de progression continue de fonctionner en arrière-plan pour les autres systèmes qui en dépendent (déclencheurs d'événements, dialogues, etc.).

Vous pouvez combiner toutes les options :

```bash
uv run python -m moteur_jeu_presentation.main --skip-splash --skip-preload --hide-info-player
```

#### Accélération GPU Metal (macOS uniquement)

Sur macOS, vous pouvez activer l'accélération GPU Metal pour améliorer les performances de rendu :

```bash
uv run python -m moteur_jeu_presentation.main --mps
# ou
uv run python -m moteur_jeu_presentation.main --metal
# optionnel : activer les logs de timings Metal
uv run python -m moteur_jeu_presentation.main --mps --profiling-metal
```

Lorsque cette option est activée, le moteur configure automatiquement `SDL_VIDEODRIVER=cocoa`, `SDL_RENDER_DRIVER=metal` et `SDL_HINT_RENDER_SCALE_QUALITY=2` pour forcer le renderer Metal natif de SDL2 et bénéficier de la meilleure qualité de mise à l'échelle matérielle. 

L'option `--profiling-metal` (qui nécessite `--mps`) active :
- L'affichage du FPS en temps réel en haut à droite de l'écran
- Des logs de statistiques de rendu (moyenne ms/fps) dans la console toutes les secondes

Sur les autres plateformes, ou si l'initialisation échoue, le jeu revient automatiquement au chemin de rendu standard.

#### Position X initiale du personnage

Pour le développement et le débogage, vous pouvez définir la position X initiale du personnage principal au démarrage du jeu :

```bash
# Lancer le jeu avec le personnage à la position X = 960 pixels (centre dans le repère 1920x1080)
uv run python -m moteur_jeu_presentation.main --player-x 960

# Lancer le jeu avec le personnage à la position X = 0 (début du niveau dans le repère 1920x1080)
uv run python -m moteur_jeu_presentation.main --start-x 0

# Lancer le jeu avec le personnage à la position X = 1920 (fin de l'écran dans le repère 1920x1080)
uv run python -m moteur_jeu_presentation.main --player-x 1920

# Combiner avec d'autres options
uv run python -m moteur_jeu_presentation.main --player-x 1000 --skip-splash --mps
```

**Important** : Les valeurs de position X sont dans le **repère de conception (1920x1080)**. Elles sont automatiquement converties vers le repère de rendu interne (1920x1080) lors de l'initialisation (actuellement identique, mais le principe de séparation est conservé).

Par défaut, le personnage est positionné au centre de l'écran (`render_width / 2` dans le repère de rendu). La caméra s'ajuste automatiquement à la position initiale du personnage.

**Note** : Aucune validation de limites n'est effectuée, le personnage peut être positionné en dehors de l'écran visible ou dans une zone avec des collisions.

Pour voir toutes les options disponibles :

```bash
uv run python -m moteur_jeu_presentation.main --help
```

## Structure du projet

Après clonage, le dossier racine porte souvent le nom du dépôt Git ; ci-dessous, **racine du projet** et **package Python** sont nommés comme le module importable `moteur_jeu_presentation`.

```
moteur_jeu_presentation/
├── src/
│   └── moteur_jeu_presentation/          # Package Python (import)
│       ├── __init__.py
│       ├── main.py          # Point d'entrée du jeu
│       ├── game/            # Logique de gameplay (progression, HUD, etc.)
│       │   ├── __init__.py
│       │   ├── progress.py  # Suivi de progression du joueur dans le niveau
│       │   ├── events.py    # Système de déclencheurs d'événements
│       │   └── hud/
│       │       ├── __init__.py
│       │       └── progress.py  # HUD d'affichage de la progression horizontale
│       ├── entities/        # Entités du jeu
│       │   ├── __init__.py
│       │   ├── player.py    # Classe Player
│       │   └── npc.py       # Classe NPC
│       ├── levels/          # Système de fichiers de niveau
│       │   ├── npc_loader.py  # Chargeur de fichiers de PNJ
│       │   ├── __init__.py
│       │   ├── config.py    # Classes LevelConfig, RowMapping, SpriteMapping
│       │   └── loader.py    # Classe LevelLoader
│       ├── stats/           # Système de caractéristiques du personnage
│       │   ├── __init__.py
│       │   ├── config.py    # Classes PlayerStatsConfig, StatDefinition
│       │   └── loader.py    # Classe PlayerStatsLoader
│       ├── inventory/       # Système d'inventaire
│       │   ├── __init__.py
│       │   ├── config.py    # Classes InventoryItem, InventoryItemConfig, ItemAnimationState
│       │   ├── loader.py    # Classe InventoryItemLoader
│       ├── ui/              # Interface utilisateur
│       │   ├── __init__.py
│       │   ├── splash_screen.py  # Écran d'accueil
│       │   ├── quit_confirmation.py  # Boîte de confirmation de quitter
│       │   ├── player_stats_display.py  # Affichage des statistiques du joueur
│       │   └── speech_bubble.py  # Bulles de dialogue
│       │   └── inventory.py # Classe Inventory
│       ├── particles/       # Moteur de particules
│       │   ├── __init__.py
│       │   ├── particle.py  # Classe Particle
│       │   ├── effect.py    # Classes ParticleEffect, ParticleEffectConfig
│       │   ├── system.py    # Classe ParticleSystem
│       │   └── utils.py     # Utilitaires (extract_dominant_color, configurations prédéfinies)
│       ├── physics/         # Système de physique et collisions
│       │   ├── __init__.py
│       │   └── collision.py # Classe CollisionSystem
│       ├── ui/              # Interface utilisateur
│       │   ├── __init__.py
│       │   ├── speech_bubble.py  # Bulles de dialogue
│       │   └── player_stats_display.py  # Interface d'affichage des statistiques
│       ├── rendering/       # Système de rendu
│       │   ├── __init__.py
│       │   ├── layer.py     # Classe Layer
│       │   └── parallax.py  # Classe ParallaxSystem
├── spec/                    # Spécifications techniques
│   ├── 1-systeme-de-couches-2d.md
│   ├── 2-personnage-principal.md
│   ├── 3-systeme-de-fichier-niveau.md
│   ├── 4-systeme-de-physique-collisions.md
│   ├── 5-mode-plein-ecran.md
│   ├── 6-systeme-de-saut.md
│   ├── 7-systeme-de-niveaux-personnage.md
│   ├── 8-systeme-de-bulles-de-dialogue.md
│   ├── 9-acceleration-graphique-mps-mac.md
│   ├── 10-affichage-statistiques-joueur.md
│   ├── 11-systeme-gestion-avancement-niveau.md
│   ├── 12-systeme-de-personnage-non-joueur.md
│   ├── 13-systeme-d-inventaire.md
│   ├── 14-moteur-de-particules.md
│   └── 17-prechargement-elements-graphiques.md
├── config/                  # Fichiers de configuration
│   ├── player_stats.toml   # Caractéristiques du personnage par niveau
│   └── inventory_items.toml  # Configuration des objets d'inventaire
├── levels/                  # Fichiers de niveau
│   ├── niveau_plateforme.niveau
│   ├── niveau_plateforme.pnj  # Configuration des PNJ
│   └── niveau_plateforme.event  # Configuration des événements
├── image/                   # Images pour les bulles de dialogue
│   └── *.png               # Images utilisées dans les dialogues des PNJ
├── sprite/                  # Sprites du jeu
│   ├── personnage/
│   │   ├── 1/
│   │   │   ├── walk.png     # Assets niveau 1 (marche)
│   │   │   └── jump.png     # Assets niveau 1 (saut)
│   │   ├── 2/
│   │   ├── 3/
│   │   ├── 4/
│   │   └── 5/
│   ├── items/               # Sprite sheets des objets d'inventaire
│   │   └── outils_all_v3.png
│   ├── interface/           # Images d'interface
│   │   ├── image-intro.png  # Image d'introduction (écran d'accueil)
│   │   └── affichage_personnage.png  # Image de fond pour l'affichage des statistiques
│   ├── background.png
│   ├── nuage.png
│   └── terrain-montage.png
├── pyproject.toml           # Configuration du projet
├── README.md                # Ce fichier
└── bonne_pratique.md        # Guide de bonnes pratiques
```

## Fonctionnalités

### Écran d'accueil

Le jeu affiche un écran d'accueil en plein écran au démarrage :
- **Image d'introduction** : Affiche l'image `sprite/interface/image-intro.png` en plein écran
- **Fond coloré** : Un fond de couleur RGB(74, 149, 172) / #4a95ac s'affiche derrière l'image
- **Effet de survol** : Le fond passe en rouge lorsque la souris survole le bouton "START"
- **Bouton START** : Cliquez sur le bouton "START" visible dans l'image pour lancer le niveau
- **Raccourcis clavier** : Appuyez sur **Entrée** ou **Espace** pour lancer le niveau directement
- **Quitter** : Appuyez sur **ESC** pour afficher une boîte de confirmation avant de quitter depuis l'écran d'accueil
- **Mise à l'échelle automatique** : L'image s'adapte automatiquement à la résolution de l'écran tout en préservant son ratio d'aspect
- **Option de développement** : Utilisez `--skip-splash` pour sauter l'écran d'accueil et lancer directement le niveau (utile pour itérer rapidement)

### Mode plein écran

Le jeu se lance automatiquement en mode plein écran pour une expérience immersive :
- **Résolution interne** : 1920x1080 (16:9) pour une qualité d'image optimale
- **Mise à l'échelle automatique** : S'adapte à la résolution de votre écran avec letterboxing si nécessaire
- **Quitter le jeu** : Appuyez sur **ESC** pour afficher une boîte de confirmation avant de quitter. La boîte propose deux boutons cliquables avec la souris : "Oui" (vert) pour confirmer la sortie et "Non" (rouge) pour annuler. Vous pouvez également utiliser **Entrée** pour confirmer ou **ESC** pour annuler.
- **Fichiers de configuration** : Les fichiers `.niveau`, `.pnj` et `.event` restent exprimés dans le repère de conception 1920x1080 ; le moteur convertit dynamiquement ces valeurs lors du lancement pour la résolution interne 1920x1080 (actuellement identique, mais le principe de séparation est conservé pour permettre des ajustements futurs).

### Personnage principal avec animations

Le jeu inclut un personnage principal contrôlable avec des animations de marche et de saut :

- **Contrôles** : Flèches directionnelles ou touches WASD pour se déplacer
- **Saut** : Flèche haut ou touche W pour sauter (uniquement au sol)
- **Double saut** : À partir du niveau 3, le joueur peut effectuer un double saut en l'air. Pour déclencher le double saut, relâchez la touche de saut après le premier saut, puis réappuyez sur la touche de saut pendant que vous êtes en l'air
- **Changement de niveau** : Touche `P` pour augmenter le niveau du personnage (jusqu'à 5) et touche `O` pour le diminuer (jusqu'à 1)
- **Level up** : Lorsqu'un événement de level up est déclenché, un message "level up (press u)" apparaît en jaune clignotant au-dessus du personnage. Appuyez sur la touche `U` pour confirmer le level up, ce qui déclenche une animation de transition de niveau spectaculaire en trois phases :
  - **Phase 1 - Zoom avant** : Un zoom de caméra de 230% est appliqué progressivement sur le joueur en 1 seconde
  - **Phase 2 - Affichage de transition** : Pendant 1.5 secondes, le texte "level [niveau actuel] -> level [nouveau niveau]" s'affiche centré à l'écran en grand, accompagné d'une phrase d'amélioration (si configurée dans `config/player_stats.toml`) affichée en dessous en taille moyenne et en gris foncé. Le sprite du personnage alterne entre l'ancien et le nouveau niveau toutes les 0.2 secondes. Le zoom reste à 230% pendant cette phase
  - **Phase 3 - Reset du zoom** : Le zoom de caméra est réinitialisé progressivement à 100% en 1 seconde
  - **Confettis** : Des confettis sont émis en continu depuis les coins du cadre de texte pendant la phase d'affichage uniquement
  - **Blocage complet** : Pendant toute la durée de l'animation (3.5 secondes au total), le joueur est complètement bloqué (pas de mouvement, pas d'interactions)
  - **Fin automatique** : L'animation se termine automatiquement après 3.5 secondes (1.0s + 1.5s + 1.0s), et le personnage reste sur le nouveau niveau
  - **Messages d'amélioration** : Les phrases d'amélioration sont configurées dans `config/player_stats.toml` dans la section `[level_up_messages]` avec les clés `level_2`, `level_3`, `level_4`, `level_5`. Les messages sont optionnels et peuvent contenir des retours à la ligne (`\n`) pour des messages multi-lignes
- **Affichage des statistiques** : Touche `S` pour afficher/masquer l'interface des statistiques du joueur (mode pause)
- **Animations** : Animations de marche fluides pour les directions gauche et droite
- **Animations de saut** : Animations de saut spécifiques pour les directions gauche et droite (5 frames par direction)
- **Sprite sheet** : Système d'animation basé sur des sprite sheets (8 frames par direction pour la marche, 5 frames par direction pour le saut)
- **Caméra** : La caméra suit automatiquement le personnage
- **Affichage du nom** : Le texte défini par la clé racine **`display_name`** dans `config/player_stats.toml` s'affiche centré au-dessus de la tête du personnage (style pixel/retro) et dans le titre de l'écran statistiques ; le jeu **exige** un fichier `player_stats.toml` valide au démarrage
- **Système d'inventaire** : Le joueur possède un inventaire qui affiche visuellement les objets collectés au-dessus du prénom. Les objets sont définis dans `config/inventory_items.toml` et utilisent des sprite sheets avec un système de cellules. Les objets peuvent être ajoutés/retirés via l'API `player.inventory.add_item()` et `player.inventory.remove_item()`. Le système inclut des animations visuelles spectaculaires :
  - **Animation d'ajout** : Les objets apparaissent au centre de l'écran à une taille 10 fois plus grande que la normale, puis diminuent progressivement de taille (de 10x à 1x) tout en se déplaçant vers leur position finale dans l'inventaire. L'animation inclut un effet de fade-in (0.6 secondes par défaut)
  - **Animation de suppression** : Les objets partent de leur position actuelle dans l'inventaire et se déplacent vers le centre de l'écran en augmentant progressivement de taille (de 1x à 10x). Au moment où l'objet atteint le centre de l'écran, des particules de flamme colorées explosent depuis le centre. Les particules utilisent une palette de couleurs chaudes (rouge, orange, jaune) avec une variation importante pour créer un effet de flamme colorée et dynamique, indépendamment de la couleur de l'objet. Les particules sont également agrandies d'un facteur 10 pour correspondre à la taille de l'objet au moment de l'explosion. L'animation complète dure 0.7 secondes par défaut, avec l'explosion déclenchée à 80% de l'animation. L'effet est dynamique et voyant pour attirer l'attention du joueur. Les particules utilisent le **moteur de particules** (spécification 14) pour créer des effets visuels réutilisables
- **Moteur de particules** : Système réutilisable pour créer des effets de particules configurables (explosion, explosion de flamme, pluie, fumée, étincelles, etc.). Le moteur peut être utilisé par différents systèmes (inventaire, combat, environnement) pour déclencher des effets visuels dynamiques. Les explosions incluent des effets avancés : friction (ralentissement progressif), gravité (chute progressive), rétrécissement progressif des particules, et variations de taille et couleur pour un rendu plus réaliste et spectaculaire. L'explosion de flamme utilise une palette de couleurs chaudes (rouge, orange, jaune) avec une variation importante pour créer un effet de flamme colorée et dynamique, indépendamment de la couleur de l'objet source. Voir la spécification 14 pour plus de détails
- **Bulles de dialogue** : Système de bulles de dialogue pour afficher du texte et/ou des images associés à un personnage (touche `B` pour afficher/masquer une bulle d'exemple)
  - **Animation du texte** : Les lettres apparaissent progressivement au fur et à mesure (30 caractères par seconde par défaut)
  - **Accélération par clic** : Cliquer n'importe où sur l'écran affiche immédiatement tout le texte restant
  - **Support des images** : Les bulles peuvent contenir des images (placées dans le répertoire `image`). Lorsqu'une image est présente, la bulle est centrée dans l'écran, prend le maximum d'espace disponible, et l'image est redimensionnée pour s'adapter à cette taille. Les images sont affichées au-dessus du texte si les deux sont présents
- **Système de dialogues avec PNJ** : Déclenchement de dialogues avec les PNJ basé sur la position du joueur dans le monde
  - **Indication visuelle** : Lorsque le joueur s'approche d'un PNJ, une indication s'affiche au-dessus du PNJ avec une animation de pulsation. Pour qu'un PNJ soit considéré comme interactif, **deux conditions doivent être remplies** :
    1. **Distance horizontale** : Le PNJ doit être à moins de 200 pixels horizontalement du joueur
    2. **Distance verticale** : Le joueur et le PNJ doivent être à peu près à la même hauteur (différence de Y <= 100 pixels)
    Cette vérification garantit que le dialogue ne peut être déclenché que si le joueur et le PNJ sont sur le même niveau ou des niveaux très proches (par exemple, sur la même plateforme ou des plateformes adjacentes).
    Le type d'indicateur dépend du type de dialogue du bloc correspondant à la position actuelle du joueur :
    - **Type "normal"** (par défaut) : Affiche "T pour parler"
    - **Type "quête"** : Affiche un "!" (point d'exclamation), similaire aux MMO RPG, pour indiquer qu'une quête est disponible
    - **Type "discution"** : Affiche "T pour ecouter et donner son avis" pour indiquer qu'il s'agit d'une discussion où le joueur peut écouter et donner son avis
    - **Type "ecoute"** : Affiche "T pour écouter" pour indiquer qu'il s'agit d'une écoute où le joueur peut simplement écouter sans donner son avis
    - **Type "regarder"** : Affiche "T pour regarder ce que c'est" pour indiquer que le dialogue permet au joueur d'examiner quelque chose
    - **Type "enseigner"** : Affiche "T pour former" pour indiquer qu'il s'agit d'une formation où le joueur peut apprendre quelque chose
    - **Type "reflexion"** : Affiche "T pour reflechir" pour indiquer que le dialogue permet au joueur de réfléchir sur quelque chose
  - L'indication utilise une taille de police doublée (28 pixels) et une couleur jaune pour se distinguer clairement des noms des PNJ (qui sont en blanc).
  - **Interaction** : Appuyez sur la touche `T` pour lancer un dialogue avec le PNJ le plus proche qui respecte les conditions d'interaction (si aucun dialogue n'est en cours)
  - **Sélection automatique** : Si plusieurs PNJ sont à portée, le système sélectionne automatiquement le plus proche horizontalement

### Système de niveaux du personnage

- **Niveaux disponibles** : de 1 à **`max_level`** défini dans `config/player_stats.toml` (clé racine ; défaut **5** si absent), avec un set d'assets par niveau sous `sprite/personnage/<n>/`
- **Organisation des assets** : Chaque niveau possède son propre répertoire `sprite/personnage/<niveau>/` contenant au minimum `walk.png` et `jump.png`
- **Sélection automatique** : Le niveau est lu depuis la section `[player]` du fichier `.niveau` et appliqué lors de l'initialisation de `Player` (la valeur doit être ≤ `max_level`)
- **Changement dynamique** : L'API `player.set_level(niveau)` recharge automatiquement les sprite sheets du niveau cible
- **Fallback géré** : Une erreur claire est levée si un asset requis est manquant pour le niveau configuré

#### Système de caractéristiques par niveau

Le personnage possède des caractéristiques (statistiques) qui évoluent selon son niveau :

- **Fichier de configuration** : `config/player_stats.toml` définit la clé racine **`display_name`** (chaîne non vide, obligatoire), la table **`[presentation]`** avec trois tableaux de chaînes non vides **`origins`**, **`class_role`**, **`traits`** (textes de la colonne présentation de l’écran statistiques, obligatoires — voir spec **7** et **10**), la clé racine **`max_level`** (niveau maximum du personnage), la clé racine optionnelle **`double_jump_unlock_level`** (niveau minimal pour autoriser le double saut, entre 1 et `max_level`, défaut **3** si absent), et pour chaque stat les valeurs `level_1` … `level_{max_level}`
- **Caractéristiques disponibles** : Force, Intelligence, Vitesse (configurables dans le fichier TOML)
- **Valeur maximale personnalisée** : Chaque caractéristique peut avoir une valeur maximale explicite (`max_value`) indépendante de la valeur au dernier niveau. Si non définie, la valeur maximale utilisée pour l'affichage est celle de `level_{max_level}`
- **Tooltips par niveau** : Chaque caractéristique peut avoir des tooltips (`tooltip_level_1` … `tooltip_level_{max_level}`), affichés au survol de l'icône d'information dans l'interface des statistiques
- **Application automatique** : Les caractéristiques sont chargées au démarrage et appliquées au personnage
- **Influence sur le gameplay** : La caractéristique "vitesse" modifie automatiquement la vitesse de déplacement du personnage
- **Accès aux valeurs** : Les propriétés `player.force`, `player.intelligence`, et `player.vitesse` permettent d'accéder aux valeurs actuelles
- **Mise à jour dynamique** : Lors d'un changement de niveau (touches `P`/`O`), les caractéristiques et les tooltips sont automatiquement mises à jour

**Format du fichier de caractéristiques** (`config/player_stats.toml`) :

```toml
max_level = 5
double_jump_unlock_level = 3
display_name = "Nom affiché du personnage"

[presentation]
origins = ["Ligne 1 (puce)", "Ligne 2"]
class_role = ["Classe : …", "Rôle : …"]
traits = ["Trait A", "Trait B"]

[stats.force]
name = "Force"
description = "Puissance physique du personnage"
tooltip_level_1 = "Force de base : Vous commencez votre aventure avec une force modeste."
tooltip_level_2 = "Force améliorée : Votre entraînement porte ses fruits."
tooltip_level_3 = "Force avancée : Votre force physique est remarquable."
tooltip_level_4 = "Force experte : Vous maîtrisez parfaitement votre force brute."
tooltip_level_5 = "Force maîtrisée : Vous avez atteint le summum de la puissance physique."
level_1 = 10
level_2 = 20
level_3 = 35
level_4 = 55
level_5 = 80

[stats.intelligence]
name = "Intelligence"
description = "Capacité intellectuelle du personnage"
tooltip_level_1 = "Intelligence de base : Votre esprit est vif mais encore en développement."
tooltip_level_2 = "Intelligence améliorée : Votre compréhension s'approfondit."
tooltip_level_3 = "Intelligence avancée : Votre sagesse est reconnue."
tooltip_level_4 = "Intelligence experte : Votre intellect est exceptionnel."
tooltip_level_5 = "Intelligence maîtrisée : Votre sagesse est légendaire."
level_1 = 8
level_2 = 18
level_3 = 32
level_4 = 52
level_5 = 75

[stats.vitesse]
name = "Vitesse"
description = "Rapidité de déplacement du personnage"
tooltip_level_1 = "Vitesse de base : Vous vous déplacez à un rythme normal."
tooltip_level_2 = "Vitesse améliorée : Vos réflexes s'aiguisent."
tooltip_level_3 = "Vitesse avancée : Votre agilité est remarquable."
tooltip_level_4 = "Vitesse experte : Vos mouvements sont presque instantanés."
tooltip_level_5 = "Vitesse maîtrisée : Vous êtes d'une rapidité légendaire."
level_1 = 12
level_2 = 22
level_3 = 38
level_4 = 58
level_5 = 85
max_value = 100  # Optionnel : valeur maximale explicite (si non défini, utilise level_5)
```

Si le fichier est absent ou invalide, le jeu continue de fonctionner sans caractéristiques (valeurs par défaut).

#### Interface d'affichage des statistiques

Le jeu inclut une interface graphique de type RPG pour afficher les statistiques du joueur :

- **Affichage/masquage** : Appuyez sur la touche `S` pour afficher ou masquer l'interface
- **Mode pause** : Lorsque l'interface est affichée, le jeu est en pause (le personnage ne bouge pas)
- **Image de fond** : L'interface utilise l'image `sprite/interface/affichage_personnage.png` comme fond du panneau, redimensionnée pour s'adapter aux dimensions du panneau tout en conservant ses proportions. L'image contient deux zones distinctes :
  - **Panneau rectangulaire supérieur** : Panneau rectangulaire central situé dans la section supérieure du cadre en bois, utilisé pour afficher le nom et le niveau du personnage
  - **Panneau central principal** : Grand panneau central sombre utilisé pour afficher le sprite, la présentation et les statistiques
- **Polices pixel art** : L'interface utilise des polices pixel art spécifiques pour chaque type d'élément :
  - **VT323** : Pour tous les éléments de texte de l'interface (nom du personnage, niveau, texte de présentation, statistiques, tooltips, icônes) - look rétro CRT, très lisible
  - **Silkscreen** : Pour les titres de section (Origines, Classe & Rôle, Traits de caractère)
  - Les polices sont recherchées dans le répertoire `fonts/` du projet, puis dans les répertoires système, avec fallback vers des polices système par défaut si elles ne sont pas trouvées
- **Section titre** : Le nom du personnage avec le niveau entre parenthèses est affiché dans le panneau rectangulaire supérieur de l'image de fond, centré horizontalement et verticalement dans ce panneau (format : "NOM DU PERSONNAGE (Niveau: X)", couleur dorée, taille importante). Le niveau se met à jour automatiquement lors d'un changement de niveau
- **Section de présentation du personnage** : Une section de présentation de style RPG est affichée dans la colonne droite de la section supérieure du panneau central principal. Les trois blocs **Origines**, **Classe & Rôle** et **Traits de caractère** sont remplis par les tableaux **`origins`**, **`class_role`** et **`traits`** de la table **`[presentation]`** dans `config/player_stats.toml` (une chaîne = une puce ; pas de valeurs par défaut dans le code). Le texte de présentation utilise une police de 18 pixels par défaut (dans le repère 1920x1080, ajustée selon le facteur d'échelle) pour améliorer la lisibilité
- **Affichage du personnage** : Le sprite du joueur est affiché dans un bloc dédié dans la colonne gauche du panneau central principal, centré horizontalement et verticalement dans ce bloc, aligné verticalement avec le centre de la section de présentation, à 400% de sa taille originale
- **Animation de rotation** : Le sprite du joueur tourne sur lui-même en affichant successivement les 4 directions (haut, bas, gauche, droite) avec un timing fixe de 0.5 seconde par direction
- **Jauges colorées** : Chaque statistique est affichée sous forme de jauge avec un code couleur :
  - Rouge : 0-33% (faible)
  - Orange : 34-66% (moyen)
  - Vert : 67-100% (élevé)
- **Indicateur de progression** : Un symbole "^" en jaune s'affiche à côté du nom de chaque statistique qui a progressé par rapport au niveau précédent. L'indicateur ne s'affiche pas au niveau 1 (pas de niveau précédent) et se met à jour automatiquement lors des changements de niveau
- **Icône d'information** : Chaque jauge est accompagnée d'une icône "I" dans un cercle (32 pixels dans le repère 1920x1080, ajustée selon le facteur d'échelle) à la fin de la jauge
- **Tooltips explicatifs** : Survoler l'icône "I" avec la souris affiche un tooltip contenant un texte explicatif détaillé de la statistique pour le niveau actuel du personnage. Le tooltip utilise une police de 21 pixels (dans le repère 1920x1080, ajustée selon le facteur d'échelle) pour améliorer la lisibilité des descriptions détaillées. Le tooltip change automatiquement lorsque le niveau du personnage change (touches `P`/`O`)
- **Layout optimisé** : L'interface utilise un layout en 3 sections :
  - **Section titre** : Nom du personnage dans le panneau rectangulaire supérieur de l'image de fond
  - **Section supérieure (panneau central)** : Sprite du personnage dans un bloc à gauche (centré verticalement), section de présentation à droite
  - **Section inférieure (panneau central)** : Statistiques organisées en 2 colonnes égales avec des polices adaptées (21 pixels par défaut dans le repère 1920x1080, ajustées selon le facteur d'échelle) pour optimiser l'espace tout en conservant la lisibilité, et des barres de hauteur 19 pixels par défaut (ajustées selon le facteur d'échelle)
- **Lisibilité améliorée** : 
  - Tailles de police garanties avec minimums après mise à l'échelle pour éviter que l'interface devienne illisible
  - Contraste amélioré avec des couleurs de texte plus claires (240, 240, 240) et des barres avec fond plus clair (80, 80, 80)
  - Bordures plus visibles (180, 180, 180, épaisseur 2 pixels) pour les barres de statistiques
  - Espacements minimaux garantis entre les éléments pour une meilleure séparation visuelle
- **Mise à jour dynamique** : Les statistiques, le sprite et les tooltips se mettent à jour automatiquement lors d'un changement de niveau
- **Adaptation à la résolution** : L'interface s'adapte automatiquement à la résolution de l'écran pour maintenir une bonne lisibilité sur différentes résolutions. Toutes les valeurs par défaut sont exprimées directement dans le repère 1920x1080 et sont ajustées avec `compute_scale()` pour s'adapter à la résolution d'affichage réelle

### Suivi d'avancement dans le niveau

- **HUD permanent** : `LevelProgressHUD` affiche en haut à gauche le nombre de pixels horizontaux parcourus (`xxxxx px`), indépendamment de la position de la caméra.
- **Ratio automatique** : Lorsque la largeur totale du niveau est connue, un pourcentage de progression s'affiche sous la valeur principale.
- **Mode debug** : Un flag optionnel permet d'afficher également le maximum atteint depuis le début du niveau.
- **Source de vérité centralisée** : `LevelProgressTracker` conserve la position monde courante, le maximum atteint, un historique glissant et des jalons (`ProgressMilestone`) prêts à être consommés par de futurs systèmes (déclencheurs narratifs, scripts, récompenses, etc.).
- **API prête pour l'extension** : L'instance expose `get_state()`, `get_triggered_milestones()` et des méthodes d'enregistrement de jalons pour faciliter les interactions futures.
- **Système de déclencheurs d'événements** : Le système `EventTriggerSystem` permet de déclencher des événements automatiques basés sur la progression du joueur (voir section "Système de déclencheurs d'événements" ci-dessus).

### Système de parallaxe multi-couches

Le jeu utilise un système de 4 couches de profondeur pour créer un effet de parallaxe :

1. **Background (Arrière-plan)** : Couche la plus éloignée, défile le plus lentement (depth 0) - **Rendue derrière le joueur**
2. **Premier fond** : Couche intermédiaire arrière, défile à vitesse moyenne-lente (depth 1) - **Rendue derrière le joueur**
3. **Éléments de gameplay** : Couche principale où évolue le personnage, défile à la vitesse de la caméra (depth 2) - **Rendue devant le joueur**
4. **Premier plan (Foreground)** : Couche la plus proche, défile le plus rapidement (depth 3) - **Rendue devant le joueur**

**Ordre de rendu** : Les couches de depth 0 et 1 sont rendues derrière le joueur, ainsi que les couches de depth 2 avec `is_background = true`. Les couches de depth 2 sans `is_background` ni `is_foreground` (plateformes normales) sont rendues devant le joueur, suivies des couches de depth 2 avec `is_foreground = true` (foreground devant les plateformes), puis des couches de depth 3 (foreground classique). Cela permet de créer un effet de profondeur où certains éléments de décor passent devant le personnage, tout en permettant d'avoir des décors à la même profondeur que les plateformes mais sans collision, et des décors de foreground qui passent devant les plateformes.

### Système de fichiers de niveau

Le jeu permet de définir les décors via des fichiers de niveau au format TOML. Le jeu charge automatiquement le fichier `levels/niveau_plateforme.niveau` au démarrage. Chaque fichier de niveau spécifie :
- **Plusieurs sprite sheets** : Possibilité de déclarer plusieurs sprite sheets avec des noms uniques dans `[sprite_sheets]`
- **Référence au sprite sheet** : Chaque ligne ou sprite individuel peut référencer le sprite sheet à utiliser via le champ `sheet`
- **Format rétrocompatible** : Le format `[sprite_sheet]` (singulier) reste supporté pour un seul sprite sheet
- L'association des lignes du sprite sheet aux couches de profondeur
- Des sprites individuels avec répétition pour créer des plateformes ou éléments spécifiques
- La répétition horizontale (`count_x`) pour répéter un sprite horizontalement
- **Sprites personnalisés pour `count_x > 3`** : Pour les sprites avec `count_x > 3`, il est possible de définir optionnellement le premier et le dernier sprite différemment du sprite de base :
  - `first_sprite_row` et `first_sprite_col` : Coordonnées du sprite à utiliser pour le premier élément de la séquence horizontale (optionnel, uniquement si `count_x > 3`)
  - `last_sprite_row` et `last_sprite_col` : Coordonnées du sprite à utiliser pour le dernier élément de la séquence horizontale (optionnel, uniquement si `count_x > 3`)
  - Les sprites intermédiaires utilisent toujours le sprite de base (`row` et `col`)
  - Cette fonctionnalité permet de créer des structures visuellement plus variées, comme des plateformes avec des extrémités différentes du corps central
- La répétition verticale (`count_y`) pour répéter un sprite verticalement vers le haut (optionnel, défaut: 1). Le sprite le plus bas est positionné à `y_offset`, et les sprites suivants sont empilés vers le haut avec un espacement de `spacing_y` entre chaque répétition
- La position verticale (`y_offset`) pour positionner le sprite le plus bas à différentes hauteurs (mesurée depuis le **haut** de l'écran)
- L'offset horizontal (`x_offset`) pour corriger le spacing des sprites répétés
- L'espacement horizontal (`spacing`) pour ajuster l'espacement entre les sprites horizontalement (pour les lignes complètes et les sprites individuels)
- L'espacement vertical (`spacing_y`) pour ajuster l'espacement entre les sprites verticalement lors de la répétition verticale (optionnel, défaut: 0.0)
- La distance entre répétitions infinies (`infinite_offset`) pour créer un espacement entre chaque répétition infinie de la couche (uniquement si `is_infinite = true`)
- Le paramètre `is_infinite` pour contrôler si une couche se répète horizontalement à l'infini (par défaut: `true`)
- Le redimensionnement (`scale`) pour redimensionner les sprites individuellement (en pourcentage, défaut: 1.0 = 100%) tout en conservant automatiquement la même position du bas
- **Paramètre `is_background`** : Pour les sprites de depth 2, permet de créer des décors qui s'affichent derrière le joueur et n'ont pas de collision (défaut: `false`). Utile pour créer des décors à la même profondeur que les plateformes mais sans collision.
- **Paramètre `is_foreground`** : Pour les sprites de depth 2, permet de créer des décors qui s'affichent devant les autres éléments de depth 2 (plateformes normales) mais restent devant le joueur, sans collision (défaut: `false`). Utile pour créer des décors de foreground qui passent devant les plateformes. **Note** : `is_background` et `is_foreground` sont mutuellement exclusifs. Si les deux sont définis à `true`, `is_background` a la priorité.
- **Tags de sprites** : Les sprites peuvent être tagués avec des identifiants pour être référencés dans les événements (par exemple, pour les masquer ou les afficher dynamiquement)
- **Opacité initiale** : Les sprites peuvent avoir une opacité initiale (`initial_alpha`) définie dans le fichier de niveau (0-255, défaut: 255 = complètement opaque). Les sprites avec `initial_alpha = 0` commencent invisibles et peuvent être affichés via un événement `sprite_show`. Les collisions sont automatiquement désactivées pour les sprites avec `initial_alpha = 0`
- Les vitesses de défilement sont automatiquement configurées selon la profondeur
- **Ordre de rendu** : Les couches de depth 0 et 1 sont rendues derrière le joueur, ainsi que les couches de depth 2 avec `is_background = true`. Les couches de depth 2 sans `is_background` ni `is_foreground` (plateformes normales) sont rendues devant le joueur, suivies des couches de depth 2 avec `is_foreground = true` (foreground devant les plateformes), puis des couches de depth 3 (foreground classique)

### Système de physique et collisions

Le jeu inclut un système de physique et de collisions :
- **Gravité** : Le personnage est soumis à la gravité et tombe vers le bas (800 pixels/s² par défaut)
- **Collisions** : Le personnage ne peut pas traverser les tiles de profondeur 2 (depth 2) de tous les côtés (haut, bas, gauche, droite), à l'exception des tiles avec `is_background = true` ou `is_foreground = true` qui n'ont pas de collision
- **Collisions latérales** : Le personnage ne peut pas traverser les tiles en se déplaçant vers la gauche ou la droite
- **Collisions verticales** : Le personnage ne peut pas traverser les tiles par le haut (plafond) ou le bas (sol/plateforme)
- **Filtrage des collisions arrière** : Les collisions horizontales avec des tiles situés à l'arrière du joueur (par rapport à sa direction de regard) sont ignorées pour améliorer le gameplay et éviter que le joueur soit bloqué par des obstacles derrière lui. Ce filtrage s'applique uniquement aux collisions horizontales, pas aux collisions verticales (sol/plafond)
- **Détection de collision** : Utilise des rectangles AABB (Axis-Aligned Bounding Box) pour une détection rapide
- **Résolution de collision** : Empêche le personnage de traverser les tiles en corrigeant sa position (résolution séparée sur X et Y)
- **État au sol** : Le personnage est considéré "au sol" lorsqu'il est en collision avec un tile par le bas
- **Vitesse de chute maximale** : Limite la vitesse de chute à 500 pixels/s pour éviter des chutes trop rapides
- **Alignement précis** : Le rectangle de collision est aligné avec le bas du sprite visuel pour éviter les décalages
- **Optimisations** : Cache des rectangles de collision et échantillonnage optimisé pour de bonnes performances
- **Saut** : Le personnage peut sauter avec la touche haut/W, appliquant une vitesse initiale vers le haut qui est modifiée par la gravité pour créer un mouvement parabolique naturel
- **Double saut** : À partir du niveau 3, le personnage peut effectuer un double saut en l'air. Pour déclencher le double saut, relâchez la touche de saut après le premier saut, puis réappuyez sur la touche de saut pendant que vous êtes en l'air. Le double saut relance un nouveau saut depuis la position actuelle du personnage
- **Plateformes mobiles** : Lorsque le personnage est sur une plateforme mobile (déplacée via les événements `sprite_move` ou `sprite_move_perpetual`), il suit automatiquement le mouvement de la plateforme en X et Y tout en conservant la possibilité de se déplacer horizontalement de manière indépendante. Le joueur peut utiliser les touches de direction gauche/droite pour se déplacer horizontalement même lorsqu'il est attaché à une plateforme mobile, permettant un gameplay plus fluide et naturel. Le mouvement du joueur s'ajoute au mouvement de la plateforme, permettant au joueur de marcher sur la plateforme tout en étant transporté par elle

### Système de personnages non joueurs (PNJ)

Le jeu inclut un système de PNJ permettant de placer des personnages sur la route du joueur :
- **Configuration séparée** : Les PNJ sont configurés dans un fichier `.pnj` séparé du fichier de niveau (`.niveau`)
- **ID technique unique** : Chaque PNJ doit avoir un identifiant technique unique (`id`) qui permet de le référencer dans les fichiers de déclencheurs d'événements
- **Positionnement automatique** : Les PNJ sont positionnés automatiquement sur le premier bloc de depth 2 par le moteur de gravité. Par défaut, il suffit de spécifier la coordonnée X (le PNJ commence à y=0.0 puis tombe). Optionnellement, vous pouvez spécifier une coordonnée Y d'apparition initiale (`y`) : le PNJ commence à cette position Y, puis la gravité le fait tomber vers le sol en dessous (y plus grand dans le repère existant)
- **Orientation** : Les PNJ peuvent être orientés vers la gauche ou la droite via le paramètre `direction` (le sprite est inversé horizontalement pour la direction gauche)
- **Animations** : Support d'animations configurées dans le fichier de PNJ (ligne, nombre de frames, vitesse, boucle)
- **Affichage du nom** : Les noms des PNJ sont affichés au-dessus de leur tête, de la même manière que le joueur (texte blanc avec contour noir)
- **Gravité** : Les PNJ sont soumis à la gravité en permanence comme le joueur, même pendant les déplacements déclenchés par événements. Cela garantit que les PNJ restent au sol ou tombent s'ils se déplacent au-dessus d'un vide
- **Intégration** : Les PNJ sont rendus dans la couche de gameplay (depth 2), après le joueur mais avant les couches de depth 2 et 3
- **Système de blocs de dialogue** : Les PNJ peuvent avoir des blocs de dialogue configurés avec des plages de position. Chaque bloc de dialogue définit une position minimale et maximale en pixels horizontaux correspondant à la position du joueur dans le monde, et contient une série d'échanges conversationnels entre le joueur et le PNJ. La position est fournie par le système de gestion de l'avancement dans le niveau (spécification 11) via `LevelProgressTracker.get_current_x()`. La méthode `get_dialogue_block_for_position()` permet de récupérer le bloc de dialogue correspondant à une position donnée. Le système de déclenchement des dialogues est implémenté : utilisez la fonction `start_dialogue()` pour démarrer un dialogue avec un PNJ, et la classe `DialogueState` gère l'affichage séquentiel des échanges via des bulles de dialogue (`SpeechBubble`). Pour interagir avec un PNJ, approchez-vous à moins de 200 pixels horizontalement, puis appuyez sur la touche `T` lorsque l'indication "T pour parler" apparaît. **Seule la distance horizontale (X) est prise en compte** - la distance verticale (Y) est ignorée, ce qui permet d'interagir avec les PNJ même s'ils sont sur des plateformes au-dessus ou en-dessous du joueur. **Contrainte de navigation** : Le passage à l'échange suivant dans un dialogue est bloqué si un événement de type `sprite_move` est en cours de déplacement. Dans ce cas, le clic est ignoré et l'utilisateur doit attendre la fin du mouvement du sprite avant de pouvoir continuer le dialogue. Cela garantit la cohérence narrative et visuelle du jeu.
- **Déclenchement d'événements via dialogues** : Les échanges de dialogue peuvent déclencher automatiquement des événements du système de déclencheurs d'événements lors de leur affichage. Utilisez le champ `trigger_events` dans un échange pour référencer les identifiants d'événements à déclencher. Les événements sont déclenchés lorsque l'échange est affiché, avant que la bulle de dialogue ne soit créée. Cela permet de déclencher des événements à des moments précis de la conversation. Pour permettre à un événement d'être déclenché plusieurs fois lors de conversations répétées, définissez `repeatable = true` dans le fichier `.event` (voir section "Système de déclencheurs d'événements").
- **Gestion d'inventaire via dialogues** : Les échanges de dialogue peuvent ajouter ou retirer des objets de l'inventaire du joueur lors de leur affichage. Utilisez les champs `add_items` et `remove_items` dans un échange pour gérer l'inventaire. Les objets sont ajoutés/retirés avec animations automatiques (fade-in pour l'ajout, saut vers l'arrière puis explosion de particules pour le retrait). Format : `add_items = {item_id = quantity}` et `remove_items = {item_id = quantity}`.
- **Déplacement déclenché par événements** : Les PNJ peuvent être déplacés automatiquement par le système de déclencheurs d'événements (voir section "Système de déclencheurs d'événements" ci-dessous)
- **Suivi du personnage principal** : Les PNJ peuvent suivre automatiquement le personnage principal via un événement déclenché par le système de déclencheurs. Le PNJ se positionne automatiquement derrière le joueur (à droite si le joueur va à gauche, à gauche si le joueur va à droite) et maintient une distance constante. La direction du PNJ est automatiquement gérée en fonction de la direction du joueur. Le suivi a la priorité sur les déplacements déclenchés par événements. Voir la section "Système de déclencheurs d'événements" pour plus de détails.

**Format de fichier de PNJ** (`levels/niveau_plateforme.pnj`) :

```toml
[[npcs]]
id = "robot_01"  # Identifiant technique unique (obligatoire)
name = "Robot"
x = 500.0
# y = 400.0  # Optionnel : position verticale d'apparition initiale. Si défini, le PNJ commence à cette position Y puis tombe vers le sol.
direction = "right"  # Orientation : "left" ou "right" (optionnel, défaut: "right")
sprite_sheet_path = "sprite/robot.png"
sprite_width = 44
sprite_height = 64

[npcs.animations.idle]
row = 0
num_frames = 4
animation_speed = 8.0
loop = true

# Blocs de dialogue optionnels (basés sur la position horizontale du joueur dans le monde)
[[npcs.dialogue_blocks]]
position_min = 0.0
position_max = 1000.0
font_size = 32
text_speed = 30.0

[[npcs.dialogue_blocks.exchanges]]
speaker = "npc"
text = "Bonjour !\nJe suis un robot."

[[npcs.dialogue_blocks.exchanges]]
speaker = "player"
text = "Regardez cette image !"
image_path = "dialogue_image.png"  # Image dans le répertoire "image"

[[npcs.dialogue_blocks]]
position_min = 1000.0
position_max = 2000.0
font_size = 32
text_speed = 30.0

[[npcs.dialogue_blocks.exchanges]]
speaker = "npc"
text = "Approchez-vous pour mieux m'entendre !"

[[npcs.dialogue_blocks.exchanges]]
speaker = "player"
text = "D'accord, je m'approche."

# Exemple de bloc de dialogue avec déclenchement d'événements
[[npcs.dialogue_blocks]]
position_min = 2000.0
position_max = 3000.0
font_size = 32
text_speed = 30.0

[[npcs.dialogue_blocks.exchanges]]
speaker = "npc"
text = "Bonjour ! Je suis ChatGPT."

[[npcs.dialogue_blocks.exchanges]]
speaker = "player"
text = "Enchanté de vous rencontrer !"

[[npcs.dialogue_blocks.exchanges]]
speaker = "npc"
text = "Regardez, quelque chose se passe !"
trigger_events = ["robot_move_01", "hide_obstacle_01"]  # Événements déclenchés lorsque cet échange est affiché
add_items = {document_etoile = 1}  # Ajouter un objet à l'inventaire avec animation

[[npcs.dialogue_blocks.exchanges]]
speaker = "player"
text = "Merci pour cet objet !"
remove_items = {document_etoile = 1}  # Retirer un objet de l'inventaire avec animation

# Exemple de bloc de dialogue de type "quête" - affiche un "!" au-dessus du PNJ
[[npcs.dialogue_blocks]]
position_min = 3000.0
position_max = 4000.0
dialogue_type = "quête"  # Type "quête" : affiche un "!" au lieu de "T pour parler"
font_size = 32
text_speed = 30.0

[[npcs.dialogue_blocks.exchanges]]
speaker = "npc"
text = "J'ai une mission importante pour vous !"

[[npcs.dialogue_blocks.exchanges]]
speaker = "player"
text = "Je suis prêt à vous aider !"

# Exemple de bloc de dialogue de type "discution" - affiche "T pour ecouter et donner son avis"
[[npcs.dialogue_blocks]]
position_min = 9000.0
position_max = 12000.0
dialogue_type = "discution"  # Type "discution" : affiche "T pour ecouter et donner son avis"

[[npcs.dialogue_blocks.exchanges]]
speaker = "npc"
text = "Qu'en pensez-vous de cette situation ?"

[[npcs.dialogue_blocks.exchanges]]
speaker = "player"
text = "Je pense que c'est une bonne idée !"

# Exemple de bloc de dialogue de type "ecoute" - affiche "T pour écouter"
[[npcs.dialogue_blocks]]
position_min = 12000.0
position_max = 15000.0
dialogue_type = "ecoute"  # Type "ecoute" : affiche "T pour écouter"

[[npcs.dialogue_blocks.exchanges]]
speaker = "player"
text = "Je pense que c'est une bonne idée !"

# Exemple de bloc de dialogue de type "regarder" - affiche "T pour regarder ce que c'est"
[[npcs.dialogue_blocks]]
position_min = 15000.0
position_max = 18000.0
dialogue_type = "regarder"  # Type "regarder" : affiche "T pour regarder ce que c'est"

[[npcs.dialogue_blocks.exchanges]]
speaker = "player"
text = "Qu'est-ce que c'est que ça ?"
image_path = "objet_mystere.png"

# Exemple de bloc de dialogue de type "enseigner" - affiche "T pour former"
[[npcs.dialogue_blocks]]
position_min = 18000.0
position_max = 21000.0
dialogue_type = "enseigner"  # Type "enseigner" : affiche "T pour former"

[[npcs.dialogue_blocks.exchanges]]
speaker = "npc"
text = "Laissez-moi vous expliquer comment cela fonctionne..."

# Exemple de bloc de dialogue de type "reflexion" - affiche "T pour reflechir"
[[npcs.dialogue_blocks]]
position_min = 21000.0
position_max = 24000.0
dialogue_type = "reflexion"  # Type "reflexion" : affiche "T pour reflechir"

[[npcs.dialogue_blocks.exchanges]]
speaker = "player"
text = "Je dois réfléchir à cette situation..."
```

Le fichier de PNJ est chargé automatiquement s'il existe à côté du fichier de niveau (même nom avec l'extension `.pnj`).

### Système de déclencheurs d'événements

Le jeu inclut un système de déclencheurs d'événements basés sur la progression du joueur dans le niveau :
- **Configuration séparée** : Les événements sont configurés dans un fichier `.event` séparé (même nom que le niveau avec l'extension `.event`)
- **Déclenchement par position** : Les événements sont déclenchés lorsque le joueur atteint une certaine position horizontale dans le monde (obtenue via `LevelProgressTracker`)
- **Types d'événements** :
  - **Déplacement de PNJ** : Permet de déplacer automatiquement un PNJ vers une position cible avec une direction et une vitesse spécifiées
  - **Suivi du personnage principal par un PNJ** : Permet à un PNJ de suivre automatiquement le personnage principal. Le PNJ se positionne automatiquement derrière le joueur (à droite si le joueur va à gauche, à gauche si le joueur va à droite) et maintient une distance constante. La direction du PNJ est automatiquement gérée en fonction de la direction du joueur. Le suivi a la priorité sur les déplacements déclenchés par événements. Un sprite pour le mouvement peut être spécifié pour gérer automatiquement la direction.
  - **Arrêt du suivi d'un PNJ** : Permet d'arrêter le suivi automatique d'un PNJ. Le PNJ s'arrête à sa position actuelle et reprend son comportement normal (animation idle, etc.). Utile pour faire arrêter un PNJ qui suit le joueur à un moment précis du jeu.
  - **Masquage de sprite** : Permet de masquer progressivement des sprites avec un effet de fade out, et optionnellement de supprimer leurs collisions
  - **Affichage de sprite** : Permet d'afficher progressivement des sprites avec un effet de fade in, et optionnellement de restaurer leurs collisions. Utile pour réafficher des sprites masqués précédemment ou afficher des sprites qui commencent invisibles (avec `initial_alpha = 0`)
  - **Déplacement de sprite** : Permet de déplacer un sprite (ou un groupe de sprites identifiés par un tag) de manière homogène vers une position cible avec une vitesse configurable. Les entités (joueur, PNJ) qui se trouvent sur la face supérieure du sprite sont automatiquement transportées avec lui (plateformes mobiles)
  - **Déplacement perpétuel de sprite** : Permet de déplacer un sprite (ou un groupe de sprites identifiés par un tag) de manière perpétuelle entre deux positions. Le sprite va de sa position initiale à une position cible, puis revient, indéfiniment. Les entités (joueur, PNJ) qui se trouvent sur la face supérieure du sprite sont automatiquement transportées avec lui (plateformes mobiles oscillantes)
  - **Rotation de sprite** : Permet de faire tourner un sprite (ou un groupe de sprites identifiés par un tag) autour de son centre à une vitesse configurable pendant une durée spécifiée. La rotation peut être dans le sens horaire (vitesse positive) ou antihoraire (vitesse négative). Après la durée configurée, la rotation s'arrête et le sprite reste à son angle final
  - **Zoom caméra sur le personnage principal** : Permet d'appliquer un zoom post-process sur la scène (monde + entités + particules + bulles), centré sur le joueur, avec une animation progressive. Un événement dédié permet de revenir au zoom initial. Les overlays UI (stats, popin quitter) ne sont pas affectés
  - **Zoom caméra sur un sprite** : Permet d'appliquer un zoom post-process sur un sprite identifié par son tag, avec des offsets X et Y personnalisables. La caméra devient fixe (ne suit plus le joueur) jusqu'au déclenchement d'un événement de reset. Utile pour mettre en valeur des objets importants ou créer des effets cinématiques
  - **Ajout d'objet à l'inventaire** : Permet d'ajouter automatiquement un objet à l'inventaire du joueur avec animation d'apparition progressive
  - **Retrait d'objet de l'inventaire** : Permet de retirer automatiquement un objet de l'inventaire du joueur avec animation de saut vers l'arrière puis explosion de particules de flamme colorées (rouge, orange, jaune)
  - **Fondu au noir de l'écran** : Permet de créer un effet de fondu au noir avec trois phases (fondu au noir, écran noir complet, fondu de retour). Un texte optionnel peut être affiché en blanc centré au milieu de l'écran pendant toute la durée du fondu. Utile pour les transitions de scène, changements de chapitre, etc.
  - **Lancement d'effet de particules** : Permet de lancer un effet de particules à un emplacement spécifique (x, y) du design, dans une zone rectangulaire (spawn_area), ou dans la zone couverte par un sprite identifié par son tag (sprite_tag). Supporte plusieurs types d'effets : explosion, confetti, flame_explosion, rain, smoke, sparks. Les paramètres (nombre de particules, vitesse, durée de vie, taille, couleur) sont optionnels et utilisent les valeurs par défaut du type d'effet si non spécifiés. Supporte plusieurs couleurs (chaque particule choisit aléatoirement une couleur parmi une liste) pour créer des effets multicolores variés. Permet de limiter la génération à un bord spécifique du sprite (spawn_edge : "top", "bottom", "left", "right") pour créer des effets ciblés (fumée depuis le haut, pluie depuis le bas, étincelles depuis les côtés, etc.). Utile pour créer des effets visuels dynamiques (explosions, célébrations, pluie, fumée, etc.)
- **Animation de déplacement** : Optionnellement, une animation temporaire peut être activée pendant le déplacement du PNJ
- **Fade out progressif** : Les sprites masqués disparaissent progressivement avec un effet de fade out configurable
- **Fade in progressif** : Les sprites affichés apparaissent progressivement avec un effet de fade in configurable
- **Suppression des collisions** : Les collisions des sprites masqués peuvent être automatiquement supprimées une fois le fade out terminé
- **Restauration des collisions** : Les collisions des sprites affichés peuvent être automatiquement restaurées une fois le fade in terminé
- **Tags de sprites** : Les sprites peuvent être tagués dans les fichiers de niveau pour être référencés dans les événements
- **Rotation autour du centre** : La rotation des sprites se fait autour du centre du sprite, garantissant que le sprite reste visuellement à la même position pendant la rotation
- **Déclenchement unique** : Par défaut, chaque événement ne peut être déclenché qu'une seule fois (pas de re-déclenchement automatique). Cependant, vous pouvez définir `repeatable = true` dans le fichier `.event` pour permettre à un événement d'être déclenché plusieurs fois (utile pour les événements déclenchés depuis les dialogues qui doivent pouvoir se relancer lors de conversations répétées)

**Format de fichier d'événements** (`levels/niveau_plateforme.event`) :

```toml
# Exemple d'événement : déplacer le robot vers la droite quand le joueur atteint 2000 pixels
[[events]]
identifier = "robot_move_01"
trigger_x = 2000.0
event_type = "npc_move"

[events.event_data]
npc_id = "robot_01"  # Doit correspondre à l'ID d'un PNJ défini dans le fichier .pnj
target_x = 2500.0  # Position X vers laquelle le PNJ doit se déplacer
direction = "right"  # Sens de déplacement : "left" ou "right"
move_speed = 300.0  # Vitesse de déplacement en pixels par seconde (optionnel, défaut: 300.0)
move_animation_row = 0  # Optionnel : ligne du sprite sheet pour l'animation de déplacement
move_animation_frames = 4  # Optionnel : nombre de frames pour l'animation de déplacement

# Exemple d'événement : faire suivre un PNJ au joueur quand le joueur atteint 2500 pixels
[[events]]
identifier = "robot_follow_player"
trigger_x = 2500.0
event_type = "npc_follow"

[events.event_data]
npc_id = "robot_01"  # Doit correspondre à l'ID d'un PNJ défini dans le fichier .pnj
follow_distance = 120.0  # Distance horizontale à maintenir derrière le joueur en pixels (optionnel, défaut: 100.0)
follow_speed = 180.0  # Vitesse de déplacement lors du suivi en pixels par seconde (optionnel, défaut: 200.0)
animation_row = 1  # Optionnel : ligne du sprite sheet pour l'animation de suivi. Si non spécifié, utilise l'animation "walk" si disponible
animation_frames = 4  # Optionnel : nombre de frames pour l'animation de suivi. Si non spécifié, utilise la configuration d'animation existante

# Exemple d'événement : arrêter le suivi d'un PNJ quand le joueur atteint 5000 pixels
[[events]]
identifier = "robot_stop_follow"
trigger_x = 5000.0
event_type = "npc_stop_follow"

[events.event_data]
npc_id = "robot_01"  # Doit correspondre à l'ID d'un PNJ défini dans le fichier .pnj. Le PNJ s'arrête à sa position actuelle

# Exemple d'événement : masquer un obstacle quand le joueur atteint 3000 pixels
[[events]]
identifier = "hide_obstacle_01"
trigger_x = 3000.0
event_type = "sprite_hide"

[events.event_data]
sprite_tag = "obstacle_removable"  # Tag du sprite à masquer (doit correspondre à un tag défini dans le fichier .niveau)
fade_duration = 2.0  # Durée de la disparition progressive en secondes (optionnel, défaut: 1.0)
remove_collisions = true  # Si true, supprime les collisions une fois le sprite complètement masqué (optionnel, défaut: true)

# Exemple d'événement : afficher un obstacle quand le joueur atteint 1500 pixels
[[events]]
identifier = "show_obstacle_01"
trigger_x = 1500.0
event_type = "sprite_show"

[events.event_data]
sprite_tag = "obstacle_revealed"  # Tag du sprite à afficher (doit correspondre à un tag défini dans le fichier .niveau)
fade_duration = 1.5  # Durée de l'apparition progressive en secondes (optionnel, défaut: 1.0)
restore_collisions = true  # Si true, restaure les collisions une fois le sprite complètement affiché (optionnel, défaut: true)

# Exemple d'événement : ajouter un objet à l'inventaire quand le joueur atteint 1500 pixels
[[events]]
identifier = "give_document_etoile"
trigger_x = 1500.0
event_type = "inventory_add"

[events.event_data]
item_id = "document_etoile"  # ID technique de l'objet (doit correspondre à un objet défini dans inventory_items.toml)
quantity = 1  # Quantité à ajouter (optionnel, défaut: 1)

# Exemple d'événement : retirer un objet de l'inventaire quand le joueur atteint 4000 pixels
[[events]]
identifier = "remove_loupe_magique"
trigger_x = 4000.0
event_type = "inventory_remove"

[events.event_data]
item_id = "loupe_magique"  # ID technique de l'objet
quantity = 1  # Quantité à retirer (optionnel, défaut: 1)

# Exemple d'événement : déplacer une plateforme mobile quand le joueur atteint 5000 pixels
# Note : Lorsque le joueur est sur une plateforme mobile, il suit automatiquement le mouvement vertical
# de la plateforme tout en conservant la possibilité de se déplacer horizontalement de manière indépendante
[[events]]
identifier = "move_platform_secret"
trigger_x = 5000.0
event_type = "sprite_move"

[events.event_data]
sprite_tag = "platform_mobile_secret"  # Tag du sprite à déplacer (doit correspondre à un tag défini dans le fichier .niveau)
move_x = 200.0  # Déplacement horizontal en pixels (peut être négatif)
move_y = -100.0  # Déplacement vertical en pixels (peut être négatif)
move_speed = 250.0  # Vitesse de déplacement en pixels par seconde (optionnel, défaut: 250.0)

# Exemple d'événement : rotation de sprite (moulin à vent)
[[events]]
identifier = "rotate_windmill"
trigger_x = 2000.0
event_type = "sprite_rotate"

[events.event_data]
sprite_tag = "windmill_blades"  # Tag du sprite à faire tourner (doit correspondre à un tag défini dans le fichier .niveau)
rotation_speed = 90.0  # Vitesse de rotation en degrés par seconde (positive = sens horaire, négative = sens antihoraire)
duration = 5.0  # Durée de la rotation en secondes. Après cette durée, la rotation s'arrête et le sprite reste à son angle final

# Exemple d'événement : rotation de sprite (sens antihoraire)
[[events]]
identifier = "rotate_gear_counterclockwise"
trigger_x = 3000.0
event_type = "sprite_rotate"

[events.event_data]
sprite_tag = "gear_mechanism"  # Tag du sprite à faire tourner
rotation_speed = -45.0  # Rotation de 45 degrés par seconde dans le sens antihoraire (négatif)
duration = 10.0  # La rotation dure 10 secondes, puis s'arrête

# Exemple d'événement : zoom caméra sur le joueur (post-process)
[[events]]
identifier = "camera_zoom_01"
trigger_x = 6500.0
event_type = "camera_zoom"

[events.event_data]
zoom_percent = 160.0
duration = 0.9
bottom_margin = 50.0
keep_bubbles_visible = true

# Exemple d'événement : zoom caméra sur un sprite
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
# Comportement : transition linéaire vers la cible (caméra déverrouillée),
# puis caméra verrouillée à la position finale sans suivre le joueur.

# Exemple d'événement : retour au zoom initial
[[events]]
identifier = "camera_zoom_reset_01"
trigger_x = 7200.0
event_type = "camera_zoom_reset"

[events.event_data]
duration = 0.9
# Comportement : transition linéaire vers la position actuelle du joueur
# avec dézoom, puis reprise du suivi normal du joueur.

# Exemple d'événement répétable : level up (peut être déclenché plusieurs fois depuis les dialogues)
[[events]]
identifier = "player_level_up"
# trigger_x non spécifié : cet événement ne peut être déclenché que manuellement (par exemple via les dialogues)
event_type = "level_up"
repeatable = true  # Cet événement peut être déclenché plusieurs fois (utile pour les dialogues répétés)

[events.event_data]
# Aucun champ requis pour les événements de level up

# Exemple d'événement : fondu au noir avec texte pour transition de chapitre
[[events]]
identifier = "fade_to_black_chapter_2"
trigger_x = 10000.0
event_type = "screen_fade"

[events.event_data]
fade_in_duration = 1.0  # Fondu au noir sur 1 seconde (optionnel, défaut: 1.0)
text_fade_in_duration = 0.5  # Apparition du texte sur 0.5 seconde (optionnel, défaut: 0.5)
text_display_duration = 2.0  # Texte visible pendant 2 secondes (optionnel, défaut: 1.0)
text_fade_out_duration = 0.5  # Disparition du texte sur 0.5 seconde (optionnel, défaut: 0.5)
fade_out_duration = 1.0 # Fondu de retour sur 1 seconde (optionnel, défaut: 1.0)
text = "Chapitre 2"      # Texte affiché en blanc centré (apparaît, reste visible, puis disparaît) (optionnel, défaut: null)

# Exemple d'événement : lancer un effet d'explosion de particules quand le joueur atteint 3000 pixels (point unique, couleur unique)
[[events]]
identifier = "explosion_at_checkpoint"
trigger_x = 3000.0
event_type = "particle_effect"

[events.event_data]
effect_type = "explosion"  # Type d'effet : "explosion", "confetti", "flame_explosion", "rain", "smoke" ou "sparks"
x = 3200.0  # Position X où l'effet est lancé (coordonnées monde du design 1920x1080)
y = 500.0   # Position Y où l'effet est lancé (coordonnées monde du design 1920x1080)
count = 30  # Optionnel : nombre de particules (si non spécifié, utilise la valeur par défaut du type d'effet)
speed = 350.0  # Optionnel : vitesse de base en pixels/seconde
lifetime = 0.5  # Optionnel : durée de vie en secondes
size = 18  # Optionnel : taille de base en pixels (diamètre)
color = [255, 200, 0]  # Optionnel : couleur RGB (si non spécifié, utilise la couleur par défaut). Note: ignoré pour "flame_explosion" et "confetti"

# Exemple d'événement avec plusieurs couleurs (chaque particule choisit aléatoirement une couleur parmi la liste)
[[events]]
identifier = "multicolor_explosion"
trigger_x = 4000.0
event_type = "particle_effect"

[events.event_data]
effect_type = "explosion"
x = 4000.0
y = 600.0
count = 40
colors = [[255, 0, 0], [255, 165, 0], [255, 255, 0], [0, 255, 0], [0, 0, 255]]  # Rouge, orange, jaune, vert, bleu
# Chaque particule choisit aléatoirement une couleur parmi cette liste

# Exemple d'événement avec zone de génération (particules générées dans une zone rectangulaire)
[[events]]
identifier = "rain_in_area"
trigger_x = 2000.0
event_type = "particle_effect"

[events.event_data]
effect_type = "rain"
spawn_area = { x_min = 2000.0, x_max = 3000.0, y_min = 0.0, y_max = 200.0 }  # Zone de génération (coordonnées monde du design 1920x1080)
count = 100  # Plus de particules pour couvrir la zone
# Les particules sont générées aléatoirement dans cette zone au lieu d'un point unique

# Exemple d'événement avec zone de génération et plusieurs couleurs
[[events]]
identifier = "multicolor_zone_explosion"
trigger_x = 6000.0
event_type = "particle_effect"

[events.event_data]
effect_type = "explosion"
spawn_area = { x_min = 6000.0, x_max = 6500.0, y_min = 400.0, y_max = 600.0 }  # Zone de génération
count = 50
colors = [[255, 100, 100], [100, 255, 100], [100, 100, 255], [255, 255, 100]]  # Rose, vert clair, bleu clair, jaune clair
# Les particules sont générées aléatoirement dans la zone et chaque particule choisit aléatoirement une couleur

# Exemple d'événement : lancer un effet de confetti (couleur ignorée, utilise une palette prédéfinie)
[[events]]
identifier = "confetti_celebration"
trigger_x = 5000.0
event_type = "particle_effect"
repeatable = true  # Peut être déclenché plusieurs fois

[events.event_data]
effect_type = "confetti"
x = 5000.0
y = 200.0
# count, speed, lifetime, size optionnels (utilisent les valeurs par défaut)
# color et colors ignorés pour "confetti" (utilise une palette de couleurs festives prédéfinie)

# Exemple d'événement avec génération progressive (particules générées sur une durée)
[[events]]
identifier = "continuous_rain"
trigger_x = 3000.0
event_type = "particle_effect"
repeatable = true

[events.event_data]
effect_type = "rain"
spawn_area = { x_min = 3000.0, x_max = 5000.0, y_min = 0.0, y_max = 100.0 }
count = 200  # Nombre total de particules
generation_duration = 5.0  # Les particules sont générées progressivement sur 5 secondes (environ 40 particules/seconde)
# Les particules continuent d'apparaître pendant 5 secondes, créant un effet de pluie continue

# Exemple d'événement : fumée depuis le haut d'une cheminée (sprite tag)
[[events]]
identifier = "smoke_from_chimney"
trigger_x = 4000.0
event_type = "particle_effect"
repeatable = true

[events.event_data]
effect_type = "smoke"
sprite_tag = "chimney"  # Tag du sprite de la cheminée (défini dans le fichier .niveau)
spawn_edge = "top"  # Générer uniquement depuis le bord supérieur de la cheminée
count = 50
generation_duration = 10.0  # Fumée continue pendant 10 secondes

# Exemple d'événement avec direction personnalisée (étincelles vers la droite)
[[events]]
identifier = "sparks_to_right"
trigger_x = 9000.0
event_type = "particle_effect"
repeatable = true

[events.event_data]
effect_type = "sparks"
x = 9000.0
y = 500.0
count = 30
speed = 400.0
lifetime = 0.3
direction_angle = 0.0  # Vers la droite (0 radians = 0°)
direction_spread = 0.5  # Dispersion de ±0.5 radians (≈±28.6°) de part et d'autre
colors = [[255, 200, 0], [255, 100, 0], [255, 255, 255]]  # Jaune, orange, blanc
# Les étincelles partent vers la droite avec une dispersion limitée, créant un effet de court-circuit horizontal

# Exemple d'événement avec direction personnalisée (pluie oblique)
[[events]]
identifier = "oblique_rain"
trigger_x = 10000.0
event_type = "particle_effect"
repeatable = true

[events.event_data]
effect_type = "rain"
spawn_area = { x_min = 10000.0, x_max = 12000.0, y_min = 0.0, y_max = 200.0 }
count = 150
speed = 250.0
lifetime = 3.0
direction_angle = 1.2  # Angle oblique vers le bas-droite (≈69°)
direction_spread = 0.3  # Dispersion limitée pour un effet de pluie oblique cohérent
# La pluie tombe en diagonale vers la droite, créant un effet de vent latéral

# Exemple d'événement : pluie depuis le bas d'un nuage (sprite tag)
[[events]]
identifier = "rain_from_cloud"
trigger_x = 5000.0
event_type = "particle_effect"
repeatable = true

[events.event_data]
effect_type = "rain"
sprite_tag = "cloud"  # Tag du sprite du nuage
spawn_edge = "bottom"  # Générer uniquement depuis le bord inférieur du nuage
count = 100
generation_duration = 8.0

# Exemple d'événement : étincelles depuis le côté gauche d'une machine (sprite tag)
[[events]]
identifier = "sparks_from_machine"
trigger_x = 6000.0
event_type = "particle_effect"
repeatable = true

[events.event_data]
effect_type = "sparks"
sprite_tag = "machine"  # Tag du sprite de la machine
spawn_edge = "left"  # Générer uniquement depuis le bord gauche de la machine
count = 30
colors = [[255, 200, 0], [255, 100, 0], [255, 255, 0]]  # Couleurs d'étincelles (jaune, orange, jaune clair)
```

**Comportement du déplacement** :
- Lorsqu'un événement est déclenché, la direction du PNJ est mise à jour avec la valeur spécifiée
- Le PNJ se déplace progressivement vers `target_x` à la vitesse `move_speed`
- Si `move_animation_row` et `move_animation_frames` sont spécifiés, une animation temporaire est activée pendant le déplacement
- L'animation temporaire est désactivée et l'animation normale reprend une fois que le PNJ a atteint sa destination
- **Gravité permanente** : La gravité s'applique en permanence pendant le déplacement. Si le PNJ se déplace au-dessus d'un vide, il tombe. Les collisions verticales sont résolues à chaque frame pour maintenir le PNJ au sol ou gérer les chutes

**Comportement du suivi** :
- Lorsqu'un événement de type `npc_follow` est déclenché, le PNJ commence à suivre automatiquement le personnage principal
- Le PNJ se positionne automatiquement derrière le joueur :
  - Si le joueur va à gauche (position X diminue), le PNJ se positionne à droite du joueur (à une distance `follow_distance` pixels)
  - Si le joueur va à droite (position X augmente), le PNJ se positionne à gauche du joueur (à une distance `follow_distance` pixels)
- La direction du PNJ est automatiquement mise à jour en fonction de la direction du joueur :
  - Si le joueur va à gauche, le PNJ regarde vers la droite (vers le joueur)
  - Si le joueur va à droite, le PNJ regarde vers la gauche (vers le joueur)
- Si `animation_row` et `animation_frames` sont spécifiés, une animation temporaire est activée pendant le suivi. Sinon, l'animation "walk" est utilisée si disponible, ou l'animation actuelle est conservée
- Le PNJ se déplace progressivement vers sa position cible à la vitesse `follow_speed`
- **Gravité permanente** : La gravité s'applique en permanence pendant le suivi. Si le PNJ se déplace au-dessus d'un vide, il tombe. Les collisions verticales sont résolues à chaque frame pour maintenir le PNJ au sol ou gérer les chutes
- **Priorité** : Le suivi du joueur a la priorité sur les déplacements déclenchés par événements (`npc_move`). Si un PNJ suit le joueur, les déplacements déclenchés par événements sont ignorés jusqu'à ce que le suivi soit arrêté
- **Arrêt du suivi** : Le suivi continue jusqu'à ce qu'un événement de type `npc_stop_follow` soit déclenché ou que la méthode `npc.stop_following_player()` soit appelée manuellement

**Comportement de l'arrêt du suivi** :
- Lorsqu'un événement de type `npc_stop_follow` est déclenché, le PNJ s'arrête à sa position actuelle
- Le PNJ reprend son comportement normal (animation idle, etc.)
- L'animation de suivi est désactivée et l'animation normale reprend
- Si le PNJ n'est pas en train de suivre le joueur au moment où l'événement est déclenché, l'événement est ignoré silencieusement (log un avertissement)
- Après l'arrêt du suivi, le PNJ peut à nouveau être déplacé par des événements de type `npc_move` ou suivre à nouveau le joueur via un événement de type `npc_follow`

**Comportement du fondu au noir** :
- Lorsqu'un événement de type `screen_fade` est déclenché, l'écran subit un fondu au noir avec les phases suivantes :
  1. **Fondu au noir** (`fade_in_duration`) : L'écran devient progressivement noir (opacité passe de 0 à 255)
  2. **Apparition du texte** (`text_fade_in_duration`) : Si un texte est configuré, le texte apparaît progressivement sur le fond noir (opacité du texte passe de 0 à 255). Cette phase est ignorée si aucun texte n'est configuré
  3. **Affichage du texte** (`text_display_duration`) : Si un texte est configuré, le texte reste visible à opacité maximale (opacité du texte = 255). Cette phase est ignorée si aucun texte n'est configuré
  4. **Disparition du texte** (`text_fade_out_duration`) : Si un texte est configuré, le texte disparaît progressivement (opacité du texte passe de 255 à 0). Cette phase est ignorée si aucun texte n'est configuré
  5. **Fondu de retour** (`fade_out_duration`) : L'écran redevient progressivement visible (opacité passe de 255 à 0)
- **Affichage du texte** : Si un texte est configuré (`text` n'est pas `null`), il est affiché en blanc centré au milieu de l'écran avec une opacité variable selon la phase. Le texte apparaît progressivement après le fade_in, reste visible, puis disparaît avant le fade_out. Le texte utilise une police système (Arial/sans-serif) en gras, avec une taille adaptée à la résolution de l'écran
- **Priorité de rendu** : L'overlay de fondu est rendu en dernier, après tous les autres éléments (joueur, PNJ, UI, bulles de dialogue, animation de transition de niveau), garantissant qu'il couvre l'écran entier
- **Utilité** : Le fondu au noir est idéal pour créer des transitions de scène, des changements de chapitre, ou des effets narratifs. Le texte permet d'afficher des informations pendant la transition (par exemple "Chapitre 2", "3 jours plus tard...", etc.)
- **Répétabilité** : Si `repeatable = true`, l'événement peut être déclenché plusieurs fois (utile pour des transitions répétées)
- **Intégration avec les dialogues** : Lorsqu'un événement `screen_fade` est déclenché depuis un dialogue (via `trigger_events` dans un échange), le système de dialogue passe automatiquement à l'échange suivant lorsque le fondu entre en phase `fade_out` (avant le fade_out). Pendant le fondu, le passage manuel (clic) est bloqué pour garantir que le fondu se termine complètement avant de permettre un nouveau passage manuel. Cela permet de créer des transitions narratives fluides pendant les conversations, avec le nouveau dialogue qui s'affiche pendant que l'écran redevient progressivement visible

**Comportement du lancement d'effet de particules** :
- Lorsqu'un événement de type `particle_effect` est déclenché, un effet de particules est créé immédiatement à la position spécifiée (x, y) ou dans une zone rectangulaire (spawn_area)
- **Types d'effets disponibles** :
  - `"explosion"` : Particules qui se dispersent dans toutes les directions avec friction, gravité et rétrécissement progressif
  - `"confetti"` : Effet festif avec palette de couleurs vives et variées (rouge, bleu, vert, jaune, violet, orange, rose)
  - `"flame_explosion"` : Explosion de flamme avec palette de couleurs chaudes (rouge, orange, jaune) - la couleur configurée est ignorée
  - `"rain"` : Particules qui tombent verticalement
  - `"smoke"` : Particules qui montent avec dispersion
  - `"sparks"` : Particules rapides et courtes
- **Paramètres optionnels** : Tous les paramètres (`count`, `speed`, `lifetime`, `size`, `color`, `colors`, `spawn_area`) sont optionnels. Si non spécifiés, les valeurs par défaut du type d'effet sont utilisées (voir spécification 14 pour les valeurs par défaut)
- **Zone de génération** : Trois méthodes de positionnement sont disponibles (priorité : `sprite_tag` > `spawn_area` > `x`/`y`) :
  - **Point unique** : Si `x` et `y` sont spécifiés, les particules sont générées à cette position unique
  - **Zone rectangulaire** : Si `spawn_area` est spécifié (format : `{ x_min, x_max, y_min, y_max }`), les particules sont générées aléatoirement dans cette zone au lieu d'un point unique. Cela permet de créer des effets plus dispersés et naturels (par exemple, une pluie sur une large zone, une explosion qui couvre une zone plutôt qu'un point unique). Si `spawn_area` est spécifié, `x` et `y` sont ignorés
  - **Zone de sprite** : Si `sprite_tag` est spécifié, les particules sont générées dans la zone couverte par tous les sprites ayant ce tag. La zone est calculée en prenant l'union des bounds de tous les sprites avec ce tag. Si `sprite_tag` est spécifié, `spawn_area`, `x` et `y` sont ignorés. Optionnellement, `spawn_edge` peut limiter la génération à un bord spécifique du sprite ("top" = bord supérieur, "bottom" = bord inférieur, "left" = bord gauche, "right" = bord droit), créant une bande d'1 pixel de largeur/hauteur le long du bord spécifié. Utile pour créer des effets ciblés (fumée depuis le haut d'une cheminée, pluie depuis le bas d'un nuage, étincelles depuis les côtés d'une machine, etc.)
- **Couleurs multiples** : Si `colors` est spécifié (liste de couleurs RGB), chaque particule choisit aléatoirement une couleur parmi cette liste lors de sa création. Cela permet de créer des effets multicolores variés (par exemple, un feu d'artifice avec plusieurs couleurs, une explosion arc-en-ciel). Si `colors` est spécifié, `color` est ignoré. Pour `"flame_explosion"` et `"confetti"`, `colors` est ignoré car ces effets utilisent des palettes prédéfinies
- **Durée de génération** : Si `generation_duration` est spécifié (en secondes), les particules sont générées progressivement sur cette durée au lieu d'être toutes créées immédiatement. Par exemple, si `count = 100` et `generation_duration = 2.0`, environ 50 particules par seconde seront générées pendant 2 secondes. Cela permet de créer des effets plus fluides et naturels (pluie continue, explosion prolongée, fumée qui s'accumule progressivement). Si `generation_duration` n'est pas spécifié, toutes les particules sont créées immédiatement (comportement par défaut, rétrocompatibilité)
- **Direction personnalisée** : Les paramètres `direction_angle` (en radians) et `direction_spread` (en radians) permettent de personnaliser la direction des particules pour tous les types d'effets. Si `direction_angle` est spécifié, il remplace la direction par défaut du type d'effet. `0.0` = vers la droite, `π/2` (≈1.57) = vers le bas, `-π/2` (≈-1.57) = vers le haut, `π` (≈3.14) = vers la gauche. `direction_spread` définit la dispersion angulaire autour de `direction_angle` : `0.0` = toutes les particules partent dans la même direction, `π/4` (≈0.79) = dispersion de 45° de part et d'autre, `2π` (≈6.28) = toutes les directions. Par exemple, pour des étincelles qui partent vers la droite au lieu de vers le haut, utiliser `direction_angle = 0.0` avec `direction_spread = 0.5` pour un cône vers la droite. Si seulement `direction_spread` est spécifié (sans `direction_angle`), la dispersion est ajustée autour de la direction par défaut du type d'effet
- **Conversion des coordonnées** : Les coordonnées `x`, `y` et les limites de `spawn_area` sont en repère de conception (1920x1080) et sont automatiquement converties vers le repère de rendu (1280x720)
- **Gestion des couleurs** : Pour `"flame_explosion"` et `"confetti"`, les paramètres `color` et `colors` sont ignorés car ces effets utilisent des palettes de couleurs prédéfinies
- **Rétrocompatibilité** : Si `colors` n'est pas spécifié mais `color` est spécifié, toutes les particules utilisent la même couleur (comportement original)
- **Cycle de vie** : Les particules sont gérées automatiquement par le système de particules (mise à jour, rendu, nettoyage). L'effet est automatiquement supprimé lorsque toutes les particules sont mortes et que la génération est terminée (si `generation_duration` est spécifié)
- **Répétabilité** : Si `repeatable = true`, l'événement peut être déclenché plusieurs fois, permettant de créer plusieurs effets simultanés
- **Utilité** : Les effets de particules sont idéaux pour créer des effets visuels dynamiques (explosions lors de la destruction d'objets, célébrations, pluie, fumée, étincelles, etc.)

Le fichier d'événements est chargé automatiquement s'il existe à côté du fichier de niveau (même nom avec l'extension `.event`).

### Système de bulles de dialogue

Le jeu inclut un système de bulles de dialogue (speech bubbles) pour afficher du texte et/ou des images associés à un personnage. Le système supporte également les animations du personnage principal pendant les dialogues :

- **Adaptation automatique** : La bulle s'adapte automatiquement à la taille du contenu (texte et/ou image)
- **Support des images** : Les bulles peuvent contenir des images (placées dans le répertoire `image`). Lorsqu'une image est présente, la bulle est centrée dans l'écran, prend le maximum d'espace disponible, et l'image est redimensionnée pour s'adapter à cette taille. Les images sont affichées au-dessus du texte si les deux sont présents
- **Texte multi-lignes** : Les retours à la ligne sont déterminés par les caractères `\n` dans le texte
- **Positionnement** : Sans image, la bulle peut être positionnée à gauche ou à droite du personnage. Avec image, la bulle est centrée dans l'écran
- **Queue/pointe** : Un élément visuel (queue) pointe vers le personnage qui parle
- **Intégration** : La bulle suit automatiquement le personnage et s'ajuste selon la position de la caméra
- **Raccourci** : Appuyez sur la touche `B` pour afficher/masquer une bulle de dialogue d'exemple

### Exemple d'utilisation

#### Personnage principal

```python
from moteur_jeu_presentation.entities import Player
import pygame

# Initialisation du personnage
player = Player(
    x=960.0,  # Centre de l'écran (1920 / 2)
    y=540.0,  # Centre de l'écran (1080 / 2)
    sprite_width=64,
    sprite_height=64,
    animation_speed=10.0,
    player_level=1,
)

# Configuration
player.speed = 250.0  # pixels par seconde
player.jump_velocity = -400.0  # Vitesse initiale de saut (négative = vers le haut)
player.jump_animation_speed = 12.0  # FPS pour l'animation de saut
# Changer de niveau à la volée (recharge automatiquement les assets)
# player.set_level(3)

# Dans la boucle de jeu
def update(dt: float) -> None:
    keys = pygame.key.get_pressed()
    player.update(dt, keys)
    # Mettre à jour la caméra pour suivre le personnage
    camera_x = player.x - SCREEN_WIDTH / 2

def draw(screen: pygame.Surface, camera_x: float) -> None:
    # Dessiner les couches derrière le joueur (depth 0 et 1)
    for layer in parallax_system._layers:
        if layer.depth <= 1:
            parallax_system._draw_layer(screen, layer)
    
    # Dessiner le joueur
    player.draw(screen, camera_x)
    
    # Dessiner les couches devant le joueur (depth 2 et 3)
    for layer in parallax_system._layers:
        if layer.depth >= 2:
            parallax_system._draw_layer(screen, layer)
```

#### Système de parallaxe

```python
from moteur_jeu_presentation.rendering import ParallaxSystem, Layer
import pygame

# Initialisation
render_width, render_height = get_render_size()
parallax = ParallaxSystem(screen_width=render_width, screen_height=render_height)

# Charger les images
bg_image = pygame.image.load("background.png").convert()
fg_image = pygame.image.load("foreground.png").convert_alpha()

# Créer les couches
background = Layer(
    name="background",
    depth=0,
    scroll_speed=0.2,
    surface=bg_image,
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
parallax.add_layer(foreground)

# Dans la boucle de jeu
def update(dt: float, camera_x: float) -> None:
    parallax.update(camera_x, dt)

def draw(screen: pygame.Surface) -> None:
    screen.fill((0, 0, 0))  # Couleur de fond
    
    # Dessiner les couches derrière le joueur (depth 0 et 1)
    for layer in parallax._layers:
        if layer.depth <= 1:
            parallax._draw_layer(screen, layer)
    
    # Dessiner les éléments de gameplay (joueur, etc.)
    game_entities.draw(screen)
    
    # Dessiner les couches devant le joueur (depth 2 et 3)
    for layer in parallax._layers:
        if layer.depth >= 2:
            parallax._draw_layer(screen, layer)
```

#### Système de bulles de dialogue

```python
from moteur_jeu_presentation.ui import show_speech_bubble, SpeechBubble
from moteur_jeu_presentation.entities import Player

# Initialisation du personnage
player = Player(x=960.0, y=540.0)

# Créer une bulle de dialogue avec texte uniquement
# Le texte peut contenir des \n pour créer plusieurs lignes
# La bulle s'adaptera automatiquement à la taille du texte
bubble = show_speech_bubble(
    character=player,
    text="Bonjour !\nJe suis Thomas.\nComment allez-vous ?",
    side="right",
    font_size=40,
    padding=12,
)

# Créer une bulle de dialogue avec image uniquement
from pathlib import Path
bubble_with_image = show_speech_bubble(
    character=player,
    text="",  # Texte vide
    side="right",
    image_path="dialogue_image.png",
    assets_root=Path("image"),  # Les images de dialogue sont dans le répertoire "image"
    padding=12,
)

# Créer une bulle de dialogue avec texte et image
bubble_with_both = show_speech_bubble(
    character=player,
    text="Regardez cette image !",
    side="right",
    image_path="dialogue_image.png",
    assets_root=Path("image"),
    image_spacing=10,  # Espacement entre l'image et le texte
    padding=12,
)
```

**Animations du personnage pendant les dialogues** :

Les dialogues peuvent déclencher des animations spécifiques du personnage principal. Configurez-les dans les fichiers `.pnj` :

```toml
[[npcs.dialogue_blocks.exchanges]]
speaker = "player"
text = "Thomas : Regardez cette animation !"
player_animation.sprite_sheet_path = "walk.png"
player_animation.row = 2
player_animation.num_frames = 8
player_animation.animation_speed = 10.0
player_animation.animation_type = "loop"  # "simple", "loop", ou "pingpong"
player_animation.start_sprite = 0  # Premier sprite à afficher (optionnel, défaut: 0)
player_animation.offset_y = 0.0  # Offset vertical en pixels (optionnel, défaut: 0.0)
```

Les types d'animation disponibles :
- **"simple"** : L'animation se joue une seule fois puis reste sur la dernière frame
- **"loop"** : L'animation se répète en boucle indéfiniment
- **"pingpong"** : L'animation va de la première à la dernière frame, puis revient en arrière, et ainsi de suite

Paramètres optionnels supplémentaires :
- **`start_sprite`** (int, défaut: 0) : Premier sprite à afficher dans la séquence d'animation (0-indexed). Permet de commencer l'animation à un sprite spécifique au lieu de toujours commencer au premier sprite.
- **`offset_y`** (float, défaut: 0.0) : Offset vertical à appliquer à l'animation en pixels. Cet offset est appliqué pendant toute la durée de l'animation pour ajuster la position verticale du personnage pendant l'animation de dialogue. Une valeur négative décale le personnage vers le haut, une valeur positive vers le bas.
- **`set_x_position`** (float, optionnel) : Position X du personnage principal exprimée dans le repère de conception (1920x1080). Si définie, le joueur est déplacé à cette position au début de l'échange et la caméra est instantanément recentrée en utilisant la même conversion que durant le gameplay (`camera_x = player.x - render_width / 2`). La valeur est automatiquement convertie vers le repère de rendu interne (1280x720).

Exemple avec les paramètres optionnels :
```toml
[[npcs.dialogue_blocks.exchanges]]
speaker = "npc"
text = "Regardez cette animation qui commence au sprite 3 avec un offset vertical !"
player_animation.sprite_sheet_path = "emote.png"
player_animation.row = 0
player_animation.num_frames = 5
player_animation.animation_speed = 8.0
player_animation.animation_type = "simple"
player_animation.start_sprite = 3  # Commencer au sprite 3 (4ème sprite, 0-indexed)
player_animation.offset_y = -10.0  # Décaler le personnage de 10 pixels vers le haut pendant l'animation
player_animation.set_x_position = 4800.0  # Position en pixels dans le repère de conception (1920x1080). La valeur est automatiquement convertie vers le repère de rendu interne (1920x1080, actuellement identique)
```

L'animation est automatiquement déclenchée lorsque l'échange est affiché et s'arrête lorsque l'échange se termine ou que le dialogue passe à l'échange suivant.

```python
# Dans la boucle de jeu
def update(dt: float, camera_x: float) -> None:
    player.update(dt, keys)
    # La bulle se met à jour automatiquement lors du draw

def draw(screen: pygame.Surface, camera_x: float) -> None:
    # Dessiner les couches de parallaxe
    parallax_system.draw(screen)
    
    # Dessiner le personnage
    player.draw(screen, camera_x)
    
    # Dessiner la bulle de dialogue (au-dessus du personnage)
    bubble.draw(screen, camera_x)
```

#### Système de fichiers de niveau

```python
from pathlib import Path
from moteur_jeu_presentation.levels import LevelLoader
from moteur_jeu_presentation.physics import CollisionSystem
from moteur_jeu_presentation.rendering import get_render_size

# Initialisation
assets_dir = Path("sprite")
level_loader = LevelLoader(assets_dir)

# Charger un niveau
level_path = Path("levels/niveau_montagne.niveau")
level_config = level_loader.load_level(level_path)

# Créer le système de parallaxe depuis le fichier de niveau et récupérer le mapping par tag
render_width, render_height = get_render_size()
parallax_system, layers_by_tag = level_loader.create_parallax_layers(
    level_config,
    render_width,
    render_height,
)

# Créer le système de collisions
collision_system = CollisionSystem(parallax_system, render_width, render_height)

# Dans la boucle de jeu
def update(dt: float, camera_x: float) -> None:
    # Appliquer la gravité
    if not player.is_on_ground:
        player.apply_gravity(dt)
    
    # Calculer le déplacement
    dx = 0.0
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        dx -= player.speed * dt
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        dx += player.speed * dt
    
    dy = player.velocity_y * dt
    
    # Résoudre les collisions
    player_rect = player.get_collision_rect()
    corrected_dx, corrected_dy, is_on_ground = collision_system.resolve_collision(
        player_rect, dx, dy, player, camera_x
    )
    
    # Appliquer le déplacement
    player.is_on_ground = is_on_ground
    player.x += corrected_dx
    player.y += corrected_dy
    
    # Mettre à jour le système de parallaxe
    parallax_system.update(camera_x, dt)

def draw(screen: pygame.Surface) -> None:
    screen.fill((0, 0, 0))
    
    # Dessiner les couches derrière le joueur (depth 0 et 1)
    for layer in parallax_system._layers:
        if layer.depth <= 1:
            parallax_system._draw_layer(screen, layer)
    
    # Dessiner le joueur
    player.draw(screen, camera_x)
    
    # Dessiner les couches devant le joueur (depth 2 et 3)
    for layer in parallax_system._layers:
        if layer.depth >= 2:
            parallax_system._draw_layer(screen, layer)
```

**Format de fichier de niveau** :

Exemple avec plusieurs sprite sheets :
```toml
# Déclaration de plusieurs sprite sheets
[sprite_sheets.ground]
path = "sprite/terrain-montage.png"
sprite_width = 64
sprite_height = 64
spacing = -20

[sprite_sheets.decor]
path = "sprite/decor-complements.png"
sprite_width = 128
sprite_height = 128
spacing = 0.0

# Définition des couches avec référence au sprite sheet
[[layers]]
sheet = "ground"
row = 0
depth = 0
is_infinite = false

[[layers]]
sheet = "decor"
row = 2
depth = 3

# Définition des sprites avec référence au sprite sheet
[[sprites]]
sheet = "ground"
row = 1
col = 1
depth = 2
count_x = 30
y_offset = 600.0
is_infinite = false
```

Exemple avec format simplifié (rétrocompatible, un seul sprite sheet) :
```toml
[sprite_sheet]
path = "sprite/terrain-montage.png"
sprite_width = 64
sprite_height = 64
spacing = -20  # Espacement par défaut pour compenser les lignes noires du sprite sheet (optionnel, défaut: 0.0)

# Format simplifié (utilise le spacing par défaut du sprite_sheet)
[layers]
0 = 0  # Ligne 0 → Background (depth 0)
1 = 1  # Ligne 1 → Premier fond (depth 1)
3 = 3  # Ligne 3 → Foreground (depth 3)

# Format étendu avec spacing personnalisé (surcharge le spacing par défaut)
# [layers]
# 0 = { depth = 0, spacing = -1.0 }  # Background avec spacing réduit de 1 pixel
# 1 = { depth = 1, spacing = 0.5 }   # Premier fond avec spacing augmenté de 0.5 pixel
```

Exemple avec sprite individuel (`levels/niveau_plateforme.niveau`) :
```toml
[sprite_sheet]
path = "sprite/terrain-montage.png"
sprite_width = 64
sprite_height = 64
spacing = -20  # Espacement par défaut pour compenser les lignes noires du sprite sheet (optionnel, défaut: 0.0)

[[sprites]]
row = 1  # Ligne 1 (0-indexed, le sprite sheet a 2 lignes: 0-1)
col = 1  # Colonne 1 (0-indexed, le sprite sheet a 2 colonnes: 0-1)
depth = 2  # Profondeur 2 = devant le joueur
count_x = 30
y_offset = 600.0  # Position verticale du haut du sprite en pixels depuis le haut (optionnel, défaut: 0.0)
x_offset = 0.0    # Offset horizontal pour corriger le spacing (optionnel, défaut: 0.0)
infinite_offset = 0.0  # Distance entre chaque répétition infinie (optionnel, défaut: 0.0, uniquement si is_infinite = true)
scale = 1.0  # Facteur de redimensionnement (optionnel, défaut: 1.0 = 100%, 0.5 = 50%, 1.5 = 150% ; la position du bas est conservée automatiquement)
initial_alpha = 255  # Opacité initiale (0-255, optionnel, défaut: 255 = complètement opaque). Utilisez 0 pour commencer invisible et afficher via un événement sprite_show
tags = ["obstacle_revealed"]  # Tags pour référencer ce sprite dans les événements (optionnel)
# spacing = -20  # Optionnel : surcharge le spacing du sprite_sheet si nécessaire
is_infinite = false  # Optionnel : désactive la répétition horizontale infinie (défaut: true)
```

**Correction du spacing** :
- `spacing` : Ajuste l'espacement horizontal entre chaque sprite
  - **Dans `[sprite_sheet]`** : Espacement par défaut appliqué à tous les sprites/layers pour compenser les bordures ou lignes noires incluses dans le sprite sheet
    - `spacing = -20` : Fait chevaucher les sprites de 20 pixels pour masquer les lignes noires/bordures du sprite sheet
    - Utile quand le sprite sheet contient des bordures ou lignes noires entre les sprites
  - **Dans `[layers]`** : Espacement entre chaque sprite de la ligne lors de la concaténation (surcharge le spacing par défaut)
  - **Dans `[[sprites]]`** : Espacement entre chaque répétition du sprite (surcharge le spacing par défaut)
  - Valeur positive : augmente l'espacement
  - Valeur négative : réduit l'espacement (les sprites se chevauchent), particulièrement utile pour compenser les bordures ou lignes noires incluses dans les sprites du sprite sheet
- `x_offset` (pour les sprites individuels uniquement) : Décalage horizontal appliqué à tous les sprites répétés
  - Valeur positive : décale vers la droite
  - Valeur négative : décale vers la gauche
  - Note : `x_offset` décale tous les sprites uniformément, tandis que `spacing` ajuste l'espacement fixe entre chaque sprite
- `infinite_offset` (pour les sprites individuels uniquement, si `is_infinite = true`) : Distance entre chaque répétition infinie de la couche
  - Valeur positive : un espace de `infinite_offset` pixels est ajouté entre chaque répétition infinie de la couche de base
  - Valeur négative : les répétitions infinies se chevauchent de `|infinite_offset|` pixels
  - Utile pour créer des couches infinies avec un espacement personnalisé entre les répétitions
  - Note : `infinite_offset` est utilisé uniquement lorsque `is_infinite = true`. Si `is_infinite = false`, utilisez `spacing` pour l'espacement entre les répétitions.
- `scale` (pour les sprites individuels uniquement) : Facteur de redimensionnement du sprite
  - `scale = 1.0` : Taille originale (100%, défaut)
  - `scale = 0.5` : Taille réduite à 50% (largeur et hauteur divisées par 2)
  - `scale = 1.5` : Taille agrandie à 150% (largeur et hauteur multipliées par 1.5)
  - Le `y_offset` continue de représenter la position du **haut** du sprite ; lorsque `scale != 1.0`, le moteur ajuste automatiquement la position verticale pour conserver la même position du bas qu'avec la taille originale
  - Le `spacing` et `x_offset` sont calculés en fonction de la largeur originale du sprite, pas de la largeur redimensionnée

## Développement

### Commandes utiles

```bash
# Formater le code
black src/

# Linter
ruff check src/

# Type checking
mypy src/
```

### Standards de code

Le projet suit les bonnes pratiques Python définies dans `bonne_pratique.md` :

- PEP 8 pour le style de code
- Type hints pour toutes les fonctions
- Docstrings Google style

## Documentation

- [Spécification du système de couches 2D](spec/1-systeme-de-couches-2d.md)
- [Spécification du personnage principal](spec/2-personnage-principal.md)
- [Spécification du système de fichier niveau](spec/3-systeme-de-fichier-niveau.md)
- [Spécification du système de physique et collisions](spec/4-systeme-de-physique-collisions.md)
- [Spécification du mode plein écran](spec/5-mode-plein-ecran.md)
- [Spécification du système de saut](spec/6-systeme-de-saut.md)
- [Spécification du système de bulles de dialogue](spec/8-systeme-de-bulles-de-dialogue.md)
- [Spécification du système de gestion de l'avancement dans le niveau](spec/11-systeme-gestion-avancement-niveau.md)
- [Spécification du système de personnages non joueurs](spec/12-systeme-de-personnage-non-joueur.md)
- [Spécification du système d'inventaire](spec/13-systeme-d-inventaire.md)
- [Spécification de l'écran d'accueil](spec/16-ecran-d-accueil.md)
- [Spécification du moteur de particules](spec/14-moteur-de-particules.md)
- [Spécification du préchargement des éléments graphiques](spec/17-prechargement-elements-graphiques.md)
- [Bonnes pratiques de développement](bonne_pratique.md)

## Contribution

Les contributions sont les bienvenues ! Veuillez vous assurer de :

1. Suivre les standards de code définis dans `bonne_pratique.md`
2. Mettre à jour les spécifications dans `spec/` et le README si le comportement du moteur change
3. Mettre à jour la documentation si nécessaire

## Licence

### Code source

Le code source du dépôt est publié sous la licence **MIT** — voir le fichier [`LICENSE.MD`](LICENSE.MD).

### Sprites des personnages (`sprite/personnage/`)

Les visuels des personnages (sous-dossiers numérotés `1` à `5`) sont composés à partir d’assets **LPC** (Liberated Pixel Cup) et ressources associées issues notamment d’[OpenGameArt](https://opengameart.org/). **Ils ne sont pas couverts par la seule licence MIT du projet** : les notices d’origine prévoient en général un **choix entre plusieurs licences** ; on y trouve typiquement **OGA-BY 3.0**, **CC-BY-SA 3.0** et **GPL 3.0**. Certains calques (accessoires, etc.) peuvent indiquer d’autres termes, par exemple **CC-BY 3.0**.

Le détail **par fichier** — licences applicables, auteurs et liens — est versionné dans chaque jeu de personnage :

`sprite/personnage/<numéro>/credits/` (notamment `credits.txt` et `credits.csv`).

Pour toute redistribution ou adaptation de ces sprites, respecter les obligations des licences concernées (attribution, partage à l’identique le cas échéant, etc.).


