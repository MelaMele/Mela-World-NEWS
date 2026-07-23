import os
import json
import re
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "8802119418:AAF13aJKhIw6HboE7O1t0F2Ow4WUkZGmQF8"
TELEGRAM_CHANNEL_ID = "@Mela_World_NEWS"

DB_FILE = "sent_news.json"
NEWS_URL = "https://news.opera.com/" 

# --- TRANSLATION HELPER ---

def clean_text(text):
    """የቴሌግራም HTML format እንዳይበላሽ ምልክቶችን ማጽጃ"""
    if not text:
        return ""
    # HTML tag ሊመስሉ የሚችሉ ምልክቶችን መተካት
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    return text

def translate_to_amharic(text):
    """ጽሑፎችን ከእንግሊዝኛ ወደ አማርኛ የሚተረጉም ፋንክሽን"""
    if not text:
        return ""
    try:
        translated = GoogleTranslator(source='auto', target='am').translate(text)
        return clean_text(translated)
    except Exception as e:
        print(f"የትርጉም ስህተት፡ {e}")
        return clean_text(text)

# --- HELPER FUNCTIONS ---

def load_sent_news():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_sent_news(sent_list):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(sent_list, f, ensure_ascii=False, indent=2)

def fetch_article_details(article_url):
    """የዜናውን ሙሉ ጽሑፍ እና ምስል ያወጣል"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    image_url = None
    content = ""
    
    try:
        res = requests.get(article_url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            
            # ምስል መፈለግ
            img_tag = soup.find("img")
            if img_tag and img_tag.get("src"):
                src = img_tag["src"]
                if src.startswith("http"):
                    image_url = src
                elif src.startswith("//"):
                    image_url = "https:" + src

            # የጽሑፍ አንቀጾችን መፈለግ
            paragraphs = soup.find_all("p")
            full_text = []
            
            for p in paragraphs:
                txt = p.get_text().strip()
                if len(txt) > 25 and not txt.startswith("©"):
                    full_text.append(txt)
            
            content = "\n\n".join(full_text[:3])
            
    except Exception as e:
        print(f"የዜናውን ዝርዝር በማውረድ ላይ ስህተት፡ {e}")
    
    return content, image_url

def send_telegram_post(title_am, content_am, image_url):
    """በአማርኛ የተተረጎመውን ዜና ወደ ቴሌግራም ይልካል"""
    
    caption_limit = 800
    if len(content_am) > caption_limit:
        content_am = content_am[:caption_limit] + "..."

    if not content_am:
        content_am = "ለተጨማሪ መረጃ ቻናላችንን ይከታተሉ።"

    caption = (
        f"<b>📰 {title_am}</b>\n\n"
        f"{content_am}\n\n"
        f"─────\n"
        f"📌 <i>አዳዲስ ዜናዎችን ለማግኘት ቻናላችንን ይከተሉ!</i>"
    )
    
    # 1. ምስል ካለ በምስል ለመላክ መሞከር
    if image_url:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        payload = {
            "chat_id": TELEGRAM_CHANNEL_ID,
            "photo": image_url,
            "caption": caption,
            "parse_mode": "HTML"
        }
        res = requests.post(url, data=payload)
        if res.status_code == 200:
            return True
        else:
            print(f"የምስል መላክ አልተሳካም ({res.status_code}): {res.text} | በጽሑፍ ብቻ በመሞከር ላይ...")

    # 2. ምስል ከሌለ ወይም ምስሉ ካልሰራ በጽሑፍ ብቻ መላክ
    url_text = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload_text = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": caption,
        "parse_mode": "HTML"
    }
    res_text = requests.post(url_text, data=payload_text)
    if res_text.status_code == 200:
        return True
    else:
        print(f"የጽሑፍ መላክ ስህተት ({res_text.status_code}): {res_text.text}")
        return False

# --- MAIN SCRAPER ---

def scrape_and_post():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    IGNORED_TITLES = ["privacy statement", "terms of service", "about us", "cookie policy", "contact us"]

    try:
        response = requests.get(NEWS_URL, headers=headers)
        if response.status_code != 200:
            print(f"ድረ-ገጹን መክፈት አልተቻለም። Status Code: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, "html.parser")
        sent_news = load_sent_news()
        
        articles = soup.find_all("a", href=True)

        count = 0
        for article in articles:
            title_en = article.get_text().strip()
            link = article["href"]

            if not link.startswith("http"):
                link = "https://news.opera.com" + link

            # የዜና ርዕስ ከ 20 አකුረፎች ያነሰ ከሆነ ወይም የህግ ገፅ ከሆነ ማለፍ
            if len(title_en) < 20 or any(ignored in title_en.lower() for ignored in IGNORED_TITLES):
                continue

            if link not in sent_news:
                print(f"\n📌 አዲስ ዜና ተገኝቷል (EN): {title_en}")
                
                full_content_en, image_url = fetch_article_details(link)
                
                print("ወደ አማርኛ በመተርጎም ላይ...")
                title_am = translate_to_amharic(title_en)
                content_am = translate_to_amharic(full_content_en) if full_content_en else ""
                
                success = send_telegram_post(title_am, content_am, image_url)
                
                sent_news.append(link)
                save_sent_news(sent_news)

                if success:
                    print("✅ ዜናው በአማርኛ ተተርጉሞ ወደ ቴሌግራም ተልኳል!")
                    count += 1
                else:
                    print("❌ ዜናውን ወደ ቴሌግራም መላክ አልተቻለም።")
                    
                if count >= 2:
                    break

        if count == 0:
            print("አዲስ ያልተላከ ዜና አልተገኘም።")

    except Exception as e:
        print(f"Scraping በሚደረግበት ወቅት ስህተት ተከሰተ: {e}")

if __name__ == "__main__":
    scrape_and_post()
