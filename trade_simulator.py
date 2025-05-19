import asyncio
import websockets
import json
import time
from collections import deque
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import logging
import sys
try:
    import config
except ImportError:
    # Create minimal config if module is missing
    class DefaultConfig:
        WS_URL = "wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP"
        PING_INTERVAL = 20
        MAX_RECONNECT_ATTEMPTS = 5
        INITIAL_RECONNECT_DELAY = 2
        MAX_RECONNECT_DELAY = 30
        STALE_DATA_THRESHOLD = 10
        DEFAULT_EXCHANGE = "OKX"
        DEFAULT_ASSET = "BTC-USDT-SWAP"
        DEFAULT_ORDER_TYPE = "market"
        DEFAULT_QUANTITY = 100.0
        DEFAULT_VOLATILITY = 0.3
        DEFAULT_FEE_TIER = 0.001
        IMPACT_GAMMA = 0.1
        IMPACT_ETA = 0.05
        SLIPPAGE_SLOPE = 0.0001
        SLIPPAGE_INTERCEPT = 0.0005
        MAKER_TAKER_COEFFICIENT = 0.01
        MAKER_TAKER_MIDPOINT = 50.0
        UI_REFRESH_RATE = 500
        UI_WINDOW_SIZE = "800x500"
    
    config = DefaultConfig()
    print("Warning: config.py not found, using default values")

# --- Set up logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('TradeSimulator')

# --- Constants ---
WS_URL = "wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP"

# --- Orderbook Data Structure ---
class OrderBook:
    def __init__(self):
        self.asks = {}  # price: quantity
        self.bids = {}  # price: quantity
        self.lock = threading.Lock()
        self.last_update_time = 0

    def update(self, asks, bids):
        with self.lock:
            for price, qty in asks:
                try:
                    price_f = float(price)
                    qty_f = float(qty)
                    if qty_f == 0:
                        self.asks.pop(price_f, None)
                    else:
                        self.asks[price_f] = qty_f
                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing ask data: {e}")
            
            for price, qty in bids:
                try:
                    price_f = float(price)
                    qty_f = float(qty)
                    if qty_f == 0:
                        self.bids.pop(price_f, None)
                    else:
                        self.bids[price_f] = qty_f
                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing bid data: {e}")
            
            self.last_update_time = time.time()

    def get_best_ask(self):
        with self.lock:
            return min(self.asks.keys()) if self.asks else None

    def get_best_bid(self):
        with self.lock:
            return max(self.bids.keys()) if self.bids else None

    def get_mid_price(self):
        best_ask = self.get_best_ask()
        best_bid = self.get_best_bid()
        return (best_ask + best_bid) / 2 if best_ask and best_bid else None
    
    def is_stale(self, max_age_seconds=None):
        """Check if orderbook data is stale"""
        max_age = max_age_seconds or config.STALE_DATA_THRESHOLD
        return time.time() - self.last_update_time > max_age

# --- Models ---

def almgren_chriss_impact(order_size, volatility, time_horizon=1.0, risk_aversion=0.1):
    try:
        gamma = config.IMPACT_GAMMA
        eta = config.IMPACT_ETA
        impact = gamma * order_size + eta * order_size * volatility * time_horizon
        return impact
    except Exception as e:
        logger.error(f"Error calculating Almgren-Chriss impact: {e}")
        return 0.0

def linear_slippage_estimate(order_size, volatility):
    try:
        slope = config.SLIPPAGE_SLOPE
        intercept = config.SLIPPAGE_INTERCEPT
        slippage = intercept + slope * order_size * volatility
        return slippage
    except Exception as e:
        logger.error(f"Error calculating slippage: {e}")
        return 0.0

def fee_estimate(order_size, fee_tier=None):
    try:
        fee = fee_tier or config.DEFAULT_FEE_TIER
        return order_size * fee
    except Exception as e:
        logger.error(f"Error calculating fees: {e}")
        return 0.0

def maker_taker_proportion(order_size):
    try:
        import math
        coef = config.MAKER_TAKER_COEFFICIENT
        midpoint = config.MAKER_TAKER_MIDPOINT
        return 1 / (1 + math.exp(-coef * (order_size - midpoint)))
    except Exception as e:
        logger.error(f"Error calculating maker/taker proportion: {e}")
        return 0.5

# --- WebSocket Client ---
class OKXWebSocketClient:
    def __init__(self, url, orderbook):
        self.url = url
        self.orderbook = orderbook
        self.ws = None
        self.latency = deque(maxlen=100)
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = config.MAX_RECONNECT_ATTEMPTS
        self.reconnect_delay = config.INITIAL_RECONNECT_DELAY
        self.running = True
        self.connect_lock = threading.Lock()

    async def connect(self):
        while self.running:
            try:
                with self.connect_lock:
                    if not self.connected:
                        logger.info(f"Connecting to {self.url}")
                        self.ws = await websockets.connect(
                            self.url, 
                            ping_interval=config.PING_INTERVAL,
                            ping_timeout=60,  # Increased ping timeout
                            close_timeout=10,
                            max_size=10_000_000  # Increased message size limit
                        )
                        self.connected = True
                        self.reconnect_attempts = 0
                        self.reconnect_delay = config.INITIAL_RECONNECT_DELAY
                        logger.info("WebSocket connected")
                        await self.subscribe()
                        await self.receive()
            except websockets.exceptions.WebSocketException as e:
                self.connected = False
                self.reconnect_attempts += 1
                logger.error(f"WebSocket connection error: {e}, attempt {self.reconnect_attempts}")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(config.MAX_RECONNECT_DELAY, self.reconnect_delay * 1.5)
            except Exception as e:
                self.connected = False
                logger.error(f"Unexpected connection error: {e}")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(config.MAX_RECONNECT_DELAY, self.reconnect_delay * 1.5)
            finally:
                # Always try to reconnect, don't give up after max_reconnect_attempts
                await asyncio.sleep(1)

    async def subscribe(self):
        try:
            sub_msg = {
                "op": "subscribe",
                "args": [{"channel": "l2-orderbook", "instId": config.DEFAULT_ASSET}]
            }
            await self.ws.send(json.dumps(sub_msg))
            logger.info("Subscribed to orderbook channel")
        except Exception as e:
            logger.error(f"Subscription error: {e}")
            self.connected = False
            raise

    async def receive(self):
        try:
            async for message in self.ws:
                start_time = time.time()
                try:
                    data = json.loads(message)
                    if "asks" in data and "bids" in data:
                        self.orderbook.update(data["asks"], data["bids"])
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                end_time = time.time()
                self.latency.append(end_time - start_time)
        except Exception as e:
            logger.error(f"WebSocket receive error: {e}")
            self.connected = False
            raise

    def get_average_latency(self):
        return (sum(self.latency) / len(self.latency)) if self.latency else 0

    def is_connected(self):
        return self.connected
        
    def shutdown(self):
        self.running = False

# --- UI ---
class TradeSimulatorUI:
    def __init__(self, root, orderbook, ws_client):
        self.root = root
        self.orderbook = orderbook
        self.ws_client = ws_client

        self.root.title("GoQuant Trade Simulator")
        self.root.geometry(config.UI_WINDOW_SIZE)
        
        # Configure grid
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        self.left_frame = ttk.Frame(root, padding="10")
        self.left_frame.grid(row=0, column=0, sticky="nsew")
        self.right_frame = ttk.Frame(root, padding="10")
        self.right_frame.grid(row=0, column=1, sticky="nsew")
        
        # Status frame at the bottom
        self.status_frame = ttk.Frame(root, padding="5")
        self.status_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.connection_status_var = tk.StringVar(value="Connecting...")
        self.status_label = ttk.Label(self.status_frame, textvariable=self.connection_status_var)
        self.status_label.pack(side="left")

        # Input Panel
        ttk.Label(self.left_frame, text="Input Parameters", font=('Helvetica', 12, 'bold')).grid(row=0, column=0, columnspan=2, pady=10)
        
        self.exchange_var = tk.StringVar(value=config.DEFAULT_EXCHANGE)
        self.asset_var = tk.StringVar(value=config.DEFAULT_ASSET)
        self.order_type_var = tk.StringVar(value=config.DEFAULT_ORDER_TYPE)
        self.quantity_var = tk.DoubleVar(value=config.DEFAULT_QUANTITY)
        self.volatility_var = tk.DoubleVar(value=config.DEFAULT_VOLATILITY)
        self.fee_tier_var = tk.DoubleVar(value=config.DEFAULT_FEE_TIER)

        inputs = [
            ("Exchange:", self.exchange_var, 'readonly'),
            ("Spot Asset:", self.asset_var, 'readonly'),
            ("Order Type:", self.order_type_var, 'readonly'),
            ("Quantity (USD):", self.quantity_var, None),
            ("Volatility:", self.volatility_var, None),
            ("Fee Tier:", self.fee_tier_var, None),
        ]
        for i, (label, var, state) in enumerate(inputs):
            ttk.Label(self.left_frame, text=label).grid(row=i+1, column=0, sticky="w", pady=5)
            entry = ttk.Entry(self.left_frame, textvariable=var, state=state) if state else ttk.Entry(self.left_frame, textvariable=var)
            entry.grid(row=i+1, column=1, pady=5, padx=5, sticky="ew")

        # Add a separator
        ttk.Separator(self.left_frame, orient='horizontal').grid(row=len(inputs)+1, column=0, columnspan=2, sticky='ew', pady=10)
        
        # Add order book info
        ttk.Label(self.left_frame, text="Order Book Info", font=('Helvetica', 12, 'bold')).grid(row=len(inputs)+2, column=0, columnspan=2, pady=10)
        
        self.best_bid_var = tk.StringVar(value="N/A")
        self.best_ask_var = tk.StringVar(value="N/A")
        self.mid_price_var = tk.StringVar(value="N/A")
        
        orderbook_items = [
            ("Best Bid:", self.best_bid_var),
            ("Best Ask:", self.best_ask_var),
            ("Mid Price:", self.mid_price_var),
        ]
        
        for i, (label, var) in enumerate(orderbook_items):
            ttk.Label(self.left_frame, text=label).grid(row=len(inputs)+3+i, column=0, sticky="w", pady=5)
            ttk.Label(self.left_frame, textvariable=var).grid(row=len(inputs)+3+i, column=1, sticky="w", pady=5)

        # Output Panel
        ttk.Label(self.right_frame, text="Trade Metrics", font=('Helvetica', 12, 'bold')).grid(row=0, column=0, columnspan=2, pady=10)
        
        self.slippage_var = tk.StringVar(value="N/A")
        self.fees_var = tk.StringVar(value="N/A")
        self.market_impact_var = tk.StringVar(value="N/A")
        self.net_cost_var = tk.StringVar(value="N/A")
        self.maker_taker_var = tk.StringVar(value="N/A")
        self.latency_var = tk.StringVar(value="N/A")

        outputs = [
            ("Expected Slippage:", self.slippage_var),
            ("Expected Fees:", self.fees_var),
            ("Expected Market Impact:", self.market_impact_var),
            ("Net Cost:", self.net_cost_var),
            ("Maker/Taker Proportion:", self.maker_taker_var),
            ("Internal Latency (ms):", self.latency_var),
        ]
        for i, (label, var) in enumerate(outputs):
            ttk.Label(self.right_frame, text=label).grid(row=i+1, column=0, sticky="w", pady=5)
            ttk.Label(self.right_frame, textvariable=var).grid(row=i+1, column=1, sticky="w", pady=5)

        # Start UI update
        self.update_ui()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def update_ui(self):
        try:
            # Update connection status
            if self.ws_client.is_connected():
                self.connection_status_var.set("Connected to OKX")
                self.status_label.config(foreground="green")
            else:
                self.connection_status_var.set("Disconnected from OKX")
                self.status_label.config(foreground="red")
            
            # Update orderbook info
            best_bid = self.orderbook.get_best_bid()
            best_ask = self.orderbook.get_best_ask()
            mid_price = self.orderbook.get_mid_price()
            
            self.best_bid_var.set(f"{best_bid:.2f}" if best_bid else "N/A")
            self.best_ask_var.set(f"{best_ask:.2f}" if best_ask else "N/A")
            self.mid_price_var.set(f"{mid_price:.2f}" if mid_price else "N/A")
            
            # Check if orderbook is stale
            if self.orderbook.is_stale():
                self.status_label.config(foreground="orange")
                self.connection_status_var.set("Warning: Orderbook data is stale")
            
            # Update trade metrics
            quantity = self.quantity_var.get()
            volatility = self.volatility_var.get()
            fee_tier = self.fee_tier_var.get()

            slippage = linear_slippage_estimate(quantity, volatility)
            fees = fee_estimate(quantity, fee_tier)
            market_impact = almgren_chriss_impact(quantity, volatility)
            net_cost = slippage + fees + market_impact
            maker_taker = maker_taker_proportion(quantity)
            latency = self.ws_client.get_average_latency() * 1000 if self.ws_client else 0

            self.slippage_var.set(f"{slippage:.6f}")
            self.fees_var.set(f"{fees:.6f}")
            self.market_impact_var.set(f"{market_impact:.6f}")
            self.net_cost_var.set(f"{net_cost:.6f}")
            self.maker_taker_var.set(f"{maker_taker:.4f}")
            self.latency_var.set(f"{latency:.2f}")
            
        except Exception as e:
            logger.error(f"Error updating UI: {e}")
        finally:
            # Schedule next update
            self.root.after(config.UI_REFRESH_RATE, self.update_ui)
    
    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit the application?"):
            logger.info("Application closing")
            self.root.destroy()
            sys.exit(0)

def start_ws_client(orderbook, ws_client_holder):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        client = OKXWebSocketClient(config.WS_URL, orderbook)
        ws_client_holder.append(client)
        loop.run_until_complete(client.connect())
    except Exception as e:
        logger.error(f"Error in WebSocket client thread: {e}")
    finally:
        # Keep the thread alive, never exit
        while True:
            try:
                time.sleep(1)
            except:
                break

def main():
    try:
        logger.info("Starting Trade Simulator")
        orderbook = OrderBook()
        ws_client_holder = []

        # Start WebSocket client in a separate thread
        ws_thread = threading.Thread(target=start_ws_client, args=(orderbook, ws_client_holder), daemon=True)
        ws_thread.start()

        # Create a placeholder client in case the WebSocket connection fails
        placeholder_client = type('obj', (object,), {
            'is_connected': lambda: False,
            'get_average_latency': lambda: 0,
            'shutdown': lambda: None
        })

        # Wait briefly for WebSocket client initialization, but proceed with UI anyway
        time.sleep(2)  # Reduced timeout to make UI appear faster
        
        ws_client = ws_client_holder[0] if ws_client_holder else placeholder_client
        
        # Initialize and start Tkinter UI
        root = tk.Tk()
        app = TradeSimulatorUI(root, orderbook, ws_client)
        
        # Handle proper cleanup on exit
        def on_exit():
            if ws_client_holder and ws_client_holder[0]:
                ws_client_holder[0].shutdown()
            root.destroy()
            
        root.protocol("WM_DELETE_WINDOW", on_exit)
        root.mainloop()
    except Exception as e:
        logger.error(f"Critical error in main: {e}")
        # Display a messagebox with the error
        try:
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            messagebox.showerror("Error", f"Failed to start application: {e}")
            root.destroy()
        except:
            pass
        sys.exit(1)

if __name__ == '__main__':
    main() 