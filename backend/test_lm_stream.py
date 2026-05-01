"""Quick test: stream from LM Studio via LangChain ChatOpenAI."""
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

async def main():
    model = ChatOpenAI(
        model="qwen/qwen3-vl-4b",
        base_url="http://localhost:1234/v1",
        api_key="local-api-key",
        temperature=0.1,
        max_tokens=100,
        streaming=True,
    )

    messages = [
        SystemMessage(content="You are a helpful assistant. Be concise."),
        HumanMessage(content="Say hello in one sentence."),
    ]

    print("Streaming chunks:")
    full = ""
    async for chunk in model.astream(messages):
        text = chunk.content or ""
        print(f"  chunk: {repr(text)}")
        full += text

    print(f"\nFull response: {repr(full)}")
    print("SUCCESS" if full.strip() else "EMPTY RESPONSE - THIS IS THE BUG")

asyncio.run(main())
