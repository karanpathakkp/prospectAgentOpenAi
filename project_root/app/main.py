import asyncio
import json
import os
import re
from datetime import datetime
import logging

from agents import Agent, Runner
from dotenv import load_dotenv
from pydantic import BaseModel
from tools.tools import tavily_search, scrape_website
from utils.utility import (
    parse_position_titles, 
    improved_search,
    FilteredProfile
)

# Load environment variables from .env file (optional)
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get desired profile count from environment variable
DESIRED_PROFILES = int(os.getenv("desired_profile", "10"))


class GeneratedRolesAndOrganizations(BaseModel):
    generated_positions: list[str]
    organization_name: str



async def main(company: str, desired_profile: int, search_term: str):
    """
    Main function - completely file-independent deployment-ready workflow.
    """
    # Configuration - can be moved to environment variables for deployment
    
    root_agent = Agent(
        name="RootAgent",
        instructions=f"i will give you some Postions titles in an organization named {company} , generate only some relevant titles used for similiar posts in that {company} , Like some companies use software engineer and some call it Member of Technical Staff",
        model="gpt-4o",
        tools=[tavily_search, scrape_website],
    )
    
    with open(os.path.join("prompts", "prompt.txt"), "r") as f:
        prompts = f.read().split("\n---\n")
        loop_agent_instructions = prompts[0].strip()
        filter_agent_instructions = prompts[1].strip() if len(prompts) > 1 else ""

    loop_agent = Agent(
        name="LoopAgent",
        instructions=loop_agent_instructions,
        model="gpt-4o",
        tools=[tavily_search, scrape_website],
    )
    
    filter_agent = Agent(
        name="FilterAgent",
        instructions=filter_agent_instructions,
        model="gpt-4o"
    )
    
    try:
        # Step 1: Generate position titles
        logger.info("="*60)
        logger.info("GENERATING POSITION TITLES")
        logger.info("="*60)
        
        print(f"Search term: {search_term}")
        print(f"Company: {company}")
        print(f"DESIRED_PROFILES: {desired_profile}")
        
        search_query = search_term
        result = await Runner.run(root_agent, search_query, max_turns=2000)
        logger.info("Final output from KaransAgent:")
        logger.info(result.final_output)
        
        # Parse position titles from the result
        position_titles = parse_position_titles(result.final_output)
        
        logger.info("="*50)
        logger.info("POSITION TITLES GENERATED:")
        logger.info("="*50)
        
        if position_titles:
            for i, title in enumerate(position_titles, 1):
                logger.info(f"{i}. {title}")
        else:
            logger.warning("No position titles found in the output")
            # Fallback position titles if generation fails
            position_titles = [
                "VP of R&D", "Head of R&D", "CTO", "CIO", 
                "Director of Innovation", "Head of Digital Transformation",
                "VP Engineering", "Chief Innovation Officer"
            ]
            logger.info("Using fallback position titles")
        
        logger.info("="*50)
        logger.info(f"Position titles as Python list: {position_titles}")
        
        # Use improved_search for in-memory streaming workflow
        final_profiles = await improved_search(position_titles, company, filter_agent, loop_agent, desired_profile, max_retries=2)
        
        logger.info("="*60)
        logger.info("WORKFLOW COMPLETED SUCCESSFULLY")
        logger.info("="*60)
        logger.info(f"Final result: {len(final_profiles) if isinstance(final_profiles, list) else 'N/A'} profiles found")
        
        return final_profiles
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    import sys
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--company', type=str, required=True)
    parser.add_argument('--desired_profile', type=int, required=True)
    parser.add_argument('--search_term', type=str, required=True)
    args = parser.parse_args()
    asyncio.run(main(args.company, args.desired_profile, args.search_term))