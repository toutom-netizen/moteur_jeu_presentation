# 16 - Écran d'accueil

## Contexte

Cette spécification définit l'implémentation d'un écran d'accueil pour le jeu. Avant de lancer le niveau de jeu, l'utilisateur doit voir un écran d'accueil en plein écran affichant l'image `image-intro.png`. Au clic sur le bouton "START" visible dans l'image, le niveau de jeu est lancé.

## Objectifs

- Afficher un écran d'accueil en plein écran avant le lancement du niveau
- Afficher l'image `sprite/interface/image-intro.png` en plein écran
- Afficher un fond de couleur RGB(244, 245, 235) / #f4f5eb derrière l'image
- Détecter le survol de la souris sur le bouton "START"
- Changer la couleur du fond en rouge lorsque la souris survole le bouton "START"
- Détecter le clic sur le bouton "START" dans l'image
- Lancer le niveau de jeu après le clic sur "START"
- **Permettre de sauter l'écran d'accueil** via un paramètre en ligne de commande (utile pour le développement et les tests)
- Maintenir la compatibilité avec le mode plein écran existant (spécification 5)
- Assurer une transition fluide entre l'écran d'accueil et le niveau

## Architecture

### État du jeu

Le jeu doit gérer deux états principaux :
1. **État d'accueil (Splash/Menu)** : Affiche l'image d'introduction et attend l'interaction utilisateur
2. **État de jeu (Gameplay)** : Le niveau de jeu normal, tel qu'implémenté actuellement

### Détection du clic sur le bouton START

L'image `image-intro.png` contient un bouton "START" visible. Pour détecter le clic, deux approches sont possibles :

1. **Approche par coordonnées fixes** : Définir une zone rectangulaire correspondant approximativement à la position du bouton "START" dans l'image
2. **Approche par détection de zone cliquable** : Utiliser les coordonnées de la souris et vérifier si elles correspondent à la zone du bouton après mise à l'échelle

**Recommandation** : Utiliser l'approche par coordonnées fixes, car elle est plus simple et plus performante. Les coordonnées seront définies en pourcentage de l'image pour s'adapter à différentes résolutions.

### Gestion de la mise à l'échelle

L'image d'introduction doit être mise à l'échelle pour remplir l'écran tout en préservant son ratio d'aspect. Le système doit :
- Charger l'image `image-intro.png`
- Calculer la mise à l'échelle nécessaire pour remplir l'écran (letterboxing si nécessaire)
- Centrer l'image sur l'écran
- Adapter les coordonnées du bouton START en fonction de la mise à l'échelle

## Spécifications techniques

### Structure des données

#### Classe `SplashScreen`

```python
class SplashScreen:
    """Gère l'affichage et l'interaction de l'écran d'accueil."""
    
    def __init__(
        self,
        image_path: Path,
        screen_width: int,
        screen_height: int,
        start_button_rect: Optional[pygame.Rect] = None,
    ) -> None:
        """
        Args:
            image_path: Chemin vers l'image d'introduction
            screen_width: Largeur de l'écran de rendu
            screen_height: Hauteur de l'écran de rendu
            start_button_rect: Rectangle définissant la zone cliquable du bouton START
                              (en coordonnées de l'image originale, optionnel)
        """
```

**Propriétés** :
- `image: pygame.Surface` : Image d'introduction chargée
- `scaled_image: pygame.Surface` : Image mise à l'échelle pour l'écran
- `image_rect: pygame.Rect` : Rectangle de positionnement de l'image sur l'écran
- `start_button_rect: pygame.Rect` : Rectangle de la zone cliquable du bouton START (en coordonnées écran)
- `is_active: bool` : Indique si l'écran d'accueil est actif
- `should_start_game: bool` : Indique si le jeu doit être lancé (après clic sur START)
- `background_color: Tuple[int, int, int]` : Couleur du fond (RGB(74, 149, 172) par défaut, rouge au survol du bouton START)
- `is_hovering_start: bool` : Indique si la souris survole le bouton START

**Méthodes principales** :
- `handle_event(event: pygame.event.Event, convert_mouse_pos: Optional[Callable] = None) -> None` : Gère les événements (clic souris, mouvement souris, touches)
- `update(dt: float) -> None` : Met à jour l'état de l'écran d'accueil (couleur du fond selon le survol)
- `draw(surface: pygame.Surface) -> None` : Dessine l'écran d'accueil (fond coloré + image)
- `_calculate_scaled_image() -> None` : Calcule la mise à l'échelle de l'image
- `_update_button_rect() -> None` : Met à jour les coordonnées du bouton START après mise à l'échelle
- `_update_background_color() -> None` : Met à jour la couleur du fond selon l'état du survol

### Chargement de l'image

L'image doit être chargée depuis `sprite/interface/image-intro.png` :

```python
from pathlib import Path
import pygame

assets_dir = Path("sprite")
image_path = assets_dir / "interface" / "image-intro.png"

if not image_path.exists():
    raise FileNotFoundError(f"Image d'introduction introuvable : {image_path}")

image = pygame.image.load(str(image_path)).convert_alpha()
```

### Mise à l'échelle de l'image

L'image doit être mise à l'échelle pour remplir l'écran tout en préservant le ratio d'aspect :

```python
def _calculate_scaled_image(self) -> None:
    """Calcule la mise à l'échelle de l'image pour remplir l'écran."""
    image_width = self.image.get_width()
    image_height = self.image.get_height()
    screen_width = self.screen_width
    screen_height = self.screen_height
    
    # Calculer les ratios de mise à l'échelle
    scale_x = screen_width / image_width
    scale_y = screen_height / image_height
    
    # Utiliser le ratio le plus grand pour remplir l'écran (crop si nécessaire)
    # ou le plus petit pour fit l'écran (letterboxing si nécessaire)
    # Pour un écran d'accueil, on préfère généralement remplir l'écran
    scale = max(scale_x, scale_y)
    
    new_width = int(image_width * scale)
    new_height = int(image_height * scale)
    
    self.scaled_image = pygame.transform.smoothscale(self.image, (new_width, new_height))
    
    # Centrer l'image
    x = (screen_width - new_width) // 2
    y = (screen_height - new_height) // 2
    self.image_rect = pygame.Rect(x, y, new_width, new_height)
```

**Note** : Pour un écran d'accueil, on peut choisir entre :
- **Remplir l'écran** (`max(scale_x, scale_y)`) : L'image remplit tout l'écran, mais peut être rognée
- **S'adapter à l'écran** (`min(scale_x, scale_y)`) : L'image entière est visible, mais peut avoir des barres noires (letterboxing)

La spécification recommande de **remplir l'écran** pour une meilleure immersion.

### Détection du clic sur le bouton START

Le bouton "START" est visible dans l'image. Pour détecter le clic, on définit une zone rectangulaire :

```python
# Coordonnées du bouton START dans l'image originale (à ajuster selon l'image réelle)
# Ces coordonnées sont en pourcentage de l'image pour faciliter l'ajustement
START_BUTTON_X_PERCENT = 0.35  # 35% depuis la gauche
START_BUTTON_Y_PERCENT = 0.75  # 75% depuis le haut
START_BUTTON_WIDTH_PERCENT = 0.30  # 30% de la largeur de l'image
START_BUTTON_HEIGHT_PERCENT = 0.10  # 10% de la hauteur de l'image

def _update_button_rect(self) -> None:
    """Met à jour les coordonnées du bouton START après mise à l'échelle."""
    image_width = self.image.get_width()
    image_height = self.image.get_height()
    
    # Calculer les coordonnées dans l'image originale
    button_x = int(image_width * START_BUTTON_X_PERCENT)
    button_y = int(image_height * START_BUTTON_Y_PERCENT)
    button_width = int(image_width * START_BUTTON_WIDTH_PERCENT)
    button_height = int(image_height * START_BUTTON_HEIGHT_PERCENT)
    
    # Appliquer la même mise à l'échelle que l'image
    scale_x = self.scaled_image.get_width() / image_width
    scale_y = self.scaled_image.get_height() / image_height
    
    # Calculer les coordonnées dans l'image mise à l'échelle
    scaled_button_x = int(button_x * scale_x)
    scaled_button_y = int(button_y * scale_y)
    scaled_button_width = int(button_width * scale_x)
    scaled_button_height = int(button_height * scale_y)
    
    # Ajouter l'offset de position de l'image sur l'écran
    self.start_button_rect = pygame.Rect(
        self.image_rect.x + scaled_button_x,
        self.image_rect.y + scaled_button_y,
        scaled_button_width,
        scaled_button_height,
    )
```

### Gestion des événements

L'écran d'accueil doit gérer :
- **Mouvement de la souris** : Détecter le survol du bouton START pour changer la couleur du fond
- **Clic souris** : Vérifier si le clic est dans la zone du bouton START
- **Touche Entrée/Espace** : Alternative au clic pour lancer le jeu
- **Touche Échap** : Afficher une boîte de confirmation avant de quitter le jeu (voir section "Boîte de confirmation de quitter")

**Important** : Les coordonnées de la souris doivent être converties depuis les coordonnées d'affichage (écran réel) vers les coordonnées internes (1280x720) car l'écran d'accueil est rendu sur la surface interne. Utiliser la fonction `convert_mouse_to_internal()` de `rendering.config` pour effectuer cette conversion.

```python
def handle_event(
    self,
    event: pygame.event.Event,
    convert_mouse_pos: Optional[Callable[[Tuple[int, int]], Tuple[int, int]]] = None,
) -> None:
    """Gère les événements de l'écran d'accueil."""
    if event.type == pygame.MOUSEMOTION:
        # Détecter le survol du bouton START
        mouse_pos = event.pos
        if convert_mouse_pos is not None:
            mouse_pos = convert_mouse_pos(mouse_pos)
        if self.start_button_rect:
            self.is_hovering_start = self.start_button_rect.collidepoint(mouse_pos)
            self._update_background_color()
    elif event.type == pygame.MOUSEBUTTONDOWN:
        if event.button == 1:  # Clic gauche
            mouse_pos = event.pos
            # Convertir les coordonnées de la souris si nécessaire (pour le mode plein écran)
            if convert_mouse_pos is not None:
                mouse_pos = convert_mouse_pos(mouse_pos)
            if self.start_button_rect and self.start_button_rect.collidepoint(mouse_pos):
                self.should_start_game = True
                self.is_active = False
    elif event.type == pygame.KEYDOWN:
        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            # Lancer le jeu avec Entrée ou Espace
            self.should_start_game = True
            self.is_active = False
        # Note: La gestion de la touche Échap est faite dans la boucle principale
        # pour afficher la boîte de confirmation
```

**Note importante** : Il ne faut **pas** convertir les coordonnées de la souris deux fois. La conversion doit être effectuée uniquement dans `handle_event()`, pas dans la boucle principale avant d'appeler `handle_event()`.

### Boîte de confirmation de quitter

Lorsque l'utilisateur appuie sur la touche Échap depuis l'écran d'accueil, une boîte de confirmation doit s'afficher au lieu de quitter directement le jeu. Cette boîte est identique à celle utilisée dans le jeu principal.

**Référence** : Pour les détails complets de l'implémentation de la boîte de confirmation (classe `QuitConfirmationDialog`), voir la spécification 5 - Mode plein écran, section "Boîte de confirmation de quitter".

La boîte de confirmation doit être gérée dans la boucle principale de l'écran d'accueil :

```python
# Variable pour gérer la boîte de confirmation de quitter
quit_confirmation_dialog = None

while splash_running and splash_screen.is_active and running:
    # ... gestion des événements ...
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            # Afficher la boîte de confirmation au lieu de quitter directement
            quit_confirmation_dialog = QuitConfirmationDialog(render_width, render_height)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # Afficher la boîte de confirmation au lieu de quitter directement
                if quit_confirmation_dialog is None:
                    quit_confirmation_dialog = QuitConfirmationDialog(render_width, render_height)
            else:
                splash_screen.handle_event(
                    event,
                    convert_mouse_pos=lambda pos: convert_mouse_to_internal(
                        pos, display_size
                    ),
                )
        else:
            # Passer l'événement à l'écran d'accueil
            splash_screen.handle_event(
                event,
                convert_mouse_pos=lambda pos: convert_mouse_to_internal(
                    pos, display_size
                ),
            )
    
    # Gérer les événements de la boîte de confirmation si elle est active
    if quit_confirmation_dialog is not None:
        for event in pygame.event.get():
            quit_confirmation_dialog.handle_event(
                event,
                convert_mouse_pos=lambda pos: convert_mouse_to_internal(
                    pos, display_size
                ),
            )
        if quit_confirmation_dialog.should_quit:
            splash_running = False
            running = False
        elif quit_confirmation_dialog.is_dismissed:
            quit_confirmation_dialog = None
    
    # ... mise à jour et rendu ...
    
    # Dessiner la boîte de confirmation par-dessus l'écran d'accueil si elle est active
    if quit_confirmation_dialog is not None:
        quit_confirmation_dialog.draw(internal_surface)
```

**Comportement** :
- La boîte de confirmation s'affiche au-dessus de l'écran d'accueil avec un fond assombri
- Le message "Voulez-vous vraiment quitter le jeu ?" est affiché
- **Dimensions adaptatives** : La taille de la boîte est calculée dynamiquement en fonction de la taille du texte pour garantir que le message est entièrement visible (voir spécification 5 pour les détails)
- Deux boutons cliquables sont disponibles : "Oui" (vert) et "Non" (rouge)
- Les boutons changent de couleur au survol de la souris
- Clic sur "Oui" : le jeu se ferme
- Clic sur "Non" : la boîte se ferme et l'écran d'accueil continue
- Touche Échap : ferme la boîte sans quitter (comme "Non")
- Touche Entrée : confirme la sortie (comme "Oui")

### Gestion du fond coloré

L'écran d'accueil doit afficher un fond de couleur qui change selon l'état du survol :
- **Couleur par défaut** : RGB `(74, 149, 172)` / Hexadécimal `#4a95ac` lorsque la souris n'est pas sur le bouton START
- **Couleur au survol** : Rouge uni `(255, 0, 0)` lorsque la souris survole le bouton START

```python
# Constantes de couleur pour le fond
BACKGROUND_COLOR_DEFAULT = (74, 149, 172)  # RGB(74, 149, 172) / #4a95ac
BACKGROUND_COLOR_HOVER = (255, 0, 0)       # Rouge

def _update_background_color(self) -> None:
    """Met à jour la couleur du fond selon l'état du survol."""
    if self.is_hovering_start:
        self.background_color = BACKGROUND_COLOR_HOVER
    else:
        self.background_color = BACKGROUND_COLOR_DEFAULT
```

### Rendu

L'écran d'accueil doit dessiner le fond coloré puis l'image mise à l'échelle par-dessus :

```python
def draw(self, surface: pygame.Surface) -> None:
    """Dessine l'écran d'accueil."""
    # Remplir l'écran avec la couleur de fond (RGB(74, 149, 172) par défaut, rouge au survol)
    surface.fill(self.background_color)
    
    # Dessiner l'image mise à l'échelle par-dessus le fond
    if self.scaled_image and self.image_rect:
        surface.blit(self.scaled_image, self.image_rect)
    
    # Optionnel : Dessiner un rectangle de debug pour visualiser la zone du bouton START
    # (à retirer en production ou activer avec un flag de debug)
    if self.debug and self.start_button_rect:
        pygame.draw.rect(surface, (255, 0, 0), self.start_button_rect, 2)
```

**Ordre de rendu** :
1. Fond coloré (RGB(74, 149, 172) ou rouge selon le survol)
2. Image d'introduction par-dessus le fond
3. Rectangle de debug (si activé)

## Implémentation

### Structure de fichiers

```
src/moteur_jeu_presentation/
├── ui/
│   ├── __init__.py
│   ├── splash_screen.py         # Classe SplashScreen
│   └── quit_confirmation.py      # Classe QuitConfirmationDialog (partagée avec le jeu principal)
├── main.py                       # Modification pour intégrer l'écran d'accueil et la boîte de confirmation
```

### Modifications dans `main.py`

La fonction `main()` doit être modifiée pour :
1. Ajouter un argument en ligne de commande pour sauter l'écran d'accueil
2. Créer et afficher l'écran d'accueil au démarrage (sauf si l'argument est activé)
3. Attendre que l'utilisateur clique sur START (sauf si l'écran d'accueil est désactivé)
4. Lancer le niveau après le clic ou directement si l'écran d'accueil est désactivé

#### Ajout de l'argument en ligne de commande

```python
def parse_arguments() -> argparse.Namespace:
    """Parse les arguments de la ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Présentation - Jeu de plateforme",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    # ... autres arguments existants ...
    
    parser.add_argument(
        "--skip-splash",
        action="store_true",
        dest="skip_splash",
        help="Passe l'écran d'accueil et lance directement le niveau (utile pour le développement)",
    )
    
    return parser.parse_args()
```

#### Intégration dans la fonction `main()`

```python
from moteur_jeu_presentation.ui import SplashScreen, QuitConfirmationDialog

def main() -> None:
    """Point d'entrée principal du jeu."""
    # Parser les arguments de la ligne de commande
    args = parse_arguments()
    
    # ... initialisation pygame et fenêtre ...
    
    # Créer et afficher l'écran d'accueil (sauf si --skip-splash est activé)
    if not args.skip_splash:
        # Créer l'écran d'accueil
        assets_dir = Path("sprite")
        image_path = assets_dir / "interface" / "image-intro.png"
        splash_screen = SplashScreen(
            image_path=image_path,
            screen_width=render_width,
            screen_height=render_height,
            debug=False,
        )
        
        # Boucle de l'écran d'accueil
        splash_running = True
        running = True  # Initialiser running pour la boucle d'accueil
        quit_confirmation_dialog = None  # Variable pour gérer la boîte de confirmation
        
        while splash_running and splash_screen.is_active and running:
            dt = clock.tick(FPS) / 1000.0
            
            # Limiter le delta time pour éviter des problèmes lors de changements de workspace
            if dt > 0.1:
                dt = 0.1  # Limiter à 100ms maximum (10 FPS minimum)
            
            # Gérer les événements
            try:
                display_size = pygame.display.get_window_size()
            except (pygame.error, AttributeError):
                display_size = screen.get_size()
            
            for event in pygame.event.get():
                # Si la boîte de confirmation est active, lui passer tous les événements
                if quit_confirmation_dialog is not None:
                    quit_confirmation_dialog.handle_event(
                        event,
                        convert_mouse_pos=lambda pos: convert_mouse_to_internal(
                            pos, display_size
                        ),
                    )
                    # Vérifier si la boîte doit être fermée
                    if quit_confirmation_dialog.should_quit:
                        splash_running = False
                        running = False
                    elif quit_confirmation_dialog.is_dismissed:
                        quit_confirmation_dialog = None
                else:
                    # Boîte non active, gérer les événements normalement
                    if event.type == pygame.QUIT:
                        # Afficher la boîte de confirmation au lieu de quitter directement
                        quit_confirmation_dialog = QuitConfirmationDialog(render_width, render_height)
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            # Afficher la boîte de confirmation au lieu de quitter directement
                            quit_confirmation_dialog = QuitConfirmationDialog(render_width, render_height)
                        else:
                            splash_screen.handle_event(
                                event,
                                convert_mouse_pos=lambda pos: convert_mouse_to_internal(
                                    pos, display_size
                                ),
                            )
                    else:
                        splash_screen.handle_event(
                            event,
                            convert_mouse_pos=lambda pos: convert_mouse_to_internal(
                                pos, display_size
                            ),
                        )
            
            # Mettre à jour
            splash_screen.update(dt)
            
            # Dessiner
            splash_screen.draw(internal_surface)
            
            # Dessiner la boîte de confirmation par-dessus l'écran d'accueil si elle est active
            if quit_confirmation_dialog is not None:
                quit_confirmation_dialog.draw(internal_surface)
            
            present_frame()
            
            # Vérifier si le jeu doit être lancé
            if splash_screen.should_start_game:
                splash_running = False
        
        # Si l'utilisateur a quitté pendant l'écran d'accueil, ne pas lancer le jeu
        if not running:
            pygame.quit()
            sys.exit(0)
    
    # ... reste du code pour charger et lancer le niveau ...
```

**Comportement** :
- Si `--skip-splash` est activé : L'écran d'accueil est complètement ignoré, le jeu charge directement le niveau
- Si `--skip-splash` n'est pas activé : L'écran d'accueil s'affiche normalement et attend l'interaction de l'utilisateur

### Module `splash_screen.py`

Créer un nouveau module `src/moteur_jeu_presentation/ui/splash_screen.py` :

```python
"""Module de gestion de l'écran d'accueil."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pygame


# Coordonnées du bouton START dans l'image originale (en pourcentage)
START_BUTTON_X_PERCENT = 0.35
START_BUTTON_Y_PERCENT = 0.75
START_BUTTON_WIDTH_PERCENT = 0.30
START_BUTTON_HEIGHT_PERCENT = 0.10

# Constantes de couleur pour le fond
BACKGROUND_COLOR_DEFAULT = (74, 149, 172)  # RGB(74, 149, 172) / #4a95ac
BACKGROUND_COLOR_HOVER = (255, 0, 0)       # Rouge


class SplashScreen:
    """Gère l'affichage et l'interaction de l'écran d'accueil."""
    
    def __init__(
        self,
        image_path: Path,
        screen_width: int,
        screen_height: int,
    ) -> None:
        """Initialise l'écran d'accueil.
        
        Args:
            image_path: Chemin vers l'image d'introduction
            screen_width: Largeur de l'écran de rendu
            screen_height: Hauteur de l'écran de rendu
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Charger l'image
        if not image_path.exists():
            raise FileNotFoundError(f"Image d'introduction introuvable : {image_path}")
        
        self.image = pygame.image.load(str(image_path)).convert_alpha()
        self.scaled_image: Optional[pygame.Surface] = None
        self.image_rect: Optional[pygame.Rect] = None
        self.start_button_rect: Optional[pygame.Rect] = None
        
        # État
        self.is_active = True
        self.should_start_game = False
        self.is_hovering_start = False
        
        # Couleur du fond
        self.background_color = BACKGROUND_COLOR_DEFAULT  # RGB(74, 149, 172) par défaut
        
        # Calculer la mise à l'échelle et les coordonnées
        self._calculate_scaled_image()
        self._update_button_rect()
    
    def _calculate_scaled_image(self) -> None:
        """Calcule la mise à l'échelle de l'image pour remplir l'écran."""
        image_width = self.image.get_width()
        image_height = self.image.get_height()
        screen_width = self.screen_width
        screen_height = self.screen_height
        
        # Calculer les ratios de mise à l'échelle
        scale_x = screen_width / image_width
        scale_y = screen_height / image_height
        
        # Utiliser le ratio le plus grand pour remplir l'écran
        scale = max(scale_x, scale_y)
        
        new_width = int(image_width * scale)
        new_height = int(image_height * scale)
        
        self.scaled_image = pygame.transform.smoothscale(self.image, (new_width, new_height))
        
        # Centrer l'image
        x = (screen_width - new_width) // 2
        y = (screen_height - new_height) // 2
        self.image_rect = pygame.Rect(x, y, new_width, new_height)
    
    def _update_button_rect(self) -> None:
        """Met à jour les coordonnées du bouton START après mise à l'échelle."""
        if self.image_rect is None or self.scaled_image is None:
            return
        
        image_width = self.image.get_width()
        image_height = self.image.get_height()
        
        # Calculer les coordonnées dans l'image originale
        button_x = int(image_width * START_BUTTON_X_PERCENT)
        button_y = int(image_height * START_BUTTON_Y_PERCENT)
        button_width = int(image_width * START_BUTTON_WIDTH_PERCENT)
        button_height = int(image_height * START_BUTTON_HEIGHT_PERCENT)
        
        # Appliquer la même mise à l'échelle que l'image
        scale_x = self.scaled_image.get_width() / image_width
        scale_y = self.scaled_image.get_height() / image_height
        
        # Calculer les coordonnées dans l'image mise à l'échelle
        scaled_button_x = int(button_x * scale_x)
        scaled_button_y = int(button_y * scale_y)
        scaled_button_width = int(button_width * scale_x)
        scaled_button_height = int(button_height * scale_y)
        
        # Calculer les coordonnées absolues du bouton (en incluant l'offset de l'image)
        button_abs_x = self.image_rect.x + scaled_button_x
        button_abs_y = self.image_rect.y + scaled_button_y
        
        # Clipper le rectangle du bouton pour qu'il soit dans les limites de la surface interne
        # (0, 0, screen_width, screen_height)
        # Ceci est important car si l'image est rognée (crop), le bouton pourrait être
        # partiellement ou complètement en dehors de la surface visible
        clipped_x = max(0, button_abs_x)
        clipped_y = max(0, button_abs_y)
        clipped_width = min(
            button_abs_x + scaled_button_width,
            self.screen_width
        ) - clipped_x
        clipped_height = min(
            button_abs_y + scaled_button_height,
            self.screen_height
        ) - clipped_y
        
        # Ne créer le rectangle que si la zone clippée est valide
        if clipped_width > 0 and clipped_height > 0:
            self.start_button_rect = pygame.Rect(
                clipped_x,
                clipped_y,
                clipped_width,
                clipped_height,
            )
        else:
            # Si le bouton est complètement en dehors de la surface, créer un rectangle vide
            self.start_button_rect = pygame.Rect(0, 0, 0, 0)
    
    def handle_event(self, event: pygame.event.Event) -> None:
        """Gère les événements de l'écran d'accueil.
        
        Args:
            event: Événement pygame à traiter
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Clic gauche
                if self.start_button_rect and self.start_button_rect.collidepoint(event.pos):
                    self.should_start_game = True
                    self.is_active = False
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                # Lancer le jeu avec Entrée ou Espace
                self.should_start_game = True
                self.is_active = False
    
    def update(self, dt: float) -> None:
        """Met à jour l'état de l'écran d'accueil.
        
        Args:
            dt: Temps écoulé depuis la dernière frame (en secondes)
        """
        # La couleur du fond est mise à jour dans handle_event() lors du mouvement de la souris
        # Cette méthode peut être étendue pour des animations, effets, etc.
        pass
    
    def _update_background_color(self) -> None:
        """Met à jour la couleur du fond selon l'état du survol."""
        if self.is_hovering_start:
            self.background_color = (255, 0, 0)  # Rouge au survol
        else:
            self.background_color = (255, 220, 0)  # Jaune par défaut
    
    def draw(self, surface: pygame.Surface) -> None:
        """Dessine l'écran d'accueil.
        
        Args:
            surface: Surface pygame sur laquelle dessiner
        """
        # Remplir l'écran en noir (pour les zones de letterboxing si nécessaire)
        surface.fill((0, 0, 0))
        
        # Dessiner l'image mise à l'échelle
        if self.scaled_image and self.image_rect:
            surface.blit(self.scaled_image, self.image_rect)
        
        # Optionnel : Dessiner un rectangle de debug pour visualiser la zone du bouton START
        # (à retirer en production ou activer avec un flag de debug)
        # if self.start_button_rect:
        #     pygame.draw.rect(surface, (255, 0, 0), self.start_button_rect, 2)
```

### Mise à jour de `ui/__init__.py`

Ajouter l'export des nouvelles classes :

```python
from moteur_jeu_presentation.ui.splash_screen import SplashScreen
from moteur_jeu_presentation.ui.quit_confirmation import QuitConfirmationDialog

__all__ = [
    "PlayerStatsDisplay",
    "SpeechBubble",
    "show_speech_bubble",
    "SplashScreen",
    "QuitConfirmationDialog",
]
```

## Contraintes et considérations

### Performance

- L'image d'introduction doit être chargée une seule fois au démarrage
- La mise à l'échelle doit être calculée une seule fois (pas à chaque frame)
- Utiliser `pygame.transform.smoothscale()` pour une meilleure qualité, mais cela peut être plus lent que `scale()`
- Pour de très grandes images, considérer pré-calculer plusieurs tailles ou utiliser une image déjà à la bonne résolution

### Compatibilité avec le mode plein écran

- L'écran d'accueil doit fonctionner correctement en mode plein écran (spécification 5)
- La mise à l'échelle doit tenir compte de la résolution de l'écran
- Les coordonnées du bouton START doivent être adaptées à la résolution réelle de l'écran

### Ajustement des coordonnées du bouton START

Les coordonnées du bouton START (`START_BUTTON_X_PERCENT`, etc.) doivent être ajustées en fonction de l'image réelle `image-intro.png`. Si l'image change, il faut redétecter la position du bouton START.

#### Méthode 1 : Utilisation du mode debug (recommandé)

1. Activer le mode debug en passant `debug=True` au constructeur de `SplashScreen` dans `main.py`
2. Lancer le jeu - un rectangle rouge s'affichera pour visualiser la zone cliquable du bouton START
3. Vérifier dans la console les informations de debug affichées au chargement (dimensions de l'image, coordonnées du rectangle)
4. Ajuster les pourcentages dans `splash_screen.py` jusqu'à ce que le rectangle corresponde au bouton START
5. Tester en cliquant sur le bouton pour vérifier que la détection fonctionne
6. **Important** : Désactiver le mode debug en production en passant `debug=False` dans `main.py` (par défaut, le mode debug est désactivé)

**Mode debug** : Le mode debug affiche :
- Les dimensions de l'image et de la surface interne
- Les coordonnées du rectangle du bouton START
- Les pourcentages utilisés
- Lors d'un clic : les coordonnées du clic et le résultat de la collision

#### Méthode 2 : Utilisation du script utilitaire

1. Utiliser le script `scripts/detect_start_button.py` :
   ```bash
   python scripts/detect_start_button.py
   ```
2. Le script affichera les dimensions de l'image
3. Ouvrir l'image dans un éditeur d'images et trouver les coordonnées du bouton START
4. Entrer les coordonnées interactivement ou utiliser les formules affichées
5. Mettre à jour les constantes dans `splash_screen.py` avec les valeurs calculées

#### Méthode 3 : Calcul manuel

Si vous connaissez les coordonnées absolues du bouton START dans l'image :

1. Trouver les dimensions de l'image (largeur × hauteur)
2. Trouver les coordonnées du coin supérieur gauche du bouton START (x, y)
3. Trouver la largeur et la hauteur du bouton START (w, h)
4. Calculer les pourcentages :
   - `START_BUTTON_X_PERCENT = x / image_width`
   - `START_BUTTON_Y_PERCENT = y / image_height`
   - `START_BUTTON_WIDTH_PERCENT = w / image_width`
   - `START_BUTTON_HEIGHT_PERCENT = h / image_height`
5. Mettre à jour les constantes dans `splash_screen.py`

### Gestion des erreurs

- Si l'image `image-intro.png` est introuvable, le jeu doit afficher une erreur claire et quitter proprement
- Si l'image ne peut pas être chargée (format invalide, etc.), gérer l'exception et quitter proprement

### Expérience utilisateur

- L'écran d'accueil doit être réactif (pas de délai perceptible entre le clic et le lancement du jeu)
- Le fond change de couleur (RGB(74, 149, 172) → rouge) de manière fluide lorsque la souris survole le bouton START
- Afficher une boîte de confirmation avant de quitter le jeu avec Échap depuis l'écran d'accueil
- Permettre de lancer le jeu avec Entrée ou Espace en plus du clic sur START
- Le changement de couleur du fond fournit un feedback visuel clair indiquant que le bouton START est interactif
- **Option de développement** : Permettre de sauter l'écran d'accueil avec `--skip-splash` pour accélérer les tests et le développement

### Pièges courants

#### Double conversion des coordonnées de la souris

**Problème** : Si les coordonnées de la souris sont converties deux fois (une fois dans la boucle principale et une fois dans `handle_event()`), le clic ne sera pas détecté correctement.

**Solution** : Ne convertir les coordonnées qu'une seule fois, de préférence dans `handle_event()` en utilisant la fonction `convert_mouse_pos` passée en paramètre.

#### Rectangle du bouton en dehors de la surface

**Problème** : Si l'image est rognée (crop) et que le bouton START est partiellement ou complètement en dehors de la surface visible, le clic ne fonctionnera pas.

**Solution** : Clipper le rectangle du bouton pour qu'il soit toujours dans les limites de la surface interne (0, 0, screen_width, screen_height). Si le bouton est complètement en dehors, créer un rectangle vide.

## Tests

### Tests à effectuer

1. **Test de chargement** : Vérifier que l'image se charge correctement
2. **Test de mise à l'échelle** : Vérifier que l'image est correctement mise à l'échelle sur différentes résolutions
3. **Test du fond coloré** : Vérifier que le fond utilise la couleur RGB(74, 149, 172) et s'affiche correctement derrière l'image
4. **Test du survol** : Vérifier que le fond passe en rouge lorsque la souris survole le bouton START
5. **Test de détection du clic** : Vérifier que le clic sur le bouton START est correctement détecté
6. **Test de lancement** : Vérifier que le niveau se lance correctement après le clic
7. **Test de raccourcis clavier** : Vérifier que Entrée et Espace lancent le jeu
8. **Test de quitter** : Vérifier que Échap affiche la boîte de confirmation depuis l'écran d'accueil
9. **Test de boîte de confirmation sur écran d'accueil** : Vérifier que la boîte de confirmation s'affiche correctement par-dessus l'écran d'accueil
10. **Test de clic sur "Oui" depuis l'écran d'accueil** : Vérifier que le clic sur "Oui" ferme le jeu depuis l'écran d'accueil
11. **Test de clic sur "Non" depuis l'écran d'accueil** : Vérifier que le clic sur "Non" ferme la boîte et continue l'écran d'accueil
9. **Test en mode plein écran** : Vérifier que l'écran d'accueil fonctionne correctement en mode plein écran
10. **Test de conversion des coordonnées** : Vérifier que le survol fonctionne correctement en mode plein écran (conversion des coordonnées de la souris)
11. **Test de l'option --skip-splash** : Vérifier que le jeu lance directement le niveau sans afficher l'écran d'accueil lorsque `--skip-splash` est activé

### Exemple de test

```python
def test_splash_screen_initialization():
    """Test que l'écran d'accueil s'initialise correctement."""
    pygame.init()
    
    try:
        image_path = Path("sprite/interface/image-intro.png")
        splash = SplashScreen(
            image_path=image_path,
            screen_width=1280,
            screen_height=720,
        )
        
        assert splash.is_active
        assert not splash.should_start_game
        assert splash.scaled_image is not None
        assert splash.image_rect is not None
        assert splash.start_button_rect is not None
    finally:
        pygame.quit()
```

## Évolutions futures possibles

- **Animation de transition** : Ajouter une animation de fondu (fade in/out) entre l'écran d'accueil et le niveau
- **Effets visuels** : Ajouter des effets de particules ou d'animation sur l'écran d'accueil
- **Menu principal** : Transformer l'écran d'accueil en menu principal avec plusieurs options (Jouer, Options, Quitter)
- **Machine à états** : Implémenter une machine à états complète (spécification suggérée dans les bonnes pratiques) pour gérer les différents écrans du jeu
- **Sons** : Ajouter des sons pour le clic sur le bouton START et la transition
- **Support de plusieurs images** : Permettre de définir différentes images d'introduction selon le contexte
- **Détection automatique du bouton** : Utiliser une technique de détection d'image pour trouver automatiquement le bouton START

## Références

- Bonnes pratiques : `bonne_pratique.md`
- Spécification mode plein écran : `spec/5-mode-plein-ecran.md`
- Documentation Pygame : [pygame.Surface](https://www.pygame.org/docs/ref/surface.html)
- Documentation Pygame : [pygame.transform](https://www.pygame.org/docs/ref/transform.html)
- Code existant : `src/moteur_jeu_presentation/main.py`
- Image d'introduction : `sprite/interface/image-intro.png`

---

**Date de création** : 2024  
**Statut** : ✅ Implémenté

