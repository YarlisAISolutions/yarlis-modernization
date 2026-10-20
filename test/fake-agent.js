// Stand-in agent for tests: reads the prompt (stdin or the file given as argv[2]), records it, and fills one
// requirement into the BRD so the post-check has something real to validate.
import { readFileSync, writeFileSync } from 'node:fs';

const prompt = process.argv[2] ? readFileSync(process.argv[2], 'utf8') : readFileSync(0, 'utf8');
writeFileSync('agent-prompt.md', prompt);
const brd = prompt.match(/in (\S+\/BRD\.md), version/)?.[1];
if (brd) {
  const t = readFileSync(brd, 'utf8').replace('## 11. Business Rules and Policy Constraints',
    '### BR-001: Update an account\n- **Statement:** Staff can change an account\'s credit limit.\n- **Supports:** BO-01\n'
    + '- **Priority:** Unknown (proposed: Must)\n- **Basis:** Derived from code (candidate)\n- **Source:** cbl/ACCTUPD.cbl:24-31\n\n'
    + '## 11. Business Rules and Policy Constraints');
  writeFileSync(brd, t);
}
process.exit(Number(process.env.FAKE_AGENT_EXIT || 0));
