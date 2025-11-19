from __future__ import annotations
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional
from dotenv import load_dotenv
from azure_keyvault import AzureKeyVaultClient


load_dotenv()


def _get_env(key: str, default: Optional[str] = None, *, required: bool = False) -> Optional[str]:
    """Lookup an environment variable, optionally enforcing its presence."""

    value = os.getenv(key, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value

@lru_cache(maxsize=None)
def _get_key_vault_client(vault_url: str) -> AzureKeyVaultClient:
    """Return a cached Key Vault client for the given vault URL."""
    return AzureKeyVaultClient(vault_url)


def get_secret(secret_name: str, vault_url: Optional[str] = None) -> Optional[str]:
    """Retrieve a Key Vault secret from the specified vault (or default vault)."""
    vault = vault_url or _get_env("KEY_VAULT_URL", "https://arch-kv-poc.vault.azure.net/")
    return _get_key_vault_client(vault).get_secret(secret_name)


def _split_space_keys(raw_value: str) -> list[str]:
    """Normalize SPACE_KEYS input allowing comma or pipe delimiters."""

    normalized: list[str] = []
    for part in raw_value.replace(",", "|").split("|"):
        part = part.strip()
        if part:
            normalized.append(part)
    return normalized


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of configuration values."""

    key_vault_url: str = _get_env("KEY_VAULT_URL", "https://arch-kv-poc.vault.azure.net/")
    openai_key_vault_url: str = _get_env("OPENAI_KEY_VAULT_URL", "https://kv-glb-vault1-dev.vault.azure.net/")
    jira_domain: Optional[str] = _get_env("JIRA_DOMAIN", "invoicecloud.atlassian.net")
    jira_email: Optional[str] = _get_env("JIRA_EMAIL", "sshang@invoicecloud.com")
    jira_api_token: Optional[str] = _get_env("JIRA_API_TOKEN")
    openai_key: Optional[str] = _get_env("OPENAI_KEY")
    azure_devops_token: Optional[str] = _get_env("Azure_DevOps_Token")
    file_dir: str = _get_env("FILE_DIR", "doc") or "doc"
    space_keys_raw: str = os.getenv("SPACE_KEYS", "EA, ED, ET, EN, Implementa, IM, PRODUCT, icinfradoc, PE, platform, PMK, DS")
    ic_base_url: str = _get_env("IC_BASE_URL", "https://ca-pri-playground2-dev.openai.azure.com")
    ic_api_version: str = _get_env("IC_API_VERSION", "2025-01-01")
    ic_chat_url: str = _get_env(
        "IC_OPENAI_URL",
        "https://ca-pri-playground2-dev.openai.azure.com/openai/deployments/cd-pri-playground2-dev/chat/completions?api-version=2025-01-01-preview",
    )
    ic_embeddings_url: str = _get_env("IC_EMBEDDINGS_URL", "https://arch-ai-svc.cognitiveservices.azure.com/")
    ic_embeddings_apikey: Optional[str] = _get_env("IC_Embeddings_APIKEY")
    ic_embeddings_model: str = _get_env("IC_EMBEDDINGS_MODEL", "text-embedding-ada-002")
    vector_store_address: str = _get_env("VECTOR_STORE_ADDRESS", "https://arch-ai-search-poc.search.windows.net")
    vector_store_password: Optional[str] = _get_env("Vector_Store_Password")



settings = Settings()

Space_Keys = _split_space_keys(settings.space_keys_raw)
File_Dir = settings.file_dir
JIRA_DOMAIN = settings.jira_domain
JIRA_EMAIL = settings.jira_email
JIRA_API_TOKEN = settings.jira_api_token
OPENAI_KEY = settings.openai_key 
Azure_DevOps_Token = settings.azure_devops_token
IC_Base_URL = settings.ic_base_url
IC_API_VERSION = settings.ic_api_version
IC_OpenAI_URL = settings.ic_chat_url
IC_Embeddings_URL = settings.ic_embeddings_url
IC_Embeddings_APIKEY = settings.ic_embeddings_apikey
IC_Embeddings_Model = settings.ic_embeddings_model
vector_store_address = settings.vector_store_address
vector_store_password = settings.vector_store_password
vault_url = settings.key_vault_url


def get_openai_key() -> Optional[str]:
    """Get OpenAI key from env or fallback to Key Vault."""
    return OPENAI_KEY or get_secret("Playground-OpenAi-ApiKey", settings.openai_key_vault_url)


def get_embedding_api_key() -> Optional[str]:
    """Get embedding API key from env or fallback to Key Vault."""
    return IC_Embeddings_APIKEY or get_secret("text-embedding-ada-002-key", vault_url)

# if env variables are not set, fetch from Key Vault
OPENAI_KEY = get_openai_key()
IC_Embeddings_APIKEY = get_embedding_api_key()

__all__ = [
    "File_Dir",
    "Space_Keys",
    "JIRA_DOMAIN",
    "JIRA_EMAIL",
    "JIRA_API_TOKEN",
    "OPENAI_KEY",
    "Azure_DevOps_Token",
    "IC_Base_URL",
    "IC_API_VERSION",
    "IC_OpenAI_URL",
    "IC_Embeddings_URL",
    "IC_Embeddings_APIKEY",
    "IC_Embeddings_Model",
    "vector_store_address",
    "vector_store_password",
    "vault_url",
    "get_secret",
    "settings",
]