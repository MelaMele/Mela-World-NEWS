import os
import json
import requests
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
# የቴሌግራም ቦት ቶከን እና የቻናል ስም ወይም ID እዚህ ያስገቡ
TELEGRAM_BOT_TOKEN = "8870500617:AAGq_oPWR4rA9mLRVYV3pUPkf-TvEKnWy-E"
TELEGRAM_CHANNEL_ID = "-1003888249349"  # ወይም ID e.g., "-100123456789"

DB_FILE = "sent_news.json"
NEWS_URL = "https://news.opera.com/" 

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
    """የዜናው ሊንክ ውስጥ ገብቶ ሙሉውን ጽሑፍ እና ምስል ያወጣል"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    image_url = None
    content = ""
    
    try:
        res = requests.get(article_url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            
            # 1. ምስል መፈለግ (በኦፔራ ኒውስ ገጽ ላይ ያለ ዋና ምስል)
            img_tag = soup.find("img")
            if img_tag and img_tag.get("src"):
                image_url = img_tag["src"]
                if not image_url.startswith("http"):
                    image_url = "https:" + image_url if image_url.startswith("//") else "https://news.opera.com" + image_url

            # 2. የጽሑፍ አንቀጾችን መፈለግ
            paragraphs = soup.find_all("p")
            full_text = []
            
            for p in paragraphs:
                txt = p.get_text().strip()
                if len(txt) > 20 and not txt.startswith("©"):
                    full_text.append(txt)
            
            content = "\n\n".join(full_text[:4])
            
    except Exception as e:
        print(f"የዜናውን ዝርዝር በማውረድ ላይ ስህተት፡ {e}")
    
    return content, image_url

def send_telegram_post(title, content, link, image_url):
    """ምስል ካለ ከምስል ጋር፣ ከሌለ በጽሑፍ ብቻ ወደ ቴሌግራም ይልካል"""
    
    # በምስል ስር የሚጻፍ ጽሑፍ (Caption) ከ1024 characters መብለጥ የለበትም
    caption_limit = 900
    if len(content) > caption_limit:
        content = content[:caption_limit] + "..."

    caption = (
        f"<b>📰 {title}</b>\n\n"
        f"{content}\n\n"
        f"─────\n"
        f"🔗 <a href='{link}'>ምንጭ፡ Opera News</a>"
    )
    
    # ምስል ካገኘ በ sendPhoto ይልካል
    if image_url:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        payload = {
            "chat_id": TELEGRAM_CHANNEL_ID,
            "photo": image_url,
            "caption": caption,
            "parse_mode": "HTML"
        }
    else:
        # ምስል ካልተገኘ በ sendMessage ይልካል
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHANNEL_ID,
            "text": caption,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
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
        sent_news = load_sent_news()
        
        articles = soup.find_all("a", href=True)

        count = 0
        for article in articles:
            title = article.get_text().strip()
            link = article["href"]

            if not link.startswith("http"):
                link = "https://news.opera.com" + link

            if len(title) < 15:
                continue

            if link not in sent_news:
                print(f"አዲስ ዜና ተገኝቷል፡ {title}")
                
                # 1. ጽሑፉን እና ምስሉን ማውረድ
                full_content, image_url = fetch_article_details(link)
                
                # 2. ወደ ቴሌግራም መላክ
                success = send_telegram_post(title, full_content, link, image_url)
                
                if success:
                    sent_news.append(link)
                    save_sent_news(sent_news)
                    print("ዜናው ከምስሉ ጋር ወደ ቴሌግራም ተልኳል!")
                    count += 1
                    
                if count >= 2:
                    break

        if count == 0:
            print("አዲስ ያልተላከ ዜና አልተገኘም።")

    except Exception as e:
        print(f"Scraping በሚደረግበት ወቅት ስህተት ተከሰተ: {e}")

if __name__ == "__main__":
    scrape_and_post()
