import os
import json
import requests
import warnings
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from deep_translator import GoogleTranslator

# Warning መልእክቱ እንዳይታይ ማደፈን (Suppress Warning)
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "8802119418:AAF13aJKhIw6HboE7O1t0F2Ow4WUkZGmQF8"
TELEGRAM_CHANNEL_ID = "@Mela_World_NEWS"

DB_FILE = "sent_news.json"

# የስፖርት ዜና ምንጭ (BBC Sport RSS Feed)
NEWS_URL = "http://feeds.bbci.co.uk/sport/football/rss.xml"

# --- TRANSLATION HELPER ---

def clean_text(text):
    """የቴሌግራም HTML format እንዳይበላሽ ምልክቶችን ማጽጃ"""
    if not text:
        return ""
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

def send_telegram_post(title_am, content_am, image_url):
    """በአማርኛ የተተረጎመውን የስፖርት ዜና ወደ ቴሌግራም ይልካል"""
    
    caption_limit = 800
    if len(content_am) > caption_limit:
        content_am = content_am[:caption_limit] + "..."

    if not content_am:
        content_am = "ለተጨማሪ የስፖርት መረጃዎች ቻናላችንን ይከታተሉ።"

    # የስፖርት ዲዛይን ያለው መልእክት
    caption = (
        f"<b>⚽ {title_am}</b>\n\n"
        f"{content_am}\n\n"
        f"─────\n"
        f"🏆 <i>አዳዲስ እና ትኩስ የስፖርት ዜናዎችን ለማግኘት ቻናላችንን ይቀላቀሉ!</i>"
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

    # 2. ምስል ከሌለ በጽሑፍ ብቻ መላክ
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

    try:
        response = requests.get(NEWS_URL, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"ምንጩን መክፈት አልተቻለም። Status Code: {response.status_code}")
            return

        # HTML parser በመጠቀም RSS መረጃን ማጽዳት
        soup = BeautifulSoup(response.content, "html.parser")
        items = soup.find_all("item")
        sent_news = load_sent_news()

        count = 0
        for item in items:
            # html.parser RSS ታጎችን በትንሹ የፊደል ለውጥ ሊያነበው ስለሚችል በጥንቃቄ መፈለግ
            title_tag = item.find("title")
            
            # BBC RSS በ html.parser ውስጥ link ወይም guid ሆኖ ሊገኝ ይችላል
            link_tag = item.find("guid") or item.find("link")
            desc_tag = item.find("description")

            title_en = title_tag.get_text(strip=True) if title_tag else ""
            link = link_tag.get_text(strip=True) if link_tag else ""
            description_en = desc_tag.get_text(strip=True) if desc_tag else ""
            
            # ምስል መፈለግ
            image_url = None
            media_thumb = item.find("media:thumbnail") or item.find("media:content")
            if media_thumb and media_thumb.get("url"):
                image_url = media_thumb["url"]

            if not link or len(title_en) < 10:
                continue

            if link not in sent_news:
                print(f"\n📌 አዲስ የስፖርት ዜና ተገኝቷል (EN): {title_en}")
                
                print("ወደ አማርኛ በመተርጎም ላይ...")
                title_am = translate_to_amharic(title_en)
                content_am = translate_to_amharic(description_en)
                
                success = send_telegram_post(title_am, content_am, image_url)
                
                sent_news.append(link)
                save_sent_news(sent_news)

                if success:
                    print("✅ የስፖርት ዜናው በአማርኛ ተተርጉሞ ተልኳል!")
                    count += 1
                else:
                    print("❌ ዜናውን መላክ አልተሳካም።")
                    
                if count >= 3:  # በአንድ ዙር 3 አዳዲስ የስፖርት ዜናዎችን ይልካል
                    break

        if count == 0:
            print("አዲስ ያልተላከ የስፖርት ዜና አልተገኘም።")

    except Exception as e:
        print(f"Scraping በሚደረግበት ወቅት ስህተት ተከሰተ: {e}")

if __name__ == "__main__":
    scrape_and_post()
