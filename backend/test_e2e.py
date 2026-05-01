import asyncio
import httpx
import websockets
import json
import sys

async def run_test():
    async with httpx.AsyncClient() as client:
        print("1. Creating session...")
        res = await client.post('http://127.0.0.1:8000/api/sessions', json={'project_name': 'test'})
        print(f"Session Response: {res.json()}")
        session_id = res.json().get('id', res.json().get('session_id'))
        print(f'Session: {session_id}')
        
        print("2. Uploading file...")
        with open('F:/source/DS-Copilot/backend/tests/fixtures/sample_data.csv', 'rb') as f:
            res = await client.post(f'http://127.0.0.1:8000/api/upload', files={'file': ('sample.csv', f, 'text/csv')}, data={'session_id': session_id})
        print(f'Upload Status: {res.status_code}')

        print("3. Starting pipeline & connecting WS...")
        res = await client.post('http://127.0.0.1:8000/api/pipeline/start', json={'session_id': session_id})
        print(f'Pipeline Trigger Status: {res.status_code}')

    # Connect WebSocket
    try:
        async with websockets.connect(f'ws://127.0.0.1:8000/ws/{session_id}') as ws:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=60)
                data = json.loads(msg)
                content = str(data.get('content', ''))
                print(f"WS [{data['type']}]: {content[:80].replace(chr(10), ' ')}")
                if data['type'] == 'result' or data['type'] == 'error':
                    break
    except asyncio.TimeoutError:
         print("WS timeout!")
    except Exception as e:
        print(f'WS Error: {e}')

asyncio.run(run_test())
