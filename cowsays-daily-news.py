## All imports and API keys at the top ##
#########################################

import google.generativeai as genai
import os
import time
import requests
import jwt
import json
import html

# --- NewsAPI.org Config ---
# Read API key from environment variable
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
if not NEWS_API_KEY:
    raise ValueError("NEWS_API_KEY environment variable not set.")

# --- Configure Gemini ---
# Read API key from environment variable
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")
genai.configure(api_key=GEMINI_API_KEY)

# --- Ghost API Config ---
# Read API key from environment variable
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY")
if not ADMIN_API_KEY:
    raise ValueError("ADMIN_API_KEY environment variable not set.")
GHOST_URL = os.environ.get("GHOST_URL")
if not GHOST_URL:
    raise ValueError("GHOST_URL environment variable not set.")


## Step 1 - Get the News with NewsAPI.org ##
############################################

def get_top_headlines():
    """
    Fetches the top 20 US headlines using the official NewsAPI.org v2 endpoint.
    Documentation: https://newsapi.org/docs/endpoints/top-headlines
    """
    print("Connecting to NewsAPI.org to fetch top headlines...")

    url = "https://newsapi.org/v2/top-headlines"

    # Define parameters according to NewsAPI docs
    params = {
        'country': 'us',      # standard 2-letter ISO 3166-1 code
        'pageSize': 25        # limit to 25 articles
    }

    # It's best practice to pass the API key in the header
    headers = {
        'X-Api-Key': NEWS_API_KEY
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status() # Raises error for 4xx/5xx status codes

        data = response.json()

        # NewsAPI returns a 'status' field we should check
        if data.get('status') != 'ok':
            print(f"NewsAPI Error: {data.get('code')} - {data.get('message')}")
            return []

        # The articles are exactly where we need them
        articles = data.get('articles', [])
        return articles

    except requests.exceptions.RequestException as e:
        print(f"Network error fetching news: {e}")
        return []
    except json.JSONDecodeError:
        print("Error: Received invalid JSON from NewsAPI.")
        return []

# --- Execution of step 1 ---
articles = get_top_headlines()

if articles:
    print(f"Successfully fetched {len(articles)} headlines from NewsAPI.org.")
else:
    print("Warning: Failed to fetch articles. Continuing with empty data.")


## Step 2 - Classify the news into Categories ##
################################################

print("Classifying news articles...")
model = genai.GenerativeModel('gemini-2.5-flash')

def get_news_topic(headline):
    """
    Uses Google Gemini to classify a headline into one of your topics.
    """
    prompt = f"""
    Classify the following news headline into ONLY one of these categories:
    Politics, Technology, Health, Sports, Business, Entertainment, Other

    Headline: "{headline}"
    Category:
    """
    try:
        response = model.generate_content(
            prompt,
            safety_settings={
                'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
            }
        )
        time.sleep(1)
        return response.text.strip()
    except Exception as e:
        print(f"Error classifying headline '{headline}': {e}")
        return "Other"

grouped_headlines = {
    "Politics": [], "Technology": [], "Health": [], "Sports": [],
    "Business": [], "Entertainment": [], "Other": []
}

for article in articles:
    headline = article['title']
    topic = get_news_topic(headline)
    source_name = article.get('source', {}).get('name', 'Unknown Source')

    article_data = {
        "headline": headline,
        "source": source_name,
        "url": article['url']
    }

    if topic in grouped_headlines and len(grouped_headlines[topic]) < 8:
        grouped_headlines[topic].append(article_data)
    elif topic not in grouped_headlines:
        if len(grouped_headlines["Other"]) < 8:
            grouped_headlines["Other"].append(article_data)

print("Classification complete.")


## Step 3 - Build "CowSay" format ##
####################################

print("Generating modern HTML summary...")

def create_html_summary(grouped_headlines):
    """
    Formats the grouped headlines into a self-contained
    HTML/CSS block that looks like a modern cowsay post.
    """

    # Build the HTML and CSS as a single string.
    # CSS is "scoped" to the .cow-post container to avoid
    # messing with Blog theme.

    html_parts = []

    # --- The CSS (inline <style> block) ---
    html_parts.append("""
    <style>
        .cow-post {
            max-width: 700px;
            margin: 2em auto;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
        }
        .cow-post .speech-bubble {
            background-color: #f8f9fa;
            border: 2px solid #dee2e6;
            border-radius: 15px;
            padding: 1.5em;
            position: relative;
            margin-bottom: 1.5em;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }
        /* The "tail" of the speech bubble */
        .cow-post .speech-bubble::after {
            content: '';
            position: absolute;
            bottom: -30px; /* Was -20px */
            left: 60px; /* Unchanged, adjust if you want to move it left/right */
            border-width: 30px 30px 30px 30px; /* Was 20px 20px 0 0 */
            border-style: solid;
            border-color: #f8f9fa transparent transparent transparent;
            filter: drop-shadow(0 3px 0 #dee2e6);
            transform: rotate(-135deg);
        }
        .cow-post h2 {
            font-size: 1.8em;
            margin-top: 0;
            color: #212529;
        }
        .cow-post h3 {
            font-size: 1.3em;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 5px;
            margin-top: 1.5em;
            color: #495057;
        }
        .cow-post ul {
            list-style-type: none;
            padding-left: 0;
        }
        .cow-post li {
            margin-bottom: 0.8em;
            padding-left: 1.2em;
            position: relative;
        }
        /* A "bullet" for the list */
        .cow-post li::before {
            content: '🐮';
            position: absolute;
            left: 0;
            top: 0;
            font-size: 0.8em;
        }
        .cow-post a {
            text-decoration: none;
            font-weight: 500;
            color: #007bff;
        }
        .cow-post a:hover {
            text-decoration: underline;
        }
        .cow-post .source {
            font-size: 0.9em;
            color: #6c757d;
        }
        .cow-post .cow-art {
            font-family: monospace, monospace;
            font-size: 1em;
            color: #495057;
            line-height: 1.2;
            text-align: left;
            /* Move cow to the left */
            margin-left: 1em;
            white-space: pre;
        }
    </style>
    """)

    # --- HTML Structure --- #
    html_parts.append('<div class="cow-post">')
    html_parts.append('  <div class="speech-bubble">')
    html_parts.append("    <h2>Good Moo-rning! Here's your daily news...</h2>")

    # Loop through topics and build HTML lists
    for topic, articles in grouped_headlines.items():
        if articles:
            # html.escape() is important to prevent HTML-injection issues
            html_parts.append(f"    <h3>{html.escape(topic.upper())}</h3>")
            html_parts.append("    <ul>")
            for article in articles:
                # Sanitize all user-facing data
                safe_url = html.escape(article['url'])
                safe_headline = html.escape(article['headline'])
                safe_source = html.escape(article['source'])

                html_parts.append("      <li>")
                html_parts.append(f'        <a href="{safe_url}" target="_blank">{safe_headline}</a>')
                html_parts.append(f'        <span class="source"> ({safe_source})</span>')
                html_parts.append("      </li>")
            html_parts.append("    </ul>")

    html_parts.append('  </div>') # Close .speech-bubble

    # Add the cow (in a <pre> tag to preserve formatting)
    cow_ascii = r"""
        \   ^__^
         \  (oo)\_______
            (__)\       )\/\
                ||----w |
                ||     ||
    """
    html_parts.append(f'  <pre class="cow-art">{html.escape(cow_ascii)}</pre>')
    html_parts.append('</div>') # Close .cow-post

    return "\n".join(html_parts)

html_content_for_ghost = create_html_summary(grouped_headlines)

# Test the output if needed (uncomment the line below)
# print(html_content_for_ghost)
print("HTML summary generated.")


## Step 4 - Post it to Ghost ##
###############################

print("Posting to Ghost...")

try:
    key_id, key_secret = ADMIN_API_KEY.split(':')
except ValueError:
    print("Error: ADMIN_API_KEY is not in the correct 'id:secret' format.")
    sys.exit(1)

# Prepare the JWT Token
# The token is valid for 5 minutes, sufficient for both requests below.
iat = int(time.time())
header = {'alg': 'HS256', 'typ': 'JWT', 'kid': key_id}
payload = {
    'iat': iat,
    'exp': iat + 300,
    'aud': '/admin/'
}
token = jwt.encode(payload, bytes.fromhex(key_secret), algorithm='HS256', headers=header)

headers = {
    'Authorization': f'Ghost {token}'
}


# STEP 4a - Get the Newsletter Slug #

newsletter_slug = "default-newsletter" # Fallback
try:
    news_url = f"{GHOST_URL}/ghost/api/admin/newsletters/"
    news_response = requests.get(news_url, headers=headers)
    
    if news_response.status_code == 200:
        news_data = news_response.json()
        # Find the first active newsletter
        active_newsletters = [n for n in news_data.get('newsletters', []) if n.get('status') == 'active']
        if active_newsletters:
            newsletter_slug = active_newsletters[0]['slug']
            print(f"found active newsletter: {newsletter_slug}")
    else:
        print(f"Warning: Could not fetch newsletters ({news_response.status_code}). Defaulting to '{newsletter_slug}'.")

except Exception as e:
    print(f"Warning: Error fetching newsletters: {e}. Defaulting to '{newsletter_slug}'.")


# STEP 4b - Create Draft Post 

print(f"Creating draft post...")
create_url = f"{GHOST_URL}/ghost/api/admin/posts/"

# Create a Mobiledoc payload that uses a single "html" card.
mobiledoc_payload = {
    "version": "0.3.1",
    "markups": [],
    "atoms": [],
    "cards": [
        ["html", {"html": html_content_for_ghost}]
    ],
    "sections": [
        [10, 0] # Section 10 (card), card index 0
    ]
}

draft_data = {
    'posts': [{
        'title': f'Cow Says Daily News - {time.strftime("%B %d, %Y")}',
        'mobiledoc': json.dumps(mobiledoc_payload),
        'status': 'draft' 
    }]
}

# Create the draft
draft_response = requests.post(create_url, json=draft_data, headers=headers)

if draft_response.status_code != 201:
    print(f"Failed to create draft: {draft_response.status_code} - {draft_response.text}")
    sys.exit(1)

draft_json = draft_response.json()
post_id = draft_json['posts'][0]['id']
# We capture 'updated_at' to prevent conflict errors in the next step
updated_at = draft_json['posts'][0]['updated_at']

print(f"Draft created (ID: {post_id}). Publishing and emailing...")


# STEP 4c - Publish and Email (Step 2 of 2)

publish_url = f"{GHOST_URL}/ghost/api/admin/posts/{post_id}/?newsletter={newsletter_slug}"

publish_data = {
    'posts': [{
        'updated_at': updated_at, # Must match the current server state
        'status': 'published',
        'email_recipient_filter': 'all' # 'all', 'none', or specific filter like 'status:free'
    }]
}

publish_response = requests.put(publish_url, json=publish_data, headers=headers)

if publish_response.status_code == 200:
    res_json = publish_response.json()
    post = res_json['posts'][0]
    
    # Check if email was actually triggered by inspecting the response
    email_info = post.get('email')
    if email_info:
        print(f"Success! Post published. Email status: {email_info.get('status')} (Recipients: {email_info.get('recipient_count')})")
    else:
        print("Post published, but NO email object returned. Please check your Mailgun settings in Ghost Admin.")
        
    print(f"Post URL: {post.get('url')}")
else:
    print(f"Failed to publish/email: {publish_response.status_code} - {publish_response.text}")
