## All imports and API keys at the top ##

import google.generativeai as genai
import os
import time
import requests
import jwt
import json
import html

# --- Configure Gemini ---
GEMINI_API_KEY = " "
genai.configure(api_key=GEMINI_API_KEY)

# --- Ghost API Config ---
ADMIN_API_KEY = " "
GHOST_URL = " " 


## Step 1 - Get the News with Gemini ##

def get_news_from_gemini():
    """
    Uses Google Gemini to find the top 20 US headlines and format them
    as a JSON list.
    """
    print("Connecting to Gemini to fetch news...")
    model = genai.GenerativeModel('gemini-2.5-flash')

    prompt = """
    You are a news aggregation service. Your task is to find the top 20 most important news headlines in the United States *right now*.
    You must respond with ONLY a valid JSON-formatted list. Do not include any other text, pre-amble, or markdown backticks like ```json or ```.
    The list should contain 20 JSON objects. Each object must have the following exact structure:
    {
      "title": "The full headline of the article",
      "url": "The direct URL to the article",
      "source": {
        "name": "The common name of the news source (e.g., 'The New York Times', 'CNN', 'Reuters')"
      }
    }
    """

    try:
        response = model.generate_content(prompt)
        json_text = response.text.strip().replace("```json", "").replace("```", "")
        articles_list = json.loads(json_text)
        return articles_list
    except Exception as e:
        print(f"Error fetching or parsing news from Gemini: {e}")
        if 'response' in locals():
            print(f"Gemini's raw (unparsed) response: {response.text}")
        return []

articles = get_news_from_gemini()
print(f"Successfully fetched {len(articles)} articles.")


## Step 2 - Classify the news into Categories ##

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


## Step 3 - Build "Cowsay" ##

print("Generating modern HTML summary...")

def create_html_summary(grouped_headlines):
    """
    Formats the grouped headlines into a self-contained
    HTML/CSS block that looks like a modern cowsay post.
    """

    # We build the HTML and CSS as a single string.
    # CSS is "scoped" to the .cow-post container to avoid
    # messing with Blog theme.

    html_parts = []

    # --- 1. The CSS (inline <style> block) ---
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
            bottom: -20px;
            left: 60px;
            border-width: 20px 20px 0 0;
            border-style: solid;
            border-color: #f8f9fa transparent transparent transparent;
            /* This little trick makes the tail's border match */
            filter: drop-shadow(0 2px 0 #dee2e6);
            transform: rotate(15deg);
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

    # --- HTML Structure ---
    html_parts.append('<div class="cow-post">')
    html_parts.append('  <div class="speech-bubble">')
    html_parts.append("    <h2>Moo-rning! Here's your daily US news summary...</h2>")

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


## Step 4 - Post it to Ghost (Corrected Fix) ##

print("Posting to Ghost...")

try:
    key_id, key_secret = ADMIN_API_KEY.split(':')
except ValueError:
    print("Error: ADMIN_API_KEY is not in the correct 'id:secret' format.")
    exit()

payload = {
    'iat': int(time.time()),
    'exp': int(time.time()) + 300,
    'aud': '/admin/'
}
token = jwt.encode(payload, bytes.fromhex(key_secret), algorithm='HS256', headers={'kid': key_id})

post_url = f"{GHOST_URL}/ghost/api/admin/posts/?send_email=true"
headers = {
    'Authorization': f'Ghost {token}'
}

# Create a Mobiledoc payload that uses a single "html" card.
mobiledoc_payload = {
    "version": "0.3.1",
    "markups": [],
    "atoms": [],
    "cards": [
        # This tells Ghost to render the raw HTML, including <style> tags
        ["html", {"html": html_content_for_ghost}]
    ],
    "sections": [
        [10, 0] # Section 10 (card), card index 0
    ]
}

data = {
    'posts': [{
        'title': f'Your Daily Cowsay News - {time.strftime("%B %d, %Y")}',

        # We are using the 'mobiledoc' key
        'mobiledoc': json.dumps(mobiledoc_payload),

        'status': 'published'
    }]
}

# Make the API call
response = requests.post(post_url, json=data, headers=headers)

if response.status_code == 201:
    print("Successfully posted and emailed the news!")
else:
    print(f"Failed to post: {response.status_code} - {response.text}")
