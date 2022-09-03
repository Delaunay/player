from collections import defaultdict
import os


IGNORE_FILE_EXTENSIONS = (
    'nfo', 'txt', 'exe' ,'pdf', 'gif', 'css', 'js', 'html', 'srt',

    #
    'png', 'jpg', 'jpeg', 'webm'
    #
)

NAMESPACE = 'FOLDER'
START = f'{NAMESPACE}_START'
RESULT = f'{NAMESPACE}_ITEM'
END = f'{NAMESPACE}_END'


def action(queue, folder, ignored_extensions=None):
    queue.put((START,))

    if ignored_extensions is None:
        ignored_extensions = IGNORE_FILE_EXTENSIONS

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
            queue.put((RESULT, file, f))

    # for k, v in duplicates.items():
    #     print(k)
    #     for item in v:
    #         print(f'    - {item}')

    queue.put((END,))
