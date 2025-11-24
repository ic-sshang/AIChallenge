"""FastAPI backend for AI Challenge application."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
from features.ticket_generator import message_gpt
from features.chatbot import chat_with_knowledge_base
from features.error_analysis import error_analysis_feature
from agents.create_tickets import JIRACreator

app = FastAPI(title="AI Challenge API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, Any]]] = None


class ChatResponse(BaseModel):
    answer: str


class JIRAContentRequest(BaseModel):
    description: str
    model_type: str = "gpt-4o-mini"


class JIRAContentResponse(BaseModel):
    content: str


class JIRATicketRequest(BaseModel):
    summary: str
    content: str
    issue_type: str = "Task"
    email: Optional[str] = None
    token: Optional[str] = None
    project_key: str = "BMS"


class JIRATicketResponse(BaseModel):
    result: str


class ErrorAnalysisRequest(BaseModel):
    error_message: str
    repo_url: str


class ErrorAnalysisResponse(BaseModel):
    analysis: str
    raw_text: str


# API Endpoints

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "AI Challenge API is running"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with knowledge base."""
    try:
        # Extract question from message field
        question = request.message
        history = request.history or []
        answer = chat_with_knowledge_base(question, history)
        return ChatResponse(answer=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@app.post("/api/jira/generate-content", response_model=JIRAContentResponse)
async def generate_jira_content(request: JIRAContentRequest):
    """Generate JIRA ticket content using GPT."""
    try:
        content = message_gpt(request.description, request.model_type)
        return JIRAContentResponse(content=content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Content generation error: {str(e)}")


@app.post("/api/jira/create-ticket", response_model=JIRATicketResponse)
async def create_jira_ticket(request: JIRATicketRequest):
    """Create a JIRA ticket."""
    try:
        result = JIRACreator.create_ticket(
            summary=request.summary,
            description=request.content,
            issue_type=request.issue_type,
            email=request.email,
            API_token=request.token,
            project_key=request.project_key
        )
        return JIRATicketResponse(result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ticket creation error: {str(e)}")


@app.post("/api/error-analysis", response_model=ErrorAnalysisResponse)
async def analyze_error(request: ErrorAnalysisRequest):
    """Analyze error with AI."""
    try:
        if not request.error_message.strip() or not request.repo_url.strip():
            raise HTTPException(
                status_code=400,
                detail="Both error message and repository URL are required"
            )
        
        result_text = ""
        for update in error_analysis_feature.analyze_error_with_ai(
            request.error_message,
            request.repo_url
        ):
            result_text += update
        
        return ErrorAnalysisResponse(analysis=result_text, raw_text=result_text)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analysis failed: {str(e)}")


@app.get("/api/error-analysis/samples")
async def get_error_samples():
    """Get sample error messages."""
    try:
        return {
            "errors": error_analysis_feature.get_sample_errors(),
            "repos": error_analysis_feature.get_sample_repos()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get samples: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
