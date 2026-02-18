from ptss import app, db
from models import User
from werkzeug.security import generate_password_hash
import os
from dotenv import load_dotenv

load_dotenv()


def sync_admin():
    with app.app_context():
        admin_pass = os.getenv("PTSS_ADMIN_PASSWORD", "admin")
        user = User.query.filter_by(username="admin").first()

        if user:
            print(f"Updating existing admin password to match .env...")
            user.password_hash = generate_password_hash(admin_pass)
        else:
            print(f"Creating new admin user with password from .env...")
            user = User(
                username="admin",
                password_hash=generate_password_hash(admin_pass),
                role="admin",
            )
            db.session.add(user)

        db.session.commit()
        print("✅ Admin user synchronization complete.")


if __name__ == "__main__":
    sync_admin()
