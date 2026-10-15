"""Tests de modos de juego: Clasico, Zen, Contrarreloj y Laberinto."""

import random

import pytest

from snake_game.config import AREA_DE_JUEGO, Dificultad, ModoJuego
from snake_game.core.guardado import GestorEstado
from snake_game.core.logica import Logica


@pytest.fixture
def logica():
    return Logica(rng=random.Random(99))


def _serpiente_corta_en_centro(modelo):
    modelo.serpiente = [(400, 350), (375, 350)]
    modelo.direccion = (25, 0)
    modelo.cola_dir = []
    modelo.bombas = []
    modelo.powerups = []
    modelo.tiempo_hasta_bomba = 9999
    modelo.tiempo_hasta_powerup = 9999
    # Comida lejos para no interferir.
    modelo.comida = logica_comida_lejos(modelo)


def logica_comida_lejos(modelo):
    from snake_game.core.modelos import Comida

    return Comida((100, 600))


def test_modo_por_defecto_es_clasico(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL)
    assert modelo.modo == "Clasico"
    assert modelo.obstaculos == []
    assert modelo.tiempo_restante == 0


def test_iniciar_partida_acepta_modo_str(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL, "Zen")
    assert modelo.modo == "Zen"


def test_modo_invalido_cae_a_clasico():
    assert ModoJuego.por_nombre("Imposible") is ModoJuego.CLASICO


def test_clasico_muere_en_muro(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL, ModoJuego.CLASICO)
    min_x, min_y, max_x, max_y = AREA_DE_JUEGO
    modelo.serpiente = [(max_x, 350), (max_x - 25, 350)]
    modelo.direccion = (25, 0)
    assert logica.actualizar(modelo) == "muerte"


def test_zen_envuelve_muro_derecho(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL, ModoJuego.ZEN)
    min_x, min_y, max_x, max_y = AREA_DE_JUEGO
    modelo.serpiente = [(max_x, 350), (max_x - 25, 350)]
    modelo.direccion = (25, 0)
    modelo.bombas = []
    assert logica.actualizar(modelo) == "seguir"
    assert modelo.cabeza() == (min_x, 350)
    assert modelo.partida_activa


def test_zen_envuelve_muro_superior(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL, ModoJuego.ZEN)
    min_x, min_y, max_x, max_y = AREA_DE_JUEGO
    modelo.serpiente = [(400, min_y), (400, min_y + 25)]
    modelo.direccion = (0, -25)
    modelo.bombas = []
    assert logica.actualizar(modelo) == "seguir"
    assert modelo.cabeza() == (400, max_y)


def test_contrarreloj_inicia_con_tiempo(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL, ModoJuego.CONTRARRELOJ)
    assert modelo.tiempo_limite == 40 * Dificultad.NORMAL.velocidad
    assert modelo.tiempo_restante == modelo.tiempo_limite


def test_crono_tiempo_por_dificultad(logica):
    esperado = {Dificultad.FACIL: 60, Dificultad.NORMAL: 40,
                Dificultad.DIFICIL: 25, Dificultad.EXTREMO: 15}
    for dif, segundos in esperado.items():
        assert dif.segundos_crono == segundos
        modelo = logica.iniciar_partida(dif, ModoJuego.CONTRARRELOJ)
        assert modelo.tiempo_limite == segundos * dif.velocidad
        assert modelo.tiempo_restante == modelo.tiempo_limite


def test_crono_respeta_dificultad_elegida(logica):
    modelo = logica.iniciar_partida(Dificultad.EXTREMO, ModoJuego.CONTRARRELOJ)
    assert modelo.velocidad == Dificultad.EXTREMO.velocidad
    assert modelo.max_bombas == Dificultad.EXTREMO.max_bombas
    assert modelo.dificultad == "Extremo"


def test_manzana_suma_tiempo_en_crono(logica):
    from snake_game.config import BONUS_MANZANA_SEG
    from snake_game.core.modelos import Comida

    modelo = logica.iniciar_partida(Dificultad.NORMAL, ModoJuego.CONTRARRELOJ)
    _serpiente_corta_en_centro(modelo)
    modelo.comida = Comida((425, 350))
    modelo.tiempo_restante = 100
    assert logica.actualizar(modelo) == "seguir"
    assert modelo.puntaje == 10
    # +bonus de la manzana, -1 del propio tick.
    assert modelo.tiempo_restante == 100 + BONUS_MANZANA_SEG * modelo.velocidad_base - 1
    assert any(e.startswith("tiempo_bonus") for e in modelo.eventos)


def test_dorada_suma_mas_tiempo_en_crono(logica):
    from snake_game.config import BONUS_DORADA_SEG
    from snake_game.core.modelos import PowerUp

    modelo = logica.iniciar_partida(Dificultad.NORMAL, ModoJuego.CONTRARRELOJ)
    _serpiente_corta_en_centro(modelo)
    modelo.powerups = [PowerUp(425, 350, "dorada", tiempo_vida=300)]
    modelo.tiempo_restante = 100
    assert logica.actualizar(modelo) == "seguir"
    assert modelo.tiempo_restante == 100 + BONUS_DORADA_SEG * modelo.velocidad_base - 1


def test_tiempo_con_tope_maximo(logica):
    from snake_game.config import TIEMPO_MAX_CRONO_SEG
    from snake_game.core.modelos import Comida

    modelo = logica.iniciar_partida(Dificultad.NORMAL, ModoJuego.CONTRARRELOJ)
    _serpiente_corta_en_centro(modelo)
    modelo.comida = Comida((425, 350))
    modelo.tiempo_restante = TIEMPO_MAX_CRONO_SEG * modelo.velocidad_base - 1
    assert logica.actualizar(modelo) == "seguir"
    # Tope aplicado y luego -1 del tick.
    assert modelo.tiempo_restante == TIEMPO_MAX_CRONO_SEG * modelo.velocidad_base - 1


def test_fuera_de_crono_comer_no_toca_el_reloj(logica):
    from snake_game.core.modelos import Comida

    modelo = logica.iniciar_partida(Dificultad.NORMAL, ModoJuego.CLASICO)
    _serpiente_corta_en_centro(modelo)
    modelo.comida = Comida((425, 350))
    assert logica.actualizar(modelo) == "seguir"
    assert modelo.tiempo_restante == 0
    assert not any(e.startswith("tiempo_bonus") for e in modelo.eventos)


def test_contrarreloj_termina_por_tiempo(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL, ModoJuego.CONTRARRELOJ)
    _serpiente_corta_en_centro(modelo)
    modelo.tiempo_restante = 2
    assert logica.actualizar(modelo) == "seguir"
    assert modelo.partida_activa
    assert logica.actualizar(modelo) == "tiempo"
    assert not modelo.partida_activa
    assert modelo.game_over


def test_contrarreloj_puede_comer_antes_del_fin(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL, ModoJuego.CONTRARRELOJ)
    _serpiente_corta_en_centro(modelo)
    from snake_game.core.modelos import Comida

    modelo.comida = Comida((425, 350))
    modelo.tiempo_restante = 50
    assert logica.actualizar(modelo) == "seguir"
    assert modelo.puntaje == 10


def test_laberinto_genera_obstaculos(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL, ModoJuego.LABERINTO)
    assert len(modelo.obstaculos) > 10
    # La aparición queda libre.
    for celda in ((400, 350), (375, 350), (350, 350)):
        assert celda not in modelo.obstaculos
    # La comida no spawnea dentro de un muro.
    assert modelo.comida is not None
    assert modelo.comida.posicion not in modelo.obstaculos
    for _ in range(20):
        assert logica.generar_comida(modelo).posicion not in modelo.obstaculos
        bomba = logica.generar_bomba(modelo)
        if bomba is not None:
            assert bomba.get_pos() not in modelo.obstaculos


def test_laberinto_intervalo_por_dificultad(logica):
    esperado = {Dificultad.FACIL: 30, Dificultad.NORMAL: 20,
                Dificultad.DIFICIL: 15, Dificultad.EXTREMO: 10}
    for dif, segundos in esperado.items():
        assert dif.segundos_laberinto == segundos
        modelo = logica.iniciar_partida(dif, ModoJuego.LABERINTO)
        assert modelo.laberinto_cada == segundos * dif.velocidad
        assert modelo.tiempo_hasta_laberinto == modelo.laberinto_cada
        assert modelo.laberinto_variante == 0


def _centrar_para_regen(logica, modelo):
    modelo.serpiente = [(400, 350), (375, 350)]
    modelo.direccion = (25, 0)
    modelo.cola_dir = []
    modelo.bombas = []
    modelo.powerups = []
    modelo.tiempo_hasta_bomba = 9999
    modelo.tiempo_hasta_powerup = 9999
    from snake_game.core.modelos import Comida
    modelo.comida = Comida((100, 600))


def test_laberinto_rota_solo_y_cambia_variante(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL, ModoJuego.LABERINTO)
    _centrar_para_regen(logica, modelo)
    vistos = [set(modelo.obstaculos)]
    for v in (1, 2):
        modelo.tiempo_hasta_laberinto = 1
        assert logica.actualizar(modelo) == "seguir"
        assert modelo.laberinto_variante == v
        assert "laberinto_cambio" in modelo.eventos
        assert modelo.tiempo_hasta_laberinto == modelo.laberinto_cada
        assert set(modelo.obstaculos) not in vistos
        vistos.append(set(modelo.obstaculos))
    # Al cerrar el ciclo vuelve a la variante 0 (idéntica si nada la tapa).
    modelo.tiempo_hasta_laberinto = 1
    assert logica.actualizar(modelo) == "seguir"
    assert modelo.laberinto_variante == 0
    assert "laberinto_cambio" in modelo.eventos


def test_rotacion_nunca_entierra_serpiente_ni_comida(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL, ModoJuego.LABERINTO)
    _centrar_para_regen(logica, modelo)
    # Serpiente larga para cubrir más celdas.
    modelo.serpiente = [(400 - 25 * i, 350) for i in range(12)]
    for _ in range(3):
        modelo.tiempo_hasta_laberinto = 1
        assert logica.actualizar(modelo) == "seguir"
        muros = set(modelo.obstaculos)
        assert not (muros & set(modelo.serpiente))
        assert modelo.comida.posicion not in muros


def test_sin_laberinto_no_hay_rotacion(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL, ModoJuego.CLASICO)
    assert modelo.laberinto_cada == 0
    _serpiente_corta_en_centro(modelo)
    for _ in range(10):
        assert logica.actualizar(modelo) == "seguir"
    assert modelo.obstaculos == []
    assert not any(e == "laberinto_cambio" for e in modelo.eventos)


def test_laberinto_obstaculo_mata(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL, ModoJuego.LABERINTO)
    assert modelo.obstaculos
    ox, oy = modelo.obstaculos[0]
    # Cabeza justo antes del obstáculo, mirando hacia él.
    modelo.serpiente = [(ox - 25, oy), (ox - 50, oy)]
    modelo.direccion = (25, 0)
    modelo.cola_dir = []
    modelo.bombas = []
    assert logica.actualizar(modelo) == "muerte"


def test_zen_tambien_muere_en_obstaculo_interno(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL, ModoJuego.ZEN)
    modelo.obstaculos = [(425, 350)]
    modelo.serpiente = [(400, 350), (375, 350)]
    modelo.direccion = (25, 0)
    modelo.cola_dir = []
    modelo.bombas = []
    assert logica.actualizar(modelo) == "muerte"


def test_records_separados_por_modo(tmp_path):
    gestor = GestorEstado(tmp_path / "e.json", tmp_path / "r.json")
    assert gestor.guardar_record(Dificultad.NORMAL, 50) is True
    # El Zen empieza de cero aunque el Clásico tenga 50.
    assert gestor.record_para(Dificultad.NORMAL, "Zen") == 0
    assert gestor.guardar_record(Dificultad.NORMAL, 30, "Zen") is True
    assert gestor.record_para(Dificultad.NORMAL, "Zen") == 30
    assert gestor.record_para(Dificultad.NORMAL) == 50
    # El Clásico conserva la clave histórica (compatible con versiones viejas).
    assert gestor.leer_records()["Normal"] == 50


def test_modo_persiste_en_prefs(tmp_path):
    from snake_game.core.guardado import EstadoJugador

    gestor = GestorEstado(tmp_path / "e.json", tmp_path / "r.json")
    gestor.guardar_estado(EstadoJugador(dificultad="Normal", musica_activa=True,
                                        ultimo_record=0, modo="Laberinto"))
    assert gestor.leer_estado().modo == "Laberinto"
    gestor.ruta_estado.write_text('{"modo": "Inexistente"}', encoding="utf-8")
    assert gestor.leer_estado().modo == "Clasico"


def test_rotacion_respeta_vecinos_de_la_cabeza(logica):
    modelo = logica.iniciar_partida(Dificultad.NORMAL, ModoJuego.LABERINTO)
    _serpiente_corta_en_centro(modelo)
    for _ in range(3):
        modelo.tiempo_hasta_laberinto = 1
        assert logica.actualizar(modelo) == "seguir"
        cx, cy = modelo.cabeza()
        vecinos = {(cx + 25, cy), (cx - 25, cy), (cx, cy + 25), (cx, cy - 25)}
        muros = set(modelo.obstaculos)
        assert modelo.cabeza() not in muros
        assert not (muros & vecinos)
