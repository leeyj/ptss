import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# PTSS Crypto Utilities


def get_cipher_suite():
    # .env 로드 및 마스터 키 설정
    key = None
    try:
        from core.models import Config

        # DB에서 키 조회
        conf = Config.query.filter_by(key="PTSS_MASTER_KEY").first()
        if conf:
            key = conf.value
    except Exception:
        # DB 연결 전이거나 앱 컨텍스트 밖일 경우
        pass

    if not key:
        # Fallback (개발 환경 또는 키 누락 시)
        key = "PTSS_INITIAL_SETUP_KEY_CHANGE_ME_NOW"

    # Ensure key is 32 bytes and base64 encoded for Fernet
    if len(key) != 44:
        import base64
        import hashlib

        key = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest()).decode()

    return Fernet(key.encode())


def encrypt_data(data: str) -> str | None:
    if not data:
        return None
    suite = get_cipher_suite()  # type: ignore
    return suite.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str | None:
    if not encrypted_data:
        return None
    try:
        suite = get_cipher_suite()  # type: ignore
        return suite.decrypt(encrypted_data.encode()).decode()
    except Exception:
        return None
