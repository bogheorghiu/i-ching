#!/usr/bin/env bun
// Usage: bun src/cli.ts <instructions.md> <task.md>   (events to stderr as JSONL, final text to stdout)
import { runAgent, DEFAULTS } from './agent.js';
const [instr, task] = process.argv.slice(2);
if (!instr || !task) { console.error('usage: cli.ts <instructions.md> <task.md>'); process.exit(2); }
const log = Bun.file(`${process.env.AGENT_WORKDIR ?? '.'}/agent-log.jsonl`).writer();
const ev = (e: object) => { const line = JSON.stringify({ ts: new Date().toISOString(), ...e }); log.write(line + '\n'); log.flush(); console.error(line); };
ev({ t: 'start', ...DEFAULTS });
// A dropped connection (container restart, proxy blip) restarts the run up to 3 times. The agent keeps
// no memory across a restart, so the task must tell it to resume from its own files.
let attempt = 0;
for (;;) {
  try { const r = await runAgent(await Bun.file(instr).text(), await Bun.file(task).text(), ev); ev({ t: 'done', usage: r.usage, id: r.id }); console.log(r.text); break; }
  catch (e: any) { const net = /ECONN|socket|fetch failed|network/i.test(String(e?.message)); ev({ t: 'error', message: e?.message, status: e?.status, attempt });
    if (!net || ++attempt > 3) { await log.end(); process.exit(1); } await Bun.sleep(30000 * attempt); }
}
await log.end();
