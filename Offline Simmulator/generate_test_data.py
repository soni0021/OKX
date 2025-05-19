import json
import random
import time
import os
import argparse

def generate_orderbook_data(base_price=50000.0, spread=10.0, depth=20, vol_factor=1.0):
    """
    Generate realistic orderbook data
    
    Args:
        base_price (float): Base price for the asset
        spread (float): Spread between best bid and ask
        depth (int): Number of levels on each side
        vol_factor (float): Volume factor to scale quantities
        
    Returns:
        dict: Orderbook data with asks and bids
    """
    # Generate asks
    asks = []
    ask_start = base_price + spread / 2
    for i in range(depth):
        price = ask_start + i * (ask_start * 0.0002)  # 0.02% steps
        qty = random.uniform(0.5, 5.0) * vol_factor / (1 + i * 0.1)  # Decreasing volume with distance
        asks.append([str(price), str(qty)])
    
    # Generate bids
    bids = []
    bid_start = base_price - spread / 2
    for i in range(depth):
        price = bid_start - i * (bid_start * 0.0002)  # 0.02% steps
        qty = random.uniform(0.5, 5.0) * vol_factor / (1 + i * 0.1)  # Decreasing volume with distance
        bids.append([str(price), str(qty)])
    
    return {
        "asks": asks,
        "bids": bids,
        "timestamp": int(time.time() * 1000)
    }

def generate_test_data_file(num_samples=100, filename="test_data.json", volatility=0.001):
    """
    Generate a series of orderbook updates and save to a file
    
    Args:
        num_samples (int): Number of orderbook samples to generate
        filename (str): Output filename
        volatility (float): Price volatility between samples
    """
    samples = []
    current_price = 50000.0  # Starting price
    
    for i in range(num_samples):
        # Random walk the price
        price_change = current_price * random.uniform(-volatility, volatility)
        current_price += price_change
        
        # Generate orderbook
        data = generate_orderbook_data(base_price=current_price, 
                                      spread=current_price * 0.0002,  # 0.02% spread
                                      depth=20,
                                      vol_factor=1.0 + random.uniform(-0.2, 0.2))  # Volume fluctuations
        
        # Add some empty or zero volume entries randomly
        if random.random() < 0.1:  # 10% chance
            idx = random.randint(0, len(data["asks"]) - 1)
            data["asks"][idx][1] = "0"
        
        if random.random() < 0.1:  # 10% chance
            idx = random.randint(0, len(data["bids"]) - 1)
            data["bids"][idx][1] = "0"
        
        samples.append(data)
        
    # Save to file
    with open(filename, 'w') as f:
        json.dump(samples, f, indent=2)
    
    print(f"Generated {num_samples} orderbook samples and saved to {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate test orderbook data")
    parser.add_argument("--samples", type=int, default=100, help="Number of samples to generate")
    parser.add_argument("--output", type=str, default="test_data.json", help="Output filename")
    parser.add_argument("--volatility", type=float, default=0.001, help="Price volatility between samples")
    
    args = parser.parse_args()
    
    generate_test_data_file(num_samples=args.samples, 
                           filename=args.output,
                           volatility=args.volatility) 