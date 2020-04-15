#!/usr/bin/env python3

import sys
import os
import requests
import json
import time
import logging
from configparser import ConfigParser

def get_streams(plex_url, plex_token):
    try:
        r = requests.get(f"{plex_url}/status/sessions?X-Plex-Token={plex_token}", headers={"Accept": "application/json"})
        r.raise_for_status()
        jstreams = json.loads(r.text)

        # make sure we got back valid info from api
        if _validate_streams(jstreams):
            return _parse_streams(jstreams)
        else:
            return {}

    except Exception as err:
        logging.critical(f"Error getting streams from Plex: {err}")
        return {}


def _validate_streams(streams):
    """High-level validation of API results"""
    if 'MediaContainer' not in streams.keys():
        logging.warning('Validation failed on API response data. "MediaContainer" missing (nobody streaming?)')
        return False

    if 'Metadata' not in streams['MediaContainer'].keys():
        logging.warning('Validation failed on API response data. "MediaContainer"->"Metadata" missing (nobody streaming?)')
        return False

    return True


def _validate_stream(user_stream):
    """Validate individual stream from API"""
    if not all(k in user_stream for k in ('Session', 'Player', 'title')):
        logging.warning('Validation failed on data. Either "Session","Player", or "title" are missing')
        return False

    if not all(k in user_stream['Player'] for k in ('state', 'address')):
        logging.warning('Validation failed on data. Either "state" or "address" are missing from "Player"')
        return False

    if 'id' not in user_stream['Session']:
        logging.warning('Validation failed on data. "id" missing from "Session")')
        return False

    return True


def _parse_streams(jstreams):
    """Compile API results into dict with only the info we want"""
    dreturn = {}
    for stream in jstreams['MediaContainer']['Metadata']:
        # make sure everything's there before we try to parse it
        if not _validate_stream(stream):
            # skip this. data might be there next time
            logging.warning('Validation failed on data. Skipping and hoping it\'s there next time)')
            continue

        # ignore paused streams
        if stream['Player']['state'] == 'paused':
            logging.debug(f'Ignoring paused stream for {stream["User"]["title"]})')
            continue

        username = stream['User']['title']
        stream_data = {'session_id': stream['Session']['id'],
                       'state': stream['Player']['state'],
                       'title': stream['title'],
                       'ip_address': stream['Player']['address']}

        if username in dreturn.keys():
            dreturn[username].append(stream_data)
        else:
            dreturn[username] = [stream_data]

    return dreturn

def save_bans(ban_list):
    """save ban_list to disk"""
    json_bans = json.dumps(ban_list)

def load_bans():
    """load bans from disk"""

def dup_check(user_streams):
    """Returns number of unique ip addresses for user"""
    if len(user_streams) == 1:
        return 1

    ip_address_list = []
    for stream in user_streams:
        ip_address_list.append(stream['ip_address'])

    # return count of unique ip addresses for user
    return len(list(set(ip_address_list)))


def ban_user(username, ban_length_hrs, ban_list):
    """Record username and epoch of ban. Return ban_list with new ban added"""
    ban_list[username] = int(time.time()) + (3600 * ban_length_hrs)
    return ban_list


def kill_all_streams(user_streams, message, plex_url, plex_token):
    """Term each user stream and send them a message"""
    for session in user_streams:
        try:
            payload = {'sessionId': session['session_id'],
                       'reason': message,
                       'X-Plex-Token': plex_token}
            r = requests.get(f"{plex_url}/status/sessions/terminate",
                             params=payload,
                             headers={"Accept": "application/json"})
            r.raise_for_status()
        except Exception as err:
            logging.error(f"Error while killing stream. Session data: {session}. Error: {err}")


def is_ban_valid(username, ban_list):
    """Return True/False if user is still banned according to ban_list"""
    logging.debug(f"Checking to see if ban for {username} is valid")
    return int(time.time()) <= ban_list[username]

def ban_time_left_human(username, ban_list):
    """Return human remaining time of ban"""
    return time.strftime("%H hours and %M minutes", time.gmtime(ban_list[username] - time.time()))


def unban_user(username, ban_list):
    """Remove username from ban_list and send back"""
    del ban_list[username]
    logging.info(f"Removed {username} from ban list")
    return ban_list


def telegram_notify(message, telegram_bot_key, chat_id):
    """Send message via Telegram"""
    try:
        r = requests.post(f"https://api.telegram.org/bot{telegram_bot_key}/sendMessage", data={'chat_id': chat_id, 'text': message})
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logging.error(f"Hit error while sending Telegram message: {err}")

# set default logging level and stream
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# load settings
try:
    config = ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
    loop_delay_sec = int(config.get('main', 'loop_delay_seconds'))
    plex_url = config.get('main', 'plex_url')
    plex_token = config.get('main', 'plex_token')
    ban_length_hrs = int(config.get('main', 'ban_length_hrs'))
    ban_msg = config.get('main', 'ban_msg')
    telegram_bot_key = config.get('telegram', 'bot_key')
    telegram_chat_id = config.get('telegram', 'chat_id')
except FileNotFoundError as err:
    print(f"Unable to read config file! Error: {err}")
    exit()
except Exception as err:
    print(f"Unable to parse config.ini or missing settings! Error: {err}")
    exit()

# {'bob': EPOCHBANEND, 'joe': 0000000000}
ban_list = {}

try:
    while True:
        streams = get_streams(plex_url, plex_token)

        for user in streams:
            # check to see if user is already banned
            if user in ban_list:
                if is_ban_valid(user, ban_list):
                    print(f"Killing all streams for banned user {user}")
                    kill_all_streams(streams[user], ban_msg + "Your ban will be lifted in {ban_time_left_human(user, ban_list)}", plex_url, plex_token)
                    telegram_notify(f"Prevented banned user {user} from streaming", telegram_bot_key, telegram_chat_id)
                else:
                    # ban has expired
                    print(f"Removing {user} from ban list. Ban has expired")
                    ban_list = unban_user(user, ban_list)
                    telegram_notify(f"Removed {user} from ban list", telegram_bot_key, telegram_chat_id)

            # check to see if user needs to be banned
            uniq_stream_locations = dup_check(streams[user])
            if uniq_stream_locations > 1:
                print(f"Banning user {user} for {ban_length_hrs} hours for streaming from {uniq_stream_locations} unique locations")
                ban_list = ban_user(user, ban_length_hrs, ban_list)

                print(f"Killing all streams for {user}")
                kill_all_streams(streams[user], ban_msg, plex_url, plex_token)

                telegram_notify(f"Banned {user} for {ban_length_hrs} hours for streaming from {uniq_stream_locations} unique locations",
                                telegram_bot_key, telegram_chat_id)

        time.sleep(loop_delay_sec)

except KeyboardInterrupt:
    print('Exiting...')
