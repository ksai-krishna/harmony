from mcp import FastMCP
from datetime import datetime

app = FastMCP(name="simple_mcp",port=8001)

## Tool Declaration
@app.tool()
def get_current_time() -> str:
    """ Gets the current time in UTC """
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M")

