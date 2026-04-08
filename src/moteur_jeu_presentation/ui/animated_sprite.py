"""Module de gestion des sprites animés pour l'interface des statistiques."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import pygame

if TYPE_CHECKING:
    from ..entities.player import Player

logger = logging.getLogger(__name__)


class AnimatedSpriteManager:
    """Gestionnaire des sprites animés du joueur pour l'interface des statistiques."""

    def __init__(
        self,
        player: "Player",  # type: ignore
        sprite_scale: float = 4.0,
        rotation_speed: float = 0.5,
    ) -> None:
        """Initialise le gestionnaire de sprites animés.

        Args:
            player: Instance du joueur
            sprite_scale: Facteur d'échelle pour le sprite (défaut: 4.0 = 400%)
            rotation_speed: Durée en secondes pour afficher chaque sprite de la rotation (défaut: 0.5)
        """
        self.player = player
        self.sprite_scale = sprite_scale
        self.rotation_speed = rotation_speed
        
        # Animation de rotation
        self.rotation_timer: float = 0.0
        self.current_rotation_frame: int = 0
        
        # Cache des sprites
        self.player_sprites: List[pygame.Surface] = []
        self._scaled_sprite_cache: Dict[Tuple[int, float], pygame.Surface] = {}
        self._cached_level: int = -1
        self._cached_scale_factor: float = 1.0

    def extract_player_sprites(self) -> List[pygame.Surface]:
        """Extrait les 4 sprites du joueur (première colonne de toutes les lignes) depuis le sprite sheet walk.

        Returns:
            Liste des 4 sprites extraits et redimensionnés, ou liste vide en cas d'erreur
        """
        # Vérifier si les sprites sont déjà en cache pour le niveau actuel et la résolution actuelle
        current_level = self.player.level_manager.level
        current_scale_factor = 1.0
        # Invalider le cache si le niveau ou le facteur d'échelle a changé
        level_changed = self._cached_level != current_level
        if self.player_sprites and not level_changed and abs(self._cached_scale_factor - current_scale_factor) < 0.01:
            return self.player_sprites

        sprites: List[pygame.Surface] = []

        try:
            # Récupérer le chemin du sprite sheet
            walk_path = self.player.level_manager.get_asset_path("walk.png")

            # Charger le sprite sheet
            sprite_sheet = pygame.image.load(str(walk_path)).convert_alpha()

            sprite_width = self.player.sprite_width
            sprite_height = self.player.sprite_height
            col = 0  # Première colonne

            # Extraire les 4 sprites (lignes 0, 1, 2, 3)
            for row in range(4):
                x = col * sprite_width
                y = row * sprite_height

                # Créer une surface pour le sprite extrait
                sprite = pygame.Surface((sprite_width, sprite_height), pygame.SRCALPHA)
                sprite.blit(sprite_sheet, (0, 0), (x, y, sprite_width, sprite_height))

                # Redimensionner le sprite : 400% de base * facteur d'échelle de la résolution
                total_scale = self.sprite_scale * current_scale_factor
                scaled_sprite = self._scale_sprite(sprite, total_scale)
                sprites.append(scaled_sprite)

            # Mettre en cache
            self.player_sprites = sprites
            self._cached_level = current_level
            self._cached_scale_factor = current_scale_factor
            
            # Réinitialiser l'animation si le niveau a changé
            if level_changed:
                self.rotation_timer = 0.0
                self.current_rotation_frame = 0

            return sprites
        except Exception as e:
            logger.warning(f"Impossible d'extraire les sprites du joueur: {e}")
            return []

    def _scale_sprite(self, sprite: pygame.Surface, scale: float) -> pygame.Surface:
        """Redimensionne un sprite selon le facteur d'échelle.

        Utilise un cache pour éviter de recalculer le redimensionnement si le sprite et le scale sont identiques.

        Args:
            sprite: Sprite à redimensionner
            scale: Facteur d'échelle (ex: 2.5 pour 250%)

        Returns:
            Sprite redimensionné
        """
        # Utiliser l'ID du sprite (adresse mémoire) comme clé de cache
        # Note: Cela fonctionne car les sprites sont réutilisés entre les frames
        sprite_id = id(sprite)
        cache_key = (sprite_id, scale)
        
        if cache_key in self._scaled_sprite_cache:
            return self._scaled_sprite_cache[cache_key]
        
        # OPTIMISATION: Éviter smoothscale si scale == 1.0 ou si la taille est identique
        if scale == 1.0:
            # Pas besoin de redimensionner, utiliser directement le sprite
            scaled_sprite = sprite
        else:
            new_width = int(sprite.get_width() * scale)
            new_height = int(sprite.get_height() * scale)
            target_size = (new_width, new_height)
            if sprite.get_size() == target_size:
                # Pas besoin de redimensionner, utiliser directement le sprite
                scaled_sprite = sprite
            else:
                scaled_sprite = pygame.transform.smoothscale(sprite, target_size)
        
        # Mettre en cache (limiter la taille du cache pour éviter les fuites mémoire)
        if len(self._scaled_sprite_cache) > 50:
            # Nettoyer le cache si trop d'entrées (garder seulement les 25 plus récentes)
            keys_to_remove = list(self._scaled_sprite_cache.keys())[:-25]
            for key in keys_to_remove:
                del self._scaled_sprite_cache[key]
        
        self._scaled_sprite_cache[cache_key] = scaled_sprite
        return scaled_sprite

    def update_rotation(self, dt: float) -> None:
        """Met à jour l'animation de rotation selon le delta time.

        Args:
            dt: Delta time en secondes
        """
        # Vérifier si le niveau a changé et réextraire les sprites si nécessaire
        current_level = self.player.level_manager.level
        level_changed = self._cached_level != current_level
        if not self.player_sprites or level_changed:
            # Réinitialiser l'animation lors du changement de niveau
            if level_changed:
                self.rotation_timer = 0.0
                self.current_rotation_frame = 0
            self.extract_player_sprites()

        if not self.player_sprites:
            return

        # Incrémenter le timer
        self.rotation_timer += dt

        # Vérifier si on doit passer au sprite suivant
        if self.rotation_timer >= self.rotation_speed:
            self.rotation_timer = 0.0
            self.current_rotation_frame = (self.current_rotation_frame + 1) % len(self.player_sprites)

    def get_current_sprite(self) -> Optional[pygame.Surface]:
        """Récupère le sprite actuel selon l'animation de rotation.

        Returns:
            Le sprite actuel, ou None si aucun sprite n'est disponible
        """
        # Vérifier si le niveau a changé et réextraire les sprites si nécessaire
        current_level = self.player.level_manager.level
        level_changed = self._cached_level != current_level
        if not self.player_sprites or level_changed:
            # Réinitialiser l'animation lors du changement de niveau
            if level_changed:
                self.rotation_timer = 0.0
                self.current_rotation_frame = 0
            self.extract_player_sprites()
        
        if not self.player_sprites:
            return None
        
        # Protection supplémentaire : s'assurer que l'index est valide
        if self.current_rotation_frame >= len(self.player_sprites):
            self.current_rotation_frame = 0
        
        return self.player_sprites[self.current_rotation_frame]

    def invalidate_cache(self) -> None:
        """Invalide le cache des sprites."""
        self.player_sprites = []
        self._cached_level = -1
        self._cached_scale_factor = 1.0
        self.rotation_timer = 0.0
        self.current_rotation_frame = 0
        # Invalider aussi le cache de redimensionnement pour éviter d'utiliser d'anciens sprites
        self._scaled_sprite_cache.clear()

