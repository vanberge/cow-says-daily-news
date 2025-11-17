## All imports and API keys at the top ##
#########################################

import google.generativeai as genai
import os
import time
import requests
import jwt
import json
import html
import sys # Necessary for sys.exit()

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
GHOST_AUTHOR = os.environ.get("GHOST_AUTHOR")
if not GHOST_AUTHOR:
    raise ValueError("GHOST_AUTHOR environment variable not set.")


## Step 1 - Get the News with NewsAPI.org ##
############################################

def get_top_headlines():
    """
    Fetches the top 25 US headlines using the official NewsAPI.org v2 endpoint.
    Documentation: https://newsapi.org/docs/endpoints/top-headlines
    """
    print("Connecting to NewsAPI.org to fetch top headlines...")

    url = "https://newsapi.org/v2/top-headlines"

    # Define parameters according to NewsAPI docs
    params = {
        'country': 'us',      # standard 2-letter ISO 3166-1 code
        'pageSize': 25        # limit to 25 articles
    }

    # Pass the API key in the header
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

model = genai.GenerativeModel('gemini-2.5-flash')

def get_news_topic(headline):
    print(f"Classifying news article: {headline}")
    """
    Uses Google Gemini to classify a headline into one of your topics.
    """
    prompt = f"""
    You are an expert news article classifier. Your task is to analyze a news article headline and assign a single, most relevant category from the defined list.

    **CATEGORY LIST AND DEFINITIONS:**
    1.  **Politics:** Government, elections, domestic policy, legislation, legal matters (e.g., Supreme Court rulings, major trials).
    2.  **Technology:** Software, hardware, AI, social media platform changes, consumer electronics, cybersecurity.
    3.  **Health:** Medical breakthroughs, public health, nutrition, fitness, mental wellness, and general lifestyle trends (e.g., travel, food).
    4.  **Business:** Stock markets, corporate earnings, industry trends, personal finance, economic indicators (inflation, employment).
    5.  **Sports:** Professional or major amateur team/athlete news, game results, sports business, and related controversies.
    6.  **Science:** Space exploration, physics, chemistry, biology (non-medical), geology, climate change, and conservation efforts.
    7.  **Weather:** Notable Storm impacts, forecasts, information on tornadoes, hurricanes, excessive heat or cold.
    8.  **Education:** Information on schools, universities, teaching professions and students in public and higher education.
    9.  **Entertainment:** Movies, music, television, celebrity gossip, pop culture, art, and gaming.
    10.  **Other:** Use only if the article's primary subject is completely irrelevant or too vague to fit any other category. This should be used as an absolute last resort.

    **PRIORITIZATION RULES (TO REDUCE 'OTHER'):**
    1.  **Choose the Primary Subject:** Classify based on the core event (e.g., Tech CEO Buys Political Ad -> Technology).
    2.  **Be Aggressive:** You MUST select one of the defined categories (1-9) if there is any reasonable connection.
    3.  **Ambiguity Fallback:** If a headline is ambiguous, default to the category that represents the broader trend or source institution.
    4.  **Use 'Other' ONLY if categories 1-9 are not broadly applicable to the headline.**

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
    "Politics": [], "Technology": [], "Health": [], "Business": [], "Sports": [],
    "Science": [], "Weather": [], "Education": [], "Entertainment": [], "Other": []
}

for article in articles:
    headline = article['title']

    print("Checking for Horoscopes...") #these show up sometimes in NewsAPI.org, we dont want them
    if "horoscope" in headline.lower():
        print(f"-> Filtered (Horoscope): {headline}")
        continue

    topic = get_news_topic(headline)
    source_name = article.get('source', {}).get('name', 'Unknown Source')
    
    # Format from NewsAPI keeps the source as part of the headline. This removes it
    separator = ' - '
    if separator in headline:
        headline = headline.split(separator, 1)[0]

    article_data = {
        "headline": headline,
        "source": source_name,
        "url": article['url']
    }

    if topic in grouped_headlines and len(grouped_headlines[topic]) < 10:
        grouped_headlines[topic].append(article_data)
    elif topic not in grouped_headlines:
        if len(grouped_headlines["Other"]) < 8:
            grouped_headlines["Other"].append(article_data)

print("Classification complete.")


## NEW STEP 3 - Generate Summary and Punny Title ##
###################################################

def get_daily_summary(grouped_headlines):
    """
    Uses Gemini to create a one-paragraph summary of the most notable stories
    from the grouped headlines, regardless of category. (Requirement 2)
    """
    print("Generating one-paragraph daily news summary...")
    
    headline_list = []
    # Concatenate all headlines and sources into a single input string for the LLM
    for topic, articles in grouped_headlines.items():
        for article in articles:
            # Format: "'Headline' (Source: SourceName in Category)"
            headline_list.append(f"'{article['headline']}' (Source: {article['source']} in {topic})")
    
    if not headline_list:
        return "No notable headlines were available today."

    headline_input = "\n".join(headline_list)

    prompt = f"""
    Analyze the following list of news headlines and sources. Your goal is to synthesize the information and generate a single, 
    compelling paragraph (maximum 5 sentences) summarizing the most notable and significant stories of the day, 
    prioritizing impact over niche topics. Mention 2-3 of the biggest news items.

    **News Headlines and Context:**
    {headline_input}

    **Daily News Summary (Single Paragraph):**
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
        print(f"Error generating summary: {e}")
        return "An issue occurred while generating the daily news summary."

daily_summary = get_daily_summary(grouped_headlines)
print("Daily news summary generated.")


def get_punny_title(summary_text):
    """
    Uses Gemini to create a punny title based on the summary and today's date. (Requirement 1)
    
    """
    print("Generating punny post title...")
    current_date_mmddyyyy = time.strftime("%m/%d/%Y")
    
    # System instruction enforces the required title format
    system_instruction = f"""
    You are an expert copywriter for a humorous daily news blog. Your job is to create one, short, catchy, punny title that captures the essence of the news. 
    It should be "fun", but not offensive given the gravity of the news

    **CRITICAL RULE:** The title MUST begin with the prefix: 'Daily News:' followed immediately by the punny hook.
    """
    
    # --- Merge instruction into the prompt ---
    full_prompt = f"""
    {system_instruction}

    Now, create the punny title based on this news summary:
    {summary_text}
    """

    try:
        response = model.generate_content(
            full_prompt, # Use the combined prompt
            safety_settings={
                'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
            }
        )
        time.sleep(1)
        # The model is instructed to include the date prefix in its response.
        return response.text.strip()
    except Exception as e:
        print(f"Error generating punny title: {e}")
        # Fallback generic title
        return f"Daily News - {time.strftime('%m/%d/%Y')} - Your Daily Dose of Moo-sings"

punny_title = get_punny_title(daily_summary)
print(f"Punny title generated: '{punny_title}'")


## Step 4 - Build "CowSay" format ##
####################################

print("Generating modern HTML summary...")

def create_html_summary(grouped_headlines, daily_summary):
    """
    Formats the grouped headlines and the daily summary into a self-contained
    HTML/CSS block that looks like a modern cowsay post.
    """

    # Build the HTML and CSS as a single string.
    html_parts = []

    # --- The CSS (inline <style> block) ---
    html_parts.append('<!--kg-card-begin: html-->') #Needed for Ghost wrapping and conversion into lexicon format
    html_parts.append("""
    <style>
        .cow-post {
            max-width: 700px;
            margin: 1em auto;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
        }
        .cow-post .speech-bubble {
            background-color: #f8f9fa;
            border: 2px solid #dee2e6;
            border-radius: 15px;
            padding: 1.5em;
            position: relative;
            margin-top: 0;
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
        .cow-post .summary-paragraph {
            margin-top: 1.5em;
            margin-bottom: 1.5em;
            padding: 0.5em 0;
            border-top: 1px solid #e9ecef;
            border-bottom: 1px solid #e9ecef;
        }
        .cow-post .cow-art {
            font-family: monospace, monospace;
            font-size: 1em;
            color: #495057;
            line-height: 1.2;
            text-align: left;
            /* Move cow to the left */
            white-space: pre;
        }
    </style>
    """)

    # --- HTML Structure --- #
    html_parts.append('<div class="cow-post">')
    html_parts.append('  <div class="speech-bubble">')
    # html_parts.append("    <h2>Good Moo-rning! Here's your daily news...</h2>")

    # --- Daily Summary Paragraph ---
    # if daily_summary and daily_summary != "No notable headlines were available today.":
    #    html_parts.append(f"    <p class='summary-paragraph'><strong>Today's Top Stories:</strong> {html.escape(daily_summary)}</p>")

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
                html_parts.append(f'        <a href="{safe_url}" target="_blank">{safe_headline}</a> - ')
                html_parts.append(f'        <span class="source"> ({safe_source})</span>')
                html_parts.append("      </li>")
            html_parts.append("    </ul>")

    html_parts.append('  </div>') # Close .speech-bubble

    # Add the cow (in a <pre> tag to preserve formatting)
    
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
    html_parts.append(f'  <pre class="cow-art">{html.escape(cow_ascii)}</pre>')
    html_parts.append('</div>') # Close .cow-post

    # Donation link in case anyone wants to help support 
    html_parts.append(""" 
    <div class="cow-post">
      <a href="https://www.buymeacoffee.com/vanberge">🐮 Support the News!</a>
    </div>
    """)
    html_parts.append('<!--kg-card-end: html-->') # Ghost wrapper closing

    return "\n".join(html_parts)

# --- Function call to include the summary ---
html_content_for_ghost = create_html_summary(grouped_headlines, daily_summary)

# To test the output, uncomment the line below
# print(html_content_for_ghost)
print("HTML summary generated.")


## Step 5 - Post it to Ghost ##
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


# STEP 5a - Get the Newsletter Slug #

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


# STEP 5b - Create Draft Post 

print(f"Creating draft post...")
create_url = f"{GHOST_URL}/ghost/api/admin/posts/?source=html"
author_id = GHOST_AUTHOR 

# Create a payload that uses a single "html" card.
draft_data = {
    'posts': [{
        # --- Use punny_title ---
        'title': punny_title, 
        'html': html_content_for_ghost,  # Use source?html in call now lets us use it here
        'authors': [  # Set the Author
            { "id": author_id }
        ], 
        'status': 'draft'  # Use 'published' to publish immediately
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


