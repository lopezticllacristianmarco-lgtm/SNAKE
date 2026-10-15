"""Configuration central: colours, layout, paths, difficulties.

Keeping every magic number and constant here makes the rest of the code
declarative and easy to tune without touching the logic.
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
PACKAGE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = PACKAGE_DIR / "assets"

# --------------------------------------------------------------------------
# Window
# --------------------------------------------------------------------------
ANCHO = 1000
ALTO = 700
FPS_MENUS = 60
TITULO = "SNAKE GAME - Professional Edition"

# --------------------------------------------------------------------------
# Grid / board
# --------------------------------------------------------------------------
TAMANO_CELDA = 25
MIN_X = 75
MAX_X = 725
MIN_Y = 100
MAX_Y = 625
AREA_DE_JUEGO = (MIN_X, MIN_Y, MAX_X, MAX_Y)

CABEZA_INICIAL = (400, 350)

# --------------------------------------------------------------------------
# Colours (a deeper, material neon palette)
# --------------------------------------------------------------------------
class Colores:
    NEGRO = (5, 8, 18)
    FONDO = (8, 15, 28)
    PANEL = (12, 18, 32)
    BLANCO = (235, 240, 255)
    GRIS = (120, 130, 150)
    GRIS_OSCURO = (60, 70, 90)

    CYAN = (0, 230, 255)
    CYAN_OSCURO = (0, 140, 200)
    ROSA = (255, 0, 200)
    ROSA_OSCURO = (170, 0, 150)
    MORADO = (190, 80, 255)

    ROJO = (255, 45, 85)
    ROJO_CLARO = (255, 100, 130)
    AMARILLO = (255, 214, 60)
    NARANJA = (255, 150, 50)

    VERDE = (60, 255, 160)
    VERDE_OSCURO = (10, 70, 40)


# --------------------------------------------------------------------------
# Difficulty
# --------------------------------------------------------------------------
class Dificultad(str, Enum):
    """Playable difficulty presets.

    ``velocidad`` is the update rate in frames per second (more = faster).
    ``factor_nivel`` multiplies the fruits required to reach the next level.
    ``vida_bomba`` is the bomb lifetime in ticks.
    ``max_bombas`` caps how many bombs coexist on the board.
    """

    FACIL = "Facil"
    NORMAL = "Normal"
    DIFICIL = "Dificil"
    EXTREMO = "Extremo"

    @property
    def velocidad(self) -> int:
        return {"FACIL": 6, "NORMAL": 8, "DIFICIL": 11, "EXTREMO": 14}[self.name]

    @property
    def factor_nivel(self) -> int:
        return {"FACIL": 6, "NORMAL": 8, "DIFICIL": 10, "EXTREMO": 12}[self.name]

    @property
    def vida_bomba(self) -> int:
        return {"FACIL": 420, "NORMAL": 330, "DIFICIL": 240, "EXTREMO": 170}[self.name]

    @property
    def max_bombas(self) -> int:
        return {"FACIL": 2, "NORMAL": 3, "DIFICIL": 4, "EXTREMO": 5}[self.name]

    @property
    def rango_bomba(self) -> tuple[int, int]:
        """(min, max) ticks between two bomb spawns, globally scaled."""
        base_min, base_max = (150, 350)
        factor = {"FACIL": 2.0, "NORMAL": 1.35, "DIFICIL": 1.0, "EXTREMO": 0.7}[self.name]
        return int(base_min * factor), int(base_max * factor)

    @property
    def segundos_crono(self) -> int:
        """Tiempo base del modo Contrarreloj según dificultad."""
        return {"FACIL": 60, "NORMAL": 40, "DIFICIL": 25, "EXTREMO": 15}[self.name]

    @property
    def segundos_laberinto(self) -> int:
        """Cada cuánto rota el laberinto: más difícil = cambia más seguido."""
        return {"FACIL": 30, "NORMAL": 20, "DIFICIL": 15, "EXTREMO": 10}[self.name]

    @classmethod
    def por_nombre(cls, nombre: str) -> Dificultad:
        try:
            return cls(nombre)
        except ValueError:
            return cls.NORMAL


# --------------------------------------------------------------------------
# Game modes
# --------------------------------------------------------------------------
class ModoJuego(str, Enum):
    """Modos de juego: clasico, zen (atraviesa muros), contrarreloj y laberinto."""

    CLASICO = "Clasico"
    ZEN = "Zen"
    CONTRARRELOJ = "Contrarreloj"
    LABERINTO = "Laberinto"

    @property
    def etiqueta_corta(self) -> str:
        return {"CLASICO": "CLASICO", "ZEN": "ZEN",
                "CONTRARRELOJ": "CRONO", "LABERINTO": "LABERINTO"}[self.name]

    @property
    def descripcion(self) -> str:
        return {
            "CLASICO": "Come y sobrevive",
            "ZEN": "Atraviesa los muros",
            "CONTRARRELOJ": (f"60/40/25/15s por dificultad, "
                             f"+{BONUS_MANZANA_SEG}s/manzana"),
            "LABERINTO": "Muros que rotan solos",
        }[self.name]

    @classmethod
    def por_nombre(cls, nombre: str) -> ModoJuego:
        try:
            return cls(nombre)
        except ValueError:
            return cls.CLASICO


BONUS_MANZANA_SEG = 3
BONUS_DORADA_SEG = 5
TIEMPO_MAX_CRONO_SEG = 120


# --------------------------------------------------------------------------
# Monedas y tienda de skins
# --------------------------------------------------------------------------
# Las monedas se ganan jugando (aunque pierdas se conservan) y se gastan en
# la tienda. Reglas:
#  - manzana normal: +1 moneda | dorada: +5 | subir de nivel: +5 bonus.
MONEDA_POR_MANZANA = 1
MONEDA_POR_DORADA = 5
MONEDA_POR_NIVEL = 5

# Catálogo de skins: id -> (nombre visible, precio, color cuerpo, color oscuro).
# La "neon" es la clásica y viene desbloqueada (precio 0).
# La "arcoiris" es LEGENDARIA: no usa colores estáticos, cicla el arcoíris
# como tira LED (ver ``color_arcoiris`` y el render animado).
SKINS: dict[str, tuple[str, int, tuple[int, int, int], tuple[int, int, int]]] = {
    "neon": ("NEON", 0, (0, 230, 255), (0, 140, 200)),
    "verde": ("VERDE", 50, (60, 255, 160), (10, 120, 70)),
    "rosa": ("ROSA", 80, (255, 0, 200), (170, 0, 150)),
    "dorada": ("DORADA", 150, (255, 214, 60), (170, 120, 20)),
    "morada": ("MORADA", 200, (190, 80, 255), (110, 40, 170)),
    "fuego": ("FUEGO", 300, (255, 80, 50), (170, 30, 20)),
    "arcoiris": ("ARCOIRIS", 100000, (255, 0, 200), (0, 230, 255)),
}
SKIN_POR_DEFECTO = "neon"
SKIN_ANIMADAS = frozenset({"arcoiris"})


def es_skin_animada(skin: str) -> bool:
    """True si la skin cambia de color con el tiempo (estilo LED)."""
    return skin_valida(skin) in SKIN_ANIMADAS


def color_arcoiris(tiempo_ms: int, desplazamiento: float = 0.0) -> tuple[int, int, int]:
    """Color LED del arcoíris: tono rotando a ~1 vuelta cada 3s + offset.

    Saturación y brillo al máximo para efecto neón. ``desplazamiento`` en
    vueltas (0..1): cada segmento de la serpiente lleva uno distinto y la
    onda de color recorre el cuerpo.
    """
    import colorsys

    tono = ((tiempo_ms / 3000.0) + desplazamiento) % 1.0
    r, g, b = colorsys.hsv_to_rgb(tono, 1.0, 1.0)
    return (int(r * 255), int(g * 255), int(b * 255))


def skin_valida(skin: str) -> str:
    """Devuelve el id si existe, si no la skin por defecto."""
    return skin if skin in SKINS else SKIN_POR_DEFECTO


def colores_skin(skin: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """(color_principal, color_oscuro) para dibujar la serpiente."""
    _, _, principal, oscuro = SKINS[skin_valida(skin)]
    return principal, oscuro


# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------
GUARDAR_DIR = Path.home() / "AppData" / "Roaming" / "SnakeGame" if os.name == "nt" else Path.home() / ".snake_game"
ARCHIVO_ESTADO = GUARDAR_DIR / "estado.json"
ARCHIVO_RECORDS = GUARDAR_DIR / "records.json"

# --------------------------------------------------------------------------
# Audio
# --------------------------------------------------------------------------
MUSICA_RUTA = ASSETS_DIR / "Snake.mp3"
FONDO_RUTA = ASSETS_DIR / "fondo.png"
SONIDOS = {
    "comer": ASSETS_DIR / "comer.wav",
    "perder": ASSETS_DIR / "perder.wav",
    "ganar": ASSETS_DIR / "ganar.wav",
    "bomba": ASSETS_DIR / "bomba.wav",
}
VOLUMEN_MUSICA = 0.5
