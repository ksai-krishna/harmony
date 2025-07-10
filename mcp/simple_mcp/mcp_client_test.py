from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama

from dotenv import load_dotenv
load_dotenv()

import asyncio
import os

async def main():
    # Configure the MultiServerMCPClient to connect to your FastMCP server
    # running on SSE at the confirmed /sse endpoint.
    client = MultiServerMCPClient(
        {
            "expense_tracker": {
                "url": "http://127.0.0.1:8000/sse",  # Confirmed SSE endpoint
                "transport": "sse",
            }
        }
    )

    # We no longer need GROQ_API_KEY for Ollama, so this line can be removed or commented out.
    # os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

    # Get tools from the connected client
    tools = await client.get_tools()
    print("Discovered tools:", [tool.name for tool in tools])

    # Initialize the ChatOllama model
    # Make sure Ollama is running and 'llama3.2' model is pulled.
    model = ChatOllama(model="llama3.2") # Using Ollama with llama3.2
    
    # Create a ReAct agent with the model and tools
    agent = create_react_agent(
        model, tools,
        debug=True
    )

    print("\n--- Testing get_time tool ---")
    time_response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "What is the current date and time?"}]}
    )
    print("Time response:", time_response['messages'][-1].content)

    print("\n--- Testing add_expense tool ---")
    add_expense_response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "I spent 500 rupees on dinner on 2024-07-01."}]}
    )
    print("Add expense response:", add_expense_response['messages'][-1].content)

    print("\n--- Testing get_expense_history tool ---")
    history_response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "Show me my expense history."}]}
    )
    print("Expense history response:", history_response['messages'][-1].content)
    
    print("\n--- Testing get_balance_by_date tool ---")
    get_expense_by_date_response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "What did i spend on 2025-07-03 ?"}]}
    )
    print("Get expense by date response:", get_expense_by_date_response['messages'][-1].content)
# Run the main asynchronous function
if __name__ == "__main__":
    asyncio.run(main())