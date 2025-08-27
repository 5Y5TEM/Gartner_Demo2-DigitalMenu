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
import base64
import json

# PDF and Document Handling
import fitz  # PyMuPDF
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

# Google Cloud Vertex AI
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from vertexai.vision_models import ImageGenerationModel

# Environment Loading
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GCP_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")

# Define file paths
CWD = Path(__file__).parent
IMAGE_OUTPUT_DIR = CWD / "images"
PDF_INPUT_PATH = (
    CWD / "Strategic Plan for a New Restaurant at Fisherman's Wharf, San Francisco.pdf"
)
FINAL_OUTPUT_PATH = CWD / "The_Anchor_And_Olive_Visual_Menu.pdf"
JSON_OUTPUT_PATH = CWD / "media_prompts.json"

# Create necessary directories
IMAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_filename(name: str) -> str:
    """Removes special characters to create a valid filename."""
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\s-]", "", name)
    name = re.sub(r"[\s-]+", "_", name)
    return name


# --- PIPELINE STEP 1: Ingest PDF and Extract Text ---
def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extracts all text from the PDF."""
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    print("✅ Step 1: Successfully extracted text from PDF.")
    return full_text


# --- PIPELINE STEP 2: Generate All Media Prompts using an LLM ---
def generate_all_media_prompts(full_text: str) -> Dict[str, Any]:
    """Uses a Gemini model to analyze the full document and create prompts for
    images (dishes, logo, interior) and videos (promo video).
    """

    model = GenerativeModel("gemini-2.5-flash")

    prompt = f"""
    You are a creative director and a marketing strategist. Analyze the following
    strategic plan for a new restaurant, "The Anchor & Olive," at Fisherman's Wharf,
    San Francisco. Your task is to extract every specific media asset mentioned
    and generate a detailed, photorealistic, or cinematic prompt for each one.

    CRITICAL INSTRUCTIONS:
    1.  **Image Prompts:**
        * Find all dishes from the "Small Plates & Mezze", "Salads & Bowls", "Main Courses",
            and "Desserts" sections.
        * Find the "Brand Logo" concept described in section 10.
        * Find the "Signature Dish - Seafood Cioppino" mock-up described in section 11.
        * Find the "Key Interior Design Element - Central Bar" mock-up from section 11.
        * For each image prompt, include specific details about lighting,
            composition, and ambiance based on the document's descriptions
            (e.g., dark plate, vibrant colors, rustic feel, refined design).
        * Do NOT include descriptions for dishes you cannot find.
        * The prompt must be for photorealistic image generation.

    2.  **Video Prompts:**
        * Find the "Promotional Video Concept" from section 12.
        * Create a single, detailed video prompt that summarizes the entire
            storyboard, from the opening drone shot to the final logo reveal.
        * Describe the scene changes, the key visuals (e.g., golden hour, fresh
            ingredients, cooking action, happy diners), and the overall tone.
        * The prompt must be for a cinematic video generation model.

    3.  **Output Format:**
        * Output ONLY a single valid JSON object.
        * The object must contain two keys: `"images"` (a list of image prompts)
            and `"videos"` (a list of video prompts).
        * Each item in the `"images"` list must be an object with
            `"asset_name"`, `"asset_type"`, and `"prompt"`.
        * Each item in the `"videos"` list must be an object with
            `"asset_name"` and `"prompt"`.

    STRATEGIC PLAN TO ANALYZE:
    ---
    {full_text}
    ---
    """

    print("🔎 Step 2: Analyzing strategic plan to generate media prompts...")
    response = model.generate_content(prompt)
    cleaned_json = response.text.strip().replace("```json", "").replace("```", "")
    media_assets = json.loads(cleaned_json)

    # Save the generated JSON to a file
    with open(JSON_OUTPUT_PATH, "w") as f:
        json.dump(media_assets, f, indent=2)

    print(f"✅ Step 2: Generated and saved media prompts to '{JSON_OUTPUT_PATH}'.")
    return media_assets


# --- PIPELINE STEP 3 & 4: Generate and Save Media Assets ---
def generate_media_assets(media_prompts: Dict[str, Any]):
    """Iterates through the media prompts and generates images and videos."""

    # Image Generation
    if "images" in media_prompts and media_prompts["images"]:
        image_model = ImageGenerationModel.from_pretrained("imagegeneration@006")
        print("\n🎨 Generating Image Assets...")
        for asset in media_prompts["images"]:
            asset_name = asset["asset_name"]
            prompt = asset["prompt"]

            print(f"   -> Generating image for: {asset_name}")
            try:
                response = image_model.generate_images(
                    prompt=prompt, number_of_images=1
                )
                image = response.images[0]
                filename_base = sanitize_filename(asset_name)
                image_filename = f"{filename_base}.png"
                image_filepath = IMAGE_OUTPUT_DIR / image_filename

                # Write the bytes to a file
                with open(image_filepath, "wb") as f:
                    f.write(image._image_bytes)

                print(f"   ✅ Saved '{asset_name}' image to '{image_filepath}'.")

            except Exception as e:
                print(f"   ❌ Could not generate image for '{asset_name}': {e}")
    else:
        print("\n🖼️ No image assets to generate.")

    # Video Generation (Placeholder)
    if "videos" in media_prompts and media_prompts["videos"]:
        print("\n🎬 Generating Video Assets (Simulation)...")
        for video_asset in media_prompts["videos"]:
            asset_name = video_asset["asset_name"]
            prompt = video_asset["prompt"]
            print(f"   -> Simulating video generation for: {asset_name}")
            print(f"   Prompt: '{prompt[:75]}...'")
            print("   (Video generation tool not available in this environment.)")
    else:
        print("\n🎥 No video assets to generate.")


# --- MAIN PIPELINE ORCHESTRATOR ---
def main():
    """Runs the full pipeline from PDF ingestion to final visual document."""
    print("🚀 Starting AI Visual Asset Generation Pipeline...")

    # Initialize Vertex AI
    vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)

    # Step 1: Extract text from the PDF
    full_text = extract_text_from_pdf(PDF_INPUT_PATH)

    # Step 2: Generate JSON of media prompts
    media_prompts = generate_all_media_prompts(full_text)

    # Step 3 & 4: Generate and save media assets based on the JSON
    generate_media_assets(media_prompts)

    print("\n🎉 Pipeline finished successfully!")


if __name__ == "__main__":
    if not GCP_PROJECT:
        print("🛑 Error: GOOGLE_CLOUD_PROJECT not found in .env file or environment.")
    else:
        main()
