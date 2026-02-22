import os
import sys
from dotenv import load_dotenv
from pdf_processor import extract_text_from_pdf
from agent import FinancialAnalystAgent
from report_generator import generate_pdf
import uuid

# Load environment variables
load_dotenv()

def main():
    print("--- Financial Analyst Agent ---")
    
    #Setup API Key
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        api_key = input("Enter your Groq API Key: ").strip()
        if not api_key:
            print("API Key is required to proceed.")
            return

    #Initialize Agent
    try:
        agent = FinancialAnalystAgent(api_key=api_key)
        print("Agent initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize agent: {e}")
        return

    #Get PDF Path
    pdf_path = input("Enter the path to the financial report PDF: ").strip()
    
    pdf_path = pdf_path.strip('"').strip("'")
    
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        
        
        return

    #Extract Text
    print("Extracting text from PDF...")
    text, _ = extract_text_from_pdf(pdf_path)
    if not text:
        print("Failed to extract text or PDF is empty.")
        return
    
    print(f"Extracted {len(text)} characters.")
    agent.set_context(text)

    #Interaction Loop
    print("\nYou can now ask questions about the financial report. Type 'exit' to quit.")
    while True:
        query = input("\nYou: ")
        if query.lower() in ["exit", "quit"]:
            break
        
        if query.lower() == "export":
            filename = f"financial_report_cli_{uuid.uuid4().hex[:8]}.pdf"
            print(f"Generating PDF report: {filename}...")
            try:
                generate_pdf(agent.history, filename)
                print(f"Report saved to {os.path.abspath(filename)}")
            except Exception as e:
                print(f"Error generating PDF: {e}")
            continue
        
        try:
            response = agent.run(query)
            print(f"Agent: {response}")
        except Exception as e:
            print(f"Error processing query: {e}")

if __name__ == "__main__":
    main()
