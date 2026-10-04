/**
 * 🌐 9Router Central AI Gateway Client (api.meuu.club)
 * Hermes v2 Universal AI Client (Node.js / ESM)
 */

import fs from 'fs';

const BASE_URL = process.env.OPENAI_BASE_URL || 'https://api.meuu.club/v1';
const API_KEY = process.env.OPENAI_API_KEY || 'sk-07ccde1e709eb2ca-e05r6c-a11b5d7c';
const DEFAULT_CHAT_MODEL = process.env.DEFAULT_CHAT_MODEL || 'ag/claude-sonnet-4-6';
const DEFAULT_FAST_MODEL = process.env.DEFAULT_FAST_MODEL || 'ag/gemini-2.5-flash';
const DEFAULT_TTS_VOICE = process.env.DEFAULT_TTS_VOICE || 'edge-tts/th-TH-PremwadeeNeural';

export class MeuuAIGateway {
  constructor(apiKey = API_KEY, baseUrl = BASE_URL) {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.headers = {
      'Authorization': `Bearer ${this.apiKey}`,
      'Content-Type': 'application/json',
      'User-Agent': 'Hermes-v2/1.0.0',
    };
  }

  async chat({ messages, model = DEFAULT_CHAT_MODEL, temperature = 0.7, max_tokens = 4096, stream = false }) {
    const res = await fetch(`${this.baseUrl}/chat/completions`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        model,
        messages,
        temperature,
        max_tokens,
        stream,
      }),
    });

    if (!res.ok) {
      throw new Error(`9Router Error ${res.status}: ${await res.text()}`);
    }

    const text = await res.text();
    if (text.startsWith('data:')) {
      const lines = text.split('\n');
      let combined = '';
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data:') && !trimmed.includes('[DONE]')) {
          const jsonStr = trimmed.slice(5).trim();
          if (jsonStr) {
            try {
              const chunk = JSON.parse(jsonStr);
              if (chunk.choices?.[0]?.delta?.content) {
                combined += chunk.choices[0].delta.content;
              }
            } catch (_) {}
          }
        }
      }
      return combined;
    }

    const data = JSON.parse(text);
    return data.choices[0].message.content;
  }

  async fastChat(prompt, systemPrompt = null) {
    const messages = [];
    if (systemPrompt) {
      messages.push({ role: 'system', content: systemPrompt });
    }
    messages.push({ role: 'user', content: prompt });
    return this.chat({ messages, model: DEFAULT_FAST_MODEL, stream: false });
  }

  async textToSpeech(text, outputPath = 'output.mp3', voice = DEFAULT_TTS_VOICE) {
    const res = await fetch(`${this.baseUrl}/audio/speech`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        model: voice,
        input: text,
        voice,
      }),
    });

    if (!res.ok) {
      throw new Error(`9Router TTS Error ${res.status}: ${await res.text()}`);
    }

    const buffer = Buffer.from(await res.arrayBuffer());
    await fs.promises.writeFile(outputPath, buffer);
    return outputPath;
  }

  async listModels() {
    const res = await fetch(`${this.baseUrl}/models`, {
      method: 'GET',
      headers: this.headers,
    });
    if (!res.ok) {
      throw new Error(`9Router Error ${res.status}: ${await res.text()}`);
    }
    const data = await res.json();
    return data.data || [];
  }
}
