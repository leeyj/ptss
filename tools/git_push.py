import subprocess
import os
import sys


def run_git_command(command):
    print(f"Running: git {' '.join(command)}")
    try:
        result = subprocess.run(
            ["git"] + command, check=True, capture_output=True, text=True
        )
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        return False
    return True


def main():
    repo_url = "https://github.com/leeyj/ptss.git"

    # 1. Check if git is initialized
    if not os.path.exists(".git"):
        print("Initializing git repository...")
        if not run_git_command(["init"]):
            return

    # 2. Add remote origin if it doesn't exist
    print("Checking remote origin...")
    try:
        remotes = subprocess.check_output(["git", "remote"]).decode().split()
        if "origin" not in remotes:
            run_git_command(["remote", "add", "origin", repo_url])
        else:
            # Update remote if it exists but is different
            run_git_command(["remote", "set-url", "origin", repo_url])
    except subprocess.CalledProcessError:
        run_git_command(["remote", "add", "origin", repo_url])

    # 3. Add files
    print("Adding files (respecting .gitignore)...")
    if not run_git_command(["add", "."]):
        return

    # 4. Commit
    print("Committing changes...")
    # Check if there are changes to commit
    status = subprocess.check_output(["git", "status", "--porcelain"]).decode()
    if not status:
        print("No changes to commit.")
    else:
        commit_msg = "v1.2.0: Integrated Terminal Settings, Snippets, Persistence and UI Enhancements"
        run_git_command(["commit", "-m", commit_msg])

    # 5. Push
    print("\nPushing to GitHub (main branch)...")
    print(
        "Note: If this hangs, you may need to enter your credentials in a separate terminal."
    )
    # Forcing main branch name
    run_git_command(["branch", "-M", "main"])

    # Use -u to set upstream
    run_git_command(["push", "-u", "origin", "main"])


if __name__ == "__main__":
    main()
