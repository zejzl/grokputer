import os
import json
from pathlib import Path
import time
import re  # For potential text cleaning

# Optional: If Redis is used for OCR results, uncomment and install redis
# import redis
# r = redis.Redis(host='localhost', port=6379, db=0)

def extract_vault_metadata(vault_path='.', output_file='vault_metadata.json', image_extensions=['.jpg', '.jpeg', '.png', '.gif', '.bmp']):
    """
    Traverse vault subdirectories, extract metadata for image files.
    Includes file sizes, timestamps, and OCR text (assumed from corresponding _ocr.txt files or logs).
    Outputs to JSON for LoRA training integration. For LoRA, formats low-conf examples as noisy/clean pairs if available.
    """
    data = []
    lora_additions = []
    current_dataset_size = 13  # From previous batch; update as needed
    
    for root, dirs, files in os.walk(vault_path):
        for file in files:
            if any(file.lower().endswith(ext) for ext in image_extensions):
                full_path = os.path.join(root, file)
                stat = os.stat(full_path)
                base_name = Path(file).stem
                
                # OCR text extraction (from file or log)
                ocr_text = ''
                conf = 0.0
                ocr_file = os.path.join(root, f"{base_name}_ocr.txt")
                low_conf_log = 'lora_low_conf.log'
                
                if os.path.exists(ocr_file):
                    try:
                        with open(ocr_file, 'r') as f:
                            lines = f.read().strip().split('\n')
                            ocr_text = lines[0] if lines else ''
                            # Assume second line is conf if present
                            if len(lines) > 1:
                                match = re.search(r'conf(?:idence)?:?\s*(\d+(?:\.\d+)?)%?', lines[1], re.I)
                                if match:
                                    conf = float(match.group(1))
                    except Exception as e:
                        ocr_text = f"OCR read error: {e}"
                
                # Check low-conf log for this file
                if os.path.exists(low_conf_log):
                    try:
                        with open(low_conf_log, 'r') as f:
                            content = f.read()
                            if base_name in content or file in content:
                                # Extract noisy example for LoRA
                                # Assume format: file: noisy_text (conf XX%)
                                match = re.search(rf'{re.escape(file)}.*?(gibberish|noisy).*?conf.*?(\d+)%?', content, re.I | re.S)
                                if match:
                                    noisy_text = match.group(1) or 'noisy extract'
                                    conf = float(match.group(2))
                                    lora_additions.append({
                                        'prompt': f"Noisy OCR from {file}: {noisy_text}",
                                        'completion': "Cleaned or corrected text",  # Placeholder; manual or AI clean
                                        'confidence': conf,
                                        'source': file
                                    })
                    except Exception as e:
                        print(f"Error reading log: {e}")
                
                entry = {
                    'path': full_path,
                    'filename': file,
                    'size_bytes': stat.st_size,
                    'modified_time': time.ctime(stat.st_mtime),
                    'ocr_text': ocr_text,
                    'confidence': conf,
                    'subdir': os.path.relpath(root, vault_path)
                }
                data.append(entry)
    
    # Write metadata JSON
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Extracted metadata for {len(data)} files to {output_file}")
    
    # Update LoRA dataset if additions
    if lora_additions:
        lora_file = 'lora_dataset.json'
        try:
            existing_lora = []
            if os.path.exists(lora_file):
                with open(lora_file, 'r') as f:
                    existing_lora = json.load(f)
            existing_lora.extend(lora_additions)
            with open(lora_file, 'w') as f:
                json.dump(existing_lora, f, indent=4)
            new_size = len(existing_lora)
            print(f"Added {len(lora_additions)} LoRA examples. Dataset now at {new_size}/50 ({new_size/50*100:.1f}% complete).")
        except Exception as e:
            print(f"LoRA update error: {e}")
    
    return data, lora_additions

if __name__ == "__main__":
    # Run on current dir or specify 'vault' subdir
    extract_vault_metadata(vault_path='.')  # Change to 'vault' if subdir exists