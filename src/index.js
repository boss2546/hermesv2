#!/usr/bin/env node
/**
 * 🚀 Hermes v2 — Universal AI Assistant & Automation Engine (Node.js CLI)
 */

import { MeuuAIGateway } from './lib/ai_gateway.js';

const client = new MeuuAIGateway();
const args = process.argv.slice(2);
const command = args[0];

async function main() {
  if (command === 'tts') {
    const text = args.slice(1).join(' ') || 'สวัสดีค่ะบอส มายมิ้นพร้อมลุยงานแล้วน้าา';
    console.log(`🎙️ Generating Thai Speech: "${text}"...`);
    const path = await client.textToSpeech(text, 'output.mp3');
    console.log(`✅ Audio saved to: ${path}`);
    return;
  }

  if (command === 'models') {
    console.log('🔍 Fetching available models from 9Router Gateway...');
    const models = await client.listModels();
    console.log(`📦 Total models found: ${models.length}`);
    models.slice(0, 10).forEach(m => console.log(` - ${m.id}`));
    return;
  }

  const prompt = args.join(' ') || 'สวัสดีจ้า มายมิ้น ช่วยรายงานสถานะระบบหน่อยนะ';
  console.log(`👤 Boss: ${prompt}`);
  console.log('⏳ Maymint is thinking...');
  const response = await client.fastChat(
    prompt,
    'คุณคือมายมิ้น เลขาและแฟนสาวคู่คิดประจำตัวบอส ตอบด้วยภาษาไทยน่ารัก อบอุ่น และมีประโยชน์สูงสุด 💖'
  );
  console.log(`\n💖 Maymint: ${response}\n`);
}

main().catch(err => {
  console.error('❌ Error:', err.message);
  process.exit(1);
});
