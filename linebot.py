# -*- coding: utf8 -*-
import sys
import sqlite3
from flask import Flask, g, request, Response
import uuid
import re
import requests
import logging
import ConfigParser
from fuzzy import fuzzme

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

DATABASE = 'dict-amis.sq3'
LINE_ENDPOINT = "https://trialbot-api.line.me"
USER_LASTWORD = {}

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


def iterrows(cur, uid):
    global USER_LASTWORD
    i = 1
    r = ''
    USER_LASTWORD[uid] = [None,]
    for row in cur:
        USER_LASTWORD[uid].append(row[0])
        r += '%d. %s\n' % (i, row[0])
        i += 1
    return r


def lookup(db, s, uid):
    global USER_LASTWORD
    cur = db.cursor()
    if isCJK(s):    # 漢語查阿美語
        cur.execute('SELECT title FROM amis WHERE example IS NULL AND cmn LIKE ? ORDER BY LENGTH(cmn)', ('%%' +s+ '%%', ))
        rows = cur.fetchall()
        if len(rows) == 0:
            return u'找不到這個詞。'
        else:
            return u'「' +s+ u'」可能的阿美語詞有:\n' + iterrows(rows, uid) + u'請輸入號碼查詢單字。'
    else:           # 阿美語查字典
        cur.execute('SELECT cmn FROM amis WHERE title=? AND example IS NULL', (s, ))
        rows = cur.fetchall()
        if len(rows) > 0:    # 找到了
            USER_LASTWORD[uid] = [s,]
            return iterrows(rows, '') + u'要看例句請輸入 0'
        cur.execute('SELECT amis FROM fuzzy WHERE fuzz LIKE ?', ('%%' + fuzzme(s) + '%%', ))
        rows = cur.fetchall()
        if len(rows) == 0:
            return u'找不到這個詞。'
        else:
            return u'請問你要找的是哪個詞?\n' + iterrows(rows, uid) + u'請輸入數字選擇。'

def user_input(db, num, uid):
    print u'>>> 使用者 [%s] 輸入了 %d' % (uid, num)
    if uid not in USER_LASTWORD:
        return u'請重新查詢單字。'
    choices = USER_LASTWORD[uid]
    if num + 1 > len(choices):
        return u'請重新選擇。'
    if num == 0:
        return get_example(db, choices[0])
    word = choices[num]
    return lookup(db, word, uid)


def get_example(db, s):
    cur = db.cursor()
    cur.execute('SELECT example, cmn FROM amis WHERE title=? AND example IS NOT NULL', (s,))
    rows = cur.fetchall()
    if len(rows) == 0:
        return u'詞條 %s 沒有例句。' % s
    i = 1
    r = '%s:\n' % s
    for row in cur:
        r += '%d. %s\n' % (i, row[0])
        r += '    %s\n' % (row[1],  )
        i += 1
    return r


def testme():
    db = connect_db()
    cur = db.cursor()
    print 'False ==', isCJK("nga'aiho")
    print 'True ==', isCJK(u'貓')
    print lookup(db, 'pusi', 'testuser')
    print user_input(db, 1, 'testuser')
    print lookup(db, 'posi', 'testuser')
    print user_input(db, 0, 'testuser')
    print lookup(db, 'pusi\'', 'testuser')
    print user_input(db, 2, 'testuser')
    print lookup(db, 'pusi^', 'testuser')
    print user_input(db, 3, 'testuser')
    print lookup(db, u'貓', 'testuser')
    print user_input(db, 2, 'testuser')
    print user_input(db, 0, 'testuser')
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
