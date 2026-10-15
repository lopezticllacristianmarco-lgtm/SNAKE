"""Escena de partida individual: juego, pausa, finales e info."""

from __future__ import annotations

import random

import pygame

from snake_game.config import ALTO, ANCHO
from snake_game.escenas.base import BaseEscena, Escena, Partida
from snake_game.ui.graficos import (
    Boton,
    blit_centrado,
    texto,
    texto_glow,
)

_UMBRAL_TOQUE = 30


class JuegoMixin(BaseEscena):
    def _direccion_desde_toque(self, evento: pygame.event.Event) -> tuple[int, int] | None:
        """Swipe touch/mouse -> movement vector (only meaningful while dragging).

        En móvil horizontal el swipe llega como FINGERDOWN/UP (x,y 0..1) o
        como ratón emulado; se aceptan ambos y se escalan al lienzo lógico
        ANCHO x ALTO para que el umbral sea igual en PC y móvil.
        """
        # --- Toque nativo móvil (FINGER*) ---
        if evento.type == pygame.FINGERDOWN:
            pos = self._pos_logica_finger(evento)
            if pos is not None:
                self._tocar_origen = pos
            return None
        if evento.type == pygame.FINGERUP:
            origen = self._tocar_origen
            pos = self._pos_logica_finger(evento)
            self._tocar_origen = None
            if origen is None or pos is None:
                return None
            return self._vector_desde_swipe(origen, pos)
        if evento.type == pygame.FINGERMOTION:
            return None  # solo inicio/fin importan para el swipe
        # --- Ratón (PC y toque emulado en Android) ---
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            self._tocar_origen = evento.pos
            return None
        if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
            origen = self._tocar_origen
            self._tocar_origen = None
            if origen is None:
                return None
            return self._vector_desde_swipe(origen, evento.pos)
        return None

    @staticmethod
    def _pos_logica_finger(evento: pygame.event.Event) -> tuple[int, int] | None:
        # Usa el mapeo con corrección de letterbox para que el swipe mida
        # igual en móviles 16:9, 20:9, tablets y PC.
        try:
            from snake_game.ui.graficos import finger_a_logico
            return finger_a_logico(evento.x, evento.y)
        except (AttributeError, TypeError, ValueError):
            return None

    @staticmethod
    def _vector_desde_swipe(origen: tuple[int, int],
                            destino: tuple[int, int]) -> tuple[int, int] | None:
        dx = destino[0] - origen[0]
        dy = destino[1] - origen[1]
        if max(abs(dx), abs(dy)) < _UMBRAL_TOQUE:
            return None
        if abs(dx) > abs(dy):
            return (25, 0) if dx > 0 else (-25, 0)
        return (0, 25) if dy > 0 else (0, -25)

    @staticmethod
    def _direccion_boton_movil(pos: tuple[int, int]) -> tuple[int, int] | None:
        """D-pad táctil situado en el margen derecho, fuera del tablero."""
        x, y = pos
        botones = {
            pygame.Rect(884, 214, 42, 42): (0, -25),
            pygame.Rect(834, 260, 42, 42): (-25, 0),
            pygame.Rect(884, 260, 42, 42): (0, 25),
            pygame.Rect(934, 260, 42, 42): (25, 0),
        }
        for rect, direccion in botones.items():
            if rect.collidepoint(x, y):
                return direccion
        return None

    def _pos_toque_evento(self, evento: pygame.event.Event) -> tuple[int, int] | None:
        if evento.type == pygame.FINGERDOWN:
            return self._pos_logica_finger(evento)
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            return evento.pos
        return None

    def _manejar_juego(self, evento: pygame.event.Event) -> None:
        if evento.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
            pos = self._pos_toque_evento(evento)
            direccion = self._direccion_boton_movil(pos) if pos else None
            if direccion and self.partida is not None:
                if self.partida.modelo.partida_activa:
                    self.partida.logica.cambiar_direccion(self.partida.modelo, direccion)
                self._tocar_origen = None
                return
        if evento.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
                           pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
            toc = self._direccion_desde_toque(evento)
            if toc and self.partida is not None:
                modelo = self.partida.modelo
                if modelo.partida_activa:
                    self.partida.logica.cambiar_direccion(modelo, toc)
            return
        if evento.type != pygame.KEYDOWN or self.partida is None:
            return
        if evento.key in (pygame.K_ESCAPE, pygame.K_p, self.teclas.get("pausa")):
            self.audio.pausar_musica()
            self._ir(Escena.PAUSA)
            return
        if evento.key == pygame.K_m:
            self._alternar_musica()
            return
        logica = self.partida.logica
        modelo = self.partida.modelo
        mapa = self._mapa_teclas_juego()
        toc = mapa.get(evento.key, {
            pygame.K_UP: (0, -25),
            pygame.K_DOWN: (0, 25),
            pygame.K_LEFT: (-25, 0),
            pygame.K_RIGHT: (25, 0),
        }.get(evento.key))
        if toc:
            logica.cambiar_direccion(modelo, toc)

    def _actualizar(self, dt: float, _tiempo_ms: int) -> None:
        if self.scena not in (Escena.JUEGO,) or self.partida is None:
            return
        modelo = self.partida.modelo
        if not modelo.partida_activa:
            return
        self.acumulador += dt
        periodo = 1.0 / max(modelo.velocidad, 1)
        limite = 4 * periodo
        while self.acumulador >= periodo and self.partida.modelo.partida_activa:
            puntos_antes = modelo.puntaje
            razon = self.partida.logica.actualizar(modelo)
            self.acumulador -= periodo
            self._sonar_eventos(modelo, puntos_antes)
            if razon != "seguir":
                self._terminar(razon)
                return
        self.acumulador = min(self.acumulador, limite)

    def _sonar_eventos(self, modelo, puntos_antes: int = 0) -> None:
        hay_powerup = any(ev.startswith("powerup:") for ev in modelo.eventos)
        # Comer manzana (sube puntaje sin power-up): el crono suma +tiempo aquí.
        if modelo.puntaje > puntos_antes and not hay_powerup:
            self.audio.reproducir("comer", 0.6)
        for ev in modelo.eventos:
            if ev.startswith("powerup:"):
                self.audio.reproducir("ganar", 0.5)
            elif ev == "escudo_bloqueo":
                self.audio.reproducir("bomba", 0.5)
            elif ev == "laberinto_cambio":
                self.audio.reproducir("bomba", 0.3)

    def _empezar_juego(self) -> None:
        self.partida = Partida(self.dificultad, self.modo,
                               seed=random.randrange(1_000_000_000))
        self.partida.modelo.skin = self.skin_activa
        self.acumulador = 0.0
        self.razon_final = "seguir"
        self.es_record_nuevo = False
        self.monedas_ganadas = 0
        self.audio.iniciar_musica()
        self._ir(Escena.JUEGO)

    def _terminar(self, razon: str) -> None:
        if self.partida is None:
            return
        self.razon_final = razon
        self.puntaje_final = self.partida.modelo.puntaje
        # Las monedas se conservan SIEMPRE (muerte, tiempo o victoria).
        self.monedas_ganadas = int(getattr(self.partida.modelo, "monedas", 0) or 0)
        self.monedas = max(0, int(self.monedas) + self.monedas_ganadas)
        self.es_record_nuevo = self.estado.guardar_record(
            self.dificultad, self.puntaje_final, self.modo.value, self.nombre)
        self._guardar_preferencias()
        self.audio.pausar_musica()
        if razon == "muerte":
            self.audio.reproducir("perder")
            self._ir(Escena.GAME_OVER)
        elif razon == "tiempo":
            self.audio.reproducir("ganar")
            self._ir(Escena.GAME_OVER)
        else:
            self.audio.reproducir("ganar")
            self._ir(Escena.GANAR)

    def _manejar_pausa(self, evento: pygame.event.Event) -> None:
        if evento.type == pygame.KEYDOWN and evento.key in (
                pygame.K_ESCAPE, pygame.K_p, self.teclas.get("pausa")):
            self.audio.iniciar_musica()
            self._ir(Escena.JUEGO)
            return
        self._manejar_y_botones(evento, self._botones_pausa())

    def _manejar_game_over(self, evento: pygame.event.Event) -> None:
        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_RETURN:
                self._empezar_juego()
                return
            if evento.key == pygame.K_ESCAPE:
                self._ir(Escena.MENU)
                self.audio.iniciar_musica()
                return
        self._manejar_y_botones(evento, self._botones_game_over())

    def _manejar_instrucciones(self, evento: pygame.event.Event) -> None:
        if evento.type == pygame.KEYDOWN and evento.key in (pygame.K_ESCAPE, pygame.K_RETURN):
            self._ir(Escena.MENU)
            return
        self._manejar_y_botones(evento, [self._boton_volver])

    def _manejar_records(self, evento: pygame.event.Event) -> None:
        if evento.type == pygame.KEYDOWN and evento.key in (pygame.K_ESCAPE, pygame.K_RETURN):
            self._ir(Escena.MENU)
            return
        self._manejar_y_botones(evento, [self._boton_volver])

    def _botones_pausa(self) -> list[Boton]:
        continuar = Boton((500, 385), 280, 54, "CONTINUAR", "principal", self._reanudar)
        reiniciar = Boton((500, 452), 280, 50, "REINICIAR", "secundario", self._empezar_juego)
        menu = Boton((500, 516), 280, 50, "MENU PRINCIPAL", "peligro", self._volver_al_menu)
        return [continuar, reiniciar, menu]

    def _botones_game_over(self) -> list[Boton]:
        reiniciar = Boton((500, 470), 260, 60, "JUGAR DE NUEVO", "principal", self._empezar_juego)
        menu = Boton((500, 545), 260, 60, "MENU", "secundario", self._volver_al_menu)
        return [reiniciar, menu]

    def _reanudar(self) -> None:
        self.audio.iniciar_musica()
        self._ir(Escena.JUEGO)

    @property
    def _boton_volver(self) -> Boton:
        return self._boton_volver_cache

    def _dibujar_juego(self, tiempo_ms: int) -> None:
        if self.partida is None:
            return
        self.render.dibujar_partida(self.partida.modelo,
                                    self.estado.record_para(self.dificultad),
                                    tiempo_ms, self.dificultad.value)

    def _dibujar_pausa(self, tiempo_ms: int) -> None:
        self._dibujar_juego(tiempo_ms)
        oscuro = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        oscuro.fill((5, 8, 18, 190))
        self.pantalla.blit(oscuro, (0, 0))
        self.render.panel(pygame.Rect(300, 210, 400, 380), (255, 0, 200))
        blit_centrado(self.pantalla, texto_glow("PAUSA", "titulo", (255, 0, 200)), (500, 265))
        if self.partida:
            blit_centrado(self.pantalla,
                          texto(f"PUNTOS: {self.partida.modelo.puntaje}   NIVEL: {self.partida.modelo.nivel}",
                                "media", (235, 240, 255)), (500, 320))
        for boton in self._botones_pausa():
            boton.dibujar(self.pantalla)

    def _dibujar_game_over(self, _tiempo_ms: int) -> None:
        ganado = self.scena == Escena.GANAR
        es_tiempo = self.razon_final == "tiempo"
        if es_tiempo:
            titulo, color, subtitulo = "TIEMPO", (255, 214, 60), "SE ACABO EL TIEMPO"
        else:
            titulo = "GANASTE" if ganado else "PERDISTE"
            color = (255, 214, 60) if ganado else (255, 45, 85)
            subtitulo = "MANZANAS COLOCADAS" if ganado else "LA SERPIENTE MURIO"
        self.render.fondo(0)
        self.render.panel(pygame.Rect(180, 130, 640, 470), color)
        blit_centrado(self.pantalla, texto_glow(titulo, "titulo", color), (500, 195))
        blit_centrado(self.pantalla, texto(subtitulo,
                                           "media", (255, 0, 200)), (500, 255))
        blit_centrado(self.pantalla, texto(f"PUNTAJE FINAL: {self.puntaje_final:04}", "grande",
                                           (235, 240, 255)), (500, 320))
        blit_centrado(self.pantalla, texto(f"+{self.monedas_ganadas} MONEDAS  ·  TOTAL {self.monedas:04} (SE CONSERVAN)",
                                           "media", (255, 214, 60)), (500, 355))
        if self.es_record_nuevo:
            destello = (pygame.time.get_ticks() // 400) % 2 == 0
            if destello:
                blit_centrado(self.pantalla, texto("NUEVO RECORD!", "grande", (255, 214, 60)),
                              (500, 380))
        blit_centrado(self.pantalla,
                      texto(f"RECORD: {self.estado.record_para(self.dificultad, self.modo.value):04}", "media",
                            (255, 214, 60)), (500, 425))
        blit_centrado(self.pantalla, texto(f"{self.modo.value.upper()} · {self.dificultad.value.upper()}   |   "
                                           "ENTER = REINICIAR   |   ESC = MENU",
                                           "pequena", (120, 130, 150)), (500, 465))
        for boton in self._botones_game_over():
            boton.dibujar(self.pantalla)

    def _dibujar_instrucciones(self, _tiempo_ms: int) -> None:
        self.render.fondo(0)
        self.render.panel(pygame.Rect(120, 60, 760, 560), (255, 0, 200))
        blit_centrado(self.pantalla, texto("COMO JUGAR", "titulo", (255, 0, 200)), (500, 105))
        reglas = [
            "CONTROLES",
            "  W / FLECHA ARRIBA  - mover arriba",
            "  S / FLECHA ABAJO   - mover abajo",
            "  A / FLECHA IZQ     - mover a la izquierda",
            "  D / FLECHA DER     - mover a la derecha",
            "MECANICA",
            "  Come la manzana roja para sumar puntos (10 c/u).",
            "  Evita chocar con tu propio cuerpo, los muros y las bombas.",
            "  Las bombas explotan: si las tocas, la partida termina.",
            "  Completa la cuota de frutas para subir de nivel.",
            "MODOS (T EN EL MENU)",
            "  ZEN: atraviesa muros. CRONO: 60/40/25/15s +3s/manzana.",
            "  LABERINTO: los muros rotan solos (30/20/15/10s).",
            "POWER-UPS",
            "  $ DORADA: +30 puntos.  E ESCUDO: rompe 1 bomba.",
            "  S LENTO: la serpiente va mas despacio un rato.",
            "ESC = PAUSA    |    M = MUSICA",
        ]
        y = 160
        for linea in reglas:
            estilo = "media" if linea in ("CONTROLES", "MECANICA", "MODOS (T EN EL MENU)",
                                           "POWER-UPS") else "normal"
            color = (255, 0, 200) if estilo == "media" else (235, 240, 255)
            blit_centrado(self.pantalla, texto(linea, estilo, color), (500, y))
            y += (30 if estilo == "media" else 24)
        self._boton_volver.dibujar(self.pantalla)

    def _dibujar_records(self, _tiempo_ms: int) -> None:
        self.render.fondo(0)
        self.render.panel(pygame.Rect(250, 120, 500, 460), (255, 214, 60))
        blit_centrado(self.pantalla, texto_glow("RECORDS", "titulo", (255, 214, 60)), (500, 155))
        mejores = self.estado.mejores_records_detalle()
        y = 235
        if not mejores:
            blit_centrado(self.pantalla, texto("Aun no hay records.", "media", (120, 130, 150)),
                          (500, y))
        for clave, valor, nombre in mejores[:6]:
            quien = nombre or "—"
            blit_centrado(self.pantalla,
                          texto(f"{quien.upper():12} {valor:04}", "media", (235, 240, 255)),
                          (500, y))
            blit_centrado(self.pantalla, texto(clave.upper(), "pequena", (120, 130, 150)),
                          (500, y + 22))
            y += 52
        self._boton_volver.dibujar(self.pantalla)
