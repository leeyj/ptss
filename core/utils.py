from flask import request


def get_client_ip():
    """Cloudflare 및 일반 프록시 헤더를 고려하여 실제 클라이언트 IP를 반환"""
    # 1. Cloudflare 전용 헤더
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip
    # 2. 표준 프록시 헤더 (Nginx 등)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    # 3. 직접 접속
    return request.remote_addr
