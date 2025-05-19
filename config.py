import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# WebSocket Configuration
WS_URL = os.getenv("WS_URL", "wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP")
PING_INTERVAL = int(os.getenv("PING_INTERVAL", "20"))

# Reconnection Configuration
MAX_RECONNECT_ATTEMPTS = int(os.getenv("MAX_RECONNECT_ATTEMPTS", "5"))
INITIAL_RECONNECT_DELAY = int(os.getenv("INITIAL_RECONNECT_DELAY", "2"))
MAX_RECONNECT_DELAY = int(os.getenv("MAX_RECONNECT_DELAY", "30"))

# Orderbook Configuration
STALE_DATA_THRESHOLD = int(os.getenv("STALE_DATA_THRESHOLD", "10"))  # seconds

# Default Trading Parameters
DEFAULT_EXCHANGE = os.getenv("DEFAULT_EXCHANGE", "OKX")
DEFAULT_ASSET = os.getenv("DEFAULT_ASSET", "BTC-USDT-SWAP")
DEFAULT_ORDER_TYPE = os.getenv("DEFAULT_ORDER_TYPE", "market")
DEFAULT_QUANTITY = float(os.getenv("DEFAULT_QUANTITY", "100.0"))
DEFAULT_VOLATILITY = float(os.getenv("DEFAULT_VOLATILITY", "0.3"))
DEFAULT_FEE_TIER = float(os.getenv("DEFAULT_FEE_TIER", "0.001"))

# Model Parameters
IMPACT_GAMMA = float(os.getenv("IMPACT_GAMMA", "0.1"))  # temporary impact coefficient
IMPACT_ETA = float(os.getenv("IMPACT_ETA", "0.05"))     # permanent impact coefficient
SLIPPAGE_SLOPE = float(os.getenv("SLIPPAGE_SLOPE", "0.0001"))
SLIPPAGE_INTERCEPT = float(os.getenv("SLIPPAGE_INTERCEPT", "0.0005"))
MAKER_TAKER_COEFFICIENT = float(os.getenv("MAKER_TAKER_COEFFICIENT", "0.01"))
MAKER_TAKER_MIDPOINT = float(os.getenv("MAKER_TAKER_MIDPOINT", "50.0"))

# UI Configuration
UI_REFRESH_RATE = int(os.getenv("UI_REFRESH_RATE", "500"))  # milliseconds
UI_WINDOW_SIZE = os.getenv("UI_WINDOW_SIZE", "800x500") 