# 10 - Affichage des statistiques du joueur

## Contexte

Cette spécification définit un système d'affichage des statistiques du joueur sous forme d'interface graphique de type RPG. L'interface doit permettre de visualiser les caractéristiques du personnage (force, intelligence, vitesse, etc.) définies dans le système de niveaux (spécification 7), avec un rendu visuel attractif utilisant des jauges de progression colorées et une représentation du personnage.

## Objectifs

- Créer un composant graphique d'affichage des statistiques du joueur de style RPG
- Afficher chaque statistique sous forme de jauge avec remplissage coloré (rouge, orange, vert) selon le niveau de remplissage
- Intégrer l'affichage du sprite du joueur avec animation de rotation (première colonne de toutes les lignes du sprite walk du niveau actuel, affiché à 400% de sa taille originale dans le bloc de gauche, centré horizontalement et verticalement sans cadre/encart visible)
- Permettre l'affichage/masquage via la touche `S` (pygame.K_s)
- Implémenter un mode dialogue bloquant : le jeu est en pause tant que l'interface est affichée, il faut réappuyer sur `S` pour continuer
- Afficher l'interface au-dessus de tous les autres éléments graphiques (z-index maximum)
- Utiliser les données du système de caractéristiques défini dans la spécification 7
- **Ajouter une icône d'information "I" dans un cercle** à la fin de chaque jauge de statistique
- **Implémenter un système de tooltip** : afficher un texte explicatif détaillé au survol de l'icône "I" avec la souris, utilisant le champ `tooltip_level_N` correspondant au niveau actuel du personnage défini dans le fichier de configuration des statistiques (spécification 7)
- **Ajouter une section d'introduction du personnage** : afficher une présentation du personnage de style RPG en haut de l'interface, incluant le **titre** avec le nom (`display_name` depuis `player_stats.toml`), et les textes d’**Origines**, **Classe & Rôle** et **Traits** sous forme de listes configurées dans **`[presentation]`** du même fichier (spécification **7**)
- **Ajouter un indicateur de progression** : afficher un symbole "^" en jaune à côté du nom de chaque statistique qui a progressé par rapport au niveau précédent (ex: si on est au niveau 2 et que la statistique "vitesse" est plus élevée qu'au niveau 1, afficher l'indicateur)

## Architecture

### Structure de l'interface

L'interface des statistiques se compose de plusieurs éléments :

1. **Fond semi-transparent** : Overlay sombre semi-transparent couvrant tout l'écran pour mettre en évidence l'interface
2. **Panneau principal** : Panneau centré utilisant l'image `affichage_personnage.png` comme fond, redimensionnée pour remplir le panneau (en utilisant le ratio maximum) tout en conservant ses proportions. Cela agrandit l'image et permet d'avoir un panneau central plus grand pour contenir tout le texte. L'image contient deux zones distinctes :
   - **Panneau rectangulaire supérieur** : Panneau rectangulaire central situé dans la section supérieure du cadre en bois, destiné à afficher le nom et le niveau du personnage
   - **Panneau central principal** : Grand panneau central sombre destiné à afficher le sprite, la présentation et les statistiques du personnage
3. **Section titre** : Nom du personnage et niveau affichés dans le **panneau rectangulaire supérieur** de l'image de fond, centrés horizontalement et verticalement dans ce panneau
4. **Section supérieure (panneau central)** : Divisée en 2 colonnes et centrée horizontalement dans le **panneau central principal** de l'image de fond, puis décalée de 100px vers la droite
   - **Colonne gauche (sprite)** : Bloc dédié pour le sprite du personnage, taille agrandie (400%), centré horizontalement et verticalement dans le bloc de gauche (sans cadre/encart visible), aligné verticalement avec le centre de la section de présentation, décalé de 100px vers la droite
   - **Colonne droite (présentation)** : Section de présentation du personnage (origines, classe & rôle, traits de caractère) occupant une largeur maximale définie pour garantir un centrage visuel avec le sprite, décalée de 100px vers la droite
5. **Section inférieure (panneau central)** : Statistiques organisées en **2 colonnes égales** dans le **panneau central principal**, décalées de 100px vers la droite (comme le sprite et la présentation), avec des polices plus grandes pour améliorer la lisibilité. Les noms et valeurs des statistiques utilisent la police **VT323**
6. **Indicateur de progression** : Symbole "^" en jaune affiché à côté du nom de chaque statistique qui a progressé par rapport au niveau précédent (même taille que le nom de la statistique, 28 pixels dans le repère 1280x720, ajusté selon le facteur d'échelle)
7. **Icône d'information** : Icône "I" dans un cercle (32 pixels dans le repère 1280x720, ajustée selon le facteur d'échelle) affichée à la fin de chaque jauge de statistique
8. **Tooltip** : Panneau de texte explicatif affiché au survol de l'icône "I" avec la souris, contenant le texte du champ `tooltip_level_N` correspondant au niveau actuel du personnage pour la statistique, avec une police de 21 pixels (ajustée selon le facteur d'échelle) pour améliorer la lisibilité

### Disposition visuelle

L'interface prend l'ensemble de l'écran avec un padding réduit sur tous les côtés. Pour la résolution de référence 1280×720, le padding est de 30px pour maximiser l'espace disponible et permettre d'afficher tout le contenu (présentation + statistiques) sans débordement. Le layout est réorganisé pour améliorer la lisibilité et optimiser l'utilisation de l'espace, en s'inspirant du style "feuille de personnage" des RPG classiques.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│  (padding 30px pour 1280×720)                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  [Cadre en bois avec torches, chaîne, engrenage]                    │   │
│  │                                                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │                                                               │   │   │
│  │  │        {display_name} (Niveau: 5)                            │   │   │
│  │  │        (Panneau rectangulaire supérieur)                     │   │   │
│  │  │                                                               │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │                                                               │   │   │
│  │  │        ┌──────────┐    ┌──────────────────────────────────┐ │   │   │
│  │  │        │          │    │                                  │ │   │   │
│  │  │        │ [Sprite] │    │  Origines                        │ │   │   │
│  │  │        │ (400%)   │    │  • Background : Chef de projet   │ │   │   │
│  │  │        │ rotation │    │  • Déclic : Il y a 5 ans...      │ │   │   │
│  │  │        │ (centré  │    │  • Mantra : Faire, mesurer...    │ │   │   │
│  │  │        │ vertical)│    │                                  │ │   │   │
│  │  │        │          │    │  Classe & Rôle                   │ │   │   │
│  │  │        │          │    │  • Classe : Project Mage...      │ │   │   │
│  │  │        │          │    │  • Sous-classe : Explorateur ML  │ │   │   │
│  │  │        │          │    │  • Alignement : Curiosité...     │ │   │   │
│  │  │        └──────────┘    │                                  │ │   │   │
│  │  │                         │  Traits de caractère             │ │   │   │
│  │  │                         │  • Bidouilleur empirique...      │ │   │   │
│  │  │                         │  • Pont entre métiers et data    │ │   │   │
│  │  │                         │  • Aime prototyper vite...       │ │   │   │
│  │  │                         └──────────────────────────────────┘ │   │   │
│  │  │                                                               │   │   │
│  │  │  ┌────────────────────┐  ┌────────────────────┐             │   │   │
│  │  │  │ Force ^            │  │ Intelligence       │             │   │   │
│  │  │  │ [████████░░] (I)   │  │ [███████░░] (I)    │             │   │   │
│  │  │  │ 80/100             │  │ 75/100             │             │   │   │
│  │  │  └────────────────────┘  └────────────────────┘             │   │   │
│  │  │                                                               │   │   │
│  │  │  ┌────────────────────┐  ┌────────────────────┐             │   │   │
│  │  │  │ Vitesse ^          │  │ [Autre stat]       │             │   │   │
│  │  │  │ [█████████░░] (I)  │  │ [████████░░] (I)   │             │   │   │
│  │  │  │ 85/100             │  │ [valeur/max]       │             │   │   │
│  │  │  └────────────────────┘  └────────────────────┘             │   │   │
│  │  │                                                               │   │   │
│  │  │        (Panneau central principal)                           │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  (padding 30px pour 1280×720)                                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Caractéristiques du layout** :
- **Panneau plein écran** : Le panneau prend toute la largeur et hauteur de l'écran avec un padding réduit (30px pour la résolution 1280×720) sur tous les côtés pour maximiser l'espace disponible et permettre d'afficher tout le contenu sans débordement
- **Structure de l'image de fond** : L'image `affichage_personnage.png` contient deux zones distinctes :
  - **Panneau rectangulaire supérieur** : Panneau rectangulaire central situé dans la section supérieure du cadre en bois, utilisé pour afficher le nom et le niveau
  - **Panneau central principal** : Grand panneau central sombre utilisé pour afficher le sprite, la présentation et les statistiques
- **Nom du personnage** : Le nom avec le niveau entre parenthèses est affiché dans le **panneau rectangulaire supérieur**, **centré horizontalement et verticalement** dans ce panneau. Format : « `{display_name}` (Niveau: X) » où **`display_name`** est la chaîne obligatoire à la racine de `config/player_stats.toml` (spécification **7**) — **même source** que le nom au-dessus du sprite du joueur (spécification **2**). Aucun nom codé en dur pour ce titre.
- **Layout en 2 zones principales** :
  - **Zone supérieure (panneau rectangulaire)** : Nom du personnage avec le niveau entre parenthèses, centré horizontalement et verticalement dans le panneau rectangulaire supérieur de l'image
  - **Zone centrale (panneau principal)** : Contenu principal divisé en 2 sections :
    - **Section supérieure** : Divisée en 2 colonnes et centrée horizontalement dans le panneau central, puis décalée de 100px vers la droite. Le sprite est dans la colonne gauche, centré verticalement dans son espace. La présentation est dans la colonne droite.
    - **Section inférieure** : Statistiques organisées en **2 colonnes**, avec des polices adaptées (28 pixels par défaut, ajustées selon le facteur d'échelle) pour optimiser l'espace tout en conservant la lisibilité
- **Sprite agrandi** : Le sprite est affiché à **400% de sa taille originale** dans un bloc dédié de 267 pixels de largeur (ajusté selon le facteur d'échelle), **centré horizontalement et verticalement** dans ce bloc sans cadre/encart visible
- **Statistiques en 2 colonnes** : Les statistiques sont organisées en 2 colonnes égales, chaque colonne occupant environ 50% de la largeur disponible (moins les marges et l'espacement entre colonnes)
- **Barres de statistiques** : Les barres de statistiques utilisent la largeur disponible dans leur colonne (moins les marges et un padding supplémentaire de 20px pour qu'elles rentrent bien dans le panneau central de l'image), puis sont réduites de 1/3 (multipliées par 2/3) pour garantir qu'elles restent bien à l'intérieur du cadre de l'image, améliorant la lisibilité
- **Espacement optimisé** : L'espacement vertical entre les statistiques est ajusté dynamiquement en fonction de la hauteur des textes et des jauges, avec un minimum de 40 pixels (ajusté selon le facteur d'échelle) pour éviter tout chevauchement
- **Espacement nom-jauge** : L'espacement entre le nom de la statistique et sa jauge est de 8 pixels (ajusté selon le facteur d'échelle) pour améliorer la lisibilité
- **Espacement entre colonnes** : Un espacement fixe de 10 pixels (en 1280×720) sépare les deux colonnes de statistiques

**Légende** : `^` représente l'indicateur de progression en jaune, affiché à côté du nom de la statistique si elle a progressé par rapport au niveau précédent. `(I)` représente l'icône "I" dans un cercle, de taille plus grande que précédemment. Au survol de cette icône, un tooltip s'affiche avec le texte explicatif de la statistique correspondant au niveau actuel du personnage.

### Section titre (nom du personnage)

Le nom du personnage et le niveau sont affichés dans le **panneau rectangulaire supérieur** de l'image de fond `affichage_personnage.png`.

**Caractéristiques** :
- **Position** : Affiché dans le panneau rectangulaire central situé dans la section supérieure du cadre en bois de l'image de fond
- **Centrage** : **Centré horizontalement et verticalement** dans le panneau rectangulaire supérieur
- **Source du nom** : `PlayerStatsConfig.display_name` (clé racine **`display_name`** dans `player_stats.toml`, non vide — erreur explicite au chargement si absent ou vide, voir spécification **7**)
- Format : « `{display_name}` (Niveau: X) » où X est le niveau actuel du personnage
- Le niveau est affiché entre parenthèses à côté du nom, sur la même ligne
- **Police** : **VT323** (Google Fonts) — look rétro CRT, très lisible pour titres/niveaux. Taille importante (ex: 28-32 pixels selon le facteur d'échelle), adaptée à la taille du panneau rectangulaire
- Couleur distinctive (ex: blanc ou couleur dorée `(255, 215, 0)`) pour un bon contraste avec le fond du panneau rectangulaire
- Style : avec optionnellement un léger effet d'ombre ou de contour pour la lisibilité
- **Détection du panneau rectangulaire** : Les coordonnées et dimensions du panneau rectangulaire supérieur doivent être détectées depuis l'image ou définies manuellement pour positionner correctement le texte

### Section de présentation du personnage

Une section de présentation du personnage de style RPG est affichée dans la colonne droite de la section supérieure du **panneau central principal**, alignée verticalement avec le sprite. Cette section présente le personnage de manière immersive et narrative.

**Structure de la présentation** :

1. **Origines** :
   - Titre de section : "Origines" — **Police** : **Silkscreen** (affichages courts, boutons et onglets). Taille moyenne, couleur secondaire
   - **Contenu** : liste de chaînes à afficher en **puces**, au même format que les traits (une entrée du fichier = une puce ; le libellé « Background », « Déclic », etc. fait partie du texte si le créateur de contenu le souhaite, ex. `"Background : …"`).
   - **Police du texte** : **VT323** — look rétro CRT, très lisible pour titres/niveaux et texte de présentation

2. **Classe & Rôle** :
   - Titre de section : "Classe & Rôle" — **Police** : **Silkscreen** (affichages courts, boutons et onglets). Taille moyenne, couleur secondaire
   - **Contenu** : même modèle qu’**Origines** — tableau de chaînes, une ligne affichée par puce (ex. `"Classe : …"`, `"Sous-classe : …"`).
   - **Police du texte** : **VT323** — look rétro CRT, très lisible pour titres/niveaux et texte de présentation

3. **Traits de caractère** :
   - Titre de section : "Traits de caractère" — **Police** : **Silkscreen** (affichages courts, boutons et onglets). Taille moyenne, couleur secondaire
   - **Contenu** : liste de chaînes, une puce par élément (comportement inchangé côté rendu par rapport à l’ancienne liste `traits`).
   - **Police du texte** : **VT323** — look rétro CRT, très lisible pour titres/niveaux et texte de présentation

**Source des textes** : les trois listes sont lues depuis `config/player_stats.toml` (section **`[presentation]`**, clés `origins`, `class_role`, `traits` — voir spécification **7**). **Aucune** constante `DEFAULT_CHARACTER_PRESENTATION` ni équivalent codé en dur dans le moteur : si le fichier stats est chargé pour le jeu, ces clés sont **obligatoires** et validées au chargement.

**Style visuel** :
- Fond légèrement différencié (optionnel) : panneau avec fond légèrement plus clair ou plus foncé que le panneau principal, ou simplement avec une bordure subtile
- Espacement vertical : 10-13 pixels entre chaque section (Origines, Classe & Rôle, Traits de caractère), ajusté selon le facteur d'échelle
- Espacement horizontal : padding de 13-20 pixels de chaque côté, ajusté selon le facteur d'échelle
- Puces : caractères Unicode (•) ou symboles personnalisés, avec un espacement de 7-10 pixels entre la puce et le texte, ajusté selon le facteur d'échelle
- Texte : **VT323** pour le texte de présentation (paragraphes), taille adaptative selon le facteur d'échelle (ex: 18-23 pixels pour le texte normal, ajusté selon le facteur d'échelle pour garantir la lisibilité de la présentation)
- **Word wrapping** : Le texte de présentation utilise un système de retour à la ligne automatique (word wrapping) pour diviser les lignes trop longues en plusieurs lignes, garantissant que tout le texte reste visible dans le panneau central de l'image. Le wrapping est effectué mot par mot pour préserver la lisibilité.
- Couleurs : hiérarchie visuelle claire (titres de section en couleur secondaire, texte en couleur de texte standard ; le nom du **titre** du panneau supérieur suit la couleur d’accent définie pour ce titre, alimenté par `display_name`)

**Configuration obligatoire (`player_stats.toml`)** :

- Le **nom dans le panneau titre** provient exclusivement de **`display_name`** (racine du TOML), comme aujourd’hui.
- Le contenu de la **colonne présentation** provient de la table **`[presentation]`** avec trois clés **`origins`**, **`class_role`**, **`traits`** : chacune est un **tableau de chaînes** (syntaxe TOML), affiché comme liste à puces — **même logique de rendu** pour les trois blocs (plus de sous-champs `background` / `trigger` / `mantra` ni `class` / `subclass` / `alignment` côté moteur).
- **Pas de valeur par défaut** dans le code pour ces listes : absence de la section, d’une clé, type incorrect, liste vide, ou chaîne vide après `strip()` pour au moins une entrée → **`ValueError`** (ou erreur de validation équivalente) au **chargement** de `player_stats.toml`, avec message explicite (fichier, section, clé).
- **`character_presentation.py`** : traiter `origins` et `class_role` comme des **`list[str]`** et les dessiner comme **`traits`** (puces + word wrapping), sans branche spéciale dictionnaire clé/valeur.

**Personnalisation / tests** :
- En jeu normal, `PlayerStatsDisplay` construit le dictionnaire passé au rendu à partir de **`player.level_manager.stats_config`** (champs issus de `[presentation]`).
- Le paramètre constructeur **`character_presentation`** reste utilisable **uniquement** pour injection en tests ou outils ; il ne doit **pas** servir de repli silencieux quand la config TOML est chargée : sans surcharge explicite, la source de vérité est le TOML.

### Système de couleurs des jauges

Les jauges utilisent un système de couleurs basé sur le pourcentage de remplissage :

- **Rouge** : 0% à 33% de remplissage (faible)
- **Orange** : 34% à 66% de remplissage (moyen)
- **Vert** : 67% à 100% de remplissage (élevé)

Le pourcentage est calculé en fonction de la valeur maximale possible pour chaque statistique (niveau 5).

### Indicateur de progression

Chaque statistique peut afficher un **indicateur de progression "^" en jaune** à côté de son nom si elle a progressé par rapport au niveau précédent.

**Caractéristiques de l'indicateur** :
- **Symbole** : "^" (caractère Unicode ou symbole personnalisé)
- **Couleur** : Jaune (ex: `(255, 215, 0)` ou `(255, 255, 0)`) pour un bon contraste et une visibilité claire
- **Taille** : Même taille que le nom de la statistique (28 pixels par défaut dans le repère 1280×720, ajustée selon le facteur d'échelle)
- **Position** : Immédiatement après le nom de la statistique, avec un espacement de 5-8 pixels (ajusté selon le facteur d'échelle)
- **Police** : **VT323** — même police que le nom de la statistique pour la cohérence visuelle

**Logique d'affichage** :
- L'indicateur s'affiche **uniquement si** :
  - Le niveau actuel du personnage est **supérieur à 1** (pas d'indicateur au niveau 1, car il n'y a pas de niveau précédent)
  - La valeur actuelle de la statistique est **strictement supérieure** à la valeur de la statistique au niveau précédent
- L'indicateur ne s'affiche **pas** si :
  - Le niveau actuel est 1 (pas de niveau précédent)
  - La valeur actuelle est égale ou inférieure à la valeur du niveau précédent
  - La statistique n'existe pas ou n'a pas de valeur définie pour le niveau précédent

**Calcul de progression** :
- Pour chaque statistique, comparer la valeur actuelle (`player.level_manager.get_stat_value(stat_identifier)`) avec la valeur du niveau précédent (`player.level_manager.stats_config.get_stat_value(stat_identifier, current_level - 1)`)
- Si `current_value > previous_value`, afficher l'indicateur "^" en jaune
- La comparaison est effectuée à chaque affichage de l'interface pour garantir que l'indicateur reflète toujours l'état actuel

**Exemple** :
- Niveau 1 : Vitesse = 12 → Pas d'indicateur (niveau 1)
- Niveau 2 : Vitesse = 22 → Indicateur "^" affiché (22 > 12)
- Niveau 3 : Vitesse = 38 → Indicateur "^" affiché (38 > 22)
- Niveau 4 : Vitesse = 58 → Indicateur "^" affiché (58 > 38)
- Niveau 5 : Vitesse = 85 → Indicateur "^" affiché (85 > 58)

**Mise à jour dynamique** :
- L'indicateur est recalculé à chaque affichage de l'interface
- Lors d'un changement de niveau (via les touches `P`/`O`), l'indicateur se met à jour automatiquement pour refléter la progression par rapport au nouveau niveau précédent

### Icône d'information et système de tooltip

Chaque jauge de statistique est accompagnée d'une **icône d'information "I" dans un cercle** positionnée à la fin de la jauge (après la valeur numérique).

**Caractéristiques de l'icône** :
- Taille : cercle de **32 pixels de diamètre** (ajusté selon le facteur d'échelle, configurable pour améliorer la visibilité)
- Couleur : blanc ou gris clair (ex: `(200, 200, 200)`) pour un bon contraste
- Position : alignée verticalement avec la jauge, à droite de la valeur numérique avec un espacement de 5-10 pixels
- **Police** : **VT323** — look rétro CRT, très lisible pour labels et petites tailles. Taille adaptée à la nouvelle taille du cercle

**Système de tooltip** :
- Le tooltip s'affiche **au survol de l'icône** avec la souris (événement `MOUSEMOTION`)
- Le tooltip contient le texte du champ `tooltip_level_N` correspondant au **niveau actuel du personnage** défini dans le fichier de configuration `player_stats.toml` (spécification 7)
  - Exemple : si le personnage est au niveau 3, le tooltip affichera le texte de `tooltip_level_3` pour la statistique survolée
  - Le niveau actuel est récupéré via `player.level_manager.level`
- Si le champ `tooltip_level_N` n'est pas défini pour le niveau actuel d'une statistique, l'icône est toujours affichée mais aucun tooltip ne s'affiche au survol
- Le tooltip est un panneau rectangulaire avec :
  - Fond semi-transparent (ex: `(30, 30, 40, 240)` avec alpha)
  - Bordure fine (1-2 pixels) de couleur claire
  - Texte multi-lignes (gérer les sauts de ligne `\n` dans le texte)
  - **Word wrapping automatique** : Les lignes de texte trop longues sont automatiquement divisées en plusieurs lignes pour respecter la largeur maximale du tooltip. Le texte ne doit jamais être tronqué.
  - Padding interne (8-10 pixels)
  - Positionnement : au-dessus ou à côté de l'icône, en évitant de sortir de l'écran
  - Largeur maximale : 600 pixels (ajusté selon le facteur d'échelle) pour améliorer la lisibilité des textes longs et éviter un trop grand nombre de retours à la ligne
  - **Taille de police** : La police du tooltip est de 21 pixels par défaut (ajustée selon le facteur d'échelle) pour améliorer la lisibilité des descriptions détaillées
  - **Police** : **VT323** — look rétro CRT, très lisible pour les descriptions détaillées des tooltips
  - Le tooltip disparaît lorsque la souris quitte l'icône ou l'interface
- **Mise à jour dynamique** : lorsque le niveau du personnage change (via les touches `P`/`O`), le tooltip affiché au survol change automatiquement pour correspondre au nouveau niveau

### Extraction et animation du sprite du joueur

Le sprite du joueur affiché correspond à :
- Le sprite sheet `walk.png` du niveau actuel du joueur
- La première colonne (col = 0) de **toutes les lignes** du sprite sheet (lignes 0, 1, 2, 3)
- Ces 4 sprites représentent le personnage vu sous différents angles (haut, bas, gauche, droite)
- Le sprite est affiché à **400% de sa taille originale** (4.0x, agrandi pour une meilleure visibilité)
- Le sprite est affiché dans un **bloc dédié en haut à gauche** du panneau, centré horizontalement et verticalement dans ce bloc **sans cadre/encart visible**
- Le sprite **tourne sur lui-même** en affichant successivement les 4 sprites avec un timing fixe, créant une animation de rotation continue
- **Dimensions du bloc sprite** : Le bloc a une largeur fixe d'environ 267 pixels (ajustée selon le facteur d'échelle) et une hauteur adaptée au sprite redimensionné, avec un padding interne de 13 pixels (ajusté selon le facteur d'échelle) pour le calcul du centrage

**Animation de rotation** :
- Les 4 sprites (lignes 0, 1, 2, 3, colonne 0) sont affichés en séquence pour créer une rotation
- Le timing de rotation est fixe (ex: 0.5 seconde par sprite, soit 2 secondes pour une rotation complète)
- L'animation se répète en boucle tant que l'interface est affichée
- L'animation continue même si le jeu est en pause (elle utilise le delta time de la boucle de rendu)
- **Gestion du changement de niveau** : À chaque frame d'animation, le système vérifie le niveau actuel du personnage (`player.level_manager.level`). Si le niveau a changé depuis la dernière extraction des sprites, les sprites sont automatiquement réextraits depuis le sprite sheet du nouveau niveau et l'animation de rotation est réinitialisée (timer remis à 0, frame actuelle remise à 0). Cela garantit que l'animation affiche toujours les sprites correspondant au niveau actuel du personnage, même si le niveau change pendant que l'interface est affichée, et évite tout mélange de sprites entre différents niveaux.

## Spécifications techniques

### Image de fond du panneau

Le panneau principal utilise l'image `affichage_personnage.png` (située dans `sprite/interface/affichage_personnage.png`) comme fond.

**Caractéristiques** :
- L'image est chargée une fois lors de l'initialisation et mise en cache
- L'image est redimensionnée pour remplir le panneau (largeur et hauteur) en utilisant le ratio maximum, ce qui agrandit l'image et permet d'avoir un panneau central plus grand. Les proportions sont conservées (aspect ratio). L'image est centrée dans le panneau si elle dépasse légèrement.
- Le redimensionnement utilise `pygame.transform.smoothscale()` pour une meilleure qualité visuelle
- L'image est dessinée en premier, avant tous les autres éléments du panneau (texte, jauges, sprite)
- Si l'image n'est pas trouvée, le panneau utilise un fond de couleur unie (couleur par défaut `bg_color`) comme fallback
- L'image est recréée uniquement si les dimensions du panneau changent (changement de résolution)

**Structure de l'image** :
L'image `affichage_personnage.png` contient deux zones distinctes qui doivent être identifiées pour le positionnement du contenu :
1. **Panneau rectangulaire supérieur** : Panneau rectangulaire central situé dans la section supérieure du cadre en bois
   - Utilisé pour afficher le nom et le niveau du personnage
   - Les coordonnées et dimensions de ce panneau doivent être détectées depuis l'image ou définies manuellement
   - Le texte est centré horizontalement et verticalement dans ce panneau
2. **Panneau central principal** : Grand panneau central sombre
   - Utilisé pour afficher le sprite, la présentation et les statistiques
   - Les coordonnées et dimensions de ce panneau doivent être détectées depuis l'image ou définies manuellement
   - Le contenu est organisé en colonnes et sections dans ce panneau

**Détection des zones** :
- Les coordonnées et dimensions des deux panneaux peuvent être :
  - Détectées automatiquement depuis l'image (analyse des zones de couleur, détection de contours)
  - Définies manuellement via des paramètres de configuration (coordonnées x, y, largeur, hauteur)
  - Définies par défaut dans le code avec des valeurs relatives à la taille de l'image
- Les coordonnées sont mises à l'échelle proportionnellement lorsque l'image est redimensionnée pour s'adapter au panneau

### Adaptation à la résolution

L'interface des statistiques est **toujours rendue directement en 1280×720** sans redimensionnement. Toutes les valeurs par défaut sont exprimées directement dans le repère de référence 1280×720 (`get_render_size()`). Les assets graphiques (images de fond, sprites) sont redimensionnés si nécessaire pour s'adapter à cette résolution, mais l'interface elle-même n'utilise pas de facteur d'échelle et est toujours rendue en 1280×720.

**Valeurs de présentation** :
- Les tailles de police de présentation (`presentation_name_font_size`, `presentation_section_font_size`, `presentation_text_font_size`) sont définies directement en 1280×720 et utilisées telles quelles (pas de scaling)
- Les espacements de présentation (`presentation_padding`, `presentation_section_spacing`) sont définis directement en 1280×720 et utilisés telles quelles (pas de scaling)
- **Toutes les valeurs hardcodées** utilisées dans la section de présentation sont définies directement en 1280×720 et utilisées telles quelles :
  - Espacement après le nom : `13` pixels
  - Espacement entre la puce et le texte : `8` pixels
  - Espacement après le titre de section : `5` pixels
  - Espacement entre les items : `3` pixels
  - Largeur du cadre sprite : `267` pixels
  - Padding interne du cadre sprite : `13` pixels
  - Hauteur par défaut du cadre sprite : `133` pixels
  - Espacement entre sprite et présentation : `21` pixels
  - Largeur minimale de la présentation : `213` pixels
  - Position Y de fallback : `67` pixels
  - Espacement après la section supérieure : `20` pixels
- **Important** : Toutes les valeurs sont définies directement en 1280×720 et utilisées telles quelles sans scaling. L'interface est toujours rendue en 1280×720.

**Rendu direct en 1280×720** :
- L'interface est **toujours rendue directement en 1280×720** sans facteur d'échelle
- Le facteur d'échelle est toujours 1.0 (pas de scaling)
- Toutes les valeurs sont utilisées directement en 1280×720 :
  - Dimensions du panneau : 1220×660 (1280 - 60 padding, 720 - 60 padding)
  - Tailles des polices : utilisées directement (28px pour les stats, 37px pour le titre, etc.)
  - Largeur et hauteur des jauges de statistiques : utilisées directement (19px de hauteur)
  - Espacements : utilisés directement (padding de 30px, espacements entre les stats, etc.)
  - Taille des icônes d'information : 32px directement
  - Dimensions des tooltips : utilisées directement (233px de largeur max, 21px de police)
  - Taille du sprite du joueur : 400% de la taille originale (4.0x)
  - Tailles des polices : utilisées directement (ex. 32px pour `presentation_name_font_size` appliqué au titre « `display_name` (Niveau: X) », 16px pour les titres de sections de la colonne présentation, 18px pour le texte de présentation)
  - Espacements de la section de présentation : utilisés directement (17px de padding, 12px entre sections)
  - Dimensions de l'image de fond du panneau : redimensionnée pour remplir le panneau (1220×660) en utilisant le ratio maximum, ce qui agrandit l'image et permet d'avoir un panneau central plus grand pour contenir tout le texte. L'image est centrée dans le panneau si elle dépasse légèrement.

**Mise en cache** :
- Les surfaces (panneau, overlay, sprites, image de fond) sont mises en cache et recréées uniquement si nécessaire (changement de niveau, invalidation du cache)
- L'image de fond est mise en cache et recréée uniquement si les dimensions du panneau changent
- Les sprites du joueur sont mis en cache et recréés uniquement si le niveau change
- Cela garantit de bonnes performances

**Résolution de référence** :
- Résolution de référence : 1280×720 pixels (`get_render_size()`)
- Toutes les valeurs par défaut de l'interface sont exprimées directement dans ce repère 1280×720
- L'interface est **toujours rendue directement en 1280×720** sans redimensionnement
- Les assets graphiques (images de fond, sprites) sont redimensionnés si nécessaire pour s'adapter à cette résolution
- Le facteur d'échelle est toujours 1.0 (pas de scaling de l'interface)

### Structure des données

#### Architecture modulaire

L'interface des statistiques du joueur est organisée en modules séparés pour améliorer la maintenabilité et la réutilisabilité :

- **`player_stats_display.py`** : Classe principale `PlayerStatsDisplay` qui orchestre l'affichage
- **`animated_sprite.py`** : Module `AnimatedSpriteManager` pour la gestion des sprites animés
- **`stat_bar.py`** : Fonctions utilitaires pour les barres de statistiques et indicateurs de progression
- **`stat_tooltip.py`** : Fonctions utilitaires pour la gestion des tooltips
- **`character_presentation.py`** : Fonctions utilitaires pour la présentation du personnage
- **`text_utils.py`** : Fonctions utilitaires pour le rendu de texte (word wrapping, rendu)

#### Classe `PlayerStatsDisplay`

```python
from typing import Optional, Dict, Any, List, Tuple
from moteur_jeu_presentation.ui.animated_sprite import AnimatedSpriteManager

class PlayerStatsDisplay:
    """Interface d'affichage des statistiques du joueur."""
    
    def __init__(
        self,
        player: Player,
        screen_width: int,
        screen_height: int,
        font: Optional[pygame.font.Font] = None,
        font_size: int = 28,
        title_font_size: int = 37,
        panel_width: int = 600,
        panel_height: int = 400,
        padding: int = 20,
        stat_bar_width: int = 200,
        stat_bar_height: int = 19,
        overlay_alpha: int = 180,
        bg_color: Tuple[int, int, int] = (40, 40, 50),
        border_color: Tuple[int, int, int] = (200, 200, 200),
        border_width: int = 3,
        title_color: Tuple[int, int, int] = (255, 255, 255),
        stat_name_color: Tuple[int, int, int] = (220, 220, 220),
            stat_value_color: Tuple[int, int, int] = (255, 255, 255),
            level_color: Tuple[int, int, int] = (255, 215, 0),
            sprite_scale: float = 4.0,
            rotation_speed: float = 0.5,
        info_icon_size: int = 32,
        info_icon_color: Tuple[int, int, int] = (200, 200, 200),
        tooltip_bg_color: Tuple[int, int, int, int] = (30, 30, 40, 240),
        tooltip_border_color: Tuple[int, int, int] = (200, 200, 200),
        tooltip_text_color: Tuple[int, int, int] = (255, 255, 255),
        tooltip_padding: int = 7,
        tooltip_max_width: int = 600,
        tooltip_font_size: int = 21,
        character_presentation: Optional[Dict[str, Any]] = None,
        presentation_name_font_size: int = 32,
        presentation_section_font_size: int = 16,
        presentation_text_font_size: int = 18,
        presentation_name_color: Tuple[int, int, int] = (255, 215, 0),
        presentation_section_color: Tuple[int, int, int] = (200, 200, 200),
        presentation_text_color: Tuple[int, int, int] = (220, 220, 220),
        presentation_padding: int = 17,
        presentation_section_spacing: int = 12,
        background_image_path: Optional[str] = None,
        fonts_dir: Optional[str] = None,
        title_panel_rect: Optional[Tuple[int, int, int, int]] = None,
        main_panel_rect: Optional[Tuple[int, int, int, int]] = None,
        offset_x: int = 70,
        offset_y: int = 0,
    ) -> None:
        """
        Args:
            player: Instance du joueur dont on affiche les statistiques
            screen_width: Largeur de l'écran
            screen_height: Hauteur de l'écran
            font: Police à utiliser pour le texte (optionnel)
            font_size: Taille de la police pour les statistiques (défaut: 28 pixels dans le repère 1280x720)
            title_font_size: Taille de la police pour le titre
            panel_width: Largeur du panneau principal (ignoré, calculé automatiquement comme screen_width - 200)
            panel_height: Hauteur du panneau principal (ignoré, calculé automatiquement comme screen_height - 200)
            padding: Espacement interne du panneau (entre les éléments à l'intérieur du panneau)
            stat_bar_width: Largeur des jauges de statistiques
            stat_bar_height: Hauteur des jauges de statistiques (défaut: 19 pixels dans le repère 1280x720)
            overlay_alpha: Transparence de l'overlay (0-255)
            bg_color: Couleur de fond du panneau (RGB)
            border_color: Couleur de la bordure du panneau (RGB)
            border_width: Épaisseur de la bordure
            title_color: Couleur du titre (RGB)
            stat_name_color: Couleur des noms de statistiques (RGB)
            stat_value_color: Couleur des valeurs de statistiques (RGB)
            level_color: Couleur de l'affichage du niveau (RGB)
            sprite_scale: Facteur d'échelle pour le sprite du joueur (défaut: 4.0 = 400%)
            rotation_speed: Durée en secondes pour afficher chaque sprite de la rotation (défaut: 0.5)
            info_icon_size: Taille de l'icône d'information en pixels (défaut: 32 dans le repère 1280x720)
            info_icon_color: Couleur de l'icône d'information (RGB, défaut: (200, 200, 200))
            tooltip_bg_color: Couleur de fond du tooltip avec alpha (RGBA, défaut: (30, 30, 40, 240))
            tooltip_border_color: Couleur de la bordure du tooltip (RGB, défaut: (200, 200, 200))
            tooltip_text_color: Couleur du texte du tooltip (RGB, défaut: (255, 255, 255))
            tooltip_padding: Espacement interne du tooltip en pixels (défaut: 7 dans le repère 1280x720)
            tooltip_max_width: Largeur maximale du tooltip en pixels (défaut: 600 dans le repère 1280x720)
            tooltip_font_size: Taille de la police du tooltip en pixels (défaut: 21 dans le repère 1280x720)
            character_presentation: Présentation explicite pour tests/outils ; si None, construite depuis `stats_config` et `[presentation]` du TOML (obligatoire en jeu — pas de défaut code)
            presentation_name_font_size: Taille de la police pour le nom du personnage (défaut: 32 dans le repère 1280x720)
            presentation_section_font_size: Taille de la police pour les titres de section (défaut: 16 dans le repère 1280x720)
            presentation_text_font_size: Taille de la police pour le texte de présentation (défaut: 18 dans le repère 1280x720)
            presentation_name_color: Couleur du nom du personnage (RGB, défaut: (255, 215, 0) = doré)
            presentation_section_color: Couleur des titres de section (RGB, défaut: (200, 200, 200))
            presentation_text_color: Couleur du texte de présentation (RGB, défaut: (220, 220, 220))
            presentation_padding: Espacement horizontal de la section de présentation (défaut: 17 dans le repère 1280x720)
            presentation_section_spacing: Espacement vertical entre les sections (défaut: 12 dans le repère 1280x720)
            background_image_path: Chemin vers l'image de fond du panneau (défaut: "sprite/interface/affichage_personnage.png")
            fonts_dir: Répertoire contenant les fichiers de polices (défaut: "fonts/" ou répertoire système)
            title_panel_rect: Rectangle du panneau rectangulaire supérieur (x, y, width, height) en coordonnées relatives à l'image originale. Si None, les coordonnées sont détectées automatiquement ou utilisent des valeurs par défaut
            main_panel_rect: Rectangle du panneau central principal (x, y, width, height) en coordonnées relatives à l'image originale. Si None, les coordonnées sont détectées automatiquement ou utilisent des valeurs par défaut
            offset_x: Décalage horizontal en pixels pour le sprite, la présentation et les statistiques (défaut: 70 dans le repère 1280x720). Permet de déplacer horizontalement tout le contenu (sprite, présentation, stats) pour s'adapter à la mise en page de l'image de fond.
            offset_y: Décalage vertical en pixels pour le sprite, la présentation et les statistiques (défaut: 0 dans le repère 1280x720). Permet de déplacer verticalement tout le contenu (sprite, présentation, stats) pour s'adapter à la mise en page de l'image de fond.
        """
```

**Propriétés** :
- `player: Player` : Instance du joueur
- `is_visible: bool` : Indique si l'interface est actuellement affichée
- `screen_width: int` : Largeur de l'écran
- `screen_height: int` : Hauteur de l'écran
- `panel_padding: int` : Padding fixe de 100px autour du panneau (le panneau prend tout l'écran avec ce padding)
- `panel_width: int` : Largeur du panneau (calculée comme screen_width - panel_padding * 2)
- `panel_height: int` : Hauteur du panneau (calculée comme screen_height - panel_padding * 2)
- `panel_surface: pygame.Surface` : Surface du panneau principal
- `overlay_surface: pygame.Surface` : Surface de l'overlay semi-transparent
- `sprite_manager: AnimatedSpriteManager` : Gestionnaire des sprites animés du joueur
- `hovered_stat_identifier: Optional[str]` : Identifiant de la statistique dont l'icône est survolée (None si aucune)
- `tooltip_surface: Optional[pygame.Surface]` : Surface du tooltip actuellement affiché (None si aucun tooltip)
- `tooltip_rect: Optional[pygame.Rect]` : Rectangle de position du tooltip
- `tooltip_font: pygame.font.Font` : Police pour le texte des tooltips (taille réduite)
- `character_presentation: Dict[str, Any]` : Dictionnaire avec les clés `origins`, `class_role`, `traits`, chacune associée à une **`list[str]`** (rempli depuis `player_stats.toml` en jeu normal)
- `presentation_name_font: pygame.font.Font` : Police pour le nom du personnage (VT323)
- `presentation_section_font: pygame.font.Font` : Police pour les titres de section (Silkscreen)
- `presentation_text_font: pygame.font.Font` : Police pour le texte de présentation (VT323)
- `stat_font: pygame.font.Font` : Police pour les noms et valeurs des statistiques (VT323)
- `tooltip_font: pygame.font.Font` : Police pour les tooltips (VT323)
- `info_icon_font: pygame.font.Font` : Police pour l'icône "I" (VT323)
- `background_image: Optional[pygame.Surface]` : Image de fond du panneau (affichage_personnage.png), mise en cache
- `background_image_scaled: Optional[pygame.Surface]` : Image de fond redimensionnée pour le panneau, mise en cache
- `title_panel_rect: Optional[pygame.Rect]` : Rectangle du panneau rectangulaire supérieur dans l'image redimensionnée (coordonnées écran)
- `main_panel_rect: Optional[pygame.Rect]` : Rectangle du panneau central principal dans l'image redimensionnée (coordonnées écran)
- `title_panel_rect_original: Optional[Tuple[int, int, int, int]]` : Rectangle du panneau rectangulaire supérieur dans l'image originale (coordonnées relatives)
- `main_panel_rect_original: Optional[Tuple[int, int, int, int]]` : Rectangle du panneau central principal dans l'image originale (coordonnées relatives)
- `_cached_screen_size: Optional[Tuple[int, int]]` : Taille d'écran mise en cache pour détecter les changements de résolution
- `_cached_panel_size: Optional[Tuple[int, int]]` : Taille du panneau mise en cache pour détecter les changements nécessitant un redimensionnement de l'image de fond

**Méthodes principales** :
- `toggle() -> None` : Bascule l'affichage (affiche si masqué, masque si affiché)
- `show() -> None` : Affiche l'interface
- `hide() -> None` : Masque l'interface
- `handle_mouse_event(event: pygame.event.Event) -> None` : Gère les événements de souris (MOUSEMOTION) pour détecter le survol des icônes
- `draw(surface: pygame.Surface, dt: float) -> None` : Dessine l'interface sur la surface (si visible) et met à jour l'animation de rotation
- `_create_overlay() -> pygame.Surface` : Crée la surface de l'overlay semi-transparent
- `_create_panel() -> pygame.Surface` : Crée la surface du panneau principal (sans le sprite animé, qui est dessiné directement dans `draw()`)
- `_load_background_image() -> Optional[pygame.Surface]` : Charge l'image de fond depuis le chemin spécifié, retourne None si l'image n'est pas trouvée
- `_scale_background_image(width: int, height: int) -> Optional[pygame.Surface]` : Redimensionne l'image de fond pour s'adapter aux dimensions du panneau, retourne None si l'image n'est pas chargée
- `_detect_panel_rects() -> Tuple[Optional[pygame.Rect], Optional[pygame.Rect]]` : Détecte ou calcule les rectangles des panneaux (rectangulaire supérieur et central principal) depuis l'image. Retourne (title_panel_rect, main_panel_rect)
- `_update_panel_rects() -> None` : Met à jour les rectangles des panneaux en fonction de la taille de l'image redimensionnée
- `_load_font(font_name: str, font_size: int, fallback_fonts: List[str] = None) -> pygame.font.Font` : Charge une police depuis le répertoire des polices avec système de fallback. Les polices sont recherchées dans l'ordre : répertoire spécifié, répertoire système, police système par défaut
- `_draw_stat_bar(...) -> Tuple[Optional[pygame.Rect], int]` : Dessine une jauge de statistique avec son indicateur de progression (si applicable) et son icône d'information. Utilise les fonctions du module `stat_bar.py`. Retourne le rectangle de l'icône et la hauteur utilisée
- `_draw_stats_in_columns(surface: pygame.Surface, x: int, y: int) -> None` : Dessine les statistiques organisées en 2 colonnes, répartissant équitablement les statistiques entre les colonnes
- `_draw_info_icon(surface: pygame.Surface, x: int, y: int, stat_identifier: str, ...) -> pygame.Rect` : Dessine l'icône "I" dans un cercle et retourne son rectangle pour la détection de survol
- `_draw_animated_sprite(surface: pygame.Surface, panel_x: int, panel_y: int) -> None` : Dessine le sprite du joueur animé en utilisant `sprite_manager.get_current_sprite()`

### Calcul des valeurs maximales

Pour chaque statistique, la valeur maximale correspond à la valeur au niveau 5 (niveau maximum). Cette valeur est récupérée depuis `PlayerStatsConfig` via `get_stat_value(stat_identifier, 5)`.

Le pourcentage de remplissage est calculé comme suit :
```python
fill_percentage = (current_value / max_value) * 100.0
```

### Détection de progression des statistiques

Pour déterminer si une statistique a progressé par rapport au niveau précédent :

1. **Récupérer le niveau actuel** : `current_level = player.level_manager.level`
2. **Vérifier si le niveau est > 1** : Si `current_level <= 1`, retourner `False` (pas de niveau précédent)
3. **Récupérer la valeur actuelle** : `current_value = player.level_manager.get_stat_value(stat_identifier)`
4. **Récupérer la valeur du niveau précédent** : `previous_value = player.level_manager.stats_config.get_stat_value(stat_identifier, current_level - 1)`
5. **Comparer les valeurs** : Si `current_value > previous_value`, retourner `True`, sinon `False`

**Gestion des erreurs** :
- Si la statistique n'existe pas (`KeyError`), retourner `False` (pas d'indicateur)
- Si le niveau précédent n'a pas de valeur définie, retourner `False` (pas d'indicateur)
- Si `stats_config` n'est pas disponible, retourner `False` (pas d'indicateur)

**Note** : Cette fonctionnalité est implémentée dans le module `stat_bar.py` via la fonction `has_stat_progressed(player, stat_identifier)`.

**Exemple d'implémentation** (dans `stat_bar.py`) :
```python
def has_stat_progressed(player: Player, stat_identifier: str) -> bool:
    """Vérifie si une statistique a progressé par rapport au niveau précédent."""
    current_level = player.level_manager.level
    if current_level <= 1:
        return False  # Pas de niveau précédent
    
    if not player.level_manager.stats_config:
        return False  # Pas de configuration de stats
    
    try:
        current_value = player.level_manager.get_stat_value(stat_identifier)
        previous_value = player.level_manager.stats_config.get_stat_value(
            stat_identifier, current_level - 1
        )
        return current_value > previous_value
    except (KeyError, ValueError):
        return False  # Statistique inexistante ou niveau invalide
```

### Chargement des polices pixel art

L'interface utilise des polices pixel art spécifiques pour chaque type d'élément :

**Polices utilisées** :
1. **VT323** (Google Fonts) : Pour tous les éléments de l'interface (nom du personnage, niveau, texte de présentation, statistiques, tooltips, icônes)
   - Look rétro CRT, très lisible pour titres/niveaux, texte de présentation, labels et petites tailles
   - Fichier attendu : `VT323-Regular.ttf` ou `VT323.ttf`

2. **Silkscreen** : Pour les titres de section (Origines, Classe & Rôle, Traits de caractère)
   - Affichages courts, boutons et onglets
   - Fichier attendu : `Silkscreen-Regular.ttf` ou `Silkscreen.ttf`

**Système de chargement** :
- Les polices sont recherchées dans l'ordre suivant :
  1. Répertoire spécifié via le paramètre `fonts_dir` (défaut : `fonts/` à la racine du projet)
  2. Répertoire système standard (selon l'OS)
  3. Police système par défaut (fallback)
- Si une police n'est pas trouvée, le système utilise une police système par défaut (ex: Arial, sans-serif) comme fallback
- Les polices sont mises en cache pour éviter de les recharger à chaque frame
- Les polices sont recréées uniquement si la taille change (adaptation à la résolution)

**Note** : Les fichiers de polices doivent être téléchargés depuis Google Fonts ou d'autres sources et placés dans le répertoire `fonts/` du projet.

### Extraction et animation du sprite du joueur

Les sprites du joueur sont extraits depuis le sprite sheet `walk.png` du niveau actuel :

1. Récupérer le sprite sheet via `player.level_manager.get_asset_path("walk.png")`
2. Charger le sprite sheet avec `pygame.image.load()`
3. Extraire les 4 sprites à la position (row=0,1,2,3, col=0) selon les dimensions du sprite (64x64 par défaut)
   - Ligne 0 (index 0) : Personnage vu du haut
   - Ligne 1 (index 1) : Personnage vu du bas
   - Ligne 2 (index 2) : Personnage vu de gauche
   - Ligne 3 (index 3) : Personnage vu de droite
4. Redimensionner chaque sprite à 400% (4.0x) de sa taille originale
5. Mettre en cache les sprites pour éviter de les recharger à chaque frame
6. Recharger les sprites uniquement si le niveau du joueur change

**Animation de rotation** :
- L'animation utilise un timer (`rotation_timer`) qui s'incrémente avec le delta time
- Chaque sprite est affiché pendant `rotation_speed` secondes (défaut: 0.5s)
- Après `rotation_speed` secondes, on passe au sprite suivant (frame suivante)
- Quand on atteint le dernier sprite (frame 3), on revient au premier (frame 0) pour créer une boucle
- L'animation continue même si le jeu est en pause (le delta time est toujours calculé dans la boucle de rendu)

**Note** : Cette fonctionnalité est gérée par la classe `AnimatedSpriteManager` dans le module `animated_sprite.py`. La classe `PlayerStatsDisplay` utilise une instance de `AnimatedSpriteManager` via la propriété `sprite_manager`.

**Positionnement** :
- **Section titre (panneau rectangulaire supérieur)** : Le nom du personnage est affiché dans le panneau rectangulaire supérieur de l'image de fond, **centré horizontalement et verticalement** dans ce panneau. Les coordonnées du panneau sont calculées depuis les rectangles détectés ou définis manuellement.
- **Section supérieure (panneau central)** : Le sprite est positionné dans la colonne gauche du panneau central principal, dans un bloc dédié, **centré verticalement** dans ce bloc (aligné au centre vertical de la section de présentation à droite) sans cadre/encart visible. La section de présentation occupe la colonne droite du panneau central.
- **Section inférieure (panneau central)** : Les statistiques sont organisées en **2 colonnes égales** dans le panneau central principal, chaque colonne occupant environ 50% de la largeur disponible (moins les marges et l'espacement entre colonnes). Les statistiques sont réparties équitablement entre les deux colonnes (ex: si 4 statistiques, 2 par colonne). L'espacement vertical entre chaque statistique dans une colonne est de 40 pixels minimum (ajusté selon le facteur d'échelle).
- **Bloc sprite** : Le bloc du sprite a une largeur fixe de 267 pixels (ajustée selon le facteur d'échelle) et une hauteur adaptée au sprite redimensionné, avec un padding interne de 13 pixels (ajusté selon le facteur d'échelle) pour le calcul du centrage. Le sprite est centré horizontalement et **verticalement** dans ce bloc **sans cadre/encart visible**.
- **Statistiques** : Les barres de statistiques utilisent toute la largeur disponible dans leur colonne (moins les marges latérales), avec les noms, valeurs et icônes alignés horizontalement. Les statistiques sont réparties de manière équilibrée entre les deux colonnes (statistiques paires : répartition égale, statistiques impaires : une colonne en contient une de plus)

### Gestion de l'état bloquant

Lorsque l'interface est affichée (`is_visible = True`) :
- Le jeu est en pause : les mises à jour du gameplay (mouvement, animations, collisions) sont suspendues
- Seuls les événements de clavier et de souris pour gérer l'interface sont traités
- La touche `S` permet de masquer l'interface et reprendre le jeu
- Les événements de souris (`MOUSEMOTION`) sont traités pour détecter le survol des icônes d'information
- L'interface est rendue au-dessus de tous les autres éléments (dernière chose dessinée dans la boucle de rendu)
- Le tooltip est affiché au-dessus de tous les autres éléments de l'interface (dernière chose dessinée)

## Intégration

### Classe `Player`

Aucune modification nécessaire de la classe `Player`. L'interface utilise les propriétés existantes :
- `player.level_manager.stats_config` : Pour accéder aux statistiques
- `player.level_manager.get_stat_value()` : Pour récupérer les valeurs actuelles
- `player.level_manager.get_stat_tooltip()` : Pour récupérer le tooltip correspondant au niveau actuel
- `player.level_manager.level` : Pour connaître le niveau actuel
- `player.level_manager.get_asset_path()` : Pour obtenir le chemin du sprite sheet

### Boucle principale (`main.py`)

Dans la boucle principale du jeu :

1. **Gestion des événements** :
   ```python
   if event.type == pygame.KEYDOWN:
       if event.key == pygame.K_s:
           stats_display.toggle()
   elif event.type == pygame.MOUSEMOTION:
       # Transmettre les événements de souris à l'interface des statistiques
       # pour gérer le survol des icônes d'information
       if stats_display.is_visible:
           # IMPORTANT : Convertir les coordonnées de la souris de la résolution d'affichage
           # vers la résolution interne (1280x720) car l'interface est rendue en résolution interne
           # Les événements de souris sont en coordonnées d'écran réel, mais le panneau est rendu
           # en 1280x720 avec un upscale et un letterboxing si nécessaire
           from moteur_jeu_presentation.rendering.config import convert_mouse_to_internal
           try:
               display_size = pygame.display.get_window_size()
           except (pygame.error, AttributeError):
               display_size = screen.get_size()
           if display_size[0] <= 0 or display_size[1] <= 0:
               display_size = screen.get_size()
           internal_mouse_pos = convert_mouse_to_internal(event.pos, display_size)
           # Créer un nouvel événement avec les coordonnées converties
           converted_event = pygame.event.Event(
               pygame.MOUSEMOTION,
               pos=internal_mouse_pos,
               rel=event.rel,
               buttons=event.buttons,
           )
           stats_display.handle_mouse_event(converted_event)
   ```

2. **Mise à jour du jeu** :
   ```python
   # Ne mettre à jour le jeu que si l'interface n'est pas affichée
   if not stats_display.is_visible:
       player.update(dt, keys)
       # ... autres mises à jour du gameplay
   ```

3. **Rendu** :
   ```python
   # Dessiner tous les éléments du jeu
   # ... (parallaxe, joueur, etc.)
   
   # Dessiner l'interface des statistiques en dernier (au-dessus de tout)
   # Note: dt est nécessaire pour l'animation de rotation
   # Le tooltip est dessiné automatiquement dans draw() si une icône est survolée
   stats_display.draw(screen, dt)
   ```

### Initialisation

```python
from moteur_jeu_presentation.ui import PlayerStatsDisplay

# Dans main.py, après la création du joueur
stats_display = PlayerStatsDisplay(
    player=player,
    screen_width=SCREEN_WIDTH,
    screen_height=SCREEN_HEIGHT,
)
```

## Structure de fichiers

```
moteur_jeu_presentation/
├── src/
│   └── moteur_jeu_presentation/
│       └── ui/
│           ├── __init__.py
│           ├── player_stats_display.py    # Classe principale PlayerStatsDisplay
│           ├── animated_sprite.py         # Module AnimatedSpriteManager
│           ├── stat_bar.py                # Fonctions utilitaires pour les barres de statistiques
│           ├── stat_tooltip.py            # Fonctions utilitaires pour les tooltips
│           ├── character_presentation.py  # Fonctions utilitaires pour la présentation du personnage
│           └── text_utils.py              # Fonctions utilitaires pour le rendu de texte
└── ...
```

## Gestion des erreurs

**Note importante sur le cache Python** : Après des modifications importantes du code (changement de valeurs par défaut, modifications de la logique d'initialisation, etc.), il est recommandé de nettoyer les caches Python pour s'assurer que les modifications sont bien prises en compte :

```bash
# Nettoyer les caches Python du projet (sauf .venv)
find src -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
find src -name "*.pyc" -delete 2>/dev/null || true
```

| Cas | Gestion | Message |
| --- | --- | --- |
| `stats_config` non disponible | Afficher un message dans l'interface ou masquer les statistiques | `"Statistiques non disponibles"` |
| Section `[presentation]` absente ou invalide dans `player_stats.toml` (clés `origins` / `class_role` / `traits` manquantes, types incorrects, listes vides, ou texte vide après normalisation) | **Erreur au chargement** — ne pas démarrer l’UI stats avec une config partielle | `ValueError` explicite (chemin fichier, clé attendue) — aligné sur `display_name` |
| Sprite sheet `walk.png` introuvable | Utiliser un sprite par défaut (rectangle coloré) ou masquer l'affichage du sprite | Logger un avertissement, continuer sans sprite |
| Image de fond `affichage_personnage.png` introuvable | Utiliser un fond de couleur unie (couleur par défaut `bg_color`) | Logger un avertissement, continuer avec fond unie |
| Panneaux (rectangulaire supérieur ou central) non détectables | Utiliser des coordonnées par défaut ou des valeurs manuelles | Logger un avertissement, utiliser des valeurs par défaut |
| Police pixel art introuvable | Utiliser une police système par défaut (fallback) | Logger un avertissement, continuer avec police système |
| Statistique inexistante | Ignorer la statistique et continuer avec les autres | Logger un avertissement |
| Niveau invalide lors de l'extraction du sprite | Utiliser le niveau 1 par défaut | Logger un avertissement |
| Champ `tooltip_level_N` non défini pour le niveau actuel d'une statistique | Afficher l'icône mais aucun tooltip au survol | Comportement normal, pas d'erreur |
| Tooltip trop large pour l'écran | Ajuster la position ou réduire la largeur | Positionner le tooltip à gauche de l'icône si nécessaire |

## Pièges courants

1. **Sprites non mis à jour après changement de niveau** : Vérifier que les sprites sont rechargés lorsque `player.level_manager.level` change. **IMPORTANT** : Lors d'un changement de niveau, l'animation de rotation doit être réinitialisée (timer remis à 0, frame actuelle remise à 0) pour éviter tout mélange de sprites entre différents niveaux. Le cache de redimensionnement doit également être invalidé pour éviter d'utiliser d'anciens sprites redimensionnés.
2. **Animation de rotation non fluide** : S'assurer que le delta time est correctement passé à `draw()` et que le timer est mis à jour à chaque frame.
3. **Sprite mal centré** : Vérifier que le calcul de position prend en compte la taille redimensionnée du sprite (400%) et que le sprite est bien centré horizontalement et **verticalement** dans son bloc dédié (sans cadre visible). Le sprite doit être aligné verticalement avec le centre de la section de présentation à droite.
4. **Statistiques non liées au gameplay** : S'assurer que la statistique "vitesse" influence réellement la vitesse de déplacement du personnage. La formule doit utiliser les valeurs comme facteur d'amélioration : `speed = base_speed * (1 + (vitesse_stat / 100))` pour que les valeurs du fichier TOML (12, 22, 38, etc.) augmentent progressivement la vitesse.
5. **Calcul incorrect du pourcentage** : S'assurer que la valeur maximale correspond bien au niveau 5, pas à une valeur arbitraire.
6. **Overlay trop opaque/transparent** : Ajuster `overlay_alpha` pour un bon équilibre entre visibilité de l'interface et du jeu en arrière-plan.
7. **Performance** : Mettre en cache les surfaces rendues (overlay, panneau, sprites redimensionnés) et ne les recréer que si nécessaire (changement de taille d'écran, changement de niveau).
8. **Gestion des événements** : S'assurer que la touche `S` n'est traitée qu'une fois par appui (événement `KEYDOWN`, pas `KEYPRESS` continu).
9. **Redimensionnement du sprite** : Utiliser `pygame.transform.scale()` ou `pygame.transform.smoothscale()` pour redimensionner les sprites. Préférer `smoothscale()` pour une meilleure qualité visuelle.
10. **Animation de rotation qui ne démarre pas** : S'assurer que le timer de rotation est réinitialisé lors de l'affichage de l'interface.
11. **Détection de survol incorrecte** : S'assurer que les rectangles des icônes sont correctement calculés et stockés pour chaque statistique. Utiliser des coordonnées relatives au panneau puis convertir en coordonnées écran.
12. **Tooltip qui sort de l'écran** : Implémenter une logique de positionnement intelligent qui vérifie les bords de l'écran et ajuste la position du tooltip (au-dessus, en dessous, à gauche, à droite de l'icône).
13. **Tooltip non mis à jour après changement de niveau** : S'assurer que le tooltip est recréé avec le bon texte correspondant au nouveau niveau lorsque le niveau du personnage change. Le tooltip doit utiliser `player.level_manager.level` pour récupérer le niveau actuel et appeler `stat_definition.get_tooltip(level)` pour obtenir le texte approprié.
14. **Performance avec plusieurs tooltips** : Mettre en cache les surfaces de tooltip et ne les recréer que si nécessaire (changement de statistique survolée, changement de taille d'écran).
15. **Rendu direct en 1280×720** : L'interface est toujours rendue directement en 1280×720 sans facteur d'échelle. Le facteur d'échelle est toujours 1.0 (pas de scaling). Toutes les valeurs sont utilisées directement en 1280×720. Les assets graphiques (images de fond, sprites) sont redimensionnés si nécessaire pour s'adapter à cette résolution, mais l'interface elle-même n'utilise pas de facteur d'échelle.
16. **Chevauchement de texte** : L'interface est toujours rendue en 1280×720, donc les espacements sont fixes. S'assurer que tous les espacements (entre le nom et la jauge, entre la jauge et la valeur, entre la valeur et l'icône) sont suffisants pour éviter les chevauchements.
17. **Layout plein écran** : Le panneau prend l'ensemble de l'écran avec un padding réduit (30px pour la résolution 1280×720) pour maximiser l'espace disponible et permettre d'afficher tout le contenu sans débordement. Les dimensions du panneau sont toujours 1220×660 (1280 - 60 padding, 720 - 60 padding). L'espacement entre les statistiques est de 40 pixels (fixe en 1280×720) pour éviter les chevauchements tout en permettant d'afficher plus de statistiques. **Taille des jauges** : Les barres de statistiques utilisent la largeur disponible dans leur colonne moins un padding supplémentaire de 20px, puis sont réduites de 1/3 (multipliées par 2/3) pour garantir qu'elles rentrent bien dans le panneau central de l'image. **Espacement entre colonnes** : Un espacement fixe de 10 pixels (en 1280×720) sépare les deux colonnes de statistiques. **Word wrapping** : Le texte de présentation utilise un système de retour à la ligne automatique pour diviser les lignes trop longues en plusieurs lignes, garantissant que tout le texte reste visible. **Vérification de débordement** : Le système vérifie que le contenu (présentation, sprite, statistiques) ne dépasse pas du panneau et ajuste automatiquement les positions si nécessaire. L'espace réservé pour les statistiques est de 180px pour laisser plus d'espace à la présentation.
18. **Section de présentation qui dépasse** : La section de présentation du personnage doit être correctement dimensionnée pour ne pas dépasser les limites du panneau. S'assurer que la hauteur totale de la présentation est calculée dynamiquement et que le contenu est correctement positionné à droite du sprite. Le système utilise un **word wrapping automatique** pour diviser les lignes trop longues en plusieurs lignes, garantissant que tout le texte reste visible. Le système utilise également un clipping automatique pour s'assurer que la présentation ne dépasse pas de l'espace réservé (espace total moins l'espace réservé pour les statistiques). Si le contenu est trop long après wrapping, il sera automatiquement coupé par le clipping.
19. **Hiérarchie visuelle de la présentation** : S'assurer que la hiérarchie visuelle est respectée (`display_name` en grand et doré dans le panneau titre, titres de section de la colonne présentation en couleur secondaire, texte en couleur standard). Les espacements entre les sections sont fixes (12px entre sections, 17px de padding).
20. **Bloc sprite trop petit ou trop grand** : Le bloc du sprite a une largeur fixe de 267 pixels (en 1280×720) pour accueillir le sprite agrandi à 400%. Le sprite doit être bien centré horizontalement et verticalement dans ce bloc sans cadre/encart visible.
21. **Lisibilité des statistiques** : S'assurer que les polices des statistiques restent lisibles tout en évitant les chevauchements. La taille est de 28 pixels (fixe en 1280×720). Les barres ont une hauteur de 19 pixels (fixe en 1280×720) et utilisent toute la largeur disponible. **IMPORTANT** : Toutes les valeurs sont utilisées directement en 1280×720 sans scaling.
24. **Centrage du titre (`display_name`)** : Vérifier que le titre avec `display_name` est centré horizontalement sur toute la largeur du panneau, en haut de l'interface, et non seulement dans la colonne de présentation narrative.
25. **Centrage vertical du sprite** : Vérifier que le sprite est centré verticalement dans son bloc, aligné avec le centre vertical de la section de présentation à droite.
26. **Organisation en 2 colonnes des statistiques** : Vérifier que les statistiques sont correctement réparties en 2 colonnes égales, avec un espacement approprié entre les colonnes. Les statistiques doivent être équitablement distribuées (ex: 4 stats = 2 par colonne, 3 stats = 2 dans une colonne et 1 dans l'autre).
27. **Taille des icônes d'information** : Vérifier que les icônes "I" sont de 32 pixels (fixe en 1280×720) et bien visibles.
28. **Taille de police des tooltips** : Vérifier que la police des tooltips est de 21 pixels (fixe en 1280×720) pour améliorer la lisibilité des descriptions détaillées.
29. **Affichage du niveau dans le titre** : Vérifier que le niveau est affiché entre parenthèses à côté de `display_name` dans le titre, sur la même ligne, et qu'il se met à jour automatiquement lorsque le niveau change.
30. **Taille de police de la présentation** : Vérifier que la taille de police du texte de présentation est de 18 pixels (fixe en 1280×720) pour améliorer la lisibilité.
22. **Contraste des couleurs** : S'assurer que les couleurs de texte ont un contraste suffisant avec le fond. Utiliser des couleurs plus claires (ex: (240, 240, 240) au lieu de (220, 220, 220)) pour améliorer la lisibilité. Les barres de statistiques doivent avoir un fond plus clair (ex: (80, 80, 80) au lieu de (60, 60, 60)) et des bordures plus visibles (ex: (180, 180, 180) avec épaisseur de 2 pixels).
23. **Espacements minimaux** : Garantir des espacements minimaux entre les éléments (ex: 8 pixels entre le nom et la jauge, 8 pixels entre la jauge et la valeur en 1280×720) pour améliorer la lisibilité. Les espacements sont fixes en 1280×720.
31. **Image de fond non chargée** : Si l'image `affichage_personnage.png` n'est pas trouvée, utiliser un fond de couleur unie comme fallback. Logger un avertissement mais continuer le fonctionnement normal de l'interface.
32. **Polices pixel art manquantes** : Si une police pixel art n'est pas trouvée, utiliser une police système par défaut comme fallback. Logger un avertissement mais continuer le fonctionnement normal. S'assurer que les polices sont bien téléchargées et placées dans le répertoire `fonts/`.
33. **Redimensionnement de l'image de fond** : L'image de fond est redimensionnée pour remplir le panneau en utilisant le ratio maximum (au lieu du minimum), ce qui agrandit l'image et permet d'avoir un panneau central plus grand pour contenir tout le texte. Les proportions sont conservées. L'image est centrée dans le panneau si elle dépasse légèrement. L'image doit être recréée uniquement si les dimensions du panneau changent.
34. **Performance avec l'image de fond** : Mettre en cache l'image de fond redimensionnée pour éviter de la recalculer à chaque frame. Ne recréer l'image que si les dimensions du panneau changent.
35. **Détection des panneaux** : S'assurer que les rectangles des panneaux (rectangulaire supérieur et central principal) sont correctement détectés ou définis. Les coordonnées doivent être mises à l'échelle proportionnellement lorsque l'image est redimensionnée.
36. **Positionnement du nom dans le panneau rectangulaire** : Vérifier que le nom et le niveau sont correctement centrés horizontalement et verticalement dans le panneau rectangulaire supérieur, et non dans le panneau central.
37. **Positionnement du contenu dans le panneau central** : Vérifier que le sprite, la présentation et les statistiques sont correctement positionnés dans le panneau central principal, et non dans le panneau rectangulaire supérieur.
38. **Cache Python après modifications** : Après des modifications importantes du code (changement de valeurs par défaut, modifications de la logique d'initialisation, etc.), nettoyer les caches Python pour s'assurer que les modifications sont bien prises en compte. Les fichiers `.pyc` et les répertoires `__pycache__` peuvent contenir d'anciennes versions compilées du code qui empêchent les modifications de prendre effet.
39. **Indicateur de progression non affiché** : Vérifier que la méthode `_has_stat_progressed()` est correctement implémentée et que la comparaison des valeurs est effectuée correctement. S'assurer que le niveau actuel est bien récupéré et que la valeur du niveau précédent est correctement calculée.
40. **Indicateur affiché incorrectement** : Vérifier que l'indicateur ne s'affiche pas au niveau 1 et qu'il ne s'affiche que si la valeur actuelle est strictement supérieure à la valeur du niveau précédent (pas égal).
41. **Positionnement de l'indicateur** : S'assurer que l'indicateur "^" est correctement positionné à côté du nom de la statistique avec un espacement approprié (5-8 pixels), et que le nom et l'indicateur sont alignés verticalement.
42. **Couleur de l'indicateur** : Vérifier que l'indicateur est bien affiché en jaune (ex: `(255, 215, 0)`) pour un bon contraste et une visibilité claire.

## Tests

### Tests unitaires

- `test_stats_display_toggle()` : Vérifier que `toggle()` change correctement l'état `is_visible`
- `test_stats_display_show_hide()` : Vérifier que `show()` et `hide()` modifient correctement l'état
- `test_bar_color_calculation()` : Vérifier que `_get_bar_color()` retourne les bonnes couleurs selon le pourcentage
- `test_sprite_extraction()` : Vérifier que les 4 sprites sont correctement extraits depuis le sprite sheet
- `test_sprite_scaling()` : Vérifier que les sprites sont correctement redimensionnés à 400%
- `test_rotation_animation()` : Vérifier que l'animation de rotation fonctionne correctement avec le timing fixe
- `test_max_value_calculation()` : Vérifier que la valeur maximale correspond bien au niveau 5
- `test_info_icon_drawing()` : Vérifier que l'icône "I" est correctement dessinée à la fin de chaque jauge
- `test_icon_hover_detection()` : Vérifier que la détection de survol des icônes fonctionne correctement
- `test_tooltip_creation()` : Vérifier que le tooltip est créé avec le bon texte depuis le champ `tooltip_level_N` correspondant au niveau actuel de la statistique
- `test_tooltip_level_matching()` : Vérifier que le tooltip affiché correspond bien au niveau actuel du personnage (ex: niveau 3 → tooltip_level_3)
- `test_tooltip_positioning()` : Vérifier que le tooltip est positionné correctement et ne sort pas de l'écran
- `test_tooltip_missing_field()` : Vérifier que l'icône est affichée même si le champ `tooltip_level_N` n'est pas défini pour le niveau actuel, mais qu'aucun tooltip ne s'affiche
- `test_tooltip_level_change()` : Vérifier que le tooltip se met à jour correctement lorsque le niveau du personnage change
- `test_progression_indicator_display()` : Vérifier que l'indicateur de progression "^" s'affiche correctement à côté du nom de la statistique qui a progressé
- `test_progression_indicator_level_1()` : Vérifier que l'indicateur ne s'affiche pas au niveau 1 (pas de niveau précédent)
- `test_progression_indicator_no_progress()` : Vérifier que l'indicateur ne s'affiche pas si la statistique n'a pas progressé (valeur égale ou inférieure)
- `test_progression_indicator_level_change()` : Vérifier que l'indicateur se met à jour correctement lors d'un changement de niveau
- `test_progression_indicator_multiple_stats()` : Vérifier que l'indicateur s'affiche uniquement pour les statistiques qui ont progressé, pas pour toutes
- `test_character_presentation_drawing()` : Vérifier que la section de présentation du personnage est correctement dessinée avec toutes les informations (trois listes en puces)
- `test_character_presentation_from_stats_config()` : Vérifier que les listes proviennent de `[presentation]` dans le TOML chargé
- `test_character_presentation_toml_validation_errors()` : Vérifier qu’une config sans `[presentation]`, sans clé, avec liste vide ou chaîne vide après `strip()`, lève une erreur explicite au chargement
- `test_character_presentation_customization()` : Vérifier que le paramètre `character_presentation` du constructeur permet encore d’injecter des données en test
- `test_character_presentation_word_wrapping()` : Vérifier que le texte de présentation utilise le word wrapping pour diviser les lignes trop longues en plusieurs lignes
- `test_character_name_with_level()` : Vérifier que le texte du titre correspond à `stats_config.display_name` avec le niveau entre parenthèses
- `test_level_update_in_title()` : Vérifier que le niveau dans le titre se met à jour automatiquement lors d'un changement de niveau
- `test_background_image_loading()` : Vérifier que l'image de fond est correctement chargée depuis le chemin spécifié
- `test_background_image_scaling()` : Vérifier que l'image de fond est correctement redimensionnée pour remplir le panneau (ratio maximum) et que le panneau central est agrandi
- `test_background_image_fallback()` : Vérifier que le panneau utilise un fond de couleur unie si l'image de fond n'est pas trouvée
- `test_panel_rect_detection()` : Vérifier que les rectangles des panneaux (rectangulaire supérieur et central principal) sont correctement détectés ou définis
- `test_panel_rect_scaling()` : Vérifier que les rectangles des panneaux sont correctement mis à l'échelle lorsque l'image est redimensionnée
- `test_character_name_in_title_panel()` : Vérifier que `display_name` et le niveau sont correctement affichés dans le panneau rectangulaire supérieur
- `test_content_in_main_panel()` : Vérifier que le sprite, la présentation et les statistiques sont correctement affichés dans le panneau central principal
- `test_font_loading()` : Vérifier que les polices pixel art sont correctement chargées depuis le répertoire des polices
- `test_font_fallback()` : Vérifier que le système utilise une police système par défaut si une police pixel art n'est pas trouvée
- `test_font_caching()` : Vérifier que les polices sont mises en cache et ne sont pas rechargées à chaque frame

### Tests d'intégration

1. Lancer le jeu et appuyer sur `S` → l'interface s'affiche
2. Vérifier que le jeu est en pause lorsque l'interface est affichée (le personnage ne bouge pas)
3. Réappuyer sur `S` → l'interface se masque et le jeu reprend
4. Changer de niveau (touches `P`/`O`) → vérifier que les statistiques se mettent à jour
5. Vérifier que les sprites du joueur correspondent au niveau actuel
6. Vérifier que les couleurs des jauges changent selon le remplissage (rouge/orange/vert)
7. Vérifier que le sprite du joueur tourne sur lui-même avec un timing régulier
8. Vérifier que le sprite est affiché à 400% de sa taille originale
9. Vérifier que le sprite est positionné dans un bloc dédié en haut à gauche et centré horizontalement et verticalement dans ce bloc sans cadre/encart visible
10. Vérifier que les statistiques occupent toute la largeur disponible avec des polices de 28 pixels par défaut (ajustées selon le facteur d'échelle)
11. Vérifier que l'icône "I" est affichée à la fin de chaque jauge de statistique
12. Survoler une icône "I" avec la souris → le tooltip s'affiche avec le texte explicatif
13. Déplacer la souris hors de l'icône → le tooltip disparaît
14. Vérifier que le tooltip est correctement positionné et ne sort pas de l'écran
15. Vérifier que le tooltip gère correctement les textes multi-lignes (sauts de ligne `\n`)
16. Vérifier que si une statistique n'a pas de champ `tooltip_level_N` pour le niveau actuel, l'icône est affichée mais aucun tooltip n'apparaît au survol
17. Changer le niveau du personnage (touches `P`/`O`) → vérifier que le tooltip affiché change pour correspondre au nouveau niveau
18. Vérifier que chaque niveau affiche le bon tooltip (niveau 1 → tooltip_level_1, niveau 2 → tooltip_level_2, etc.)
19. Vérifier que l'indicateur de progression "^" s'affiche en jaune à côté du nom des statistiques qui ont progressé
20. Vérifier que l'indicateur ne s'affiche pas au niveau 1 (pas de niveau précédent)
21. Vérifier que l'indicateur ne s'affiche pas si la statistique n'a pas progressé (valeur égale ou inférieure au niveau précédent)
22. Changer de niveau (touches `P`/`O`) → vérifier que l'indicateur se met à jour correctement pour refléter la progression par rapport au nouveau niveau précédent
23. Vérifier que l'indicateur s'affiche uniquement pour les statistiques qui ont progressé, pas pour toutes
24. Vérifier que la section de présentation du personnage s'affiche correctement à droite du sprite
25. Vérifier que toutes les informations de présentation (origines, classe & rôle, traits) sont affichées et que le titre du panneau supérieur reprend bien `display_name` depuis la config
26. Vérifier que la section de présentation est correctement positionnée et espacée
27. Vérifier que les polices et couleurs de la présentation sont appliquées correctement
28. Vérifier que la section de présentation s'adapte correctement au facteur d'échelle
29. Vérifier que le texte de présentation utilise le word wrapping pour diviser les lignes trop longues en plusieurs lignes et que tout le texte reste visible
30. Vérifier que le bloc du sprite a une largeur fixe appropriée de 267 pixels (ajustée selon le facteur d'échelle) et que le sprite est bien centré horizontalement et verticalement dans ce bloc sans cadre/encart visible
31. Vérifier que le libellé `display_name` avec le niveau entre parenthèses est centré horizontalement en haut du panneau sur toute la largeur
32. Vérifier que le niveau est affiché entre parenthèses à côté de `display_name` et se met à jour automatiquement lors d'un changement de niveau
33. Vérifier que le sprite est centré verticalement dans son espace, aligné avec le centre de la section de présentation
34. Vérifier que les statistiques sont organisées en 2 colonnes avec une répartition équitable
35. Vérifier que les jauges de statistiques rentrent bien dans le panneau central de l'image grâce au padding supplémentaire de 20px
36. Vérifier que les icônes d'information sont de 32 pixels (fixe en 1280×720) et bien visibles
37. Vérifier que la police des statistiques est de 28 pixels (fixe en 1280×720)
38. Vérifier que la police des tooltips est de 21 pixels (fixe en 1280×720) pour améliorer la lisibilité
39. Vérifier que la police du texte de présentation est de 18 pixels (fixe en 1280×720)
40. Vérifier que les modules séparés (`animated_sprite.py`, `stat_bar.py`, `stat_tooltip.py`, `character_presentation.py`, `text_utils.py`) fonctionnent correctement et sont bien intégrés
41. Vérifier que le texte de présentation utilise le word wrapping pour diviser les lignes trop longues en plusieurs lignes et que tout le texte reste visible
42. Vérifier que l'image de fond `affichage_personnage.png` est correctement chargée et affichée dans le panneau
43. Vérifier que l'image de fond est correctement redimensionnée pour remplir le panneau (ratio maximum) et que le panneau central est agrandi pour contenir tout le texte
44. Vérifier que le panneau utilise un fond de couleur unie si l'image de fond n'est pas trouvée
45. Vérifier que les polices pixel art (VT323, Silkscreen) sont correctement chargées et utilisées
46. Vérifier que le système utilise une police système par défaut si une police pixel art n'est pas trouvée
47. Vérifier que les polices sont correctement appliquées à chaque élément (titre avec `display_name`, titres de section, texte de présentation, statistiques, tooltips)
48. Vérifier que `display_name` et le niveau sont affichés dans le panneau rectangulaire supérieur de l'image de fond
49. Vérifier que `display_name` et le niveau sont centrés horizontalement et verticalement dans le panneau rectangulaire supérieur
50. Vérifier que le sprite, la présentation et les statistiques sont affichés dans le panneau central principal de l'image de fond
51. Vérifier que les rectangles des panneaux sont correctement détectés ou définis et mis à l'échelle lors du redimensionnement

### Vérifications visuelles

- L'interface est centrée à l'écran
- L'overlay couvre tout l'écran avec la bonne transparence
- Les jauges sont correctement remplies selon les valeurs
- Les couleurs des jauges correspondent aux pourcentages (rouge < 33%, orange 34-66%, vert > 67%)
- Le sprite du joueur est correctement affiché dans un bloc dédié dans la colonne gauche, centré horizontalement et verticalement dans ce bloc sans cadre/encart visible, aligné avec le centre vertical de la section de présentation
- Le sprite du joueur est affiché à 400% de sa taille originale (agrandi pour une meilleure visibilité)
- Le sprite du joueur tourne sur lui-même avec une animation fluide et régulière
- Le texte est lisible et bien aligné, avec des polices adaptées (28 pixels par défaut pour les statistiques dans le repère 1280x720, ajustées selon le facteur d'échelle)
- Les barres de statistiques sont suffisamment larges et visibles (19 pixels de hauteur dans le repère 1280x720, ajustées selon le facteur d'échelle)
- Les statistiques occupent toute la largeur disponible pour une meilleure lisibilité
- L'indicateur de progression "^" est visible en jaune à côté du nom des statistiques qui ont progressé
- L'indicateur de progression ne s'affiche pas au niveau 1 (pas de niveau précédent)
- L'indicateur de progression ne s'affiche pas si la statistique n'a pas progressé
- L'icône "I" est visible et bien positionnée à la fin de chaque jauge
- L'icône "I" est clairement visible (bon contraste avec le fond)
- Le tooltip s'affiche de manière fluide au survol de l'icône
- Le tooltip est lisible avec un bon contraste texte/fond
- Le tooltip est bien positionné et ne gêne pas la lecture des autres éléments
- La section de présentation du personnage est visible et bien formatée
- Le texte `display_name` avec le niveau entre parenthèses est mis en évidence (couleur dorée, taille importante) et centré horizontalement en haut du panneau
- Le niveau est affiché entre parenthèses à côté de `display_name` et se met à jour automatiquement lors d'un changement de niveau
- Les statistiques sont organisées en 2 colonnes avec une répartition équitable
- Les icônes d'information sont de 32 pixels dans le repère 1280x720 (ajustées selon le facteur d'échelle) et bien visibles
- La police des statistiques est de 28 pixels par défaut dans le repère 1280x720 (ajustée selon le facteur d'échelle)
- La police des tooltips est de 21 pixels dans le repère 1280x720 (ajustée selon le facteur d'échelle) pour améliorer la lisibilité des descriptions détaillées
- La police du texte de présentation est de 18 pixels par défaut dans le repère 1280x720 (ajustée selon le facteur d'échelle)
- Les sections (Origines, Classe & Rôle, Traits) sont clairement séparées et lisibles
- La hiérarchie visuelle est respectée (titre `display_name` > sections > texte)
- L'image de fond `affichage_personnage.png` est correctement affichée dans le panneau
- L'image de fond est correctement redimensionnée pour remplir le panneau (ratio maximum) et le panneau central est agrandi pour contenir tout le texte
- Les polices pixel art sont correctement appliquées (VT323 pour tous les éléments de texte, Silkscreen pour les titres de section)
- Le style pixel art est cohérent et améliore l'immersion dans l'univers du jeu
- `display_name` et le niveau sont correctement affichés dans le panneau rectangulaire supérieur de l'image de fond
- `display_name` et le niveau sont centrés horizontalement et verticalement dans le panneau rectangulaire supérieur
- Le sprite, la présentation et les statistiques sont correctement affichés dans le panneau central principal de l'image de fond
- La séparation visuelle entre le panneau rectangulaire supérieur (nom/niveau) et le panneau central (contenu principal) est claire et respecte la structure de l'image

## Évolutions futures

- Ajouter des animations d'apparition/disparition (fade in/out, slide)
- Permettre la navigation entre plusieurs pages de statistiques si le nombre de stats augmente
- Ajouter des effets visuels (particules, brillances) sur les jauges - **Note** : Pour les effets de particules, utiliser le moteur de particules (spécification 14)
- Afficher des informations supplémentaires (XP, progression vers le niveau suivant)
- Permettre la personnalisation des couleurs et du style via un fichier de configuration
- Ajouter des sons lors de l'ouverture/fermeture de l'interface
- Ajouter des animations d'apparition pour la section de présentation
- Permettre l'affichage d'une image/portrait du personnage dans la section de présentation

---

**Statut** : ✅ Implémenté

