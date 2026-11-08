import { tool } from '@openrouter/agent/tool';
import { z } from 'zod';
import { dirname } from 'path';
import { mkdirSync } from 'fs';

// Everything the agent may touch lives under WORKDIR; paths outside it are refused.
const WORKDIR = process.env.AGENT_WORKDIR ?? process.cwd();
const inside = (p: string) => { const r = Bun.fileURLToPath(new URL(p, `file://${WORKDIR}/`)); if (!r.startsWith(WORKDIR)) throw new Error(`path outside ${WORKDIR}: ${p}`); return r; };

// The DeepSeek tool API. Public, academic queries only: it offers no zero-retention guarantee.
async function deepseek(path: 'search' | 'fetch', body: object) {
  const r = await fetch(`https://api.deepseek.com/v1/tools/${path}`, { method: 'POST',
    headers: { Authorization: `Bearer ${process.env.DEEPSEEK_API_KEY ?? ''}`, 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const text = await r.text();
  return r.ok ? text.slice(0, 60000) : JSON.stringify({ error: r.status, body: text.slice(0, 2000) });
}

export const tools = [
  tool({ name: 'file_read', description: 'Read a text file under the work directory. Returns at most 2000 lines from offset (1-indexed).',
    inputSchema: z.object({ path: z.string(), offset: z.number().optional() }),
    execute: async ({ path, offset }) => { try { const l = (await Bun.file(inside(path)).text()).split('\n'); const s = (offset ?? 1) - 1; return { content: l.slice(s, s + 2000).join('\n'), totalLines: l.length }; } catch (e: any) { return { error: e.message }; } } }),
  tool({ name: 'file_write', description: 'Write (create or overwrite) a text file under the work directory.',
    inputSchema: z.object({ path: z.string(), content: z.string() }),
    execute: async ({ path, content }) => { try { const p = inside(path); mkdirSync(dirname(p), { recursive: true }); await Bun.write(p, content); return { ok: true, bytes: content.length }; } catch (e: any) { return { error: e.message }; } } }),
  tool({ name: 'shell', description: 'Run a shell command in the work directory (timeout 600 s). Use it to run python3 scripts you wrote. Output is truncated to 20000 chars.',
    inputSchema: z.object({ command: z.string(), timeoutSec: z.number().optional() }),
    execute: async ({ command, timeoutSec }) => { const p = Bun.spawn(['bash', '-c', command], { cwd: WORKDIR, stdout: 'pipe', stderr: 'pipe', env: process.env });
      const t = setTimeout(() => p.kill(), (timeoutSec ?? 600) * 1000); const [o, e] = await Promise.all([new Response(p.stdout).text(), new Response(p.stderr).text()]); const code = await p.exited; clearTimeout(t);
      return { exitCode: code, stdout: o.slice(-20000), stderr: e.slice(-5000) }; } }),
  tool({ name: 'deepseek_search', description: 'Web search via DeepSeek. Finds Chinese database records (CNKI, VIP, Wanfang), library catalogues (CiNii), publisher and university pages. Returns JSON results with title, url, snippet, summary.',
    inputSchema: z.object({ query: z.string(), count: z.number().optional(), needContent: z.boolean().optional() }),
    execute: async ({ query, count, needContent }) => deepseek('search', { query, count: count ?? 8, need_content: needContent ?? false }) }),
  tool({ name: 'deepseek_fetch', description: 'Fetch a public URL via DeepSeek and return its content.',
    inputSchema: z.object({ url: z.string() }), execute: async ({ url }) => deepseek('fetch', { url }) }),
] as const;
