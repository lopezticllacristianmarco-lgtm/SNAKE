"""Audio manager.

Ensures every referenced sound exists. The original code silently failed
when ``comer.wav`` / ``perder.wav`` / ``ganar.wav`` / ``bomba.wav`` were
missing — this module *generates* a good-quality synth effect for any
missing file (sweeps, noise bursts, envelopes — stdlib only), so the game
always has enjoyable sound even on a fresh checkout.
"""

from __future__ import annotations

import logging
import math
import os
import random
import struct
import wave
from pathlib import Path

import pygame

from snake_game.config import MUSICA_RUTA, SONIDOS, VOLUMEN_MUSICA

logger = logging.getLogger(__name__)

_ES_ANDROID = "ANDROID_ARGUMENT" in os.environ

#: Extensiones que pygame.mixer.music reproduce de forma fiable.
EXTENSIONES_MUSICA = {".mp3", ".ogg", ".wav"}


def buscar_canciones(limite: int = 50) -> list[Path]:
    """Canciones del dispositivo (mp3/ogg/wav), ordenadas y sin duplicados.

    - PC: ~/Music, ~/Downloads, carpeta del juego y ``assets/``.
    - Android: Music/Download del almacenamiento (requiere permiso de audio).
    Nunca lanza: si no hay permiso o carpeta, devuelve lo que encuentre.
    """
    carpetas: list[Path] = []
    try:
        carpetas.append(Path.home() / "Music")
    except (RuntimeError, OSError):
        pass
    try:
        carpetas.append(Path.home() / "Download")
        carpetas.append(Path.home() / "Downloads")
    except (RuntimeError, OSError):
        pass
    if _ES_ANDROID:
        for base in ("/sdcard", "/storage/emulated/0"):
            carpetas.append(Path(base) / "Music")
            carpetas.append(Path(base) / "Download")
            carpetas.append(Path(base) / "Download" / "Music")
    else:
        carpetas.append(Path.cwd())
    try:
        from snake_game.config import ASSETS_DIR
        carpetas.append(ASSETS_DIR)
    except ImportError:
        pass

    encontradas: list[Path] = []
    vistos: set[str] = set()
    for carpeta in carpetas:
        try:
            if not carpeta.is_dir():
                continue
            for ruta in sorted(carpeta.iterdir()):
                if len(encontradas) >= limite:
                    break
                try:
                    if not ruta.is_file():
                        continue
                except OSError:
                    continue
                if ruta.suffix.lower() not in EXTENSIONES_MUSICA:
                    continue
                clave = str(ruta.resolve()) if hasattr(ruta, "resolve") else str(ruta)
                if clave in vistos:
                    continue
                vistos.add(clave)
                encontradas.append(ruta)
        except (OSError, PermissionError):
            continue
    return encontradas


def nombre_cancion(ruta: str | Path, maximo: int = 26) -> str:
    """Nombre corto para mostrar en la UI (sin extensión, recortado)."""
    if not ruta:
        return "ORIGINAL"
    nombre = Path(str(ruta)).stem.strip() or "CANCION"
    return nombre[:maximo] if len(nombre) <= maximo else nombre[:maximo - 1] + "…"

_SAMPLERATE = 44100
_SCALAR = 0.8 * 32767


# --------------------------------------------------------------------------
# Pure synth (stdlib only)
# --------------------------------------------------------------------------
def _tono_con_sweep(frecuencia: float, duracion: float, volumen: float,
                    decaimiento: float = 3.0, barrido: float = 1.0,
                    armonicos: float = 0.25, vibrato_hz: float = 0.0) -> bytes:
    """Sine with exponential decay, optional pitch sweep and harmonics.

    ``barrido`` > 1 rises (pop, pickup), < 1 falls (thump, explosion).
    ``armonicos`` is the weight of the 2nd/3rd harmonic for a brighter tone.
    """
    n = int(_SAMPLERATE * duracion)
    muestras = bytearray()
    vib = 0.0
    for i in range(n):
        t = i / _SAMPLERATE
        f_actual = frecuencia * (barrido ** (t / max(duracion, 1e-9)))
        if vibrato_hz:
            vib += 2 * math.pi * vibrato_hz / _SAMPLERATE
        env = math.exp(-decaimiento * t)
        w = 2 * math.pi * f_actual * t + vib * 0.015
        onda = math.sin(w) + armonicos * (0.5 * math.sin(2 * w) + 0.25 * math.sin(3 * w))
        valor = int(_SCALAR * volumen * env * onda)
        muestras += struct.pack("<h", max(-32767, min(32767, valor)))
    return bytes(muestras)


def _ruido(duracion: float, volumen: float, decaimiento: float = 5.0,
           retardo: float = 0.0) -> bytes:
    """White-noise burst with a decaying envelope (explosions, crackle)."""
    n = int(_SAMPLERATE * duracion)
    retardo_n = int(_SAMPLERATE * retardo)
    muestras = bytearray()
    rng = random.Random(0x5EA)
    acumulado = 0.0
    for i in range(n):
        t = i / _SAMPLERATE
        env = math.exp(-decaimiento * t) if t > 0 else 0
        if i < retardo_n:
            valor = 0
        else:
            impulso = rng.uniform(-1.0, 1.0)
            acumulado += 0.2 * (impulso - acumulado)  # soft low-pass
            valor = int(_SCALAR * volumen * env * acumulado * 2.2)
        muestras += struct.pack("<h", max(-32767, min(32767, valor)))
    return bytes(muestras)


def _concatenar(*trozos: bytes, silencio_entre: float = 0.0) -> bytes:
    """Stack PCM chunks; optionally inserting a short silence between them."""
    if silencio_entre:
        silencio = b"\x00\x00" * int(_SAMPLERATE * silencio_entre)
    else:
        silencio = b""
    return silencio.join(trozos)


def _suavizar(pcm: bytes) -> bytes:
    """Soft-knee limiter to avoid hard clipping on multi-layer mixes."""
    salida = bytearray(len(pcm))
    for i in range(0, len(pcm), 2):
        muestra = struct.unpack_from("<h", pcm, i)[0]
        x = muestra / 32767.0
        y = math.tanh(x * 1.6)
        salida[i:i + 2] = struct.pack("<h", int(y * _SCALAR))
    return bytes(salida)


def generar_wav(ruta, *trozos: bytes) -> None:
    """Write PCM bytes to a mono 16-bit WAV file."""
    politono = _suavizar(_concatenar(*trozos))
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(_SAMPLERATE)
        w.writeframesraw(politono)


def _sintetizar(ruta, nombre: str) -> None:
    """Create a juicy game-sensible SFX for a missing file."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if nombre == "comer":
        # Rising chirp + sparkle + tiny click: classic "pickup".
        base = _tono_con_sweep(frecuencia=920, duracion=0.09, volumen=0.55,
                               decaimiento=14.0, barrido=1.7, armonicos=0.5)
        brillo = _tono_con_sweep(frecuencia=1560, duracion=0.11, volumen=0.3,
                                 decaimiento=12.0, barrido=1.5, armonicos=0.3)
        generar_wav(ruta, base, brillo, _ruido(0.02, 0.25, 30.0))
    elif nombre == "bomba":
        # Noise blast + sub-bass thump with a falling pitch.
        blast = _ruido(0.42, 0.75, decaimiento=6.5)
        thump = _tono_con_sweep(frecuencia=110, duracion=0.5, volumen=0.9,
                                decaimiento=5.5, barrido=0.45, armonicos=0.4)
        crackle = _ruido(0.30, 0.35, decaimiento=14.0, retardo=0.02)
        generar_wav(ruta, blast, thump, crackle)
    elif nombre == "perder":
        # Two descending sighs: sad but soft.
        baja = _tono_con_sweep(frecuencia=330, duracion=0.6, volumen=0.5,
                               decaimiento=2.6, barrido=0.55, armonicos=0.35)
        grave = _tono_con_sweep(frecuencia=196, duracion=0.7, volumen=0.45,
                                decaimiento=2.6, barrido=0.45, armonicos=0.25)
        generar_wav(ruta, baja, grave)
    elif nombre == "ganar":
        # Major arpeggio with sparkle (C5 E5 G5 C6).
        notas = []
        for nota, dur, barrido in ((523, 0.16, 1.12), (659, 0.16, 1.12),
                                   (784, 0.16, 1.12), (1047, 0.42, 1.0)):
            notas.append(_tono_con_sweep(nota, dur, 0.45, decaimiento=3.2,
                                         barrido=barrido, armonicos=0.5,
                                         vibrato_hz=6.0))
        final = _tono_con_sweep(2093, 0.28, 0.2, decaimiento=6.0, armonicos=0.6)
        generar_wav(ruta, _concatenar(*notas, final, silencio_entre=0.03))
    else:  # pragma: no cover
        generar_wav(ruta, _tono_con_sweep(440, 0.2, 0.4, 4.0))


def asegurar_sonidos() -> None:
    """Create every missing sound using synthesis. Never raises."""
    for nombre, ruta in SONIDOS.items():
        if not ruta.exists():
            logger.info("Generando sonido sintetizado: %s", nombre)
            try:
                _sintetizar(ruta, nombre)
            except OSError as exc:  # pragma: no cover
                logger.warning("No se pudo generar %s: %s", ruta, exc)


# --------------------------------------------------------------------------
# Pygame-driven player
# --------------------------------------------------------------------------
class Audio:
    """Loads generated sounds and streams background music."""

    def __init__(self) -> None:
        self.disponible = False
        self.musica_activa = True
        self.volumen_musica = VOLUMEN_MUSICA
        self.volumen_efectos = 0.8
        # Canción elegida del dispositivo (ruta absoluta o ""); "" = original.
        self.musica_custom: str = ""
        self.sonidos: dict[str, pygame.mixer.Sound] = {}

        try:
            pygame.mixer.init()
            self.disponible = True
        except pygame.error as exc:
            logger.warning("Audio no disponible: %s", exc)
            return

        for nombre, ruta in SONIDOS.items():
            try:
                self.sonidos[nombre] = pygame.mixer.Sound(str(ruta))
            except (pygame.error, OSError) as exc:
                logger.warning("No se pudo cargar %s: %s", nombre, exc)

    # -- música ----------------------------------------------------------
    def ruta_musica_actual(self) -> Path:
        """La canción a reproducir: la del dispositivo si existe, si no la original."""
        if self.musica_custom:
            custom = Path(self.musica_custom)
            if custom.is_file():
                return custom
        return MUSICA_RUTA

    def definir_musica(self, ruta: str | Path | None) -> bool:
        """Elige la canción del dispositivo ("" / None = original). Reinicia si suena."""
        texto = "" if ruta is None else str(ruta).strip()
        if texto and not Path(texto).is_file():
            return False
        self.musica_custom = texto
        if self.musica_activa and self.disponible:
            self.iniciar_musica()
        return True

    def iniciar_musica(self) -> None:
        if not self.disponible or not self.musica_activa:
            return
        ruta = self.ruta_musica_actual()
        if not ruta.exists():
            logger.warning("No se encuentra la musica: %s", ruta)
            return
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(str(ruta))
            pygame.mixer.music.set_volume(self.volumen_musica)
            pygame.mixer.music.play(-1)
        except (pygame.error, OSError) as exc:
            logger.warning("No se pudo reproducir la música: %s", exc)

    def pausar_musica(self) -> None:
        if not self.disponible:
            return
        try:
            pygame.mixer.music.pause()
        except pygame.error:
            pass

    def reanudar_musica(self) -> None:
        if not self.disponible:
            return
        try:
            pygame.mixer.music.unpause()
        except pygame.error:
            pass

    def detener_musica(self) -> None:
        if not self.disponible:
            return
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass

    # -- efectos ----------------------------------------------------------
    def reproducir(self, nombre: str, volumen: float = 0.8) -> None:
        """Play one of ``comer``, ``perder``, ``ganar``, ``bomba``."""
        if not self.disponible:
            return
        sonido = self.sonidos.get(nombre)
        if sonido is None:
            return
        try:
            sonido.set_volume(max(0.0, min(1.0, volumen * self.volumen_efectos)))
            sonido.play()
        except pygame.error:  # pragma: no cover
            pass

    def aplicar_volumen_musica(self) -> None:
        """Reaplica el volumen sin reiniciar la pista (para el slider)."""
        if not self.disponible:
            return
        try:
            pygame.mixer.music.set_volume(self.volumen_musica)
        except pygame.error:  # pragma: no cover
            pass

    def cerrar(self) -> None:
        if self.disponible:
            try:
                pygame.mixer.quit()
            except pygame.error:
                pass
