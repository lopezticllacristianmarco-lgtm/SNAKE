"""Tests for the central configuration (constants & difficulty presets)."""

from snake_game.config import AREA_DE_JUEGO, SONIDOS, TAMANO_CELDA, Dificultad


def test_formato_sonidos():
    for nombre, ruta in SONIDOS.items():
        assert ruta.suffix == ".wav", nombre
        assert nombre in {"comer", "perder", "ganar", "bomba"}


def test_posiciones_tablero_grid():
    min_x, min_y, max_x, max_y = AREA_DE_JUEGO
    ancho = (max_x - min_x) // TAMANO_CELDA + 1
    alto = (max_y - min_y) // TAMANO_CELDA + 1
    assert min_x % TAMANO_CELDA == 0
    assert min_y % TAMANO_CELDA == 0
    assert ancho * alto > 0
    for d in Dificultad:
        assert d.factor_nivel >= 5
        assert d.max_bombas >= 1
        assert d.rango_bomba[0] <= d.rango_bomba[1]
        assert d.velocidad >= 6


def test_por_nombre_con_valor_invalido():
    assert Dificultad.por_nombre("Neon") is Dificultad.NORMAL
    assert Dificultad.por_nombre("Extremo") is Dificultad.EXTREMO
