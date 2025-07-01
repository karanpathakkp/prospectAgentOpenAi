import os
import requests
import logging
from typing import Dict
import datetime
import json
from agents import function_tool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

@function_tool
def scrape_website(website_url: str, session_id: str = "default_session") -> dict:
    """Scrapes a website using Firecrawl API.

    Args:
        website_url (str): The URL of the website to scrape.
        session_id (str): Current session ID for storing results.
    
    Returns:
        dict: status and result or error msg.
    """
    try:
        # Validate inputs
        if not website_url or not isinstance(website_url, str):
            return {
                "status": "error",
                "error_message": "Invalid website URL provided",
                "url": website_url
            }

        # Get API key from environment variables
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            return {
                "status": "error",
                "error_message": "FIRECRAWL_API_KEY not found in environment variables",
                "url": website_url
            }
        
        # Firecrawl API endpoint
        api_url = "https://api.firecrawl.dev/v1/scrape"
        
        # Request headers
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Request payload
        payload = {
            "url": website_url,
            "formats": ["markdown"],  # Only get markdown to reduce content size
            "waitFor": 5000,
            "timeout": 20000
        }
        
        logger.info(f"Scraping website: {website_url}")

        # Make API request with context management
        with requests.Session() as session:
            response = session.post(
                api_url, 
                headers=headers, 
                json=payload, 
                timeout=45
            )

            if response.status_code == 200:
                # Parse and extract website data
                response_data = response.json()
                
                # Check if the response is successful
                if not response_data.get("success", False):
                    error_msg = "Failed to scrape website: API returned unsuccessful response"
                    logger.error(error_msg)
                    return {
                        "status": "error",
                        "error_message": error_msg,
                        "url": website_url
                    }
                
                # Extract the actual data from the response
                website_data = response_data.get("data", {})
                
                # Get content and truncate if necessary
                content = website_data.get("content", "N/A")
                markdown = website_data.get("markdown", "N/A")
                
                # Truncate content to reasonable size (approximately 4000 characters)
                if len(content) > 4000:
                    content = content[:4000] + "... (content truncated)"
                if len(markdown) > 4000:
                    markdown = markdown[:4000] + "... (content truncated)"
                
                # Format the data for better readability
                formatted_result = {
                    "status": "success",
                    "website_data": {
                        "Basic Information": {
                            "URL": website_url,
                            "Title": website_data.get("metadata", {}).get("title", "N/A"),
                            "Description": website_data.get("metadata", {}).get("description", "N/A"),
                            "Language": website_data.get("metadata", {}).get("language", "N/A")
                        },
                        "Content": {
                            "Text": content,
                            "Markdown": markdown
                        },
                        "Links": website_data.get("links", [])[:5]
                    },
                    "timestamp": datetime.datetime.now().isoformat()
                }
                
                logger.info(f"Successfully scraped website: {website_url}")
                return formatted_result
            else:
                error_msg = f"API Error {response.status_code}: {response.text}"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "error_message": error_msg,
                    "url": website_url
                }
            
    except requests.exceptions.Timeout:
        error_msg = f"Timeout while scraping website: {website_url}"
        logger.error(error_msg)
        return {
            "status": "error",
            "error_message": error_msg,
            "url": website_url
        }
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Request failed for {website_url}: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "error_message": error_msg,
            "url": website_url
        }
    
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON response for {website_url}: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "error_message": error_msg,
            "url": website_url
        }
    
    except Exception as e:
        error_msg = f"Unexpected error scraping {website_url}: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "error_message": error_msg,
            "url": website_url
        }

@function_tool
def tavily_search(query: str, search_depth: str = "advanced", max_results: int = 10) -> Dict:
    """Searches the web using Tavily API

    Args:
        query: The search query
        search_depth: The search depth ('basic' or 'advanced')
        max_results: Maximum number of results to return (default 10 to manage context)

    Returns:
        Dict containing search results or error information
    """
    # Update the query parameter after it is received
    # For example, let's append a custom string to the query
    query = f"{query} get  Name, Position, complete work history and  experience and previous roles in content Section"  # <-- You can change this to whatever you want to add

    # Print the query being passed to tavily_search
    print(f"🔍 TAVILY SEARCH QUERY: {query}")

    try:
        if not query or not isinstance(query, str):
            print("--------------------------------")
            print(query)
            print("--------------------------------")
            return {"status": "error", "error_message": "Query must be a non-empty string"}

        # Get API key from environment variable
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            # Fallback to hardcoded key if environment variable not available
            # api_key = "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"

            max_results = int(max_results) if isinstance(max_results, str) else max_results
        if max_results <= 0:
            return {"status": "error", "error_message": "max_results must be a positive integer"}

        valid_depths = ["basic", "advanced"]
        if search_depth not in valid_depths:
            logger.warning(f"Invalid search_depth '{search_depth}', using 'basic'")
            search_depth = "basic"

        api_url = "https://api.tavily.com/search"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "query": query,
            "topic": "general",
            "search_depth": search_depth,
            "chunks_per_source": 2,  # Reduced from 3 to 2
            "max_results": max_results,
            "time_range": None,
            "days": 7,
            "include_answer": True,
            "include_raw_content": False,  # Changed to False to reduce content size
            "include_images": False,
            "include_image_descriptions": False,
            "include_domains": [],
            "exclude_domains": [],
            "country": None
        }

        logger.info(f"Performing Tavily search: {query}")

        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        logger.info(f"API response status: {response.status_code}")
        #logger.info(f"Full API response for query '{query}': {response.text}")

        if response.status_code != 200:
            error_msg = f"API Error {response.status_code}: {response.text}"
            logger.error(error_msg)
            return {"status": "error", "error_message": error_msg}

        results = response.json()

        # Process and truncate results
        processed_results = []
        for result in results.get("results", []):
            # Truncate content if it exists
            if "content" in result and len(result["content"]) > 1000:
                result["content"] = result["content"][:1000] + "... (content truncated)"

            # Keep only essential fields
            processed_result = {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
                "score": result.get("score", 0)
            }
            processed_results.append(processed_result)

        final_response = {
            "status": "success",
            "query": query,
            "results": processed_results,
            "answer": results.get("answer", "")[:500] if results.get("answer") else ""  # Truncate answer
        }

        logger.info(f"Tavily search completed successfully for query: {query}")
        return final_response

    except Exception as e:
        error_msg = f"Error in tavily_search: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error_message": error_msg}