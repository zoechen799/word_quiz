import requests
from typing import List, Dict, Optional
import json
from util import load_config
import re
class AzureOpenAI:
    def __init__(self):
        # 从配置文件加载设置
        config = load_config("azure_openai")
        self.api_base = config["base_url"]
        self.api_version = config["api_version"]
        self.api_key = config["api_key"]
        self.deployment_name = config["deployment_name"]
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        top_p: float = 0.95,
        frequency_penalty: float = 0,
        presence_penalty: float = 0,
        max_tokens: int = 800,
        stop: Optional[List[str]] = None
    ) -> Dict:
        """
        发送请求到 Azure OpenAI API
        
        Args:
            messages: 消息列表，每个消息包含 role 和 content
            temperature: 温度参数，控制随机性
            top_p: 核采样参数
            frequency_penalty: 频率惩罚参数
            presence_penalty: 存在惩罚参数
            max_tokens: 最大生成令���数
            stop: 停止生成的标记列表
        
        Returns:
            API 响应的 JSON 数据
        """
        url = f"{self.api_base}/openai/deployments/{self.deployment_name}/chat/completions?api-version={self.api_version}"
        
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }
        
        payload = {
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "max_tokens": max_tokens,
            "stop": stop
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()  # 检查响应状态
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API 请求失败: {str(e)}")
            raise

# 创建单例实例
azure_openai = AzureOpenAI()

def get_chat_completion(
    messages: List[Dict[str, str]],
    **kwargs
) -> str:
    """
    获取 AI 聊天回复的便捷函数
    
    Args:
        messages: 消息列表
        **kwargs: 其他可选参数
    
    Returns:
        AI 的回���文本
    """
    try:
        response = azure_openai.chat_completion(messages, **kwargs)
        return response['choices'][0]['message']['content']
    except Exception as e:
        print(f"获取 AI 回复失败: {str(e)}")
        raise

def calculate_similarity_openai(text1, text2):
    messages = [
        {
            "role": "system",
            "content": "请比较一下如下中文回答和答案的意思,回答以 '回答:'开始，以'.'结束， 答案以'答案:' 开始, 后面的都是答案。的语义相似度，一模一样就是100分，完全不一样就是0分，请根据语义相似性给出分数。答案可能包含多个意思，用','或者';'分隔。如果回答跟答案中某一个意思相似，也请给出90分以上的分数。"
        },
        {
            "role": "user",
            "content": f"回答: {text1}. 答案: {text2}"
        }
    ]
    
    try:
        response = get_chat_completion(messages)
        pattern = r'[-+]?\d*\.?\d+'
        match = re.search(pattern, response)
        if match:
            similarity = float(match.group())
            print(f"回答: {text1} 与答案: {text2} 的相似度: {similarity}")
            return similarity
        else:
            print(f"相似度找不到: {response}")
            return 0
    except Exception as e:
        print(f"错误: {str(e)}") 

# 使用示例
if __name__ == "__main__":
    messages = [
        {
            "role": "system",
            "content": "请比较一下如下中文回答和答案的意思,回答以 '回答:'开始，以'.'结束， 答案以'答案:' 开始, 后面的都是答案。的语义相似度，一模一样就是100分，完全不一样就是0分，请根据语义相似性给出分数。答案可能包含多个意思，用','或者';'分隔。如果回答跟答案中某一个意思相似，也请给出90分以上的分数。"
        },
        {
            "role": "user",
            "content": "回答:不正常   答案: 反常的，异常的；变态的"
        }
    ]
    
    try:
        response = get_chat_completion(messages)
        print(f"AI 回复: {response}")
    except Exception as e:
        print(f"错误: {str(e)}") 