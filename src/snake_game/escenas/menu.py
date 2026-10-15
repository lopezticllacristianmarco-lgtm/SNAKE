"""Escena del menú principal."""

from __future__ import annotations

import pygame

from snake_game import __version__ as __paquete_version__
from snake_game.config import (
    BONUS_MANZANA_SEG,
    Dificultad,
    ModoJuego,
)
from snake_game.escenas.base import CREDITO, BaseEscena, Escena
from snake_game.ui.graficos import (
    Boton,
    blit_centrado,
    pinchar_creditos,
    texto,
    texto_glow,
)


class MenuMixin(BaseEscena):
    _PALETAS_DIFICULTAD = {
        Dificultad.FACIL: (0, 255, 150),
        Dificultad.NORMAL: (0, 230, 255),
        Dificultad.DIFICIL: (255, 180, 50),
        Dificultad.EXTREMO: (255, 45, 85),
    }
    _PALETAS_MODO = {
        ModoJuego.CLASICO: (0, 230, 255),
        ModoJuego.ZEN: (60, 255, 160),
        ModoJuego.CONTRARRELOJ: (255, 214, 60),
        ModoJuego.LABERINTO: (190, 80, 255),
    }

    def _crear_menu(self) -> None:
        """Construct the menu widgets; cheap enough to rebuild per frame."""
        self.boton_jugar = Boton((500, 458), 380, 56, "INICIAR JUEGO",
                                 "principal", self._empezar_juego)
        self.boton_dificultad: list[Boton] = []
        for i, dif in enumerate(Dificultad):
            cx = 280 + i * 150
            self.boton_dificultad.append(
                Boton((cx, 300), 138, 46, dif.value.upper(), "opcion", None,
                      fuente_tamano="media")
            )
        self.dificultad_control = 0
        self._refrescar_dificultad(silenciar=True)

        self.boton_modo: list[Boton] = []
        for i, modo in enumerate(ModoJuego):
            cx = 245 + i * 170
            self.boton_modo.append(
                Boton((cx, 404), 158, 36, modo.etiqueta_corta, "opcion", None,
                      fuente_tamano="normal")
            )
        self._refrescar_modo(silenciar=True)

        self.boton_instrucciones = Boton((300, 512), 190, 44, "INSTRUCCIONES",
                                         "secundario", lambda: self._ir(Escena.INSTRUCCIONES))
        self.boton_records = Boton((500, 512), 190, 44, "RECORDS",
                                   "secundario", lambda: self._ir(Escena.RECORDS))
        self.boton_ajustes = Boton((700, 512), 190, 44, "AJUSTES",
                                   "opcion", self._abrir_ajustes, fuente_tamano="normal")
        self.boton_tienda = Boton((500, 578), 340, 48, "TIENDA DE SKINS",
                                  "secundario", self._abrir_tienda,
                                  fuente_tamano="normal")
        self.boton_salir = Boton((500, 646), 190, 40, "SALIR",
                                 "peligro", lambda: pygame.event.post(pygame.event.Event(pygame.QUIT)))

    def _cambiar_dificultad(self, direccion: int) -> None:
        """Cycle difficulty with the arrow keys (mouse uses the chips)."""
        opciones = list(Dificultad)
        i = opciones.index(self.dificultad)
        self.dificultad = opciones[(i + direccion) % len(opciones)]
        self._refrescar_dificultad()
        self._guardar_preferencias()

    def _cambiar_modo(self, direccion: int) -> None:
        """Cycle game mode with T (mouse uses the chips)."""
        opciones = list(ModoJuego)
        i = opciones.index(self.modo)
        self.modo = opciones[(i + direccion) % len(opciones)]
        self._refrescar_modo()
        self._guardar_preferencias()

    def _refrescar_dificultad(self, silenciar: bool = False) -> None:
        """Highlight the selected chip with a filled colour, the rest muted."""
        for i, dif in enumerate(Dificultad):
            if dif is self.dificultad:
                color = self._PALETAS_DIFICULTAD[dif]
                self.boton_dificultad[i].estilo = {
                    "relleno": color,
                    "borde": (255, 255, 255),
                    "texto": (8, 10, 18),
                    "hover_relleno": color,
                    "radio": 14,
                }
            else:
                self.boton_dificultad[i].estilo = {
                    "relleno": (10, 16, 34),
                    "borde": (58, 68, 88),
                    "texto": (150, 160, 180),
                    "hover_relleno": (16, 26, 48),
                    "radio": 14,
                }
        if not silenciar:
            self.audio.reproducir("comer", 0.5)

    def _refrescar_modo(self, silenciar: bool = False) -> None:
        """Highlight the selected mode chip, mute the rest."""
        for i, modo in enumerate(ModoJuego):
            if modo is self.modo:
                color = self._PALETAS_MODO[modo]
                self.boton_modo[i].estilo = {
                    "relleno": color,
                    "borde": (255, 255, 255),
                    "texto": (8, 10, 18),
                    "hover_relleno": color,
                    "radio": 12,
                }
            else:
                self.boton_modo[i].estilo = {
                    "relleno": (10, 16, 34),
                    "borde": (58, 68, 88),
                    "texto": (150, 160, 180),
                    "hover_relleno": (16, 26, 48),
                    "radio": 12,
                }
        if not silenciar:
            self.audio.reproducir("comer", 0.5)

    def _alternar_musica(self) -> None:
        self.audio.musica_activa = not self.audio.musica_activa
        etiqueta = "MUSICA: ON" if self.audio.musica_activa else "MUSICA: OFF"
        for boton in (getattr(self, "boton_musica", None),
                      getattr(self, "boton_aj_musica", None)):
            if boton is not None:
                boton.etiqueta = etiqueta
        if self.audio.musica_activa:
            self.audio.iniciar_musica()
        else:
            self.audio.pausar_musica()
        self._guardar_preferencias()

    def _volver_al_menu(self) -> None:
        self._crear_menu()
        self._ir(Escena.MENU)
        self.audio.iniciar_musica()

    def _todos_botones_menu(self) -> list[Boton]:
        return ([self.boton_jugar, *self.boton_dificultad, *self.boton_modo,
                 self.boton_instrucciones]
                + [self.boton_records, self.boton_ajustes,
                   self.boton_tienda, self.boton_salir])

    def _manejar_menu(self, evento: pygame.event.Event) -> None:
        if evento.type == pygame.KEYDOWN:
            if evento.key in (pygame.K_LEFT,):
                self._cambiar_dificultad(-1)
                return
            if evento.key in (pygame.K_RIGHT,):
                self._cambiar_dificultad(1)
                return
            if evento.key == pygame.K_t:
                self._cambiar_modo(1)
                return
            if evento.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._empezar_juego()
                return
            if evento.key == pygame.K_m:
                self._alternar_musica()
                return
            if evento.key == pygame.K_i:
                self._ir(Escena.INSTRUCCIONES)
                return
        pos = self._pos_tap(evento)
        if pos is not None:
            for i, boton in enumerate(self.boton_dificultad):
                if boton.rect.collidepoint(pos):
                    dif = list(Dificultad)[i]
                    if dif is not self.dificultad:
                        self.dificultad = dif
                        self._refrescar_dificultad()
                        self._guardar_preferencias()
                    return
            for i, boton in enumerate(self.boton_modo):
                if boton.rect.collidepoint(pos):
                    modo = list(ModoJuego)[i]
                    if modo is not self.modo:
                        self.modo = modo
                        self._refrescar_modo()
                        self._guardar_preferencias()
                    return
        self._manejar_y_botones(evento, self._todos_botones_menu())

    def _dibujar_menu(self, tiempo_ms: int) -> None:
        self.render.fondo(tiempo_ms)

        # Título: bloque grande con doble brillo.
        blit_centrado(self.pantalla, texto_glow("SNAKE", "titulo", (0, 230, 255),
                                                (80, 200, 255)), (500, 105))
        blit_centrado(self.pantalla, texto_glow("GAME", "grande", (255, 0, 200),
                                                (255, 80, 230)), (500, 158))
        blit_centrado(self.pantalla, texto("NEON EDITION", "pequena", (140, 155, 180)),
                      (500, 196))

        # Panel principal con gradiente (dificultad + modo + jugar + fila + tienda).
        self.render.panel(pygame.Rect(150, 228, 700, 392), (0, 230, 255),
                          gradiente=((16, 26, 52), (28, 12, 52)))

        # Selector de dificultad.
        blit_centrado(self.pantalla, texto("DIFICULTAD", "pequena", (120, 135, 160)),
                      (500, 252))
        for boton in self.boton_dificultad:
            boton.dibujar(self.pantalla)

        # Estadísticas de la dificultad seleccionada.
        dif = self.dificultad
        if self.modo is ModoJuego.CONTRARRELOJ:
            stats = (f"TIEMPO {dif.segundos_crono}s  ·  VEL {dif.velocidad}  ·  "
                     f"+{BONUS_MANZANA_SEG}s/MANZANA")
        else:
            stats = (f"VEL {dif.velocidad}  ·  BOMBAS {dif.max_bombas}  ·  "
                     f"FRUTAS/NIVEL {dif.factor_nivel}")
        blit_centrado(self.pantalla, texto(stats, "pequena", (160, 175, 200)), (500, 336))
        record_actual = self.estado.record_para(self.dificultad, self.modo.value)
        blit_centrado(self.pantalla,
                      texto(f"RECORD {self.modo.etiqueta_corta}: {record_actual:04}   ·   "
                            f"MONEDAS: {self.monedas:04}",
                            "media", (255, 214, 60)),
                      (500, 360))

        # Selector de modo.
        blit_centrado(self.pantalla,
                      texto(f"MODO  ·  {self.modo.descripcion.upper()}",
                            "pequena", (120, 135, 160)),
                      (500, 382))
        for boton in self.boton_modo:
            boton.dibujar(self.pantalla)

        self.boton_jugar.dibujar(self.pantalla)
        for boton in (self.boton_instrucciones, self.boton_records, self.boton_ajustes):
            boton.dibujar(self.pantalla)
        self.boton_tienda.dibujar(self.pantalla)
        self.boton_salir.dibujar(self.pantalla)

        blit_centrado(self.pantalla,
                      texto("<- -> DIFICULTAD   T MODO   ENTER JUGAR   M MUSICA",
                            "pequena", (110, 125, 150)), (500, 684))
        pinchar_creditos(self.pantalla, CREDITO, f"v{__paquete_version__}")
