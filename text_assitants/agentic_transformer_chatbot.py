from transformers import AutoTokenizer, AutoModelForCausalLM
from langchain.llms import HuggingFacePipeline
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory
from langchain_core.tools import Tool

import torch
from datetime import datetime
import gradio as gr
from transformers import pipeline
import operator

# === Load Qwen Model and Tokenizer ===
model_name = "Qwen/Qwen1.5-0.5B-Chat"
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True).to("cuda" if torch.cuda.is_available() else "cpu")

# === LangChain-compatible HF Pipeline ===
pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=512, temperature=0.7)
llm = HuggingFacePipeline(pipeline=pipe)

# === Tools (Functions with Descriptions) ===

def get_current_day_fn(input: str) -> str:
    # Returns the current day of the week
    return f"Today is: {datetime.now().strftime('%A')}"

def whats_my_name_fn(input: str) -> str:
    return "Your name is Sai"

# Simple calculator tool - safely evaluate arithmetic expressions
def calculator_fn(expression: str) -> str:
    try:
        # Only allow certain characters to prevent code injection
        allowed_chars = "0123456789+-*/(). "
        if any(c not in allowed_chars for c in expression):
            return "Error: Invalid characters in expression."

        # Evaluate expression safely using eval with restricted globals and locals
        result = eval(expression, {"__builtins__": None}, {})
        return f"The result is: {result}"
    except Exception as e:
        return f"Error evaluating expression: {str(e)}"

tools = [
    Tool(name="Get Current Day", func=get_current_day_fn, description="Returns the current day of the week."),
    Tool(name="What's My Name", func=whats_my_name_fn, description="Tells the user's name."),
    Tool(name="Calculator", func=calculator_fn, description="Evaluates simple arithmetic expressions.")
]

# === Memory for Multi-turn History ===
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# === LangChain Agent Setup ===
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    memory=memory,
    verbose=True
)

# === Gradio Chat Handler ===
def chat_fn(message, history):
    try:
        response = agent.run(message)
        if not response.strip():
            response = "I'm not sure how to respond to that."
    except Exception as e:
        response = f"An error occurred: {str(e)}"
    history.append((message, response))
    return "", history


# === Gradio UI ===
with gr.Blocks() as demo:
    gr.Markdown("# 🤖 Qwen Agentic Chatbot with Tools")
    chatbot = gr.Chatbot(label="Qwen Agent", height=500)
    msg = gr.Textbox(label="Message", placeholder="Ask me anything...")
    state = gr.State([])

    send = gr.Button("Send")
    clear = gr.Button("Clear")

    send.click(chat_fn, [msg, state], [msg, chatbot])
    msg.submit(chat_fn, [msg, state], [msg, chatbot])
    clear.click(lambda: ("", []), None, [msg, state, chatbot])

demo.launch()
