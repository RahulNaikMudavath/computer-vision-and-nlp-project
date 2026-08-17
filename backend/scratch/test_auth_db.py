import unittest
import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.database import Base, User, UserSettings

class TestAuthDatabase(unittest.TestCase):
    def setUp(self):
        # Use an in-memory SQLite database for testing
        self.engine = create_engine("sqlite:///:memory:")
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        self.session = self.Session()

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_create_user_with_settings(self):
        # Create a new user
        user = User(
            email="test@example.com",
            hashed_password="hashedpassword123",
            full_name="Test User",
            role="Standard User"
        )
        self.session.add(user)
        self.session.commit()

        # Check user fields
        queried_user = self.session.query(User).filter_by(email="test@example.com").first()
        self.assertIsNotNone(queried_user)
        self.assertEqual(queried_user.full_name, "Test User")
        self.assertEqual(queried_user.role, "Standard User")
        self.assertTrue(queried_user.is_active)

        # Create settings for user
        settings = UserSettings(
            user_id=queried_user.id,
            theme="dark",
            language="en",
            default_ocr_language="en",
            email_notifications=True
        )
        self.session.add(settings)
        self.session.commit()

        # Verify relationship loading
        self.assertEqual(queried_user.settings.theme, "dark")
        self.assertTrue(queried_user.settings.email_notifications)

if __name__ == "__main__":
    unittest.main()
