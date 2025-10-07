import gradio as gr
import sys
import io
from contextlib import redirect_stdout, redirect_stderr
from features.ticket_generator import message_gpt
from features.chatbot import chat_with_knowledge_base, Knowledge
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
        
        def update_knowledge_base(progress=gr.Progress()):
            """Update the knowledge base from Confluence and force rebuild embeddings."""
            import threading
            import time
            import queue
            
            # Helper functions for better readability
            def format_elapsed_time(elapsed_seconds):
                """Format elapsed time into a human-readable string."""
                minutes = elapsed_seconds // 60
                seconds = elapsed_seconds % 60
                return f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
            
            def collect_queue_output(output_queue):
                """Collect all available output from the queue."""
                outputs = []
                try:
                    while True:
                        output = output_queue.get_nowait()
                        if output and output.strip():
                            outputs.append(output.strip())
                except queue.Empty:
                    pass
                return outputs
            
            def fetch_confluence_data_with_timeout(timeout=120):
                """Fetch Confluence data in a separate thread with timeout."""
                def fetch_data():
                    try:
                        webscraper.write_confluence_data_to_file()
                        return True
                    except Exception as e:
                        print(f"Confluence fetch error: {e}")
                        return False
                
                fetch_thread = threading.Thread(target=fetch_data)
                fetch_thread.daemon = True
                fetch_thread.start()
                
                start_time = time.time()
                while fetch_thread.is_alive() and (time.time() - start_time) < timeout:
                    elapsed = int(time.time() - start_time)
                    yield f"⏳ Confluence fetch in progress... ({elapsed}s elapsed)\n"
                    time.sleep(30)
                
                if fetch_thread.is_alive():
                    yield "⚠️ Confluence fetch taking too long, proceeding with existing data...\n"
                else:
                    yield "✅ Confluence data fetched successfully!\n"
            
            class RealtimeCapture:
                """Custom stdout capture that forwards output to queue in real-time."""
                def __init__(self, queue_ref, original_stdout):
                    self.queue = queue_ref
                    self.original_stdout = original_stdout
                
                def write(self, text):
                    if text and text.strip():
                        self.queue.put(text)
                    self.original_stdout.write(text)
                
                def flush(self):
                    self.original_stdout.flush()
            
            def create_embeddings_with_monitoring(knowledge, chunks, output_queue):
                """Create embeddings with stdout monitoring."""
                embedding_result = {"success": False, "error": None}
                
                def create_embeddings():
                    old_stdout = sys.stdout
                    try:
                        # Redirect stdout to capture output
                        sys.stdout = RealtimeCapture(output_queue, old_stdout)
                        knowledge.get_embeddings_using_Azure(chunks, update_knowledge_base=True)
                        embedding_result["success"] = True
                    except Exception as e:
                        embedding_result["error"] = str(e)
                    finally:
                        sys.stdout = old_stdout
                
                # Start embedding thread
                embedding_thread = threading.Thread(target=create_embeddings)
                embedding_thread.daemon = True
                embedding_thread.start()
                
                return embedding_thread, embedding_result
            
            def monitor_embedding_progress(embedding_thread, output_queue, update_interval=60):
                """Monitor embedding progress and yield updates."""
                start_time = time.time()
                last_update = 0
                recent_outputs = []
                
                while embedding_thread.is_alive():
                    elapsed = int(time.time() - start_time)
                    
                    # Collect new outputs
                    new_outputs = collect_queue_output(output_queue)
                    recent_outputs.extend(new_outputs)
                    
                    # Yield immediate updates if we have new output
                    if new_outputs:
                        yield "".join(f"{output}\n" for output in new_outputs)
                    
                    # Periodic status updates
                    elif elapsed - last_update >= update_interval:
                        time_str = format_elapsed_time(elapsed)
                        status_update = f"⏳ Embedding creation in progress... ({time_str} elapsed)\n"
                        
                        # Show recent progress
                        # if recent_outputs:
                        #     status_update += "📝 Recent progress:\n"
                        #     for output in recent_outputs[-2:]:
                        #         status_update += f"   {output}\n"
                        
                        # yield status_update
                        last_update = elapsed
                    
                    time.sleep(30)  # Check every 30 seconds
            
            def finalize_embedding_results(embedding_result, output_queue):
                """Process final embedding results and remaining output."""
                # Collect any remaining output
                remaining_outputs = collect_queue_output(output_queue)
                final_output = ""
                
                if embedding_result["success"]:
                    final_output += "✅ Embedding creation completed successfully!\n"
                    
                    if remaining_outputs:
                        final_output += "📝 Final embedding logs:\n"
                        # Show last 5 outputs
                        for output in remaining_outputs[-5:]:
                            final_output += f"   {output}\n"
                
                elif embedding_result["error"]:
                    final_output += f"❌ Error during embedding creation: {embedding_result['error']}\n"
                    raise Exception(embedding_result["error"])
                else:
                    final_output += "✅ Embedding creation completed!\n"
                
                return final_output
            
            # Main execution flow
            log_output = ""
            
            try:
                # Step 1: Initialize
                progress(0, desc="Starting knowledge base update...")
                log_output += "🔄 Starting knowledge base update...\n"
                yield log_output
                
                # Step 2: Fetch Confluence data
                progress(0.1, desc="Fetching latest data from Confluence...")
                log_output += "📥 Fetching latest data from Confluence...\n"
                yield log_output
                
                try:
                    for update in fetch_confluence_data_with_timeout():
                        log_output += update
                        yield log_output
                except Exception as confluence_error:
                    log_output += f"⚠️ Confluence fetch failed: {str(confluence_error)}\n"
                    log_output += "📁 Proceeding with existing local data...\n"
                    yield log_output
                
                # Step 3: Process documents
                progress(0.2, desc="Processing documents and creating chunks...")
                log_output += "🔍 Processing documents and creating chunks...\n"
                yield log_output
                
                knowledge = Knowledge()
                chunks = knowledge.process_confluence_data()
                log_output += f"📊 Found {len(chunks)} document chunks to process\n"
                yield log_output
                
                # Step 4: Create embeddings
                progress(0.3, desc="Creating embeddings with rate limiting...")
                log_output += "🚀 Starting embedding creation with rate limiting...\n"
                log_output += "⚠️ This will take several minutes due to API rate limits...\n"
                yield log_output
                
                try:
                    output_queue = queue.Queue()
                    embedding_thread, embedding_result = create_embeddings_with_monitoring(
                        knowledge, chunks, output_queue
                    )
                    
                    # Monitor progress
                    for progress_update in monitor_embedding_progress(embedding_thread, output_queue):
                        log_output += progress_update
                        yield log_output
                    
                    # Finalize results
                    final_output = finalize_embedding_results(embedding_result, output_queue)
                    log_output += final_output
                    yield log_output
                    
                except Exception as embedding_error:
                    log_output += f"❌ Error during embedding creation: {str(embedding_error)}\n"
                    yield log_output
                    raise
                
                # Step 5: Complete
                progress(1.0, desc="Knowledge base update completed!")
                log_output += "✅ Knowledge base successfully updated!\n"
                log_output += "🎉 You can now ask questions with the latest information!\n"
                yield log_output
                
            except Exception as e:
                progress(1.0, desc="Error occurred during update")
                log_output += f"❌ Error updating knowledge base: {str(e)}\n"
                yield log_output
        
        gr.ChatInterface(fn=chat_with_knowledge_base, type="messages", chatbot=chatbot)
        with gr.Accordion("ℹ️ Need to update knowledge base?", open=False):
            gr.Markdown("⚠️ **Note**: Knowledge base update may take 5-15 minutes due to API rate limiting.")
            
            with gr.Row():
                fetch_update_btn = gr.Button("📥 Update Knowledge from Confluence", elem_classes=["custom-btn-1"])
            
            # Progress and log display
            update_logs = gr.Textbox(
                label="📋 Update Progress & Logs", 
                lines=8, 
                value="", 
                interactive=False,
                visible=True,
                show_copy_button=True
            )
            
            # Button click handler
            fetch_update_btn.click(
                fn=update_knowledge_base,
                outputs=[update_logs]
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