#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from crewai_tools import tool
import auth
import time

# --- All your v6 tools go here ---
# (Import them or copy-paste them)
# from fapc_tools_v6 import (
#     secure_cli_tool, click_screen_tool, take_screenshot_tool,
#     analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool
# )
# _ = (secure_cli_tool, click_screen_tool, ...) # etc.
# ---

# --- Stateful Browser Session ---
# This object will be created by the master script and
# will hold the live browser session.
class BrowserSession:
    def __init__(self):
        self.driver = None
        print("[BrowserTool] Session initialized.")

    def start_browser(self):
        if self.driver:
            return "Browser is already running."
        try:
            options = Options()
            options.add_argument("--headless") # Run in the background
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            service = Service(executable_path="/usr/local/bin/geckodriver")
            self.driver = webdriver.Firefox(service=service, options=options)
            return "Firefox browser started in headless mode."
        except Exception as e:
            return f"Error starting browser: {e}"

    def stop_browser(self):
        if not self.driver:
            return "Browser is not running."
        try:
            self.driver.quit()
            self.driver = None
            return "Browser session stopped."
        except Exception as e:
            return f"Error stopping browser: {e}"

    def navigate(self, url: str):
        if not self.driver:
            return "Error: Browser not started. Use 'start_browser_tool' first."
        try:
            self.driver.get(url)
            return f"Navigated to {url}. Current page title: {self.driver.title}"
        except Exception as e:
            return f"Error navigating: {e}"

    def fill_form(self, selector: str, text: str):
        if not self.driver:
            return "Error: Browser not started."
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            element.clear()
            element.send_keys(text)
            return f"Filled element '{selector}' with text."
        except Exception as e:
            return f"Error filling form: {e}"

    def click_element(self, selector: str):
        if not self.driver:
            return "Error: Browser not started."
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            element.click()
            time.sleep(2) # Wait for page to react
            return f"Clicked element '{selector}'."
        except Exception as e:
            return f"Error clicking element: {e}"

    def read_page(self):
        if not self.driver:
            return "Error: Browser not started."
        try:
            # Get all visible text
            body = self.driver.find_element(By.TAG_NAME, 'body')
            return body.text[:4000] # Return first 4000 chars
        except Exception as e:
            return f"Error reading page: {e}"

# --- Create a global session for the tools to share ---
# This is a simple way to maintain state between tool calls.
browser_session = BrowserSession()

# --- Create the @tool wrappers ---

@tool("Start Browser Tool")
def start_browser_tool(user_id: int) -> str:
    """
    Starts the headless Firefox browser.
    This MUST be called before any other browser action.
    (user_id is for logging).
    """
    auth.log_activity(user_id, 'browser_start', 'Attempting to start browser', 'success')
    return browser_session.start_browser()

@tool("Stop Browser Tool")
def stop_browser_tool(user_id: int) -> str:
    """
    Stops and closes the browser session.
    (user_id is for logging).
    """
    auth.log_activity(user_id, 'browser_stop', 'Stopping browser', 'success')
    return browser_session.stop_browser()

@tool("Navigate URL Tool")
def navigate_url_tool(url: str, user_id: int) -> str:
    """
    Navigates the browser to a specific URL.
    - url: The full URL (e.g., 'https://google.com').
    - user_id: The user_id for logging.
    """
    auth.log_activity(user_id, 'browser_navigate', f"Navigating to {url}", 'success')
    return browser_session.navigate(url)

@tool("Fill Form Tool")
def fill_form_tool(selector: str, text: str, user_id: int) -> str:
    """
    Fills a form field with text.
    - selector: The CSS selector for the input (e.g., 'input#username').
    - text: The text to type.
    - user_id: The user_id for logging.
    """
    auth.log_activity(user_id, 'browser_fill', f"Filling {selector}", 'success')
    return browser_session.fill_form(selector, text)

@tool("Click Element Tool")
def click_element_tool(selector: str, user_id: int) -> str:
    """
    Clicks a button or link.
    - selector: The CSS selector for the element (e.g., 'button.submit').
    - user_id: The user_id for logging.
    """
    auth.log_activity(user_id, 'browser_click', f"Clicking {selector}", 'success')
    return browser_session.click_element(selector)

@tool("Read Page Text Tool")
def read_page_text_tool(user_id: int) -> str:
    """
    Reads all visible text from the current webpage.
    (user_id is for logging).
    """
    auth.log_activity(user_id, 'browser_read', 'Reading page text', 'success')
    return browser_session.read_page()