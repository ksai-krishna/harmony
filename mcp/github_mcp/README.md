## github-mcp
now
This project is an Expense Tracker built using the Model Context Protocol (MCP) framework.

### Features
- Track user expenses with categories and dates
- Check current balance for a user
- View expense history
- Simple in-memory storage for demonstration

### Project Structure
- `app.py`: Main MCP server with tools for expense tracking
- `main.py`: Simple entry point script
- `pyproject.toml`: Project metadata and dependencies

### Requirements
- Python 3.12+
- Dependencies: `mcp-agent`, `requests` (see `pyproject.toml`)

### Usage
1. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
2. Run the MCP server:
   ```sh
   python app.py
   ```

### Example Tools
- **get_balance(user_id)**: Returns the current balance for the user.
- **add_expense(user_id, amount, category, date)**: Adds an expense for the user.
- **get_expense_history(user_id)**: Shows the user's expense history.

---
This project is for demonstration and learning purposes.
