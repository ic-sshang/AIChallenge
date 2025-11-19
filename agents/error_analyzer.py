import requests
import os
import re
import sys
from typing import Dict, List, Optional, Tuple
import base64
from urllib.parse import urlparse
import json
from datetime import datetime, timedelta

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Azure_DevOps_Token, OPENAI_KEY, IC_OpenAI_URL


class ErrorAnalyzer:
    """
    Agent for analyzing errors based on repository codebase and error messages.
    Supports Azure DevOps repositories for code analysis.
    """
    
    def __init__(self):
        self.azure_devops_token = Azure_DevOps_Token  # Personal Access Token for Azure DevOps
        self.supported_extensions = {
          '.js', '.ts', '.cs', '.vb', '.aspx', '.ascx', '.xml', '.config', '.json',
          '.xml', '.csproj', '.vbproj', '.sln', '.sql'
        }
    
    def parse_repo_url(self, repo_url: str) -> Optional[Tuple[str, str]]:
        """
        Parse repository URL to extract organization and project/repo name.
        
        Args:
            repo_url: Azure DevOps repository URL
            
        Returns:
            Tuple of (organization, project/repo) or None if invalid
        """
        try:
            # Handle Azure DevOps URL formats
            # Format: https://dev.azure.com/{organization}/{project}/_git/{repository}
            azure_patterns = [
                r'dev\.azure\.com/([\w\-\.]+)/([\w\-\.]+)/_git/([\w\-\.]+)/?$',
                r'([\w\-\.]+)\.visualstudio\.com/([\w\-\.]+)/_git/([\w\-\.]+)/?$'
            ]
            
            for pattern in azure_patterns:
                # Use original URL (not lowercased) to preserve case sensitivity
                match = re.search(pattern, repo_url, re.IGNORECASE)
                if match:
                    if 'dev.azure.com' in repo_url.lower():
                        org, project, repo = match.groups()
                        return org, f"{project}/{repo}"
                    else:
                        org, project, repo = match.groups()
                        return org, f"{project}/{repo}"
            
            return None
        except Exception as e:
            print(f"Error parsing repo URL: {e}")
            return None
    
    def get_repo_structure(self, owner: str, repo: str, path: str = "") -> Dict:
        """
        Get repository file structure using Azure DevOps API.
        
        Args:
            owner: Repository owner/organization
            repo: Repository name (project/repo format)
            path: Path within repository (optional)
            
        Returns:
            Dictionary containing file structure
        """
        return self._get_azure_repo_structure(owner, repo, path)
    
    def _get_azure_repo_structure(self, organization: str, project_repo: str, path: str = "") -> Dict:
        """Get Azure DevOps repository structure."""
        # Parse project and repo from project_repo
        parts = project_repo.split('/')
        if len(parts) != 2:
            print(f"❌ Invalid Azure repo format: {project_repo}")
            return {}
        
        project, repo = parts
        
        # Azure DevOps REST API URL
        base_url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repo}/items"
        
        params = {
            'api-version': '7.0',
            'scopePath': f'/{path}' if path else '/',
            'recursionLevel': 'OneLevel'
        }
        
        headers = {}
        if self.azure_devops_token:
            # Use Basic authentication with PAT
            import base64
            credentials = base64.b64encode(f':{self.azure_devops_token}'.encode()).decode()
            headers['Authorization'] = f'Basic {credentials}'
        
        try:
            print(f"🔍 Fetching repo structure: {organization}/{project}/{repo}")
            if path:
                print(f"📁 Path: {path}")
            
            response = requests.get(base_url, headers=headers, params=params)
            
            # Add detailed error information
            if response.status_code == 404:
                print(f"❌ Repository not found (404)")
                print(f"   Organization: {organization}")
                print(f"   Project: {project}")
                print(f"   Repository: {repo}")
                print(f"   Full URL: {response.url}")
                return {}
            elif response.status_code == 403:
                print(f"❌ Access denied (403): Check permissions for repository")
                return {}
            elif response.status_code == 401:
                print(f"❌ Unauthorized (401): Check Azure DevOps token")
                return {}
            
            response.raise_for_status()
            
            # Convert Azure DevOps format to GitHub-like format for compatibility
            azure_data = response.json()
            converted_data = []
            
            for item in azure_data.get('value', []):
                if item.get('gitObjectType') == 'tree':
                    converted_data.append({
                        'name': item['path'].split('/')[-1],
                        'path': item['path'].lstrip('/'),
                        'type': 'dir'
                    })
                elif item.get('gitObjectType') == 'blob':
                    converted_data.append({
                        'name': item['path'].split('/')[-1],
                        'path': item['path'].lstrip('/'),
                        'type': 'file',
                        'size': item.get('size', 0),
                        'download_url': item.get('url', '')
                    })
            
            print(f"✅ Found {len(converted_data)} items in repository structure")
            return converted_data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching Azure DevOps repo structure: {e}")
            print(f"   Repository: {organization}/{project}/{repo}")
            return {}
    
    def get_file_content(self, owner: str, repo: str, file_path: str) -> Optional[str]:
        """
        Get content of a specific file from Azure DevOps repository.
        
        Args:
            owner: Repository owner/organization
            repo: Repository name (project/repo format)
            file_path: Path to the file
            
        Returns:
            File content as string or None if error
        """
        return self._get_azure_file_content(owner, repo, file_path)
    
    def _get_azure_file_content(self, organization: str, project_repo: str, file_path: str) -> Optional[str]:
        """Get file content from Azure DevOps."""
        # Parse project and repo
        parts = project_repo.split('/')
        if len(parts) != 2:
            print(f"Invalid project_repo format: {project_repo}")
            return None
        
        project, repo = parts
        
        # Azure DevOps REST API URL for file content
        url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repo}/items"
        
        params = {
            'api-version': '7.0',
            'path': f'/{file_path}',
            'includeContent': 'true'
        }
        
        headers = {}
        if self.azure_devops_token:
            import base64
            credentials = base64.b64encode(f':{self.azure_devops_token}'.encode()).decode()
            headers['Authorization'] = f'Basic {credentials}'
        
        try:
            # print(f"🔍 Fetching file content: {organization}/{project}/{repo} -> {file_path}")
            # print(f"📡 Request URL: {url}")
            # print(f"📋 Parameters: {params}")
            
            response = requests.get(url, headers=headers, params=params)
            
            # Add detailed error information
            if response.status_code == 404:
                print(f"❌ File not found (404): {file_path}")
                print(f"   Organization: {organization}")
                print(f"   Project: {project}")
                print(f"   Repository: {repo}")
                print(f"   Full URL: {response.url}")
                return None
            elif response.status_code == 403:
                print(f"❌ Access denied (403): Check permissions for {file_path}")
                return None
            elif response.status_code == 401:
                print(f"❌ Unauthorized (401): Check Azure DevOps token")
                return None
            
            response.raise_for_status()
            
            # Check content type to determine how to parse response
            content_type = response.headers.get('content-type', '').lower()
            
            if 'application/json' in content_type:
                # JSON response with structured data
                file_data = response.json()
                content = file_data.get('content', '')
                
                # Handle different encoding types
                if file_data.get('contentMetadata', {}).get('encoding') == 'base64':
                    content = base64.b64decode(content).decode('utf-8', errors='ignore')
            else:
                # Raw text content (what we're actually getting)
                content = response.text
                # Remove BOM if present
                if content.startswith('\ufeff'):
                    content = content[1:]
                elif content.startswith('ï»¿'):
                    content = content[3:]  # Remove UTF-8 BOM bytes
            
            # print(f"✅ Successfully fetched file content: {file_path} ({len(content)} characters)")
            return content
            
        except Exception as e:
            print(f"❌ Error fetching Azure DevOps file content: {e}")
            print(f"   File path: {file_path}")
            print(f"   Repository: {organization}/{project}/{repo}")
            return None
    
    def get_recent_commits(self, organization: str, project_repo: str, days: int = 14) -> List[Dict]:
        """
        Get commits from the past N days using Azure DevOps API.
        
        Args:
            organization: Azure DevOps organization
            project_repo: Project and repository name (project/repo format)
            days: Number of days to look back (default 14)
            
        Returns:
            List of commits with metadata
        """
        # Parse project and repo
        parts = project_repo.split('/')
        if len(parts) != 2:
            return []
        
        project, repo = parts
        
        # Calculate date threshold
        since_date = (datetime.now() - timedelta(days=days)).isoformat() + 'Z'
        
        # Azure DevOps REST API URL for commits
        url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repo}/commits"
        
        params = {
            'api-version': '7.0',
            'searchCriteria.fromDate': since_date,
            '$top': 100  # Limit to recent 100 commits
        }
        
        headers = {}
        if self.azure_devops_token:
            import base64
            credentials = base64.b64encode(f':{self.azure_devops_token}'.encode()).decode()
            headers['Authorization'] = f'Basic {credentials}'
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            commits_data = response.json()
            return commits_data.get('value', [])
            
        except Exception as e:
            print(f"Error fetching recent commits: {e}")
            return []
    
    def get_commit_changes(self, organization: str, project_repo: str, commit_id: str) -> List[Dict]:
        """
        Get the files changed in a specific commit.
        
        Args:
            organization: Azure DevOps organization
            project_repo: Project and repository name (project/repo format)
            commit_id: Commit ID/SHA
            
        Returns:
            List of changed files
        """
        # Parse project and repo
        parts = project_repo.split('/')
        if len(parts) != 2:
            return []
        
        project, repo = parts
        
        # Azure DevOps REST API URL for commit changes
        url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repo}/commits/{commit_id}/changes"
        
        params = {
            'api-version': '7.0'
        }
        
        headers = {}
        if self.azure_devops_token:
            import base64
            credentials = base64.b64encode(f':{self.azure_devops_token}'.encode()).decode()
            headers['Authorization'] = f'Basic {credentials}'
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            changes_data = response.json()
            return changes_data.get('changes', [])
            
        except Exception as e:
            print(f"Error fetching commit changes for {commit_id}: {e}")
            return []
    
    def get_recently_changed_files(self, owner: str, repo: str, days: int = 14) -> List[Dict]:
        """
        Get files that have been changed in the past N days.
        
        Args:
            owner: Repository owner/organization
            repo: Repository name (project/repo format)
            days: Number of days to look back (default 14)
            
        Returns:
            List of recently changed files with metadata
        """
        print(f"Fetching commits from the past {days} days...")
        recent_commits = self.get_recent_commits(owner, repo, days)
        
        if not recent_commits:
            print("No recent commits found")
            return []
        
        print(f"Found {len(recent_commits)} recent commits")
        
        # Collect all changed files from recent commits
        changed_files = {}  # Use dict to avoid duplicates
        
        for commit in recent_commits:
            commit_id = commit.get('commitId', '')
            commit_message = commit.get('comment', '')
            commit_date = commit.get('author', {}).get('date', '')
            
            # print(f"Processing commit: {commit_id[:8]} - {commit_message[:50]}...")
            
            changes = self.get_commit_changes(owner, repo, commit_id)
            
            for change in changes:
                item = change.get('item', {})
                if item.get('gitObjectType') == 'blob':  # Only files, not directories
                    file_path = item.get('path', '').lstrip('/')
                    file_name = file_path.split('/')[-1] if file_path else ''
                    
                    # Check if file extension is supported
                    if any(file_name.endswith(ext) for ext in self.supported_extensions):
                        if file_path not in changed_files:
                            changed_files[file_path] = {
                                'path': file_path,
                                'name': file_name,
                                'size': item.get('size', 0),
                                'last_commit_id': commit_id,
                                'last_commit_message': commit_message,
                                'last_commit_date': commit_date,
                                'change_type': change.get('changeType', 'unknown')
                            }
        
        print(f"Found {len(changed_files)} unique files changed in the past {days} days")
        return list(changed_files.values())
    
    def extract_relevant_files(self, owner: str, repo: str, error_message: str, max_files: int = 40, days: int = 14) -> List[Dict]:
        """
        Extract files that might be relevant to the error message using AI-powered analysis.
        Now focuses on files changed in the past N days.
        
        Args:
            owner: Repository owner/organization
            repo: Repository name (project/repo format)
            error_message: Error message to analyze
            max_files: Maximum number of files to analyze
            days: Number of days to look back for recent changes (default 14)
            
        Returns:
            List of relevant files with their content
        """
        print(f"🔍 Analyzing files changed in the past {days} days...")
        
        # Get recently changed files instead of all files
        recently_changed_files = self.get_recently_changed_files(owner, repo, days)
        
        if not recently_changed_files:
            print("⚠️ No recently changed files found. Falling back to error-specific file search...")
            # Fallback: look for files mentioned in the error message
            return self._extract_error_specific_files(owner, repo, error_message, max_files)
        
        print(f"📋 Found {len(recently_changed_files)} recently changed files")
        
        # Use AI to determine which recently changed files are most relevant to the error
        relevant_file_paths = self.ai_select_relevant_files(recently_changed_files, error_message, max_files)
        
        # Get content for the selected files
        relevant_files = []
        for file_path in relevant_file_paths:
            content = self.get_file_content(owner, repo, file_path)
            if content:
                # Limit individual file content to prevent token overflow
                MAX_FILE_CONTENT = 10000  # characters
                if len(content) > MAX_FILE_CONTENT:
                    content = content[:MAX_FILE_CONTENT] + f"\n... (file truncated, original size: {len(content)} characters)"
                
                file_info = next((f for f in recently_changed_files if f['path'] == file_path), {})
                relevant_files.append({
                    'path': file_path,
                    'name': file_info.get('name', file_path.split('/')[-1]),
                    'content': content,  # Limit content size
                    'size': file_info.get('size', 0),
                    'last_commit_id': file_info.get('last_commit_id', ''),
                    'last_commit_message': file_info.get('last_commit_message', ''),
                    'last_commit_date': file_info.get('last_commit_date', ''),
                    'change_type': file_info.get('change_type', 'unknown')
                })
        
        return relevant_files
    
    def _extract_error_specific_files(self, owner: str, repo: str, error_message: str, max_files: int = 40) -> List[Dict]:
        """
        Fallback method to extract files specifically mentioned in the error message.
        
        Args:
            owner: Repository owner/organization
            repo: Repository name (project/repo format)
            error_message: Error message to analyze
            max_files: Maximum number of files to analyze
            
        Returns:
            List of relevant files with their content
        """
        print("🔎 Searching for files specifically mentioned in the error message...")
        
        # Extract file names and paths from error message
        file_patterns = [
            r'\\([^\\]+\.(?:cs|vb|aspx|ascx|config|json|xml))',  # Windows paths
            r'/([^/]+\.(?:cs|vb|aspx|ascx|config|json|xml))',   # Unix paths
            r'([A-Za-z][A-Za-z0-9_]*\.(?:cs|vb|aspx|ascx|config|json|xml))',  # File names
        ]
        
        mentioned_files = set()
        for pattern in file_patterns:
            matches = re.findall(pattern, error_message, re.IGNORECASE)
            mentioned_files.update(matches)
        
        print(f"📄 Found {len(mentioned_files)} files mentioned in error: {list(mentioned_files)}")
        
        # Search for these files in the repository
        found_files = []
        
        def search_for_files(path: str = "", depth: int = 0):
            MAXDEPTH = 4
            if depth > MAXDEPTH or len(found_files) >= max_files:
                return
            
            contents = self.get_repo_structure(owner, repo, path)
            if not contents:
                return
            
            # Handle both list and dict responses
            if isinstance(contents, dict):
                contents = [contents]
            
            for item in contents:
                if len(found_files) >= max_files:
                    break
                    
                if item.get('type') == 'file':
                    file_path = item['path']
                    file_name = item['name']
                    
                    # Check if this file is mentioned in the error
                    if any(mentioned_file.lower() in file_name.lower() for mentioned_file in mentioned_files):
                        content = self.get_file_content(owner, repo, file_path)
                        if content:
                            found_files.append({
                                'path': file_path,
                                'name': file_name,
                                'content': content[:5000],  # Limit content size
                                'size': item.get('size', 0),
                                'matched_pattern': next((f for f in mentioned_files if f.lower() in file_name.lower()), '')
                            })
                            
                elif item.get('type') == 'dir' and depth < MAXDEPTH:
                    # Recursively search subdirectories
                    search_for_files(item['path'], depth + 1)
        
        search_for_files()
        
        print(f"✅ Found {len(found_files)} relevant files mentioned in the error")
        return found_files
    
    def ai_select_relevant_files(self, all_files: List[Dict], error_message: str, max_files: int = 40) -> List[str]:
        """
        Use AI to select the most relevant files based on the error message.
        
        Args:
            all_files: List of all files in the repository
            error_message: Error message to analyze
            max_files: Maximum number of files to select
            
        Returns:
            List of file paths that are most relevant to the error
        """
        if not all_files:
            return []
        
        # Limit files for token efficiency - but don't pre-filter based on patterns
        # Let AI decide relevance based on the actual error message
        selected_files = all_files[:50]  # Just limit total number for token efficiency
        file_list = "\n".join([f"- {f['path']}" for f in selected_files])
        
        ai_prompt = f"""You are a code analysis expert. Analyze this specific error message and select the {max_files} most relevant files from the repository.

ERROR MESSAGE TO ANALYZE:
{error_message}

AVAILABLE FILES IN REPOSITORY:
{file_list}

ANALYSIS INSTRUCTIONS:
1. Look for files whose names contain keywords from the error message
2. If the error mentions specific classes, methods, or namespaces, find files likely to contain them
3. Consider the error type (e.g., NullReferenceException, SqlException) and find related files
4. Look for configuration files if the error seems configuration-related
5. Include entry points (Program.cs, Startup.cs) only if the error occurs during startup

IMPORTANT: Base your selection ONLY on the specific error message provided, not on generic .NET patterns.

Return ONLY a JSON array of the most relevant file paths:
["path/to/relevant/file1.cs", "path/to/relevant/file2.cs"]"""
        
        try:
            if OPENAI_KEY and IC_OpenAI_URL:
                headers = {
                    'api-key': OPENAI_KEY,
                    'Content-Type': 'application/json'
                }
                
                payload = json.dumps({
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a code analysis expert that helps identify relevant files for error analysis. Return only a JSON array of file paths without any additional text."
                        },
                        {
                            "role": "user",
                            "content": ai_prompt
                        }
                    ],
                    "temperature": 0.1
                })
                
                response = requests.post(
                    IC_OpenAI_URL,
                    headers=headers,
                    data=payload
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    ai_response = response_data['choices'][0]['message']['content'].strip()
                    
                    # Try to extract JSON array from response
                    try:
                        # Clean up the response - sometimes AI adds extra text
                        if '[' in ai_response and ']' in ai_response:
                            start = ai_response.find('[')
                            end = ai_response.rfind(']') + 1
                            json_str = ai_response[start:end]
                            selected_paths = json.loads(json_str)
                            
                            # Validate that the paths exist in our file list
                            available_paths = [f['path'] for f in all_files]
                            valid_paths = [path for path in selected_paths if path in available_paths]
                            
                            if valid_paths:
                                return valid_paths[:max_files]
                        
                    except (json.JSONDecodeError, KeyError):
                        print("Failed to parse AI response as JSON, using fallback")
                else:
                    print(f"Azure OpenAI API error (select relevant files): {response.status_code} {response.text}")
            
            # Fallback to smart selection
            return self._smart_file_selection_fallback(all_files, error_message, max_files)
            
        except Exception as e:
            print(f"AI file selection failed, using fallback: {e}")
            return self._smart_file_selection_fallback(all_files, error_message, max_files)
    
    def _smart_file_selection_fallback(self, all_files: List[Dict], error_message: str, max_files: int) -> List[str]:
        """
        Fallback method for smart file selection when AI is not available.
        Focuses on error message content rather than generic patterns.
        """
        scored_files = []
        error_lower = error_message.lower()
        
        # Extract meaningful keywords from error message (filter out common words)
        error_keywords = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', error_lower)
        # Filter out very short words and common words
        common_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'among', 'against', 'within', 'without', 'throughout', 'error', 'exception', 'null', 'reference'}
        error_keywords = [k for k in error_keywords if len(k) > 3 and k not in common_words]
        
        for file_info in all_files:
            file_path = file_info['path'].lower()
            file_name = file_info['name'].lower()
            score = 0
            
            # High score for direct keyword matches in filename
            for keyword in error_keywords:
                if keyword in file_name:
                    score += 20  # High priority for filename matches
                elif keyword in file_path:
                    score += 10  # Medium priority for path matches
            
            # Look for class/namespace patterns in error message
            # Extract potential class names (PascalCase words)
            class_patterns = re.findall(r'\b[A-Z][a-zA-Z0-9]*\b', error_message)
            for class_name in class_patterns:
                if len(class_name) > 3:
                    class_lower = class_name.lower()
                    if class_lower in file_name:
                        score += 15
                    elif class_lower in file_path:
                        score += 8
            
            # Check for specific error types and related files
            if 'sqlexception' in error_lower or 'database' in error_lower:
                if any(pattern in file_path for pattern in ['data', 'repository', 'dbcontext', 'sql']):
                    score += 12
            
            if 'configuration' in error_lower or 'config' in error_lower:
                if file_name.endswith(('.config', '.json', '.xml')):
                    score += 15
            
            if 'startup' in error_lower or 'program' in error_lower:
                if any(pattern in file_name for pattern in ['startup', 'program', 'main']):
                    score += 15
            
            # Slight preference for code files over other types, but only if there's already some relevance
            if score > 0 and file_name.endswith(('.cs', '.vb')):
                score += 2
            
            if score > 0:
                scored_files.append((file_info['path'], score))
        
        # Sort by score and return top files
        scored_files.sort(key=lambda x: x[1], reverse=True)
        return [file_path for file_path, _ in scored_files[:max_files]]
    
    def analyze_error(self, error_message: str, repo_url: str, progress_callback=None, days: int = 14) -> Dict:
        """
        Perform root cause analysis of an error based on Azure DevOps repository code.
        Now focuses on files changed in the past N days.
        
        Args:
            error_message: The error message to analyze
            repo_url: Azure DevOps repository URL
            progress_callback: Optional callback for progress updates
            days: Number of days to look back for recent changes (default 14)
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            if progress_callback:
                progress_callback("🔍 Parsing repository URL...")
            
            # Parse repository URL
            repo_info = self.parse_repo_url(repo_url)
            if not repo_info:
                return {
                    'success': False,
                    'error': 'Invalid repository URL. Please provide a valid Azure DevOps repository URL.'
                }
            
            owner, repo = repo_info
            
            if progress_callback:
                progress_callback(f"📂 Analyzing Azure DevOps repository: {owner}/{repo}")
            
            # Extract relevant files (now focusing on recent changes)
            if progress_callback:
                progress_callback(f"🔎 Extracting files changed in the past {days} days...")
            
            relevant_files = self.extract_relevant_files(owner, repo, error_message, days=days)
            
            if not relevant_files:
                return {
                    'success': False,
                    'error': f'No relevant files found in the repository from the past {days} days or repository is inaccessible. Please check permissions and repository URL.'
                }
            
            if progress_callback:
                progress_callback(f"📋 Found {len(relevant_files)} relevant files from recent changes")
            
            # Prepare context for analysis
            context = self.prepare_analysis_context(error_message, relevant_files)
            
            if progress_callback:
                progress_callback("🤖 Performing AI-powered root cause analysis...")
            
            # Debug: Print context size
            context_chars = len(context)
            estimated_tokens = context_chars // 4
            print(f"📊 Context prepared: {context_chars:,} characters (~{estimated_tokens:,} tokens)")
            
            if estimated_tokens > 100000:
                print("⚠️ Warning: Context may be approaching token limits")
            
            # Perform analysis using AI
            analysis_result = self.perform_ai_analysis(context)
            
            return {
                'success': True,
                'analysis': analysis_result,
                'files_analyzed': [f['path'] for f in relevant_files],
                'repo_info': f"{owner}/{repo}",
                'platform': 'azure',
                'analysis_scope': f'Files changed in the past {days} days',
                'commit_info': [
                    {
                        'path': f['path'],
                        'last_commit_id': f.get('last_commit_id', ''),
                        'last_commit_message': f.get('last_commit_message', ''),
                        'change_type': f.get('change_type', 'unknown')
                    } for f in relevant_files if f.get('last_commit_id')
                ]
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Analysis failed: {str(e)}'
            }
    
    def prepare_analysis_context(self, error_message: str, relevant_files: List[Dict]) -> str:
        """
        Prepare context for AI analysis.
        
        Args:
            error_message: The error message
            relevant_files: List of relevant files with content
            
        Returns:
            Formatted context string
        """
        # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
        MAX_TOKENS = 100000  # Leave room for response and system prompt
        MAX_CHARS = MAX_TOKENS * 4
        
        context = f"""ERROR MESSAGE:
{error_message}

RELEVANT CODE FILES:
"""
        
        current_length = len(context)
        files_included = 0
        
        for file_info in relevant_files:
            file_content = file_info['content']
            file_path = file_info['path']
            
            # Truncate individual file content if too large
            max_file_chars = min(8000, (MAX_CHARS - current_length) // max(1, len(relevant_files) - files_included))
            
            if len(file_content) > max_file_chars:
                # Extract key parts: beginning, any error-related sections, and end
                truncated_content = self._smart_truncate_content(file_content, max_file_chars, error_message)
                file_section = f"""
                    --- FILE: {file_path} (TRUNCATED - {len(file_content)} chars total) ---
                    {truncated_content}
                    [... content truncated for token limit ...]

                    """
            else:
                file_section = f"""
                    --- FILE: {file_path} ---
                    {file_content}

                    """
            
            # Check if adding this file would exceed limits
            if current_length + len(file_section) > MAX_CHARS:
                context += f"""
                    --- ADDITIONAL FILES OMITTED DUE TO TOKEN LIMIT ---
                    {len(relevant_files) - files_included} more files were analyzed but omitted from context to stay within token limits.
                    Files omitted: {[f['path'] for f in relevant_files[files_included:]]}

                    """
                break
            
            context += file_section
            current_length += len(file_section)
            files_included += 1
        
        return context
    
    def _smart_truncate_content(self, content: str, max_chars: int, error_message: str) -> str:
        """
        Intelligently truncate file content while preserving relevant parts.
        
        Args:
            content: Full file content
            max_chars: Maximum characters to keep
            error_message: Error message to find relevant sections
            
        Returns:
            Truncated content with most relevant parts preserved
        """
        if len(content) <= max_chars:
            return content
        
        lines = content.split('\n')
        
        # Extract keywords from error message for relevance scoring
        error_keywords = re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', error_message.lower())
        error_keywords = [k for k in error_keywords if len(k) > 3]
        
        # Score lines based on relevance
        scored_lines = []
        for i, line in enumerate(lines):
            score = 0
            line_lower = line.lower()
            
            # Higher score for lines containing error keywords
            for keyword in error_keywords:
                if keyword in line_lower:
                    score += 10
            
            # Score for important code patterns
            if any(pattern in line_lower for pattern in ['public', 'private', 'class', 'method', 'function', 'sub ', 'dim ', 'if ', 'try', 'catch', 'throw']):
                score += 3
            
            # Score for configuration and important declarations
            if any(pattern in line_lower for pattern in ['config', 'connection', 'setting', 'import', 'using', 'namespace']):
                score += 2
            
            scored_lines.append((i, line, score))
        
        # Always include the beginning (class/namespace declarations)
        beginning_lines = lines[:min(20, len(lines))]
        
        # Sort by relevance and take top scoring lines
        scored_lines.sort(key=lambda x: x[2], reverse=True)
        
        # Take top relevant lines while maintaining some order
        relevant_lines = []
        used_chars = len('\n'.join(beginning_lines))
        
        # Add beginning
        for line in beginning_lines:
            relevant_lines.append(line)
        
        # Add most relevant lines if we have space
        remaining_chars = max_chars - used_chars
        for line_num, line, score in scored_lines:
            if score > 0 and line_num >= 20:  # Skip lines already included in beginning
                if len(line) + 1 <= remaining_chars:  # +1 for newline
                    relevant_lines.append(f"... (line {line_num + 1}) ...")
                    relevant_lines.append(line)
                    remaining_chars -= len(line) + 1
                    if remaining_chars < 100:  # Leave some room
                        break
        
        return '\n'.join(relevant_lines)
    
    def perform_ai_analysis(self, context: str) -> str:
        """
        Perform AI-powered analysis of the error and code context using Azure OpenAI.
        Enhanced for .NET technologies.
        
        Args:
            context: Prepared context with error and code
            
        Returns:
            Analysis result from AI
        """
        try:
            if OPENAI_KEY and IC_OpenAI_URL:
                # Create a specialized prompt for error analysis
                analysis_prompt = f"""You are an expert .NET developer and error analysis specialist. Analyze the following error message and related code files to provide a comprehensive root cause analysis.

{context}

Please provide a detailed analysis following this structure:

# Root Cause Analysis

## Error Summary
Provide a clear, concise summary of what the error means and where it occurs.

## Root Cause Identification
1. **Primary Cause**: Identify the most likely root cause based on the error message and code
2. **Contributing Factors**: List any secondary issues that may have contributed
3. **Code Location**: Pinpoint the exact location and line where the problem occurs

## Code Analysis
- Analyze the specific code patterns that led to this error
- Identify any anti-patterns or problematic implementations
- Review variable initialization, null checks, and object lifecycle

## Immediate Fixes
Provide specific, actionable code changes to fix this error:
```csharp
// Example fix with actual code snippets
```

## Prevention Strategies
- Suggest coding practices to prevent similar errors
- Recommend additional validation or error handling
- Identify areas for refactoring or improvement

## Testing Recommendations
- Suggest specific test cases to verify the fix
- Recommend integration tests or scenarios to prevent regression

## Additional Considerations
- Performance implications of the fix
- Security considerations if applicable
- Compatibility with existing code

Focus on practical, implementable solutions specific to this error and codebase."""

                headers = {
                    'api-key': OPENAI_KEY,
                    'Content-Type': 'application/json'
                }
                
                payload = json.dumps({
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert .NET developer and error analysis specialist. Provide detailed, actionable root cause analysis for software errors. Focus on practical solutions and specific code fixes."
                        },
                        {
                            "role": "user",
                            "content": analysis_prompt
                        }
                    ],
                    "temperature": 0.2
                })
                
                response = requests.post(
                    IC_OpenAI_URL,
                    headers=headers,
                    data=payload
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    ai_analysis = response_data['choices'][0]['message']['content'].strip()
                    
                    # Add metadata about the analysis
                    analysis_with_metadata = f"""{ai_analysis}

---
**Analysis Metadata:**
- Analysis performed using AI-powered root cause detection
- Based on recent code changes and error context
- Recommendations are specific to .NET/C#/VB.NET applications
- Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
                    return analysis_with_metadata
                else:
                    print(f"Azure OpenAI API error: {response.status_code} {response.text}")
                    return self._fallback_analysis_template(context)
            else:
                print("OpenAI credentials not available, using fallback analysis")
                return self._fallback_analysis_template(context)
                
        except Exception as e:
            print(f"Error during AI analysis: {e}")
            return self._fallback_analysis_template(context)
    
    def _fallback_analysis_template(self, context: str) -> str:
        """
        Fallback analysis template when AI is not available.
        
        Args:
            context: Error and code context
            
        Returns:
            Template-based analysis
        """
        # Extract error type and file info from context for basic analysis
        error_lines = context.split('\n')[:10]  # First 10 lines usually contain the error
        error_text = '\n'.join(error_lines)
        
        analysis = f"""
# Root Cause Analysis (.NET Focus)

## Error Summary
Based on the provided error message and Azure DevOps repository code analysis:

**Error Context:**
{error_text}

## Potential Root Causes
1. **Primary Cause**: [Analysis based on error patterns]
   - Check for null reference exceptions in the code
   - Verify object initialization before usage
   - Review method parameters and return values
   
2. **Secondary Causes**: [Other possible contributing factors]
   - Missing NuGet packages or assembly references
   - Configuration file issues (web.config, appsettings.json)
   - Database connection or Entity Framework issues
   - Dependency injection container misconfigurations

## Code Analysis (.NET Specific)
- **Files Examined**: Recently changed C#/VB.NET files and configuration files
- **Framework Patterns**: ASP.NET, Entity Framework, dependency injection patterns
- **Common Issues**: 
  - Null reference exceptions
  - Configuration binding issues
  - Object lifecycle problems
  - Missing error handling

## Recommended Solutions

### 1. Immediate Fixes
```csharp
// Example: Add null checks
if (someObject != null)
{{
    // Your code here
}}

// Example: Initialize objects properly
var myObject = new MyClass();

// Example: Use safe navigation
var result = myObject?.SomeProperty?.SomeMethod();
```

### 2. Long-term Improvements
- Implement proper error handling middleware
- Add comprehensive logging (Serilog, NLog, or built-in ILogger)
- Use dependency injection best practices
- Implement proper configuration validation
- Add unit tests with proper mocking

## .NET Best Practices
- **Null Safety**: Use nullable reference types (C# 8.0+)
- **Configuration**: Use IOptions pattern for strongly-typed configuration
- **Logging**: Implement structured logging
- **Exception Handling**: Use global exception handling middleware
- **Testing**: Add unit tests with proper mocking

## Configuration Checks
```json
// appsettings.json example
{{
  "ConnectionStrings": {{
    "DefaultConnection": "Server=...;Database=...;Trusted_Connection=true;"
  }},
  "Logging": {{
    "LogLevel": {{
      "Default": "Information"
    }}
  }}
}}
```

## Additional Recommendations
- Review NuGet package versions for compatibility
- Check .NET Framework/Core version compatibility
- Validate database migration status
- Ensure proper error handling in controllers/services
- Consider implementing health checks

---
**Note:** This analysis was generated using fallback templates. For more detailed AI-powered analysis, ensure OpenAI credentials are properly configured.
"""
        
        return analysis
