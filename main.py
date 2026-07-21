import os
import json
import requests
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
# የቴሌግራም ቦት ቶከን እና የቻናል ስም ወይም ID እዚህ ያስገቡ
TELEGRAM_BOT_TOKEN = "8870500617:AAGq_oPWR4rA9mLRVYV3pUPkf-TvEKnWy-E"
TELEGRAM_CHANNEL_ID = "@YOUR_CHANNEL_USERNAME"  # ወይም ID e.g., "-100123456789"

# የተላኩ ዜናዎችን መመዝገቢያ JSON ፋይል
DB_FILE = "sent_news.json"

# የ Opera News/Mini URL (ወይም የዜና ድረ-ገጽ)
NEWS_URL = "https://news.opera.com/" 

# --- HELPER FUNCTIONS ---

def load_sent_news():
    """ቀደም ሲል የተላኩ ዜናዎችን ከ JSON ፋይል ያነባል"""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_sent_news(sent_list):
    """የተላኩ ዜናዎችን ወደ JSON ፋይል ያስቀምጣል"""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(sent_list, f, ensure_ascii=False, indent=2)

def send_telegram_message(title, link):
    """ዜናውን ወደ ቴሌግራም ቻናል የሚልክ ፋንክሽን"""
    message = f"<b>{title}</b>\n\n🔗 <a href='{link}'>ሙሉውን ለማንበብ እዚህ ይጫኑ</a>\n\nበራስ-ሰር የተላከ ዜና 🤖"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    
    try:
        response = requests.post(url, data=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"ስህተት ተከሰተ (Telegram API): {e}")
        return False

# --- MAIN SCRAPER ---

def scrape_and_post():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(NEWS_URL, headers=headers)
        if response.status_code != 200:
            print(f"ድረ-ገጹን መክፈት አልተቻለም። Status Code: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, "html.parser")
        
        # የተላኩ ዜናዎችን ዝርዝር መጫን
        sent_news = load_sent_news()
        
        # በ Opera News ገጽ ላይ ያሉትን የዜና ሊንኮች መፈለግ
        # (እንደ ገጹ HTML አወቃቀር ታጎች ሊቀየሩ ይችላሉ)
        articles = soup.find_all("a", href=True)

        count = 0
        for article in articles:
            title = article.get_text().strip()
            link = article["href"]

            # ሊንኩ Relative ከሆነ ወደ Absolute መለወጥ
            if not link.startswith("http"):
                link = "https://news.opera.com" + link

            # አጭር ጽሑፎችን ወይም ባዶ ርዕሶችን ማጣራት
            if len(title) < 15:
                continue

            # ዜናው ቀደም ሲል ካልተላከ ብቻ መላክ
            if link not in sent_news:
                print(f"አዲስ ዜና ተገኝቷል፡ {title}")
                
                success = send_telegram_message(title, link)
                if success:
                    sent_news.append(link)
                    save_sent_news(sent_news)
                    print("በተሳካ ሁኔታ ወደ ቴሌግራም ተልኳል!")
                    count += 1
                    
                # በአንድ ጊዜ ብዙ እንዳይላክ ገደብ ማድረግ (ለምሳሌ 3 ዜና ብቻ)
                if count >= 3:
                    break

        if count == 0:
            print("አዲስ ያልተላከ ዜና አልተገኘም።")

    except Exception as e:
        print(f"Scraping በሚደረግበት ወቅት ስህተት ተከሰተ: {e}")

if __name__ == "__main__":
    scrape_and_post()
