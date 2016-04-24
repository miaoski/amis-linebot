# -*- coding: utf8 -*-

import re

# copied from stackoverflow
HANUNI = re.compile(ur'^[⺀-⺙⺛-⻳⼀-⿕々〇〡-〩〸-〺〻㐀-䶵一-鿃豈-鶴侮-頻並-龎]+$', re.UNICODE)

def guoyu(uid, txt):
    print u'UID %s 查國語萌典: %s' % (uid, txt)
    r = 'undefined'
    if HANUNI.match(txt):
        get = requests.get('https://www.moedict.tw/a/%s.json' % txt)
        if get.status_code == 200:
            j = get.json()
            if 'r' in j and 'n' in j:
                r = u'%s (%s部%d劃)\n' % (stripWordSeg(j['t']), stripWordSeg(j['r']), j['n'])
            else:
                r = stripWordSeg(j['t']) + '\n'
            for h in j['h']:
                i = 1
                if 'b' in h and 'p' in h:
                    r = r + u'%s %s\n' % (h['b'], h['p'])
                for d in h['d']:
                    if 'type' in d:
                        word_class = u'[%s詞]' % stripWordSeg(d['type'])
                    else:
                        word_class = ''
                    r = r + '%d. %s %s\n' % (i, word_class, stripWordSeg(d['f']))
                    if 'e' in d:
                        for ex in d['e']:
                            r = r + u'　%s\n' % stripWordSeg(ex)
                    i = i + 1
                if 's' in h:
                    r = r + u'相似詞: %s' % stripWordSeg(h['s'])
            return r
        elif get.status_code == 404:
            return u'查無此字。'
        else:
            app.logger.warn(str(get.status_code))
            app.logger.warn(str(get.text))
            return u'系統錯誤，請稍候再試。'
    else:
        return u'查詢字串內含非漢字的字元，請重新輸入。'
    return r


def taigi(uid, txt):
    print u'UID %s 查台語萌典: %s' % (uid, txt)
    r = 'undefined'
    if HANUNI.match(txt):
        get = requests.get('https://www.moedict.tw/t/%s.json' % txt)
        if get.status_code == 200:
            j = get.json()
            if 'r' in j and 'n' in j:
                r = u'%s (%s部%d劃)\n' % (stripWordSeg(j['t']), stripWordSeg(j['r']), j['n'])
            else:
                r = stripWordSeg(j['t']) + '\n'
            for h in j['h']:
                i = 1
                reading = stripWordSeg(h.get('reading', u'發'))
                if 'T' in h:
                    r = r + u'%s音: %s\n' % (reading, h['T'])
                for d in h['d']:
                    if 'type' in d:
                        word_class = u'[%s詞] ' % stripWordSeg(d['type'])
                    else:
                        word_class = ''
                    r = r + '%d. %s%s\n' % (i, word_class, stripWordSeg(d['f']))
                    if 'e' in d:
                        for ex in d['e']:
                            r = r + u'%s\n' % renderMoeExample(stripWordSeg(ex))
                    i = i + 1
                if 's' in h:
                    r = r + u'相似詞: %s' % stripWordSeg(h['s'])
            return r
            # MP3 in https://1763c5ee9859e0316ed6-db85b55a6a3fbe33f09b9245992383bd.ssl.cf1.rackcdn.com/04208.mp3
            # j['h'][0]['_'] left pad 0 to 5 digits
        elif get.status_code == 404:
            return u'查無此字。'
        else:
            app.logger.warn(str(get.status_code))
            app.logger.warn(str(get.text))
            return u'系統錯誤，請稍候再試。'
    else:
        return u'查詢字串內含非漢字的字元，請重新輸入。'
    return 


def hakkafa(uid, txt):
    print u'UID %s 查客語萌典: %s' % (uid, txt)
    r = 'undefined'
    if HANUNI.match(txt):
        get = requests.get('https://www.moedict.tw/h/%s.json' % txt)
        if get.status_code == 200:
            j = get.json()
            r = stripWordSeg(j['t']) + '\n'
            for h in j['h']:
                i = 1
                reading = stripWordSeg(h.get('reading', u'發'))
                if 'p' in h:
                    r = r + h['p'].replace(u'\u20de', '') + '\n'    # 不要四方框
                for d in h['d']:
                    if 'type' in d and d['type'] != '':
                        word_class = u'[%s詞] ' % stripWordSeg(d['type'])
                    else:
                        word_class = ''
                    r = r + '%d. %s%s\n' % (i, word_class, stripWordSeg(d['f']))
                    if 'e' in d:
                        for ex in d['e']:
                            r = r + u'%s\n' % renderMoeExample(stripWordSeg(ex))
                    i = i + 1
                if 's' in h:
                    r = r + u'相似詞: %s' % stripWordSeg(h['s'])
            return r
            # MP3 in https://1763c5ee9859e0316ed6-db85b55a6a3fbe33f09b9245992383bd.ssl.cf1.rackcdn.com/04208.mp3
            # j['h'][0]['='] left pad 0 to 5 digits
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
    r = s.replace(u'\ufff9', u'　') \
         .replace(u'\ufffa', u'\n　') \
         .replace(u'\ufffb', u'\n　(') + ')'
    return r.replace(u'\n　()', '')           # XXX: Dirty Hack


def stripWordSeg(s):
    #TAG_RE = re.compile(r'<[^>]+>')
    #return TAG_RE.sub('', s)
    return s.replace('`', '').replace('~', '')
