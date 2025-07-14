import click
from rich.console import Console
from utils.api_client import make_request, save_token, clear_token


console = Console()


@click.group()
def auth():
    """Manages user authentication."""
    pass


@auth.command()
@click.option('--email', prompt=True, help="User's email address.")
@click.option('--password', prompt=True, hide_input=True, help="User's password.")
@click.pass_context
def login(ctx, email, password):
    """Log in to get an access token."""
    api_url = ctx.obj['API_URL']
    data = {"email": email, "password": password}

    console.print(f"Attempting to log in as [cyan]{email}[/cyan]...")
    response = make_request("POST", api_url, "/auth/login", json=data)

    if response and response.status_code == 200:
        token_data = response.json()
        save_token(token_data["access_token"])
    else:
        console.print("[bold red]Login failed.[/bold red]")


@auth.command()
@click.option('--email', prompt=True, help="Your desired email address.")
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help="Your desired password.")
@click.pass_context
def signup(ctx, email, password):
    """Register a new user account."""
    api_url = ctx.obj['API_URL']
    data = {"email": email, "password": password}

    response = make_request("POST", api_url, "/auth/signup", json=data)

    if response and response.status_code == 201:
        console.print("✅ [bold green]User registration successful! You can now log in.[/bold green]")


@auth.command()
@click.pass_context
def verify(ctx):
    """Verify the current session token."""
    api_url = ctx.obj['API_URL']
    response = make_request("POST", api_url, "/auth/verify")

    if response and response.status_code == 200:
        user_data = response.json()
        console.print(f"✅ [bold green]Token is valid.[/bold green] Logged in as: [cyan]{user_data['email']}[/cyan]")


@auth.command()
def logout():
    """Log out by deleting the local token."""
    clear_token()
