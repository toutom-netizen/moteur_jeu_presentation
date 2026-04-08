"""Module de chargement des fichiers de configuration de PNJ."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Literal, Optional

from PIL import Image

try:
    # Python 3.11+ a tomllib intégré
    import tomllib as tomli  # type: ignore
except ImportError:
    # Python < 3.11 nécessite tomli
    try:
        import tomli
    except ImportError:
        raise ImportError(
            "tomli is required for Python < 3.11. Install it with: pip install tomli"
        )

from .config import (
    AnimationConfig,
    DialogueBlockConfig,
    DialogueExchangeConfig,
    NPCConfig,
    NPCsConfig,
    PlayerAnimationConfig,
)
from ..rendering.config import compute_design_scale, get_render_size


class NPCLoader:
    """Chargeur de fichiers de configuration de PNJ."""

    def __init__(self, assets_dir: Path) -> None:
        """Initialise le chargeur de PNJ.

        Args:
            assets_dir: Répertoire de base pour les ressources
        """
        self.assets_dir = Path(assets_dir)

    def load_npcs(self, npcs_path: Path) -> NPCsConfig:
        """Charge un fichier de configuration de PNJ.

        Args:
            npcs_path: Chemin vers le fichier .pnj ou .toml

        Returns:
            Configuration des PNJ chargée

        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            ValueError: Si le format du fichier est invalide
        """
        npcs_path = Path(npcs_path)

        if not npcs_path.exists():
            raise FileNotFoundError(f"Fichier de PNJ introuvable: {npcs_path}")

        try:
            with open(npcs_path, "rb") as f:
                data = tomli.load(f)
        except Exception as e:
            raise ValueError(f"Erreur lors du parsing du fichier TOML: {e}") from e

        # Valider et extraire la configuration des PNJ
        if "npcs" not in data:
            raise ValueError("Section [npcs] manquante dans le fichier de configuration")

        npcs_data = data["npcs"]
        if not isinstance(npcs_data, list):
            raise ValueError("Section [npcs] doit être une liste")

        # Calculer les facteurs de conversion du repère de conception (1920x1080) vers la surface de rendu interne
        render_width, render_height = get_render_size()
        scale_x, scale_y = compute_design_scale((render_width, render_height))

        npcs: list[NPCConfig] = []

        for npc_data in npcs_data:
            if not isinstance(npc_data, dict):
                raise ValueError("Chaque élément de [npcs] doit être un dictionnaire")

            # Champs obligatoires
            required_fields = ["id", "name", "x", "sprite_sheet_path", "sprite_width", "sprite_height"]
            for field in required_fields:
                if field not in npc_data:
                    raise ValueError(f"Champ '{field}' manquant dans la configuration d'un PNJ")

            npc_id = str(npc_data["id"])
            name = str(npc_data["name"])
            # Convertir la position x du repère de conception (1920x1080) vers la surface de rendu interne
            x = float(npc_data["x"]) * scale_x
            # Charger y optionnel (convertir du repère de conception vers la surface de rendu interne si défini)
            y_raw = npc_data.get("y")
            y: Optional[float] = None
            if y_raw is not None:
                y = float(y_raw) * scale_y
            sprite_sheet_path = str(npc_data["sprite_sheet_path"])
            sprite_width = int(npc_data["sprite_width"])
            sprite_height = int(npc_data["sprite_height"])

            # Valider que l'ID n'est pas vide
            if not npc_id:
                raise ValueError(f"L'ID du PNJ ne peut pas être vide pour le PNJ '{name}'")

            # Valider les valeurs
            if sprite_width <= 0:
                raise ValueError(f"sprite_width doit être positif pour le PNJ '{name}'")
            if sprite_height <= 0:
                raise ValueError(f"sprite_height doit être positif pour le PNJ '{name}'")
            
            # Charger le sprite sheet pour valider les dimensions
            sprite_path = Path(sprite_sheet_path)
            if not sprite_path.is_absolute():
                # Résoudre le chemin relatif depuis la racine du projet
                sprite_path = Path.cwd() / sprite_sheet_path
            
            if not sprite_path.exists():
                raise FileNotFoundError(f"Sprite sheet introuvable: {sprite_path} pour le PNJ '{name}'")
            
            try:
                # Charger temporairement l'image pour vérifier les dimensions
                sprite_sheet = Image.open(sprite_path)
                sheet_width, sheet_height = sprite_sheet.size
                
                # Valider que les dimensions sont compatibles
                if sheet_width % sprite_width != 0:
                    # Calculer les diviseurs de sheet_width pour suggérer les bonnes dimensions
                    # Limiter la recherche pour éviter les listes trop longues
                    max_divisor = min(sheet_width, 256)
                    valid_widths = [i for i in range(1, max_divisor + 1) if sheet_width % i == 0]
                    raise ValueError(
                        f"sprite_width {sprite_width} n'est pas compatible avec le sprite sheet du PNJ '{name}' "
                        f"(largeur {sheet_width}). La largeur doit être divisible exactement par sprite_width. "
                        f"Dimensions valides possibles: {valid_widths}"
                    )
                
                if sheet_height % sprite_height != 0:
                    # Calculer les diviseurs de sheet_height pour suggérer les bonnes dimensions
                    # Limiter la recherche pour éviter les listes trop longues
                    max_divisor = min(sheet_height, 256)
                    valid_heights = [i for i in range(1, max_divisor + 1) if sheet_height % i == 0]
                    raise ValueError(
                        f"sprite_height {sprite_height} n'est pas compatible avec le sprite sheet du PNJ '{name}' "
                        f"(hauteur {sheet_height}). La hauteur doit être divisible exactement par sprite_height. "
                        f"Dimensions valides possibles: {valid_heights}"
                    )
            except Exception as e:
                if isinstance(e, (ValueError, FileNotFoundError)):
                    raise
                raise ValueError(f"Erreur lors de la vérification du sprite sheet du PNJ '{name}': {e}") from e

            # Champs optionnels
            direction_str = str(npc_data.get("direction", "right"))
            if direction_str not in ("left", "right"):
                raise ValueError(
                    f"direction doit être 'left' ou 'right' pour le PNJ '{name}', reçu: '{direction_str}'"
                )
            direction: Literal["left", "right"] = direction_str  # type: ignore
            sprite_scale = float(npc_data.get("sprite_scale", 2.0))
            font_path = npc_data.get("font_path")
            font_size = int(npc_data.get("font_size", 36))
            name_color = tuple(npc_data.get("name_color", [255, 255, 255]))
            name_outline_color = tuple(npc_data.get("name_outline_color", [0, 0, 0]))
            name_offset_y = float(npc_data.get("name_offset_y", -4.0))

            # Charger les animations
            animations: Dict[str, AnimationConfig] = {}
            if "animations" in npc_data:
                animations_data = npc_data["animations"]
                if not isinstance(animations_data, dict):
                    raise ValueError(f"Section 'animations' doit être un dictionnaire pour le PNJ '{name}'")

                for anim_name, anim_data in animations_data.items():
                    if not isinstance(anim_data, dict):
                        raise ValueError(
                            f"Configuration d'animation '{anim_name}' doit être un dictionnaire pour le PNJ '{name}'"
                        )

                    required_anim_fields = ["row", "num_frames", "animation_speed"]
                    for field in required_anim_fields:
                        if field not in anim_data:
                            raise ValueError(
                                f"Champ '{field}' manquant dans l'animation '{anim_name}' du PNJ '{name}'"
                            )

                    row = int(anim_data["row"])
                    num_frames = int(anim_data["num_frames"])
                    animation_speed = float(anim_data["animation_speed"])
                    loop = bool(anim_data.get("loop", True))

                    # Valider les valeurs
                    if row < 0:
                        raise ValueError(f"row doit être >= 0 pour l'animation '{anim_name}' du PNJ '{name}'")
                    if num_frames <= 0:
                        raise ValueError(
                            f"num_frames doit être positif pour l'animation '{anim_name}' du PNJ '{name}'"
                        )
                    if animation_speed < 0:
                        raise ValueError(
                            f"animation_speed doit être >= 0 pour l'animation '{anim_name}' du PNJ '{name}'"
                        )

                    animations[anim_name] = AnimationConfig(
                        row=row, num_frames=num_frames, animation_speed=animation_speed, loop=loop
                    )

            # Charger les blocs de dialogue
            dialogue_blocks: List[DialogueBlockConfig] = []
            if "dialogue_blocks" in npc_data:
                dialogue_blocks_data = npc_data["dialogue_blocks"]
                if not isinstance(dialogue_blocks_data, list):
                    raise ValueError(
                        f"Section 'dialogue_blocks' doit être une liste pour le PNJ '{name}'"
                    )

                for block_data in dialogue_blocks_data:
                    if not isinstance(block_data, dict):
                        raise ValueError(
                            f"Chaque élément de 'dialogue_blocks' doit être un dictionnaire pour le PNJ '{name}'"
                        )

                    # Champs obligatoires du bloc
                    required_block_fields = ["position_min", "position_max", "exchanges"]
                    for field in required_block_fields:
                        if field not in block_data:
                            raise ValueError(
                                f"Champ '{field}' manquant dans un bloc de dialogue du PNJ '{name}'"
                            )

                    # Convertir les positions du repère de conception (1920x1080) vers la surface de rendu interne
                    position_min = float(block_data["position_min"]) * scale_x
                    position_max = float(block_data["position_max"]) * scale_x
                    exchanges_data = block_data["exchanges"]

                    # Valider les valeurs du bloc
                    if position_min < 0:
                        raise ValueError(
                            f"position_min doit être >= 0 pour un bloc de dialogue du PNJ '{name}'"
                        )
                    if position_max < position_min:
                        raise ValueError(
                            f"position_max doit être >= position_min pour un bloc de dialogue du PNJ '{name}'"
                        )

                    if not isinstance(exchanges_data, list):
                        raise ValueError(
                            f"Section 'exchanges' doit être une liste pour un bloc de dialogue du PNJ '{name}'"
                        )
                    if len(exchanges_data) == 0:
                        raise ValueError(
                            f"Un bloc de dialogue doit contenir au moins un échange pour le PNJ '{name}'"
                        )

                    # Champs optionnels du bloc
                    block_font_size = block_data.get("font_size")
                    if block_font_size is not None:
                        block_font_size = int(block_font_size)
                        if block_font_size <= 0:
                            raise ValueError(
                                f"font_size doit être positif pour un bloc de dialogue du PNJ '{name}'"
                            )
                    else:
                        block_font_size = 32  # Valeur par défaut

                    block_text_speed = block_data.get("text_speed")
                    if block_text_speed is not None:
                        block_text_speed = float(block_text_speed)
                        if block_text_speed <= 0:
                            raise ValueError(
                                f"text_speed doit être positif pour un bloc de dialogue du PNJ '{name}'"
                            )
                    else:
                        block_text_speed = 30.0  # Valeur par défaut

                    # Charger dialogue_type (optionnel, défaut: "normal")
                    dialogue_type_str = block_data.get("dialogue_type", "normal")
                    if dialogue_type_str not in ("normal", "quête", "discution", "ecoute", "regarder", "enseigner", "reflexion"):
                        raise ValueError(
                            f"dialogue_type doit être 'normal', 'quête', 'discution', 'ecoute', 'regarder', 'enseigner' ou 'reflexion' pour un bloc de dialogue du PNJ '{name}', reçu: '{dialogue_type_str}'"
                        )
                    dialogue_type: Literal["normal", "quête", "discution", "ecoute", "regarder", "enseigner", "reflexion"] = dialogue_type_str  # type: ignore

                    # Charger les échanges du bloc
                    exchanges: List[DialogueExchangeConfig] = []
                    for exchange_data in exchanges_data:
                        if not isinstance(exchange_data, dict):
                            raise ValueError(
                                f"Chaque élément de 'exchanges' doit être un dictionnaire pour le PNJ '{name}'"
                            )

                        # Champs obligatoires de l'échange
                        required_exchange_fields = ["speaker", "text"]
                        for field in required_exchange_fields:
                            if field not in exchange_data:
                                raise ValueError(
                                    f"Champ '{field}' manquant dans un échange du PNJ '{name}'"
                                )

                        speaker_str = str(exchange_data["speaker"])
                        if speaker_str not in ("npc", "player"):
                            raise ValueError(
                                f"speaker doit être 'npc' ou 'player' pour un échange du PNJ '{name}', reçu: '{speaker_str}'"
                            )
                        speaker: Literal["npc", "player"] = speaker_str  # type: ignore

                        text = str(exchange_data["text"])

                        # Charger image_path (optionnel)
                        image_path = exchange_data.get("image_path")
                        if image_path is not None:
                            image_path = str(image_path)

                        # Valider que le texte ou l'image est présent
                        if not text and not image_path:
                            raise ValueError(
                                f"Un échange doit avoir au moins du texte ou une image (image_path) pour le PNJ '{name}'"
                            )

                        # Utiliser les valeurs du bloc par défaut, mais permettre la surcharge
                        exchange_font_size = exchange_data.get("font_size")
                        if exchange_font_size is not None:
                            exchange_font_size = int(exchange_font_size)
                            if exchange_font_size <= 0:
                                raise ValueError(
                                    f"font_size doit être positif pour un échange du PNJ '{name}'"
                                )
                        else:
                            exchange_font_size = block_font_size

                        exchange_text_speed = exchange_data.get("text_speed")
                        if exchange_text_speed is not None:
                            exchange_text_speed = float(exchange_text_speed)
                            if exchange_text_speed <= 0:
                                raise ValueError(
                                    f"text_speed doit être positif pour un échange du PNJ '{name}'"
                                )
                        else:
                            exchange_text_speed = block_text_speed

                        # Charger trigger_events (optionnel) pour cet échange
                        trigger_events = exchange_data.get("trigger_events")
                        if trigger_events is not None:
                            if not isinstance(trigger_events, list):
                                raise ValueError(
                                    f"trigger_events doit être une liste pour un échange du PNJ '{name}'"
                                )
                            # Valider que tous les éléments sont des chaînes
                            trigger_events = [str(event_id) for event_id in trigger_events]
                        else:
                            trigger_events = None

                        # Charger add_items (optionnel) pour cet échange
                        add_items = exchange_data.get("add_items")
                        if add_items is not None:
                            if not isinstance(add_items, dict):
                                raise ValueError(
                                    f"add_items doit être un dictionnaire pour un échange du PNJ '{name}'"
                                )
                            # Convertir en Dict[str, int]
                            add_items_dict: Dict[str, int] = {}
                            for item_id, quantity in add_items.items():
                                item_id_str = str(item_id)
                                quantity_int = int(quantity)
                                if quantity_int <= 0:
                                    raise ValueError(
                                        f"La quantité pour '{item_id_str}' dans add_items doit être > 0 pour un échange du PNJ '{name}'"
                                    )
                                add_items_dict[item_id_str] = quantity_int
                        else:
                            add_items_dict = None

                        # Charger remove_items (optionnel) pour cet échange
                        remove_items = exchange_data.get("remove_items")
                        if remove_items is not None:
                            if not isinstance(remove_items, dict):
                                raise ValueError(
                                    f"remove_items doit être un dictionnaire pour un échange du PNJ '{name}'"
                                )
                            # Convertir en Dict[str, int]
                            remove_items_dict: Dict[str, int] = {}
                            for item_id, quantity in remove_items.items():
                                item_id_str = str(item_id)
                                quantity_int = int(quantity)
                                if quantity_int <= 0:
                                    raise ValueError(
                                        f"La quantité pour '{item_id_str}' dans remove_items doit être > 0 pour un échange du PNJ '{name}'"
                                    )
                                remove_items_dict[item_id_str] = quantity_int
                        else:
                            remove_items_dict = None

                        # Charger player_animation (optionnel) pour cet échange
                        player_animation = None
                        if "player_animation" in exchange_data:
                            anim_data = exchange_data["player_animation"]
                            if not isinstance(anim_data, dict):
                                raise ValueError(
                                    f"player_animation doit être un dictionnaire pour un échange du PNJ '{name}'"
                                )
                            
                            required_anim_fields = ["sprite_sheet_path", "row", "num_frames", "animation_speed"]
                            for field in required_anim_fields:
                                if field not in anim_data:
                                    raise ValueError(
                                        f"Champ '{field}' manquant dans player_animation pour un échange du PNJ '{name}'"
                                    )
                            
                            sprite_sheet_path_anim = str(anim_data["sprite_sheet_path"])
                            row_anim = int(anim_data["row"])
                            num_frames_anim = int(anim_data["num_frames"])
                            animation_speed_anim = float(anim_data["animation_speed"])
                            animation_type_str = str(anim_data.get("animation_type", "simple"))
                            
                            # Valider animation_type
                            if animation_type_str not in ("simple", "loop", "pingpong"):
                                raise ValueError(
                                    f"animation_type doit être 'simple', 'loop' ou 'pingpong' pour player_animation d'un échange du PNJ '{name}', reçu: '{animation_type_str}'"
                                )
                            animation_type: Literal["simple", "loop", "pingpong"] = animation_type_str  # type: ignore
                            
                            # Charger start_sprite et offset_y (optionnels avec valeurs par défaut)
                            start_sprite_anim = int(anim_data.get("start_sprite", 0))
                            offset_y_anim = float(anim_data.get("offset_y", 0.0))
                            set_x_position_raw = anim_data.get("set_x_position")
                            set_x_position_anim: Optional[float] = None
                            if set_x_position_raw is not None:
                                try:
                                    set_x_position_anim = float(set_x_position_raw)
                                except (TypeError, ValueError) as exc:
                                    raise ValueError(
                                        f"set_x_position doit être un nombre (repère de conception 1920x1080) pour player_animation d'un échange du PNJ '{name}'"
                                    ) from exc
                            
                            # Valider les valeurs
                            if row_anim < 0:
                                raise ValueError(
                                    f"row doit être >= 0 pour player_animation d'un échange du PNJ '{name}'"
                                )
                            if num_frames_anim <= 0:
                                raise ValueError(
                                    f"num_frames doit être positif pour player_animation d'un échange du PNJ '{name}'"
                                )
                            if animation_speed_anim <= 0:
                                raise ValueError(
                                    f"animation_speed doit être > 0 pour player_animation d'un échange du PNJ '{name}'"
                                )
                            if start_sprite_anim < 0:
                                raise ValueError(
                                    f"start_sprite doit être >= 0 pour player_animation d'un échange du PNJ '{name}'"
                                )
                            
                            player_animation = PlayerAnimationConfig(
                                sprite_sheet_path=sprite_sheet_path_anim,
                                row=row_anim,
                                num_frames=num_frames_anim,
                                animation_speed=animation_speed_anim,
                                animation_type=animation_type,
                                start_sprite=start_sprite_anim,
                                offset_y=offset_y_anim,
                                set_x_position=set_x_position_anim,
                            )

                        exchanges.append(
                            DialogueExchangeConfig(
                                speaker=speaker,
                                text=text,
                                font_size=exchange_font_size,
                                text_speed=exchange_text_speed,
                                image_path=image_path,
                                trigger_events=trigger_events,
                                add_items=add_items_dict,
                                remove_items=remove_items_dict,
                                player_animation=player_animation,
                            )
                        )

                    dialogue_blocks.append(
                        DialogueBlockConfig(
                            position_min=position_min,
                            position_max=position_max,
                            exchanges=exchanges,
                            dialogue_type=dialogue_type,
                            font_size=block_font_size,
                            text_speed=block_text_speed,
                        )
                    )

            # Vérifier l'unicité de l'ID
            for existing_npc in npcs:
                if existing_npc.id == npc_id:
                    raise ValueError(
                        f"ID dupliqué '{npc_id}' trouvé pour le PNJ '{name}'. "
                        "Chaque PNJ doit avoir un ID unique au sein d'un niveau."
                    )

            npc_config = NPCConfig(
                id=npc_id,
                name=name,
                x=x,
                y=y,
                direction=direction,
                sprite_sheet_path=sprite_sheet_path,
                sprite_width=sprite_width,
                sprite_height=sprite_height,
                sprite_scale=sprite_scale,
                animations=animations if animations else None,
                font_path=font_path,
                font_size=font_size,
                name_color=name_color,  # type: ignore
                name_outline_color=name_outline_color,  # type: ignore
                name_offset_y=name_offset_y,
                dialogue_blocks=dialogue_blocks if dialogue_blocks else None,
            )

            npcs.append(npc_config)

        return NPCsConfig(npcs=npcs)

