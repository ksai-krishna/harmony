from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama
from dotenv import load_dotenv

import asyncio
import gradio as gr
import os

# Load environment variables
load_dotenv()

# Global variables to reuse across chats
agent = None

async def setup_agent():
    global agent
    if agent is None:
        # Connect to FastMCP server via SSE
        client = MultiServerMCPClient(
            {
                "expense_tracker": {
                    "url": "http://127.0.0.1:8000/sse",
                    "transport": "sse",
                }
            }
        )

        tools = await client.get_tools()
        print("Discovered tools:", [tool.name for tool in tools])

        # Setup Ollama model (make sure it's running)
        model = ChatOllama(model="llama3.2")

        # Create the ReAct agent
        agent = create_react_agent(model, tools, debug=True)

    return agent

async def chat_handler(message, history):
    """Handles user messages from the Gradio chat interface."""
    agent = await setup_agent()

    try:
        response = await agent.ainvoke({
            "messages": [{"role": "user", "content": message}]
        })
        return response['messages'][-1].content
    except Exception as e:
        return f"Error: {str(e)}"

# Create the Gradio ChatInterface
demo = gr.ChatInterface(
    fn=chat_handler,
    title="💰 Expense Tracker Assistant",
    description="Ask questions like:\n- 'What is the current date and time?'\n- 'I spent 500 rupees on dinner on 2024-07-01.'\n- 'Show me my expense history.'\n- 'What did I spend on 2025-07-03?'",
    theme="soft",
)

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()  # Required to run asyncio with Gradio in some environments

    demo.launch()
