// This is the TypeScript frontend logic
// It connects the UI (HTML) to the Rust backend (Tauri)

// Import the 'invoke' function from Tauri
import { invoke } from "@tauri-apps/api/tauri";

// --- Global State ---
let apiUrl: string | null = null;
let apiToken: string | null = null; // We will store the JWT here

// --- DOM Elements ---
const loginContainer = document.querySelector<HTMLDivElement>("#login-container");
const chatContainer = document.querySelector<HTMLDivElement>("#chat-container");
const loginForm = document.querySelector<HTMLFormElement>("#login-form");
const loginStatus = document.querySelector<HTMLParagraphElement>("#login-status");
const apiUrlInput = document.querySelector<HTMLInputElement>("#api-url");
const usernameInput = document.querySelector<HTMLInputElement>("#login-username");
const passwordInput = document.querySelector<HTMLInputElement>("#login-password");

const chatForm = document.querySelector<HTMLFormElement>("#chat-form");
const chatInput = document.querySelector<HTMLInputElement>("#chat-input");
const chatWindow = document.querySelector<HTMLDivElement>("#chat-window");

// --- Login Logic ---
loginForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!apiUrlInput || !usernameInput || !passwordInput || !loginStatus) return;

  const url = apiUrlInput.value;
  const username = usernameInput.value;
  const password = passwordInput.value;
  loginStatus.textContent = "Authenticating...";

  try {
    // This calls the 'login' function in your Rust (main.rs) backend
    const response: string = await invoke("login", {
      username: username,
      password: password,
      apiOnionUrl: url,
    });

    // Login was successful
    console.log(response);
    apiUrl = url; // Store the URL for later
    
    // We don't get the token, the Rust state stores it.
    // This is more secure!
    
    // Switch to the chat UI
    if (loginContainer) loginContainer.hidden = true;
    if (chatContainer) chatContainer.hidden = false;
    
    addMessageToChat("ARCHON", "Authentication successful. Standing by for command.");

  } catch (err) {
    // Login failed
    loginStatus.textContent = `Login failed: ${err}`;
  }
});

// --- Chat Logic ---
chatForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!chatInput || !apiUrl) return;

  const command = chatInput.value;
  if (command.trim() === "") return;

  // Add the user's message to the UI
  addMessageToChat("Operator", command);
  chatInput.value = "";
  chatInput.disabled = true;

  try {
    // This calls the 'run_archon_command' in your Rust backend
    const response: string = await invoke("run_archon_command", {
      command: command,
      apiOnionUrl: apiUrl,
    });
    
    // Add Archon's response to the UI
    addMessageToChat("ARCHON", response);

  } catch (err) {
    addMessageToChat("ARCHON", `Error: ${err}`);
  }

  chatInput.disabled = false;
  chatInput.focus();
});

// --- UI Helper Function ---
function addMessageToChat(role: "Operator" | "ARCHON", text: string) {
  if (!chatWindow) return;

  const messageDiv = document.createElement("div");
  messageDiv.classList.add("message");
  messageDiv.classList.add(role.toLowerCase());

  const roleP = document.createElement("p");
  roleP.classList.add("message-role");
  roleP.textContent = role;

  const textPre = document.createElement("pre");
  textPre.classList.add("message-text");
  textPre.textContent = text;

  messageDiv.appendChild(roleP);
  messageDiv.appendChild(textPre);
  chatWindow.appendChild(messageDiv);

  // Scroll to the bottom
  chatWindow.scrollTop = chatWindow.scrollHeight;
}