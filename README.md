# Cow-Says Daily News Bot

[![Cow-Says Daily News Bot](https://github.com/vanberge/cow-says-daily-news/actions/workflows/daily_news.yml/badge.svg)](https://github.com/vanberge/cow-says-daily-news/actions/workflows/daily_news.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

A daily news bot that uses the NewsAPI.org and Google Gemini API to curate top US headlines, classifies them into categories, formats them into a modern "cowsay"-style speech bubble, and automatically publishes the post to a Ghost blog.

This project started as an experiment with ASCII `cowsay` art and evolved into a fully responsive HTML/CSS post to be mobile-friendly while keeping the original's spirit.

## Final Post Example

![Alt text](./screencap.png?raw=true "Final Post Example")

---

## Features

* **Automated News Aggregation:** Uses the NewsAPI.org API to get top news headlines.
* **AI-Powered Classification:** Automatically classifies each headline into categories (Politics, Technology, Health, Sports, Business, etc.).
* **Modern 'Cowsay' Formatting:** Generates a fully responsive, self-contained HTML/CSS post that mimics the classic `cowsay` speech bubble.
* **Automatic Publishing:** Posts the final summary to your Ghost blog using the Admin API.
* **Email Subscribers:** Automatically emails the new post to all your Ghost subscribers on publish.

---

## How It Works

The script operates in four main steps:

1.  **Step 1: Fetch News**
    Scrape NewsAPI.org for top headlines in the us (25 maximum articles) and return a clean JSON list containing the `title`, `url`, and `source.name`.

2.  **Step 2: Classify News**
    The script iterates through each headline. A second Gemini API prompt classifies each one into a predefined category (e.g., `Politics`, `Technology`, `Other`). The classified articles are stored in a Python dictionary.

3.  **Step 3: Build HTML Post**
    A Python function dynamically generates a single, self-contained HTML string. This string includes all the CSS needed to render the responsive "speech bubble," the formatted news lists with links, and the cow `pre` (monospace) art.

4.  **Step 4: Post to Ghost**
    The script authenticates with the Ghost Admin API by generating a JWT. It then sends the final HTML content inside a `mobiledoc` `html` card payload. This ensures that Ghost renders the custom HTML and `<style>` tags correctly without sanitizing them.

---

## 🚀 Getting Started

### 1. Prerequisites

* Python 3.10+
* A Google Gemini API Key
* A running Ghost blog
* A Ghost Admin API Key (from your Ghost admin panel)

### 2. Installation

1.  Clone the repository:
    ```bash
    git clone [https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git)
    cd YOUR_REPO_NAME
    ```

2.  Install the required Python libraries:
    ```bash
    pip install -r requirements.txt
    ```
    *(Other libraries like `json`, `time`, `os`, and `html` are part of the standard Python library.)*

### 3. Configuration

Open the main Python script (`your_script_name.py`) and set the following variables at the top:

* `GEMINI_API_KEY`: Your API key from Google AI Studio.
* `ADMIN_API_KEY`: Your Ghost Admin API Key (in the format `id:secret`).
* `GHOST_URL`: The full URL of your blog (e.g., `https://my-blog.ghost.io`).

---

## 🏃‍♀️ Running the Bot

Once configured, you can run the bot manually:

```bash
python your_script_name.py
