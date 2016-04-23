# -*- coding: utf8 -*-
import sys
import sqlite3
import flask
import uuid
import re
import logging
import ConfigParser
import requests
import json
import amis
import pprint
import types

app = flask.Flask(__name__)
app.logger.setLevel(logging.DEBUG)

DATABASE = 'dict-amis.sq3'
LINE_ENDPOINT = "https://trialbot-api.line.me"
USER_LASTWORD = {}
USER_STAT = {}
RE_NUM = re.compile(r'^[0-9]+$')

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
        # app.logger.info(flask.request.json)
        for messaging in flask.request.json['entry'][0]['messaging']:
            if 'sender' not in messaging:
                app.logger.warn('How can I response to a message without sender?')
                pprint.pprint(messaging)
                continue
            if 'id' not in messaging['sender']:
                app.logger.warn('How can I response to a sender without id?')
                pprint.pprint(messaging)
                continue
            uid = messaging['sender']['id']
            if 'message' in messaging:
                if 'text' not in messaging['message']:
                    sendFBMsg(uid, u'本機器人只接受文字查詢哦!')
                    return flask.Response(status=200)
                msg = messaging['message']['text']
                app.logger.info(u'UID %d 查詢 %s' % (uid, msg))
                r = amis.lookup(db, msg, uid)
                sendFBMsg(uid, r)
            if 'postback' in messaging:
                if 'payload' not in messaging['postback']:
                    app.logger.warn('How can I know a postback without payload?')
                    pprint.pprint(messaging)
                    continue
                pb = messaging['postback']['payload']
                if pb == '**SkipExample':       # 不看例句
                    app.logger.info(u'UID %d 不看例句' % uid)
                    r = u'請輸入您要查詢的單字。'
                elif pb.startswith('**-'):
                    app.logger.info(u'UID %d 看例句 %s' % (uid, pb))
                    r = amis.getExample(db, pb[3:])
                else:
                    app.logger.info(u'UID %d 選取 %s' % (uid, pb))
                    r = amis.lookup(db, pb, uid)
                sendFBMsg(uid, r)
        return flask.Response(status=200)


# http://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks-in-python
def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i+n]

def sendFBMsg(uid, msg):
    url = 'https://graph.facebook.com/v2.6/me/messages?access_token=%s' % FB_APP_TOKEN
    data = {'recipient': {'id': uid}}
    if isinstance(msg, types.StringTypes):
        data['message'] = {'text': msg}
    elif isinstance(msg, types.DictType):
        if msg['type'] == 'options':                # 選擇單字
            elements = []
            i = 1
            for words in chunks(msg['words'], 3):   # FB 每個 button 最多三個選項
                buttons = [{"type": "postback", "title": xs, "payload": xs} for xs in words]
                elements.append({'title': '%s (%d)' % (msg['text'], i), 'buttons': buttons})
                i = i + 1
            # pprint.pprint(elements)
            data['message'] = {"attachment": {"type":"template", "payload": {"template_type":"generic", 'elements': elements}}}
        elif msg['type'] == 'stropt':               # 要看例句嗎
            data['message'] = {"attachment": {"type":"template", "payload": { 
                "template_type":"button", "text": msg['text'], "buttons": [
                    {"type": "postback", "title": u'看例句', "payload": '**-' + msg['words'][0]},
                    {"type": "postback", "title": u'不看', "payload": '**SkipExample'},
                    ]}}}
        else:
            app.logger.error('Unknown msg %s', msg)
            return
    else:
        app.logger.error('Unknown type %s', str(type(msg)))
        return
    # app.logger.info('response to %d' % uid)
    r = requests.post(url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
    if r.status_code != requests.codes.ok:
        pprint.pprint(data)
        app.logger.warn(str(r.status_code))
        app.logger.warn(str(r.headers))


def isValidChannelSignature(exp, raw):
    import hashlib
    import hmac
    import base64
    secret = LINE_HEADERS['X-Line-ChannelSecret']
    calc = base64.b64encode(hmac.new(secret, raw, digestmod=hashlib.sha256).digest())
    if exp != calc:
        print 'X-Line-Channelsignature: ' + exp
        print 'Calculated             : ' + calc
        return False
    else:
        return True

@app.route('/callback', methods=['POST',])
def linebot():
    import urllib
    if 'X-Line-Channelsignature' not in flask.request.headers:
        app.logger.warn('No Channelsignature')
        return flask.Response(status=470)
    if not isValidChannelSignature(
            urllib.unquote(flask.request.headers['X-Line-Channelsignature']), 
            flask.request.get_data()):
        app.logger.info(flask.request.json)
        return flask.Response(status=470)
    if not flask.request.json:
        app.logger.warn('No JSON')
        app.logger.info(flask.request.json)
        return flask.Response(status=470)
    if 'result' not in flask.request.json:
        app.logger.warn('There is no result in request.json')
        app.logger.info(flask.request.json)
        return flask.Response(status=470)
    db = amis.loaddb()
    for req in flask.request.json["result"]:
        if req["eventType"] == "138311609100106403":
            pprint.pprint(req)
            uid = req["content"]['params'][0]
            sendLineText(uid, u"Nga'ayho!  歡迎使用阿美語萌典 Line 機器人!")
        elif req["eventType"] == "138311609000106303":
            uid = req["content"]["from"]
            txt = req["content"]["text"]
            if txt is None:
                pprint.pprint(req)
                return flask.Response(status=470)
            txt = txt.strip()
            if RE_NUM.match(txt):
                choice = int(txt)
                r = amis.numpadInput(db, choice, uid)
            else:
                r = amis.lookup(db, txt, uid)
            sendLineText(uid, r)
    return flask.Response(status=200)

def sendLineText(to, msg):
    data = { "contentType": 1, "toType": 1 }
    if isinstance(msg, types.StringTypes):
        data['text'] = msg
    elif isinstance(msg, types.DictType):
        if msg['type'] == 'options':        # 選擇單字
            data['text'] = msg['text'] +'\n'+ amis.iterrows([[x,] for x in msg['words']], to)
        elif msg['type'] == 'stropt':       # 要看例句嗎
            data['text'] = u'%s\n請輸入 0 查看例句' % msg['text']
    else:
        app.logger.error('Unknown msg %s', msg)
    lineEvents(to, data)

def lineEvents(to, content):
    data = {
        "to": [to,],
        "toChannel": 1383378250,
        "eventType": "138311608800106203",
        "content": content,
    }
    # app.logger.info(data)
    r = requests.post(LINE_ENDPOINT + "/v1/events", data=json.dumps(data), headers=LINE_HEADERS)
    if r.status_code != requests.codes.ok:
        pprint.pprint(data)
        app.logger.warn(str(r.status_code))
        app.logger.warn(str(r.headers))
        app.logger.warn(str(r.text))


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
            "Content-Type": 'application/json; charset=UTF-8',
        }
    except:
        print u'請 cp linebot.cfg.default linebot.cfg 並修改裡面的設定'
        raise
    app.config['JSON_AS_ASCII'] = False     # JSON in UTF-8
    app.config['DEBUG'] = True
    context = ('fullchain.pem', 'privkey.pem') # Copy /etc/letsencrypt/live/ files to current dir
    app.run(host = '0.0.0.0', threaded=False, port=8443, ssl_context=context)
    print 'Shutdown...'
