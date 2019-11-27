import requests
import os
import hashlib
import requests
import string
import random
import time
import sys
from urllib.parse import urlencode
import json
import urllib.request as urllib2

Debug = False
API_ENDPOINT = "https://aip.baidubce.com/api/v1/solution/direct/img_censor"


def get_token():
    host = os.getenv('BAIDU_OPENPLATFORM')
    request = urllib2.Request(host)
    request.add_header('Content-Type', 'application/json; charset=UTF-8')
    response = urllib2.urlopen(request)
    content = response.read()
    if (content):
        r = json.loads(content.decode('utf-8'))
        #print(json.dumps(r, indent=4, sort_keys=True))
        return r['access_token']
    else:
        return ''


BAIDU_ACCESS_TOKEN = get_token()
TOKEN_GENERATED = int(time.time())


def porn_pic_index(msg):
    global BAIDU_ACCESS_TOKEN
    global TOKEN_GENERATED
    if int(time.time()) - TOKEN_GENERATED > 20 * 60 * 60 * 24: # 20 days
        BAIDU_ACCESS_TOKEN = get_token()
        TOKEN_GENERATED = int(time.time())

    try:
        filename = msg.split('[CQ:image,file=', 1)[1].split(']')[0]
        # TODO: jpg png bmp
        dirname = os.path.dirname(__file__)
        path = os.path.join(dirname, 'data', 'image', filename + '.cqimg')
        if Debug:
            print("image path: ", path)
        with open(path, 'r', encoding="GB2312") as f:
            url = ""
            width = ""
            height = ""
            for line in f:
                if line.startswith('url='):
                    url = line[4:].strip()
                if line.startswith("height="):
                    height = line[7:].strip()
                if line.startswith("width="):
                    width = line[6:].strip()

            try:
                file_height = int(height)
                file_width = int(width)
                if Debug:
                    print("Height and width: ", file_height, file_width)
                if min(file_height, file_width) < 400:
                    return { 'code': 1, 'msg': "height and width too small" }
                if max(file_height, file_width) > 4096:
                    return { 'code': 1, 'msg': "height and width too large" }
            except Exception as e:
                return { 'code': 2, 'msg': str(e) }


            data = dict()
            data['scenes'] = ['antiporn']
            data['imgUrl'] = url
            if Debug:
                print("url: ", data['imgUrl'])

            imgCensorUrl = API_ENDPOINT + "?access_token=" + BAIDU_ACCESS_TOKEN
            request = urllib2.Request(url=imgCensorUrl, data=json.dumps(data).encode('utf8'))
            request.add_header('Content-Type', 'application/json')
            response = urllib2.urlopen(request, timeout=5)
            content = response.read()
            #print(content)
            if (content):
                r = json.loads(content.decode('utf-8'))
                if Debug:
                    print(json.dumps(r, indent=4, sort_keys=True, ensure_ascii=False))
                    #print("test")
                if "error_code" in r:
                    return { 'code': r['error_code'], 'msg': r['error_msg'] }
                else:
                    sexy = 0
                    porn = 0
                    for c in r['result']['antiporn']['result']:
                        if c['class_name'] == "色情":
                            porn = int(c['probability'] * 100)
                        if c['class_name'] == "性感":
                            sexy = int(c['probability'] * 40) #sexy系数调整，最终输出最大值为64
                    return { 'code': 0, 'msg': 'Success', 'value': max(sexy, porn) }

            else:
                return { 'code': -1, 'msg': 'API Error' }


    except FileNotFoundError:
        return { 'code': -1, 'msg': 'File not found' }
