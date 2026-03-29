import { defineConfig } from 'vite';
import { config } from 'dotenv';
import { resolve } from 'path';
import { aiProxyPlugin } from './server/ai-proxy';

// Load .env from session-4, fall back to session-02
config({ path: resolve(__dirname, '.env') });
if (!process.env.ANTHROPIC_API_KEY) {
  config({ path: resolve(__dirname, '../session-02/.env') });
}

export default defineConfig({
  plugins: [aiProxyPlugin()],
  server: {
    host: '0.0.0.0',
    port: 4174,
  },
});
