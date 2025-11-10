import os
import time
import subprocess

# Launch Notepad from WSL (calls Windows)
print("Opening Notepad from WSL...")
subprocess.run(['powershell.exe', '-Command', 'Start-Process notepad.exe'], shell=True)
time.sleep(3)  # Wait for focus

# Type text using PowerShell SendKeys (Windows .NET)
subprocess.run(['powershell.exe', '-Command', '[System.Windows.Forms.SendKeys]::SendWait(\"hello word, why?\")'], shell=True)
print("Text typed: 'hello word, why?' via Windows bridge")