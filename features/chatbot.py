import gradio as gr
import os
import time
import math
from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI
from langchain_chroma import Chroma
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.schema import Document
from tiktoken import get_encoding
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate
from config import OPENAI_KEY, File_Dir,IC_OpenAI_URL, IC_Embeddings_APIKEY, IC_Embeddings_URL, IC_Embeddings_Model
from system_prompt import chatbot_instruction

enc = get_encoding("cl100k_base")
db_name = ".chroma"

class Knowledge:
    def __init__(self):
        pass

    # Chunk size and overlap can be adjusted based on needs 
    def chunk_text(self, text):  
        """Chunk text into smaller pieces for embedding."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,  # measured in characters or tokens depending on splitter
            chunk_overlap=200
        )
        chunks = splitter.split_text(text)
        return chunks
    
    def safe_chunks(self, text, max_tokens=3000):
        """Ensure chunks are within token limit."""
        chunks = self.chunk_text(text)
        safe = []
        for chunk in chunks:
            tokens = len(enc.encode(chunk))
            if tokens > max_tokens:
                # split further instead of keeping giant chunk
                mid = len(chunk) // 2
                safe.extend([chunk[:mid], chunk[mid:]])
            else:
                safe.append(chunk)
        return safe

    def process_confluence_data(self):
        """Read text files from directory and chunk them."""
        folder_path = File_Dir
        all_chunks = []
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path): 
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                    chunks = self.safe_chunks(text)
                    for chunk in chunks:
                        all_chunks.append(Document(
                            page_content=chunk,
                            metadata={"title": filename}
                        ))
        print(f"Total chunks created: {len(all_chunks)}")
        return all_chunks
    
    def get_embeddings_using_Azure(self, chunks, update_knowledge_base = False):
        """Get or create embeddings using Azure OpenAI."""
        emb = AzureOpenAIEmbeddings(
                model = IC_Embeddings_Model,
                azure_endpoint = IC_Embeddings_URL,
                api_key = IC_Embeddings_APIKEY,
                openai_api_version="2024-02-01"
            )
        if os.path.exists(db_name) and not update_knowledge_base:
            # load existing vectorstore
            vectorstore = Chroma(persist_directory=db_name, embedding_function=emb)
            print(f"Loaded vectorstore with {vectorstore._collection.count()} documents")
            return vectorstore
        else:
            # create new vectorstore with rate limiting
            vectorstore = self._create_vectorstore_with_rate_limiting(chunks, emb)
        return vectorstore

    def _create_vectorstore_with_rate_limiting(self, chunks, embedding_function):
        """Create vectorstore with rate limiting to avoid exceeding API limits."""
        BATCH_SIZE = 100  # Process 100 documents at a time
        MAX_TOKENS_PER_MINUTE = 90000  # Leave some buffer from 100k limit
        DELAY_BETWEEN_BATCHES = 1  # seconds
        
        print(f"Processing {len(chunks)} chunks in batches of {BATCH_SIZE}", flush=True)
        
        # Calculate total tokens to estimate processing time
        total_tokens = sum(len(enc.encode(chunk.page_content)) for chunk in chunks)
        estimated_minutes = math.ceil(total_tokens / MAX_TOKENS_PER_MINUTE)
        print(f"Estimated processing time: {estimated_minutes} minutes for {total_tokens} tokens", flush=True)
        
        vectorstore = None
        
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i:i + BATCH_SIZE]
            batch_tokens = sum(len(enc.encode(chunk.page_content)) for chunk in batch)
            
            print(f"Processing batch {i//BATCH_SIZE + 1}/{math.ceil(len(chunks)/BATCH_SIZE)} "
                  f"({len(batch)} docs, {batch_tokens} tokens)", flush=True)
            
            try:
                if vectorstore is None:
                    # Create initial vectorstore with first batch
                    print("Creating initial vectorstore...", flush=True)
                    vectorstore = Chroma.from_documents(
                        documents=batch,
                        embedding=embedding_function,
                        persist_directory=db_name
                    )
                    print("Initial vectorstore created successfully", flush=True)
                else:
                    # Add subsequent batches to existing vectorstore
                    print("Adding batch to existing vectorstore...", flush=True)
                    vectorstore.add_documents(batch)
                    # print("Batch added successfully", flush=True)
                
                # Add delay to respect rate limits
                if i + BATCH_SIZE < len(chunks):  # Don't delay after last batch
                    # print(f"Waiting {DELAY_BETWEEN_BATCHES} seconds before next batch...", flush=True)
                    time.sleep(DELAY_BETWEEN_BATCHES)
                    
            except Exception as e:
                if "rate limit" in str(e).lower():
                    print(f"Rate limit hit. Waiting 60 seconds...", flush=True)
                    time.sleep(60)
                    print("Retrying after rate limit wait...", flush=True)
                    # Retry the batch
                    if vectorstore is None:
                        vectorstore = Chroma.from_documents(
                            documents=batch,
                            embedding=embedding_function,
                            persist_directory=db_name
                        )
                    else:
                        vectorstore.add_documents(batch)
                    print("Retry successful", flush=True)
                else:
                    print(f"Error processing batch: {e}", flush=True)
                    raise
        
        print(f"Vectorstore created with {vectorstore._collection.count()} documents", flush=True)
        return vectorstore

    def create_qa_chain(self):
        """Create a conversational retrieval chain."""
        # create a new Chat 
        llm = AzureChatOpenAI(azure_deployment="cd-pri-playground2-dev",
                              azure_endpoint= IC_OpenAI_URL,
                              api_key=OPENAI_KEY,
                              api_version="2025-01-01-preview",
                               temperature=0.7)
     
        # set up the conversation memory for the chat
        memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
        chunks = []
        vectorstore = self.get_embeddings_using_Azure(chunks)
        # k is how many chunks to use, can be adjusted based on needs
        retriever = vectorstore.as_retriever(search_kwargs={"k": 200})

        qa_prompt = PromptTemplate(
            input_variables=["context", "question"],
            template=chatbot_instruction
        )

        conversation_chain = ConversationalRetrievalChain.from_llm(llm=llm, retriever=retriever, memory=memory, combine_docs_chain_kwargs={"prompt": qa_prompt})
        
        return conversation_chain

def chat_with_knowledge_base(question, history):
    """Chat with the knowledge base using the conversation chain."""
    knowledge = Knowledge()
    conversation_chain = knowledge.create_qa_chain()
    result = conversation_chain.invoke({"question": question})
    return result["answer"]


# if __name__ == "__main__":
#     view = gr.ChatInterface(chat_with_knowledge_base, type="messages").launch(share=True)
