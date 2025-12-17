## All imports and API keys at the top ##
#########################################

import google.generativeai as genai
import os
import time
import datetime
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
    Includes a retry mechanism: checks once, waits 30 seconds on failure, and tries again.
    Documentation: https://newsapi.org/docs/endpoints/top-headlines
    """
     
    url = "https://newsapi.org/v2/top-headlines"

    # Define parameters according to NewsAPI docs
    params = {
        'country': 'us',      # standard 2-letter ISO 3166-1 code
        'pageSize': 26        # Shoot for 25 articles, with at least 1 filtered out.
    }

    # Pass the API key in the header
    headers = {
        'X-Api-Key': NEWS_API_KEY
    }
    
    max_retries = 3
    retry_delay = 30 # Seconds

    for attempt in range(1, max_retries + 1):
        print(f"Connecting to NewsAPI.org (Attempt {attempt}/{max_retries})...")

        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status() # Raises error for 4xx/5xx status codes

            data = response.json()

            # NewsAPI returns a 'status' field we should check
            if data.get('status') != 'ok':
                print(f"NewsAPI Error: {data.get('code')} - {data.get('message')}")
                # If it's a logic error (like bad API key), retrying usually won't help, so we break or return empty
                return []

            # The articles are exactly where we need them
            articles = data.get('articles', [])
            return articles

        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            print(f"Error fetching news: {e}")
            
            # If this is not the last attempt, wait and retry
            if attempt < max_retries:
                print(f"Waiting {retry_delay} seconds before retrying...")
                time.sleep(retry_delay)
            else:
                print("All retry attempts failed.")
                return []

    return []

# --- Execution of step 1 ---
articles = get_top_headlines()

if articles:
    print(f"Successfully fetched {len(articles)} headlines from NewsAPI.org.")
else:
    print("Error: Failed to fetch articles after retries. Exiting")
    sys.exit(1)


## Step 2 - Classify the news into Categories ##
################################################

model = genai.GenerativeModel('gemini-3-flash-preview')

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

    #Filter out some sources
    print("Checking sources for and filtering out social media...") 
    filter_urls = ('facebook.com','x.com','.gov','bsky.app','threads.com','truthsocial.com','reddit.com','instagram.com','tiktok.com')
    article_url = article['url']

    if any(source in article_url for source in filter_urls):
        print(f"Found forbidden source in URL: {article_url}, skipping")
        continue

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


## STEP 3 - Punny Title ##
##########################

def get_punny_title(grouped_headlines):
    """
    Uses Gemini to create a punny title based on the summary and today's date. 
    
    """
    print("Generating punny post title...")
    
    # Get the current day of the week (e.g., "Monday") and construct the new prefix
    day_name = datetime.datetime.now().strftime("%A")
    title_prefix = f"{day_name} Edition:"
    
    headline_list = []
    # Concatenate all headlines and sources into a single input string for the LLM
    for topic, articles in grouped_headlines.items():
        for article in articles:
            # Format: "'Headline' (Source: SourceName in Category)"
            headline_list.append(f"'{article['headline']}' (Source: {article['source']} in {topic})")
    
    if not headline_list:
        return "No notable headlines were available today."

    headline_input = "\n".join(headline_list)

    # System instruction enforces the required title format, now using the dynamic prefix
    system_instruction = f"""
    You are an expert copywriter for a daily news blog. 
    Your job is to create a short, catchy title that captures the essence of the day's news.
    You will consider how impactful each headline is, and the title you generate should reference 1-2 of the headlines
    
    **CRITICAL RULE:** The title MUST begin with the prefix: '{title_prefix}' followed immediately by the title you generated.
    """
    
    # --- Merge instruction into the prompt ---
    full_prompt = f"""
    {system_instruction}

    Now, create the title based on this collection of news headlines.
    {headline_input}
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
        return response.text.strip()
    
    except Exception as e:
        print(f"Error generating punny title: {e}")
        return f"Daily News: Your Daily Dose of Moo-sings" # Fallback generic title

# Exectuion of Step 3
punny_title = get_punny_title(grouped_headlines)
print(f"Punny title generated: '{punny_title}'")


## Step 4 - Build "CowSay" format ##
####################################

print("Generating modern HTML summary...")

def create_html_summary(grouped_headlines):
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
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
        }
        .cow-post-donate {
            max-width: 700px;
            margin: 1em auto;
            padding-top: 20px; 
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
            margin-top: 0;
            color: #495057;
        }
        .cow-post ul {
            list-style-type: none;
            padding-left: 0;
            padding-bottom: 15px;
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
        .cow-post-donate a {
            text-decoration: none;
            font-weight: 500;
            color: #007bff;
        }
        .cow-post a:hover {
            text-decoration: underline;
        }
        .cow-post-donate a:hover {
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
            white-space: pre;
        }
    </style>
    """)

    # --- HTML Structure --- #
    html_parts.append('<div class="cow-post">')
    html_parts.append('  <div class="speech-bubble">')
    
    # Loop through topics and build HTML lists
    for topic, articles in grouped_headlines.items():
        if articles:
            # html.escape() is important to prevent HTML-injection issues
            html_parts.append(f"    <h3>{html.escape(topic.upper())}</h3>")
            html_parts.append("    <ul>")
            for article in articles:
                # Sanitize all user-facing data
                print(f"Original URL: {article['url']}")
                safe_url = html.escape(article['url']).replace(r'\\u003d', '=')
                print(f"Sanitized URL:{safe_url}")
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
    <div class="cow-post-donate">
      <a href="https://www.buymeacoffee.com/vanberge">🐮 Support the News!</a>
    </div>
    """)
    html_parts.append('<!--kg-card-end: html-->') # Ghost wrapper closing

    return "\n".join(html_parts)

# --- Function call to include the summary ---
html_content_for_ghost = create_html_summary(grouped_headlines)

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


