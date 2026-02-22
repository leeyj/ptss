import requests
import os
from dotenv import load_dotenv
from pathlib import Path


def send_discord_report(content):
    # 스크립트 위치 기준으로 tools/pri.env 또는 pri.env 탐색
    current_dir = Path(__file__).parent
    pri_env_path = current_dir / "pri.env"

    if not pri_env_path.exists():
        # 루트 기준 탐색
        pri_env_path = Path("tools/pri.env")

    load_dotenv(pri_env_path)

    token = os.getenv("DISCORD_BOT_TOKEN")
    admin_id = os.getenv("ADMIN_USER_ID")

    if not token or not admin_id:
        print(
            f"Error: DISCORD_BOT_TOKEN or ADMIN_USER_ID is missing (Checked path: {pri_env_path.absolute()})"
        )
        return False

    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}

    try:
        # 1. 관리자와의 DM 채널 생성
        dm_channel_res = requests.post(
            "https://discord.com/api/v10/users/@me/channels",
            headers=headers,
            json={"recipient_id": admin_id},
            timeout=10,
        )
        dm_channel_res.raise_for_status()
        channel_id = dm_channel_res.json()["id"]

        # 2. 메시지 전송
        chunks = [content[i : i + 1900] for i in range(0, len(content), 1900)]
        for i, chunk in enumerate(chunks):
            msg_payload = {
                "content": f"**[PTSS 테스트 리포트 - Part {i + 1}]**\n{chunk}"
                if len(chunks) > 1
                else f"**[PTSS 테스트 리포트]**\n{chunk}"
            }
            requests.post(
                f"https://discord.com/api/v10/channels/{channel_id}/messages",
                headers=headers,
                json=msg_payload,
                timeout=10,
            ).raise_for_status()

        print(f"Success: Discord 리포트가 {admin_id}에게 전송되었습니다.")
        return True
    except Exception as e:
        print(f"Failed to send Discord message: {e}")
        return False


if __name__ == "__main__":
    send_discord_report("이것은 PTSS AI 팀의 자동 보고 시스템 테스트 메시지입니다.")
