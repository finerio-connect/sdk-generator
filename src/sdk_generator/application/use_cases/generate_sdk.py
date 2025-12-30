import subprocess
from sdk_generator.infraestructure.open_api_generator_impl import OpenApiGeneratorImpl
from sdk_generator.domain.model.sdk_spec import SdkSpec
from sdk_generator.infraestructure.file_system.file_system import FileSystem


class GenerateSdkUseCase:
    def __init__(self):
        self.open_api_generator = OpenApiGeneratorImpl()
        self.file_system = FileSystem()
        pass

    def execute(self, config: SdkSpec):
        if not self.open_api_generator.check_datamodel_codegen():
            raise RuntimeError(
                "datamodel-code-generator no está instalado.\n"
                "Instálalo con: pip install 'datamodel-code-generator[http]'\n"
                "O agrega al pyproject.toml: datamodel-code-generator>=0.25.0"
            )

        if self.file_system.exists(config.output_dir):
            if config.overwrite:
                self.file_system.remove(config.output_dir)
            else:
                raise FileExistsError(
                    f"El directorio de salida {config.output_dir} ya existe. "
                    "Usa overwrite=True para reemplazarlo."
                )

        self.file_system.mkdir(config.output_dir)

        self.open_api_generator.generate_models(config)

        print(f"\nSDK generado en: {config.output_dir.resolve()}")



