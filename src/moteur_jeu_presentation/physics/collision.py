"""Module de gestion des collisions entre le personnage et les tiles."""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Optional, Tuple

import pygame

if TYPE_CHECKING:
    from ..rendering.parallax import ParallaxSystem
    from ..entities.entity import Entity
else:
    # Import réel pour éviter les imports circulaires
    from ..entities.entity import Entity

logger = logging.getLogger("moteur_jeu_presentation.collision")


class CollisionSystem:
    """Système de gestion des collisions entre le personnage et les tiles."""

    def __init__(
        self,
        parallax_system: ParallaxSystem,
        screen_width: int,
        screen_height: int,
    ) -> None:
        """Initialise le système de collisions.

        Args:
            parallax_system: Système de parallaxe contenant les couches
            screen_width: Largeur de l'écran
            screen_height: Hauteur de l'écran
        """
        self.parallax_system = parallax_system
        self.screen_width = screen_width
        self.screen_height = screen_height
        self._collision_layers: list = []  # Mise en cache des couches de depth 2
        self._solid_rects_cache: dict[str, list[pygame.Rect]] = {}  # Cache des rectangles par layer
        # Gestion des plateformes mobiles : {layer_id: {'layer': Layer, 'passengers': set[Entity], 'frame_delta': (dx, dy)}}
        self.moving_platforms: dict[str, dict] = {}

    def _get_solid_layers(self) -> list:
        """Récupère toutes les couches de depth 2 (tiles solides).
        
        Exclut les layers masquées (opacité = 0 ou attribut is_hidden = True)
        et les layers avec is_background = True ou is_foreground = True pour éviter de vérifier les collisions
        avec des sprites invisibles ou des décors non solides.

        Returns:
            Liste des couches de depth 2 qui ne sont pas masquées et qui sont solides
        """
        if not self._collision_layers:
            # Filtrer les layers de depth 2 qui ne sont pas masquées et qui sont solides
            self._collision_layers = [
                layer for layer in self.parallax_system._layers
                if layer.depth == 2
                and (not hasattr(layer, 'alpha') or layer.alpha > 0)
                and (not hasattr(layer, 'is_hidden') or not layer.is_hidden)
                and not layer.is_background
                and not layer.is_foreground
            ]
        return self._collision_layers

    def _get_climbable_layers(self) -> list:
        """Récupère toutes les couches grimpables (depth 2 avec is_background = true et is_climbable = true).
        
        Returns:
            Liste des couches grimpables
        """
        return [
            layer for layer in self.parallax_system._layers
            if layer.depth == 2
            and (not hasattr(layer, 'alpha') or layer.alpha > 0)
            and (not hasattr(layer, 'is_hidden') or not layer.is_hidden)
            and hasattr(layer, 'is_background') and layer.is_background
            and hasattr(layer, 'is_climbable') and layer.is_climbable
        ]

    def get_climbable_rects(self, camera_x: float) -> list[pygame.Rect]:
        """Récupère tous les rectangles de collision des blocs grimpables visibles.
        
        Args:
            camera_x: Position horizontale de la caméra
            
        Returns:
            Liste des rectangles de collision des blocs grimpables
        """
        climbable_layers = self._get_climbable_layers()
        climbable_rects: list[pygame.Rect] = []
        
        for layer in climbable_layers:
            # Utiliser la même logique que get_collision_rects() pour extraire les rectangles
            # mais uniquement pour les couches grimpables
            solid_rects = self._extract_solid_rects_from_surface(
                layer.surface, layer.name, tile_size=64
            )
            
            layer_width = layer.surface.get_width()
            infinite_offset = getattr(layer, "infinite_offset", 0.0)
            
            if layer.repeat:
                # Couche répétable : créer des rectangles pour chaque répétition visible
                effective_width = layer_width + infinite_offset
                if effective_width <= 0:
                    effective_width = layer_width
                
                num_repeats = math.ceil(self.screen_width / effective_width) + 2
                start_offset = -(layer.offset_x % effective_width)
                world_x_base = getattr(layer, "world_x_offset", 0.0)
                
                for i in range(num_repeats):
                    screen_x = start_offset + (i * effective_width)
                    # Convertir en coordonnées du monde
                    world_x = world_x_base + screen_x + camera_x
                    
                    # Vérifier si visible (avec marge)
                    if (
                        world_x + layer_width >= camera_x - 100
                        and world_x <= camera_x + self.screen_width + 100
                    ):
                        for rect in solid_rects:
                            # Prendre en compte world_y_offset pour les plateformes mobiles
                            world_y_offset = getattr(layer, 'world_y_offset', 0.0)
                            world_rect = pygame.Rect(
                                round(world_x + rect.x),
                                round(rect.y + world_y_offset),
                                round(rect.width),
                                round(rect.height),
                            )
                            climbable_rects.append(world_rect)
            else:
                # Couche non répétable
                world_x_base = getattr(layer, "world_x_offset", 0.0)
                
                # Vérifier si visible (avec marge)
                if world_x_base + layer_width >= camera_x - 100 and world_x_base <= camera_x + self.screen_width + 100:
                    for rect in solid_rects:
                        # Prendre en compte world_y_offset pour les plateformes mobiles
                        world_y_offset = getattr(layer, 'world_y_offset', 0.0)
                        world_rect = pygame.Rect(
                            round(world_x_base + rect.x),
                            round(rect.y + world_y_offset),
                            round(rect.width),
                            round(rect.height),
                        )
                        climbable_rects.append(world_rect)
        
        return climbable_rects

    def check_climbable_collision(self, player_rect: pygame.Rect, camera_x: float, player: Entity) -> bool:
        """Vérifie si le personnage est en collision avec un bloc grimpable.
        
        Met à jour player.is_on_climbable en fonction du résultat.
        
        Args:
            player_rect: Rectangle de collision du personnage dans l'espace du monde
            camera_x: Position horizontale de la caméra
            player: Référence au personnage pour mettre à jour is_on_climbable
            
        Returns:
            True si le personnage est en collision avec un bloc grimpable, False sinon
        """
        climbable_rects = self.get_climbable_rects(camera_x)
        
        # Vérifier si le joueur intersecte avec un bloc grimpable
        is_on_climbable = False
        for climbable_rect in climbable_rects:
            if player_rect.colliderect(climbable_rect):
                is_on_climbable = True
                break
        
        # Mettre à jour la propriété du joueur
        if hasattr(player, 'is_on_climbable'):
            player.is_on_climbable = is_on_climbable
        
        return is_on_climbable

    def get_collision_rects(self, camera_x: float) -> list[pygame.Rect]:
        """Récupère tous les rectangles de collision des tiles de depth 2 visibles.

        Args:
            camera_x: Position horizontale de la caméra

        Returns:
            Liste des rectangles de collision dans l'espace du monde
        """
        collision_rects: list[pygame.Rect] = []
        solid_layers = self._get_solid_layers()

        for layer in solid_layers:
            layer_width = layer.surface.get_width()
            layer_height = layer.surface.get_height()

            # Pour depth 2, scroll_speed = 1.0, donc les tiles sont fixes dans l'espace du monde
            # La position dans l'espace du monde est: world_x = screen_x + camera_x
            # Mais layer.offset_x = camera_x * scroll_speed = camera_x (pour depth 2)

            # Analyser la surface pour trouver les zones solides (pixels non-transparents)
            # Utiliser la taille de sprite du niveau (64x64 par défaut)
            # Le cache évite de recalculer les rectangles à chaque frame
            solid_rects = self._extract_solid_rects_from_surface(layer.surface, layer.name, tile_size=64)

            # Pour depth 2, scroll_speed = 1.0, donc les tiles sont fixes dans l'espace du monde
            # layer.offset_x = camera_x * scroll_speed = camera_x
            # À l'écran, screen_x = -layer.offset_x = -camera_x
            # Dans l'espace du monde, world_x_base = screen_x + camera_x = -camera_x + camera_x = 0
            # Donc la surface commence toujours à world_x = 0 dans l'espace du monde

            if layer.repeat:
                # Couche répétable : créer des rectangles pour chaque répétition visible
                infinite_offset = getattr(layer, "infinite_offset", 0.0)
                effective_width = layer_width + infinite_offset
                if effective_width <= 0:
                    effective_width = layer_width

                num_repeats = math.ceil(self.screen_width / effective_width) + 2
                start_offset = -(layer.offset_x % effective_width)
                base_world_offset = getattr(layer, "world_x_offset", 0.0)

                for i in range(num_repeats):
                    screen_x = start_offset + (i * effective_width)
                    # Convertir en coordonnées du monde
                    world_x_base = base_world_offset + screen_x + camera_x

                    # Vérifier si visible (avec marge)
                    if (
                        world_x_base + layer_width >= camera_x - 100
                        and world_x_base <= camera_x + self.screen_width + 100
                    ):
                        # Ajouter tous les rectangles solides de cette répétition
                        for solid_rect in solid_rects:
                            # Utiliser round() pour un arrondi cohérent avec le rectangle du joueur
                            # Prendre en compte world_y_offset pour les plateformes mobiles
                            world_y_offset = getattr(layer, 'world_y_offset', 0.0)
                            collision_rect = pygame.Rect(
                                round(world_x_base + solid_rect.x),
                                round(solid_rect.y + world_y_offset),
                                round(solid_rect.width),
                                round(solid_rect.height),
                            )
                            collision_rects.append(collision_rect)
            else:
                # Couche non répétable : la surface commence à world_x = layer.world_x_offset
                # (peut être négatif pour les sprites avec x_offset négatif)
                world_x_base = layer.world_x_offset if hasattr(layer, 'world_x_offset') else 0.0

                # Vérifier si visible (avec marge)
                if world_x_base + layer_width >= camera_x - 100 and world_x_base <= camera_x + self.screen_width + 100:
                    # Ajouter tous les rectangles solides
                    for solid_rect in solid_rects:
                        # Utiliser round() pour un arrondi cohérent avec le rectangle du joueur
                        # Prendre en compte world_y_offset pour les plateformes mobiles
                        world_y_offset = getattr(layer, 'world_y_offset', 0.0)
                        collision_rect = pygame.Rect(
                            round(world_x_base + solid_rect.x),
                            round(solid_rect.y + world_y_offset),
                            round(solid_rect.width),
                            round(solid_rect.height),
                        )
                        collision_rects.append(collision_rect)

        return collision_rects

    def _extract_solid_rects_from_surface(
        self, surface: pygame.Surface, layer_name: str, tile_size: int = 64
    ) -> list[pygame.Rect]:
        """Extrait les rectangles de collision depuis une surface.

        Utilise un cache pour éviter de recalculer les rectangles à chaque frame.
        Trouve la position exacte des sprites (pas alignée sur des multiples de tile_size)
        pour éviter les décalages visuels.

        Args:
            surface: Surface à analyser
            layer_name: Nom de la couche (pour le cache)
            tile_size: Taille des tuiles de collision (par défaut: 64)

        Returns:
            Liste des rectangles de collision (dans l'espace de la surface)
        """
        # Vérifier le cache
        if layer_name in self._solid_rects_cache:
            return self._solid_rects_cache[layer_name]

        solid_rects: list[pygame.Rect] = []
        width = surface.get_width()
        height = surface.get_height()

        # 1) Tentative : utiliser un mask pour récupérer des bounding boxes précises
        try:
            mask = pygame.mask.from_surface(surface)
            mask_rects = mask.get_bounding_rects()
            if mask_rects:
                solid_rects = [pygame.Rect(rect) for rect in mask_rects]
        except pygame.error:
            # Fallback vers l'approche échantillonnée si la création du mask échoue
            mask_rects = []

        # 2) Fallback : si le mask n'a rien trouvé (surface vide) ou a échoué,
        #    revenir à l'approche échantillonnée par colonnes pour conserver le comportement historique.
        if not solid_rects:
            sample_step = 8

            for x in range(0, width, tile_size):
                # Trouver la première position y où il y a des pixels solides dans cette colonne
                first_solid_y = None
                first_solid_x = None
                last_solid_x = None

                # Échantillonner verticalement pour trouver rapidement la zone
                for y in range(0, height, sample_step):
                    # Vérifier quelques pixels dans cette colonne à cette hauteur
                    has_solid = False
                    check_x_positions = [
                        x,
                        min(x + tile_size // 2, width - 1),
                        min(x + tile_size - 1, width - 1),
                    ]

                    for check_x in check_x_positions:
                        try:
                            color = surface.get_at((check_x, y))
                            if len(color) >= 4 and color[3] > 0:  # Pixel non-transparent
                                has_solid = True
                                break
                        except IndexError:
                            continue

                    if has_solid:
                        # Une fois qu'on a trouvé une zone avec des pixels, chercher plus précisément
                        # le premier pixel solide en remontant depuis cette position
                        search_start = max(0, y - sample_step)
                        for fine_y in range(search_start, y + 1):
                            for check_x in range(x, min(x + tile_size, width)):
                                try:
                                    color = surface.get_at((check_x, fine_y))
                                    if len(color) >= 4 and color[3] > 0:
                                        first_solid_y = fine_y
                                        break
                                except IndexError:
                                    continue
                            if first_solid_y is not None:
                                break
                        break

                if first_solid_y is None:
                    continue

                # Déterminer la largeur exacte occupée par des pixels non-transparents dans cette colonne
                x_start = x
                x_end = min(x + tile_size, width)
                for fine_x in range(x_start, x_end):
                    for fine_y in range(first_solid_y, min(first_solid_y + tile_size, height)):
                        try:
                            color = surface.get_at((fine_x, fine_y))
                            if len(color) >= 4 and color[3] > 0:
                                if first_solid_x is None:
                                    first_solid_x = fine_x
                                last_solid_x = fine_x
                                break
                        except IndexError:
                            continue

                if first_solid_x is None:
                    first_solid_x = x
                if last_solid_x is None:
                    last_solid_x = x_end - 1

                rect_width = max(1, (last_solid_x - first_solid_x) + 1)
                rect_height = min(tile_size, height - first_solid_y)

                tile_rect = pygame.Rect(
                    first_solid_x,
                    first_solid_y,
                    rect_width,
                    rect_height,
                )
                solid_rects.append(tile_rect)

        # Mettre en cache le résultat
        self._solid_rects_cache[layer_name] = solid_rects
        return solid_rects

    def _has_solid_pixels(self, surface: pygame.Surface, rect: pygame.Rect) -> bool:
        """Vérifie si une zone rectangulaire contient des pixels non-transparents.

        Args:
            surface: Surface à analyser
            rect: Rectangle à vérifier

        Returns:
            True si la zone contient des pixels non-transparents, False sinon
        """
        # Échantillonner quelques pixels pour optimiser
        # On vérifie les coins et le centre
        check_points = [
            (rect.left, rect.top),
            (rect.right - 1, rect.top),
            (rect.left, rect.bottom - 1),
            (rect.right - 1, rect.bottom - 1),
            (rect.centerx, rect.centery),
        ]

        for x, y in check_points:
            if 0 <= x < surface.get_width() and 0 <= y < surface.get_height():
                try:
                    color = surface.get_at((x, y))
                    # Vérifier si le pixel n'est pas transparent (alpha > 0)
                    if len(color) >= 4 and color[3] > 0:
                        return True
                except IndexError:
                    continue

        return False

    def remove_layer_collisions(self, layer_name: str) -> None:
        """Supprime les rectangles de collision d'une layer du cache.
        
        Utilisé par le système d'événements lors du masquage de sprites
        pour retirer les collisions d'une layer qui n'est plus visible.
        
        Args:
            layer_name: Nom de la layer dont les collisions doivent être supprimées
        """
        if layer_name in self._solid_rects_cache:
            del self._solid_rects_cache[layer_name]

    def remove_layer_from_collisions(self, layer) -> None:
        """Retire une layer de la liste des layers de collision.
        
        Utilisé par le système d'événements lors du masquage de sprites
        pour exclure une layer des détections de collision futures.
        
        Args:
            layer: La layer à retirer des collisions
        """
        # Réinitialiser le cache pour forcer un recalcul
        self._collision_layers = []
        # La prochaine fois que _get_solid_layers() sera appelée,
        # elle recalculera la liste sans la layer masquée

    def restore_layer_collisions(self, layer) -> None:
        """Restaure les rectangles de collision d'une layer dans le cache.
        
        Utilisé par le système d'événements lors de l'affichage de sprites
        pour réintégrer les collisions d'une layer qui redevient visible.
        
        Args:
            layer: La layer dont les collisions doivent être restaurées
        """
        # Recalculer les rectangles de collision (même logique que lors du chargement)
        solid_rects = self._extract_solid_rects_from_surface(layer.surface, layer.name, tile_size=64)
        self._solid_rects_cache[layer.name] = solid_rects

    def add_layer_to_collisions(self, layer) -> None:
        """Réintègre une layer dans la liste des layers de collision.
        
        Utilisé par le système d'événements lors de l'affichage de sprites
        pour inclure une layer dans les détections de collision futures.
        
        Args:
            layer: La layer à réintégrer dans les collisions
        """
        # Réinitialiser le cache pour forcer un recalcul
        self._collision_layers = []
        # La prochaine fois que _get_solid_layers() sera appelée,
        # elle recalculera la liste avec la layer restaurée

    def check_collision(
        self, player_rect: pygame.Rect, camera_x: float
    ) -> Optional[pygame.Rect]:
        """Vérifie si le personnage entre en collision avec un tile.

        Args:
            player_rect: Rectangle de collision du personnage dans l'espace du monde
            camera_x: Position horizontale de la caméra

        Returns:
            Rectangle de collision du tile si collision détectée, None sinon
        """
        collision_rects = self.get_collision_rects(camera_x)

        for tile_rect in collision_rects:
            # Pour cette fonction simple, on n'applique pas d'élargissement
            # car on n'a pas accès à l'entité. Utiliser directement les rectangles.
            if player_rect.colliderect(tile_rect):
                return tile_rect

        return None

    def resolve_collision(
        self,
        player_rect: pygame.Rect,
        dx: float,
        dy: float,
        entity: Entity,
        camera_x: float,
    ) -> Tuple[float, float, bool]:
        """Résout une collision en ajustant le déplacement.

        Args:
            player_rect: Rectangle de collision de l'entité dans l'espace du monde
            dx: Déplacement horizontal prévu
            dy: Déplacement vertical prévu
            entity: Référence à l'entité pour gérer la vitesse verticale
            camera_x: Position horizontale de la caméra

        Returns:
            Tuple (dx_corrected, dy_corrected, is_on_ground) avec les déplacements corrigés
            et l'état au sol
        """
        is_on_ground = False

        # Récupérer tous les rectangles de collision autour de la caméra courante
        collision_rects = self.get_collision_rects(camera_x)

        # Ajuster les rectangles pour tenir compte de l'échelle de l'entité.
        # IMPORTANT : On n'agrandit que la LARGEUR, pas la hauteur, pour éviter des collisions
        # verticales incorrectes (ex: sauter au-dessus d'un bloc).
        # Pour limiter les retours en arrière lors des déplacements, l'élargissement est dynamique
        # selon l'état du mouvement horizontal et vertical.
        base_width_expand = max(0.0, entity.display_width - entity.collision_width)

        # Coefficient d'élargissement par défaut (en l'air ou cas nécessitant une tolérance plus large)
        air_expand = min(base_width_expand * 0.3, 6.0)  # limite maximale 6px
        # Coefficient réduit lors d'une chute ou déplacement horizontal
        slide_expand = min(base_width_expand * 0.1, 4.0)

        if base_width_expand <= 0.0:
            width_expand = 0.0
        elif entity.is_on_ground and abs(dx) > 0.0:
            # Au sol et en mouvement: désactiver l'élargissement pour éviter les retours en arrière
            width_expand = 0.0
        elif entity.velocity_y >= 0.0:
            # En chute ou déplacement vertical nul : garder une faible tolérance
            width_expand = slide_expand
        else:
            # En phase ascendante (saut), conserver une tolérance plus élevée pour éviter les gaps
            width_expand = air_expand
 
        collision_rects = [
            pygame.Rect(
                rect.x - width_expand / 2,
                rect.y,  # Hauteur inchangée
                rect.width + width_expand,
                rect.height  # Hauteur inchangée
            )
            for rect in collision_rects
        ]

        # Si l'entité se déplace rapidement, la caméra peut se déplacer fortement
        # entre la frame précédente (camera_x) et la position prévue après déplacement.
        # Dans ce cas, on récupère également les rectangles autour de la future caméra,
        # afin d'éviter de manquer les collisions lors de déplacements rapides (ex: niveau 5).
        future_camera_x = entity.x + dx - (self.screen_width / 2)
        if abs(future_camera_x - camera_x) > (self.screen_width * 0.25):
            # Utiliser le même facteur d'élargissement réduit pour les rectangles futurs
            future_rects = [
                pygame.Rect(
                    rect.x - width_expand / 2,
                    rect.y,  # Hauteur inchangée
                    rect.width + width_expand,
                    rect.height  # Hauteur inchangée
                )
                for rect in self.get_collision_rects(future_camera_x)
            ]
            if future_rects:
                seen: set[tuple[int, int, int, int]] = {
                    (rect.x, rect.y, rect.width, rect.height) for rect in collision_rects
                }
                for rect in future_rects:
                    key = (rect.x, rect.y, rect.width, rect.height)
                    if key not in seen:
                        collision_rects.append(rect)
                        seen.add(key)

        # Résoudre d'abord horizontalement, puis verticalement
        # Cela permet de gérer correctement les collisions avec plusieurs tiles

        # Résolution horizontale (empêche la traversée latérale)
        # D'abord, vérifier si le personnage est déjà en collision HORIZONTALE et le sortir si nécessaire
        # On ne sort pas des collisions verticales légitimes (comme être au sol)
        new_rect_x = player_rect.copy()
        
        # Limite de sécurité pour les boucles itératives
        max_iterations = 10
        
        # Vérifier les collisions horizontales existantes et sortir le personnage si nécessaire
        # On itère pour gérer plusieurs collisions simultanées
        # IMPORTANT: On ne sort que des collisions HORIZONTALES, pas des collisions verticales
        # IMPORTANT: On désactive la pré-correction si le joueur est au sol ET se déplace horizontalement
        # car cela peut causer des retours en arrière indésirables
        iteration_pre = 0
        # Ne faire la pré-correction que si le joueur n'est pas au sol OU ne se déplace pas
        # Cela évite les corrections horizontales qui poussent le joueur en arrière quand il marche sur un bloc
        should_pre_correct = not (entity.is_on_ground and dx != 0)
        
        if should_pre_correct:
            while iteration_pre < max_iterations:
                collision_found_pre = False
                for tile_rect in collision_rects:
                    if new_rect_x.colliderect(tile_rect):
                        # Vérifier si c'est une collision principalement horizontale ou verticale
                        overlap_left = new_rect_x.right - tile_rect.left
                        overlap_right = tile_rect.right - new_rect_x.left
                        overlap_top = new_rect_x.bottom - tile_rect.top
                        overlap_bottom = tile_rect.bottom - new_rect_x.top
                        
                        # Calculer les overlaps horizontaux et verticaux
                        overlap_horizontal = min(overlap_left, overlap_right)
                        overlap_vertical = min(overlap_top, overlap_bottom)
                        
                        # FILTRAGE DES COLLISIONS ARRIÈRE : Ignorer les collisions avec des tiles
                        # situés à l'arrière du joueur par rapport à sa direction de regard
                        player_center_x = new_rect_x.x + new_rect_x.width / 2
                        tile_center_x = tile_rect.x + tile_rect.width / 2
                        is_back_collision = False
                        
                        if hasattr(entity, 'current_direction'):
                            if entity.current_direction == "left" and tile_center_x > player_center_x:
                                # Le joueur regarde vers la gauche, le tile est à droite (arrière)
                                is_back_collision = True
                            elif entity.current_direction == "right" and tile_center_x < player_center_x:
                                # Le joueur regarde vers la droite, le tile est à gauche (arrière)
                                is_back_collision = True
                        
                        # Si c'est une collision principalement horizontale (pas verticale)
                        # On sort le personnage horizontalement
                        # SAUF si c'est une collision arrière (qui est ignorée)
                        if overlap_horizontal < overlap_vertical and not is_back_collision:
                            collision_found_pre = True
                            if overlap_left < overlap_right:
                                # Plus proche du côté gauche, sortir par la gauche
                                new_rect_x.right = tile_rect.left
                            else:
                                # Plus proche du côté droit, sortir par la droite
                                new_rect_x.left = tile_rect.right
                            break  # Corriger une collision à la fois
                
                if not collision_found_pre:
                    break
                iteration_pre += 1
        
        # Maintenant appliquer le déplacement horizontal
        new_rect_x.x += dx
        
        # Vérifier les collisions horizontales et corriger
        # On doit itérer jusqu'à ce qu'il n'y ait plus de collisions
        # pour gérer les cas où plusieurs tiles sont impliqués
        iteration = 0
        while iteration < max_iterations:
            collision_found = False
            for tile_rect in collision_rects:
                if new_rect_x.colliderect(tile_rect):
                    # Vérifier si c'est une collision principalement horizontale
                    # On ne corrige que les collisions horizontales, pas les verticales
                    overlap_left = new_rect_x.right - tile_rect.left
                    overlap_right = tile_rect.right - new_rect_x.left
                    overlap_top = new_rect_x.bottom - tile_rect.top
                    overlap_bottom = tile_rect.bottom - new_rect_x.top
                    
                    # Calculer les overlaps horizontaux et verticaux
                    overlap_horizontal = min(overlap_left, overlap_right)
                    overlap_vertical = min(overlap_top, overlap_bottom)
                    
                    # FILTRAGE DES COLLISIONS ARRIÈRE : Ignorer les collisions avec des tiles
                    # situés à l'arrière du joueur par rapport à sa direction de regard
                    player_center_x = new_rect_x.x + new_rect_x.width / 2
                    tile_center_x = tile_rect.x + tile_rect.width / 2
                    is_back_collision = False
                    
                    if hasattr(entity, 'current_direction'):
                        if entity.current_direction == "left" and tile_center_x > player_center_x:
                            # Le joueur regarde vers la gauche, le tile est à droite (arrière)
                            is_back_collision = True
                        elif entity.current_direction == "right" and tile_center_x < player_center_x:
                            # Le joueur regarde vers la droite, le tile est à gauche (arrière)
                            is_back_collision = True
                    
                    # Si c'est une collision principalement horizontale, on la corrige
                    # SAUF si c'est une collision arrière (qui est ignorée)
                    if overlap_horizontal < overlap_vertical and not is_back_collision:
                        # Approche "STEP UP" pour fluidifier le mouvement sur les plateformes
                        should_correct = True
                        step_up_applied = False
                        
                        if entity.is_on_ground and dx != 0:
                            # Quand au sol et en mouvement, détecter si on heurte le bord d'une plateforme
                            # 
                            # SOLUTION "STEP UP" : Au lieu d'ignorer ou de bloquer, on pousse légèrement
                            # le joueur vers le HAUT pour qu'il "monte" sur le bord du bloc
                            # C'est beaucoup plus fluide et naturel qu'un blocage brutal
                            
                            # Recalculer la position du bas AVANT le déplacement horizontal
                            player_rect_before = player_rect.copy()
                            player_bottom_before = player_rect_before.bottom
                            tile_top = tile_rect.top
                            
                            # Critère : Si le bas du joueur AVANT déplacement était proche du haut du tile
                            # Tolérance de 12 pixels pour détecter les bords de plateforme
                            is_near_platform_edge = player_bottom_before <= tile_top + 12
                            
                            # Si on est près d'un bord de plateforme, appliquer le "step up"
                            if is_near_platform_edge:
                                # Calculer combien il faut monter pour passer au-dessus du tile
                                # On monte juste assez pour dégager le haut du tile
                                step_up_amount = tile_top - new_rect_x.bottom + 1
                                
                                # Limiter le step up à un maximum raisonnable (5 pixels)
                                # pour éviter des sauts trop importants
                                if step_up_amount > 0 and step_up_amount <= 5:
                                    # Appliquer le step up : monter le rectangle
                                    new_rect_x.y += step_up_amount
                                    step_up_applied = True
                                    should_correct = False  # Pas besoin de corriger horizontalement
                        
                        if should_correct and not step_up_applied:
                            collision_found = True
                            # Déterminer la direction de la collision en fonction de la position relative
                            # et de la direction du mouvement
                            
                            # Si on se déplace vers la droite, on doit être bloqué à gauche du tile
                            if dx > 0:
                                # Bloquer à gauche du tile
                                new_rect_x.right = tile_rect.left
                            # Si on se déplace vers la gauche, on doit être bloqué à droite du tile
                            elif dx < 0:
                                # Bloquer à droite du tile
                                new_rect_x.left = tile_rect.right
                            else:
                                # Si dx == 0 après correction, déterminer la direction de sortie
                                # en fonction de la position relative
                                if overlap_left < overlap_right:
                                    # Plus proche du côté gauche, sortir par la gauche
                                    new_rect_x.right = tile_rect.left
                                else:
                                    # Plus proche du côté droit, sortir par la droite
                                    new_rect_x.left = tile_rect.right
                            break  # Corriger une collision à la fois
            
            if not collision_found:
                break
            iteration += 1

        # Résolution verticale (avec le rectangle horizontalement corrigé)
        # Empêche la traversée verticale
        new_rect = new_rect_x.copy()
        new_rect.y += dy
        
        # Vérifier les collisions verticales et corriger
        iteration = 0
        while iteration < max_iterations:
            collision_found = False
            for tile_rect in collision_rects:
                # DÉTECTION AMÉLIORÉE : Vérifier non seulement le chevauchement,
                # mais aussi si le joueur a traversé le tile pendant le déplacement
                # Cette détection est critique pour empêcher le personnage de passer à travers
                # un tile en une seule frame lorsque la vitesse est très élevée (ex: niveau 5)
                has_collision = False
                
                # Cas 1 : Chevauchement direct (détection classique)
                if new_rect.colliderect(tile_rect):
                    has_collision = True
                # Cas 2 : Traversée complète vers le bas (dy > 0)
                # Le joueur était au-dessus et est maintenant en dessous
                elif dy > 0:
                    # Vérifier si le joueur a traversé le tile verticalement
                    # Position avant : joueur au-dessus ou chevauchant le haut du tile
                    # Position après : joueur en dessous ou chevauchant le bas du tile
                    player_was_above = player_rect.bottom <= tile_rect.top
                    player_is_below = new_rect.top >= tile_rect.bottom
                    # Vérifier aussi le chevauchement horizontal
                    horizontal_overlap = (
                        new_rect.right > tile_rect.left and 
                        new_rect.left < tile_rect.right
                    )
                    if player_was_above and player_is_below and horizontal_overlap:
                        has_collision = True
                # Cas 3 : Traversée complète vers le haut (dy < 0)
                # Le joueur était en dessous et est maintenant au-dessus
                elif dy < 0:
                    player_was_below = player_rect.top >= tile_rect.bottom
                    player_is_above = new_rect.bottom <= tile_rect.top
                    horizontal_overlap = (
                        new_rect.right > tile_rect.left and 
                        new_rect.left < tile_rect.right
                    )
                    if player_was_below and player_is_above and horizontal_overlap:
                        has_collision = True
                
                if has_collision:
                    # Vérifier si c'est une collision principalement VERTICALE
                    # Cela évite de corriger verticalement une collision de coin qui est plutôt horizontale
                    overlap_left = new_rect.right - tile_rect.left
                    overlap_right = tile_rect.right - new_rect.left
                    overlap_top = new_rect.bottom - tile_rect.top
                    overlap_bottom = tile_rect.bottom - new_rect.top
                    
                    # Calculer les overlaps horizontaux et verticaux
                    overlap_horizontal = min(overlap_left, overlap_right)
                    overlap_vertical = min(overlap_top, overlap_bottom)
                    
                    # Vérifier si le joueur est vraiment au-dessus ou en dessous du tile
                    # et non pas sur le côté (après correction horizontale)
                    # Après une correction horizontale, le joueur peut être poussé sur le côté du tile,
                    # mais son rectangle peut encore chevaucher le tile verticalement.
                    # Dans ce cas, nous ne devons PAS appliquer de correction verticale.
                    player_center_x = new_rect.x + new_rect.width / 2
                    tile_left = tile_rect.x
                    tile_right = tile_rect.x + tile_rect.width
                    
                    # Si le centre du joueur est clairement à gauche ou à droite du tile,
                    # c'est une collision de côté résolue horizontalement - on ignore la correction verticale
                    # On utilise une petite tolérance pour gérer les cas limites
                    tolerance = 2.0
                    is_on_side = (player_center_x < tile_left - tolerance or 
                                 player_center_x > tile_right + tolerance)

                    # Détection d'une entrée par le dessous du coin avant :
                    # si le joueur était sous le bas du tile avant déplacement et passe au-dessus,
                    # on considère la collision comme verticale même si l'overlap horizontal est minime.
                    entered_from_below = (
                        dy < 0
                        and player_rect.top >= tile_rect.bottom
                        and new_rect.top < tile_rect.bottom
                        and new_rect.right > tile_rect.left
                        and new_rect.left < tile_rect.right
                    )

                    if entered_from_below:
                        collision_found = True
                        # Trouver le plafond le plus haut intersecté à cette abscisse
                        player_span_left = new_rect.left
                        player_span_right = new_rect.right
                        highest_ceiling = tile_rect.bottom

                        for candidate in collision_rects:
                            if (
                                player_span_right > candidate.left
                                and player_span_left < candidate.right
                                and player_rect.top >= candidate.bottom
                                and new_rect.top < candidate.bottom
                            ):
                                if candidate.bottom < highest_ceiling:
                                    highest_ceiling = candidate.bottom

                        new_rect.top = highest_ceiling
                        entity.velocity_y = 0.0
                        break
                    
                    # Ne corriger verticalement que si :
                    # 1. La collision est principalement VERTICALE (overlap_vertical <= overlap_horizontal)
                    # 2. ET le joueur n'est pas clairement sur le côté du tile (après correction horizontale)
                    # Cela évite les corrections verticales incorrectes après une correction horizontale sur un coin
                    if overlap_vertical <= overlap_horizontal and not is_on_side:
                        collision_found = True
                        if dy > 0:  # Déplacement vers le bas (chute)
                            # Bloquer au-dessus du tile
                            # Placer le bas du rectangle de collision exactement au-dessus du tile
                            # Cela garantit qu'il n'y a pas d'espace entre le joueur et le tile
                            # et que le joueur ne peut JAMAIS se retrouver en dessous du tile
                            new_rect.bottom = tile_rect.top
                            entity.velocity_y = 0.0  # Réinitialiser la vitesse verticale
                            is_on_ground = True  # L'entité est au sol
                            
                            # Détecter si c'est une plateforme mobile et attacher l'entité
                            # Vérifier si le tile appartient à une plateforme mobile
                            platform_layer = self._find_layer_for_rect(tile_rect, camera_x)
                            if platform_layer:
                                self._maybe_attach_entity_to_layer(entity, new_rect, platform_layer, tile_rect)
                        elif dy < 0:  # Déplacement vers le haut
                            # Bloquer en dessous du tile
                            new_rect.top = tile_rect.bottom
                            entity.velocity_y = 0.0  # Réinitialiser la vitesse verticale
                        else:
                            # Si dy == 0, on est déjà en collision verticalement
                            # Déterminer la direction de sortie en fonction de la position relative
                            if overlap_top < overlap_bottom:
                                # Plus proche du haut, sortir par le haut
                                new_rect.bottom = tile_rect.top
                                entity.velocity_y = 0.0
                                is_on_ground = True
                            else:
                                # Plus proche du bas, sortir par le bas
                                new_rect.top = tile_rect.bottom
                                entity.velocity_y = 0.0
                        break  # Corriger une collision à la fois
            
            if not collision_found:
                break
            iteration += 1

        # Attacher l'entité aux plateformes mobiles même sans mouvement vertical
        self._reattach_if_needed(entity, new_rect, camera_x)

        # Vérifier si l'entité est attachée à une plateforme mobile
        # Si oui, vérifier qu'elle est toujours sur la plateforme (avec compensation du delta)
        if entity.attached_platform is not None:
            platform_layer = entity.attached_platform
            if platform_layer.name in self.moving_platforms:
                platform_data = self.moving_platforms[platform_layer.name]
                # Récupérer le delta de cette frame pour compenser (comme dans _reattach_if_needed)
                delta_x, delta_y = platform_data.get('frame_delta', (0.0, 0.0))
                entity_rect = entity.get_collision_rect()
                platform_rects = self._get_layer_collision_rects(platform_layer, camera_x)
                
                is_still_on_platform = False
                for platform_rect in platform_rects:
                    # Compenser le delta pour vérifier avec la position AVANT le déplacement
                    adjusted_rect = pygame.Rect(
                        platform_rect.x - round(delta_x),
                        platform_rect.y - round(delta_y),
                        platform_rect.width,
                        platform_rect.height,
                    )
                    # Utiliser les mêmes tolérances que _is_entity_on_platform_surface
                    if self._is_entity_on_platform_surface(entity_rect, adjusted_rect, entity):
                        is_still_on_platform = True
                        break
                
                # Si l'entité saute (velocity_y < 0), la détacher
                # Sinon, tant qu'elle est sur la plateforme, elle reste attachée
                if not is_still_on_platform or getattr(entity, 'velocity_y', 0.0) < 0:
                    self._detach_entity_from_platform(entity)
                    logger.debug("Entité détachée de plateforme mobile: layer='%s'", platform_layer.name)
        
        # Retourner les déplacements corrigés
        # Le déplacement corrigé doit être calculé pour que le bas du rectangle de collision
        # reste aligné avec le bas du sprite visuel
        corrected_dx = new_rect.x - player_rect.x
        corrected_dy = new_rect.y - player_rect.y
        return (corrected_dx, corrected_dy, is_on_ground)
    
    def _find_layer_for_rect(self, rect: pygame.Rect, camera_x: float):
        """Trouve la layer correspondant à un rectangle de collision.
        
        Args:
            rect: Rectangle de collision
            camera_x: Position horizontale de la caméra
            
        Returns:
            La layer correspondante ou None
        """
        solid_layers = self._get_solid_layers()
        for layer in solid_layers:
            layer_rects = self._get_layer_collision_rects(layer, camera_x)
            for layer_rect in layer_rects:
                # Vérifier si les rectangles correspondent (avec tolérance)
                if (abs(layer_rect.x - rect.x) < 1 and
                    abs(layer_rect.y - rect.y) < 1 and
                    abs(layer_rect.width - rect.width) < 1 and
                    abs(layer_rect.height - rect.height) < 1):
                    return layer
        return None

    def on_layer_translated(self, layer, delta_x: float, delta_y: float) -> None:
        """Notifie le système qu'une layer a été déplacée.
        
        Cette méthode est appelée par EventTriggerSystem à chaque frame où
        une plateforme mobile se déplace. Elle enregistre le déplacement pour
        l'appliquer aux passagers après la résolution des collisions.
        
        Args:
            layer: La layer qui a été déplacée
            delta_x: Déplacement horizontal de la frame
            delta_y: Déplacement vertical de la frame
        """
        layer_id = layer.name
        # Initialiser ou mettre à jour la plateforme mobile
        if layer_id not in self.moving_platforms:
            self.moving_platforms[layer_id] = {
                'layer': layer,
                'passengers': set(),
                'frame_delta': (0.0, 0.0)
            }
        else:
            self.moving_platforms[layer_id]['layer'] = layer
        # Enregistrer le déplacement de cette frame
        self.moving_platforms[layer_id]['frame_delta'] = (delta_x, delta_y)
    
    def apply_platform_movements(self, entities: list) -> None:
        """Applique les déplacements des plateformes mobiles aux passagers attachés.
        
        Cette méthode doit être appelée APRÈS la résolution des collisions pour chaque entité.
        Elle applique le déplacement de la plateforme aux entités attachées.
        Le joueur suit le mouvement de la plateforme en X et Y, tout en pouvant se déplacer
        horizontalement de manière indépendante via les touches.
        
        Args:
            entities: Liste des entités à vérifier (joueur, PNJ, etc.)
        """
        for layer_id, platform_data in list(self.moving_platforms.items()):
            delta_x, delta_y = platform_data['frame_delta']
            passengers = platform_data['passengers']
            
            # Appliquer le déplacement à tous les passagers
            for entity in list(passengers):
                # Appliquer le déplacement de la plateforme (X et Y)
                # Le joueur suit la plateforme, mais peut aussi bouger en X indépendamment via les touches
                entity.x += delta_x
                entity.y += delta_y
                # Maintenir is_on_ground = True pendant le transport
                entity.is_on_ground = True
            
            # Réinitialiser le delta pour la prochaine frame
            platform_data['frame_delta'] = (0.0, 0.0)
    
    def _maybe_attach_entity_to_layer(self, entity: Entity, entity_rect: pygame.Rect, platform_layer, platform_rect: pygame.Rect) -> None:
        """Attache l'entité à la plateforme si les conditions sont réunies."""
        if platform_layer.name not in self.moving_platforms:
            return
        if not self._is_entity_on_platform_surface(entity_rect, platform_rect, entity):
            return
        self._attach_entity_to_platform(entity, platform_layer)

    def _reattach_if_needed(self, entity: Entity, entity_rect: pygame.Rect, camera_x: float) -> None:
        """Attache l'entité aux plateformes mobiles actives même sans mouvement vertical.
        
        IMPORTANT: La plateforme a déjà été déplacée (world_x/y_offset mis à jour) mais
        l'entité n'a pas encore reçu le delta. On compense donc le frame_delta pour
        détecter si l'entité était sur la plateforme AVANT le déplacement de cette frame.
        """
        if not self.moving_platforms:
            return
        for platform_id, platform_data in self.moving_platforms.items():
            layer = platform_data.get('layer')
            if layer is None:
                continue
            # Récupérer le delta de cette frame (la plateforme a déjà bougé de ce delta)
            delta_x, delta_y = platform_data.get('frame_delta', (0.0, 0.0))
            platform_rects = self._get_layer_collision_rects(layer, camera_x)
            for platform_rect in platform_rects:
                # Compenser le delta pour obtenir la position AVANT le déplacement
                # (l'entité n'a pas encore été déplacée, on doit comparer avec l'ancienne position)
                adjusted_rect = pygame.Rect(
                    platform_rect.x - round(delta_x),
                    platform_rect.y - round(delta_y),
                    platform_rect.width,
                    platform_rect.height,
                )
                if self._is_entity_on_platform_surface(entity_rect, adjusted_rect, entity):
                    self._attach_entity_to_platform(entity, layer)
                    return

    def _is_entity_on_platform_surface(self, entity_rect: pygame.Rect, platform_rect: pygame.Rect, entity: Entity) -> bool:
        """Retourne True si l'entité se trouve sur la face supérieure du rectangle de plateforme."""
        entity_bottom = entity_rect.bottom
        platform_top = platform_rect.top
        vertical_distance = entity_bottom - platform_top
        # Autoriser une légère marge (pénétration / gap) pour absorber les arrondis
        if not (-4 <= vertical_distance <= 12):
            return False
        overlap_h = min(
            entity_rect.right - platform_rect.left,
            platform_rect.right - entity_rect.left,
        )
        overlap_ratio = overlap_h / entity.collision_width if entity.collision_width > 0 else 0.0
        if overlap_ratio < 0.25:
            return False
        # Éviter d'attacher pendant un saut important vers le haut
        if getattr(entity, "velocity_y", 0.0) < 0:
            return False
        return True

    def _attach_entity_to_platform(self, entity: Entity, layer) -> None:
        """Associe l'entité à la plateforme donnée."""
        entry = self.moving_platforms.setdefault(
            layer.name, {'layer': layer, 'passengers': set(), 'frame_delta': (0.0, 0.0)}
        )
        entry['layer'] = layer
        if entity.attached_platform and entity.attached_platform != layer:
            self._detach_entity_from_platform(entity)
        entry['passengers'].add(entity)
        entity.attached_platform = layer
        entity.is_on_ground = True

    def _detach_entity_from_platform(self, entity: Entity) -> None:
        """Détache proprement l'entité de sa plateforme actuelle."""
        if entity.attached_platform is None:
            return
        layer_id = entity.attached_platform.name
        if layer_id in self.moving_platforms:
            self.moving_platforms[layer_id]['passengers'].discard(entity)
        entity.attached_platform = None
    
    def _get_layer_collision_rects(self, layer, camera_x: float) -> list[pygame.Rect]:
        """Récupère les rectangles de collision d'une layer spécifique.
        
        Args:
            layer: La layer dont on veut les rectangles
            camera_x: Position horizontale de la caméra
            
        Returns:
            Liste des rectangles de collision de la layer
        """
        layer_width = layer.surface.get_width()
        solid_rects = self._extract_solid_rects_from_surface(layer.surface, layer.name, tile_size=64)
        collision_rects: list[pygame.Rect] = []
        
        world_x_base = getattr(layer, 'world_x_offset', 0.0)
        world_y_offset = getattr(layer, 'world_y_offset', 0.0)
        
        if layer.repeat:
            infinite_offset = getattr(layer, "infinite_offset", 0.0)
            effective_width = layer_width + infinite_offset
            if effective_width <= 0:
                effective_width = layer_width
            
            num_repeats = math.ceil(self.screen_width / effective_width) + 2
            start_offset = -(layer.offset_x % effective_width)
            
            for i in range(num_repeats):
                screen_x = start_offset + (i * effective_width)
                world_x = world_x_base + screen_x + camera_x
                
                if (
                    world_x + layer_width >= camera_x - 100
                    and world_x <= camera_x + self.screen_width + 100
                ):
                    for rect in solid_rects:
                        collision_rect = pygame.Rect(
                            round(world_x + rect.x),
                            round(rect.y + world_y_offset),
                            round(rect.width),
                            round(rect.height),
                        )
                        collision_rects.append(collision_rect)
        else:
            if world_x_base + layer_width >= camera_x - 100 and world_x_base <= camera_x + self.screen_width + 100:
                for rect in solid_rects:
                    collision_rect = pygame.Rect(
                        round(world_x_base + rect.x),
                        round(rect.y + world_y_offset),
                        round(rect.width),
                        round(rect.height),
                    )
                    collision_rects.append(collision_rect)
        
        return collision_rects
    
    
    def release_passengers_from_layer(self, layer) -> None:
        """Relâche tous les passagers attachés à une layer.
        
        Args:
            layer: La layer dont on veut relâcher les passagers
        """
        layer_id = layer.name
        if layer_id in self.moving_platforms:
            passengers = self.moving_platforms[layer_id].get('passengers', set())
            for entity in passengers:
                # Réactiver le contrôle normal
                if hasattr(entity, 'attached_platform'):
                    entity.attached_platform = None
            del self.moving_platforms[layer_id]

