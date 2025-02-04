import requests
import logging
import json
import time
import datetime
import pandas as pd
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from telegram import Bot

# ---------------------------
# Config Loader
# ---------------------------
def load_config(config_path="config.json"):
    with open(config_path, "r") as f:
        config = json.load(f)
    return config

# ---------------------------
# DexScreener API Client Module
# ---------------------------
class DexscreenerClient:
    BASE_URL = "https://api.dexscreener.com"
    RATE_LIMIT_DELAY = 10  # Delay in seconds between requests

    def __init__(self):
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)

    def request_with_rate_limit(self, url):
        """ Handles API rate limits by retrying with delay """
        retries = 3
        for attempt in range(retries):
            response = self.session.get(url)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:  # Too Many Requests
                logging.warning("⚠️ Rate limit hit! Waiting before retrying...")
                time.sleep(self.RATE_LIMIT_DELAY * (attempt + 1))  # Exponential backoff
            else:
                logging.error(f"❌ API Request failed: {response.status_code} - {response.text}")
                break
    
    def get_latest_token_profiles(self):
        url = f"{self.BASE_URL}/token-profiles/latest/v1"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def get_latest_boosted_tokens(self):
        url = f"{self.BASE_URL}/token-boosts/latest/v1"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def get_top_boosted_tokens(self):
        url = f"{self.BASE_URL}/token-boosts/top/v1"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def search_pairs(self, query):
        url = f"{self.BASE_URL}/latest/dex/search"
        params = {"q": query}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    

# ---------------------------
# Telegram Notification Helper
# ---------------------------
def send_telegram_notification(message, config):
    """
    Sends a message via Telegram using BonkBot.
    Requires 'telegram' section in the config with 'bot_token' and 'chat_id'.
    """
    telegram_conf = config.get("telegram", {})
    bot_token = telegram_conf.get("bot_token")
    chat_id = telegram_conf.get("chat_id")
    if not bot_token or not chat_id:
        logging.warning("Telegram configuration missing; cannot send notification.")
        return
    try:
        bot = Bot(token=bot_token)
        bot.send_message(chat_id=chat_id, text=message)
        logging.info("Telegram notification sent.")
    except Exception as e:
        logging.error(f"Error sending Telegram notification: {e}")

# ---------------------------
# Data Storage Module using SQLAlchemy
# ---------------------------
Base = declarative_base()

class TokenSnapshot(Base):
    __tablename__ = 'token_snapshots'
    id = Column(Integer, primary_key=True)
    token_address = Column(String, index=True)
    chain_id = Column(String)
    icon = Column(String)
    description = Column(String)
    links = Column(JSON)
    price_usd = Column(Float)
    liquidity = Column(Float)
    volume_usd = Column(Float)
    developer = Column(String)  # Optional field
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

engine = create_engine('sqlite:///dexscreener_data.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


# ---------------------------
# Analysis Module
# ---------------------------
def analyze_token_trends(session, config):
    query = session.query(TokenSnapshot)
    data = [{
        'token_address': snap.token_address,
        'price_usd': snap.price_usd,
        'liquidity': snap.liquidity,
        'volume_usd': snap.volume_usd,
        'timestamp': snap.timestamp
    } for snap in query.all()]
    
    df = pd.DataFrame(data)
    if df.empty:
        return []
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    
    flagged = []
    for token, group in df.groupby('token_address'):
        group = group.set_index('timestamp')
        hourly = group['price_usd'].resample('1H').last().dropna()
        if len(hourly) < 2:
            continue
        change = (hourly.iloc[-1] - hourly.iloc[0]) / hourly.iloc[0] * 100
        if change > 50:
            flagged.append((token, change))
    
    return flagged





