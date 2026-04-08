"""Module de gestion des bulles de dialogue."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Protocol, Tuple, Union

import pygame

from ..rendering.config import compute_design_scale, compute_scale, get_render_size


# Cache global pour les images de dialogue (évite de recharger les mêmes images)
# Clé: chemin absolu de l'image (str), Valeur: Surface pygame
_global_image_cache: Dict[str, pygame.Surface] = {}


def preload_dialogue_images(npcs_config, assets_root: Path = Path("image")) -> None:
    """Précharge toutes les images de dialogue depuis la configuration des PNJ.
    
    Cette fonction parcourt tous les blocs de dialogue et échanges pour trouver
    toutes les images référencées, puis les charge dans le cache global.
    Cela évite les freezes lors de l'affichage des dialogues avec images.
    
    Args:
        npcs_config: Configuration des PNJ (NPCsConfig) contenant tous les dialogues
        assets_root: Répertoire de base pour résoudre les chemins d'images relatifs (défaut: "image")
    """
    assets_root_path = Path(assets_root)
    images_loaded = 0
    images_failed = 0
    
    # Parcourir tous les PNJ
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
                    images_loaded += 1
                except (FileNotFoundError, pygame.error) as e:
                    # En cas d'erreur, log un avertissement mais continuer
                    print(f"Warning: Impossible de précharger l'image {exchange.image_path}: {e}")
                    images_failed += 1
    
    if images_loaded > 0:
        print(f"Images de dialogue préchargées : {images_loaded} image(s)")
    if images_failed > 0:
        print(f"Warning: {images_failed} image(s) n'ont pas pu être préchargée(s)")


def _calculate_scale_factor() -> float:
    """Calcule le facteur d'échelle basé sur la résolution logique de rendu.
    
    Utilise d'abord la taille de la surface logique (`pygame.display.get_surface()`),
    ce qui garantit un comportement identique quel que soit le backend de scaling
    (hardware Metal ou software). Si la surface n'est pas disponible (ex: avant
    la création de la fenêtre), on retombe sur la taille physique de la fenêtre.
    """
    display_size: Optional[Tuple[int, int]] = None

    try:
        surface = pygame.display.get_surface()
        if surface is not None:
            display_size = surface.get_size()
    except (pygame.error, AttributeError):
        display_size = None

    if not display_size or display_size[0] <= 0 or display_size[1] <= 0:
        try:
            display_size = pygame.display.get_window_size()
        except (pygame.error, AttributeError):
            display_size = None

    if not display_size or display_size[0] <= 0 or display_size[1] <= 0:
        return 1.0

    scale_factor = compute_scale(display_size)
    return max(0.5, min(2.0, scale_factor))


class CharacterProtocol(Protocol):
    """Protocole définissant l'interface minimale requise pour un personnage."""

    x: float
    y: float
    sprite_width: int
    sprite_height: int
    display_width: float
    display_height: float


class SpeechBubble:
    """Représente une bulle de dialogue associée à un personnage."""

    def __init__(
        self,
        text: str,
        character: CharacterProtocol,
        side: str = "right",
        font: Optional[pygame.font.Font] = None,
        font_size: int = 40,
        padding: int = 10,
        tail_size: int = 35,
        bg_color: Tuple[int, int, int] = (255, 255, 255),
        text_color: Tuple[int, int, int] = (0, 0, 0),
        border_color: Tuple[int, int, int] = (0, 0, 0),
        border_width: int = 2,
        line_spacing: int = 2,
        offset_y: float = -80.0,
        text_speed: float = 30.0,
        image_path: Optional[Union[str, Path]] = None,
        assets_root: Optional[Path] = None,
        image_spacing: int = 8,
    ) -> None:
        """Initialise une bulle de dialogue.

        Args:
            text: Texte à afficher dans la bulle (peut être vide si une image est présente)
            character: Entité (personnage) associée à la bulle
            side: Position de la bulle ("left" ou "right")
            font: Police à utiliser (optionnel, utilise une police par défaut si None)
            font_size: Taille de la police en pixels
            padding: Espacement interne entre le contenu (texte/image) et les bords de la bulle
            tail_size: Taille de la queue/pointe en pixels
            bg_color: Couleur de fond de la bulle (RGB)
            text_color: Couleur du texte (RGB)
            border_color: Couleur de la bordure (RGB)
            border_width: Épaisseur de la bordure en pixels
            line_spacing: Espacement vertical entre les lignes de texte en pixels
            offset_y: Offset vertical pour positionner la bulle au-dessus du personnage
            text_speed: Vitesse d'affichage du texte en caractères par seconde (défaut: 30.0)
            image_path: Chemin vers l'image à afficher dans la bulle (optionnel, relatif à assets_root ou absolu)
            assets_root: Répertoire de base pour résoudre les chemins d'images relatifs (optionnel)
            image_spacing: Espacement vertical entre l'image et le texte en pixels (défaut: 8)
        """
        self.text = text
        self.character = character
        self.side = side
        self.padding = padding
        self.tail_size = tail_size
        self.bg_color = bg_color
        self.text_color = text_color
        self.border_color = border_color
        self.border_width = border_width
        self.line_spacing = line_spacing
        self.offset_y = offset_y
        self.text_speed = text_speed
        self.image_path = image_path
        self.assets_root = Path(assets_root) if assets_root else None
        self.image_spacing = image_spacing
        self._image_surface: Optional[pygame.Surface] = None  # Image originale (non redimensionnée)
        self._scaled_image_surface: Optional[pygame.Surface] = None  # Image redimensionnée (calculée si nécessaire)
        # Cache pour les images redimensionnées (clé: (target_width, target_height))
        # Évite de recalculer le redimensionnement si les dimensions n'ont pas changé
        self._scaled_image_cache: Dict[Tuple[int, int], pygame.Surface] = {}
        self._last_scaled_dimensions: Optional[Tuple[int, int]] = None

        # État de l'animation du texte
        self._displayed_chars: int = 0
        self._text_complete: bool = False
        self._accumulated_time: float = 0.0
        self._last_displayed_chars: int = 0  # Pour optimiser la recréation de la surface

        # Dimensions calculées pour le corps de la bulle et la queue
        self._bubble_body_height: int = 0
        self._tail_base_height: int = 0
        self._tail_tip_offset_x: int = 0
        self._tail_tip_offset_y: int = 0
        self._tail_control_offset_x: int = 0
        self._tail_control_offset_y: int = 0

        # Convertir les valeurs de base du repère de conception (1920x1080) vers la résolution interne (1280x720 ou autre)
        render_width, render_height = get_render_size()
        scale_x, scale_y = compute_design_scale((render_width, render_height))
        # Convertir du repère 1920x1080 vers la résolution interne (1280x720, 1536x864, etc.)
        # IMPORTANT : Les bulles sont rendues sur la surface interne qui sera automatiquement
        # mise à l'échelle vers l'écran réel. On ne doit donc PAS appliquer de facteur d'échelle
        # supplémentaire basé sur la taille d'affichage réelle, car cela créerait une double mise à l'échelle.
        # Si on appliquait _scale_factor (qui dépend de RENDER_WIDTH via compute_scale), le texte
        # deviendrait plus petit quand on augmente RENDER_WIDTH, ce qui est incorrect.
        converted_font_size = int(font_size * scale_y)
        converted_padding = int(padding * scale_y)
        converted_tail_size = int(tail_size * scale_y)
        converted_border_width = int(border_width * scale_y)
        converted_line_spacing = int(line_spacing * scale_y)
        converted_image_spacing = int(image_spacing * scale_y)
        converted_offset_y = offset_y * scale_y
        
        # Stocker les valeurs converties (utilisées directement, sans facteur d'échelle supplémentaire)
        self._base_font_size = converted_font_size
        self._base_padding = converted_padding
        self._base_tail_size = converted_tail_size
        self._base_border_width = converted_border_width
        self._base_line_spacing = converted_line_spacing
        self._base_image_spacing = converted_image_spacing
        self._base_offset_y = converted_offset_y
        
        # Utiliser directement les valeurs converties (pas de facteur d'échelle supplémentaire)
        # La surface interne sera automatiquement mise à l'échelle vers l'écran réel lors du blit
        self.padding = converted_padding
        self.tail_size = converted_tail_size
        self.border_width = converted_border_width
        self.line_spacing = converted_line_spacing
        self.image_spacing = converted_image_spacing
        self.offset_y = converted_offset_y
        
        # Initialiser la police avec la taille convertie
        # IMPORTANT : L'utilisateur fournit toujours font_size dans le repère de conception (1920x1080),
        # qui est converti vers la résolution interne. La mise à l'échelle vers l'écran réel se fait
        # automatiquement lors du blit de la surface interne vers l'écran.
        # Debug: afficher les valeurs pour vérifier la conversion
        # print(f"SpeechBubble font_size: design={font_size}, converted={converted_font_size}")
        try:
            self.font = pygame.font.SysFont("arial", converted_font_size, bold=True)
        except pygame.error:
            self.font = pygame.font.SysFont("sans-serif", converted_font_size, bold=True)

        # Créer la surface de la bulle (sera recréée lors du premier update avec l'animation)
        self.surface: Optional[pygame.Surface] = None
        self.rect = pygame.Rect(0, 0, 0, 0)

    def _calculate_text_dimensions(self) -> Tuple[int, int]:
        """Calcule les dimensions nécessaires pour afficher le texte.

        Les dimensions sont calculées en fonction du texte fourni, en utilisant
        les caractères \n pour déterminer les lignes. La bulle s'adapte au texte.
        """
        # Séparer le texte en lignes selon les \n
        lines = self.text.split("\n")

        if not lines:
            # Texte vide
            return 0, 0

        # Filtrer les lignes vides
        non_empty_lines = [line for line in lines if line]

        if not non_empty_lines:
            return 0, 0

        # Calculer la largeur maximale parmi toutes les lignes non vides
        max_line_width = max(self.font.size(line)[0] for line in non_empty_lines)

        # Calculer la hauteur totale : somme des hauteurs de chaque ligne + espacement
        line_height = self.font.get_height()
        num_lines = len(non_empty_lines)
        total_height = num_lines * line_height

        # Ajouter l'espacement entre les lignes (sauf pour la dernière)
        if num_lines > 1:
            total_height += (num_lines - 1) * self.line_spacing

        return max_line_width, total_height

    def _load_image(self) -> Optional[pygame.Surface]:
        """Charge l'image depuis le chemin spécifié (avec mise en cache globale).
        
        Utilise un cache global pour éviter de recharger les mêmes images plusieurs fois,
        ce qui réduit significativement les freezes lors de l'affichage de dialogues avec images.
        
        Returns:
            Surface pygame de l'image chargée, ou None si le chargement échoue ou si aucun chemin n'est fourni
        """
        if self.image_path is None:
            return None
        
        # Si l'image est déjà en cache local, la retourner
        if self._image_surface is not None:
            return self._image_surface
        
        try:
            # Résoudre le chemin (relatif à assets_root ou absolu)
            if self.assets_root is not None and not Path(self.image_path).is_absolute():
                image_full_path = self.assets_root / self.image_path
            else:
                image_full_path = Path(self.image_path)
            
            # Utiliser le chemin absolu comme clé pour le cache global
            image_cache_key = str(image_full_path.resolve())
            
            # Vérifier le cache global d'abord
            if image_cache_key in _global_image_cache:
                # Utiliser l'image du cache global
                cached_image = _global_image_cache[image_cache_key]
                # Créer une copie pour éviter les problèmes de référence partagée
                # (bien que pygame.Surface soit immutable pour la plupart des opérations)
                self._image_surface = cached_image
                return cached_image
            
            # Charger l'image avec convert_alpha() pour optimiser le rendu
            image = pygame.image.load(str(image_full_path)).convert_alpha()
            
            # Mettre en cache global (limiter la taille du cache pour éviter les fuites mémoire)
            if len(_global_image_cache) > 50:
                # Nettoyer le cache si trop d'entrées (garder seulement les 30 plus récentes)
                keys_to_remove = list(_global_image_cache.keys())[:-30]
                for key in keys_to_remove:
                    del _global_image_cache[key]
            
            _global_image_cache[image_cache_key] = image
            
            # Mettre en cache local aussi
            self._image_surface = image
            return image
        except (FileNotFoundError, pygame.error) as e:
            # En cas d'erreur, ignorer l'image et continuer avec le texte uniquement
            print(f"Warning: Impossible de charger l'image {self.image_path}: {e}")
            self._image_surface = None
            return None

    def _calculate_max_bubble_size(self) -> Tuple[int, int]:
        """Calcule la taille maximale de la bulle en fonction de l'écran et du personnage.
        
        Cette méthode est utilisée uniquement lorsqu'une image est présente.
        La bulle prend le maximum d'espace tout en laissant la vision du personnage.
        
        IMPORTANT : Utilise la taille de la surface interne (1280x720) car les bulles
        sont dessinées sur la surface interne, pas sur la surface d'affichage réelle.
        
        Returns:
            Tuple (largeur_max, hauteur_max) en pixels
        """
        # Utiliser la taille de la surface interne (1280x720) car les bulles sont
        # dessinées sur la surface interne, pas sur la surface d'affichage réelle
        screen_width, screen_height = get_render_size()
        
        # CORRECTION : Garder les marges SEULEMENT EN BAS pour afficher le joueur
        # Les marges gauche, haut, droite sont réduites à 0 pour maximiser l'espace
        # Convertir les marges du repère de conception (1920x1080) vers la résolution interne (1280x720)
        render_width, render_height = get_render_size()
        _, scale_y = compute_design_scale((render_width, render_height))
        person_height_reserved_design = 200  # Espace réservé pour le personnage en bas (repère 1920x1080)
        # Marge du bas réduite pour maximiser l'espace disponible pour les images haute résolution
        margin_bottom_design = 50  # Marge du bas pour laisser de l'espace au personnage (repère 1920x1080)
        person_height_reserved = int(person_height_reserved_design * scale_y)
        margin_left = 0  # Pas de marge à gauche
        margin_top = 0  # Pas de marge en haut
        margin_right = 0  # Pas de marge à droite
        margin_bottom = int(margin_bottom_design * scale_y)
        
        # Hauteur maximale : écran moins l'espace réservé en bas
        max_height = screen_height - margin_bottom
        
        # Largeur maximale : écran entier (pas de marges latérales)
        max_width = screen_width
        
        return max_width, max_height

    def _scale_image_to_fit(self, target_width: int, target_height: int) -> Optional[pygame.Surface]:
        """Redimensionne l'image pour qu'elle rentre dans les dimensions cibles en préservant les proportions.
        
        Utilise smoothscale pour une meilleure qualité de redimensionnement, particulièrement
        important pour les images haute résolution.
        
        Utilise un cache pour éviter de recalculer le redimensionnement si les dimensions n'ont pas changé.
        
        Args:
            target_width: Largeur cible en pixels
            target_height: Hauteur cible en pixels
        
        Returns:
            Surface pygame de l'image redimensionnée, ou None si aucune image n'est chargée
        """
        original_image = self._load_image()
        if original_image is None:
            return None
        
        # Vérifier le cache
        cache_key = (target_width, target_height)
        if cache_key in self._scaled_image_cache:
            return self._scaled_image_cache[cache_key]
        
        original_width = original_image.get_width()
        original_height = original_image.get_height()
        
        # Calculer le ratio de redimensionnement pour préserver les proportions
        width_ratio = target_width / original_width
        height_ratio = target_height / original_height
        scale_ratio = min(width_ratio, height_ratio)  # Prendre le plus petit pour que l'image rentre
        
        # Calculer les nouvelles dimensions
        new_width = int(original_width * scale_ratio)
        new_height = int(original_height * scale_ratio)
        
        # OPTIMISATION: Éviter smoothscale si la taille cible est identique à la taille originale
        target_size = (new_width, new_height)
        if original_image.get_size() == target_size:
            # Pas besoin de redimensionner, utiliser directement l'image originale
            scaled_image = original_image
        else:
            # Utiliser smoothscale pour une meilleure qualité de redimensionnement
            # Cela est particulièrement important pour les images haute résolution
            # qui sont redimensionnées vers le bas, car smoothscale utilise un algorithme
            # de lissage qui préserve mieux les détails que scale()
            scaled_image = pygame.transform.smoothscale(original_image, target_size)
        
        # Mettre en cache (limiter la taille du cache pour éviter les fuites mémoire)
        if len(self._scaled_image_cache) > 10:
            # Nettoyer le cache si trop d'entrées (garder seulement les 5 plus récentes)
            keys_to_remove = list(self._scaled_image_cache.keys())[:-5]
            for key in keys_to_remove:
                del self._scaled_image_cache[key]
        
        self._scaled_image_cache[cache_key] = scaled_image
        return scaled_image

    def _calculate_content_dimensions(self) -> Tuple[int, int]:
        """Calcule les dimensions nécessaires pour afficher le contenu (texte et/ou image).
        
        Si une image est présente, la bulle prend le maximum d'espace disponible.
        Sinon, les dimensions sont basées uniquement sur le texte.
        
        Returns:
            Tuple (largeur, hauteur) en pixels
        """
        text_width, text_height = self._calculate_text_dimensions()
        image = self._load_image()
        
        if image is None:
            # Pas d'image, dimensions basées uniquement sur le texte
            return text_width, text_height
        
        # Avec image : calculer la taille maximale de la bulle
        max_bubble_width, max_bubble_height = self._calculate_max_bubble_size()
        
        # Réserver de l'espace pour le texte si présent
        text_space = 0
        if text_width > 0 and text_height > 0:
            text_space = text_height + self.image_spacing
        
        # Espace disponible pour l'image = hauteur max moins padding et espace texte
        available_height = max_bubble_height - self.padding * 2 - text_space
        available_width = max_bubble_width - self.padding * 2
        
        # Redimensionner l'image pour qu'elle rentre dans l'espace disponible
        scaled_image = self._scale_image_to_fit(available_width, available_height)
        if scaled_image is None:
            # Si le redimensionnement échoue, utiliser l'image originale
            scaled_image = image
        
        image_width = scaled_image.get_width()
        image_height = scaled_image.get_height()
        
        # Stocker l'image redimensionnée pour le rendu
        self._scaled_image_surface = scaled_image
        
        # Dimensions du contenu : largeur = max(texte, image), hauteur = image + texte + espacement
        content_width = max(text_width, image_width)
        content_height = image_height
        if text_width > 0 and text_height > 0:
            content_height += self.image_spacing + text_height
        
        return content_width, content_height

    def _render_text(self) -> pygame.Surface:
        """Génère la surface du texte multi-lignes avec animation progressive.

        Le texte est rendu ligne par ligne, en utilisant les \n comme séparateurs.
        Seuls les caractères jusqu'à _displayed_chars sont affichés.
        """
        if not self.text:
            # Retourner une surface vide
            return pygame.Surface((0, 0), pygame.SRCALPHA)

        # Calculer les dimensions basées sur le texte complet (pour la taille de la bulle)
        text_width, text_height = self._calculate_text_dimensions()
        
        # Ajouter de l'espace pour le contour (2 pixels de chaque côté * 2 couches = 4 pixels par côté)
        outline_thickness = 2
        extra_width = outline_thickness * 2
        extra_height = outline_thickness * 2
        
        # Créer la surface pour le texte
        text_surface = pygame.Surface((text_width + extra_width, text_height + extra_height), pygame.SRCALPHA)

        # Diviser le texte complet en lignes
        all_lines = self.text.split("\n")

        # Rendre chaque ligne
        y_offset = 0
        line_height = self.font.get_height()
        char_index = 0

        for full_line in all_lines:
            if full_line:  # Ligne non vide dans le texte complet
                # Calculer combien de caractères de cette ligne doivent être affichés
                if char_index + len(full_line) <= self._displayed_chars:
                    # Toute la ligne est affichée
                    line_to_render = full_line
                    char_index += len(full_line) + 1  # +1 pour le \n
                elif char_index < self._displayed_chars:
                    # Seulement une partie de la ligne est affichée
                    chars_in_line = self._displayed_chars - char_index
                    line_to_render = full_line[:chars_in_line]
                    char_index = self._displayed_chars
                else:
                    # Cette ligne n'est pas encore affichée
                    line_to_render = ""

                if line_to_render:
                    # Rendre le texte avec un contour blanc pour améliorer la visibilité, comme pour les noms de PNJ
                    outline_thickness = 2  # Épaisseur fixe pour cohérence avec NPC.name (était variable avec scale_factor)
                    outline_color = (255, 255, 255)  # Contour blanc
                    
                    # Rendre le contour
                    for layer in range(outline_thickness):
                        offset = layer + 1
                        for dx in [-offset, 0, offset]:
                            for dy in [-offset, 0, offset]:
                                if dx != 0 or dy != 0:
                                    outline_surface = self.font.render(line_to_render, True, outline_color)
                                    text_surface.blit(outline_surface, (dx + outline_thickness, y_offset + dy + outline_thickness))
                    
                    # Rendre le texte principal par-dessus le contour
                    line_surface = self.font.render(line_to_render, True, self.text_color)
                    text_surface.blit(line_surface, (outline_thickness, y_offset + outline_thickness))

                y_offset += line_height + self.line_spacing
            else:
                # Ligne vide : avancer le compteur de caractères
                if char_index < self._displayed_chars:
                    char_index += 1  # Pour le \n
                y_offset += line_height + self.line_spacing

        return text_surface

    def _draw_tail(self, surface: pygame.Surface, position: Tuple[int, int], side: str) -> None:
        """Dessine la queue/pointe de la bulle.

        Args:
            surface: Surface sur laquelle dessiner
            position: Position du point d'attache (coin de la bulle)
            side: Côté de la bulle ("left" ou "right")
        """
        x, y = position
        tail_points: list[Tuple[int, int]] = []

        base_height = max(self._tail_base_height, 6)
        tip_offset_x = max(self._tail_tip_offset_x, 8)
        tip_offset_y = max(self._tail_tip_offset_y, 6)
        control_offset_x = max(self._tail_control_offset_x, 4)
        control_offset_y = max(self._tail_control_offset_y, 4)

        if side == "right":
            # Base le long du bord gauche de la bulle
            base_top = (x, y - base_height)
            base_bottom = (x, y)
            control = (x - control_offset_x, y + control_offset_y)
            tip = (x - tip_offset_x, y + tip_offset_y)
            raw_points = [base_top, control, tip, base_bottom]
        else:  # side == "left"
            base_top = (x, y - base_height)
            base_bottom = (x, y)
            control = (x + control_offset_x, y + control_offset_y)
            tip = (x + tip_offset_x, y + tip_offset_y)
            raw_points = [base_top, base_bottom, tip, control]

        tail_points = [(int(round(px)), int(round(py))) for px, py in raw_points]

        # Dessiner la queue avec un fond et une bordure épaisse pour un style BD belge
        pygame.draw.polygon(surface, self.bg_color, tail_points)
        # Dessiner la bordure avec une épaisseur importante pour la queue (style BD belge)
        # La bordure de la queue est plus épaisse que celle du corps de la bulle pour plus de visibilité
        border_width_tail = max(self.border_width + 2, 4)  # Au moins 4 pixels pour la queue (style BD belge)
        pygame.draw.polygon(surface, self.border_color, tail_points, border_width_tail)

    def _create_bubble_surface(self) -> pygame.Surface:
        """Crée la surface complète de la bulle avec queue, texte et/ou image.
        
        L'image est affichée au-dessus du texte si les deux sont présents.
        Si une image est présente, elle est redimensionnée pour s'adapter à la taille maximale de la bulle.
        """
        # Calculer les dimensions du contenu (texte + image)
        content_width, content_height = self._calculate_content_dimensions()
        
        if content_width == 0 and content_height == 0:
            # Pas de contenu, retourner une surface minimale
            content_width = 50
            content_height = 50
        
        # Dimensions de la bulle = contenu + padding
        bubble_width = content_width + self.padding * 2
        bubble_height = content_height + self.padding * 2

        # Stocker la hauteur du corps de la bulle (sans la queue)
        self._bubble_body_height = bubble_height

        # Calculer les dimensions de la queue pour un style BD belge
        base_height = max(int(self.tail_size * 0.6), 12)
        base_height = min(base_height, max(bubble_height - 6, 8))
        tip_offset_y = min(self.tail_size, max(int(self.tail_size * 0.7), 8))
        tip_offset_x = max(int(self.tail_size * 1.1), self.tail_size + 6)
        control_offset_x = max(int(tip_offset_x * 0.4), 4)
        control_offset_y = max(int(tip_offset_y * 0.4), 4)

        self._tail_base_height = base_height
        self._tail_tip_offset_x = tip_offset_x
        self._tail_tip_offset_y = tip_offset_y
        self._tail_control_offset_x = control_offset_x
        self._tail_control_offset_y = control_offset_y

        # Créer la surface de la bulle (avec espace pour la queue)
        # La queue peut dépasser, donc on ajoute un peu d'espace
        surface_height = bubble_height + self.tail_size
        surface = pygame.Surface((bubble_width, surface_height), pygame.SRCALPHA)

        # Dessiner le corps de la bulle (rectangle arrondi)
        bubble_rect = pygame.Rect(0, 0, bubble_width, bubble_height)
        pygame.draw.rect(surface, self.bg_color, bubble_rect, border_radius=8)
        pygame.draw.rect(surface, self.border_color, bubble_rect, width=self.border_width, border_radius=8)

        # Position de départ pour le contenu (padding)
        y_offset = self.padding
        
        # Charger et afficher l'image si présente
        # Utiliser l'image redimensionnée si disponible, sinon l'originale
        image = self._scaled_image_surface if self._scaled_image_surface is not None else self._load_image()
        if image is not None:
            # Centrer l'image horizontalement
            image_x = (bubble_width - image.get_width()) // 2
            surface.blit(image, (image_x, y_offset))
            y_offset += image.get_height() + self.image_spacing
        
        # Afficher le texte si présent
        if self.text:
            text_surface = self._render_text()
            if text_surface.get_width() > 0:
                # Centrer le texte horizontalement
                text_x = (bubble_width - text_surface.get_width()) // 2
                surface.blit(text_surface, (text_x, y_offset))

        # Dessiner la queue
        if self.side == "right":
            # Queue attachée au coin inférieur gauche
            tail_x = 0
            tail_y = bubble_height
        else:  # side == "left"
            # Queue attachée au coin inférieur droit
            tail_x = bubble_width
            tail_y = bubble_height

        self._draw_tail(surface, (tail_x, tail_y), self.side)

        return surface

    def _get_tail_attachment_point(self) -> Tuple[int, int]:
        """Calcule le point d'attache de la queue sur la bulle."""
        base_y = self.rect.y + self._bubble_body_height
        if self.side == "right":
            # Queue attachée au coin inférieur gauche
            return (self.rect.x, base_y)
        else:  # side == "left"
            # Queue attachée au coin inférieur droit
            return (self.rect.x + self.rect.width, base_y)

    def update(self, camera_x: float, dt: float = 0.0) -> None:
        """Met à jour la position de la bulle et l'animation du texte.

        Args:
            camera_x: Position horizontale de la caméra
            dt: Delta time en secondes (pour l'animation du texte)
        """
        # Mettre à jour l'animation du texte si elle n'est pas complète
        if not self._text_complete:
            self._accumulated_time += dt
            new_displayed_chars = int(self._accumulated_time * self.text_speed)

            # Limiter au nombre total de caractères
            if new_displayed_chars >= len(self.text):
                self._displayed_chars = len(self.text)
                self._text_complete = True
            else:
                self._displayed_chars = new_displayed_chars

            # Invalider le cache de la surface si le texte a changé
            # (nécessaire pour recréer la surface avec le nouveau texte affiché)
            if self._displayed_chars != self._last_displayed_chars:
                self.surface = None
                self._last_displayed_chars = self._displayed_chars

        # Recalculer la surface si nécessaire (texte animé ou première fois)
        if self.surface is None:
            self.surface = self._create_bubble_surface()

        # Mettre à jour la position de la bulle
        self._update_position(camera_x)

    def skip_animation(self) -> None:
        """Affiche immédiatement tout le texte (appelé lors d'un clic)."""
        if not self._text_complete:
            self._displayed_chars = len(self.text)
            self._text_complete = True
            self._accumulated_time = len(self.text) / self.text_speed
            # Invalider le cache pour recréer la surface
            self.surface = None
            self._last_displayed_chars = self._displayed_chars

    def handle_event(self, event: pygame.event.Event, camera_x: float) -> bool:
        """Gère les événements (clic n'importe où sur l'écran pour accélérer l'affichage).

        Args:
            event: Événement pygame à traiter
            camera_x: Position horizontale de la caméra (non utilisée, conservée pour compatibilité)

        Returns:
            True si l'événement a été traité, False sinon

        Note:
            Le clic peut être effectué n'importe où sur l'écran, pas seulement sur la bulle.
            Cela simplifie l'interaction pour l'utilisateur.
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Clic gauche
                # Accélérer l'animation du texte, peu importe où le clic a été effectué
                if not self._text_complete:
                    self.skip_animation()
                    return True
        return False

    def _update_position(self, camera_x: float) -> None:
        """Met à jour uniquement la position de la bulle sans affecter l'animation.

        Args:
            camera_x: Position horizontale de la caméra
        """
        # S'assurer que la surface existe
        if self.surface is None:
            # Créer la surface si elle n'existe pas encore
            self.surface = self._create_bubble_surface()

        # S'assurer que le rectangle de collision a la bonne taille
        if self.surface is not None:
            self.rect.width = self.surface.get_width()
            self.rect.height = self.surface.get_height()

        # Position du personnage à l'écran
        char_screen_x = self.character.x - camera_x
        char_screen_y = self.character.y

        # Position de la bulle
        bubble_width = self.surface.get_width()
        bubble_height = self.surface.get_height()

        # Vérifier si une image est présente
        has_image = self._load_image() is not None

        if has_image:
            # AVEC IMAGE : Centrer la bulle dans l'écran, maximiser l'espace en haut/gauche/droite
            # IMPORTANT : Utiliser la taille de la surface interne (1280x720) car les bulles
            # sont dessinées sur la surface interne, pas sur la surface d'affichage réelle
            screen_width, screen_height = get_render_size()

            # Centrer horizontalement (pas de marges latérales)
            bubble_x = (screen_width - bubble_width) // 2

            # Positionnement vertical : placer en haut (marge = 0) pour maximiser l'espace
            margin_bottom = 200  # Marge du bas pour le personnage
            bubble_y = 0  # Placer en haut sans marge
            
            # S'assurer que la bulle ne sort pas en bas ou en haut
            max_bubble_y = screen_height - margin_bottom
            if bubble_y + bubble_height > max_bubble_y:
                bubble_y = max_bubble_y - bubble_height
            
            # S'assurer que la bulle ne sort pas en haut
            if bubble_y < 0:
                bubble_y = 0

            self.rect.x = int(bubble_x)
            self.rect.y = int(bubble_y)
        else:
            # SANS IMAGE : Positionnement classique attaché au personnage
            # Calculer la hauteur du corps de la bulle (basée sur le contenu complet : texte)
            content_width, content_height = self._calculate_content_dimensions()
            bubble_body_height = content_height + self.padding * 2

            # Position verticale : au-dessus du personnage
            # Utiliser la hauteur affichée pour rester aligné lorsque le sprite est redimensionné
            char_bottom = char_screen_y + self.character.sprite_height / 2
            char_top = char_bottom - getattr(self.character, "display_height", self.character.sprite_height)

            # On positionne la bulle en fonction du corps, la queue dépasse en dessous
            bubble_y = char_top + self.offset_y - bubble_body_height

            # Position horizontale selon le côté
            # Convertir l'offset horizontal du repère de conception (1920x1080) vers la résolution interne (1280x720)
            render_width, render_height = get_render_size()
            _, scale_y = compute_design_scale((render_width, render_height))
            horizontal_offset_design = 10  # Offset horizontal pour positionner la bulle (repère 1920x1080)
            screen_margin_design = 10  # Marge d'écran pour éviter que la bulle sorte (repère 1920x1080)
            converted_horizontal_offset = int(horizontal_offset_design * scale_y)
            converted_screen_margin = int(screen_margin_design * scale_y)
            
            half_width = getattr(self.character, "display_width", self.character.sprite_width) / 2
            if self.side == "right":
                bubble_x = char_screen_x + half_width + converted_horizontal_offset
            else:
                bubble_x = char_screen_x - bubble_width - half_width - converted_horizontal_offset

            # Ajuster pour éviter que la bulle sorte de l'écran
            # IMPORTANT : Utiliser la taille de la surface interne (1280x720) car les bulles
            # sont dessinées sur la surface interne, pas sur la surface d'affichage réelle
            screen_width, _ = get_render_size()

            if bubble_x < 0:
                bubble_x = converted_screen_margin
            elif bubble_x + bubble_width > screen_width:
                bubble_x = screen_width - bubble_width - converted_screen_margin

            # IMPORTANT : Ne pas repositionner la bulle de manière absolue (ni en X ni en Y).
            # Cela garantir que la bulle reste visuellement attachée au personnage qui parle,
            # même si ce personnage sort partiellement de l'écran. Les bulles sont donc
            # entièrement pilotées par la position du personnage.

            self.rect.x = int(bubble_x)
            self.rect.y = int(bubble_y)

    def _is_clicked(self, mouse_pos: Tuple[int, int]) -> bool:
        """Vérifie si la bulle a été cliquée.

        Args:
            mouse_pos: Position de la souris (x, y) en coordonnées écran

        Returns:
            True si la bulle a été cliquée, False sinon

        Note:
            Cette méthode suppose que `_update_position()` ou `update()` a été appelé
            récemment pour que `self.rect` soit à jour.
        """
        if self.surface is None or self.rect.width == 0 or self.rect.height == 0:
            return False

        # Vérifier si le clic est dans le rectangle de la bulle
        return self.rect.collidepoint(mouse_pos)

    def draw(self, surface: pygame.Surface, camera_x: float, dt: float = 0.0) -> None:
        """Dessine la bulle sur la surface.

        Args:
            surface: Surface sur laquelle dessiner
            camera_x: Position horizontale de la caméra
            dt: Delta time en secondes (pour l'animation du texte)
        """
        # Mettre à jour la position et l'animation
        self.update(camera_x, dt)

        # Dessiner la bulle
        surface.blit(self.surface, self.rect)


def show_speech_bubble(
    character: CharacterProtocol,
    text: str,
    side: str = "right",
    duration: Optional[float] = None,
    **kwargs,
) -> SpeechBubble:
    """Affiche une bulle de dialogue pour un personnage.

    Args:
        character: Personnage associé à la bulle
        text: Texte à afficher
        side: Position de la bulle ("left" ou "right")
        duration: Durée d'affichage en secondes (None = affichage permanent jusqu'à fermeture manuelle)
        **kwargs: Arguments additionnels passés à SpeechBubble.__init__()

    Returns:
        Instance de SpeechBubble créée
    """
    bubble = SpeechBubble(text=text, character=character, side=side, **kwargs)

    # TODO: Implémenter la gestion de la durée si nécessaire
    if duration is not None:
        # Pour l'instant, on ignore la durée
        # Cela pourrait être géré par un gestionnaire de bulles
        pass

    return bubble

