"""Headless smoke test: boots the full App under the dummy video driver,
walks through every scene, simulates keys/clicks, and exits cleanly."""

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame  # noqa: E402

from snake_game.app import App, Escena  # noqa: E402


def evento_tipo(tipo, **datos):
    return pygame.event.Event(tipo, **datos)


def main():
    import tempfile
    from pathlib import Path as _Path

    from snake_game.core.guardado import GestorEstado

    app = App()
    # No tocar el estado real del jugador: redirigir el guardado a tmp.
    _tmp = _Path(tempfile.mkdtemp(prefix="smoke_snake_"))
    app.estado = GestorEstado(_tmp / "estado.json", _tmp / "records.json")
    assert app.scena == Escena.MENU

    # 1) Some animated menu frames.
    for _ in range(10):
        app._dibujar_menu(5000)
        pygame.display.flip()

# 2) Start a game.
    app._empezar_juego()
    assert app.scena == Escena.JUEGO
    assert app.partida is not None

    # Park the snake in the middle of a row pointing left; far from walls.
    modelo = app.partida.modelo
    modelo.serpiente = [(600, 600), (625, 600), (650, 600), (675, 600)]
    modelo.direccion = (-25, 0)
    modelo.velocidad = 6  # easy pace: plenty of margin before the wall
    app.acumulador = 0.0

    # 3) Play ticks; the 4-long snake is way short of both the left wall
    #    (50..575) and its own tail, so it survives every tick.
    for _ in range(60):
        app._actualizar(0.04, 0)
    assert app.partida.modelo.cabeza()[0] >= 50
    app._manejar_juego(evento_tipo(pygame.KEYDOWN, key=pygame.K_w))
    app._actualizar(0.04, 0)
    assert app.partida.modelo.partida_activa
    app._dibujar_juego(1000)
    pygame.display.flip()

    # 4) Pause / resume cycle.
    app._manejar_juego(evento_tipo(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert app.scena == Escena.PAUSA
    app._dibujar_pausa(2000)
    pygame.display.flip()
    app._manejar_pausa(evento_tipo(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert app.scena == Escena.JUEGO

    # 5) Kill the snake to reach game over (force wall death).
    min_x, min_y, max_x, max_y = app.partida.modelo.limites
    app.partida.modelo.serpiente[0] = (max_x, app.partida.modelo.cabeza()[1])
    while app.partida.modelo.partida_activa:
        app._actualizar(0.02, 0)
        app._actualizar(0.5, 0)
    assert app.scena == Escena.GAME_OVER
    app._dibujar_game_over(3000)
    pygame.display.flip()

    # 6) Restart and let death happen again, then go to the menu.
    app._manejar_game_over(evento_tipo(pygame.KEYDOWN, key=pygame.K_RETURN))
    assert app.scena == Escena.JUEGO
    app._manejar_game_over(evento_tipo(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    app._manejar_juego(evento_tipo(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert app.scena == Escena.PAUSA
    app._manejar_pausa(evento_tipo(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    app._manejar_juego(evento_tipo(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    app._manejar_pausa(evento_tipo(pygame.MOUSEMOTION, pos=(500, 452)))
    app._manejar_pausa(evento_tipo(pygame.MOUSEBUTTONDOWN, button=1, pos=(500, 452)))
    assert app.scena == Escena.JUEGO

    # 7) Difficulty chips: mouse + keyboard change the selected difficulty.
    from snake_game.config import Dificultad

    app.dificultad = Dificultad.NORMAL
    app._ir(Escena.MENU)
    app._crear_menu()
    assert app.dificultad.name == "NORMAL"
    app._manejar_menu(evento_tipo(pygame.MOUSEBUTTONDOWN, button=1, pos=(730, 300)))
    assert app.dificultad.name == "EXTREMO"
    # EXTREMO <- <- = NORMAL (circular)
    app._manejar_menu(evento_tipo(pygame.KEYDOWN, key=pygame.K_LEFT))
    app._manejar_menu(evento_tipo(pygame.KEYDOWN, key=pygame.K_LEFT))
    assert app.dificultad.name == "NORMAL"
    app._manejar_menu(evento_tipo(pygame.KEYDOWN, key=pygame.K_RIGHT))
    assert app.dificultad.name == "DIFICIL"
    app._manejar_menu(evento_tipo(pygame.KEYDOWN, key=pygame.K_LEFT))
    assert app.dificultad.name == "NORMAL"
    app._manejar_menu(evento_tipo(pygame.KEYDOWN, key=pygame.K_RETURN))
    assert app.scena == Escena.JUEGO

    # 8) Screens: instructions and records.
    app._crear_menu()
    app._manejar_menu(evento_tipo(pygame.MOUSEBUTTONDOWN, button=1, pos=(340, 495)))
    assert app.scena == Escena.INSTRUCCIONES
    app._dibujar_instrucciones(0)
    pygame.display.flip()
    app._manejar_instrucciones(evento_tipo(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    app._crear_menu()
    app._manejar_menu(evento_tipo(pygame.MOUSEBUTTONDOWN, button=1, pos=(500, 495)))
    assert app.scena == Escena.RECORDS
    app._dibujar_records(0)
    pygame.display.flip()

    # 9) Tienda: monedas se conservan al perder y sirven para comprar skins.
    app.monedas = 200
    app.skins = ["neon"]
    app.skin_activa = "neon"
    app._abrir_tienda()
    assert app.scena == Escena.TIENDA
    app._dibujar_tienda(0)
    pygame.display.flip()
    app._comprar_o_equipar("morada")
    assert "morada" in app.skins
    assert app.skin_activa == "morada"
    assert app.monedas == 0
    app._empezar_juego()
    assert app.partida.modelo.skin == "morada"
    # Simular ganancia y muerte: las monedas deben conservarse.
    app.partida.modelo.monedas = 7
    app._terminar("muerte")
    assert app.scena == Escena.GAME_OVER
    assert app.monedas_ganadas == 7
    assert app.monedas == 7
    app._dibujar_game_over(0)
    pygame.display.flip()

    # 9b) Legendaria arcoiris: compra, equipo y dibujo animado.
    app.monedas = 100000
    app.skins = ["neon"]
    app.skin_activa = "neon"
    app._abrir_tienda()
    app._comprar_o_equipar("arcoiris")
    assert "arcoiris" in app.skins
    assert app.skin_activa == "arcoiris"
    assert app.monedas == 0
    app._empezar_juego()
    assert app.partida.modelo.skin == "arcoiris"
    for _t in (0, 500, 1500):
        app._dibujar_tienda(_t)
        app.render.dibujar_serpiente(app.partida.modelo, _t)
    pygame.display.flip()

    # 10) Música del dispositivo: elegir, ciclar y volver a original.
    from pathlib import Path as _P
    wavs = sorted((_P("src") / "snake_game" / "assets").glob("*.wav"))
    app._abrir_ajustes()
    assert app.scena == Escena.AJUSTES
    if wavs:
        app._usar_musica(str(wavs[0]))
        assert app.audio.musica_custom == str(wavs[0])
        assert app.estado.leer_estado().musica_custom == str(wavs[0])
    app._dibujar_ajustes(0)
    pygame.display.flip()
    app._cambiar_cancion(1)
    app._restaurar_musica()
    assert app.audio.musica_custom == ""
    assert app.estado.leer_estado().musica_custom == ""

    app.audio.cerrar()
    pygame.quit()
    print("SMOKE TEST OK")


if __name__ == "__main__":
    main()
