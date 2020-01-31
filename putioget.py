import json
import logging
import os
import putiopy
import requests

from dumbdb import DumbDB


logging.basicConfig(
    level=getattr(logging, os.environ.get('LOG_LEVEL', 'warning').upper()))
log = logging.getLogger()

client = putiopy.Client(os.environ['PUTIO_OAUTH_TOKEN'])
downloaded_files = DumbDB('downloaded_before.txt')


def get_missing_files(file_resources):
    missing_files = []
    for file_resource in file_resources:
        log.debug(
            ' ↦ Analysing %s %d %s', file_resource.file_type, file_resource.id,
            file_resource.name)

        log.debug(
            '   ↦ Maybe wanted %d %s', file_resource.id, file_resource.name)

        if downloaded_files.exists(file_resource.id):
            continue

        missing_files.append(file_resource)

        log.debug('Partial wanted\n%s', missing_files)
    return missing_files


def get_missing_videos():
    resource_ids = client.File.list(parent_id=-1, file_type='VIDEO')
    log.debug(' ↦ Found %d videos', len(resource_ids))
    return get_missing_files(resource_ids)


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


for f in get_missing_videos():
    if aria2_download(f.get_download_link()):
        log.info(f'Added {f.id} ({f.name}) to aria2 queue')
        downloaded_files.add(f.id)
