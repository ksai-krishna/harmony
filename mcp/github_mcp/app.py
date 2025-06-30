from mcp.server.fastmcp import FastMCP
from typing import List, Dict

# In-memory mock database with starting balance and empty history
user_expenses = {
    "U001": {"balance": 10000, "history": []},  # Starting with ₹10,000
}

# Create MCP server
mcp = FastMCP("ExpenseTracker")

# Tool: Check Current Balance
@mcp.tool()
def get_balance(user_id: str) -> str:
    """Check current balance for the user"""
    data = user_expenses.get(user_id)
    if data:
        return f"{user_id} has ₹{data['balance']} remaining."
    return "User ID not found."

# Tool: Add an Expense
@mcp.tool()
def add_expense(user_id: str, amount: float, category: str, date: str) -> str:
    """
    Add an expense with amount, category (e.g., 'Food', 'Travel'), and date (e.g., '2025-06-25')
    """
    if user_id not in user_expenses:
        return "User ID not found."

    if amount > user_expenses[user_id]["balance"]:
        return f"Insufficient balance. Tried to spend ₹{amount}, but only ₹{user_expenses[user_id]['balance']} available."

    # Deduct and add to history
    user_expenses[user_id]["balance"] -= amount
    user_expenses[user_id]["history"].append({
        "amount": amount,
        "category": category,
        "date": date
    })

    return f"₹{amount} spent on {category}. Remaining balance: ₹{user_expenses[user_id]['balance']}."

# Tool: Get Expense History
@mcp.tool()
def get_expense_history(user_id: str) -> str:
    """Get expense history for the user"""
    data = user_expenses.get(user_id)
    if not data:
        return "User ID not found."

    history = data['history']
    if not history:
        return "No expenses recorded."

    summary = "\n".join(
        [f"₹{entry['amount']} on {entry['category']} ({entry['date']})" for entry in history]
    )
    return f"Expense history for {user_id}:\n{summary}"

# Resource: Greeting
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}! Ready to track your expenses today?"

if __name__ == "__main__":
    mcp.run()
