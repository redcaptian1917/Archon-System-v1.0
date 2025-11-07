#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - MEDIA SYNTHESIS CREW (vFINAL)
#
# This is the specialist "Media Factory" & "Creative Department".
# It is called by the `archon_ceo` agent via `delegate_to_crew`.
#
# Its purpose is to:
# 1. (VisualConceptAgent) Research and design visual/audio concepts.
# 2. (ImageArtistAgent) Generate images using ComfyUI.
# 3. (AudioEngineerAgent) Generate speech using Coqui-TTS.
# 4. (VideoArtistAgent) Generate video clips (future).
# -----------------------------------------------------------------

import sys
import argparse
import json
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# --- Internal Imports ---
# Import the tools this crew needs from the master "Armory"
try:
    from fapc_tools import (
        comfyui_image_tool,
        text_to_speech_tool,
        web_search_tool,
        learn_fact_tool,
        recall_facts_tool,
        secure_cli_tool # For FFMPEG tasks
    )
except ImportError:
    print("CRITICAL: fapc_tools.py not found.", file=sys.stderr)
    sys.exit(1)

# ---
# 1. SPECIALIST MODEL SETUP
# ---
try:
    # A general-purpose model is perfect for these creative tasks
    ollama_llm = Ollama(model="llama3:8b", base_url="http://ollama:11434")
    ollama_llm.invoke("Test") # Test connection
except Exception as e:
    print(f"[Media Crew ERROR] Could not connect to Ollama: {e}", file=sys.stderr)
    sys.exit(1)

# ---
# 2. SPECIALIST AGENT DEFINITIONS
# ---

# Agent 1: The Art Director
concept_agent = Agent(
    role="Art Director & Concept Artist",
    goal="Research visual/audio concepts and write detailed, effective prompts for the specialist artists and engineers to execute.",
    backstory=(
        "You are a visionary Art Director for the Archon corporation. "
        "Your job is to translate a high-level command (e.g., 'make an ad') "
        "into a concrete, multi-step execution plan. "
        "You use 'web_search_tool' to research design trends, color palettes, "
        "and competitor styles. You then write the *exact* prompts for the "
        "Image, Video, and Audio agents. Your final plan is a JSON object "
        "that the other agents will parse."
    ),
    tools=[web_search_tool, recall_facts_tool],
    llm=ollama_llm,
    verbose=True
)

# Agent 2: The Image Artist
image_artist_agent = Agent(
    role="AI Image Artist (Illustrator)",
    goal="Generate high-quality images using ComfyUI based on prompts from the Art Director.",
    backstory=(
        "You are an AI Artist. You are a master of Stable Diffusion and ComfyUI. "
        "You take a precise prompt from the Art Director and use the "
        "'comfyui_image_tool' to generate the image. You "
        "must specify a clear output path for each image (e.g., 'logo_v1.png')."
    ),
    tools=[comfyui_image_tool],
    llm=ollama_llm,
    verbose=True
)

# Agent 3: The Audio Engineer
audio_engineer_agent = Agent(
    role="Audio Engineer & Sound Designer",
    goal="Generate voice-overs and audio using Coqui-TTS and other audio tools.",
    backstory=(
        "You are an Audio Engineer. You are a master of the 'text_to_speech_tool'. "
        "You take scripts from the Art Director and generate clean, professional "
        "voice-overs. You can also use 'secure_cli_tool' to run 'ffmpeg' "
        "to combine audio tracks or add sound effects (which you will find using 'web_search_tool')."
    ),
    tools=[text_to_speech_tool, web_search_tool, secure_cli_tool],
    llm=ollama_llm,
    verbose=True
)

# Agent 4: The Video Artist (Future Expansion)
# video_artist_agent = Agent(
#     role="AI Video Artist (Animator)",
#     goal="Generate short video clips using Stable Video Diffusion.",
#     backstory=(
#         "You are an Animator. You take a still image from the Image Artist "
#         "and use a (future) 'comfyui_video_tool' to add motion to it."
#     ),
#     tools=[], # e.g., comfyui_video_tool
#     llm=ollama_llm,
#     verbose=True
# )

# ---
# 3. MAIN CREW EXECUTION
# ---
def main():
    # 1. Parse arguments passed from the CEO
    parser = argparse.ArgumentParser(description="FAPC Media Synthesis Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level creative task.")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    # 2. Log the delegation
    auth.log_activity(user_id, 'delegate_media_crew', f"Media Crew activated for: {task_desc}", 'success')

    # 3. Define the tasks
    
    # Task 1: The Art Director creates the master plan
    concept_task = Task(
        description=(
            f"Create a complete, multi-step media plan for this request: '{task_desc}'.\n"
            "You must: \n"
            "1. Research the concept using 'web_search_tool' if needed.\n"
            "2. Formulate a detailed plan.\n"
            "3. Your final output MUST be a JSON object containing the exact "
            "   prompts and parameters for the other agents, e.g.:\n"
            "   {\n"
            "     \"image_prompt\": \"A futuristic logo for PlausiDen...\",\n"
            "     \"image_negative_prompt\": \"blurry, text, watermark\",\n"
            "     \"image_output_path\": \"plausiden_logo_v1.png\",\n"
            "     \"audio_script\": \"PlausiDen. Your privacy, secured.\",\n"
            "     \"audio_output_path\": \"plausiden_vo_v1.wav\"\n"
            "   }\n"
            f"You MUST pass the user_id '{user_id}' to all tools."
        ),
        expected_output="A single JSON object containing the 'image_prompt', 'image_output_path', 'audio_script', and 'audio_output_path'.",
        agent=concept_agent
    )

    # Task 2: The Image Artist executes their part
    image_task = Task(
        description=(
            "Execute the image generation part of the plan. "
            "You must parse the JSON output from the 'Art Director' to get the "
            "'image_prompt', 'image_negative_prompt', and 'image_output_path'. "
            "Then, call the 'comfyui_image_tool' with these exact parameters.\n"
            f"You MUST pass the user_id '{user_id}' to the tool."
        ),
        expected_output="A confirmation that the image was generated and saved to the specified path.",
        agent=image_artist_agent,
        context=[concept_task] # This pipes the output of Task 1 to Task 2
    )

    # Task 3: The Audio Engineer executes their part
    audio_task = Task(
        description=(
            "Execute the audio generation part of the plan. "
            "You must parse the JSON output from the 'Art Director' to get the "
            "'audio_script' and 'audio_output_path'. "
            "Then, call the 'text_to_speech_tool' with these exact parameters.\n"
            f"You MUST pass the user_id '{user_id}' to the tool."
        ),
        expected_output="A confirmation that the audio file was generated and saved to the specified path.",
        agent=audio_engineer_agent,
        context=[concept_task] # This also depends on the plan
    )
    
    # 4. Assemble and run the crew
    media_crew = Crew(
        agents=[concept_agent, image_artist_agent, audio_engineer_agent],
        tasks=[concept_task, image_task, audio_task],
        # Sequential: Plan -> Image -> Audio
        process=Process.sequential,
        verbose=2
    )
    
    result = media_crew.kickoff()
    
    # 5. Print the final result to stdout
    # The `archon_ceo` agent will read this output.
    print(f"\n--- Media Synthesis Crew Task Complete ---")
    print(result)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"CRITICAL CREW FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
