# 19 - Gestion de l'affichage du curseur

✅ **Implémenté**

## Contexte

Le jeu utilise le curseur système par défaut. Pour renforcer l’identité visuelle et la cohérence avec l’univers du jeu, le pointeur de la souris doit être remplacé par une image personnalisée. L’implémentation s’appuie sur l’API native de Pygame (Pygame 2) pour le curseur personnalisé, ce qui garantit un positionnement correct du curseur (y compris en mode plein écran, letterboxing et accélération Metal) sans logique de dessin manuelle.

## Objectifs

- Remplacer le curseur système par une image personnalisée chargée depuis le projet.
- Utiliser exclusivement l’API Pygame : `pygame.mouse.set_cursor()` et `pygame.cursors.Cursor`.
- Stocker les assets du curseur dans un dossier dédié avec une taille d’image variable (non fixée par la spec).
- Définir un point de « hotspot » (point de clic) configurable pour que le curseur reste précis.
- Charger le curseur une seule fois (au démarrage ou lors du préchargement) et le réutiliser.
- Restaurer le curseur système à la sortie du jeu si nécessaire (dialogue de confirmation, etc.).

## Périmètre et dépendances

- **Pygame 2** : utilisation de `pygame.cursors.Cursor(hotspot, surface)` (curseur couleur) et `pygame.mouse.set_cursor()`.
- **Spécification 17 (Préchargement)** : le chargement de l’image du curseur peut être intégré au préchargement des éléments graphiques ou effectué après l’initialisation de la fenêtre (avant ou après l’écran d’accueil).
- **Spécifications 5 (Plein écran), 9 (Metal), 15 (Résolution)** : le curseur étant géré par le système/Pygame, aucune conversion de coordonnées ni branchement spécifique Metal/software n’est requis pour son affichage.

## Emplacement des assets

- **Dossier** : `sprite/cursor/`
- **Contenu** : un ou plusieurs fichiers image (ex. `cursor.png`) utilisables comme curseur.
- **Taille** : variable. La spécification n’impose pas de dimensions fixes ; l’image est utilisée telle quelle (éventuellement redimensionnée par configuration ou par le moteur pour rester lisible selon la résolution). Les contraintes éventuelles (taille max recommandée pour certains OS) peuvent être documentées en note d’implémentation.
- **Format** : image avec transparence recommandée (PNG avec canal alpha), chargée via `pygame.image.load(...).convert_alpha()`.

## Spécifications techniques

### API Pygame utilisée

- **Création du curseur** : `pygame.cursors.Cursor(hotspot, surface)`
  - `hotspot` : tuple `(x, y)` en pixels, point de la surface qui correspond au « point de clic ». Doit rester dans les bornes de la surface (`0 <= x < largeur`, `0 <= y < hauteur`).
  - `surface` : `pygame.Surface` (image chargée avec transparence).
- **Activation** : `pygame.mouse.set_cursor(cursor)` où `cursor` est une instance de `pygame.cursors.Cursor`.
- **Visibilité** : le curseur personnalisé respecte l’état de visibilité géré par `pygame.mouse.set_visible()`. Aucun besoin de cacher le curseur système et de dessiner une sprite à la main.

### Chargement et moment d’initialisation

- Charger l’image du curseur depuis `sprite/cursor/` (chemin relatif à la racine du projet ou résolu depuis le chemin du projet, comme pour les autres assets).
- Créer la `pygame.Surface` une seule fois (cache ou variable dédiée), puis construire `pygame.cursors.Cursor(hotspot, surface)` et appeler `pygame.mouse.set_cursor(...)` une fois après la création de la fenêtre d’affichage (`pygame.display.set_mode` ou équivalent).
- Le hotspot peut être dérivé de la taille de l’image (ex. coin supérieur gauche `(0, 0)` ou centre `(largeur // 2, hauteur // 2)`) ou lu depuis une configuration (fichier ou constantes).

### Comportement attendu

- Dès l’initialisation du curseur personnalisé, le pointeur affiché est l’image fournie, avec le point de clic au hotspot.
- Aucun dessin manuel du curseur dans la boucle de rendu n’est requis.
- **Absence d'image** : s'il n'y a aucun fichier image exploitable dans `sprite/cursor/` (ou le fichier par défaut est absent), le curseur personnalisé n'est pas appliqué : le curseur système est conservé, sans erreur ni avertissement.
- En cas d'échec de chargement (fichier présent mais illisible) ou de création du curseur par Pygame, le jeu conserve le curseur système par défaut (fallback gracieux) et peut logger un avertissement.

### Restauration du curseur

- Lors d’une sortie propre du jeu (ou avant d’afficher un dialogue système hors jeu), le curseur par défaut peut être rétabli soit en créant un curseur système (`pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_ARROW)` ou `pygame.cursors.Cursor()`) puis `pygame.mouse.set_cursor(...)`, soit en laissant Pygame gérer l’état à la fermeture. La spec recommande de documenter dans l’implémentation le choix effectué (restauration explicite ou non).

## Notes d’implémentation

- **Cache** : pour rester cohérent avec les bonnes pratiques du projet (cache des ressources), la surface du curseur peut être stockée dans un cache dédié ou dans le module de préchargement s’il est décidé d’inclure le curseur dans le préchargement.
- **Hotspot** : par défaut, un hotspot en `(0, 0)` ou au centre de l’image est un choix simple ; un fichier de configuration (ex. TOML) ou des constantes dans le module de rendu/UI permettent de rendre le hotspot configurable sans changer le code métier.
- **Taille variable** : si l’image est très grande, certains systèmes ou drivers peuvent la redimensionner ou la tronquer. Une taille raisonnable (ex. 16x16 à 64x64) est en général sans problème ; au-delà, des tests par plateforme sont recommandés.
- **Préchargement (spec 17)** : si le curseur est préchargé avec les autres éléments graphiques, il doit être chargé après l’initialisation de la fenêtre (car `set_cursor` nécessite un display actif). Une option est de charger l’image pendant le préchargement et de n’appeler `set_cursor` qu’après la création de la fenêtre, au même endroit que les autres initialisations post-display.
