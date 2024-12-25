from transformers import BertTokenizer, BertModel
import torch
import torch.nn.functional as F
import os

class BertSimilarity:
    def __init__(self, model_name='bert-base-chinese'):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        # 指定模型目录路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_dir = os.path.join(current_dir, 'models', 'bert-base-chinese')
        print(f"模型目录: {model_dir}")
        # 直接使用模型目录路径，而不是模型名称
        self.tokenizer = BertTokenizer.from_pretrained(
            model_dir,  # 使用完整路径而不是模型名称
            cache_dir=model_dir
        )
        self.model = BertModel.from_pretrained(
            model_dir,  # 使用完整路径而不是模型名称
            cache_dir=model_dir
        ).to(self.device)
        print("模型加载成功！")
        
    def get_text_embedding(self, text):
        """获取文本的BERT嵌入向量"""
        inputs = self.tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=512)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            # 使用[CLS]标记的输出作为整个句子的表示
            embeddings = outputs.last_hidden_state[:, 0, :]
            # 归一化
            embeddings = F.normalize(embeddings, p=2, dim=1)
            
        return embeddings
    
    def calculate_similarity(self, text1, text2):
        """计算两个文本的相似度"""
        embedding1 = self.get_text_embedding(text1)
        embedding2 = self.get_text_embedding(text2)
        
        # 计算余弦相似度
        similarity = torch.mm(embedding1, embedding2.T)
        print(f"计算两个文本的相似度: {text1}, {text2} 相似度分数: {similarity[0][0]}")
        return float(similarity[0][0]) 

if __name__ == "__main__":
    similarity = BertSimilarity()
    text1 = "不寻常"
    text2 = "反常的，异常的；变态的"
    score = similarity.calculate_similarity(text1, text2)
    print(f"相似度分数: {score}")