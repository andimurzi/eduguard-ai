"""Koneksi MySQL (SQLAlchemy + PyMySQL)."""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()
DB_URL = os.getenv("DB_URL", "mysql+pymysql://root:@localhost:3306/eduguard?charset=utf8mb4")
engine = create_engine(DB_URL, pool_pre_ping=True, pool_recycle=1800)
