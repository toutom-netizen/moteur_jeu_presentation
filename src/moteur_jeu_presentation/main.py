"""Point d'entrée principal du jeu Présentation."""

from __future__ import annotations

import argparse
import cProfile
import io
import math
import os
import pstats
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import pygame

from moteur_jeu_presentation.entities import (
    MAX_PLAYER_LEVEL,
    MIN_PLAYER_LEVEL,
    NPC,
    Player,
)
from moteur_jeu_presentation.entities.npc import DialogueState, start_dialogue
from moteur_jeu_presentation.game import LevelProgressTracker
from moteur_jeu_presentation.game.events import EventTriggerSystem
from moteur_jeu_presentation.game.hud import LevelProgressHUD
from moteur_jeu_presentation.levels import LevelLoader, NPCLoader
from moteur_jeu_presentation.physics import CollisionSystem
from moteur_jeu_presentation.inventory import Inventory, InventoryItemLoader
from moteur_jeu_presentation.particles import ParticleSystem
from moteur_jeu_presentation.stats import PlayerStatsLoader
from moteur_jeu_presentation.ui import (
    PlayerStatsDisplay,
    QuitConfirmationDialog,
    SpeechBubble,
    SplashScreen,
    show_speech_bubble,
)
from moteur_jeu_presentation.ui.speech_bubble import preload_dialogue_images
from moteur_jeu_presentation.assets import AssetPreloader, set_custom_cursor
from moteur_jeu_presentation.rendering.config import (
    compute_scale,
    compute_scaled_size,
    convert_mouse_to_internal,
    get_render_size,
    letterbox_offsets,
)
from moteur_jeu_presentation.rendering.camera_zoom import CameraZoomController


# Distance d'interaction avec les PNJ (en pixels)
# Deux conditions doivent être remplies : distance horizontale ET distance verticale
INTERACTION_DISTANCE = 200.0  # Distance horizontale maximale (pixels)
INTERACTION_Y_THRESHOLD = 100.0  # Différence de hauteur maximale entre le joueur et le PNJ (pixels)


def is_entity_visible(
    entity_x: float,
    entity_y: float,
    sprite_width: int,
    sprite_height: int,
    camera_x: float,
    screen_width: int,
    screen_height: int,
    margin: int = 50,
) -> bool:
    """Vérifie si une entité est visible à l'écran (avec marge pour le culling).
    
    Args:
        entity_x: Position horizontale de l'entité dans le monde
        entity_y: Position verticale de l'entité dans le monde
        sprite_width: Largeur du sprite de l'entité
        sprite_height: Hauteur du sprite de l'entité
        camera_x: Position horizontale de la caméra
        screen_width: Largeur de l'écran
        screen_height: Hauteur de l'écran
        margin: Marge en pixels pour éviter le culling trop agressif (défaut: 50)
        
    Returns:
        True si l'entité est visible (ou proche de l'écran), False sinon
    """
    # Calculer la position à l'écran
    screen_x = entity_x - camera_x
    screen_y = entity_y
    
    # Calculer les bords du sprite (centré sur entity_x, entity_y)
    left = screen_x - sprite_width / 2
    right = screen_x + sprite_width / 2
    top = screen_y - sprite_height / 2
    bottom = screen_y + sprite_height / 2
    
    # Vérifier si le sprite intersecte avec la zone visible (avec marge)
    return (
        right >= -margin
        and left <= screen_width + margin
        and bottom >= -margin
        and top <= screen_height + margin
    )


def find_nearest_interactable_npc(
    player_x: float,
    player_y: float,
    npcs: list[NPC],
    player_position: float,
) -> Optional[NPC]:
    """Trouve le PNJ le plus proche à portée d'interaction.
    
    Pour qu'un PNJ soit considéré comme interactif, deux conditions doivent être remplies :
    1. La distance horizontale (X) doit être <= INTERACTION_DISTANCE
    2. La différence de hauteur (Y) doit être <= INTERACTION_Y_THRESHOLD
    
    L'indication n'est affichée que si le PNJ a un bloc de dialogue disponible
    à la position actuelle du joueur (c'est-à-dire qu'il existe un bloc de dialogue
    dont la plage de position correspond à la position actuelle du joueur).
    
    Args:
        player_x: Position horizontale du joueur dans le monde
        player_y: Position verticale du joueur dans le monde
        npcs: Liste des PNJ dans le niveau
        player_position: Position horizontale du joueur dans le monde (utilisée pour vérifier les blocs de dialogue disponibles)
        
    Returns:
        Le PNJ le plus proche qui respecte toutes les conditions d'interaction,
        ou None si aucun PNJ n'est à portée
    """
    nearest_npc = None
    min_distance = INTERACTION_DISTANCE
    
    for npc in npcs:
        # Vérifier que le PNJ a un bloc de dialogue disponible à la position actuelle du joueur
        # (pas seulement qu'il a des blocs configurés, mais qu'il y en a un qui correspond à cette position)
        dialogue_block = npc.get_dialogue_block_for_position(player_position)
        if dialogue_block is None:
            continue
        
        # Calculer la distance horizontale
        distance_x = abs(player_x - npc.x)
        
        # Vérifier que le PNJ est à portée horizontalement
        if distance_x > INTERACTION_DISTANCE:
            continue
        
        # Calculer la différence de hauteur
        distance_y = abs(player_y - npc.y)
        
        # Vérifier que le joueur et le PNJ sont à peu près à la même hauteur
        if distance_y > INTERACTION_Y_THRESHOLD:
            continue
        
        # Si toutes les conditions sont remplies, vérifier si c'est le PNJ le plus proche
        if distance_x < min_distance:
            min_distance = distance_x
            nearest_npc = npc
    
    return nearest_npc


def _build_interaction_indicator_surface(
    text: str,
    font: pygame.font.Font,
    text_color: tuple[int, int, int],
    outline_thickness: int,
) -> tuple[pygame.Surface, int, int, int]:
    """Construit une surface pré-rendue pour l'indicateur d'interaction.

    Returns:
        Tuple contenant (surface, largeur du texte, hauteur du texte, padding de l'outline)
    """
    text_surface = font.render(text, True, text_color)
    outline_surface = font.render(text, True, (0, 0, 0))

    padding = outline_thickness
    width = text_surface.get_width() + padding * 2
    height = text_surface.get_height() + padding * 2

    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    for dx in range(-outline_thickness, outline_thickness + 1):
        for dy in range(-outline_thickness, outline_thickness + 1):
            if dx == 0 and dy == 0:
                continue
            surface.blit(outline_surface, (dx + padding, dy + padding))

    surface.blit(text_surface, (padding, padding))
    return surface, text_surface.get_width(), text_surface.get_height(), outline_thickness


def draw_interaction_indicator(
    surface: pygame.Surface,
    npc: NPC,
    camera_x: float,
    font: pygame.font.Font,
    player_position: float,
    base_font_size: int = 28,
    alpha: float = 1.0,
    indicator_cache: Optional[Dict[str, tuple[pygame.Surface, int, int, int]]] = None,
    quest_font: Optional[pygame.font.Font] = None,
    font_cache: Optional[Dict[int, pygame.font.Font]] = None,
) -> None:
    """Dessine l'indication d'interaction au-dessus du PNJ.
    
    Le type d'indicateur dépend du type de dialogue du bloc correspondant
    à la position actuelle du joueur (voir spécification 12).
    
    Args:
        surface: Surface pygame sur laquelle dessiner
        npc: Le PNJ pour lequel afficher l'indication
        camera_x: Position horizontale de la caméra
        font: Police à utiliser pour le texte (taille de base, utilisée pour "T pour parler")
        player_position: Position horizontale actuelle du joueur dans le monde
        base_font_size: Taille de base de la police en pixels (utilisée pour calculer la taille du "!")
        alpha: Opacité du texte (0.0 à 1.0)
        font_cache: Cache pour les polices créées (évite de recréer les polices à chaque frame)
    """
    # Convertir la taille de police du repère de conception (1920x1080) vers la résolution interne (1920x1080)
    from moteur_jeu_presentation.rendering.config import compute_design_scale, get_render_size
    render_width, render_height = get_render_size()
    _, scale_y = compute_design_scale((render_width, render_height))
    converted_base_font_size = int(base_font_size * scale_y)
    
    # Calculer la position à l'écran
    screen_x = npc.x - camera_x
    screen_y = npc.y
    
    # Déterminer le type de dialogue pour cette position
    # OPTIMISATION: Ajouter une gestion d'erreur pour éviter les blocages
    try:
        dialogue_type = npc.get_dialogue_type_for_position(player_position)
    except Exception:
        # En cas d'erreur, ne pas afficher l'indication plutôt que de bloquer
        return
    
    # Si aucun bloc de dialogue n'est disponible à cette position, ne pas afficher l'indication
    if dialogue_type is None:
        return
    
    # Initialiser le cache de polices si nécessaire
    if font_cache is None:
        font_cache = {}
    
    # Initialiser display_font pour éviter UnboundLocalError
    display_font: Optional[pygame.font.Font] = None
    
    # Choisir le texte selon le type de dialogue
    cache_key: Optional[str]
    if dialogue_type == "quête":
        text = "!"
        outline_thickness = 6
        cache_key = f"quest_{converted_base_font_size}"
        # Si quest_font n'est pas fourni, utiliser le cache
        if quest_font is None:
            quest_font_size = int(converted_base_font_size * 3)  # 3 fois plus gros
            # Utiliser le cache pour éviter de recréer la police à chaque frame
            if quest_font_size not in font_cache:
                try:
                    font_cache[quest_font_size] = pygame.font.SysFont("arial", quest_font_size, bold=True)
                except pygame.error:
                    try:
                        font_cache[quest_font_size] = pygame.font.SysFont("sans-serif", quest_font_size, bold=True)
                    except pygame.error:
                        # Si la création de la police échoue, ne pas afficher
                        return
            quest_font = font_cache[quest_font_size]
        display_font = quest_font
    elif dialogue_type == "discution":
        text = "T pour ecouter et donner son avis"
        outline_thickness = 2
        cache_key = f"discution_{converted_base_font_size}"
        # OPTIMISATION: Utiliser le cache au lieu de vérifier get_height() à chaque frame
        if converted_base_font_size not in font_cache:
            try:
                font_cache[converted_base_font_size] = pygame.font.SysFont("arial", converted_base_font_size, bold=True)
            except pygame.error:
                try:
                    font_cache[converted_base_font_size] = pygame.font.SysFont("sans-serif", converted_base_font_size, bold=True)
                except pygame.error:
                    # Si la création de la police échoue, utiliser la police fournie
                    display_font = font
                    if display_font is None:
                        return
        else:
            display_font = font_cache[converted_base_font_size]
    elif dialogue_type == "ecoute":
        text = "T pour écouter"
        outline_thickness = 2
        cache_key = f"ecoute_{converted_base_font_size}"
        if converted_base_font_size not in font_cache:
            try:
                font_cache[converted_base_font_size] = pygame.font.SysFont("arial", converted_base_font_size, bold=True)
            except pygame.error:
                try:
                    font_cache[converted_base_font_size] = pygame.font.SysFont("sans-serif", converted_base_font_size, bold=True)
                except pygame.error:
                    display_font = font
                    if display_font is None:
                        return
        else:
            display_font = font_cache[converted_base_font_size]
    elif dialogue_type == "regarder":
        text = "T pour regarder ce que c'est"
        outline_thickness = 2
        cache_key = f"regarder_{converted_base_font_size}"
        if converted_base_font_size not in font_cache:
            try:
                font_cache[converted_base_font_size] = pygame.font.SysFont("arial", converted_base_font_size, bold=True)
            except pygame.error:
                try:
                    font_cache[converted_base_font_size] = pygame.font.SysFont("sans-serif", converted_base_font_size, bold=True)
                except pygame.error:
                    display_font = font
                    if display_font is None:
                        return
        else:
            display_font = font_cache[converted_base_font_size]
    elif dialogue_type == "enseigner":
        text = "T pour former"
        outline_thickness = 2
        cache_key = f"enseigner_{converted_base_font_size}"
        if converted_base_font_size not in font_cache:
            try:
                font_cache[converted_base_font_size] = pygame.font.SysFont("arial", converted_base_font_size, bold=True)
            except pygame.error:
                try:
                    font_cache[converted_base_font_size] = pygame.font.SysFont("sans-serif", converted_base_font_size, bold=True)
                except pygame.error:
                    display_font = font
                    if display_font is None:
                        return
        else:
            display_font = font_cache[converted_base_font_size]
    elif dialogue_type == "reflexion":
        text = "T pour reflechir"
        outline_thickness = 2
        cache_key = f"reflexion_{converted_base_font_size}"
        if converted_base_font_size not in font_cache:
            try:
                font_cache[converted_base_font_size] = pygame.font.SysFont("arial", converted_base_font_size, bold=True)
            except pygame.error:
                try:
                    font_cache[converted_base_font_size] = pygame.font.SysFont("sans-serif", converted_base_font_size, bold=True)
                except pygame.error:
                    display_font = font
                    if display_font is None:
                        return
        else:
            display_font = font_cache[converted_base_font_size]
    else:
        text = "T pour parler"
        outline_thickness = 2
        cache_key = f"talk_{converted_base_font_size}"
        if converted_base_font_size not in font_cache:
            try:
                font_cache[converted_base_font_size] = pygame.font.SysFont("arial", converted_base_font_size, bold=True)
            except pygame.error:
                try:
                    font_cache[converted_base_font_size] = pygame.font.SysFont("sans-serif", converted_base_font_size, bold=True)
                except pygame.error:
                    display_font = font
                    if display_font is None:
                        return
        else:
            display_font = font_cache[converted_base_font_size]
    
    if display_font is None:
        return
    
    text_color = (255, 255, 0)
    cached_surface_data: Optional[tuple[pygame.Surface, int, int, int]] = None
    if indicator_cache is not None and cache_key is not None:
        cached_surface_data = indicator_cache.get(cache_key)
        if cached_surface_data is None:
            try:
                cached_surface_data = _build_interaction_indicator_surface(
                    text,
                    display_font,
                    text_color,
                    outline_thickness,
                )
                indicator_cache[cache_key] = cached_surface_data
            except Exception:
                # En cas d'erreur lors de la création de la surface, ne pas bloquer
                return
    
    if cached_surface_data is not None:
        indicator_surface, text_width, text_height, padding = cached_surface_data
        if alpha < 1.0:
            indicator_surface.set_alpha(int(255 * alpha))
        else:
            indicator_surface.set_alpha(None)
    else:
        try:
            text_surface = display_font.render(text, True, text_color)
            if alpha < 1.0:
                text_surface.set_alpha(int(255 * alpha))
            outline_surface = display_font.render(text, True, (0, 0, 0))
            indicator_surface = None
            text_width = text_surface.get_width()
            text_height = text_surface.get_height()
            padding = outline_thickness
        except Exception:
            # En cas d'erreur lors du rendu, ne pas bloquer
            return
    
    # Centrer horizontalement
    text_x = round(screen_x - text_width / 2)
    # Positionner au-dessus du nom (le nom est à environ -sprite_height/2 - name_height - offset)
    # Convertir les offsets du repère de conception (1920x1080) vers la résolution interne (1920x1080)
    name_offset_y_design = 4.0  # Offset pour positionner le nom (repère 1920x1080)
    spacing_offset_design = 12.0  # Espacement entre le nom et l'indicateur (repère 1920x1080)
    vertical_offset_design = 60.0  # Offset vertical supplémentaire (repère 1920x1080)
    converted_name_offset = name_offset_y_design * scale_y
    converted_spacing_offset = spacing_offset_design * scale_y
    converted_vertical_offset = vertical_offset_design * scale_y
    name_y = screen_y - npc.sprite_height / 2 - (npc.name_rect.height if npc.name_rect else 0) - converted_name_offset
    text_y = round(name_y - text_height - converted_spacing_offset) - converted_vertical_offset
    
    try:
        if cached_surface_data is not None:
            draw_x = text_x - padding
            draw_y = text_y - padding
            surface.blit(indicator_surface, (draw_x, draw_y))
        else:
            for dx in range(-outline_thickness, outline_thickness + 1):
                for dy in range(-outline_thickness, outline_thickness + 1):
                    if dx != 0 or dy != 0:
                        surface.blit(outline_surface, (text_x + dx, text_y + dy))
            
            surface.blit(text_surface, (text_x, text_y))
    except Exception:
        # En cas d'erreur lors du blit, ne pas bloquer
        return


def is_macos() -> bool:
    """Vérifie si l'application s'exécute sur macOS."""
    return sys.platform == "darwin"


def enable_metal_acceleration() -> Tuple[bool, Dict[str, Optional[str]]]:
    """Active l'accélération GPU Metal sur macOS et mémorise les variables d'environnement d'origine.

    Returns:
        Tuple (success, original_env) où :
        - success: True si l'accélération a été activée, False sinon
        - original_env: Copie des valeurs originales des variables modifiées
    """
    if not is_macos():
        print("Accélération Metal non disponible sur cette plateforme")
        return False, {}

    original_env = {
        "SDL_VIDEODRIVER": os.environ.get("SDL_VIDEODRIVER"),
        "SDL_RENDER_DRIVER": os.environ.get("SDL_RENDER_DRIVER"),
        "SDL_HINT_RENDER_SCALE_QUALITY": os.environ.get("SDL_HINT_RENDER_SCALE_QUALITY"),
        "SDL_HINT_RENDER_BATCHING": os.environ.get("SDL_HINT_RENDER_BATCHING"),
        "SDL_HINT_RENDER_VSYNC": os.environ.get("SDL_HINT_RENDER_VSYNC"),
    }

    try:
        os.environ["SDL_VIDEODRIVER"] = "cocoa"
        os.environ["SDL_RENDER_DRIVER"] = "metal"
        # Activer le batching et la synchronisation verticale pour déléguer plus de travail au GPU
        os.environ["SDL_HINT_RENDER_BATCHING"] = "1"
        os.environ["SDL_HINT_RENDER_VSYNC"] = "1"
        # Utiliser "2" (best) pour tirer parti de la mise à l'échelle matérielle Metal
        os.environ.setdefault("SDL_HINT_RENDER_SCALE_QUALITY", "2")
        print("Accélération GPU Metal activée (driver video: cocoa, renderer: metal)")
        return True, original_env
    except Exception as exc:
        print(f"Impossible d'activer l'accélération Metal : {exc}")
        disable_metal_acceleration(original_env)
        return False, original_env


def disable_metal_acceleration(original_env: Dict[str, Optional[str]]) -> None:
    """Restaure les variables d'environnement modifiées pour Metal."""
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def parse_arguments() -> argparse.Namespace:
    """Parse les arguments de la ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Présentation - Jeu de plateforme",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--mps",
        "--metal",
        action="store_true",
        dest="enable_metal",
        help="Active l'accélération GPU Metal sur macOS (améliore les performances)",
    )
    parser.add_argument(
        "--profiling-metal",
        action="store_true",
        dest="profiling_metal",
        help="Active le profilage Metal avec affichage du FPS à l'écran et logs dans la console (nécessite --mps)",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        dest="enable_profiling",
        help="Active le profiling cProfile détaillé pour identifier les goulots d'étranglement (ralentit le jeu)",
    )
    parser.add_argument(
        "--profile-frames",
        type=int,
        default=300,
        dest="profile_frames",
        help="Nombre de frames à profiler avec --profile (défaut: 300 = ~5 secondes à 60 FPS)",
    )
    parser.add_argument(
        "--skip-splash",
        action="store_true",
        dest="skip_splash",
        help="Passe l'écran d'accueil et lance directement le niveau (utile pour le développement)",
    )
    parser.add_argument(
        "--player-x",
        "--start-x",
        type=float,
        default=None,
        dest="player_x",
        help="Position X initiale du personnage principal en pixels dans le repère de conception (1920x1080) (défaut: centre de l'écran)",
    )
    parser.add_argument(
        "--skip-preload",
        action="store_true",
        dest="skip_preload",
        help="Passe le préchargement des éléments graphiques (utile pour le développement)",
    )
    parser.add_argument(
        "--hide-info-player",
        action="store_true",
        dest="hide_info_player",
        help="Masque les éléments de positionnement du joueur en haut à gauche (HUD de progression)",
    )
    
    return parser.parse_args()


def main() -> None:
    """Point d'entrée principal du jeu."""
    # Parser les arguments de la ligne de commande
    args = parse_arguments()
    
    # Activer l'accélération Metal si demandée
    metal_enabled = False
    original_env: Dict[str, Optional[str]] = {}
    if args.enable_metal:
        metal_enabled, original_env = enable_metal_acceleration()
        if not metal_enabled:
            print("Metal n'a pas pu être activé, utilisation du chemin de rendu standard.")
    elif args.profiling_metal:
        print("Option --profiling-metal ignorée : activez --mps pour l'utiliser.")

    profiling_metal_enabled = metal_enabled and args.profiling_metal
    profiling_accumulator = 0.0
    profiling_frames = 0
    profiling_last_log = time.perf_counter()
    
    # Système de calcul de FPS pour l'affichage à l'écran (plus fiable que clock.get_fps())
    fps_display_accumulator = 0.0
    fps_display_frames = 0
    fps_display_last_update = time.perf_counter()
    fps_display_value = 0.0  # Valeur de FPS affichée (mise à jour toutes les 0.5 secondes)
    
    # Système de profiling cProfile pour identifier les goulots d'étranglement
    profiling_enabled = args.enable_profiling
    profiling_frame_count = 0
    profiling_target_frames = args.profile_frames
    profiler = None
    
    if profiling_enabled:
        print(f"\n{'='*80}")
        print("MODE PROFILING ACTIVÉ")
        print(f"Le jeu va profiler {profiling_target_frames} frames (~{profiling_target_frames/60:.1f}s à 60 FPS)")
        print("ATTENTION: Le profiling ralentit significativement le jeu")
        print(f"{'='*80}\n")
        profiler = cProfile.Profile()
    
    # Initialiser pygame (doit être après la configuration des variables d'environnement)
    pygame.init()
    
    # Optimisation : filtrer les événements pour ne traiter que ceux nécessaires
    # Cela réduit la charge de traitement des événements inutiles
    pygame.event.set_allowed([
        pygame.QUIT,
        pygame.KEYDOWN,
        pygame.KEYUP,
        pygame.MOUSEBUTTONDOWN,
        pygame.MOUSEMOTION,
        pygame.WINDOWFOCUSLOST,
        pygame.WINDOWFOCUSGAINED,
        pygame.WINDOWSIZECHANGED,
        pygame.VIDEORESIZE,
    ])

    # Configuration de la fenêtre
    render_width, render_height = get_render_size()
    FPS = 60

    def set_display_mode(size: tuple[int, int], flags: int = 0) -> pygame.Surface:
        """Crée une fenêtre en demandant la synchronisation verticale si disponible."""
        try:
            return pygame.display.set_mode(size, flags, vsync=1)
        except TypeError:
            # Version de pygame sans support du paramètre vsync
            return pygame.display.set_mode(size, flags)

    # Flags de base
    # SCALED est utilisé pour le mode Hardware Scaling sur Metal
    base_flags = pygame.DOUBLEBUF | pygame.RESIZABLE
    windowed_flags = base_flags
    
    display_info = pygame.display.Info()
    native_display_size = (
        getattr(display_info, "current_w", render_width) or render_width,
        getattr(display_info, "current_h", render_height) or render_height,
    )

    def find_fallback_size() -> tuple[int, int]:
        """Détermine la meilleure résolution fenêtrée disponible ≤ résolution interne."""
        modes = pygame.display.list_modes()
        if modes and modes != -1:
            candidates = [
                mode for mode in modes if mode[0] <= render_width and mode[1] <= render_height
            ]
            if candidates:
                return max(candidates, key=lambda mode: mode[0] * mode[1])
        return (
            min(native_display_size[0], render_width),
            min(native_display_size[1], render_height),
        )

    # Initialisation de l'affichage
    if metal_enabled:
        # MODE HARDWARE SCALING (Metal)
        # On demande une fenêtre de la taille logique (render_width, render_height) avec SCALED
        # SDL/Metal s'occupe de l'upscale vers la résolution de l'écran
        print(f"Mode Metal Hardware Scaling activé: Résolution logique {render_width}x{render_height}")
        try:
            # FULLSCREEN | SCALED active le "desktop fullscreen" avec scaling hardware
            screen = set_display_mode(
                (render_width, render_height), 
                pygame.FULLSCREEN | pygame.SCALED | base_flags
            )
            current_display_size = (render_width, render_height)
            current_display_flags = pygame.FULLSCREEN | pygame.SCALED | base_flags
        except pygame.error as e:
            print(f"Echec Metal HW Scaling: {e}. Repli sur fallback...")
            metal_enabled = False # Désactiver Metal pour utiliser le fallback
            disable_metal_acceleration(original_env)
            # Fallback ci-dessous
            
    if not metal_enabled:
        # MODE SOFTWARE SCALING (Classique)
        # On essaie d'abord le plein écran natif
        try:
            screen = set_display_mode(native_display_size, pygame.FULLSCREEN | base_flags)
            current_display_size = native_display_size
            current_display_flags = pygame.FULLSCREEN | base_flags
        except pygame.error:
            # Fallback fenêtré
            fallback_size = find_fallback_size()
            screen = set_display_mode(fallback_size, base_flags)
            current_display_size = fallback_size
            current_display_flags = base_flags

    pygame.display.set_caption("Présentation")
    clock = pygame.time.Clock()

    initial_scale = compute_scale(current_display_size) if current_display_size else 1.0
    render_scale_factor = max(0.5, min(2.0, initial_scale))
    
    # Créer la surface de rendu interne
    if metal_enabled:
        # En mode Metal, on peut dessiner directement sur l'écran (qui est une surface 1920x1080)
        # ou utiliser une surface intermédiaire. Pour éviter une copie inutile, on utilise l'écran.
        # Cependant, pour garder la compatibilité avec le reste du code qui attend internal_surface,
        # on fait pointer internal_surface vers screen.
        internal_surface = screen
    else:
        # En mode normal, surface intermédiaire pour le software scaling
        internal_surface = pygame.Surface((render_width, render_height)).convert(screen)

    # Surfaces de rendu pour le zoom caméra (post-process)
    # - scene_surface: rendu du gameplay (monde + entités + particules + textes in-scene)
    scene_surface = pygame.Surface((render_width, render_height)).convert(screen)

    # Cache de la surface scalée pour le zoom caméra (évite des allocations fréquentes)
    camera_scaled_scene_surface: Optional[pygame.Surface] = None
    camera_cached_scaled_size: Optional[tuple[int, int]] = None
    
    # Cache pour la surface redimensionnée (évite de recalculer à chaque frame)
    cached_scaled_surface: Optional[pygame.Surface] = None
    cached_scaled_size: Optional[tuple[int, int]] = None

    # Police pour l'affichage du FPS (si profiling activé)
    fps_font: Optional[pygame.font.Font] = None
    fps_surface_cache: Optional[pygame.Surface] = None
    fps_text_cache: str = ""
    if profiling_metal_enabled:
        fps_font = pygame.font.Font(None, 24)  # Police système, taille 24

    # Police pour l'affichage d'informations de debug (toujours disponible si possible)
    debug_font: Optional[pygame.font.Font] = None
    debug_surface_cache: Optional[pygame.Surface] = None
    debug_text_cache: str = ""
    try:
        debug_font = pygame.font.Font(None, 18)
    except pygame.error:
        debug_font = None

    # Police pour l'indication d'interaction avec les PNJ
    # Taille de base : 28 pixels dans le repère 1920x1080
    # Convertir d'abord vers 1920x1080, puis appliquer le scaling d'affichage
    from moteur_jeu_presentation.rendering.config import compute_design_scale
    _, design_scale_y = compute_design_scale((render_width, render_height))
    base_font_size_design = 28  # Taille dans le repère 1920x1080
    converted_base_font_size = int(base_font_size_design * design_scale_y)  # Converti vers 1920x1080 (actuellement identique)
    interaction_font: Optional[pygame.font.Font] = None
    quest_interaction_font: Optional[pygame.font.Font] = None
    interaction_font_size: int = max(18, int(converted_base_font_size * render_scale_factor))
    try:
        interaction_font = pygame.font.SysFont("arial", interaction_font_size, bold=True)
    except pygame.error:
        try:
            interaction_font = pygame.font.SysFont("sans-serif", interaction_font_size, bold=True)
        except pygame.error:
            interaction_font = None
    # Préparer une police agrandie pour l'indicateur de quête (point d'exclamation)
    quest_font_size = max(interaction_font_size * 2, int(interaction_font_size * 3))
    try:
        quest_interaction_font = pygame.font.SysFont("arial", quest_font_size, bold=True)
    except pygame.error:
        try:
            quest_interaction_font = pygame.font.SysFont("sans-serif", quest_font_size, bold=True)
        except pygame.error:
            quest_interaction_font = interaction_font
    
    interaction_indicator_cache: Dict[str, tuple[pygame.Surface, int, int, int]] = {}
    # Cache pour les polices créées dans draw_interaction_indicator (évite de recréer les polices à chaque frame)
    interaction_font_cache: Dict[int, pygame.font.Font] = {}

    # OPTIMISATION: Cache de la taille de la fenêtre pour éviter les appels répétés
    cached_display_size: Optional[Tuple[int, int]] = None
    
    # OPTIMISATION: Réutiliser les listes de commandes de blit pour éviter les allocations
    _reusable_layer_commands: list[tuple[pygame.Surface, tuple[int, int]]] = []
    _reusable_front_layer_commands: list[tuple[pygame.Surface, tuple[int, int]]] = []
    _reusable_draw_commands: list[tuple[pygame.Surface, tuple[int, int]]] = []
    _reusable_name_commands: list[tuple[pygame.Surface, tuple[int, int]]] = []

    def present_frame(dirty_rects: Optional[list[pygame.Rect]] = None) -> None:
        nonlocal cached_scaled_surface, cached_scaled_size
        nonlocal profiling_accumulator, profiling_frames, profiling_last_log, profiling_metal_enabled
        nonlocal cached_display_size, metal_enabled

        if profiling_metal_enabled:
            render_start = time.perf_counter()

        # OPTIMISATION CRITIQUE: Chemin Metal optimisé (Hardware Scaling)
        if metal_enabled:
            # En mode Metal avec SDL_HINT_RENDER_SCALE_QUALITY et SCALED:
            # 1. internal_surface est un alias de screen (voir init)
            # 2. On a déjà dessiné directement sur screen dans redraw_scene
            # 3. SDL/Metal s'occupe du scaling et des bandes noires lors du flip
            # OPTIMISATION 2: Utiliser update() avec dirty rectangles si disponible
            # NOTE: Désactivé pour Metal car le hardware scaling complique les dirty rects
            # Pour l'instant, on utilise toujours flip() pour Metal
            pygame.display.flip()
        else:
            # Chemin de fallback standard (Software Scaling)
            # OPTIMISATION: Utiliser le cache de la taille de la fenêtre
            if cached_display_size is None:
                try:
                    cached_display_size = pygame.display.get_window_size()
                except (pygame.error, AttributeError):
                    cached_display_size = screen.get_size()
            
            display_size = cached_display_size
            if display_size[0] <= 0 or display_size[1] <= 0:
                display_size = screen.get_size()
                cached_display_size = display_size

            scaled_size = compute_scaled_size(display_size)
            if scaled_size[0] <= 0 or scaled_size[1] <= 0:
                scaled_size = (render_width, render_height)

            # OPTIMISATION: Éviter smoothscale si la taille est identique (scale == 1.0)
            internal_size = internal_surface.get_size()
            if scaled_size == internal_size:
                # Pas besoin de redimensionner, utiliser directement la surface interne
                cached_scaled_surface = internal_surface
                cached_scaled_size = scaled_size
            else:
                if cached_scaled_surface is None or cached_scaled_size != scaled_size:
                    cached_scaled_surface = pygame.Surface(scaled_size).convert(screen)
                    cached_scaled_size = scaled_size

                pygame.transform.smoothscale(
                    internal_surface,
                    scaled_size,
                    cached_scaled_surface,
                )

            offset_x, offset_y = letterbox_offsets(display_size)
            if offset_x != 0 or offset_y != 0:
                screen.fill((0, 0, 0))

            screen.blit(cached_scaled_surface, (offset_x, offset_y))
            # OPTIMISATION 2: Utiliser update() avec dirty rectangles si disponible
            if dirty_rects is not None and len(dirty_rects) > 0:
                # Convertir les dirty rectangles de la résolution interne vers la résolution d'affichage
                scaled_dirty_rects = []
                for rect in dirty_rects:
                    # Calculer le facteur d'échelle
                    scale_x = scaled_size[0] / render_width
                    scale_y = scaled_size[1] / render_height
                    # Convertir le rectangle
                    scaled_rect = pygame.Rect(
                        int(rect.x * scale_x) + offset_x,
                        int(rect.y * scale_y) + offset_y,
                        int(rect.width * scale_x),
                        int(rect.height * scale_y)
                    )
                    scaled_dirty_rects.append(scaled_rect)
                pygame.display.update(scaled_dirty_rects)
            else:
                pygame.display.flip()

        if profiling_metal_enabled:
            elapsed = time.perf_counter() - render_start
            profiling_accumulator += elapsed
            profiling_frames += 1
            now = time.perf_counter()
            if now - profiling_last_log >= 1.0:
                avg_ms = (profiling_accumulator / max(profiling_frames, 1)) * 1000.0
                fps = profiling_frames / max(now - profiling_last_log, 1e-6)
                print(
                    f"[Metal profiling] rendu moyen {avg_ms:.3f} ms "
                    f"({fps:.1f} fps) sur {profiling_frames} frame(s)"
                )
                profiling_accumulator = 0.0
                profiling_frames = 0
                profiling_last_log = now

    # Résoudre le chemin racine du projet
    project_root = Path(__file__).parent.parent.parent

    # Curseur personnalisé (spec 19) : appliqué après création de la fenêtre
    try:
        set_custom_cursor(project_root)
    except Exception as e:
        import logging
        logging.getLogger("moteur_jeu_presentation").warning("Curseur personnalisé non chargé : %s", e)

    # Charger les configurations AVANT le préchargement et l'écran d'accueil
    # (nécessaire pour le préchargement)
    assets_dir = Path("sprite")
    level_loader = LevelLoader(assets_dir)
    level_path = Path("levels/niveau_plateforme.niveau")

    # Stats en premier : borne max_player_level pour valider [player].level dans le .niveau
    # Le joueur et l'UI exigent player_stats.toml avec display_name (non vide).
    stats_config_path = project_root / "config" / "player_stats.toml"
    if not stats_config_path.exists():
        print(
            f"Erreur: fichier requis introuvable : {stats_config_path}\n"
            "Créez ce fichier avec au minimum les clés racines max_level et display_name "
            "(voir spec/7-systeme-de-niveaux-personnage.md).",
            file=sys.stderr,
        )
        pygame.quit()
        sys.exit(1)
    try:
        stats_loader = PlayerStatsLoader(stats_config_path)
        stats_config = stats_loader.load_stats()
        print(f"Caractéristiques chargées depuis {stats_config_path}")
    except Exception as e:
        print(
            f"Erreur: impossible de charger les caractéristiques depuis {stats_config_path}:\n{e}",
            file=sys.stderr,
        )
        pygame.quit()
        sys.exit(1)

    max_player_level_cap = stats_config.max_level
    level_config = level_loader.load_level(
        level_path, max_player_level=max_player_level_cap
    )

    # Charger les PNJ (optionnel)
    npcs_config = None
    npcs_path = Path("levels/niveau_plateforme.pnj")
    if npcs_path.exists():
        try:
            npc_loader = NPCLoader(assets_dir)
            npcs_config = npc_loader.load_npcs(npcs_path)
        except Exception as e:
            print(f"Warning: Impossible de charger les PNJ depuis {npcs_path}: {e}")
            print("Le jeu continuera sans PNJ.")
    else:
        print(f"Info: Fichier de PNJ introuvable à {npcs_path}, continuant sans PNJ")
    
    # Charger la configuration des objets d'inventaire (optionnel)
    inventory_config = None
    inventory_config_path = project_root / "config" / "inventory_items.toml"
    if inventory_config_path.exists():
        try:
            item_loader = InventoryItemLoader(inventory_config_path)
            inventory_config = item_loader.load_items()
            print(f"Configuration d'inventaire chargée : {len(inventory_config.items)} objets")
        except Exception as e:
            print(f"Warning: Impossible de charger la configuration d'inventaire : {e}")
    else:
        print(f"Info: Fichier de configuration d'inventaire introuvable à {inventory_config_path}, continuant sans inventaire")
    
    # Précharger tous les éléments graphiques (sauf si --skip-preload est activé)
    if not args.skip_preload:
        print("[Préchargement] Début du préchargement des éléments graphiques...")
        
        # Créer le préchargeur
        preloader = AssetPreloader(
            screen=screen,
            screen_width=render_width,
            screen_height=render_height,
            project_root=project_root,
        )
        
        # Précharger tous les éléments
        preloader.preload_all_assets(
            level_config=level_config,
            npcs_config=npcs_config,
            inventory_config=inventory_config,
            stats_config=stats_config,
            player_level=level_config.player_level,
        )
        
        print("[Préchargement] Préchargement terminé.")
    
    # Créer et afficher l'écran d'accueil (sauf si --skip-splash est activé)
    if not args.skip_splash:
        # Créer l'écran d'accueil
        image_path = project_root / "sprite" / "interface" / "image-intro.png"
        
        try:
            splash_screen = SplashScreen(
                image_path=image_path,
                screen_width=render_width,
                screen_height=render_height,
                debug=False,  # Mode debug désactivé en production
            )
        except FileNotFoundError as e:
            print(f"Erreur: {e}")
            print("Le jeu va démarrer directement sans écran d'accueil.")
            splash_screen = None
    else:
        splash_screen = None
    
    # Boucle de l'écran d'accueil
    if splash_screen is not None:
        splash_running = True
        running = True  # Initialiser running pour la boucle d'accueil
        quit_confirmation_dialog_splash: Optional[QuitConfirmationDialog] = None  # Variable pour gérer la boîte de confirmation
        
        while splash_running and splash_screen.is_active and running:
            dt = clock.tick(FPS) / 1000.0
            
            # Limiter le delta time pour éviter des problèmes lors de changements de workspace
            if dt > 0.1:
                dt = 0.1  # Limiter à 100ms maximum (10 FPS minimum)
            
            # Gérer les événements
            # OPTIMISATION: Utiliser le cache de la taille de la fenêtre
            # Pour la conversion des inputs souris :
            # - En mode Metal Hardware Scaling : utiliser la taille LOGIQUE (render_width, render_height)
            #   car SDL retourne déjà les coordonnées souris dans cet espace.
            # - En mode Software Scaling : utiliser la taille PHYSIQUE de la fenêtre
            #   car SDL retourne les coordonnées brutes et on doit faire la conversion nous-mêmes.
            if metal_enabled:
                 display_size = (render_width, render_height)
                 # On n'utilise pas cached_display_size ici pour éviter de mélanger logique/physique
            else:
                if cached_display_size is None:
                    try:
                        cached_display_size = pygame.display.get_window_size()
                    except (pygame.error, AttributeError):
                        cached_display_size = screen.get_size()
                display_size = cached_display_size
            
            for event in pygame.event.get():
                # Si la boîte de confirmation est active, lui passer tous les événements
                if quit_confirmation_dialog_splash is not None:
                    quit_confirmation_dialog_splash.handle_event(
                        event,
                        convert_mouse_pos=lambda pos: convert_mouse_to_internal(
                            pos, display_size
                        ),
                    )
                    # Vérifier si la boîte doit être fermée
                    if quit_confirmation_dialog_splash.should_quit:
                        splash_running = False
                        running = False
                    elif quit_confirmation_dialog_splash.is_dismissed:
                        quit_confirmation_dialog_splash = None
                else:
                    # Boîte non active, gérer les événements normalement
                    if event.type == pygame.QUIT:
                        # Afficher la boîte de confirmation au lieu de quitter directement
                        quit_confirmation_dialog_splash = QuitConfirmationDialog(render_width, render_height)
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            # Afficher la boîte de confirmation au lieu de quitter directement
                            quit_confirmation_dialog_splash = QuitConfirmationDialog(render_width, render_height)
                        else:
                            splash_screen.handle_event(
                                event,
                                convert_mouse_pos=lambda pos: convert_mouse_to_internal(
                                    pos, display_size
                                ),
                            )
                    else:
                        # Passer l'événement à l'écran d'accueil
                        # La conversion des coordonnées de la souris sera faite dans handle_event()
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
            if quit_confirmation_dialog_splash is not None:
                quit_confirmation_dialog_splash.draw(internal_surface)
            
            present_frame(None)
            
            # Vérifier si le jeu doit être lancé
            if splash_screen.should_start_game:
                splash_running = False
        
        # Si l'utilisateur a quitté pendant l'écran d'accueil, ne pas lancer le jeu
        if not running:
            pygame.quit()
            sys.exit(0)
    
    # Créer le système de parallaxe depuis le niveau et récupérer le mapping par tag
    parallax_system, layers_by_tag = level_loader.create_parallax_layers(
        level_config,
        render_width,
        render_height,
    )

    # Pré-calculer les listes de couches par rapport à la profondeur pour éviter les filtres à chaque frame
    # Couches derrière le joueur : depth 0, 1, et depth 2 avec is_background = true
    parallax_layers_behind = [
        layer for layer in parallax_system._layers
        if layer.depth <= 1 or (layer.depth == 2 and layer.is_background)
    ]
    # Couches devant le joueur : depth 2 sans is_background ni is_foreground (plateformes normales)
    parallax_layers_front_normal = [
        layer for layer in parallax_system._layers
        if layer.depth == 2 and not layer.is_background and not layer.is_foreground
    ]
    # Couches devant le joueur : depth 2 avec is_foreground (foreground devant les plateformes)
    parallax_layers_front_foreground = [
        layer for layer in parallax_system._layers
        if layer.depth == 2 and layer.is_foreground
    ]
    # Couches devant le joueur : depth 3 (foreground classique)
    parallax_layers_front_depth3 = [
        layer for layer in parallax_system._layers
        if layer.depth == 3
    ]
    
    # Optimisation : vérifier si les couches de background couvrent toute la hauteur de l'écran
    # Si oui, on peut éviter le fill() de background
    background_covers_screen = any(
        layer._cached_height >= render_height for layer in parallax_layers_behind
    )

    # Créer le système de collisions
    collision_system = CollisionSystem(parallax_system, render_width, render_height)

    # Créer les instances des PNJ (les configurations sont déjà chargées)
    npcs: list[NPC] = []
    npcs_dict: Dict[str, NPC] = {}  # Dictionnaire des PNJ indexés par ID
    if npcs_config is not None:
        try:
            for npc_config in npcs_config.npcs:
                npc = NPC(npc_config, collision_system, assets_dir)
                npcs.append(npc)
                npcs_dict[npc.id] = npc
            print(f"{len(npcs)} PNJ chargés depuis {npcs_path}")
            
            # Les images de dialogue sont déjà préchargées si le préchargement a été fait
            # Sinon, les précharger maintenant
            if args.skip_preload:
                image_assets_root = project_root / "image"
                preload_dialogue_images(npcs_config, assets_root=image_assets_root)
        except Exception as e:
            print(f"Warning: Impossible de créer les instances des PNJ : {e}")
            print("Le jeu continuera sans PNJ.")

    # Créer le système de particules global
    particle_system = ParticleSystem()

    # Créer l'inventaire
    # Les sprites sont déjà préchargés si le préchargement a été fait
    inventory = Inventory(
        item_config=inventory_config,
        particle_system=particle_system  # Passer la référence au système de particules global
    )
    if inventory_config is not None:
        # Si le préchargement n'a pas été fait, précharger maintenant
        if args.skip_preload:
            inventory.preload_all_sprites()
            print(f"Sprites d'inventaire préchargés : {len(inventory._sprite_sheet_cache)} sprite sheets")

    # Initialiser le personnage
    # Déterminer la position X initiale (depuis l'argument ou valeur par défaut)
    # IMPORTANT : L'argument --player-x est dans le repère de conception (1920x1080)
    # Il doit être converti vers le repère de rendu (1920x1080)
    from moteur_jeu_presentation.rendering.config import compute_design_scale
    
    if args.player_x is not None:
        # Convertir la position X du repère de design (1920x1080) vers le repère de rendu (1920x1080)
        scale_x, _ = compute_design_scale((render_width, render_height))
        initial_x = args.player_x * scale_x
    else:
        # Position par défaut : centre de l'écran dans le repère de rendu
        initial_x = render_width / 2
    
    player = Player(
        x=initial_x,  # Position X dans le repère de rendu (1920x1080)
        y=100.0,  # Position initiale en haut pour tester la gravité
        sprite_width=64,
        sprite_height=64,
        animation_speed=10.0,
        player_level=level_config.player_level,
        stats_config=stats_config,
        inventory_config=inventory_config,
    )

    # Passer la référence au système de particules global au joueur
    player.set_particle_system(particle_system)

    # Note: Les caches sont maintenant partagés automatiquement via les caches globaux
    # définis dans assets.preloader, donc il n'est plus nécessaire de partager
    # manuellement les caches entre les instances

    def draw_debug_overlay(target_surface: pygame.Surface) -> None:
        """Affiche les informations de debug (position du joueur)."""
        nonlocal debug_surface_cache, debug_text_cache

        if debug_font is None:
            return

        debug_text = f"Player X: {player.x:.1f}  Y: {player.y:.1f}"
        if debug_surface_cache is None or debug_text != debug_text_cache:
            debug_surface_cache = debug_font.render(
                debug_text,
                True,
                (255, 255, 255),
            )
            # OPTIMISATION 1: Optimiser le format de pixel de la surface
            if debug_surface_cache is not None:
                debug_surface_cache = optimize_surface_format(debug_surface_cache, internal_surface)
            debug_text_cache = debug_text

        if debug_surface_cache is not None:
            debug_rect = debug_surface_cache.get_rect()
            # Convertir la position du repère de conception (1920x1080) vers la résolution interne (1920x1080)
            from moteur_jeu_presentation.rendering.config import compute_design_scale
            _, scale_y = compute_design_scale((render_width, render_height))
            debug_offset_design = 10  # Offset debug dans le repère 1920x1080
            debug_offset = int(debug_offset_design * scale_y)
            debug_rect.topleft = (debug_offset, debug_offset)
            target_surface.blit(debug_surface_cache, debug_rect)

    def redraw_scene(target_surface: pygame.Surface, dirty_rects: Optional[list[pygame.Rect]] = None) -> None:
        """Redessine toute la scène sur la surface cible.
        
        OPTIMISATION CRITIQUE: Utilise le batching des commandes blit pour réduire drastiquement
        le nombre d'appels système et améliorer le FPS de 2-3x.
        
        OPTIMISATION 2: Support des dirty rectangles pour ne redessiner que les zones modifiées.
        
        Args:
            target_surface: Surface pygame sur laquelle dessiner
            dirty_rects: Liste optionnelle de rectangles à redessiner (None = redessiner tout)
        """
        # Le zoom caméra applique un post-process (scale + translation) sur des surfaces intermédiaires.
        # Les dirty rects deviennent incorrects (zones transformées), donc on force un full redraw.
        if camera_zoom_controller.is_active:
            _full_redraw_scene(target_surface)
            return

        # OPTIMISATION 2: Si dirty_rects est fourni et activé, ne redessiner que ces zones
        if _use_dirty_rects and dirty_rects is not None and len(dirty_rects) > 0 and not _full_redraw:
            # Redessiner uniquement les zones sales
            for rect in dirty_rects:
                # Clipper le rectangle à la taille de la surface
                clipped_rect = rect.clip(target_surface.get_rect())
                if clipped_rect.width > 0 and clipped_rect.height > 0:
                    # Créer une sous-surface temporaire pour cette zone
                    temp_surface = target_surface.subsurface(clipped_rect)
                    # Redessiner cette zone spécifique
                    _redraw_region(temp_surface, clipped_rect.x, clipped_rect.y, target_surface)
            return
        
        # Redessiner toute la scène (mode normal ou première frame)
        _full_redraw_scene(target_surface)
    
    def _redraw_region(region_surface: pygame.Surface, offset_x: int, offset_y: int, full_surface: pygame.Surface) -> None:
        """Redessine une région spécifique de la scène.
        
        Args:
            region_surface: Surface de la région à redessiner
            offset_x: Offset horizontal de la région
            offset_y: Offset vertical de la région
            full_surface: Surface complète pour référence
        """
        # Pour l'instant, on redessine simplement toute la scène
        # Une implémentation plus fine nécessiterait de savoir quels éléments sont dans cette région
        # Ceci est une version simplifiée - peut être améliorée plus tard
        pass

    def _blit_zoomed(
        src: pygame.Surface,
        dst: pygame.Surface,
        scaled_size: tuple[int, int],
        offset: tuple[int, int],
        *,
        alpha: bool,
    ) -> None:
        """Blit une scène sur dst en appliquant scale + offset.

        IMPORTANT perf: éviter smoothscale si transform neutre.
        """
        nonlocal camera_scaled_scene_surface, camera_cached_scaled_size

        # OPTIMISATION: Éviter smoothscale si la taille est identique (scale == 1.0) et pas d'offset
        src_size = src.get_size()
        if scaled_size == src_size and offset == (0, 0):
            dst.blit(src, (0, 0))
            return

        if camera_cached_scaled_size != scaled_size:
            camera_scaled_scene_surface = None
            camera_cached_scaled_size = scaled_size

        # alpha is currently unused (scene surface has no alpha), kept for call-site compatibility
        _ = alpha
        
        # OPTIMISATION: Éviter smoothscale si la taille est identique (scale == 1.0)
        if scaled_size == src_size:
            # Pas besoin de redimensionner, bliter directement
            dst.blit(src, offset)
            return
        
        if camera_scaled_scene_surface is None:
            camera_scaled_scene_surface = pygame.Surface(scaled_size).convert(dst)
        pygame.transform.smoothscale(src, scaled_size, camera_scaled_scene_surface)
        dst.blit(camera_scaled_scene_surface, offset)

    def _draw_scene_base(dst: pygame.Surface, world_particle_commands: list[tuple[pygame.Surface, tuple[int, int]]]) -> None:
        """Dessine la scène 'monde' (fond + entités + particules monde)."""
        # Optimisation : éviter le fill() si les couches de background couvrent tout l'écran
        if not background_covers_screen:
            dst.fill((30, 30, 30))  # Couleur de fond sombre

        # OPTIMISATION: Réutiliser la liste de commandes au lieu de la recréer
        nonlocal _reusable_layer_commands
        _reusable_layer_commands.clear()

        # Dessiner les couches derrière le joueur (depth 0 et 1)
        for layer in parallax_layers_behind:
            _reusable_layer_commands.extend(parallax_system._get_layer_blit_commands(layer))

        # Envoyer toutes les commandes des layers de fond en un seul appel
        if _reusable_layer_commands:
            dst.blits(_reusable_layer_commands, False)

        # Dessiner les entités (joueur + PNJ) en une seule passe de blitting
        draw_entities(dst, camera_x)

        # Dessiner l'indication d'interaction si un PNJ est à portée (pas pendant transition)
        if current_dialogue is None and interaction_font is not None and not player.level_transition_active:
            player_position = progress_tracker.get_current_x()
            nearest_npc = find_nearest_interactable_npc(player.x, player.y, npcs, player_position)
            if nearest_npc:
                pulse = 0.7 + 0.3 * (math.sin(current_ticks / 500.0) * 0.5 + 0.5)
                draw_interaction_indicator(
                    dst,
                    nearest_npc,
                    camera_x,
                    interaction_font,
                    player_position,
                    base_font_size_design,
                    pulse,
                    interaction_indicator_cache,
                    quest_interaction_font,
                    interaction_font_cache,
                )

        # OPTIMISATION: Réutiliser la liste de commandes au lieu de la recréer
        nonlocal _reusable_front_layer_commands
        _reusable_front_layer_commands.clear()

        # Dessiner les couches devant le joueur
        for layer in parallax_layers_front_normal:
            _reusable_front_layer_commands.extend(parallax_system._get_layer_blit_commands(layer))
        for layer in parallax_layers_front_foreground:
            _reusable_front_layer_commands.extend(parallax_system._get_layer_blit_commands(layer))
        for layer in parallax_layers_front_depth3:
            _reusable_front_layer_commands.extend(parallax_system._get_layer_blit_commands(layer))

        if _reusable_front_layer_commands:
            dst.blits(_reusable_front_layer_commands, False)

        # Particules monde uniquement (les particules "screen_space" sont rendues en overlay)
        if world_particle_commands:
            dst.blits(world_particle_commands, False)

    def _draw_overlay_ui(dst: pygame.Surface) -> None:
        """Dessine l'UI overlay (non impactée par zoom caméra)."""
        # UI overlay (ne doit pas être impactée par le zoom caméra)
        stats_display.draw(dst, dt)
        # Afficher le HUD de progression uniquement si l'option --hide-info-player n'est pas activée
        if not args.hide_info_player:
            progress_hud.draw(dst)
        # Afficher les informations de debug (position du joueur) uniquement si l'option --hide-info-player n'est pas activée
        if not args.hide_info_player:
            draw_debug_overlay(dst)

        if profiling_metal_enabled and fps_font is not None:
            nonlocal fps_surface_cache, fps_text_cache
            fps_text = f"FPS: {fps_display_value:.1f}"
            if fps_surface_cache is None or fps_text_cache != fps_text:
                fps_surface_cache = fps_font.render(fps_text, True, (255, 255, 255))
                if fps_surface_cache is not None:
                    fps_surface_cache = optimize_surface_format(fps_surface_cache, internal_surface)
                fps_text_cache = fps_text

            if fps_surface_cache is not None:
                fps_rect = fps_surface_cache.get_rect()
                from moteur_jeu_presentation.rendering.config import compute_design_scale

                _, scale_y = compute_design_scale((render_width, render_height))
                padding = int(10 * scale_y)
                fps_rect.topright = (render_width - padding, padding)
                dst.blit(fps_surface_cache, fps_rect)

    def _draw_bubbles(dst: pygame.Surface) -> None:
        """Dessine les bulles dans le repère 'monde' (avant zoom)."""
        if current_dialogue is not None:
            current_dialogue.draw(dst, camera_x)
        if speech_bubble is not None:
            speech_bubble.draw(dst, camera_x, dt)

    def _draw_bubbles_after_zoom(dst: pygame.Surface, transform) -> None:
        """Dessine les bulles après le zoom (elles n'influencent pas la caméra).

        Objectif: éviter que la caméra se décale quand la taille de la bulle change.
        On calcule la position écran via la transformation (offset + zoom) mais on garde
        la taille de la bulle telle quelle, puis on clamp pour qu'elle reste visible.
        """
        # current_dialogue.current_bubble: on n'anime pas ici (déjà géré par le dialogue)
        bubble_pairs: list[tuple[SpeechBubble, float]] = []
        if current_dialogue is not None and current_dialogue.current_bubble is not None:
            bubble_pairs.append((current_dialogue.current_bubble, 0.0))
        if speech_bubble is not None:
            bubble_pairs.append((speech_bubble, dt))

        for bubble, bubble_dt in bubble_pairs:
            # Mettre à jour surface + rect (sans dessiner)
            bubble.update(camera_x, bubble_dt)
            if bubble.surface is None:
                continue

            # Position écran issue de la scène zoomée (mais sans zoom de taille de bulle)
            x = transform.offset_x + bubble.rect.x * transform.zoom
            y = transform.offset_y + bubble.rect.y * transform.zoom
            x_i = int(round(x))
            y_i = int(round(y))

            # Clamp pour garantir visibilité
            max_x = render_width - bubble.surface.get_width()
            max_y = render_height - bubble.surface.get_height()
            if max_x < 0:
                max_x = 0
            if max_y < 0:
                max_y = 0
            if x_i < 0:
                x_i = 0
            elif x_i > max_x:
                x_i = max_x
            if y_i < 0:
                y_i = 0
            elif y_i > max_y:
                y_i = max_y

            dst.blit(bubble.surface, (x_i, y_i))

    def _draw_top_overlays(dst: pygame.Surface, overlay_particle_commands: list[tuple[pygame.Surface, tuple[int, int]]]) -> None:
        """Dessine les overlays (au-dessus de tout) + particules screen-space."""
        # Particules overlay (screen-space) : ex. confettis de transition de niveau
        if overlay_particle_commands:
            dst.blits(overlay_particle_commands, False)

        # Transition niveau (au-dessus de tout)
        player._draw_level_transition(dst)

        # Fondu au noir (au-dessus de tout)
        if event_system is not None:
            fade_alpha, fade_text, text_alpha = event_system.get_screen_fade_state()
            if fade_alpha > 0:
                fade_surface = pygame.Surface((render_width, render_height))
                fade_surface.set_alpha(fade_alpha)
                fade_surface.fill((0, 0, 0))
                dst.blit(fade_surface, (0, 0))

                if fade_text and text_alpha > 0:
                    from moteur_jeu_presentation.rendering.config import compute_design_scale

                    _, scale_y = compute_design_scale((render_width, render_height))
                    font_size = int(60 * scale_y)
                    try:
                        fade_font = pygame.font.SysFont("arial", font_size, bold=True)
                    except pygame.error:
                        fade_font = pygame.font.SysFont("sans-serif", font_size, bold=True)

                    text_surface = fade_font.render(fade_text, True, (255, 255, 255))
                    text_surface.set_alpha(text_alpha)
                    text_x = (render_width - text_surface.get_width()) // 2
                    text_y = (render_height - text_surface.get_height()) // 2
                    dst.blit(text_surface, (text_x, text_y))

        # Boîte de confirmation quitter (au-dessus de tout)
        if quit_confirmation_dialog is not None:
            quit_confirmation_dialog.draw(dst)
    
    def _full_redraw_scene(target_surface: pygame.Surface) -> None:
        """Redessine toute la scène.
        
        Args:
            target_surface: Surface pygame sur laquelle dessiner
        """
        # Particules: calculer en une passe et réutiliser pour la scène + overlays.
        world_particle_commands, overlay_particle_commands = particle_system.get_display_commands_split(
            camera_x,
            render_width,
            render_height,
            margin=100,
        )

        # Path without zoom: keep original render order
        if not camera_zoom_controller.is_active:
            _draw_scene_base(target_surface, world_particle_commands)
            _draw_overlay_ui(target_surface)
            _draw_bubbles(target_surface)
            _draw_top_overlays(target_surface, overlay_particle_commands)
            return

        # Zoom path: render scene, apply zoom, draw overlay UI (unaffected), then draw bubbles AFTER zoom.
        _draw_scene_base(scene_surface, world_particle_commands)

        # Compute player draw rect (pre-zoom). IMPORTANT: bubbles do NOT influence the camera transform.
        player_sprite, (player_draw_x, player_draw_y) = player.get_draw_command(camera_x)
        player_draw_rect = pygame.Rect(
            int(player_draw_x),
            int(player_draw_y),
            int(player_sprite.get_width()),
            int(player_sprite.get_height()),
        )

        transform = camera_zoom_controller.compute_transform(
            player_draw_rect=player_draw_rect,
            bubble_rects=None,
            layers_by_tag=layers_by_tag,
        )

        # Clear and blit zoomed scene
        target_surface.fill((0, 0, 0))
        _blit_zoomed(
            scene_surface,
            target_surface,
            transform.scaled_size,
            (transform.offset_x, transform.offset_y),
            alpha=False,
        )

        # Overlay UI (not affected by zoom)
        _draw_overlay_ui(target_surface)

        # Bubbles AFTER zoom (camera does not move because of bubble size)
        _draw_bubbles_after_zoom(target_surface, transform)

        # Top overlays
        _draw_top_overlays(target_surface, overlay_particle_commands)

    # OPTIMISATION: Cache des calculs de visibilité des PNJ
    _visibility_cache: Dict[Tuple[float, float, float], bool] = {}
    _last_camera_x: float = float('inf')
    _visibility_cache_threshold: float = 10.0  # Invalider le cache si la caméra a bougé de plus de 10 pixels

    # OPTIMISATION: Réutiliser les objets temporaires pour réduire les allocations
    _temp_visibility_cache_key: list[float] = [0.0, 0.0, 0.0]  # Évite la création de tuple à chaque frame

    # OPTIMISATION 2: Système de dirty rectangles pour ne redessiner que les zones modifiées
    # NOTE: Désactivé par défaut car complexe avec le scrolling. Peut être activé pour des scènes statiques.
    _use_dirty_rects = False  # Désactivé pour l'instant
    _dirty_rects = []  # type: list[pygame.Rect]
    _full_redraw = True  # True pour la première frame ou après un changement majeur
    _last_camera_x_for_dirty = float('inf')
    _last_player_x = float('inf')
    _last_player_y = float('inf')
    _dirty_rect_threshold = 5.0  # Seuil de mouvement pour déclencher un dirty rect

    def optimize_surface_format(surface: pygame.Surface, reference_surface: pygame.Surface) -> pygame.Surface:
        """Optimise le format de pixel d'une surface pour correspondre à la surface de référence.
        
        OPTIMISATION 1: S'assure que toutes les surfaces utilisent le format de pixel optimal
        pour améliorer les performances de blitting.
        
        Args:
            surface: Surface à optimiser
            reference_surface: Surface de référence (généralement l'écran)
            
        Returns:
            Surface optimisée (peut être la même si déjà optimisée)
        """
        # Si la surface a déjà le bon format, ne rien faire
        if surface.get_flags() & pygame.SRCALPHA:
            # Surface avec transparence : utiliser convert_alpha avec référence
            try:
                return surface.convert_alpha(reference_surface)
            except (TypeError, AttributeError):
                # Fallback pour les versions de pygame qui ne supportent pas le paramètre
                return surface.convert_alpha()
        else:
            # Surface sans transparence : utiliser convert avec référence
            try:
                return surface.convert(reference_surface)
            except (TypeError, AttributeError):
                # Fallback pour les versions de pygame qui ne supportent pas le paramètre
                return surface.convert()

    def draw_entities(surface: pygame.Surface, camera_x: float) -> None:
        """Dessine le joueur et les PNJ en regroupant les blits pour réduire les appels CPU->SDL."""
        # OPTIMISATION: Réutiliser les listes de commandes au lieu de les recréer
        nonlocal _reusable_draw_commands, _reusable_name_commands
        nonlocal _visibility_cache, _last_camera_x, _temp_visibility_cache_key
        _reusable_draw_commands.clear()
        _reusable_name_commands.clear()
        
        _reusable_draw_commands.append(player.get_draw_command(camera_x))
        visible_npcs: list[NPC] = []

        # OPTIMISATION: Invalider le cache de visibilité si la caméra a bougé significativement
        if abs(camera_x - _last_camera_x) > _visibility_cache_threshold:
            _visibility_cache.clear()
            _last_camera_x = camera_x

        for npc in npcs:
            # OPTIMISATION: Utiliser le cache de visibilité et éviter la création de tuple
            _temp_visibility_cache_key[0] = npc.x
            _temp_visibility_cache_key[1] = npc.y
            _temp_visibility_cache_key[2] = camera_x
            cache_key = tuple(_temp_visibility_cache_key)
            if cache_key in _visibility_cache:
                is_visible = _visibility_cache[cache_key]
            else:
                is_visible = is_entity_visible(
                    npc.x,
                    npc.y,
                    getattr(npc, "display_width", npc.sprite_width),
                    getattr(npc, "display_height", npc.sprite_height),
                    camera_x,
                    render_width,
                    render_height,
                )
                _visibility_cache[cache_key] = is_visible
            
            if is_visible:
                visible_npcs.append(npc)
                _reusable_draw_commands.append(npc.get_draw_command(camera_x))

        surface.blits(_reusable_draw_commands, False)

        # Dessiner le nom du joueur d'abord
        player_name_command = player.get_name_draw_command(camera_x)
        if player_name_command is not None:
            _reusable_name_commands.append(player_name_command)

        for npc in visible_npcs:
            name_command = npc.get_name_draw_command(camera_x)
            if name_command is not None:
                _reusable_name_commands.append(name_command)

        if _reusable_name_commands:
            surface.blits(_reusable_name_commands, False)

        # Dessiner l'inventaire au-dessus du nom
        if player.inventory is not None:
            player.draw_inventory(surface, camera_x, render_width, render_height)

        # Dessiner l'affichage de level up si actif (au-dessus de l'inventaire)
        player._draw_level_up(surface, camera_x)

    # Position de la caméra (suit le personnage)
    camera_x = 0.0

    # Interface d'affichage des statistiques
    stats_display = PlayerStatsDisplay(
        player=player,
        screen_width=render_width,
        screen_height=render_height,
    )

    # Contrôleur de zoom caméra (post-process)
    camera_zoom_controller = CameraZoomController()

    # Suivi de l'avancement horizontal
    progress_tracker = LevelProgressTracker(player=player)
    # Initialiser current_x avec la position initiale du joueur
    # pour que les dialogues puissent être déclenchés immédiatement
    progress_tracker.update(0.0)
    progress_hud = LevelProgressHUD(progress_tracker, debug_mode=False)

    # Système de déclencheurs d'événements
    event_system: Optional[EventTriggerSystem] = None
    events_path = Path("levels/niveau_plateforme.event")
    if events_path.exists():
        try:
            event_system = EventTriggerSystem(
                progress_tracker,
                npcs_dict,
                layers_by_tag,
                parallax_system,
                collision_system,  # Optionnel, nécessaire pour supprimer les collisions lors du masquage
                player,  # Optionnel, nécessaire pour les événements d'inventaire
                particle_system,  # Optionnel, nécessaire pour les événements particle_effect
                camera_zoom_controller,  # Optionnel, pour les événements de zoom caméra
            )
            event_system.load_events(events_path)
            print(f"Événements chargés depuis {events_path}")
        except Exception as e:
            print(f"Warning: Impossible de charger les événements depuis {events_path}: {e}")
            print("Le jeu continuera sans événements.")
    else:
        print(f"Info: Fichier d'événements introuvable à {events_path}, continuant sans événements")

    # Bulle de dialogue (optionnelle, pour test)
    speech_bubble: Optional[SpeechBubble] = None
    
    # État du dialogue en cours avec un PNJ
    current_dialogue: Optional[DialogueState] = None

    # Variable pour gérer la boîte de confirmation de quitter
    quit_confirmation_dialog: Optional[QuitConfirmationDialog] = None

    # Boucle principale
    running = True
    while running:
        # Démarrer le profiling après quelques frames de warm-up (pour éviter les initialisations)
        if profiling_enabled and profiling_frame_count == 10 and profiler is not None:
            print("Démarrage du profiling...")
            profiler.enable()
        
        # Calculer le delta time
        dt = clock.tick(FPS) / 1000.0  # Convertir en secondes
        
        # Incrémenter le compteur de frames pour le profiling
        if profiling_enabled:
            profiling_frame_count += 1
        
        # Mettre en cache pygame.time.get_ticks() pour éviter les appels multiples par frame
        current_ticks = pygame.time.get_ticks()
        
        # Limiter le delta time pour éviter des problèmes lors de changements de workspace
        # Si le delta time est trop grand (par exemple > 0.1 seconde), le limiter
        # Cela évite que le personnage se déplace trop loin ou disparaisse
        if dt > 0.1:
            dt = 0.1  # Limiter à 100ms maximum (10 FPS minimum)
        
        # Calculer le FPS pour l'affichage (mise à jour toutes les 0.5 secondes pour stabilité)
        if profiling_metal_enabled:
            fps_display_accumulator += dt
            fps_display_frames += 1
            now = time.perf_counter()
            if now - fps_display_last_update >= 0.5:  # Mettre à jour toutes les 0.5 secondes
                if fps_display_frames > 0 and fps_display_accumulator > 0:
                    fps_display_value = fps_display_frames / fps_display_accumulator
                else:
                    # Fallback : utiliser 1.0 / dt si disponible
                    fps_display_value = 1.0 / dt if dt > 0 else 0.0
                fps_display_accumulator = 0.0
                fps_display_frames = 0
                fps_display_last_update = now

        # Gérer les événements
        for event in pygame.event.get():
            # Si la boîte de confirmation est active, lui passer tous les événements en priorité
            if quit_confirmation_dialog is not None:
                # Convertir les coordonnées de la souris si nécessaire
                if metal_enabled:
                    display_size_for_convert = (render_width, render_height)
                else:
                    if cached_display_size is None:
                        try:
                            cached_display_size = pygame.display.get_window_size()
                        except (pygame.error, AttributeError):
                            cached_display_size = screen.get_size()
                    display_size_for_convert = cached_display_size
                
                quit_confirmation_dialog.handle_event(
                    event,
                    convert_mouse_pos=lambda pos: convert_mouse_to_internal(
                        pos, display_size_for_convert
                    ),
                )
                # Vérifier si la boîte doit être fermée
                if quit_confirmation_dialog.should_quit:
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
                    elif event.key == pygame.K_t:
                        # Lancer le dialogue avec le PNJ le plus proche
                        # Deux conditions doivent être remplies : distance horizontale ET distance verticale
                        # Blocage pendant la transition de niveau
                        if current_dialogue is None and not player.level_transition_active:
                            # Obtenir la position actuelle du joueur pour vérifier les blocs de dialogue disponibles
                            player_position = progress_tracker.get_current_x()
                            nearest_npc = find_nearest_interactable_npc(player.x, player.y, npcs, player_position)
                            if nearest_npc:
                                # Démarrer le dialogue (la position du joueur est obtenue via progress_tracker)
                                current_dialogue = start_dialogue(nearest_npc, progress_tracker, event_system)
                    elif event.key == pygame.K_p:
                        # Augmenter le niveau du joueur sans dépasser le maximum
                        new_level = min(player.player_level + 1, player.max_player_level)
                        if new_level != player.player_level:
                            player.set_level(new_level)
                            print(f"Niveau du joueur augmenté à {new_level}")
                    elif event.key == pygame.K_o:
                        # Diminuer le niveau du joueur sans descendre sous le minimum
                        new_level = max(player.player_level - 1, MIN_PLAYER_LEVEL)
                        if new_level != player.player_level:
                            player.set_level(new_level)
                            print(f"Niveau du joueur diminué à {new_level}")
                    elif event.key == pygame.K_s:
                        # Afficher/masquer l'interface des statistiques
                        stats_display.toggle()
                    elif event.key == pygame.K_b:
                        # Afficher/masquer une bulle de dialogue (pour test)
                        if speech_bubble is None:
                            speech_bubble = show_speech_bubble(
                                character=player,
                                text="Bonjour !\nJe suis Thomas.\nComment allez-vous ?",
                                side="right",
                                font_size=40,
                                padding=12,
                            )
                            print("Bulle de dialogue affichée (appuyez sur B pour la masquer, cliquez sur la bulle pour accélérer)")
                        else:
                            speech_bubble = None
                            print("Bulle de dialogue masquée")
                    elif event.key == pygame.K_u:
                        # Confirmer le level up en augmentant le niveau de +1 et masquer l'affichage
                        if player.level_up_active:
                            # Augmentation de +1 sans dépasser max_level (player_stats.toml)
                            new_level = min(player.player_level + 1, player.max_player_level)
                            # Augmenter le niveau si possible (utilise les mécanismes existants)
                            # Note : L'augmentation est toujours de +1 niveau, il n'est pas possible d'augmenter de plusieurs niveaux
                            if new_level != player.player_level:
                                # Démarrer l'animation de transition de niveau (voir spécification 11)
                                player.start_level_transition(player.player_level, new_level, camera_zoom_controller)
                                player.set_level(new_level)
                                print(f"Niveau du joueur augmenté à {new_level}")
                            # Masquer l'affichage de level up
                            player.hide_level_up()
                            # Réinitialiser tous les événements de type level_up pour permettre de les redéclencher
                            if event_system is not None:
                                for event_config in event_system.events:
                                    if event_config.event_type == "level_up":
                                        event_system.reset_event_by_identifier(event_config.identifier)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Transmettre les événements de clic à la bulle de dialogue
                    if speech_bubble is not None:
                        speech_bubble.handle_event(event, camera_x)
                    
                    # Transmettre les événements au dialogue en cours
                    if current_dialogue is not None:
                        if current_dialogue.handle_event(event, camera_x):
                            # Si le dialogue est terminé, le nettoyer
                            if current_dialogue.is_complete():
                                current_dialogue = None
                elif event.type == pygame.MOUSEMOTION:
                    # Transmettre les événements de souris à l'interface des statistiques
                    # pour gérer le survol des icônes d'information
                    if stats_display.is_visible:
                        # Convertir les coordonnées de la souris de la résolution d'affichage vers la résolution interne
                        # OPTIMISATION: Utiliser le cache de la taille de la fenêtre
                        if metal_enabled:
                            display_size = (render_width, render_height)
                        else:
                            if cached_display_size is None:
                                try:
                                    cached_display_size = pygame.display.get_window_size()
                                except (pygame.error, AttributeError):
                                    cached_display_size = screen.get_size()
                            display_size = cached_display_size
                            
                        if display_size[0] <= 0 or display_size[1] <= 0:
                            display_size = screen.get_size()
                            if not metal_enabled:
                                cached_display_size = display_size
                        internal_mouse_pos = convert_mouse_to_internal(event.pos, display_size)
                        # Créer un nouvel événement avec les coordonnées converties
                        converted_event = pygame.event.Event(
                            pygame.MOUSEMOTION,
                            pos=internal_mouse_pos,
                            rel=event.rel,
                            buttons=event.buttons,
                        )
                        stats_display.handle_mouse_event(converted_event)
                elif event.type == pygame.WINDOWFOCUSLOST:
                    # La fenêtre a perdu le focus (changement de workspace, etc.)
                    # Ne rien faire, le jeu continue de tourner
                    pass
                elif event.type == pygame.WINDOWFOCUSGAINED:
                    # La fenêtre a regagné le focus
                    # Invalider le cache de la taille de la fenêtre
                    cached_display_size = None
                    # S'assurer que la surface d'affichage est toujours valide
                    # En mode plein écran, pygame peut avoir besoin de recréer la surface
                    try:
                        # Vérifier que la surface est toujours valide
                        _ = screen.get_size()
                    except (pygame.error, AttributeError):
                        # Recréer la surface si elle est invalide
                        try:
                            screen = set_display_mode(
                                current_display_size,
                                current_display_flags,
                            )
                        except pygame.error:
                            # Fallback vers mode fenêtré si le plein écran échoue
                            current_display_size, current_display_flags = find_fallback_size(), windowed_flags
                            screen = set_display_mode(current_display_size, current_display_flags)
                    
                    # S'assurer que la surface interne est toujours valide
                    # Si elle est invalidée, la recréer (ou réassigner)
                    try:
                        _ = internal_surface.get_size()
                        # En mode Metal, si l'écran a changé, internal_surface (qui est un alias) doit être mis à jour
                        if metal_enabled and internal_surface != screen:
                             internal_surface = screen
                    except (pygame.error, AttributeError):
                        if metal_enabled:
                            internal_surface = screen
                        else:
                            internal_surface = pygame.Surface((render_width, render_height)).convert(screen)
                        
                        # Invalider le cache
                        cached_scaled_surface = None
                        cached_scaled_size = None
                        # Invalider le cache FPS
                        fps_surface_cache = None
                        fps_text_cache = ""
                elif event.type in (pygame.WINDOWSIZECHANGED, pygame.VIDEORESIZE):
                    # La taille de la fenêtre a changé, invalider le cache
                    cached_display_size = None

        if player.consume_camera_snap_request():
            # Ne pas mettre à jour la caméra si elle est fixe (zoom sur sprite actif)
            if not camera_zoom_controller.is_camera_fixed:
                camera_x = player.x - render_width / 2

        # Récupérer l'état des touches
        keys = pygame.key.get_pressed()

        # Synchroniser la caméra courante pour les transitions de zoom
        camera_zoom_controller.set_current_camera_x(camera_x)

        # Mettre à jour le système de déclencheurs d'événements AVANT le calcul du mouvement
        # Cela permet aux plateformes mobiles de se déplacer et d'appliquer leur mouvement aux passagers
        if event_system is not None:
            event_system.update(dt)

        # Mettre à jour le zoom caméra (post-process) indépendamment du gameplay/UI
        camera_zoom_controller.update(dt)

        # Appliquer la caméra interpolée si un zoom la contrôle
        camera_x_override = camera_zoom_controller.get_camera_x_override()
        if camera_x_override is not None:
            camera_x = camera_x_override

        # Ne mettre à jour le jeu que si l'interface des stats n'est pas affichée
        if not stats_display.is_visible:
            # Blocage complet pendant la transition de niveau
            if not player.level_transition_active:
                # Obtenir le rectangle de collision du personnage (pour la détection des blocs grimpables)
                player_rect = player.get_collision_rect()
                
                # Vérifier si le joueur est sur un bloc grimpable
                collision_system.check_climbable_collision(player_rect, camera_x, player)
                
                # Gérer la grimpe (prioritaire sur le saut)
                climb_dy = player._handle_climb_input(keys, dt)
                
                if climb_dy != 0.0:
                    # Le joueur est en train de grimper
                    # Mettre à jour les animations (mais pas le saut, qui est géré par _handle_climb_input)
                    # On appelle update() mais _handle_jump_input ne fera rien car is_climbing est True
                    has_constraint = current_dialogue is not None and current_dialogue.has_position_constraint()
                    player.update(dt, camera_x, keys, has_position_constraint=has_constraint)
                    
                    # Calculer le déplacement horizontal
                    # Neutraliser le mouvement horizontal si le joueur est attaché à une plateforme mobile
                    # ou si une contrainte de position est active dans le dialogue
                    dx = 0.0
                    if player.attached_platform is None:
                        # Vérifier si une contrainte de position est active dans le dialogue
                        if current_dialogue is not None and current_dialogue.has_position_constraint():
                            # Blocage du mouvement horizontal pendant la contrainte
                            dx = 0.0
                        else:
                            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                                dx -= player.speed * dt
                            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                                dx += player.speed * dt
                    
                    # Appliquer le déplacement vertical de grimpe
                    dy = climb_dy
                    # La gravité est désactivée pendant la grimpe (ne pas appeler apply_gravity)
                else:
                    # Pas de grimpe, comportement normal
                    # Mettre à jour le personnage (gère le saut et les animations)
                    # IMPORTANT: Doit être appelé avant le calcul du déplacement pour que le saut modifie velocity_y
                    has_constraint = current_dialogue is not None and current_dialogue.has_position_constraint()
                    player.update(dt, camera_x, keys, has_position_constraint=has_constraint)

                    # Appliquer la gravité (si le personnage n'est pas au sol)
                    if not player.is_on_ground:
                        player.apply_gravity(dt)

                    # Calculer le déplacement prévu
                    # Permettre le mouvement horizontal même si le joueur est attaché à une plateforme mobile
                    # Le mouvement vertical sera géré par la plateforme
                    dx = 0.0
                    # Vérifier si une contrainte de position est active dans le dialogue
                    if current_dialogue is not None and current_dialogue.has_position_constraint():
                        # Blocage du mouvement horizontal pendant la contrainte
                        dx = 0.0
                    else:
                        # Permettre le mouvement horizontal même si attaché à une plateforme
                        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                            dx -= player.speed * dt
                        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                            dx += player.speed * dt

                    # Le déplacement vertical est géré par la gravité (et le saut qui modifie velocity_y)
                    dy = player.velocity_y * dt

                # Obtenir le rectangle de collision du personnage (mise à jour après déplacement)
                player_rect = player.get_collision_rect()

                # Résoudre les collisions (player hérite maintenant de Entity)
                corrected_dx, corrected_dy, is_on_ground = collision_system.resolve_collision(
                    player_rect, dx, dy, player, camera_x
                )

                # Mettre à jour l'état au sol
                player.is_on_ground = is_on_ground

                # Appliquer le déplacement corrigé
                # Le déplacement est calculé pour que le rectangle de collision soit correctement positionné
                # et que le bas du sprite visuel reste aligné avec le bas du rectangle de collision
                player.x += corrected_dx
                player.y += corrected_dy
                
                # Maintenir la position X si une contrainte de position est active dans le dialogue
                if current_dialogue is not None and current_dialogue.has_position_constraint():
                    constrained_x = current_dialogue.get_constrained_x_position()
                    if constrained_x is not None:
                        player.x = constrained_x
                
                # Appliquer les déplacements des plateformes mobiles aux passagers
                # (doit être fait APRÈS la résolution des collisions)
                collision_system.apply_platform_movements([player])
            else:
                # Pendant la transition, le personnage ne bouge pas
                # Mettre à jour uniquement les animations (pas le mouvement)
                has_constraint = current_dialogue is not None and current_dialogue.has_position_constraint()
                player.update(dt, camera_x, keys, has_position_constraint=has_constraint)

            # Mettre à jour la caméra pour suivre le personnage
            # La caméra suit le personnage horizontalement (sauf si fixe pour zoom sur sprite)
            if not camera_zoom_controller.is_camera_fixed:
                camera_x = player.x - render_width / 2

            # Mettre à jour le système de parallaxe
            parallax_system.update(camera_x, dt)

            # Mettre à jour les PNJ
            for npc in npcs:
                npc.update(dt, camera_x)
                # Appliquer les déplacements des plateformes mobiles aux PNJ attachés
                collision_system.apply_platform_movements([npc])

        # Mettre à jour le dialogue en cours (indépendamment de l'interface stats)
        if current_dialogue is not None:
            current_dialogue.update(camera_x, dt)
            # Vérifier si le dialogue est terminé
            if current_dialogue.is_complete():
                current_dialogue = None

        # Mettre à jour le système de particules global
        # OPTIMISATION: Passer les paramètres de la caméra pour le culling et éviter les calculs inutiles
        particle_system.update(dt, camera_x, render_width, render_height, margin=200)

        # Mettre à jour les animations d'inventaire (se fait même si l'interface stats est affichée)
        # Passer camera_x pour la conversion des coordonnées lors de la création des particules
        if player.inventory is not None:
            player.inventory.update_animations(dt, camera_x)

        # Mettre à jour le suivi de progression (se fait même si l'interface stats est affichée)
        progress_tracker.update(dt)

        # OPTIMISATION 2: Calculer les dirty rectangles avant de redessiner (si activé)
        # Note: Pas besoin de nonlocal car ces variables sont dans le même scope (fonction main())
        dirty_rects_to_use = None
        if _use_dirty_rects:
            # Détecter les changements significatifs
            camera_moved = abs(camera_x - _last_camera_x_for_dirty) > _dirty_rect_threshold
            player_moved = abs(player.x - _last_player_x) > _dirty_rect_threshold or abs(player.y - _last_player_y) > _dirty_rect_threshold
            
            # Si la caméra ou le joueur a bougé significativement, marquer pour redessiner
            if _full_redraw or camera_moved or player_moved:
                _dirty_rects.clear()
                _full_redraw = False
                _last_camera_x_for_dirty = camera_x
                _last_player_x = player.x
                _last_player_y = player.y
            
            dirty_rects_to_use = _dirty_rects if not _full_redraw and len(_dirty_rects) > 0 else None
        
        # Dessiner sur la surface interne (avec dirty rectangles si disponibles et activés)
        redraw_scene(internal_surface, dirty_rects_to_use)

        # Mettre à l'échelle et afficher sur l'écran
        try:
            # Vérifier que la surface interne est valide
            _ = internal_surface.get_size()
            present_frame(dirty_rects_to_use if _use_dirty_rects else None)
        except (pygame.error, AttributeError):
            # Si une surface est invalide, essayer de la recréer
            # Recréer la surface interne si nécessaire
            try:
                _ = internal_surface.get_size()
                if metal_enabled and internal_surface != screen:
                    internal_surface = screen
            except (pygame.error, AttributeError):
                if metal_enabled:
                    internal_surface = screen
                else:
                    internal_surface = pygame.Surface((render_width, render_height)).convert(screen)
                # Invalider le cache FPS
                fps_surface_cache = None
                fps_text_cache = ""
            
            # Recréer la surface d'affichage si nécessaire
            try:
                _ = screen.get_size()
            except (pygame.error, AttributeError):
                try:
                    screen = set_display_mode(
                        current_display_size,
                        current_display_flags,
                    )
                except pygame.error:
                    # Fallback vers mode fenêtré si le plein écran échoue
                    current_display_size, current_display_flags = find_fallback_size(), windowed_flags
                    screen = set_display_mode(current_display_size, current_display_flags)
                    # Invalider le cache car la taille de l'écran a changé
                    cached_scaled_surface = None
                    cached_scaled_size = None
            
            # Redessiner immédiatement après la recréation (full redraw)
            _full_redraw = True
            redraw_scene(internal_surface, None)
            present_frame(None)
        
        # Arrêter le profiling après le nombre de frames cible
        if profiling_enabled and profiling_frame_count >= (profiling_target_frames + 10) and profiler is not None:
            print("\nArrêt du profiling...")
            profiler.disable()
            
            # Générer et afficher le rapport de profiling
            print(f"\n{'='*80}")
            print("RAPPORT DE PROFILING - TOP 30 FONCTIONS LES PLUS COÛTEUSES")
            print(f"{'='*80}\n")
            
            # Créer un buffer pour capturer les statistiques
            s = io.StringIO()
            ps = pstats.Stats(profiler, stream=s)
            
            # Trier par temps cumulé (tottime) pour voir les vraies consommatrices
            ps.strip_dirs()
            ps.sort_stats('tottime')
            ps.print_stats(30)  # Top 30 fonctions
            
            print(s.getvalue())
            
            # Aussi afficher le rapport trié par temps cumulatif (cumtime)
            print(f"\n{'='*80}")
            print("RAPPORT DE PROFILING - TOP 30 PAR TEMPS CUMULÉ (avec appels)")
            print(f"{'='*80}\n")
            
            s = io.StringIO()
            ps = pstats.Stats(profiler, stream=s)
            ps.strip_dirs()
            ps.sort_stats('cumtime')
            ps.print_stats(30)
            
            print(s.getvalue())
            
            # Sauvegarder les stats pour analyse ultérieure
            profile_output_path = Path(__file__).parent.parent.parent / "profile_results.prof"
            ps.dump_stats(str(profile_output_path))
            print(f"\nStatistiques sauvegardées dans: {profile_output_path}")
            print("Utilisez 'python -m pstats profile_results.prof' pour une analyse interactive\n")
            
            # Quitter automatiquement après le profiling
            running = False

    if metal_enabled:
        disable_metal_acceleration(original_env)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()

