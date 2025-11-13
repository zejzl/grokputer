import subprocess
import sys
from pathlib import Path

with open("main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find if __name__ == '__main__':
insert_pos = -1
for i, line in enumerate(lines):
    if "if __name__ == '__main__' :" in line:
        insert_pos = i
        break

if insert_pos != -1:
    docker_check = """def check_and_start_docker():
    \"\"\"
    Check if Docker Compose services are running, start if not.
    \"\"\"
    try:
        # Try new docker compose
        result = subprocess.run(['docker', 'compose', 'ps'], capture_output=True, text=True, timeout=10)
        if result.returncode != 0 or 'Up' not in result.stdout:
            print("[DOCKER] Services not running, starting docker-compose up -d...")
            subprocess.run(['docker', 'compose', 'up', '-d'], check=True)
            print("[DOCKER] Started services.")
        else:
            print("[DOCKER] Services already running.")
    except FileNotFoundError:
        # Fallback to old docker-compose
        try:
            result = subprocess.run(['docker-compose', 'ps'], capture_output=True, text=True, timeout=10)
            if result.returncode != 0 or 'Up' not in result.stdout:
                print("[DOCKER] Services not running, starting docker-compose up -d...")
                subprocess.run(['docker-compose', 'up', '-d'], check=True)
                print("[DOCKER] Started services.")
            else:
                print("[DOCKER] Services already running.")
        except Exception as e:
            print(f"[DOCKER] Error checking/starting services: {e}")
            print("[INFO] Continuing without Docker services.")

# Call before main
check_and_start_docker()

if __name__ == '__main__':
    main()
"""
    # Replace the if __name__ block
    lines[insert_pos] = docker_check.splitlines()[0]  # def check...
    # Insert the rest before if __name__
    for line in docker_check.splitlines()[1:-1]:  # Exclude first and last
        lines.insert(insert_pos + 1, line + "\\n")
    # The last line is already there

    with open("main.py", "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("Docker check added to main.py.")
