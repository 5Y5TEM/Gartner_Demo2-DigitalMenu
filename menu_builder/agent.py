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

from google.adk.agents import Agent
from dotenv import load_dotenv
from .prompts import return_instructions_root
from .tools import load_image_list, save_html, call_rag_agent, call_qc_agent

load_dotenv()


# --- Example Agent using a Llama 3 model deployed from Model Garden ---

# Replace with your actual Vertex AI Endpoint resource name
llama3_endpoint = "projects/msubasioglu-genai-sa/locations/us-central1/endpoints/YOUR_LLAMA3_ENDPOINT_ID"


root_agent = Agent(
    model="gemini-2.5-flash",
    # model=llama3_endpoint,
    name="frontend_builder_agent",
    instruction=return_instructions_root(),
    tools=[call_rag_agent, call_qc_agent, load_image_list, save_html],
)
