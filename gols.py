#!/usr/bin/env python3

import os
import re

import requests
from bs4 import BeautifulSoup

import json

def main():
    # Get absolute path of JSON file
    script_dir = os.path.dirname(__file__)
    rel_path = "gols.json"
    abs_json_path = os.path.join(script_dir, rel_path)

    # Get JSON data
    with open(abs_json_path, 'r') as f:
        golsdata = json.load(f)

    # Login to Garmin connect
    session = login(golsdata['username'], golsdata['password'])

    # Call upload for each directory
    for directory in golsdata['directories']:
        upload(directory, session)

def login(username, password):
    print("Logging in...")

    WEBHOST = "https://connect.garmin.com"
    REDIRECT = "https://connect.garmin.com/modern/"
    BASE_URL = "https://connect.garmin.com/signin/"
    # GAUTH = "http://connect.garmin.com/gauth/hostname"
    SSO = "https://sso.garmin.com/sso"
    CSS = "https://static.garmincdn.com/com.garmin.connect/ui/css/gauth-custom-v1.2-min.css"

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:66.0) Gecko/20100101 Firefox/66.0',
        'Origin': "https://sso.garmin.com"
    }

    params = {'service': REDIRECT,
              'webhost': WEBHOST,
              'source': BASE_URL,
              'redirectAfterAccountLoginUrl': REDIRECT,
              'redirectAfterAccountCreationUrl': REDIRECT,
              'gauthHost': SSO,
              'locale': 'en_US',
              'id': 'gauth-widget',
              'cssUrl': CSS,
              'clientId': 'GarminConnect',
              'rememberMeShown': 'true',
              'rememberMeChecked': 'false',
              'createAccountShown': 'true',
              'openCreateAccount': 'false',
              'displayNameShown': 'false',
              'consumeServiceTicket': 'false',
              'initialFocus': 'true',
              'embedWidget': 'false',
              'generateExtraServiceTicket': 'true',
              'generateTwoExtraServiceTickets': 'false',
              'generateNoServiceTicket': 'false',
              'globalOptInShown': 'true',
              'globalOptInChecked': 'false',
              'mobile': 'false',
              'connectLegalTerms': 'true',
              'locationPromptShown': 'true',
              'showPassword': 'true'}

    data_login = {
        'username': username,
        'password': password,
        'embed': 'false'
    }

    # begin session with headers because, requests client isn't an option, dunno if Icewasel is still banned...
    print('Login into Garmin connect')
    s = requests.session()
    s.headers.update(headers)
    # we need the cookies and csrf token from the login page before we can post the user/pass
    url_gc_login = 'https://sso.garmin.com/sso/signin'
    req_login = s.get(url_gc_login, params=params, headers=headers)
    if req_login.status_code != 200:
        print('issue with {}'.format(
            req_login))

    csrf_input = BeautifulSoup(req_login.content.decode(), 'html.parser').find('input', {'name': '_csrf'})
    if not csrf_input or not csrf_input.get('value'):
        raise Exception('Unable to get csrf token from login page.')
    data_login['_csrf'] = csrf_input.get('value')

    req_login2 = s.post(url_gc_login, data=data_login, params=params, headers=headers)
    if req_login2.status_code != 200:
        print('issue with {}'.format(
            req_login2))
    # extract the ticket from the login response
    pattern = re.compile(r".*\?ticket=([-\w]+)\";.*", re.MULTILINE | re.DOTALL)
    match = pattern.match(req_login2.content.decode())
    if not match:
        raise Exception('Did not get a ticket in the login response. Cannot log in. Did you enter the correct username and password?')
    login_ticket = match.group(1)
    print('login ticket=' + login_ticket)

    url_gc_post_auth = 'https://connect.garmin.com/modern/activities?'

    params_post_auth = {'ticket': login_ticket}
    req_post_auth = s.get(url_gc_post_auth, params=params_post_auth)
    if req_post_auth.status_code != 200:
        raise Exception('issue with {}'.format(req_post_auth))
    else:
        print("Login OK")
        return s

def upload(directory_fit, session):
    print("Uploading...")

    # url_upload = 'https://connect.garmin.com/proxy/upload-service-1.1/json/upload/.fit'
    url_upload = 'https://connect.garmin.com/modern/proxy/upload-service/upload/.fit'
    if len(os.listdir(directory_fit)):
        for filename in [f for f in os.listdir(directory_fit) if os.path.isfile(os.path.join(directory_fit, f))]:
            print('uploading:  {}'.format(filename))
            files = {'data': (filename,
                              open(os.path.join(directory_fit, filename), 'rb'),
                              'application/octet-stream')
                     }
            session.headers.update({'Referer': 'https://connect.garmin.com/modern/import-data', 'NK': 'NT'})
            req5 = session.post(url_upload, files=files)
            # Succesful status code is 201 Created for activity and 202 Accepted for wellness files
            success_codes = [201, 202]
            if req5.status_code not in success_codes:
                print(
                    'issue with {}'.format(
                        req5))
            else:
                print("Succesfully uploaded {}".format(filename))

            # fn = req5.json()['detailedImportResult']['fileName']
            if 'failures' in req5.json()['detailedImportResult']:
                for failure in req5.json()['detailedImportResult']['failures']:
                    m_failures = failure['messages'][0]['content']
                    print(m_failures)
            if 'successes' in req5.json()['detailedImportResult']:
                for successes in req5.json()['detailedImportResult']['successes']:
                    m_success = 'https://connect.garmin.com/modern/activity/' + str(
                        successes['internalId'])
                    print(m_success)

        print('Done uploading')
    else:
        print('No file found in {}'.format(directory_fit))
    print('Finished')



if __name__ == "__main__":
    main()
