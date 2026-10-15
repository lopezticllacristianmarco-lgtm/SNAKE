"""Escena de ajustes: volúmenes, pantalla completa y teclas."""

from __future__ import annotations

import pygame

from snake_game.escenas.base import BaseEscena, Escena
from snake_game.ui.graficos import (
    Boton,
    blit_centrado,
    texto,
    texto_glow,
)

ACCIONES_AJUSTES = (
    ("arriba", "ARRIBA"),
    ("abajo", "ABAJO"),
    ("izq", "IZQ"),
    ("der", "DER"),
    ("pausa", "PAUSA"),
)


class AjustesMixin(BaseEscena):
    def _abrir_ajustes(self) -> None:
        self.ajuste_captura = None
        self.ajuste_nombre_editando = False
        self.ajuste_musica_mensaje = ""
        self._crear_ajustes()
        self._ir(Escena.AJUSTES)

    def _crear_ajustes(self) -> None:
        """Reconstruye los widgets (las etiquetas dependen de los valores)."""
        self.boton_aj_mus_menos = Boton((440, 190), 54, 44, "-", "opcion",
                                        lambda: self._cambiar_volumen("musica", -0.1))
        self.boton_aj_mus_mas = Boton((590, 190), 54, 44, "+", "opcion",
                                      lambda: self._cambiar_volumen("musica", 0.1))
        etiqueta_mus = "ON" if self.audio.musica_activa else "OFF"
        self.boton_aj_musica = Boton((690, 190), 100, 44, etiqueta_mus, "opcion",
                                     self._alternar_musica, fuente_tamano="normal")
        self.boton_aj_ef_menos = Boton((440, 250), 54, 44, "-", "opcion",
                                       lambda: self._cambiar_volumen("efectos", -0.1))
        self.boton_aj_ef_mas = Boton((590, 250), 54, 44, "+", "opcion",
                                     lambda: self._cambiar_volumen("efectos", 0.1))
        self.boton_aj_teclas: list[Boton] = []
        for i, (accion, nombre) in enumerate(ACCIONES_AJUSTES):
            cx = 236 + i * 132
            tecla = self._nombre_tecla(self.teclas.get(accion, 0))
            self.boton_aj_teclas.append(
                Boton((cx, 344), 124, 42, f"{nombre}:{tecla}", "opcion",
                      lambda acc=accion: self._empezar_captura(acc),
                      fuente_tamano="pequena")
            )
        # Música del dispositivo: ciclar (< >), elegir archivo o volver a original.
        self.boton_mus_ant = Boton((360, 548), 54, 40, "<", "opcion",
                                   lambda: self._cambiar_cancion(-1))
        self.boton_mus_sig = Boton((428, 548), 54, 40, ">", "opcion",
                                   lambda: self._cambiar_cancion(1))
        self.boton_mus_archivo = Boton((570, 548), 170, 40, "ELEGIR...",
                                       "secundario", self._elegir_archivo_musica,
                                       fuente_tamano="normal")
        self.boton_mus_original = Boton((745, 548), 110, 40, "ORIGINAL",
                                        "opcion", self._restaurar_musica,
                                        fuente_tamano="pequena")

    def _botones_ajustes(self) -> list[Boton]:
        return [self.boton_aj_mus_menos, self.boton_aj_mus_mas,
                self.boton_aj_musica, self.boton_aj_ef_menos,
                self.boton_aj_ef_mas, *self.boton_aj_teclas,
                self.boton_mus_ant, self.boton_mus_sig,
                self.boton_mus_archivo, self.boton_mus_original,
                self._boton_volver]

    # -- música del dispositivo --------------------------------------
    def _canciones_disponibles(self) -> list[str]:
        """[""] (=ORIGINAL) + rutas encontradas en el dispositivo."""
        from snake_game.audio import buscar_canciones
        try:
            return [""] + [str(p) for p in buscar_canciones()]
        except OSError:
            return [""]

    def _nombre_musica_actual(self) -> str:
        from snake_game.audio import nombre_cancion
        custom = (self.audio.musica_custom or "").strip()
        if not custom:
            return "ORIGINAL"
        from pathlib import Path
        nombre = nombre_cancion(custom)
        return nombre if Path(custom).is_file() else f"{nombre} (FALTA)"

    def _cambiar_cancion(self, direccion: int) -> None:
        opciones = self._canciones_disponibles()
        actual = (self.audio.musica_custom or "").strip()
        try:
            i = opciones.index(actual)
        except ValueError:
            i = 0 if direccion > 0 else len(opciones) - 1
            self._usar_musica(opciones[i] if opciones else "")
            return
        self._usar_musica(opciones[(i + direccion) % len(opciones)])

    def _usar_musica(self, ruta: str) -> None:
        if not ruta:
            self.audio.definir_musica("")
            self.ajuste_musica_mensaje = ""
        elif self.audio.definir_musica(ruta):
            self.ajuste_musica_mensaje = ""
        else:
            self.ajuste_musica_mensaje = "NO SE PUDO USAR ESE ARCHIVO."
            self.audio.reproducir("bomba", 0.4)
            return
        self._guardar_preferencias()
        self.audio.reproducir("comer", 0.5)

    def _restaurar_musica(self) -> None:
        self._usar_musica("")

    def _elegir_archivo_musica(self) -> None:
        """Selector de archivo (PC) o guía de carpeta Music (móvil)."""
        import os
        if "ANDROID_ARGUMENT" in os.environ:
            n = len(self._canciones_disponibles()) - 1
            if n > 0:
                self.ajuste_musica_mensaje = f"HAY {n} EN MUSIC/DOWNLOAD: USA < > PARA ELEGIR."
            else:
                self.ajuste_musica_mensaje = "COPIA UN MP3 A LA CARPETA MUSIC Y PULSA < >."
            return
        try:
            import tkinter as tk
            from tkinter import filedialog
        except ImportError:
            self.ajuste_musica_mensaje = "COPIA UN MP3 A TU CARPETA DE MUSICA Y USA < >."
            return
        try:
            raiz = tk.Tk()
            raiz.withdraw()
            raiz.attributes("-topmost", True)
            ruta = filedialog.askopenfilename(
                title="Elegir canción",
                filetypes=[("Audio", "*.mp3 *.ogg *.wav"), ("Todos", "*.*")])
            raiz.destroy()
        except Exception:  # noqa: BLE001 - diálogo nativo impredecible
            self.ajuste_musica_mensaje = "NO SE PUDO ABRIR EL SELECTOR."
            return
        if ruta:
            self._usar_musica(ruta)
        self._crear_ajustes()

    # -- valores ------------------------------------------------------
    def _cambiar_volumen(self, cual: str, delta: float) -> None:
        if cual == "musica":
            self.audio.volumen_musica = round(
                min(1.0, max(0.0, self.audio.volumen_musica + delta)), 2)
            self.audio.aplicar_volumen_musica()
        else:
            self.audio.volumen_efectos = round(
                min(1.0, max(0.0, self.audio.volumen_efectos + delta)), 2)
            self.audio.reproducir("comer", 0.6)  # preview del nivel
        self._guardar_preferencias()

    # -- teclas -------------------------------------------------------
    @staticmethod
    def _nombre_tecla(codigo: int) -> str:
        try:
            return pygame.key.name(codigo).upper()
        except (ValueError, AttributeError):
            return "?"

    def _mapa_teclas_juego(self) -> dict:
        """Keycode -> vector, según la configuración del jugador."""
        t = self.teclas
        return {t["arriba"]: (0, -25), t["abajo"]: (0, 25),
                t["izq"]: (-25, 0), t["der"]: (25, 0)}

    def _empezar_captura(self, accion: str) -> None:
        self.ajuste_captura = accion
        self.audio.reproducir("comer", 0.5)

    def _asignar_tecla(self, accion: str, codigo: int) -> None:
        teclas = dict(self.teclas)
        for otra, valor in teclas.items():
            if otra != accion and valor == codigo:
                teclas[otra] = teclas[accion]  # swap: sin duplicados
        teclas[accion] = codigo
        self.teclas = teclas
        self.ajuste_captura = None
        self._guardar_preferencias()
        self.audio.reproducir("ganar", 0.4)
        self._crear_ajustes()

    # -- escena -------------------------------------------------------
    def _manejar_ajustes(self, evento: pygame.event.Event) -> None:
        pos = self._pos_tap(evento)
        if pos is not None:
            if self._caja_nombre().collidepoint(pos):
                self.ajuste_nombre_editando = True
                self.ajuste_captura = None
                return
            if self.ajuste_nombre_editando:
                self._terminar_edicion_nombre()
        if evento.type == pygame.KEYDOWN:
            if self.ajuste_nombre_editando:
                self._teclear_nombre(evento)
                return
            if self.ajuste_captura is not None:
                if evento.key == pygame.K_ESCAPE:
                    self.ajuste_captura = None
                else:
                    self._asignar_tecla(self.ajuste_captura, evento.key)
                return
            if evento.key == pygame.K_ESCAPE:
                self._ir(Escena.MENU)
                return
        self._manejar_y_botones(evento, self._botones_ajustes())

    # -- nombre -------------------------------------------------------
    @staticmethod
    def _caja_nombre() -> pygame.Rect:
        caja = pygame.Rect(0, 0, 240, 44)
        caja.center = (560, 442)
        return caja

    def _teclear_nombre(self, evento: pygame.event.Event) -> None:
        from snake_game.core.guardado import NOMBRE_MAXIMO, normalizar_nombre

        if evento.key in (pygame.K_RETURN, pygame.K_ESCAPE):
            self._terminar_edicion_nombre()
            return
        if evento.key == pygame.K_BACKSPACE:
            self.nombre = self.nombre[:-1]
            return
        if evento.unicode and evento.unicode.isprintable() \
                and len(self.nombre) < NOMBRE_MAXIMO:
            self.nombre = normalizar_nombre(self.nombre + evento.unicode)

    def _terminar_edicion_nombre(self) -> None:
        from snake_game.core.guardado import normalizar_nombre

        self.nombre = normalizar_nombre(self.nombre)
        self.ajuste_nombre_editando = False
        self._guardar_preferencias()
        self.audio.reproducir("comer", 0.5)

    def _dibujar_ajustes(self, _tiempo_ms: int) -> None:
        self.render.fondo(0)
        self.render.panel(pygame.Rect(150, 80, 700, 560), (0, 230, 255),
                          gradiente=((16, 26, 52), (28, 12, 52)))
        blit_centrado(self.pantalla, texto_glow("AJUSTES", "titulo", (0, 230, 255)),
                      (500, 125))

        blit_centrado(self.pantalla, texto("VOL. MUSICA", "normal", (235, 240, 255)),
                      (300, 190))
        self.boton_aj_mus_menos.dibujar(self.pantalla)
        blit_centrado(self.pantalla,
                      texto(f"{int(self.audio.volumen_musica * 100)}%", "media",
                            (255, 214, 60)), (515, 190))
        self.boton_aj_mus_mas.dibujar(self.pantalla)
        self.boton_aj_musica.dibujar(self.pantalla)

        blit_centrado(self.pantalla, texto("VOL. EFECTOS", "normal", (235, 240, 255)),
                      (300, 250))
        self.boton_aj_ef_menos.dibujar(self.pantalla)
        blit_centrado(self.pantalla,
                      texto(f"{int(self.audio.volumen_efectos * 100)}%", "media",
                            (255, 214, 60)), (515, 250))
        self.boton_aj_ef_mas.dibujar(self.pantalla)

        blit_centrado(self.pantalla,
                      texto("TECLAS (FLECHAS SIEMPRE VALEN)", "pequena",
                            (120, 135, 160)), (500, 310))
        for boton in self.boton_aj_teclas:
            boton.dibujar(self.pantalla)

        if self.ajuste_captura is not None:
            nombre = dict(ACCIONES_AJUSTES).get(self.ajuste_captura, "")
            blit_centrado(self.pantalla,
                          texto(f"PULSA TECLA PARA {nombre} (ESC CANCELA)",
                                "media", (255, 214, 60)), (500, 392))
        else:
            blit_centrado(self.pantalla,
                          texto("CLICK EN UNA TECLA Y PULSA LA NUEVA  ·  ESC = MENU",
                                "pequena", (120, 130, 150)), (500, 392))

        # Nombre de jugador (récords).
        blit_centrado(self.pantalla, texto("NOMBRE", "normal", (235, 240, 255)),
                      (330, 442))
        caja = self._caja_nombre()
        pygame.draw.rect(self.pantalla, (10, 16, 34), caja, border_radius=10)
        borde = (0, 230, 255) if self.ajuste_nombre_editando else (88, 98, 118)
        pygame.draw.rect(self.pantalla, borde, caja, width=2, border_radius=10)
        parpadeo = (pygame.time.get_ticks() // 500) % 2 == 0
        cursor = "_" if self.ajuste_nombre_editando and parpadeo else ""
        blit_centrado(self.pantalla,
                      texto(f"{self.nombre}{cursor}" or " ", "media", (235, 240, 255)),
                      caja.center)

        # Canción del dispositivo (mp3/ogg/wav de tu Música/Descargas).
        blit_centrado(self.pantalla,
                      texto("MUSICA DEL DISPOSITIVO", "pequena",
                            (120, 135, 160)), (500, 488))
        blit_centrado(self.pantalla,
                      texto(f"♪ {self._nombre_musica_actual()}", "media",
                            (255, 214, 60)), (500, 514))
        self.boton_mus_ant.dibujar(self.pantalla)
        self.boton_mus_sig.dibujar(self.pantalla)
        self.boton_mus_archivo.dibujar(self.pantalla)
        self.boton_mus_original.dibujar(self.pantalla)
        if getattr(self, "ajuste_musica_mensaje", ""):
            blit_centrado(self.pantalla, texto(self.ajuste_musica_mensaje, "pequena",
                                               (255, 150, 50)), (500, 580))
        self._boton_volver.dibujar(self.pantalla)
