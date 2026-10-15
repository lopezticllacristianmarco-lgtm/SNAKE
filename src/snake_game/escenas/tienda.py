"""Tienda de skins: se compran con las monedas ganadas en los niveles.

Las monedas se conservan aunque pierdas la partida (se suman al terminar).
"""

from __future__ import annotations

import pygame

from snake_game import __version__ as __paquete_version__
from snake_game.config import (
    SKINS,
    color_arcoiris,
    colores_skin,
    es_skin_animada,
    skin_valida,
)
from snake_game.escenas.base import CREDITO, BaseEscena, Escena
from snake_game.ui.graficos import (
    Boton,
    blit_centrado,
    pinchar_creditos,
    texto,
    texto_glow,
)


def _columnas_tienda() -> int:
    """3 columnas hasta 6 skins; 4 cuando hay más (ej. la legendaria)."""
    return 3 if len(SKINS) <= 6 else 4


def _posicion_skin(i: int) -> tuple[int, int]:
    """Centro (cx, cy) de la tarjeta i en el panel 150..850."""
    cols = _columnas_tienda()
    fila = i // cols
    col = i % cols
    if cols == 3:
        return (300 + col * 200, 330 + fila * 150)
    return (245 + col * 170, 330 + fila * 150)


class TiendaMixin(BaseEscena):
    def _crear_tienda(self) -> None:
        """Reconstruye los botones según monedas/skins actuales."""
        self._botones_tienda_accion: list[Boton] = []
        for i, skin_id in enumerate(SKINS):
            cx, cy = _posicion_skin(i)
            self._botones_tienda_accion.append(
                Boton((cx, cy + 42), 140, 38, "...", "opcion",
                      lambda s=skin_id: self._comprar_o_equipar(s),
                      fuente_tamano="pequena")
            )
        self._refrescar_tienda()
        self.boton_tienda_volver = Boton((500, 620), 200, 48, "VOLVER",
                                         "secundario",
                                         lambda: self._ir(Escena.MENU))

    def _refrescar_tienda(self) -> None:
        """Etiquetas COMPRAR/EQUIPADO/ACTIVA según estado."""
        for boton, skin_id in zip(self._botones_tienda_accion, SKINS, strict=True):
            nombre, precio, _, _ = SKINS[skin_id]
            if skin_id == self.skin_activa:
                boton.etiqueta = "ACTIVA"
                boton.estilo = {"relleno": (10, 48, 26), "borde": (60, 255, 160),
                                "texto": (235, 240, 255), "hover_relleno": (10, 48, 26),
                                "radio": 8}
            elif skin_id in self.skins:
                boton.etiqueta = "EQUIPAR"
                boton.estilo = {"relleno": (10, 48, 60), "borde": (0, 230, 255),
                                "texto": (235, 240, 255), "hover_relleno": (16, 60, 80),
                                "radio": 8}
            else:
                boton.etiqueta = f"${precio}"
                boton.estilo = {"relleno": (40, 32, 10), "borde": (255, 214, 60),
                                "texto": (255, 214, 60), "hover_relleno": (60, 46, 14),
                                "radio": 8}

    def _comprar_o_equipar(self, skin_id: str) -> None:
        skin_id = skin_valida(skin_id)
        _, precio, _, _ = SKINS[skin_id]
        if skin_id == self.skin_activa:
            return
        if skin_id in self.skins:
            self.skin_activa = skin_id
            self.audio.reproducir("comer", 0.5)
        elif self.monedas >= precio:
            self.monedas -= precio
            self.skins = sorted(set(self.skins) | {skin_id}, key=list(SKINS).index)
            self.skin_activa = skin_id
            self.audio.reproducir("ganar", 0.6)
        else:
            self.tienda_mensaje = f"TE FALTAN {precio - self.monedas} MONEDAS. JUEGA NIVELES PARA GANAR MAS."
            self.audio.reproducir("bomba", 0.4)
            return
        self.tienda_mensaje = ""
        self._refrescar_tienda()
        self._guardar_preferencias()

    def _abrir_tienda(self) -> None:
        self.tienda_mensaje = ""
        self._crear_tienda()
        self._ir(Escena.TIENDA)

    def _manejar_tienda(self, evento: pygame.event.Event) -> None:
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            self._ir(Escena.MENU)
            return
        self._manejar_y_botones(evento, [*self._botones_tienda_accion,
                                         self.boton_tienda_volver])

    def _dibujar_tienda(self, tiempo_ms: int) -> None:
        self.render.fondo(tiempo_ms)
        self.render.panel(pygame.Rect(150, 60, 700, 560), (255, 214, 60),
                          gradiente=((16, 26, 52), (52, 40, 12)))
        blit_centrado(self.pantalla, texto_glow("TIENDA DE SKINS", "titulo",
                                                (255, 214, 60)), (500, 105))
        blit_centrado(self.pantalla,
                      texto(f"MONEDAS: {self.monedas:04}  ·  GANA 1 POR MANZANA, 5 DORADA, 5 POR NIVEL",
                            "media", (255, 214, 60)), (500, 158))
        blit_centrado(self.pantalla,
                      texto("LAS MONEDAS SE CONSERVAN AUNQUE PIERDAS  ·  LED = ANIMADA",
                            "pequena", (120, 130, 150)), (500, 188))
        for i, skin_id in enumerate(SKINS):
            nombre, precio, _, _ = SKINS[skin_id]
            cx, cy = _posicion_skin(i)
            animada = es_skin_animada(skin_id)
            if animada:
                principal = color_arcoiris(tiempo_ms)
                oscuro = color_arcoiris(tiempo_ms, 0.5)
            else:
                principal, oscuro = colores_skin(skin_id)
            # Tarjeta de la skin (dorada si es legendaria).
            tarjeta = pygame.Rect(0, 0, 160, 120)
            tarjeta.center = (cx, cy)
            pygame.draw.rect(self.pantalla, (10, 16, 34), tarjeta, border_radius=12)
            if skin_id == self.skin_activa:
                borde = (60, 255, 160)
            elif animada:
                borde = color_arcoiris(tiempo_ms, 0.25)
            else:
                borde = (58, 68, 88)
            pygame.draw.rect(self.pantalla, borde, tarjeta, width=2, border_radius=12)
            # Mini serpiente de muestra: la legendaria se anima como LED.
            for k in range(3):
                if animada:
                    c = color_arcoiris(tiempo_ms, desplazamiento=-k / 12.0)
                else:
                    t = k / 2
                    c = (int(principal[0] * (1 - t) + oscuro[0] * t),
                         int(principal[1] * (1 - t) + oscuro[1] * t),
                         int(principal[2] * (1 - t) + oscuro[2] * t))
                pygame.draw.rect(self.pantalla, c,
                                 (cx - 45 + k * 30, cy - 28, 26, 26), border_radius=8)
            blit_centrado(self.pantalla, texto(nombre, "media", (235, 240, 255)),
                          (cx, cy + 8))
            if animada:
                estado = ("DESBLOQUEADA · LED" if skin_id in self.skins
                          else f"BLOQUEADA · ${precio} · LED")
            else:
                estado = ("DESBLOQUEADA" if skin_id in self.skins
                          else f"BLOQUEADA · ${precio}")
            blit_centrado(self.pantalla, texto(estado, "pequena", (120, 130, 150)),
                          (cx, cy + 28))
        for boton in self._botones_tienda_accion:
            boton.dibujar(self.pantalla)
        if getattr(self, "tienda_mensaje", ""):
            blit_centrado(self.pantalla, texto(self.tienda_mensaje, "pequena",
                                               (255, 45, 85)), (500, 580))
        self.boton_tienda_volver.dibujar(self.pantalla)
        pinchar_creditos(self.pantalla, CREDITO, f"v{__paquete_version__}")
