"""
Azure Key Vault utility for accessing secrets using VS Code credentials.
"""

from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential, ChainedTokenCredential, AzureCliCredential, VisualStudioCodeCredential
from typing import Optional
import os


class AzureKeyVaultClient:
    """
    Azure Key Vault client that uses VS Code credentials for authentication.
    """
    
    def __init__(self, key_vault_url: str):
        """
        Initialize the Key Vault client.
        
        Args:
            key_vault_url: The URL of your Azure Key Vault (e.g., "https://your-keyvault.vault.azure.net/")
        """
        self.key_vault_url = key_vault_url
        self.client = None
        self._setup_credential()
    
    def _setup_credential(self):
        """
        Setup Azure credentials with priority for VS Code authentication.
        """
        try:
            # Create a chained credential that tries VS Code first, then falls back to other methods
            credential_chain = ChainedTokenCredential(
                VisualStudioCodeCredential(),  # VS Code credentials (preferred)
                AzureCliCredential(),          # Azure CLI credentials (fallback)
                DefaultAzureCredential()       # Default credential chain (final fallback)
            )
            
            # Create the Key Vault client
            self.client = SecretClient(vault_url=self.key_vault_url, credential=credential_chain)
            print(f"✅ Successfully connected to Key Vault: {self.key_vault_url}")
            
        except Exception as e:
            print(f"❌ Failed to connect to Key Vault: {e}")
            self.client = None
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Retrieve a secret from Key Vault.
        
        Args:
            secret_name: Name of the secret to retrieve
            
        Returns:
            Secret value or None if not found/error
        """
        if not self.client:
            print("❌ Key Vault client not initialized")
            return None
        
        try:
            secret = self.client.get_secret(secret_name)
            print(f"✅ Successfully retrieved secret: {secret_name}")
            return secret.value
        except Exception as e:
            print(f"❌ Failed to retrieve secret '{secret_name}': {e}")
            return None
    
    def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """
        Set a secret in Key Vault.
        
        Args:
            secret_name: Name of the secret
            secret_value: Value of the secret
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            print("❌ Key Vault client not initialized")
            return False
        
        try:
            self.client.set_secret(secret_name, secret_value)
            print(f"✅ Successfully set secret: {secret_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to set secret '{secret_name}': {e}")
            return False
    
    def list_secrets(self) -> list:
        """
        List all secret names in the Key Vault.
        
        Returns:
            List of secret names
        """
        if not self.client:
            print("❌ Key Vault client not initialized")
            return []
        
        try:
            secrets = []
            for secret_properties in self.client.list_properties_of_secrets():
                secrets.append(secret_properties.name)
            print(f"✅ Found {len(secrets)} secrets in Key Vault")
            return secrets
        except Exception as e:
            print(f"❌ Failed to list secrets: {e}")
            return []


def load_config_from_keyvault(key_vault_url: str, secret_mappings: dict) -> dict:
    """
    Load configuration values from Azure Key Vault.
    
    Args:
        key_vault_url: URL of the Key Vault
        secret_mappings: Dictionary mapping config keys to secret names
                        e.g., {"OPENAI_KEY": "openai-api-key", "AZURE_TOKEN": "azure-devops-token"}
    
    Returns:
        Dictionary with configuration values
    """
    kv_client = AzureKeyVaultClient(key_vault_url)
    config = {}
    
    for config_key, secret_name in secret_mappings.items():
        secret_value = kv_client.get_secret(secret_name)
        if secret_value:
            config[config_key] = secret_value
        else:
            print(f"⚠️ Could not retrieve {config_key} from Key Vault")
    
    return config


# Example usage function
def example_usage():
    """
    Example of how to use the Azure Key Vault client.
    """
    # Replace with your Key Vault URL
    key_vault_url = "https://your-keyvault-name.vault.azure.net/"
    
    # Initialize client
    kv_client = AzureKeyVaultClient(key_vault_url)
    
    # Get a secret
    openai_key = kv_client.get_secret("openai-api-key")
    if openai_key:
        print(f"Retrieved OpenAI key: {openai_key[:10]}...")
    
    # Set a secret
    success = kv_client.set_secret("test-secret", "test-value")
    
    # List all secrets
    secrets = kv_client.list_secrets()
    print(f"Secrets in vault: {secrets}")


if __name__ == "__main__":
    example_usage()