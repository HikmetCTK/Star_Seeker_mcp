import os
import sys
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
import re 
import time
import sys
# Import local project logic
from config import get_data_dir, logger, get_default_model
from server import _fetch_stars_impl as fetch_stars_tool, _search_stars_impl as search_stars_tool

load_dotenv()
gemini_clients = {}
chat_sessions = {}
# Initialize DATA_DIR
DATA_DIR = get_data_dir()
DEFAULT_MODEL = get_default_model()
def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment.")
        sys.exit(1)
    return genai.Client(api_key=api_key)

# Session management for Gradio

def get_chat_session(session_id="default"):
    
    if session_id in chat_sessions:
        logger.info(f"[Gemini] Reusing existing chat session: {session_id}")
        return chat_sessions[session_id]
    
    logger.info(f"[Gemini] Creating new client & chat for session: {session_id}")

    # 🚨 ALWAYS create a NEW client
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    gemini_clients[session_id] = client

    tools = [fetch_stars_tool, search_stars_tool]

    config = types.GenerateContentConfig(
        tools=tools,
        system_instruction="""
        You are the GitHub Stars Intelligence Agent, powered by Google Gemini.
        Your goal is to help users manage, search, and discover repositories from their starred repositories
        .

        IMPORTANT:
        - Always use tools for data access
        - Never  predicts user github name
        """
    )

    chat_sessions[session_id] = client.chats.create(
        model=DEFAULT_MODEL,
        config=config
    )

    return chat_sessions[session_id]


def chat_with_agent(message, history):
    """Robust chat function for Gradio with full client reset handling."""
    import time
    import re

    if not message or not message.strip():
        return "⚠️ Please enter a message."

    session_id = "gradio_user"
    retries = 3

    while retries > 0:
        try:
            chat = get_chat_session(session_id)
            response = chat.send_message(message)

            response_text = response.text

            # 🔥 Fallback: Gemini sometimes returns text only in parts
            if not response_text:
                if hasattr(response, "candidates") and response.candidates:
                    parts = response.candidates[0].content.parts
                    text_parts = [
                        p.text for p in parts
                        if hasattr(p, "text") and p.text
                    ]
                    response_text = " ".join(text_parts)

            if not response_text or response_text.strip() == "":
                return "✅ Operation completed. What would you like to do next?"

            return response_text

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Gradio Chat Error: {error_msg}")

            # 🧨 CLIENT CLOSED — ROOT CAUSE
            if "client has been closed" in error_msg.lower():
                logger.warning("Gemini client closed. Resetting client & chat.")
                chat_sessions.pop(session_id, None)
                gemini_clients.pop(session_id, None)
                retries -= 1
                continue

            # 🚦 QUOTA / RATE LIMIT
            if "429" in error_msg or "quota" in error_msg.lower():
                match = re.search(r"retry in (\d+\.?\d*)s", error_msg)
                delay = float(match.group(1)) if match else 30.0

                if retries > 1:
                    logger.warning(f"Quota hit. Retrying in {delay}s...")
                    time.sleep(delay + 1)
                    retries -= 1
                    continue
                else:
                    return "⚠️ API quota exceeded. Please try later."

            # 🔄 SESSION INVALID
            if "400" in error_msg or "expired" in error_msg.lower():
                logger.warning("Session expired. Resetting.")
                chat_sessions.pop(session_id, None)
                gemini_clients.pop(session_id, None)
                return "🔄 Session reset. Please resend your message."

            return f"❌ Unexpected error: {error_msg}"

    return "❌ Max retries reached. Please check your API usage limits."


def github_star_agent():
    """
    A standalone agent that uses the Google Gen AI SDK to manage GitHub stars.
    It can fetch stars for a user and search through them semantically.
    """
    client = get_gemini_client()
    
    # Define the tools available to the agent
    tools = [fetch_stars_tool, search_stars_tool]
    
    # Configuration for the agent
    config = types.GenerateContentConfig(
        tools=tools,
        system_instruction="""
        You are the GitHub Stars Intelligence Agent, powered by Google Gemini.
        Your goal is to help users manage, search, and discover repositories from their stars.

        CORE TOOLS:
        1. fetch_stars_tool: Call this to refresh or initial index a user's starred repos.
        2. search_stars_tool: Call this to perform semantic/Hybrid search through indexed stars.

        IMPORTANT - CRITICAL GUIDELINES:
        - NEVER try to read local file paths (like .json files) directly using your own reasoning. 
        - You MUST use 'search_stars_tool' for all information retrieval tasks.
        - If you haven't searched yet, DO NOT guess or assume what is in the user's stars.
        - If the username is unknown, ask for it immediately.
        - You cannot "see" the raw data files; you only see what the tools return.
        """
    )

    print("--- StarSeeker Agent Playground ---")
    print("Type 'exit' to quit.\n")

    chat = client.chats.create(model=DEFAULT_MODEL, config=config)

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        import time
        retries = 3
        while retries > 0:
            try:
                response = chat.send_message(user_input)
                response_text = response.text
                
                if not response_text:
                    try:
                        if hasattr(response, 'candidates') and response.candidates:
                            parts = response.candidates[0].content.parts
                            text_parts = [p.text for p in parts if hasattr(p, 'text') and p.text]
                            response_text = " ".join(text_parts) if text_parts else None
                    except (AttributeError, IndexError, TypeError):
                        pass
                
                if not response_text or response_text.strip() == "":
                    response_text = "I've completed the requested operation. What would you like to do next?"
                
                print("-" * 100)
                print(f"\nAGENT RESPONSE: {response_text}\n")
                print("-" * 100)
                break
                
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    import re
                    match = re.search(r"retry in (\d+\.?\d*)s", str(e))
                    delay = float(match.group(1)) if match else 30.0
                    print(f"\n[Quota exceeded, waiting {delay}s before retrying... {retries} retries left]")
                    time.sleep(delay + 1)
                    retries -= 1
                else:
                    print(f"\nAn error occurred: {e}\n")
                    break
        
        if retries == 0:
            print("\nMax retries reached. Please check your API usage limits.\n")

def launch_gradio_interface():
    """Launch the Gradio web interface using the simple ChatInterface."""
    import gradio as gr
    
    def predict(message, history):
        # We use the existing chat_with_agent logic but adapt for ChatInterface
        return chat_with_agent(message, history)

    demo = gr.ChatInterface(
        fn=predict,
        title="🚀 StarSeeker Agent Playground",
        description="Powered by Google Gemini. Fetch and search your GitHub stars with ease.",
        
        examples=[" github name : HikmetCTK I want to create fitness app for android  ", "github name : HikmetCTK find me a good web for ocr and pdf reader", ]
    )
    
    print("Launching Gradio at http://127.0.0.1:8080")
    demo.launch(server_name="0.0.0.0", server_port=8080, share=False)

if __name__ == "__main__":

    
    # Check if --cli flag is passed for command-line interface
    if "--cli" in sys.argv or "-c" in sys.argv:
        github_star_agent()
    else:
        # Default: launch Gradio interface
        launch_gradio_interface()
