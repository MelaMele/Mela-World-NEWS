import os
import json
import requests
import warnings
import random
import html
from datetime import datetime, timedelta
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from deep_translator import GoogleTranslator
from gtts import gTTS

# Warning ማደፈን
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# --- CONFIGURATION & CHECKS ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@Mela_World_Sports")
CHANNEL_LINK = "https://t.me/Mela_World_Sports"
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    print("❌ ስህተት፡ TELEGRAM_BOT_TOKEN በ Environment Variables ውስጥ አልተገኘም! እባክህ GitHub Secretsን አረጋግጥ።")

DB_FILE = "sent_news.json"
NEWS_URL = "http://feeds.bbci.co.uk/sport/football/rss.xml"
TRANSFER_NEWS_URL = "http://feeds.bbci.co.uk/sport/football/gossip/rss.xml"

# --- TRANSLATION HELPER ---

def clean_text(text):
    """HTML Tagዎችን ማፅዳት እና የተበላሹ charactersን ማስተካከል"""
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
    """የቴሌግራም ጽሁፍ/ፎቶ መልእክት መላኪያ"""
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️ BOT TOKEN ስለሌለ መልእክት መላክ አልተቻለም።")
        return False

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

# --- FEATURE: TEXT TO VOICE / AUDIO POST ---

def send_audio_summary(text_content, caption_title):
    """ጽሁፍን ወደ አማርኛ ድምፅ (Voice) ቀይሮ በቴሌግራም መላክ"""
    if not TELEGRAM_BOT_TOKEN or not text_content:
        return
    
    audio_file = "news_summary.mp3"
    try:
        # gTTS ን በመጠቀም ጽሁፉን ወደ አማርኛ ድምፅ መቀየር
        tts = gTTS(text=text_content, lang='am')
        tts.save(audio_file)
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio"
        caption = f"🎙 <b>{caption_title} (በድምፅ)</b>\n\n─────\n🏆 <i>Mela World Sports</i>"
        
        with open(audio_file, 'rb') as audio:
            files = {'audio': audio}
            data = {
                'chat_id': TELEGRAM_CHANNEL_ID,
                'caption': caption,
                'parse_mode': 'HTML'
            }
            res = requests.post(url, data=data, files=files)
            if res.status_code == 200:
                print("✅ የድምፅ ዜና (Audio Post) በተሳካ ሁኔታ ተልኳል!")
    except Exception as e:
        print(f"የድምፅ ፋይል ማዘጋጀት/መላክ አልተሳካም: {e}")
    finally:
        if os.path.exists(audio_file):
            os.remove(audio_file)

# --- MATCH POLL ---

def send_match_poll(home_team, away_team):
    """የጨዋታ ውጤት ግምት መስጫ Poll"""
    if not TELEGRAM_BOT_TOKEN:
        return
    
    home_am = translate_to_amharic(home_team)
    away_am = translate_to_amharic(away_team)
    
    question = f"🔮 የዛሬ ተጠበቂ ጨዋታ ግምት፦ {home_am} VS {away_am} - ማን ያሸንፋል?"
    options = [f"🔴 {home_am}", "🤝 አቻ (Draw)", f"🔵 {away_am}"]
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPoll"
    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "question": question,
        "options": json.dumps(options),
        "is_anonymous": True
    }
    try:
        res = requests.post(url, data=payload)
        if res.status_code == 200:
            print(f"✅ የጨዋታ ግምት Poll ተልኳል: {home_team} VS {away_team}")
    except Exception as e:
        print(f"Poll መላክ አልተሳካም: {e}")

# --- TRANSFER NEWS SCRAPER ---

def fetch_transfer_news():
    """የዝውውር ጭወታዎችን ለይቶ ማውጫና መላኪያ"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(TRANSFER_NEWS_URL, headers=headers, timeout=10)
        if response.status_code != 200:
            return

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

            if not link or len(title_en) < 10:
                continue

            if link not in sent_news:
                title_am = translate_to_amharic(title_en)
                content_am = translate_to_amharic(description_en)

                caption = (
                    f"🔄 <b>የተጫዋቾች ዝውውር ዜና እና ጭወታዎች</b>\n\n"
                    f"📌 <b>{title_am}</b>\n\n"
                    f"{content_am}\n\n"
                    f"─────────────────\n"
                    f"🏆 <i>Mela World Sports - የዝውውር መረጃዎች</i>"
                )
                
                success = send_telegram_post(caption)
                if success:
                    print(f"✅ የዝውውር ዜና ተልኳል: {title_en}")
                    # አጭር የድምፅ መረጃም አብሮ ይልካል
                    send_audio_summary(f"{title_am}። {content_am}", f"የዝውውር ዜና፡ {title_am}")
                    sent_news.append(link)
                    save_sent_news(sent_news)
                    break
    except Exception as e:
        print(f"የዝውውር ዜና ሲሰበሰብ ስህተት ተከሰተ: {e}")

# --- QUIZ & TOP SCORERS ---

def send_daily_quiz():
    if not TELEGRAM_BOT_TOKEN:
        return

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
    except Exception as e:
        print(f"Quiz መላክ አልተሳካም: {e}")

def fetch_top_scorers():
    url = "https://www.espn.com/soccer/stats/_/league/ENG.1"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.content, "html.parser")
            rows = soup.find_all("tr", class_="Table__TR")
            
            text = "⚽ <b>የእንግሊዝ ፕሪሚየር ሊግ ከፍተኛ ግብ አስቆጣሪዎች (Top 5)</b>\n\n"
            text += "<b>ደረጃ | ተጫዋች | ግብ</b>\n"
            text += "─────────────────\n"
            
            count = 0
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 2:
                    name_elem = cols[1].find("a")
                    goals_elem = cols[-1].text.strip()
                    
                    if name_elem and goals_elem.isdigit():
                        count += 1
                        player_am = translate_to_amharic(name_elem.text.strip())
                        text += f"<b>{count}.</b> {player_am} — <b>{goals_elem} ግብ</b>\n"
                        if count >= 5:
                            break
            
            if count > 0:
                text += "\n─────\n🏆 <i>Mela World Sports</i>"
                send_telegram_post(text)
                print("✅ የከፍተኛ ግብ አስቆጣሪዎች ሰንጠረዥ ተልኳል!")
    except Exception as e:
        print(f"የግብ አስቆጣሪዎችን ማውጣት አልተቻለም: {e}")

# --- FOOTBALL DATA (FIXTURES & STANDINGS) ---

def fetch_today_matches():
    if not FOOTBALL_API_KEY:
        return

    url = "https://api.football-data.org/v4/competitions/PL/matches?status=SCHEDULED"
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            matches = data.get("matches", [])
            
            today_eat = (datetime.utcnow() + timedelta(hours=3)).strftime("%Y-%m-%d")
            today_matches = [m for m in matches if m.get("utcDate", "").startswith(today_eat)]
            
            if today_matches:
                text = "📅 <b>የዛሬ የኢንግሊዝ ፕሪሚየር ሊግ ተጠበቂ ጨዋታዎች</b>\n\n"
                for m in today_matches[:5]:
                    home = m['homeTeam']['name']
                    away = m['awayTeam']['name']
                    time_utc = datetime.strptime(m['utcDate'], "%Y-%m-%dT%H:%M:%SZ")
                    eat_time = time_utc + timedelta(hours=3)
                    time_str = eat_time.strftime("%H:%M")
                    text += f"⚽ <b>{home} VS {away}</b>\n⏰ ሰዓት፦ {time_str}\n\n"
                
                text += "─────\n🏆 <i>Mela World Sports</i>"
                send_telegram_post(text)
                print("✅ የጨዋታ ፕሮግራም ተልኳል!")

                main_match = today_matches[0]
                send_match_poll(main_match['homeTeam']['name'], main_match['awayTeam']['name'])
            else:
                print("ዛሬ የተመዘገበ የፕሪሚየር ሊግ ጨዋታ የለም።")
    except Exception as e:
        print(f"የጨዋታ ፕሮግራም ማውጣት አልተቻለም: {e}")

def fetch_top_standings():
    if not FOOTBALL_API_KEY:
        return

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
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:
        response = requests.get(NEWS_URL, headers=headers, timeout=10)
        if response.status_code != 200:
            return

        soup = BeautifulSoup(response.content, "xml")
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
                
                if success:
                    print(f"✅ ዜና ተልኳል: {title_en}")
                    # የመጀመሪያውን አዲስ ዜና በድምፅ (Voice) አብሮ ይልካል
                    if count == 0:
                        send_audio_summary(f"{title_am}። {content_am}", title_am)
                    
                    sent_news.append(link)
                    save_sent_news(sent_news)
                    count += 1
                    
                if count >= 3:
                    break

    except Exception as e:
        print(f"Scraping በሚደረግበት ወቅት ስህተት ተከሰተ: {e}")

if __name__ == "__main__":
    scrape_and_post()
    fetch_transfer_news()
    fetch_today_matches()
    fetch_top_standings()
    fetch_top_scorers()
    send_daily_quiz()
