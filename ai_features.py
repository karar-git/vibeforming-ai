import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY environment variable is not set")

client = genai.Client(api_key=GOOGLE_API_KEY)


class ChatBot:
    """Chatbot with web search capability using Gemini."""

    def __init__(self, model: str = "gemini-2.5-flash"):
        self.model = model
        self.system_prompt = "You are a helpful assistant that can search the web to answer questions. Provide accurate, up-to-date information."
        self.history = []

        self.grounding_tool = types.Tool(google_search=types.GoogleSearch())
        self.config = types.GenerateContentConfig(
            system_instruction=self.system_prompt, tools=[self.grounding_tool]
        )

    def chat(self, user_message: str) -> dict:
        """Send a message and get a response with web search enabled."""
        self.history.append(
            types.Content(role="user", parts=[types.Part(text=user_message)])
        )

        response = client.models.generate_content(
            model=self.model,
            contents=self.history,
            config=self.config,
        )

        assistant_text = response.text
        self.history.append(
            types.Content(role="model", parts=[types.Part(text=assistant_text)])
        )

        # Extract grounding metadata (search queries and sources)
        search_queries = []
        sources = []

        if response.candidates and response.candidates[0].grounding_metadata:
            metadata = response.candidates[0].grounding_metadata

            # Get search queries
            if metadata.web_search_queries:
                search_queries = list(metadata.web_search_queries)

            # Get sources from grounding chunks
            if metadata.grounding_chunks:
                for chunk in metadata.grounding_chunks:
                    if chunk.web:
                        sources.append({"title": chunk.web.title, "url": chunk.web.uri})

        return {
            "text": assistant_text,
            "search_queries": search_queries,
            "sources": sources,
        }

    def get_history(self) -> list:
        """Return conversation history in simple format."""
        messages = []
        for content in self.history:
            role = "user" if content.role == "user" else "assistant"
            text = content.parts[0].text if content.parts else ""
            messages.append({"role": role, "text": text})
        return messages

    def reset(self):
        """Clear conversation history."""
        self.history = []
