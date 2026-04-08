# Bonnes Pratiques de Développement Python - Jeu Pygame

## Table des matières
1. [Structure du projet](#structure-du-projet)
2. [Gestion des dépendances avec uv](#gestion-des-dépendances-avec-uv)
3. [Organisation du code](#organisation-du-code)
4. [Standards Python](#standards-python)
5. [Bonnes pratiques Pygame](#bonnes-pratiques-pygame)
6. [Gestion des ressources](#gestion-des-ressources)
7. [Architecture du jeu](#architecture-du-jeu)
8. [Documentation](#documentation)

---

## Structure du projet

```
moteur_jeu_presentation/
├── src/
│   └── moteur_jeu_presentation/          # Package principal
│       ├── __init__.py
│       ├── main.py          # Point d'entrée
│       ├── game/
│       │   ├── __init__.py
│       │   ├── game.py      # Classe principale du jeu
│       │   └── states/      # États du jeu (menu, gameplay, pause, etc.)
│       ├── entities/        # Entités du jeu (joueur, ennemis, etc.)
│       ├── utils/           # Utilitaires (helpers, constants, etc.)
│       └── assets/          # Références aux ressources
├── assets/                  # Ressources (images, sons, fonts)
│   ├── images/
│   ├── sounds/
│   └── fonts/
├── docs/                    # Documentation
├── .gitignore
├── pyproject.toml           # Configuration uv et projet
├── README.md
└── bonne pratique.md        # Ce fichier
```

---

## Gestion des dépendances avec uv

### Installation de uv

```bash
# Installation de uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Configuration du projet

**pyproject.toml** :
```toml
[project]
name = "moteur_jeu_presentation"
version = "0.1.0"
description = "Jeu développé avec pygame"
requires-python = ">=3.10"
dependencies = [
    "pygame>=2.5.0",
]

[project.optional-dependencies]
dev = [
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.black]
line-length = 100
target-version = ['py310']

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
```

### Commandes uv essentielles

```bash
# Créer un environnement virtuel et installer les dépendances
uv venv
source .venv/bin/activate  # Sur macOS/Linux
# ou
.venv\Scripts\activate  # Sur Windows

# Installer les dépendances
uv pip install -e .

# Installer les dépendances de développement
uv pip install -e ".[dev]"

# Ajouter une nouvelle dépendance
uv pip install pygame

# Synchroniser les dépendances depuis pyproject.toml
uv pip sync pyproject.toml

# Mettre à jour les dépendances
uv pip install --upgrade-package pygame
```

---

## Organisation du code

### Principes généraux

1. **Séparation des responsabilités** : Chaque module/classe a une responsabilité unique
2. **DRY (Don't Repeat Yourself)** : Éviter la duplication de code
3. **KISS (Keep It Simple, Stupid)** : Privilégier la simplicité
4. **Composition plutôt qu'héritage** : Préférer la composition pour la flexibilité

### Structure des modules

```python
# Exemple de structure de module
"""
Module de gestion des entités du jeu.

Ce module contient les classes de base pour toutes les entités
interactives du jeu.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.game import Game

import pygame


class Entity:
    """Classe de base pour toutes les entités du jeu."""
    
    def __init__(self, x: float, y: float, game: Game) -> None:
        self.x = x
        self.y = y
        self.game = game
        
    def update(self, dt: float) -> None:
        """Met à jour l'entité."""
        pass
        
    def draw(self, surface: pygame.Surface) -> None:
        """Dessine l'entité sur la surface."""
        pass
```

---

## Standards Python

### PEP 8 - Style Guide

1. **Nommage** :
   - Classes : `PascalCase` (ex: `GameState`, `Player`)
   - Fonctions/variables : `snake_case` (ex: `update_game`, `player_speed`)
   - Constantes : `UPPER_SNAKE_CASE` (ex: `SCREEN_WIDTH`, `FPS`)
   - Privé : préfixe `_` (ex: `_internal_method`)

2. **Longueur des lignes** : Maximum 100 caractères

3. **Imports** :
   ```python
   # Ordre des imports :
   # 1. Bibliothèque standard
   import os
   import sys
   from typing import Optional
   
   # 2. Bibliothèques tierces
   import pygame
   
   # 3. Imports locaux
   from game.game import Game
   from entities.player import Player
   ```

### Type Hints

**Toujours utiliser les type hints** pour améliorer la lisibilité et la maintenabilité :

```python
from typing import Optional, List, Dict, Tuple

def calculate_damage(
    base_damage: int,
    multiplier: float,
    critical: bool = False
) -> int:
    """Calcule les dégâts infligés."""
    damage = int(base_damage * multiplier)
    return damage * 2 if critical else damage

def get_entities_in_range(
    position: Tuple[float, float],
    radius: float
) -> List[Entity]:
    """Retourne toutes les entités dans un rayon donné."""
    # ...
    return []
```

### Docstrings

Utiliser les docstrings Google style :

```python
def move_player(self, dx: float, dy: float) -> None:
    """Déplace le joueur d'un offset donné.
    
    Args:
        dx: Déplacement horizontal (pixels)
        dy: Déplacement vertical (pixels)
        
    Raises:
        ValueError: Si le déplacement sort des limites du jeu.
    """
    # ...
```

### Programmation objet

ne pas hesiter a reformater les classes afin d'introduire de la hierarchie de classe quand c'est necessaire

---

## Bonnes pratiques Pygame

### optimisation graphique

ne pas hésiter a utiliser des mécaniques de cache pour optimiser le rendu

### Initialisation

```python
import pygame

# Initialiser pygame
pygame.init()

# Configuration de la fenêtre
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Créer la fenêtre
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("presentation")
clock = pygame.time.Clock()
```

### Boucle de jeu principale

```python
def main() -> None:
    """Point d'entrée principal du jeu."""
    running = True
    game = Game()
    
    while running:
        # Calculer le delta time
        dt = clock.tick(FPS) / 1000.0  # Convertir en secondes
        
        # Gérer les événements
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            game.handle_event(event)
        
        # Mettre à jour le jeu
        game.update(dt)
        
        # Dessiner
        screen.fill((0, 0, 0))  # Effacer l'écran
        game.draw(screen)
        pygame.display.flip()
    
    pygame.quit()
```

### Gestion des événements

```python
class GameState:
    """État de base du jeu."""
    
    def handle_event(self, event: pygame.event.Event) -> None:
        """Gère un événement pygame."""
        if event.type == pygame.KEYDOWN:
            self.handle_keydown(event.key)
        elif event.type == pygame.KEYUP:
            self.handle_keyup(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.handle_mouse_down(event.pos, event.button)
    
    def handle_keydown(self, key: int) -> None:
        """Gère l'appui d'une touche."""
        pass
```

### Delta Time

**Toujours utiliser le delta time** pour des mouvements indépendants de la fréquence d'images :

```python
class Player:
    def __init__(self) -> None:
        self.speed = 200  # pixels par seconde
        self.x = 0.0
        self.y = 0.0
    
    def update(self, dt: float) -> None:
        """Met à jour la position du joueur."""
        keys = pygame.key.get_pressed()
        
        if keys[pygame.K_LEFT]:
            self.x -= self.speed * dt
        if keys[pygame.K_RIGHT]:
            self.x += self.speed * dt
        if keys[pygame.K_UP]:
            self.y -= self.speed * dt
        if keys[pygame.K_DOWN]:
            self.y += self.speed * dt
```

### Sprites et groupes

Utiliser les groupes de sprites pygame pour une gestion efficace :

```python
import pygame.sprite

class Player(pygame.sprite.Sprite):
    def __init__(self, x: float, y: float) -> None:
        super().__init__()
        self.image = pygame.Surface((32, 32))
        self.image.fill((255, 0, 0))
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
    
    def update(self, dt: float) -> None:
        """Met à jour le sprite."""
        # Logique de mise à jour
        pass

# Utilisation
all_sprites = pygame.sprite.Group()
player = Player(100, 100)
all_sprites.add(player)

# Dans la boucle de jeu
all_sprites.update(dt)
all_sprites.draw(screen)
```

---

## Gestion des ressources

### Chargement des ressources

Créer un gestionnaire de ressources centralisé :

```python
from pathlib import Path
from typing import Dict
import pygame

class AssetManager:
    """Gestionnaire centralisé des ressources du jeu."""
    
    def __init__(self, assets_dir: Path) -> None:
        self.assets_dir = assets_dir
        self._images: Dict[str, pygame.Surface] = {}
        self._sounds: Dict[str, pygame.mixer.Sound] = {}
        self._fonts: Dict[str, pygame.font.Font] = {}
    
    def load_image(self, name: str, scale: float = 1.0) -> pygame.Surface:
        """Charge une image avec mise en cache."""
        if name not in self._images:
            path = self.assets_dir / "images" / name
            image = pygame.image.load(str(path)).convert_alpha()
            if scale != 1.0:
                size = (int(image.get_width() * scale), 
                       int(image.get_height() * scale))
                image = pygame.transform.scale(image, size)
            self._images[name] = image
        return self._images[name]
    
    def load_sound(self, name: str) -> pygame.mixer.Sound:
        """Charge un son avec mise en cache."""
        if name not in self._sounds:
            path = self.assets_dir / "sounds" / name
            self._sounds[name] = pygame.mixer.Sound(str(path))
        return self._sounds[name]
    
    def load_font(self, name: str, size: int) -> pygame.font.Font:
        """Charge une police avec mise en cache."""
        key = f"{name}_{size}"
        if key not in self._fonts:
            path = self.assets_dir / "fonts" / name
            self._fonts[key] = pygame.font.Font(str(path), size)
        return self._fonts[key]
```

### Utilisation

```python
# Dans le code du jeu
ASSETS_DIR = Path(__file__).parent.parent / "assets"
asset_manager = AssetManager(ASSETS_DIR)

# Charger une ressource
player_image = asset_manager.load_image("player.png", scale=2.0)
jump_sound = asset_manager.load_sound("jump.wav")
font = asset_manager.load_font("arial.ttf", 24)
```

---

## Architecture du jeu

### Pattern State Machine

Utiliser une machine à états pour gérer les différents écrans/états du jeu :

```python
from abc import ABC, abstractmethod
from typing import Optional
import pygame

class GameState(ABC):
    """Classe de base pour les états du jeu."""
    
    def __init__(self, game: Game) -> None:
        self.game = game
    
    @abstractmethod
    def handle_event(self, event: pygame.event.Event) -> None:
        """Gère un événement."""
        pass
    
    @abstractmethod
    def update(self, dt: float) -> None:
        """Met à jour l'état."""
        pass
    
    @abstractmethod
    def draw(self, surface: pygame.Surface) -> None:
        """Dessine l'état."""
        pass

class Game:
    """Classe principale du jeu."""
    
    def __init__(self) -> None:
        self.running = True
        self.state: Optional[GameState] = None
    
    def change_state(self, new_state: GameState) -> None:
        """Change l'état actuel du jeu."""
        self.state = new_state
    
    def handle_event(self, event: pygame.event.Event) -> None:
        """Transmet l'événement à l'état actuel."""
        if self.state:
            self.state.handle_event(event)
    
    def update(self, dt: float) -> None:
        """Met à jour le jeu."""
        if self.state:
            self.state.update(dt)
    
    def draw(self, surface: pygame.Surface) -> None:
        """Dessine le jeu."""
        if self.state:
            self.state.draw(surface)
```

### Exemple d'état

```python
class MenuState(GameState):
    """État du menu principal."""
    
    def __init__(self, game: Game) -> None:
        super().__init__(game)
        self.selected_option = 0
        self.options = ["Jouer", "Options", "Quitter"]
    
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_option = (self.selected_option - 1) % len(self.options)
            elif event.key == pygame.K_DOWN:
                self.selected_option = (self.selected_option + 1) % len(self.options)
            elif event.key == pygame.K_RETURN:
                self._select_option()
    
    def _select_option(self) -> None:
        if self.selected_option == 0:
            self.game.change_state(PlayState(self.game))
        elif self.selected_option == 2:
            self.game.running = False
    
    def update(self, dt: float) -> None:
        pass
    
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((30, 30, 30))
        # Dessiner le menu
        # ...
```

---

## Documentation

### README.md

Le README doit contenir :
- Description du projet
- Prérequis et installation
- Instructions de lancement
- Structure du projet
- Contribution

### Commentaires dans le code

- **Expliquer le "pourquoi"**, pas le "comment"
- Utiliser des docstrings pour toutes les fonctions/classes publiques
- Commenter les algorithmes complexes
- Éviter les commentaires redondants

```python
# ❌ Mauvais
x = x + 1  # Incrémente x de 1

# ✅ Bon
# Ajuster la position pour compenser le décalage de la caméra
x = x + camera_offset
```

---

## Checklist de développement

### Avant de commiter

- [ ] Code formaté avec `black`
- [ ] Linting passé avec `ruff`
- [ ] Type checking passé avec `mypy`
- [ ] Documentation à jour
- [ ] Pas de code commenté/debug
- [ ] Variables et fonctions bien nommées
- [ ] Gestion d'erreurs appropriée

### Commandes utiles

```bash
# Formater le code
black src/

# Linter
ruff check src/

# Type checking
mypy src/

# Tout en une fois
black src/ && ruff check src/ && mypy src/
```

---

## Ressources supplémentaires

- [PEP 8 - Style Guide](https://pep8.org/)
- [Pygame Documentation](https://www.pygame.org/docs/)
- [uv Documentation](https://github.com/astral-sh/uv)
- [Real Python - Game Development](https://realpython.com/pygame-a-primer/)

---

**Dernière mise à jour** : 2024

