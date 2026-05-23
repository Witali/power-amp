import json
import tempfile
import unittest
from pathlib import Path

from scripts import pipeline_config


class PipelineConfigTests(unittest.TestCase):
    def test_missing_parallelism_config_uses_defaults(self) -> None:
        values = pipeline_config.load_pipeline_parallelism(Path("missing-pipeline-parallelism.json"))

        self.assertEqual(values["max_parallel_opencv_tasks"], 1)
        self.assertEqual(values["max_parallel_ocr_tasks"], 1)
        self.assertEqual(values["tesseract_threads_per_process"], 1)

    def test_parallelism_config_reads_positive_integers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pipeline_parallelism.json"
            path.write_text(
                json.dumps(
                    {
                        "max_parallel_opencv_tasks": 8,
                        "max_parallel_ocr_tasks": "8",
                        "tesseract_threads_per_process": 0,
                    }
                ),
                encoding="utf-8",
            )

            values = pipeline_config.load_pipeline_parallelism(path)

        self.assertEqual(values["max_parallel_opencv_tasks"], 8)
        self.assertEqual(values["max_parallel_ocr_tasks"], 8)
        self.assertEqual(values["tesseract_threads_per_process"], 1)


if __name__ == "__main__":
    unittest.main()
