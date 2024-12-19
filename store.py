from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import bcrypt
from typing import Optional
from migrator import run_migrations
from util import load_config

# 获取数据库配置
config = load_config('database')

# 创建数据库连接
DATABASE_URL = f"mysql+pymysql://{config['username']}:{config['password']}@localhost/{config['url'].split('/')[-1].split('?')[0]}?charset=utf8mb4"
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

# 创建数���库表
def init_db():
    # 运行数据库迁移
    run_migrations()