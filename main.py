from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter
from pydantic import BaseModel
import json
from difflib import SequenceMatcher
from typing import Optional
from store import UserStore, init_db
from speech import text_to_speech
import jwt as pyjwt
from datetime import datetime, timedelta
import os
import tempfile
from fastapi.responses import FileResponse

# 创建API路由器
api_router = APIRouter(prefix="/api")

app = FastAPI()

# 用于追踪当前单词索引的变量
current_word_index = 0

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 修改OAuth2配置，使用新的token路径
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

# JWT 配置
SECRET_KEY = "your-secret-key"  # 在生产环境中应该使用环境变量
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

init_db()

# 加载单词数据
with open('toefl.json', 'r', encoding='utf-8') as f:
    word_list = json.load(f)

class UserCreate(BaseModel):
    username: str
    password: str

class UserAnswer(BaseModel):
    answer: str

class WordResponse(BaseModel):
    word: str
    phonetic: Optional[str]
    part_of_speech: Optional[str]

def calculate_similarity(text1: str, text2: str) -> float:
    """计算两个文本之间的相似度"""
    return SequenceMatcher(None, text1, text2).ratio()

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """验证用户token并返回用户名"""
    try:
        payload = pyjwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="无效的认证信息")
        return username
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token已过期，请重新登录")
    except Exception:
        raise HTTPException(status_code=401, detail="无效的认证信息")

def create_access_token(data: dict):
    """创建访问令牌"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = pyjwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 将所有API路由添加到路由器
@api_router.post("/register")
def register_user(user: UserCreate):
    """注册新用户"""
    result = UserStore.create_user(user.username, user.password)
    if not result:
        raise HTTPException(status_code=400, detail="用户名已存在")
    return {"message": "注册成功"}

@api_router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """用户登录"""
    user = UserStore.verify_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    access_token = create_access_token({"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.get("/current-word")
async def get_current_word(username: str = Depends(get_current_user)):
    """获取当前单词"""
    current_word_index = UserStore.get_word_index(username)
    if current_word_index >= len(word_list):
        raise HTTPException(status_code=404, detail="已完成所有单词学习")
    
    word_data = word_list[current_word_index]
    return WordResponse(
        word=word_data["word"],
        phonetic=word_data.get("phonetic"),
        part_of_speech=word_data.get("part_of_speech")
    )

@api_router.post("/check-answer")
async def check_answer(
    user_answer: UserAnswer,
    username: str = Depends(get_current_user)
):
    """检查用户答案"""
    current_word_index = UserStore.get_word_index(username)
    
    if current_word_index >= len(word_list):
        raise HTTPException(status_code=404, detail="已完成所有单词学习")
    
    correct_meaning = word_list[current_word_index]["chinese_meaning"]
    # 打印当前的单词和索引，用于调试
    print(f"用户: {username}, 当前单词: {word_list[current_word_index]['word']}, current_word_index: {current_word_index}")
    meanings = [m.strip() for m in correct_meaning.replace('；', ';', ',', '，').split(';')]
    
    max_similarity = max(calculate_similarity(user_answer.answer, meaning) for meaning in meanings)
    
    response = {
        "similarity": round(max_similarity * 100, 2),
        "passed": max_similarity >= 0.6,
        "correct_meaning": correct_meaning
    }
    
    return response

@api_router.post("/next-word")
async def next_word(username: str = Depends(get_current_user)):
    """移动到下一个单词"""
    current_word_index = UserStore.get_word_index(username)
    new_index = current_word_index + 1
    
    if new_index >= len(word_list):
        raise HTTPException(status_code=404, detail="已完成所有单词学习")
    
    UserStore.update_word_index(username, new_index)
    word_data = word_list[new_index]
    current_word_index = new_index
    return WordResponse(
        word=word_data["word"],
        phonetic=word_data.get("phonetic"),
        part_of_speech=word_data.get("part_of_speech")
    )

@api_router.get("/progress")
def get_progress():
    """获取学习进度"""
    return {
        "current_index": current_word_index,
        "total_words": len(word_list),
        "progress_percentage": round((current_word_index / len(word_list)) * 100, 2)
    }

@api_router.post("/reset")
def reset_progress():
    """重置学习进度"""
    global current_word_index
    current_word_index = 0
    return {"message": "进度已重置"}

@api_router.get("/word-audio/{word}")
async def get_word_audio(word: str):
    """获取单词的音频文件"""
    try:
        audio_path = text_to_speech(word)
        # 打印audio_path
        print(f"audio_path: {audio_path}")

        # 返回音频文件
        return FileResponse(
            audio_path,
            media_type="audio/wav",
            filename=f"{word}.wav"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 将API路由器注册到应用
app.include_router(api_router)

# 配置多个静态目录
app.mount("/js", StaticFiles(directory="ui/js"), name="js")
app.mount("/css", StaticFiles(directory="ui/css"), name="css")
app.mount("/images", StaticFiles(directory="ui/images"), name="images")

# HTML文件目录放在最后配置
app.mount("/", StaticFiles(directory="ui", html=True), name="ui") 