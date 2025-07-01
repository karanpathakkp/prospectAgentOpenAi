import asyncio
import json
import os
import re
from datetime import datetime
import logging

from agents import Agent, Runner
from dotenv import load_dotenv
from pydantic import BaseModel
from tools import tavily_search, scrape_website
from utility import (
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
    
    loop_agent = Agent(
        name="LoopAgent",
        #output_type=PositionTitle,
        instructions=(
            f"You are an agent that performs Tavily searches to find LinkedIn profiles and web profiles "
            f"of individuals at {company}. When given a search query, perform a Tavily search and return "
            f"the raw Tavily API response exactly as received. Do not modify, format, or summarize the results. "
            f"Simply return the complete JSON response from the Tavily API with all the search results. "
            f"Your output must be valid JSON that contains a 'results' key with an array of profile objects."
            f"\n\nSEARCH REQUIREMENTS:"
            f"\n- Find profiles of people working at {company} in the specified role"
            f"\n- Extract detailed information about their experience, education, skills, and achievements"
            f"\n- Focus on getting complete work history, not just current position"
            f"\n- Look for leadership experience, technical skills, and innovation background"
            f"\n- Ensure you get enough detail to assess their suitability for leadership/R&D roles"
            f"\n- Do not return company pages, posts, or articles - only individual profiles"
        ),
        model="gpt-4o",
        tools=[tavily_search, scrape_website],
    )
    
    filter_agent = Agent(
        name="FilterAgent",
        
        instructions=(
            f"You are an expert HR analyst and filtering agent specializing in identifying top leadership and R&D talent for {company}. "
            f"You receive a list of LinkedIn profiles and must analyze each one comprehensively to select the {DESIRED_PROFILES} best candidates. "
            f"\n\nANALYSIS CRITERIA:"
            f"\n1. ROLE RELEVANCE (0-10): How well the person's current/previous roles align with {search_term}"
            f"\n2. EXPERIENCE SCORE (0-10): Based on total years of experience, with bonus for relevant industry experience"
            f"\n3. LEADERSHIP INDICATORS (0-10): Evidence of leadership roles, team management, strategic decision-making"
            f"\n4. TECHNICAL/R&D SCORE (0-10): Technical skills, innovation experience, R&D background, patents, publications"
            #f"\n5. COMPANY MATCH (0-10): How well their background aligns with {company}'s industry and culture"
            f"\n\nSCORING METHODOLOGY:"
            f"\n- Calculate a custom score (0-100) based on the above criteria"
            f"\n- Ignore the original Tavily score completely"
            f"\n- Weight: Role Relevance (25%), Experience (20%), Leadership (25%), Technical (20%), Company Match (10%)"
            f"\n\nREQUIRED OUTPUT FORMAT:"
            f"\nReturn a JSON array of {DESIRED_PROFILES} profiles with the following structure:"
            f"\n{{\n"
            f"  'title': 'Profile title',\n"
            f"  'url': 'LinkedIn URL',\n"
            f"  'content': 'Original content',\n"
            f"  'score': [YOUR_CUSTOM_SCORE_0_100],\n"
            f"  'role_relevance_score': [0-10],\n"
            f"  'experience_score': [0-10],\n"
            f"  'leadership_score': [0-10],\n"
            f"  'technical_score': [0-10],\n"
           
            f"  'total_years_experience': [number],\n"
            f"  'current_role': 'Current position title',\n"
            f"  'previous_companies': ['company1', 'company2'],\n"
            f"  'education': ['degree1', 'degree2'],\n"
            f"  'skills': ['skill1', 'skill2'],\n"
            f"  'analysis_notes': 'Your detailed analysis of why this person is a good fit'\n"
            f"\n}}\n"
            f"\nFILTERING RULES:"
            f"\n- ONLY include individual LinkedIn profiles (not posts, articles, or company pages)"
            f"\n- Prioritize profiles with clear leadership or technical leadership experience"
            f"\n- Look for innovation, R&D, digital transformation, or strategic technology experience"
            f"\n- Consider both current and previous roles for relevance"
            f"\n- Analyze the content carefully to extract experience details, skills, and achievements"
            f"\n- Provide detailed analysis_notes explaining your scoring rationale"
            f"\n\nIMPORTANT: Extract as much information as possible from the content field to populate all the detailed fields. "
            f"Be thorough in your analysis and provide specific reasons for your scoring decisions."
        ),
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