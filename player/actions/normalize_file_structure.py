from collections import defaultdict
from pathlib import Path
import os


def get_parents(base, path):
    parents = []
    current_path = Path(path).parent.absolute()

    while current_path != Path(base):
        depth += 1
        parents.append(current_path.name)
        current_path = current_path.parent.absolute()

    return list(reversed(parents))


def action(queue, base):
    """"""

    for root, dirs, files in os.walk(base):

        for file in files:
            pass


