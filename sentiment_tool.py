import os
import requests
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Ensure VADER lexicon is downloaded
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon', quiet=True)

class SentimentAnalyzer:
    def __init__(self, news_api_key=None):
        self.news_api_key = news_api_key or "207bb07d51b242988157a15f97c6f262" # Default from provided code
        self.analyzer = SentimentIntensityAnalyzer()

    def fetch_news(self, ticker, company_name=None):
        """Fetch recent news for a ticker from NewsAPI using fallback strategies."""
        url = "https://newsapi.org/v2/everything"
        
        # Strategy 1: Ticker + Keywords (Most relevant)
        queries = [f"{ticker} AND (stock OR market OR finance)"]
        
        # Strategy 2: Company Name (if provided)
        if company_name and company_name != "Unknown":
            queries.append(company_name)
            
        # Strategy 3: Ticker only (Broadest)
        queries.append(ticker)
        
        for query in queries:
            params = {
                "q": query,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 20,
                "apiKey": self.news_api_key
            }
            
            try:
                response = requests.get(url, params=params, timeout=5)
                data = response.json()
                articles = data.get("articles", [])
                
                if articles:
                    print(f"DEBUG: Found {len(articles)} articles using query: '{query}'")
                    return articles
                
                print(f"DEBUG: No news for '{query}', trying next strategy...")
                
            except Exception as e:
                print(f"Error fetching news for '{query}': {e}")
                
        return []

    def analyze_sentiment(self, text):
        """Get compound sentiment score for text."""
        if not text: return 0.0
        return self.analyzer.polarity_scores(text)["compound"]

    def get_stock_sentiment(self, ticker, company_name=None):
        """
        Analyze sentiment for a stock ticker.
        Returns dict with score, label, top articles, and 7-day trend.
        """
        articles = self.fetch_news(ticker, company_name)
        
        from datetime import datetime, timedelta, timezone
        
        # Initialize 7-day trend (Today down to D-6)
        today = datetime.now(timezone.utc).date()
        date_labels = [(today - timedelta(days=i)) for i in range(7)]
        date_labels.reverse() # Oldest to newest: [D-6, ..., Today]
        
        daily_scores = {str(d): [] for d in date_labels}
        
        if not articles:
            return {
                "sentiment_score": 0.0,
                "sentiment_label": "Neutral",
                "news": [],
                "sentiment_trend": [0.0] * 7
            }

        scored_articles = []
        weighted_sum = 0.0
        total_weight = 0.0
        
        # Analyze each article
        for i, article in enumerate(articles):
            title = article.get("title", "")
            description = article.get("description", "") or ""
            text_to_analyze = f"{title}. {description}"
            published_at = article.get("publishedAt", "")
            
            score = self.analyze_sentiment(text_to_analyze)
            
            # Map to trend dates
            try:
                pub_date = datetime.strptime(published_at[:10], "%Y-%m-%d").date()
                date_str = str(pub_date)
                if date_str in daily_scores:
                    daily_scores[date_str].append(score)
            except:
                pass

            # Weight recent articles higher for the "current" score
            weight = len(articles) - i
            weighted_sum += score * weight
            total_weight += weight
            
            scored_articles.append({
                "title": title,
                "source": article.get("source", {}).get("name", "Unknown"),
                "url": article.get("url", "#"),
                "published_at": published_at,
                "sentiment_score": score
            })

        # Calculate final aggregated score
        final_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        # Construct trend array
        trend = []
        last_valid_score = 0.0
        for d in date_labels:
            scores = daily_scores.get(str(d), [])
            if scores:
                day_avg = sum(scores) / len(scores)
                trend.append(round(day_avg, 2))
                last_valid_score = day_avg
            else:
                # Fill gaps with last known score or 0
                trend.append(round(last_valid_score, 2))

        # Determine Label
        if final_score >= 0.05:
            label = "Positive"
        elif final_score <= -0.05:
            label = "Negative"
        else:
            label = "Neutral"

        return {
            "sentiment_score": round(final_score, 2),
            "sentiment_label": label,
            "news": scored_articles[:20], # Return top 20 for display
            "sentiment_trend": trend
        }


# Usage:
# analyzer = SentimentAnalyzer()
# result = analyzer.get_stock_sentiment("AAPL")
