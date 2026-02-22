import subprocess
import os
import sys


def run_audit():
    print("=== PTSS Security Audit (Bandit & Pip-audit) ===")

    # 결과가 저장될 디렉토리 (이미 .gitignore에 등록되어 있음)
    test_dir = "tests"
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)

    bandit_output = os.path.join(test_dir, "bandit_report.txt")
    pip_audit_output = os.path.join(test_dir, "pip_audit_report.txt")

    # 1. Bandit Scan
    print(f"Running Bandit scan... (Output: {bandit_output})")
    try:
        # 가상환경의 bandit 실행 (Windows 경로 고려)
        bandit_path = os.path.join(".venv_test", "Scripts", "bandit")
        if not os.path.exists(bandit_path + ".exe"):
            bandit_path = "bandit"  # fallback to system

        subprocess.run(
            [
                bandit_path,
                "-r",
                ".",
                "-x",
                "./.venv_test,./tests",
                "-f",
                "txt",
                "-o",
                bandit_output,
            ],
            check=False,
        )
        print("[V] Bandit report generated.")
    except Exception as e:
        print(f"[X] Bandit failed: {e}")

    # 2. Pip-audit
    print(f"Running Pip-audit... (Output: {pip_audit_output})")
    try:
        pip_audit_path = os.path.join(".venv_test", "Scripts", "pip-audit")
        if not os.path.exists(pip_audit_path + ".exe"):
            pip_audit_path = "pip-audit"

        with open(pip_audit_output, "w", encoding="utf-8") as f:
            subprocess.run(
                [pip_audit_path],
                stdout=f,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
        print("[V] Pip-audit report generated.")
    except Exception as e:
        print(f"[X] Pip-audit failed: {e}")

    print(
        "\n[INFO] All security reports are saved in 'tests/' directory and will not be tracked by Git."
    )


if __name__ == "__main__":
    run_audit()
