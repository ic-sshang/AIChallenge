import requests
import os
import json
from typing import Dict, List, Optional
from agents.error_analyzer import ErrorAnalyzer
from config import OPENAI_KEY, IC_OpenAI_URL


class ErrorAnalysisFeature:
    """
    Feature class for error analysis functionality.
    Integrates with ErrorAnalyzer agent and Azure OpenAI services.
    """
    
    def __init__(self):
        self.analyzer = ErrorAnalyzer()
        self.setup_ai_client()
    
    def setup_ai_client(self):
        """Setup Azure OpenAI client for analysis."""
        try:
            # Check if Azure OpenAI credentials are available
            if OPENAI_KEY and IC_OpenAI_URL:
                self.ai_available = True
                print("✅ Azure OpenAI client configured successfully")
            else:
                self.ai_available = False
                print("⚠️ Azure OpenAI credentials not configured")
        except Exception as e:
            print(f"❌ AI client setup failed: {e}")
            self.ai_available = False
    
    def validate_inputs(self, error_message: str, repo_url: str) -> Optional[str]:
        """
        Validate user inputs.
        
        Args:
            error_message: Error message to analyze
            repo_url: Repository URL
            
        Returns:
            Error message if validation fails, None if valid
        """
        if not error_message.strip():
            return "Please provide an error message to analyze."
        
        if not repo_url.strip():
            return "Please provide a repository URL."
        
        if not ('dev.azure.com' in repo_url.lower() or 'visualstudio.com' in repo_url.lower()):
            return "Currently only Azure DevOps repositories are supported."
        
        return None
    
    def analyze_error_with_ai(self, error_message: str, repo_url: str, progress_callback=None, days: int = 14):
        """
        Main function to analyze error with AI assistance.
        Now focuses on files changed in the past N days.
        
        Args:
            error_message: The error message to analyze
            repo_url: Azure DevOps repository URL
            progress_callback: Callback for progress updates
            days: Number of days to look back for recent changes (default 14)
            
        Yields:
            Progress updates and final analysis
        """
        try:
            # Validate inputs
            validation_error = self.validate_inputs(error_message, repo_url)
            if validation_error:
                yield f"❌ Validation Error: {validation_error}"
                return
            
            yield "🚀 Starting error analysis with recent changes focus...\n\n"
            yield f"🔍 Analyzing files changed in the past {days} days\n\n"
            
            # Step 1: Repository Analysis with Recent Changes Focus
            yield "📂 Analyzing repository structure and extracting relevant files from recent commits...\n\n"
            
            def update_progress(message):
                yield f"   {message}\n\n"
            
            # Use the ErrorAnalyzer to get repository context (now with days parameter)
            result = self.analyzer.analyze_error(error_message, repo_url, progress_callback=update_progress, days=days)
            
            if not result['success']:
                yield f"❌ Repository Analysis Failed: {result['error']}\n\n"
                return
            
            yield f"✅ Repository Analysis Complete!\n\n"
            yield f"   📋 Analyzed repository: {result['repo_info']}\n\n"
            yield f"   📅 Analysis scope: {result.get('analysis_scope', 'Recent changes')}\n\n"
            yield f"   📁 Files examined: {len(result['files_analyzed'])}\n\n"
            
            # Show commit information for analyzed files
            commit_info = result.get('commit_info', [])
            if commit_info:
                yield "   📝 Recent commit information:\n\n"
                for info in commit_info[:3]:  # Show first 3 commits
                    yield f"      • {info['path']} (Commit: {info['last_commit_id'][:8]})\n\n"
                    yield f"        └─ {info['last_commit_message'][:60]}...\n\n"
                if len(commit_info) > 3:
                    yield f"      ... and {len(commit_info) - 3} more recent changes\n\n"
            
            # List analyzed files
            yield "   📄 Relevant files found:\n\n"
            for file_path in result['files_analyzed'][:5]:  # Show first 5 files
                yield f"      • {file_path}\n\n"
            if len(result['files_analyzed']) > 5:
                yield f"      ... and {len(result['files_analyzed']) - 5} more files\n\n"
            
            # Step 2: AI Analysis
            yield "\n\n🤖 Performing AI-powered root cause analysis...\n\n"
            
            # The error analyzer now handles AI analysis internally
            yield f"✅ AI Analysis Complete!\n\n"
            yield f"📊 **Root Cause Analysis Results:**\n\n"
            yield result['analysis']
            
            # Add summary of analysis scope
            yield f"\n\n---\n\n"
            yield f"**Analysis Summary:**\n\n"
            yield f"- Repository: {result['repo_info']}\n\n"
            yield f"- Scope: {result.get('analysis_scope', 'Recent changes')}\n\n"
            yield f"- Files analyzed: {len(result['files_analyzed'])}\n\n"
            yield f"- AI-powered: {'✅' if self.ai_available else '❌'}\n\n"
            
        except Exception as e:
            yield f"❌ Analysis failed with error: {str(e)}\n\n"
    
    def get_sample_repos(self) -> List[Dict[str, str]]:
        """
        Get list of sample Azure DevOps repositories for testing.
        
        Returns:
            List of sample repository information
        """
        return [
            {
                "name": "Invoice Cloud Biller API",
                "url": "https://dev.azure.com/invoicecloud/Biller/_git/BillerSearchAPI",
                "description": "Azure DevOps C# API repository for billing services"
            },
            {
                "name": "Invoice Cloud Src Project",
                "url": "https://dev.azure.com/invoicecloud/Src/_git/MyIIS",
                "description": "Azure DevOps .NET project with IIS configuration"
            },
            {
                "name": "Sample .NET Web App",
                "url": "https://dev.azure.com/invoicecloud/ProjectName/_git/WebApplication",
                "description": "Sample ASP.NET web application repository"
            }
        ]
    
    def get_sample_errors(self) -> List[str]:
        """
        Get list of sample error messages for testing.
        Focused on .NET and common enterprise application errors.
        
        Returns:
            List of sample error messages
        """
        return [
            # .NET specific errors with stack traces
            """System.NullReferenceException: Object reference not set to an instance of an object.
   at BillerPortal.Services.UserService.GetUserById(Int32 userId) in C:\\src\\Services\\UserService.cs:line 45
   at BillerPortal.Controllers.UserController.GetUser(Int32 id) in C:\\src\\Controllers\\UserController.cs:line 23""",
            
            """System.ArgumentNullException: Value cannot be null. Parameter name: connectionString
   at System.Data.SqlClient.SqlConnection..ctor(String connectionString)
   at BillerPortal.Data.DatabaseContext.CreateConnection() in C:\\src\\Data\\DatabaseContext.cs:line 12""",
            
            """System.InvalidOperationException: Unable to resolve service for type 'BillerPortal.Services.IEmailService' while attempting to activate 'BillerPortal.Controllers.NotificationController'.
   at Microsoft.Extensions.DependencyInjection.ActivatorUtilities.GetService()""",
            
            """Microsoft.EntityFrameworkCore.DbUpdateException: An error occurred while updating the entries. See the inner exception for details.
   at Microsoft.EntityFrameworkCore.Update.ReaderModificationCommandBatch.Execute()
   at BillerPortal.Data.Repository.SaveChanges() in C:\\src\\Data\\Repository.cs:line 78""",
            
            """System.Configuration.ConfigurationErrorsException: Configuration system failed to initialize
   at System.Configuration.ConfigurationManager.GetSection(String sectionName)
   at BillerPortal.Configuration.AppSettings.Load() in C:\\src\\Configuration\\AppSettings.cs:line 15""",
            
            """System.Data.SqlClient.SqlException: A network-related or instance-specific error occurred while establishing a connection to SQL Server.
   at System.Data.SqlClient.SqlInternalConnection.OnError()
   at BillerPortal.Data.SqlRepository.ExecuteQuery() in C:\\src\\Data\\SqlRepository.cs:line 33""",
            
            """System.Web.HttpException: The controller for path '/api/billing' was not found or does not implement IController.
   at System.Web.Mvc.MvcHandler.ProcessRequestInit()""",
            
            """System.TypeLoadException: Could not load type 'BillerPortal.Models.InvoiceModel' from assembly 'BillerPortal.Core, Version=1.0.0.0'
   at BillerPortal.Services.InvoiceService.CreateInvoice() in C:\\src\\Services\\InvoiceService.cs:line 28""",
            
            # Configuration and deployment errors
            "System.IO.FileNotFoundException: Could not load file or assembly 'Newtonsoft.Json, Version=13.0.0.0' or one of its dependencies.",
            
            "System.Security.SecurityException: Request for the permission of type 'System.Security.Permissions.FileIOPermission' failed.",
            
            # Web-specific errors
            "System.Web.UI.ViewStateException: Invalid viewstate. Client IP: 192.168.1.100 User-Agent: Mozilla/5.0",
            
            "System.Web.Services.Protocols.SoapException: Server was unable to process request. ---> System.ArgumentException: Invalid billing account number.",
            
            # Database and Entity Framework errors
            "System.Data.Entity.Infrastructure.DbUpdateConcurrencyException: Store update, insert, or delete statement affected an unexpected number of rows (0).",
            
            "System.Data.Entity.ModelConfiguration.ModelValidationException: One or more validation errors were detected during model generation",
            
            # Modern .NET Core errors
            "Microsoft.AspNetCore.Http.BadHttpRequestException: Reading the request body timed out due to data arriving too slowly.",
            
            "System.Text.Json.JsonException: The JSON value could not be converted to System.DateTime."
        ]


# Create a global instance for use in UI
error_analysis_feature = ErrorAnalysisFeature()