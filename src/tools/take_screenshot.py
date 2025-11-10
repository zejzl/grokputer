import pyautogui
screenshot = pyautogui.screenshot()
screenshot.save('./vault/screenshot.png')
print("Screenshot saved to ./vault/screenshot.png")