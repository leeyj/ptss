from ptss import app, db, decrypt_data
from models import Host, Config
import os

with app.app_context():
    host = Host.query.order_by(Host.id.desc()).first()
    if not host:
        print("No host found.")
    else:
        print(f"Host: {host.name} ({host.id})")
        print(f"Hostname: {host.hostname}")
        print(f"Username: {host.username}")
        print(f"Auth Type: {host.auth_type}")
        print(f"Raw Password in DB: {host.password}")

        # Check Master Key
        env_key = os.getenv("PTSS_MASTER_KEY")
        db_key_conf = Config.query.filter_by(key="PTSS_MASTER_KEY").first()
        db_key = db_key_conf.value if db_key_conf else None

        print(f"Env Master Key: {env_key}")
        print(f"DB Master Key: {db_key}")

        try:
            # Try to decrypt key if exists
            if host.encrypted_key:
                decrypted = decrypt_data(host.encrypted_key)
                print(f"Decrypted Key Start: {decrypted[:20]}...")
            else:
                print("No encrypted key found for this host.")
        except Exception as e:
            print(f"Decryption Error: {e}")
