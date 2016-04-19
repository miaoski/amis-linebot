# -*- coding: utf8 -*-
import sys
import sqlite3
import flask
import uuid
import re
import logging
import ConfigParser
from fuzzy import fuzzme
import requests
import json
import amis

app = flask.Flask(__name__)
app.logger.setLevel(logging.DEBUG)

DATABASE = 'dict-amis.sq3'
LINE_ENDPOINT = "https://trialbot-api.line.me"
USER_LASTWORD = {}
RE_NUM = re.compile(r'[0-9]+')

def connect_db():
    return sqlite3.connect(DATABASE)

@app.before_request
def before_request():
    flask.g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    if hasattr(flask.g, 'db'):
        flask.g.db.close()

@app.route('/')
def homepage():
    return 'Welcome to Amis LINE BOT', 200

@app.route('/fb', methods=['GET', 'POST'])
def fbbot():
    if flask.request.method == 'GET':
        if flask.request.args.get('hub.verify_token') == FB_TOKEN:
            return flask.request.args.get('hub.challenge'), 200
    if flask.request.method == 'POST':
        db = amis.loaddb()
        try:
            app.logger.info(flask.request.json)
            for messaging in flask.request.json['entry'][0]['messaging']:
                msg = messaging['message']['text']
                uid = messaging['sender']['id']
                if RE_NUM.match(msg):
                    choice = int(msg)
                    r = amis.user_input(db, choice, uid)
                else:
                    r = amis.lookup(db, msg, uid)
                send_fb_msg(uid, r)
                return flask.Response(status=200)
        except:
            app.logger.info(flask.request.json)
            return flask.Response(status=400)

def send_fb_msg(uid, msg):
    url = 'https://graph.facebook.com/v2.6/me/messages?access_token=%s' % FB_APP_TOKEN
    data = {'recipient': {'id': uid},
            'message': {'text': msg}}
    app.logger.info(data)
    r = requests.post(url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
    if r.status_code != requests.codes.ok:
        app.logger.warn(str(r.status_code))
        app.logger.warn(str(r.headers))


@app.route('/callback', methods=['POST',])
def line_callback():
    app.logger.info(flask.request.json)
    try:
        req = flask.request.json["result"][0]
    except:
        app.looger.error('No json[result][0]')
        return flask.Response(status=470)
    if req["eventType"] == "138311609100106403":
        send_text([req["from"]], u"Nga'ayho!  Mikamsia to\n謝謝你使用阿美語萌典 Line 機器人!\n")
    elif req["eventType"] == "138311609000106303":
        uid = req["content"]["from"]
        txt = req["content"]["text"].strip()
        if RE_NUM.match(txt):
            choice = int(txt)
            r = amis.user_input(db, choice, uid)
        else:
            r = amis.lookup(db, txt, uid)
        send_text(uid, r)
    return flask.Response(status=200)

def send_text(to, text):
    content = {
        "contentType": 1,
        "toType": 1,
        "text": text
    }
    events(to, content)

def events(to, content):
    app.logger.info(content)
    data = {
        "to": to,
        "toChannel": "1383378250",
        "eventType": "138311608800106203",
        "content": content,
    }
    r = requests.post(LINE_ENDPOINT + "/v1/events", data=json.dumps(data), headers=LINE_HEADERS)
    app.logger.info(r.text)
    return r


if __name__ == "__main__":
    config = ConfigParser.ConfigParser()
    try:
        (FB_TOKEN, FB_APP_TOKEN) = [x.strip() for x in open('fbtoken.cfg')]
    except:
        print u'請修改 fbtoken.cfg'
        raise
    try:
        config.read('linebot.cfg')
        LINE_HEADERS = {
            "X-Line-ChannelID": config.get('linebot', 'channelID'),
            "X-Line-ChannelSecret": config.get('linebot', 'channelSecret'),
            "X-Line-Trusted-User-With-ACL": config.get('linebot', 'MID'),
        }
    except:
        print u'請 cp linebot.cfg.default linebot.cfg 並修改裡面的設定'
        raise
    app.config['JSON_AS_ASCII'] = False     # JSON in UTF-8
    app.config['DEBUG'] = True
    context = ('fullchain.pem', 'privkey.pem') # Copy /etc/letsencrypt/live/ files to current dir
    app.run(host = '0.0.0.0', threaded=False, port=443, ssl_context=context)
    print 'Shutdown...'
