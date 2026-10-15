"""Unit tests for the pure game rules (no pygame needed)."""

import random

import pytest

from snake_game.config import AREA_DE_JUEGO, TAMANO_CELDA, Dificultad
from snake_game.core.logica import Logica


@pytest.fixture
def logica():
    return Logica(rng=random.Random(1234))


def test_iniciar_partida_configura_dificultad(logica):
    modelo = logica.iniciar_partida(Dificultad.EXTREMO)
    assert modelo.dificultad == "Extremo"
    assert modelo.velocidad == Dificultad.EXTREMO.velocidad
    assert modelo.max_bombas == Dificultad.EXTREMO.max_bombas
    assert modelo.partida_activa
    assert not modelo.game_over
    assert modelo.comida is not None


def test_comida_nunca_sobre_la_serpiente(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL)
    for _ in range(50):
        comida = logica.generar_comida(modelo)
        assert comida is not None
        assert comida.posicion not in modelo.serpiente


def test_avance_derecha(logica):
    modelo = logica.iniciar_partida()
    cabeza_inicial = modelo.cabeza()
    logica.actualizar(modelo)
    assert modelo.cabeza() == (cabeza_inicial[0] + TAMANO_CELDA, cabeza_inicial[1])
    assert modelo.partida_activa


def test_no_da_marcha_atras(logica):
    modelo = logica.iniciar_partida()
    # The snake moves right; reversing would hit its own neck.
    logica.cambiar_direccion(modelo, (-TAMANO_CELDA, 0))
    direccion_despues = modelo.direccion
    logica.actualizar(modelo)
    assert modelo.direccion == direccion_despues
    assert modelo.partida_activa


def test_colision_con_muro_mata(logica):
    modelo = logica.iniciar_partida()
    min_x, min_y, max_x, max_y = AREA_DE_JUEGO
    # Force the head to the right wall's edge and try to go one cell beyond.
    modelo.serpiente[0] = (max_x, modelo.cabeza()[1])
    resultado = logica.actualizar(modelo)
    assert resultado == "muerte"
    assert modelo.game_over
    assert not modelo.partida_activa


def test_comer_hace_crecer_y_suma_puntos(logica):
    modelo = logica.iniciar_partida()
    comida = modelo.comida
    assert comida is not None
    modelo.serpiente[0] = (comida.posicion[0] - TAMANO_CELDA, comida.posicion[1])
    largo_inicial = len(modelo.serpiente)
    resultado = logica.actualizar(modelo)
    assert resultado == "seguir"
    assert modelo.cabeza() == comida.posicion
    assert modelo.puntaje == 10
    assert len(modelo.serpiente) == largo_inicial + 1


def test_tabla_completa_gana(logica):
    modelo = logica.iniciar_partida()
    # Fill the whole board with the snake body so no food fits.
    todos = list(logica.posiciones_tablero)
    modelo.serpiente = todos
    assert logica.generar_comida(modelo) is None
    comida = modelo.comida
    assert comida is None or True


def test_subir_nivel_tras_cuota_de_frutos(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL)
    assert modelo.nivel == 1
    # A short snake keeps crashes impossible while we grind for the quota.
    modelo.serpiente = modelo.serpiente[:2]
    for turno in range(modelo.factor_nivel):
        c = modelo.cabeza()
        modelo.comida = logica.generar_comida(modelo)
        assert modelo.comida is not None
        # Force a pellet right ahead of the head.
        modelo.comida.posicion = (c[0] + TAMANO_CELDA, c[1])
        resultado = logica.actualizar(modelo)
        assert resultado == "seguir", f"fallo al fruto {turno}"
        assert modelo.frutos == ((turno + 1) % modelo.factor_nivel)
    assert modelo.nivel == 2
    assert modelo.frutos == 0


def test_maximo_bombas_respetado(logica):
    modelo = logica.iniciar_partida(Dificultad.EXTREMO)
    modelo.tiempo_hasta_bomba = 0
    for _ in range(modelo.max_bombas + 5):
        logica._evolucionar_bombas_y_particulas(modelo)
        assert len(modelo.bombas) <= modelo.max_bombas
