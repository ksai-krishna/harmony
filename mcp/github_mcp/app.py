from mcp import FastMCP
from typing import List, Dict
import psycopg2
import os
from dotenv import load_dotenv
# In-memory mock database with starting balance and empty history
load_dotenv()
# Create MCP server
mcp = FastMCP("ExpenseTracker")
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

@mcp.resource(uri="db://expenses_db")
class ExpenseDB:
    def __init__(self):
        self.conn = psycopg2.connect(
            user = USER,
            password = PASSWORD,
            host = HOST,
            port = PORT,
            dbname = DBNAME
        )
        self.cursor = self.conn.cursor()
    def _init_db(self):
        """Initialize the database with a table for expenses"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                user_id VARCHAR(50),
                title VARCHAR(100),
                expense INTEGER,
                date DATE
            )
        """)
        self.conn.commit()
    def get_conn(self):
        """Get the database connection"""
        return self.conn

# Tools

@mcp.tool()
def add_expense(user_id: str, title: str, expense: int, date: str,db: ExpenseDB) -> str:
    """
    Record a new expense for a user.

    Use this tool to log an expense with a title, amount, and date. It is used
    when the user mentions spending money or adding a new transaction.
    Parameters:
        user_id (str): The ID of the user who is adding the expense.
        title (str): A brief description of the expense (e.g., "Lunch", "Groceries").
        expense (int): The amount spent in rupees.
        date (str): The date of the expense in 'YYYY-MM-DD' format.
        db (ExpenseDB): The injected database resource.
    """

    conn = db.get_conn()
    cursor = db.cursor
    try:
        cursor.execute("""
            INSERT INTO expenses (user_id, title, expense, date)
            VALUES (%s, %s, %s, %s)
        """, (user_id, title, expense, date))
        conn.commit()
        return f"Expense of ₹{expense} added for {user_id} on {date}."
    except Exception as e:
        return f"Error adding expense: {str(e)}"
    finally:
        cursor.close()
        conn.close()

@mcp.tool()
def get_expense_history(user_id: str, db: ExpenseDB) -> str:
    """
    Retrieve the complete expense history for a specific user.

    This tool returns all past expenses recorded by the user in the form of
    itemized entries (title, amount, and date). It is useful for answering
    questions such as:
    
    - "How much did I spend on food last week?"
    - "What did I spend on groceries?"
    - "Show me my expenses from January"
    - "List all expenses related to phone or travel"
    
    The AI should call this tool to fetch all recorded transactions, and then
    perform keyword filtering, date-based filtering, or category-based analysis
    (as needed) to answer the user's query. If no expenses are found, it will
    return a friendly message.

    Parameters:
        user_id (str): The ID of the user whose expense history is requested.
        db (ExpenseDB): The injected database resource.

    Returns:
        str: A formatted list of expenses (title, amount, date) or an error message.
    """

    conn = db.get_conn()
    cursor = db.cursor
    try:
        cursor.execute("""
            SELECT title, expense, date FROM expenses WHERE user_id = %s
        """, (user_id,))
        records = cursor.fetchall()
        if not records:
            return "No expenses recorded for this user."
        
        history = "\n".join(
            [f"{title}: ₹{expense} on {date}" for title, expense, date in records]
        )
        return f"Expense history for {user_id}:\n{history}"
    except Exception as e:
        return f"Error retrieving expense history: {str(e)}"
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    mcp.run()
