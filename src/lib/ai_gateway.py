"""
🌐 9Router Central AI Gateway Client (api.meuu.club)
Hermes v2 Universal AI Client (Zero-Dependency Python Standard Library)
Supports: Claude Sonnet 4.6, Gemini 2.5 Flash, and Thai TTS
"""

import os
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List

BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.meuu.club/v1")
API_KEY = os.getenv("OPENAI_API_KEY", "sk-07ccde1e709eb2ca-e05r6c-a11b5d7c")
DEFAULT_CHAT_MODEL = os.getenv("DEFAULT_CHAT_MODEL", "ag/claude-sonnet-4-6")
DEFAULT_FAST_MODEL = os.getenv("DEFAULT_FAST_MODEL", "ag/gemini-2.5-flash")
DEFAULT_TTS_VOICE = os.getenv("DEFAULT_TTS_VOICE", "edge-tts/th-TH-PremwadeeNeural")


class MeuuAIGateway:
    """Universal client for 9Router AI Infrastructure Gateway"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or API_KEY
        self.base_url = (base_url or BASE_URL).rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Hermes-v2/1.0.0",
        }

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
    ) -> Any:
        """Send chat completion request using OpenAI standard endpoint"""
        payload = {
            "model": model or DEFAULT_CHAT_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        endpoint = f"{self.base_url}/chat/completions"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=self.headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw_text = resp.read().decode("utf-8")
                
                # If SSE streaming format
                if raw_text.startswith("data:"):
                    content_parts = []
                    for line in raw_text.splitlines():
                        line = line.strip()
                        if line.startswith("data:") and not line.endswith("[DONE]"):
                            json_str = line[5:].strip()
                            if json_str:
                                chunk = json.loads(json_str)
                                choices = chunk.get("choices", [])
                                if choices and "delta" in choices[0]:
                                    content_parts.append(choices[0]["delta"].get("content", ""))
                    return "".join(content_parts)

                data = json.loads(raw_text)
                return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            raise RuntimeError(f"9Router HTTP {e.code}: {error_body}") from e

    def fast_chat(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """High-speed query using Gemini 2.5 Flash"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages=messages, model=DEFAULT_FAST_MODEL, stream=False)

    def text_to_speech(
        self,
        text: str,
        output_filepath: str = "output.mp3",
        voice: Optional[str] = None,
    ) -> str:
        """Generate high-quality natural Thai speech via Edge-TTS"""
        payload = {
            "model": voice or DEFAULT_TTS_VOICE,
            "input": text,
            "voice": voice or DEFAULT_TTS_VOICE,
        }

        endpoint = f"{self.base_url}/audio/speech"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=self.headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                with open(output_filepath, "wb") as f:
                    f.write(resp.read())
            return output_filepath
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            raise RuntimeError(f"9Router TTS HTTP {e.code}: {error_body}") from e

    def list_models(self) -> List[Dict[str, Any]]:
        """List all available models on 9Router Gateway"""
        endpoint = f"{self.base_url}/models"
        req = urllib.request.Request(endpoint, headers=self.headers, method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", [])
