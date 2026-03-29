import type { Plugin } from 'vite';

interface DecideBody {
  provider: 'anthropic' | 'openai';
  prompt: string;
  fighter: unknown;
  opponent: unknown;
  round: number;
  exchange: number;
}

async function callAnthropic(apiKey: string, prompt: string): Promise<{ action: string; reasoning: string }> {
  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: 'claude-haiku-4-5-20251001',
      max_tokens: 150,
      messages: [{ role: 'user', content: prompt }],
    }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Anthropic ${res.status}: ${text.slice(0, 200)}`);
  }

  const json = await res.json() as { content: Array<{ text: string }> };
  const text = json.content?.[0]?.text ?? '';
  return parseAiResponse(text);
}

async function callOpenAI(apiKey: string, prompt: string): Promise<{ action: string; reasoning: string }> {
  const res = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: 'gpt-4o-mini',
      max_tokens: 150,
      messages: [{ role: 'user', content: prompt }],
    }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`OpenAI ${res.status}: ${text.slice(0, 200)}`);
  }

  const json = await res.json() as { choices: Array<{ message: { content: string } }> };
  const text = json.choices?.[0]?.message?.content ?? '';
  return parseAiResponse(text);
}

function parseAiResponse(text: string): { action: string; reasoning: string } {
  // Try to extract JSON from the response
  const jsonMatch = text.match(/\{[\s\S]*?"action"\s*:\s*"([^"]+)"[\s\S]*?\}/);
  if (jsonMatch) {
    try {
      const parsed = JSON.parse(jsonMatch[0]) as { action?: string; reasoning?: string };
      return {
        action: parsed.action ?? 'guard',
        reasoning: parsed.reasoning ?? '',
      };
    } catch { /* fall through */ }
  }

  // Fallback: look for a known action name anywhere in the text
  const actions = [
    'jab', 'cross', 'hook', 'earSlap', 'uppercut', 'bodyShot',
    'kickL', 'kickR', 'slip', 'block', 'duck', 'parry',
    'advance', 'retreat', 'guard',
  ];
  for (const action of actions) {
    if (text.includes(action)) {
      return { action, reasoning: text.slice(0, 100) };
    }
  }

  return { action: 'guard', reasoning: 'Could not parse AI response' };
}

export function aiProxyPlugin(): Plugin {
  return {
    name: 'ai-proxy',
    configureServer(server) {
      server.middlewares.use('/api/decide', async (req, res) => {
        if (req.method !== 'POST') {
          res.statusCode = 405;
          res.end('Method not allowed');
          return;
        }

        const chunks: Buffer[] = [];
        for await (const chunk of req) {
          chunks.push(chunk as Buffer);
        }
        const body = JSON.parse(Buffer.concat(chunks).toString()) as DecideBody;

        const anthropicKey = process.env.ANTHROPIC_API_KEY ?? '';
        const openaiKey = process.env.OPENAI_API_KEY ?? '';

        try {
          let result: { action: string; reasoning: string };

          if (body.provider === 'anthropic' && anthropicKey) {
            result = await callAnthropic(anthropicKey, body.prompt);
          } else if (body.provider === 'openai' && openaiKey) {
            result = await callOpenAI(openaiKey, body.prompt);
          } else {
            throw new Error(`No API key for provider: ${body.provider}`);
          }

          res.setHeader('content-type', 'application/json');
          res.end(JSON.stringify({
            action: result.action,
            reasoning: result.reasoning,
            source: 'remote',
          }));
        } catch (err) {
          console.error(`[ai-proxy] ${body.provider} error:`, (err as Error).message);
          res.setHeader('content-type', 'application/json');
          res.end(JSON.stringify({
            action: 'guard',
            reasoning: (err as Error).message,
            source: 'fallback',
          }));
        }
      });
    },
  };
}
