#!/usr/bin/env python3
# Archon Agent - Web Browser (Selenium) Tools

import time
from crewai_tools import tool
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from ..core import auth

browser_session = None

class BrowserSession:
    """A stateful, persistent browser session for the agent."""
    def __init__(self):
        self.driver = None
        print("[BrowserTool] Session initialized.")

    def start_browser(self):
        global browser_session
        if self.driver:
            return "Browser is already running."
        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            # Route Selenium through Tor (via the Docker service 'tor-proxy')
            options.set_preference('network.proxy.type', 1)
            options.set_preference('network.proxy.socks', 'tor-proxy')
            options.set_preference('network.proxy.socks_port', 9050)
            options.set_preference('network.proxy.socks_remote_dns', True)

            service = Service(executable_path="/usr/local/bin/geckodriver")
            self.driver = webdriver.Firefox(service=service, options=options)
            browser_session = self
            return "Firefox browser started in headless, Tor-enabled mode."
        except Exception as e:
            return f"Error starting browser: {e}"

    def stop_browser(self):
        global browser_session
        if not self.driver:
            return "Browser is not running."
        try:
            self.driver.quit()
            self.driver = None
            browser_session = None
            return "Browser session stopped."
        except Exception as e:
            return f"Error stopping browser: {e}"

    def navigate(self, url: str):
        if not self.driver: return "Error: Browser not started."
        try:
            self.driver.get(url)
            return f"Navigated to {url}. Current page title: {self.driver.title}"
        except Exception as e: return f"Error navigating: {e}"

    def fill_form(self, selector: str, text: str):
        if not self.driver: return "Error: Browser not started."
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            element.clear(); element.send_keys(text)
            return f"Filled element '{selector}'."
        except Exception as e: return f"Error filling form: {e}"

    def click_element(self, selector: str):
        if not self.driver: return "Error: Browser not started."
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            element.click(); time.sleep(2) # Wait for page reaction
            return f"Clicked element '{selector}'."
        except Exception as e: return f"Error clicking element: {e}"

    def read_page(self):
        if not self.driver: return "Error: Browser not started."
        try:
            body = self.driver.find_element(By.TAG_NAME, 'body')
            return body.text[:4000] # Return first 4000 chars
        except Exception as e: return f"Error reading page: {e}"

@tool("Start Browser Tool")
def start_browser_tool(user_id: int) -> str:
    """Starts the persistent, headless, Tor-enabled Firefox browser session."""
    global browser_session
    if not browser_session:
        browser_session = BrowserSession()
    auth.log_activity(user_id, 'browser_start', 'Starting browser', 'success')
    return browser_session.start_browser()

@tool("Stop Browser Tool")
def stop_browser_tool(user_id: int) -> str:
    """Stops and closes the browser session."""
    global browser_session
    if not browser_session: return "Browser not running."
    auth.log_activity(user_id, 'browser_stop', 'Stopping browser', 'success')
    result = browser_session.stop_browser()
    browser_session = None # Ensure it's fully reset
    return result

@tool("Navigate URL Tool")
def navigate_url_tool(url: str, user_id: int) -> str:
    """Navigates the browser to a specific URL."""
    if not browser_session: return "Error: Browser not started. Use 'start_browser_tool' first."
    auth.log_activity(user_id, 'browser_navigate', f"Nav to {url}", 'success')
    return browser_session.navigate(url)

@tool("Fill Form Tool")
def fill_form_tool(selector: str, text: str, user_id: int) -> str:
    """Fills a form field with text, identified by a CSS selector."""
    if not browser_session: return "Error: Browser not started."
    auth.log_activity(user_id, 'browser_fill', f"Filling {selector}", 'success')
    return browser_session.fill_form(selector, text)

@tool("Click Element Tool")
def click_element_tool(selector: str, user_id: int) -> str:
    """Clicks a button or link, identified by a CSS selector."""
    if not browser_session: return "Error: Browser not started."
    auth.log_activity(user_id, 'browser_click', f"Clicking {selector}", 'success')
    return browser_session.click_element(selector)

@tool("Read Page Text Tool")
def read_page_text_tool(user_id: int) -> str:
    """Reads all visible text from the current webpage."""
    if not browser_session: return "Error: Browser not started."
    auth.log_activity(user_id, 'browser_read', 'Reading page text', 'success')
    return browser_session.read_page()
