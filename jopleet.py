#!/usr/bin/env python3

# jopleet.py, Copyright (c) 2020 Jan-Piet Mens <jp@mens.de>
# Obtain text and images from individual tweet URLs and submit as
# new notes to a Joplin notebook.

import configparser
from string import Template
import tweepy
import os
import sys
import json
import requests
import re

jurl = None
token = None
parent_folder = None

# This is the Markdown template which will be written to each note.

t = Template("""$text

$images

$name (@$screen_name)
[$date]($url)
""")

def upload_image(filename, url):
    """ url points to image in tweet; download the bytes and upload
        to Joplin; return a resource_id """

    resource_id = None
    joplin_url = "{0}/resources?token={1}".format(jurl, token)

    payload = {
        "title" : filename,
    }

    tw_r = requests.get(url)
    if tw_r.status_code == 200:
        # tw_r.decode_content = True

        files = {
            "data" : (filename, tw_r.content, "application/octet-stream"),
            "props" : (None, json.dumps(payload), "application/json"),
        }

        r = requests.request("POST", verify=False, url=joplin_url, files=files)
        if r.status_code == 200:
            data = json.loads(r.text)
            resource_id = data['id']
        else:
            print("UPLOAD of image failed", r.content)
            print(r.status_code)

    return resource_id

def trunc(s, length=50):
    if len(s) <= length:
        return s
    else:
        return " ".join(s[:length + 1].split(' ')[0:-1]) + "..."

def new_note(params):

    # print(params)

    headers = {
        "Content-type" : "application/json",
        "Accept" : "text/plain"
    }
    joplin_url = "{0}/notes?token={1}".format(jurl, token)

    data = {
        "parent_id"     : parent_folder,
        "is_todo"       : 0,
        "title"         : trunc(params["text"]),
        "body"          : params["body"],
        "author"        : params["screen_name"],
        "source_url"    : params["url"],
    }

    if "lat" in params:
        # warning: Joplin wants strings!
        data["latitude"] = str(params["lat"])
        data["longitude"] = str(params["lon"])
        data["altitude"] = "0.0000"

    print(json.dumps(data, indent=4))

    r = requests.post(joplin_url, data=json.dumps(data), headers=headers)
    if r.status_code == 200:
        print(r.text)

def store(api, url, status):

    status_id = status.id
    # remove link to tweet in body
    s = re.sub('https://t\.co/[a-zA-Z0-9]+$', '', status.full_text)
    images = ""
    params = {
        'url'           : url,
        'status_id'     : status_id,
        'date'          : status.created_at,
        'name'          : status.user.name,
        'screen_name'   : status.user.screen_name,
        'profile_img'   : status.user.profile_image_url_https,
        'text'          : s,
        'images'        : images,
    }

    # Coordinates do not yet work, due to a bug I just submitted
    # https://github.com/laurent22/joplin/issues/3884

    if status.coordinates is not None:
        if "coordinates" in status.coordinates:
            params["lon"] = status.coordinates["coordinates"][0]
            params["lat"] = status.coordinates["coordinates"][1]

    # see if we have media and upload each image (warning: no check!)
    # to Joplin; assemble resource_ids so we can create Markdown
    # image links to add to the note's body

    if 'extended_entities' in status._json:
        if 'media' in status._json["extended_entities"]:
            for image in status._json["extended_entities"]['media']:
                u = image['media_url']
                # get image, send to Joplin
                basename = u.split('/')[-1]
                filename = f'tweet_{status_id}-{basename}'
                resource_id = upload_image(filename, u)
                if resource_id is not None:
                    images = images + f'![{filename}](:/{resource_id})\n\n'

    params['images'] = images

    params["body"] = t.substitute(params)

    new_note(params)

if __name__ == '__main__':

    config = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "jopleet.config")

    configparser = configparser.RawConfigParser()
    configparser.read(config)

    jurl = configparser.get('authentication', 'joplin_url')
    token = configparser.get('authentication', 'token')
    parent_folder = configparser.get('authentication', 'parent_folder')

    ConsumerKey = configparser.get('authentication', 'ConsumerKey')
    ConsumerSecret = configparser.get('authentication', 'ConsumerSecret')
    AccessToken = configparser.get('authentication', 'AccessToken')
    AccessTokenSecret = configparser.get('authentication', 'AccessTokenSecret')

    auth = tweepy.OAuthHandler(ConsumerKey, ConsumerSecret)
    auth.set_access_token(AccessToken, AccessTokenSecret)
    api = tweepy.API(auth)

    for url in sys.argv[1:]:
        status_id = url.split('/')[-1]

        status = api.get_status(status_id, include_entities=True, tweet_mode='extended')
        store(api, url, status)

