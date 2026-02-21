import os
import gzip
import shutil
from datetime import datetime, timedelta
from core.database import db


def compress_recording(file_path):
    """파일을 Gzip으로 압축하고 원본을 삭제합니다."""
    gz_path = f"{file_path}.gz"
    try:
        with open(file_path, "rb") as f_in:
            with gzip.open(gz_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(file_path)
        return gz_path
    except Exception as e:
        print(f"[REPROD] Compression failed: {e}")
        return file_path


def cleanup_old_recordings(app):
    """설정된 보관 기간이 지난 녹화 파일을 삭제합니다."""
    with app.app_context():
        try:
            from core.models import Config, History

            days_conf = Config.query.filter_by(key="rec_retention_days").first()
            days = (
                int(days_conf.value) if days_conf and days_conf.value.isdigit() else 30
            )

            threshold = datetime.now() - timedelta(days=days)
            old_histories = History.query.filter(
                History.action_type == "SESSION",
                History.timestamp < threshold,
                History.recording_path != None,
            ).all()

            for hist in old_histories:
                if hist.recording_path and os.path.exists(hist.recording_path):
                    try:
                        os.remove(hist.recording_path)
                    except Exception:
                        pass
                hist.recording_path = None  # 경로 정보 초기화
            db.session.commit()
        except Exception as e:
            print(f"[REPROD] Cleanup failed: {e}")
