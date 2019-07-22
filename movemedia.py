import os
import re
import shutil
import PTN  # https://github.com/divijbindlish/parse-torrent-name
from omdbapi.movie_search import GetMovie  # ombdapi==0.5.1
from pathlib import Path

from dumbdb import DumbDB


OMDBAPI_KEY = os.environ['OMDBAPI_KEY']
MEDIA_SUFFIXES = ['.mkv', '.mp4']
TV_BASE = Path('/mnt/Multimedia/TV')
MOVIE_BASE = Path('/mnt/Multimedia/Moohovies')
# FIXME: refactor TV_MOVED
TV_MOVED = {}

def media_iter(source_path):
    for file in Path(source_path).glob('**/*'):
        # skip downloads in progress
        if file.with_suffix(file.suffix + '.aria2').exists():
            continue

        # skip empty files
        if file.stat().st_size == 0:
            continue

        if file.suffix in MEDIA_SUFFIXES:
            yield file


def is_movie(file):
    """
    :type file: Path
    """
    metadata = PTN.parse(file.name)
    if not (metadata['title'] and metadata.get('year')):
        return False

    movie = GetMovie(title=metadata['title'], api_key=OMDBAPI_KEY)
    maybe_year = movie.get_data('Year')['Year']
    if str(metadata['year']) == str(maybe_year):
        return True

    return False


def destination_guess(file):
    def _is_match(a, b):
        return a['season'] == b['season'] and a['episode'] == b['episode']


    def _append_moved(mlist, mdata):
        mlist.append({
            'season': mdata['season'], 'episode': mdata['episode']
        })


    def _is_tv_episode(mdata):
        return mdata['title'] and mdata.get('season') and mdata.get('episode')

    metadata = PTN.parse(file.name)

    if not _is_tv_episode(metadata):
        return None

    title = metadata['title'].title()

    moved_episodes = TV_MOVED.get(title)
    if moved_episodes is None:
        TV_MOVED[title] = []

    for entry in TV_MOVED[title]:
        if _is_match(metadata, entry):
            return None

    _append_moved(TV_MOVED[title], metadata)

    return TV_BASE.joinpath(metadata['title'].title())


def get_destination(file):
    if is_movie(file):
        return MOVIE_BASE

    return destination_guess(file)


def move_with_create(file_path, target_path):
    if target_path.joinpath(f.name).exists():
        print(f'    ERROR. Already exists: {target_path.joinpath(f.name)}')
        return False

    if not target_path.exists():
        os.makedirs(str(target_path), mode=0o777)

    try:
        shutil.move(str(file_path), str(target_path))
    except (shutil.Error, OSError) as e:
        print(f'    ERROR. {e}')
        return False

    return True


print('Processing media files')
processed_files = DumbDB('movemedia_processed.txt')
something_moved = False
for f in media_iter('/home/thiago/putio'):

    if processed_files.exists(str(f)):
        continue

    print(f)

    target_path = get_destination(f)
    if target_path is not None:
        print(f'    ↦ Moving to {target_path}', end='', flush=True)
        move_with_create(f, target_path)
        print()

    processed_files.add(str(f))

if not something_moved:
    exit(1)
