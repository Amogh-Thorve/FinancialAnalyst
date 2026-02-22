# FinAnalyst: Agentic Financial Reasoning System

FinAnalyst is a powerful "Agentic" financial analysis tool designed to transform unstructured financial data (like PDF annual reports) or simple stock tickers into a comprehensive, verified, and interactive dashboard.

It leverages a multi-layered approach combining AI reasoning, real-time market data enrichment, and automated validation to provide high-fidelity financial insights.

## 🚀 Key Features

- **Agentic PDF Analysis**: Upload a PDF (e.g., an annual report) and have the agent extract core financial metrics automatically.
- **Real-time Data Enrichment**: Integrates with Alpha Vantage to fetch live stock prices, fundamentals, and historical data to verify and supplement extracted information.
- **Sentiment Market Pulse**: Scans global news via NewsAPI and performs VADER sentiment analysis to gauge market mood.
- **Automated Verification**: Includes a `MetricsValidator` that cross-references AI-extracted data with raw PDF text to prevent hallucinations.
- **Interactive Dashboard**: A modern, glassmorphic UI featuring Chart.js visualizations for financial stability benchmarking, risk radar, and stock trends.
- **Streaming Chat Interface**: Talk to the expert financial agent in real-time. It can use tools to look up stocks, forecast trends, and plot interactive charts.
- **PDF Report Export**: Export your entire analysis session into a professionally formatted PDF report.

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python)
- **AI Orchestration**: LangChain & LangChain Groq
- **LLM**: Llama 3.1 8b (via Groq)
- **Data APIs**: Alpha Vantage (Fundamentals/Price), NewsAPI (Sentiment)
- **NLP**: NLTK VADER
- **PDF Processing**: PyPDF (Reader), ReportLab (Generator)
- **Frontend**: Vanilla JS, HTML, CSS (Glassmorphism), Chart.js

## 📋 Prerequisites

To run this project, you will need the following API keys:
1. **Groq API Key**: For the Llama 3.1 8b reasoning engine.
2. **Alpha Vantage API Key**: For real-time financial data.
3. **NewsAPI Key**: For sentiment analysis news fetching.

## ⚙️ Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd FinancialAnalyst_Ticker
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Create a `.env` file in the root directory and add your API keys:
   ```env
   GROQ_API_KEY=your_groq_key_here
   ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here
   NEWS_API_KEY=your_newsapi_key_here
   ```

4. **Run the Application**:
   Execute the provided batch file to start the server:
   ```bash
   run_server.bat
   ```
   Or run manually:
   ```bash
   python server.py
   ```

The dashboard will be available at `http://localhost:8000`.

## 🧠 Technical Architecture

FinAnalyst follows a deterministic workflow to ensure accuracy:
1. **Metadata Extraction**: Identifies the company and ticker using regex and LLM fallbacks.
2. **Metrics Extraction**: Prompts the LLM with strict JSON templates, injecting live API data as the "Source of Truth".
3. **Validation**: The `MetricsValidator` scans the raw PDF text for numeric evidence and re-calculates ratios (ROE, EPS, D/E) to assign a confidence score.
4. **Sentiment Scoring**: Articles are weighted by recency to calculate a 7-day sentiment trend.

## ⚖️ Scoring Methodology

The dashboard uses a standardized **Stability Benchmarking** system:
- **Liquidity**: Based on Current Ratio (Threshold: 1.20)
- **Solvency**: Based on Debt-to-Equity (Threshold: 2.00)
- **Market Risk**: Based on Beta (Threshold: 1.30)
- **Confidence**: Based on Insider Ownership (Threshold: 10%)

---
*Disclaimer: This tool is for educational and informational purposes only and does not constitute financial advice.*
