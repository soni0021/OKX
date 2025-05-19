import asyncio
import json
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import logging
import sys
import os
import argparse
from collections import deque

from trade_simulator import OrderBook, TradeSimulatorUI, almgren_chriss_impact, linear_slippage_estimate, fee_estimate, maker_taker_proportion
import config

# --- Set up logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('OfflineSimulator')

class OfflineDataSimulator:
    """Class to simulate WebSocket connection using offline data"""
    def __init__(self, orderbook, data_file, replay_speed=1.0):
        self.orderbook = orderbook
        self.data_file = data_file
        self.replay_speed = replay_speed
        self.connected = False
        self.paused = False
        self.latency = deque(maxlen=100)
        self.current_index = 0
        self.data = []
        self.stop_event = threading.Event()
    
    def load_data(self):
        """Load data from file"""
        try:
            with open(self.data_file, 'r') as f:
                self.data = json.load(f)
            logger.info(f"Loaded {len(self.data)} orderbook samples from {self.data_file}")
            return True
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error loading data file: {e}")
            return False
    
    def start(self):
        """Start the simulator"""
        if self.load_data():
            self.connected = True
            self.stop_event.clear()
            threading.Thread(target=self.replay_data, daemon=True).start()
            return True
        return False
    
    def stop(self):
        """Stop the simulator"""
        self.stop_event.set()
        self.connected = False
    
    def pause(self):
        """Pause the simulator"""
        self.paused = True
    
    def resume(self):
        """Resume the simulator"""
        self.paused = False
    
    def replay_data(self):
        """Replay the data at specified speed"""
        try:
            while not self.stop_event.is_set() and self.current_index < len(self.data):
                if not self.paused:
                    start_time = time.time()
                    
                    # Get next sample
                    sample = self.data[self.current_index]
                    
                    # Update orderbook
                    self.orderbook.update(sample.get("asks", []), sample.get("bids", []))
                    
                    # Move to next sample
                    self.current_index += 1
                    
                    # Calculate processing time
                    processing_time = time.time() - start_time
                    self.latency.append(processing_time)
                    
                    # Sleep to maintain replay speed
                    delay = (1.0 / self.replay_speed) - processing_time
                    if delay > 0:
                        time.sleep(delay)
                    
                    # Log progress periodically
                    if self.current_index % 10 == 0:
                        logger.info(f"Processed {self.current_index}/{len(self.data)} samples")
                else:
                    # When paused, just sleep a bit
                    time.sleep(0.1)
            
            # If we've reached the end, start over
            if self.current_index >= len(self.data) and not self.stop_event.is_set():
                logger.info("Reached end of data, restarting")
                self.current_index = 0
                self.replay_data()
                
        except Exception as e:
            logger.error(f"Error in replay_data: {e}")
            self.connected = False
    
    def is_connected(self):
        """Return connection status"""
        return self.connected
    
    def get_average_latency(self):
        """Return average latency"""
        return (sum(self.latency) / len(self.latency)) if self.latency else 0

class OfflineSimulatorUI(TradeSimulatorUI):
    """Extended UI for offline simulator with playback controls"""
    def __init__(self, root, orderbook, simulator):
        super().__init__(root, orderbook, simulator)
        
        # Add replay controls
        self.control_frame = ttk.Frame(root, padding="5")
        self.control_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        
        # Add speed control
        ttk.Label(self.control_frame, text="Replay Speed:").pack(side="left", padx=5)
        self.speed_var = tk.DoubleVar(value=simulator.replay_speed)
        speed_options = [0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
        speed_menu = ttk.OptionMenu(self.control_frame, self.speed_var, simulator.replay_speed, *speed_options, 
                                     command=self.change_speed)
        speed_menu.pack(side="left", padx=5)
        
        # Add control buttons
        self.pause_button = ttk.Button(self.control_frame, text="Pause", command=self.toggle_pause)
        self.pause_button.pack(side="left", padx=5)
        
        self.restart_button = ttk.Button(self.control_frame, text="Restart", command=self.restart_simulation)
        self.restart_button.pack(side="left", padx=5)
        
        # Add progress info
        self.progress_var = tk.StringVar(value="0/0")
        ttk.Label(self.control_frame, text="Progress:").pack(side="left", padx=5)
        ttk.Label(self.control_frame, textvariable=self.progress_var).pack(side="left", padx=5)
        
        # Update UI with progress information
        self.update_ui()
    
    def toggle_pause(self):
        """Toggle pause/resume"""
        simulator = self.ws_client  # Using the same variable name for compatibility
        if simulator.paused:
            simulator.resume()
            self.pause_button.config(text="Pause")
        else:
            simulator.pause()
            self.pause_button.config(text="Resume")
    
    def restart_simulation(self):
        """Restart the simulation from beginning"""
        simulator = self.ws_client
        simulator.current_index = 0
        self.connection_status_var.set("Restarted simulation")
    
    def change_speed(self, value):
        """Change replay speed"""
        self.ws_client.replay_speed = float(value)
    
    def update_ui(self):
        """Override to add progress updates"""
        super().update_ui()
        
        # Update progress
        simulator = self.ws_client
        if hasattr(simulator, 'current_index') and hasattr(simulator, 'data'):
            self.progress_var.set(f"{simulator.current_index}/{len(simulator.data)}")
        
        # Schedule next update
        self.root.after(config.UI_REFRESH_RATE, self.update_ui)

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Run the trade simulator with offline data")
    parser.add_argument("--data", type=str, default="test_data.json", help="JSON file with orderbook data")
    parser.add_argument("--speed", type=float, default=1.0, help="Replay speed multiplier")
    args = parser.parse_args()
    
    try:
        logger.info("Starting Offline Trade Simulator")
        
        # Check if data file exists
        if not os.path.exists(args.data):
            logger.error(f"Data file not found: {args.data}")
            logger.info("Generating test data first...")
            from generate_test_data import generate_test_data_file
            generate_test_data_file(filename=args.data)
        
        # Create orderbook
        orderbook = OrderBook()
        
        # Create simulator
        simulator = OfflineDataSimulator(orderbook, args.data, args.speed)
        
        # Start simulator
        if not simulator.start():
            logger.error("Failed to start simulator")
            sys.exit(1)
        
        # Create UI
        root = tk.Tk()
        app = OfflineSimulatorUI(root, orderbook, simulator)
        
        # Set window title
        root.title(f"GoQuant Trade Simulator - Offline Mode - {os.path.basename(args.data)}")
        
        # Start UI main loop
        root.mainloop()
    except Exception as e:
        logger.error(f"Critical error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 