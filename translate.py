import os
import re
import shutil
import requests
import time

# ------------------------------
# CONFIG
# ------------------------------

SOURCE_LANG = "zh"
TARGET_LANG = "en"
MAKE_BACKUPS = True

translation_cache = {}
MAX_RETRIES = 3
RETRY_DELAY = 2
api_dead = False

# ------------------------------
# TRANSLATE FUNCTION (MyMemory)
# ------------------------------

def translate_text(text):
    global api_dead
    text = text.strip()
    if not text or api_dead:
        return text

    if text in translation_cache:
        return translation_cache[text]

    for attempt in range(1, MAX_RETRIES+1):
        try:
            url = "https://api.mymemory.translated.net/get"
            params = {"q": text, "langpair": f"{SOURCE_LANG}|{TARGET_LANG}"}
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                data = r.json()
                translated = data.get("responseData", {}).get("translatedText", text)
                # Check if quota exceeded
                if "YOU USED ALL AVAILABLE FREE TRANSLATIONS" in translated:
                    print("\n🚨 MyMemory daily free quota reached. Translation stopped.")
                    api_dead = True
                    return text
                translation_cache[text] = translated
                return translated
            print(f"⚠️ MyMemory error (attempt {attempt}): {r.text}")
        except Exception as e:
            print(f"⚠️ Request exception (attempt {attempt}): {e}")
        time.sleep(RETRY_DELAY)

    print(f"❌ Translation failed for: {text}")
    return text

# ------------------------------
# TEXT EXTRACTION
# ------------------------------

CHINESE_RE = re.compile(r"[\u4e00-\u9fff]+")

def extract_chinese(text):
    return list(dict.fromkeys(CHINESE_RE.findall(text)))

# ------------------------------
# FILE PROCESSOR
# ------------------------------

TEXT_EXTS = {
    ".txt", ".json", ".toml", ".cfg", ".ini",
    ".zs", ".snbt", ".mcfunction", ".kubejs"
}

def process_file(path, backup_root):
    print(f"📄 Processing: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
    except:
        print("❌ Cannot read file.")
        return

    if MAKE_BACKUPS:
        backup_path = os.path.join(backup_root, os.path.relpath(path))
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(path, backup_path)

    chinese_phrases = extract_chinese(data)
    if not chinese_phrases:
        print("➡ No Chinese found.")
        return

    translated_data = data
    for phrase in chinese_phrases:
        translated = translate_text(phrase)
        translated_data = translated_data.replace(phrase, translated)
        if api_dead:
            print("⚠️ Stopping further translations due to MyMemory quota.")
            break

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(translated_data)
    except:
        print("❌ Failed to write file.")
        return

    print("✔ File translated.")

# ------------------------------
# DIRECTORY SCAN
# ------------------------------

def process_directory(folder):
    print(f"\n🔍 Scanning folder: {folder}")
    backup_root = os.path.join(folder, "_backup")
    files_to_process = []

    for root, dirs, files in os.walk(folder):
        if "_backup" in root:
            continue
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext in TEXT_EXTS:
                files_to_process.append(os.path.join(root, filename))

    print(f"\n📦 Found {len(files_to_process)} files.\n")

    # Sequential processing
    for f in files_to_process:
        process_file(f, backup_root)
        if api_dead:
            print("⚠️ Quota reached, stopping script.")
            break

    print("\n✅ Translation complete. Backups stored in _backup folder.")

# ------------------------------
# MAIN
# ------------------------------

if __name__ == "__main__":
    folder = input("Enter modpack folder path: ").strip()
    if not os.path.isdir(folder):
        print("❌ Invalid folder.")
        exit()
    process_directory(folder)
