# 14 - Moteur de particules

## Contexte

Cette spécification définit un moteur de particules réutilisable pour créer des effets visuels dynamiques dans le jeu. Le moteur de particules est un asset indépendant qui peut être utilisé par différents systèmes (inventaire, combat, environnement, etc.) pour déclencher des effets de particules configurables.

**Note d'implémentation** : Le système de particules global (`ParticleSystem`, `ParticleEffect`, `ParticleEffectConfig`) est maintenant implémenté et utilisé par le système d'inventaire et l'animation de confetti lors du passage de niveau. Les fonctions utilitaires (`create_confetti_config()`, `create_flame_explosion_config()`, etc.) sont également disponibles.

## Objectifs

- Créer un moteur de particules réutilisable et indépendant
- Permettre la création d'effets de particules configurables (explosion, pluie, feu, etc.)
- Optimiser les performances avec un système de cache
- Gérer le cycle de vie des particules (création, mise à jour, suppression)
- Permettre l'extraction de couleur depuis des sprites pour les particules
- Fournir une API simple pour déclencher des effets depuis n'importe quel système

## Architecture

### Structure générale

Le moteur de particules se compose de :
- **Classe `Particle`** : Représente une particule individuelle avec ses propriétés (position, vitesse, couleur, durée de vie)
- **Classe `ParticleEffect`** : Représente un effet de particules (groupe de particules avec configuration)
- **Classe `ParticleSystem`** : Gestionnaire principal qui met à jour et rend tous les effets actifs
- **Utilitaires** : Fonctions pour extraire les couleurs depuis des sprites, créer des configurations d'effets prédéfinis

### Types d'effets supportés

Le moteur doit supporter différents types d'effets configurables :
- **Explosion** : Particules qui se dispersent dans toutes les directions depuis un point, avec friction (ralentissement progressif), gravité (chute progressive), rétrécissement progressif, et variations de taille et couleur pour un effet dynamique et spectaculaire
- **Explosion de flamme** : Variante d'explosion avec une palette de couleurs chaudes (rouge, orange, jaune) et une variation importante de couleur pour créer un effet de flamme colorée et dynamique, indépendamment de la couleur de l'objet source
- **Confetti** : Effet festif avec des particules colorées qui se dispersent dans toutes les directions, utilisées pour célébrer des événements comme le passage de niveau (voir section "Animation de confetti pour le passage de niveau")
- **Pluie/Chute** : Particules qui tombent verticalement
- **Fumée** : Particules qui montent avec dispersion
- **Étincelles** : Particules rapides et courtes
- **Personnalisé** : Configuration libre pour des effets spécifiques

## Spécifications techniques

### Structure des données

#### Classe `Particle`

```python
@dataclass
class Particle:
    """Représente une particule individuelle."""
    x: float  # Position horizontale (en pixels, coordonnées monde)
    y: float  # Position verticale (en pixels, coordonnées monde)
    velocity_x: float  # Vitesse horizontale (en pixels/seconde)
    velocity_y: float  # Vitesse verticale (en pixels/seconde)
    color: Tuple[int, int, int]  # Couleur RGB de la particule
    lifetime: float  # Durée de vie restante (en secondes)
    max_lifetime: float  # Durée de vie maximale (en secondes)
    size: int  # Taille de la particule (diamètre en pixels)
    
    def update(self, dt: float) -> None:
        """Met à jour la position et la durée de vie de la particule.
        
        Args:
            dt: Delta time en secondes
        """
        self.x += self.velocity_x * dt
        self.y += self.velocity_y * dt
        self.lifetime -= dt
    
    def is_alive(self) -> bool:
        """Vérifie si la particule est encore vivante.
        
        Returns:
            True si la particule est encore vivante, False sinon
        """
        return self.lifetime > 0.0
    
    def get_opacity(self) -> int:
        """Calcule l'opacité de la particule basée sur sa durée de vie.
        
        Returns:
            Opacité de 0 à 255
        """
        if self.max_lifetime <= 0:
            return 255
        progress = self.lifetime / self.max_lifetime
        return int(255 * progress)
    
    def get_size(self, size_shrink: bool = False) -> int:
        """Calcule la taille actuelle de la particule.
        
        Si size_shrink est True, la taille diminue progressivement de la taille initiale à 0.
        
        Args:
            size_shrink: Si True, la taille diminue avec la durée de vie
        
        Returns:
            Taille actuelle de la particule en pixels
        """
        if not size_shrink or self.max_lifetime <= 0:
            return self.size
        progress = self.lifetime / self.max_lifetime
        return int(self.size * progress)
```

#### Classe `ParticleEffectConfig`

```python
@dataclass
class ParticleEffectConfig:
    """Configuration pour créer un effet de particules."""
    count: int  # Nombre de particules à créer
    speed: float  # Vitesse de base des particules (pixels/seconde)
    speed_variation: float = 0.3  # Variation de vitesse (0.0 à 1.0, ex: 0.3 = ±30%)
    lifetime: float  # Durée de vie des particules (secondes)
    lifetime_variation: float = 0.0  # Variation de durée de vie (0.0 à 1.0)
    size: int  # Taille de base des particules (diamètre en pixels)
    size_variation: float = 0.0  # Variation de taille (0.0 à 1.0)
    color: Tuple[int, int, int]  # Couleur de base des particules (RGB)
    color_variation: float = 0.0  # Variation de couleur (0.0 à 1.0, ajuste la saturation)
    direction_type: Literal["explosion", "rain", "smoke", "sparks", "custom"] = "explosion"
    direction_angle: float = 0.0  # Angle de direction pour "custom" (en radians, 0 = droite)
    direction_spread: float = 2.0 * math.pi  # Étalement de direction (en radians, 2π = toutes directions)
    gravity: float = 0.0  # Force de gravité appliquée (pixels/seconde², positif = vers le bas)
    friction: float = 0.0  # Coefficient de friction/décélération (0.0 à 1.0, ex: 0.95 = ralentit de 5% par seconde). Si > 0, les particules ralentissent progressivement
    size_shrink: bool = False  # Si True, les particules rétrécissent progressivement pendant leur durée de vie (de leur taille initiale à 0)
    fade_out: bool = True  # Si True, les particules disparaissent progressivement
```

#### Classe `ParticleEffect`

```python
class ParticleEffect:
    """Représente un effet de particules actif."""
    
    def __init__(
        self,
        x: float,
        y: float,
        config: ParticleEffectConfig,
        effect_id: Optional[str] = None,
    ) -> None:
        """
        Args:
            x: Position horizontale de départ (coordonnées monde)
            y: Position verticale de départ (coordonnées monde)
            config: Configuration de l'effet
            effect_id: Identifiant optionnel pour l'effet (pour le suivi)
        """
        self.x = x
        self.y = y
        self.config = config
        self.effect_id = effect_id
        self.particles: List[Particle] = []
        self.is_active = True
        self._create_particles()
    
    def _create_particles(self) -> None:
        """Crée les particules selon la configuration."""
        import math
        import random
        
        for _ in range(self.config.count):
            # Calculer la direction selon le type
            if self.config.direction_type == "explosion":
                angle = random.uniform(0, 2 * math.pi)
            elif self.config.direction_type == "rain":
                angle = math.pi / 2  # Vers le bas
            elif self.config.direction_type == "smoke":
                angle = -math.pi / 2  # Vers le haut
            elif self.config.direction_type == "sparks":
                angle = random.uniform(-math.pi / 4, math.pi / 4)  # Vers le haut avec variation
            else:  # "custom"
                angle = self.config.direction_angle + random.uniform(
                    -self.config.direction_spread / 2,
                    self.config.direction_spread / 2
                )
            
            # Calculer la vitesse avec variation
            speed = self.config.speed * random.uniform(
                1.0 - self.config.speed_variation,
                1.0 + self.config.speed_variation
            )
            
            velocity_x = math.cos(angle) * speed
            velocity_y = math.sin(angle) * speed
            
            # Calculer la durée de vie avec variation
            lifetime = self.config.lifetime * random.uniform(
                1.0 - self.config.lifetime_variation,
                1.0 + self.config.lifetime_variation
            )
            
            # Calculer la taille avec variation
            size = int(self.config.size * random.uniform(
                1.0 - self.config.size_variation,
                1.0 + self.config.size_variation
            ))
            size = max(1, size)  # Taille minimale de 1 pixel
            
            # Calculer la couleur avec variation
            color = self._apply_color_variation(self.config.color, self.config.color_variation)
            
            particle = Particle(
                x=self.x,
                y=self.y,
                velocity_x=velocity_x,
                velocity_y=velocity_y,
                color=color,
                lifetime=lifetime,
                max_lifetime=lifetime,
                size=size
            )
            self.particles.append(particle)
    
    def _apply_color_variation(self, base_color: Tuple[int, int, int], variation: float) -> Tuple[int, int, int]:
        """Applique une variation de couleur.
        
        Args:
            base_color: Couleur de base (RGB)
            variation: Niveau de variation (0.0 à 1.0)
            
        Returns:
            Couleur avec variation appliquée
        """
        if variation <= 0.0:
            return base_color
        
        import random
        r, g, b = base_color
        variation_amount = int(255 * variation)
        
        r = max(0, min(255, r + random.randint(-variation_amount, variation_amount)))
        g = max(0, min(255, g + random.randint(-variation_amount, variation_amount)))
        b = max(0, min(255, b + random.randint(-variation_amount, variation_amount)))
        
        return (r, g, b)
    
    def update(self, dt: float, camera_x: float = 0.0, screen_width: int = 1920, screen_height: int = 1080, margin: int = 200) -> None:
        """Met à jour toutes les particules de l'effet.
        
        OPTIMISATION: Ne met à jour que les particules visibles ou proches de l'écran.
        Les particules hors écran voient uniquement leur durée de vie décrémentée
        (pas de calcul de position/physique) pour économiser les calculs.
        
        Args:
            dt: Delta time en secondes
            camera_x: Position horizontale de la caméra (pour le culling, optionnel)
            screen_width: Largeur de l'écran pour le culling (défaut: 1920)
            screen_height: Hauteur de l'écran pour le culling (défaut: 1080)
            margin: Marge en pixels pour le culling hors écran (défaut: 200)
        """
        for particle in list(self.particles):
            # OPTIMISATION: Vérifier si la particule est visible avant de la mettre à jour
            particle_x_screen = particle.x - camera_x
            
            # Si la particule est hors écran (avec marge), on ne la met pas à jour complètement
            if (particle_x_screen + particle.size < -margin or
                particle_x_screen > screen_width + margin or
                particle.y + particle.size < -margin or
                particle.y > screen_height + margin):
                # Particule hors écran : on met à jour uniquement la durée de vie pour qu'elle meure correctement
                particle.lifetime -= dt
                if not particle.is_alive():
                    self.particles.remove(particle)
                continue  # Skip les calculs de position, gravité, friction, etc.
            
            # Particule visible : mise à jour complète
            # Appliquer la gravité si configurée
            if self.config.gravity != 0.0:
                particle.velocity_y += self.config.gravity * dt
            
            # Appliquer la friction/décélération si configurée
            # La friction réduit la vitesse progressivement (ex: 0.95 = ralentit de 5% par seconde)
            if self.config.friction > 0.0:
                # Calculer le facteur de ralentissement basé sur le temps écoulé
                # friction = 0.95 signifie que la vitesse est multipliée par 0.95 chaque seconde
                # Pour un dt, on applique: velocity *= friction^dt
                friction_factor = self.config.friction ** dt
                particle.velocity_x *= friction_factor
                particle.velocity_y *= friction_factor
            
            # Mettre à jour la particule
            particle.update(dt)
            
            # Supprimer les particules mortes
            if not particle.is_alive():
                self.particles.remove(particle)
        
        # Désactiver l'effet si toutes les particules sont mortes
        if len(self.particles) == 0:
            self.is_active = False
    
    def has_particles(self) -> bool:
        """Vérifie si l'effet contient encore des particules vivantes.
        
        Returns:
            True si l'effet contient des particules, False sinon
        """
        return len(self.particles) > 0
```

#### Classe `ParticleSystem`

```python
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
    ) -> ParticleEffect:
        """Crée et ajoute un nouvel effet de particules.
        
        Args:
            x: Position horizontale de départ (coordonnées monde)
            y: Position verticale de départ (coordonnées monde)
            config: Configuration de l'effet
            effect_id: Identifiant optionnel pour l'effet
            
        Returns:
            L'effet créé
        """
        effect = ParticleEffect(x, y, config, effect_id)
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
                effect.update(dt, camera_x, screen_width, screen_height, margin)
            # Si l'effet est hors écran, on ne le met pas à jour pour économiser les calculs
            # Les particules continueront d'exister mais ne bougeront pas jusqu'à ce qu'elles reviennent à l'écran
            # ou que l'effet soit supprimé s'il n'a plus de particules
            
            if not effect.is_active:
                self.effects.remove(effect)
    
    def _is_effect_visible(self, effect: ParticleEffect, camera_x: float, screen_width: int, screen_height: int, margin: int) -> bool:
        """Vérifie si un effet est visible ou proche de l'écran.
        
        Args:
            effect: L'effet à vérifier
            camera_x: Position horizontale de la caméra
            screen_width: Largeur de l'écran
            screen_height: Hauteur de l'écran
            margin: Marge en pixels
            
        Returns:
            True si l'effet est visible ou proche de l'écran, False sinon
        """
        # Si l'effet n'a pas encore de particules mais est en train d'en générer, on le considère comme visible
        if len(effect.particles) == 0:
            # Vérifier si la position de l'effet est visible
            effect_x_screen = effect.x - camera_x
            effect_y = effect.y
            
            return not (effect_x_screen < -margin or 
                       effect_x_screen > screen_width + margin or
                       effect_y < -margin or 
                       effect_y > screen_height + margin)
        
        # Calculer les bornes de l'effet basées sur les positions des particules
        min_x = min(p.x for p in effect.particles)
        max_x = max(p.x for p in effect.particles)
        min_y = min(p.y for p in effect.particles)
        max_y = max(p.y for p in effect.particles)
        
        # Convertir en coordonnées écran
        min_x_screen = min_x - camera_x
        max_x_screen = max_x - camera_x
        
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
    ) -> List[Tuple[pygame.Surface, Tuple[int, int]]]:
        """Génère les commandes de dessin pour toutes les particules actives.

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
            for particle in effect.particles:
                # Calculer la taille actuelle de la particule (peut diminuer si size_shrink est activé)
                current_size = particle.get_size(effect.config.size_shrink)
                if current_size <= 0:
                    continue  # Ignorer les particules qui ont rétréci à 0

                # Calculer l'opacité si fade_out est activé
                if effect.config.fade_out:
                    opacity = particle.get_opacity()
                else:
                    opacity = 255

                # OPTIMISATION: Culling des particules hors écran
                # Calculer la position à l'écran
                particle_x = int(particle.x - camera_x)
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
                    # Créer une nouvelle surface si pas en cache
                    particle_surface = pygame.Surface((current_size, current_size), pygame.SRCALPHA)
                    color_with_alpha = (r, g, b, opacity)
                    pygame.draw.circle(
                        particle_surface,
                        color_with_alpha,
                        (current_size // 2, current_size // 2),
                        current_size // 2
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
```

### Utilitaires

#### Extraction de couleur depuis un sprite

```python
def extract_dominant_color(
    sprite: Optional[pygame.Surface],
    sample_count: int = 100,
    default_color: Tuple[int, int, int] = (255, 200, 0),
) -> Tuple[int, int, int]:
    """Extrait la couleur dominante d'un sprite.
    
    Args:
        sprite: Surface du sprite (peut être None)
        sample_count: Nombre de pixels à échantillonner (défaut: 100)
        default_color: Couleur par défaut si le sprite est None ou invalide
        
    Returns:
        Couleur RGB dominante, ou couleur par défaut
    """
    if sprite is None:
        return default_color
    
    import random
    
    width = sprite.get_width()
    height = sprite.get_height()
    
    if width <= 0 or height <= 0:
        return default_color
    
    # Échantillonner quelques pixels (pas tous pour la performance)
    sample_count = min(sample_count, width * height)
    r_sum, g_sum, b_sum, count = 0, 0, 0, 0
    
    for _ in range(sample_count):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        color = sprite.get_at((x, y))
        
        # Ignorer les pixels transparents
        if color[3] > 128:  # Alpha > 128
            r_sum += color[0]
            g_sum += color[1]
            b_sum += color[2]
            count += 1
    
    if count > 0:
        return (r_sum // count, g_sum // count, b_sum // count)
    else:
        return default_color
```

#### Configurations prédéfinies

```python
def create_explosion_config(
    count: int = 24,
    speed: float = 320.0,
    lifetime: float = 0.4,
    size: int = 16,
    color: Tuple[int, int, int] = (255, 200, 0),
) -> ParticleEffectConfig:
    """Crée une configuration d'effet d'explosion dynamique et spectaculaire.
    
    L'effet d'explosion est inspiré des explosions classiques dans les jeux vidéo :
    - Les particules se dispersent dans toutes les directions
    - Les particules ralentissent progressivement (friction)
    - Les particules tombent sous l'effet de la gravité
    - Les particules varient en taille et en couleur pour un effet plus riche
    - Les particules rétrécissent progressivement pendant leur durée de vie
    - Les particules disparaissent progressivement (fade-out)
    
    Args:
        count: Nombre de particules (défaut: 24)
        speed: Vitesse de base (pixels/seconde, défaut: 320.0)
        lifetime: Durée de vie (secondes, défaut: 0.4)
        size: Taille de base des particules (diamètre en pixels, défaut: 16)
        color: Couleur de base (RGB, défaut: (255, 200, 0) = jaune/orange)
        
    Returns:
        Configuration d'effet d'explosion avec friction, gravité et variations
    """
    return ParticleEffectConfig(
        count=count,
        speed=speed,
        speed_variation=0.4,  # Variation de vitesse augmentée (40%) pour plus de dynamisme
        lifetime=lifetime,
        lifetime_variation=0.2,  # Variation de durée de vie (20%) pour un effet plus naturel
        size=size,
        size_variation=0.5,  # Variation de taille importante (50%) pour des particules de tailles variées
        color=color,
        color_variation=0.3,  # Variation de couleur (30%) pour un effet plus riche et coloré
        direction_type="explosion",
        direction_spread=2.0 * math.pi,  # Toutes les directions (360 degrés)
        gravity=400.0,  # Gravité modérée pour faire tomber les particules progressivement
        friction=0.92,  # Friction de 8% par seconde (0.92) : les particules ralentissent progressivement
        size_shrink=True,  # Les particules rétrécissent progressivement pendant leur durée de vie
        fade_out=True,  # Les particules disparaissent progressivement
    )

def create_rain_config(
    count: int = 50,
    speed: float = 200.0,
    lifetime: float = 2.0,
    size: int = 4,
    color: Tuple[int, int, int] = (150, 150, 255),
) -> ParticleEffectConfig:
    """Crée une configuration d'effet de pluie.
    
    Args:
        count: Nombre de particules
        speed: Vitesse de chute (pixels/seconde)
        lifetime: Durée de vie (secondes)
        size: Taille des particules (diamètre en pixels)
        color: Couleur de base (RGB)
        
    Returns:
        Configuration d'effet de pluie
    """
    return ParticleEffectConfig(
        count=count,
        speed=speed,
        speed_variation=0.2,
        lifetime=lifetime,
        size=size,
        color=color,
        direction_type="rain",
        gravity=100.0,  # Accélération vers le bas
        fade_out=False,
    )

def create_smoke_config(
    count: int = 30,
    speed: float = 50.0,
    lifetime: float = 3.0,
    size: int = 8,
    color: Tuple[int, int, int] = (100, 100, 100),
) -> ParticleEffectConfig:
    """Crée une configuration d'effet de fumée.
    
    Args:
        count: Nombre de particules
        speed: Vitesse de montée (pixels/seconde)
        lifetime: Durée de vie (secondes)
        size: Taille de base des particules (diamètre en pixels)
        color: Couleur de base (RGB)
        
    Returns:
        Configuration d'effet de fumée
    """
    return ParticleEffectConfig(
        count=count,
        speed=speed,
        speed_variation=0.4,
        lifetime=lifetime,
        lifetime_variation=0.3,
        size=size,
        size_variation=0.5,  # Les particules de fumée varient en taille
        color=color,
        color_variation=0.2,
        direction_type="smoke",
        direction_spread=math.pi / 4,  # Dispersion limitée vers le haut
        gravity=-20.0,  # Légère poussée vers le haut
        fade_out=True,
    )

def create_sparks_config(
    count: int = 15,
    speed: float = 400.0,
    lifetime: float = 0.3,
    size: int = 6,
    color: Tuple[int, int, int] = (255, 200, 0),
) -> ParticleEffectConfig:
    """Crée une configuration d'effet d'étincelles.
    
    Args:
        count: Nombre de particules
        speed: Vitesse de base (pixels/seconde)
        lifetime: Durée de vie (secondes)
        size: Taille des particules (diamètre en pixels)
        color: Couleur de base (RGB)
        
    Returns:
        Configuration d'effet d'étincelles
    """
    return ParticleEffectConfig(
        count=count,
        speed=speed,
        speed_variation=0.5,
        lifetime=lifetime,
        size=size,
        color=color,
        direction_type="sparks",
        gravity=200.0,  # Les étincelles tombent
        fade_out=True,
    )

def create_flame_explosion_config(
    count: int = 24,
    speed: float = 320.0,
    lifetime: float = 0.4,
    size: int = 16,
) -> ParticleEffectConfig:
    """Crée une configuration d'effet d'explosion de flamme colorée et dynamique.
    
    L'effet d'explosion de flamme est conçu pour ressembler à une explosion de feu :
    - Les particules se dispersent dans toutes les directions
    - Les particules ralentissent progressivement (friction)
    - Les particules tombent sous l'effet de la gravité
    - Les particules utilisent une palette de couleurs chaudes (rouge, orange, jaune) avec une variation importante pour un effet coloré et dynamique
    - Les particules varient en taille pour un effet plus riche
    - Les particules rétrécissent progressivement pendant leur durée de vie
    - Les particules disparaissent progressivement (fade-out)
    
    La couleur de base est un orange/rouge vif (255, 100, 0) avec une variation importante (0.6)
    qui permet des variations vers le rouge foncé, l'orange vif et le jaune, créant un effet
    de flamme colorée et dynamique. Cette configuration ne dépend pas de la couleur de l'objet
    source et produit toujours un effet d'explosion de flamme spectaculaire.
    
    Args:
        count: Nombre de particules (défaut: 24)
        speed: Vitesse de base (pixels/seconde, défaut: 320.0)
        lifetime: Durée de vie (secondes, défaut: 0.4)
        size: Taille de base des particules (diamètre en pixels, défaut: 16)
        
    Returns:
        Configuration d'effet d'explosion de flamme avec friction, gravité et variations de couleur importantes
    """
    return ParticleEffectConfig(
        count=count,
        speed=speed,
        speed_variation=0.4,  # Variation de vitesse augmentée (40%) pour plus de dynamisme
        lifetime=lifetime,
        lifetime_variation=0.2,  # Variation de durée de vie (20%) pour un effet plus naturel
        size=size,
        size_variation=0.5,  # Variation de taille importante (50%) pour des particules de tailles variées
        color=(255, 100, 0),  # Couleur de base orange/rouge vif pour l'effet de flamme
        color_variation=0.6,  # Variation de couleur importante (60%) pour créer un effet de flamme colorée (rouge, orange, jaune)
        direction_type="explosion",
        direction_spread=2.0 * math.pi,  # Toutes les directions (360 degrés)
        gravity=400.0,  # Gravité modérée pour faire tomber les particules progressivement
        friction=0.92,  # Friction de 8% par seconde (0.92) : les particules ralentissent progressivement
        size_shrink=True,  # Les particules rétrécissent progressivement pendant leur durée de vie
        fade_out=True,  # Les particules disparaissent progressivement
    )

def create_confetti_config(
    count: int = 50,
    speed: float = 400.0,
    lifetime: float = 2.5,
    size: int = 12,
) -> ParticleEffectConfig:
    """Crée une configuration d'effet de confetti festif.
    
    L'effet de confetti est conçu pour célébrer des événements comme le passage de niveau :
    - Les particules se dispersent dans toutes les directions
    - Les particules utilisent une palette de couleurs vives et variées (rouge, bleu, vert, jaune, violet, orange, rose)
    - Les particules ralentissent progressivement (friction)
    - Les particules tombent sous l'effet de la gravité
    - Les particules varient en taille, vitesse et couleur pour un effet dynamique
    - Les particules rétrécissent progressivement pendant leur durée de vie
    - Les particules disparaissent progressivement (fade-out)
    
    Args:
        count: Nombre de particules (défaut: 50)
        speed: Vitesse de base (pixels/seconde, défaut: 400.0)
        lifetime: Durée de vie (secondes, défaut: 2.5)
        size: Taille de base des particules (diamètre en pixels, défaut: 12)
        
    Returns:
        Configuration d'effet de confetti avec friction, gravité et variations de couleur importantes
    """
    # Palette de couleurs festives pour les confettis
    # Note: La couleur de base sera choisie aléatoirement lors de la création des particules
    # Pour simplifier, on utilise une couleur moyenne et on laisse la variation de couleur faire le reste
    base_color = (255, 100, 100)  # Couleur de base (rose/rouge) avec variation importante
    
    return ParticleEffectConfig(
        count=count,
        speed=speed,
        speed_variation=0.5,  # Variation de vitesse importante (50%) pour plus de dynamisme
        lifetime=lifetime,
        lifetime_variation=0.3,  # Variation de durée de vie (30%) pour un effet plus naturel
        size=size,
        size_variation=0.6,  # Variation de taille importante (60%) pour des confettis de tailles variées
        color=base_color,
        color_variation=0.8,  # Variation de couleur très importante (80%) pour créer une palette colorée et festive
        direction_type="explosion",
        direction_spread=2.0 * math.pi,  # Toutes les directions (360 degrés)
        gravity=500.0,  # Gravité modérée pour faire tomber les confettis progressivement
        friction=0.90,  # Friction de 10% par seconde (0.90) : les confettis ralentissent progressivement
        size_shrink=True,  # Les confettis rétrécissent progressivement pendant leur durée de vie
        fade_out=True,  # Les confettis disparaissent progressivement
    )
```

**Note** : Pour obtenir une palette de couleurs plus variée pour les confettis, on peut créer plusieurs effets de particules avec des couleurs différentes et les déclencher simultanément, ou modifier le système de particules pour supporter une palette de couleurs multiples.
```

## Intégration

### Initialisation globale

Le système de particules doit être initialisé une seule fois et partagé dans toute l'application :

```python
# Dans main.py ou dans un module de gestion globale
from moteur_jeu_presentation.particles import ParticleSystem

# Créer une instance globale du système de particules
particle_system = ParticleSystem()
```

### Utilisation depuis l'inventaire

```python
# Dans inventory.py
from moteur_jeu_presentation.particles import ParticleSystem, create_flame_explosion_config

# Supposons que particle_system est accessible globalement ou injecté
def remove_item(self, item_id: str, quantity: int = 1, animated: bool = True) -> bool:
    """Retire un objet de l'inventaire avec effet de particules de flamme."""
    # ... logique de retrait ...
    
    if animated:
        # Créer la configuration d'explosion de flamme (couleur indépendante de l'objet)
        config = create_flame_explosion_config(
            count=24,
            speed=320.0,
            lifetime=0.4,
            size=16,
        )
        
        # Calculer la position de l'objet dans le monde
        world_x = player_x + item_offset_x
        world_y = player_y + item_offset_y
        
        # Créer l'effet de particules
        particle_system.create_effect(world_x, world_y, config, effect_id=f"inventory_{item_id}")
    
    return True
```

### Utilisation depuis le système de combat

```python
# Exemple d'utilisation pour un effet de dégâts
from moteur_jeu_presentation.particles import ParticleSystem, create_explosion_config

def apply_damage(self, target_x: float, target_y: float, damage_type: str) -> None:
    """Applique des dégâts avec effet de particules."""
    if damage_type == "fire":
        config = create_explosion_config(
            count=30,
            speed=200.0,
            lifetime=0.5,
            size=12,
            color=(255, 100, 0),  # Orange/rouge pour le feu
        )
    elif damage_type == "ice":
        config = create_explosion_config(
            count=20,
            speed=150.0,
            lifetime=0.6,
            size=10,
            color=(100, 200, 255),  # Bleu pour la glace
        )
    else:
        config = create_explosion_config(
            count=15,
            speed=250.0,
            lifetime=0.3,
            size=8,
            color=(200, 200, 200),  # Gris pour les dégâts normaux
        )
    
    particle_system.create_effect(target_x, target_y, config)
```

### Utilisation depuis l'environnement

```python
# Exemple d'effet de pluie continu
from moteur_jeu_presentation.particles import ParticleSystem, create_rain_config

def start_rain_effect(self) -> None:
    """Démarre un effet de pluie continu."""
    config = create_rain_config(
        count=100,
        speed=300.0,
        lifetime=5.0,
        size=3,
        color=(150, 150, 255),
    )
    
    # Créer plusieurs effets de pluie à différentes positions
    for i in range(10):
        x = random.uniform(0, SCREEN_WIDTH)
        y = random.uniform(-100, 0)  # Commencer au-dessus de l'écran
        particle_system.create_effect(x, y, config, effect_id=f"rain_{i}")
```

### Animation de confetti pour le passage de niveau

L'animation de confetti est utilisée pour célébrer visuellement le passage de niveau du personnage principal. Cette animation est déclenchée automatiquement lors de l'augmentation du niveau du personnage (voir spécification 7 - Système de niveaux du personnage).

#### Caractéristiques de l'animation

1. **Déclenchement** : L'animation de confetti est déclenchée automatiquement pendant l'animation de transition de niveau (voir spécification 11). Les confettis sont émis en continu pendant toute la durée de l'animation de transition, jusqu'à 1 seconde avant la fin.

2. **Position d'émission** : Les confettis sont émis **uniquement** depuis deux positions distinctes correspondant aux coins du texte de transition de niveau :
   - **Coin haut gauche du texte** : Position `(text_x, text_y)` où `text_x` et `text_y` sont les coordonnées du coin supérieur gauche du texte de transition (voir spécification 11, section "Animation de transition de niveau")
   - **Coin haut droit du texte** : Position `(text_x + text_width, text_y)` où `text_width` est la largeur du texte de transition
   - **Note importante** : Les coordonnées du texte sont en coordonnées écran, mais le système de particules utilise des coordonnées monde. Il faut convertir les coordonnées écran en coordonnées monde en ajoutant `camera_x` pour la coordonnée X (la coordonnée Y reste généralement identique car il n'y a pas de décalage vertical de caméra)
   - **Aucune émission depuis le personnage** : Les confettis ne doivent jamais être émis depuis la position du personnage (`self.x`, `self.y`). L'émission se fait exclusivement depuis les coins du texte de transition.

3. **Durée et fréquence** :
   - Les confettis sont lancés **en continu** pendant toute la durée de l'animation de transition de niveau
   - L'émission de confettis **s'arrête 1 seconde avant la fin** de l'animation de transition
   - Par exemple, si l'animation de transition dure 1.5 secondes, les confettis sont émis de 0.0 à 0.5 secondes (pendant 0.5 secondes)
   - La fréquence d'émission est configurable via `CONFETTI_EMISSION_INTERVAL` (défaut: 0.2 secondes entre chaque émission)

4. **Configuration de l'effet** : L'effet de confetti utilise la fonction `create_confetti_config()` qui crée une configuration d'explosion avec des couleurs variées et festives :
   - **Palette de couleurs** : Les confettis utilisent une palette de couleurs vives et variées (rouge, bleu, vert, jaune, violet, orange, rose) pour créer un effet festif et coloré
   - **Dispersion** : Les particules se dispersent dans toutes les directions (360 degrés) depuis chaque position d'émission
   - **Gravité** : Les confettis tombent progressivement sous l'effet de la gravité pour un effet réaliste
   - **Friction** : Les confettis ralentissent progressivement pendant leur chute
   - **Variations** : Les confettis varient en taille, vitesse et couleur pour un effet dynamique et naturel
   - **Nombre de particules** : Configurable via `CONFETTI_COUNT_PER_EMISSION` (défaut: 60 particules par émission, doublé pour plus d'effet visuel)

5. **Durée de vie des particules** : Chaque particule de confetti dure environ 2-3 secondes, avec un fade-out progressif.

#### Intégration dans la classe Player

La classe `Player` (voir spécification 7) doit être étendue pour déclencher l'animation de confetti lors du passage de niveau :

**Nouvelles propriétés** :
- `particle_system: Optional[ParticleSystem]` : Référence au système de particules (optionnel, peut être `None` si le système n'est pas disponible)
- `_confetti_emission_timer: float = 0.0` : Timer pour gérer la fréquence d'émission de confettis
- `_confetti_last_emission_time: float = 0.0` : Temps de la dernière émission (pour éviter les émissions multiples dans la même frame)

**Nouvelles méthodes** :
- `set_particle_system(particle_system: ParticleSystem) -> None` : Définit la référence au système de particules
- `_emit_confetti_from_text_corners(camera_x: float) -> None` : Émet des confettis depuis les coins haut gauche et haut droit du texte de transition

**Méthodes obsolètes** :
- `_trigger_confetti_celebration()` : Cette méthode ne doit plus être utilisée pour le passage de niveau. Elle peut être supprimée ou conservée pour d'autres usages futurs si nécessaire. **Aucune émission de confetti ne doit être déclenchée depuis la position du personnage**.

**Modification de la méthode `_update_level_transition()`** :

L'animation de confetti est intégrée dans `_update_level_transition()` de la classe `Player`. La méthode doit être modifiée pour gérer l'émission continue de confettis :

```python
def _update_level_transition(self, dt: float, camera_x: float = 0.0) -> None:
    """Met à jour l'animation de transition de niveau et l'émission de confettis."""
    if not self.level_transition_active:
        return
    
    self.level_transition_timer -= dt
    self.level_transition_switch_timer += dt
    
    # Gérer l'alternance des sprites
    if self.level_transition_switch_timer >= self.level_transition_switch_interval:
        self.level_transition_switch_timer = 0.0
        self.level_transition_showing_old = not self.level_transition_showing_old
    
    # Gérer l'émission de confettis
    # Les confettis sont émis en continu jusqu'à 1 seconde avant la fin
    if self.particle_system is not None:
        time_remaining = self.level_transition_timer
        if time_remaining > CONFETTI_STOP_BEFORE_END:
            # Mettre à jour le timer d'émission
            self._confetti_emission_timer += dt
            
            # Vérifier si une nouvelle émission doit être créée
            if self._confetti_emission_timer >= CONFETTI_EMISSION_INTERVAL:
                self._confetti_emission_timer = 0.0
                self._emit_confetti_from_text_corners(camera_x)
    
    # Terminer l'animation si le timer est écoulé
    if self.level_transition_timer <= 0.0:
        self.level_transition_active = False
        self.level_transition_showing_old = False
        self.level_transition_old_sprite_sheet = None
        self.level_transition_text_surface = None
        # Réinitialiser le timer de confettis
        self._confetti_emission_timer = 0.0
        self._confetti_last_emission_time = 0.0

def _emit_confetti_from_text_corners(self, camera_x: float) -> None:
    """Émet des confettis depuis les coins haut gauche et haut droit du texte de transition."""
    if self.particle_system is None or self.level_transition_text_surface is None:
        return
    
    from moteur_jeu_presentation.particles import create_confetti_config
    import time
    
    # Calculer les coordonnées du texte (en coordonnées écran)
    # Ces coordonnées sont calculées de la même manière que dans _draw_level_transition()
    screen_width = 1280  # RENDER_WIDTH (à récupérer depuis la configuration ou la surface)
    screen_height = 720  # RENDER_HEIGHT (à récupérer depuis la configuration ou la surface)
    text_width = self.level_transition_text_surface.get_width()
    text_height = self.level_transition_text_surface.get_height()
    text_x = (screen_width - text_width) // 2
    text_y = (screen_height - text_height) // 2
    
    # Position du coin haut gauche (en coordonnées écran)
    left_x_screen = text_x
    left_y_screen = text_y
    
    # Position du coin haut droit (en coordonnées écran)
    right_x_screen = text_x + text_width
    right_y_screen = text_y
    
    # Convertir en coordonnées monde (ajouter camera_x pour X, Y reste identique)
    left_x_world = left_x_screen + camera_x
    left_y_world = left_y_screen
    right_x_world = right_x_screen + camera_x
    right_y_world = right_y_screen
    
    # Créer la configuration de confetti
    config = create_confetti_config(
        count=CONFETTI_COUNT_PER_EMISSION,
        speed=400.0,
        lifetime=2.5,
        size=12,
    )
    
    # Créer un timestamp unique pour les identifiants
    timestamp = time.time()
    
    # Créer les effets de particules depuis les deux positions
    self.particle_system.create_effect(
        left_x_world,
        left_y_world,
        config,
        effect_id=f"confetti_level_up_left_{timestamp}"
    )
    
    self.particle_system.create_effect(
        right_x_world,
        right_y_world,
        config,
        effect_id=f"confetti_level_up_right_{timestamp}"
    )
```

**Variables de configuration** (à ajouter dans le module `player.py` ou dans un module de configuration) :

```python
CONFETTI_EMISSION_INTERVAL: float = 0.2  # Intervalle entre chaque émission en secondes
CONFETTI_STOP_BEFORE_END: float = 1.0  # Durée avant la fin où l'émission s'arrête en secondes
CONFETTI_COUNT_PER_EMISSION: int = 60  # Nombre de particules par émission (doublé pour plus d'effet visuel)
CONFETTI_HORIZONTAL_OFFSET: float = 80.0  # Offset horizontal en pixels pour déplacer les confettis plus loin à gauche et à droite (dans le repère de conception 1920x1080, converti automatiquement)
```

#### Intégration dans la boucle de jeu

Le système de particules doit être initialisé et passé au `Player` lors de la création :

```python
# Dans main.py ou dans le GameState
from moteur_jeu_presentation.particles import ParticleSystem

# Créer le système de particules
particle_system = ParticleSystem()

# Créer le joueur
player = Player(x, y, player_level=1, stats_config=stats_config)

# Passer la référence au système de particules
player.set_particle_system(particle_system)

# Dans la boucle de jeu
def update(dt: float) -> None:
    # ... autres mises à jour ...
    # OPTIMISATION: Passer les paramètres de la caméra pour le culling
    particle_system.update(dt, camera_x, render_width, render_height, margin=200)
    # ... autres mises à jour ...

def draw(surface: pygame.Surface) -> None:
    # ... autres rendus ...
    
    # Rendre les particules
    particle_commands = particle_system.get_display_commands(camera_x, render_width, render_height, margin=100)
    if particle_commands:
        surface.blits(particle_commands, False)
    
    # ... autres rendus ...
```

#### Intégration avec l'animation de transition de niveau

L'animation de confetti est intégrée directement dans l'animation de transition de niveau (voir spécification 11) pour créer un effet visuel combiné et festif :

- L'animation de transition de niveau affiche le texte "level X -> level Y" centré à l'écran et alterne les sprites
- L'animation de confetti émet des particules colorées **en continu** depuis les coins haut gauche et haut droit du texte de transition
- Les confettis sont émis pendant toute la durée de l'animation de transition, jusqu'à 1 seconde avant la fin
- Les deux animations sont synchronisées et se déroulent simultanément pour créer un effet de célébration complet

**Ordre de déclenchement** :
1. L'utilisateur appuie sur `U` pour confirmer le level up
2. L'animation de transition de niveau démarre (`start_level_transition()`)
3. Dans `_update_level_transition()`, l'émission de confettis commence automatiquement depuis les coins du texte
4. Les confettis sont émis en continu (toutes les 0.2 secondes par défaut) jusqu'à 1 seconde avant la fin de l'animation
5. Les animations se terminent et le jeu reprend normalement

**Note importante** : L'émission de confettis est gérée **uniquement** dans `_update_level_transition()` pour être parfaitement synchronisée avec l'animation de transition. **Aucune émission de confetti ne doit être déclenchée depuis la position du personnage** - les confettis sont émis exclusivement depuis les coins haut gauche et haut droit du texte de transition. La méthode `_trigger_confetti_celebration()` ne doit plus être utilisée pour le passage de niveau et peut être supprimée ou conservée pour d'autres usages futurs si nécessaire.

#### Configuration

Les paramètres de l'animation de confetti peuvent être configurés via des constantes dans la classe `Player` ou via un fichier de configuration :

```python
# Constantes recommandées
DEFAULT_CONFETTI_COUNT = 50  # Nombre de particules
DEFAULT_CONFETTI_SPEED = 400.0  # Vitesse de base (pixels/seconde)
DEFAULT_CONFETTI_LIFETIME = 2.5  # Durée de vie (secondes)
DEFAULT_CONFETTI_SIZE = 12  # Taille de base (diamètre en pixels)
```

#### Gestion des erreurs

- Si le système de particules n'est pas disponible (`particle_system is None`), l'animation de confetti est ignorée silencieusement (pas d'erreur levée)
- Si la position du personnage n'est pas disponible, utiliser des coordonnées par défaut (0, 0) ou ignorer l'animation

#### Optimisations

- L'animation de confetti est légère et n'impacte pas significativement les performances
- Le nombre de particules peut être ajusté selon les performances de la plateforme cible
- Les particules sont automatiquement nettoyées par le système de particules une fois leur durée de vie écoulée
- Le culling des particules hors écran (voir section "Optimisations de performance") s'applique également aux confettis, réduisant les calculs pour les particules qui sortent de l'écran

### Boucle principale

```python
# Dans main.py
def main() -> None:
    """Point d'entrée principal du jeu."""
    # ... initialisation ...
    
    particle_system = ParticleSystem()
    
    while running:
        dt = clock.tick(FPS) / 1000.0
        
        # Mettre à jour le système de particules
        # OPTIMISATION: Passer les paramètres de la caméra pour le culling et éviter les calculs inutiles
        particle_system.update(dt, camera_x, render_width, render_height, margin=200)
        
        # ... autres mises à jour ...
        
        # Rendu
        screen.fill((0, 0, 0))
        
        # ... autres rendus ...
        
        # Rendre les particules
        particle_commands = particle_system.get_display_commands(camera_x, render_width, render_height, margin=100)
        if particle_commands:
            screen.blits(particle_commands, False)
        
        pygame.display.flip()
```

## Optimisations de performance

### Optimisations de culling (frustum culling)

- **Culling des effets hors écran** : `ParticleSystem.update()` accepte les paramètres de la caméra (`camera_x`, `screen_width`, `screen_height`, `margin`) et ne met à jour que les effets visibles ou proches de l'écran. Les effets complètement hors écran ne sont pas mis à jour, économisant ainsi les calculs de position et de physique pour toutes leurs particules.
- **Culling des particules hors écran** : `ParticleEffect.update()` accepte également les paramètres de la caméra et ne met à jour que les particules visibles. Les particules hors écran voient uniquement leur durée de vie décrémentée (pas de calcul de position, gravité, friction), ce qui économise considérablement les calculs.
- **Marge de culling** : Une marge configurable (défaut: 200 pixels pour `update()`, 100 pixels pour `get_display_commands()`) permet d'éviter le culling trop agressif et de s'assurer que les particules proches de l'écran sont toujours mises à jour.
- **Impact sur les performances** : Cette optimisation est particulièrement importante lorsque de nombreux effets de particules sont actifs simultanément, car elle évite de calculer les positions de milliers de particules hors écran.

### Optimisations de rendu

- **Cache des surfaces de particules** : Les surfaces de particules sont mises en cache avec une clé composite `(size, r, g, b, opacity)` pour maximiser la réutilisation. Le cache est limité à 500 entrées pour éviter les fuites mémoire.
- **Création directe des surfaces** : Les surfaces de particules sont créées directement avec la couleur et l'opacité pour préserver correctement les couleurs. Chaque particule crée sa propre surface avec `pygame.Surface((size, size), pygame.SRCALPHA)` et dessine le cercle directement avec `pygame.draw.circle()` en utilisant la couleur avec l'opacité dans le canal alpha.
- **Culling au rendu** : `get_display_commands()` effectue également un culling des particules hors écran avant de créer les commandes de dessin, évitant ainsi la création inutile de surfaces.

### Limitation du nombre de particules

- **Nombre configurable** : Le nombre de particules par effet est configurable via `ParticleEffectConfig.count`
- **Nettoyage automatique** : Les particules mortes sont automatiquement supprimées de la liste
- **Limite globale optionnelle** : Une limite globale peut être ajoutée pour éviter d'avoir trop de particules simultanées

### Échantillonnage limité pour la couleur

- **Extraction de couleur optimisée** : L'extraction de la couleur dominante utilise un échantillonnage limité (100 pixels par défaut) pour éviter de parcourir tous les pixels du sprite

### Rendu optimisé

- **Utilisation de `blits()`** : Les particules sont rendues en utilisant `blits()` pour réduire les appels CPU->SDL
- **Commandes de dessin** : Le système génère des commandes de dessin qui peuvent être regroupées avec d'autres éléments

## Gestion des erreurs

| Cas | Gestion | Message |
| --- | --- | --- |
| Sprite None pour extraction de couleur | Retourner la couleur par défaut | (pas de message, comportement attendu) |
| Taille de particule <= 0 | Forcer à 1 pixel minimum | (pas de message, correction automatique) |
| Configuration invalide | Lever `ValueError` | `Invalid particle effect configuration: {reason}` |
| Effet introuvable lors de la suppression | Retourner `False` | (pas de message, comportement attendu) |

## Pièges courants

1. **Coordonnées monde vs écran** : Les particules utilisent des coordonnées monde et doivent être ajustées avec `camera_x` lors du rendu. S'assurer que la position de départ est en coordonnées monde.

2. **Performance avec beaucoup de particules** : Limiter le nombre de particules par effet et le nombre d'effets simultanés. Utiliser les configurations prédéfinies qui sont optimisées.

3. **Rendu des couleurs de particules** : Pour préserver correctement les couleurs des particules, dessiner directement le cercle avec `pygame.draw.circle()` en utilisant la couleur de la particule avec l'opacité dans le canal alpha. Ne pas utiliser `BLEND_MULT` avec une surface blanche, car cela peut altérer les couleurs. Utiliser `color_with_alpha = (*particle.color, opacity)` et dessiner directement le cercle avec cette couleur.

4. **Nettoyage des effets** : Les effets sont automatiquement supprimés quand toutes leurs particules sont mortes, mais on peut aussi les supprimer manuellement avec `remove_effect()`.

5. **Gravité et direction** : La gravité est appliquée en plus de la vitesse initiale. Pour un effet de chute, utiliser `direction_type="rain"` avec une gravité positive.

6. **Variation de couleur** : La variation de couleur ajuste la saturation. Pour des effets plus réalistes, utiliser une variation modérée (0.1 à 0.3).

7. **Durée de vie** : S'assurer que la durée de vie est suffisante pour que les particules soient visibles, mais pas trop longue pour éviter d'accumuler des particules mortes.

8. **Culling et paramètres de caméra** : Pour bénéficier de l'optimisation de culling, toujours passer les paramètres de la caméra (`camera_x`, `screen_width`, `screen_height`, `margin`) à `ParticleSystem.update()`. Si ces paramètres ne sont pas fournis, tous les effets seront mis à jour même s'ils sont hors écran, ce qui peut impacter les performances. Les particules hors écran continueront d'exister mais ne bougeront pas jusqu'à ce qu'elles reviennent à l'écran ou que leur durée de vie expire.

9. **Résolution design vs rendu (RENDER > DESIGN)** : Les positions passées à `create_effect()` et utilisées pour le rendu doivent être cohérentes avec la surface de rendu (repère de rendu, cf. spec 15). Pour les événements `particle_effect` avec `sprite_tag`, les bounds des layers viennent du LevelLoader déjà en repère de rendu : ne pas les multiplier une seconde fois par `compute_design_scale()`, sinon les particules sont mal placées quand RENDER > DESIGN.

## Tests

### Tests unitaires

- `test_particle_update()` : Vérifier que `Particle.update()` met à jour correctement la position et la durée de vie
- `test_particle_is_alive()` : Vérifier que `Particle.is_alive()` retourne les bonnes valeurs
- `test_particle_get_opacity()` : Vérifier que `Particle.get_opacity()` calcule correctement l'opacité
- `test_particle_get_size()` : Vérifier que `Particle.get_size()` calcule correctement la taille avec et sans `size_shrink`
- `test_particle_effect_creation()` : Vérifier que `ParticleEffect` crée le bon nombre de particules selon la configuration
- `test_particle_effect_update()` : Vérifier que `ParticleEffect.update()` met à jour toutes les particules et supprime les mortes
- `test_particle_system_create_effect()` : Vérifier que `ParticleSystem.create_effect()` crée et ajoute un effet
- `test_particle_system_update()` : Vérifier que `ParticleSystem.update()` met à jour tous les effets et supprime les inactifs
- `test_particle_system_update_culling()` : Vérifier que `ParticleSystem.update()` ne met à jour que les effets visibles quand les paramètres de caméra sont fournis
- `test_particle_effect_update_culling()` : Vérifier que `ParticleEffect.update()` ne met à jour que les particules visibles quand les paramètres de caméra sont fournis
- `test_particle_system_display_commands()` : Vérifier que `ParticleSystem.get_display_commands()` génère les bonnes commandes de dessin
- `test_particle_system_display_commands_culling()` : Vérifier que `ParticleSystem.get_display_commands()` exclut les particules hors écran
- `test_extract_dominant_color()` : Vérifier que l'extraction de couleur fonctionne correctement
- `test_create_flame_explosion_config()` : Vérifier que la configuration d'explosion de flamme utilise les bonnes couleurs (palette chaude) et une variation importante
- `test_create_confetti_config()` : Vérifier que la configuration de confetti utilise les bonnes couleurs (palette festive) et une variation importante
- `test_particle_surface_cache()` : Vérifier que le cache de surfaces fonctionne (création unique, réutilisation)

### Tests d'intégration

1. Créer un effet d'explosion → vérifier que les particules se dispersent dans toutes les directions, ralentissent progressivement (friction), tombent sous l'effet de la gravité, rétrécissent progressivement, et varient en taille et couleur
2. Créer un effet d'explosion de flamme → vérifier que les particules utilisent une palette de couleurs chaudes (rouge, orange, jaune) avec une variation importante, indépendamment de la couleur de l'objet source
3. Créer un effet de confetti → vérifier que les particules se dispersent dans toutes les directions avec une palette de couleurs vives et variées (rouge, bleu, vert, jaune, violet, orange, rose), ralentissent progressivement (friction), tombent sous l'effet de la gravité, et varient en taille, vitesse et couleur
4. Créer un effet de pluie → vérifier que les particules tombent verticalement
5. Créer un effet de fumée → vérifier que les particules montent avec dispersion
6. Créer plusieurs effets simultanés → vérifier que tous sont mis à jour et rendus correctement
7. Vérifier le nettoyage automatique → créer un effet, attendre que toutes les particules meurent, vérifier que l'effet est supprimé
8. Vérifier le culling des effets hors écran → créer des effets à différentes positions, vérifier que seuls les effets visibles sont mis à jour
9. Vérifier le culling des particules hors écran → créer un effet avec des particules qui sortent de l'écran, vérifier que les particules hors écran ne sont pas mises à jour (sauf durée de vie)

### Vérifications visuelles

- Les particules se déplacent correctement selon leur configuration
- Les particules disparaissent progressivement si `fade_out=True`
- Les particules utilisent la bonne couleur
- Les particules sont correctement ajustées avec la caméra
- Les effets prédéfinis (explosion, explosion de flamme, confetti, pluie, fumée, étincelles) ont l'apparence attendue
- L'explosion de flamme utilise une palette de couleurs chaudes (rouge, orange, jaune) avec une variation importante pour créer un effet coloré et dynamique
- Le confetti utilise une palette de couleurs vives et variées (rouge, bleu, vert, jaune, violet, orange, rose) avec une variation importante pour créer un effet festif et coloré
- Les performances restent bonnes même avec plusieurs effets simultanés
- **Pour les explosions** : Vérifier que les particules ralentissent progressivement (friction), tombent sous l'effet de la gravité, rétrécissent progressivement (`size_shrink`), et varient en taille et couleur pour un effet dynamique et spectaculaire
- **Culling** : Vérifier que les particules hors écran ne sont pas mises à jour (pas de calcul de position/physique) et que les effets hors écran ne sont pas mis à jour du tout, améliorant ainsi les performances

## Évolutions futures

- **Formes de particules personnalisées** : Permettre d'utiliser des sprites personnalisés au lieu de cercles
- **Effets de particules attachés** : Permettre d'attacher un effet à une entité qui suit son mouvement
- **Système d'émetteurs** : Créer des émetteurs qui génèrent continuellement des particules
- **Interactions entre particules** : Permettre aux particules d'interagir entre elles (collisions, attraction, répulsion)
- **Effets de particules complexes** : Support pour des effets plus complexes (feu, eau, électricité)
- **Configuration via fichiers** : Permettre de définir des effets de particules dans des fichiers de configuration
- **Particules avec texture** : Support pour des particules avec textures au lieu de couleurs unies
- **Effets de particules 3D** : Support pour des effets de particules avec profondeur (optionnel)

## Références

- Bonnes pratiques : `bonne_pratique.md`
- Spécification système d'inventaire : `spec/13-systeme-d-inventaire.md` (implémentation originale des particules)
- Spécification système de niveaux du personnage : `spec/7-systeme-de-niveaux-personnage.md` (utilisation de l'animation de confetti pour le passage de niveau)
- Documentation Pygame : [pygame.Surface](https://www.pygame.org/docs/ref/surface.html), [pygame.draw](https://www.pygame.org/docs/ref/draw.html)

## Structure de fichiers recommandée

```
moteur_jeu_presentation/
├── src/
│   └── moteur_jeu_presentation/
│       └── particles/
│           ├── __init__.py
│           ├── particle.py          # Classe Particle
│           ├── effect.py            # Classe ParticleEffect, ParticleEffectConfig
│           ├── system.py            # Classe ParticleSystem
│           └── utils.py             # Utilitaires (extract_dominant_color, configurations prédéfinies)
└── ...
```

---

**Date de création** : 2024  
**Statut** : ✅ Implémenté

