from __future__ import print_function

import json
import requests
from furl import furl
import uuid
import paho.mqtt.client as mqtt


MQTT_SERVER_IP      = "54.250.71.242"
MQTT_SERVER_PORT    = 1883

cloud_user_dev_info_api_url = 'https://www.xizhan.xyz/api/user/dev'
cloud_valid_token_api_url = 'https://www.xizhan.xyz/api/valid'


def get_device_from_private_cloud(token):
    user_devices = []
    params = {
        'get_user_info': True,
        'access_token': token
    }
    url = furl(cloud_user_dev_info_api_url).set(params)
    ret = requests.get(url)

    user_dev_info           = json.loads(ret.text)
    user_dev_names          = user_dev_info['device_names'].split(',')
    user_dev_serial_numbers = user_dev_info['device_serial_number'].split(',')
    user_dev_num            = len(user_dev_names)

    for i in range(user_dev_num):
        user_device = {
            'endpointId': user_dev_serial_numbers[i],
            'friendlyName': user_dev_names[i],
            'description': 'STB from HangZhou NationalChip Company',
            'manufacturerName': 'HangZhou NationalChip Company',
            'displayCategories': [
                'TV'
            ],
            'cookie': {},
            'capabilities': [
                {
                    'type': 'AlexaInterface',
                    'interface': 'Alexa.Speaker',
                    'version': '3',
                    'properties': {
                        'supported': [
                            {
                                'name': 'volume'
                            }
                        ]
                    }
                },
                {
                    'type': 'AlexaInterface',
                    'interface': 'Alexa.ChannelController',
                    'version': '3',
                    'properties': {
                        'supported': [
                            {
                                'name': 'channel'
                            }
                        ]
                    }
                },
                {
                    'type': 'AlexaInterface',
                    'interface': 'Alexa',
                    'version': '3'
                }
            ]
        }

        user_devices.append(user_device)

    return user_devices


def get_uuid():
    return str(uuid.uuid1())


def valid_token(token):
    params = {
        'valid': None,
        'access_token': token
    }
    url = furl(cloud_valid_token_api_url).set(params)
    ret = requests.get(url)
    return json.loads(ret.text)['valid']


def handle_discovery_v3(request):

    # Get the OAuth token from the request.
    user_access_token = request['directive']['payload']['scope']['token']

    # valid access token
    if user_access_token == None or valid_token(user_access_token) == 'false':
        print('The user access token is invalid!')
        response = {
            'state': 'The user access token is invalid!'
        }
        return response

    response = {
        'event': {
            'header': {
                'namespace': 'Alexa.Discovery',
                'name': 'AddOrUpdateReport',
                'payloadVersion': '3',
                'messageId': get_uuid()
            },
            'payload': {
                'endpoints': get_device_from_private_cloud(user_access_token)
            }
        }
    }

    return response


def send_directive_to_STB(topic, msg):
    client = mqtt.Client()
    client.connect(MQTT_SERVER_IP, MQTT_SERVER_PORT, 60)
    client.publish(topic, msg, 1)
    client.disconnect()


def response_directive_for_smarthome_skill(request, directive_name):
    response = {
        'context': {
            'properties': [
                {
                    'namespace': request['directive']['header']['namespace'],
                    'name': directive_name,
                    'value': {
                    }
                }
            ]
        },
        'event': {
            'header': {
                'messageId': get_uuid(),
                'correlationToken': request['directive']['header']['correlationToken'],
                'namespace': 'Alexa',
                'name': 'Response',
                'payloadVersion': '3'
            },
            'endpoint': {
                'endpointId': request['directive']['endpoint']['endpointId']
            }
        },
        'payload': {}
    }

    return response


def handle_change_channel_v3(request):
    device_serial_number = request['directive']['endpoint']['endpointId']
    intent = request['directive']['payload']['channelMetadata']['name']

    if '-' in intent:
        send_directive_to_STB(device_serial_number, 'channel_switch' + intent.split('-')[1])
    else:
        send_directive_to_STB(device_serial_number, 'channel_switch' + intent)

    return response_directive_for_smarthome_skill(request, 'channel')


def handle_skip_channels_v3(request):
    device_serial_number = request['directive']['endpoint']['endpointId']
    intent = request['directive']['payload']['channelCount']

    if intent == 1:
        send_directive_to_STB(device_serial_number, 'channel_up')
    if intent == -1:
        send_directive_to_STB(device_serial_number, 'channel_down')

    return response_directive_for_smarthome_skill(request, 'channel')


def handle_set_volume_v3(request):
    device_serial_number = request['directive']['endpoint']['endpointId']
    intent = request['directive']['payload']['volume']
    send_directive_to_STB(device_serial_number, 'volume_switch' + str(intent))

    return response_directive_for_smarthome_skill(request, 'volume')


def handle_adjust_volume_v3(request):
    device_serial_number = request['directive']['endpoint']['endpointId']
    intent = request['directive']['payload']['volume']
    send_directive_to_STB(device_serial_number, 'volume_up/down' + str(intent))

    return response_directive_for_smarthome_skill(request, 'volume')


# --------------- Main handler ---------------

def lambda_handler(request, context):
    if request['directive']['header']['name'] == 'Discover':
        return handle_discovery_v3(request)
    elif request['directive']['header']['name'] == 'ChangeChannel':
        return handle_change_channel_v3(request)
    elif request['directive']['header']['name'] == 'SkipChannels':
        return handle_skip_channels_v3(request)
    elif request['directive']['header']['name'] == 'SetVolume':
        return handle_set_volume_v3(request)
    elif request['directive']['header']['name'] == 'AdjustVolume':
        return handle_adjust_volume_v3(request)
    else:
        print('No support namespace:' + request['directive']['header']['namespace'])
        response = {
            'response': 'No support namespace:' + request['directive']['header']['namespace']
        }
        return response

