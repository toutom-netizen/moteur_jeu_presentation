"""Module de gestion de l'écran d'accueil."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, Tuple

import pygame


# Coordonnées du bouton START dans l'image originale (en pourcentage)
# Ajuster ces valeurs si l'image change
# Pour trouver les bonnes valeurs:
# 1. Activer le mode debug (debug=True)
# 2. Lancer le jeu et voir où se trouve le rectangle rouge
# 3. Ajuster les pourcentages jusqu'à ce que le rectangle corresponde au bouton START
# 4. Ou utiliser le script scripts/detect_start_button.py
START_BUTTON_X_PERCENT = 0.35  # 35% depuis la gauche (environ centre)
START_BUTTON_Y_PERCENT = 0.66  # 80% depuis le haut (bas de l'écran)
START_BUTTON_WIDTH_PERCENT = 0.272  # 30% de la largeur de l'image
START_BUTTON_HEIGHT_PERCENT = 0.16  # 10% de la hauteur de l'image

# Constantes de couleur pour le fond
BACKGROUND_COLOR_DEFAULT = (244, 245, 235)  # RGB(74, 149, 172) / #4a95ac
BACKGROUND_COLOR_HOVER = (255, 0, 0)       # Rouge


class SplashScreen:
    """Gère l'affichage et l'interaction de l'écran d'accueil."""
    
    def __init__(
        self,
        image_path: Path,
        screen_width: int,
        screen_height: int,
        debug: bool = False,
    ) -> None:
        """Initialise l'écran d'accueil.
        
        Args:
            image_path: Chemin vers l'image d'introduction
            screen_width: Largeur de l'écran de rendu
            screen_height: Hauteur de l'écran de rendu
            debug: Si True, affiche un rectangle rouge pour visualiser la zone du bouton START
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.debug = debug
        
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
        self.background_color = BACKGROUND_COLOR_DEFAULT
        
        # Calculer la mise à l'échelle et les coordonnées
        self._calculate_scaled_image()
        self._update_button_rect()
        
        # Afficher les informations de debug si activé
        if self.debug:
            image_width = self.image.get_width()
            image_height = self.image.get_height()
            print(f"Debug SplashScreen:")
            print(f"  Image: {image_width}x{image_height} pixels")
            print(f"  Surface interne: {self.screen_width}x{self.screen_height} pixels")
            if self.start_button_rect:
                print(f"  Bouton START rect: {self.start_button_rect}")
                print(f"  Coordonnées en %: X={START_BUTTON_X_PERCENT:.2%}, Y={START_BUTTON_Y_PERCENT:.2%}, W={START_BUTTON_WIDTH_PERCENT:.2%}, H={START_BUTTON_HEIGHT_PERCENT:.2%}")
    
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
        
        # OPTIMISATION: Éviter smoothscale si scale == 1.0 ou si la taille est identique
        target_size = (new_width, new_height)
        if scale == 1.0 or self.image.get_size() == target_size:
            # Pas besoin de redimensionner, utiliser directement l'image
            self.scaled_image = self.image
        else:
            self.scaled_image = pygame.transform.smoothscale(self.image, target_size)
        
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
    
    def handle_event(
        self,
        event: pygame.event.Event,
        convert_mouse_pos: Optional[Callable[[Tuple[int, int]], Tuple[int, int]]] = None,
    ) -> None:
        """Gère les événements de l'écran d'accueil.
        
        Args:
            event: Événement pygame à traiter
            convert_mouse_pos: Fonction optionnelle pour convertir les coordonnées de la souris
                              depuis les coordonnées d'affichage vers les coordonnées internes
        """
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
                if self.debug:
                    print(f"Debug: Clic à {event.pos} (écran) -> {mouse_pos} (interne)")
                    if self.start_button_rect:
                        print(f"Debug: Bouton rect = {self.start_button_rect}")
                        print(f"Debug: Collision = {self.start_button_rect.collidepoint(mouse_pos)}")
                if self.start_button_rect and self.start_button_rect.collidepoint(mouse_pos):
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
            self.background_color = BACKGROUND_COLOR_HOVER
        else:
            self.background_color = BACKGROUND_COLOR_DEFAULT
    
    def draw(self, surface: pygame.Surface) -> None:
        """Dessine l'écran d'accueil.
        
        Args:
            surface: Surface pygame sur laquelle dessiner
        """
        # Remplir l'écran avec la couleur de fond (RGB(74, 149, 172) par défaut, rouge au survol)
        surface.fill(self.background_color)
        
        # Dessiner l'image mise à l'échelle par-dessus le fond
        if self.scaled_image and self.image_rect:
            surface.blit(self.scaled_image, self.image_rect)
        
        # Optionnel : Dessiner un rectangle de debug pour visualiser la zone du bouton START
        if self.debug and self.start_button_rect:
            pygame.draw.rect(surface, (255, 0, 0), self.start_button_rect, 2)

