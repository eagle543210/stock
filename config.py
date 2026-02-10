import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Binance
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
    BINANCE_TESTNET = True # Default to True as per current code usage

    # Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PREDICTION_LOG_FILE = os.path.join(BASE_DIR, 'prediction_log.csv')
    TRADE_AUDIT_LOG = os.path.join(BASE_DIR, 'trade_audit.log')
    ERROR_MODEL_FILE = os.path.join(BASE_DIR, 'error_model.joblib')

    # Models
    MODEL_PATH_TEMPLATE = os.path.join(BASE_DIR, '{ticker}_model.joblib')

    # Settings
    SIGNAL_LOG_MAX_LEN = 100
    DEFAULT_TIMEFRAME = '5m'
    
    @classmethod
    def get_model_path(cls, ticker: str):
        # Handle cases where ticker has special chars like '/'
        safe_ticker = ticker.replace('/', '_').upper()
        # Handle cases where ticker is just a code like '600519' -> '600519'
        # Current logic has inconsistent naming:
        # Stock: ticker.upper().split('.')[0] (e.g. 600519.SH -> 600519)
        # Crypto: ticker.replace('/', '_').upper() (e.g. BTC/USDT -> BTC_USDT)
        
        if '.' in ticker: # Stock
             safe_ticker = ticker.upper().split('.')[0]
        
        return cls.MODEL_PATH_TEMPLATE.format(ticker=safe_ticker)

    # Proxy
    HTTP_PROXY = os.getenv('HTTP_PROXY')
    HTTPS_PROXY = os.getenv('HTTPS_PROXY')


config = Config()
