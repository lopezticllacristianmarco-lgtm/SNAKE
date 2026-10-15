# 🐍 SNAKE GAME — Edición Profesional

Una reescritura profesional del clásico Snake. Arquitectura por capas,
máquina de estados, persistencia robusta, audio auto-generado y tests
unitarios. Sin dependencias más allá de **pygame** y **pytest**.

## 🚀 Cómo ejecutar

En **Windows**, lo más sencillo es usar los scripts incluidos:

```bat
instalar.bat     :: instala Python (si falta), pygame y el juego (1 sola vez)
ejecutar.bat     :: abre el juego
```

> `instalar.bat` también abre el puerto 5555 en el Firewall de Windows
> automáticamente, necesario para jugar en red.

O a mano (Linux / macOS / avanzado):

```bat
pip install -r requirements.txt
python -m snake_game
```

O instalarlo como paquete (crea el comando `snake`):

```bat
pip install -e .
snake
```

> Funciona desde cualquier directorio: los assets se resuelven con la ruta
> absoluta del paquete, no con el directorio actual.

## 🌐 Multijugador en red local (LAN)

- **SER ANFITRIÓN**: una de las máquinas crea la sala. Se muestra un **código
  de 4 dígitos** además de la IP y el puerto (5555). En la sala, el anfitrión
  elige **dificultad** (click o `←`/`→`) y **modo** (click o `T`):
  Clásico, Zen, Contrarreloj o Laberinto. La otra máquina se une.
   - Conecta ambos PCs a la **misma red Wi-Fi / router**.
   - Al ser anfitrión se intenta abrir el puerto 5555 en el Firewall de Windows.
     Si Windows pide permiso, acéptalo (o ejecuta `instalar.bat` como
     **administrador** la primera vez).
- **UNIRSE A PARTIDA**: la segunda máquina escribe el **código de 4 dígitos**
  (o la IP directa) del anfitrión y pulsa `ENTER`. Debe funcionar en segundos.
- No hacen falta dos anfitriones: uno crea la sala (anfitrión) y el otro se
  une (invitado). Si el invitado no conecta, revisa firewall y que ambos estén
  en la misma red.

## 📶 Multijugador por internet (datos móviles)

EL modo local no sirve cuando el celular está con datos móviles (CGNAT:
las operadoras no permiten conexiones entrantes). Para eso está el **relay**:
un servidor público que conecta hacia fuera con cada jugador y reenvía las
tramas del juego entre los dos.

1. **Arranca el relay** en cualquier máquina con IP pública (VPS, tu router
   con port-forward, o un túnel tipo ngrok):
   ```bat
   python -m snake_game.relay 5556
   ```
   El anfitrión y el invitado se conectan con esta dirección.
2. En el juego, elige la **RED: INTERNET (MOVIL)** en el menú Multijugador.
3. **SER ANFITRIÓN**: crea la sala; el relay asigna un **código de 4 dígitos**.
   El invitado los escribe en cualquier parte del mundo (móvil + datos o Wi-Fi).
4. No hace falta abrir puertos ni configurar el firewall en modo internet.

Para usar tu propio relay, define su dirección antes de arrancar el juego:

```bat
set SNAKE_RELAY=midominio.com:5556
python -m snake_game
```

> El relay por defecto es `127.0.0.1:5556` (solo pruebas locales). En el APK
> de Android se compila apuntando al relay público que elijas.

## 📱 Android (APK)

El juego corre en Android (touch = deslizar el dedo hacia la dirección). Dos
formas de obtener el APK:

- **GitHub Actions (recomendado):** haz push del repo a GitHub; el workflow
  `.github/workflows/build-apk.yml` compila el APK en la nube y lo sube como
  artefacto (sin instalar nada en tu PC).
- **Local:** instala Linux/WSL con `buildozer` y ejecuta
  `buildozer android debug` (el APK queda en `bin/`).

## 🎮 Controles

| Tecla            | Acción                 |
|------------------|------------------------|
| `W` / `↑`        | Mover arriba           |
| `S` / `↓`        | Mover abajo            |
| `A` / `←`        | Mover a la izquierda   |
| `D` / `→`        | Mover a la derecha     |
| `ESC` / `P`      | Pausar / reanudar      |
| `T`              | Cambiar modo de juego (menú / sala) |
| `M`              | Activar / silenciar música |
| `ENTER`          | Reiniciar (fin de partida) |

**Móvil (Android):** desliza el dedo hacia arriba / abajo / izquierda / derecha
para mover la serpiente. El menú y los botones se tocan directamente.

## ⚙️ Características

- **Dificultades**: Fácil, Normal, Difícil y Extremo (velocidad, bombas y
  cuota de nivel se escalan automáticamente).
- **Modos de juego**: Clásico, Zen (atraviesa los muros), Contrarreloj
  (60s en Fácil, 40s en Normal, 25s en Difícil, 15s en Extremo; cada
  manzana suma +3s, la dorada +5s) y Laberinto (muros internos letales
  que rotan solos: cada 30s en Fácil, 20s en Normal, 15s en Difícil
  y 10s en Extremo).
  Récords y última selección se guardan por modo.
- **Power-ups**: Dorada (+30), Escudo (rompe 1 bomba) y Lento.
- **Ajustes**: nombre de jugador (editable, por defecto `JUGADOR`), volumen
  de música y efectos y teclas reasignables (las flechas siempre valen).
  Todo persiste entre sesiones.
- **Se adapta sola**: la ventana se ajusta a cada pantalla conservando el
  aspecto (render escalado, sin configurar nada).
- **Multijugador con reglas**: el anfitrión elige dificultad y modo en la
  sala; el invitado interpola snapshots para movimiento suave; protocolo
  versionado (incompatibles se rechazan con aviso).
- **Sistema de niveles**: se sube de nivel completando la cuota de frutas.
- **Bombas** con tiempo de vida, sonido y animación de destello.
- **Partículas** al comer y efectos de brillo neón procedurales.
- **Récords por dificultad** y modo, con el nombre del jugador, guardados
  en JSON en `%APPDATA%/SnakeGame`
  (Windows) o `~/.snake_game` (Linux/macOS).
- **Audio autosuficiente**: si falla un `.wav`, se genera uno con síntesis
  (stdlib) en `snake_game/assets`.
- **Pausa, instrucciones, pantalla de récords** y transición suave entre
  pantallas.

## 🧩 Arquitectura

```
snake/
├── src/snake_game/
│   ├── config.py     # constantes, colores, dificultades, modos, rutas
│   ├── audio.py      # gestor de sonido + síntesis WAV (stdlib)
│   ├── app.py        # estado compartido y bucle principal
│   ├── escenas/      # una mezcla por pantalla (menu, sala, juego, multi, ajustes)
│   ├── red.py        # multijugador TCP en red local (host/invitado, protocolo V=1)
│   ├── relay.py      # relay público para jugar por internet (móvil)
│   ├── core/
│   │   ├── modelos.py   # modelos de dominio (sin pygame)
│   │   ├── logica.py    # reglas del juego (sin pygame, determinista)
│   │   ├── multijugador.py  # simulación 2J + interpolación de snapshots
│   │   └── guardado.py  # persistencia JSON (estado + récords)
│   └── ui/
│       ├── graficos.py  # fuentes, texto con brillo, botones
│       └── render.py    # renderizado de la partida
├── tests/             # tests unitarios (pytest) + smoke test headless
├── instalar.bat       # instalación automática (Windows)
└── ejecutar.bat       # lanzar el juego (Windows)
```

El núcleo (`core/`) no importa pygame: puede probarse y extenderse de forma
aislada. La interfaz (``ui/``) solo dibuja; la aplicación (``app.py``)
orquesta los cambios de estado.

## ✅ Pruebas

```bat
python -m pytest tests -q
python tests/smoke_test.py   # arranque headless de todas las escenas
python -m pytest tests/test_relay.py -q   # integración del relay (emparejamiento + reenvío)
```

## 🧾 Licencia

MIT. Créditos: Cristian López.