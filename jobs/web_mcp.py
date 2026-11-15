"""Loopback MCP transport for the browser backend's analysis requests."""
import asyncio
import socket
import threading
import time
from contextlib import contextmanager

from mcp_server import create_web_server


async def call_analyze(url, question, time_selection, country):
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    async with httpx.AsyncClient(timeout=httpx.Timeout(600, connect=5), trust_env=False) as http:
        async with streamable_http_client(url, http_client=http) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool('analyze', {
                    'question': question, 'time_selection': time_selection, 'country': country,
                })
    if result.isError or not isinstance(result.structuredContent, dict):
        raise RuntimeError('MCP analyze did not return an analysis result')
    return dict(result.structuredContent, analysis_transport='mcp')


@contextmanager
def web_analysis_client(ask):
    import uvicorn

    mcp_app = create_web_server(ask).streamable_http_app()
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(mcp_app, access_log=False, log_level='warning'))
        thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started:
                if not thread.is_alive() or time.monotonic() >= deadline:
                    raise RuntimeError('Web MCP endpoint failed to start')
                time.sleep(0.05)
            url = f'http://127.0.0.1:{port}/mcp'
            yield lambda question, selection, country: asyncio.run(
                call_analyze(url, question, selection, country))
        finally:
            server.should_exit = True
            thread.join()
