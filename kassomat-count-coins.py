#!/usr/bin/env python2
import json
import uuid
from redis import StrictRedis
import sh


redis = StrictRedis()
pubsub = redis.pubsub()
pubsub.subscribe('hopper-response')
event_pubsub = redis.pubsub()
event_pubsub.subscribe('hopper-event')

def lolprint(msg):
    print(sh.lolcat(sh.echo(msg)))

def to_int(s):
  try:
    return int(s)
  except ValueError:
    return None


def wait_for_message(correlId):
    for msg in pubsub.listen():
        if msg['type'] != 'message':
            continue
        data = json.loads(msg['data'])
        if data['correlId'] == correlId:
 	    return data


def wait_for_event(event):
    for msg in event_pubsub.listen():
        if msg['type'] != 'message':
            continue
        data = json.loads(msg['data'])
        if data['event'] == event:
            return data


def count_coins():
    while True:
        raw_value = raw_input("> to count coins now, please enter 'yes': ")
        if raw_value != 'yes':
    	    break

        smart_empty()

        lolprint("waiting for 'smart emptied' event")  

        smart_emptied = wait_for_event('smart emptied')
        lolprint("amount of money emptied: %d" % (int(smart_emptied['amount'])))

        get_cashbox_payout_operation_data()


def get_cashbox_payout_operation_data(): 
    lolprint("Sending cashbox-payout-operation-data to the machine:")

    correlId = str(uuid.uuid4()) 
    redis.publish('hopper-request', json.dumps({
         "cmd": "cashbox-payout-operation-data",
         "msgId": correlId
    }))
    msg = wait_for_message(correlId)
#   status = 'success' if msg['result'] == 'ok' else 'error'
    status = "ok"
 
    levels = {int(level['value']): int(level['level']) for level in msg['levels']}
    lolprint("Quantity of coins emptied:")
    for value, count in levels.items():
        lolprint("%3d Eurocent x %3d" % (value, levels[value]))


def smart_empty(): 
    lolprint("Sending smart-empty to the machine:")

    correlId = str(uuid.uuid4()) 
    redis.publish('hopper-request', json.dumps({
         "cmd": "smart-empty",
         "msgId": correlId
    }))
    msg = wait_for_message(correlId)
    status = 'success' if msg['result'] == 'ok' else 'error'


if __name__ == '__main__':
    lolprint("Welcome to Count-o-matic!\n")

    count_coins() 
 
    lolprint("Bye.")
