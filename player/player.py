from multiprocessing.dummy import Process
from queue import Empty
from multiprocessing import Manager
import os
import time
import importlib_resources
import sys

from PyQt5 import QtWidgets, QtGui, QtCore


from player.random_play import PlaylistAutoPlay
import player.actions.open_folder as open_folder
import player.actions.delete as delete_file
import player.actions.check_duplicates as check_duplicates


def import_vlc():
    if sys.platform == "win32":
        path = importlib_resources.files('player.binaries.win64')
        os.environ['PYTHON_VLC_LIB_PATH'] = str(path / 'libvlc.dll')

    import vlc
    return vlc

vlc = import_vlc()


class Player(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.setWindowTitle("Media Player")

        # Widgets Setup
        self.instance = vlc.Instance()
        self.vlcplayer = self.instance.media_player_new()
        self.vlcplayer.audio_set_volume(0)
        self.playlist = self._playlist()
        self.search = None
        self.playlist_items  = []

        self.videoframe = QtWidgets.QFrame()
        self._update_frame()

        self.volume = self._volume_slider()
        self.position = self._position_slider()
        # -------------

        self.layout()

        # Playlist data
        self.base_folder = None
        self.names = dict()
        self.auto_play = PlaylistAutoPlay(self.names)
        # -------------

        self._shortcuts()

        # Async
        self.manager = Manager()
        self.queue = self.manager.Queue()
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self._update_ui)
        self.timer.start()
        self._tasks = dict()
        # -------------

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.manager.__exit__(*args)

    def skip(self, diff_seconds):
        """Skipp a few seconds (forward or back)"""
        # convert to ms
        diff = int(diff_seconds * 1000)

        current = self.vlcplayer.get_time()
        new = max(current + diff, 0)
        self.vlcplayer.set_time(new)

        l = self.vlcplayer.get_length()
        if l > 0:
            pos = new / l
            self.position.setValue(pos * 1000)

    def open_folder(self, folder):
        self.base_folder = folder
        self._async_action(open_folder.action, folder)

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
        vbox = QtWidgets.QVBoxLayout()
        self.search = QtWidgets.QLineEdit()

        vbox.addWidget(self.search, 1)
        self.search.textChanged.connect(self.filter_playlist)
        vbox.addWidget(self.playlist, 90)

        vbox.addLayout(self._playlist_controls(), 10)
        main.addLayout(vbox, 20)

        vboxlayout = QtWidgets.QVBoxLayout()
        vboxlayout.addWidget(self.videoframe)

        controls = self.controls_layout()
        vboxlayout.addLayout(controls)
        main.addLayout(vboxlayout, 90)

        widget.setLayout(main)

    def remove_filter(self):
        self.auto_play.set_selection_set(None)
        for item in self.playlist_items:
            item.setHidden(False)

    def filter_playlist(self, text):
        if text == '':
            self.remove_filter()

        count = 0
        all = self.playlist_items
        selection = []

        for item in all:
            contains = text.lower() in item.text().lower()
            item.setHidden(not contains)
            count += int(contains)

            if contains:
                selection.append(item.text())

        self.auto_play.set_selection_set(selection)
        print(f'{text} {count}')

    def _playlist_controls(self):
        play = QtWidgets.QPushButton('Play')
        play.clicked.connect(self.toggle_play_pause)
        nxt = QtWidgets.QPushButton('Next')
        nxt.clicked.connect(self.next_item)
        prv = QtWidgets.QPushButton('Prev')
        prv.clicked.connect(self.prev_item)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(prv)
        hbox.addWidget(play)
        hbox.addWidget(nxt)
        return hbox

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
        """Play a file"""
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
            self.next_item()

    #
    #   Shortcuts
    #
    def delete_file(self):
        file = self.auto_play.current()
        self.next_item()

        path = self.names.pop(file)
        self.auto_play.remove(file)

        self._async_action(delete_file.action, self.base_folder, path)

    def forward_long(self):
        """Forward 10 sec"""
        self.skip(10)

    def forward_small(self):
        """forward 0.5 sec"""
        self.skip(0.5)

    def back_small(self):
        """Go back 0.5 sec"""
        self.skip(-0.5)

    def back_long(self):
        """Go back 10 sec"""
        self.skip(-10)

    def toggle_play_pause(self):
        """Pause play the video"""
        self.vlcplayer.pause()

    def next_item(self):
        """Play next item"""
        item = self.auto_play.next()
        if item:
            self.play_file(item)

    def prev_item(self):
        """Play previous item"""
        item = self.auto_play.previous()
        if item:
            self.play_file(item)

    def _test_action(self):
        self._async_action(check_duplicates.action, self.base_folder)

    def _shortcuts(self):
        shortcuts = [
            ("right", self.forward_small),
            ("ctrl+right", self.forward_long),
            ("left", self.back_small),
            ("ctrl+left", self.back_long),
            ("space", self.toggle_play_pause),
            ("a", self.prev_item),
            ("d", self.next_item),
            ('Delete', self.delete_file),
            ('c', self._test_action)
        ]

        for k, v in shortcuts:
            short = QtWidgets.QShortcut(k, self)
            short.activated.connect(v)

    #
    # Async Message handler
    #
    def _async_action(self, fun, *args, **kwargs):
        p = Process(target=fun, args=(self.queue,) + args, kwargs=kwargs)
        p.start()

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

    def _add_playlist_item(self, file, path):
        self.names[file] = path

        item = QtWidgets.QListWidgetItem(file)

        self.playlist_items.append(item)
        self.playlist.addItem(item)

        # Check if we have a filter on the playlist
        if self.search and self.search.text() != "":
            valid = self.search.text().lower() in file.lower()
            item.setHidden(not valid)

            if valid:
                self.auto_play.add_to_selection(file)
        else:
            self.auto_play.add_to_selection(file)

    def _process_result(self, action, *args):
        if action == open_folder.START:
            print(f'Looking for items')

        if action == open_folder.RESULT:
            file, path = args
            self._add_playlist_item(file, path)

            # wait for a bit before playing the item
            # so it does not always start on the same file
            if len(self.names) == 1000:
                self.auto_play.reset()
                self.next_item()

        if action == open_folder.END:
            print(f'Found {len(self.names)} inside the folder')
            self.playlist.sortItems()

            if len(self.names) < 1000:
                self.next_item()


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

    with Player() as player:
        player.show()
        player.resize(1280, 720)

        args = parser.parse_args()
        player.open_folder(args.folder)

        sys.exit(app.exec_())