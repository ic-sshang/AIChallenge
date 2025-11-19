import gradio as gr
from fastapi import FastAPI
from ui import main_ui

app = FastAPI()

app = gr.mount_gradio_app(app, main_ui, path="")

# test in local without FastAPI
# main_ui.launch(inbrowser=True)