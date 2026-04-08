"""Module de gestion de la boîte de confirmation de quitter."""

from __future__ import annotations

from typing import Callable, Optional, Tuple

import pygame


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
        
        # Stocker la hauteur de la zone des boutons pour le rendu
        self.button_area_height = button_area_height
        
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
        # Centrer le texte verticalement dans la zone de texte (au-dessus des boutons)
        text_y = self.dialog_y + (self.dialog_height - self.button_area_height) // 2
        text_rect = text_surface.get_rect(center=(
            self.dialog_x + self.dialog_width // 2,
            text_y,
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
