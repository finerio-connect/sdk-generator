import typer
from rich import print

from sdk_generator.rules.app_module import app_module as rules_module
from sdk_generator.embeddings.app_module import app_module as embeddings_module
# from sdk_generator.commands.validate import validate

app = typer.Typer(
    name="sdk-generator",
    help="SDK Generator for Cortex services",
    no_args_is_help=True,
)

app.add_typer(rules_module, name="rules")
app.add_typer(embeddings_module, name="embeddings")

