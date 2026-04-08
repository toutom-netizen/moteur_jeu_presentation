# 5 - Mode plein écran

## Contexte

Cette spécification définit l'implémentation du mode plein écran pour le jeu. Le jeu doit pouvoir se lancer directement en mode plein écran, offrant une expérience immersive à l'utilisateur sans nécessiter d'interaction supplémentaire.

## Objectifs

- Lancer le jeu en mode plein écran par défaut
- Utiliser la résolution native de l'écran ou une résolution adaptée
- Maintenir les proportions et le ratio d'aspect du jeu
- Assurer la compatibilité avec le système de parallaxe et de rendu existant
- Permettre éventuellement de basculer entre mode plein écran et fenêtré (évolution future)

## Architecture

### Mode plein écran dans Pygame

Pygame offre plusieurs méthodes pour gérer le mode plein écran :
- `pygame.FULLSCREEN` : Mode plein écran avec résolution native de l'écran
- `pygame.SCALED` : Mode plein écran avec mise à l'échelle automatique
- Combinaison des deux flags pour un meilleur contrôle

### Résolution et mise à l'échelle

Le jeu est désormais conçu pour une résolution interne de **1920x1080** (16:9). En mode plein écran :
- Si l'écran a un ratio 16:9 ou des dimensions supérieures, utiliser la résolution native pour la fenêtre et appliquer un letterboxing si nécessaire
- Si l'écran a un ratio différent, utiliser une mise à l'échelle et un remplissage noir pour préserver les proportions
- Les dimensions de rendu internes restent 1920x1080 pour la cohérence du gameplay

## Spécifications techniques

### Initialisation de la fenêtre

#### Modification de `pygame.display.set_mode()`

```python
from moteur_jeu_presentation.rendering import get_render_size

render_width, render_height = get_render_size()

# Mode Metal (hardware scaling)
screen = pygame.display.set_mode(
    (render_width, render_height),
    pygame.FULLSCREEN | pygame.SCALED | pygame.DOUBLEBUF,
)

# Mode standard (software scaling) : plein écran natif sans SCALED
# screen = pygame.display.set_mode(
#     native_display_size,
#     pygame.FULLSCREEN | pygame.DOUBLEBUF,
# )
```

**Paramètres** :
- `render_width` / `render_height` : 1920x1080 (résolution interne)
- `pygame.FULLSCREEN` : Active le mode plein écran
- `pygame.SCALED` : Utilisé en mode Metal pour activer le scaling matériel (non utilisé en mode standard)
- `pygame.DOUBLEBUF` : Active le double buffering pour limiter le tearing

### Gestion de la résolution

#### Récupération de la résolution de l'écran

```python
import pygame

# Récupérer les informations de l'écran
display_info = pygame.display.Info()
screen_width = display_info.current_w
screen_height = display_info.current_h
```

#### Surface de rendu interne

Pour maintenir la cohérence du gameplay et des calculs de collision, le jeu doit utiliser une surface de rendu interne à la résolution fixe (1920x1080) :

```python
from moteur_jeu_presentation.rendering import compute_scaled_size, get_render_size, letterbox_offsets

render_width, render_height = get_render_size()
internal_surface = pygame.Surface((render_width, render_height)).convert(screen)

def present_frame(screen: pygame.Surface, internal: pygame.Surface) -> None:
    display_size = pygame.display.get_window_size()
    scaled_size = compute_scaled_size(display_size)
    scaled_surface = pygame.transform.smoothscale(internal, scaled_size)
    offset = letterbox_offsets(display_size)
    if offset != (0, 0):
        screen.fill((0, 0, 0))
    screen.blit(scaled_surface, offset)
    pygame.display.flip()
```

**Important** :
- En mode Metal, `pygame.SCALED` est activé et le rendu peut être directement réalisé sur `screen` (résolution logique).
- En mode standard, le jeu utilise une surface interne 1920x1080 et applique un `smoothscale` manuel pour garantir la qualité du rendu (avec letterboxing automatique si nécessaire).

### Gestion des événements

Le mode plein écran doit gérer les événements suivants :

```python
# Variable pour gérer la boîte de confirmation de quitter
quit_confirmation_dialog = None

for event in pygame.event.get():
    # Si la boîte de confirmation est active, lui passer tous les événements en priorité
    if quit_confirmation_dialog is not None:
        quit_confirmation_dialog.handle_event(event, convert_mouse_pos)
        # Vérifier si la boîte doit être fermée
        if quit_confirmation_dialog.should_quit:
            running = False
        elif quit_confirmation_dialog.is_dismissed:
            quit_confirmation_dialog = None
    else:
        # Boîte non active, gérer les événements normalement
        if event.type == pygame.QUIT:
            # Afficher la boîte de confirmation au lieu de quitter directement
            quit_confirmation_dialog = QuitConfirmationDialog(screen_width, screen_height)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # Afficher la boîte de confirmation au lieu de quitter directement
                quit_confirmation_dialog = QuitConfirmationDialog(screen_width, screen_height)
            # Évolution future : basculer entre plein écran et fenêtré
            # elif event.key == pygame.K_F11:
            #     toggle_fullscreen()
        elif event.type == pygame.WINDOWFOCUSLOST:
            # La fenêtre a perdu le focus (changement de workspace, etc.)
            # Ne rien faire, le jeu continue de tourner
            pass
        elif event.type == pygame.WINDOWFOCUSGAINED:
            # La fenêtre a regagné le focus
            # S'assurer que la surface d'affichage est toujours valide
            # En mode plein écran, pygame peut avoir besoin de recréer la surface
            try:
                # Vérifier que la surface est toujours valide
                _ = screen.get_size()
            except (pygame.error, AttributeError):
                # Recréer la surface si elle est invalide
                try:
                    screen = pygame.display.set_mode(
                        (SCREEN_WIDTH, SCREEN_HEIGHT),
                        pygame.FULLSCREEN | pygame.SCALED,
                    )
                except pygame.error:
                    # Fallback vers mode fenêtré si le plein écran échoue
                    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
```

**Note importante** : Il est également recommandé de vérifier la validité de la surface avant chaque opération de rendu pour éviter les erreurs si la surface devient invalide.

### Boîte de confirmation de quitter

Lorsque l'utilisateur appuie sur la touche Échap ou ferme la fenêtre, une boîte de confirmation doit s'afficher au lieu de quitter directement le jeu. Cette boîte affiche un message demandant confirmation et propose deux boutons cliquables avec la souris : "Oui" et "Non".

#### Classe `QuitConfirmationDialog`

```python
class QuitConfirmationDialog:
    """Gère l'affichage et l'interaction de la boîte de confirmation de quitter."""
    
    def __init__(
        self,
        screen_width: int,
        screen_height: int,
    ) -> None:
        """Initialise la boîte de confirmation.
        
        Args:
            screen_width: Largeur de l'écran de rendu
            screen_height: Hauteur de l'écran de rendu
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # État
        self.should_quit = False
        self.is_dismissed = False
        
        # Police pour le texte (doit être créée avant de calculer les dimensions)
        try:
            self.font = pygame.font.Font(None, 36)
        except pygame.error:
            # Fallback vers police système si None ne fonctionne pas
            try:
                self.font = pygame.font.SysFont("arial", 36)
            except pygame.error:
                self.font = pygame.font.SysFont("sans-serif", 36)
        
        self.message_text = "Voulez-vous vraiment quitter le jeu ?"
        
        # Calculer les dimensions de la boîte en fonction de la taille du texte
        # Rendre le texte pour obtenir ses dimensions
        text_surface = self.font.render(self.message_text, True, (255, 255, 255))
        text_width, text_height = text_surface.get_size()
        
        # Marges minimales
        padding_horizontal = 40  # Marge horizontale de chaque côté
        padding_vertical = 80   # Marge verticale (haut + bas)
        button_area_height = 80  # Espace pour les boutons en bas
        
        # Dimensions minimales pour les boutons
        self.button_width = 100
        self.button_height = 40
        self.button_spacing = 20
        
        # Calculer la largeur minimale nécessaire (texte + marges ou boutons + espacement)
        min_width_for_buttons = (self.button_width * 2) + self.button_spacing + (padding_horizontal * 2)
        dialog_width = max(text_width + (padding_horizontal * 2), min_width_for_buttons)
        
        # Calculer la hauteur minimale nécessaire (texte + marges + boutons)
        dialog_height = text_height + padding_vertical + button_area_height
        
        # Dimensions et position de la boîte de dialogue
        self.dialog_width = int(dialog_width)
        self.dialog_height = int(dialog_height)
        self.dialog_x = (screen_width - self.dialog_width) // 2
        self.dialog_y = (screen_height - self.dialog_height) // 2
        
        # Dimensions et position des boutons (déjà définies ci-dessus)
        
        # Bouton "Oui"
        self.yes_button_rect = pygame.Rect(
            self.dialog_x + self.dialog_width // 2 - self.button_width - self.button_spacing // 2,
            self.dialog_y + self.dialog_height - 60,
            self.button_width,
            self.button_height,
        )
        
        # Bouton "Non"
        self.no_button_rect = pygame.Rect(
            self.dialog_x + self.dialog_width // 2 + self.button_spacing // 2,
            self.dialog_y + self.dialog_height - 60,
            self.button_width,
            self.button_height,
        )
        
        # État de survol des boutons
        self.is_hovering_yes = False
        self.is_hovering_no = False
    
    def handle_event(
        self,
        event: pygame.event.Event,
        convert_mouse_pos: Optional[Callable[[Tuple[int, int]], Tuple[int, int]]] = None,
    ) -> None:
        """Gère les événements de la boîte de confirmation.
        
        Args:
            event: Événement pygame à traiter
            convert_mouse_pos: Fonction optionnelle pour convertir les coordonnées de la souris
        """
        if event.type == pygame.MOUSEMOTION:
            mouse_pos = event.pos
            if convert_mouse_pos is not None:
                mouse_pos = convert_mouse_pos(mouse_pos)
            
            self.is_hovering_yes = self.yes_button_rect.collidepoint(mouse_pos)
            self.is_hovering_no = self.no_button_rect.collidepoint(mouse_pos)
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Clic gauche
                mouse_pos = event.pos
                if convert_mouse_pos is not None:
                    mouse_pos = convert_mouse_pos(mouse_pos)
                
                if self.yes_button_rect.collidepoint(mouse_pos):
                    self.should_quit = True
                    self.is_dismissed = True
                elif self.no_button_rect.collidepoint(mouse_pos):
                    self.is_dismissed = True
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # Échap ferme la boîte sans quitter
                self.is_dismissed = True
            elif event.key == pygame.K_RETURN:
                # Entrée confirme la sortie
                self.should_quit = True
                self.is_dismissed = True
    
    def draw(self, surface: pygame.Surface) -> None:
        """Dessine la boîte de confirmation.
        
        Args:
            surface: Surface pygame sur laquelle dessiner
        """
        # Dessiner un overlay semi-transparent (fond assombri)
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        surface.blit(overlay, (0, 0))
        
        # Dessiner la boîte de dialogue
        dialog_rect = pygame.Rect(
            self.dialog_x,
            self.dialog_y,
            self.dialog_width,
            self.dialog_height,
        )
        pygame.draw.rect(surface, (50, 50, 50), dialog_rect)
        pygame.draw.rect(surface, (200, 200, 200), dialog_rect, 2)
        
        # Dessiner le message
        text_surface = self.font.render(self.message_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(
            self.dialog_x + self.dialog_width // 2,
            self.dialog_y + 60,
        ))
        surface.blit(text_surface, text_rect)
        
        # Dessiner le bouton "Oui"
        yes_color = (100, 200, 100) if self.is_hovering_yes else (80, 180, 80)
        pygame.draw.rect(surface, yes_color, self.yes_button_rect)
        pygame.draw.rect(surface, (200, 200, 200), self.yes_button_rect, 2)
        yes_text = self.font.render("Oui", True, (255, 255, 255))
        yes_text_rect = yes_text.get_rect(center=self.yes_button_rect.center)
        surface.blit(yes_text, yes_text_rect)
        
        # Dessiner le bouton "Non"
        no_color = (200, 100, 100) if self.is_hovering_no else (180, 80, 80)
        pygame.draw.rect(surface, no_color, self.no_button_rect)
        pygame.draw.rect(surface, (200, 200, 200), self.no_button_rect, 2)
        no_text = self.font.render("Non", True, (255, 255, 255))
        no_text_rect = no_text.get_rect(center=self.no_button_rect.center)
        surface.blit(no_text, no_text_rect)
```

**Comportement** :
- La boîte de confirmation s'affiche au centre de l'écran avec un fond assombri (overlay semi-transparent)
- Le message "Voulez-vous vraiment quitter le jeu ?" est affiché
- **Dimensions adaptatives** : La taille de la boîte est calculée dynamiquement en fonction de la taille du texte pour garantir que le message est entièrement visible. La largeur est calculée comme le maximum entre la largeur du texte (avec marges) et la largeur minimale nécessaire pour les boutons. La hauteur est calculée comme la somme de la hauteur du texte, des marges verticales et de l'espace nécessaire pour les boutons.
- Deux boutons cliquables sont disponibles : "Oui" (vert) et "Non" (rouge)
- Les boutons changent de couleur au survol de la souris
- Clic sur "Oui" : le jeu se ferme
- Clic sur "Non" : la boîte se ferme et le jeu continue
- Touche Échap : ferme la boîte sans quitter (comme "Non")
- Touche Entrée : confirme la sortie (comme "Oui")

## Implémentation

### Structure de fichiers

```
src/moteur_jeu_presentation/
├── main.py          # Modification de l'initialisation de la fenêtre
├── ui/
│   ├── __init__.py
│   └── quit_confirmation.py    # Nouvelle classe QuitConfirmationDialog
```

### Modifications dans `main.py`

#### Configuration de la fenêtre

```python
def main() -> None:
    """Point d'entrée principal du jeu."""
    # Initialiser pygame
    pygame.init()

    # Configuration de la fenêtre
    render_width, render_height = get_render_size()
    FPS = 60

    # Créer la fenêtre en mode plein écran
    screen = pygame.display.set_mode(
        (render_width, render_height),
        pygame.FULLSCREEN | pygame.SCALED | pygame.DOUBLEBUF,
    )
    pygame.display.set_caption("Présentation")
    clock = pygame.time.Clock()
    
    # ... reste du code ...
```

### Option : Surface de rendu interne (recommandé)

Pour une meilleure cohérence et contrôle, utiliser une surface de rendu interne :

```python
def main() -> None:
    """Point d'entrée principal du jeu."""
    # Initialiser pygame
    pygame.init()

    # Configuration de la fenêtre
    render_width, render_height = get_render_size()
    FPS = 60

    # Créer la surface de rendu interne
    internal_surface = pygame.Surface((render_width, render_height))

    # Créer la fenêtre en mode plein écran
    screen = pygame.display.set_mode(
        (render_width, render_height),
        pygame.FULLSCREEN | pygame.SCALED | pygame.DOUBLEBUF,
    )
    pygame.display.set_caption("Présentation")
    clock = pygame.time.Clock()
    
    # ... initialisation du jeu ...
    
    # Boucle principale
    running = True
    while running:
        # ... logique du jeu ...
        
        # Dessiner sur la surface interne
        internal_surface.fill((30, 30, 30))
        
        # Dessiner les couches derrière le joueur
        for layer in parallax_system._layers:
            if layer.depth <= 1:
                parallax_system._draw_layer(internal_surface, layer)
        
        # Dessiner le personnage
        player.draw(internal_surface, camera_x)
        
        # Dessiner les couches devant le joueur
        for layer in parallax_system._layers:
            if layer.depth >= 2:
                parallax_system._draw_layer(internal_surface, layer)
        
        # Dessiner la boîte de confirmation par-dessus le jeu si elle est active
        if quit_confirmation_dialog is not None:
            quit_confirmation_dialog.draw(internal_surface)
        
        # Mettre à l'échelle et afficher sur l'écran
        # Vérifier que la surface est toujours valide avant de dessiner
        try:
            screen_size = screen.get_size()
            scaled_surface = pygame.transform.scale(internal_surface, screen_size)
            screen.blit(scaled_surface, (0, 0))
            pygame.display.flip()
        except (pygame.error, AttributeError):
            # Si la surface est invalide, essayer de la recréer
            try:
                screen = pygame.display.set_mode(
                    (SCREEN_WIDTH, SCREEN_HEIGHT),
                    pygame.FULLSCREEN | pygame.SCALED,
                )
            except pygame.error:
                # Fallback vers mode fenêtré si le plein écran échoue
                screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            # Redessiner immédiatement après la recréation
            screen_size = screen.get_size()
            scaled_surface = pygame.transform.scale(internal_surface, screen_size)
            screen.blit(scaled_surface, (0, 0))
            pygame.display.flip()
    
    pygame.quit()
    sys.exit(0)
```

## Contraintes et considérations

### Performance

- La mise à l'échelle peut avoir un impact sur les performances, surtout sur les écrans haute résolution
- Utiliser `pygame.SCALED` peut améliorer les performances grâce à l'accélération matérielle
- Tester sur différentes résolutions d'écran pour valider les performances
- Si un buffer de mise à l'échelle est mis en cache, continuer à appeler `pygame.transform.scale` à chaque frame (en réutilisant ce buffer comme destination) afin que le contenu mis à jour de `internal_surface` soit bien affiché.
- Lorsque la taille de la fenêtre correspond exactement à la surface interne (ex. 1920x1080), éviter toute mise à l'échelle inutile et blitter directement `internal_surface` sur `screen`.

### Ratio d'aspect

- Le jeu est conçu pour un ratio 16:9 (1920x1080)
- Sur des écrans avec un ratio différent (16:10, 21:9, etc.), des barres noires peuvent apparaître ou l'image peut être étirée
- `pygame.SCALED` avec `pygame.FULLSCREEN` gère généralement bien ces cas

### Compatibilité

- Vérifier que tous les systèmes de rendu (parallaxe, sprites, collisions) fonctionnent correctement en mode plein écran
- Les calculs de position doivent rester basés sur la résolution interne (1920x1080)
- La caméra et le système de parallaxe doivent continuer à fonctionner correctement

### Expérience utilisateur

- Le mode plein écran offre une immersion maximale
- La touche ESC affiche une boîte de confirmation avant de quitter le jeu, évitant les sorties accidentelles
- La boîte de confirmation propose deux boutons cliquables avec la souris : "Oui" et "Non"
- La taille de la boîte de confirmation s'adapte automatiquement au texte pour garantir une lisibilité optimale
- Évolution future : permettre de basculer entre plein écran et fenêtré avec F11

### Gestion des erreurs

```python
try:
    screen = pygame.display.set_mode(
        (SCREEN_WIDTH, SCREEN_HEIGHT),
        pygame.FULLSCREEN | pygame.SCALED
    )
except pygame.error as e:
    print(f"Erreur lors de l'initialisation du mode plein écran : {e}")
    # Fallback vers mode fenêtré
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
```

### Pièges courants

#### Le personnage disparaît après un changement de workspace

**Problème** : Quand on change de workspace (ou qu'on minimise la fenêtre) et qu'on revient, le personnage ou d'autres éléments du jeu disparaissent.

**Cause** : Quand la fenêtre perd le focus (changement de workspace, minimisation, etc.), pygame peut invalider la surface d'affichage (`screen`). Quand on revient, la surface peut être invalide ou avoir changé de taille, ce qui empêche le rendu correct.

**Solution** :

1. **Gérer les événements de focus** : Écouter les événements `pygame.WINDOWFOCUSLOST` et `pygame.WINDOWFOCUSGAINED` pour détecter quand la fenêtre perd et regagne le focus.

2. **Vérifier la validité de la surface** : Avant chaque opération de rendu, vérifier que la surface est toujours valide en appelant `screen.get_size()` dans un bloc try/except.

3. **Recréer la surface si nécessaire** : Si la surface est invalide, la recréer avec `pygame.display.set_mode()`.

**Exemple de code** :

```python
# Dans la boucle de jeu, lors du rendu
try:
    screen_size = screen.get_size()
    scaled_surface = pygame.transform.scale(internal_surface, screen_size)
    screen.blit(scaled_surface, (0, 0))
    pygame.display.flip()
except (pygame.error, AttributeError):
    # Si la surface est invalide, essayer de la recréer
    try:
        screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            pygame.FULLSCREEN | pygame.SCALED,
        )
    except pygame.error:
        # Fallback vers mode fenêtré si le plein écran échoue
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    # Redessiner immédiatement après la recréation
    screen_size = screen.get_size()
    scaled_surface = pygame.transform.scale(internal_surface, screen_size)
    screen.blit(scaled_surface, (0, 0))
    pygame.display.flip()
```

**Note importante** : Il est recommandé de gérer à la fois les événements de focus ET de vérifier la validité de la surface avant chaque rendu pour une robustesse maximale.

**Autres points importants** :

1. **Limiter le delta time** : Quand la fenêtre perd le focus, le delta time peut devenir très grand (plusieurs secondes). Il faut limiter le delta time pour éviter que le personnage se déplace trop loin ou disparaisse :
   ```python
   dt = clock.tick(FPS) / 1000.0
   # Limiter le delta time pour éviter des problèmes lors de changements de workspace
   if dt > 0.1:
       dt = 0.1  # Limiter à 100ms maximum (10 FPS minimum)
   ```

2. **Vérifier la surface interne** : La surface interne (`internal_surface`) peut aussi être invalidée. Il faut la vérifier et la recréer si nécessaire :
   ```python
   try:
       _ = internal_surface.get_size()
   except (pygame.error, AttributeError):
       internal_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
   ```

3. **Redessiner après recréation** : Si une surface est recréée, il faut redessiner tout le contenu immédiatement pour éviter un écran vide.

#### La boîte de confirmation est trop petite et le texte est coupé

**Problème** : Le texte de la boîte de confirmation est coupé ou la boîte est trop petite pour contenir le message complet.

**Cause** : Si les dimensions de la boîte de dialogue sont fixes, elles peuvent ne pas être suffisantes pour contenir le texte, surtout si le texte est long ou si la police est grande.

**Solution** : Calculer dynamiquement les dimensions de la boîte en fonction de la taille du texte rendu :

1. **Créer la police avant de calculer les dimensions** : La police doit être créée avant de pouvoir calculer la taille du texte.

2. **Rendre le texte pour obtenir ses dimensions** : Utiliser `font.render()` pour créer une surface de texte temporaire et obtenir ses dimensions avec `get_size()`.

3. **Calculer les dimensions avec marges** : Ajouter des marges minimales autour du texte et s'assurer que la largeur est au moins égale à la largeur minimale nécessaire pour les boutons.

4. **Centrer le texte verticalement** : Calculer la position verticale du texte en fonction de la hauteur de la boîte et de la zone réservée aux boutons pour un centrage optimal.

**Exemple de code** :

```python
# Créer la police avant de calculer les dimensions
self.font = pygame.font.Font(None, 36)
self.message_text = "Voulez-vous vraiment quitter le jeu ?"

# Rendre le texte pour obtenir ses dimensions
text_surface = self.font.render(self.message_text, True, (255, 255, 255))
text_width, text_height = text_surface.get_size()

# Marges minimales
padding_horizontal = 40
padding_vertical = 80
button_area_height = 80

# Calculer la largeur (maximum entre texte + marges et boutons + espacement)
min_width_for_buttons = (self.button_width * 2) + self.button_spacing + (padding_horizontal * 2)
dialog_width = max(text_width + (padding_horizontal * 2), min_width_for_buttons)

# Calculer la hauteur (texte + marges + boutons)
dialog_height = text_height + padding_vertical + button_area_height

# Utiliser ces dimensions pour créer la boîte
self.dialog_width = int(dialog_width)
self.dialog_height = int(dialog_height)
```

**Note importante** : Cette approche garantit que la boîte s'adapte automatiquement à la longueur du texte, évitant les problèmes de texte coupé même si le message change à l'avenir.

#### Les événements de souris ne sont plus traités après l'ajout de la boîte de confirmation

**Problème** : Après l'ajout de la boîte de confirmation, les clics de souris ne fonctionnent plus pour passer les messages de dialogue ou interagir avec d'autres éléments du jeu.

**Cause** : Les événements `pygame.MOUSEBUTTONDOWN` et `pygame.MOUSEMOTION` ont été placés à l'intérieur du bloc `elif event.type == pygame.KEYDOWN:`, ce qui signifie qu'ils ne seront jamais exécutés car un événement de souris n'est pas un événement de clavier.

**Solution** : S'assurer que tous les types d'événements sont au même niveau dans la structure `if/elif` :

```python
for event in pygame.event.get():
    if quit_confirmation_dialog is not None:
        # Gérer les événements de la boîte de confirmation
        quit_confirmation_dialog.handle_event(event, convert_mouse_pos)
        # ...
    else:
        # Boîte non active, gérer les événements normalement
        if event.type == pygame.QUIT:
            # ...
        elif event.type == pygame.KEYDOWN:
            # Gérer les touches du clavier
            if event.key == pygame.K_ESCAPE:
                # ...
        elif event.type == pygame.MOUSEBUTTONDOWN:  # ⚠️ AU MÊME NIVEAU QUE KEYDOWN
            # Gérer les clics de souris
            # ...
        elif event.type == pygame.MOUSEMOTION:  # ⚠️ AU MÊME NIVEAU QUE KEYDOWN
            # Gérer le mouvement de la souris
            # ...
        elif event.type == pygame.WINDOWFOCUSLOST:
            # ...
```

**Erreur courante** : Ne pas mettre les événements de souris dans le bloc `KEYDOWN` :

```python
# ❌ MAUVAIS - Les événements de souris ne seront jamais traités
elif event.type == pygame.KEYDOWN:
    if event.key == pygame.K_ESCAPE:
        # ...
    elif event.type == pygame.MOUSEBUTTONDOWN:  # ❌ Jamais exécuté !
        # ...
```

**Note importante** : Chaque type d'événement (`pygame.QUIT`, `pygame.KEYDOWN`, `pygame.MOUSEBUTTONDOWN`, etc.) doit être au même niveau dans la structure `if/elif`, pas imbriqué dans un autre type d'événement.

## Tests

### Tests à effectuer

1. **Test de lancement** : Vérifier que le jeu se lance correctement en mode plein écran
2. **Test de résolution** : Tester sur différentes résolutions d'écran (1920x1080, 1920x1080, 2560x1440, 3840x2160, etc.) - la résolution interne de référence est maintenant 1920x1080
3. **Test de ratio d'aspect** : Tester sur des écrans avec différents ratios (16:9, 16:10, 21:9)
4. **Test de performance** : Vérifier que les performances restent acceptables en mode plein écran
5. **Test de rendu** : Vérifier que tous les éléments sont correctement affichés et mis à l'échelle
6. **Test de sortie** : Vérifier que la touche ESC affiche la boîte de confirmation
7. **Test de boîte de confirmation** : Vérifier que la boîte de confirmation s'affiche correctement avec les boutons "Oui" et "Non"
8. **Test de clic sur "Oui"** : Vérifier que le clic sur "Oui" ferme le jeu
9. **Test de clic sur "Non"** : Vérifier que le clic sur "Non" ferme la boîte et continue le jeu
10. **Test de survol des boutons** : Vérifier que les boutons changent de couleur au survol de la souris
7. **Test de changement de workspace** : Vérifier que le jeu continue de fonctionner correctement après un changement de workspace ou une minimisation de la fenêtre

### Exemple de test

```python
def test_fullscreen_initialization():
    """Test que le mode plein écran s'initialise correctement."""
    pygame.init()
    
    try:
        screen = pygame.display.set_mode(
            (1280, 720),
            pygame.FULLSCREEN | pygame.SCALED
        )
        
        assert screen.get_flags() & pygame.FULLSCREEN
        assert screen.get_size() == (1280, 720) or screen.get_size() == pygame.display.get_surface().get_size()
    finally:
        pygame.quit()
```

## Évolutions futures possibles

- **Basculer entre plein écran et fenêtré** : Ajouter un raccourci clavier (F11) pour basculer entre les modes
- **Sélection de résolution** : Permettre à l'utilisateur de choisir la résolution en mode plein écran
- **Mode fenêtré bordeless** : Offrir un mode fenêtré sans bordure comme alternative
- **Paramètres de configuration** : Sauvegarder la préférence de mode d'affichage dans un fichier de configuration
- **Support multi-écrans** : Permettre de choisir sur quel écran afficher le jeu en mode plein écran

## Références

- Bonnes pratiques : `bonne_pratique.md`
- Documentation Pygame : [pygame.display.set_mode](https://www.pygame.org/docs/ref/display.html#pygame.display.set_mode)
- Documentation Pygame : [pygame.display.Info](https://www.pygame.org/docs/ref/display.html#pygame.display.Info)
- Code existant : `src/moteur_jeu_presentation/main.py`

---

**Date de création** : 2024  
**Statut** : ✅ Implémenté

