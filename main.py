import os
import json
import requests
import warnings
import random
import html
from datetime import datetime, timedelta
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from deep_translator import GoogleTranslator

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

# --- አጠቃላይ የስፖርት ዜናዎች ምንጭ (All Sports RSS Feeds) ---
NEWS_URLS = [
    "http://feeds.bbci.co.uk/sport/rss.xml",             # BBC Sport (አጠቃላይ ስፖርት)
    "https://www.skysports.com/rss/12010",               # Sky Sports News (አጠቃላይ)
    "https://www.espn.com/espn/rss/news",                # ESPN News (የተለያዩ ስፖርቶች)
    "https://www.theguardian.com/sport/rss",             # The Guardian Sport
    "http://feeds.bbci.co.uk/sport/football/rss.xml",    # BBC Football
    "https://www.sportskeeda.com/feed",                  # Sportskeeda (Multi-sport)
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
    # እስከ 500 የሚደርሱ የተላኩ ሊንኮችን ብቻ ይዞ የፋይሉን መጠን ለመቀነስ
    if len(sent_list) > 500:
        sent_list = sent_list[-500:]
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
        try:
            res = requests.post(url, data=payload, timeout=10)
            if res.status_code == 200:
                return True
        except Exception as e:
            print(f"ምስል ሲላክ ስህተት፡ {e}")

    # ምስል ከሌለ ወይም ምስሉ ካልተላከ ፅሁፉን ብቻ ይልካል
    url_text = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload_text = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": caption,
        "parse_mode": "HTML",
        "reply_markup": json.dumps(reply_markup)
    }
    res_text = requests.post(url_text, data=payload_text, timeout=10)
    return res_text.status_code == 200


# --- TRANSFER NEWS SCRAPER ---
def fetch_transfer_news():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(TRANSFER_NEWS_URL, headers=headers, timeout=10)
        if response.status_code != 200: 
            return

        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")
        sent_news = load_sent_news()

        for item in items[:1]:  # በየሩጫው ቢበዛ 1 የዝውውር ዜና ብቻ እንዲልክ
            title_tag = item.find("title")
            link_tag = item.find("guid") or item.find("link")
            desc_tag = item.find("description")

            title_en = title_tag.get_text(strip=True) if title_tag else ""
            link = link_tag.get_text(strip=True) if link_tag else ""
            description_en = desc_tag.get_text(strip=True) if desc_tag else ""

            if not link or len(title_en) < 10: 
                continue

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


# --- MAIN MULTI-SPORT SCRAPER ---
def scrape_and_post():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    sent_news = load_sent_news()
    posts_sent_this_run = 0

    # ምንጮቹን በዘፈቀደ በማደባለቅ ከተለያዩ የስፖርት አይነቶች ዜናዎች እንዲመጡ ይደረጋል
    shuffled_urls = NEWS_URLS.copy()
    random.shuffle(shuffled_urls)

    for feed_url in shuffled_urls:
        if posts_sent_this_run >= 3:  # በአንድ ጊዜ ከ3 አጠቃላይ ዜና በላይ እንዳይልክ
            break
            
        try:
            response = requests.get(feed_url, headers=headers, timeout=10)
            if response.status_code != 200: 
                continue

            soup = BeautifulSoup(response.content, "xml")
            items = soup.find_all("item")

            # ዜናዎቹን በዘፈቀደ ማውጣት
            random.shuffle(items)

            for item in items:
                title_tag = item.find("title")
                link_tag = item.find("guid") or item.find("link")
                desc_tag = item.find("description")

                title_en = title_tag.get_text(strip=True) if title_tag else ""
                link = link_tag.get_text(strip=True) if link_tag else ""
                description_en = desc_tag.get_text(strip=True) if desc_tag else ""
                
                image_url = None
                media_thumb = item.find("media:thumbnail") or item.find("media:content") or item.find("enclosure")
                if media_thumb and media_thumb.get("url"):
                    image_url = media_thumb["url"]

                if not link or len(title_en) < 10: 
                    continue

                if link not in sent_news:
                    title_am = translate_to_amharic(title_en)
                    content_am = translate_to_amharic(description_en)
                    
                    caption_limit = 700
                    if len(content_am) > caption_limit:
                        content_am = content_am[:caption_limit] + "..."

                    caption = (
                        f"🔥 <b>ትኩስ የስፖርት ዜና</b>\n\n"
                        f"🏆 <b>{title_am}</b>\n\n"
                        f"{content_am}\n\n"
                        f"─────────────────\n"
                        f"📌 <i>ለፈጣን መረጃ ቻናላችንን ይቀላቀሉ!</i>"
                    )
                    
                    success = send_telegram_post(caption, image_url)
                    
                    if success:
                        print(f"✅ አጠቃላይ የስፖርት ዜና ተልኳል: {title_en}")
                        sent_news.append(link)
                        save_sent_news(sent_news)
                        posts_sent_this_run += 1
                        break  # ከአንድ ምንጭ 1 ዜና እንደላከ ወደ ቀጣዩ ምንጭ ይሻገራል
                        
        except Exception as e:
            print(f"ከ {feed_url} መረጃ ማውጣት አልተቻለም: {e}")

if __name__ == "__main__":
    print("🚀 ቦቱ ስራ ጀምሯል...")
    
    # 1. አጠቃላይ የስፖርት ዜናዎችን ያመጣል (እግር ኳስ፣ ባስኬትቦል፣ ቴኒስ፣ ወዘተ)
    scrape_and_post()       
    
    # 2. የዝውውር ዜና (በምጣኔ ይላካል)
    fetch_transfer_news()
