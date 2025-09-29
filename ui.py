import gradio as gr
from features.ticket_generator import message_gpt
from features.chatbot import chat_with_knowledge_base
from agents.create_tickets import JIRACreator
from agents.create_files import WebScraper

with gr.Blocks(css="""
               .custom-btn-1 {background-color: #1976d2; color: white; border-radius: 8px;}
               .custom-btn-2 {background-color: #e53935; color: white; border-radius: 8px;} 
               .btn-active { background-color: #1976d2 !important; color: white !important; }
               .btn-inactive { background-color: #e0e0e0 !important; color: black !important; }
               """) as main_ui:
    with gr.Row():
        chat_btn = gr.Button("💬 Engineering Q&A",elem_classes=["btn-active"])
        jira_btn = gr.Button("📝 Jira Creator",elem_classes=["btn-inactive "])
        
    with gr.Column(visible=False) as jira_page:
        summary = gr.Textbox(label="Summary", placeholder="Enter issue summary")
        description = gr.Textbox(label="Description", placeholder="Enter issue description", lines=4)
        model_type = gr.Dropdown(choices=["gpt-5-mini", "gpt-4o-mini"], value="gpt-4o-mini", label="Model Type")
        issue_type = gr.Dropdown(choices=["Task", "Bug", "Story"], value="Task", label="Issue Type")
        project_key = gr.Dropdown(choices=[("BMS", "BMS"), ("Pulse", "PUL"), ("Platform", "PLAT")], value="BMS", label="Project Team")

        show_creds = gr.Checkbox(label="Enter User Email & API Token", value=False)
        instruction = gr.HighlightedText(value=[("""If you don't enter your own email and API token, system will use a default account to create the ticket. To get an API token: \n1. Log in to https://id.atlassian.com/manage-profile/security. \n2. Go to "API tokens" and click "Create API token".\n3. Copy the token and use it in your application.""", None)],
                                                color_map={"highlight": "yellow"}, visible=False)  
        email_box = gr.Textbox(label="Email", placeholder="Enter your email", visible=False)
        token_box = gr.Textbox(label="API Token", placeholder="Enter your API token", type="password", visible=False)

        submit_btn = gr.Button("Generate Content Preview",elem_classes=["custom-btn-1"])
        output_content = gr.Textbox(label="Generated Content", lines=5)
        
        create_btn = gr.Button("Create JIRA Ticket",elem_classes=["custom-btn-2"])
        output = gr.Textbox(label="Result")

        def toggle_creds(show):
            return {email_box: gr.update(visible=show), token_box: gr.update(visible=show), instruction: gr.update(visible=show)}

        show_creds.change(toggle_creds, inputs=[show_creds], outputs=[email_box, token_box, instruction])

        submit_btn.click(fn=message_gpt, inputs=[description, model_type], outputs=output_content)
        create_btn.click(fn=JIRACreator.create_ticket, inputs=[summary, output_content, issue_type, email_box, token_box, project_key], outputs=output)
        

    with gr.Column(visible=True) as chat_page:
        chatbot = gr.Chatbot(
        value=[
            {"role": "assistant", "content": (
                "👋 Hi, I am your engineering Q&A assistant. "
                "You can ask me any questions related to product, system architecture and engineering, "
                "and I will search relevant information from Confluence."
            )}
        ],
        type="messages"
    )
        webscraper = WebScraper()
        gr.ChatInterface(fn=chat_with_knowledge_base, type="messages", chatbot=chatbot)
        with gr.Accordion("ℹ️ Need to update knowledge base?", open=False):
            gr.Button("update knowledge from Confluence", elem_classes=["custom-btn-1"]).click(
            fn= webscraper.write_confluence_data_to_file,
            inputs=[],
            outputs=[],
            js="() => { alert('Updating knowledge base from Confluence. This may take a few minutes.'); }"
            )
        
      

    def show_jira():
        return {
                jira_page: gr.update(visible=True), 
                chat_page: gr.update(visible=False),
                jira_btn: gr.update(elem_classes=["btn-active"]),
                chat_btn: gr.update(elem_classes=["btn-inactive"])
                }

    def show_chat():
        return {
            jira_page: gr.update(visible=False), 
            chat_page: gr.update(visible=True),
            jira_btn: gr.update(elem_classes=["btn-inactive"]),
            chat_btn: gr.update(elem_classes=["btn-active"]),
            }

    
    jira_btn.click(show_jira, outputs=[jira_page, chat_page, jira_btn, chat_btn])
    chat_btn.click(show_chat, outputs=[jira_page, chat_page, jira_btn, chat_btn])

