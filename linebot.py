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
USER_DICT = {}
USER_DICT_DEFAULT = 'fey'
SUPPORTED_DICT = {
        'fey': u'阿美語(方敏英)字典', 
        'moe': u'國語萌典',
        'tai': u'臺灣閩南語'}
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
                txt = messaging['message']['text']
                try:
                    txt = txt.strip()
                except:
                    pass
                app.logger.info(u'UID %d 查詢 %s' % (uid, txt))
                if not hasValidDict(uid):
                    sendLineText(uid, u'系統錯誤，已切回阿美語(方敏英)字典。')
                elif txt[0] in ('/', '?'):            # 功能鍵
                    r = command(uid, txt)
                    sendFBMsg(uid, r)
                elif USER_DICT[uid] == 'fey':
                    r = lineAmisDict(uid, txt)
                    sendFBMsg(uid, r)
                elif USER_DICT[uid] == 'moe':
                    r = lineMoeDict(uid, txt)
                    sendFBMsg(uid, r)
                elif USER_DICT[uid] == 'tai':
                    r = lineTaiDict(uid, txt)
                    sendFBMsg(uid, r)
                else:
                    app.logger.error('Should not be here.  Fatal 1.')
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

def sendFBMsg(uid, txt):
    url = 'https://graph.facebook.com/v2.6/me/messages?access_token=%s' % FB_APP_TOKEN
    data = {'recipient': {'id': uid}}
    if isinstance(txt, types.StringTypes):
        data['message'] = {'text': txt}
    elif isinstance(txt, types.DictType):
        if txt['type'] == 'options':                # 選擇單字
            elements = []
            i = 1
            for words in chunks(txt['words'], 3):   # FB 每個 button 最多三個選項
                buttons = [{"type": "postback", "title": xs, "payload": xs} for xs in words]
                elements.append({'title': '%s (%d)' % (txt['text'], i), 'buttons': buttons})
                i = i + 1
            # pprint.pprint(elements)
            data['message'] = {"attachment": {"type":"template", "payload": {"template_type":"generic", 'elements': elements}}}
        elif txt['type'] == 'stropt':               # 要看例句嗎
            data['message'] = {"attachment": {"type":"template", "payload": { 
                "template_type":"button", "text": txt['text'], "buttons": [
                    {"type": "postback", "title": u'看例句', "payload": '**-' + txt['words'][0]},
                    {"type": "postback", "title": u'不看', "payload": '**SkipExample'},
                    ]}}}
        else:
            app.logger.error('Unknown msg %s', txt)
            return
    else:
        app.logger.error('Unknown type %s', str(type(txt)))
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
    for req in flask.request.json["result"]:
        if req["eventType"] == "138311609100106403":
            uid = req["content"]['params'][0]
            sendLineText(uid, u"Nga'ayho!  歡迎使用阿美語萌典 Line 機器人!")
        elif req["eventType"] == "138311609000106303":
            uid = req["content"]["from"]
            txt = req["content"]["text"]
            if txt is None:
                pprint.pprint(req)
                return flask.Response(status=470)
            txt = txt.strip()
            if not hasValidDict(uid):
                sendLineText(uid, u'系統錯誤，已切回阿美語(方敏英)字典。')
            elif txt[0] in ('/', '?'):            # 功能鍵
                r = command(uid, txt)
                sendLineText(uid, r)
            elif USER_DICT[uid] == 'fey':
                r = lineAmisDict(uid, txt)
                sendLineText(uid, r)
            elif USER_DICT[uid] == 'moe':
                r = lineMoeDict(uid, txt)
                sendLineText(uid, r)
            elif USER_DICT[uid] == 'tai':
                r = lineTaiDict(uid, txt)
                sendLineText(uid, r)
            else:
                app.logger.error('Should not be here.  Fatal 1.')
    return flask.Response(status=200)


def hasValidDict(uid):
    global USER_DICT
    if uid not in USER_DICT:
        USER_DICT[uid] = USER_DICT_DEFAULT
    if USER_DICT[uid] in SUPPORTED_DICT:
        return True
    else:
        app.logger.error('Unknown USER_DICT: %s' % uid)
        pprint.pprint(USER_DICT)
        USER_DICT[uid] = USER_DICT_DEFAULT
        return False


def lineAmisDict(uid, txt):
    db = amis.loaddb()
    if RE_NUM.match(txt):             # Line 輸入數字鍵查詢候選詞
        choice = int(txt)
        r = amis.numpadInput(db, choice, uid)
    else:
        r = amis.lookup(db, txt, uid)
    return r


def lineMoeDict(uid, txt):
    print u'UID %s 查國語萌典: %s' % (uid, txt)
    # copied from stackoverflow
    HANUNI = re.compile(ur'^[⺀-⺙⺛-⻳⼀-⿕々〇〡-〩〸-〺〻㐀-䶵一-鿃豈-鶴侮-頻並-龎]+$', re.UNICODE)
    r = 'undefined'
    if HANUNI.match(txt):
        get = requests.get('https://www.moedict.tw/a/%s.json' % txt)
        if get.status_code == 200:
            j = get.json()
            if 'r' in j and 'n' in j:
                r = u'%s (%s部%d劃)\n' % (stripHTML(j['t']), stripHTML(j['r']), j['n'])
            else:
                r = stripHTML(j['t']) + '\n'
            for h in j['h']:
                i = 1
                if 'b' in h and 'p' in h:
                    r = r + u'%s %s\n' % (h['b'], h['p'])
                for d in h['d']:
                    if 'type' in d:
                        word_class = u'[%s詞]' % stripHTML(d['type'])
                    else:
                        word_class = ''
                    r = r + '%d. %s %s\n' % (i, word_class, stripHTML(d['f']))
                    if 'e' in d:
                        for ex in d['e']:
                            r = r + u'　%s\n' % stripHTML(ex)
                    i = i + 1
            return r
        elif get.status_code == 404:
            return u'查無此字。'
        else:
            pprint.pprint(txt)
            app.logger.warn(str(get.status_code))
            app.logger.warn(str(get.text))
            return u'系統錯誤，請稍候再試。'
    else:
        return u'查詢字串內含非漢字的字元，請重新輸入。'
    return r


def lineTaiDict(uid, txt):
    print u'UID %s 查台語萌典: %s' % (uid, txt)
    # copied from stackoverflow
    HANUNI = re.compile(ur'^[⺀-⺙⺛-⻳⼀-⿕々〇〡-〩〸-〺〻㐀-䶵一-鿃豈-鶴侮-頻並-龎]+$', re.UNICODE)
    r = 'undefined'
    if HANUNI.match(txt):
        get = requests.get('https://www.moedict.tw/t/%s.json' % txt)
        if get.status_code == 200:
            j = get.json()
            if 'r' in j and 'n' in j:
                r = u'%s (%s部%d劃)\n' % (stripHTML(j['t']), stripHTML(j['r']), j['n'])
            else:
                r = stripHTML(j['t']) + '\n'
            for h in j['h']:
                i = 1
                reading = stripHTML(h.get('reading', u'發'))
                if 'T' in h:
                    r = r + u'%s音: %s\n' % (reading, h['T'])
                for d in h['d']:
                    if 'type' in d:
                        word_class = u'[%s詞] ' % stripHTML(d['type'])
                    else:
                        word_class = ''
                    r = r + '%d. %s%s\n' % (i, word_class, stripHTML(d['f']))
                    if 'e' in d:
                        for ex in d['e']:
                            r = r + u'　%s\n' % renderMoeExample(stripHTML(ex))
                    i = i + 1
            return r
            # MP3 in https://1763c5ee9859e0316ed6-db85b55a6a3fbe33f09b9245992383bd.ssl.cf1.rackcdn.com/04208.mp3
            # j['h'][0]['_'] left pad 0 to 5 digits
        elif get.status_code == 404:
            return u'查無此字。'
        else:
            pprint.pprint(txt)
            app.logger.warn(str(get.status_code))
            app.logger.warn(str(get.text))
            return u'系統錯誤，請稍候再試。'
    else:
        return u'查詢字串內含非漢字的字元，請重新輸入。'
    return 


def renderMoeExample(s):
    return s.replace(u'\ufff9', '') \
            .replace(u'\ufffa', '(') \
            .replace(u'\ufffb', ')')


def stripHTML(s):
    #TAG_RE = re.compile(r'<[^>]+>')
    #return TAG_RE.sub('', s)
    return s.replace('`', '').replace('~', '')


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


def command(uid, cmd):
    cmd = cmd.lower()
    general_help_msg = u'/ 或 ?: 本使用說明\n'
    for k,v in SUPPORTED_DICT.iteritems():
        general_help_msg += u'/%s : 切換至%s\n' % (k, v)
    hasValidDict(uid)
    if len(cmd) < 2 or cmd == '/?' or cmd == '/h':
        curdict = u'您目前使用的是: %s' % SUPPORTED_DICT.get(USER_DICT[uid], u'不明的外星字典')
        return curdict + '\n' + general_help_msg
    for k,v in SUPPORTED_DICT.iteritems():
        if cmd[1:] == k:
            USER_DICT[uid] = cmd[1:]
            return u'已切換至%s' % v
    return general_help_msg


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
