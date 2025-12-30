import unittest
from sdk_generator import GenerateSdkUseCase, SdkGenerateConfig
from pathlib import Path


class MyTestCase(unittest.TestCase):
    def test_use_case_sdk_generate(self):

        output_dir= Path("../build/python")
        spec_path=Path("openapi_test.json")

        config = SdkGenerateConfig(
            output_dir=output_dir,
            spec_path=spec_path,
            package_name="sdk_cortex_rules",
            version="1.0.2",
            overwrite=True,
            use_integrated_client=False
        )

        use_case= GenerateSdkUseCase()

        use_case.execute(
            config
        )




if __name__ == '__main__':
    unittest.main()
