import os
from pathlib import Path

from player.actions.normalize_file_structure import get_parents




def action(queue, base, path):
    """This is not a real delete, it is going to stage the delete by moving the file to
    a deleted folder.
    """

    deleted = os.path.join(base, 'deleted')
    os.makedirs(deleted, exist_ok=True)

    # Get how faraway from the base folder we are
    parents = get_parents(base, path)
