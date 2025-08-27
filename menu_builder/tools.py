# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool

# from .sub_agents import retriever_agent
import json
from pathlib import Path
from typing import List
import sys
import os

# This line finds the path to the 'RAG' directory and adds it to the list
# of places Python looks for packages.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from .sub_agents import retriever_agent, qc_agent


async def call_rag_agent(
    question: str,
    tool_context: ToolContext,
):
    """Tool to call RAG agent."""

    agent_tool = AgentTool(agent=retriever_agent)

    agent_output = await agent_tool.run_async(
        args={"request": question}, tool_context=tool_context
    )
    tool_context.state["agent_output"] = agent_output
    return agent_output


async def call_qc_agent(
    question: str,
    tool_context: ToolContext,
):
    """Tool to call QC agent."""

    agent_tool = AgentTool(agent=qc_agent)

    agent_output = await agent_tool.run_async(
        args={"request": question}, tool_context=tool_context
    )
    tool_context.state["agent_output"] = agent_output
    return agent_output


def load_image_list() -> List[str]:
    """
    Finds and lists all image filenames from the 'resources/images'
    directory and returns them as a list.
    """
    try:
        # Get the directory where this script is located (e.g., '.../rag/')
        script_dir = Path(__file__).parent.resolve()

        # Construct the path to the images directory
        image_dir = script_dir / "resources" / "images"

        if not image_dir.exists():
            print(f"❌ Error: The directory '{image_dir}' was not found.")
            return []

        # List all files in the directory and filter for common image extensions
        image_extensions = (".png", ".jpg", ".jpeg", ".webp")
        filenames = [
            f for f in os.listdir(image_dir) if f.lower().endswith(image_extensions)
        ]

        if not filenames:
            print(f"⚠️ Warning: No image files found in '{image_dir}'.")
            return []

        print(f"✅ Successfully found {len(filenames)} images in '{image_dir}'.")
        return filenames

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []


def save_html(html_content: str, base_filename: str) -> str:
    """
    Saves HTML content to a file, automatically incrementing a version number
    to avoid overwriting existing files.

    Args:
        html_content (str): The HTML content to be saved.
        base_filename (str): The desired base name for the file (e.g., 'menu').

    Returns:
        The full path to the newly saved HTML file.
    """
    try:
        script_dir = Path(__file__).parent.resolve()
        output_dir = script_dir / "resources"

        output_dir.mkdir(parents=True, exist_ok=True)

        base_filename = base_filename.removesuffix(".html")

        file_path = output_dir / f"{base_filename}.html"

        if not file_path.exists():
            final_path = file_path
        else:
            version = 2
            while True:
                versioned_path = output_dir / f"{base_filename}_v{version}.html"
                if not versioned_path.exists():
                    final_path = versioned_path
                    break
                version += 1

        with open(final_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"✅ HTML file saved successfully to: {final_path}")
        return str(final_path)

    except Exception as e:
        print(f"❌ An unexpected error occurred while saving the file: {e}")
        return ""


# --- Example of how to run and test the tool ---
if __name__ == "__main__":
    # This block will only run if you execute this script directly
    image_filenames = load_image_list()
    print(image_filenames)
    # if image_filenames:
    #     print("\n--- List of Loaded Image Filenames ---")
    #     for name in image_filenames:
    #         print(name)
