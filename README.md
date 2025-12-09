# Cow-Says Daily News Bot

[![Cow-Says Daily News Bot](https://github.com/vanberge/cow-says-daily-news/actions/workflows/daily_news.yml/badge.svg)](https://github.com/vanberge/cow-says-daily-news/actions/workflows/daily_news.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)
[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-orange.svg)](https://www.gnu.org/licenses/gpl-3.0.txt)

A daily news bot that uses NewsAPI.org and Google's Gemini LLM to curate top US headlines and classify them into categories, format them into a modern "cowsay"-style speech bubble, and automatically publishes the post to a Ghost blog.

This project started as an experiment with ASCII `cowsay` art and evolved into a fully responsive HTML/CSS post to be mobile-friendly while keeping the original's spirit.

## Final Post Example

![Alt text](./screencap.png?raw=true "Final Post Example")

---

## Features

* **Automated News Aggregation:** Uses the NewsAPI.org API to get top news headlines.
* **AI-Powered Classification:** Automatically classifies each headline into categories (Politics, Technology, Health, Sports, Business, etc.).
* **Modern 'Cowsay' Formatting:** Generates a clean and simple self-contained HTML/CSS post that mimics the classic `cowsay` speech bubble.
* **Automatic Publishing:** Posts the final summary to your Ghost blog using the Admin API.
* **Email Subscribers:** Automatically emails the new post to all your Ghost subscribers on publish.

---

## How It Works

The script operates in four main steps:

1.  **Step 1: Fetch News**
    Scrape NewsAPI.org for top headlines in the us (25 maximum articles) and return a clean JSON list containing the `title`, `url`, and `source.name`.

2.  **Step 2: Classify News**
    The script iterates through each headline an uses Google's Gemini API to classify each one into a predefined category (e.g., `Politics`, `Technology`, `Other`). The classified articles are stored in a Python dictionary.

3.  **Step 3: Build HTML Post**
    A Python function dynamically generates a single, self-contained HTML string. This string includes all the CSS needed to render the responsive "speech bubble," the formatted news lists with links, and the cow `pre` (monospace) art.

4.  **Step 4: Post to Ghost**
    The script authenticates with the Ghost Admin API by generating a JWT. It then sends the final HTML content inside an `html` card payload. This ensures that Ghost renders the custom HTML and `<style>` tags correctly without sanitizing them.

---

## 🚀 Getting Started

### 1. Prerequisites

* Python 3.10+
* A NewsAPI.org API Key [Link](https://newsapi.org/docs)
* A Google Gemini API Key [Link](https://ai.google.dev/gemini-api/docs/api-key)
* A running Ghost blog
* A Ghost Admin API Key (from your Ghost admin panel)

### 2. Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/vanberge/cow-says-daily-news.git
    cd ./cow-says-daily-news
    ```

2.  Install the required Python libraries:
    ```bash
    pip install -r requirements.txt
    ```
    *(Other libraries like `json`, `time`, `os`, and `html` are part of the standard Python library.)*

### 3. Configuration

Open the main Python script (`cowsays-daily-news.py`) and set the following variables:

* `NEWS_API_KEY`: Your NewsAPI key from NewsAPI.org.
* `GEMINI_API_KEY`: Your API key from Google AI Studio.
* `ADMIN_API_KEY`: Your Ghost Admin API Key (in the format `id:secret`).
* `GHOST_URL`: The full URL of your blog (e.g., `https://my-blog.ghost.io`).

Follow best practices and store these sensitive keys in an encrypted secrets manager!
NOT in your souce code

---

## 🏃‍♀️ Running the Bot

Once configured, you can run the bot manually:

```bash
python cowsays-daily-news.py
```

## GPL v3 License 

CowSaysDailyNews.com - [Full license](https://github.com/vanberge/cow-says-daily-news/blob/main/LICENSE)

Copyright (C) 2025 Eric VanBergen

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

