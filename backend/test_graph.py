import asyncio
from app.agent.core.orchestrator import build_pipeline_graph
from app.models.schemas import InternalPipelineModel

async def main():
    graph = build_pipeline_graph()
    initial_state = InternalPipelineModel(
        session_id="test-session",
        dataset_path="f:\\source\\DS-Copilot\\data\\iris.csv",
        project_name="IrisTest",
        user_settings={
            "llm_provider": "local",
            "model_name": "llama-3",
        }
    ).model_dump()

    try:
        async for event in graph.astream(initial_state):
            print(event)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
