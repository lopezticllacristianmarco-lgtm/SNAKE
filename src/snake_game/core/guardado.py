"""Persistence layer — state file and record tables as JSON.

Replaces the fragile single-line ``record.txt`` of the original with a
versioned, validated JSON store kept outside the game folder (AppData on
Windows, ``~/.snake_game`` elsewhere). Corruption never crashes the game:
a bad file is backed up and replaced.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from snake_game.config import (
    ARCHIVO_ESTADO,
    ARCHIVO_RECORDS,
    SKINS,
    SKIN_POR_DEFECTO,
    Dificultad,
    ModoJuego,
    skin_valida,
)

logger = logging.getLogger(__name__)


def _cargar_json(ruta: Path, por_defecto) -> dict:
    """Load a JSON file, tolerating missing/corrupt content."""
    try:
        with open(ruta, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("root is not an object")
        return data
    except FileNotFoundError:
        return dict(por_defecto)
    except (json.JSONDecodeError, ValueError, OSError) as exc:
        logger.warning("No se pudo leer %s (%s); se usara estado limpio.", ruta, exc)
        try:
            shutil.copyfile(ruta, ruta.with_suffix(ruta.suffix + ".bak"))
        except OSError:
            pass
        return dict(por_defecto)


def _guardar_json(ruta: Path, data: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(ruta.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(ruta)


@dataclass
class EstadoJugador:
    """Non-gameplay preferences persisted between sessions."""

    dificultad: str = Dificultad.NORMAL.value
    musica_activa: bool = True
    ultimo_record: int = 0
    modo: str = ModoJuego.CLASICO.value
    volumen_musica: float = 0.5
    volumen_efectos: float = 0.8
    teclas: dict = field(default_factory=dict)
    nombre: str = "JUGADOR"
    # Monedero persistente: se conserva aunque pierdas la partida.
    monedas: int = 0
    # Skins desbloqueadas (ids del catálogo) y skin equipada.
    skins: list = field(default_factory=lambda: [SKIN_POR_DEFECTO])
    skin_activa: str = SKIN_POR_DEFECTO
    # Canción elegida del dispositivo (ruta absoluta; "" = música original).
    musica_custom: str = ""


NOMBRE_POR_DEFECTO = "JUGADOR"
NOMBRE_MAXIMO = 12
RUTA_MUSICA_MAXIMO = 512


def normalizar_musica_custom(ruta) -> str:
    """Ruta de música válida o "" (no exige que el archivo aún exista)."""
    if not isinstance(ruta, str):
        return ""
    limpio = ruta.strip()
    if not limpio or len(limpio) > RUTA_MUSICA_MAXIMO:
        return ""
    if "\x00" in limpio:
        return ""
    return limpio


NOMBRE_POR_DEFECTO = "JUGADOR"
NOMBRE_MAXIMO = 12


def normalizar_nombre(nombre) -> str:
    """Nombre visible: imprimible, recortado, nunca vacío."""
    if not isinstance(nombre, str):
        return NOMBRE_POR_DEFECTO
    limpio = "".join(c for c in nombre.strip() if c.isprintable()).strip()
    return limpio[:NOMBRE_MAXIMO] or NOMBRE_POR_DEFECTO


ACCIONES_TECLAS = ("arriba", "abajo", "izq", "der", "pausa")

# WASD + P por defecto (códigos pygame; las flechas siempre funcionan).
TECLAS_POR_DEFECTO = {"arriba": 119, "abajo": 115, "izq": 97, "der": 100,
                      "pausa": 112}


def normalizar_teclas(teclas) -> dict:
    """Filtra un dict cargado: solo acciones conocidas con códigos enteros."""
    limpias = dict(TECLAS_POR_DEFECTO)
    if isinstance(teclas, dict):
        for accion in ACCIONES_TECLAS:
            valor = teclas.get(accion)
            if isinstance(valor, int) and 0 < valor < 1024:
                limpias[accion] = valor
    return limpias


def clave_record(dificultad: Dificultad, modo: str = ModoJuego.CLASICO.value) -> str:
    """Clave de récord: el Clásico reuse la clave histórica (compatible)."""
    if modo in ("", ModoJuego.CLASICO.value, None):
        return dificultad.value
    return f"{modo}/{dificultad.value}"


def normalizar_skins(skins) -> list[str]:
    """Lista de ids válidos, siempre con la skin por defecto incluida."""
    limpias: list[str] = []
    if isinstance(skins, (list, tuple)):
        for s in skins:
            if isinstance(s, str) and s in SKINS and s not in limpias:
                limpias.append(s)
    if SKIN_POR_DEFECTO not in limpias:
        limpias.insert(0, SKIN_POR_DEFECTO)
    return limpias


class GestorEstado:
    """Loads/saves :class:`EstadoJugador` and the per-difficulty records."""

    def __init__(self, ruta_estado: Path | None = None, ruta_records: Path | None = None) -> None:
        self.ruta_estado = ruta_estado or ARCHIVO_ESTADO
        self.ruta_records = ruta_records or ARCHIVO_RECORDS

    # -- estado ---------------------------------------------------------
    def leer_estado(self) -> EstadoJugador:
        data = _cargar_json(self.ruta_estado, {})
        dificultad = data.get("dificultad", "")
        if dificultad not in {d.value for d in Dificultad}:
            dificultad = Dificultad.NORMAL.value
        modo = data.get("modo", ModoJuego.CLASICO.value)
        if modo not in {m.value for m in ModoJuego}:
            modo = ModoJuego.CLASICO.value
        try:
            volumen_musica = float(data.get("volumen_musica", 0.5))
        except (TypeError, ValueError):
            volumen_musica = 0.5
        try:
            volumen_efectos = float(data.get("volumen_efectos", 0.8))
        except (TypeError, ValueError):
            volumen_efectos = 0.8
        skins = normalizar_skins(data.get("skins"))
        activa = skin_valida(str(data.get("skin_activa", SKIN_POR_DEFECTO)))
        if activa not in skins:
            activa = SKIN_POR_DEFECTO
        try:
            monedas = max(0, int(data.get("monedas", 0) or 0))
        except (TypeError, ValueError):
            monedas = 0
        return EstadoJugador(
            dificultad=dificultad,
            musica_activa=bool(data.get("musica_activa", True)),
            ultimo_record=int(data.get("ultimo_record", 0)),
            modo=modo,
            volumen_musica=min(1.0, max(0.0, volumen_musica)),
            volumen_efectos=min(1.0, max(0.0, volumen_efectos)),
            teclas=normalizar_teclas(data.get("teclas")),
            nombre=normalizar_nombre(data.get("nombre")),
            monedas=monedas,
            skins=skins,
            skin_activa=activa,
            musica_custom=normalizar_musica_custom(data.get("musica_custom", "")),
        )

    def guardar_estado(self, estado: EstadoJugador) -> None:
        skins = normalizar_skins(estado.skins)
        activa = skin_valida(estado.skin_activa)
        if activa not in skins:
            activa = SKIN_POR_DEFECTO
        _guardar_json(
            self.ruta_estado,
            {
                "version": 1,
                "dificultad": estado.dificultad,
                "musica_activa": estado.musica_activa,
                "ultimo_record": estado.ultimo_record,
                "modo": estado.modo,
                "volumen_musica": estado.volumen_musica,
                "volumen_efectos": estado.volumen_efectos,
                "teclas": normalizar_teclas(estado.teclas),
                "nombre": normalizar_nombre(estado.nombre),
                "monedas": max(0, int(estado.monedas or 0)),
                "skins": skins,
                "skin_activa": activa,
                "musica_custom": normalizar_musica_custom(estado.musica_custom),
            },
        )

    # -- records --------------------------------------------------------
    @staticmethod
    def _puntos_y_nombre(valor) -> tuple[int, str] | None:
        """Acepta récord histórico (int) y nuevo ({"puntos", "nombre"})."""
        if isinstance(valor, int) and valor >= 0:
            return valor, ""
        if isinstance(valor, dict):
            puntos = valor.get("puntos")
            if isinstance(puntos, int) and puntos >= 0:
                nombre = valor.get("nombre") or ""
                nombre = normalizar_nombre(nombre) if nombre else ""
                return puntos, nombre
        return None

    def leer_records_detalle(self) -> dict[str, tuple[int, str]]:
        """Récords como {clave: (puntos, nombre)}."""
        data = _cargar_json(self.ruta_records, {})
        registros = data.get("records", {})
        limpios: dict[str, tuple[int, str]] = {}
        for clave, valor in registros.items():
            if not isinstance(clave, str):
                continue
            es_base = any(clave == d.value for d in Dificultad)
            if not (es_base or "/" in clave):
                continue
            parsedo = self._puntos_y_nombre(valor)
            if parsedo is not None:
                limpios[clave] = parsedo
        return limpios

    def leer_records(self) -> dict[str, int]:
        return {c: p for c, (p, _) in self.leer_records_detalle().items()}

    def record_para(self, dificultad: Dificultad,
                    modo: str = ModoJuego.CLASICO.value) -> int:
        return self.leer_records().get(clave_record(dificultad, modo), 0)

    def guardar_record(self, dificultad: Dificultad, puntaje: int,
                       modo: str = ModoJuego.CLASICO.value,
                       nombre: str = NOMBRE_POR_DEFECTO) -> bool:
        """Store the score for a difficulty+mode. Returns True when it beats it."""
        records = self.leer_records_detalle()
        clave = clave_record(dificultad, modo)
        anterior = records.get(clave, (0, ""))[0]
        if puntaje > anterior:
            records[clave] = (puntaje, normalizar_nombre(nombre))
            _guardar_json(self.ruta_records, {
                "version": 1,
                "records": {c: {"puntos": p, "nombre": n}
                            for c, (p, n) in records.items()},
            })
            return True
        return False

    def mejores_records(self) -> list[tuple[str, int]]:
        """Records ordered best-first for the record screen."""
        records = self.leer_records()
        return sorted(records.items(), key=lambda item: item[1], reverse=True)

    def mejores_records_detalle(self) -> list[tuple[str, int, str]]:
        """(clave, puntos, nombre) ordenados de mejor a peor."""
        detalle = self.leer_records_detalle()
        return sorted(((c, p, n) for c, (p, n) in detalle.items()),
                      key=lambda item: item[1], reverse=True)
