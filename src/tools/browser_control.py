import asyncio
from typing import Optional, Dict, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import base64
from io import BytesIO
from PIL import Image

class BrowserControl:
    """
    Singleton Selenium WebDriver wrapper for Grokputer.
    Headless mode for sandboxing. Async-friendly via asyncio.to_thread.
    """
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            async def init_instance():
                async with cls._lock:
                    if cls._instance is None:
                        cls._instance = super(BrowserControl, cls).__new__(cls)
                        cls._instance._initialized = False
                    return cls._instance
            # Note: __new__ is sync; full init in get_instance()
        return cls._instance

    @classmethod
    async def get_instance(cls) -> 'BrowserControl':
        if cls._instance is None or not cls._instance._initialized:
            cls._instance = super(BrowserControl, cls).__new__(cls)
            cls._instance._driver = None
            cls._instance._initialized = True
            await cls._instance._init_driver()
        return cls._instance

    async def _init_driver(self):
        """Initialize headless Chrome WebDriver."""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        service = Service(ChromeDriverManager().install())
        self._driver = webdriver.Chrome(service=service, options=options)
        self._wait = WebDriverWait(self._driver, 10)

    async def execute_async(self, func: callable, *args, **kwargs) -> Any:
        """Run Selenium action in thread pool for async compatibility."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)

    async def navigate(self, url: str) -> bool:
        """Navigate to URL."""
        def _navigate():
            self._driver.get(url)
            return self._driver.current_url == url
        return await self.execute_async(_navigate)

    async def find_element(self, by: str, value: str) -> Optional[Dict[str, Any]]:
        """Find element by locator (e.g., By.ID, 'search-box'). Returns dict with coords if found."""
        def _find():
            try:
                element = self._wait.until(EC.presence_of_element_located((getattr(By, by.upper()), value)))
                location = element.location
                size = element.size
                return {
                    'found': True,
                    'x': location['x'],
                    'y': location['y'],
                    'width': size['width'],
                    'height': size['height'],
                    'text': element.text
                }
            except (NoSuchElementException, TimeoutException):
                return {'found': False}
        return await self.execute_async(_find)

    async def click(self, by: str, value: str) -> bool:
        """Click element by locator."""
        def _click():
            try:
                element = self._wait.until(EC.element_to_be_clickable((getattr(By, by.upper()), value)))
                element.click()
                return True
            except (NoSuchElementException, TimeoutException):
                return False
        return await self.execute_async(_click)

    async def get_page_source(self) -> str:
        """Get page HTML source."""
        def _get_source():
            return self._driver.page_source
        return await self.execute_async(_get_source)

    async def get_text(self, by: str, value: str) -> Optional[str]:
        """Extract text from element."""
        def _get_text():
            try:
                element = self._driver.find_element(getattr(By, by.upper()), value)
                return element.text
            except NoSuchElementException:
                return None
        return await self.execute_async(_get_text)

    async def screenshot_page(self, full: bool = True) -> str:
        """Screenshot page (full or viewport). Returns base64 PNG."""
        def _screenshot():
            if full:
                # Full page screenshot (requires JS for scrolling)
                total_height = self._driver.execute_script("return document.body.scrollHeight")
                self._driver.set_window_size(1920, total_height)
            png = self._driver.get_screenshot_as_png()
            img = Image.open(BytesIO(png))
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return img_str
        return await self.execute_async(_screenshot)

    async def close(self):
        """Close browser."""
        if self._driver:
            def _close():
                self._driver.quit()
            await self.execute_async(_close)
            self._driver = None