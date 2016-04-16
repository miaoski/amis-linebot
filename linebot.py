# -*- coding: utf8 -*-
import sys
import sqlite3
from flask import Flask, g, request, Response
import uuid
import re
import requests
import logging
import ConfigParser

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

DATABASE = 'dict-amis.sq3'
LINE_ENDPOINT = "https://trialbot-api.line.me"

def connect_db():
    return sqlite3.connect(DATABASE)

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'):
        g.db.close()

@app.route('/')
def homepage():
    return 'Welcome to Amis LINE BOT', 200

@app.route('/callback', methods=['POST',])
def line_callback():
    app.logger.info(request.json)
    app.logger.info(request.headers)
    if not signature_validation(request.get_data()):
        return Response(status=470)
    req = request.json["result"][0]
    if req["eventType"] == "138311609100106403":
        send_text([req["from"]], u"Nga'ayho!  Mikamsia to\n謝謝你使用阿美語萌典 Line 機器人!\n")
    elif req["eventType"] == "138311609000106303":
        to = [req["content"]["from"]]
        txt = req["content"]["text"].strip()
        if isCJK('txt'):
            send_text(to, '漢字查阿美語，查查查...還沒做好 :(')
        else:
            send_text(to, '阿美語查漢語，查查查...還沒做好 :(')
    return Response(status=200)

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
        "content": content
    }
    r = requests.post(LINE_ENDPOINT + "/v1/events", json=data, headers=LINE_HEADERS)
    app.logger.info(r.text)

def isCJK(s):
    return re.match(r'[\u00-\uff]+', s) is None


def lookup(s):
    return u'你查的是: ' + s

def testme():
    print 'False ==', isCJK("nga'aiho")
    print 'True ==', isCJK(u'貓')
    print lookup('pusi')
    print lookup('posi')
    print lookup('pusi\'')
    print lookup('pusi^')
    print lookup(u'貓')
    sys.exit(10)

if __name__ == "__main__":
    testme()
    config = ConfigParser.ConfigParser()
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
    app.config['DEBUG'] = False
    context = ('cert1.pem', 'privkey1.pem') # Copy /etc/letsencrypt/live/ files to current dir
    app.run(host = '0.0.0.0', threaded=False, port=8443, ssl_context=context)
    print 'Shutdown...'
