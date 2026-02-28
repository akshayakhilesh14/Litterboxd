from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv
import os
import ssl

load_dotenv()

# DigitalOcean MySQL Connection String
# Format: mysql+aiomysql://user:password@host:port/database
MYSQL_USER = os.getenv("MYSQL_USER", "doadmin")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_HOST = os.getenv(
    "MYSQL_HOST", "litterboxd-hackillinois-do-user-33939044-0.k.db.ondigitalocean.com")
MYSQL_PORT = os.getenv("MYSQL_PORT", "25060")
MYSQL_DB = os.getenv("MYSQL_DB", "defaultdb")

DATABASE_URL = f"mysql+aiomysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

# Create async engine with DigitalOcean SSL configuration
# DigitalOcean requires SSL for remote connections
# Note: aiomysql handles SSL automatically for remote connections
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL logging
    future=True,
    pool_pre_ping=True,  # Verify connections before using them
)

# Create session factory
async_session = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Base for ORM models
Base = declarative_base()


async def get_db():
    """Dependency for FastAPI to get async database session"""
    async with async_session() as session:
        yield session


async def init_db():
    """Initialize database - create all tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def ping():
    """Test database connection"""
    async with async_session() as session:
        result = await session.execute("SELECT 1")
        return result.fetchone()
