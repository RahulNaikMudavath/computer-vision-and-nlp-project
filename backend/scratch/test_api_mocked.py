import unittest
import os
import sys
from fastapi.testclient import TestClient

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.models.database import Base, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set up test database engine
test_db_file = "test_temp_api.db"
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

class TestMockedAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=test_engine)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()
        if os.path.exists(test_db_file):
            try:
                os.remove(test_db_file)
            except Exception:
                pass

    def test_health_check(self):
        # Check simple root/health endpoint if exists, or check login response
        response = self.client.get("/")
        # If / returns 404 because it is not defined, we check docs
        if response.status_code == 404:
            response = self.client.get("/docs")
        self.assertEqual(response.status_code, 200)

    def test_invalid_login(self):
        # Post to login with invalid credentials
        response = self.client.post("/auth/login", json={"email": "wrong@test.com", "password": "wrong"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Incorrect email or password.")

if __name__ == "__main__":
    unittest.main()
