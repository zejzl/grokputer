import win32gui
import win32con
import pyautogui
import time

def find_git_cli_windows():
    windows = []
    def enum_callback(hwnd, windows_list):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if 'git_cli' in title.lower():
                windows_list.append((hwnd, title))
        return True
    win32gui.EnumWindows(enum_callback, windows)
    return windows

if __name__ == "__main__":
    print("Starting auto-approver. Looking for windows with 'git_cli' in title.")
    print("Press Ctrl+C to stop.")
    
    try:
        while True:
            git_windows = find_git_cli_windows()
            if not git_windows:
                print("No git_cli windows found. Sleeping 300s...")
                time.sleep(300)
                continue
            
            print(f"Found {len(git_windows)} git_cli windows. Cycling through them...")
            for hwnd, title in git_windows:
                print(f"Activating window: {title}")
                # Restore if minimized
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                # Bring to front
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(1)  # Give time to focus
                # Type the message
                pyautogui.typewrite("approved, pls go on<3")
                pyautogui.press('enter')
                time.sleep(0.5)  # Short pause before next window
            
            print("Cycle complete. Sleeping 300 seconds...")
            time.sleep(300)
    except KeyboardInterrupt:
        print("\nStopped by user.")