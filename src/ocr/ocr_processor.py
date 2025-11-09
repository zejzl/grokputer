import pytesseract
from PIL import Image
import cv2
import asyncio
import os
import zlib  # For TOON compression

class OCRProcessor:
    def __init__(self, tesseract_path=None):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path or '/usr/bin/tesseract'

    def preprocess_image(self, img_path):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        preprocessed_path = img_path.replace('.png', '_preprocessed.png').replace('.jpg', '_preprocessed.jpg')
        cv2.imwrite(preprocessed_path, img)
        return preprocessed_path

    def detect_text_regions(self, img_path):
        img = cv2.imread(img_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        regions = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w > 50 and h > 10:
                cropped = img[y:y+h, x:x+w]
                region_path = img_path.replace('.png', f'_region_{len(regions)}.png')
                cv2.imwrite(region_path, cropped)
                regions.append((x, y, w, h, region_path))
        return regions

    def retry_preprocess(self, img_path, method: str = "deskew"):
        img = cv2.imread(img_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if method == "deskew":
            coords = cv2.findNonZero(gray)
            if coords is not None:
                angle = cv2.minAreaRect(coords)[-1]
                if angle < -45:
                    angle = -(90 + angle)
                else:
                    angle = -angle
                (h, w) = img.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                img = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        elif method == "adaptive":
            gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        retry_path = img_path.replace('.png', '_retry.png')
        cv2.imwrite(retry_path, img)
        return retry_path

    def extract_text(self, img_path, lang='eng', conf_threshold=80):
        preprocessed = self.preprocess_image(img_path)
        data = pytesseract.image_to_data(Image.open(preprocessed), lang=lang, output_type=pytesseract.Output.DICT)
        text = pytesseract.image_to_string(Image.open(preprocessed), lang=lang)
        confs = [int(c) for c in data['conf'] if int(c) > 0]
        conf = sum(confs) / len(confs) if confs else 0
        if conf < conf_threshold:
            return None, conf
        return text.strip(), conf

    async def async_extract(self, img_path, lang='eng', conf_threshold=80):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.extract_text, img_path, lang, conf_threshold)

    async def recover_extract(self, img_path, max_retries: int = 3):
        for i in range(max_retries):
            text, conf = await self.async_extract(img_path)
            if conf >= 80 or i == max_retries - 1:
                return text, conf
            retry_path = self.retry_preprocess(img_path, method=["otsu", "adaptive", "deskew"][i % 3])
            img_path = retry_path
        return None, 0

if __name__ == "__main__":
    processor = OCRProcessor()
    text, conf = asyncio.run(processor.async_extract("test.png"))
    print(f"Extracted: {text}, Conf: {conf}%")
