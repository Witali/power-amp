import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import local_python_packages


class LocalPythonPackagesTests(unittest.TestCase):
    def test_candidate_package_dirs_use_current_python_tag_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            package_root = project_root / "local_tools" / "python_packages"
            package_root.mkdir(parents=True)
            versioned = package_root / local_python_packages.current_python_tag()
            versioned.mkdir()

            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(local_python_packages.candidate_package_dirs(project_root), [versioned])

    def test_legacy_root_is_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            package_root = project_root / "local_tools" / "python_packages"
            package_root.mkdir(parents=True)

            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(
                    local_python_packages.candidate_package_dirs(project_root),
                    [package_root / local_python_packages.current_python_tag()],
                )

            with patch.dict(os.environ, {"POWER_AMP_ALLOW_LEGACY_PYTHON_PACKAGES": "1"}, clear=True):
                self.assertEqual(
                    local_python_packages.candidate_package_dirs(project_root),
                    [package_root / local_python_packages.current_python_tag(), package_root],
                )

    def test_explicit_package_dirs_override_project_candidates(self) -> None:
        paths = [Path("C:/tmp/py-a"), Path("C:/tmp/py-b")]
        raw = os.pathsep.join(str(path) for path in paths)

        with patch.dict(os.environ, {"POWER_AMP_PYTHON_PACKAGES": raw}, clear=True):
            self.assertEqual(local_python_packages.candidate_package_dirs(Path("unused")), paths)

    def test_add_local_python_packages_adds_only_existing_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            versioned = project_root / "local_tools" / "python_packages" / local_python_packages.current_python_tag()
            versioned.mkdir(parents=True)
            original = list(sys.path)
            try:
                with patch.dict(os.environ, {}, clear=True):
                    local_python_packages.add_local_python_packages(project_root)
                    self.assertEqual(sys.path[0], str(versioned))
            finally:
                sys.path[:] = original


if __name__ == "__main__":
    unittest.main()
