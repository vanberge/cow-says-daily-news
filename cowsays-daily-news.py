import os
import time
import datetime
import requests
import jwt
import json
import html
import sys
from google import genai
from google.genai import types

# --- API Config ---
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
if not NEWS_API_KEY:
    raise ValueError("NEWS_API_KEY environment variable not set.")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY")
if not ADMIN_API_KEY:
    raise ValueError("ADMIN_API_KEY environment variable not set.")

GHOST_URL = os.environ.get("GHOST_URL")
if not GHOST_URL:
    raise ValueError("GHOST_URL environment variable not set.")

GHOST_AUTHOR = os.environ.get("GHOST_AUTHOR")
if not GHOST_AUTHOR:
    raise ValueError("GHOST_AUTHOR environment variable not set.")

# --- Initialize Gemini 3.1 Client ---
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_ID = "gemini-3.1-flash-lite-preview"

## Step 1 - Get the News with NewsAPI.org ##
############################################

def get_top_headlines():
    url = "https://newsapi.org/v2/top-headlines"
    params = {'country': 'us', 'pageSize': 26}
    headers = {'X-Api-Key': NEWS_API_KEY}
    
    max_retries = 3
    retry_delay = 30

    for attempt in range(1, max_retries + 1):
        print(f"Connecting to NewsAPI.org (Attempt {attempt}/{max_retries})...")
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            if data.get('status') != 'ok':
                print(f"NewsAPI Error: {data.get('code')} - {data.get('message')}")
                return []

            return data.get('articles', [])
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            print(f"Error fetching news: {e}")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                return []
    return []

articles = get_top_headlines()
if not articles:
    print("Error: Failed to fetch articles. Exiting")
    sys.exit(1)

## Step 2 - Classify the news into Categories ##
################################################

def get_news_topic(headline):
    print(f"Classifying: {headline[:50]}...")
    prompt = f"""
    Assign a single category from this list: Politics, Technology, Health, Business, Sports, Science, Weather, Education, Entertainment, Other.
    Headline: "{headline}"
    Category:
    """
    try:
        # Using the new SDK syntax for content generation and safety
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                safety_settings=[
                    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                ]
            )
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error classifying: {e}")
        return "Other"

grouped_headlines = {k: [] for k in ["Politics", "Technology", "Health", "Business", "Sports", "Science", "Weather", "Education", "Entertainment", "Other"]}

for article in articles:
    headline = article['title']
    if "horoscope" in headline.lower(): continue

    topic = get_news_topic(headline)
    source_name = article.get('source', {}).get('name', 'Unknown Source')
    
    if ' - ' in headline:
        headline = headline.split(' - ', 1)[0]

    filter_urls = ('facebook.com','x.com','.gov','bsky.app','threads.com','truthsocial.com','reddit.com','instagram.com','tiktok.com')
    if any(s in article['url'] for s in filter_urls): continue

    article_data = {"headline": headline, "source": source_name, "url": article['url']}

    if topic in grouped_headlines and len(grouped_headlines[topic]) < 10:
        grouped_headlines[topic].append(article_data)
    else:
        if len(grouped_headlines["Other"]) < 5:
            grouped_headlines["Other"].append(article_data)

## STEP 3 - Punny Title ##
##########################

def get_punny_title(grouped_headlines):
    print("Generating punny title...")
    day_name = datetime.datetime.now().strftime("%A")
    title_prefix = f"{day_name} Edition:"
    
    headline_list = []
    for topic, arts in grouped_headlines.items():
        for a in arts:
            headline_list.append(f"'{a['headline']}' ({a['source']} in {topic})")
    
    if not headline_list: return f"{title_prefix} The Quiet News Day"

    headline_input = "\n".join(headline_list)
    prompt = f"""
    You are a pun-loving copywriter. Create a catchy title referencing 1-2 of these headlines.
    CRITICAL: The title MUST begin with '{title_prefix}'.
    
    Headlines:
    {headline_input}
    """
    
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                safety_settings=[types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE")]
            )
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error: {e}")
        return f"{title_prefix} Daily News Roundup"

punny_title = get_punny_title(grouped_headlines)

## Step 4 - Build "CowSay" format ##
####################################

def create_html_summary(grouped_headlines):
    html_parts = ['<!--kg-card-begin: html-->', '<style>']
    html_parts.append("""
        .cow-post { max-width: 700px; font-family: sans-serif; line-height: 1.6; }
        .speech-bubble { background: #f8f9fa; border: 2px solid #dee2e6; border-radius: 15px; padding: 1.5em; position: relative; margin-bottom: 1.5em; }
        .speech-bubble::after { content: ''; position: absolute; bottom: -30px; left: 60px; border-width: 30px; border-style: solid; border-color: #f8f9fa transparent transparent transparent; transform: rotate(-135deg); }
        .cow-post h3 { border-bottom: 2px solid #e9ecef; color: #495057; }
        .cow-post ul { list-style: none; padding: 0; }
        .cow-post li::before { content: '🐮'; margin-right: 8px; }
        .cow-art { font-family: monospace; white-space: pre; color: #495057; }
    """)
    html_parts.append('</style><div class="cow-post"><div class="speech-bubble">')
    
    for topic, articles in grouped_headlines.items():
        if articles:
            html_parts.append(f"<h3>{html.escape(topic.upper())}</h3><ul>")
            for article in articles:
                safe_url = html.escape(article['url']).replace(r'\\u003d', '=')
                html_parts.append(f'<li><a href="{safe_url}">{html.escape(article["headline"])}</a> <small>({html.escape(article["source"])})</small></li>')
            html_parts.append("</ul>")

    cow_ascii = r"""
< Thanks, this has been   >
< Will MaCowvoy reporting >
 --------------------------
        \   ^__^
         \  (oo)\_______
            (__)\       )\/\
                ||----w |
                ||     ||
"""
    html_parts.append(f'</div><pre class="cow-art">{html.escape(cow_ascii)}</pre></div><!--kg-card-end: html-->')
    return "\n".join(html_parts)

html_content = create_html_summary(grouped_headlines)

## Step 5 - Post to Ghost ##
############################

print(f"Posting to Ghost: {punny_title}")

key_id, key_secret = ADMIN_API_KEY.split(':')
iat = int(time.time())
header = {'alg': 'HS256', 'typ': 'JWT', 'kid': key_id}
payload = {'iat': iat, 'exp': iat + 300, 'aud': '/admin/'}
token = jwt.encode(payload, bytes.fromhex(key_secret), algorithm='HS256', headers=header)
headers = {'Authorization': f'Ghost {token}'}

# Get Newsletter
newsletter_slug = "default-newsletter"
try:
    res = requests.get(f"{GHOST_URL}/ghost/api/admin/newsletters/", headers=headers)
    if res.status_code == 200:
        active = [n for n in res.json().get('newsletters', []) if n.get('status') == 'active']
        if active: newsletter_slug = active[0]['slug']
except: pass

# Create Draft
draft_data = {
    'posts': [{
        'title': punny_title,
        'html': html_content,
        'authors': [{"id": GHOST_AUTHOR}],
        'status': 'draft'
    }]
}
draft_res = requests.post(f"{GHOST_URL}/ghost/api/admin/posts/?source=html", json=draft_data, headers=headers)

if draft_res.status_code == 201:
    post_data = draft_res.json()['posts'][0]
    # Publish
    pub_url = f"{GHOST_URL}/ghost/api/admin/posts/{post_data['id']}/?newsletter={newsletter_slug}"
    pub_res = requests.put(pub_url, json={'posts': [{'updated_at': post_data['updated_at'], 'status': 'published', 'email_recipient_filter': 'all'}]}, headers=headers)
    print(f"Post Live: {pub_res.status_code}")
else:
    print(f"Failed: {draft_res.text}")