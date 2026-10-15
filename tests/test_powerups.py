"""Tests de power-ups: dorada, escudo y lento (sin pygame)."""

import random

import pytest

from snake_game.config import TAMANO_CELDA, Dificultad
from snake_game.core.logica import Logica
from snake_game.core.modelos import PowerUp


@pytest.fixture
def logica():
    return Logica(rng=random.Random(7))


def _poner_powerup_delante(logica, modelo, tipo):
    c = modelo.cabeza()
    modelo.powerups = [PowerUp(c[0] + TAMANO_CELDA, c[1], tipo, tiempo_vida=300)]
    modelo.tiempo_hasta_powerup = 9999
    modelo.tiempo_hasta_bomba = 9999


def test_generar_powerup_no_solapa(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL)
    for _ in range(20):
        pu = logica.generar_powerup(modelo)
        assert pu is not None
        assert pu.get_pos() not in modelo.serpiente
        assert pu.tipo in ("dorada", "escudo", "lento")


def test_dorada_suma_30_y_emite_evento(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL)
    modelo.serpiente = modelo.serpiente[:2]
    _poner_powerup_delante(logica, modelo, "dorada")
    puntos = modelo.puntaje
    assert logica.actualizar(modelo) == "seguir"
    assert modelo.puntaje == puntos + 30
    assert "powerup:dorada" in modelo.eventos
    assert modelo.powerups == []


def test_escudo_protege_de_bomba(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL)
    modelo.serpiente = modelo.serpiente[:2]
    _poner_powerup_delante(logica, modelo, "escudo")
    assert logica.actualizar(modelo) == "seguir"
    assert modelo.escudo_ticks > 0
    # Ahora chocar una bomba no mata: la destruye.
    from snake_game.core.modelos import Bomba

    c = modelo.cabeza()
    modelo.bombas = [Bomba(c[0] + TAMANO_CELDA, c[1], 300)]
    assert logica.actualizar(modelo) == "seguir"
    assert modelo.partida_activa
    assert "escudo_bloqueo" in modelo.eventos


def test_sin_escudo_la_bomba_mata(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL)
    modelo.serpiente = modelo.serpiente[:2]
    assert modelo.escudo_ticks == 0
    from snake_game.core.modelos import Bomba

    c = modelo.cabeza()
    modelo.bombas = [Bomba(c[0] + TAMANO_CELDA, c[1], 300)]
    assert logica.actualizar(modelo) == "muerte"


def test_lento_baja_velocidad_y_luego_restaura(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL)
    modelo.serpiente = modelo.serpiente[:2]
    base = modelo.velocidad_base
    _poner_powerup_delante(logica, modelo, "lento")
    assert logica.actualizar(modelo) == "seguir"
    assert modelo.lento_ticks > 0
    assert modelo.velocidad == max(4, base - 3)
    modelo.lento_ticks = 1
    modelo.tiempo_hasta_powerup = 9999
    modelo.tiempo_hasta_bomba = 9999
    logica._evolucionar_bombas_y_particulas(modelo)
    assert modelo.velocidad == base


def test_powerup_expira_con_el_tiempo(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL)
    c = modelo.cabeza()
    modelo.powerups = [PowerUp(c[0] + 100, c[1], "dorada", tiempo_vida=1)]
    modelo.tiempo_hasta_powerup = 9999
    modelo.tiempo_hasta_bomba = 9999
    logica._evolucionar_bombas_y_particulas(modelo)
    assert modelo.powerups == []
