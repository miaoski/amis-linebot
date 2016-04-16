# -*- coding: utf8 -*-
# 產生 Fuzzy 查詢的字根

import sys
import sqlite3

def fuzzme(v):
    return v.replace('v', 'f') \
            .replace('o', 'u') \
            .replace('ng', 'n') \
            .replace('g', 'n') \
            .replace("'", '') \
            .replace('^', '') \
            .replace('e', '')

if __name__ == '__main__':
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
