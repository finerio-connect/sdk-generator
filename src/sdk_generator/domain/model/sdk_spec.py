from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True)
class SdkSpec:
    spec_path: Path
    output_dir: Path
    package_name: str
    version: str
    overwrite: bool
    use_integrated_client: bool
