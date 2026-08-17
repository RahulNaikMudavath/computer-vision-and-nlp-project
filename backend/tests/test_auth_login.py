import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.models.database import Base, get_db

# Set up test database engine
test_db_file = "test_temp_login.db"
test_engine = create_engine(f"sqlite:///{test_db_file}", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Override get_db dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    if os.path.exists(test_db_file):
        try:
            os.remove(test_db_file)
        except Exception:
            pass

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_login_endpoint_returns_tokens_for_registered_user(client):
    response = client.post(
        '/auth/register',
        json={
            'email': 'login-test@example.com',
            'password': 'secret123',
            'full_name': 'Login Test'
        },
    )
    assert response.status_code == 200

    login_response = client.post(
        '/auth/login',
        json={
            'email': 'login-test@example.com',
            'password': 'secret123',
        },
    )

    assert login_response.status_code == 200
    body = login_response.json()
    assert body['token_type'] == 'bearer'
    assert body['access_token']
    assert body['refresh_token']
