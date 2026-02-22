import os
import time
from dotenv import load_dotenv
from agent import FinancialAnalystAgent

# Load env for API keys
load_dotenv()

def test_large_context():
    print("Initializing Agent...")
    try:
        agent = FinancialAnalystAgent()
    except Exception as e:
        print(f"Failed to init agent: {e}")
        return

    # Create dummy large context (> 20k chars)
    print("Generating large context...")
    large_text = "This is a financial report for International Business Machines Corporation (IBM). " * 500
    large_text += "\nTicker: IBM\n"
    large_text += "Fiscal Year: 2024\n"
    large_text += "Revenue: $60.5 Billion\n" * 100
    large_text += "Risks: " + "Market volatility is high. " * 500
    
    print(f"Context Length: {len(large_text)} chars")
    
    agent.set_context(large_text)
    
    print("\n--- Testing extract_metadata ---")
    start = time.time()
    meta = agent.extract_metadata()
    print(f"Metadata Result: {meta}")
    print(f"Time taken: {time.time() - start:.2f}s")
    
    print("\n--- Testing extract_metrics ---")
    start = time.time()
    metrics = agent.extract_metrics()
    
    if metrics:
        print("Metrics Extraction Successful!")
        print(f"Keys found: {list(metrics.keys())}")
    else:
        print("Metrics Extraction Failed (None returned)")
        
    print(f"Time taken: {time.time() - start:.2f}s")

if __name__ == "__main__":
    test_large_context()
