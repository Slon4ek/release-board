from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass

from src.config import settings

engine = create_async_engine(settings.DB_URL)
engine_null_pool = create_async_engine(settings.DB_URL, pool_pre_ping=True, pool_size=0)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
async_session_maker_null_pool = async_sessionmaker(engine_null_pool, expire_on_commit=False)


class Base(DeclarativeBase, MappedAsDataclass):
    pass
