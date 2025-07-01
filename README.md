# Prospect Research Agent

This project implements an AI agent that can search for and analyze information about key decision-makers in companies, specifically focusing on roles related to R&D and digital transformation.

## Features

- Uses Tavily API for web searches
- Implements web scraping capabilities
- Can identify and analyze profiles of key decision-makers
- Supports custom search queries and instructions

## Setup

1. Clone the repository

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your API keys:

```sh
TAVILY_API_KEY=your_tavily_api_key
```

## Usage

Run the main script:

```bash
python prospect.py
python api.py   (in app forlder)
```
 
## Sample cURL request
curl -X POST "http://localhost:8000/prospect/search" \
  -H "Content-Type: application/json" \
  -d '{
    "company": "OpenAI",
    "search_term": "R&D",
    "max_profiles": 5
  }'

## Project Structure

- `prospect.py`: Main script for running the agent
- `tools.py`: Contains the search and scraping tools
- `prompt.txt`: Contains the agent's instructions
- `.env`: Environment variables (not tracked in git)

## Requirements

- Python 3.x
- OpenAI API access
- Tavily API key

## Tree
prospectAgentOpenAi
    └── project_root
        ├── README.md
        ├── app
        │   ├── __pycache__
        │   │   └── main.cpython-312.pyc
        │   ├── api.py
        │   ├── main.py
        │   ├── prompts
        │   │   └── prompt.txt
        │   ├── tools
        │   │   ├── __pycache__
        │   │   │   └── tools.cpython-312.pyc
        │   │   └── tools.py
        │   └── utils
        │       ├── __pycache__
        │       │   └── utility.cpython-312.pyc
        │       └── utility.py
        ├── requirements.txt
        └── scripts
            ├── client_example.py
            ├── fix_dependencies.sh
            └── start_api.sh
