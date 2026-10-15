"""Tests de ajustes: persistencia, volúmenes, pantalla y teclas."""

import pygame
import pytest

from snake_game.core.guardado import (
    TECLAS_POR_DEFECTO,
    EstadoJugador,
    GestorEstado,
    normalizar_teclas,
)


@pytest.fixture
def gestor(tmp_path):
    return GestorEstado(
        ruta_estado=tmp_path / "estado.json",
        ruta_records=tmp_path / "records.json",
    )


def test_teclas_por_defecto_wasd():
    assert TECLAS_POR_DEFECTO == {"arriba": 119, "abajo": 115, "izq": 97,
                                  "der": 100, "pausa": 112}


def test_normalizar_teclas_filtra_basura():
    assert normalizar_teclas(None) == TECLAS_POR_DEFECTO
    assert normalizar_teclas("hola") == TECLAS_POR_DEFECTO
    limpias = normalizar_teclas({"arriba": 105, "pausa": "x", "trampa": 1})
    assert limpias["arriba"] == 105
    assert limpias["pausa"] == TECLAS_POR_DEFECTO["pausa"]
    assert "trampa" not in limpias


def test_ajustes_persisten(gestor):
    gestor.guardar_estado(EstadoJugador(volumen_musica=0.2, volumen_efectos=0.9,
                                        teclas={"arriba": 105, "abajo": 106,
                                                "izq": 107, "der": 108,
                                                "pausa": 109},
                                        nombre="Ana"))
    estado = gestor.leer_estado()
    assert estado.volumen_musica == 0.2
    assert estado.volumen_efectos == 0.9
    assert estado.teclas["arriba"] == 105
    assert estado.nombre == "Ana"


def test_volumenes_fuera_de_rango_se_sujetan(gestor):
    gestor.ruta_estado.write_text(
        '{"volumen_musica": 9.5, "volumen_efectos": -3}', encoding="utf-8")
    estado = gestor.leer_estado()
    assert estado.volumen_musica == 1.0
    assert estado.volumen_efectos == 0.0


def _app_headless():
    import os

    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    from snake_game.app import App
    from snake_game.escenas.base import Escena

    return App(), Escena


def _click(app, x, y):
    app._manejar_ajustes(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                            button=1, pos=(x, y)))


def test_ajustes_volumen_y_volver():
    app, Escena = _app_headless()
    try:
        app._abrir_ajustes()
        assert app.scena == Escena.AJUSTES
        app._dibujar_ajustes(0)

        antes = app.audio.volumen_musica
        _click(app, 590, 190)  # VOL MUSICA +
        assert app.audio.volumen_musica == round(min(1.0, antes + 0.1), 2)
        _click(app, 440, 250)  # VOL EFECTOS -
        assert app.audio.volumen_efectos < 0.8

        # VOLVER con click regresa al menú (regresión: no estaba cableado).
        app._manejar_ajustes(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                                button=1, pos=(500, 620)))
        assert app.scena == Escena.MENU

        app._abrir_ajustes()
        app._manejar_ajustes(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        assert app.scena == Escena.MENU
    finally:
        app.audio.cerrar()
        pygame.quit()


def test_ajustes_captura_y_swap_de_teclas():
    app, _ = _app_headless()
    try:
        app._abrir_ajustes()
        _click(app, 236, 344)  # tecla ARRIBA
        assert app.ajuste_captura == "arriba"
        app._manejar_ajustes(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i))
        assert app.teclas["arriba"] == pygame.K_i
        assert app.ajuste_captura is None
        # Swap: la I estaba libre; ahora bindear ABAJO a la I la quita de ARRIBA.
        _click(app, 368, 344)  # tecla ABAJO
        app._manejar_ajustes(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i))
        assert app.teclas["abajo"] == pygame.K_i
        assert app.teclas["arriba"] != pygame.K_i
        # ESC cancela la captura sin tocar nada.
        _click(app, 500, 344)
        app._manejar_ajustes(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        assert app.ajuste_captura is None
    finally:
        app.audio.cerrar()
        pygame.quit()

def test_tecla_custom_mueve_la_serpiente():
    app, _ = _app_headless()
    try:
        from snake_game.core.guardado import normalizar_teclas

        app.teclas = normalizar_teclas({"arriba": pygame.K_i, "abajo": pygame.K_o,
                                        "izq": pygame.K_j, "der": pygame.K_l,
                                        "pausa": pygame.K_p})
        app._empezar_juego()
        modelo = app.partida.modelo
        modelo.serpiente = [(400, 350), (375, 350)]
        modelo.direccion = (25, 0)
        app._manejar_juego(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i))
        assert modelo.cola_dir and modelo.cola_dir[-1] == (0, -25)
    finally:
        app.audio.cerrar()
        pygame.quit()


def _tecla(app, codigo, unicode=""):
    app._manejar_ajustes(pygame.event.Event(pygame.KEYDOWN, key=codigo,
                                            unicode=unicode))


def test_editor_de_nombre():
    app, _ = _app_headless()
    try:
        app.nombre = "JUGADOR"
        app._abrir_ajustes()
        # Click en la caja -> edita.
        app._manejar_ajustes(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                                button=1, pos=(560, 442)))
        assert app.ajuste_nombre_editando is True
        for _ in range(7):
            _tecla(app, pygame.K_BACKSPACE)
        for letra, codigo in (("a", pygame.K_a), ("n", pygame.K_n),
                              ("a", pygame.K_a)):
            _tecla(app, codigo, letra)
        assert app.nombre == "ana"
        _tecla(app, pygame.K_RETURN)
        assert app.ajuste_nombre_editando is False
        assert app.nombre == "ana"
        assert app.estado.leer_estado().nombre == "ana"
        app._dibujar_ajustes(0)
        # Vacío -> vuelve al valor por defecto.
        app._manejar_ajustes(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                                button=1, pos=(560, 442)))
        for _ in range(12):
            _tecla(app, pygame.K_BACKSPACE)
        _tecla(app, pygame.K_RETURN)
        assert app.nombre == "JUGADOR"
    finally:
        app.audio.cerrar()
        pygame.quit()
