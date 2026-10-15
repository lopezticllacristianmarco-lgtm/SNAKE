"""Rendering of the playing field, snake, food, bombs, particles and HUD.

All drawing is derived from the *model*; the renderer never mutates game
state, and every animation is procedural (no external sprites required).
The optional ``fondo.png`` is blended on top of a procedural nebula starfield.
"""

from __future__ import annotations

import math
import random

import pygame

from snake_game.config import (
    ALTO,
    ANCHO,
    AREA_DE_JUEGO,
    FONDO_RUTA,
    TAMANO_CELDA,
    Colores,
    color_arcoiris,
    colores_skin,
    es_skin_animada,
    skin_valida,
)
from snake_game.core.modelos import ModeloSnake
from snake_game.ui.graficos import blit_centrado, texto


def _grado(color_a: tuple[int, int, int], color_b: tuple[int, int, int],
           t: float) -> tuple[int, int, int]:
    """Linear interpolation (0..1) between two colours."""
    return tuple(int(a + (b - a) * t) for a, b in zip(color_a, color_b, strict=False))


class Renderizador:
    """Neon renderer for every game screen."""

    def __init__(self, pantalla: pygame.Surface) -> None:
        self.pantalla = pantalla
        self.fondo_cargado: pygame.Surface | None = None
        self.estrellas: list[tuple[int, int, int]] = self._crear_estrellas()
        self._cache_panel: dict[tuple, pygame.Surface] = {}
        self._intentar_cargar_fondo()

    # ------------------------------------------------------------------
    # Background
    # ------------------------------------------------------------------
    def _crear_estrellas(self, cuantas: int = 140) -> list[tuple[int, int, int]]:
        rng = random.Random(42)  # deterministic starfield
        return [(rng.randint(0, ANCHO), rng.randint(0, ALTO),
                 rng.randint(1, 3)) for _ in range(cuantas)]

    def _intentar_cargar_fondo(self) -> None:
        if not FONDO_RUTA.exists():
            return
        try:
            imagen = pygame.image.load(str(FONDO_RUTA)).convert()
            self.fondo_cargado = pygame.transform.scale(imagen, (ANCHO, ALTO))
        except (pygame.error, OSError) as exc:
            print(f"No se pudo cargar {FONDO_RUTA}: {exc}")

    def fondo(self, tiempo_ms: int, con_estrellas: bool = True) -> None:
        """Procedural cyan nebula + drifting stars (or the blendable image)."""
        self.pantalla.fill(Colores.FONDO)
        for i, (sx, sy, sr) in enumerate(self.estrellas):
            brillo = 90 + 60 * math.sin(tiempo_ms / 900 + i)
            color = (
                max(0, min(255, int(60 + brillo))),
                max(0, min(255, int(90 + brillo))),
                max(0, min(255, int(120 + brillo))),
            )
            if con_estrellas:
                pygame.draw.circle(self.pantalla, color, (sx, sy), sr)
        if self.fondo_cargado is not None:
            self.fondo_cargado.set_alpha(150)
            self.pantalla.blit(self.fondo_cargado, (0, 0))

    # ------------------------------------------------------------------
    # Static chrome (panels, board, controls) — drawn before each frame
    # ------------------------------------------------------------------
    def panel(self, rect: pygame.Rect, color: tuple[int, int, int],
              gradiente: tuple[tuple[int, int, int], tuple[int, int, int]] | None = None) -> None:
        """Draw a rounded panel, optionally with a vertical gradient fill.

        El relleno con gradiente se cachea por (w, h, colores) porque
        redibujarlo línea a línea cada frame a 60fps es muy costoso.
        """
        if gradiente is None:
            pygame.draw.rect(self.pantalla, Colores.PANEL, rect, border_radius=16)
        else:
            clave = (rect.width, rect.height, gradiente[0], gradiente[1])
            superficie = self._cache_panel.get(clave)
            if superficie is None:
                superficie = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                base_a, base_b = gradiente
                for y in range(rect.height):
                    t = y / max(rect.height - 1, 1)
                    color_grad = _grado(base_a, base_b, t)
                    pygame.draw.line(superficie, color_grad, (2, y), (rect.width - 2, y))
                # Esquinas redondeadas: máscara simple recortando el borde.
                mascara = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                pygame.draw.rect(mascara, (255, 255, 255, 255),
                                 mascara.get_rect(), border_radius=16)
                superficie.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
                self._cache_panel[clave] = superficie
            self.pantalla.blit(superficie, rect.topleft)
        pygame.draw.rect(self.pantalla, color, rect, width=3, border_radius=16)

    def marco_juego(self) -> None:
        min_x, min_y, max_x, max_y = AREA_DE_JUEGO
        # La celda ocupa [origen, origen + TAMANO_CELDA): el borde jugable
        # real termina una celda mas alla del ultimo origen.
        x0, y0 = min_x, min_y
        x1, y1 = max_x + TAMANO_CELDA, max_y + TAMANO_CELDA
        margen = 14
        area = pygame.Rect(x0 - margen, y0 - margen,
                           (x1 - x0) + 2 * margen, (y1 - y0) + 2 * margen)
        # Relleno interior para que se vea claramente donde se puede jugar.
        interior = pygame.Rect(x0, y0, x1 - x0, y1 - y0)
        pygame.draw.rect(self.pantalla, (10, 18, 36), interior)
        pygame.draw.rect(self.pantalla, Colores.CYAN, area, width=2, border_radius=8)
        pygame.draw.rect(self.pantalla, (0, 100, 100), area.inflate(-4, -4),
                         width=1, border_radius=8)
        for gx in range(x0, x1 + 1, TAMANO_CELDA):
            pygame.draw.line(self.pantalla, (20, 30, 40),
                             (gx, y0), (gx, y1))
        for gy in range(y0, y1 + 1, TAMANO_CELDA):
            pygame.draw.line(self.pantalla, (20, 30, 40),
                             (x0, gy), (x1, gy))

    def panel_controles(self, dificultad: str, nivel: int, frutos_restantes: int) -> None:
        self.panel(pygame.Rect(830, 120, 150, 380), Colores.ROSA)

        blit_centrado(self.pantalla, texto("TOCA PARA MOVER", "pequena", Colores.CYAN), (905, 177))
        # Flechas grandes, espaciadas y táctiles, dentro del panel derecho.
        flechas = [
            (pygame.Rect(884, 214, 42, 42), "↑", Colores.CYAN),
            (pygame.Rect(834, 260, 42, 42), "←", Colores.ROSA),
            (pygame.Rect(884, 260, 42, 42), "↓", Colores.CYAN),
            (pygame.Rect(934, 260, 42, 42), "→", Colores.ROSA),
        ]
        for rect, simbolo, color in flechas:
            pygame.draw.rect(self.pantalla, Colores.PANEL, rect, border_radius=9)
            pygame.draw.rect(self.pantalla, color, rect, width=3, border_radius=9)
            blit_centrado(self.pantalla, texto(simbolo, "media", Colores.BLANCO), rect.center)
        blit_centrado(self.pantalla, texto("DESLIZA TAMBIEN", "pequena", Colores.GRIS), (905, 325))
        blit_centrado(self.pantalla, texto("ESC = MENU", "pequena", Colores.GRIS), (905, 360))
        blit_centrado(self.pantalla, texto("M = SONIDO", "pequena", Colores.GRIS), (905, 385))
        blit_centrado(self.pantalla, texto("DIFICULTAD", "pequena", Colores.GRIS), (905, 420))
        blit_centrado(self.pantalla, texto(dificultad.upper(), "media", Colores.AMARILLO), (905, 448))
        blit_centrado(self.pantalla, texto(f"NIVEL {nivel}", "media", Colores.ROSA), (905, 478))

    # ------------------------------------------------------------------
    # Entities
    # ------------------------------------------------------------------
    def _hud(self, modelo: ModeloSnake, record: int) -> None:
        if modelo.modo == "Contrarreloj" and modelo.tiempo_limite:
            seg = (modelo.tiempo_restante + max(modelo.velocidad_base, 1) - 1) \
                // max(modelo.velocidad_base, 1)
            titulo = f"CRONO {seg:02}s"
            color_titulo = Colores.AMARILLO
        elif modelo.modo == "Zen":
            titulo, color_titulo = "JUGANDO · ZEN", Colores.VERDE
        elif modelo.modo == "Laberinto":
            titulo, color_titulo = "JUGANDO · LABERINTO", Colores.MORADO
        else:
            titulo, color_titulo = "JUGANDO", Colores.CYAN
        blit_centrado(self.pantalla, texto(titulo, "grande", color_titulo), (425, 42))
        blit_centrado(self.pantalla, texto(f"PUNTOS {modelo.puntaje:03}", "media", Colores.BLANCO), (250, 25))
        blit_centrado(self.pantalla, texto(f"NIVEL {modelo.nivel}", "media", Colores.ROSA), (425, 25))
        blit_centrado(self.pantalla, texto(f"RECORD {record:03}", "media", Colores.AMARILLO), (660, 25))
        blit_centrado(self.pantalla, texto(f"MONEDAS +{getattr(modelo, 'monedas', 0):03}",
                                           "media", Colores.AMARILLO), (110, 52))
        prog = modelo.factor_nivel - modelo.frutos
        blit_centrado(self.pantalla, texto(f"PROX NIVEL: {prog}", "pequena", Colores.GRIS), (620, 52))
        # Efectos activos.
        y_ef = 70
        if modelo.modo == "Laberinto" and modelo.laberinto_cada > 0:
            base = max(modelo.velocidad_base, 1)
            seg = (modelo.tiempo_hasta_laberinto + base - 1) // base
            blit_centrado(self.pantalla,
                          texto(f"MUROS {seg:02}s", "pequena", Colores.MORADO),
                          (250, y_ef))
            y_ef += 16
        if modelo.escudo_ticks > 0:
            blit_centrado(self.pantalla,
                          texto(f"ESCUDO {modelo.escudo_ticks // 10 + 1}s", "pequena", Colores.CYAN),
                          (250, y_ef))
            y_ef += 16
        if modelo.lento_ticks > 0:
            blit_centrado(self.pantalla,
                          texto(f"LENTO {modelo.lento_ticks // 10 + 1}s", "pequena", Colores.MORADO),
                          (250, y_ef))

    def dibujar_serpiente(self, modelo: ModeloSnake, tiempo_ms: int = 0) -> None:
        skin = skin_valida(getattr(modelo, "skin", "neon"))
        animada = es_skin_animada(skin)
        principal, oscuro = colores_skin(skin)
        serpiente = modelo.serpiente
        largo = len(serpiente)
        for i, (bx, by) in enumerate(serpiente):
            if i == 0:
                pygame.draw.rect(self.pantalla, (120, 255, 255),
                                 (bx - 3, by - 3, 31, 31), border_radius=10, width=3)
            if animada:
                # LED arcoíris: la onda recorre el cuerpo (cabeza = tiempo actual,
                # cada segmento atrasa ~1/12 de vuelta) y además rota con el tiempo.
                color_cuerpo = color_arcoiris(tiempo_ms, desplazamiento=-i / 12.0)
            else:
                progreso = i / max(largo - 1, 1)
                color_cuerpo = (
                    int(principal[0] * (1 - progreso) + oscuro[0] * progreso),
                    int(principal[1] * (1 - progreso) + oscuro[1] * progreso),
                    int(principal[2] * (1 - progreso) + oscuro[2] * progreso),
                )
            pygame.draw.rect(self.pantalla, color_cuerpo, (bx, by, 23, 23), border_radius=8)
            pygame.draw.rect(self.pantalla, (255, 255, 255), (bx + 5, by + 5, 13, 13),
                             border_radius=5, width=1)

        cabeza_x, cabeza_y = modelo.cabeza()
        dx, dy = modelo.direccion
        if dx > 0:
            pygame.draw.circle(self.pantalla, Colores.NEGRO, (cabeza_x + 18, cabeza_y + 7), 3)
            pygame.draw.circle(self.pantalla, Colores.NEGRO, (cabeza_x + 18, cabeza_y + 18), 3)
            pygame.draw.line(self.pantalla, Colores.ROSA, (cabeza_x + 23, cabeza_y + 12),
                             (cabeza_x + 30, cabeza_y + 12), 2)
        elif dx < 0:
            pygame.draw.circle(self.pantalla, Colores.NEGRO, (cabeza_x + 6, cabeza_y + 7), 3)
            pygame.draw.circle(self.pantalla, Colores.NEGRO, (cabeza_x + 6, cabeza_y + 18), 3)
            pygame.draw.line(self.pantalla, Colores.ROSA, (cabeza_x, cabeza_y + 12),
                             (cabeza_x - 7, cabeza_y + 12), 2)
        elif dy > 0:
            pygame.draw.circle(self.pantalla, Colores.NEGRO, (cabeza_x + 7, cabeza_y + 18), 3)
            pygame.draw.circle(self.pantalla, Colores.NEGRO, (cabeza_x + 18, cabeza_y + 18), 3)
            pygame.draw.line(self.pantalla, Colores.ROSA, (cabeza_x + 12, cabeza_y + 23),
                             (cabeza_x + 12, cabeza_y + 30), 2)
        else:
            pygame.draw.circle(self.pantalla, Colores.NEGRO, (cabeza_x + 7, cabeza_y + 6), 3)
            pygame.draw.circle(self.pantalla, Colores.NEGRO, (cabeza_x + 18, cabeza_y + 6), 3)
            pygame.draw.line(self.pantalla, Colores.ROSA, (cabeza_x + 12, cabeza_y),
                             (cabeza_x + 12, cabeza_y - 7), 2)

    def dibujar_comida(self, modelo: ModeloSnake, tiempo_ms: int) -> None:
        if modelo.comida is None:
            return
        cx, cy = modelo.comida.posicion
        pulso = (math.sin(tiempo_ms / 240) + 1) / 2  # 0..1
        # Centro exacto de la celda para que la manzana quede alineada con
        # la cuadricula (medio pixel arriba/izquierda de lo anterior).
        radio = int(11 + 1.5 * pulso)
        centro = (cx + 12, cy + 12)
        pygame.draw.circle(self.pantalla, (255, 60, 90), centro, radio + 3)
        pygame.draw.circle(self.pantalla, Colores.ROJO, centro, radio)
        pygame.draw.circle(self.pantalla, Colores.ROJO_CLARO, centro, 4)
        pygame.draw.circle(self.pantalla, Colores.ROSA, centro, radio + 2, 2)

    def dibujar_bombas(self, modelo: ModeloSnake) -> None:
        for bomba in modelo.bombas:
            if not bomba.activa:
                continue
            if bomba.en_destello:
                continue
            bx, by, r = bomba.x, bomba.y, 10
            pygame.draw.circle(self.pantalla, (255, 150, 50), (bx + 12, by + 12), r + 5, 2)
            pygame.draw.circle(self.pantalla, Colores.NARANJA, (bx + 12, by + 12), r)
            pygame.draw.circle(self.pantalla, (255, 200, 100), (bx + 10, by + 10), 4)
            pygame.draw.line(self.pantalla, Colores.GRIS, (bx + 12, by + 2), (bx + 12, by - 5), 2)
            pygame.draw.circle(self.pantalla, Colores.ROJO, (bx + 12, by - 5), 3)

    def dibujar_obstaculos(self, modelo: ModeloSnake) -> None:
        """Muros internos del modo Laberinto."""
        self.dibujar_muros(modelo.obstaculos)

    def dibujar_muros(self, muros: list) -> None:
        """Muros internos (acepta lista de [x, y] o tuplas)."""
        for muro in muros:
            ox, oy = muro
            pygame.draw.rect(self.pantalla, (30, 16, 55), (ox, oy, 23, 23),
                             border_radius=6)
            pygame.draw.rect(self.pantalla, Colores.MORADO, (ox, oy, 23, 23),
                             width=2, border_radius=6)
            pygame.draw.circle(self.pantalla, (90, 50, 140), (ox + 11, oy + 11), 3)

    def dibujar_particulas(self, modelo: ModeloSnake) -> None:
        for p in modelo.particulas:
            pygame.draw.circle(self.pantalla, p.color, (int(p.x), int(p.y)), p.radio)

    def dibujar_powerups(self, modelo: ModeloSnake, tiempo_ms: int) -> None:
        from snake_game.ui.graficos import texto as _texto
        colores = {"dorada": Colores.AMARILLO, "escudo": Colores.CYAN,
                   "lento": Colores.MORADO}
        letras = {"dorada": "$", "escudo": "E", "lento": "S"}
        for pu in modelo.powerups:
            if not pu.activa:
                continue
            # Parpadeo cuando está por expirar.
            if pu.tiempo_vida < 60 and (tiempo_ms // 150) % 2 == 0:
                continue
            color = colores.get(pu.tipo, Colores.BLANCO)
            cx, cy = pu.x + 12, pu.y + 12
            pulso = (math.sin(tiempo_ms / 240) + 1) / 2
            radio = int(10 + 1.5 * pulso)
            # Rombo exterior + círculo interior + letra.
            pygame.draw.polygon(self.pantalla, color,
                                [(cx, cy - radio - 3), (cx + radio + 3, cy),
                                 (cx, cy + radio + 3), (cx - radio - 3, cy)], 2)
            pygame.draw.circle(self.pantalla, color, (cx, cy), radio)
            pygame.draw.circle(self.pantalla, Colores.NEGRO, (cx, cy), radio - 3)
            etiqueta = _texto(letras.get(pu.tipo, "?"), "normal", color)
            self.pantalla.blit(etiqueta, etiqueta.get_rect(center=(cx, cy)))

    # ------------------------------------------------------------------
    # Whole-frame composition
    # ------------------------------------------------------------------
    def dibujar_partida(self, modelo: ModeloSnake, record: int, tiempo_ms: int,
                        dificultad: str) -> None:
        self.fondo(tiempo_ms)
        self.marco_juego()
        self.dibujar_obstaculos(modelo)
        self.dibujar_serpiente(modelo, tiempo_ms)
        self.dibujar_comida(modelo, tiempo_ms)
        self.dibujar_bombas(modelo)
        self.dibujar_powerups(modelo, tiempo_ms)
        self.dibujar_particulas(modelo)
        self._hud(modelo, record)
        self.panel_controles(dificultad, modelo.nivel, modelo.frutos_restantes_para_nivel())
