import json
import os
import socket
import subprocess
import threading
import time

SOCKET_PATH = "/tmp/poolsuite.sock"


class MpvClient:
    def __init__(self, initial_url, socket_path=SOCKET_PATH):
        self.socket_path = socket_path
        self.proc = None
        self.sock = None
        self.state = {
            "media-title": None,
            "pause": False,
            "volume": 100,
            "mute": False,
            "duration": None,
            "time-pos": None,
        }
        self.state_lock = threading.Lock()
        self._reader_thread = None
        self._stop = False
        self._on_update = None
        self._start_mpv(initial_url)
        self._connect()
        self._observe_properties()
        self._start_reader()

    def _start_mpv(self, initial_url):
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)
        self.proc = subprocess.Popen(
            [
                "mpv",
                "--no-video",
                "--idle=yes",
                f"--input-ipc-server={self.socket_path}",
                initial_url,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _connect(self, timeout=5.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if os.path.exists(self.socket_path):
                try:
                    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    sock.connect(self.socket_path)
                    self.sock = sock
                    return
                except OSError:
                    pass
            time.sleep(0.1)
        raise RuntimeError("Could not connect to mpv IPC socket")

    def _send(self, command):
        payload = json.dumps({"command": command}) + "\n"
        self.sock.sendall(payload.encode("utf-8"))

    def _observe_properties(self):
        for prop in ("media-title", "pause", "volume", "mute", "duration", "time-pos"):
            self._send(["observe_property", 0, prop])

    def set_update_callback(self, callback):
        """callback(state_dict) invoked on the reader thread whenever state changes."""
        self._on_update = callback

    def _start_reader(self):
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()

    def _read_loop(self):
        buf = b""
        while not self._stop:
            try:
                chunk = self.sock.recv(4096)
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self._handle_message(msg)

    def _handle_message(self, msg):
        if msg.get("event") == "property-change":
            name = msg.get("name")
            value = msg.get("data")
            if name in self.state:
                with self.state_lock:
                    self.state[name] = value
                if self._on_update:
                    self._on_update(self.get_state())

    def get_state(self):
        with self.state_lock:
            return dict(self.state)

    # Commands (fire-and-forget)
    def toggle_pause(self):
        self._send(["cycle", "pause"])

    def next_track(self):
        self._send(["playlist-next", "weak"])

    def prev_track(self):
        self._send(["playlist-prev", "weak"])

    def shuffle(self):
        self._send(["playlist-shuffle"])

    def set_volume(self, volume):
        self._send(["set_property", "volume", volume])

    def toggle_mute(self):
        self._send(["cycle", "mute"])

    def load_playlist(self, url):
        self._send(["loadlist", url, "replace"])

    def quit(self):
        self._stop = True
        try:
            self._send(["quit"])
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.proc.kill()


if __name__ == "__main__":
    from playlists import PLAYLISTS

    client = MpvClient(PLAYLISTS["official"])
    client.set_update_callback(lambda s: print(s))
    try:
        print("mpv running, press Ctrl+C to quit")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        client.quit()
