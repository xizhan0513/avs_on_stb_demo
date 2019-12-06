from __future__ import print_function

import json
import requests
from furl import furl


# Resource server interface
cloud_api_url = 'https://www.xizhan.xyz/api'


"""
This sample demonstrates a simple skill built with the Amazon Alexa Skills Kit.
The Intent Schema, Custom Slots, and Sample Utterances for this skill, as well
as testing instructions are located at http://amzn.to/1LzFrj6
For additional samples, visit the Alexa Skills Kit Getting Started guide at
http://amzn.to/1LGWsLG
"""

# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': "SessionSpeechlet - " + title,
            'content': "SessionSpeechlet - " + output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------

def get_welcome_response():
    """ If we wanted to initialize the session to have some attributes we could
    add those here
    """

    card_title = "Welcome"
    speech_output = "Welcome to hangzhou nationalchip"
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "you can try to say bedroom channel up or living room volume down"
    should_end_session = False
    return build_response({}, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Thank you for trying the nationalchip Alexa Skills. " \
                    "Have a nice day! "
    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def after_set_response(msg):
    card_title = "Response"
    speech_output = "ok, " + msg
    should_end_session = False
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def set_channel_up(intent, session):
    id = intent['slots']['channel_up_location_slot']['resolutions']['resolutionsPerAuthority'][0]['values'][0]['value']['id']
    location = intent['slots']['channel_up_location_slot']['resolutions']['resolutionsPerAuthority'][0]['values'][0]['value']['name']

    params = {
        'dev_id': id,
        'intent': intent['name'],
        'access_token': session['user']['accessToken']
    }
    url = furl(cloud_api_url).set(params)
    requests.get(url=url)

    return after_set_response(location + " channel up")


def set_channel_down(intent, session):
    id = intent['slots']['channel_down_location_slot']['resolutions']['resolutionsPerAuthority'][0]['values'][0]['value']['id']
    location = intent['slots']['channel_down_location_slot']['resolutions']['resolutionsPerAuthority'][0]['values'][0]['value']['name']

    params = {
        'dev_id': id,
        'intent': intent['name'],
        'access_token': session['user']['accessToken']
    }
    url = furl(cloud_api_url).set(params)
    requests.get(url=url)

    return after_set_response(location + " channel down")


def set_channel_switch(intent, session):
    id = intent['slots']['channel_switch_location_slot']['resolutions']['resolutionsPerAuthority'][0]['values'][0]['value']['id']
    location = intent['slots']['channel_switch_location_slot']['resolutions']['resolutionsPerAuthority'][0]['values'][0]['value']['name']
    value = intent['slots']['channel_switch_numbers_slot']['value']

    params = {
        'dev_id': id,
        'intent': intent['name'],
        'value': value,
        'access_token': session['user']['accessToken']
    }
    url = furl(cloud_api_url).set(params)
    requests.get(url=url)

    return after_set_response(location + " switch channel to " + value)


def set_volume_up(intent, session):
    id = intent['slots']['volume_up_location_slot']['resolutions']['resolutionsPerAuthority'][0]['values'][0]['value']['id']
    location = intent['slots']['volume_up_location_slot']['resolutions']['resolutionsPerAuthority'][0]['values'][0]['value']['name']

    params = {
        'dev_id': id,
        'intent': intent['name'],
        'access_token': session['user']['accessToken']
    }
    url = furl(cloud_api_url).set(params)
    requests.get(url=url)

    return after_set_response(location + " volume up")


def set_volume_down(intent, session):
    id = intent['slots']['volume_down_location_slot']['resolutions']['resolutionsPerAuthority'][0]['values'][0]['value']['id']
    location = intent['slots']['volume_down_location_slot']['resolutions']['resolutionsPerAuthority'][0]['values'][0]['value']['name']

    params = {
        'dev_id': id,
        'intent': intent['name'],
        'access_token': session['user']['accessToken']
    }
    url = furl(cloud_api_url).set(params)
    requests.get(url=url)

    return after_set_response(location + " volume down")


def set_volume_switch(intent, session):
    id = intent['slots']['volume_switch_location_slot']['resolutions']['resolutionsPerAuthority'][0]['values'][0]['value']['id']
    location = intent['slots']['volume_switch_location_slot']['resolutions']['resolutionsPerAuthority'][0]['values'][0]['value']['name']
    value = intent['slots']['volume_switch_numbers_slot']['value']

    params = {
        'dev_id': id,
        'intent': intent['name'],
        'value': value,
        'access_token': session['user']['accessToken']
    }
    url = furl(cloud_api_url).set(params)
    requests.get(url=url)

    return after_set_response(location + ' switch volume to ' + value)


# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch

    return get_welcome_response()


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to your skill's intent handlers
    if intent_name == "channel_up":
        return set_channel_up(intent, session)
    elif intent_name == "channel_down":
        return set_channel_down(intent, session)
    elif intent_name == "channel_switch":
        return set_channel_switch(intent, session)
    elif intent_name == "volume_up":
        return set_volume_up(intent, session)
    elif intent_name == "volume_down":
        return set_volume_down(intent, session)
    elif intent_name == "volume_switch":
        return set_volume_switch(intent, session)
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.
    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here


# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    if (event['session']['application']['applicationId'] !=
            "amzn1.ask.skill.d48a9b6f-b54f-4654-a5cb-5517eb174f45"):
        raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])

    raise ValueError("Invalid request type")

