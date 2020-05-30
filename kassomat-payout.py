#!/usr/bin/env python2
import json
import uuid
from redis import StrictRedis


redis = StrictRedis()
pubsub = redis.pubsub()
pubsub.subscribe('hopper-response')


def wait_for_message(correlId):
    for msg in pubsub.listen():
        if msg['type'] != 'message':
            continue
        data = json.loads(msg['data'])
        if data['correlId'] == correlId:
            return data


def get_levels():
    correlId = str(uuid.uuid4())
    redis.publish('hopper-request', json.dumps({
        "cmd": "get-all-levels",
        "msgId": correlId
    }))
    msg = wait_for_message(correlId)
    return {int(level['value']): int(level['level']) for level in msg['levels']}


def do_payout(value):
    print("Dispensing %s Eurocent" % (value))
    correlId = str(uuid.uuid4())
    redis.publish('hopper-request', json.dumps({
            "cmd": "do-payout",
            "msgId": correlId,
            "amount": value
    }))
    msg = wait_for_message(correlId)
    if 'error' in msg.keys():
        print("Error: %s\nPlease try another amount.\n" % msg['error'])
    else:
        status = 'success' if msg['result'] == 'ok' else 'error'
        print("%3d Eurocent dispensed: %s" % (value, status))


if __name__ == '__main__':
    print("Welcome to kassomat maintenance mode!\n")
    while True:

        print("Waiting for current coin levels\n")
        levels = get_levels()
        print("The following coins are in the machine:\n")
        sum = 0
        for value, count in sorted(levels.items()):
            print("%3d Eurocent x %3d" % (value, count))
            sum += int(value) * int(count)

        print("\nHopper money status: %.2f EUR left\n" % (float(sum)/100))

        print("""
        want to payout something?
          - empty line to quit
          - "yes" or anything else, really, to try again.
        """)
        answer = raw_input('> ')
        if answer == '':
            break
        else:
            do_payout(int(answer))

    print("Bye.")
