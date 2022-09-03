from copy import deepcopy
import random


class PlaylistAutoPlay:
    """This plays a list of files.

    It keeps the back and forward history (so if you go back when you go forward again it will be the same file).

    It can play the list in loop with and without replacement.

    """
    def __init__(self, playlist) -> None:
        self.playlist = playlist
        self.selected = None
        self.loop = True
        self.shuffle = True
        self.with_replacement = False
        self.remains = []

        self.history = []
        self.next_items = []

    def add_to_selection(self, item):
        if self.selected:
            self.selected.append(item)

        self.remains.append(item)

    def set_selection_set(self, selection):
        self.selected = selection
        self.playlist_grew()

    def get_selection_set(self):
        if self.selected is None:
            return list(self.playlist.keys())

        return deepcopy(self.selected)

    def select(self):
        """Select a random index"""
        if self.shuffle:
            return random.randrange(0, len(self.remains))
        else:
            return 0

    def remove(self, item):
        """Remove an item from the history because it was removed from the playlist"""
        try:
            self.history.remove(item)
        except:
            pass

    def current(self):
        """Get current item that is playing"""
        return self.history[-1]

    def reset(self):
        """Reset the playlist"""
        self.remains = self.get_selection_set()
        self.history = []
        self.next_items = []

    def playlist_grew(self):
        """Notify that the playlist grew"""
        self.remains = self.get_selection_set()

        for prev in self.history:
            try:
                self.remains.remove(prev)
            except:
                pass

    def next(self):
        """fetch next item to play"""
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
        """Play item that was previously playing"""
        if len(self.history) < 2:
            return None

        current = self.history.pop(-1)
        self.next_items.append(current)

        prev = self.history[-1]
        return self.playlist[prev]
