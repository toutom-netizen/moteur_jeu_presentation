"""Module de gestion du système de particules global."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pygame

from .effect import ParticleEffect, ParticleEffectConfig


class ParticleSystem:
    """Gestionnaire principal du moteur de particules."""

    def __init__(self) -> None:
        """Initialise le système de particules."""
        self.effects: List[ParticleEffect] = []
        # OPTIMISATION: Cache amélioré avec clé composite (size, r, g, b, opacity)
        # Limite de 500 entrées pour éviter les fuites mémoire
        self._particle_surface_cache: Dict[Tuple[int, int, int, int, int], pygame.Surface] = {}
        self._cache_max_size = 500
    
    def create_effect(
        self,
        x: float,
        y: float,
        config: ParticleEffectConfig,
        effect_id: Optional[str] = None,
        spawn_area: Optional[Dict[str, float]] = None,
        screen_space: bool = False,
    ) -> ParticleEffect:
        """Crée et ajoute un nouvel effet de particules.
        
        Args:
            x: Position horizontale de départ (coordonnées monde). Utilisé comme position de référence si spawn_area est None, ou comme coin supérieur gauche de la zone si spawn_area est spécifié
            y: Position verticale de départ (coordonnées monde). Utilisé comme position de référence si spawn_area est None, ou comme coin supérieur gauche de la zone si spawn_area est spécifié
            config: Configuration de l'effet
            effect_id: Identifiant optionnel pour l'effet
            spawn_area: Zone de génération des particules (optionnel). Si spécifié, les particules sont générées aléatoirement dans cette zone. Format: {"x_min": float, "x_max": float, "y_min": float, "y_max": float} (en coordonnées monde). Si None, toutes les particules sont générées à la position (x, y)
            
        Returns:
            L'effet créé
        """
        effect = ParticleEffect(x, y, config, effect_id, spawn_area, screen_space=screen_space)
        self.effects.append(effect)
        return effect
    
    def update(self, dt: float, camera_x: float = 0.0, screen_width: int = 1920, screen_height: int = 1080, margin: int = 200) -> None:
        """Met à jour tous les effets actifs.
        
        OPTIMISATION: Ne met à jour que les effets visibles ou proches de l'écran.
        Les effets hors écran ne sont pas mis à jour pour économiser les calculs.
        
        Args:
            dt: Delta time en secondes
            camera_x: Position horizontale de la caméra (pour le culling, optionnel)
            screen_width: Largeur de l'écran pour le culling (défaut: 1920)
            screen_height: Hauteur de l'écran pour le culling (défaut: 1080)
            margin: Marge en pixels pour le culling hors écran (défaut: 200)
        """
        for effect in list(self.effects):
            # OPTIMISATION: Ne mettre à jour que les effets visibles ou proches de l'écran
            if self._is_effect_visible(effect, camera_x, screen_width, screen_height, margin):
                effect_camera_x = 0.0 if getattr(effect, "screen_space", False) else camera_x
                effect.update(dt, effect_camera_x, screen_width, screen_height, margin)
            # Si l'effet est hors écran, on ne le met pas à jour pour économiser les calculs
            # Les particules continueront d'exister mais ne bougeront pas jusqu'à ce qu'elles reviennent à l'écran
            # ou que l'effet soit supprimé s'il n'a plus de particules
            
            if not effect.is_active:
                self.effects.remove(effect)
    
    def _is_effect_visible(self, effect: ParticleEffect, camera_x: float, screen_width: int, screen_height: int, margin: int) -> bool:
        """Vérifie si un effet est visible ou proche de l'écran.
        
        OPTIMISATION: Pré-calculer is_screen_space et effect_camera_x pour éviter les appels répétés à getattr.
        
        Args:
            effect: L'effet à vérifier
            camera_x: Position horizontale de la caméra
            screen_width: Largeur de l'écran
            screen_height: Hauteur de l'écran
            margin: Marge en pixels
            
        Returns:
            True si l'effet est visible ou proche de l'écran, False sinon
        """
        # OPTIMISATION: Pré-calculer is_screen_space une seule fois
        is_screen_space = effect.screen_space if hasattr(effect, "screen_space") else False
        effect_camera_x = 0.0 if is_screen_space else camera_x
        
        # Si l'effet n'a pas encore de particules mais est en train d'en générer, on le considère comme visible
        if len(effect.particles) == 0:
            # Vérifier si la position de l'effet est visible
            effect_x_screen = effect.x - effect_camera_x
            effect_y = effect.y
            
            return not (effect_x_screen < -margin or 
                       effect_x_screen > screen_width + margin or
                       effect_y < -margin or 
                       effect_y > screen_height + margin)
        
        # OPTIMISATION: Calculer les bornes de l'effet en une seule passe
        # Utiliser une boucle unique pour calculer min/max simultanément
        particles = effect.particles
        if not particles:
            return False
        
        min_x = particles[0].x
        max_x = particles[0].x
        min_y = particles[0].y
        max_y = particles[0].y
        
        for p in particles[1:]:
            if p.x < min_x:
                min_x = p.x
            elif p.x > max_x:
                max_x = p.x
            if p.y < min_y:
                min_y = p.y
            elif p.y > max_y:
                max_y = p.y
        
        # Convertir en coordonnées écran (effect_camera_x déjà pré-calculé)
        min_x_screen = min_x - effect_camera_x
        max_x_screen = max_x - effect_camera_x
        
        # Vérifier si l'effet est visible (avec marge)
        return not (max_x_screen < -margin or 
                   min_x_screen > screen_width + margin or
                   max_y < -margin or 
                   min_y > screen_height + margin)
    
    def get_display_commands(
        self,
        camera_x: float,
        screen_width: int = 1920,
        screen_height: int = 1080,
        margin: int = 100,
        screen_space_only: Optional[bool] = None,
    ) -> List[Tuple[pygame.Surface, Tuple[int, int]]]:
        """Génère les commandes de dessin pour tous les effets actifs.

        OPTIMISATION: Cache des surfaces de particules et culling hors écran.

        Args:
            camera_x: Position horizontale de la caméra (pour ajuster les coordonnées)
            screen_width: Largeur de l'écran pour le culling (défaut: 1920)
            screen_height: Hauteur de l'écran pour le culling (défaut: 1080)
            margin: Marge en pixels pour le culling hors écran (défaut: 100)

        Returns:
            Liste des commandes de dessin (surface, position)
        """
        commands: List[Tuple[pygame.Surface, Tuple[int, int]]] = []

        for effect in self.effects:
            # OPTIMISATION: Pré-calculer is_screen_space une fois par effet au lieu d'utiliser getattr
            is_screen_space = effect.screen_space if hasattr(effect, "screen_space") else False
            if screen_space_only is True and not is_screen_space:
                continue
            if screen_space_only is False and is_screen_space:
                continue

            # OPTIMISATION: Pré-calculer les valeurs constantes par effet
            config = effect.config
            size_shrink = config.size_shrink
            fade_out = config.fade_out
            camera_x_for_particles = 0.0 if is_screen_space else camera_x

            for particle in effect.particles:
                # OPTIMISATION: Calculer la taille actuelle de la particule (peut diminuer si size_shrink est activé)
                current_size = particle.get_size(size_shrink)
                if current_size <= 0:
                    continue  # Ignorer les particules qui ont rétréci à 0

                # OPTIMISATION: Calculer l'opacité si fade_out est activé (pré-calculé)
                if fade_out:
                    opacity = particle.get_opacity()
                else:
                    opacity = 255

                # OPTIMISATION: Culling des particules hors écran
                # Calculer la position à l'écran (camera_x_for_particles pré-calculé)
                particle_x = int(particle.x if is_screen_space else (particle.x - camera_x_for_particles))
                particle_y = int(particle.y)

                # Vérifier si la particule est visible (avec marge pour éviter le culling trop agressif)
                if (particle_x + current_size < -margin or
                    particle_x > screen_width + margin or
                    particle_y + current_size < -margin or
                    particle_y > screen_height + margin):
                    continue  # Particule hors écran, ignorer

                # OPTIMISATION: Cache des surfaces de particules
                # Clé composite incluant taille et couleur/opacité pour maximiser la réutilisation
                r, g, b = particle.color
                cache_key = (current_size, r, g, b, opacity)

                # Vérifier le cache
                if cache_key in self._particle_surface_cache:
                    particle_surface = self._particle_surface_cache[cache_key]
                else:
                    # OPTIMISATION: Pré-calculer current_size // 2 une seule fois
                    half_size = current_size // 2
                    # Créer une nouvelle surface si pas en cache
                    particle_surface = pygame.Surface((current_size, current_size), pygame.SRCALPHA)
                    color_with_alpha = (r, g, b, opacity)
                    pygame.draw.circle(
                        particle_surface,
                        color_with_alpha,
                        (half_size, half_size),
                        half_size
                    )

                    # Ajouter au cache
                    self._particle_surface_cache[cache_key] = particle_surface

                    # OPTIMISATION: Gestion de la taille du cache pour éviter les fuites mémoire
                    if len(self._particle_surface_cache) > self._cache_max_size:
                        # Supprimer une entrée arbitraire (LRU approximatif)
                        oldest_key = next(iter(self._particle_surface_cache))
                        del self._particle_surface_cache[oldest_key]

                commands.append((particle_surface, (particle_x, particle_y)))

        return commands

    def get_display_commands_split(
        self,
        camera_x: float,
        screen_width: int = 1920,
        screen_height: int = 1080,
        margin: int = 100,
    ) -> Tuple[
        List[Tuple[pygame.Surface, Tuple[int, int]]],
        List[Tuple[pygame.Surface, Tuple[int, int]]],
    ]:
        """Génère en une seule passe les commandes de dessin séparées monde / overlay.

        But: éviter d'itérer 2 fois sur les particules par frame quand on doit dessiner:
        - particules "monde" (soustraites à camera_x, zoomées avec la scène)
        - particules "overlay" (screen-space, dessinées après le zoom)
        """
        world_commands: List[Tuple[pygame.Surface, Tuple[int, int]]] = []
        overlay_commands: List[Tuple[pygame.Surface, Tuple[int, int]]] = []

        for effect in self.effects:
            # OPTIMISATION: Pré-calculer is_screen_space une fois par effet
            is_screen_space = effect.screen_space if hasattr(effect, "screen_space") else False

            # OPTIMISATION: Pré-calculer les valeurs constantes par effet
            config = effect.config
            size_shrink = config.size_shrink
            fade_out = config.fade_out
            camera_x_for_particles = 0.0 if is_screen_space else camera_x

            for particle in effect.particles:
                # OPTIMISATION: Calculer la taille actuelle de la particule (size_shrink pré-calculé)
                current_size = particle.get_size(size_shrink)
                if current_size <= 0:
                    continue  # Ignorer les particules qui ont rétréci à 0

                # OPTIMISATION: Calculer l'opacité si fade_out est activé (fade_out pré-calculé)
                if fade_out:
                    opacity = particle.get_opacity()
                else:
                    opacity = 255

                # OPTIMISATION: Position à l'écran (camera_x_for_particles pré-calculé)
                particle_x = int(particle.x if is_screen_space else (particle.x - camera_x_for_particles))
                particle_y = int(particle.y)

                # Culling hors écran
                if (
                    particle_x + current_size < -margin
                    or particle_x > screen_width + margin
                    or particle_y + current_size < -margin
                    or particle_y > screen_height + margin
                ):
                    continue

                # Cache des surfaces de particules
                r, g, b = particle.color
                cache_key = (current_size, r, g, b, opacity)
                if cache_key in self._particle_surface_cache:
                    particle_surface = self._particle_surface_cache[cache_key]
                else:
                    # OPTIMISATION: Pré-calculer current_size // 2 une seule fois
                    half_size = current_size // 2
                    particle_surface = pygame.Surface((current_size, current_size), pygame.SRCALPHA)
                    color_with_alpha = (r, g, b, opacity)
                    pygame.draw.circle(
                        particle_surface,
                        color_with_alpha,
                        (half_size, half_size),
                        half_size,
                    )
                    self._particle_surface_cache[cache_key] = particle_surface

                    if len(self._particle_surface_cache) > self._cache_max_size:
                        oldest_key = next(iter(self._particle_surface_cache))
                        del self._particle_surface_cache[oldest_key]

                cmd = (particle_surface, (particle_x, particle_y))
                if is_screen_space:
                    overlay_commands.append(cmd)
                else:
                    world_commands.append(cmd)

        return world_commands, overlay_commands
    
    def clear_all(self) -> None:
        """Supprime tous les effets actifs."""
        self.effects.clear()
    
    def remove_effect(self, effect_id: str) -> bool:
        """Supprime un effet par son identifiant.
        
        Args:
            effect_id: Identifiant de l'effet à supprimer
            
        Returns:
            True si l'effet a été trouvé et supprimé, False sinon
        """
        for effect in list(self.effects):
            if effect.effect_id == effect_id:
                self.effects.remove(effect)
                return True
        return False

