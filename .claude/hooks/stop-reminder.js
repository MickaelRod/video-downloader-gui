#!/usr/bin/env node
// Hook Stop : affiche a l'utilisateur (message non bloquant) :
//  1. le travail non sauvegarde : fichiers modifies non commites, fichiers non suivis, commits non pousses
//     (un seul rappel par etat et par session ; .claude/status-ignore = prefixes de chemins a ne pas signaler) ;
//  2. un rappel de point d'etape quand la session dure depuis 3 h (puis 6 h, 9 h...).
//     Un hook ne voit pas la duree de la session : on la reconstitue depuis le premier evenement Stop. Si plus de
//     90 minutes s'ecoulent sans activite, le compteur repart de zero (session laissee ouverte la nuit).
// Ne bloque jamais, ne relance jamais Claude.
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const THRESHOLD_MS = 3 * 3600 * 1000; // point d'etape toutes les 3 h
const IDLE_RESET_MS = 90 * 60 * 1000; // inactivite qui remet le compteur a zero

try {
  let input = {};
  try { input = JSON.parse(fs.readFileSync(0, 'utf8')); } catch (e) { process.exit(0); }
  if (input.stop_hook_active) process.exit(0);

  const projectDir = process.env.CLAUDE_PROJECT_DIR || input.cwd || process.cwd();
  const cwd = input.cwd || projectDir;
  const sid = String(input.session_id || 'sans-session').replace(/[^\w-]/g, '');
  const key = `${sid}-${Buffer.from(projectDir).toString('hex').slice(-16)}`;

  // --- 1. Duree de la session
  const timeReminder = () => {
    const now = Number(process.env.CLAUDE_STOP_NOW) || Date.now();
    const file = path.join(os.tmpdir(), `claude-time-${key}.json`);
    let st = { start: now, last: now, n: 0 };
    try {
      const s = JSON.parse(fs.readFileSync(file, 'utf8'));
      if (now - s.last <= IDLE_RESET_MS) st = s;
    } catch (e) { /* premier evenement de la session */ }
    st.last = now;
    const n = Math.floor((now - st.start) / THRESHOLD_MS);
    let msg = '';
    if (n > st.n) {
      const hours = Math.round(((now - st.start) / 3600000) * 10) / 10;
      msg = `Session active depuis environ ${hours} h : bon moment pour un point d'etape (committer, mettre la doc a jour, faire un compte-rendu) ou reprendre dans une nouvelle session.`;
      st.n = n;
    }
    try { fs.writeFileSync(file, JSON.stringify(st)); } catch (e) { /* ignore */ }
    return msg;
  };

  // --- 2. Travail non sauvegarde
  const gitReminder = () => {
    const git = (args) => spawnSync('git', args, { cwd, encoding: 'utf8', timeout: 8000 });
    if (git(['rev-parse', '--is-inside-work-tree']).stdout.trim() !== 'true') return '';

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

    const memo = path.join(os.tmpdir(), `claude-stop-${key}.txt`);
    const fingerprint = JSON.stringify([branch, modified, untracked, ahead]);
    const last = fs.existsSync(memo) ? fs.readFileSync(memo, 'utf8') : '';

    const dirty = modified.length || untracked.length || ahead;
    if (!dirty) { try { fs.writeFileSync(memo, ''); } catch (e) { /* ignore */ } return ''; }
    if (fingerprint === last) return '';
    try { fs.writeFileSync(memo, fingerprint); } catch (e) { /* ignore */ }

    const names = (arr) => arr.slice(0, 4).join(', ') + (arr.length > 4 ? `, +${arr.length - 4}` : '');
    const parts = [];
    if (modified.length) parts.push(`${modified.length} fichier(s) modifie(s) non commite(s) (${names(modified)})`);
    if (untracked.length) parts.push(`${untracked.length} fichier(s) non suivi(s) (${names(untracked)})`);
    if (ahead) parts.push(`${ahead} commit(s) non pousse(s) sur ${branch}`);
    return 'Rappel : ' + parts.join(', ') + '.';
  };

  const messages = [gitReminder(), timeReminder()].filter(Boolean);
  if (messages.length) process.stdout.write(JSON.stringify({ systemMessage: messages.join(' ') }));
} catch (e) {
  process.exit(0); // jamais bloquant
}
