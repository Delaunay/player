from collections import defaultdict
from multiprocessing.dummy import Process
from queue import Empty
import random
from multiprocessing import Manager
import os
import time
import importlib_resources
import sys

from PyQt5 import QtWidgets, QtGui, QtCore

def import_vlc():
    if sys.platform == "win32":
        path = importlib_resources.files('player.binaries.win64')
        os.environ['PYTHON_VLC_LIB_PATH'] = str(path / 'libvlc.dll')

    import vlc
    return vlc

vlc = import_vlc()


IGNORE_FILE_EXTENSIONS = (
    'nfo', 'txt', 'exe' ,'pdf', 'gif', 'css', 'js', 'html'
)


class PlaylistAutoPlay:
    """This plays a list of files.

    It keeps the back and forward history (so if you go back when you go forward again it will be the same file).

    It can play the list in loop with and without replacement.

    """
    def __init__(self, playlist) -> None:
        self.playlist = playlist

        self.loop = True
        self.shuffle = True
        self.with_replacement = False
        self.remains = []

        self.history = []
        self.next_items = []

    def select(self):
        if self.shuffle:
            return random.randrange(0, len(self.remains))
        else:
            return 0

    def reset(self):
        self.remains = list(self.playlist.keys())
        self.history = []
        self.next_items = []

    def next(self):
        while self.next_items:
            item = self.next_items.pop()
            self.history.append(item)
            return self.playlist[item]

        if len(self.remains) == 0:
            if self.loop:
                self.reset()
            else:
                return None

        idx = self.select()

        if not self.with_replacement:
            selected = self.remains.pop(idx)
        else:
            selected = self.remains[idx]

        self.history.append(selected)
        return self.playlist[selected]

    def previous(self):
        if len(self.history) < 2:
            return None

        current = self.history.pop(-1)
        self.next_items.append(current)

        prev = self.history[-1]
        return self.playlist[prev]


def async_open_folder(queue, folder):
    queue.put(('FOLDER_START',))

    duplicates = defaultdict(set)
    names = dict()

    for root, dirs, files in os.walk(folder):

        for file in files:
            ext = file.rsplit('.', maxsplit=1)[-1]

            if ext in IGNORE_FILE_EXTENSIONS:
                continue

            f = os.path.join(root, file)

            if file in names and f != names[file]:
                original = names[file]
                duplicates[file].add(original)
                duplicates[file].add(f)
                continue

            names[file] = f
            queue.put(('FOLDER_ITEM', file, f))

    for k, v in duplicates.items():
        print(k)
        for item in v:
            print(f'    - {item}')

    queue.put(('FOLDER_END',))



class Player(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.setWindowTitle("Media Player")

        self.instance = vlc.Instance()
        self.vlcplayer = self.instance.media_player_new()
        self.vlcplayer.audio_set_volume(0)
        self.playlist = self._playlist()

        self.videoframe = QtWidgets.QFrame()
        self._update_frame()

        self.volume = self._volume_slider()
        self.position = self._position_slider()
        self.layout()

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self._update_ui)
        self.timer.start()

        self.names = dict()
        self.auto_play = PlaylistAutoPlay(self.names)

        self._shortcuts()
        self.manager = Manager()
        self.queue = self.manager.Queue()

    def skip(self, diff_seconds):
        # convert to ms
        diff = int(diff_seconds * 1000)

        current = self.vlcplayer.get_time()
        new = max(current + diff, 0)
        self.vlcplayer.set_time(new)

        l = self.vlcplayer.get_length()
        if l > 0:
            pos = new / l
            self.position.setValue(pos * 1000)

    def forward_long(self):
        self.skip(10)

    def forward_small(self):
        self.skip(0.5)

    def back_small(self):
        self.skip(-0.5)

    def back_long(self):
        self.skip(-10)

    def toggle_play_pause(self):
        self.vlcplayer.pause()

    def next_item(self):
        item = self.auto_play.next()
        if item:
            self.play_file(item)

    def prev_item(self):
        item = self.auto_play.previous()
        if item:
            self.play_file(item)

    def _shortcuts(self):
        short = QtWidgets.QShortcut("right", self)
        short.activated.connect(self.forward_small)

        short = QtWidgets.QShortcut("ctrl+right", self)
        short.activated.connect(self.forward_long)

        short = QtWidgets.QShortcut("left", self)
        short.activated.connect(self.back_small)

        short = QtWidgets.QShortcut("ctrl+left", self)
        short.activated.connect(self.back_long)

        short = QtWidgets.QShortcut("space", self)
        short.activated.connect(self.toggle_play_pause)

        short = QtWidgets.QShortcut("a", self)
        short.activated.connect(self.prev_item)

        short = QtWidgets.QShortcut("d", self)
        short.activated.connect(self.next_item)

    def play_playlist_item(self, item):
        name = item.text()

        file_path = self.names[name]

        print(file_path, str(file_path))
        self.play_file(str(file_path))

    def _playlist(self):
        playlist = QtWidgets.QListWidget()
        playlist.itemDoubleClicked.connect(self.play_playlist_item)
        playlist.itemActivated.connect(self.play_playlist_item)
        return playlist

    def open_folder(self, folder, depth=0):
        p = Process(target=async_open_folder, args=(self.queue, folder))
        p.start()

    def sync_open_folder(self, folder, depth=0):
        for root, dirs, files in os.walk(folder):

            for file in files:
                ext = file.rsplit('.', maxsplit=1)[-1]

                if ext in IGNORE_FILE_EXTENSIONS:
                    continue

                self._add_to_playlist(root, file)

        if depth == 0:
            print(len(self.names))

            for k, v in self.duplicates.items():
                print(k)
                for item in v:
                    print(f'    - {item}')

            names = sorted([n for n in self.names.keys()])
            for n in names:
                item = QtWidgets.QListWidgetItem(n)
                self.playlist.addItem(item)

            self.auto_play = PlaylistAutoPlay(self.names)
            self.play_file(self.auto_play.next())

    def _add_to_playlist(self, root, file):
        f = os.path.join(root, file)

        if file in self.names and f != self.names[file]:
            original = self.names[file]
            self.duplicates[file].add(original)
            self.duplicates[file].add(f)
            return

        self.names[file] = f

    def layout(self):
        widget = QtWidgets.QWidget(self)
        self.setCentralWidget(widget)

        # ---
        palette = self.videoframe.palette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(0,0,0))
        self.videoframe.setPalette(palette)
        self.videoframe.setAutoFillBackground(True)
        # ---

        main = QtWidgets.QHBoxLayout()
        main.addWidget(self.playlist, 20)

        vboxlayout = QtWidgets.QVBoxLayout()
        vboxlayout.addWidget(self.videoframe)

        controls = self.controls_layout()
        vboxlayout.addLayout(controls)
        main.addLayout(vboxlayout, 90)

        widget.setLayout(main)

    def controls_layout(self):
        controls = QtWidgets.QVBoxLayout()

        vol_pos = QtWidgets.QHBoxLayout()
        vol_pos.addWidget(self.position, 80)
        vol_pos.addWidget(self.volume, 10)
        controls.addLayout(vol_pos)

        return controls

    def set_volume(self, value):
        self.vlcplayer.audio_set_volume(value)

    def _volume_slider(self):
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        slider.setToolTip("Volume")
        slider.setMaximum(100)
        slider.setValue(self.vlcplayer.audio_get_volume())
        slider.valueChanged.connect(self.set_volume)
        return slider

    def set_position(self, value=None):
        if value is None:
            value = self.position.value()
        else:
            self.position.setValue(value)

        self.vlcplayer.set_position(value / 1000.0)

    def _position_slider(self):
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        slider.setMaximum(1000)

        slider.sliderMoved.connect(self.set_position)
        slider.sliderPressed.connect(self.set_position)
        return slider

    def play_file(self, file):
        self.media = self.instance.media_new(file)
        self.vlcplayer.set_media(self.media)
        self.media.parse()

        self.setWindowTitle(self.media.get_meta(vlc.Meta.Title))
        self.position.setValue(0)
        self.vlcplayer.play()

        # video_take_snapshot
        print(
            self.vlcplayer.video_get_size(),
            self.vlcplayer.get_fps(),
            self.vlcplayer.get_length(),
            self.vlcplayer.get_time(),
            self.vlcplayer.is_seekable(),
        )

    def _update_frame(self):
        if sys.platform.startswith('linux'):
            self.vlcplayer.set_xwindow(self.videoframe.winId())
        elif sys.platform == "win32":
            self.vlcplayer.set_hwnd(self.videoframe.winId())
        elif sys.platform == "darwin":
            self.vlcplayer.set_nsobject(int(videoframe.winId()))

    def _update_ui(self):
        self._process_async_work()

        if self.vlcplayer.is_playing():
            media_pos = int(self.vlcplayer.get_position() * 1000)
            self.position.setValue(media_pos)

        state = self.vlcplayer.get_state()
        if state == vlc.State.Ended:
            self.play_file(self.auto_play.next())

    #
    # Async Message handler
    #

    def _get_result(self):
        try:
            return self.queue.get(block=False)
        except Empty:
            return None

    def _process_async_work(self):
        # Limit time we can spend handling results in a single tick
        # this is to avoid locking UI
        start = time.time()

        while time.time() - start < 0.1:
            item = self._get_result()

            if item is None:
                return

            self._process_result(*item)

    def _process_result(self, action, *args):
        if action == "FOLDER_START":
            print(f'Looking for items')

        if action == "FOLDER_ITEM":
            file, path = args
            self.names[file] = path

            item = QtWidgets.QListWidgetItem(file)
            self.playlist.addItem(item)

            # wait for a bit before playing the item
            # so it does not always start on the same file
            if len(self.names) == 1000:
                self.auto_play.reset()
                self.next_item()

        if action == "FOLDER_END":
            print(f'Found {len(self.names)} inside the folder')
            self.auto_play.reset()





def set_style(app):
    """ Define Qt Dark Style"""

    font = QtGui.QFont("Op/enSans-Regular.svg")

    p = app.palette()
    p.setColor(QtGui.QPalette.Window,		QtGui.QColor(53, 53, 53))
    p.setColor(QtGui.QPalette.WindowText,	QtGui.QColor(255, 255, 255))
    p.setColor(QtGui.QPalette.Base,		    QtGui.QColor(5, 5, 5))
    p.setColor(QtGui.QPalette.Text,		    QtGui.QColor(255, 255, 255))
    p.setColor(QtGui.QPalette.Button,		QtGui.QColor(33, 33, 33))
    p.setColor(QtGui.QPalette.ButtonText,	QtGui.QColor(255, 255, 255))
    p.setColor(QtGui.QPalette.Highlight,	QtGui.QColor(100, 100, 200))
    p.setColor(QtGui.QPalette.BrightText,	QtGui.QColor(255, 255, 255))
    p.setColor(QtGui.QPalette.Midlight,	    QtGui.QColor(55, 55, 55))
    p.setColor(QtGui.QPalette.Dark,		    QtGui.QColor(55, 55, 55))
    p.setColor(QtGui.QPalette.Mid,		    QtGui.QColor(55, 55, 55))
    p.setColor(QtGui.QPalette.Shadow,		QtGui.QColor(55, 55, 55))
    app.setPalette(p)

def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=str, default='.', help="Playlist folder to open")

    app = QtWidgets.QApplication(sys.argv)
    set_style(app)

    player = Player()

    player.show()
    player.resize(640, 480)

    args = parser.parse_args()
    player.open_folder(args.folder)

    sys.exit(app.exec_())