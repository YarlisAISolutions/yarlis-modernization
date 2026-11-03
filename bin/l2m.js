#!/usr/bin/env node
// l2m: legacy to modern. Analyze legacy code and generate versioned, traceable BRD/FRD/SRD/RTM documents with
// the agent of your choice. Deterministic steps run the bundled Python scripts; writing is done by the agent.
import { main } from '../lib/cli.js';

try {
  process.exitCode = main(process.argv.slice(2));
} catch (e) {
  console.error(`l2m: ${e.message}`);
  process.exitCode = e.exitCode || (e.code?.startsWith?.('ERR_PARSE_ARGS') ? 2 : 1);
}
