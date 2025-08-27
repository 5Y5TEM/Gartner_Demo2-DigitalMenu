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

import fitz  # From the PyMuPDF library
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from google import genai
import os
import re
import json
from pathlib import Path
from dotenv import load_dotenv

# This block finds and loads your .env file from the project root (RAG/)
try:
    project_root = Path(__file__).resolve().parents[3]
    dotenv_path = project_root / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path)
        print("✅ Successfully loaded credentials from .env file.")
    else:
        print(
            "⚠️ .env file not found at project root. Relying on shell environment variables."
        )
except IndexError:
    print("⚠️ Could not determine project root. Relying on shell environment variables.")


def extract_images_from_pdf(pdf_filename: str):
    """
    Parses a PDF from the 'agent/resources/' folder, determines its path
    relative to this script's location, and saves images to
    'agent/resources/images/'.

    Args:
        pdf_filename (str): The name of the PDF file (e.g., 'my_document.pdf').
    """
    try:
        # 1. Determine the correct paths relative to this script's location
        # Path to the current file (tools.py)
        current_file_path = Path(__file__)
        # Navigate up three levels to get to the 'agent/' directory
        agent_root_dir = current_file_path.resolve().parents[2]

        # Define the resource and output directories based on the agent root
        resource_dir = agent_root_dir / "resources"
        output_dir = resource_dir / "images"
        pdf_path = resource_dir / pdf_filename

        # 2. Check if the source PDF file exists
        if not pdf_path.exists():
            print(f"❌ Error: The file '{pdf_path}' was not found.")
            return

        # 3. Create the output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ Output directory is '{output_dir}'.")

        # Open the PDF
        doc = fitz.open(pdf_path)
        image_count = 0
        print(f"📄 Processing '{pdf_filename}'...")

        # Iterate through each page of the PDF
        for page_index in range(len(doc)):
            page = doc.load_page(page_index)
            image_list = page.get_images(full=True)

            if image_list:
                print(f"🔎 Found {len(image_list)} images on page {page_index + 1}")

            # Iterate through all images on the current page
            for image_index, img in enumerate(image_list, start=1):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                # Define a unique, descriptive filename
                image_filename = f"image_p{page_index + 1}_i{image_index}.{image_ext}"
                image_filepath = output_dir / image_filename

                # Save the image to the output directory
                with open(image_filepath, "wb") as img_file:
                    img_file.write(image_bytes)

                image_count += 1

        print(f"\n🎉 **Extraction Complete!**")
        print(f"Total images saved: {image_count}")
        print(f"Images are located in: '{output_dir}'")

        doc.close()

    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def sanitize_filename(name: str) -> str:
    """Removes special characters to create a valid filename."""
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\s-]", "", name)
    name = re.sub(r"[\s-]+", "_", name)
    return name


def analyze_and_rename_images_vertex_ai(project_id: str, location: str):
    """
    Analyzes images using the Vertex AI SDK with GCP authentication.
    """
    try:
        vertexai.init(project=project_id, location=location)
        print(f"✅ Vertex AI initialized for project '{project_id}' in '{location}'.")

        current_file_path = Path(__file__)
        agent_root_dir = current_file_path.resolve().parents[2]
        image_dir = agent_root_dir / "resources" / "images"
        json_output_path = agent_root_dir / "resources" / "image_descriptions.json"

        if not image_dir.exists():
            print(f"❌ Error: Directory '{image_dir}' not found.")
            return

        model = GenerativeModel("gemini-2.5-flash")

        generic_image_pattern = re.compile(r"^image_p\d+_i\d+\..+$")
        files_to_process = [
            f for f in os.listdir(image_dir) if generic_image_pattern.match(f)
        ]

        if not files_to_process:
            print("✅ No new images to process.")
            return

        print(f"🔎 Found {len(files_to_process)} new images to analyze.")

        image_descriptions = {}
        for filename in files_to_process:
            original_path = image_dir / filename
            print(f"\nAnalyzing '{filename}'...")

            try:
                # --- THIS BLOCK IS NOW CORRECTED AND MORE ROBUST ---
                extension = original_path.suffix.lower()
                # The keys in this dictionary now correctly match the extension without the dot
                mime_type_map = {
                    "png": "image/png",
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                    "webp": "image/webp",
                }
                # We look up the extension *without* the leading dot
                mime_type = mime_type_map.get(extension[1:])

                # Safety Check: If the mime_type is not found, skip the file.
                if not mime_type:
                    print(
                        f"⚠️ Skipping '{filename}' due to unsupported file type: {extension}"
                    )
                    continue
                # --- END OF CORRECTION ---

                with open(original_path, "rb") as f:
                    image_bytes = f.read()

                image_part = Part.from_data(data=image_bytes, mime_type=mime_type)

                prompt = """
                You are a file naming expert. Analyze this image of a restaurant dish.
                Provide a JSON object with:
                1. "filename": A short, descriptive, URL-friendly name for the file, without the extension.
                """

                response = model.generate_content([prompt, image_part])
                response_text = (
                    response.text.strip().replace("```json", "").replace("```", "")
                )
                data = json.loads(response_text)
                new_name_base = sanitize_filename(data["filename"])
                new_filename = f"{new_name_base}{extension}"
                new_path = image_dir / new_filename

                os.rename(original_path, new_path)
                print(f"✅ Renamed to '{new_filename}'")
                image_descriptions[new_filename] = data["description"]

            except Exception as e:
                print(f"❌ Failed to process '{filename}': {e}")

        if image_descriptions:
            with open(json_output_path, "w") as f:
                json.dump(image_descriptions, f, indent=4)
            print(
                f"\n🎉 **Analysis Complete!** Descriptions saved to '{json_output_path}'"
            )
        else:
            print("\n⚠️ No images were successfully processed.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    # pdf_to_process = "demo1_output.pdf"
    # extract_images_from_pdf(pdf_to_process)

    gcp_project = os.getenv("GOOGLE_CLOUD_PROJECT")
    gcp_location = os.getenv("GOOGLE_CLOUD_LOCATION")

    if gcp_project and gcp_location:
        analyze_and_rename_images_vertex_ai(
            project_id=gcp_project, location=gcp_location
        )
    else:
        print(
            "🛑 Error: Could not find GOOGLE_CLOUD_PROJECT and/or GOOGLE_CLOUD_LOCATION in your .env file or environment."
        )
