#!/usr/bin/env python2
import json
import uuid
from redis import StrictRedis
import sh


redis = StrictRedis()
pubsub = redis.pubsub()
pubsub.subscribe('hopper-response')

def lolprint(msg):
    print(sh.lolcat(sh.echo(msg)))

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


def change_levels(levels):
    lollolprint("""
    Please enter the desired coin value.
     - empty line to quit
     - raw numbers to add coins.
     - prefix "-" to remove coins.
     - prefix "=" to set an absolute amount of coins
    """)
    
    while True:
        raw_value = raw_input("> coin value: ")
        if raw_value == '':
    	    break
        try:
          value = int(raw_value)
        except ValueError:
          value = None
        if not value or value not in levels.keys():
    	    lolprint("invalid value, valid are:",
    	    ", ".join([str(k) for k in levels.keys()]))
    	    continue
    
        raw_count = raw_input("> count: ")
        
        if len(raw_count) > 1 and raw_count[0] in ('-', '='):
            operator = raw_count[0]
            raw_count = raw_count[1:]
        else:
            operator = None
    
        if raw_count == '':
            break
        try:
            count = int(raw_count)
        except ValueError:
            lolprint("invalid count, please enter an integer.")
            continue
    
        if operator == '=':
            levels[value] = count
        elif operator == '-':
            absolute = levels[value] - count
            levels[value] = absolute if absolute > 0 else 0
        else:
            levels[value] = levels[value] + count
    
        lolprint("new: %3d Eurocent x %3d" % (value, levels[value]))
    return levels


def set_levels(levels): 
    lolprint("Sending the following values to the machine:")
    for value, count in sorted(levels.items()):
        correlId = str(uuid.uuid4()) 
        redis.publish('hopper-request', json.dumps({
            "cmd": "set-denomination-level",
            "msgId": correlId,
	    "amount": value,
	    "level": count
	}))
        msg = wait_for_message(correlId)
        status = 'success' if msg['result'] == 'ok' else 'error'
        lolprint("%3d Eurocent x %3d : %s" % (value, levels[value], status))



if __name__ == '__main__':
    lolprint("Welcome to kassomat maintenance mode!\n")
    lolprint("Waiting for current coin levels\n")
    levels = get_levels()
    lolprint("The following coins are in the machine:\n")
    for value, count in sorted(levels.items()):
        lolprint("%3d Eurocent x %3d" % (value, count))

    while True:
        levels = change_levels(levels)
        set_levels(levels)
        
        lolprint("""
        want to change something?
          - empty line to quit
          - "yes" or anything else, really, to try again.
        """)
        answer = raw_input('> ')
        if answer == '':
            break 
 
    lolprint("Bye.")
