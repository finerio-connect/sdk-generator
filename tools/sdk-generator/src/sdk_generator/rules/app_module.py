import typer
from pathlib import Path
from sdk_generator.rules.generate import generate as generate_rules_sdk

app_module = typer.Typer(
    help="Commands related to Cortex Rules SDK",
    no_args_is_help=True,
)


@app_module.command("generate")
def generate(
        spec: Path = typer.Option(..., "--spec"),
        output: Path = typer.Option(Path("../../sdks/cortex_rules_sdk"), "--output"),
        overwrite: bool = typer.Option(False,"--overwrite")

):
    generate_rules_sdk(
        spec=spec,
        version="1",
        output_dir=output,
        overwrite=overwrite
    )
