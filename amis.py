# -*- coding: utf8 -*-
# 產生 Fuzzy 查詢的字根等等

import sys
import sqlite3
import re
import logging

SQLDB_NAME = 'dict-amis.sq3'
USER_LASTWORD = {}

def loaddb():
    return sqlite3.connect(SQLDB_NAME)


def fuzzme(v):
    return v.replace('v', 'f') \
            .replace('o', 'u') \
            .replace('ng', 'n') \
            .replace('g', 'n') \
            .replace("'", '') \
            .replace('^', '') \
            .replace('e', '')

def isCJK(s):
    return re.match(r'[\u00-\uff]+', s) is None


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
        cur.execute('SELECT title FROM amis WHERE example IS NULL AND cmn LIKE ? ORDER BY LENGTH(cmn)', ('%%' +s+ '%%', ))
        rows = cur.fetchall()
        if len(rows) == 0:
            return u'找不到這個詞。'
        else:
            return u'「' +s+ u'」可能的阿美語詞有:\n' + iterrows(rows, uid) + u'請輸入號碼查詢單字。'
    else:           # 阿美語查字典
        s = s.lower()
        cur.execute('SELECT cmn FROM amis WHERE title=? AND example IS NULL', (s, ))
        rows = cur.fetchall()
        if len(rows) > 0:    # 找到了
            USER_LASTWORD[uid] = [s,]
            return iterrows(rows, None) + u'要看例句請輸入 0'
        cur.execute('SELECT amis FROM fuzzy WHERE fuzz LIKE ?', ('%%' + fuzzme(s) + '%%', ))
        rows = cur.fetchall()
        if len(rows) == 0:
            return u'找不到這個詞。'
        else:
            return u'請問你要找的是哪個詞?\n' + iterrows(rows, uid) + u'請輸入數字選擇。'

def user_input(db, num, uid):
    logging.debug(u'>>> 使用者 [%s] 輸入了 %d' % (uid, num))
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
    for row in rows:
        r += '%d. %s\n' % (i, row[0])
        r += '    %s\n' % (row[1],  )
        i += 1
    return r


def testme():
    db = loaddb()
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


if __name__ == '__main__':
    print 'Generating fuzzy table.'
    conn = sqlite3.connect('dict-amis.sq3')
    cur = conn.cursor()
    cur.execute('DELETE FROM fuzzy')
    conn.commit()

    cur.execute('SELECT DISTINCT title FROM amis')
    for row in cur.fetchall():
        cur.execute('INSERT INTO fuzzy VALUES (?,?)', (fuzzme(row[0]), row[0]))

    conn.commit()
    conn.close()
    print 'Done.'
