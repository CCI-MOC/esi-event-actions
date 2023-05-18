# SET NOTIFICATION LEVEL TO INFO FOR IRONIC AND IRONIC API; RESTART IRONIC_CONDUCTOR AND IRONIC_API
# MESSAGING DRIVER messagingv2

import configparser
import json
import os
import pika
import re
import sys

def get_object_value_from_key(object_data, key):
    key_list = key.split('.')
    current_object_data = object_data
    for current_key in key_list:
        current_object_data = current_object_data[current_key]
    return current_object_data

def main():
    config = configparser.ConfigParser()
    config.read('esi-event-action-listener.conf')
    user = config['DEFAULT']['user']
    password = config['DEFAULT']['password']
    host = config['DEFAULT']['host']
    port = config['DEFAULT']['port']
    queues = (config['DEFAULT']['queues']).split(',')
    credentials = pika.PlainCredentials(user, password)
    connection_parameters = pika.ConnectionParameters(host, port, '/', credentials)
    connection = pika.BlockingConnection(connection_parameters)
    channel = connection.channel()

    print(' [*] Loading configuration')
    event_dict = {}
    for section in config.sections():
        events = (config[section].get('events')).split(',')
        script = config[section].get('script')
        script_params = (config[section].get('script_params','')).split(',')
        filter_params = json.loads(config[section].get('filter_params', "{}"))
        print(" [*] Loading configuration for %s" % section)
        print("     Script %s will be run for events %s" % (script, events))
        print("     Params: %s" % script_params)
        print("     Filter params: %s" % filter_params)
        for event in events:
            if event not in event_dict:
                event_dict[event] = []
            script_dict = {
                "script": script,
                "script_params": script_params,
                "filter_params": filter_params
            }
            event_dict[event].append(script_dict)

    def callback(ch, method, properties, body):
        message_json = json.loads(json.loads(body)["oslo.message"])
        event = message_json["event_type"]
        ironic_node_data = message_json["payload"]["ironic_object.data"]
        node_name = ironic_node_data["name"]
        node_uuid = ironic_node_data["uuid"]
        print(" [x] Event %s on node %s (%s) " % (event, node_name, node_uuid))
        print("     Node data: %r " % ironic_node_data)
        if event in event_dict:
            for script_dict in event_dict[event]:
                script = script_dict["script"]
                script_params = script_dict["script_params"]
                filter_params = script_dict["filter_params"]
                node_params = []
                print("     Checking script %s on node %s" % (script, node_name))
                should_run = True
                for key in filter_params:
                    param_value = get_object_value_from_key(ironic_node_data, key)
                    pattern = re.compile(filter_params[key])
                    print("     Filtering %s with pattern %s" % (key, pattern))
                    if not pattern.match(param_value):
                        print("     Excluding because %s value is %s" % (key, param_value))
                        should_run = False
                        continue
                if not should_run:
                    continue
                for script_param in script_params:
                    param_value = get_object_value_from_key(ironic_node_data, script_param)
                    node_params.append(param_value)
                print("     Running script %s with params %s" % (script, node_params))
                os.system("%s %s" % (script, ' '.join(node_params)))

    for queue in queues:
        channel.queue_declare(queue=queue)
        channel.basic_consume(queue=queue, on_message_callback=callback, auto_ack=True)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
