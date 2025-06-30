import re
import requests
from mcp.server.fastmcp import FastMCP
import sys

# === Config ===
DEFAULT_FILE = "app.py"
DEFAULT_BRANCH = "main"
DEFAULT_COMMENT_LIMIT = 3

# === MCP Server ===
mcp = FastMCP(name="github_mcp_agent")

# === Repo Extract Helper ===
def extract_repo_url(text: str):
    match = re.search(r"github\.com/([\w\-]+)/([\w\-]+)", text)
    return (match.group(1), match.group(2)) if match else (None, None)

# === Tool: Get File ===
@mcp.tool()
def get_file(input: str) -> str:
    """Fetches `app.py` from a GitHub repo mentioned in plain text."""
    owner, repo = extract_repo_url(input)
    if not owner or not repo:
        return "❌ Couldn’t parse repo from input text."

    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{DEFAULT_BRANCH}/{DEFAULT_FILE}"
    r = requests.get(url)
    if r.status_code != 200:
        return f"❌ Error fetching file: {r.status_code} {r.text}"

    return f"📄 `{DEFAULT_FILE}` from `{owner}/{repo}`:\n\n{r.text[:2000]}"


# === Tool: Summarize Comments (Raw View) ===
@mcp.tool()
def summarize_comments(input: str) -> str:
    """Returns the most recent GitHub issue comments as plain text."""
    owner, repo = extract_repo_url(input)
    if not owner or not repo:
        return "❌ Couldn’t parse repo from input text."

    url = f"https://api.github.com/repos/{owner}/{repo}/issues/comments"
    r = requests.get(url)
    if r.status_code != 200:
        return f"❌ Error fetching comments: {r.status_code} {r.text}"

    comments = [c["body"] for c in r.json()[:DEFAULT_COMMENT_LIMIT]]
    if not comments:
        return "⚠️ No recent comments found."

    return "🗨️ Latest Comments:\n\n" + "\n\n---\n\n".join(comments)

# Resource: Greeting
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}! How can I assist you with github today?"

# def main():
#     # mcp.add_tool(get_file)
#     # mcp.add_tool(summarize_comments)

#     # Example usage
#     input_text = "https://github.com/ggml-org/llama.cpp"
#     print(get_file(input_text))
#     print(summarize_comments(input_text))

# === Run ===
if __name__ == "__main__":
    # main()
    print('...', file=sys.stderr)
    mcp.run()
    
