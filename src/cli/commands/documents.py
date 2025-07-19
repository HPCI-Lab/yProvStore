import os
import click
import json
from rich.console import Console
from rich.table import Table
from utils.api_client import make_request


console = Console()


@click.group()
def documents():
    """Create, download, and manage provenance documents."""
    pass


@documents.command(name="list")
@click.pass_context
def list_documents(ctx):
    """List all available document records."""
    api_url = ctx.obj['API_URL']
    response = make_request("GET", api_url, "/documents")

    if response and response.status_code == 200:
        doc_list = response.json()
        if not doc_list:
            console.print("[yellow]No documents found.[/yellow]")
            return

        table = Table(title="Available Provenance Documents")
        table.add_column("PID", style="cyan", no_wrap=True)
        table.add_column("Version", style="magenta")
        table.add_column("Owner", style="green")
        table.add_column("Parent PID", style="cyan")

        for doc in doc_list:
            table.add_row(doc['pid'], str(doc['version']), doc['owner_email'], doc.get('parent_document_pid', 'N/A'))

        console.print(table)


@documents.command(name="get")
@click.argument('pid')
@click.pass_context
def get_document(ctx, pid):
    """Get detailed info for a specific document by its PID."""
    api_url = ctx.obj['API_URL']
    response = make_request("GET", api_url, f"/documents/{pid}")

    if response and response.status_code == 200:
        console.print_json(data=response.json())


# TODO: add --value to pass a JSON string instead

@documents.command(name="create")
@click.option(
    '--json-file',
    required=True,  # Make this option mandatory
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Path to a JSON file with the document data."
)
@click.option('--parent-pid', help="PID of the parent document, if any.")
@click.pass_context
def create_document(ctx, json_file, parent_pid):
    """Publish a new document from a JSON data file."""
    api_url = ctx.obj['API_URL']
    params = {'parent_document_pid': parent_pid} if parent_pid else {}

    console.print(f"Uploading document from JSON file: [cyan]{json_file}[/cyan]")

    # Read and validate the JSON file
    try:
        with open(json_file, 'r') as f:
            document_data = json.load(f)
    except json.JSONDecodeError:
        console.print(f"❌ [bold red]Error:[/bold red] The file '{json_file}' does not contain valid JSON.")
        return
    except IOError:
        console.print(f"❌ [bold red]Error:[/bold red] Could not read the file '{json_file}'.")
        return

    # Prepare the payload and make the API request
    payload = {"document_data": document_data}
    response = make_request("POST", api_url, "/documents", params=params, json=payload)

    if response and response.status_code == 200:
        console.print("✅ [bold green]Document created successfully![/bold green]")
        console.print_json(data=response.json())


@documents.command(name="download")
@click.argument('pid')
@click.option(
    '-o', '--output',
    type=click.Path(dir_okay=False, writable=True),
    help="Full path to save the file (e.g., 'my_dir/my_doc.json'). This overrides --output-folder."
)
@click.option(
    '--output-folder',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True),
    help="Folder to save the file in. The filename will default to the document's PID."
)
@click.pass_context
def download_document(ctx, pid, output, output_folder):
    """Download a document file by its PID."""

    # Determine the final output path based on the provided options
    if output:
        # If a full output path is given, it takes precedence
        output_path = output
        output_folder = os.path.dirname(output_path)
    elif output_folder:
        # If only a folder is given, construct the path using the PID as the filename
        output_path = os.path.join(output_folder, f"{pid}.prov")
    else:
        # If no location is specified, save the file in the current directory
        output_path = f"{pid}.prov"
        output_folder = os.getcwd()

    api_url = ctx.obj['API_URL']
    console.print(f"Downloading document [cyan]{pid}[/cyan] to [yellow]{output_path}[/yellow]...")

    split = pid.split('/')
    if len(split) == 2:
        # If the PID includes a prefix, create the prefix folder it if it doesn't exist
        prefix_path = os.path.join(output_folder, split[0])
        if not os.path.exists(prefix_path):
            os.makedirs(prefix_path)
    elif (len(split) > 2):
        console.print(f"❌ [bold red]Error:[/bold red] Invalid PID format '{pid}'. Expected format is 'prefix/pid' or 'pid'.")
        return

    response = make_request("GET", api_url, f"/documents/{pid}/download", stream=True)

    if response and response.status_code == 200:
        try:
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            console.print(f"✅ [bold green]Download complete![/bold green] File saved to [yellow]{output_path}[/yellow].")
        except IOError as e:
            console.print(f"[bold red]Error writing to file:[/bold red] {e}")
