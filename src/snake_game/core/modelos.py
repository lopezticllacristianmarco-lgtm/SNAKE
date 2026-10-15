"""Domain models. Purely data — no pygame imports, fully unit-testable.

These objects describe *state*; the rules that mutate them live in
:mod:`snake_game.core.logica` and the rendering lives in the ``ui`` layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from snake_game.config import AREA_DE_JUEGO, CABEZA_INICIAL, TAMANO_CELDA

Vector = tuple[int, int]


@dataclass(eq=False)
class Comida:
    """The (single) food pellet on the board."""

    posicion: Vector

    def get_pos(self) -> Vector:
        return self.posicion


@dataclass
class Bomba:
    """A timed hazard. Disappears once ``tiempo_vida`` ticks elapse."""

    x: int
    y: int
    tiempo_vida: int
    activa: bool = True
    parpadeo: int = 0
    radio: int = 10

    def get_pos(self) -> Vector:
        return (self.x, self.y)

    def actualizar(self) -> None:
        """Advance one tick. Turns ``activa`` off when life is gone."""
        if not self.activa:
            return
        self.tiempo_vida -= 1
        self.parpadeo += 1
        if self.tiempo_vida <= 0:
            self.activa = False

    @property
    def en_destello(self) -> bool:
        """True during the final blink phase (before papering out)."""
        return self.tiempo_vida < 90 and self.parpadeo % 10 < 5


@dataclass
class PowerUp:
    """Recogible temporal: dorada (+puntos), escudo (anti-bomba) o lento."""

    x: int
    y: int
    tipo: str  # "dorada" | "escudo" | "lento"
    tiempo_vida: int = 300
    activa: bool = True

    def get_pos(self) -> Vector:
        return (self.x, self.y)

    def actualizar(self) -> None:
        if not self.activa:
            return
        self.tiempo_vida -= 1
        if self.tiempo_vida <= 0:
            self.activa = False


@dataclass
class Particula:
    """A tiny drifting particle used for the "eating" effect."""

    x: float
    y: float
    vx: float
    vy: float
    radio: int
    color: tuple[int, int, int]
    vida: int

    def actualizar(self) -> None:
        self.x += self.vx
        self.y += self.vy
        self.vida -= 1


@dataclass
class ModeloSnake:
    """Full observable game state for a running match."""

    dificultad: str = "Normal"
    velocidad: int = 8
    factor_nivel: int = 8
    vida_bomba: int = 330
    max_bombas: int = 3
    rango_bomba: tuple[int, int] = (150, 350)

    serpiente: list[Vector] = field(
        default_factory=lambda: [
            CABEZA_INICIAL,
            (CABEZA_INICIAL[0] - TAMANO_CELDA, CABEZA_INICIAL[1]),
            (CABEZA_INICIAL[0] - TAMANO_CELDA * 2, CABEZA_INICIAL[1]),
        ]
    )
    direccion: Vector = (TAMANO_CELDA, 0)
    cola_dir: list[Vector] = field(default_factory=list)
    comida: Comida | None = None
    bombas: list[Bomba] = field(default_factory=list)
    particulas: list[Particula] = field(default_factory=list)
    powerups: list[PowerUp] = field(default_factory=list)
    tiempo_hasta_bomba: int = 0
    tiempo_hasta_powerup: int = 180

    # Efectos temporales (en ticks de simulación).
    escudo_ticks: int = 0
    lento_ticks: int = 0
    velocidad_base: int = 8
    # Eventos del último tick para que la UI reaccione (sonidos, HUD).
    # Ej: ["powerup:dorada", "powerup:escudo", "escudo_bloqueo"]
    eventos: list[str] = field(default_factory=list)

    puntaje: int = 0
    frutos: int = 0
    nivel: int = 1
    frutos_para_nivel: int = 8
    # Monedas ganadas en ESTA partida (se conservan aunque pierdas: al
    # terminar se suman al monedero persistente).
    monedas: int = 0
    # Skin activa de la serpiente (id del catálogo SKINS).
    skin: str = "neon"

    # Modo de juego ("Clasico" | "Zen" | "Contrarreloj" | "Laberinto").
    modo: str = "Clasico"
    # Muros internos del modo Laberinto (celdas letales, incluso en Zen).
    obstaculos: list[Vector] = field(default_factory=list)
    # Rotación del laberinto: ticks para el próximo cambio y su intervalo.
    tiempo_hasta_laberinto: int = 0
    laberinto_cada: int = 0
    laberinto_variante: int = 0
    # Contrarreloj: ticks de simulación restantes y totales.
    tiempo_restante: int = 0
    tiempo_limite: int = 0

    partida_activa: bool = False
    game_over: bool = False
    gano: bool = False

    def cabeza(self) -> Vector:
        return self.serpiente[0]

    @property
    def limites(self) -> tuple[int, int, int, int]:
        return AREA_DE_JUEGO

    def frutos_restantes_para_nivel(self) -> int:
        return max(0, self.frutos_para_nivel - self.frutos)
