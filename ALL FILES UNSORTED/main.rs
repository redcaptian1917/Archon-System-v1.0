// This is the Rust backend for your Tauri app.
// It handles the secure connection to your API gateway.

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// --- Structs for API communication ---
#[derive(Serialize)]
struct CommandPayload {
    command: String,
}

#[derive(Deserialize, Debug)]
struct LoginResponse {
    access_token: String,
    token_type: String,
}

#[derive(Deserialize, Debug)]
struct ApiError {
    detail: String,
}

// --- State Management ---
// This holds the reqwest client and JWT token in a secure state
pub struct AppState(std::sync::Mutex<AppStateInternal>);
pub struct AppStateInternal {
    client: reqwest::Client,
    jwt: Option<String>,
}

// --- Tauri Command: Login ---
// This function is callable from your JavaScript.
// It logs into your API and stores the JWT.
#[tauri::command]
async fn login(
    username: &str,
    password: &str,
    api_onion_url: &str,
    state: tauri::State<'_, AppState>,
) -> Result<String, String> {
    
    // 1. Build the HTTP client with Tor SOCKS proxy
    // This assumes you have Tor running on your local desktop (127.0.0.1:9050)
    let proxy = reqwest::Proxy::all("socks5h://127.0.0.1:9050")
        .map_err(|e| format!("Failed to create proxy: {}", e))?;
    
    let client = reqwest::Client::builder()
        .proxy(proxy)
        .build()
        .map_err(|e| format!("Failed to build client: {}", e))?;

    // 2. Prepare the login form data
    let mut params = HashMap::new();
    params.insert("username", username);
    params.insert("password", password);

    let login_url = format!("http://{}/token", api_onion_url);

    // 3. Send the login request
    let res = client
        .post(&login_url)
        .form(&params)
        .send()
        .await;

    match res {
        Ok(response) => {
            if response.status().is_success() {
                let login_response = response
                    .json::<LoginResponse>()
                    .await
                    .map_err(|e| format!("Failed to parse login response: {}", e))?;
                
                // 4. Store the client and token in our secure state
                let mut app_state = state.0.lock().unwrap();
                app_state.client = client; // Store the client for future use
                app_state.jwt = Some(login_response.access_token);
                
                Ok("Login successful".to_string())
            } else {
                let error_response = response
                    .json::<ApiError>()
                    .await
                    .map_err(|e| format!("Failed to parse error: {}", e))?;
                Err(format!("Login failed: {}", error_response.detail))
            }
        }
        Err(e) => Err(format!("Login request failed: {}. Is your local Tor service running?", e)),
    }
}

// --- Tauri Command: Run Archon Command ---
// This uses the stored JWT to run a command.
#[tauri::command]
async fn run_archon_command(
    command: &str,
    api_onion_url: &str,
    state: tauri::State<'_, AppState>,
) -> Result<String, String> {
    
    let (client, jwt) = {
        let app_state = state.0.lock().unwrap();
        (app_state.client.clone(), app_state.jwt.clone())
    };

    let jwt = match jwt {
        Some(token) => token,
        None => return Err("Not authenticated. Please log in first.".to_string()),
    };

    let command_url = format!("http://{}/command/sync", api_onion_url);

    // Send the command
    let res = client
        .post(&command_url)
        .bearer_auth(jwt)
        .json(&CommandPayload {
            command: command.to_string(),
        })
        .send()
        .await;

    match res {
        Ok(response) => {
            if response.status().is_success() {
                let text_response = response
                    .text()
                    .await
                    .map_err(|e| format!("Failed to read response: {}", e))?;
                Ok(text_response)
            } else {
                let error_text = response.text().await.unwrap_or_default();
                Err(format!("Command failed: {}", error_text))
            }
        }
        Err(e) => Err(format!("Command request failed: {}", e)),
    }
}

fn main() {
    // 1. **(CRITICAL FIX)** We need a non-streaming endpoint for this simple app.
    // Go to 'api_gateway.py' and add a new endpoint:
    // @app.post("/command/sync")
    // async def execute_command_sync(
    //     cmd: CommandRequest,
    //     current_user: Annotated[User, Depends(get_current_admin)]
    // ):
    //     user_id = current_user.user_id
    //     command_str = cmd.command
    //     full_cmd = ["./archon_ceo.py", "--user-id", str(user_id), "--command", command_str]
    //     
    //     # Run as a blocking process and capture all output
    //     result = subprocess.run(full_cmd, capture_output=True, text=True)
    //     
    //     if result.returncode != 0:
    //         return PlainTextResponse(result.stderr, status_code=500)
    //     return PlainTextResponse(result.stdout)
    //
    // 2. You must also add 'asyncio' and 'StreamingResponse' imports:
    // 'from starlette.responses import StreamingResponse, PlainTextResponse'
    // 'import asyncio'

    // 3. Initialize the state
    let proxy = reqwest::Proxy::all("socks5h://127.0.0.1:9050").unwrap();
    let client = reqwest::Client::builder().proxy(proxy).build().unwrap();
    let state = AppState(std::sync::Mutex::new(AppStateInternal {
        client: client,
        jwt: None,
    }));

    tauri::Builder::default()
        .manage(state) // Add the state to Tauri
        .invoke_handler(tauri::generate_handler![login, run_archon_command])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}