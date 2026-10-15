"""Application shell — window, state and main loop.

Scene behaviour lives in :mod:`snake_game.escenas` (one mixin per screen);
this module only owns the shared state and drives the state machine.
"""

from __future__ import annotations

import os

import pygame

from snake_game.audio import Audio, asegurar_sonidos
from snake_game.config import (
    ALTO,
    ANCHO,
    FPS_MENUS,
    TITULO,
    Dificultad,
    ModoJuego,
    skin_valida,
)
from snake_game.core.guardado import (
    EstadoJugador,
    GestorEstado,
    normalizar_musica_custom,
    normalizar_skins,
    normalizar_teclas,
)
from snake_game.escenas.ajustes import AjustesMixin
from snake_game.escenas.base import Escena, Partida
from snake_game.escenas.juego import JuegoMixin
from snake_game.escenas.menu import MenuMixin
from snake_game.escenas.tienda import TiendaMixin
from snake_game.ui.graficos import Boton
from snake_game.ui.render import Renderizador

_ES_ANDROID = "ANDROID_ARGUMENT" in os.environ


def _resolucion_nativa() -> tuple[int, int]:
    """Resolución física de la pantalla, siempre en apaisado (w >= h).

    Prueba en orden: ``display.Info``, ``get_desktop_sizes``. Si todo falla
    devuelve el lienzo lógico. Forzar apaisado evita que un móvil en
    portrait deforme el juego (SDL hará letterbox con SCALED).
    """
    candidatos: list[tuple[int, int]] = []
    try:
        info = pygame.display.Info()
        if info.current_w > 0 and info.current_h > 0:
            candidatos.append((info.current_w, info.current_h))
    except pygame.error:
        pass
    try:
        for w, h in pygame.display.get_desktop_sizes():
            if w > 0 and h > 0:
                candidatos.append((w, h))
    except (pygame.error, NotImplementedError):
        pass
    # Quedarse con la más grande (pantalla principal).
    if candidatos:
        dw, dh = max(candidatos, key=lambda s: s[0] * s[1])
        if dh > dw:  # portrait -> intercambiar para seguir en horizontal
            dw, dh = dh, dw
        return dw, dh
    return ANCHO, ALTO


def _tamano_auto() -> tuple[int, int]:
    """Ventana inicial: llena la pantalla conservando el aspecto 10:7.

    El lienzo lógico es ANCHO x ALTO = 1000x700 (landscape). En móvil la
    orientación está bloqueada a horizontal (``orientation = landscape``),
    y SDL con SCALED ajusta solo el contenido a cualquier tamaño de
    pantalla (móvil chico, grande, tablet, PC) con letterbox si el aspecto
    difiere (ej. 20:9). Aquí devolvemos un tamaño de ventana apaisado que
    cabe en la pantalla (94% del display).
    """
    dw, dh = _resolucion_nativa()
    if dw > 0 and dh > 0:
        escala = min(dw / ANCHO, dh / ALTO) * 0.94
        escala = max(0.6, escala)
        return round(ANCHO * escala), round(ALTO * escala)
    return ANCHO, ALTO


def _crear_ventana() -> pygame.Surface:
    """Crea la ventana apaisada auto-ajustada a la pantalla.

    El lienzo lógico siempre es ANCHO x ALTO (1000x700, horizontal);
    ``SCALED`` lo estira a la ventana (y mapea ratón/táctil), así el juego
    se ajusta solo en cualquier móvil sin tocar código.
    En Android se pide la resolución nativa en FULLSCREEN para ocupar toda
    la pantalla horizontal sea cual sea el modelo.
    """
    nativa = _resolucion_nativa()
    if _ES_ANDROID:
        candidatos = [
            (nativa, pygame.SCALED | pygame.FULLSCREEN),
            ((ANCHO, ALTO), pygame.SCALED | pygame.FULLSCREEN),
            ((ANCHO, ALTO), pygame.SCALED),
            ((0, 0), pygame.FULLSCREEN),
            ((ANCHO, ALTO), 0),
        ]
    elif os.environ.get("SDL_VIDEODRIVER") == "dummy":
        # Tests headless: el driver dummy no soporta SCALED repetido.
        candidatos = [((ANCHO, ALTO), 0)]
    else:
        candidatos = [(_tamano_auto(), pygame.SCALED | pygame.RESIZABLE),
                      (nativa, pygame.SCALED | pygame.RESIZABLE),
                      ((ANCHO, ALTO), pygame.SCALED),
                      ((ANCHO, ALTO), 0)]
    ultimo_error: Exception | None = None
    for tamano, flags in candidatos:
        try:
            return pygame.display.set_mode(tamano, flags)
        except pygame.error as exc:
            ultimo_error = exc
    raise pygame.error(f"no se pudo crear la ventana: {ultimo_error}")


def pos_logica_desde_finger(evento: pygame.event.Event) -> tuple[int, int] | None:
    """Convierte un evento FINGER (x,y normalizados 0..1) a coords lógicas.

    Descuenta el letterbox de SCALED para que valga en cualquier pantalla
    de móvil (16:9, 20:9, tablets). Devuelve None si no trae x/y.
    """
    x = getattr(evento, "x", None)
    y = getattr(evento, "y", None)
    if x is None or y is None:
        return None
    try:
        from snake_game.ui.graficos import finger_a_logico
        return finger_a_logico(float(x), float(y))
    except (TypeError, ValueError):
        return None


class App(MenuMixin, JuegoMixin, AjustesMixin, TiendaMixin):
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(TITULO)
        # Las fuentes cacheadas quedan inválidas tras un pygame.quit() previo
        # (suite de tests): limpiarlas para no reusar objetos muertos.
        try:
            from snake_game.ui.graficos import _FUENTES_CACHE, _TEXTO_CACHE
            _FUENTES_CACHE.clear()
            for cache in _TEXTO_CACHE.values():
                cache.clear()
        except ImportError:
            pass
        self.pantalla = _crear_ventana()
        self.reloj = pygame.time.Clock()
        self._tocar_origen: tuple[int, int] | None = None

        asegurar_sonidos()
        self.audio = Audio()
        self.render = Renderizador(self.pantalla)

        self.estado = GestorEstado()
        self.prefs = self.estado.leer_estado()
        self.audio.musica_activa = self.prefs.musica_activa
        self.audio.volumen_musica = self.prefs.volumen_musica
        self.audio.volumen_efectos = self.prefs.volumen_efectos
        self.audio.musica_custom = normalizar_musica_custom(self.prefs.musica_custom)
        self.teclas = normalizar_teclas(self.prefs.teclas)
        self.ajuste_captura = None
        self.ajuste_nombre_editando = False
        self.ajuste_musica_mensaje = ""

        self.dificultad = Dificultad.por_nombre(self.prefs.dificultad)
        self.modo = ModoJuego.por_nombre(self.prefs.modo)
        self.nombre = self.prefs.nombre
        # Tienda: monedero persistente + skins.
        self.monedas: int = max(0, int(self.prefs.monedas or 0))
        self.skins: list[str] = normalizar_skins(self.prefs.skins)
        self.skin_activa: str = skin_valida(self.prefs.skin_activa)
        if self.skin_activa not in self.skins:
            self.skin_activa = self.skins[0]
        self.tienda_mensaje: str = ""
        self.scena: str = Escena.MENU
        self.partida: Partida | None = None
        self.acumulador = 0.0
        self.razon_final = "seguir"
        self.es_record_nuevo = False
        self.puntaje_final = 0
        self.monedas_ganadas = 0

        self._crear_menu()
        self._crear_tienda()
        self.audio.iniciar_musica()
        self._boton_volver_cache = Boton((500, 620), 200, 48, "VOLVER",
                                         "secundario", lambda: self._ir(Escena.MENU))

        self._manejo: dict[str, type] = {
            Escena.MENU: self._manejar_menu,
            Escena.AJUSTES: self._manejar_ajustes,
            Escena.TIENDA: self._manejar_tienda,
            Escena.INSTRUCCIONES: self._manejar_instrucciones,
            Escena.RECORDS: self._manejar_records,
            Escena.JUEGO: self._manejar_juego,
            Escena.PAUSA: self._manejar_pausa,
            Escena.GAME_OVER: self._manejar_game_over,
            Escena.GANAR: self._manejar_game_over,
        }
        self._dibujo: dict[str, type] = {
            Escena.MENU: self._dibujar_menu,
            Escena.AJUSTES: self._dibujar_ajustes,
            Escena.TIENDA: self._dibujar_tienda,
            Escena.INSTRUCCIONES: self._dibujar_instrucciones,
            Escena.RECORDS: self._dibujar_records,
            Escena.JUEGO: self._dibujar_juego,
            Escena.PAUSA: self._dibujar_pausa,
            Escena.GAME_OVER: self._dibujar_game_over,
            Escena.GANAR: self._dibujar_game_over,
        }

    # ------------------------------------------------------------------
    # Entry points
    # ------------------------------------------------------------------
    def _reajustar_a_pantalla(self, tamano: tuple[int, int] | None = None) -> None:
        """Recrea la ventana para que siga ajustada a la pantalla actual.

        - Si ``tamano`` viene (VIDEORESIZE), se usa tal cual.
        - Si no, se usa la resolución nativa actual (plegables, split-screen,
          rotación, cambio de monitor, DPI).
        Mantiene el lienzo lógico ANCHO x ALTO: SCALED reescala y centra con
        letterbox, sin deformar y sin tocar el resto del código.
        """
        if os.environ.get("SDL_VIDEODRIVER") == "dummy":
            return
        if tamano is None:
            tamano = _resolucion_nativa()
        w, h = int(tamano[0]), int(tamano[1])
        if w <= 0 or h <= 0:
            return
        # Nunca ventana portrait: el juego es horizontal.
        if h > w:
            w, h = h, w
        flags = pygame.SCALED | pygame.RESIZABLE
        if _ES_ANDROID:
            flags = pygame.SCALED | pygame.FULLSCREEN
        try:
            self.pantalla = pygame.display.set_mode((w, h), flags)
            self.render.pantalla = self.pantalla
        except pygame.error:
            pass

    def ejecutar(self) -> None:
        try:
            while True:
                tiempo_ms = pygame.time.get_ticks()
                dt = self.reloj.tick(FPS_MENUS) / 1000.0
                for evento in pygame.event.get():
                    if evento.type == pygame.QUIT:
                        return
                    if evento.type == pygame.VIDEORESIZE:
                        # PC / móvil redimensionable: auto-ajustar al nuevo tamaño.
                        self._reajustar_a_pantalla(tuple(evento.size))
                        continue
                    if evento.type in (
                        getattr(pygame, "WINDOWSIZECHANGED", -1),
                        getattr(pygame, "WINDOWMAXIMIZED", -1),
                        getattr(pygame, "WINDOWRESTORED", -1),
                    ):
                        # Plegables, split-screen, DeX, cambio de pantalla.
                        self._reajustar_a_pantalla()
                        continue
                    if evento.type == getattr(pygame, "DISPLAYEVENT", -1):
                        self._reajustar_a_pantalla()
                        continue
                    self._manejo[self.scena](evento)
                self._actualizar(dt, tiempo_ms)
                self._dibujo[self.scena](tiempo_ms)
                pygame.display.flip()
        finally:
            self.audio.cerrar()
            pygame.quit()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _guardar_preferencias(self) -> None:
        self.prefs = EstadoJugador(
            dificultad=self.dificultad.value,
            musica_activa=self.audio.musica_activa,
            ultimo_record=self.estado.record_para(self.dificultad, self.modo.value),
            modo=self.modo.value,
            volumen_musica=self.audio.volumen_musica,
            volumen_efectos=self.audio.volumen_efectos,
            teclas=dict(self.teclas),
            nombre=self.nombre,
            monedas=self.monedas,
            skins=list(self.skins),
            skin_activa=self.skin_activa,
            musica_custom=normalizar_musica_custom(self.audio.musica_custom),
        )
        self.estado.guardar_estado(self.prefs)

    # ------------------------------------------------------------------
    # Scene control
    # ------------------------------------------------------------------
    def _ir(self, scena: str) -> None:
        self.scena = scena


def main() -> None:
    App().ejecutar()
