import json
import re
import logging
import os
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv
from typing import Optional, List, Dict
from agents import Runner


# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class PositionTitle(BaseModel):
    model_config = ConfigDict(
        extra='forbid',  # Replaces Config.extra = 'forbid'
        validate_assignment=True  # Replaces Config.validate_assignment = True
    )
    
    position_title: str
    organization_name: str
    linkedin_profile: str
    experience: int
    current_company: str
    current_company_experience: int

class FilteredProfile(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
        validate_assignment=True
    )
    
    title: str
    url: str
    content: str
    score: float
    experience: Optional[List[Dict]] = []
    

def parse_position_titles(agent_output):
    """Extract position titles from agent output"""
    position_titles = []
    
    try:
        if isinstance(agent_output, str):
            # Try to find JSON array in the string
            json_match = re.search(r'\[.*\]', agent_output, re.DOTALL)
            if json_match:
                position_titles = json.loads(json_match.group())
            else:
                # Parse line by line as fallback
                lines = agent_output.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#') and len(line) > 3:
                        # Remove numbering and formatting
                        clean_line = re.sub(r'^[\d\-\.\s]+', '', line)
                        if clean_line:
                            position_titles.append(clean_line)
        else:
            position_titles = agent_output
            
    except Exception as parse_error:
        logger.error(f"Error parsing position titles: {parse_error}")
        position_titles = [agent_output] if agent_output else []
    
    return position_titles

def extract_profiles(result):
    """Extracts profile dicts from various result formats."""
    profiles = []
    
    # Debug logging
    # print("DEBUG: agent_result.final_output =", result)
    print(f"One More Time Done")
    # print("DEBUG: type =", type(result))
    
    if not result:
        return profiles
    
    # Handle different result formats
    if isinstance(result, str):
        # Handle markdown-wrapped JSON (```json ... ```)
        if result.startswith('```json') and result.endswith('```'):
            result = result[7:-3].strip()  # Remove ```json and ``` markers
        elif result.startswith('```') and result.endswith('```'):
            result = result[3:-3].strip()  # Remove ``` markers
        
        try:
            import json
            result = json.loads(result)
        except json.JSONDecodeError:
            logger.warning("Could not parse string result as JSON")
            return profiles
    
    if not isinstance(result, dict):
        return profiles
    
    # Check for different possible structures
    profile_data = None
    
    # Format 1: Direct Tavily API response format
    if 'results' in result:
        profile_data = result['results']
    
    # Format 2: Your loop_agent format with 'profiles' key
    elif 'profiles' in result:
        profile_data = result['profiles']
    
    # Format 3: If result is already a list of profiles
    elif isinstance(result, list):
        profile_data = result
    
    if profile_data:
        for res in profile_data:
            if isinstance(res, dict):
                profiles.append({
                    'title': res.get('title', ''),
                    'url': res.get('url', ''),
                    'content': res.get('content', ''),
                    'score': res.get('score', 0)
                })
            elif isinstance(res, PositionTitle):
                profiles.append({
                    'title': res.position_title,
                    'url': res.linkedin_profile,
                    'content': '',  # or any other relevant field
                    'score': 0      # or any other relevant field
                })
    
    return profiles

def deduplicate_by_url(profiles):
    """Deduplicate profiles by URL."""
    seen = set()
    unique = []
    for p in profiles:
        url = p.get('url')
        if url and url not in seen:
            unique.append(p)
            seen.add(url)
    return unique

async def improved_search(position_titles, company, filter_agent, loop_agent, desired_profile, max_retries=2):
    """
    Improved search workflow that keeps everything in memory.
    No file dependencies - all data processing happens in memory.
    Stage 2 runs first (web-wide search), then Stage 1 (non-LinkedIn) if needed.
    Retries the process if not enough relevant profiles are found after filtering.
    Accumulates unique relevant profiles across retries.
    """
    attempt = 0
    accumulated_profiles = []
    accumulated_urls = set()
    while attempt <= max_retries:
        all_profiles = []
        logger.info(f"=== Improved search attempt {attempt+1} of {max_retries+1} ===")
        # Stage 2: Web-wide search (NO LinkedIn) - runs first
        logger.info("="*50)
        logger.info("STAGE 2: WEB-WIDE SEARCH (NO LINKEDIN) - IN-MEMORY")
        logger.info("="*50)
        
        for title in position_titles:
            query = f"{title} at {company}. "
            logger.info(f"Searching web-wide (no LinkedIn): {query}")
            try:
                agent_result = await Runner.run(loop_agent, f"Search for: {query}", max_turns=5)
                profiles = extract_profiles(agent_result.final_output)
                all_profiles.extend(profiles)
                
                # Check if we have enough profiles to stop early
                unique_profiles = deduplicate_by_url(all_profiles)
                if len(unique_profiles) > 2 * desired_profile:
                    logger.info(f"Found {len(unique_profiles)} profiles, stopping early (target: {2 * desired_profile})")
                    break
            except Exception as e:
                logger.error(f"Web-wide search failed for {title}: {e}")
        
        unique_profiles = deduplicate_by_url(all_profiles)
        logger.info(f"Profiles found after web-wide search (no LinkedIn): {len(unique_profiles)}")
        logger.info(f"unique_profiles: {unique_profiles}")
        
        # Stage 1: LinkedIn search if needed (ONLY LinkedIn)
        if len(unique_profiles) < desired_profile:
            logger.info("="*50)
            logger.info("STAGE 1: LINKEDIN-ONLY SEARCH FOR REMAINING PROFILES (IN-MEMORY)")
            logger.info("="*50)
            
            needed = desired_profile - len(unique_profiles)
            logger.info(f"Need {needed} more profiles, searching LinkedIn...")
            
            for title in position_titles[1:]:  # Start from second value
                # LinkedIn-only search
                query = f"{title} {company} site:linkedin.com get Name, Position, complete work history and experience and previous roles in content Section"
                logger.info(f"Searching LinkedIn only: {query}")
                try:
                    agent_result = await Runner.run(loop_agent, f"Search for: {query}", max_turns=5)
                    profiles = extract_profiles(agent_result.final_output)
                    all_profiles.extend(profiles)
                    
                    # Check if we have enough profiles after each search
                    unique_profiles = deduplicate_by_url(all_profiles)
                    if len(unique_profiles) >= desired_profile:
                        logger.info(f"Reached target of {desired_profile} profiles, stopping search")
                        break
                except Exception as e:
                    logger.error(f"LinkedIn search failed for {title}: {e}")
        
        unique_profiles = deduplicate_by_url(all_profiles)
        
        # Final filtering with agent - with improved error handling for Pydantic v2
        logger.info("="*50)
        logger.info(f"FILTERING FINAL {desired_profile} PROFILES (IN-MEMORY):")
        logger.info("="*50)
        
        if unique_profiles:
            filter_input = json.dumps(unique_profiles, indent=2)
            profiles_needed = desired_profile - len(accumulated_profiles)
            filter_result = await Runner.run(
                filter_agent,
                f"Select the {profiles_needed} best profiles from this list (as a JSON array): {filter_input}"
            )
            logger.info(f"Filtered profiles this attempt:")
            logger.info(filter_result.final_output)
            # Try to parse the output as a list
            try:
                output = filter_result.final_output.strip()
                # Remove markdown code block if present
                if output.startswith('```json') and output.endswith('```'):
                    output = output[7:-3].strip()
                elif output.startswith('```') and output.endswith('```'):
                    output = output[3:-3].strip()
                filtered_profiles = json.loads(output)
            except Exception as e:
                logger.warning(f"Could not parse filter agent output as JSON: {e}")
                filtered_profiles = []
            # Add only new unique profiles to accumulated_profiles
            new_profiles = []
            for p in filtered_profiles:
                url = p.get('url')
                if url and url not in accumulated_urls:
                    accumulated_urls.add(url)
                    new_profiles.append(p)
            accumulated_profiles.extend(new_profiles)
            logger.info(f"Accumulated {len(accumulated_profiles)} unique relevant profiles so far.")
            if len(accumulated_profiles) >= desired_profile:
                logger.info(f"Reached desired number of profiles ({desired_profile}). Returning accumulated profiles.")
                return accumulated_profiles[:desired_profile]
            else:
                logger.warning(f"Filter agent returned only {len(filtered_profiles)} new profiles, expected {profiles_needed}. Retrying...")
        else:
            logger.warning("No profiles available for filtering")
        attempt += 1
    logger.warning(f"After {max_retries+1} attempts, still fewer than {desired_profile} relevant profiles. Returning best found.")
    return accumulated_profiles if accumulated_profiles else []