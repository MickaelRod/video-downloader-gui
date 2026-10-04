#!/usr/bin/env node
// Hook SessionStart : injecte l'etat Git du depot comme contexte au demarrage de session.
// Mode lu dans .claude/git-mode ("branch" par defaut ou "main"). Ne bloque jamais la session.
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const emit = (text) => {
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: { hookEventName: 'SessionStart', additionalContext: text },
  }));
  process.exit(0);
};

try {
  let input = {};
  try { input = JSON.parse(fs.readFileSync(0, 'utf8')); } catch (e) { /* stdin vide */ }
  const projectDir = process.env.CLAUDE_PROJECT_DIR || input.cwd || process.cwd();
  const cwd = input.cwd || projectDir;

  const git = (args, timeout) => spawnSync('git', args, { cwd, encoding: 'utf8', timeout: timeout || 5000 });
  if (git(['rev-parse', '--is-inside-work-tree']).stdout.trim() !== 'true') process.exit(0);

  let mode = 'branch';
  try {
    const m = fs.readFileSync(path.join(projectDir, '.claude', 'git-mode'), 'utf8').trim();
    if (m === 'main' || m === 'branch') mode = m;
  } catch (e) { /* defaut */ }

  const branch = git(['branch', '--show-current']).stdout.trim() || '(HEAD detache)';
  const fetched = git(['fetch', '-q', 'origin'], 8000).status === 0;

  let sync = 'synchronisation avec GitHub non verifiee (fetch impossible)';
  if (fetched) {
    const r = git(['rev-list', '--left-right', '--count', `origin/${branch}...HEAD`]);
    if (r.status === 0) {
      const [behind, ahead] = r.stdout.trim().split(/\s+/).map(Number);
      sync = behind === 0 && ahead === 0
        ? 'a jour avec GitHub'
        : `${behind} commit(s) de retard, ${ahead} commit(s) d'avance sur origin/${branch}`;
    } else {
      sync = `pas de branche origin/${branch} (branche locale uniquement)`;
    }
  }

  const lines = git(['status', '--porcelain']).stdout.split('\n').filter(Boolean);
  const tracked = lines.filter((l) => !l.startsWith('??'));
  const untracked = lines.filter((l) => l.startsWith('??'));
  const names = (arr) => arr.slice(0, 5).map((l) => l.slice(3).trim()).join(', ') + (arr.length > 5 ? `, +${arr.length - 5}` : '');
  const last = git(['log', '-1', '--format=%h %cs %s']).stdout.trim();

  const out = [
    `Etat Git au demarrage (${path.basename(projectDir)}) :`,
    `- Branche : ${branch} | mode du projet : ${mode === 'main' ? 'main directement (exception)' : 'branche dev-xxx par defaut, fusion vers main toujours validee par Mickael'}`,
    `- Synchronisation : ${sync}`,
    `- Fichiers suivis modifies : ${tracked.length ? `${tracked.length} (${names(tracked)})` : 'aucun'}`,
    `- Fichiers non suivis : ${untracked.length ? `${untracked.length} (${names(untracked)})` : 'aucun'}`,
    `- Dernier commit : ${last || 'aucun'}`,
  ];

  // Projet prevu pour le local : avertir si la session tourne dans le cloud.
  // Le fichier .claude/local-only contient la raison (a commiter pour etre visible dans le cloud).
  if (process.env.CLAUDE_CODE_REMOTE === 'true') {
    try {
      const why = fs.readFileSync(path.join(projectDir, '.claude', 'local-only'), 'utf8').trim();
      out.unshift(`ATTENTION : cette session tourne dans le CLOUD, mais ce projet est prevu pour le LOCAL. ${why || ''} Signale-le a Mickael des ton premier message et propose de continuer en local (ou en local avec controle a distance) si la tache en depend.`);
    } catch (e) { /* projet utilisable dans le cloud */ }
  }

  const alerts = [];
  if (mode === 'branch' && /^(main|master)$/.test(branch)) alerts.push('Mode branche mais la branche courante est main : creer une branche dev-xxx avant toute modification.');
  if (fetched && /de retard/.test(sync) && !/^0 commit/.test(sync)) alerts.push('Le depot est en retard sur GitHub : faire un pull (avance rapide) avant de modifier, et verifier que les fichiers non suivis ne sont pas en conflit avec les commits entrants.');
  if (tracked.length) alerts.push('Des modifications non commitees existent deja : ne pas les melanger a la tache demandee, et les signaler a Mickael.');
  if (alerts.length) out.push('Alertes : ' + alerts.join(' '));

  emit(out.join('\n'));
} catch (e) {
  process.exit(0); // ne jamais bloquer le demarrage de session
}
