#!/usr/bin/env python2
import sys
import json
import time
import uuid
from redis import StrictRedis


redis = StrictRedis()
hopper_response = redis.pubsub()
hopper_response.subscribe('hopper-response')

hopper_event = redis.pubsub()
hopper_event.subscribe('hopper-event')


class SSPError(Exception):
    pass


def wait_for_response(correlId):
    """blocks until it can return a message with a matching correlId."""
    for msg in hopper_response.listen():
        if 'sspError' in msg:
            raise SSPError(msg['sspError'])
        if msg['type'] != 'message':
            continue
        data = json.loads(msg['data'])
        if data['correlId'] == correlId:
            return data


def wait_for_event(event):
    """blocks until it can return a matching_event."""
    for msg in hopper_event.listen():
        if msg['type'] != 'message':
            continue
        data = json.loads(msg['data'])
        if data['event'] == event:
            return data


def levels_from_message(msg):
    return {int(level['value']): int(level['level'])
            for level in msg['levels']}


def print_levels(levels):
    for value, count in sorted(levels.items()):
        print("%3d Eurocent x %3d" % (value, levels[value]))


def fatal(msg):
    print >> sys.stderr, msg
    time.sleep(4)
    sys.exit(1)


def hopper_request(command, **args):
    """send a request to hoppers request queue and wait for a response."""
    correlId = str(uuid.uuid4())
    args.update({
        "cmd": command,
        "msgId": correlId
    })
    redis.publish('hopper-request', json.dumps(args))
    return wait_for_response(correlId)


def get_levels():
    """returns current coin levels as an array where coin values are the keys
    and their counts are values."""
    msg = hopper_request('get-all-levels')
    return levels_from_message(msg)


def set_levels(levels):
    """set an array where coin values are the keys and their counts are values
    as new coin leves for the machine"""

    print("Sending the following values to the machine:")
    for coin, count in sorted(levels.items()):
        hopper_request('set-denomination-level',
                       amount=coin, level=count)


def empty_and_count():
    print('Asking the machine to empty itself.')
    hopper_request('smart-empty')
    wait_for_event('smart emptied')
    msg = hopper_request('cashbox-payout-operation-data')
    levels = levels_from_message(msg)
    if 0 in levels and levels[0] > 0:
        print('Warning: detected %s unknown coins.' % levels[0])
    del(levels[0])
    return levels


def refill():
    print("""
 _  __                                   _
| |/ /__ _ ___ ___  ___  _ __ ___   __ _| |_
| ' // _` / __/ __|/ _ \| '_ ` _ \ / _` | __|
| . \ (_| \__ \__ \ (_) | | | | | | (_| | |_
|_|\_\__,_|___/___/\___/|_| |_| |_|\__,_|\__| v1.33.7
""")
    print("I believe, the following amount of coins should be inside me:\n")
    expected_levels = get_levels()
    print_levels(expected_levels)

    print("Just let me check. Are you ready to catch all the coins, which \
    are going to fall out of me in a moment? Then press enter")
    raw_input('> ')
    actual_levels = empty_and_count()
    if expected_levels != actual_levels:
        print("Uh, the actual levels did not match my expectations: \n Actual Values:")
        print_levels(actual_levels)
        fatal('I\'m exiting now. Byebye')


    print('Looks good. Please put *ONLY* the coins you want to add \
    into the machine, so I can count them. Then press enter')
    raw_input('> ')

    additional_levels = empty_and_count()
    expected_levels = dict()
    for coin, count in additional_levels.items():
        expected_levels[coin] = actual_levels[coin] + count

    print('Okay, after you added...')
    print_levels(additional_levels)
    print('...we should have...')
    print_levels(expected_levels)
    print('...lets check that. Please put *ALL* the coins into the machine \
    now and we are going to empty one more time, okay?')
    raw_input('> ')

    actual_levels = empty_and_count()
    if expected_levels != actual_levels:
        print("Uh, the actual levels did not match my expectations: \n Actual Values:")
        print_levels(actual_levels)
        fatal('I\'m exiting now. Byebye')

    print('Okay. That\'s it, I am going to save this state to the machine',
          'so please put *ALL* your coins into it and you are done.')

    print_levels(actual_levels)
    set_levels(actual_levels)


if __name__ == '__main__':
    try:
        refill()
    except SSPError as e:
        print('the hardware returned unexpected values: ', e.msg)
