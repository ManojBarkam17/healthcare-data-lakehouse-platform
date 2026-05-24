"""Tests for Airflow DAG definitions — syntax and structure validation."""

import ast
from pathlib import Path

import pytest

DAGS_DIR = Path(__file__).resolve().parent.parent.parent / "dags"


class TestDAGSyntax:
    """Validate that all DAG files are valid Python."""

    @pytest.fixture
    def dag_files(self):
        return list(DAGS_DIR.glob("*.py"))

    def test_dag_files_exist(self, dag_files):
        py_files = [f for f in dag_files if f.name != "__init__.py"]
        assert len(py_files) >= 2, "Expected at least 2 DAG files"

    def test_dag_files_parse(self, dag_files):
        for dag_file in dag_files:
            try:
                ast.parse(dag_file.read_text())
            except SyntaxError as e:
                pytest.fail(f"Syntax error in {dag_file.name}: {e}")

    def test_healthcare_pipeline_dag_exists(self):
        assert (DAGS_DIR / "healthcare_pipeline_dag.py").exists()

    def test_data_quality_dag_exists(self):
        assert (DAGS_DIR / "data_quality_dag.py").exists()

    def test_dag_ids_are_defined(self, dag_files):
        """Ensure each DAG file defines a dag_id."""
        for dag_file in dag_files:
            if dag_file.name == "__init__.py":
                continue
            content = dag_file.read_text()
            assert "dag_id" in content, f"{dag_file.name} missing dag_id"

    def test_no_hardcoded_passwords(self, dag_files):
        """Ensure DAGs don't contain hardcoded credentials."""
        sensitive_patterns = ["password=", "secret=", "api_key=", "token="]
        for dag_file in dag_files:
            if dag_file.name == "__init__.py":
                continue
            content = dag_file.read_text().lower()
            for pattern in sensitive_patterns:
                # Allow patterns in comments or doc strings about security
                lines_with_pattern = [
                    line.strip()
                    for line in content.split("\n")
                    if pattern in line and not line.strip().startswith("#")
                ]
                assert len(lines_with_pattern) == 0, (
                    f"{dag_file.name} contains potential credential: {pattern}"
                )
