# -*- coding: utf8 -*-
# 產生 Fuzzy 查詢的字根等等

import sys
import sqlite3
import re
import logging
import json

SUPPORTED_DICT = {
        'fey': 'dict-fey.sq3',
        'safolu': 'dict-safolu.sq3',
        }
USER_LASTWORD = {}
RE_NUM = re.compile(r'^[0-9]+$')

def loaddb(dic):
    if dic in SUPPORTED_DICT:
        return sqlite3.connect(SUPPORTED_DICT[dic])
    else:
        return None


def fuzzme(v):
    return v.replace('v', 'f') \
            .replace('o', 'u') \
            .replace('ng', 'n') \
            .replace('g', 'n') \
            .replace('d', 'l') \
            .replace("'", '') \
            .replace('^', '') \
            .replace('e', '')

def isCJK(s):
    try:
        s = s.strip()
    except:
        pass
    # return re.match(r'^[a-zA-Z\'"^:]+$', s) is None
    return re.match(ur'^[\u0000-\u00ff]+$', s) is None


def fey(uid, txt):
    db = loaddb('fey')
    if db is None:
        return u'系統錯誤，找不到資料庫'
    if RE_NUM.match(txt):               # 輸入數字鍵查詢候選詞
        choice = int(txt)
        r = numpadInput(db, choice, uid)
    else:
        r = lookup(db, txt, uid)
    return r

def safolu(uid, txt):
    if RE_NUM.match(txt):               # 輸入數字鍵查詢候選詞
        num = int(txt)
        print u'>>> 使用者 [%s] 輸入了 %d' % (uid, num)
        if uid not in USER_LASTWORD:
            return u'請重新查詢單字。'
        choices = USER_LASTWORD[uid]
        if num + 1 > len(choices):
            return u'請重新選擇。'
        word = choices[num]
        return safolu(uid, word)
    db = loaddb('safolu')
    cur = db.cursor()
    print u'UID %s 查蔡中涵辭典: %s' % (uid, txt)
    if isCJK(txt):    # 漢語查阿美語
        cur.execute('SELECT title FROM amis WHERE cmn LIKE ? ORDER BY LENGTH(cmn) LIMIT 10', ('%%' +txt+ '%%', ))
        rows = cur.fetchall()
        answer = [r[0] for r in rows]
        cur.execute('SELECT title FROM amis WHERE json LIKE ? LIMIT 10', ('%%' +txt+ '%%', ))
        rows = cur.fetchall()
        answer = answer + [r[0] for r in rows if r[0] not in answer]
        if len(answer) == 0:
            return u'找不到這個詞。'
        else:
            return {'type': 'options',
                    'text': u'有「%s」的阿美語詞' % txt, 
                    'words': answer[:10]}
    cur.execute('SELECT json FROM amis WHERE title=?', (txt,))
    row = cur.fetchone()
    if row:
        j = json.loads(row[0])
        r = ''
        for h in j['h']:
            i = 1
            r = r + j['t']
            if 'stem' in j:
                r = r + ' (%s)' % j['stem']
            r = r + ':\n'
            for d in h['d']:
                r = r + '%d. %s\n' % (i, d['f'])
                if 'e' in d:
                    for ex in d['e']:
                        r = r + u'%s\n' % renderSafoluExample(ex)
                if 's' in d:
                    r = r + u'⟹ ' + ', '.join(d['s']) + '\n'
                i = i + 1
            if 's' in h:
                r = r + u'相似詞: %s' % (h['s'],)
        return r
    else:
        cur.execute('SELECT amis FROM fuzzy WHERE fuzz LIKE ? ORDER BY LENGTH(amis) LIMIT 10', ('%%' + fuzzme(txt) + '%%', ))
        rows = cur.fetchall()
        if len(rows) == 0:
            return u'找不到這個詞。'
        else:
            return {'type': 'options', 
                    'text': u'請問你要查哪個詞?',
                    'words': [r[0] for r in rows]}

def renderSafoluExample(s):
    r = s.replace(u'\ufff9', u'　') \
         .replace(u'\ufffa', u'') \
         .replace(u'\ufffb', u'\n　')
    return r


def iterrows(cur, uid = None):
    global USER_LASTWORD
    i = 1
    r = ''
    if uid:
        USER_LASTWORD[uid] = [None,]
    for row in cur:
        if uid:
            USER_LASTWORD[uid].append(row[0])
        r += '%d. %s\n' % (i, row[0])
        i += 1
    return r


def lookup(db, s, uid):
    global USER_LASTWORD
    cur = db.cursor()
    if isCJK(s):    # 漢語查阿美語
        cur.execute('SELECT title FROM amis WHERE example IS NULL AND cmn LIKE ? ORDER BY LENGTH(cmn) LIMIT 10', ('%%' +s+ '%%', ))
        rows = cur.fetchall()
        if len(rows) == 0:
            return u'找不到這個詞。'
        else:
            return {'type': 'options',
                    'text': u'有「%s」的阿美語詞' % s, 
                    'words': [r[0] for r in rows]}
    else:           # 阿美語查字典
        s = s.lower()
        cur.execute('SELECT cmn FROM amis WHERE title=? AND example IS NULL LIMIT 10', (s, ))
        rows = cur.fetchall()
        if len(rows) > 0:    # 找到了
            if uid in USER_LASTWORD and type(USER_LASTWORD[uid]) == type([]):
                USER_LASTWORD[uid][0] = s
            else:
                USER_LASTWORD[uid] = [s,]
            r = '%s: %s' % (s, rows[0][0])
            e = getExample(db, s)
            if len(e) > 0: r = r + '\n' + e
            return r
        cur.execute('SELECT amis FROM fuzzy WHERE fuzz LIKE ? ORDER BY LENGTH(amis) LIMIT 10', ('%%' + fuzzme(s) + '%%', ))
        rows = cur.fetchall()
        if len(rows) == 0:
            return u'找不到這個詞。'
        else:
            return {'type': 'options', 
                    'text': u'請問你要查哪個詞?',
                    'words': [r[0] for r in rows]}


def getExample(db, s):
    cur = db.cursor()
    cur.execute('SELECT example, cmn FROM amis WHERE title=? AND example IS NOT NULL', (s,))
    rows = cur.fetchall()
    r = ''
    if len(rows) == 0:
        return r
    i = 1
    for row in rows:
        r += '%d. %s\n' % (i, row[0])
        r += u'　%s\n' % (row[1],  )
        i += 1
    return r


def numpadInput(db, num, uid):
    print u'>>> 使用者 [%s] 輸入了 %d' % (uid, num)
    if uid not in USER_LASTWORD:
        return u'請重新查詢單字。'
    choices = USER_LASTWORD[uid]
    if num + 1 > len(choices):
        return u'請重新選擇。'
    word = choices[num]
    return lookup(db, word, uid)


def testme():
    db = loaddb('fey')
    cur = db.cursor()
    print 'False ==', isCJK("nga'aiho")
    print 'True ==', isCJK(u'貓')
    print lookup(db, 'pusi', 'testuser')
    print numpadInput(db, 1, 'testuser')
    print lookup(db, 'posi', 'testuser')
    print numpadInput(db, 0, 'testuser')
    print lookup(db, 'pusi\'', 'testuser')
    print numpadInput(db, 2, 'testuser')
    print lookup(db, 'pusi^', 'testuser')
    print numpadInput(db, 3, 'testuser')
    print lookup(db, u'貓', 'testuser')
    print numpadInput(db, 2, 'testuser')
    print numpadInput(db, 0, 'testuser')
    sys.exit(10)


def fuzzy_fey():
    print 'Generating fuzzy table.'
    conn = sqlite3.connect(SUPPORTED_DICT['fey'])
    cur = conn.cursor()
    cur.execute('DELETE FROM fuzzy')
    conn.commit()

    cur.execute('SELECT DISTINCT title FROM amis')
    for row in cur.fetchall():
        cur.execute('INSERT INTO fuzzy VALUES (?,?)', (fuzzme(row[0]), row[0]))

    conn.commit()
    conn.close()
    print 'Done.'


if __name__ == '__main__':
    pass
