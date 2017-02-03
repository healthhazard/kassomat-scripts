#!/usr/bin/env python2
import json
import uuid
from redis import StrictRedis


redis = StrictRedis()
pubsub = redis.pubsub()
pubsub.subscribe('hopper-response')
event_pubsub = redis.pubsub()
event_pubsub.subscribe('hopper-event')


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


def ssp_get_all_levels():
    print("[SSP] Sending get-all-levels to the machine:")

    correlId = str(uuid.uuid4())
    redis.publish('hopper-request', json.dumps({
    	"cmd": "get-all-levels",
   	 "msgId": correlId
    }))
    msg = wait_for_message(correlId)
    return {int(level['value']): int(level['level']) for level in msg['levels']}


def ssp_get_cashbox_payout_operation_data(): 
    print("[SSP] Sending cashbox-payout-operation-data to the machine:")

    correlId = str(uuid.uuid4()) 
    redis.publish('hopper-request', json.dumps({
         "cmd": "cashbox-payout-operation-data",
         "msgId": correlId
    }))
    msg = wait_for_message(correlId)
#    status = 'success' if msg['result'] == 'ok' else 'error'
    status = "ok"
 
    levels = {int(level['value']): int(level['level']) for level in msg['levels']}
    print("Quantity of coins emptied:")
    for value, count in levels.items():
        print("%3d Eurocent x %3d" % (value, levels[value]))


def ssp_smart_empty(): 
    print("[SSP] Sending smart-empty to the machine:")

    correlId = str(uuid.uuid4()) 
    redis.publish('hopper-request', json.dumps({
         "cmd": "smart-empty",
         "msgId": correlId
    }))
    msg = wait_for_message(correlId)
    status = 'success' if msg['result'] == 'ok' else 'error'


def ssp_set_levels(levels): 
    print("[SSP] Sending set-denomination-level to the machine:")
    print("Sending the following values to the machine:")

    for value, count in levels.items():
        correlId = str(uuid.uuid4()) 
        redis.publish('hopper-request', json.dumps({
            "cmd": "set-denomination-level",
            "msgId": correlId,
	    "amount": value,
	    "level": count
	}))
        msg = wait_for_message(correlId)
        status = 'success' if msg['result'] == 'ok' else 'error'
        print("%3d Eurocent x %3d : %s" % (value, levels[value], status))


def refill():
    print("Welcome to refill mode!")

    initialExpectedCoins = ssp_get_all_levels()
    
    # press enter to continue

    ssp_smart_empty()
    wait_for_event('smart emptied')
    # machine is empty now!

    initialActualCoins = ssp_get_cashbox_payout_operation_data()
    # amount for value 0 indicates the unknown coins! -> remove after check for amount == 0

    bool initialStateOk = initialExpectedCoins eq initialActualCoins

    print("Put the additional coins into the machine now")
 
    # press enter to continue

    ssp_smart_empty()
    wait_for_event('smart emptied')
    # machine is empty now!

    additionalCoins = ssp_get_cashbox_payout_operation_data()
    # amount for value 0 indicates the unknown coins! -> remove after check for amount == 0

    finalExpectedCoins = initialActualCoins + additionalCoins

    print("Put *all* the coins into the machine now")

    # press enter to continue

    ssp_smart_empty()
    wait_for_event('smart emptied')
    # machine is empty now!

    finalActualCoins = ssp_get_cashbox_payout_operation_data()
    # amount for value 0 indicates the unknown coins! -> remove after check for amount == 0

    bool finalStateOk = finalExpectedCoins eq finalActualCoins

    print("Put *all* the coins back into the machine now")

    ssp_set_levels(finalActualCoins)

    # check the levels with the finalActualCoins here
    ssp_get_all_levels()

    print("**DONE**")


if __name__ == '__main__':
    print("Welcome to Refill-o-matic!\n")

    refill() 
 
    print("Bye.")
