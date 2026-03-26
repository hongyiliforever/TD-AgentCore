import datetime
import hashlib
import json
import random

APP_ID = "APP_ID";
TIMESTAMP = "TIMESTAMP";
TRANS_ID = "TRANS_ID";
TOKEN = "TOKEN"

'''
    生成认证信息
    无body时传入None
'''


def generateAuth(appid, secret, body=None):
    # TIMESTAMP
    time_stamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S %f')
    time_stamp = str(time_stamp)[:-3]
    # TRANS_ID
    trans_id = get_random()
    # TOKEN
    token = generateToken(appid, secret, time_stamp, trans_id, body)
    dict = {}
    dict.update({APP_ID: appid, TIMESTAMP: time_stamp, TRANS_ID: trans_id, TOKEN: token})
    auth = json.dumps(dict)
    return auth


'''
根据传入的信息生成token
'''


def generateToken(appId, secret, timestamp, transId, body):
    if (body != None):
        str = APP_ID + appId + TIMESTAMP + timestamp + TRANS_ID + transId + body + secret
        token = hashlib.md5(str.encode("utf-8")).hexdigest()
        # print(str + "=======" + token)
        return token
    else:
        str = APP_ID + appId + TIMESTAMP + timestamp + TRANS_ID + transId + "{}" + secret
        token = hashlib.md5(str.encode("utf-8")).hexdigest()
        # print(str + "=======" + token)
        return token


def get_random():
    rand = random.randint(9000, 9999)
    nowTime = datetime.datetime.now().strftime('%y%m%d%H%M%S%f')
    # 对字符串进行切片 丢掉后三位数字
    nowTime = str(nowTime)[:-3]
    return nowTime + str(rand)
