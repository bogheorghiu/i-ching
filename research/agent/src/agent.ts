import { OpenRouter } from '@openrouter/agent';
import { stepCountIs, maxCost } from '@openrouter/agent/stop-conditions';
import { tools } from './tools/index.js';

// Claude through OpenRouter, pinned to Anthropic so it runs on the owner's own Anthropic key (BYOK).
export const DEFAULTS = { model: process.env.AGENT_MODEL ?? 'anthropic/claude-sonnet-5.5', maxSteps: Number(process.env.AGENT_MAX_STEPS ?? 150), maxCost: Number(process.env.AGENT_MAX_COST ?? 8), reasoning: process.env.AGENT_REASONING ?? null };

export async function runAgent(instructions: string, input: string, onEvent: (e: object) => void) {
  const client = new OpenRouter({ apiKey: process.env.OPENROUTER_API_KEY ?? '' });
  const result = client.callModel({
    model: DEFAULTS.model, instructions, input, tools,
    provider: { only: ['anthropic'] } as any,
    // Anthropic automatic prompt caching: the breakpoint follows the growing conversation, so each step
    // re-reads the earlier context at the cache-read price instead of paying full input again.
    cacheControl: { type: 'ephemeral' },
    ...(process.env.AGENT_REASONING ? { reasoning: { effort: process.env.AGENT_REASONING } as any } : {}),
    stopWhen: [stepCountIs(DEFAULTS.maxSteps), maxCost(DEFAULTS.maxCost)],
  });
  for await (const item of result.getItemsStream()) {
    if (item.type === 'function_call' && item.status === 'completed') onEvent({ t: 'call', name: item.name, args: (item.arguments ?? '').slice(0, 300) });
    else if (item.type === 'function_call_output') onEvent({ t: 'result', out: (typeof item.output === 'string' ? item.output : JSON.stringify(item.output)).slice(0, 300) });
  }
  const r = await result.getResponse();
  return { text: r.outputText ?? '', usage: r.usage, id: (r as any).id };
}
