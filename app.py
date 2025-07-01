import datetime
import operator
import os

import gradio as gr
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_experimental.tools import PythonREPLTool
from langchain_ollama import ChatOllama
from langchain_ollama import OllamaEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.document_loaders import PyPDFLoader
from langchain_mcp_adapters import load_mcp_tools

DB_DIR = "./chroma_db"  # Directory to store the Chroma vector store
EMBEDDING_MODEL_NAME = "nomic-embed-text"  # Replace with your actual model name
LLM_MODEL_NAME = "llama3.2"  # Replace with your actual model name
# LLM_MODEL_NAME = "qwen3:0.6b"  # Replace with your actual model name
DOC_PATH = "annual-report-2024-2025.pdf"  # Path to your document file

embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL_NAME,num_ctx=2048)
if os.path.exists(DB_DIR):
    vectorstore = Chroma(persist_directory=DB_DIR,embedding_function=embeddings)
else:
    loader = TextLoader(DOC_PATH)
    loader = PyPDFLoader(DOC_PATH)  # Use PyPDFLoader for PDF files
    documents = loader.load()
    splitter = CharacterTextSplitter(chunk_size=500,chunk_overlap=50)
    docs = splitter.split_documents(documents)
    vectorstore = Chroma.from_documents(documents=docs,embedding=embeddings,persist_directory=DB_DIR)

def build_rag_chain():
    
    retriever = vectorstore.as_retriever()
    llm = ChatOllama(model=LLM_MODEL_NAME)
    qa_chain = RetrievalQA.from_chain_type(llm=llm,retriever=retriever)
    return qa_chain


@tool
def rag_tool(query:str) -> str:
    """
    It performs retrieval-augmented generation (RAG) using a local vector database.
    Only use this tool if the user asks questions related to the document's content.
    And the document is an annual report for 2024-2025 of tcs also can summarize the document.
    """
    qa_chain = build_rag_chain()
    answer = qa_chain.invoke(query)
    answer = answer['result'] if isinstance(answer, dict) else answer
    answer = answer + "\n\nplease understand this and give the same content."
    print(answer,"from rag_tool")
    return answer


# --- 1. Define Tools ---

# Tool to get the current time and day
@tool
def get_current_time_and_day() -> str:
    """Gets the current date and time, including the day of the week. only invoke only when the user asks for current time or day."""
    now = datetime.datetime.now()
    return now.strftime("%A, %B %d, %Y at %I:%M:%S %p %Z")

# Tool for calculations using Python REPL (Read-Eval-Print Loop)
# This allows the LLM to execute Python code for arithmetic.
calculator_tool = PythonREPLTool()

# -- MCP Tools --

mcp_tools = load_mcp_tools(
    base_url="http://localhost:3333",  # or wherever your MCP server is hosted
    tool_uris=[
        "tool://get_time",
        "tool://add_expense",
        "tool://get_expense_history",
    ],
    resources=["db://expenses_db"]
)


# List of tools available to the agent
tools = [
    get_current_time_and_day,
    rag_tool,
    *mcp_tools
    ]

# --- 2. Initialize LLM ---
# Using the latest ChatOllama from langchain_ollama
llm = ChatOllama(model=LLM_MODEL_NAME)

# --- 3. Create the Agent ---

# Agent Prompt Template - Crucial for guiding the LLM
# We use MessagesPlaceholder for dynamic history and scratchpad
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful AI assistant. "
            # Removed the explicit {tools} placeholder here.
            # create_tool_calling_agent handles tool descriptions internally.
            "You must use the provided tools to answer user questions when appropriate. "
            "If a tool is not suitable, respond directly. "
            # "Always include the full conversation history. "
            # "Today's date is " + datetime.date.today().strftime("%A, %B %d, %Y") + ". "
            "The current location is Bengaluru, Karnataka, India."
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"), # This is where intermediate steps go
    ]
)

# Convert Gradio's history format to LangChain's message objects
def _format_chat_history(chat_history):
    formatted_messages = []
    for chat_message in chat_history:
        if chat_message["role"] == "user":
            formatted_messages.append(HumanMessage(content=chat_message["content"]))
        elif chat_message["role"] == "assistant":
            # For simplicity, we'll assume assistant messages are just AI messages.
            # In a more complex agent, you might need to parse for tool calls
            # that were part of previous assistant turns if they were yielded directly.
            formatted_messages.append(AIMessage(content=chat_message["content"]))
    return formatted_messages

# Create the LangChain Agent
# `create_tool_calling_agent` is the recommended way for tool-calling models
agent = create_tool_calling_agent(llm, tools, prompt)

# Create the AgentExecutor
# This handles the full agentic loop: planning, tool calling, responding.
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True) # verbose=True to see agent's thought process in console


# --- 4. Gradio Interface Function ---

def stream_agentic_response(message, history):
    """
    Processes user input using the LangChain AgentExecutor and streams the response
    back to the Gradio ChatInterface.
    """
    # Gradio's `history` contains the conversation as a list of dicts.
    # Convert it to LangChain's message format for the agent executor.
    formatted_history = _format_chat_history(history)
    print(formatted_history, "formatted_history")
    # Accumulate the full response content for display and history
    full_response_content = ""

    try:
        # Stream from the AgentExecutor
        # The stream method yields dictionaries representing agent steps
        # This is where the magic happens for tool usage and final output.
        for s in agent_executor.stream(
            {"input": message, "chat_history": formatted_history}
        ):
            # The 's' dictionary will contain different keys depending on the agent's step.
            # We are interested in the final 'output' from the agent.
            
            # For a more detailed streaming of agent thoughts and tool use:
            # - `s.get("actions")`: Agent decided to call a tool. You could yield a message like "Agent is using tool: [tool_name]"
            # - `s.get("steps")`: Tool execution results. You could yield "Tool output: [output]"
            # - `s.get("output")`: The final human-readable response from the agent.
            
            # For this simplified Gradio streaming, we'll only yield the final output
            # which will appear in the chatbot's response area.
            print(s)
            if "output" in s:
                # Stream the final output character by character
                for char in s["output"]:
                    full_response_content += char
                    yield full_response_content

            
    except Exception as e:
        yield f"An error occurred: {e}"
        print(f"Error during agent streaming: {e}")


# --- 5. Create Gradio ChatInterface ---
demo = gr.ChatInterface(
    fn=stream_agentic_response,
    chatbot=gr.Chatbot(height=400, type='messages'), # 'messages' type is crucial for role handling
    textbox=gr.Textbox(placeholder="Ask me about time, calculations, or anything else!", container=False, scale=7),
    title="Agentic Chatbot using Llama3.2 with Tools",
    description=(
        "This chatbot can leverage tools for specific tasks like "
        "getting the current time/day and performing calculations. It streams responses for a smoother experience."
    ),
    examples=[
        "What is the current time and day?",
        "Calculate 123 + (45 * 8) / 2.",
        "What is the capital of Japan?", # Direct LLM response
        "Tell me a fun fact about giraffes.",
        "How many days until Christmas 2025?", # Requires calculation and current date knowledge
    ],
    cache_examples=False, # Set to False as tool outputs (like time) change
    theme="soft",
    # retry_btn="Retry",
    # undo_btn="Delete Last",
    # clear_btn="Clear All",
)

# --- 6. Launch Gradio App ---
demo.launch(share=True)