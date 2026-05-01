import asyncio
import httpx
import websockets
import json
import sqlite3

async def run_test():
    async with httpx.AsyncClient() as client:
        print("Uploading file...")
        with open('F:/source/DS-Copilot/backend/tests/fixtures/sample_data.csv', 'rb') as f:
            res = await client.post('http://127.0.0.1:8000/api/upload', files={'file': ('sample_data.csv', f, 'text/csv')})
            filepath = res.json()['filepath']
        print(f"File uploaded to: {filepath}")

        print("Starting pipeline...")
        payload = {
            "dataset_path": filepath,
            "project_name": "lm-studio-test",
            "llm_provider": "openai",
            "model_name": "google/gemma-3-4b",
            "llm_base_url": "http://127.0.0.1:1234/v1",
            "llm_api_key": "lm-studio",
            "execution_env": "local",
            "skip_eda": False
        }
        res = await client.post('http://127.0.0.1:8000/api/pipeline/start', json=payload)
        session_id = res.json()['session_id']
        print(f"Session Id: {session_id}")

    try:
        async with websockets.connect(f'ws://127.0.0.1:8000/ws/{session_id}') as ws:
            jupyter_cells = []
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=180)
                data = json.loads(msg)
                
                if data['type'] == 'code':
                    jupyter_cells.append(data.get('content', ''))
                    print(f"\n[Generated Code]\n{data.get('content', '')[:200]}...")

                if data['type'] == 'error':
                    print(f"Pipeline Error: {data}")
                    break
                
                if data['type'] == 'result':
                    print("Pipeline Finished!")
                    break

            print("\n----- FULL EXTRACTED JUPYTER CODE -----")
            print("\n".join(jupyter_cells))

    except Exception as e:
        print(f'WS Error: {e}')

asyncio.run(run_test())
