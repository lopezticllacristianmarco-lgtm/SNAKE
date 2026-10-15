"""Game rules — pure Python, deterministic when given a seed.

This module knows **nothing** about pygame. Every rule that made the
original ``SNAKE.py`` logic live inside the game loop (collision, growth,
bombs, particles, levelling) lives here, where it can be unit-tested.
"""

from __future__ import annotations

import random

from snake_game.config import (
    AREA_DE_JUEGO,
    BONUS_DORADA_SEG,
    BONUS_MANZANA_SEG,
    MONEDA_POR_DORADA,
    MONEDA_POR_MANZANA,
    MONEDA_POR_NIVEL,
    TAMANO_CELDA,
    TIEMPO_MAX_CRONO_SEG,
    Dificultad,
    ModoJuego,
)
from snake_game.core.modelos import Bomba, Comida, ModeloSnake, Particula, PowerUp, Vector

# Efectos de power-ups (en ticks de simulación).
DURACION_ESCUDO = 150
DURACION_LENTO = 150
VIDA_POWERUP = 300
RANGO_POWERUP = (250, 500)
TIPOS_POWERUP = ("dorada", "escudo", "lento")


def muros_laberinto(variante: int = 0) -> list[Vector]:
    """Trazado base del laberinto (sin filtrar): 3 variantes con huecos."""
    min_x, min_y, max_x, max_y = AREA_DE_JUEGO
    muros: list[Vector] = []
    if variante == 1:
        # Espejo: vertical a la izquierda + horizontal arriba.
        for y in range(min_y + 50, max_y - 50 + 1, TAMANO_CELDA):
            if y not in (325, 350, 375):
                muros.append((275, y))
        for x in range(min_x + 50, max_x - 50 + 1, TAMANO_CELDA):
            if x not in (375, 400, 425):
                muros.append((x, 250))
    elif variante == 2:
        # Doble horizontal con huecos en lados opuestos.
        for x in range(min_x + 50, max_x - 50 + 1, TAMANO_CELDA):
            if x not in (550, 575, 600):
                muros.append((x, 225))
        for x in range(min_x + 50, max_x - 50 + 1, TAMANO_CELDA):
            if x not in (150, 175, 200):
                muros.append((x, 525))
    else:
        # Muro vertical con hueco en la fila de aparición (y=350).
        for y in range(min_y + 50, max_y - 50 + 1, TAMANO_CELDA):
            if y not in (325, 350, 375):
                muros.append((525, y))
        # Muro horizontal con hueco central.
        for x in range(min_x + 50, max_x - 50 + 1, TAMANO_CELDA):
            if x not in (375, 400, 425):
                muros.append((x, 475))
    return muros


class Logica:
    """Builds and advances a :class:`ModeloSnake`.

    ``rng`` can be seeded to make runs reproducible for tests.
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.posiciones_tablero: list[Vector] = []
        self._reconstruir_posiciones()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def _reconstruir_posiciones(self) -> None:
        min_x, min_y, max_x, max_y = AREA_DE_JUEGO
        self.posiciones_tablero = [
            (px, py)
            for py in range(min_y, max_y + 1, TAMANO_CELDA)
            for px in range(min_x, max_x + 1, TAMANO_CELDA)
        ]

    def iniciar_partida(self, dificultad: Dificultad = Dificultad.NORMAL,
                          modo: ModoJuego | str = ModoJuego.CLASICO) -> ModeloSnake:
        """Create a fresh match for the given difficulty and mode."""
        if isinstance(modo, str):
            modo = ModoJuego.por_nombre(modo)
        modelo = ModeloSnake(
            dificultad=dificultad.value,
            velocidad=dificultad.velocidad,
            velocidad_base=dificultad.velocidad,
            factor_nivel=dificultad.factor_nivel,
            vida_bomba=dificultad.vida_bomba,
            max_bombas=dificultad.max_bombas,
            rango_bomba=dificultad.rango_bomba,
            modo=modo.value,
        )
        if modo is ModoJuego.LABERINTO:
            modelo.obstaculos = self._generar_laberinto(modelo, variante=0)
            modelo.laberinto_cada = dificultad.segundos_laberinto * dificultad.velocidad
            modelo.tiempo_hasta_laberinto = modelo.laberinto_cada
            modelo.laberinto_variante = 0
        if modo is ModoJuego.CONTRARRELOJ:
            modelo.tiempo_limite = dificultad.segundos_crono * dificultad.velocidad
            modelo.tiempo_restante = modelo.tiempo_limite
        modelo.frutos = 0
        modelo.frutos_para_nivel = dificultad.factor_nivel
        modelo.comida = self.generar_comida(modelo)
        modelo.partida_activa = True
        modelo.game_over = False
        modelo.gano = False
        return modelo

    def _generar_laberinto(self, modelo: ModeloSnake | None = None,
                           variante: int = 0) -> list[Vector]:
        """Muros internos fijos con huecos; nunca cubren la aparición.

        Hay 3 variantes que rotan solas durante la partida. Al regenerar,
        se respeta lo ocupado (serpiente, comida, bombas, power-ups) para
        no matar ni enterrar nada de forma injusta.
        """
        muros = muros_laberinto(variante)
        # Evita la zona de aparición por seguridad.
        prohibida = {(400, 350), (375, 350), (350, 350), (425, 350)}
        if modelo is not None:
            prohibida |= set(modelo.serpiente)
            prohibida |= {b.get_pos() for b in modelo.bombas}
            prohibida |= {p.get_pos() for p in modelo.powerups if p.activa}
            if modelo.comida is not None:
                prohibida.add(modelo.comida.posicion)
            # Ni al rotar un muro aparece pegado a tu próximo paso.
            if modelo.serpiente:
                cx, cy = modelo.serpiente[0]
                prohibida |= {(cx + TAMANO_CELDA, cy), (cx - TAMANO_CELDA, cy),
                              (cx, cy + TAMANO_CELDA), (cx, cy - TAMANO_CELDA)}
        return [m for m in muros if m not in prohibida]

    def _envolver_muros(self, modelo: ModeloSnake, nueva: Vector) -> Vector:
        """Modo Zen: salir por un lado entra por el opuesto."""
        min_x, min_y, max_x, max_y = modelo.limites
        nx, ny = nueva
        if nx < min_x:
            nx = max_x
        elif nx > max_x:
            nx = min_x
        if ny < min_y:
            ny = max_y
        elif ny > max_y:
            ny = min_y
        return (nx, ny)

    def generar_comida(self, modelo: ModeloSnake) -> Comida | None:
        """Food can never spawn on the snake's own body (nor in walls)."""
        ocupado = set(modelo.serpiente) | set(modelo.obstaculos)
        libres = [p for p in self.posiciones_tablero if p not in ocupado]
        if not libres:
            return None
        return Comida(self.rng.choice(libres))

    def generar_bomba(self, modelo: ModeloSnake) -> Bomba | None:
        """A bomb never overlaps the snake, an existing bomb or a wall."""
        ocupado = set(modelo.serpiente) | {b.get_pos() for b in modelo.bombas}
        ocupado |= set(modelo.obstaculos)
        libres = [p for p in self.posiciones_tablero if p not in ocupado]
        if not libres:
            return None
        x, y = self.rng.choice(libres)
        return Bomba(x, y, modelo.vida_bomba)

    def generar_powerup(self, modelo: ModeloSnake) -> PowerUp | None:
        """Un power-up no solapa serpiente, comida, bombas, muros ni otros."""
        ocupado = set(modelo.serpiente) | {b.get_pos() for b in modelo.bombas}
        ocupado |= {p.get_pos() for p in modelo.powerups if p.activa}
        ocupado |= set(modelo.obstaculos)
        if modelo.comida is not None:
            ocupado.add(modelo.comida.posicion)
        libres = [p for p in self.posiciones_tablero if p not in ocupado]
        if not libres:
            return None
        x, y = self.rng.choice(libres)
        return PowerUp(x, y, self.rng.choice(list(TIPOS_POWERUP)), VIDA_POWERUP)

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def cambiar_direccion(self, modelo: ModeloSnake, nueva: Vector) -> None:
        """Queue a direction, forbidding a 180° reversal.

        Pygame dispatches one queued action per tick, which fixes the
        "two-keys-same-frame" fast-turn exploit of the original game.
        """
        if nueva == modelo.direccion:
            return
        if len(modelo.cola_dir) < 3:
            modelo.cola_dir.append(nueva)

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------
    def siguiente_cabeza(self, modelo: ModeloSnake) -> Vector:
        dx, dy = modelo.direccion
        cx, cy = modelo.cabeza()
        return (cx + dx, cy + dy)

    def actualizar(self, modelo: ModeloSnake) -> str:
        """Advance the simulation by one tick.

        Returns one of ``"seguir"``, ``"muerte"``, ``"ganado"`` or
        ``"tiempo"`` (contrarreloj agotada) so the UI can react without
        reaching into game state.
        """
        if not modelo.partida_activa:
            return "terminado"
        modelo.eventos.clear()

        if modelo.cola_dir:
            siguiente = modelo.cola_dir.pop(0)
            # A queued turn is only legal if it does not reverse us.
            if siguiente != (-modelo.direccion[0], -modelo.direccion[1]):
                modelo.direccion = siguiente

        nueva = self.siguiente_cabeza(modelo)
        if modelo.modo == ModoJuego.ZEN.value:
            nueva = self._envolver_muros(modelo, nueva)
        resultado = self._comprobar_muro_o_bomba(modelo, nueva)
        if resultado:
            return resultado

        comio = modelo.comida is not None and nueva == modelo.comida.posicion
        cuerpo_para_colision = modelo.serpiente if comio else modelo.serpiente[:-1]
        if nueva in cuerpo_para_colision:
            return self._terminar(modelo, "muerte")

        modelo.serpiente.insert(0, nueva)
        if comio:
            self._comer(modelo)
        else:
            modelo.serpiente.pop()

        self._comer_powerup_si_hay(modelo, nueva)
        self._evolucionar_bombas_y_particulas(modelo)
        if modelo.modo == ModoJuego.CONTRARRELOJ.value and modelo.tiempo_restante > 0:
            modelo.tiempo_restante -= 1
            if modelo.tiempo_restante <= 0:
                return self._terminar(modelo, "tiempo")
        if modelo.modo == ModoJuego.LABERINTO.value and modelo.laberinto_cada > 0:
            modelo.tiempo_hasta_laberinto -= 1
            if modelo.tiempo_hasta_laberinto <= 0:
                modelo.laberinto_variante = (modelo.laberinto_variante + 1) % 3
                modelo.obstaculos = self._generar_laberinto(
                    modelo, modelo.laberinto_variante)
                modelo.tiempo_hasta_laberinto = modelo.laberinto_cada
                modelo.eventos.append("laberinto_cambio")
        return "seguir"

    def _sumar_tiempo(self, modelo: ModeloSnake, segundos: int) -> None:
        """Bonus de tiempo en Crono (con tope para mantener la tensión)."""
        base = max(modelo.velocidad_base, 1)
        tope = TIEMPO_MAX_CRONO_SEG * base
        modelo.tiempo_restante = min(modelo.tiempo_restante + segundos * base, tope)
        modelo.eventos.append(f"tiempo_bonus:+{segundos}s")

    def _comer_powerup_si_hay(self, modelo: ModeloSnake, nueva: Vector) -> None:
        for pu in modelo.powerups:
            if pu.activa and nueva == pu.get_pos():
                pu.activa = False
                self._aplicar_powerup(modelo, pu.tipo)
                break
        modelo.powerups = [p for p in modelo.powerups if p.activa]

    def _aplicar_powerup(self, modelo: ModeloSnake, tipo: str) -> None:
        if tipo == "dorada":
            modelo.puntaje += 30
            modelo.frutos += 1
            modelo.monedas += MONEDA_POR_DORADA
            if modelo.frutos >= modelo.frutos_para_nivel:
                modelo.nivel += 1
                modelo.frutos = 0
                modelo.frutos_para_nivel = modelo.factor_nivel
                modelo.monedas += MONEDA_POR_NIVEL
            if modelo.modo == ModoJuego.CONTRARRELOJ.value:
                self._sumar_tiempo(modelo, BONUS_DORADA_SEG)
        elif tipo == "escudo":
            modelo.escudo_ticks = DURACION_ESCUDO
        elif tipo == "lento":
            modelo.lento_ticks = DURACION_LENTO
            modelo.velocidad = max(4, modelo.velocidad_base - 3)
        modelo.eventos.append(f"powerup:{tipo}")
        cx, cy = modelo.cabeza()
        color = {"dorada": (255, 214, 60), "escudo": (0, 230, 255),
                 "lento": (190, 80, 255)}.get(tipo, (255, 255, 255))
        for _ in range(12):
            modelo.particulas.append(
                Particula(
                    x=cx + 12.0, y=cy + 12.0,
                    vx=self.rng.uniform(-2.5, 2.5),
                    vy=self.rng.uniform(-2.5, 2.5),
                    radio=self.rng.randint(2, 4),
                    color=color, vida=35,
                )
            )

    def _comprobar_muro_o_bomba(self, modelo: ModeloSnake, nueva: Vector) -> str:
        """Wall / bomb / labyrinth hits happen before the snake moves."""
        nx, ny = nueva
        min_x, min_y, max_x, max_y = modelo.limites
        if not (min_x <= nx <= max_x and min_y <= ny <= max_y):
            return self._terminar(modelo, "muerte")
        if nueva in modelo.obstaculos:
            return self._terminar(modelo, "muerte")
        for bomba in modelo.bombas:
            if bomba.activa and nueva == bomba.get_pos():
                if modelo.escudo_ticks > 0:
                    # El escudo destruye la bomba en vez de matar.
                    bomba.activa = False
                    modelo.eventos.append("escudo_bloqueo")
                    modelo.powerups = [p for p in modelo.powerups if p.activa]
                    return ""
                return self._terminar(modelo, "muerte")
        return ""

    def _comer(self, modelo: ModeloSnake) -> None:
        """Score, level-up, particles and the next pellet."""
        modelo.puntaje += 10
        modelo.frutos += 1
        modelo.monedas += MONEDA_POR_MANZANA
        if modelo.frutos >= modelo.frutos_para_nivel:
            modelo.nivel += 1
            modelo.frutos = 0
            modelo.frutos_para_nivel = modelo.factor_nivel
            modelo.monedas += MONEDA_POR_NIVEL
        if modelo.modo == ModoJuego.CONTRARRELOJ.value:
            self._sumar_tiempo(modelo, BONUS_MANZANA_SEG)

        cx, cy = modelo.cabeza()
        for _ in range(10):
            modelo.particulas.append(
                Particula(
                    x=cx + 12.0,
                    y=cy + 12.0,
                    vx=self.rng.uniform(-2, 2),
                    vy=self.rng.uniform(-2, 2),
                    radio=self.rng.randint(2, 4),
                    color=self.rng.choice(
                        [(255, 0, 200), (0, 230, 255), (255, 214, 60)]
                    ),
                    vida=30,
                )
            )

        modelo.comida = self.generar_comida(modelo)
        if modelo.comida is None:
            return self._terminar(modelo, "ganado")

    def _evolucionar_bombas_y_particulas(self, modelo: ModeloSnake) -> None:
        # Efectos temporales.
        if modelo.escudo_ticks > 0:
            modelo.escudo_ticks -= 1
        if modelo.lento_ticks > 0:
            modelo.lento_ticks -= 1
            if modelo.lento_ticks <= 0:
                modelo.velocidad = modelo.velocidad_base
        # Bombs: spawn timer, aging, eviction.
        if modelo.tiempo_hasta_bomba <= 0 and len(modelo.bombas) < modelo.max_bombas:
            nueva = self.generar_bomba(modelo)
            if nueva:
                modelo.bombas.append(nueva)
                modelo.tiempo_hasta_bomba = self.rng.randint(*modelo.rango_bomba)
            else:
                modelo.tiempo_hasta_bomba = 40
        else:
            modelo.tiempo_hasta_bomba -= 1

        # Power-ups: un solo activo, con vida limitada.
        activos = [p for p in modelo.powerups if p.activa]
        if modelo.tiempo_hasta_powerup <= 0 and len(activos) < 1:
            nuevo = self.generar_powerup(modelo)
            if nuevo:
                modelo.powerups.append(nuevo)
                modelo.tiempo_hasta_powerup = self.rng.randint(*RANGO_POWERUP)
            else:
                modelo.tiempo_hasta_powerup = 60
        else:
            modelo.tiempo_hasta_powerup -= 1

        for bomba in modelo.bombas:
            bomba.actualizar()
        modelo.bombas = [b for b in modelo.bombas if b.activa]

        for pu in modelo.powerups:
            pu.actualizar()
        modelo.powerups = [p for p in modelo.powerups if p.activa]

        # Particles.
        for p in modelo.particulas:
            p.actualizar()
        modelo.particulas = [p for p in modelo.particulas if p.vida > 0]

    def _terminar(self, modelo: ModeloSnake, motivo: str) -> str:
        if motivo == "muerte":
            modelo.game_over = True
        elif motivo == "ganado":
            modelo.gano = True
        elif motivo == "tiempo":
            modelo.game_over = True
            modelo.eventos.append("tiempo_agotado")
        modelo.partida_activa = False
        return motivo
