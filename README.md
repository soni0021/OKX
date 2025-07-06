# Trade Simulator

A high-performance trade simulator that connects to OKX's WebSocket API to process L2 orderbook data for cryptocurrency trading. The system estimates transaction costs and market impact while maintaining high performance.

## Features

- Real-time L2 orderbook processing with thread-safe updates
- UI for input and output using Tkinter with live updates
- Models for slippage, fees, market impact, and maker/taker prediction
- Performance-optimized with threading, efficient data structures, and latency measurement
- Well-documented and modular for maintainability and extension

## Installation

1. Clone this repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the trade simulator:

```bash
python trade_simulator.py
```

The application will:
1. Connect to OKX WebSocket for L2 orderbook data
2. Display a UI with input parameters and calculated outputs
3. Update the calculations in real-time

## Input Parameters

- **Exchange**: The cryptocurrency exchange (default: OKX)
- **Spot Asset**: The trading pair (default: BTC-USDT-SWAP)
- **Order Type**: The type of order (default: market)
- **Quantity (USD)**: The order size in USD
- **Volatility**: The volatility parameter used in calculations
- **Fee Tier**: The fee tier parameter used in calculations

## Output Metrics

- **Expected Slippage**: Estimated price difference between expected and actual execution
- **Expected Fees**: Estimated transaction fees
- **Expected Market Impact**: Estimated price impact of the order
- **Net Cost**: Total transaction cost
- **Maker/Taker Proportion**: Estimated proportion of order filled as maker vs taker
- **Internal Latency**: Processing latency in milliseconds

## Models

The simulator implements several financial models:

1. **Almgren-Chriss Impact Model**: For market impact estimation
2. **Linear Slippage Model**: For slippage estimation
3. **Fee Model**: For transaction fee calculation
4. **Maker/Taker Model**: For estimating execution path

## Requirements

- Python 3.7+
- GUI environment for Tkinter
- Network access for WebSocket streaming

## Notes

For production use, further error handling, logging, and configuration management are recommended. 
