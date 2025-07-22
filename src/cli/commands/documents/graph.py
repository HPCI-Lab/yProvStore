import os
import click
import json

from rich.console import Console
from rich.table import Table

from utils.api_client import make_request


console = Console()


@click.group(name="graph")
def graph():
    """
    Manage graph operations on provenance documents.

    You must pass a fully-qualified PID (prefix/id).
    """
    pass


@graph.command(name="list")
@click.argument("pid")
@click.option("--entity-types", "-t", multiple=True, help="Filter by entity types (e.g., entity, agent, wasDerivedFrom).")
@click.option("--entity-ids", "-e", multiple=True, help="Filter by entity IDs.")
@click.option("--in-json", "-j", is_flag=True, help="Output the results in JSON format (all data is written).")
@click.option("--display-data", "-d", is_flag=True, help="Display the data field in the output console.")
@click.option("--output", "-o", type=click.Path(), help="Output file path to save the results (all data is written).")
@click.pass_context
def list_elements(ctx, pid, entity_types, entity_ids, in_json, display_data, output):
    """
    List elements in a provenance document graph.

    PID should be in the format prefix/id.
    """
    api_url = ctx.obj['API_URL']

    if pid.count("/") != 1:
        console.print("[red]Error: PID must be in the format prefix/id.[/red]")
        return

    response = make_request(
        method="GET",
        api_url=api_url,
        endpoint=f"/documents/{pid}/graph/list",
        params={
            "entity_types": list(entity_types) if entity_types else None,
            "entity_ids": list(entity_ids) if entity_ids else None
        }
    )

    if response.status_code != 200:
        console.print(f"[red]Error: {response.json().get('detail', 'Unknown error occurred.')}")
        return

    data = response.json()
    if output:
        os.makedirs(os.path.dirname(output), exist_ok=True)
        with open(output, 'w') as f:
            json.dump(data, f, indent=2)
        console.print(f"[green]Results saved to {output}[/green]")
        return
    if in_json:
        console.print(json.dumps(data, indent=2))
        return
    table = Table(title="Provenance Document Graph Elements")

    table.add_column("ID", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Group", style="green")
    table.add_column("Is Element", style="yellow")
    table.add_column("Is Relation", style="blue")
    if display_data:
        table.add_column("Data", style="white")
    
    for element in data.get("elements", []):
        row = [
            element["id"],
            element["type"],
            element["group"],
            str(element["is_element"]),
            str(element["is_relation"])
        ]
        if display_data:
            row.append(
                json.dumps(element["data"], indent=2)
            )
        table.add_row(*row)

    console.print(table)
    if data.get("warnings"):
        console.print("[yellow]Warnings:[/yellow]")
        for warning in data["warnings"]:
            console.print(f"- {warning}")
    else:
        console.print("[green]No warnings encountered.[/green]")
    console.print(f"[blue]Total elements found: {len(data.get('elements', []))}[/blue]")
