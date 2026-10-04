#!/usr/bin/env node
// Garde-fou PreToolUse (Bash) : bloque les commandes destructrices,
// demande confirmation avant toute fusion/push vers main (mode "branch").
// Mode lu dans .claude/git-mode : "branch" (defaut) ou "main" (exception).
// En cas d'erreur interne du hook : demande confirmation (jamais de passage silencieux).
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const decide = (decision, reason) => {
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: decision,
      permissionDecisionReason: reason,
    },
  }));
  process.exit(0);
};

try {
  main();
} catch (e) {
  decide('ask', 'Hook guard-git en erreur (' + e.message + ') : confirmation requise par precaution.');
}

function main() {
  let input = {};
  try { input = JSON.parse(fs.readFileSync(0, 'utf8')); } catch (e) { process.exit(0); }
  if (input.tool_name && input.tool_name !== 'Bash') process.exit(0);
  const raw = (input.tool_input && input.tool_input.command) || '';
  if (!raw) process.exit(0);

  const projectDir = process.env.CLAUDE_PROJECT_DIR || input.cwd || process.cwd();
  const cwd = input.cwd || projectDir;

  let mode = 'branch';
  try {
    const m = fs.readFileSync(path.join(projectDir, '.claude', 'git-mode'), 'utf8').trim();
    if (m === 'main' || m === 'branch') mode = m;
  } catch (e) { /* defaut : branch */ }

  // Retire heredocs et chaines entre guillemets (ex. messages de commit)
  // pour ne pas declencher sur du texte.
  const cmd = raw
    .replace(/<<-?\s*['"]?(\w+)['"]?[\s\S]*?\n\s*\1\b/g, ' ')
    .replace(/"(?:[^"\\]|\\.)*"/g, '""')
    .replace(/'[^']*'/g, "''");

  const segments = cmd.split(/&&|\|\||;|\||\n/).map((s) => s.trim()).filter(Boolean);

  const currentBranch = () => {
    try {
      return execSync('git rev-parse --abbrev-ref HEAD', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
    } catch (e) { return null; }
  };
  // Branche inconnue => prudence : on la traite comme main.
  const onMain = () => { const b = currentBranch(); return b === null || /^(main|master)$/.test(b); };
  const isMain = (t) => /^(\+?[\w\/.-]*:)?(main|master)$/.test(t) || /^refs\/heads\/(main|master)$/.test(t);

  const touchesMainViaCheckout = segments.some((s) => /^git\s+(checkout|switch)\b.*\b(main|master)\b/.test(s));

  for (const seg of segments) {
    const tokens = seg.split(/\s+/);

    // rm -rf (toutes variantes de flags)
    if (tokens[0] === 'rm') {
      const flags = tokens.slice(1).filter((t) => t.startsWith('-')).join(' ');
      const rec = /--recursive/.test(flags) || /(^|\s)-[a-zA-Z]*[rR]/.test(flags);
      const frc = /--force/.test(flags) || /(^|\s)-[a-zA-Z]*f/.test(flags);
      if (rec && frc) decide('deny', 'BLOQUE : rm -rf interdit par le hook. Supprime a la main ou demande une alternative ciblee.');
    }

    if (tokens[0] !== 'git' && tokens[0] !== 'gh') continue;
    const args = tokens.slice(1);
    const sub = args.find((a) => !a.startsWith('-'));

    if (tokens[0] === 'git' && sub === 'reset' && args.includes('--hard')) {
      decide('deny', 'BLOQUE : git reset --hard interdit par le hook.');
    }

    if (tokens[0] === 'git' && sub === 'push') {
      const rest = args.slice(args.indexOf('push') + 1);
      const flags = rest.filter((a) => a.startsWith('-'));
      const refs = rest.filter((a) => !a.startsWith('-'));
      if (flags.some((f) => /^--force/.test(f) || /^-[a-zA-Z]*f/.test(f)) || refs.some((r) => r.startsWith('+'))) {
        decide('deny', 'BLOQUE : push --force interdit par le hook.');
      }
      if (flags.some((f) => f === '-d' || f === '--delete') || refs.some((r) => /^:\S+/.test(r))) {
        decide('deny', 'BLOQUE : suppression de branche distante interdite par le hook.');
      }
      if (mode === 'branch') {
        const explicit = refs.slice(1); // refs[0] = remote
        const toMain = explicit.length
          ? explicit.some(isMain)
          : onMain();
        if (toMain) decide('ask', 'Push vers main (= mise en production) : confirmation requise.');
      }
    }

    if (tokens[0] === 'git' && sub === 'merge' && mode === 'branch') {
      if (onMain() || touchesMainViaCheckout) {
        decide('ask', 'Fusion vers main (= mise en production) : confirmation requise.');
      }
    }

    if (tokens[0] === 'gh' && sub === 'pr' && args.includes('merge') && mode === 'branch') {
      decide('ask', 'Fusion de PR (vers main) : confirmation requise.');
    }
  }

  process.exit(0);
}
