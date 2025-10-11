
from dotenv import load_dotenv
import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

load_dotenv()
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")      
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")                 
OPENAI_KEY = os.getenv("OPENAI_KEY")
Azure_DevOps_Token = os.getenv("Azure_DevOps_Token")
File_Dir = "doc"
Space_Keys = ["ED"]
# ["EA","ED", "ET", "EN", "Implementa", "IM", "PRODUCT", "icinfradoc", "PE", "platform", "PMK","DS"]
IC_Base_URL = "https://ca-pri-playground2-dev.openai.azure.com"
IC_API_VERSION = "2025-01-01"
IC_OpenAI_URL = "https://ca-pri-playground2-dev.openai.azure.com/openai/deployments/cd-pri-playground2-dev/chat/completions?api-version=2025-01-01-preview"
IC_Embeddings_URL = "https://arch-ai-svc.cognitiveservices.azure.com/"
IC_Embeddings_APIKEY = os.getenv("IC_Embeddings_APIKEY")
IC_Embeddings_Model = "text-embedding-ada-002"
# vault_url = "https://kv-glb-vault1-dev.vault.azure.net/"
# secret_name = "Playground-OpenAi-ApiKey"
# credential = DefaultAzureCredential()

# client = SecretClient(vault_url=vault_url, credential=credential)
# secret = client.get_secret(secret_name)          # Optional: specify version with get_secret(name, version)
# print("Secret value:", secret.value)