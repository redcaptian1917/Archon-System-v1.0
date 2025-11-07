#!/usr/bin/env python3

import sys
import argparse
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# Import the tools this crew needs
from fapc_tools_v22 import (
    comfyui_image_tool,
    text_to_speech_tool,
    web_search_tool,
    learn_fact_tool,
    secure_cli_tool # For FFMPEG
)

# --- 1. Setup Specialist Models ---
ollama_llm = Ollama(model="llama3:8b", base_url="http://ollama:11434")

# --- 2. Define Specialist Agents ---
concept_agent = Agent(
    role="Art Director & Concept Artist",
    goal="Research visual concepts and write detailed, effective prompts for the artists.",
    backstory=(
        "You are a world-class Art Director. You use 'web_search_tool' to "
        "research competitors, color theory, and design trends. You then "
        "write highly descriptive, professional prompts for the "
        "image and audio agents to execute."
    ),
    tools=[web_search_tool],
    llm=ollama_llm,
    verbose=True
)

image_artist_agent = Agent(
    role="AI Image Artist",
    goal="Generate high-quality images using ComfyUI based on prompts.",
    backstory=(
        "You are an AI Artist. You take prompts from the Art Director "
        "and use 'comfyui_image_tool' to generate them. You "
        "must specify a clear output path for each image."
    ),
    tools=[comfyui_image_tool],
    llm=ollama_llm,
    verbose=True
)

audio_engineer_agent = Agent(
    role="Audio Engineer & Sound Designer",
    goal="Generate voice-overs and audio using Coqui-TTS.",
    backstory=(
        "You are an Audio Engineer. You take scripts and use "
        "'text_to_speech_tool' to generate clean, professional "
        "voice-overs. You save the output as .wav files."
    ),
    tools=[text_to_speech_tool],
    llm=ollama_llm,
    verbose=True
)

# --- 3. Main Crew Execution ---
def main():
    parser = argparse.ArgumentParser(description="FAPC Media Synthesis Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level creative task.")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    auth.log_activity(user_id, 'delegate', f"Media Crew activated for: {task_desc}", 'success')

    # Define tasks (This is a simplified example)
    # A real workflow would be more complex and managed by the agent
    
    # Task 1: Generate the concept and prompts
    concept_task = Task(
        description=f"Create a concept for this task: '{task_desc}'. "
                    "Your output must be a JSON object containing: "
                    "1. 'image_prompt' (a detailed SDXL prompt) "
                    "2. 'image_path' (a filename like 'output.png') "
                    "3. 'audio_script' (a script for the voice-over)",
        expected_output="A JSON object with image_prompt, image_path, and audio_script.",
        agent=concept_agent
    )

    # Task 2: Generate the image
    image_task = Task(
        description=(
            "Generate the image. You must parse the 'image_prompt' and "
            "'image_path' from the concept task's output. "
            f"Pass the user_id '{user_id}' to the tool."
        ),
        expected_output="A confirmation of the image saved path.",
        agent=image_artist_agent,
        context=[concept_task]
    )
    
    # Task 3: Generate the audio
    audio_task = Task(
        description=(
            "Generate the voice-over. You must parse the 'audio_script' "
            "from the concept task's output. Save it as 'output.wav'. "
            f"Pass the user_id '{user_id}' to the tool."
        ),
        expected_output="A confirmation of the audio saved path.",
        agent=audio_engineer_agent,
        context=[concept_task]
    )

    media_crew = Crew(
        agents=[concept_agent, image_artist_agent, audio_engineer_agent],
        tasks=[concept_task, image_task, audio_task],
        process=Process.sequential,
        verbose=2
    )
    
    result = media_crew.kickoff()
    print(result)

if __name__ == "__main__":
    main()
```

---

### 5. ⬆️ Upgrade `archon_ceo.py`

Finally, make your Archon agent aware of its new `MediaSynthesisCrew`.

1.  Open `archon_ceo.py`.
2.  Change the import from `fapc_tools_v21` to `fapc_tools_v22`.
3.  Add the new tools (`comfyui_image_tool`, `text_to_speech_tool`) to the import list and the `archon_agent`'s `tools` list.
4.  Update the `master_task` description to include the new **`mediasynthesis_crew`** (note the name change from `creative_crew`).

**New `master_task` description (excerpt):**
```python
    master_task = Task(
        description=(
            f"Execute this high-level command: '{user_command}'.\n"
            "...use the 'delegate_to_crew' tool.\n"
            "You currently have: 'coding_crew', 'cybersecurity_crew', 'business_crew', "
            "'ai_and_research_crew', 'plausiden_crew', 'support_crew', "
            "'purpleteam_crew', 'dfir_crew', 'hardening_crew', 'memory_manager_crew', 'mediasynthesis_crew'.\n" # <-- ADDED
            f"You MUST pass the user_id '{user_id}' to every tool you use."
        ),
        # ... rest of task
    )
```

---

### 6. 🚀 How to Use It

1.  **Make the new crew executable:**
    ```bash
    docker-compose exec archon-app chmod +x mediasynthesis_crew.py
    ```
2.  **Download Models:** You must `docker-compose exec comfyui ...` and `docker-compose exec coqui-tts ...` to download the `sd_xl_base_1.0.safetensors` model and the `tts_models/en/ljspeech/tacotron2-DDC` model into their respective model volumes.
3.  **Run your "Archon" agent with a media synthesis command:**

    ```bash
    docker-compose exec archon-app ./archon_ceo.py "Delegate to the MediaSynthesisCrew: 'Create a simple ad for PlausiDen. The image should be a futuristic, abstract network. The audio should say: PlausiDen. Your privacy, secured.'"