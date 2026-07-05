import tkinter as tk

from mpv_client import MpvClient
from playlists import PLAYLISTS
from ui import PoolsuiteUI


def main():
    root = tk.Tk()
    ui = PoolsuiteUI(root)

    client = MpvClient(PLAYLISTS[ui.playlist_var.get()])

    def on_state_update(state):
        root.after(0, lambda: ui.refresh(state))

    client.set_update_callback(on_state_update)

    def on_close():
        client.quit()
        root.destroy()

    ui.on_play_pause = client.toggle_pause
    ui.on_next = client.next_track
    ui.on_prev = client.prev_track
    ui.on_shuffle = client.shuffle
    ui.on_mute = client.toggle_mute
    ui.on_quit = on_close
    ui.on_volume_change = client.set_volume
    ui.on_playlist_change = lambda name: client.load_playlist(PLAYLISTS[name])

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
