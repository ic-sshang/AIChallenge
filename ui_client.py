"""Gradio UI that connects to FastAPI backend."""

import gradio as gr
import requests
from typing import List, Dict

# Backend API URL - adjust for your deployment
API_BASE_URL = "http://localhost:8000"


def call_chat_api(message: Dict, history: List[Dict]) -> str:
    """Call the chat API."""
    try:
        # Extract text content from message dict
        question = message.get("content", "") if isinstance(message, dict) else str(message)
        response = requests.post(
            f"{API_BASE_URL}/api/chat",
            json={"message": question, "history": history},
            timeout=120
        )
        response.raise_for_status()
        return response.json()["answer"]
    except Exception as e:
        return f"❌ Error: {str(e)}"


def call_generate_jira_content_api(description: str, model_type: str) -> str:
    """Call the JIRA content generation API."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/jira/generate-content",
            json={"description": description, "model_type": model_type},
            timeout=60
        )
        response.raise_for_status()
        return response.json()["content"]
    except Exception as e:
        return f"❌ Error: {str(e)}"


def call_create_jira_ticket_api(
    summary: str,
    content: str,
    issue_type: str,
    email: str,
    token: str,
    project_key: str
) -> str:
    """Call the JIRA ticket creation API."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/jira/create-ticket",
            json={
                "summary": summary,
                "content": content,
                "issue_type": issue_type,
                "email": email if email else None,
                "token": token if token else None,
                "project_key": project_key
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()["result"]
    except Exception as e:
        return f"❌ Error: {str(e)}"


def call_error_analysis_api(error_message: str, repo_url: str):
    """Call the error analysis API."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/error-analysis",
            json={"error_message": error_message, "repo_url": repo_url},
            timeout=600
        )
        response.raise_for_status()
        result = response.json()
        return result["analysis"], result["raw_text"]
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        return error_msg, error_msg


def get_error_samples():
    """Get sample errors and repos from API."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/error-analysis/samples", timeout=10)
        response.raise_for_status()
        data = response.json()
        return data["errors"], data["repos"]
    except Exception:
        return [], []


with gr.Blocks(css="""
               .custom-btn-1 {background-color: #1976d2; color: white; border-radius: 8px;}
               .custom-btn-2 {background-color: #e53935; color: white; border-radius: 8px;} 
               .btn-active { background-color: #1976d2 !important; color: white !important; }
               .btn-inactive { background-color: #e0e0e0 !important; color: black !important; }
               .error-analysis-header { 
                   background: linear-gradient(90deg, #f3f4f6, #e5e7eb); 
                   padding: 1rem; 
                   border-radius: 8px; 
                   margin-bottom: 1rem; 
               }
               .analysis-results {
                   max-height: 600px;
                   overflow-y: auto;
                   padding: 1rem;
                   border: 1px solid #e0e0e0;
                   border-radius: 8px;
                   background-color: #fafafa;
               }
               """) as main_ui:
    
    gr.Markdown("# 🤖 AI Engineering Assistant")
    
    with gr.Row():
        chat_btn = gr.Button("💬 Engineering Q&A", elem_classes=["btn-active"])
        jira_btn = gr.Button("📝 Jira Creator", elem_classes=["btn-inactive"])
        error_btn = gr.Button("🔍 Error Analysis", elem_classes=["btn-inactive"])
    
    # JIRA Page
    with gr.Column(visible=False) as jira_page:
        gr.Markdown("## 📝 JIRA Ticket Creator")
        summary = gr.Textbox(label="Summary", placeholder="Enter issue summary")
        description = gr.Textbox(label="Description", placeholder="Enter issue description", lines=4)
        model_type = gr.Dropdown(
            choices=["gpt-5-mini", "gpt-4o-mini"],
            value="gpt-4o-mini",
            label="Model Type"
        )
        issue_type = gr.Dropdown(
            choices=["Task", "Bug", "Story"],
            value="Task",
            label="Issue Type"
        )
        project_key = gr.Dropdown(
            choices=[("BMS", "BMS"), ("Pulse", "PUL"), ("Platform", "PLAT")],
            value="BMS",
            label="Project Team"
        )

        show_creds = gr.Checkbox(label="Enter User Email & API Token", value=False)
        instruction = gr.HighlightedText(
            value=[("""To get an API token: \n1. Log in to https://id.atlassian.com/manage-profile/security. \n2. Go to "API tokens" and click "Create API token".\n3. Copy the token.""", None)],
            color_map={"highlight": "yellow"},
            visible=False
        )
        email_box = gr.Textbox(label="Email", placeholder="Enter your email", visible=False)
        token_box = gr.Textbox(label="API Token", placeholder="Enter your API token", type="password", visible=False)

        submit_btn = gr.Button("Generate Content Preview", elem_classes=["custom-btn-1"])
        output_content = gr.Textbox(label="Generated Content", lines=5)
        
        create_btn = gr.Button("Create JIRA Ticket", elem_classes=["custom-btn-2"])
        output = gr.Textbox(label="Result")

        def toggle_creds(show):
            return {
                email_box: gr.update(visible=show),
                token_box: gr.update(visible=show),
                instruction: gr.update(visible=show)
            }

        show_creds.change(toggle_creds, inputs=[show_creds], outputs=[email_box, token_box, instruction])
        submit_btn.click(
            fn=call_generate_jira_content_api,
            inputs=[description, model_type],
            outputs=output_content
        )
        create_btn.click(
            fn=call_create_jira_ticket_api,
            inputs=[summary, output_content, issue_type, email_box, token_box, project_key],
            outputs=output
        )
    
    # Error Analysis Page
    with gr.Column(visible=False) as error_page:
        gr.Markdown("## 🔍 Error Analysis & Root Cause Detection")
        
        error_samples, repo_samples = get_error_samples()
        
        with gr.Row():
            with gr.Column(scale=2):
                error_message = gr.Textbox(
                    label="Error Message",
                    placeholder="Paste your error message here",
                    lines=8
                )
            with gr.Column(scale=1):
                gr.Markdown("### 💡 Sample Errors")
                sample_error_dropdown = gr.Dropdown(
                    choices=error_samples,
                    label="Quick Examples",
                    value=None
                )
        
        with gr.Row():
            with gr.Column(scale=2):
                repo_url = gr.Textbox(
                    label="Azure DevOps Repository URL",
                    placeholder="https://dev.azure.com/organization/project/_git/repository"
                )
            with gr.Column(scale=1):
                gr.Markdown("### 📚 Sample Repositories")
                sample_repo_dropdown = gr.Dropdown(
                    choices=[(f"{repo['name']} - {repo['description']}", repo['url']) for repo in repo_samples],
                    label="Quick Examples",
                    value=None
                )
        
        with gr.Row():
            analyze_btn = gr.Button("🚀 Start Error Analysis", elem_classes=["custom-btn-1"])
            clear_btn = gr.Button("🗑️ Clear", elem_classes=["custom-btn-2"])
        
        analysis_output = gr.Markdown(value="", elem_classes=["analysis-results"])
        
        with gr.Accordion("📄 Raw Text", open=False):
            raw_output = gr.Textbox(label="Raw Text", lines=10, show_copy_button=True)
        
        sample_error_dropdown.change(lambda x: x if x else "", inputs=[sample_error_dropdown], outputs=[error_message])
        sample_repo_dropdown.change(lambda x: x if x else "", inputs=[sample_repo_dropdown], outputs=[repo_url])
        clear_btn.click(lambda: ("", "", "", ""), outputs=[error_message, repo_url, analysis_output, raw_output])
        analyze_btn.click(
            fn=call_error_analysis_api,
            inputs=[error_message, repo_url],
            outputs=[analysis_output, raw_output]
        )
    
    # Chat Page
    with gr.Column(visible=True) as chat_page:
        chatbot = gr.Chatbot(
            height=600,
            value=[{
                "role": "assistant",
                "content": "👋 Hi, I am your engineering Q&A assistant. Ask me anything!"
            }],
            type="messages"
        )
        gr.ChatInterface(fn=call_chat_api, type="messages", chatbot=chatbot)
    
    # Page navigation
    def show_jira():
        return {
            jira_page: gr.update(visible=True),
            chat_page: gr.update(visible=False),
            error_page: gr.update(visible=False),
            jira_btn: gr.update(elem_classes=["btn-active"]),
            chat_btn: gr.update(elem_classes=["btn-inactive"]),
            error_btn: gr.update(elem_classes=["btn-inactive"])
        }

    def show_chat():
        return {
            jira_page: gr.update(visible=False),
            chat_page: gr.update(visible=True),
            error_page: gr.update(visible=False),
            jira_btn: gr.update(elem_classes=["btn-inactive"]),
            chat_btn: gr.update(elem_classes=["btn-active"]),
            error_btn: gr.update(elem_classes=["btn-inactive"])
        }

    def show_error():
        return {
            jira_page: gr.update(visible=False),
            chat_page: gr.update(visible=False),
            error_page: gr.update(visible=True),
            jira_btn: gr.update(elem_classes=["btn-inactive"]),
            chat_btn: gr.update(elem_classes=["btn-inactive"]),
            error_btn: gr.update(elem_classes=["btn-active"])
        }
    
    jira_btn.click(show_jira, outputs=[jira_page, chat_page, error_page, jira_btn, chat_btn, error_btn])
    chat_btn.click(show_chat, outputs=[jira_page, chat_page, error_page, jira_btn, chat_btn, error_btn])
    error_btn.click(show_error, outputs=[jira_page, chat_page, error_page, jira_btn, chat_btn, error_btn])


if __name__ == "__main__":
    main_ui.launch(server_name="0.0.0.0", server_port=7860)
