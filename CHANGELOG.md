# Changelog

Todos los cambios notables de Snake Game se documentan aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

## [1.1.0] - 2026-09-10

### Agregado
- Nombre de jugador (por defecto `JUGADOR`, editable en Ajustes): aparece en
  récords y en el multijugador (sala, pantalla final); viaja en el handshake.
- VOLVER de Ajustes responde al click (no estaba cableado).
- Sin modo pantalla completa: la ventana se auto-ajusta a cada pantalla
  (SCALED + fallback si el driver no lo soporta).
- Multijugador: aparición separada (sin muerte al entrar) y rotación de
  laberinto que nunca pega muros a tu cabeza.

### Agregado
- Menú de Ajustes: volumen de música y efectos, pantalla completa y
  reasignación de teclas (persistentes).
- Interpolación del invitado en multijugador (movimiento suave entre snapshots).
- Versión de protocolo de red (`V: 1` en HELLO/HOLA/REG); conexiones con
  versión distinta se rechazan con mensaje claro.
- El anfitrión elige dificultad y modo en la sala (multijugador).
- CI: tests + ruff en cada push/PR.

### Cambiado
- `app.py` dividido en escenas (`snake_game/escenas/`).
- Récords del multijugador: pantalla de EMPATE cuando el crono iguala puntos.

## [1.0.0] - 2026-09-09

### Agregado
- Modos de juego: Clásico, Zen, Contrarreloj (60/40/25/15s + bonus por comer)
  y Laberinto rotativo (30/20/15/10s por dificultad).
- Power-ups: Dorada (+30), Escudo y Lento.
- Multijugador LAN + relay por internet, con empate en crono.
- Audio sintetizado (stdlib), récords por modo, APK vía GitHub Actions.
- Tests unitarios + smoke test headless.
