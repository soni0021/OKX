import unittest
import asyncio
import config
from trade_simulator import OrderBook, almgren_chriss_impact, linear_slippage_estimate, fee_estimate, maker_taker_proportion

class TestTradeSimulator(unittest.TestCase):
    def setUp(self):
        self.orderbook = OrderBook()
        # Sample orderbook data
        self.sample_asks = [["50000.0", "1.5"], ["50100.0", "2.0"], ["50200.0", "1.0"]]
        self.sample_bids = [["49900.0", "2.5"], ["49800.0", "3.0"], ["49700.0", "1.5"]]
        
    def test_orderbook_update(self):
        self.orderbook.update(self.sample_asks, self.sample_bids)
        
        # Check if asks were updated correctly
        self.assertEqual(len(self.orderbook.asks), 3)
        self.assertEqual(self.orderbook.asks[50000.0], 1.5)
        self.assertEqual(self.orderbook.asks[50100.0], 2.0)
        self.assertEqual(self.orderbook.asks[50200.0], 1.0)
        
        # Check if bids were updated correctly
        self.assertEqual(len(self.orderbook.bids), 3)
        self.assertEqual(self.orderbook.bids[49900.0], 2.5)
        self.assertEqual(self.orderbook.bids[49800.0], 3.0)
        self.assertEqual(self.orderbook.bids[49700.0], 1.5)
        
        # Test removing entries (qty = 0)
        self.orderbook.update([["50000.0", "0"]], [["49800.0", "0"]])
        self.assertEqual(len(self.orderbook.asks), 2)
        self.assertNotIn(50000.0, self.orderbook.asks)
        self.assertEqual(len(self.orderbook.bids), 2)
        self.assertNotIn(49800.0, self.orderbook.bids)
    
    def test_best_prices(self):
        self.orderbook.update(self.sample_asks, self.sample_bids)
        
        # Check best ask (lowest ask price)
        self.assertEqual(self.orderbook.get_best_ask(), 50000.0)
        
        # Check best bid (highest bid price)
        self.assertEqual(self.orderbook.get_best_bid(), 49900.0)
        
        # Check mid price
        self.assertEqual(self.orderbook.get_mid_price(), 49950.0)
    
    def test_almgren_chriss_impact(self):
        order_size = 100.0
        volatility = 0.3
        
        # Calculate expected impact using the formula and config values
        expected_impact = config.IMPACT_GAMMA * order_size + config.IMPACT_ETA * order_size * volatility
        
        impact = almgren_chriss_impact(order_size, volatility)
        self.assertAlmostEqual(impact, expected_impact)
    
    def test_slippage_estimate(self):
        order_size = 200.0
        volatility = 0.25
        
        # Calculate expected slippage using the formula and config values
        expected_slippage = config.SLIPPAGE_INTERCEPT + config.SLIPPAGE_SLOPE * order_size * volatility
        
        slippage = linear_slippage_estimate(order_size, volatility)
        self.assertAlmostEqual(slippage, expected_slippage)
    
    def test_fee_estimate(self):
        order_size = 150.0
        fee_tier = 0.002
        
        # Test with explicit fee tier
        expected_fee = order_size * fee_tier
        fee = fee_estimate(order_size, fee_tier)
        self.assertAlmostEqual(fee, expected_fee)
        
        # Test with default fee tier from config
        expected_default_fee = order_size * config.DEFAULT_FEE_TIER
        default_fee = fee_estimate(order_size)
        self.assertAlmostEqual(default_fee, expected_default_fee)
    
    def test_maker_taker_proportion(self):
        import math
        
        # Test values below, at, and above the midpoint
        for order_size in [25.0, 50.0, 100.0]:
            expected = 1 / (1 + math.exp(-config.MAKER_TAKER_COEFFICIENT * (order_size - config.MAKER_TAKER_MIDPOINT)))
            proportion = maker_taker_proportion(order_size)
            self.assertAlmostEqual(proportion, expected)
        
        # Test extreme values
        self.assertLess(maker_taker_proportion(1.0), 0.5)  # Should be closer to 0
        self.assertGreater(maker_taker_proportion(1000.0), 0.5)  # Should be closer to 1

if __name__ == '__main__':
    unittest.main() 