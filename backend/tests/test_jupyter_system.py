import pytest
import pandas as pd
import numpy as np
import os
import shutil
from app.infrastructure.jupyter_system import JupyterEngineer, StatefulSandbox, PathValidator

@pytest.fixture
def engineer():
    return JupyterEngineer()

@pytest.fixture
def sandbox_dir():
    path = "./test_sandbox"
    os.makedirs(path, exist_ok=True)
    yield path
    if os.path.exists(path):
        shutil.rmtree(path)

class TestJupyterSystem:
    def test_stateful_execution(self, engineer):
        """Test that state persists across multiple cell executions."""
        # Cell 1: Define a variable
        cell1 = engineer.execute_cell("Define x", "x = 10")
        assert "COMPLETED" in cell1["outputs"][0]["data"]
        
        # Cell 2: Use the variable
        cell2 = engineer.execute_cell("Use x", "y = x * 2")
        assert "COMPLETED" in cell2["outputs"][0]["data"]
        
        # Cell 3: Check y
        cell3 = engineer.execute_cell("Check y", "print(y)")
        # The print output is clean from the summary
        # The print output is clean from the summary
        success, stdout, stderr, result_obj = engineer.sandbox.execute("print(y)")
        assert stdout.strip() == "20"

    def test_df_info_markdown(self, engineer):
        """Test the visual gate and markdown summary for DataFrames."""
        code = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2, 3], 'B': [None, 5, 6]})
"""
        cell = engineer.execute_cell("Create DF", code, metrics_df_name="df")
        data = cell["outputs"][0]["data"]
        assert "### 📊 Execution Summary" in data
        assert "| Records | 3 |" in data
        assert "| Columns | 2 |" in data
        assert "| Nulls | 1 |" in data

    def test_path_validation(self):
        """Test relative path enforcement."""
        # Relative paths should be fine
        PathValidator.validate_path("./data/test.csv")
        PathValidator.validate_path("data/test.csv")
        
        # Absolute paths should raise ValueError
        with pytest.raises(ValueError):
            if os.name == 'nt':
                PathValidator.validate_path("C:/data/test.csv")
            else:
                PathValidator.validate_path("/data/test.csv")

    def test_file_existence_assertion(self, sandbox_dir):
        """Test that file existence assertion works."""
        test_file = os.path.join(sandbox_dir, "test.txt")
        
        # Should raise RuntimeError if file doesn't exist
        with pytest.raises(RuntimeError):
            PathValidator.assert_exists(test_file)
            
        # Should pass if file exists
        with open(test_file, "w") as f:
            f.write("test")
        PathValidator.assert_exists(test_file)

    def test_recovery_protocol(self, engineer):
        """Test that errors trigger the recovery protocol."""
        cell = engineer.execute_cell("Faulty Cell", "print(non_existent_variable)")
        data = cell["outputs"][0]["data"]
        assert "### ⚠️ Recovery Protocol Triggered" in data
        assert "Variable or function not defined" in data
        assert "NameError" in data

    def test_backend_json_contract(self, engineer):
        """Verify the returned JSON structure matches Spec 4."""
        cell = engineer.execute_cell("Simple Cell", "a = 1")
        assert "cell_type" in cell
        assert "source" in cell
        assert "outputs" in cell
        assert cell["cell_type"] == "code"
        assert isinstance(cell["outputs"], list)
        assert cell["outputs"][0]["output_type"] == "markdown"
        assert "data" in cell["outputs"][0]
