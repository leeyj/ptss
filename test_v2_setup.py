from ptss import app, db
from models import User


def test_setup_redirect():
    with app.test_client() as client:
        # 1. Any access without users should redirect to /setup
        response = client.get("/")
        print(
            f"Access /: {response.status_code}, Location: {response.status_code == 302 and '/setup' in response.headers.get('Location', '')}"
        )

        # 2. Access /setup should be 200
        response = client.get("/setup")
        print(f"Access /setup: {response.status_code}")

        # 3. Perform setup
        data = {
            "username": "newadmin",
            "password": "newpassword123",
            "master_key": "test_master_key_123",
        }
        response = client.post("/setup", data=data, follow_redirects=True)
        print(f"Setup POST: {response.status_code}")

        # 4. Verify user exists
        with app.app_context():
            user = User.query.filter_by(username="newadmin").first()
            if user:
                print(f"✅ User 'newadmin' created successfully.")
            else:
                print(f"❌ User creation failed.")


if __name__ == "__main__":
    test_setup_redirect()
