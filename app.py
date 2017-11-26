# -*- coding: utf8 -*-
import re
import logging
import ConfigParser
import requests
import json
import amis
import moe
import pprint
import types
from flask import Flask, request, abort
from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import (MessageEvent, TextMessage, TextSendMessage)

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)
config = ConfigParser.ConfigParser()
try:
    (FB_TOKEN, FB_APP_TOKEN) = [x.strip() for x in open('fbtoken.cfg')]
except:
    print u'請修改 fbtoken.cfg'
    raise
try:
    config.read('linebot.cfg')
    line_bot_api = LineBotApi(config.get('linebot', 'channelAccessToken'))
    handler = WebhookHandler(config.get('linebot', 'channelSecret'))
except:
    print u'請 cp linebot.cfg.default linebot.cfg 並修改裡面的設定'
    raise

USER_DICT = {}
USER_DICT_DEFAULT = 'safolu'
USER_DICT_CODE = ['fey', 'safolu', 'moe', 'tai', 'hak']
SUPPORTED_DICT = {
        'fey': u'阿美語(方敏英)字典', 
        'safolu': u'阿美語(蔡中涵)字典', 
        'moe': u'國語萌典',
        'tai': u'臺灣閩南語',
        'hak': u'客語萌典'}
RE_NUM = re.compile(r'^[0-9]+$')
FB_MSG_MAXLEN = 300                 # 官方限 320 自我審查一下

@app.route('/')
def homepage():
    return 'Welcome to Amis LINE BOT', 200

@app.route('/fb', methods=['GET', 'POST'])
def fbbot():
    if request.method == 'GET':
        if request.args.get('hub.verify_token') == FB_TOKEN:
            return request.args.get('hub.challenge'), 200
    if request.method == 'POST':
        # app.logger.info(request.json)
        for messaging in request.json['entry'][0]['messaging']:
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
                r = textSearch(uid, txt)
                sendFBMsg(uid, r)
            if 'postback' in messaging:
                if 'payload' not in messaging['postback']:
                    app.logger.warn('How can I know a postback without payload?')
                    pprint.pprint(messaging)
                    continue
                pb = messaging['postback']['payload']
                # print uid,pb
                # app.logger.info(u'UID %d 選取 %s' % (uid, pb))
                r = textSearch(uid, pb)
                sendFBMsg(uid, r)
        return flask.Response(status=200)


def fbSplitMsg(s):
    r = ''
    for x in s.split('\n'):
        if len(x) >= 300:       # 超過 300 個字元的我們就算了
            print u'丟掉超過300字的字串:', x
            continue
        if len(r) + len(x) < 300:
            r = r + x + '\n'
        else:
            yield r
            r = x + '\n'
    yield r


# http://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks-in-python
def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i+n]

def sendFBMsg(uid, txt):
    url = 'https://graph.facebook.com/v2.6/me/messages?access_token=%s' % FB_APP_TOKEN
    data = {'recipient': {'id': uid}}
    if isinstance(txt, types.StringTypes):
        if len(txt) > FB_MSG_MAXLEN:
            for xs in fbSplitMsg(txt):
                sendFBMsg(uid, xs)                  # 在噁心的地方 recursive
        else:
            data['message'] = {'text': txt.strip()}
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

#
# LINE Bot 從這裡開始
#

@app.route('/callback', methods=['POST',])
def linebot_callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def linebot_message(event):
    txt = event.message.text.strip()
    uid = event.source.user_id
    answer = textSearch(uid, txt)
    reply = line_text_postprocess(uid, answer)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply))
    return 0


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


def line_text_postprocess(uid, msg):
    if isinstance(msg, types.StringTypes):
        reply = msg
    elif isinstance(msg, types.DictType):
        if msg['type'] == 'options':        # 選擇單字
            reply = msg['text'] +'\n'+ amis.iterrows([[x,] for x in msg['words']], uid)
        elif msg['type'] == 'stropt':       # 要看例句嗎
            reply = u'%s\n請輸入 0 查看例句' % msg['text']
    else:
        app.logger.error('Unknown msg %s', msg)
    return reply


def command(uid, cmd):
    cmd = cmd.lower()
    general_help_msg = u'/ 或 ?: 本使用說明\n'
    for i in range(len(USER_DICT_CODE)):
        general_help_msg += u'/%d : 切換至%s\n' % (i+1, SUPPORTED_DICT[USER_DICT_CODE[i]])
    hasValidDict(uid)
    if len(cmd) < 2 or cmd == '/?' or cmd == '/h':
        curdict = u'您目前使用的是: %s' % SUPPORTED_DICT.get(USER_DICT[uid], u'不明的外星字典')
        return curdict + '\n' + general_help_msg
    if RE_NUM.match(cmd[1:]):
        try:
            dic = int(cmd[1:]) - 1
            USER_DICT[uid] = USER_DICT_CODE[dic]
            return u'已切換至%s' % SUPPORTED_DICT[USER_DICT_CODE[dic]]
        except:
            return u'沒有這個指令。'
    return general_help_msg


def textSearch(uid, txt):
    app.logger.info(u'UID %s 查詢 %s' % (str(uid), txt))
    hasValidDict(uid)
    if txt[0] in ('/', '?'):            # 功能鍵
        return command(uid, txt)
    if USER_DICT[uid] == 'fey':
        return amis.fey(uid, txt)
    if USER_DICT[uid] == 'safolu':
        return amis.safolu(uid, txt)
    if USER_DICT[uid] == 'moe':
        return moe.guoyu(uid, txt)
    if USER_DICT[uid] == 'tai':
        return moe.taigi(uid, txt)
    if USER_DICT[uid] == 'hak':
        return moe.hakkafa(uid, txt)
    app.logger.error('Should not be here.  Fatal 1.')


#
# main
#
app.config['JSON_AS_ASCII'] = False     # JSON in UTF-8
app.config['DEBUG'] = False
context = ('fullchain.pem', 'privkey.pem') # Copy /etc/letsencrypt/live/ files to current dir
app.run(host = '0.0.0.0', threaded=False, port=8443, ssl_context=context)
