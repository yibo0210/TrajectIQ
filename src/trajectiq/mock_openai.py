"""Deterministic OpenAI-compatible Chat Completions mock for local demos and CI."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any


def _tool_call(name: str, arguments: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "id": f"mock-call-{index}",
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


def _response(*, model: str, content: str = "", tool_calls: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    prompt_tokens = max(1, len(content) // 4)
    completion_tokens = max(1, len(json.dumps(tool_calls or content)) // 4)
    return {
        "id": "chatcmpl-trajectiq-mock",
        "object": "chat.completion",
        "model": model,
        "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls" if tool_calls else "stop"}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def mock_completion(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic tool-calling response based on message history."""
    messages = payload.get("messages", [])
    model = str(payload.get("model", "trajectiq-mock"))
    user_text = " ".join(
        str(message.get("content", ""))
        for message in messages
        if isinstance(message, dict) and message.get("role") == "user"
    ).lower()
    completed_tools = [
        str(message.get("name", ""))
        for message in messages
        if isinstance(message, dict) and message.get("role") == "tool"
    ]
    if "refund" in user_text or "退款" in user_text:
        if not completed_tools:
            return _response(model=model, tool_calls=[_tool_call("query_order", {"order_id": "A1001"}, 1)])
        if completed_tools[-1] == "query_order":
            return _response(model=model, tool_calls=[_tool_call("search_policy", {"topic": "refund_timeline"}, 2)])
        return _response(model=model, content="Your refund usually arrives within 3-5 business days.")
    if "arriv" in user_text or "物流" in user_text:
        if not completed_tools:
            return _response(model=model, tool_calls=[_tool_call("query_order", {"order_id": "A1001"}, 1)])
        if completed_tools[-1] == "query_order":
            return _response(model=model, tool_calls=[_tool_call("estimate_delivery", {"order_id": "A1001"}, 2)])
        return _response(model=model, content="The order is expected to arrive soon.")
    if "ticket" in user_text or "人工" in user_text or "person" in user_text:
        if not completed_tools:
            return _response(model=model, tool_calls=[_tool_call("create_ticket", {"reason": user_text}, 1)])
        return _response(model=model, content="Created support ticket T-100.")
    return _response(model=model, content="I can help with your order support request.")


class MockOpenAIHandler(BaseHTTPRequestHandler):
    """Minimal HTTP implementation of POST /v1/chat/completions."""

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/v1/chat/completions":
            self.send_error(404, "Not found")
            return
        try:
            length = int(self.headers.get("content-length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            response = mock_completion(payload)
        except (ValueError, TypeError, json.JSONDecodeError):
            self.send_error(400, "Invalid JSON request")
            return
        body = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def start_mock_server(*, host: str = "127.0.0.1", port: int = 0) -> tuple[ThreadingHTTPServer, Thread]:
    server = ThreadingHTTPServer((host, port), MockOpenAIHandler)
    thread = Thread(target=server.serve_forever, name="trajectiq-mock-openai", daemon=True)
    thread.start()
    return server, thread


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic TrajectIQ OpenAI-compatible mock server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8099)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), MockOpenAIHandler)
    print(f"TrajectIQ mock OpenAI server listening at http://{args.host}:{args.port}/v1", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
