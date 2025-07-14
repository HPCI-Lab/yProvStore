import click
from commands.auth import auth
from commands.documents import documents


@click.group()
@click.option(
    '--api-url',
    default='http://127.0.0.1:8000',
    help='Base URL of the yProv API server.',
    envvar='YPROV_API_URL'  # Allows setting via environment variable
)
@click.pass_context
def cli(ctx, api_url):
    """
    yProv CLI: A command-line tool for the yProv Provenance Service.

    You can set the API URL using the --api-url option or by setting
    the YPROV_API_URL environment variable.
    """
    # Ensure the context object exists and store the API URL
    ctx.ensure_object(dict)
    ctx.obj['API_URL'] = api_url


# Add command groups to the main CLI
cli.add_command(auth)
cli.add_command(documents)


if __name__ == '__main__':
    cli()
