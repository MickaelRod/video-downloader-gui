#!/usr/bin/env node
// Hook Stop : rappelle (message visible par l'utilisateur, jamais bloquant) le travail non sauvegarde :
// fichiers modifies non commites, fichiers non suivis, commits non pousses.
// - Un seul rappel par etat et par session (silence si rien n'a change depuis le dernier rappel).
// - .claude/status-ignore : prefixes de chemins a ne pas signaler (un par ligne, # = commentaire).
// - Ne bloque jamais, ne relance jamais Claude.
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

try {
  let input = {};
  try { input = JSON.parse(fs.readFileSync(0, 'utf8')); } catch (e) { process.exit(0); }
  if (input.stop_hook_active) process.exit(0);

  const projectDir = process.env.CLAUDE_PROJECT_DIR || input.cwd || process.cwd();
  const cwd = input.cwd || projectDir;
  const git = (args) => spawnSync('git', args, { cwd, encoding: 'utf8', timeout: 8000 });
  if (git(['rev-parse', '--is-inside-work-tree']).stdout.trim() !== 'true') process.exit(0);

  let ignore = [];
  try {
    ignore = fs.readFileSync(path.join(projectDir, '.claude', 'status-ignore'), 'utf8')
      .split(/\r?\n/).map((l) => l.trim()).filter((l) => l && !l.startsWith('#'));
  } catch (e) { /* aucun fichier a ignorer */ }

  const branch = git(['branch', '--show-current']).stdout.trim() || '(HEAD detache)';
  const lines = git(['status', '--porcelain']).stdout.split('\n').filter(Boolean).map((l) => ({
    untracked: l.startsWith('??'),
    file: l.slice(3).replace(/^.* -> /, '').replace(/^"|"$/g, '').trim(),
  })).filter((x) => !ignore.some((p) => x.file.startsWith(p)));
  // Git sous Windows (autocrlf) marque parfois "modifie" un fichier au contenu identique : on confirme par un vrai diff.
  const reallyChanged = (f) => git(['diff', '--quiet', '--', f]).status !== 0 || git(['diff', '--cached', '--quiet', '--', f]).status !== 0;
  const modified = lines.filter((x) => !x.untracked).map((x) => x.file).filter(reallyChanged);
  const untracked = lines.filter((x) => x.untracked).map((x) => x.file);

  let ahead = 0;
  const up = git(['rev-list', '--count', '@{u}..HEAD']);
  if (up.status === 0) ahead = Number(up.stdout.trim()) || 0;

  const sid = String(input.session_id || 'sans-session').replace(/[^\w-]/g, '');
  const memo = path.join(os.tmpdir(), `claude-stop-${sid}-${Buffer.from(projectDir).toString('hex').slice(-16)}.txt`);
  const fingerprint = JSON.stringify([branch, modified, untracked, ahead]);
  const last = fs.existsSync(memo) ? fs.readFileSync(memo, 'utf8') : '';

  const dirty = modified.length || untracked.length || ahead;
  if (!dirty) { try { fs.writeFileSync(memo, ''); } catch (e) { /* ignore */ } process.exit(0); }
  if (fingerprint === last) process.exit(0);
  try { fs.writeFileSync(memo, fingerprint); } catch (e) { /* ignore */ }

  const names = (arr) => arr.slice(0, 4).join(', ') + (arr.length > 4 ? `, +${arr.length - 4}` : '');
  const parts = [];
  if (modified.length) parts.push(`${modified.length} fichier(s) modifie(s) non commite(s) (${names(modified)})`);
  if (untracked.length) parts.push(`${untracked.length} fichier(s) non suivi(s) (${names(untracked)})`);
  if (ahead) parts.push(`${ahead} commit(s) non pousse(s) sur ${branch}`);

  process.stdout.write(JSON.stringify({ systemMessage: 'Rappel : ' + parts.join(', ') + '.' }));
} catch (e) {
  process.exit(0); // jamais bloquant
}
