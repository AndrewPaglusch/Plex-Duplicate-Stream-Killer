#!/usr/bin/env python3

import sys
import os
import requests
import json
import time
import logging
import ipaddress
from datetime import datetime
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
        logging.error(f"Error getting streams from Plex: {err}")
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
                       'device': stream['Player'].get('device', 'Unknown'),
                       'ip_address': stream['Player']['address']}

        if username in dreturn.keys():
            dreturn[username].append(stream_data)
        else:
            dreturn[username] = [stream_data]

    return dreturn


def save_bans(ban_list):
    """save ban_list to disk"""
    try:
        with open('/data/bans.json', 'w') as f:
            f.write(json.dumps(ban_list))
    except Exception as err:
        logging.error(f'Error saving bans to disk. {err}')
    else:
        logging.info('Saved bans to disk')


def load_bans():
    """load bans from disk"""
    try:
        with open('/data/bans.json', 'r') as f:
            return json.loads(f.read())
    except Exception as err:
        logging.info(f'bans.json does not exist or can not be read. This will be created when someone is banned. {err}')
        return {}
    else:
        logging.debug('Loaded bans from disk')

def get_unique_ips(user_streams, network_whitelist):
    """Return list of each IP address being used in user_streams"""
    ip_address_list = []
    for stream in user_streams:
        # only count streams from non-whitelisted ip addresses
        if any([ ipaddress.IPv4Address(stream['ip_address']) in n for n in network_whitelist ]):
            logging.debug(f'Ignoring stream from {stream["ip_address"]} (whitelisted)')
        else:
            ip_address_list.append(stream['ip_address'])

    # return list of unique ip addresses for user streams
    return list(set(ip_address_list))

def log_user_ip_history(user_history, user, uniq_streams):
    """log ip addresses being used by user to user_history, along with timestamp"""
    user_history.setdefault(user, [])
    time_now = int(time.time())
    user_history[user].extend((time_now, ip) for ip in uniq_streams)
    return user_history

def cleanup_user_history(user_history, user_history_length_hrs):
    """remove history that is older than user_history_length_hrs for all users"""
    epoch_cutoff = int(time.time()) - (3600 * user_history_length_hrs)
    filtered_history = {}
 
    for user, entries in user_history.items():
        kept_entries = [(epoch, ip_address) for epoch, ip_address in entries if epoch >= epoch_cutoff]
        filtered_history[user] = kept_entries
 
    return filtered_history

def count_ips_in_history(user_history, user):
    """return the number of unique ip addresses a user has logged in user_history"""
    if user not in user_history:
        return 0

    uniq_ips = set(ip for _, ip in user_history[user])
    return len(uniq_ips)

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


def log_stream_data(user_streams):
    """Log information about each stream for a user"""
    for stream_num, session in enumerate(user_streams):
        device = session['device']
        ip_addr = session['ip_address']
        media_title = session['title']
        logging.info(f"(Stream {stream_num}) DEVICE: \"{device}\" IPADDR: \"{ip_addr}\" MEDIA: \"{media_title}\"")

def log_ip_history(username, user_history):
    ip_history = []
    logging.info(f"IP history for user {username}:")

    for entry in user_history[username]:
        timestamp, ip_address = entry
        if not ip_history or ip_history[-1][1] != ip_address:
            ip_history.append((timestamp, ip_address))
            logging.info(f"{datetime.fromtimestamp(timestamp)} - {ip_address}")

def is_ban_valid(username, ban_list):
    """Return True/False if user is still banned according to ban_list"""
    logging.debug(f"Checking to see if ban for {username} is valid")
    return int(time.time()) <= ban_list[username]


def ban_time_left_human(username, ban_list):
    """Return human remaining time of ban"""
    seconds_left = ban_list[username] - time.time()
    hours_left = seconds_left // 3600
    minutes_left = (seconds_left - hours_left * 3600) // 60
    return f"{int(hours_left)} hours and {int(minutes_left)} minutes"


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

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# load settings
try:
    config = ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
    loop_delay_sec = int(config.get('main', 'loop_delay_seconds'))
    plex_url = config.get('main', 'plex_url')
    plex_token = config.get('main', 'plex_token')
    max_unique_streams = int(config.get('main', 'max_unique_streams'))
    user_history_ban_enabled = config.get('main', 'user_history_ban_enabled').lower() == "true"
    user_history_length_hrs = int(config.get('main', 'user_history_length_hrs'))
    user_history_ban_ip_thresh = int(config.get('main', 'user_history_ban_ip_thresh'))
    ban_length_hrs = int(config.get('main', 'ban_length_hrs'))
    ban_msg = config.get('main', 'ban_msg')
    user_whitelist = config.get('main', 'user_whitelist').lower().split()
    network_whitelist = [ ipaddress.IPv4Network(n) for n in config.get('main', 'network_whitelist').split() ]
    telegram_bot_key = config.get('telegram', 'bot_key')
    telegram_chat_id = config.get('telegram', 'chat_id')
except FileNotFoundError as err:
    logging.critical(f"Unable to read config file! Error: {err}")
    exit()
except Exception as err:
    logging.critical(f"Unable to parse config.ini or missing settings! Error: {err}")
    exit()

# {'bob': EPOCHBANEND, 'joe': 0000000000}
ban_list = load_bans()

# {'bob': [(EPOCH1, IPADDR), (EPOCH2, IPADDR),...,]
user_history = {}

try:
    while True:
        streams = get_streams(plex_url, plex_token)

        for user in streams:
            # continue if the user is in a whitelist
            if user.lower() in user_whitelist:
                logging.debug(f"User {user} is in whitelist. Not going to count streams")
                continue

            # check to see if user is already banned
            if user in ban_list:
                if is_ban_valid(user, ban_list):
                    logging.info(f"Killing all streams for banned user {user}")
                    kill_all_streams(streams[user], ban_msg + f" Your ban will be lifted in {ban_time_left_human(user, ban_list)}.", plex_url, plex_token)
                    telegram_notify(f"Prevented banned user {user} from streaming", telegram_bot_key, telegram_chat_id)
                    continue
                else:
                    # ban has expired
                    logging.info(f"Removing {user} from ban list. Ban has expired")
                    ban_list = unban_user(user, ban_list)
                    save_bans(ban_list)
                    telegram_notify(f"Removed {user} from ban list", telegram_bot_key, telegram_chat_id)

            #get a unique list of ip addresses that the user is currently streaming with
            uniq_streams = get_unique_ips(streams[user], network_whitelist)

            # log user ip history to user_history
            if user_history_ban_enabled:
                user_history = log_user_ip_history(user_history, user, uniq_streams)
                user_history = cleanup_user_history(user_history, user_history_length_hrs)

                # check history to see if too many unique ips have been logged over the past user_history_length_hrs hours
                uniq_ip_history = count_ips_in_history(user_history, user)
                if uniq_ip_history > user_history_ban_ip_thresh:
                    logging.info(f"Banning user {user} for streaming from more than {user_history_ban_ip_thresh} IP addresses over the previous {user_history_ban_ip_thresh} hours")
                    ban_list = ban_user(user, ban_length_hrs, ban_list)
                    save_bans(ban_list)

                    logging.info(f"Killing all streams for {user}")
                    log_ip_history(user, user_history)
                    kill_all_streams(streams[user], ban_msg + f" Your ban will be lifted in {ban_time_left_human(user, ban_list)}.", plex_url, plex_token)

                    telegram_notify(f"Banning user {user} for streaming from more than {user_history_ban_ip_thresh} IP addresses over the previous {user_history_ban_ip_thresh} hours", telegram_bot_key, telegram_chat_id)
                    continue

            # check user streams to see if greater than max_unique_streams
            uniq_stream_count = len(uniq_streams)
            if uniq_stream_count > max_unique_streams:
                logging.info(f"Banning user {user} for {ban_length_hrs} hours for streaming from {uniq_stream_count} unique locations.")
                ban_list = ban_user(user, ban_length_hrs, ban_list)
                save_bans(ban_list)

                logging.info(f"Killing all streams for {user}")
                log_stream_data(streams[user])
                kill_all_streams(streams[user], ban_msg + f" Your ban will be lifted in {ban_time_left_human(user, ban_list)}.", plex_url, plex_token)

                telegram_notify(f"Banned {user} for {ban_length_hrs} hours for streaming from {uniq_stream_count} unique locations.", telegram_bot_key, telegram_chat_id)

        time.sleep(loop_delay_sec)

except KeyboardInterrupt:
    logging.info('Exiting...')
