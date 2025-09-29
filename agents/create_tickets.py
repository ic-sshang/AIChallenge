import requests
import base64
from config import JIRA_DOMAIN, JIRA_EMAIL, JIRA_API_TOKEN

class JIRACreator:
    def __init__(self):
        pass

    # --- Function to create Jira issue ---
    def create_ticket(summary, description, issue_type, email, API_token, project_key):
        if not summary or not description or not issue_type or not project_key:
            return "❌ All fields are required."
        
        if not email or not API_token:
            print("default auth")
            auth = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
        else:
            print("user_auth")
            auth = base64.b64encode(f"{email}:{API_token}".encode()).decode()
        try:
            url = f"https://{JIRA_DOMAIN}/rest/api/3/issue"
            headers = {
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/json"
            }
            try:
                first_index = description.index("User Story")
                second_index = description.index("Acceptance Criteria")
                third_index = description.index("Scenarios")

                user_story = description[first_index:second_index].strip()
                acceptance_criteria = description[second_index:third_index].strip()
                testing = description[third_index:].strip()
                if not user_story or not acceptance_criteria or not testing:
                    return "❌ Please ensure the description includes 'User Story', 'Acceptance Criteria', and 'Scenarios' sections."
            except Exception as e:
                return "❌ Please ensure the description includes 'User Story', 'Acceptance Criteria', and 'Scenarios' sections."
            
            # Format description as Atlassian Document Format (ADF)
            adf_description = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "panel",
                        "attrs": {"panelType": "info"},
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": user_story
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "type": "panel",
                        "attrs": {"panelType": "success"},
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": acceptance_criteria
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "type": "panel",
                        "attrs": {"panelType": "note"},
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": testing
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
            payload = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": summary,
                    "description": adf_description,
                    "issuetype": {"name": issue_type}
                }
            }
        
            response = requests.post(url, headers=headers, json=payload, verify=False)

            if response.status_code == 201:
                issue_key = response.json()["key"]
                return f"✅ Ticket created: {issue_key}"
            else:
                return f"❌ Failed: {response.status_code} - {response.text}"
        except Exception as e:
            return f"❌ Error: {str(e)}"