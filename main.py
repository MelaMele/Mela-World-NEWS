import os
import json
import requests
import warnings
import random
import html
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from deep_translator import GoogleTranslator

# የማያስፈልጉ Warningዎችን ማደፈን
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# --- ውቅሮች (CONFIGURATIONS) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@Mela_World_Sports")
CHANNEL_LINK = "https://t.me/Mela_World_Sports"
DB_FILE = "sent_news.json"

# --- የስፖርት ዜና ምንጮች ---
NEWS_FEEDS = {
    "GENERAL": [
        "http://feeds.bbci.co.uk/sport/rss.xml",
        "https://www.skysports.com/rss/12010",
        "https://www.espn.com/espn/rss/news",
        "https://www.theguardian.com/sport/rss",
        "http://feeds.bbci.co.uk/sport/football/rss.xml",
        "https://www.sportskeeda.com/feed",
    ],
    "TRANSFER": [
        "http://feeds.bbci.co.uk/sport/football/gossip/rss.xml"
    ]
}

# የስፖርት ቃላት ትርጉም ማስተካከያ (የተዛቡ ትርጉሞችን ለማረም)
SPORTS_GLOSSARY = {
    "Gunners": "መድፈኞቹ",
    "Red Devils": "ቀያይ ሰይጣኖች",
    "Clean sheet": "መረብን ሳያስደፍሩ መውጣት",
    "Hat-trick": "ሀት-ትሪክ",
    "penalty": "የፍጹም ቅጣት ምት",
    "transfer window": "የዝውውር መስኮት",
    "midfielder": "አማካኝ",
    "striker": "አጥቂ",
    "defender": "ተከላካይ",
    "goalkeeper": "በረኛ"
}

# --- HTTP SESSION ---
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
})


# --- DATABASE FUNCTIONS ---
def load_sent_news():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, IOError):
            return set()
    return set()

def save_sent_news(sent_set):
    sent_list = list(sent_set)[-500:]  # የቅርብ 500 ዜናዎችን ብቻ ማስቀረት
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(sent_list, f, ensure_ascii=False, indent=2)


# --- TRANSLATION & TEXT PROCESSING ---
def sanitize_text(text):
    if not text:
        return ""
    text = html.unescape(text)
    # የቴሌግራም HTML ታጎችን ላለመስበር ምልክቶችን ማስተካከል
    return text.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")

def translate_to_amharic(text):
    if not text:
        return ""
    try:
        # አስቀድሞ የሚታወቁ ቃላቶችን ማስተካከል
        for en, am in SPORTS_GLOSSARY.items():
            text = text.replace(en, am)

        translated = GoogleTranslator(source='auto', target='am').translate(text)
        return sanitize_text(translated)
    except Exception as e:
        print(f"⚠️ የትርጉም ስህተት: {e}")
        return sanitize_text(text)


# --- TELEGRAM POSTING ---
def send_telegram_post(caption, image_url=None):
    if not TELEGRAM_BOT_TOKEN:
        print("❌ የቦት ቶከን አልተገኘም!")
        return False

    reply_markup = {
        "inline_keyboard": [[{"text": "📢 ቻናላችንን ይቀላቀሉ", "url": CHANNEL_LINK}]]
    }

    # 1. ምስል ካለው በፎቶ መልኩ ይልካል
    if image_url:
        photo_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        photo_payload = {
            "chat_id": TELEGRAM_CHANNEL_ID,
            "photo": image_url,
            "caption": caption[:1024],  # ለፎቶ Caption ገደቡ 1024 ፊደል ነው
            "parse_mode": "HTML",
            "reply_markup": json.dumps(reply_markup)
        }
        try:
            res = session.post(photo_url, data=photo_payload, timeout=12)
            if res.status_code == 200:
                return True
        except Exception as e:
            print(f"⚠️ ምስል መላክ አልተቻለም፡ {e}")

    # 2. ምስል ከሌለ ወይም ፎቶው ካልሰራ በጽሁፍ ብቻ ይልካል
    msg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    msg_payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": caption[:4096],  # ለጽሁፍ መልእክት ገደቡ 4096 ነው
        "parse_mode": "HTML",
        "reply_markup": json.dumps(reply_markup)
    }
    try:
        res = session.post(msg_url, data=msg_payload, timeout=12)
        return res.status_code == 200
    except Exception as e:
        print(f"❌ መልእክት መላክ አልተቻለም: {e}")
        return False


# --- RSS FEED PROCESSOR ---
def process_feed(feed_url, is_transfer=False):
    """ከአንድ RSS feed አዲስ ዜና አምጥቶ ይለጥፋል"""
    sent_news = load_sent_news()
    try:
        res = session.get(feed_url, timeout=10)
        if res.status_code != 200:
            return False

        soup = BeautifulSoup(res.content, "xml")
        items = soup.find_all("item")

        # የቅርብ 10 ዜናዎችን ብቻ ይመረምራል
        for item in items[:10]:
            title_tag = item.find("title")
            link_tag = item.find("guid") or item.find("link")
            desc_tag = item.find("description")

            title_en = title_tag.get_text(strip=True) if title_tag else ""
            link = link_tag.get_text(strip=True) if link_tag else ""
            desc_en = desc_tag.get_text(strip=True) if desc_tag else ""

            if not link or len(title_en) < 10 or link in sent_news:
                continue

            # ምስል ማውጣት
            image_url = None
            media = item.find("media:thumbnail") or item.find("media:content") or item.find("enclosure")
            if media and media.get("url"):
                image_url = media["url"]

            # ወደ አማርኛ መተርጎም
            title_am = translate_to_amharic(title_en)
            content_am = translate_to_amharic(desc_en)

            if len(content_am) > 650:
                content_am = content_am[:650] + "..."

            # የመልእክት ቅርጸት (Template)
            header = "🔄 <b>የተጫዋቾች ዝውውር መረጃ</b>" if is_transfer else "🔥 <b>ትኩስ የስፖርት ዜና</b>"
            caption = (
                f"{header}\n\n"
                f"📌 <b>{title_am}</b>\n\n"
                f"{content_am}\n\n"
                f"─────────────────\n"
                f"🏆 <i>Mela World Sports</i>"
            )

            if send_telegram_post(caption, image_url):
                print(f"✅ ተልኳል: {title_en}")
                sent_news.add(link)
                save_sent_news(sent_news)
                return True

    except Exception as e:
        print(f"⚠️ ስህተት ከ {feed_url} ሲሰበሰብ: {e}")

    return False


# --- MAIN RUNNER ---
def run():
    print("🚀 ቦቱ ስራ ጀምሯል...")

    # 1. አጠቃላይ ዜናዎችን ማሰራጨት (ቢበዛ 2 ወይም 3 ዜና)
    general_feeds = NEWS_FEEDS["GENERAL"].copy()
    random.shuffle(general_feeds)
    posted_count = 0

    for feed in general_feeds:
        if posted_count >= 2:
            break
        if process_feed(feed, is_transfer=False):
            posted_count += 1

    # 2. የዝውውር ዜና ማሰራጨት (1 ዜና)
    for feed in NEWS_FEEDS["TRANSFER"]:
        if process_feed(feed, is_transfer=True):
            break

    print("🏁 ስራው ተጠናቋል!")

if __name__ == "__main__":
    run()
