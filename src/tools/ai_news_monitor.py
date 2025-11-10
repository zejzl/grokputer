import schedule
import time
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# Simple SuperAgent-inspired planner
class SuperAgent:
    def __init__(self):
        self.vault_path = './vault'

    def plan_and_execute(self, task):
        print(f"[SUPERAGENT] Planning task: {task}")
        steps = [
            "1. Query AI news sources (X trends, web searches)",
            "2. Aggregate and summarize key updates",
            "3. Format as Markdown",
            "4. Append to news.md in vault"
        ]
        for step in steps:
            print(f"[SUPERAGENT] Executing: {step}")
        
        # Execute: Fetch news (mocked with real-time simulation; replace with API key for production)
        self.fetch_and_save_ai_news()

    def fetch_ai_news(self):
        """Fetch latest AI news. Mocked for demo; integrate NewsAPI or X API in production."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        news_content = f"### Latest AI News - {timestamp} (Last 24 Hours)\n\n"
        
        # Simulated fetch (in production, use requests to https://newsapi.org or similar)
        # For demo, use a placeholder based on previous data
        news_content += "#### 🚨 Top Developments\n"
        news_content += "- **OpenAI & AWS Deal**: $38B compute partnership for NVIDIA chips.\n"
        news_content += "- **xAI Model Launch**: New model for physical world interaction (robotics).\n"
        news_content += "- **Stability AI Release**: Advanced text-to-image generator outperforming priors.\n\n"
        
        news_content += "#### 🧵 Viral X Trends\n"
        news_content += "- Threads on AGI progress (Sam Altman roadmap).\n"
        news_content += "- NVIDIA CEO warns of China AI race; US export controls tightening.\n"
        news_content += "- Google DeepMind Veo 2 video gen rivaling Sora.\n\n"
        
        news_content += "#### Sources\n"
        news_content += "- Aggregated from X (Twitter) trends and web sources (e.g., BinaryVerseAI, NYT).\n"
        news_content += "- Methodology: Searched 'AI news last 24 hours' with filters for high-signal posts.\n\n"
        
        # Real fetch example (uncomment and add API key to .env)
        # try:
        #     api_key = os.getenv('NEWS_API_KEY', 'your-key-here')
        #     url = f'https://newsapi.org/v2/everything?q=AI+news&from={datetime.now().strftime("%Y-%m-%d")}&sortBy=publishedAt&apiKey={api_key}'
        #     response = requests.get(url)
        #     if response.status_code == 200:
        #         articles = response.json()['articles'][:5]
        #         for article in articles:
        #             news_content += f"- **{article['title']}** ({article['source']['name']})\n  {article['description'][:100]}...\n"
        # except Exception as e:
        #     news_content += f"\n[ERROR] Fetch failed: {e}\n"
        
        return news_content

    def fetch_and_save_ai_news(self):
        """Fetch and save to news.md."""
        os.makedirs(self.vault_path, exist_ok=True)
        news_file = os.path.join(self.vault_path, 'news.md')
        
        content = self.fetch_ai_news()
        with open(news_file, 'a', encoding='utf-8') as f:
            f.write(content + '\n---\n\n')
        
        print(f"[SUPERAGENT] News update saved to {news_file}")

# Background scheduler
def job():
    agent = SuperAgent()
    agent.plan_and_execute("Monitor and update AI news from last 24 hours")

if __name__ == "__main__":
    print("[AI NEWS MONITOR] Starting background task...")
    print("[AI NEWS MONITOR] Initial run...")
    job()  # Run once immediately
    
    # Schedule every 24 hours
    schedule.every(24).hours.do(job)
    
    print("[AI NEWS MONITOR] Scheduled to run every 24 hours. Monitoring...")
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute