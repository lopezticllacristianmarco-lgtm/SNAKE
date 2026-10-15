"""Unit tests for the persistence layer (JSON robustness)."""

import json

import pytest

from snake_game.config import Dificultad
from snake_game.core.guardado import GestorEstado


@pytest.fixture
def gestor(tmp_path):
    return GestorEstado(
        ruta_estado=tmp_path / "estado.json",
        ruta_records=tmp_path / "records.json",
    )


def test_estado_por_defecto(gestor):
    estado = gestor.leer_estado()
    assert estado.musica_activa is True
    assert estado.dificultad == Dificultad.NORMAL.value


def test_ciclo_estado(gestor):
    from snake_game.core.guardado import EstadoJugador

    gestor.guardar_estado(EstadoJugador(dificultad="Extremo", musica_activa=False, ultimo_record=120))
    estado = gestor.leer_estado()
    assert estado.dificultad == "Extremo"
    assert estado.musica_activa is False
    assert estado.ultimo_record == 120


def test_dificultad_invalida_se_normaliza(gestor):

    gestor.ruta_estado.write_text(json.dumps({"dificultad": "Imposible"}), encoding="utf-8")
    assert gestor.leer_estado().dificultad == Dificultad.NORMAL.value


def test_archivo_corrupto_no_peta(gestor):
    gestor.ruta_estado.write_text("{esto no es json", encoding="utf-8")
    estado = gestor.leer_estado()
    assert estado.dificultad == "Normal"


def test_guardar_record_actualiza(gestor):
    assert gestor.record_para(Dificultad.NORMAL) == 0
    assert gestor.guardar_record(Dificultad.NORMAL, 50) is True
    assert gestor.guardar_record(Dificultad.NORMAL, 30) is False  # no baja
    assert gestor.record_para(Dificultad.NORMAL) == 50
    assert gestor.guardar_record(Dificultad.NORMAL, 80) is True
    assert gestor.record_para(Dificultad.NORMAL) == 80


def test_mejores_records_ordenados(gestor):
    gestor.guardar_record(Dificultad.FACIL, 10)
    gestor.guardar_record(Dificultad.EXTREMO, 500)
    gestor.guardar_record(Dificultad.NORMAL, 42)
    mejores = gestor.mejores_records()
    assert mejores[0] == ("Extremo", 500)
    assert [v for _, v in mejores] == sorted((v for _, v in mejores), reverse=True)


def test_ignora_valores_invalidos(gestor):
    gestor.ruta_records.write_text(json.dumps({"records": {"Normal": "x", "Dificil": -3}}),
                                   encoding="utf-8")
    assert gestor.record_para(Dificultad.NORMAL) == 0
    assert gestor.record_para(Dificultad.DIFICIL) == 0


def test_normalizar_nombre():
    from snake_game.core.guardado import normalizar_nombre

    assert normalizar_nombre("  Ana  ") == "Ana"
    assert normalizar_nombre("") == "JUGADOR"
    assert normalizar_nombre("   ") == "JUGADOR"
    assert normalizar_nombre(None) == "JUGADOR"
    assert normalizar_nombre("a" * 30) == "a" * 12


def test_nombre_persiste(gestor):
    from snake_game.core.guardado import EstadoJugador

    gestor.guardar_estado(EstadoJugador(nombre="  Beto "))
    assert gestor.leer_estado().nombre == "Beto"
    assert GestorEstado(gestor.ruta_estado, gestor.ruta_records).leer_estado().nombre == "Beto"


def test_records_guardan_nombre(gestor):
    assert gestor.guardar_record(Dificultad.NORMAL, 50, nombre="Ana") is True
    assert gestor.guardar_record(Dificultad.NORMAL, 30, nombre="Beto") is False
    detalle = gestor.leer_records_detalle()
    assert detalle["Normal"] == (50, "Ana")
    assert gestor.record_para(Dificultad.NORMAL) == 50
    assert gestor.mejores_records_detalle()[0] == ("Normal", 50, "Ana")


def test_records_viejos_sin_nombre_siguen_valiendo(gestor):
    gestor.ruta_records.write_text(json.dumps({"records": {"Normal": 42}}),
                                   encoding="utf-8")
    assert gestor.record_para(Dificultad.NORMAL) == 42
    assert gestor.leer_records_detalle()["Normal"] == (42, "")
