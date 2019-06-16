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


# TODO: more mappings, move to config file
LOCATION_MAPPINGS = [
    {'re': re.compile(r'^archer[\W]', re.IGNORECASE),
     'destination': TV_BASE / 'Archer (2009)'},
]


def location_iter():
    for location_mapping in LOCATION_MAPPINGS:
        yield location_mapping['re'], location_mapping['destination']


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


def get_destination(file):
    # TODO: move based on TVDB information
    for re, destination in location_iter():
        if re.match(file.name):
            if not destination.is_dir():
                print(f'    ERROR. Not a directory: {destination}')
                return None

            return destination

    if is_movie(file):
        return MOVIE_BASE


print('Processing media files')
processed_files = DumbDB('movemedia_processed.txt')
something_moved = False
for f in media_iter('/home/thiago/putio'):

    if processed_files.exists(str(f)):
        continue

    print(f)

    target_path = get_destination(f)
    if target_path is None:
        print(f'    Destination not found')
    else:
        if target_path.joinpath(f.name).exists():
            print(f'    ERROR. Already exists: {target_path.joinpath(f.name)}')
        else:
            print(f'    ↦ Moving to {target_path}', end='')
            shutil.move(str(f), str(target_path))
            print()
            something_moved = True

    processed_files.add(str(f))

if not something_moved:
    exit(1)
