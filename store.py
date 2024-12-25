from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import bcrypt
from typing import Optional
from migrator import run_migrations
from util import load_config

# 获取数据库配置
config = load_config('database')

def get_database_url(config):
    # 从 URL 中解析主机名/IP地址
    # 假设 config['url'] 格式为: "mysql://hostname:3306/dbname?param=value"
    url_parts = config['url'].split('/')
    host = url_parts[2].split(':')[0]  # 提取主机名部分
    
    # 获取数据库名
    database = url_parts[-1].split('?')[0]
    
    # 构建完整的数据库URL
    DATABASE_URL = f"mysql+pymysql://{config['username']}:{config['password']}@{host}/{database}?charset=utf8mb4"
    return DATABASE_URL

# 创建数据库连接
DATABASE_URL = get_database_url(config)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    password_hash = Column(String(255))
    current_word_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WrongWord(Base):
    __tablename__ = "wrong_words"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False)
    word = Column(String(100), nullable=False)
    error_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class UserStore:

    @staticmethod
    def create_user(username: str, password: str) -> Optional[User]:
        """创建新用户"""
        db = SessionLocal()
        try:
            # 检查用户名是否已存在
            if db.query(User).filter(User.username == username).first():
                return None
            
            # 对密码进行加密
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            user = User(
                username=username,
                password_hash=password_hash.decode('utf-8'),
                current_word_index=0
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        finally:
            db.close()

    @staticmethod
    def verify_user(username: str, password: str) -> Optional[User]:
        """验证用户登录"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                return None
            
            if bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                return user
            return None
        finally:
            db.close()

    @staticmethod
    def update_word_index(username: str, index: int) -> bool:
        """更新用户的单词索引"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                return False
            
            user.current_word_index = index
            db.commit()
            return True
        finally:
            db.close()

    @staticmethod
    def get_word_index(username: str) -> Optional[int]:
        """获取用户的当前单词索引"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == username).first()
            return user.current_word_index if user else None
        finally:
            db.close()

    @staticmethod
    def add_to_wrong_list(username: str, word: str) -> Optional[int]:
        """添加单词到错词本，如果已存在则增加错误次数"""
        with SessionLocal() as db:
            try:
                count = 0
                # 查找是否已存在
                wrong_word = db.query(WrongWord).filter(
                    WrongWord.username == username,
                    WrongWord.word == word
                ).first()

                if wrong_word:
                    # 如果存在，增加错误次数
                    wrong_word.error_count += 1
                    wrong_word.updated_at = func.now()
                    count = wrong_word.error_count
                else:
                    # 如果不存在，创建新记录
                    wrong_word = WrongWord(
                        username=username,
                        word=word
                    )
                    db.add(wrong_word)
                    count = 1
                db.commit()
                return count
            except SQLAlchemyError as e:
                db.rollback()
                raise e

    @staticmethod
    def remove_from_wrong_list(username: str, word: str) -> None:
        """从错词本中移除单词"""
        with SessionLocal() as db:
            try:
                db.query(WrongWord).filter(
                    WrongWord.username == username,
                    WrongWord.word == word
                ).delete()
                db.commit()
            except SQLAlchemyError as e:
                db.rollback()
                raise e

    @staticmethod
    def increase_wrong_count(username: str, word: str) -> None:
        """增加单词的错误次数"""
        with SessionLocal() as db:
            try:
                wrong_word = db.query(WrongWord).filter(
                    WrongWord.username == username,
                    WrongWord.word == word
                ).first()
                
                if wrong_word:
                    wrong_word.error_count += 1
                    wrong_word.updated_at = func.now()
                    db.commit()
            except SQLAlchemyError as e:
                db.rollback()
                raise e

    @staticmethod
    def get_wrong_list(username: str, page: int = 1, page_size: int = 10) -> list:
        """获取用户的错词列表，支持分页"""
        with SessionLocal() as db:
            try:
                offset = (page - 1) * page_size
                wrong_words = db.query(WrongWord).filter(
                    WrongWord.username == username
                ).order_by(
                    WrongWord.error_count.desc(),
                    WrongWord.updated_at.desc()
                ).offset(offset).limit(page_size).all()

                return [
                    {
                        "word": w.word,
                        "error_count": w.error_count,
                        "created_at": w.created_at,
                        "updated_at": w.updated_at
                    } for w in wrong_words
                ]
            except SQLAlchemyError as e:
                raise e

    @staticmethod
    def get_wrong_words_count(username: str) -> int:
        """获取用户错词总数"""
        with SessionLocal() as db:
            try:
                return db.query(WrongWord).filter(
                    WrongWord.username == username
                ).count()
            except SQLAlchemyError as e:
                raise e
    @staticmethod
    def get_word_error_count(username: str, word: str) -> int:
        """获取用户某个单词的错误次数"""
        with SessionLocal() as db:
            try:
                wrong_word = db.query(WrongWord).filter(
                    WrongWord.username == username,
                    WrongWord.word == word
                ).first()
                
                return wrong_word.error_count if wrong_word else 0
            except SQLAlchemyError as e:
                raise e
# 创建数据库表
def init_db():
    # 运行数据库迁移
    run_migrations()