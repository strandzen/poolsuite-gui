# poolsuite-gui

A retro cassette-deck desktop player for [Poolsuite FM](https://poolsuite.net/)'s
curated SoundCloud playlists. Native Linux GUI — no Electron, no browser, no
webview. Just Tkinter, cairo-rendered skeuomorphic graphics, and mpv doing the
heavy lifting over its JSON IPC socket.

<!-- TODO: add docs/screenshot.png and restore: ![screenshot](docs/screenshot.png) -->

## Features

- Silver cassette-recorder interface: smoked tape window, twin spinning reels,
  piano-key transport controls
- Reels spin with tape-deck physics — wind down on pause, spin up on play,
  full 360° flick on track skip or playlist change
- 8 Poolsuite FM playlists, switchable from the deck
- Play/pause, prev/next, shuffle, mute (latching key), volume popup
- All graphics rendered at 2x and downscaled — crisp at native size
- Audio handled entirely by mpv; the GUI is a remote control

## Requirements

- Python 3 with Tkinter
- [mpv](https://mpv.io/) (with yt-dlp for SoundCloud resolution)
- pycairo
- Pillow

Arch/CachyOS:

```sh
sudo pacman -S mpv yt-dlp tk python-cairo python-pillow
```

## Run

```sh
python3 main.py
```

## Install (app menu entry)

```sh
./install.sh
```

Installs a `.desktop` entry to `~/.local/share/applications` pointing at this
checkout.

## How it works

`main.py` wires two halves together:

- `mpv_client.py` spawns `mpv --no-video --idle=yes --input-ipc-server=...`,
  observes `media-title` / `pause` / `volume` / `mute` / `duration` /
  `time-pos` over the socket, and pushes state changes from a reader thread.
- `ui.py` + `theme.py` draw the deck. The body, reels, and keys are rendered
  once with cairo/Pillow at startup; animation is just swapping pre-rendered
  reel frames on a 60 fps `after()` loop with real elapsed-time physics.

## Credits

- All music curation by [Poolsuite FM](https://poolsuite.net/) — support them.
- Playlist mapping based on
  [jamespember/poolsuite-cli](https://github.com/jamespember/poolsuite-cli).
- This is an unofficial tool that streams Poolsuite's public SoundCloud
  playlists. Not affiliated with Poolsuite FM.

## License

MIT — see [LICENSE](LICENSE).
