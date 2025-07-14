import os
import requests
from pathlib import Path
from rich.console import Console


console = Console()


# Path to store the authentication token
TOKEN_FILE = Path.home() / ".yprov_token"


def save_token(token: str):
    """Saves the JWT token to a file in the user's home directory."""
    try:
        TOKEN_FILE.write_text(token)
        console.print("🔑 [bold green]Authentication token saved successfully.[/bold green]")
    except IOError as e:
        console.print(f"[bold red]Error saving token:[/bold red] {e}")


def load_token() -> str | None:
    """Loads the JWT token from the file."""
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    return None


def clear_token():
    """Removes the saved token file for logout."""
    if TOKEN_FILE.exists():
        os.remove(TOKEN_FILE)
        console.print("✅ [bold]Successfully logged out.[/bold]")


def make_request(method: str, api_url: str, endpoint: str, **kwargs):
    """
    A centralized function to make API requests.
    It automatically adds the auth token if available.
    """
    token = load_token()
    headers = kwargs.pop("headers", {})

    # Add authentication header if a token exists
    if token:
        headers["Authorization"] = f"Bearer {token}"

    full_url = f"{api_url.rstrip('/')}/{endpoint.lstrip('/')}"

    try:
        response = requests.request(method, full_url, headers=headers, **kwargs)

        # Check for HTTP errors and print informative messages
        if not response.ok:
            error_details = response.json() if response.headers.get("Content-Type") == "application/json" else response.text
            console.print(f"[bold red]Error {response.status_code}:[/bold red]", error_details)
            return None

        return response

    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]API request failed:[/bold red] {e}")
        return None
