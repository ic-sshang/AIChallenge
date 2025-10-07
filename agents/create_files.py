import os
import unicodedata
import requests
import re
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup
from config import JIRA_DOMAIN, JIRA_EMAIL, JIRA_API_TOKEN, Space_Keys, File_Dir
from features.chatbot import Knowledge


class WebScraper:
    def __init__(self):
        self.BASE_URL = f"https://{JIRA_DOMAIN}/wiki/rest/api"
        self.auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)

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


if __name__ == "__main__":
    scraper = WebScraper()
    scraper.write_confluence_data_to_file()
