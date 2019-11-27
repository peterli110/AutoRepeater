# -*- coding:utf-8 -*-

from gensim.models import Word2Vec
from flask import Flask, abort, jsonify, request
import numpy as np
import jieba
import linecache
import json
import re
import os
import random
import logging
import time
import math
from util import porn_pic_index


Debug = False
Anti25 = True
Ban_Time = 20 if Debug == True else 60 * 30 # 30min

# logger
logger = logging.getLogger('autoReply')
logger.setLevel(logging.INFO)
log_fh = open("error.log", "a", encoding="utf-8")
ch = logging.StreamHandler(log_fh)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

# path
dirname = os.path.dirname(__file__)
raw_data = os.path.join(dirname, '/dataset/target.txt')
model = os.path.join(dirname, '/model/w2v.mod')

# init model and parameters
model_w2v = Word2Vec.load(model)
sample_size = 2000


# count line of raw data
raw_file = open(raw_data, "r", encoding='utf-8')
count_line = len(raw_file.readlines())
raw_file.close()

# 防止恶意刷屏
last_words = []
last_words_fromGroup = {}

banned_QQ = {}
setu_Group = {}

# filter non chinese char
chinese_pattern = re.compile("["
                u"\U0001F600-\U0001F64F"  # emoticons
                u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                u"\U0001F680-\U0001F6FF"  # transport & map symbols
                u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                u"\u0000-\u002f"
                u"\u003a-\u0040"
                u"\u005b-\u0060"
                u"\u007b-\u4dff"
                u"\u9FA6-\uffff"
                u"\u0669"
                u"\u06f6"
                u"\u0e51"
                u"\u0f40"
                u"\u0f0b"
                u"\u141b"
                u"\u200d"
                u"\u2640-\u2642"
                u"\u2600-\u2B55"
                u"\u2200"
                u"\u23cf"
                u"\u23e9"
                u"\u231a"
                u"\u3030"
                u"\u30fb"
                u"\ufe0f"
                u"\uff65"
                u"\uff89"
                u"\uff9f"
                u"\xa0"
                u"\xb4"
                u"\xbf"
    "]+", flags=re.UNICODE)

# result object init
class ResultInfo(object):
    def __init__(self, index, score, text):
        self.id = index
        self.score = score
        self.text = text

class BanQQ(object):
    def __init__(self):
        self.count = 0
        self.ts = int(time.time())

# return parameters of /message
class RepeaterResult(object):
    def __init__(self, code = 2, msg = "", score = "0"):
        self.code = code
        self.msg = msg
        self.score = score
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
            sort_keys=True, indent=4)

# return parameters of /setu
class SetuResult(object):
    def __init__(self, code = 2, msg = "", score = 0, shouldBan = False):
        self.code = code
        self.msg = msg
        self.score = score
        self.shouldBan = shouldBan
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
            sort_keys=True, indent=4)

app = Flask(__name__)


@app.route('/message', methods=['POST'])
def reply():
    #time.sleep(2)
    global last_words
    global last_words_fromGroup
    req_msg = request.form.get('msg', None)
    fromGroup = request.form.get('group', None)
    fromQQ = request.form.get('qq', None)
    isRepeat = False

    if fromQQ:
        if fromQQ in banned_QQ:
            # expired, delete qq from ban list
            if int(time.time()) - banned_QQ[fromQQ].ts > Ban_Time:
                del banned_QQ[fromQQ]
            # just ignore
            else:
                return RepeaterResult(2).toJSON()

    if not req_msg:
        return RepeaterResult(-1).toJSON()

    #if req_msg == "safe word":
        #return jsonify({ 'code': 2 })

    if req_msg.startswith('对话 '):
        req_msg = req_msg[3:]

    if "[CQ:image,file=" in req_msg:
        return RepeaterResult(2).toJSON()

    req_msg = chinese_pattern.sub(r'', req_msg)

    if Debug:
        print("input: ", req_msg)

    logger.debug("received input from group " + (fromGroup if fromGroup else "None") + " : " + req_msg)

    words = list(jieba.cut(req_msg.strip(), cut_all=False))
    words_to_process = words.copy()

    # check if word is match the vocabulary
    for w in words:
        if Debug:
            print("words to process: ", w)
        if w not in model_w2v.wv.vocab:
            # remove not matched words
            if Debug:
                print("words not in voc: ", w)
            words_to_process.remove(w)
        if fromGroup and fromGroup in last_words_fromGroup and isinstance(last_words_fromGroup[fromGroup], list):
            if w in last_words_fromGroup[fromGroup]:
                if Debug:
                    print("words to remove: ", w)
                isRepeat = True
                words_to_process.remove(w)
        elif w in last_words:
            if Debug:
                print("words to remove: ", w)
            isRepeat = True
            words_to_process.remove(w)

    # none of words matched
    words_length = len(words_to_process)
    if Debug:
        print("remaining words length: ", words_length)
    if words_length == 0 and isRepeat:
        # whole sentence is identical to last_words
        logger.info("反25已检测到可能的恶意刷屏:\n[%s]\nQQ: %s 群号:%s" % (req_msg, fromQQ if fromQQ else "None", fromGroup if fromGroup else "None"))
        if fromQQ:
            if fromQQ not in banned_QQ:
                banned_QQ[fromQQ] = BanQQ()
            else:
                banned_QQ[fromQQ].count += 1
                banned_QQ[fromQQ].ts = int(time.time())
        return RepeaterResult(0, '再刷屏就不理你们了哼QAQ' + ("\n[Debug] bot将在%s秒内不回答QQ: %s" % (Ban_Time, fromQQ if fromQQ else "None")) if Debug == True else "").toJSON()
    elif words_length == 0:
        # unknown words
        return RepeaterResult(1).toJSON()

    if Anti25 == True:
        if fromGroup:
            last_words_fromGroup[fromGroup] = words.copy()
        else:
            last_words = words.copy()
    # choose random ${sample_size} lines as samples
    rand_line = np.random.choice(range(count_line),size=sample_size,replace=False)

    res = []
    index = 0
    for line in rand_line:
        sample_text = linecache.getline(raw_data, line).strip().split()
        try:
            score = model_w2v.n_similarity(words_to_process, sample_text)
        except Exception as e:
            logger.error('Input: ' + req_msg + '\nError: ' + str(e))
            return RepeaterResult(2).toJSON()

        # just return a likely-related msg
        if score > 0.7:
            return RepeaterResult(0, "".join(sample_text), str(score)).toJSON()

        res.append(ResultInfo(index, score, "".join(sample_text)))
        index += 1

    res.sort(key=lambda x:x.score, reverse=True)

    if Debug:
        k = 0
        for i in res:
            k += 1
            print ("text %s: %s, score : %s" % (i.id, i.text, i.score))
            if k > 3:
                print ("\n")
                break

    return RepeaterResult(0, res[4].text, str(score)).toJSON()


@app.route('/setu', methods=['POST'])
def reply_setu():
    req_msg = request.form.get('msg', None)
    fromGroup = request.form.get('group', None)
    fromQQ = request.form.get('qq', None)

    if Debug:
        print("input: ", req_msg)

    if "[CQ:image,file=" not in req_msg:
        return SetuResult(2).toJSON()

    if fromGroup and fromQQ:
        if fromGroup in setu_Group and setu_Group[fromGroup] == fromQQ:
            if Debug:
                print("Duplicated msg from QQ: ", fromQQ)
            else:
                return SetuResult(2).toJSON() # 防刷屏
        else:
            setu_Group[fromGroup] = fromQQ

    result = porn_pic_index(req_msg)
    if result['code'] == 0:
        #return jsonify({ 'code': 0, 'msg': "色图指数：" + str(porn_index) + "%" })
        if Debug:
            print("Original porn value: ", result['value'])
        temp_value = result['value'];
        logger.info("色图识别成功: QQ: %s, Group: %s, Raw: %s, Out: %s" % (fromQQ if fromQQ else "None", fromGroup if fromGroup else "None", result['value'], temp_value))
        if (temp_value > 10):
            temp_value = int(temp_value * math.log10(result['value']))
            if (temp_value > 100):
                temp_value = 100
        if Debug:
            print("Return porn value: ", temp_value)
        result_msg = "色图指数：" + str(temp_value) + "%"
        if temp_value < 5:
            return SetuResult(0, "", 0, False).toJSON()
        elif temp_value > 50 and temp_value <= 90:
            result_msg += "\n警察叔叔就是这个人o(╥﹏╥)o"
            return SetuResult(0, result_msg, temp_value, False).toJSON()
        elif temp_value > 90:
            result_msg += "\n群要没了o(╥﹏╥)o"
            return SetuResult(0, result_msg, temp_value, True).toJSON()
        else:
            return SetuResult(0, result_msg, temp_value, False).toJSON()
    elif Debug == True:
        return SetuResult(0, result['msg']).toJSON()
    elif result['code'] == 1:
        return SetuResult(2).toJSON()
    else:
        logger.error('读取图片失败: ' + result['msg'])
        return SetuResult(2).toJSON()

if __name__ == '__main__':
    app.run(port=7777, debug=Debug)
