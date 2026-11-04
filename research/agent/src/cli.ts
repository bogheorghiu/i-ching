#!/usr/bin/env bun
// Usage: bun src/cli.ts <instructions.md> <task.md>   (events to stderr as JSONL, final text to stdout)
import { runAgent, DEFAULTS } from './agent.js';
const [instr, task] = process.argv.slice(2);
if (!instr || !task) { console.error('usage: cli.ts <instructions.md> <task.md>'); process.exit(2); }
const log = Bun.file(`${process.env.AGENT_WORKDIR ?? '.'}/agent-log.jsonl`).writer();
const ev = (e: object) => { const line = JSON.stringify({ ts: new Date().toISOString(), ...e }); log.write(line + '\n'); log.flush(); console.error(line); };
ev({ t: 'start', ...DEFAULTS });
try { const r = await runAgent(await Bun.file(instr).text(), await Bun.file(task).text(), ev); ev({ t: 'done', usage: r.usage, id: r.id }); console.log(r.text); }
catch (e: any) { ev({ t: 'error', message: e?.message, status: e?.status }); process.exit(1); }
finally { await log.end(); }
