import json
import subprocess
import sys

from aifa_pipeline.database import ROOT


def test_cli_builds_bundled_catalog_offline_and_repeats(tmp_path):
    command = [sys.executable, "-m", "aifa_pipeline", "build", "--output", str(tmp_path)]
    for _ in range(2):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert "Finished. Results:" in result.stdout
    metrics = json.loads((tmp_path / "metrics.json").read_text())
    assert metrics["catalog"]["source_rows"] == 332
    assert metrics["catalog"]["unique_aic"] == 331
    assert metrics["catalog"]["products_requiring_review"] == 2
    assert metrics["catalog"]["extracted_documents"] == 0
    assert metrics["sources"][0]["sha256"] == "b8aaa79716707a960b0bc7bc147a6a6a9d1cb444fb82f902428f0edef82ebaaa"
    assert len(list(tmp_path.glob("*.csv"))) == 6


def test_import_has_no_credentials_or_network_side_effects(tmp_path):
    script = "import sys; sys.path.insert(0, sys.argv[1]); import aifa_pipeline.__main__; import aifa_pipeline.sheets"
    result = subprocess.run([sys.executable, "-c", script, str(ROOT)], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert list(tmp_path.iterdir()) == []
