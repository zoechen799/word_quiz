from text_similarity_bert import BertSimilarity
from concurrent.futures import ThreadPoolExecutor
from typing import List
from open_ai import calculate_similarity_openai
import asyncio
from functools import partial

similarity = BertSimilarity()

def compare_single_meaning(answer: str, meaning: str) -> float:
    """比较单个含义与答案的相似度"""
    return similarity.calculate_similarity(answer.strip(), meaning.strip()) * 100

async def check_similarity(answer: str, correct_meaning: str) -> float:
    """
    多线程计算答案与标准答案的相似度
    
    Args:
        answer: 用户输入的答案
        correct_meaning: 正确答案（可能包含多个含义，用分号分隔）
        threshold: 相似度阈值，默认0.8
        
    Returns:
        bool: 是否匹配成功
    """
    # 分割多个含义
    meanings = [m for m in correct_meaning
                .replace('；', ';')
                .replace(',', ';')
                .replace('，', ';')
                .split(';') if m.strip()]
    
    if not meanings:
        return False
        
    # 使用线程池并行计算相似度
    with ThreadPoolExecutor(max_workers=min(len(meanings), 5)) as executor:
        # 提交所有比较任务
        future_to_meaning = {
            executor.submit(compare_single_meaning, answer, meaning): meaning 
            for meaning in meanings
        }
        # 获取所有相似度结果
        similarities = []
        for future in future_to_meaning:
            try:
                similarity_score = future.result()
                similarities.append(similarity_score)
            except Exception as e:
                print(f"计算相似度时发生错误: {e}")
                continue
    
    # 如果没有有效的相似度结果，返回False
    if not similarities:
        return False
    # 返回最大相似度是否超过阈值
    return max(similarities)

# 使用示例
async def check_answer_by_all_means(answer: str, correct_meaning: str) -> bool:
    """
    检查答案是否正确
    
    Args:
        answer: 用户输入的答案
        word: 单词信息，包含chinese字段作为正确答案
        
    Returns:
        bool: 答案是否正确
    """
    if not answer or not correct_meaning:
        return False
    
    # 将同步函数包装成异步函数
    async def run_sync_in_thread(func, *args):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)
    
    # 并发执行两个相似度计算
    num1, num2 = await asyncio.gather(
        check_similarity(answer, correct_meaning),
        run_sync_in_thread(calculate_similarity_openai, answer, correct_meaning)
    )
    
    print(f"bert 模型打分: {num1}, openai 打分: {num2}")
    return min(num1, num2)