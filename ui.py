import math
import time
import tkinter as tk

import theme
from playlists import PLAYLISTS

REEL_TICK_MS = 16  # ~60fps
REEL_STEADY_VELOCITY = 60.0    # degrees per second while playing
REEL_APPROACH_RATE = 1.94      # exponential chase constant (per second)
REEL_BURST_VELOCITY = 600.0    # degrees per second during a skip burst
REEL_BURST_DEGREES = 360.0     # extra rotation on skip/playlist change

KEY_DEFS = [
    # (strip name, key face text, red?)
    ("SHUFFLE", "SHUFFLE", True),
    ("PLAY", "PLAY\nPAUSE", False),
    ("REW", "REW", False),
    ("F.FWD", "F.FWD", False),
    ("MUTE", "MUTE", False),
    ("STOP", "STOP\nEJECT", False),
]


def _fmt_time(seconds):
    if seconds is None:
        return "--:--"
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


class PoolsuiteUI:
    def __init__(self, root):
        self.root = root
        root.title("poolsuite")
        root.geometry(f"{theme.WIDTH}x{theme.HEIGHT}")
        root.resizable(False, False)
        root.configure(bg=theme.BODY_HEX)

        self.canvas = tk.Canvas(
            root, width=theme.WIDTH, height=theme.HEIGHT, highlightthickness=0
        )
        self.canvas.pack()

        # keep references alive, Tk drops images with no live ref
        self.body_image = theme.render_body()
        self.canvas.create_image(0, 0, image=self.body_image, anchor="nw")

        self.reel_frames = theme.render_reel_frames()
        self.reel_angle = 0.0
        self.reel_velocity = 0.0
        self.reel_target_velocity = 0.0
        self.reel_burst_remaining = 0.0
        self.reel_items = [
            self.canvas.create_image(theme.REEL_L_CX, theme.REEL_CY, image=self.reel_frames[0]),
            self.canvas.create_image(theme.REEL_R_CX, theme.REEL_CY, image=self.reel_frames[0]),
        ]

        # callbacks, set by main.py
        self.on_play_pause = lambda: None
        self.on_next = lambda: None
        self.on_prev = lambda: None
        self.on_shuffle = lambda: None
        self.on_mute = lambda: None
        self.on_quit = lambda: None
        self.on_volume_change = lambda v: None
        self.on_playlist_change = lambda name: None

        self._last_pause_state = None
        self._volume_popup = None
        self.volume_var = tk.IntVar(value=100)
        self._latched = {"PLAY": False, "MUTE": False}

        self._build_keys()
        self._build_widgets()
        self._last_tick_time = time.perf_counter()
        self._reel_tick()

    # --- cassette keys as cairo-rendered canvas images ---
    def _build_keys(self):
        self._key_images = {}
        self._key_items = {}
        self._key_handlers = {
            "SHUFFLE": self._handle_shuffle,
            "PLAY": lambda: self.on_play_pause(),
            "REW": self._handle_prev,
            "F.FWD": self._handle_next,
            "MUTE": self._handle_mute,
            "STOP": lambda: self.on_quit(),
        }
        for i, (name, text, red) in enumerate(KEY_DEFS):
            normal = theme.render_key(text, red=red)
            pressed = theme.render_key(text, red=red, pressed=True)
            self._key_images[name] = (normal, pressed)
            item = self.canvas.create_image(theme.key_x(i), theme.KEYS_CY, image=normal)
            self._key_items[name] = item
            self.canvas.tag_bind(item, "<ButtonPress-1>",
                                 lambda e, n=name: self._key_down(n))
            self.canvas.tag_bind(item, "<ButtonRelease-1>",
                                 lambda e, n=name: self._key_up(n))

    def _key_down(self, name):
        self._show_key(name, pressed=True)
        self._key_handlers[name]()

    def _key_up(self, name):
        # latched keys keep their pressed look from refresh() state
        if not self._latched.get(name, False):
            self._show_key(name, pressed=False)

    def _show_key(self, name, pressed):
        normal, down = self._key_images[name]
        self.canvas.itemconfigure(self._key_items[name], image=down if pressed else normal)

    def _set_latch(self, name, latched):
        if self._latched.get(name) != latched:
            self._latched[name] = latched
            self._show_key(name, pressed=latched)

    # --- Tk widgets ---
    def _build_widgets(self):
        # playlist selector, top center
        bar = tk.Frame(self.root, bg=theme.BODY_HEX)
        self.canvas.create_window(theme.WIDTH / 2, 30, window=bar)
        tk.Label(
            bar, text="PLAYLIST", font=theme.FONT_LABEL,
            fg=theme.LABEL_TEXT, bg=theme.BODY_HEX,
        ).pack(side=tk.LEFT, padx=(0, 6))
        self.playlist_var = tk.StringVar(value="official")
        self.playlist_menu = tk.OptionMenu(
            bar, self.playlist_var, *PLAYLISTS.keys(),
            command=self._handle_playlist_change,
        )
        self.playlist_menu.config(
            font=theme.FONT_TITLE, fg=theme.KEY_TEXT, bg=theme.KEY_HEX,
            activebackground=theme.BODY_DARK_HEX, relief=tk.RAISED, bd=2,
            highlightthickness=0, width=10,
        )
        self.playlist_menu.pack(side=tk.LEFT)

        # track name, top center of cassette window (between the reels)
        self.track_var = tk.StringVar(value="-- no tape --")
        self.track_label = tk.Label(
            self.root, textvariable=self.track_var, font=theme.FONT_TRACK,
            fg=theme.WINDOW_TEXT, bg=theme.WINDOW_HEX,
            wraplength=theme.WIN_X1 - theme.WIN_X0 - 160, justify=tk.CENTER,
        )
        self.canvas.create_window(
            theme.TRACK_CX, theme.TRACK_Y, window=self.track_label, anchor="n"
        )

        # bottom row inside window: progress + time + VOL
        row_y = theme.WIN_Y1 - 22
        pad = 18
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = tk.Scale(
            self.root, variable=self.progress_var, from_=0, to=100,
            orient=tk.HORIZONTAL, length=280, showvalue=False,
            bg=theme.WINDOW_HEX, troughcolor="#3a3836", highlightthickness=0,
            state=tk.DISABLED, sliderrelief=tk.FLAT, sliderlength=14, width=8,
        )
        self.canvas.create_window(theme.WIN_X0 + pad, row_y, window=self.progress_bar, anchor="w")

        self.time_var = tk.StringVar(value="--:-- / --:--")
        self.time_label = tk.Label(
            self.root, textvariable=self.time_var, font=theme.FONT_LABEL,
            fg=theme.WINDOW_TEXT, bg=theme.WINDOW_HEX,
        )
        self.canvas.create_window(theme.WIN_X0 + pad + 292, row_y, window=self.time_label, anchor="w")

        self.volume_btn = tk.Button(
            self.root, text="VOL", font=theme.FONT_LABEL,
            fg=theme.KEY_TEXT, bg=theme.KEY_HEX, activebackground=theme.BODY_DARK_HEX,
            relief=tk.RAISED, bd=2, command=self._open_volume_popup,
        )
        self.canvas.create_window(theme.WIN_X1 - pad, row_y, window=self.volume_btn, anchor="e")

    # --- volume popup ---
    def _open_volume_popup(self):
        if self._volume_popup is not None and self._volume_popup.winfo_exists():
            self._volume_popup.lift()
            return
        popup = tk.Toplevel(self.root)
        popup.title("volume")
        popup.configure(bg=theme.BODY_HEX)
        popup.resizable(False, False)
        popup.transient(self.root)
        x = self.root.winfo_rootx() + theme.WIDTH - 220
        y = self.root.winfo_rooty() + theme.WIN_Y1 - 40
        popup.geometry(f"200x70+{x}+{y}")
        slider = tk.Scale(
            popup, variable=self.volume_var, from_=0, to=100,
            orient=tk.HORIZONTAL, length=180, label="VOLUME",
            font=theme.FONT_LABEL, bg=theme.BODY_HEX, fg=theme.LABEL_TEXT,
            troughcolor=theme.BODY_DARK_HEX, highlightthickness=0,
            command=lambda v: self.on_volume_change(int(v)),
        )
        slider.pack(padx=8, pady=2)
        self._volume_popup = popup

    # --- click handlers: reel burst, then forward ---
    def _handle_prev(self):
        self._trigger_burst()
        self.on_prev()

    def _handle_next(self):
        self._trigger_burst()
        self.on_next()

    def _handle_shuffle(self):
        self._trigger_burst()
        self.on_shuffle()

    def _handle_playlist_change(self, name):
        self._trigger_burst()
        self.on_playlist_change(name)

    def _handle_mute(self):
        self.on_mute()

    def _trigger_burst(self):
        self.reel_burst_remaining += REEL_BURST_DEGREES

    # --- reel animation, both reels share one angle, driven by real elapsed time ---
    def _reel_tick(self):
        now = time.perf_counter()
        dt = now - self._last_tick_time
        self._last_tick_time = now

        approach_frac = 1 - math.exp(-REEL_APPROACH_RATE * dt)
        self.reel_velocity += (self.reel_target_velocity - self.reel_velocity) * approach_frac

        extra = 0.0
        if self.reel_burst_remaining > 0:
            extra = min(REEL_BURST_VELOCITY * dt, self.reel_burst_remaining)
            self.reel_burst_remaining -= extra

        self.reel_angle = (self.reel_angle + self.reel_velocity * dt + extra) % 360
        n = len(self.reel_frames)
        idx = int(self.reel_angle / (360 / n)) % n
        frame = self.reel_frames[idx]
        for item in self.reel_items:
            self.canvas.itemconfigure(item, image=frame)

        self.root.after(REEL_TICK_MS, self._reel_tick)

    def _set_playing(self, playing):
        self.reel_target_velocity = REEL_STEADY_VELOCITY if playing else 0.0

    # Called from main.py to refresh from mpv state
    def refresh(self, state):
        title = state.get("media-title")
        if title:
            self.track_var.set(title)

        pause = state.get("pause")
        self._set_latch("PLAY", not pause)
        if pause != self._last_pause_state:
            self._last_pause_state = pause
            self._set_playing(not pause)

        self._set_latch("MUTE", bool(state.get("mute")))

        duration = state.get("duration")
        time_pos = state.get("time-pos")
        if duration and time_pos is not None:
            self.progress_bar.config(to=duration)
            self.progress_var.set(time_pos)
        self.time_var.set(f"{_fmt_time(time_pos)} / {_fmt_time(duration)}")

        volume = state.get("volume")
        if volume is not None and int(volume) != self.volume_var.get():
            self.volume_var.set(int(volume))


if __name__ == "__main__":
    root = tk.Tk()
    ui = PoolsuiteUI(root)
    ui.on_play_pause = lambda: print("play/pause")
    ui.on_next = lambda: print("next")
    ui.on_prev = lambda: print("prev")
    ui.on_shuffle = lambda: print("shuffle")
    ui.on_mute = lambda: print("mute")
    ui.on_quit = root.destroy
    ui.on_volume_change = lambda v: print("volume", v)
    ui.on_playlist_change = lambda name: print("playlist", name)
    root.mainloop()
