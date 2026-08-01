import os
import json
import requests
import warnings
import random
from datetime import datetime, timedelta
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from deep_translator import GoogleTranslator

# Warning ማደፈን
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8802119418:AAF13aJKhIw6HboE7O1t0F2Ow4WUkZGmQF8")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@Mela_World_Sports")
CHANNEL_LINK = "https://t.me/Mela_World_Sports"

FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "0b09d7c9459947b2b90b2a16fbdf9cb8")

DB_FILE = "sent_news.json"
NEWS_URL = "http://feeds.bbci.co.uk/sport/football/rss.xml"

# --- TRANSLATION HELPER ---

def clean_text(text):
    if not text:
        return ""
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
    """የቴሌግራም መልእክት መላኪያ (ከነ Join Button)"""
    reply_markup = {
        "inline_keyboard": [
            [{"text": "📢 ቻናላችንን ይቀላቀሉ (Join)", "url": CHANNEL_LINK}]
        ]
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

# --- NEW FEATURES: QUIZ & TOP SCORERS ---

def send_daily_quiz():
    """አውቶማቲክ የስፖርት Quiz/ጥያቄና መልስ ለተከታታዮች መላኪያ"""
    quizzes = [
        {
            "question": "🧠 የቀኑ የስፖርት Quiz: በፕሪሚየር ሊጉ ታሪክ በአንድ ሰሞን (Season) ብዙ ግቦችን ያገባው ተጫዋች ማነው?",
            "options": ["ኤርሊንግ ሃላንድ", "አላን ሺረር", "ክርስቲያኖ ሮናልዶ", "ታሪ አንሪ"],
            "correct_option_id": 0
        },
        {
            "question": "🧠 የቀኑ የስፖርት Quiz: ቻምፒየንስ ሊግን በብዛት ያሸነፈው ክለብ የትኛው ነው?",
            "options": ["ኤሲ ሚላን", "ሪያል ማድሪድ", "ባየርን ሙኒክ", "ሊቨርፑል"],
            "correct_option_id": 1
        },
        {
            "question": "🧠 የቀኑ የስፖርት Quiz: ባሎንዶርን በብዛት የተቀናጀው ተጫዋች ማነው?",
            "options": ["ክርስቲያኖ ሮናልዶ", "ሊዮኔል ሜሲ", "ዮሃን ክሩይፍ", "ሚሼል ፕላቲኒ"],
            "correct_option_id": 1
        }
    ]
    
    quiz = random.choice(quizzes)
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPoll"
    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "question": quiz["question"],
        "options": json.dumps(quiz["options"]),
        "is_anonymous": True,
        "type": "quiz",
        "correct_option_id": quiz["correct_option_id"]
    }
    try:
        res = requests.post(url, data=payload)
        if res.status_code == 200:
            print("✅ የዕለቱ Quiz ተልኳል!")
        else:
            print(f"Quiz ስህተት: {res.text}")
    except Exception as e:
        print(f"Quiz መላክ አልተሳካም: {e}")

def fetch_top_scorers():
    """የእንግሊዝ ፕሪሚየር ሊግ ከፍተኛ ግብ አስቆጣሪዎችን ያወጣል"""
    url = "https://api.football-data.org/v4/competitions/PL/scorers"
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            scorers = data.get("scorers", [])
            
            text = "⚽ <b>የእንግሊዝ ፕሪሚየር ሊግ ከፍተኛ ግብ አስቆጣሪዎች (Top 5)</b>\n\n"
            text += "<b>ደረጃ | ተጫዋች | ክለብ | ግብ</b>\n"
            text += "─────────────────\n"
            
            for index, item in enumerate(scorers[:5], 1):
                player_name = item['player']['name']
                team_name = item['team']['name']
                goals = item['goals']
                text += f"<b>{index}.</b> {player_name} ({team_name}) — <b>{goals} ግብ</b>\n"
                
            text += "\n─────\n🏆 <i>Mela World Sports</i>"
            send_telegram_post(text)
            print("✅ የከፍተኛ ግብ አስቆጣሪዎች ሰንጠረዥ ተልኳል!")
    except Exception as e:
        print(f"የግብ አስቆጣሪዎችን መረጃ ማውጣት አልተቻለም: {e}")

# --- FOOTBALL DATA (FIXTURES & STANDINGS) ---

def fetch_today_matches():
    url = "https://api.football-data.org/v4/competitions/PL/matches?status=SCHEDULED"
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            matches = data.get("matches", [])
            
            # የዛሬን ቀን በኢትዮጵያ ሰዓት (UTC+3) ማሰላት
            today_eat = (datetime.utcnow() + timedelta(hours=3)).strftime("%Y-%m-%d")
            
            today_matches = [m for m in matches if m.get("utcDate", "").startswith(today_eat)]
            
            if today_matches:
                text = "📅 <b>የዛሬ የኢንግሊዝ ፕሪሚየር ሊግ ተጠበቂ ጨዋታዎች</b>\n\n"
                for m in today_matches[:5]:
                    home = m['homeTeam']['name']
                    away = m['awayTeam']['name']
                    time_utc = datetime.strptime(m['utcDate'], "%Y-%m-%dT%H:%M:%SZ")
                    
                    # ወደ ኢትዮጵያ ሰዓት መቀየር (UTC + 3)
                    eat_time = time_utc + timedelta(hours=3)
                    time_str = eat_time.strftime("%H:%M")
                    
                    text += f"⚽ <b>{home} VS {away}</b>\n⏰ ሰዓት፦ {time_str}\n\n"
                
                text += "─────\n🏆 <i>Mela World Sports</i>"
                send_telegram_post(text)
                print("✅ የጨዋታ ፕሮግራም ተልኳል!")
            else:
                print("ዛሬ የተመዘገበ የፕሪሚየር ሊግ ጨዋታ የለም።")
    except Exception as e:
        print(f"የጨዋታ ፕሮግራም ማውጣት አልተቻለም: {e}")

def fetch_top_standings():
    url = "https://api.football-data.org/v4/competitions/PL/standings"
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            table = data['standings'][0]['table']
            
            text = "📊 <b>የእንግሊዝ ፕሪሚየር ሊግ የደረጃ ሰንጠረዥ (Top 5)</b>\n\n"
            text += "<b>ደረጃ | ክለብ | ተጫወቱ | ነጥብ</b>\n"
            text += "─────────────────\n"
            
            for team in table[:5]:
                pos = team['position']
                name = team['team']['name']
                played = team['playedGames']
                pts = team['points']
                text += f"<b>{pos}.</b> {name} | {played} | <b>{pts}</b>\n"
                
            text += "\n─────\n🏆 <i>Mela World Sports</i>"
            send_telegram_post(text)
            print("✅ የደረጃ ሰንጠረዥ ተልኳል!")
    except Exception as e:
        print(f"የደረጃ ሰንጠረዥ ማውጣት አልተቻለም: {e}")

# --- MAIN SCRAPER ---

def scrape_and_post():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(NEWS_URL, headers=headers, timeout=10)
        if response.status_code != 200:
            return

        soup = BeautifulSoup(response.content, "html.parser")
        items = soup.find_all("item")
        sent_news = load_sent_news()

        count = 0
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

            if not link or len(title_en) < 10:
                continue

            if link not in sent_news:
                print(f"\n📌 አዲስ ዜና ተገኝቷል: {title_en}")
                
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
                    f"📌 <i>የአውሮፓ እና የሀገር ውስጥ ስፖርት መረጃዎችን ለማግኘት አሁኑኑ ይቀላቀሉን!</i>"
                )
                
                success = send_telegram_post(caption, image_url)
                
                sent_news.append(link)
                save_sent_news(sent_news)

                if success:
                    print("✅ ዜናው በአማርኛ ተተርጉሞ ተልኳል!")
                    count += 1
                    
                if count >= 3:
                    break

        if count == 0:
            print("አዲስ ያልተላከ የስፖርት ዜና አልተገኘም።")

    except Exception as e:
        print(f"Scraping በሚደረግበት ወቅት ስህተት ተከሰተ: {e}")

if __name__ == "__main__":
    scrape_and_post()
    
    fetch_today_matches()
    fetch_top_standings()
    fetch_top_scorers()
    send_daily_quiz()
