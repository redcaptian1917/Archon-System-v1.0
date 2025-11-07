#!/usr/bin/env python3

import sys
import argparse
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# Import the tools this crew needs from the new v9 file
from fapc_tools_v9 import (
    generate_image_tool,
    web_search_tool # For researching design concepts
)

# --- 1. Setup Specialist Models ---
ollama_llm = Ollama(model="llama3:8b", base_url="http://localhost:11434")

# --- 2. Define Specialist Agents ---

# Agent 1: The Design Concept Generator
design_concept_agent = Agent(
    role="Visual Concept Designer",
    goal="Develop creative and effective visual design concepts, including detailed image generation prompts.",
    backstory=(
        "You are a visionary graphic designer and marketing expert. Your job "
        "is to translate abstract ideas into concrete visual concepts. "
        "You use 'web_search_tool' to research design trends and examples, "
        "then you formulate highly descriptive prompts for the image generator. "
        "You do NOT generate images yourself; you create perfect prompts for them."
    ),
    tools=[web_search_tool],
    llm=ollama_llm,
    verbose=True
)

# Agent 2: The Image Generator
image_artist_agent = Agent(
    role="AI Image Artist",
    goal="Generate high-quality images based on detailed prompts provided by the designer. Save images to specified paths.",
    backstory=(
        "You are an expert AI artist. You take precise, descriptive prompts "
        "from the designer and use the 'generate_image_tool' to create visual "
        "assets. You know how to fine-tune parameters like negative prompts, "
        "steps, and CFG scale to achieve the desired aesthetic. "
        "You always save the generated image to the specified output path."
    ),
    tools=[generate_image_tool],
    llm=ollama_llm,
    verbose=True
)


# --- 3. Main Crew Execution ---
def main():
    parser = argparse.ArgumentParser(description="FAPC Creative Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level creative task.")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    auth.log_activity(user_id, 'delegate', f"Creative Crew activated for: {task_desc}", 'success')

    # Define tasks
    # Task 1: Generate the design concept and prompt
    concept_task = Task(
        description=f"Develop a visual concept and detailed Stable Diffusion prompt for: '{task_desc}'. Include aesthetic, style, and content. Specify a clear output filename like 'logo_final.png'.",
        expected_output="A detailed visual concept description and a precise Stable Diffusion prompt ready for the image generator, including output_path.",
        agent=design_concept_agent
    )

    # Task 2: Generate the image
    generate_task = Task(
        description=(
            "Based on the generated prompt from the concept designer, "
            "use the 'generate_image_tool' to create the image. "
            "Extract the prompt and output_path from the previous task's output. "
            f"You MUST pass the user_id '{user_id}' to the generate_image_tool."
        ),
        expected_output="Confirmation that the image was generated and saved to the specified path.",
        agent=image_artist_agent,
        context=[concept_task] # The image artist depends on the concept designer
    )

    creative_crew = Crew(
        agents=[design_concept_agent, image_artist_agent],
        tasks=[concept_task, generate_task],
        process=Process.sequential,
        verbose=2
    )
    
    result = creative_crew.kickoff()
    print(result) # Print result to stdout for "Archon"

if __name__ == "__main__":
    main()