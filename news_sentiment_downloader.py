# -*- coding: utf-8 -*-
import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# --- 配置 ---
DATA_CACHE_DIR = 'stock_data_cache'
NEWS_SENTIMENT_FILE = os.path.join(DATA_CACHE_DIR, 'factor_news_sentiment_daily.csv')

# --- 加载环境变量 ---
load_dotenv()
NEWS_API_KEY = os.getenv('NEWS_API_KEY')

# --- NLTK VADER 初始化 ---
def initialize_nltk_vader():
    """下载并初始化 NLTK VADER 情感分析所需的数据"""
    try:
        nltk.data.find('sentiment/vader_lexicon.zip')
        print("NLTK VADER lexicon 已存在。")
    except LookupError:
        print("正在下载 NLTK VADER lexicon...")
        nltk.download('vader_lexicon')
        print("下载完成。")

initialize_nltk_vader()
sia = SentimentIntensityAnalyzer()

def get_news_sentiment(days_ago=30):
    """
    从 NewsAPI 获取过去 N 天的金融新闻，并计算每日的平均情绪分数。
    """
    if not NEWS_API_KEY:
        print("错误: 未在 .env 文件中找到 NEWS_API_KEY。")
        return

    print("开始从 NewsAPI 获取新闻头条...")
    
    all_sentiments = []
    
    # 循环获取过去每一天的新闻
    for i in range(min(days_ago, 29)):
        date = datetime.now() - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        
        print(f"正在获取 {date_str} 的新闻...")

        # 搜索与金融市场相关的关键词
        keywords = "stock market OR finance OR economy OR investing OR trading"
        
        url = ('https://newsapi.org/v2/everything?'
               f'q={keywords}&'
               f'from={date_str}&'
               f'to={date_str}&'
               'sortBy=publishedAt&'
               'language=en&'  # VADER 对英文情绪分析效果最好
               f'apiKey={NEWS_API_KEY}')

        try:
            response = requests.get(url)
            response.raise_for_status()
            articles = response.json().get('articles', [])
            
            if not articles:
                print(f"警告: 未能从 NewsAPI 获取到 {date_str} 的任何新闻文章。")
                continue

            # --- 计算情绪分数 ---
            for article in articles:
                title = article.get('title', '')
                if title:
                    sentiment_score = sia.polarity_scores(title)['compound']
                    all_sentiments.append({'date': date_str, 'sentiment_score': sentiment_score})

        except requests.exceptions.RequestException as e:
            print(f"❌ 请求 NewsAPI 时发生错误 ({date_str}): {e}")
        except Exception as e:
            print(f"❌ 处理新闻数据时发生未知错误 ({date_str}): {e}")

    if not all_sentiments:
        print("警告: 在指定日期范围内无法计算任何情绪分数。")
        return

    # --- 按天聚合情绪分数 ---
    df = pd.DataFrame(all_sentiments)
    daily_sentiment = df.groupby('date')['sentiment_score'].mean().reset_index()
    daily_sentiment.rename(columns={'sentiment_score': 'news_sentiment'}, inplace=True)
    
    print("每日平均情绪分数计算完成。")
    
    # --- 更新并保存到 CSV 文件 ---
    if not os.path.exists(DATA_CACHE_DIR):
        os.makedirs(DATA_CACHE_DIR)

    if os.path.exists(NEWS_SENTIMENT_FILE):
        try:
            existing_df = pd.read_csv(NEWS_SENTIMENT_FILE)
            combined_df = pd.concat([existing_df, daily_sentiment])
            combined_df.drop_duplicates(subset='date', keep='last', inplace=True)
            combined_df.sort_values(by='date', inplace=True)
            final_df = combined_df
        except pd.errors.EmptyDataError:
            final_df = daily_sentiment
    else:
        final_df = daily_sentiment
    
    final_df.to_csv(NEWS_SENTIMENT_FILE, index=False)
    print(f"✅ 成功将新闻情绪因子更新并保存至 {NEWS_SENTIMENT_FILE}")

if __name__ == '__main__':
    print("--- 开始执行新闻情绪因子下载脚本 ---")
    get_news_sentiment()
    print("--- 新闻情绪因子下载脚本执行完毕 ---")
