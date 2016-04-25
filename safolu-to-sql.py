# -*- coding: utf8 -*-

import sys
import json
import sqlite3
from amis import fuzzme

conn = sqlite3.connect('dict-safolu.sq3')

def load_amis():
    cur = conn.cursor()
    cur.execute('DELETE FROM amis')
    conn.commit()
    dictionary = json.load(open("dict-safolu.json"))
    for word in dictionary:
        title = word['title']
        content = json.dumps(word, ensure_ascii=False) \
                .replace(u'\ufff9\ufffa\ufffb', '') \
                .replace('"heteronyms"', '"h"') \
                .replace('"definitions":', '"d":') \
                .replace('"title":', '"t":') \
                .replace('"example":', '"e":') \
                .replace('"synonyms":', '"s":') \
                .replace('"def":', '"f":')
        cur.execute('INSERT INTO amis VALUES (?,?)', (title, content))
    conn.commit()


def fuzzy_amis():
    cur = conn.cursor()
    cur.execute('DELETE FROM fuzzy')
    conn.commit()
    cur.execute('SELECT DISTINCT title FROM amis')
    for row in cur.fetchall():
        print row[0]
        cur.execute('INSERT INTO fuzzy VALUES (?,?)', (fuzzme(row[0]), row[0]))
    conn.commit()


if __name__ == '__main__':
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS amis (title text, json text)')
    cur.execute('CREATE INDEX IF NOT EXISTS amis_title ON amis (title)')
    cur.execute('CREATE TABLE IF NOT EXISTS fuzzy (fuzz text, amis text)')
    cur.execute('CREATE INDEX IF NOT EXISTS fuzzy_fuzz ON fuzzy (fuzz)')
    conn.commit()
    load_amis()
    fuzzy_amis()
