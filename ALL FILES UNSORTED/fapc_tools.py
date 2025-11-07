#!/usr/bin/env python3

import subprocess
import sys
from crewai_tools import tool

# This script "tool-ifies" your existing command-line agents for CrewAI.

@tool("Find Tasks Tool")
def find_tasks_tool(query: str) -> str:
    """
    Use this tool to find and retrieve tasks from the vector database.
    The input 'query' is a natural language string, exactly as a human
    would type it.
    Example: find_tasks_tool("all critical tasks for PlausiDen")
    Returns a string containing the formatted report of found tasks.
    """
    print(f"[Tool Call: find_tasks_tool] Input: '{query}'")
    try:
        # We must split the query string into a list of arguments
        # to correctly pass it to 'project_status.py', which uses nargs='+'
        args = query.split()

        # We run the 'project_status.py' script as a subprocess
        result = subprocess.run(
            ['python3', 'project_status.py'] + args,
            capture_output=True,
            text=True,
            check=True
        )
        # Return the standard output of the script
        return result.stdout
    except subprocess.CalledProcessError as e:
        # If the script fails, return the error message
        return f"Error finding tasks: {e.stderr}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

@tool("Update Task Tool")
def update_task_tool(task_id: str, updates: str) -> str:
    """
    Use this tool to update an existing task's metadata.
    'task_id' is the unique ID of the task.
    'updates' is a string of command-line arguments for the update,
    for example: '--status "in_progress" --priority "High"'
    Example: update_task_tool(
        task_id="task_f8c1b2a3-...",
        updates="--status completed"
    )
    Returns a string containing the success or error message.
    """
    print(f"[Tool Call: update_task_tool] ID: '{task_id}', Updates: '{updates}'")
    try:
        # Split the updates string into arguments
        update_args = updates.split()

        # Build the full command
        command = ['python3', 'task_manager.py', task_id] + update_args

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error updating task: {e.stderr}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

@tool("Create Task Tool")
def create_task_tool(task_description: str) -> str:
    """
    Use this tool to create a new task in the vector database.
    'task_description' is a full, natural language description of the task.
    Example: create_task_tool("Set up a new Tor hidden service for the
    Defendology website, this is high priority.")
    Returns a string containing the success or error message.
    """
    print(f"[Tool Call: create_task_tool] Description: '{task_description}'")
    try:
        # Split the description string for nargs='+'
        args = task_description.split()

        result = subprocess.run(
            ['python3', 'task_ingestor.py'] + args,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error creating task: {e.stderr}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"
    # --- New Tool for Intelligence Agent ---
import requests
from bs4 import BeautifulSoup

@tool("Scrape Website Tool")
def scrape_website_tool(url: str) -> str:
    """
    Use this tool to scrape the text content from a given URL.
    The input 'url' must be a valid, full URL (e.g., 'https://...').
    It returns the first 4000 characters of the website's
    text content.
    Example: scrape_website_tool("https://nist.gov/pqc")
    Returns a string of the site's text content.
    """
    print(f"[Tool Call: scrape_website_tool] URL: '{url}'")
    try:
        # 1. Fetch the HTML content
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # Raise an error for bad responses

        # 2. Parse the HTML with BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")

        # 3. Extract all text
        # This will get text from all <p>, <div>, <h1>, etc. tags
        all_text = soup.get_text(separator=' ', strip=True)

        # 4. Clean up whitespace
        cleaned_text = ' '.join(all_text.split())

        # 5. Return the first 4000 characters to avoid context overflow
        if len(cleaned_text) > 4000:
            print(f"[Tool Call: scrape_website_tool] Succeeded. Truncating content from {len(cleaned_text)} chars.")
            return cleaned_text[:4000]
        else:
            print(f"[Tool Call: scrape_website_tool] Succeeded. Returning {len(cleaned_text)} chars.")
            return cleaned_text

    except requests.exceptions.RequestException as e:
        return f"Error during web request: {e}"
    except Exception as e:
        return f"An unexpected error occurred during scraping: {e}"

# --- New Tool for Intelligence Agent ---
import requests
from bs4 import BeautifulSoup

@tool("Scrape Website Tool")
def scrape_website_tool(url: str) -> str:
    """
Use this tool to scrape the text content from a given URL.
The input 'url' must be a valid, full URL (e.g., 'https://...').
It returns the first 4000 characters of the website's
text content.
Example: scrape_website_tool("https://nist.gov/pqc")
Returns a string of the site's text content.
    """
    print(f"[Tool Call: scrape_website_tool] URL: '{url}'")
    try:
        # 1. Fetch the HTML content
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # Raise an error for bad responses

        # 2. Parse the HTML with BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")

        # 3. Extract all text
        # This will get text from all <p>, <div>, <h1>, etc. tags
        all_text = soup.get_text(separator=' ', strip=True)

        # 4. Clean up whitespace
        cleaned_text = ' '.join(all_text.split())

        # 5. Return the first 4000 characters to avoid context overflow
        if len(cleaned_text) > 4000:
            print(f"[Tool Call: scrape_website_tool] Succeeded. Truncating content from {len(cleaned_text)} chars.")
            return cleaned_text[:4000]
        else:
            print(f"[Tool Call: scrape_website_tool] Succeeded. Returning {len(cleaned_text)} chars.")
            return cleaned_text

    except requests.exceptions.RequestException as e:
        return f"Error during web request: {e}"
    except Exception as e:
        return f"An unexpected error occurred during scraping: {e}"

# --- New Tool for Threat Watchtower ---
from duckduckgo_search import DDGS

@tool("Web Search Tool")
def web_search_tool(query: str) -> str:
    """
Use this tool to search the web for recent articles and information.
The input 'query' is a natural language search query.
Example: web_search_tool("newest PQC vulnerabilities 2025")
Returns a string of the top 5 search results, including their
URL and a snippet.
    """
    print(f"[Tool Call: web_search_tool] Query: '{query}'")
    try:
        # Use DDGS to find the top 5 recent results
        with DDGS() as ddgs:
            results = list(ddgs.text(
                               keywords=query,
                               region='wt-wt',
                               safesearch='off',
                               timelimit='w', # 'w' = last week, 'd' = last day
                               max_results=5
                           ))

        if not results:
            return "No recent results found."

        # Format the results into a clean string for the agent
        formatted_results = []
        for i, res in enumerate(results):
            formatted_results.append(
                f"Result {i+1}:\n"
                f"  Title: {res['title']}\n"
                f"  URL: {res['href']}\n"
                f"  Snippet: {res['body']}\n"
            )

        return "\n".join(formatted_results)

    except Exception as e:
        return f"An unexpected error occurred during search: {e}"