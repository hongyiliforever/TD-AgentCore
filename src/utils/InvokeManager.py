import base64
import requests
import urllib3
from src.utils import TokenUtil as TU
from src.utils.logger import agent_logger as logger


class InvokeManager:
    appId = ''
    secret = ''

    AUTH_HEADER = "Authentication"
    CONTENT_TYPE_JSON_UTF8 = "application/json; charset=utf-8"
    """
       :param appid
       :param secret
    """
    def __init__(self, appid, secret):
        if appid == None or appid == '' or secret == None or secret == '':
            raise RuntimeError("appid or secret is None")
        self.appId = appid
        self.secret = secret

    # Get方式请求
    def getModeRequest(self, url, headers=None):
        if headers is None:
            headers = {}
        # 设置认证请求头
        self.addHeaders(headers, self.appId, self.secret)
        # print(headers)
        respones = requests.get(url, json=dict(), headers=headers, verify=False)
        return respones

    # Post方式请求
    def postModeRequest(self, url, body, headers=None):
        if headers is None:
            headers = {"Content-Type": self.CONTENT_TYPE_JSON_UTF8}
        else:
            headers.update({"Content-Type": self.CONTENT_TYPE_JSON_UTF8})
        # 设置认证请求头
        self.addHeaders(headers, self.appId, self.secret, body=body)
        logger.info("asr_api Authentication: %r ", headers)
        urllib3.disable_warnings()
        respones = requests.post(url, data=body, headers=headers, verify=False)
        return respones

    def addHeaders(self, headers, appId, secret, body=None):
        token = TU.generateAuth(appId, secret, body)
        logger.info("asr_api token: %r ", token)
        # 切片去除前两位和最后一位 因为base加密后是 b'kgahjshjohjdksag' 我们只要引号里面的内容
        tokenResult = str(base64.b64encode(token.encode("utf-8")))[2:][:-1]
        headers.update({self.AUTH_HEADER: tokenResult})

#
# if __name__ == '__main__':
#     ass = InvokeManager(get_config_value('appCode_id'), get_config_value('appCode_secret'))
#     # respones = ass.getModeRequest('http://172.24.131.188:38001/api/middlleplatform/UoySu8/nujYhZ/v1.0')
#     dic = {}
#     json = json.dumps(dic)
#     print(json)
#     respones = ass.postModeRequest('https://172.24.131.188:38001/api/middlleplatform/qIaDXL/i9xFbP/v1.0', json)
#     print(respones.json())
