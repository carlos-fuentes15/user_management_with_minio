# Standard library
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

# Third-party
import pytest
import pytest_asyncio
from httpx import AsyncClient
from faker import Faker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, scoped_session

# Application-specific
from app.main import app
from app.database import Base
from app.models.user_model import User, UserRole
from app.dependencies import get_db, get_settings
from app.utils.security import hash_password
from app.utils.template_manager import TemplateManager
from app.services.email_service import EmailService
from app.services.jwt_service import create_access_token

fake = Faker()
settings = get_settings()

# --------------------------------------------------------------------
# TEST DB: force local SQLite so tests don't resolve external hosts
# --------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Async engine/session for tests
engine = create_async_engine(TEST_DATABASE_URL, echo=getattr(settings, "debug", False))
AsyncTestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
AsyncSessionScoped = scoped_session(AsyncTestingSessionLocal)

# -------------------------------------------------------
# Per-test database create/drop and session management
# -------------------------------------------------------
@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_database():
    """Create all tables before each test, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def db_session(setup_database):
    """Async SQLAlchemy session per test."""
    async with AsyncSessionScoped() as session:
        try:
            yield session
        finally:
            await session.close()

# ---------------------------
# HTTP client for API tests
# ---------------------------
@pytest_asyncio.fixture(scope="function")
async def async_client(db_session: AsyncSession):
    """
    Async HTTP client that overrides get_db dependency to use the per-test session.
    """
    async def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        try:
            yield client
        finally:
            app.dependency_overrides.clear()

# -------------------
# Email service mock
# -------------------
@pytest.fixture
def email_service():
    """
    Returns real EmailService only if send_real_mail is 'true', otherwise a mock.
    Prevents accidental real email sending during tests.
    """
    if getattr(settings, "send_real_mail", "false") == "true":
        tm = TemplateManager()
        return EmailService(template_manager=tm)
    mock_service = AsyncMock(spec=EmailService)
    mock_service.send_verification_email.return_value = None
    mock_service.send_user_email.return_value = None
    return mock_service

# -------------------------
# User factory-style fixtures (unique values to avoid UNIQUE errors)
# -------------------------
def _uniq_username() -> str:
    return f"{fake.user_name()}_{uuid4().hex[:8]}"

def _uniq_email() -> str:
    # keep a valid email format but unique prefix
    return f"{uuid4().hex[:8]}_{fake.user_name()}@example.com"

@pytest_asyncio.fixture(scope="function")
async def locked_user(db_session: AsyncSession):
    user = User(
        nickname=_uniq_username(),
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        email=_uniq_email(),
        hashed_password=hash_password("MySuperPassword$1234"),
        role=UserRole.AUTHENTICATED,
        email_verified=False,
        is_locked=True,
        failed_login_attempts=getattr(settings, "max_login_attempts", 5),
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest_asyncio.fixture(scope="function")
async def user(db_session: AsyncSession):
    user = User(
        nickname=_uniq_username(),
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        email=_uniq_email(),
        hashed_password=hash_password("MySuperPassword$1234"),
        role=UserRole.AUTHENTICATED,
        email_verified=False,
        is_locked=False,
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest_asyncio.fixture(scope="function")
async def verified_user(db_session: AsyncSession):
    user = User(
        nickname=_uniq_username(),
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        email=_uniq_email(),
        hashed_password=hash_password("MySuperPassword$1234"),
        role=UserRole.AUTHENTICATED,
        email_verified=True,
        is_locked=False,
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest_asyncio.fixture(scope="function")
async def unverified_user(db_session: AsyncSession):
    user = User(
        nickname=_uniq_username(),
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        email=_uniq_email(),
        hashed_password=hash_password("MySuperPassword$1234"),
        role=UserRole.AUTHENTICATED,
        email_verified=False,
        is_locked=False,
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest_asyncio.fixture(scope="function")
async def users_with_same_role_50_users(db_session: AsyncSession):
    users = []
    for _ in range(50):
        u = User(
            nickname=_uniq_username(),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=_uniq_email(),
            hashed_password=hash_password("MySuperPassword$1234"),
            role=UserRole.AUTHENTICATED,
            email_verified=False,
            is_locked=False,
        )
        db_session.add(u)
        users.append(u)
    await db_session.commit()
    return users

@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    user = User(
        nickname=f"admin_{uuid4().hex[:8]}",
        email=f"admin_{uuid4().hex[:8]}@example.com",
        first_name="John",
        last_name="Doe",
        hashed_password=hash_password("securepassword"),
        role=UserRole.ADMIN,
        is_locked=False,
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest_asyncio.fixture
async def manager_user(db_session: AsyncSession):
    user = User(
        nickname=f"manager_{uuid4().hex[:8]}",
        first_name="John",
        last_name="Doe",
        email=f"manager_{uuid4().hex[:8]}@example.com",
        hashed_password=hash_password("securepassword"),
        role=UserRole.MANAGER,
        is_locked=False,
    )
    db_session.add(user)
    await db_session.commit()
    return user

# -------------------------
# Token fixtures (sync)
# -------------------------
@pytest.fixture(scope="function")
def admin_token(admin_user: User):
    token_data = {"sub": str(admin_user.id), "role": admin_user.role.name}
    return create_access_token(data=token_data, expires_delta=timedelta(minutes=30))

@pytest.fixture(scope="function")
def manager_token(manager_user: User):
    token_data = {"sub": str(manager_user.id), "role": manager_user.role.name}
    return create_access_token(data=token_data, expires_delta=timedelta(minutes=30))

@pytest.fixture(scope="function")
def user_token(user: User):
    token_data = {"sub": str(user.id), "role": user.role.name}
    return create_access_token(data=token_data, expires_delta=timedelta(minutes=30))
