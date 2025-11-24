import os
import unicodedata
import requests
import re
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup
from config import JIRA_DOMAIN, JIRA_EMAIL, JIRA_API_TOKEN, Space_Keys, File_Dir, AZURE_STORAGE_CONNECTION_STRING, BLOB_CONTAINER_NAME
from features.chatbot import Knowledge
from azure.storage.blob import BlobServiceClient
from azure.storage.blob import ContentSettings


class WebScraper:
    def __init__(self):
        self.BASE_URL = f"https://{JIRA_DOMAIN}/wiki/rest/api"
        self.auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
        self.blob_service_client = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING
        )
        self.container_client = self.blob_service_client.get_container_client(
            BLOB_CONTAINER_NAME
        )
        try:
            self.container_client.create_container()
            print(f"✓ Created container: {BLOB_CONTAINER_NAME}")
        except Exception as e:
            # Container already exists or other error
            if "ContainerAlreadyExists" in str(e) or "already exists" in str(e).lower():
                print(f"✓ Container already exists: {BLOB_CONTAINER_NAME}")
            else:
                print(f"⚠ Container check: {e}")

    def get_confluence_pages(self, space_key):
        """Fetch all pages from a given Confluence space."""
        url = f"https://{JIRA_DOMAIN}/wiki/rest/api/content/search"
        cql = f"space={space_key} AND type=page"
        all_pages = []

        # initial request
        params = {"cql": cql, "limit": 50, "expand": "body.storage"}
        resp = requests.get(url, params=params, auth=self.auth)
        data = resp.json()

        while True:
            results = data.get("results", [])
            all_pages.extend(results)

            # check if a next page exists
            next_link = data.get("_links", {}).get("next")
            if not next_link:
                break  # no more pages

            # follow the next link
            next_url = f"https://{JIRA_DOMAIN}/wiki{next_link}"
            resp = requests.get(next_url, auth=self.auth)
            data = resp.json()

        return all_pages

    def extract_text(self, page):
        """Extract and clean text from a Confluence page."""
        raw_html = page["body"]["storage"]["value"]
        soup = BeautifulSoup(raw_html, "html.parser")
        return soup.get_text(separator="\n")  # clean text

    def safe_filename(self, name: str) -> str:
        """Generate a safe filename from a given string."""
        # replace invalid characters with underscore
        name = re.sub(r'[\\/*?:"<>|]', "_", name)
        name = unicodedata.normalize("NFKD", name)
        name = re.sub(r'[\\/*?:"<>|]', "_", name)  # Windows-reserved
        name = re.sub(r"\s+", " ", name).strip()
        name = re.sub(r"[\U00010000-\U0010FFFF]", "", name)  # drop emoji/supplementary
        return name

    def write_confluence_data_to_file(self):
        """Write all Confluence pages from specified spaces to text files."""
        if not os.path.exists(File_Dir):
            os.makedirs(File_Dir)
        for space_key in Space_Keys:
            pages = self.get_confluence_pages(space_key)
            if not pages:
                print(f"No pages found in space {space_key}")
                continue
            for page in pages:
                text = self.extract_text(page)
                print(page["title"])
                title = self.safe_filename(page["title"])
                url = page["_links"]["webui"]
                text += f"\n URL:{url}"
                with open(
                    f"{File_Dir}/{title}.txt",
                    "w",
                    encoding="utf-8",
                    errors="replace",
                    newline="\n",
                ) as f:
                    f.write(text)
        print(f"All confluence data written to files in '{File_Dir}' directory.")

    def write_confluence_data_to_blob_storage(self):
        """Upload all Confluence pages from specified spaces to Azure Blob Storage."""
        total_uploaded = 0
        total_skipped = 0
        total_updated = 0
        
        for space_key in Space_Keys:
            if not space_key.strip():
                continue
                
            print(f"\nProcessing space: {space_key}")
            pages = self.get_confluence_pages(space_key)
            
            if not pages:
                print(f"No pages found in space {space_key}")
                continue
                
            for page in pages:
                try:
                    text = self.extract_text(page)
                    title = self.safe_filename(page["title"])
                    url = page["_links"]["webui"]
                    text += f"\n\nURL:{url}"
                    
                    # Create blob name with space key prefix for organization
                    blob_name = f"{space_key}/{title}.txt"
                    blob_client = self.container_client.get_blob_client(blob_name)
                    
                    # Check if blob exists and compare content
                    new_content = text.encode("utf-8")
                    should_upload = True
                    
                    try:
                        # Download existing blob content
                        existing_blob = blob_client.download_blob()
                        existing_content = existing_blob.readall()
                        
                        # Compare content
                        if existing_content == new_content:
                            print(f"⊘ Skipped (no changes): {title}")
                            total_skipped += 1
                            should_upload = False
                        else:
                            print(f"↻ Updated: {title}")
                            total_updated += 1
                    except Exception:
                        # Blob doesn't exist, will upload as new
                        print(f"✓ Uploaded (new): {title}")
                        total_uploaded += 1
                    
                    # Upload to blob storage only if content changed or new
                    if should_upload:
                        blob_client.upload_blob(
                            new_content,
                            overwrite=True,
                            content_settings=ContentSettings(content_type="text/plain", charset="utf-8")
                        )
                    
                except Exception as e:
                    print(f"✗ Error processing {page.get('title', 'unknown')}: {e}")
                    
        print(f"\n✓ Summary:")
        print(f"  - New uploads: {total_uploaded}")
        print(f"  - Updated: {total_updated}")
        print(f"  - Skipped (no changes): {total_skipped}")
        print(f"  - Total processed: {total_uploaded + total_updated + total_skipped}")


if __name__ == "__main__":
    scraper = WebScraper()
    # scraper.write_confluence_data_to_file()
    scraper.write_confluence_data_to_blob_storage()