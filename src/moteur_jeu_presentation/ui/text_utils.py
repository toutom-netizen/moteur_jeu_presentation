"""Utilitaires pour le rendu de texte dans l'interface."""

from __future__ import annotations

from typing import List, Optional

import pygame


def render_text(text: str, font: pygame.font.Font, color: tuple[int, int, int]) -> pygame.Surface:
    """Rend un texte avec la police et la couleur spécifiées.

    Args:
        text: Texte à rendre
        font: Police à utiliser
        color: Couleur du texte (RGB)

    Returns:
        Surface contenant le texte rendu
    """
    return font.render(text, True, color)


def wrap_text(text: str, max_width: int, font: pygame.font.Font) -> List[str]:
    """Divise un texte en plusieurs lignes pour respecter une largeur maximale.

    Args:
        text: Texte à diviser
        max_width: Largeur maximale en pixels
        font: Police à utiliser

    Returns:
        Liste des lignes de texte après word wrapping
    """
    if not text:
        return []

    # Si le texte tient dans la largeur, le retourner tel quel
    text_width = font.size(text)[0]
    if text_width <= max_width:
        return [text]

    # Diviser le texte en mots
    words = text.split(" ")
    if not words:
        return []

    wrapped_lines = []
    current_line = ""

    for word in words:
        # Tester si on peut ajouter le mot à la ligne actuelle
        test_line = current_line + (" " if current_line else "") + word
        test_width = font.size(test_line)[0]

        if test_width <= max_width:
            # Le mot tient, l'ajouter à la ligne actuelle
            current_line = test_line
        else:
            # Le mot ne tient pas
            if current_line:
                # Sauvegarder la ligne actuelle et commencer une nouvelle ligne
                wrapped_lines.append(current_line)
                current_line = word
            else:
                # Le mot seul est trop long, le couper caractère par caractère
                # (cas rare mais possible)
                if wrapped_lines:
                    # Ajouter le mot tronqué à la dernière ligne si possible
                    wrapped_lines.append(word[:len(word) // 2])
                    current_line = word[len(word) // 2:]
                else:
                    # Premier mot trop long, le diviser
                    chars_per_line = max(1, len(word) * max_width // font.size(word)[0])
                    for i in range(0, len(word), chars_per_line):
                        wrapped_lines.append(word[i:i + chars_per_line])
                    current_line = ""

    # Ajouter la dernière ligne si elle n'est pas vide
    if current_line:
        wrapped_lines.append(current_line)

    return wrapped_lines if wrapped_lines else [text]

