import os
import requests
import time
import json
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
try:
    from googlesearch import search as google_search
except ImportError:
    google_search = None
from dotenv import load_dotenv

from dotenv import load_dotenv
from sentiment_tool import SentimentAnalyzer

class FinancialAnalystAgent:
    def __init__(self, api_key=None, alpha_vantage_key=None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API Key is missing. Please provide it or set GROQ_API_KEY in .env")
        
        self.alpha_vantage_key = alpha_vantage_key or os.getenv("ALPHA_VANTAGE_API_KEY", "demo")
        
        self.llm = ChatGroq(
            groq_api_key=self.api_key, 
            model_name="llama-3.1-8b-instant",
            temperature=0
        )
        
        # Initialize Sentiment Analyzer
        self.sentiment_analyzer = SentimentAnalyzer()
        self.rate_limited = False
        
        # internal state for tools
        self._current_financial_context = ""
        
        # Define tools
        @tool
        def stock_lookup(ticker: str):
            """Get current stock price and info for a given ticker."""
            return self._get_stock_data(ticker)

        @tool
        def forecast_stock(ticker: str):
            """Get historical data to analyze trends and forecast future price."""
            return self._get_price_history(ticker)

        @tool
        def plot_chart(ticker: str):
            """Generates and displays an interactive financial chart for the provided stock ticker symbol."""
            return self._get_raw_history(ticker)

        self.tools = [stock_lookup, forecast_stock, plot_chart]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        self.history = []
        self.last_metrics = None

    def set_context(self, text):
        self._current_financial_context = text

    def _get_stock_data(self, ticker):
        try:
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={self.alpha_vantage_key}"
            response = requests.get(url, timeout=10)
            data = response.json()
            quote = data.get("Global Quote", {})
            if not quote:
                return f"Could not fetch data for {ticker}."
            return f"Stock: {ticker}\nPrice: ${quote.get('05. price')}\nChange: {quote.get('10. change percent')}"
        except Exception as e:
            return f"Error fetching stock data: {str(e)}"

    def _get_price_history(self, ticker):
        try:
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={self.alpha_vantage_key}"
            response = requests.get(url, timeout=10)
            data = response.json()
            daily_series = data.get("Time Series (Daily)", {})
            if not daily_series:
                return f"No historical data available for '{ticker}'."
            sorted_dates = sorted(daily_series.keys(), reverse=True)[:30]
            history = []
            for date in sorted_dates:
                day_data = daily_series[date]
                history.append(f"{date}: Close=${day_data['4. close']}")
            return "\n".join(history)
        except Exception as e:
            return f"Error: {str(e)}"

    def _get_raw_history(self, ticker):
        try:
            # 1. Price History
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={self.alpha_vantage_key}"
            response = requests.get(url, timeout=10)
            data = response.json()
            daily_series = data.get("Time Series (Daily)", {})
            
            if not daily_series:
                return {"error": f"No data for {ticker}"}
            
            sorted_dates = sorted(daily_series.keys()) # Ascending for chart
            prices = [float(daily_series[d]['4. close']) for d in sorted_dates]

            # Small delay to avoid rate limiting
            time.sleep(1)

            # 2. Overview Metrics
            url_overview = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={self.alpha_vantage_key}"
            res_overview = requests.get(url_overview, timeout=10)
            data_overview = res_overview.json()
            
            print(f"DEBUG: OVERVIEW response keys: {list(data_overview.keys())[:5]}")
            
            # Format dividend yield as percentage
            div_yield = data_overview.get("DividendYield", "N/A")
            if div_yield != "N/A" and div_yield:
                try:
                    div_yield = f"{float(div_yield) * 100:.2f}%"
                except:
                    div_yield = "N/A"
            
            pe_ratio = data_overview.get("PERatio", "N/A")
            market_cap = data_overview.get("MarketCapitalization", "N/A")
            
            print(f"DEBUG: PE={pe_ratio}, MC={market_cap}, DY={div_yield}")
            
            metrics = {
                "pe_ratio": pe_ratio,
                "market_cap": market_cap,
                "dividend_yield": div_yield
            }

            return {"ticker": ticker, "dates": sorted_dates, "prices": prices, "metrics": metrics}
        except Exception as e:
            print(f"ERROR in _get_raw_history: {e}")
            return {"error": str(e)}



    def run(self, query):
        if not self._current_financial_context and "upload" not in query.lower():
            # Be lenient if checking stock without PDF, but prompt implies context needed
            pass

        system_prompt = f"""You are an expert financial analyst.
        Context: {self._current_financial_context[:5000]}
        Answer the user's question.
        Use tools whenever possible for stock data, charts, or images.
        """
        
        messages = [SystemMessage(content=system_prompt)] + self.history + [HumanMessage(content=query)]
        
        try:
            print(f"DEBUG: Invoking LLM with {len(messages)} messages...")
            response = self.llm_with_tools.invoke(messages)
            print(f"DEBUG: LLM Response content: '{response.content}'")
            print(f"DEBUG: LLM Tool calls: {response.tool_calls}")
            
            # Handle Tool Calls (Iterative)
            max_iterations = 5
            iteration = 0
            
            while response.tool_calls and iteration < max_iterations:
                iteration += 1
                tool_call = response.tool_calls[0]
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                print(f"DEBUG: Handling tool call: {tool_name} with args: {tool_args}")
                
                # Execute tool
                result = None
                if tool_name == "stock_lookup":
                    result = self._get_stock_data(**tool_args)
                elif tool_name == "forecast_stock":
                    result = self._get_price_history(**tool_args)
                elif tool_name == "plot_chart":
                    chart_data = self._get_raw_history(**tool_args)
                    if "error" in chart_data: return f"Error: {chart_data['error']}"
                    # Record usage in history
                    self.history.append(HumanMessage(content=query))
                    self.history.append(AIMessage(content=f"[CHART] {tool_args['ticker']}"))
                    return {"text": f"Interactive chart for {tool_args['ticker']}", "chart_data": chart_data}
                else:
                    result = f"Tool '{tool_name}' not found."

                # Append tool result to messages for re-invocation
                messages.append(response) # Append AIMessage with tool_calls
                messages.append(ToolMessage(tool_call_id=tool_call["id"], content=str(result)))
                
                print(f"DEBUG: Re-invoking LLM after {tool_name}...")
                response = self.llm_with_tools.invoke(messages)
                print(f"DEBUG: LLM Response content: '{response.content}'")
                print(f"DEBUG: LLM Tool calls: {response.tool_calls}")

            # Final content
            content = response.content
            self.history.append(HumanMessage(content=query))
            self.history.append(AIMessage(content=str(content)))
            return content
            
        except Exception as e:
            return f"Error: {e}"
    def run_stream(self, query):
        """Generator that streams response chunks."""
        if not self._current_financial_context and "upload" not in query.lower():
             pass

        system_prompt = f"""You are an expert financial analyst.
        Context: {self._current_financial_context[:5000]}
        Answer the user's question.
        Use tools whenever possible for stock data, charts, or images.
        """
        
        messages = [SystemMessage(content=system_prompt)] + self.history + [HumanMessage(content=query)]
        
        try:
            # First LLM Call (non-streaming to check for tools first, or we could stream this too if we handle Token vs ToolChunk)
            # For simplicity, let's invoke standard to check for TOOLS. If no tools, we could have streamed, but
            # to keep logic unified:
            # 1. Ask LLM (wait)
            # 2. If tools -> yield status -> run tools -> ask LLM (Stream)
            # 3. If no tools -> just return text (we missed streaming start), OR we can just stream the second part.
            
            # Use binding for initial check
            response = self.llm_with_tools.invoke(messages)
            
            # Handle Tool Calls
            max_iterations = 5
            iteration = 0
            
            while response.tool_calls and iteration < max_iterations:
                iteration += 1
                tool_call = response.tool_calls[0]
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                # Yield status update
                yield f"[STATUS] Using tool: {tool_name}...\n"
                
                # Execute tool
                result = None
                if tool_name == "stock_lookup":
                    result = self._get_stock_data(**tool_args)
                elif tool_name == "forecast_stock":
                    result = self._get_price_history(**tool_args)
                elif tool_name == "plot_chart":
                    chart_data = self._get_raw_history(**tool_args)
                    if "error" in chart_data: 
                        yield f"Error: {chart_data['error']}"
                        return
                        
                    # For charts, we yield a special marker or just the chart description
                    # yield f"[CHART_DATA] {chart_data}\n" # REMOVED to prevent raw data leak 
                    # Re-design: server handles this? Or we yield a json line?
                    # Let's keep it simple: Agent logic usually returns text.
                    # For plot_chart, the valid result to LLM is "Chart created". 
                    # But the User needs the data.
                    # Let's yield a special block that frontend intercepts.
                    import json
                    chart_text = f"Generated chart for {tool_args['ticker']}"
                    yield f"__JSON_START__{json.dumps({'chart_data': chart_data, 'text': chart_text})}__JSON_END__"
                    
                    # Update history
                    self.history.append(HumanMessage(content=query))
                    self.history.append(AIMessage(content=f"[CHART] {tool_args['ticker']}"))
                    return # End stream
                    
                else:
                    result = f"Tool '{tool_name}' not found."

                messages.append(response) 
                messages.append(ToolMessage(tool_call_id=tool_call["id"], content=str(result)))
                
                # Check if we need more tools
                response = self.llm_with_tools.invoke(messages)

            # Final Answer Streaming
            # Now we have the final response (or the first response if no tools were used)
            # But wait, we already invoked it above to get 'response'. 
            # If it had no tools, 'response.content' is the answer.
            # We wanted to STREAM the answer.
            # Strategy: If we already have the answer content, we can just yield it.
            # Ideally we would have used .stream() from the start.
            
            if response.content:
                 yield response.content
            
            # Update history
            self.history.append(HumanMessage(content=query))
            self.history.append(AIMessage(content=response.content))
            
        except Exception as e:
            yield f"Error: {e}"

    def extract_metrics(self):
        """Extract comprehensive financial metrics for dashboard display."""
        if not self._current_financial_context:
            return None

        # Strengthen prompt with LIVE DATA injection and STRICT JSON formatting
        
        # 1. Get Metadata/Ticker
        metadata = self.extract_metadata()
        ticker = None
        realtime_metrics = {}
        
        if metadata:
            ticker = metadata.get("ticker")
            if not ticker or ticker == "Unknown":
                company_name = metadata.get("company_name")
                if company_name and company_name != "Unknown":
                    ticker = self._search_ticker(company_name)
            
            if ticker and ticker != "Unknown":
                realtime_metrics = self._fetch_realtime_metrics(ticker)

        prompt = f"""
        Analyze the following financial context and extract metrics.
        
        CRITICAL RULES:
        1. LIVE API DATA (Inject below) is the ABSOLUTE SOURCE OF TRUTH for numeric metrics. 
           If there is a conflict between the text and API data, use the API DATA.
        2. DO NOT return "N/A" for red_flags or critical_red_flags. 
           If no specific red flags are in the document, analyze the provided metrics 
           (e.g., high PE, low current ratio, or high debt) to infer a POTENTIAL 
           risk relevant to the company's sector.
        3. OUTPUT FORMAT: STRICT JSON ONLY. 
           - NO comments (e.g. // comment).
           - NO markdown blocks (e.g. ```json).
           - NO conversational text.
        4. Ticker identified: {ticker if ticker else "Unknown"}
        
        LIVE API DATA:
        {json.dumps(realtime_metrics) if realtime_metrics else "No live data available."}
        
        CONTEXT:
        {self._current_financial_context[:10000]}
        
        Return JSON with these keys:
        - company_name, company_description, fiscal_year, revenue, net_income
        - revenue_growth, profit_margin, risk_score (0-10)
        - volatility (Low/Med/High), eps, pe_ratio, roe, revenue_cagr
        - debt_equity, current_ratio, ownership, beta, market_cap
        - dividend_yield, free_cash_flow, price_to_book
        - red_flags (min 2 strings, NEVER N/A)
        - risk_details: {{
            "liquidity": {{ "summary": "...", "factors": [], "critical_red_flags": "..." }},
            "market": {{ ... }},
            "credit": {{ ... }},
            "governance": {{ ... }}
        }}
        - revenue_segments: {{
            "Segment Name 1": {{ "weight": 45, "actual_value": "$45B", "yoy_growth": "+5%" }},
            "Segment Name 2": {{ "weight": 55, "actual_value": "$55B", "yoy_growth": "-2%" }}
        }} (MUST be a dictionary, NOT a list)
        """

        try:
            with open("debug_log.txt", "a") as f: f.write(f"[{time.time()}] Promoting metrics with LLM...\n")
            response = self.llm.invoke(prompt)
            content = response.content
            with open("debug_log.txt", "a") as f: f.write(f"[{time.time()}] LLM response received. Length: {len(content)}\n")
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = content[start:end]
                # Cleanup: Remove comments if AI ignores instruction
                import re
                # Remove // comments but protect http://
                json_str = re.sub(r'(?<!:)//.*', '', json_str)
                
                metrics = json.loads(json_str)
                
                # Post-Merge: Ensure verified status for API data
                if realtime_metrics:
                    for k, v in realtime_metrics.items():
                        if v is not None and v != "N/A":
                            # FORCE OVERWRITE PDF DATA
                            metrics[k] = v
                            metrics[f'{k}_status'] = "VERIFIED"
                            metrics[f'{k}_confidence'] = "HIGH"
                    
                    # Derive overall risk score from API risks if available
                    api_risks = [realtime_metrics.get(rk) for rk in ['liquidity_risk', 'market_risk', 'credit_risk', 'governance_risk']]
                    api_risks = [r for r in api_risks if r is not None]
                    if api_risks:
                        metrics['risk_score'] = sum(api_risks) / (len(api_risks) * 10) # Convert 0-100 to 0-10
                
                # Add Sentiment/News (Passing Company Name for Fallback Search)
                if ticker and ticker != "Unknown":
                    try:
                        company_name_query = metrics.get('company_name', ticker)
                        with open("debug_log.txt", "a") as f: f.write(f"[{time.time()}] Calling sentiment_analyzer for {ticker}\n")
                        sentiment_data = self.sentiment_analyzer.get_stock_sentiment(ticker, company_name_query)
                        metrics['sentiment'] = sentiment_data
                        with open("debug_log.txt", "a") as f: f.write(f"[{time.time()}] Sentiment analysis complete\n")
                        
                        # Fix empty chart by overwriting LLM-generated trend with real trend
                        if sentiment_data and 'sentiment_trend' in sentiment_data:
                            metrics['sentiment_trend'] = sentiment_data['sentiment_trend']
                            
                        print(f"✓ Sentiment analysis complete: {sentiment_data.get('sentiment_label', 'N/A')} ({len(sentiment_data.get('news', []))} articles)")
                    except Exception as e:
                        print(f"Sentiment Analysis Error in extract_metrics: {e}")
                        metrics['sentiment'] = None


                # FORCE RISK NORMALIZATION (Same as analyze_stock)
                if 'risk_details' in metrics:
                    self._normalize_risk_data(metrics, metrics['risk_details'])
                else:
                    # Fallback if AI structure is flat
                    self._normalize_risk_data(metrics, metrics)

                # RED FLAG SAFETY NET: Calculate flags if missing
                if not metrics.get('red_flags') or len(metrics.get('red_flags')) == 0:
                    metrics['red_flags'] = self._calculate_implied_red_flags(metrics)

                # Keep validator for anything NOT in realtime (red flags, specific PDF projections)
                from metrics_validator import MetricsValidator
                validator = MetricsValidator(self._current_financial_context)
                validation_report = validator.validate_all_metrics(metrics)
                
                # Add validation results (Skip forcing confidence here, already done for VERIFIED items)
                metrics['_validation'] = validation_report
                for metric_name, validation in validation_report['validations'].items():
                    status_key = f'{metric_name}_status'
                    if metrics.get(status_key) != "VERIFIED":
                        metrics[f'{metric_name}_confidence'] = validation['confidence']
                        metrics[status_key] = validation['status']
                
                with open("debug_log.txt", "a") as f: f.write(f"[{time.time()}] metrics extraction complete. Keys: {list(metrics.keys())}\n")
                print(f"DEBUG METRICS: {json.dumps(metrics)}")
                self.last_metrics = metrics
                return metrics
            return None
        except Exception as e:
            print(f"Error extracting metrics: {e}")
            if 'content' in locals():
                print(f"DEBUG raw content: {content}")
            return None

    def _calculate_implied_red_flags(self, metrics):
        """Generate red flags from quantitative data if LLM fails to find text-based risks."""
        with open("debug_log.txt", "a") as f: f.write(f"[{time.time()}] Calculating implied red flags\n")
        flags = []
        try:
            # Valuation
            pe = float(metrics.get('pe_ratio', 0) or 0)
            if pe > 45: flags.append(f"Extremely High Valuation (P/E: {pe})")
            
            # Liquidity
            cr = float(metrics.get('current_ratio', 0) or 0)
            if cr > 0 and cr < 0.8: flags.append(f"Liquidity Concern (Current Ratio: {cr})")
            
            # Leverage
            de = float(metrics.get('debt_equity', 0) or 0)
            if de > 2.5: flags.append(f"High Leverage (Debt/Equity: {de})")
            
            # Profitability
            pm = str(metrics.get('profit_margin', '0')).replace('%', '')
            if float(pm) < 0: flags.append("Negative Profit Margin")
            
            # Volatility
            if metrics.get('volatility') == 'High': flags.append("High Stock Volatility")

        except Exception as e:
            print(f"Error calculating implied flags: {e}")
            
        if not flags:
            flags.append("No critical quantitative risks detected.")
            
        return flags


    def _fetch_realtime_metrics(self, ticker):
        """Fetch live financial data from Alpha Vantage for core metrics."""
        self.rate_limited = False  # Reset status
        try:
            # 1. OVERVIEW
            with open("debug_log.txt", "a") as f: f.write(f"[{time.time()}] Calling OVERVIEW for {ticker} (2s delay)\n")
            time.sleep(2.0)  # Safe buffer after potential validation calls
            url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={self.alpha_vantage_key}"
            res = requests.get(url, timeout=10)
            data = res.json()
            with open("debug_log.txt", "a") as f: f.write(f"[{time.time()}] OVERVIEW call done. Data: {bool(data)}\n")
            
            if not data or "Symbol" not in data:
                error_msg = data.get("Note") or data.get("Information") or "No data found for this symbol"
                with open("debug_log.txt", "a") as f: f.write(f"[{time.time()}] OVERVIEW check failed for {ticker}: {error_msg}\n")
                if "Note" in data or "Information" in data:
                    self.rate_limited = True
                return {}

            # Helpers for formatting
            def fmt_large(val):
                if not val or val == "N/A": return "N/A"
                try:
                    v = float(val)
                    if v >= 1e12: return f"{v/1e12:.2f}T"
                    if v >= 1e9: return f"{v/1e9:.2f}B"
                    if v >= 1e6: return f"{v/1e6:.2f}M"
                    return f"{v:,.0f}"
                except: return str(val)

            def fmt_pct(val, plus=False):
                if not val or val == "N/A": return "N/A"
                try:
                    v = float(val)
                    if abs(v) < 2.0: v *= 100 # assume decimal
                    return f"{'+' if plus and v > 0 else ''}{v:.1f}%"
                except: return str(val)

            # Format primary metrics
            mc_val = fmt_large(data.get("MarketCapitalization"))
            roe_val = fmt_pct(data.get("ReturnOnEquityTTM"))
            rev_growth_val = fmt_pct(data.get("QuarterlyRevenueGrowthYOY"), plus=True)
            pm_val = fmt_pct(data.get("ProfitMargin"))

            # Liquidity & Ownership
            current_ratio = data.get("CurrentRatio", "N/A")
            ownership = data.get("PercentInsiders", "N/A")
            beta = data.get("Beta", "N/A")

            # 2. Fetch Quarterly Income Statement for history
            history = {}
            if not self.rate_limited:
                try:
                    with open("debug_log.txt", "a") as f: f.write(f"[{time.time()}] Calling INCOME_STATEMENT (2s sleep first)\n")
                    time.sleep(2.0) # Increased Rate limiting
                    is_url = f"https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={ticker}&apikey={self.alpha_vantage_key}"
                    is_data = requests.get(is_url, timeout=10).json()
                    
                    if "Note" in is_data or "Information" in is_data:
                        with open("debug_log.txt", "a") as f: f.write(f"[{time.time()}] INCOME_STATEMENT rate limited\n")
                        self.rate_limited = True
                    
                    quarterly_reports = is_data.get("quarterlyReports", [])[:5]
                    quarterly_reports.reverse()
                    
                    if quarterly_reports:
                        history = {
                            "eps": [float(r.get("dilutedEarningsPerShare", 0) or 0) for r in quarterly_reports],
                            "revenue": [float(r.get("totalRevenue", 0) or 0) for r in quarterly_reports],
                            "net_income": [float(r.get("netIncome", 0) or 0) for r in quarterly_reports]
                        }
                except: pass

            # Calculate Trends
            revenue_growth_trend = "positive"
            profit_trend = "positive"
            if history.get("revenue") and len(history["revenue"]) >= 2:
                revenue_growth_trend = "positive" if history["revenue"][-1] >= history["revenue"][-2] else "negative"
            if history.get("net_income") and len(history["net_income"]) >= 2:
                profit_trend = "positive" if history["net_income"][-1] >= history["net_income"][-2] else "negative"

            # Debt/Equity Calculation
            debt_equity = data.get("DebtEquityRatio", "0.0")
            if not debt_equity or debt_equity == "None": debt_equity = "0.0"
            
            # Risk Score Calculations (Internal Calibration)
            # Scores are 0-100 (Higher = MORE RISK)
            try:
                cr_f = float(current_ratio) if current_ratio != "N/A" else 1.5
                li_risk = max(0, min(100, (2.0 - cr_f) * 50))
                
                beta_f = float(beta) if beta != "N/A" else 1.1
                ma_risk = max(0, min(100, (beta_f / 2.0) * 100))
                
                de_f = float(debt_equity) if debt_equity != "0.0" else 0.5
                cr_risk = max(0, min(100, (de_f / 3.0) * 100))
                
                own_f = float(ownership) if ownership != "N/A" else 10.0
                go_risk = max(0, min(100, (1.0 - (own_f / 50)) * 100)) # Simple heuristic
            except:
                li_risk, ma_risk, cr_risk, go_risk = 30, 45, 25, 40 # Defaults
            
            # 3. Fetch Quarterly Balance Sheet for history
            price_to_book = data.get("PriceToBookRatio", "N/A")
            if not self.rate_limited:
                try:
                    with open("debug_log.txt", "a") as f: f.write(f"[{time.time()}] Calling BALANCE_SHEET (2s sleep first)\n")
                    time.sleep(2.0) # Increased Rate limiting
                    bs_url = f"https://www.alphavantage.co/query?function=BALANCE_SHEET&symbol={ticker}&apikey={self.alpha_vantage_key}"
                    bs_data = requests.get(bs_url, timeout=5).json()
                    
                    if "Note" in bs_data or "Information" in bs_data:
                        with open("debug_log.txt", "a") as f: f.write(f"[{time.time()}] BALANCE_SHEET rate limited\n")
                        self.rate_limited = True
                    
                    bs_reports = bs_data.get("quarterlyReports", [])[:5]
                    
                    if bs_reports:
                        latest_bs = bs_reports[0]
                        equity = float(latest_bs.get("totalShareholderEquity", 0) or 0)
                        shares_outstanding = float(data.get("SharesOutstanding", 0) or 0)
                        if shares_outstanding > 0 and equity > 0:
                            book_val = equity / shares_outstanding
                            curr_price = float(data.get("50DayMovingAverage", 0) or 1.0) # Fallback to 1.0
                            price_to_book = f"{curr_price / book_val:.2f}"

                        # History mapping (reverse for chronological)
                        bs_reports_rev = list(reversed(bs_reports))
                        history["debt_equity"] = []
                        history["current_ratio"] = []
                        for r in bs_reports_rev:
                            td = float(r.get("shortTermDebt", 0) or 0) + float(r.get("longTermDebt", 0) or 0)
                            eq = float(r.get("totalShareholderEquity", 0) or 1)
                            history["debt_equity"].append(round(td / eq, 3))
                            
                            ca = float(r.get("totalCurrentAssets", 0) or 0)
                            cl = float(r.get("totalCurrentLabels", 0) or float(r.get("totalCurrentLiabilities", 0) or 1))
                            history["current_ratio"].append(round(ca / cl, 3))
                        
                        if history["debt_equity"]:
                            latest_de = history["debt_equity"][-1]
                            if debt_equity == "0.0" or debt_equity == "N/A":
                                debt_equity = f"{latest_de:.2f}"
                except Exception as e:
                    print(f"BS Fetch Failed: {e}")
            
            # Free Cash Flow Calculation
            free_cash_flow = "N/A"
            if not self.rate_limited:
                try:
                    with open("debug_log.txt", "a") as f: f.write(f"[{time.time()}] Calling CASH_FLOW (2s sleep first)\n")
                    time.sleep(2.0)  # Increased Rate limiting
                    cf_url = f"https://www.alphavantage.co/query?function=CASH_FLOW&symbol={ticker}&apikey={self.alpha_vantage_key}"
                    cf_data = requests.get(cf_url, timeout=5).json()
                    with open("debug_log.txt", "a") as f: f.write(f"[{time.time()}] CASH_FLOW done. Data: {bool(cf_data)}\n")
                    
                    if "Note" in cf_data or "Information" in cf_data:
                        with open("debug_log.txt", "a") as f: f.write(f"[{time.time()}] CASH_FLOW rate limited\n")
                        self.rate_limited = True

                    cf_reports = cf_data.get("quarterlyReports", [])
                    if cf_reports:
                        latest_cf = cf_reports[0]
                        operating_cf = float(latest_cf.get("operatingCashflow", 0) or 0)
                        capex = float(latest_cf.get("capitalExpenditures", 0) or 0)
                        
                        # FCF = Operating Cash Flow - Capital Expenditures
                        fcf_value = operating_cf - abs(capex)  # capex is usually negative
                        
                        # Format FCF
                        if abs(fcf_value) >= 1e9:
                            free_cash_flow = f"${fcf_value/1e9:.2f}B"
                        elif abs(fcf_value) >= 1e6:
                            free_cash_flow = f"${fcf_value/1e6:.2f}M"
                        else:
                            free_cash_flow = f"${fcf_value/1e3:.2f}K"
                except Exception as e:
                    print(f"Debug: Free Cash Flow calculation failed: {e}")


            return {
                "ticker": ticker,
                "eps": data.get("EPS", "N/A"),
                "pe_ratio": data.get("PERatio", "N/A"),
                "roe": roe_val,
                "revenue_cagr": rev_growth_val,
                "revenue_growth": rev_growth_val,
                "revenue_growth_trend": revenue_growth_trend,
                "profit_margin": pm_val,
                "profit_trend": profit_trend,
                "market_cap": mc_val,
                "dividend_yield": fmt_pct(data.get('DividendYield')),
                "debt_equity": debt_equity,
                "beta": data.get("Beta", "N/A"),
                "current_ratio": data.get("CurrentRatio", "N/A"),
                "ownership": fmt_pct(data.get('PercentInsiders')),
                "free_cash_flow": free_cash_flow,
                "price_to_book": price_to_book,
                "liquidity_risk": int(li_risk),
                "market_risk": int(ma_risk),
                "credit_risk": int(cr_risk),
                "governance_risk": int(go_risk),
                "history": history,
                "raw_overview": data # Optimization: Store for reuse
            }
        except Exception as e:
            print(f"Error fetching realtime metrics: {e}")
            return {}

    def _search_ticker(self, company_name):
        """Fallback to search for a ticker symbol by company name."""
        try:
            url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={company_name}&apikey={self.alpha_vantage_key}"
            res = requests.get(url, timeout=10).json()
            matches = res.get("bestMatches", [])
            if matches:
                return matches[0].get("1. symbol", "Unknown")
        except:
            pass
        return "Unknown"
    
    def _validate_ticker(self, ticker, company_name):
        """Validate that ticker matches the company name using API lookup."""
        try:
            # STRATEGY 1: Reverse Lookup (Search by Ticker to see if company name matches)
            # This handles cases where "Apple Inc" search returns international listings first
            print(f"DEBUG: Validating ticker '{ticker}' for company '{company_name}'...")
            
            url_ticker = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={ticker}&apikey={self.alpha_vantage_key}"
            res_ticker = requests.get(url_ticker, timeout=10).json()
            matches_ticker = res_ticker.get("bestMatches", [])
            
            # Check if any of the matches for this ticker correspond to the company name
            for match in matches_ticker:
                symbol = match.get("1. symbol", "")
                name = match.get("2. name", "")
                
                # Check for exact ticker match
                if symbol.upper() == ticker.upper():
                    # Fuzzy match company name (or checks if one is contained in the other)
                    # e.g. "Apple Inc" in "Apple Inc." or vice versa
                    if company_name.lower().split()[0] in name.lower() or name.lower().split()[0] in company_name.lower():
                        print(f"✓ Ticker '{ticker}' validated via reverse lookup ({name})")
                        return ticker

            # STRATEGY 2: Forward Lookup (Search by Company Name) - Fallback
            print(f"DEBUG: Reverse lookup inconclusive. Searching by company name '{company_name}'...")
            url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={company_name}&apikey={self.alpha_vantage_key}"
            res = requests.get(url, timeout=10).json()
            matches = res.get("bestMatches", [])
            
            if not matches:
                print(f"DEBUG: No matches found for company '{company_name}', keeping ticker '{ticker}'")
                return ticker  # Keep original if no matches
            
            # Check if provided ticker is in top 3 matches
            top_symbols = [m.get("1. symbol", "").upper() for m in matches[:3]]
            print(f"DEBUG: API suggests tickers {top_symbols} for '{company_name}'")
            
            if ticker.upper() in top_symbols:
                print(f"✓ Ticker '{ticker}' validated for '{company_name}'")
                return ticker  # Ticker is correct
            else:
                # Ticker mismatch, use the best match
                best_match = matches[0].get("1. symbol", ticker)
                print(f"⚠ Ticker '{ticker}' doesn't match '{company_name}'. Suggesting '{best_match}'")
                return best_match
        except Exception as e:
            print(f"DEBUG: Ticker validation error: {e}")
            return ticker  # Keep original on error

    def extract_metadata(self):
        """Extract report metadata from valid context."""
        if not self._current_financial_context:
            return None

        # STEP 1: Try regex pattern matching for ticker symbols first
        import re
        ticker_regex_found = None
        # Reduce context sample for regex to catch header info efficiently
        context_sample = self._current_financial_context[:4000]
        
        # Common ticker patterns
        ticker_patterns = [
            r'(?:Ticker|Symbol):\s*([A-Z]{1,5}(?:\.[A-Z]{2})?)',  # "Ticker: IBM"
            r'(?:NYSE|NASDAQ|NSE|BSE):\s*([A-Z]{1,5})',  # "NYSE: IBM"
            r'\((?:NYSE|NASDAQ|NSE|BSE):\s*([A-Z]{1,5})\)',  # "(NYSE: IBM)"
            r'Trading Symbol:\s*([A-Z]{1,5}(?:\.[A-Z]{2})?)',  # "Trading Symbol: IBM"
        ]
        
        for pattern in ticker_patterns:
            match = re.search(pattern, context_sample, re.IGNORECASE)
            if match:
                ticker_regex_found = match.group(1).upper()
                print(f"✓ DEBUG: Regex found ticker: {ticker_regex_found}")
                break
        
        # Optimization: If Regex found a likely ticker, use a much smaller prompt to just get company name/fiscal year
        # This avoids the large extraction if we already have the critical piece (Ticker)
        context_limit = 3000 if ticker_regex_found else 6000
        
        # STEP 2: Use LLM to extract metadata
        prompt = f"""
        Extract the following information from this financial report.
        
        {f"NOTE: A potential ticker '{ticker_regex_found}' was already found. Please verify if this is correct." if ticker_regex_found else "Search for explicit ticker mentions like 'Ticker: XXX'."}
        
        Extract:
        1. Company Name
        2. Fiscal Year
        3. Ticker Symbol (Confirm '{ticker_regex_found}' if valid, otherwise find correct one)

        Return ONLY a JSON object with keys: "company_name", "fiscal_year", "ticker".
        Use "Unknown" if not found.

        Context:
        {self._current_financial_context[:context_limit]}
        """

        try:
            response = self.llm.invoke(prompt)
            content = response.content
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != -1:
                import json
                metadata = json.loads(content[start:end])
                
                # Debug logging
                print(f"DEBUG: LLM extracted metadata: company='{metadata.get('company_name')}', ticker='{metadata.get('ticker')}'")
                
                # STEP 3: Validate and correct ticker if regex found a match
                if ticker_regex_found:
                    # Trust regex if LLM says Unknown or fails, OR if LLM agrees
                    llm_ticker = metadata.get('ticker', 'Unknown')
                    if llm_ticker == 'Unknown' or (llm_ticker != ticker_regex_found and len(llm_ticker) > 5):
                         metadata['ticker'] = ticker_regex_found
                
                # STEP 4: Validate ticker against company name if both are available
                if metadata.get('ticker') and metadata.get('ticker') != 'Unknown' and metadata.get('company_name') and metadata.get('company_name') != 'Unknown':
                    validated_ticker = self._validate_ticker(metadata['ticker'], metadata['company_name'])
                    if validated_ticker and validated_ticker != metadata['ticker']:
                        print(f"⚠ WARNING: Ticker validation corrected '{metadata['ticker']}' to '{validated_ticker}'")
                        metadata['ticker'] = validated_ticker
                
                print(f"✓ FINAL: Extracted ticker='{metadata.get('ticker')}' for company='{metadata.get('company_name')}'")
                return metadata
            return None
        except Exception as e:
            print(f"Error extracting metadata: {e}")
            return {'ticker': ticker_regex_found} if ticker_regex_found else None


    def analyze_stock(self, ticker):
        """Analyze a stock by ticker, fetching realtime data and generating context."""
        self.rate_limited = False
        try:
            # 1. Fetch Realtime Metrics
            realtime_metrics = self._fetch_realtime_metrics(ticker)
            # if not realtime_metrics: return None  <-- Removed to allow fallback

            # 1.5 Fetch Sentiment Data
            try:
                sentiment_data = self.sentiment_analyzer.get_stock_sentiment(ticker)
                realtime_metrics['sentiment'] = sentiment_data
            except Exception as e:
                print(f"Sentiment Analysis Error: {e}")
                realtime_metrics['sentiment'] = None

            
            # 2. Use Company Overview (Reused from realtime_metrics if available)
            overview = realtime_metrics.get('raw_overview', {})
            
            if not overview or not overview.get("Name"):
                # If _fetch_realtime_metrics didn't get it (due to direct fail), try once more or fallback
                url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={self.alpha_vantage_key}"
                res = requests.get(url, timeout=10)
                overview = res.json()

            # Fallback: If OVERVIEW is empty (common for Indian stocks e.g. .BSE), use Web Search
            if not overview or not overview.get("Name"):
                print(f"DEBUG: Overview empty for {ticker}, attempting Web Search fallback...")
                search_data = self._fetch_overview_via_search(ticker)
                if search_data:
                    # Merge search data into overview/metrics
                    overview.update(search_data)
                    # Also populate metrics directly if possible
                    realtime_metrics.update(search_data)

            
            # Create a synthetic context string
            self._current_financial_context = f"""
            FINANCIAL REPORT FOR {overview.get('Name', ticker)} ({ticker})
            
            Description: {overview.get('Description', 'No description available.')}
            
            Key Metrics:
            - Market Cap: {realtime_metrics.get('market_cap', 'N/A')}
            - PE Ratio: {realtime_metrics.get('pe_ratio', 'N/A')}
            - EPS: {realtime_metrics.get('eps', 'N/A')}
            - Dividend Yield: {realtime_metrics.get('dividend_yield', 'N/A')}
            - Profit Margin: {realtime_metrics.get('profit_margin', 'N/A')}
            - ROE: {realtime_metrics.get('roe', 'N/A')}
            - Revenue Growth: {realtime_metrics.get('revenue_growth', 'N/A')}
            
            Risk Factors (inferred):
            - Volatility: High/Medium/Low based on Beta ({overview.get('Beta', 'N/A')})
            - Debt/Equity Ratio: {realtime_metrics.get('debt_equity', 'N/A')}
            
            Fiscal Year End: {overview.get('FiscalYearEnd', 'N/A')}
            Sector: {overview.get('Sector', 'N/A')}
            Industry: {overview.get('Industry', 'N/A')}
            """
            
            # 3. Enhance metrics with AI analysis based on the new context
            # We can reuse extract_metrics but pre-fill with realtime_metrics
            # Or just use realtime_metrics and add AI guesses for missing parts (like risk text)
            
            # Let's do a hybrid approach:
            # Call extract_metrics() which now uses self._current_financial_context
            # Note: extract_metrics logic in agent.py already calls _fetch_realtime_metrics internally if it finds a ticker.
            # So calling extract_metrics() might be redundant in fetching, but it handles the LLM part well.
            # However, extract_metrics expects to parse context.
            
            # Let's simplify: Use realtime_metrics as base, and ask LLM to fill in risk/qualitative data.
            
            metrics = realtime_metrics.copy()
            metrics['company_name'] = overview.get('Name', ticker)
            metrics['fiscal_year'] = f"FY {overview.get('FiscalYearEnd', 'N/A')}"
            metrics['company_description'] = overview.get('Description', 'No description available.')

            # Determine Volatility based on Beta
            beta = float(overview.get('Beta', 1.0)) if overview.get('Beta') and overview.get('Beta') != 'None' else 1.0
            if beta > 1.5: metrics['volatility'] = 'High'
            elif beta < 0.8: metrics['volatility'] = 'Low'
            else: metrics['volatility'] = 'Medium'
            
            # Risk & Revenue Analysis Prompt
            risk_prompt = f"""
            Analyze the following company based on its metrics and description:
            Company: {metrics['company_name']}
            Description: {overview.get('Description', '')}
            Sector: {overview.get('Sector', '')}
            PE: {metrics.get('pe_ratio')}
            Debt/Equity: {metrics.get('debt_equity')}
            Profit Margin: {metrics.get('profit_margin')}
            Beta: {beta}

            Generate a comprehensive Financial Analysis (Risk & Revenue):
            1. A realistic Risk Score (0-10) - NEVER return 0 unless absolutely risk-free. Default to ~2-5 for low risk.
            2. 3 brief "Red Flags" or key risks (strings)
            3. Profit Trend (positive/negative/neutral)
            4. Detailed assessment for 4 risk categories: Liquidity, Market, Credit, Governance.
               For each, provide:
               - "score" (10-100) - Estimate a realistic risk level. Low risk should be 10-30, not 0.
               - "factors" (list of specific bullet points why)
               - "alarming_details" (Crucial: Describe the worst-case scenario or critical impact. Do NOT provide mitigation.)
               - "industry_avg" (Estimate a realistic numerical industry benchmark for this risk category)
            
            5. Revenue Segmentation & Trends (Infer likely segments from Description/Industry if exact data unknown):
               - "revenue_segments": {{
                    "Segment Name": {{ "weight": 60, "actual_value": "$XXB", "yoy_growth": "+X%", "insight": "Brief factor" }},
                    ... (Total weight should sum to approx 100)
                 }}
               - "segment_insight": "Brief AI insight about revenue diversity and stability."
            
            Return JSON:
            {{
                "risk_score": 5.5,
                "red_flags": ["High Debt", "Declining Margins"],
                "profit_trend": "positive",
                "risk_details": {{
                    "liquidity": {{ "score": 40, "factors": ["Low cash"], "alarming_details": "Potential insolvency if burn rate continues.", "industry_avg": 30 }},
                    "market": {{ "score": 60, "factors": ["High beta"], "alarming_details": "Vulnerable to sector downturns.", "industry_avg": 45 }},
                    "credit": {{ "score": 30, "factors": ["High D/E"], "alarming_details": "Risk of default on obligations.", "industry_avg": 25 }},
                    "governance": {{ "score": 20, "factors": ["Board stability"], "alarming_details": "Lack of independent oversight.", "industry_avg": 40 }}
                }},
                "revenue_segments": {{
                    "Core Products": {{ "weight": 70, "actual_value": "$10B", "yoy_growth": "+5%", "insight": "Main revenue driver." }},
                    "Services": {{ "weight": 30, "actual_value": "$4B", "yoy_growth": "+12%", "insight": "High margin growth." }}
                }},
                "segment_insight": "Revenue is well diversified with strong growth in services."
            }}
            """
            
            try:
                risk_res = self.llm.invoke(risk_prompt)
                with open("debug_log.txt", "a") as f: f.write(f"[{time.time()}] Risk AI response: {risk_res.content[:500]}\n")
                import json
                # rough parsing
                c_start = risk_res.content.find('{')
                c_end = risk_res.content.rfind('}') + 1
                if c_start != -1:
                    risk_data = json.loads(risk_res.content[c_start:c_end])
                    metrics.update(risk_data)
                    
                    # Flatten risk scores for frontend compatibility
                    if 'risk_details' in risk_data:
                        rd = risk_data['risk_details']
                        # Map distinct keys or normalize
                        # The prompt returns "Liquidity Risk", "Market Risk", etc.
                        # We need 'liquidity_risk', 'market_risk' etc.
                        self._normalize_risk_data(metrics, rd)
                        with open("debug_log.txt", "a") as f: f.write(f"[{time.time()}] Risk details normalized. Keys: {list(metrics.get('risk_details', {}).keys())}\n")
                        
                        # Add sector benchmarks for radar chart consistency
                        metrics['sector_benchmarks'] = {
                            "liquidity": 30,
                            "market": 45,
                            "credit": 25,
                            "governance": 40
                        }
            except Exception as e:
                print(f"Risk AI Error: {e}")
                metrics['risk_score'] = 5.0
                metrics['red_flags'] = ["Unable to assess detailed risks"]
                
             # Fill defaults
            if 'profit_trend' not in metrics:
                 try:
                     raw_pm = metrics.get('profit_margin', '0%')
                     if isinstance(raw_pm, str):
                         pm = float(raw_pm.strip('%'))
                     else:
                         pm = float(raw_pm)
                     metrics['profit_trend'] = 'positive' if pm > 0 else 'negative'
                 except:
                     metrics['profit_trend'] = 'neutral'

            # Add VERIFIED status for all metrics returned from API
            # This ensures the frontend shows the "Live" badge and checkmarks
            verified_keys = [
                'eps', 'pe_ratio', 'roe', 'revenue_cagr', 'revenue_growth', 
                'profit_margin', 'market_cap', 'debt_equity', 'beta', 
                'current_ratio', 'ownership', 'free_cash_flow', 'price_to_book'
            ]
            for vk in verified_keys:
                if metrics.get(vk) and metrics.get(vk) != 'N/A':
                    metrics[f'{vk}_status'] = "VERIFIED"
                    metrics[f'{vk}_confidence'] = "HIGH"

            metrics['rate_limit'] = self.rate_limited
            self.last_metrics = metrics
            return metrics
            
        except Exception as e:
            print(f"Error in analyze_stock: {e}")
            return None


    def _normalize_risk_data(self, metrics, rd):
        """Unified helper to normalize risk keys and scores for both analyze_stock and extract_metrics."""
        def get_robust_item(cat_name, data_source):
            if not isinstance(data_source, dict): return None
            target = cat_name.lower().replace(' risk', '').strip()
            for k, v in data_source.items():
                k_clean = str(k).lower().replace(' risk', '').strip()
                if target == k_clean or target in k_clean:
                    return v
            return None

        def get_score_robust(item):
            if isinstance(item, (int, float)): return float(item)
            score_val = 0
            if isinstance(item, dict):
                score_val = item.get('score') or item.get('Score') or item.get('value') or item.get('ratio') or 0
            else:
                score_val = item
            
            try:
                # Handle strings with %, $, commas
                clean = str(score_val).replace('%', '').replace('$', '').replace(',', '').strip()
                if clean.lower() == 'n/a' or not clean: return 0
                return float(clean)
            except:
                return 0

        # Normalize the risk_details structure and top-level scores simultaneously
        normalized_rd = {}
        categories = ['liquidity', 'market', 'credit', 'governance']
        
        for cat in categories:
            item = get_robust_item(cat, rd)
            
            # 1. Determine best score (PRIORITIZE API/CALCULATED SCORES)
            extracted_score = get_score_robust(item)
            existing_score = metrics.get(f'{cat}_risk')
            
            # Use Existing (API) score if available and valid
            if existing_score is not None and float(existing_score) > 0:
                final_score = float(existing_score)
            elif extracted_score > 0:
                final_score = extracted_score
            else:
                final_score = 0 # Default if both missing
            
            # 2. Update Top Level Metric
            metrics[f'{cat}_risk'] = int(final_score)
            
            # 3. Build Normalized Detail Object
            if item and isinstance(item, dict):
                normalized_rd[cat] = {
                    "score": int(final_score), # Sync with top level
                    "factors": item.get('factors') or item.get('Factors') or [],
                    "summary": item.get('summary') or item.get('Summary') or item.get('alarming_details') or "No summary.",
                    "industry_avg": item.get('industry_avg') or item.get('Industry_Avg') or item.get('Benchmark') or "N/A",
                    "trend": item.get('trend') or "neutral",
                    "critical_red_flags": item.get('critical_red_flags') or item.get('Critical_Red_Flags') or None
                }
            else:
                normalized_rd[cat] = {
                    "score": int(final_score), 
                    "factors": ["No details provided"], 
                    "summary": "AI assessment unavailable.", 
                    "industry_avg": "N/A", 
                    "trend": "neutral",
                    "critical_red_flags": None
                }

        metrics['risk_details'] = normalized_rd
        
        # 4. Add sector benchmarks for the Radar Chart
        metrics['sector_benchmarks'] = {
            "liquidity": 30, "market": 45, "credit": 25, "governance": 40
        }


    def _fetch_overview_via_search(self, ticker):
        """Fetch company overview and metrics via Web Search when API fails."""
        try:
            if not google_search:
                print("Google Search library not installed.")
                return {}

            query = f"{ticker} stock financial overview market cap pe ratio description sector risk factors key metrics"
            print(f"DEBUG: Searching web via Google for: {query}")
            
            # Fetch top 3 results text (simulated by getting snippets if library supports, or just URLs)
            # googlesearch-python's search() yields URLs. 
            # Ideally we need text. Simple 'search' yields URLs. 
            # 'search(query, advanced=True)' yields Result objects with title/description in googlesearch-python 1.x
            
            search_results = []
            try:
                # advanced=True returns objects with title and description
                results = google_search(query, num_results=3, advanced=True)
                for r in results:
                    search_results.append(f"Title: {r.title}\nSnippet: {r.description}\n")
            except:
                 # Fallback to bad basic search if advanced not supported (older lib)
                 # converting iterator to list
                 results = list(google_search(query, num_results=3))
                 search_results = [f"URL: {r}" for r in results]

            text_content = "\n".join(search_results)
            
            # Use LLM to parse search results into structured data
            prompt = f"""
            Extract financial metrics for {ticker} from the following search snippets/results.
            If values are missing, provide reasonable estimates based on the text or context.
            
            Search Results:
            {text_content[:4000]}
            
            Return JSON with these keys:
            - Name: Company Name
            - Description: Brief description
            - Sector: Sector
            - MarketCapitalization: e.g. "15T" or "150B"
            - PERatio: e.g. 25.5
            - EPS: e.g. 102.5
            - DividendYield: e.g. "1.5%"
            - ProfitMargin: e.g. "12%"
            - 52WeekHigh: e.g. 2500
            - 52WeekLow: e.g. 2000
            - 52WeekLow: e.g. 2000
            - risk_details: Same structure as above (Liquidity, Market, Credit, Governance) with scores (10-100), factors, and alarming_details (worst case). Estimate based on context.
            
            Return ONLY valid JSON. Use double quotes for all keys and string values.
            """
            
            response = self.llm.invoke(prompt)
            import json
            import ast
            
            content = response.content
            # Try to find JSON block
            c_start = content.find('{')
            c_end = content.rfind('}') + 1
            
            if c_start != -1:
                json_str = content[c_start:c_end]
                try:
                    # Priority 1: Strict JSON
                    data = json.loads(json_str)
                except json.JSONDecodeError:
                    try:
                        # Priority 2: Python-style dict (single quotes)
                        data = ast.literal_eval(json_str)
                    except:
                        # Priority 3: Simple retry or partial fix? 
                        # For now, return empty if both fail
                         print(f"DEBUG: Failed to parse JSON: {json_str}")
                         return {}
                # Flatten risk scores for frontend compatibility
                if 'risk_details' in data:
                    rd = data['risk_details']
                    def get_score(cat_name):
                        # Try exact match, lower, and without ' Risk' suffix
                        keys_to_try = [
                            cat_name, 
                            cat_name.lower(), 
                            cat_name.replace(' Risk', ''), 
                            cat_name.replace(' Risk', '').lower()
                        ]
                        
                        item = None
                        for k in keys_to_try:
                            if k in rd:
                                item = rd[k]
                                break
                            # Try finding key that *contains* k (partial match fallback)
                            if not item:
                                for rk in rd.keys():
                                    if k.lower() in rk.lower():
                                        item = rd[rk]
                                        break
                            if item: break

                        if item:
                            # Handle "score", "Score", or just the value if item is int
                            if isinstance(item, (int, float)): return item
                            return item.get('score') or item.get('Score') or 0
                        return 0

                    data['liquidity_risk'] = get_score('Liquidity Risk')
                    data['market_risk'] = get_score('Market Risk')
                    data['credit_risk'] = get_score('Credit Risk')
                    data['governance_risk'] = get_score('Governance Risk')
                return data
            return {}
        except Exception as e:
            print(f"Search Fallback Error: {e}")
            return {}
