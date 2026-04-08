"""Module de préchargement des éléments graphiques."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

import pygame

from ..entities.player_level_manager import MAX_PLAYER_LEVEL

if TYPE_CHECKING:
    from ..inventory.config import InventoryItemConfig
    from ..levels.config import LevelConfig, NPCsConfig
    from ..stats.config import PlayerStatsConfig

logger = logging.getLogger("moteur_jeu_presentation.preloader")

# Caches globaux partagés pour tous les composants
# Ces caches sont remplis lors du préchargement et utilisés par les composants
# pour éviter de recharger les mêmes assets plusieurs fois

# Cache global pour les sprite sheets de niveau
# Clé: nom du sprite sheet (str), Valeur: Surface pygame
_global_level_sprite_sheet_cache: Dict[str, pygame.Surface] = {}

# Cache global pour les sprite sheets d'inventaire
# Clé: chemin absolu du sprite sheet (str), Valeur: Surface pygame
_global_inventory_sprite_sheet_cache: Dict[str, pygame.Surface] = {}

# Cache global pour les sprites extraits d'inventaire
# Clé: item_id (str), Valeur: Surface pygame
_global_inventory_cached_surfaces: Dict[str, pygame.Surface] = {}

# Cache global pour les sprite sheets des PNJ
# Clé: chemin absolu du sprite sheet (str), Valeur: Surface pygame
_global_npc_sprite_sheet_cache: Dict[str, pygame.Surface] = {}

# Cache global pour les sprites des PNJ redimensionnés
# Clé: (sprite_path_key, row, col, display_width, display_height) (tuple)
#   - sprite_path_key: chemin absolu du sprite sheet (str)
#   - row: ligne du sprite dans le sprite sheet (0-based)
#   - col: colonne du sprite dans le sprite sheet (0-based)
#   - display_width: largeur d'affichage après scaling (int)
#   - display_height: hauteur d'affichage après scaling (int)
# Valeur: Surface pygame du sprite extrait et redimensionné
_global_npc_scaled_sprite_cache: Dict[tuple[str, int, int, int, int], pygame.Surface] = {}

# Cache global pour les sprites des PNJ redimensionnés et retournés horizontalement
# Clé: (sprite_path_key, row, col, display_width, display_height) (tuple)
# Valeur: Surface pygame du sprite extrait, redimensionné et retourné
_global_npc_scaled_flipped_sprite_cache: Dict[tuple[str, int, int, int, int], pygame.Surface] = {}

# Cache global pour les sprites de niveau redimensionnés
# Clé: (sheet_name, row, col, scale) (tuple), Valeur: Surface pygame
_global_level_scaled_sprite_cache: Dict[tuple[str, int, int, float], pygame.Surface] = {}

# Cache global pour les sprite sheets du joueur
# Clé: chemin absolu du sprite sheet (str), Valeur: Surface pygame
_global_player_sprite_sheet_cache: Dict[str, pygame.Surface] = {}

# Cache global pour les sprites du joueur redimensionnés
# Clé: (level, animation_type, row, col, display_width, display_height) (tuple)
#   - level: niveau du joueur (1-5)
#   - animation_type: "walk", "jump", "climb"
#   - row: ligne du sprite (0-based)
#   - col: colonne du sprite (0-based)
#   - display_width: largeur d'affichage (int)
#   - display_height: hauteur d'affichage (int)
# Valeur: Surface pygame du sprite redimensionné
_global_player_scaled_sprite_cache: Dict[tuple[int, str, int, int, int, int], pygame.Surface] = {}


class LoadingBar:
    """Gère l'affichage de la barre de chargement."""
    
    def __init__(
        self,
        screen: pygame.Surface,
        screen_width: int,
        screen_height: int,
    ) -> None:
        """Initialise la barre de chargement.
        
        Args:
            screen: Surface pygame pour dessiner la barre
            screen_width: Largeur de l'écran
            screen_height: Hauteur de l'écran
        """
        self.screen = screen
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Dimensions de la barre
        self.bar_width = 600
        self.bar_height = 30
        self.bar_x = (screen_width - self.bar_width) // 2
        self.bar_y = (screen_height - self.bar_height) // 2
        
        # Couleurs
        self.bar_color = (74, 149, 172)  # Couleur principale du jeu
        self.bar_bg_color = (50, 50, 50)
        self.text_color = (255, 255, 255)
        
        # Police
        try:
            self.font = pygame.font.SysFont("arial", 24, bold=True)
        except pygame.error:
            self.font = pygame.font.SysFont("sans-serif", 24, bold=True)
    
    def draw(
        self,
        progress: float,
        category: str,
        current: int,
        total: int,
    ) -> None:
        """Dessine la barre de chargement.
        
        Args:
            progress: Progression actuelle (0.0 à 1.0)
            category: Nom de la catégorie en cours de chargement
            current: Nombre d'éléments chargés dans la catégorie actuelle
            total: Nombre total d'éléments dans la catégorie actuelle
        """
        # Fond noir
        self.screen.fill((0, 0, 0))
        
        # Fond de la barre
        pygame.draw.rect(
            self.screen,
            self.bar_bg_color,
            (self.bar_x, self.bar_y, self.bar_width, self.bar_height),
        )
        
        # Barre de progression
        progress_width = int(self.bar_width * progress)
        pygame.draw.rect(
            self.screen,
            self.bar_color,
            (self.bar_x, self.bar_y, progress_width, self.bar_height),
        )
        
        # Texte de progression
        if total > 0:
            text = f"{category}... {current}/{total}"
        else:
            text = f"{category}..."
        
        text_surface = self.font.render(text, True, self.text_color)
        text_rect = text_surface.get_rect(center=(self.screen_width // 2, self.bar_y - 40))
        self.screen.blit(text_surface, text_rect)
        
        # Pourcentage
        percent_text = f"{int(progress * 100)}%"
        percent_surface = self.font.render(percent_text, True, self.text_color)
        percent_rect = percent_surface.get_rect(
            center=(self.screen_width // 2, self.bar_y + self.bar_height + 20)
        )
        self.screen.blit(percent_surface, percent_rect)
        
        pygame.display.flip()


class AssetPreloader:
    """Gère le préchargement de tous les éléments graphiques du jeu."""
    
    def __init__(
        self,
        screen: pygame.Surface,
        screen_width: int,
        screen_height: int,
        project_root: Path,
    ) -> None:
        """Initialise le préchargeur.
        
        Args:
            screen: Surface pygame pour afficher la barre de chargement
            screen_width: Largeur de l'écran de rendu
            screen_height: Hauteur de l'écran de rendu
            project_root: Chemin racine du projet
        """
        self.screen = screen
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.project_root = project_root
        
        # Barre de chargement
        self.loading_bar = LoadingBar(screen, screen_width, screen_height)
        
        # État de progression
        self.progress = 0.0
        self.current_category = ""
        self.current_count = 0
        self.current_total = 0
        self.total_loaded = 0
        self.total_to_load = 0
        
        # Statistiques
        self.loading_stats: Dict[str, int] = {}
    
    def preload_all_assets(
        self,
        level_config: "LevelConfig",
        npcs_config: Optional["NPCsConfig"],
        inventory_config: Optional["InventoryItemConfig"],
        stats_config: Optional["PlayerStatsConfig"],
        player_level: int,
    ) -> Dict[str, Any]:
        """Précharge tous les éléments graphiques.
        
        Args:
            level_config: Configuration du niveau
            npcs_config: Configuration des PNJ
            inventory_config: Configuration des objets d'inventaire
            stats_config: Configuration des stats du joueur
            player_level: Niveau initial du joueur
            
        Returns:
            Dictionnaire contenant les statistiques de chargement
        """
        # Estimer le nombre total d'éléments à charger de manière plus précise
        self.total_to_load = self._estimate_total_items(
            level_config, npcs_config, inventory_config, stats_config
        )
        
        # Initialiser la progression
        self.total_loaded = 0
        self._update_progress("Initialisation...", 0, self.total_to_load)
        
        # Catégories de chargement
        categories = [
            ("Sprites de niveau", self._preload_level_sprites, (level_config,)),
            ("Sprites du joueur", self._preload_player_sprites, (stats_config, player_level)),
            ("Sprites des PNJ", self._preload_npc_sprites, (npcs_config,)),
            ("Sprites d'inventaire", self._preload_inventory_sprites, (inventory_config,)),
            ("Images de dialogue", self._preload_dialogue_images, (npcs_config,)),
        ]
        
        # Précharger chaque catégorie
        for category_name, preload_func, args in categories:
            if args[0] is None and category_name in ("Sprites des PNJ", "Images de dialogue"):
                continue  # Ignorer si npcs_config est None
            
            self._log_category_start(category_name)
            
            try:
                count = preload_func(*args)
                self.loading_stats[category_name] = count
                # Note: self.total_loaded est mis à jour dans les méthodes _preload_* au fur et à mesure
                self._log_category_end(category_name, count)
            except Exception as e:
                logger.warning(f"Erreur lors du préchargement de {category_name}: {e}")
                print(f"[Préchargement] Warning: Erreur lors du préchargement de {category_name}: {e}")
                self.loading_stats[category_name] = 0
        
        # Afficher le total final
        self._log_total()
        
        # Afficher 100% à la fin
        self._update_progress("Terminé", self.total_loaded, self.total_loaded)
        
        return {
            "total_loaded": self.total_loaded,
            "stats": self.loading_stats,
        }
    
    def _estimate_total_items(
        self,
        level_config: "LevelConfig",
        npcs_config: Optional["NPCsConfig"],
        inventory_config: Optional["InventoryItemConfig"],
        stats_config: Optional["PlayerStatsConfig"],
    ) -> int:
        """Estime le nombre total d'éléments à charger.
        
        Args:
            level_config: Configuration du niveau
            npcs_config: Configuration des PNJ
            inventory_config: Configuration des objets d'inventaire
            stats_config: Configuration des stats du joueur
            
        Returns:
            Estimation du nombre total d'éléments à charger
        """
        total = 0
        
        # Sprites de niveau : sprite sheets + sprites redimensionnés
        total += len(level_config.sprite_sheets)  # Sprite sheets
        total += len(level_config.sprites) * 3  # Sprites redimensionnés (estimation: base + first + last)
        
        # Sprites du joueur : max_level × 3 animations × ~32 frames
        n_player_levels = (
            stats_config.max_level if stats_config is not None else MAX_PLAYER_LEVEL
        )
        total += n_player_levels * 3 * 32  # Estimation
        
        # Sprites des PNJ
        if npcs_config:
            for npc_config in npcs_config.npcs:
                total += 1  # Sprite sheet
                # Estimer le nombre de frames (dépend des animations)
                if npc_config.animations:
                    for anim_config in npc_config.animations.values():
                        total += anim_config.num_frames * 2  # Normal + flipped
        
        # Sprites d'inventaire
        if inventory_config:
            total += len(inventory_config.items) * 2  # Sprite sheet + sprite extrait (estimation)
        
        # Images de dialogue
        if npcs_config:
            # Estimer en parcourant les dialogues
            for npc_config in npcs_config.npcs:
                if npc_config.dialogue_blocks:
                    for dialogue_block in npc_config.dialogue_blocks:
                        for exchange in dialogue_block.exchanges:
                            if exchange.image_path:
                                total += 1
        
        return total
    
    def _preload_level_sprites(self, level_config: "LevelConfig") -> int:
        """Précharge tous les sprites de niveau avec progression continue.
        
        Args:
            level_config: Configuration du niveau
            
        Returns:
            Nombre total d'images chargées (sprite sheets + sprites redimensionnés)
        """
        from ..rendering.config import compute_design_scale
        
        # 1. Calculer le total avant de commencer
        total_sprite_sheets = len([s for s in level_config.sprite_sheets.values() if s.path.exists()])
        total_scaled_sprites = len(level_config.sprites) * 3  # Estimation: base + first + last
        total_items = total_sprite_sheets + total_scaled_sprites
        
        count = 0
        
        # Calculer les facteurs de conversion (même logique que dans loader.py)
        scale_x, scale_y = compute_design_scale((self.screen_width, self.screen_height))
        
        # 2. Charger tous les sprite sheets avec mise à jour de progression
        for sheet_name, sheet_config in level_config.sprite_sheets.items():
            if not sheet_config.path.exists():
                print(f"[Préchargement]   - Sprite sheet '{sheet_name}' : introuvable, ignoré")
                continue
            
            try:
                sprite_sheet = pygame.image.load(str(sheet_config.path)).convert_alpha()
                
                # Mettre en cache global
                _global_level_sprite_sheet_cache[sheet_name] = sprite_sheet
                
                count += 1
                self.total_loaded += 1
                print(f"[Préchargement]   - Sprite sheet '{sheet_name}' : 1 image chargée")
                
                # Mettre à jour la progression après chaque sprite sheet
                self._update_progress("Sprites de niveau", count, total_items)
                pygame.event.pump()
            except Exception as e:
                print(f"[Préchargement]   - Erreur lors du chargement du sprite sheet '{sheet_name}': {e}")
        
        # 3. Précharger tous les sprites individuels avec leur scaling appliqué
        scaled_sprites_count = 0
        for sprite_mapping in level_config.sprites:
            sheet_name = sprite_mapping.sheet
            scale = sprite_mapping.scale
            
            # Vérifier que le sprite sheet est chargé
            if sheet_name not in _global_level_sprite_sheet_cache:
                continue
            
            sprite_sheet = _global_level_sprite_sheet_cache[sheet_name]
            sheet_config = level_config.sprite_sheets[sheet_name]
            original_width = sheet_config.sprite_width
            original_height = sheet_config.sprite_height
            
            # Fonction helper pour précharger un sprite avec scaling
            def preload_scaled_sprite(sprite_row: int, sprite_col: int) -> None:
                """Précharge un sprite avec son scaling appliqué."""
                cache_key = (sheet_name, sprite_row, sprite_col, scale)
                
                # Vérifier si déjà en cache
                if cache_key in _global_level_scaled_sprite_cache:
                    return
                
                # Extraire le sprite
                x = sprite_col * sheet_config.sprite_width
                y = sprite_row * sheet_config.sprite_height
                rect = pygame.Rect(x, y, sheet_config.sprite_width, sheet_config.sprite_height)
                sprite = pygame.Surface(
                    (sheet_config.sprite_width, sheet_config.sprite_height), pygame.SRCALPHA
                )
                sprite.blit(sprite_sheet, (0, 0), rect)
                
                # Appliquer le redimensionnement (même logique que dans loader.py)
                # Étape 1 : Appliquer le scale dans le repère 1920x1080
                scaled_width_in_design = original_width * scale
                scaled_height_in_design = original_height * scale
                # Étape 2 : Convertir vers la résolution interne 1280x720
                new_width = int(scaled_width_in_design * scale_x)
                new_height = int(scaled_height_in_design * scale_y)
                
                # Redimensionner le sprite seulement si nécessaire
                if new_width != original_width or new_height != original_height:
                    sprite = pygame.transform.smoothscale(sprite, (new_width, new_height))
                
                # Convertir pour optimiser le rendu
                sprite = sprite.convert_alpha()
                
                # Mettre en cache global
                _global_level_scaled_sprite_cache[cache_key] = sprite
            
            # Précharger le sprite de base
            preload_scaled_sprite(sprite_mapping.row, sprite_mapping.col)
            scaled_sprites_count += 1
            self.total_loaded += 1
            
            # Précharger les sprites personnalisés si définis
            if sprite_mapping.first_sprite_row is not None and sprite_mapping.first_sprite_col is not None:
                preload_scaled_sprite(sprite_mapping.first_sprite_row, sprite_mapping.first_sprite_col)
                scaled_sprites_count += 1
                self.total_loaded += 1
            
            if sprite_mapping.last_sprite_row is not None and sprite_mapping.last_sprite_col is not None:
                preload_scaled_sprite(sprite_mapping.last_sprite_row, sprite_mapping.last_sprite_col)
                scaled_sprites_count += 1
                self.total_loaded += 1
            
            # Mettre à jour la progression après chaque sprite redimensionné
            self._update_progress("Sprites de niveau", count + scaled_sprites_count, total_items)
            pygame.event.pump()
        
        if scaled_sprites_count > 0:
            print(f"[Préchargement]   - Sprites redimensionnés préchargés : {scaled_sprites_count} images")
            count += scaled_sprites_count
        
        return count
    
    def _preload_player_sprites(
        self,
        stats_config: Optional["PlayerStatsConfig"],
        player_level: int,
    ) -> int:
        """Précharge tous les sprites du joueur avec progression continue.
        
        Args:
            stats_config: Configuration des stats du joueur
            player_level: Niveau initial du joueur
            
        Returns:
            Nombre total de frames chargées
        """
        from ..entities.player_level_manager import PlayerLevelManager
        from ..rendering.config import compute_design_scale, get_render_size
        
        max_lv = stats_config.max_level if stats_config is not None else MAX_PLAYER_LEVEL
        # 1. Calculer le total avant de commencer (estimation)
        total_items = max_lv * 3 * 32  # Estimation
        
        total_frames = 0
        assets_root = self.project_root / "sprite" / "personnage"
        
        # Calculer le scaling (même logique que dans Player.__init__)
        render_width, render_height = get_render_size()
        scale_x, scale_y = compute_design_scale((render_width, render_height))
        
        # Utiliser le même sprite_scale que Player (défaut: 2.0)
        sprite_scale = 2.0
        sprite_width = 64
        sprite_height = 64
        
        # Calculer les dimensions d'affichage (même logique que dans Player.__init__)
        # Étape 1 : Appliquer le sprite_scale dans le repère 1920x1080
        scaled_width_in_design = sprite_width * sprite_scale
        scaled_height_in_design = sprite_height * sprite_scale
        # Étape 2 : Convertir vers la résolution interne 1280x720
        display_width = int(scaled_width_in_design * scale_x)
        display_height = int(scaled_height_in_design * scale_y)
        
        # Précharger pour tous les niveaux (1 à max_level)
        for level in range(1, max_lv + 1):
            try:
                level_manager = PlayerLevelManager(assets_root, level, stats_config)
                
                # Charger les sprite sheets du niveau
                walk_frames = 0
                jump_frames = 0
                climb_frames = 0
                
                # Précharger walk.png
                try:
                    walk_path = level_manager.get_asset_path("walk.png")
                    walk_path_key = str(Path(walk_path).resolve())
                    walk_sheet = pygame.image.load(str(walk_path)).convert_alpha()
                    # Mettre en cache global le sprite sheet
                    _global_player_sprite_sheet_cache[walk_path_key] = walk_sheet
                    self.total_loaded += 1
                    self._update_progress("Sprites du joueur", total_frames, total_items)
                    pygame.event.pump()
                    
                    # Extraire toutes les frames (4 lignes, 8 colonnes) et les redimensionner
                    for row in range(4):
                        for col in range(8):
                            x = col * 64
                            y = row * 64
                            if x + 64 <= walk_sheet.get_width() and y + 64 <= walk_sheet.get_height():
                                rect = pygame.Rect(x, y, 64, 64)
                                frame = walk_sheet.subsurface(rect).copy()
                                frame = frame.convert_alpha()
                                # Redimensionner avec le scaling
                                scaled_frame = pygame.transform.smoothscale(
                                    frame, (display_width, display_height)
                                )
                                scaled_frame = scaled_frame.convert_alpha()
                                # Mettre en cache global
                                cache_key = (level, "walk", row, col, display_width, display_height)
                                _global_player_scaled_sprite_cache[cache_key] = scaled_frame
                                walk_frames += 1
                                total_frames += 1
                                self.total_loaded += 1
                                
                                # Mettre à jour la progression après chaque frame (ou par lots)
                                if (row * 8 + col) % 8 == 0:  # Toutes les 8 frames
                                    self._update_progress("Sprites du joueur", total_frames, total_items)
                                    pygame.event.pump()
                except Exception as e:
                    print(f"[Préchargement]   - Niveau {level} walk.png : {e}")
                
                # Précharger jump.png
                try:
                    jump_path = level_manager.get_asset_path("jump.png")
                    jump_path_key = str(Path(jump_path).resolve())
                    jump_sheet = pygame.image.load(str(jump_path)).convert_alpha()
                    # Mettre en cache global le sprite sheet
                    _global_player_sprite_sheet_cache[jump_path_key] = jump_sheet
                    self.total_loaded += 1
                    self._update_progress("Sprites du joueur", total_frames, total_items)
                    pygame.event.pump()
                    
                    # Extraire toutes les frames (4 lignes, 8 colonnes) et les redimensionner
                    for row in range(4):
                        for col in range(8):
                            x = col * 64
                            y = row * 64
                            if x + 64 <= jump_sheet.get_width() and y + 64 <= jump_sheet.get_height():
                                rect = pygame.Rect(x, y, 64, 64)
                                frame = jump_sheet.subsurface(rect).copy()
                                frame = frame.convert_alpha()
                                # Redimensionner avec le scaling
                                scaled_frame = pygame.transform.smoothscale(
                                    frame, (display_width, display_height)
                                )
                                scaled_frame = scaled_frame.convert_alpha()
                                # Mettre en cache global
                                cache_key = (level, "jump", row, col, display_width, display_height)
                                _global_player_scaled_sprite_cache[cache_key] = scaled_frame
                                jump_frames += 1
                                total_frames += 1
                                self.total_loaded += 1
                                
                                # Mettre à jour la progression après chaque frame (ou par lots)
                                if (row * 8 + col) % 8 == 0:  # Toutes les 8 frames
                                    self._update_progress("Sprites du joueur", total_frames, total_items)
                                    pygame.event.pump()
                except Exception as e:
                    print(f"[Préchargement]   - Niveau {level} jump.png : {e}")
                
                # Précharger climb.png (optionnel)
                try:
                    climb_path = level_manager.get_asset_path("climb.png")
                    climb_path_key = str(Path(climb_path).resolve())
                    climb_sheet = pygame.image.load(str(climb_path)).convert_alpha()
                    # Mettre en cache global le sprite sheet
                    _global_player_sprite_sheet_cache[climb_path_key] = climb_sheet
                    self.total_loaded += 1
                    self._update_progress("Sprites du joueur", total_frames, total_items)
                    pygame.event.pump()
                    
                    # Extraire toutes les frames (4 lignes, 8 colonnes) et les redimensionner
                    for row in range(4):
                        for col in range(8):
                            x = col * 64
                            y = row * 64
                            if x + 64 <= climb_sheet.get_width() and y + 64 <= climb_sheet.get_height():
                                rect = pygame.Rect(x, y, 64, 64)
                                frame = climb_sheet.subsurface(rect).copy()
                                frame = frame.convert_alpha()
                                # Redimensionner avec le scaling
                                scaled_frame = pygame.transform.smoothscale(
                                    frame, (display_width, display_height)
                                )
                                scaled_frame = scaled_frame.convert_alpha()
                                # Mettre en cache global
                                cache_key = (level, "climb", row, col, display_width, display_height)
                                _global_player_scaled_sprite_cache[cache_key] = scaled_frame
                                climb_frames += 1
                                total_frames += 1
                                self.total_loaded += 1
                                
                                # Mettre à jour la progression après chaque frame (ou par lots)
                                if (row * 8 + col) % 8 == 0:  # Toutes les 8 frames
                                    self._update_progress("Sprites du joueur", total_frames, total_items)
                                    pygame.event.pump()
                except Exception:
                    # climb.png est optionnel, pas d'erreur si absent
                    pass
                
                level_total = walk_frames + jump_frames + climb_frames
                
                print(
                    f"[Préchargement]   - Niveau {level} : {level_total} frames chargées "
                    f"(walk: {walk_frames}, jump: {jump_frames}, climb: {climb_frames}) "
                    f"avec scaling {sprite_scale}x -> {display_width}x{display_height}"
                )
                
                # Mettre à jour la progression après chaque niveau
                self._update_progress("Sprites du joueur", total_frames, total_items)
                pygame.event.pump()
            except Exception as e:
                print(f"[Préchargement]   - Erreur lors du préchargement du niveau {level}: {e}")
        
        return total_frames
    
    def _extract_all_frames(
        self,
        sheet: pygame.Surface,
        sprite_width: int,
        sprite_height: int,
        num_rows: int,
        num_cols: int,
    ) -> list[pygame.Surface]:
        """Extrait toutes les frames d'un sprite sheet.
        
        Args:
            sheet: Sprite sheet à extraire
            sprite_width: Largeur d'un sprite
            sprite_height: Hauteur d'un sprite
            num_rows: Nombre de lignes
            num_cols: Nombre de colonnes
            
        Returns:
            Liste des frames extraites
        """
        frames = []
        sheet_width = sheet.get_width()
        sheet_height = sheet.get_height()
        
        for row in range(num_rows):
            for col in range(num_cols):
                x = col * sprite_width
                y = row * sprite_height
                
                # Vérifier que le sprite est dans les limites
                if x + sprite_width <= sheet_width and y + sprite_height <= sheet_height:
                    rect = pygame.Rect(x, y, sprite_width, sprite_height)
                    try:
                        sprite = sheet.subsurface(rect).copy()
                        sprite = sprite.convert_alpha()
                        frames.append(sprite)
                    except (ValueError, pygame.error):
                        pass
        
        return frames
    
    def _preload_npc_sprites(self, npcs_config: "NPCsConfig") -> int:
        """Précharge tous les sprites des PNJ avec progression continue.
        
        Args:
            npcs_config: Configuration des PNJ
            
        Returns:
            Nombre total d'images chargées (sprite sheets + sprites redimensionnés)
        """
        from ..rendering.config import compute_design_scale, get_render_size
        
        # 1. Calculer le total avant de commencer
        total_items = 0
        for npc_config in npcs_config.npcs:
            total_items += 1  # Sprite sheet
            if npc_config.animations:
                for anim_config in npc_config.animations.values():
                    total_items += anim_config.num_frames * 2  # Normal + flipped
        
        total_count = 0
        
        # Calculer le scaling (même logique que dans NPC.__init__)
        render_width, render_height = get_render_size()
        scale_x, scale_y = compute_design_scale((render_width, render_height))
        
        for npc_config in npcs_config.npcs:
            try:
                # Charger le sprite sheet du PNJ
                sprite_path = Path(npc_config.sprite_sheet_path)
                if not sprite_path.is_absolute():
                    sprite_path = self.project_root / sprite_path
                
                if sprite_path.exists():
                    sprite_sheet = pygame.image.load(str(sprite_path)).convert_alpha()
                    
                    # Mettre en cache global (clé: chemin absolu)
                    sprite_path_key = str(sprite_path.resolve())
                    _global_npc_sprite_sheet_cache[sprite_path_key] = sprite_sheet
                    
                    total_count += 1
                    self.total_loaded += 1
                    
                    # Mettre à jour la progression après le sprite sheet
                    self._update_progress("Sprites des PNJ", total_count, total_items)
                    pygame.event.pump()
                    
                    # Calculer les dimensions d'affichage (même logique que dans NPC.__init__)
                    # Étape 1 : Appliquer le sprite_scale dans le repère 1920x1080
                    scaled_width_in_design = npc_config.sprite_width * npc_config.sprite_scale
                    scaled_height_in_design = npc_config.sprite_height * npc_config.sprite_scale
                    # Étape 2 : Convertir vers la résolution interne 1280x720
                    display_width = int(scaled_width_in_design * scale_x)
                    display_height = int(scaled_height_in_design * scale_y)
                    
                    # Calculer les dimensions du sprite sheet
                    sheet_width = sprite_sheet.get_width()
                    sheet_height = sprite_sheet.get_height()
                    num_cols = sheet_width // npc_config.sprite_width
                    num_rows = sheet_height // npc_config.sprite_height
                    
                    # Précharger tous les sprites utilisés par les animations
                    scaled_sprites_count = 0
                    if npc_config.animations:
                        # Précharger tous les sprites de chaque animation
                        for anim_config in npc_config.animations.values():
                            row = anim_config.row
                            num_frames = anim_config.num_frames
                            
                            # Précharger chaque frame de l'animation
                            for col in range(num_frames):
                                # Vérifier que le sprite est dans les limites
                                if row < num_rows and col < num_cols:
                                    # Extraire le sprite
                                    x = col * npc_config.sprite_width
                                    y = row * npc_config.sprite_height
                                    
                                    # Valider que le rectangle d'extraction reste dans les limites
                                    if x + npc_config.sprite_width <= sheet_width and y + npc_config.sprite_height <= sheet_height:
                                        rect = pygame.Rect(x, y, npc_config.sprite_width, npc_config.sprite_height)
                                        
                                        try:
                                            sprite = sprite_sheet.subsurface(rect).copy()
                                            sprite = sprite.convert_alpha()
                                            
                                            # Redimensionner le sprite si nécessaire
                                            if npc_config.sprite_scale != 1.0:
                                                cache_key = (sprite_path_key, row, col, display_width, display_height)
                                                
                                                # Vérifier si déjà en cache
                                                if cache_key not in _global_npc_scaled_sprite_cache:
                                                    scaled_sprite = pygame.transform.smoothscale(
                                                        sprite, (display_width, display_height)
                                                    )
                                                    scaled_sprite = scaled_sprite.convert_alpha()
                                                    _global_npc_scaled_sprite_cache[cache_key] = scaled_sprite
                                                    
                                                    # Précharger aussi la version retournée
                                                    flipped_sprite = pygame.transform.flip(scaled_sprite, True, False)
                                                    flipped_sprite = flipped_sprite.convert_alpha()
                                                    _global_npc_scaled_flipped_sprite_cache[cache_key] = flipped_sprite
                                                    
                                                    scaled_sprites_count += 2  # Normal + flipped
                                                    total_count += 2
                                                    self.total_loaded += 2
                                                    
                                                    # Mettre à jour la progression après chaque sprite (ou par lots)
                                                    if scaled_sprites_count % 4 == 0:  # Toutes les 4 sprites
                                                        self._update_progress("Sprites des PNJ", total_count, total_items)
                                                        pygame.event.pump()
                                        except (ValueError, pygame.error):
                                            pass
                    
                    print(
                        f"[Préchargement]   - PNJ '{npc_config.id}' : "
                        f"1 sprite sheet + {scaled_sprites_count} sprites redimensionnés chargés "
                        f"(scaling {npc_config.sprite_scale}x -> {display_width}x{display_height})"
                    )
                    
                    # Mettre à jour la progression après chaque PNJ
                    self._update_progress("Sprites des PNJ", total_count, total_items)
                    pygame.event.pump()
                else:
                    print(f"[Préchargement]   - PNJ '{npc_config.id}' : sprite sheet introuvable")
            except Exception as e:
                print(f"[Préchargement]   - Erreur lors du préchargement du PNJ '{npc_config.id}': {e}")
        
        return total_count
    
    def _preload_inventory_sprites(
        self,
        inventory_config: Optional["InventoryItemConfig"],
    ) -> int:
        """Précharge tous les sprites d'inventaire avec progression continue.
        
        Args:
            inventory_config: Configuration des objets d'inventaire
            
        Returns:
            Nombre total d'images chargées (sprite sheets + sprites extraits)
        """
        if inventory_config is None:
            return 0
        
        # 1. Calculer le total avant de commencer
        total_items = len(inventory_config.items) * 2  # Sprite sheet + sprite extrait (estimation)
        
        sprite_sheets_count = 0
        sprites_count = 0
        total_count = 0
        
        # Charger tous les sprite sheets et extraire les sprites dans les caches globaux
        for item_id, item in inventory_config.items.items():
            try:
                # Charger le sprite sheet (si pas déjà en cache)
                sprite_path_str = str(item.sprite_path)
                if sprite_path_str not in _global_inventory_sprite_sheet_cache:
                    sprite_sheet = pygame.image.load(sprite_path_str).convert_alpha()
                    _global_inventory_sprite_sheet_cache[sprite_path_str] = sprite_sheet
                    sprite_sheets_count += 1
                    total_count += 1
                    self.total_loaded += 1
                    
                    # Mettre à jour la progression après chaque sprite sheet
                    self._update_progress("Sprites d'inventaire", total_count, total_items)
                    pygame.event.pump()
                else:
                    sprite_sheet = _global_inventory_sprite_sheet_cache[sprite_path_str]
                
                # Extraire le sprite (si pas déjà en cache)
                if item_id not in _global_inventory_cached_surfaces:
                    sprite = item._extract_cell(sprite_sheet)
                    _global_inventory_cached_surfaces[item_id] = sprite
                    sprites_count += 1
                    total_count += 1
                    self.total_loaded += 1
                    
                    # Mettre à jour la progression après chaque sprite extrait
                    self._update_progress("Sprites d'inventaire", total_count, total_items)
                    pygame.event.pump()
            except Exception as e:
                print(f"[Préchargement]   - Erreur lors du préchargement de l'objet '{item_id}': {e}")
        
        print(
            f"[Préchargement]   - Sprite sheets : {sprite_sheets_count} images chargées"
        )
        print(
            f"[Préchargement]   - Sprites extraits : {sprites_count} images chargées"
        )
        
        return sprite_sheets_count + sprites_count
    
    def _preload_dialogue_images(self, npcs_config: "NPCsConfig") -> int:
        """Précharge toutes les images de dialogue avec progression continue.
        
        Args:
            npcs_config: Configuration des PNJ
            
        Returns:
            Nombre total d'images chargées
        """
        from ..ui.speech_bubble import _global_image_cache
        
        # 1. Calculer le total avant de commencer
        total_items = 0
        for npc_config in npcs_config.npcs:
            if npc_config.dialogue_blocks:
                for dialogue_block in npc_config.dialogue_blocks:
                    for exchange in dialogue_block.exchanges:
                        if exchange.image_path:
                            total_items += 1
        
        if total_items == 0:
            return 0
        
        image_assets_root = self.project_root / "image"
        assets_root_path = Path(image_assets_root)
        count = 0
        
        # 2. Charger les images une par une avec mise à jour de progression
        for npc_config in npcs_config.npcs:
            if npc_config.dialogue_blocks is None:
                continue
            
            # Parcourir tous les blocs de dialogue
            for dialogue_block in npc_config.dialogue_blocks:
                # Parcourir tous les échanges
                for exchange in dialogue_block.exchanges:
                    if exchange.image_path is None:
                        continue
                    
                    try:
                        # Résoudre le chemin (relatif à assets_root ou absolu)
                        if not Path(exchange.image_path).is_absolute():
                            image_full_path = assets_root_path / exchange.image_path
                        else:
                            image_full_path = Path(exchange.image_path)
                        
                        # Utiliser le chemin absolu comme clé pour le cache global
                        image_cache_key = str(image_full_path.resolve())
                        
                        # Vérifier si l'image est déjà en cache
                        if image_cache_key in _global_image_cache:
                            continue
                        
                        # Charger l'image avec convert_alpha() pour optimiser le rendu
                        image = pygame.image.load(str(image_full_path)).convert_alpha()
                        
                        # Mettre en cache global
                        _global_image_cache[image_cache_key] = image
                        count += 1
                        self.total_loaded += 1
                        
                        # Mettre à jour la progression après chaque image
                        self._update_progress("Images de dialogue", count, total_items)
                        pygame.event.pump()
                    except (FileNotFoundError, pygame.error) as e:
                        # En cas d'erreur, log un avertissement mais continuer
                        print(f"[Préchargement]   - Warning: Impossible de précharger l'image {exchange.image_path}: {e}")
        
        print(f"[Préchargement]   - {count} images de dialogue chargées")
        
        return count
    
    def _update_progress(self, category: str, current: int, total: int) -> None:
        """Met à jour la progression et redessine la barre de chargement.
        
        Cette méthode doit être appelée régulièrement pendant le chargement de chaque catégorie,
        après chaque élément chargé (sprite sheet, sprite extrait, frame, etc.).
        
        Args:
            category: Nom de la catégorie en cours
            current: Nombre d'éléments chargés dans la catégorie actuelle
            total: Nombre total d'éléments dans la catégorie actuelle
        """
        self.current_category = category
        self.current_count = current
        self.current_total = total
        
        # Calculer la progression globale basée sur le nombre total d'éléments chargés
        # La progression globale prend en compte toutes les catégories
        if self.total_to_load > 0:
            self.progress = min(self.total_loaded / self.total_to_load, 1.0)
        else:
            self.progress = 0.0
        
        # Redessiner la barre de chargement
        self.loading_bar.draw(
            self.progress,
            self.current_category,
            self.current_count,
            self.current_total,
        )
        
        # Important : Appeler pygame.event.pump() pour maintenir la réactivité de la fenêtre
        # Cette méthode est appelée depuis les méthodes _preload_* qui doivent aussi appeler
        # pygame.event.pump() après chaque mise à jour
    
    def _log_category_start(self, category: str) -> None:
        """Log le début d'une catégorie."""
        print(f"[Préchargement] Chargement des {category.lower()}...")
    
    def _log_category_end(self, category: str, count: int) -> None:
        """Log la fin d'une catégorie."""
        print(f"[Préchargement] {category} chargés : {count} images au total")
    
    def _log_total(self) -> None:
        """Log le total final."""
        print(f"[Préchargement] Préchargement terminé : {self.total_loaded} images chargées au total")
