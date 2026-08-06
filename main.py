import os
import json
import requests
import warnings
import random
import html
from datetime import datetime, timedelta
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from deep_translator import GoogleTranslator
# from gtts import gTTS # (ድምፅ ስለማንፈልግ ይሄንን ዘግተነዋል)

# Warning ማደፈን
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# --- CONFIGURATION & CHECKS ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@Mela_World_Sports")
CHANNEL_LINK = "https://t.me/Mela_World_Sports"
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    print("❌ ስህተት፡ TELEGRAM_BOT_TOKEN በ Environment Variables ውስጥ አልተገኘም!")
if not FOOTBALL_API_KEY:
    print("⚠️ ማስጠንቀቂያ፡ FOOTBALL_API_KEY አልተገኘም! የጨዋታ መርሃግብር ላይሰራ ይችላል።")

DB_FILE = "sent_news.json"

# ከተለያዩ ድህረ-ገጾች ለማምጣት List ተጠቅመናል (List of RSS Feeds)
NEWS_URLS = [
    "http://feeds.bbci.co.uk/sport/football/rss.xml",
    "http://feeds.archysport.com/football/rss.xml",
    "https://www.goal.com/feeds/en/news" # ተጨማሪ ምንጭ
]
TRANSFER_NEWS_URL = "http://feeds.bbci.co.uk/sport/football/gossip/rss.xml"

# --- TRANSLATION HELPER ---
def clean_text(text):
    if not text:
        return ""
    text = html.unescape(text)
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    return text

def translate_to_amharic(text):
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

def send_telegram_post(caption, image_url=None):
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️ BOT TOKEN ስለሌለ መልእክት መላክ አልተቻለም።")
        return False

    reply_markup = {
        "inline_keyboard": [[{"text": "📢 ቻናላችንን ይቀላቀሉ (Join)", "url": CHANNEL_LINK}]]
    }
    
    if image_url:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        payload = {
            "chat_id": TELEGRAM_CHANNEL_ID,
            "photo": image_url,
            "caption": caption,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(reply_markup)
        }
        res = requests.post(url, data=payload)
        if res.status_code == 200:
            return True

    url_text = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload_text = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": caption,
        "parse_mode": "HTML",
        "reply_markup": json.dumps(reply_markup)
    }
    res_text = requests.post(url_text, data=payload_text)
    return res_text.status_code == 200


# --- TRANSFER NEWS SCRAPER ---
def fetch_transfer_news():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(TRANSFER_NEWS_URL, headers=headers, timeout=10)
        if response.status_code != 200: return

        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")
        sent_news = load_sent_news()

        for item in items[:2]:
            title_tag = item.find("title")
            link_tag = item.find("guid") or item.find("link")
            desc_tag = item.find("description")

            title_en = title_tag.get_text(strip=True) if title_tag else ""
            link = link_tag.get_text(strip=True) if link_tag else ""
            description_en = desc_tag.get_text(strip=True) if desc_tag else ""

            if not link or len(title_en) < 10: continue

            if link not in sent_news:
                title_am = translate_to_amharic(title_en)
                content_am = translate_to_amharic(description_en)

                caption = (
                    f"🔄 <b>የተጫዋቾች ዝውውር እና ጭምጭምታዎች</b>\n\n"
                    f"📌 <b>{title_am}</b>\n\n"
                    f"{content_am}\n\n"
                    f"─────────────────\n"
                    f"🏆 <i>Mela World Sports</i>"
                )
                
                success = send_telegram_post(caption)
                if success:
                    print(f"✅ የዝውውር ዜና ተልኳል: {title_en}")
                    sent_news.append(link)
                    save_sent_news(sent_news)
                    break
    except Exception as e:
        print(f"የዝውውር ዜና ሲሰበሰብ ስህተት ተከሰተ: {e}")


# --- MAIN MULTI-SOURCE SCRAPER ---
def scrape_and_post():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    sent_news = load_sent_news()
    posts_sent_this_run = 0

    # በእያንዳንዱ ድህረ-ገጽ ላይ እየዞረ ዜና ያወጣል
    for feed_url in NEWS_URLS:
        if posts_sent_this_run >= 3: # በአንድ ጊዜ ከ3 ዜና በላይ እንዳይልክ (Spam እንዳይሆን)
            break
            
        try:
            response = requests.get(feed_url, headers=headers, timeout=10)
            if response.status_code != 200: continue

            soup = BeautifulSoup(response.content, "xml")
            items = soup.find_all("item")

            for item in items:
                title_tag = item.find("title")
                link_tag = item.find("guid") or item.find("link")
                desc_tag = item.find("description")

                title_en = title_tag.get_text(strip=True) if title_tag else ""
                link = link_tag.get_text(strip=True) if link_tag else ""
                description_en = desc_tag.get_text(strip=True) if desc_tag else ""
                
                image_url = None
                media_thumb = item.find("media:thumbnail") or item.find("media:content")
                if media_thumb and media_thumb.get("url"):
                    image_url = media_thumb["url"]

                if not link or len(title_en) < 10: continue

                if link not in sent_news:
                    title_am = translate_to_amharic(title_en)
                    content_am = translate_to_amharic(description_en)
                    
                    caption_limit = 700
                    if len(content_am) > caption_limit:
                        content_am = content_am[:caption_limit] + "..."

                    caption = (
                        f"🔥 <b>ትኩስ የስፖርት ዜና</b>\n\n"
                        f"⚽ <b>{title_am}</b>\n\n"
                        f"{content_am}\n\n"
                        f"─────────────────\n"
                        f"📌 <i>ለፈጣን መረጃ ቻናላችንን ይቀላቀሉ!</i>"
                    )
                    
                    success = send_telegram_post(caption, image_url)
                    
                    if success:
                        print(f"✅ ዜና ተልኳል: {title_en}")
                        sent_news.append(link)
                        save_sent_news(sent_news)
                        posts_sent_this_run += 1
                        break # ከአንድ ምንጭ አንድ ዜና ብቻ ወስዶ ወደ ቀጣዩ ድህረ-ገጽ ያልፋል
                        
        except Exception as e:
            print(f"ከ {feed_url} መረጃ ማውጣት አልተቻለም: {e}")

# (ሌሎቹን ፋንክሽኖች እንደ fetch_today_matches, fetch_top_standings, እና fetch_top_scorers አላጠፋኋቸውም፣ እንዳሉ ይጠቅማሉ)

if __name__ == "__main__":
    print("🚀 ቦቱ ስራ ጀምሯል...")
    
    scrape_and_post()       # 1. ዜና ከተለያዩ ድረ-ገጾች ያመጣል
    fetch_transfer_news()   # 2. የዝውውር ዜና ያመጣል
    
    # የጥያቄ (Quiz) እና የድምፅ (Audio) ፋንክሽኖችን እንዳይሰሩ አድርገናቸዋል (Commented out)
    # send_daily_quiz() 
    # send_audio_summary(...)
    
    # የ API Key ካለህ እነዚህን ከታች ያሉትን "#" በማጥፋት መጠቀም ትችላለህ
    # fetch_today_matches()
    # fetch_top_standings()
    # fetch_top_scorers()
