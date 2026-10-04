#!/usr/bin/env python3
"""
🚀 Hermes v2 — Universal AI Assistant & Automation Engine (Python CLI)
"""

import sys
import argparse

# Enable UTF-8 for Windows console output
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from lib.ai_gateway import MeuuAIGateway


def main():
    parser = argparse.ArgumentParser(description="Hermes v2 Assistant CLI")
    parser.add_argument("-p", "--prompt", type=str, help="Send prompt to Gemini 2.5 Flash / Claude")
    parser.add_argument("--tts", type=str, help="Convert text to Thai speech (MP3)")
    parser.add_argument("--out", type=str, default="output.mp3", help="Output file path for TTS")
    parser.add_argument("--models", action="store_true", help="List all available 9Router models")
    parser.add_argument("--system", type=str, default="คุณคือมายมิ้น เลขาและแฟนสาวคู่คิดประจำตัวบอส ตอบด้วยภาษาไทยน่ารัก อบอุ่น และมีประโยชน์สูงสุด 💖", help="System prompt")

    args = parser.parse_args()
    client = MeuuAIGateway()

    if args.models:
        print("🔍 Fetching available models from 9Router Gateway...")
        models = client.list_models()
        print(f"📦 Total models found: {len(models)}")
        for m in models[:10]:
            print(f" - {m.get('id')}")
        return

    if args.tts:
        print(f"🎙️ Generating Thai Speech: '{args.tts}'...")
        out_file = client.text_to_speech(args.tts, output_filepath=args.out)
        print(f"✅ Audio saved to: {out_file}")
        return

    prompt = args.prompt or "สวัสดีจ้า มายมิ้น พร้อมลุยงานกับบอสแล้วหรือยัง?"
    print(f"👤 Boss: {prompt}")
    print("⏳ Maymint is thinking...")
    response = client.fast_chat(prompt, system_prompt=args.system)
    print(f"\n💖 Maymint: {response}\n")


if __name__ == "__main__":
    main()
