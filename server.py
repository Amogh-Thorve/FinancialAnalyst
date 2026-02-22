import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

# Import existing agent logic
# Ensure these files are in the same directory or PYTHONPATH
from agent import FinancialAnalystAgent
from pdf_processor import extract_text_from_pdf
from report_generator import generate_pdf
import uuid

load_dotenv()

app = FastAPI(title="Financial Analyst Agent API")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve index.html at root
@app.get("/")
async def read_root():
    return FileResponse('static/index.html')

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev only. In prod, specify the frontend URL.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Agent Instance
class AgentState:
    agent: Optional[FinancialAnalystAgent] = None

state = AgentState()

class InitRequest(BaseModel):
    groq_api_key: str
    alpha_vantage_key: Optional[str] = None

class ChatRequest(BaseModel):
    message: str

class AnalyzeRequest(BaseModel):
    ticker: str

@app.post("/api/init")
async def init_agent(request: InitRequest):
    try:
        # If keys are provided, use them. Otherwise rely on environment (handled by Agent init if None passed, but we pass explicitly if provided)
        # The Agent class in agent.py prefers passed args over os.getenv if passed.
        
        # We need to handle the case where keys might be empty strings
        g_key = request.groq_api_key if request.groq_api_key else None
        av_key = request.alpha_vantage_key if request.alpha_vantage_key else None
        
        state.agent = FinancialAnalystAgent(api_key=g_key, alpha_vantage_key=av_key)
        return {"status": "success", "message": "Agent initialized successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not state.agent:
        raise HTTPException(status_code=400, detail="Agent not initialized. Please set API keys first.")
    
    try:
        # Save temp file
        temp_file_path = f"temp_{file.filename}"
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Text extraction logic (sync for simplicity, could be async)
        text, num_pages = extract_text_from_pdf(temp_file_path)
        
        # Cleanup
        os.remove(temp_file_path)

        if not text:
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")

        state.agent.set_context(text)
        
        # Extract metrics for dashboard
        metrics = state.agent.extract_metrics()
        
        # Extract metadata for sidebar
        metadata = state.agent.extract_metadata()
        if metadata:
            metadata["pages_analyzed"] = num_pages
            metadata["data_source"] = file.filename

        return {
            "message": f"Successfully processed {file.filename}",
            "metrics": metrics,
            "metadata": metadata
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/api/analyze")
async def analyze_stock(request: AnalyzeRequest):
    if not state.agent:
         # Try to init from env if not already
        try:
            state.agent = FinancialAnalystAgent()
        except:
             raise HTTPException(status_code=400, detail="Agent not initialized. Please set API keys first.")
    
    try:
        print(f"DEBUG: Analyzing ticker: {request.ticker}")
        metrics = state.agent.analyze_stock(request.ticker)
        
        if not metrics:
             raise HTTPException(status_code=400, detail="Could not analyze stock. Please check the ticker.")

        return {
            "message": f"Successfully analyzed {request.ticker}",
            "metrics": metrics
        }
        
    except Exception as e:
        print(f"ERROR in /api/analyze: {e}")
        raise HTTPException(status_code=500, detail=f"Error analyzing stock: {str(e)}")

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not state.agent:
         # Try to init from env if not already
        try:
            state.agent = FinancialAnalystAgent()
        except:
             raise HTTPException(status_code=400, detail="Agent not initialized.")

    from fastapi.responses import StreamingResponse
    
    print(f"DEBUG: Processing message: {request.message}")
    
    return StreamingResponse(
        state.agent.run_stream(request.message),
        media_type="text/plain"
    )

@app.post("/api/reset")
async def reset():
    if state.agent:
        state.agent.history = []
    # Note: we keep the context (PDF) unless explicitly cleared, but usually reset implies clearing conversation history.
    # If we want to clear everything including PDF context, we would do:
    # if state.agent: state.agent = None (or create new)
    # For now, let's just clear history as that's typical "New Chat" behavior while keeping the doc.
    # To fully reset, the user can just refresh the page (which clears the UI state) but backend state persists.
    # Let's actually fully reset the agent for a clean slate.
    state.agent = None 
    return {"status": "success", "message": "Agent reset."}

@app.get("/api/export_pdf")
async def export_pdf():
    if not state.agent:
         raise HTTPException(status_code=400, detail="Agent not initialized.")
    
    # Check if we have anything to export
    if not state.agent.history and not state.agent.last_metrics:
         raise HTTPException(status_code=400, detail="No data available to export. Please perform an analysis first.")
    
    try:
        # Create temp filename
        filename = f"report_{uuid.uuid4()}.pdf"
        filepath = os.path.join("static", filename)
        
        # Pass both history and last_metrics
        generate_pdf(state.agent.history, filepath, metrics=state.agent.last_metrics)
        
        return FileResponse(filepath, filename=filename, media_type='application/pdf')
    except Exception as e:
        print(f"PDF Export Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")

@app.get("/api/env")
async def get_env():
    return {
        "groq_api_key": os.getenv("GROQ_API_KEY", ""),
        "alpha_vantage_key": os.getenv("ALPHA_VANTAGE_API_KEY", "")
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
