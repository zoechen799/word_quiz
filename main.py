from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
import json
from difflib import SequenceMatcher
from typing import Optional
from store import UserStore, init_db
from speech import text_to_speech
import jwt as pyjwt
from datetime import datetime, timedelta
import os
from fastapi.responses import FileResponse
from check_answer import check_answer_by_all_means
import math
from util import load_config

# 创建API路由器
api_router = APIRouter(prefix="/api")

app = FastAPI()

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 开发模式配置
class NoCache(StaticFiles):
    def is_not_modified(self, response_headers, request_headers) -> bool:
        return False

# 根据环境变量判断是否为开发模式
if os.getenv("ENV") == "development":
    static_files = NoCache
else:
    static_files = StaticFiles
    init_db()

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
# similarity = BertSimilarity()

# 加载JWT配置
jwt_config = load_config("jwt")

# 使用配置中的JWT设置
SECRET_KEY = jwt_config["secret_key"]
ALGORITHM = jwt_config["algorithm"]
ACCESS_TOKEN_EXPIRE_MINUTES = int(jwt_config["access_token_expire_minutes"])

# 加载单词数据
with open('toefl.json', 'r', encoding='utf-8') as f:
    word_list = json.load(f)

# 加载章节数据
with open('chapter.json', 'r', encoding='utf-8') as f:
    chapter_list = json.load(f)

def get_word_index(word: str):
    # 返回word在word_list中的索引, word_list的格式是[{word: str, phonetic: str, part_of_speech: str, chinese_meaning: str}]
    return next((i for i, w in enumerate(word_list) if w["word"] == word), None)

# 遍历chapter_list，找到start_word和end_word，在word_list中的索引，作为start_index和end_index
for chapter in chapter_list:
    chapter["start_index"] = get_word_index(chapter["start_word"])
    chapter["end_index"] = get_word_index(chapter["end_word"])

class UserCreate(BaseModel):
    username: str
    password: str

class UserAnswer(BaseModel):
    answer: str

class Progress(BaseModel):
    index: int

class WordResponse(BaseModel):
    word: str
    phonetic: Optional[str]
    part_of_speech: Optional[str]


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
    if current_word_index is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if current_word_index >= len(word_list):
        raise HTTPException(status_code=404, detail="已完成所有单词学习")
    
    current_word = word_list[current_word_index]["word"]
    correct_meaning = word_list[current_word_index]["chinese_meaning"]
    score = await check_answer_by_all_means(user_answer.answer, correct_meaning)
    passed = score >= 80
    wrong_count = UserStore.get_word_error_count(username, current_word)
    response = {
        "similarity": score,
        "passed": passed,
        "correct_meaning": correct_meaning,
        "wrong_count": wrong_count  # 添加错误次数到响应中
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
def get_progress(username: str = Depends(get_current_user)):
    """获取学习进度"""
    current_word_index = UserStore.get_word_index(username)
    
    # 获取当前章节信息
    current_chapter = None
    chapter_index = None
    for idx, chapter in enumerate(chapter_list):
        if chapter["start_index"] <= current_word_index < chapter["end_index"]:
            current_chapter = chapter
            chapter_index = idx
            break
    
    # 如果找到当前章节，计算章节内进度
    chapter_progress = None
    if current_chapter:
        chapter_total = current_chapter["end_index"] - current_chapter["start_index"]
        chapter_current = current_word_index - current_chapter["start_index"] + 1
        chapter_progress = round((chapter_current / chapter_total) * 100, 2)
    
    return {
        "current_index": current_word_index,
        "chapter_current": chapter_current,
        "current_chapter_index": chapter_index,
        "total_words": len(word_list),
        "progress_percentage": round((current_word_index / len(word_list)) * 100, 2),
        "current_chapter_progress": chapter_progress,
        "current_chapter_total_words": (current_chapter["end_index"] - current_chapter["start_index"]) if current_chapter else None
    }

# 切换章节
@api_router.post("/switch-chapter")
def switch_chapter(progress: Progress,
                   username: str = Depends(get_current_user)):
    """切换章节"""
    # 根据chapter_index从chapter_list中获取start_word, 然后更新UserStore中的current_word_index
    start_word = chapter_list[progress.index]["start_word"]
    # 查找 start_word 在 word_list 中的索引
    start_index = next(
        (i for i, word in enumerate(word_list) if word["word"] == start_word),
        None
    )
    
    if start_index is None:
        raise HTTPException(status_code=404, detail=f"找不到单词 {start_word}")
        
    print(f"start_word: {start_word}, index: {start_index}")
    UserStore.update_word_index(username, start_index)


@api_router.post("/reset")
def reset_progress(username: str = Depends(get_current_user)):
    """重置学习进度"""
    UserStore.update_word_index(username, 0)
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
            media_type="audio/mp3",
            filename=f"{word}.mp3"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/add-to-wrong-list")
async def add_to_wrong_list(request: dict, 
      username: str = Depends(get_current_user)):
    word = request.get("word")
    
    if not username or not word:
        raise HTTPException(status_code=400, detail="Missing username or word")
    
    try:
        # 这里添加将单词加入错词本的逻辑
        UserStore.add_to_wrong_list(username, word)
        return {"message": "Successfully added to wrong list"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/get-wrong-list")
def get_wrong_list(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=5, ge=1),
    username: str = Depends(get_current_user)
):
    """获取用户的错词列表"""
    wrong_words = UserStore.get_wrong_list(username, page, per_page)
    # wrong_words 是格式为[{"word": "word", "error_count": 1}]的一个list
    # 根据wrong_words中的word，从word_list中获取对应的chinese_meaning
    for word in wrong_words:
        word_info = next((w for w in word_list if w["word"] == word["word"]), None)
        if word_info:
            word["meaning"] = word_info["chinese_meaning"]
    total_count = UserStore.get_wrong_words_count(username)
    total_pages = math.ceil(total_count / per_page)
    return {
        "words": wrong_words,
        "total_pages": total_pages,
        "current_page": page,
        "total_words": total_count
    }

@app.post("/api/next-word")
async def next_word(username: str = Depends(get_current_user)):
    """获取下一个单词"""
    current_word_index = UserStore.get_word_index(username)
    
    # 如果是新用户，初始化索引为0
    if current_word_index is None:
        # 没有找到用户的情况下，需要重定向到登录页面
        raise HTTPException(status_code=401, detail="无效的认证信息")
    else:
        new_index = current_word_index + 1
        # 检查是否超出单词列表范围
        if new_index >= len(word_list):
            raise HTTPException(status_code=404, detail="已完成所有单词学习")
        
        UserStore.update_word_index(username, new_index)
        current_word_index = new_index
    
    return {
        "word": word_list[current_word_index]["word"],
        "phonetic": word_list[current_word_index].get("phonetic", "")
    }

# 将API路由器注册到应用
app.include_router(api_router)

# 配置多个静态目录
app.mount("/js", static_files(directory="ui/js"), name="js")
app.mount("/css", static_files(directory="ui/css"), name="css")
app.mount("/images", static_files(directory="ui/images"), name="images")

# HTML文件目录放在最后配置
app.mount("/", static_files(directory="ui", html=True), name="ui") 