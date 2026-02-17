from app import app, db

with app.app_context():
    try:
        db.create_all()
        print("db.create_all() finished.")
    except Exception as e:
        print(f"Error: {e}")
