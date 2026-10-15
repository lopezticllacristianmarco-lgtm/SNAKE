"""Base de escenas: constantes, partida y ayudas compartidas.

``App`` (en ``snake_game.app``) conserva el estado y el bucle principal;
estos mixins aportan el comportamiento por escena.
"""

from __future__ import annotations

import random

import pygame

from snake_game.config import Dificultad, ModoJuego
from snake_game.core.logica import Logica
from snake_game.core.modelos import ModeloSnake
from snake_game.ui.graficos import Boton

CREDITO = "SNAKE GAME - Edicion Profesional"


class Escena:
    MENU = "menu"
    INSTRUCCIONES = "instrucciones"
    RECORDS = "records"
    JUEGO = "juego"
    PAUSA = "pausa"
    GAME_OVER = "game_over"
    GANAR = "ganar"
    AJUSTES = "ajustes"
    TIENDA = "tienda"


class Partida:
    """One playable match: the model plus the pure-logic engine."""

    def __init__(self, dificultad: Dificultad, modo: ModoJuego, seed: int) -> None:
        self.logica = Logica(random.Random(seed))
        self.modelo: ModeloSnake = self.logica.iniciar_partida(dificultad, modo)
        self.seed = seed


class BaseEscena:
    """Ayudas compartidas por todas las escenas."""

    @staticmethod
    def _pos_tap(evento: pygame.event.Event) -> tuple[int, int] | None:
        """Posición lógica del tap para PC y móvil horizontal.

        - MOUSEBUTTONDOWN -> evento.pos (SDL ya mapea SCALED a ANCHO x ALTO,
          incluyendo letterbox en pantallas 20:9, tablets, etc).
        - FINGERDOWN -> evento.x/y normalizados -> lienzo lógico con
          corrección de bandas vía ``finger_a_logico``.
        Devuelve None si no es un tap.
        """
        if evento.type == pygame.MOUSEBUTTONDOWN and getattr(evento, "button", 1) == 1:
            return getattr(evento, "pos", None)
        if evento.type == pygame.FINGERDOWN:
            try:
                from snake_game.ui.graficos import finger_a_logico
                return finger_a_logico(evento.x, evento.y)
            except (AttributeError, TypeError, ValueError):
                return None
        return None

    def _manejar_y_botones(self, evento: pygame.event.Event, botones: list[Boton]) -> None:
        # Ratón (PC) + toque (móvil horizontal). FINGERDOWN no trae .pos,
        # lo convierte Boton.manejar a coords lógicas ANCHO x ALTO.
        if evento.type not in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION,
                               pygame.FINGERDOWN):
            return
        for boton in botones:
            if boton.manejar(evento):
                break
