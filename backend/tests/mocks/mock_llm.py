# backend/tests/mocks/mock_llm.py
"""
Mock LLM for testing without API keys.
Returns predefined responses per task type.
"""
from langchain_core.messages import AIMessage
from typing import List, Any


class MockChatModel:
    """Mock chat model that returns predefined responses."""

    RESPONSES = {
        "data_cleaning": '```python\nimport pandas as pd\ndf = pd.read_csv("data.csv")\ndf = df.dropna()\ndf.to_csv("data/processed/cleaned_data.csv", index=False)\nprint(\'{"rows_cleaned": 100, "nulls_removed": 5}\')\n```',
        "eda": '```python\nimport pandas as pd\nimport matplotlib.pyplot as plt\ndf = pd.read_csv("data/processed/cleaned_data.csv")\nplt.figure()\ndf.hist()\nplt.savefig("output/figures/dist.png")\nplt.close()\nprint(\'{"plots_generated": 3}\')\n```',
        "model_selection": '{"task_type":"classification","target_column":"species","recommended_models":[{"name":"RandomForest","class":"sklearn.ensemble.RandomForestClassifier","reason":"Good baseline","priority":1,"hyperparameters":{"n_estimators":100}}],"baseline_model":"LogisticRegression","evaluation_metrics":["accuracy","f1_score"],"cross_validation_strategy":"stratified_kfold","feature_engineering_suggestions":[],"warnings":[]}',
        "code_writing": '```python\nimport pandas as pd\nfrom sklearn.ensemble import RandomForestClassifier\nfrom sklearn.model_selection import train_test_split\nfrom sklearn.metrics import accuracy_score\nimport joblib, os, json\nos.makedirs("output/models", exist_ok=True)\ndf = pd.read_csv("data/processed/cleaned_data.csv")\nX = df.drop("species", axis=1)\ny = df["species"]\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\nmodel = RandomForestClassifier(n_estimators=100)\nmodel.fit(X_train, y_train)\nacc = accuracy_score(y_test, model.predict(X_test))\njoblib.dump(model, "output/models/best_model.pkl")\nprint(json.dumps({"best_model":"RandomForest","accuracy":round(acc,4)}))\n```',
        "testing": '```python\nimport pytest\nimport pandas as pd\nimport joblib\n\ndef test_data_exists():\n    df = pd.read_csv("data/processed/cleaned_data.csv")\n    assert len(df) > 0\n\ndef test_model_exists():\n    model = joblib.load("output/models/best_model.pkl")\n    assert model is not None\n\nif __name__ == "__main__":\n    pytest.main([__file__, "-v"])\n```',
        "optimization": '```python\nprint(\'{"best_score": 0.95, "improvement_pct": 3.2, "best_params": {"n_estimators": 200}}\')\n```',
        "documentation": "Documentation generated successfully.",
        "general": "I'm DS-Copilot, your AI data science assistant. How can I help?",
    }

    def __init__(self, task_type="general"):
        self.task_type = task_type

    async def ainvoke(self, messages, **kwargs):
        response = self.RESPONSES.get(self.task_type, self.RESPONSES["general"])
        return AIMessage(content=response)

    async def astream(self, messages, **kwargs):
        response = self.RESPONSES.get(self.task_type, self.RESPONSES["general"])
        for word in response.split(" "):
            yield AIMessage(content=word + " ")


class MockLLMRouter:
    """Mock LLM Router for testing."""

    def __init__(self):
        self._call_count = 0
        self._available_providers = ["mock"]

    def get_model(self, task_type="general", **kwargs):
        self._call_count += 1
        return MockChatModel(task_type=task_type)

    async def stream_response(self, messages, task_type="general"):
        model = MockChatModel(task_type=task_type)
        async for chunk in model.astream(messages):
            yield chunk.content

    def get_stats(self):
        return {"total_calls": self._call_count, "budget_remaining": 100, "available_providers": ["mock"]}
