from collections import defaultdict
import os
import hashlib
from pathlib import Path


def compute_hash(hash, name):
    with open(name, 'rb') as f:
        for chunck in iter(lambda: f.read(4096), b""):
            hash.update(chunck)

    return hash.hexdigest()


def delete(base, file):
    deleted = os.path.join(base, 'deleted')
    os.makedirs(deleted, exist_ok=True)

    dest = os.path.join(deleted, Path(file).name)
    os.rename(file, dest)


def action(queue, base):
    """Check for identical files"""

    print('Checking for duplicates')

    filenames = defaultdict(list)
    found = defaultdict(list)
    processed_count = 0

    for root, dirs, files in os.walk(base):

        for file in files:
            path = os.path.join(root, file)
            hash = compute_hash(hashlib.md5(), path)

            if hash in found:
                print(f'Removed {path}')
                delete(base, path)

            found[hash].append(path)
            filenames[file].append(path)

            processed_count += 1

            if processed_count % 100 == 0:
                print(f'Processed {processed_count} files')

    #
    print('Files are identical')
    print('-------------------')
    for k, v in found.items():
        if len(v) == 1:
            continue

        print(f'{k}:')
        for file in v:
            print(f'    - {file}')

    print('Filename are duplicates')
    print('-----------------------')
    for k, v in filenames.items():
        if len(v) == 1:
            continue

        print(f'{k}:')
        for file in v:
            print(f'    - {file}')

