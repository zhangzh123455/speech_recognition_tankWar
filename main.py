# -*- coding:utf-8 -*-

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
import websocket
import hashlib
import base64
import hmac
import json
from urllib.parse import urlencode
from settings import Settings
import ssl
from wsgiref.handlers import format_date_time
from datetime import datetime
import time
from time import mktime, sleep
import _thread as thread
import pyaudio
from tank_war import TankWar
import socket
import re
tankWar = TankWar()
HOST = '127.0.0.1'
PROT = 50007
STATUS_FIRST_FRAME = 0  # 第一帧的标识
STATUS_CONTINUE_FRAME = 1  # 中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识


class Ws_Param(object):
    # 初始化
    def __init__(self, APPID, APIKey, APISecret):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret


        # 公共参数(common)
        self.CommonArgs = {"app_id": self.APPID}
        # 业务参数(business)
        self.BusinessArgs = {"domain": "iat", "language": "zh_cn", "accent": "mandarin", "vinfo":1,"vad_eos":10000}

    # 生成url
    def create_url(self):
        url = 'wss://ws-api.xfyun.cn/v2/iat'
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接字符串
        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/iat " + "HTTP/1.1"
        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }
        # 拼接鉴权参数，生成url
        url = url + '?' + urlencode(v)
        # print("date: ",date)
        # print("v: ",v)
        # 此处打印出建立连接时候的url,参考本demo的时候可取消上方打印的注释，比对相同参数时生成的url与自己代码生成的url是否一致
        # print('websocket url :', url)
        return url


# 收到websocket消息的处理

def on_message(ws, message):
    global s
    try:
        code = json.loads(message)["code"]
        sid = json.loads(message)["sid"]
        if code != 0:
            errMsg = json.loads(message)["message"]
            print("sid:%s call error:%s code is:%s" % (sid, errMsg, code))

        else:
            data = json.loads(message)["data"]["result"]["ws"]
            result = ""
            for i in data:
                for w in i["cw"]:
                    result += w["w"]

            if result == '。' or result=='.。' or result==' .。' or result==' 。':
                pass
            else:
                if re.search(".*\u5de6.*", result):
                    # 说“左”
                    tankWar.hero.direction = Settings.LEFT
                    tankWar.hero.is_moving = True
                    tankWar.hero.is_hit_wall = False
                    print("left")
                elif re.search(".*\u53f3.*", result):
                    # 说“右”
                    tankWar.hero.direction = Settings.RIGHT
                    tankWar.hero.is_moving = True
                    tankWar.hero.is_hit_wall = False
                    print("right")
                elif re.search(".*\u4e0a.*", result):
                    # 说“上”
                    tankWar.hero.direction = Settings.UP
                    tankWar.hero.is_moving = True
                    tankWar.hero.is_hit_wall = False
                    print("up")
                elif re.search(".*\u4e0b.*", result):
                    # 说“下”
                    tankWar.hero.direction = Settings.DOWN
                    tankWar.hero.is_moving = True
                    tankWar.hero.is_hit_wall = False
                    print("down")
                elif re.search(".*\u53d1\u5c04.*", result):
                    # 说“发射”，坦克发射三发子弹
                    tankWar.hero.shot()
                    sleep(0.5)
                    tankWar.hero.shot()
                    sleep(0.5)
                    tankWar.hero.shot()
                    print("shot")
                elif re.search(".*\u505c.*", result):
                    # 说“停”，坦克停止移动
                    tankWar.hero.is_moving = False
                print("翻译结果: %s。" % (result))

    except Exception as e:
        print("receive msg,but parse exception:", e)


# 收到websocket错误的处理
def on_error(ws, error):
    print("### error:", error)


# 收到websocket关闭的处理
def on_close(ws):
    # pass
    print("### closed ###")


# 收到websocket连接建立的处理
def on_open(ws):
    def run(*args):
        status = STATUS_FIRST_FRAME  # 音频的状态信息，标识音频是第一帧，还是中间帧、最后一帧
        CHUNK = 520                 # 定义数据流块
        FORMAT = pyaudio.paInt16  # 16bit编码格式
        CHANNELS = 1  # 单声道
        RATE = 16000  # 16000采样频率
        p = pyaudio.PyAudio()
        # 创建音频流
        stream = p.open(format=FORMAT,  # 音频流wav格式
                        channels=CHANNELS,  # 单声道
                        rate=RATE,  # 采样率16000
                        input=True,
                        frames_per_buffer=CHUNK)

        print("- - - - - - - - - 开始录音 ...- - - - - - - - - ")
        print("请对麦克风说“上” “下” “左” “右” “停”和”发射“来控制坦克")
        # for i in range(0,int(RATE/CHUNK*60)):
        for i in range(0, int(RATE / CHUNK * 60)):
            buf = stream.read(CHUNK)
            if not buf:
                status = STATUS_LAST_FRAME
            if status == STATUS_FIRST_FRAME:

                d = {"common": wsParam.CommonArgs,
                     "business": wsParam.BusinessArgs,
                     "data": {"status": 0, "format": "audio/L16;rate=16000",
                              "audio": str(base64.b64encode(buf), 'utf-8'),
                              "encoding": "raw"}}
                d = json.dumps(d)
                ws.send(d)
                status = STATUS_CONTINUE_FRAME
                # 中间帧处理
            elif status == STATUS_CONTINUE_FRAME:
                d = {"data": {"status": 1, "format": "audio/L16;rate=16000",
                              "audio": str(base64.b64encode(buf), 'utf-8'),
                              "encoding": "raw"}}
                ws.send(json.dumps(d))

            # 最后一帧处理
            elif status == STATUS_LAST_FRAME:
                d = {"data": {"status": 2, "format": "audio/L16;rate=16000",
                              "audio": str(base64.b64encode(buf), 'utf-8'),
                              "encoding": "raw"}}
                ws.send(json.dumps(d))
                time.sleep(1)
                break

        stream.stop_stream()
        stream.close()
        p.terminate()
        ws.close()
    thread.start_new_thread(run, ())


def run():
    global wsParam
    wsParam = Ws_Param(APPID=ID, APIKey= KEY,
                       APISecret=SECRET)
    websocket.enableTrace(False)
    wsUrl = wsParam.create_url()
    ws = websocket.WebSocketApp(wsUrl, on_message=on_message, on_error=on_error)
    ws.on_open = on_open
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}, ping_interval=60, ping_timeout=5)
    end = time.time()
    print('Running time: %s Seconds' % (end - start))
    return 1

# !!APPID,APIKey,APISecret要改成自己申请的API

import threading
from threading import Thread


def run_it():
    while True:
        """
        当进程小于等于2（本进程加上坦克大战进程）
        即调用接口的进程因为一分钟到了或者其他原因断开时
        重新调用它
        """
        if threading.activeCount() <= 2:
            Thread(target=run).start()


if __name__ == '__main__':
    start=time.time()
    # print(threading.activeCount())
    Thread(target=run_it).start()
    sleep(2)
    # print(threading.activeCount())
    Thread(target=tankWar.run_game()).start()



