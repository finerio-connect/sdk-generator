import typer
from pathlib import Path
from sdk_generator.embeddings.generate_sdk import generate as generate_sdk_embeddings

app_module = typer.Typer(
    help="Commands related to Cortex Rules SDK",
    no_args_is_help=True,
)

@app_module.command("generate")
def generate(
    spec: Path = typer.Option(..., "--spec"),
    output: Path = typer.Option(Path("../../sdks/cortex_embeddings_sdk"), "--output"),
    overwrite: bool = typer.Option(False,"--overwrite")
):
    generate_sdk_embeddings(
        spec=spec,
        output_dir=output,
        overwrite=overwrite,
        version="1.0.0"
    )
