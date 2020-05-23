import os
import re
import shutil
import time

from pathlib import Path

import PTN  # https://github.com/divijbindlish/parse-torrent-name
from omdbapi.movie_search import GetMovie  # ombdapi==0.5.1

from dumbdb import DumbDB


OMDBAPI_KEY = os.environ['OMDBAPI_KEY']
MEDIA_SUFFIXES = ['.mkv', '.mp4']
TV_BASE = Path('/mnt/Multimedia/TV')
MOVIE_BASE = Path('/mnt/Multimedia/Movies')
# FIXME refactor TV_MOVED
TV_MOVED = {}
MIN_MTIME_TO_MOVE = 60  # don't move files modified less than second ago

# FIXME Talkshows like Stephen Colbert get funky metadata
# e.g.: Stephen.Colbert.2019.07.24.Chris.Wallace.PROPER.1080p.WEB.x264-KOMPOST.mkv
#    'year': 2019, 
#    'resolution': '1080p', 
#    'codec': 'x264', 
#    'group': 'KOMPOST.mkv', 
#    'proper': True, 
#    'container': 'mkv', 
#    'title': 'Stephen Colbert', 
#    'excess': ['07.24.Chris.Wallace', 'WEB']
KNOWN_TV_TITLES = ['stephen colbert']


def media_iter(source_path):
    for file in Path(source_path).glob('**/*'):
        # skip non-media files
        if file.suffix not in MEDIA_SUFFIXES:
            continue

        # skip APF stuff
        if '.AppleDouble' in str(file.absolute()):
            continue

        # skip downloads in progress (f.ext -> f.ext.aria2)
        if file.with_suffix(file.suffix + '.aria2').exists():
            continue

        # skip empty files
        if file.stat().st_size == 0:
            continue

        # skip files that were recently modified
        if (time.time() - file.stat().st_mtime) < MIN_MTIME_TO_MOVE:
            continue

        yield file


def get_movie_title_year(file):
    metadata = PTN.parse(file.name)
    if not (metadata['title'] and metadata.get('year')):
        return None, None

    return metadata['title'], metadata['year']


def is_movie(file):
    """
    :type file: Path
    """
    title, year = get_movie_title_year(file)
    if not (title and year):
        print('    x Not a movie: missing title and/or year')
        return False

    movie = GetMovie(title=title, api_key=OMDBAPI_KEY)
    try:
        movie_year = int(movie.get_data('Year')['Year'])
    except ValueError:
        print(f'    x Not a movie; not found on OMDB: {title}')
        return False

    if not str(year) == str(movie_year):
        print(f'    x Not a movie: year on filename {year} does not match OMDB {movie_year}')
        return False

    return True


def _is_tv_episode(mdata):
    # FIXME Talkshows like Stephen Colbert get funky metadata
    if mdata['title'].lower() in KNOWN_TV_TITLES:
        mdata['season'] = mdata.get('season', 'no-season')
        mdata['episode'] = mdata.get('episode', mdata.get('excess', 'no-episode'))
        return True

    return mdata['title'] and mdata.get('season') and mdata.get('episode')


def destination_guess(file):
    def _is_match(a, b):
        return a['season'] == b['season'] and a['episode'] == b['episode']


    def _append_moved(mlist, mdata):
        mlist.append({
            'season': mdata['season'], 'episode': mdata['episode']
        })


    metadata = PTN.parse(file.name)

    if not _is_tv_episode(metadata):
        print(f'    x Not TV: missing title, season and/or episode {metadata}')
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


def safe_filename(name):
    safe_chars = ' .-_'
    return "".join([c for c in name if c.isalpha() or c.isdigit() or c in safe_chars]).rstrip()


def get_destination(file):
    destination = destination_guess(file)

    if destination is None:
        if is_movie(file):
            title, year = get_movie_title_year(file)
            folder = safe_filename(f'{title}.{year}')
            destination = MOVIE_BASE.joinpath(folder)
            destination.mkdir()

    return destination


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
        something_moved = True

    processed_files.add(str(f))

if not something_moved:
    exit(1)
