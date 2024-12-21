# -*- coding:utf-8 -*-
 
import websocket
import datetime
import hashlib
import base64
import hmac
import json
from urllib.parse import urlencode
import time
import ssl
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import _thread as thread
import os
from util import load_config
import threading
import asyncio
from pathlib import Path
 
STATUS_FIRST_FRAME = 0  # 第一帧的标识
STATUS_CONTINUE_FRAME = 1  # 中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识
 
# 获取数据库配置
config = load_config('xfyun')

class Ws_Param(object):
    # 初始化
    def __init__(self, APPID, APIKey, APISecret, Text):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.Text = Text
 
        # 公共参数(common)
        self.CommonArgs = {"app_id": self.APPID}
        # 业务参数(business)，更多个性化参数可在官网查看
        self.BusinessArgs = {"aue": "lame", "auf": "audio/L16;rate=16000", "vcn": "xiaoyan", "tte": "utf8","ent":"aisound"}
        self.Data = {"status": 2, "text": str(base64.b64encode(self.Text.encode('utf-8')), "UTF8")}
        #使用小语种须使用以下方式，此处的unicode指的是 utf16小端的编码方式，即"UTF-16LE"”
        #self.Data = {"status": 2, "text": str(base64.b64encode(self.Text.encode('utf-16')), "UTF8")}
 
    # 生成url
    def create_url(self):
        url = 'wss://tts-api.xfyun.cn/v2/tts'
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
 
        # 拼接字符串
        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/tts " + "HTTP/1.1"
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
 
class SpeechGenerator:
    def __init__(self):
        self.completion_event = threading.Event()
        self.error = None
        self.output_path = None

def on_message(ws, message):
    try:
        message = json.loads(message)
        code = message["code"]
        audio = message["data"]["audio"]
        audio = base64.b64decode(audio)
        status = message["data"]["status"]
        
        # 确保speech目录存在
        Path("./speech").mkdir(exist_ok=True)
        output_path = f"./speech/{ws.text}.mp3"
        
        if code != 0:
            ws.speech_generator.error = f"错误码：{code}, 错误信息：{message['message']}"
            ws.speech_generator.completion_event.set()
            ws.close()
            return
            
        with open(output_path, 'ab') as f:
            f.write(audio)
        
        if status == 2:
            print("------>文本合成结束")
            ws.speech_generator.output_path = output_path
            ws.speech_generator.completion_event.set()
            ws.close()

    except Exception as e:
        ws.speech_generator.error = f"接收消息异常: {str(e)}"
        ws.speech_generator.completion_event.set()
        ws.close()
 
 
 
# 收到websocket错误的处理
def on_error(ws, error):
    print("### error:", error)
 
 
# 收到websocket关闭的处理
def on_close(ws):
    print("### closed ###")
 
 
# 收到websocket连接建立的处理
def on_open(ws):
    def run(*args):
        d = {"common": ws.wsParam.CommonArgs,
             "business": ws.wsParam.BusinessArgs,
             "data": ws.wsParam.Data,
             }
        d = json.dumps(d)
        print("------>开始发送文本数据")
        ws.send(d)
        if os.path.exists(f"./speech/{ws.text}.mp3"):
            os.remove(f"./speech/{ws.text}.mp3")
 
    thread.start_new_thread(run, ())
 
def generate_speech_sync(text):
    """
    同步生成语音文件
    :param text: 要转换的文本
    :return: 生成的音频文件路径
    :raises: Exception 如果生成过程中发生错误
    """
    config = load_config('xfyun')
    wsParam = Ws_Param(APPID=config['appid'],
                      APIKey=config['apikey'],
                      APISecret=config['apisecret'],
                      Text=text)
    
    speech_generator = SpeechGenerator()
    
    websocket.enableTrace(False)
    wsUrl = wsParam.create_url()
    ws = websocket.WebSocketApp(wsUrl, 
                              on_message=on_message, 
                              on_error=on_error, 
                              on_close=on_close)
    ws.wsParam = wsParam
    ws.text = text
    ws.speech_generator = speech_generator
    ws.on_open = on_open
    
    # 在新线程中运行WebSocket
    ws_thread = threading.Thread(target=lambda: ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}))
    ws_thread.daemon = True
    ws_thread.start()
    
    # 等待完成或超时
    timeout = int(config.get('timeout', 50))
    if not speech_generator.completion_event.wait(timeout=timeout):  # 50秒超时
        raise Exception("语音生成超时")
    
    # 检查是否有错误
    if speech_generator.error:
        raise Exception(speech_generator.error)
    
    return speech_generator.output_path

# 如果./speech/text.mp3存在，则返回文件路径，否则生成语音文件
def text_to_speech(text):
    if os.path.exists(f"./speech/{text}.mp3"):
        return f"./speech/{text}.mp3"
    else:
        return generate_speech_sync(text)