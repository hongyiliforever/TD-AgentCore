import json
import requests
from src.utils.encrypt_util import decrypt, encrypt
from src.utils.logger import agent_logger as logger


def get_access_token():
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'client_credentials',
        'client_id': 'app_17357877855858299446',
        'client_secret': '091f457d59fb4fb901bac903d4728ceb'
    }
    response = requests.post('http://132.225.2.246:9001/oauth2/oauth/token', headers=headers, data=data)
    response.raise_for_status()
    token_response = response.json()
    return token_response['access_token']


def gen_advice_api(kf_sn, advice_info):
    """
    移网投诉_智能回单_预回单信息入库
    """
    try:
        logger.info("gen_advice_api  kf_sn : %r , advice_info: %r", kf_sn, advice_info)
        access_token = get_access_token()
        json_data = {"kfSn": kf_sn, "huiAdvice": advice_info}
        data = json.dumps(json_data)
        encrypt_data = encrypt(data)
        app_url = 'http://132.225.2.246:21100/http'
        headers = {
            'appCode': 'app_17357877855858299446',
            'apiCode': 'API_CODE_17434098057531497174',
            'format': 'json',
            'accessToken': access_token,
            'apiVersion': '2.0.0',
            'Content-Type': 'application/json'
        }
        response = requests.post(app_url, data=encrypt_data, headers=headers)
        if response.status_code == 200:
            decrypt_res = decrypt(response.text)
            logger.info("gen_advice_api kf_sn : %r,  response: %r", kf_sn, decrypt_res)
            result = json.loads(decrypt_res)['result']
        else:
            logger.info(f"gen_advice_api failed with status code {response.status_code}: {response.text}")
            result = []
    except Exception as e:
        logger.info("gen_advice_api res: %r", e)
        result = []
    return result
