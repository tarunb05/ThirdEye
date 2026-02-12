import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class CostTracker:
    def __init__(self):
        self.total_cost = 0.0
        self.requests = []
    
    def log_request(self, model: str, tokens: int, cost: float, latency: float):
        self.total_cost += cost
        self.requests.append({
            'model': model,
            'tokens': tokens,
            'cost': cost,
            'latency': latency,
            'timestamp': time.time()
        })
        logging.info(f'{model}: {tokens} tokens, \, {latency:.2f}s')

cost_tracker = CostTracker()
