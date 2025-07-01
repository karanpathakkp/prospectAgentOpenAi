import requests
import time
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_BASE_URL = "http://localhost:8000"

# Get desired profile count from environment variable
DEFAULT_MAX_PROFILES = int(os.getenv("desired_profile", "10"))
DEFAULT_COMPANY = os.getenv("TARGET_COMPANY", "OpenAI")

def search_prospects(company: str = None, search_term: str = None, max_profiles: int = None):
    """
    Search for prospects at a given company.
    
    Args:
        company (str, optional): The target company name (uses default from .env if not specified)
        search_term (str, optional): Custom search term
        max_profiles (int): Maximum number of profiles to return (defaults to desired_profile from .env)
    
    Returns:
        dict: Response with request_id and status
    """
    if max_profiles is None:
        max_profiles = DEFAULT_MAX_PROFILES
    
    url = f"{API_BASE_URL}/prospect/search"
    
    payload = {
        "max_profiles": max_profiles
    }
    
    # Only include company if specified (otherwise uses default from .env)
    if company:
        payload["company"] = company
    
    if search_term:
        payload["search_term"] = search_term
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    
    return response.json()

def get_search_status(request_id: str):
    """
    Get the status of a search request.
    
    Args:
        request_id (str): The request ID from search_prospects
    
    Returns:
        dict: Current status and results if completed
    """
    url = f"{API_BASE_URL}/prospect/status/{request_id}"
    
    response = requests.get(url)
    response.raise_for_status()
    
    return response.json()

def wait_for_completion(request_id: str, max_wait_time: int = 300, check_interval: int = 5):
    """
    Wait for a search to complete.
    
    Args:
        request_id (str): The request ID
        max_wait_time (int): Maximum time to wait in seconds
        check_interval (int): How often to check status in seconds
    
    Returns:
        dict: Final result when completed
    """
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        status = get_search_status(request_id)
        
        if status["status"] in ["completed", "error"]:
            return status
        
        print(f"Status: {status['status']} - {status['message']}")
        time.sleep(check_interval)
    
    raise TimeoutError(f"Search did not complete within {max_wait_time} seconds")

def list_all_searches():
    """
    List all search requests.
    
    Returns:
        dict: List of all searches and their statuses
    """
    url = f"{API_BASE_URL}/prospect/list"
    
    response = requests.get(url)
    response.raise_for_status()
    
    return response.json()

def delete_search(request_id: str):
    """
    Delete a search request.
    
    Args:
        request_id (str): The request ID to delete
    """
    url = f"{API_BASE_URL}/prospect/{request_id}"
    
    response = requests.delete(url)
    response.raise_for_status()
    
    return response.json()

def main():
    """
    Example usage of the Prospect Research API.
    """
    print("=== Prospect Research API Client Example ===\n")
    print(f"Default company: {DEFAULT_COMPANY}")
    print(f"Default max profiles: {DEFAULT_MAX_PROFILES}\n")
    
    # Example 1: Search using default company from .env
    print("1. Searching for prospects using default company...")
    try:
        result = search_prospects()  # No company specified - uses default
        request_id = result["request_id"]
        print(f"   Request ID: {request_id}")
        print(f"   Status: {result['status']}")
        print(f"   Message: {result['message']}\n")
        
        # Wait for completion
        print("2. Waiting for search to complete...")
        final_result = wait_for_completion(request_id)
        
        print(f"   Final Status: {final_result['status']}")
        print(f"   Message: {final_result['message']}")
        
        if final_result["profiles"]:
            print(f"   Found {len(final_result['profiles'])} profiles:")
            for i, profile in enumerate(final_result["profiles"], 1):
                print(f"   {i}. {profile.get('title', 'N/A')}")
                print(f"      URL: {profile.get('url', 'N/A')}")
                print(f"      Score: {profile.get('score', 'N/A')}")
                print()
        else:
            print("   No profiles found.")
        
    except Exception as e:
        print(f"   Error: {e}\n")
    
    # Example 2: Search for specific company
    print("3. Searching for prospects at 'Microsoft'...")
    try:
        result = search_prospects(company="Microsoft")
        request_id = result["request_id"]
        print(f"   Request ID: {request_id}")
        print(f"   Status: {result['status']}")
        print(f"   Message: {result['message']}\n")
        
        # Wait for completion
        print("4. Waiting for search to complete...")
        final_result = wait_for_completion(request_id)
        
        print(f"   Final Status: {final_result['status']}")
        print(f"   Message: {final_result['message']}")
        
        if final_result["profiles"]:
            print(f"   Found {len(final_result['profiles'])} profiles:")
            for i, profile in enumerate(final_result["profiles"][:3], 1):  # Show first 3
                print(f"   {i}. {profile.get('title', 'N/A')}")
                print(f"      URL: {profile.get('url', 'N/A')}")
                print(f"      Score: {profile.get('score', 'N/A')}")
                print()
        else:
            print("   No profiles found.")
        
    except Exception as e:
        print(f"   Error: {e}\n")
    
    # Example 3: List all searches
    print("5. Listing all searches...")
    try:
        searches = list_all_searches()
        print(f"   Total searches: {searches['total']}")
        for search in searches["searches"]:
            company = search.get('company', 'Unknown')
            print(f"   - {search['request_id']}: {search['status']} (Company: {company})")
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    main() 