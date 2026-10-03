"""
🌐 9Router Central AI Gateway Client (api.meuu.club)
Hermes v2 Universal AI Client: Supports Claude Sonnet 4.6, Gemini 2.5 Flash, and Thai TTS
"""

import os
import requests
from typing import Generator, Optional, Dict, Any, List

# Load configuration from environment or fallback to defaults
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.meuu.club/v1")
API_KEY = os.getenv("OPENAI_API_KEY", "sk-07ccde1e709eb2ca-e05r6c-a11b5d7c")
DEFAULT_CHAT_MODEL = os.getenv("DEFAULT_CHAT_MODEL", "ag/claude-sonnet-4-6")
DEFAULT_FAST_MODEL = os.getenv("DEFAULT_FAST_MODEL", "ag/gemini-2.5-flash")
DEFAULT_TTS_VOICE = os.getenv("DEFAULT_TTS_VOICE", "th-TH-PremwadeeNeural")


class MeuuAIGateway:
    """Universal client for 9Router AI Infrastructure Gateway"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or API_KEY
        self.base_url = (base_url or BASE_URL).rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
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
        response = requests.post(endpoint, headers=self.headers, json=payload, stream=stream)
        response.raise_for_status()

        if stream:
            return response.iter_lines()
        
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def fast_chat(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """High-speed query using Gemini 2.5 Flash"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages=messages, model=DEFAULT_FAST_MODEL)

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
        response = requests.post(endpoint, headers=self.headers, json=payload)
        response.raise_for_status()

        with open(output_filepath, "wb") as f:
            f.write(response.content)

        return output_filepath

    def list_models(self) -> List[Dict[str, Any]]:
        """List all available models on 9Router Gateway"""
        endpoint = f"{self.base_url}/models"
        response = requests.get(endpoint, headers=self.headers)
        response.raise_for_status()
        return response.json().get("data", [])


if __name__ == "__main__":
    client = MeuuAIGateway()
    print("Testing connection to 9Router Gateway...")
    try:
        reply = client.fast_chat("สวัสดีจ้า ขอข้อความสั้นๆ 1 บรรทัดทดสอบระบบหน่อยนะ")
        print(f"✅ AI Response: {reply}")
    except Exception as e:
        print(f"❌ Error: {e}")
