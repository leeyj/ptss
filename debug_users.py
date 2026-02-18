from ptss import app, db
from models import User

with app.app_context():
    count = User.query.count()
    print(f"DEBUG_USER_COUNT: {count}")
    if count > 0:
        for u in User.query.all():
            print(f"DEBUG_USER: {u.username}")
