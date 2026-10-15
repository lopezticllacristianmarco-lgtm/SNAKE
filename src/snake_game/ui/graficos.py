"""(Pygame graphics helpers: themed fonts, glow text and reusable buttons."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pygame

from snake_game.config import ALTO, ANCHO, Colores


def finger_a_logico(x: float, y: float) -> tuple[int, int]:
    """Convierte toque normalizado (0..1) a coords del lienzo lógico.

    Con ``SCALED`` SDL ajusta el lienzo ANCHO x ALTO a cualquier pantalla
    con letterbox (bandas si el aspecto difiere, ej. 20:9 vs 10:7).
    El ratón ya viene mapeado por SDL, pero FINGER trae 0..1 de la ventana
    física, así que hay que descontar las bandas y dividir por la escala.
    """
    try:
        ww, wh = pygame.display.get_window_size()
    except pygame.error:
        ww, wh = ANCHO, ALTO
    if ww <= 0 or wh <= 0:
        return (int(x * ANCHO), int(y * ALTO))
    escala = min(ww / ANCHO, wh / ALTO)
    if escala <= 0:
        return (int(x * ANCHO), int(y * ALTO))
    ox = (ww - ANCHO * escala) / 2
    oy = (wh - ALTO * escala) / 2
    lx = (float(x) * ww - ox) / escala
    ly = (float(y) * wh - oy) / escala
    return (int(lx), int(ly))


# --------------------------------------------------------------------------
# Fonts
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Tipografia:
    nombre: str = "Consolas"
    titulo: int = 62
    grande: int = 36
    media: int = 26
    normal: int = 20
    pequena: int = 15

    def _cargar(self, destino: int, bold: bool) -> pygame.font.Font:
        clave = (self.nombre, destino, bold)
        if clave not in _FUENTES_CACHE:
            try:
                _FUENTES_CACHE[clave] = pygame.font.SysFont(self.nombre, destino, bold=bold)
            except pygame.error:  # pragma: no cover - exotic systems
                _FUENTES_CACHE[clave] = pygame.font.Font(None, destino)
        return _FUENTES_CACHE[clave]

    @property
    def titulo_f(self) -> pygame.font.Font:
        return self._cargar(self.titulo, True)

    @property
    def grande_f(self) -> pygame.font.Font:
        return self._cargar(self.grande, True)

    @property
    def media_f(self) -> pygame.font.Font:
        return self._cargar(self.media, True)

    @property
    def normal_f(self) -> pygame.font.Font:
        return self._cargar(self.normal, False)

    @property
    def pequena_f(self) -> pygame.font.Font:
        return self._cargar(self.pequena, False)


_FUENTES = Tipografia()

_FUENTES_CACHE: dict[tuple, pygame.font.Font] = {}


def texto(texto: str, tamano: str = "normal", color: tuple[int, int, int] = Colores.BLANCO,
          negrita: bool = False) -> pygame.Surface:
    """Render a line of text with a per-line memoised cache."""
    clave = (texto, tamano, color, negrita)
    cache = _TEXTO_CACHE[tamano]
    if clave not in cache:
        fuente = {
            "titulo": _FUENTES.titulo_f,
            "grande": _FUENTES.grande_f,
            "media": _FUENTES.media_f,
            "normal": _FUENTES.normal_f,
            "pequena": _FUENTES.pequena_f,
        }[tamano]
        cache[clave] = fuente.render(texto, True, color)
    return cache[clave]


_TEXTO_CACHE: dict[str, dict[tuple, pygame.Surface]] = {k: {} for k in
                                                       ("titulo", "grande", "media", "normal", "pequena")}


def texto_glow(cadena: str, tamano: str, color: tuple[int, int, int],
               color_glow: tuple[int, int, int] | None = None) -> pygame.Surface:
    """Text with a soft neon halo (cheap 4-direction shadow trick)."""
    brillo = color_glow or color
    base = texto(cadena, tamano, brillo)
    superficie = pygame.Surface((base.get_width() + 8, base.get_height() + 8), pygame.SRCALPHA)
    for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
        superficie.blit(base, (4 + dx, 4 + dy))
    superficie.blit(texto(cadena, tamano, color), (4, 4))
    return superficie


def blit_centrado(destino: pygame.Surface, superficie: pygame.Surface,
                  centro: tuple[int, int]) -> None:
    destino.blit(superficie, superficie.get_rect(center=centro))


# --------------------------------------------------------------------------
# Buttons
# --------------------------------------------------------------------------
@dataclass
class EstiloBoton:
    relleno: tuple[int, int, int] = (18, 26, 52)
    borde: tuple[int, int, int] = Colores.CYAN
    texto: tuple[int, int, int] = Colores.BLANCO
    hover_relleno: tuple[int, int, int] | None = None
    radio: int = 8


ESTILOS = {
    "principal": EstiloBoton((10, 48, 26), Colores.CYAN, Colores.BLANCO),
    "secundario": EstiloBoton((26, 22, 60), Colores.ROSA, Colores.BLANCO),
    "peligro": EstiloBoton((66, 22, 26), Colores.ROJO, Colores.BLANCO),
    "opcion": EstiloBoton((14, 22, 40), Colores.GRIS_OSCURO, Colores.BLANCO),
}


class Boton:
    """A neon-styled button with hover and onClick."""

    def __init__(self, centro: tuple[int, int], ancho: int, alto: int, etiqueta: str,
                 estilo: str = "opcion", on_click: Callable[[], None] | None = None,
                 fuente_tamano: str = "media") -> None:
        self.rect = pygame.Rect(0, 0, ancho, alto)
        self.rect.center = centro
        self.etiqueta = etiqueta
        self.estilo = ESTILOS[estilo]
        self.on_click = on_click
        self.fuente_tamano = fuente_tamano
        self.hover = False

    def manejar(self, evento: pygame.event.Event) -> bool:
        """Return True when this button consumed the click/tap."""
        # Toque móvil: FINGERDOWN trae x,y normalizados (0..1) de la ventana
        # física; se convierte al lienzo lógico descontando letterbox.
        if evento.type == pygame.FINGERDOWN:
            try:
                pos = finger_a_logico(evento.x, evento.y)
            except (AttributeError, TypeError, ValueError):
                return False
            if self.rect.collidepoint(pos):
                if self.on_click is not None:
                    self.on_click()
                return True
            return False
        pos = getattr(evento, "pos", None)
        if pos is None:
            return False
        if evento.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(pos)
        if self.rect.collidepoint(pos) and evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if self.on_click is not None:
                self.on_click()
            return True
        return False

    def _estilo(self, clave: str, por_defecto=None):
        """Read a style key from either an EstiloBoton or a plain dict."""
        if isinstance(self.estilo, dict):
            return self.estilo.get(clave, por_defecto)
        return getattr(self.estilo, clave, por_defecto)

    def dibujar(self, pantalla: pygame.Surface) -> None:
        relleno = self._estilo("hover_relleno") or self._estilo("relleno")
        radio = self._estilo("radio", 8)
        if self.hover:
            relleno = tuple(min(255, c + 28) for c in relleno)
        pygame.draw.rect(pantalla, relleno, self.rect, border_radius=radio)
        pygame.draw.rect(pantalla, self._estilo("borde"), self.rect,
                         width=2, border_radius=radio)
        etiqueta = texto(self.etiqueta, self.fuente_tamano, self._estilo("texto"))
        blit_centrado(pantalla, etiqueta, self.rect.center)
        if self.hover:
            pygame.draw.rect(pantalla, self._estilo("borde"), self.rect.inflate(6, 6),
                             width=1, border_radius=radio + 2)


def pinchar_creditos(pantalla: pygame.Surface, nombre: str, version: str) -> None:
    """Small credit line pinned to the bottom of a screen."""
    crep = texto(nombre, "pequena", Colores.GRIS)
    pantalla.blit(crep, (12, pantalla.get_height() - crep.get_height() - 10))
    ver = texto(version, "pequena", Colores.GRIS_OSCURO)
    pantalla.blit(ver, (pantalla.get_width() - ver.get_width() - 12,
                        pantalla.get_height() - ver.get_height() - 10))
