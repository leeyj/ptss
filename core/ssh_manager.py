import paramiko  # type: ignore
import os
import shlex


class SSHManager:
    def __init__(self):
        self.client = None
        self.sftp = None
        self.current_path = "~"

    def connect(
        self,
        hostname,
        port,
        username,
        password=None,
        key_path=None,
        pkey_content=None,
        keepalive=0,
    ):
        try:
            self.client = paramiko.SSHClient()
            self.client.load_system_host_keys()
            # 기본적으로는 경고 없이 추가하지만, 가능하면 알려진 호스트 확인
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # type: ignore # nosec

            if pkey_content:
                # 메모리 상의 키 콘텐츠 직접 사용 (io.StringIO 활용)
                import io

                key_file_obj = io.StringIO(pkey_content)
                private_key = paramiko.RSAKey.from_private_key(key_file_obj)
                self.client.connect(  # type: ignore
                    hostname, port=port, username=username, pkey=private_key
                )
            elif key_path and os.path.exists(key_path):
                private_key = paramiko.RSAKey.from_private_key_file(key_path)
                self.client.connect(  # type: ignore
                    hostname, port=port, username=username, pkey=private_key
                )
            else:
                self.client.connect(  # type: ignore
                    hostname, port=port, username=username, password=password
                )

            # 세션 유지 설정 (Keepalive)
            if keepalive > 0:
                transport = self.client.get_transport()  # type: ignore
                if transport:
                    transport.set_keepalive(keepalive)

            # 접속 후 기초 경로 확인
            stdin, stdout, stderr = self.client.exec_command("pwd")  # type: ignore
            self.current_path = stdout.read().decode().strip()

            return True, "Connected successfully"
        except Exception as e:
            return False, str(e)

    def get_sftp(self):
        if not self.client:
            return None, "Not connected"
        try:
            self.sftp = self.client.open_sftp()
            return self.sftp, "SFTP session opened"
        except Exception as e:
            return None, str(e)

    def get_shell(self, term="xterm", width=80, height=24):
        if not self.client:
            return None
        return self.client.invoke_shell(term=term, width=width, height=height)

    def execute_script_file(self, script_content, filename="ptss_script.sh"):
        """스크립트를 서버에 파일로 업로드한 뒤 실행하고 삭제함"""
        if not self.client:
            return None, "Not connected"

        try:
            sftp = self.client.open_sftp()

            # 스크립트 파일 생성 (임시 경로)
            remote_path = f"/tmp/{filename}"
            with sftp.file(remote_path, "w") as f:
                f.write(script_content)

            # 실행 권한 부여
            sftp.chmod(remote_path, 0o755)
            sftp.close()

            # 실행 (Login shell 사용)
            quoted_path = shlex.quote(remote_path)
            cmd = f"bash -l -c {quoted_path}"
            stdin, stdout, stderr = self.client.exec_command(cmd)

            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()

            # 실행 후 삭제 (Cleanup)
            self.client.exec_command(f"rm {shlex.quote(remote_path)}")

            return {"stdout": out, "stderr": err}, "Execution completed"
        except Exception as e:
            return None, str(e)

    def get_completions(self, partial):
        if not self.client:
            return []

        # 쉘 환경에 구애받지 않는 ls 자동 완성
        quoted_partial = shlex.quote(partial)
        # partial 뒤에 *가 붙으므로 완전히 쿼팅하기보다 partial 부분만 보호
        cmd = f"ls -d {quoted_partial}* 2>/dev/null"
        stdin, stdout, stderr = self.client.exec_command(cmd)
        results = stdout.read().decode().splitlines()
        return [r for r in results if r]

    def upload_file(self, local_file, remote_path):
        if not self.client:
            return False, "Not connected"
        try:
            sftp, msg = self.get_sftp()
            if not sftp:
                return False, msg
            sftp.putfo(local_file, remote_path)
            return True, "Upload successful"
        except Exception as e:
            return False, str(e)

    def download_file(self, remote_path):
        if not self.client:
            return None, "Not connected"
        try:
            sftp, msg = self.get_sftp()
            if not sftp:
                return None, msg
            import io

            file_obj = io.BytesIO()
            sftp.getfo(remote_path, file_obj)
            file_obj.seek(0)
            return file_obj, "Download successful"
        except Exception as e:
            return None, str(e)

    def list_dir(self, path="."):
        if not self.client:
            return None, "Not connected"
        try:
            import stat
            from datetime import datetime

            sftp, msg = self.get_sftp()
            if not sftp:
                return None, msg
            files = []
            for attr in sftp.listdir_attr(path):
                # 권한을 -rwxr-xr-x 형식 및 3자리 숫자 형식으로 변환
                mode_str = stat.filemode(attr.st_mode)
                mode_oct = str(oct(attr.st_mode))[-3:]  # type: ignore

                # 날짜 형식화 (YYYY-MM-DD HH:mm)
                dt = datetime.fromtimestamp(attr.st_mtime)
                date_str = dt.strftime("%Y-%m-%d %H:%M")

                files.append(
                    {
                        "filename": attr.filename,
                        "size": attr.st_size,
                        "mode": mode_str,
                        "mode_oct": mode_oct,
                        "is_dir": (attr.st_mode & 0o40000) != 0,
                        "mtime": attr.st_mtime,
                        "date_str": date_str,
                    }
                )
            return files, "Success"
        except Exception as e:
            return None, str(e)

    def read_log(self, remote_path, lines=100):
        if not self.client:
            return None, "Not connected"
        try:
            quoted_path = shlex.quote(remote_path)
            cmd = f"tail -n {int(lines)} {quoted_path}"
            stdin, stdout, stderr = self.client.exec_command(cmd)  # type: ignore
            return stdout.read().decode("utf-8", errors="ignore"), "Success"
        except Exception as e:
            return None, str(e)

    def read_file_content(self, remote_path):
        """원격 파일의 전체 내용을 텍스트로 읽어옴"""
        if not self.client:
            return None, "Not connected"
        try:
            sftp, msg = self.get_sftp()
            if not sftp:
                return None, msg

            with sftp.open(remote_path, "r") as f:
                content = f.read().decode("utf-8", errors="ignore")
            return content, "Success"
        except Exception as e:
            return None, str(e)

    def write_file_content(self, remote_path, content):
        """텍스트 내용을 원격 파일에 저장함 (덮어쓰기)"""
        if not self.client:
            return False, "Not connected"
        try:
            sftp, msg = self.get_sftp()
            if not sftp:
                return False, msg

            # w 모드로 열어서 덮어쓰기
            with sftp.open(remote_path, "w") as f:
                f.write(content.encode("utf-8"))
            return True, "Success"
        except Exception as e:
            return False, str(e)

    def get_system_stats(self):
        """원격 서버의 CPU, RAM, Disk 사용량을 조회함 (최종 안정화 버전)"""
        if not self.client:
            return None

        try:
            # CPU (idle 추출 후 계산), RAM (free), Disk (df)
            # LC_ALL=C를 통해 영문 출력 강제 (로케일 이슈 방지)
            cmd = (
                "LC_ALL=C top -bn1 | grep 'Cpu(s)' | awk '{for(i=1;i<=NF;i++){if($i~/id/){print $(i-1)}}}' | head -1; "
                "free | grep Mem | awk '{print $3/$2 * 100.0}'; "
                "df / | awk 'NR==2 {print $5}' | sed 's/%//'"
            )
            stdin, stdout, stderr = self.client.exec_command(cmd)  # type: ignore
            raw_out = stdout.read().decode().strip()
            stats = raw_out.splitlines()

            if len(stats) >= 3:
                try:
                    # CPU idle 추출 (쉼표 제거 및 float 변환)
                    cpu_idle_raw = stats[0].replace(",", ".")
                    cpu_idle = float(cpu_idle_raw)

                    # RAM 및 Disk
                    ram_usage = float(stats[1])
                    disk_usage = float(stats[2])

                    return {
                        "cpu": float(f"{(100.0 - cpu_idle):.1f}"),
                        "ram": float(f"{ram_usage:.1f}"),
                        "disk": float(f"{disk_usage:.1f}"),
                    }
                except (ValueError, IndexError) as e:
                    print(f"Stats Parse Error: {e} | Raw: {raw_out}")
                    # 기본값 반환
                    return {"cpu": 0.0, "ram": 0.0, "disk": 0.0}
        except Exception as e:
            print(f"Stats Execution Error: {e}")
            return None
        return None

    def close(self):
        if self.sftp:
            try:
                self.sftp.close()  # type: ignore
            except Exception:
                pass
        if self.client:
            try:
                self.client.close()  # type: ignore
            except Exception:
                pass
