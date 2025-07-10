from mcp.server.fastmcp import FastMCP
# from fastmcp import FastMCP
from typing import List, Dict
import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime
# In-memory mock database with starting balance and empty history
load_dotenv()
# Create MCP server
mcp = FastMCP(name="Expense Tracker1")
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")



class ExpenseDB:
    def __init__(self):
        self.conn = psycopg2.connect(
            user = USER,
            password = PASSWORD,
            host = HOST,
            port = PORT,
            dbname = DBNAME
        )
        self._init_db()
    def _init_db(self):
        """Initialize the database with a table for expenses"""
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                expense_id SERIAL,
                title VARCHAR(100),
                amount INTEGER,
                date_time TIMESTAMP DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Kolkata'),
                PRIMARY KEY (expense_id,date_time)
            )
        """)
        self.conn.commit()
    def get_conn(self):
        """Get the database connection"""
        return self.conn

# Resource: ExpenseDB
@mcp.resource(uri="db://expenses_db")
def get_expense_db() -> ExpenseDB:
    """
    Get the ExpenseDB resource.
    
    This resource provides access to the database for expense tracking.
    It initializes the database and creates the necessary table if it doesn't exist.
    """
    return ExpenseDB()

# Tools

@mcp.tool()
def get_time() -> str:
    """
    Get the current date and time, including the day of the week.
    
    This tool is used when the user asks for the current time or day.
    and it is also required for the expense tracking system to log the date
    of expenses accurately. It provides a formatted string with the current
    It returns a formatted string with the current date and time.
    """
    now = datetime.now()
    return now.strftime("%A, %B %d, %Y at %I:%M:%S %p %Z")

@mcp.tool()
def add_expense(title: str, amount: int) -> str:
    """
    Record a new expense for a person.

    Use this tool to log an expense with a title, amount, and date. It is used
    when the user mentions spending money or adding a new transaction.
    Parameters:
        title (str): A brief description of the expense (e.g., "Lunch", "Groceries").
        amount (int): The amount spent in rupees.
    """
    db = get_expense_db()
    conn = db.get_conn()
    cursor = db.cursor
    try:
        cursor.execute("""
            INSERT INTO expenses (title, amount)
            VALUES (%s, %s)
        """, (title, amount))
        conn.commit()
        # date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"Expense of ₹{amount} with title {title}."
    except Exception as e:
        return f"Error adding expense: {str(e)}"
    finally:
        cursor.close()
        conn.close()

@mcp.tool()
def get_expense_history() -> str:
    """
    Retrieve the complete expense history.

    This tool returns all past expenses recorded in db in the form of
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
        None

    Returns:
        str: A formatted list of expenses (title, amount, date) or an error message.
    """
    db = get_expense_db()
    conn = db.get_conn()
    cursor = db.cursor
    try:
        cursor.execute("""
            SELECT title, amount, date_time FROM expenses
        """)
        records = cursor.fetchall()
        
        history = "\n".join(
            [f"Spent for {title}: ₹{expense} on {date}" for title, expense, date in records]
        )
        return f"Expense history is :\n{history}"
    except Exception as e:
        return f"Error retrieving expense history: {str(e)}"
    finally:
        cursor.close()
        conn.close()

@mcp.tool()
def get_expense_by_date(date: str) -> str:
    """
    Retrieve expenses for a specific date.

    This tool returns all expenses recorded on a given date.
    It is useful for answering questions like:
    
    - "What did I spend on 2024-07-01?"
    
    Parameters:
        date (str): The date in YYYY-MM-DD format to filter expenses.

    Returns:
        str: A formatted list of expenses for the specified date or an error message.
    """
    db = get_expense_db()
    conn = db.get_conn()
    cursor = db.cursor
    try:
        cursor.execute("""
            SELECT title, amount, date_time FROM expenses
            WHERE date_time::date = %s
        """, (date,))
        records = cursor.fetchall()
        
        if not records:
            return f"No expenses found for {date}."
        
        history = "\n".join(
            [f"{title}: ₹{expense} on {date_time}" for title, expense, date_time in records]
        )
        return f"Expenses on {date}:\n{history}"
    except Exception as e:
        return f"Error retrieving expenses for {date}: {str(e)}"
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    mcp.run(transport="sse")