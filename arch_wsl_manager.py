import subprocess
import time

def run_in_arch(command):
    """Run a command in Arch Linux WSL distribution."""
    try:
        result = subprocess.run(['wsl', '-d', 'archlinux', '-e', 'bash', '-c', command], 
                                capture_output=True, text=True, check=True)
        print(f"Arch command '{command}' output:\n{result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command '{command}': {e.stderr}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("Starting Arch WSL Manager.")
    print("This will update pacman and pull git in a specified repo every 300 seconds.")
    print("Adjust repo_path below to your git repo inside Arch.")
    print("Press Ctrl+C to stop.")
    
    repo_path = "/home/user/grok-repo"  # CHANGE THIS to your actual repo path in Arch, e.g., /home/$USER/your-repo
    
    try:
        while True:
            # Ensure Arch is running (wsl will start it if stopped)
            if run_in_arch("echo 'Arch WSL is up and running'"):
                # Update system with pacman
                if run_in_arch("sudo pacman -Syu --noconfirm"):
                    print("Pacman update successful.")
                else:
                    print("Pacman update failed (may need sudo config for no password).")
                
                # Git pull in the repo
                git_cmd = f"cd '{repo_path}' && git pull origin main || git pull origin master"
                if run_in_arch(git_cmd):
                    print("Git pull successful.")
                else:
                    print("Git pull failed (check repo path or git setup).")
            else:
                print("Failed to connect to Arch WSL.")
            
            print("Cycle complete. Sleeping 300 seconds...")
            time.sleep(300)
    except KeyboardInterrupt:
        print("\nStopped by user.")
        print("To stop Arch WSL: wsl --terminate archlinux")