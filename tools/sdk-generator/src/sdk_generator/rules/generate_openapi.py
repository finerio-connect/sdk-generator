from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT / "src"))

from cortex_rules.interfaces.api.app import app


def dump_openapi(output_path: Path) -> None:
    schema = app.openapi()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera el archivo OpenAPI para la API de reglas.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("build/openapi.json"),
        help="Ruta del archivo de salida (por defecto build/openapi.json)",
    )
    args = parser.parse_args()
    dump_openapi(args.output)
    print(f"Especificacion OpenAPI generada en {args.output.resolve()}")


if __name__ == "__main__":
    main()
