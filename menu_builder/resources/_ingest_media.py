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

import os
import re
from pathlib import Path
from typing import List, Dict, Any
import json

# PDF and Document Handling
import fitz  # PyMuPDF
from weasyprint import HTML

# Google Cloud Vertex AI
import vertexai
from vertexai.generative_models import GenerativeModel

# Environment Loading
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GCP_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")

CWD = Path(__file__).parent
IMAGE_DIR = CWD / "images"
PDF_INPUT_PATH = (
    CWD / "Strategic Plan for a New Restaurant at Fisherman's Wharf, San Francisco.pdf"
)
FINAL_OUTPUT_PATH = CWD / "The_Anchor_And_Olive_Visual_Menu_v3_Gemini"


# --- PIPELINE STEP 1: Gather Inputs ---
def get_source_data(pdf_path: Path, image_dir: Path) -> (List[str], List[str]):
    """Extracts all text from the PDF and gets all image filenames."""
    # Extract all text, page by page
    doc = fitz.open(pdf_path)
    all_pages_text = [page.get_text() for page in doc]
    print(f"✅ Gathered text from {len(all_pages_text)} pages.")

    # Get all image filenames from the resources/images directory
    image_filenames = [
        f for f in os.listdir(image_dir) if f.endswith((".png", ".jpg", ".jpeg"))
    ]
    print(f"✅ Found {len(image_filenames)} generated images.")

    return all_pages_text, image_filenames


# --- PIPELINE STEP 2: Reconstruct Document using Gemini 2.5 Pro ---
def reconstruct_html_with_gemini(
    all_pages_text: List[str], image_filenames: List[str]
) -> str:
    """Uses Gemini to reconstruct the document with images embedded."""

    # Using a powerful model capable of handling large context and instruction
    model = GenerativeModel("gemini-1.5-pro-001")

    images_list_str = "\n".join(f"- {name}" for name in image_filenames)
    pages_text_str = ""
    for i, text in enumerate(all_pages_text):
        pages_text_str += (
            f"\n\n--- START OF PAGE {i+1} ---\n{text}\n--- END OF PAGE {i+1} ---"
        )

    # --- PROMPT CORRECTION IS HERE ---
    prompt = f"""
    You are an expert document layout specialist and a web developer.
    Your task is to reconstruct a multi-page document as a single, well-formatted HTML file.

    You will be given the full text content of the original document, separated by page markers, and a list of image filenames. The filenames are descriptive of the menu items they represent.

    **INSTRUCTIONS:**
    1.  Read through the original document text.
    2.  When you encounter a menu item in the "Detailed Menu Plan" section that clearly matches an image filename from the provided list, you **must** insert the corresponding image directly after that item's description.
    3.  **CRITICAL PATH INSTRUCTION: All image src paths MUST be relative and use the format `images/FILENAME.png`. Do NOT include any other parent folders.**
    4.  Use appropriate HTML tags for structure (e.g., `<h1>`, `<h2>`, `<p>`, `<ul>`, `<li>`).
    5.  Preserve the overall structure and content of the original document.
    6.  Your final output must be a single, complete HTML code block, starting with `<!DOCTYPE html>` and ending with `</html>`. Do not add any commentary before or after the code.

    **IMAGE FILENAMES AVAILABLE:**
    {images_list_str}

    **ORIGINAL DOCUMENT TEXT:**
    {pages_text_str}
    """

    print("🧠 Sending document context and image list to Gemini for reconstruction...")
    response = model.generate_content(prompt)

    # Clean the response to ensure it's just the HTML
    html_output = response.text.strip().replace("```html", "").replace("```", "")

    print("✅ Step 2: Received reconstructed HTML from Gemini.")
    return html_output


# --- PIPELINE STEP 3: Save HTML to File ---
def save_html_file(html_content: str, output_path: Path):
    """Saves a string of HTML content to a file."""
    print("💾 Saving generated HTML to file...")
    try:
        with open(output_path + ".html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"✅ Step 3: Successfully saved final HTML to '{output_path+'.html'}'.")
    except Exception as e:
        print(f"❌ Failed during HTML save: {e}")


# --- PIPELINE STEP 4: Convert HTML to PDF ---
def convert_html_to_pdf(html_content: str, output_path: Path):
    """Converts a string of HTML content to a PDF file."""
    print("📄 Converting generated HTML to PDF...")
    try:
        HTML(string=html_content, base_url=str(CWD)).write_pdf(output_path + ".pdf")
        print(f"✅ Step 4: Successfully saved final PDF to '{output_path+'.pdf'}'.")
    except Exception as e:
        print(f"❌ Failed during PDF conversion: {e}")


# --- MAIN PIPELINE ORCHESTRATOR ---
def main():
    """Runs the full pipeline."""
    print("🚀 Starting AI Document Reconstruction Pipeline...")

    vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)

    # Step 1: Get all the necessary inputs
    all_pages_text, image_filenames = get_source_data(PDF_INPUT_PATH, IMAGE_DIR)

    # Step 2: Let Gemini do the heavy lifting of reconstruction
    reconstructed_html = reconstruct_html_with_gemini(all_pages_text, image_filenames)

    # Step 3: Save the final HTML to a file
    save_html_file(reconstructed_html, FINAL_OUTPUT_PATH)

    # # Step 4: Convert the final HTML to a PDF
    # convert_html_to_pdf(reconstructed_html, FINAL_OUTPUT_PATH)

    print("🎉 Pipeline finished successfully!")


if __name__ == "__main__":
    if not GCP_PROJECT:
        print("🛑 Error: GOOGLE_CLOUD_PROJECT not found in .env file or environment.")
    else:
        # Use the correct DYLD path for WeasyPrint on macOS
        DYLD_PATH = f"DYLD_FALLBACK_LIBRARY_PATH=$(brew --prefix)/lib"
        print(f"Running main pipeline... (This may take several minutes)")
        main()
