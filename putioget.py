import json
import logging
import os
import putiopy
import requests

logging.basicConfig(
    level=getattr(logging, os.environ.get('LOG_LEVEL', 'warning').upper()))
log = logging.getLogger()

client = putiopy.Client(os.environ['PUTIO_OAUTH_TOKEN'])
wanted_names = ['showrss', 'chill.institute']
wanted_extensions = ['mp4', 'mkv']

# find wanted resource ids
def get_wanted_ids(wanted_names):
    ids = []
    for file_resource in client.File.list():
        if file_resource.name in wanted_names:
            ids.append(file_resource.id)
    return ids

def mark_as_downloaded(resource_id):
    with open("downloaded_before.txt", "a") as f:
        f.write(str(resource_id))
        f.write('\n')


def downloaded_before(resource_id):
    str_id = str(resource_id)
    try:
        with open('downloaded_before.txt', 'r') as f:
            for line in f:
                if line.strip() == str_id:
                    return True
    except FileNotFoundError:
        pass

    return False


def get_files(resource_id, _seen=[]):
    wanted_files = []
    log.info('Scanning %s', resource_id)
    for file_resource in client.File.list(resource_id):
        log.debug(
            ' ↦ Analysing %s %d %s', file_resource.file_type, file_resource.id,
            file_resource.name)
        if file_resource.id in _seen:
            log.debug(
                '   ↦ Already seen %d %s', file_resource.id, file_resource.name)
            continue

        if file_resource.file_type == 'FOLDER':
            _seen.append(file_resource.id)
            log.debug(
                '   ↦ Traversing to %d %s', file_resource.id,
                file_resource.name)
            wanted_files += get_files(file_resource.id, _seen=_seen)

        if file_resource.file_type == 'VIDEO':
            log.debug(
                '   ↦ Maybe wanted %d %s', file_resource.id, file_resource.name)

            if downloaded_before(file_resource.id):
                continue

            if file_resource.extension.lower() in wanted_extensions:
                log.debug('     ↦ Wanted')
                wanted_files.append(file_resource)

    log.debug('Partial wanted\n%s', wanted_files)
    return wanted_files


def get_multiple_files(resource_ids):
    wanted_files = []
    for resource_id in resource_ids:
        wanted_files += get_files(resource_id)
    return wanted_files

wanted_ids = get_wanted_ids(wanted_names)
wanted_files = get_multiple_files(wanted_ids)


def aria2_download(url, dir='/home/thiago/putio'):
    websocket_url = os.environ['ARIA_URL']
    aria_secret = os.environ['ARIA_SECRET']
    headers = {'content-type': 'application/json'}

    payload = {
        "method": "aria2.addUri",
        "params": [f'token:{aria_secret}', [url], {'dir': dir}],
        "jsonrpc": "2.0",
        "id": 0,
    }
    response = requests.post(
        websocket_url, data=json.dumps(payload), headers=headers)

    log.debug(response)

    if response.status_code == 200:
        log.debug(response.text)
        return True

    msg = response.json().get('error')
    if msg is None:
        msg = response.text
    log.error(f"Error adding {url} to aria2: {msg}")

    return False


for f in wanted_files:
    if aria2_download(f.get_download_link()):
        log.info(f'Added {f.id} ({f.name}) to aria2 queue')
        mark_as_downloaded(f.id)
