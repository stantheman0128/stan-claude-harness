#!/usr/bin/env node
/**
 * claude-mem-sync — Cross-device memory sync for claude-mem via Supabase Storage
 *
 * Subcommands:
 *   setup --url <supabase-url> --key <service-role-key>   One-time setup
 *   download                                               Pull cloud DB if newer (SessionStart hook)
 *   upload                                                 Push local DB to cloud (Stop hook)
 *   status                                                 Show sync state
 *
 * Identity: uses organizationUuid from ~/.claude/.credentials.json
 * Storage:  Supabase Storage bucket "claude-mem-sync"
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync, statSync, unlinkSync, renameSync, readdirSync, appendFileSync } from 'fs';
import { join, dirname } from 'path';
import { homedir, hostname } from 'os';
import { execFileSync } from 'child_process';

// ─── Constants ───────────────────────────────────────────
const HOME = homedir();
const DATA_DIR = join(HOME, '.claude-mem');
const CLAUDE_DIR = join(HOME, '.claude');
if (existsSync(join(DATA_DIR, '.paused'))) process.exit(0);
const CONFIG_PATH = join(DATA_DIR, 'sync-config.json');
const CREDS_PATH = join(CLAUDE_DIR, '.credentials.json');
const LOG_PATH = join(DATA_DIR, 'sync.log');
const DB_NAME = 'claude-mem.db';
const DB_PATH = join(DATA_DIR, DB_NAME);
const SETTINGS_NAME = 'settings.json';
const SETTINGS_PATH = join(DATA_DIR, SETTINGS_NAME);
const CHROMA_DIR = join(DATA_DIR, 'chroma');
const PID_PATH = join(DATA_DIR, 'worker.pid');
const BUCKET = 'claude-mem-sync';
const FETCH_TIMEOUT = 15_000;

// ─── Logging ─────────────────────────────────────────────
function log(level, msg) {
  const ts = new Date().toISOString();
  const line = `[${ts}] [${level}] ${msg}\n`;
  try { appendFileSync(LOG_PATH, line); } catch {}
  if (level === 'ERROR' || process.argv.includes('--verbose')) {
    process.stderr.write(line);
  }
}

// ─── Config & Identity ───────────────────────────────────
function loadConfig() {
  if (!existsSync(CONFIG_PATH)) return null;
  try { return JSON.parse(readFileSync(CONFIG_PATH, 'utf8')); } catch { return null; }
}

function getOrgUuid() {
  if (!existsSync(CREDS_PATH)) return null;
  try {
    return JSON.parse(readFileSync(CREDS_PATH, 'utf8')).organizationUuid || null;
  } catch { return null; }
}

// ─── Supabase Storage helpers ────────────────────────────
function authHeaders(key, contentType) {
  const h = { 'Authorization': `Bearer ${key}`, 'apikey': key };
  if (contentType) h['Content-Type'] = contentType;
  return h;
}

async function supaFetch(url, key, opts = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), opts.timeout || FETCH_TIMEOUT);
  try {
    return await fetch(url, {
      ...opts,
      headers: { ...authHeaders(key, opts.contentType), ...opts.headers },
      signal: controller.signal
    });
  } finally {
    clearTimeout(timer);
  }
}

async function listCloudFiles(config, orgUuid) {
  const resp = await supaFetch(
    `${config.supabaseUrl}/storage/v1/object/list/${BUCKET}`,
    config.supabaseKey,
    {
      method: 'POST',
      contentType: 'application/json',
      body: JSON.stringify({ prefix: `${orgUuid}/`, limit: 200 })
    }
  );
  if (!resp.ok) return [];
  return resp.json();
}

async function uploadFile(config, orgUuid, remotePath, localPath) {
  const data = readFileSync(localPath);
  const resp = await supaFetch(
    `${config.supabaseUrl}/storage/v1/object/${BUCKET}/${orgUuid}/${remotePath}`,
    config.supabaseKey,
    {
      method: 'POST',
      contentType: 'application/octet-stream',
      headers: { 'x-upsert': 'true' },
      body: data,
      timeout: 60_000
    }
  );
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Upload failed (${resp.status}): ${text}`);
  }
  log('INFO', `upload: ${remotePath} OK (${data.length} bytes)`);
}

async function downloadFile(config, orgUuid, remotePath, localPath) {
  const resp = await supaFetch(
    `${config.supabaseUrl}/storage/v1/object/${BUCKET}/${orgUuid}/${remotePath}`,
    config.supabaseKey,
    { timeout: 60_000 }
  );
  if (!resp.ok) {
    if (resp.status === 404) return false;
    throw new Error(`Download failed (${resp.status})`);
  }
  const buffer = Buffer.from(await resp.arrayBuffer());
  const tmpPath = localPath + '.sync-tmp';
  mkdirSync(dirname(localPath), { recursive: true });
  writeFileSync(tmpPath, buffer);
  renameSync(tmpPath, localPath);
  log('INFO', `download: ${remotePath} OK (${buffer.length} bytes)`);
  return true;
}

// ─── Worker management ───────────────────────────────────
function killWorker() {
  if (!existsSync(PID_PATH)) return;
  try {
    const pidData = JSON.parse(readFileSync(PID_PATH, 'utf8'));
    process.kill(pidData.pid, 'SIGTERM');
    log('INFO', `Killed worker PID ${pidData.pid}`);
  } catch {}
}

// ─── WAL Checkpoint ──────────────────────────────────────
function checkpointWAL() {
  // Try sqlite3 CLI (safe, no shell injection — uses execFileSync)
  try {
    execFileSync('sqlite3', [DB_PATH, 'PRAGMA wal_checkpoint(TRUNCATE);'], { stdio: 'ignore', timeout: 10_000 });
    log('INFO', 'WAL checkpoint completed (sqlite3)');
    return true;
  } catch {}
  // Try node:sqlite
  try {
    const { DatabaseSync } = require('node:sqlite');
    const db = new DatabaseSync(DB_PATH);
    db.exec('PRAGMA wal_checkpoint(TRUNCATE)');
    db.close();
    log('INFO', 'WAL checkpoint completed (node:sqlite)');
    return true;
  } catch {}
  log('WARN', 'WAL checkpoint skipped (no sqlite available)');
  return false;
}

// ─── Chroma file enumeration ─────────────────────────────
function listChromaFiles() {
  const files = [];
  if (!existsSync(CHROMA_DIR)) return files;
  function walk(dir, prefix) {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const rel = prefix ? `${prefix}/${entry.name}` : entry.name;
      if (entry.isDirectory()) walk(join(dir, entry.name), rel);
      else files.push({ remotePath: `chroma/${rel}`, localPath: join(dir, entry.name) });
    }
  }
  walk(CHROMA_DIR, '');
  return files;
}

// ─── Cloud timestamp helper ──────────────────────────────
async function getCloudDbTime(config, orgUuid) {
  const files = await listCloudFiles(config, orgUuid);
  const dbFile = files.find(f => f.name === DB_NAME);
  return dbFile ? new Date(dbFile.updated_at).getTime() : null;
}

function getLocalDbTime() {
  return existsSync(DB_PATH) ? statSync(DB_PATH).mtimeMs : null;
}

// ═══════════════════════════════════════════════════════════
// SUBCOMMANDS
// ═══════════════════════════════════════════════════════════

async function cmdSetup(args) {
  let url = '', key = '';
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--url' && args[i + 1]) url = args[i + 1];
    if (args[i] === '--key' && args[i + 1]) key = args[i + 1];
  }
  if (!url || !key) {
    console.error('Usage: claude-mem-sync setup --url <supabase-url> --key <service-role-key>');
    process.exit(1);
  }

  const orgUuid = getOrgUuid();
  if (!orgUuid) {
    console.error('Error: Cannot read organizationUuid. Are you logged into Claude Code?');
    process.exit(1);
  }

  console.log(`Organization UUID: ${orgUuid}`);
  console.log(`Supabase URL: ${url}`);

  // Validate
  console.log('Validating credentials...');
  const resp = await supaFetch(`${url}/storage/v1/bucket`, key);
  if (!resp.ok) {
    console.error(`Error: Supabase returned ${resp.status}. Check your URL and key.`);
    process.exit(1);
  }
  console.log('Credentials OK');

  // Create bucket
  console.log('Creating bucket...');
  const bucketResp = await supaFetch(`${url}/storage/v1/bucket`, key, {
    method: 'POST',
    contentType: 'application/json',
    body: JSON.stringify({ id: BUCKET, name: BUCKET, public: false, file_size_limit: 52428800 })
  });
  const bucketText = await bucketResp.text();
  if (bucketResp.ok) console.log(`Bucket "${BUCKET}" created`);
  else if (bucketText.includes('already exists')) console.log(`Bucket "${BUCKET}" already exists`);
  else console.error(`Warning: ${bucketResp.status}: ${bucketText}`);

  // Write config
  const config = { supabaseUrl: url, supabaseKey: key, bucket: BUCKET, enabled: true };
  mkdirSync(DATA_DIR, { recursive: true });
  writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2));
  console.log(`Config written to ${CONFIG_PATH}`);

  // Initial upload
  if (existsSync(DB_PATH)) {
    console.log('Performing initial upload...');
    await cmdUpload(config, orgUuid);
    console.log('Initial upload complete');
  } else {
    console.log('No local DB found. Will download from cloud on next session.');
  }

  console.log('\nSetup complete! Restart Claude Code to activate sync.');
}

async function cmdDownload(config, orgUuid) {
  config = config || loadConfig();
  orgUuid = orgUuid || getOrgUuid();
  if (!config?.enabled || !orgUuid) return;

  log('INFO', 'download: checking cloud...');

  const cloudTime = await getCloudDbTime(config, orgUuid);
  if (!cloudTime) { log('INFO', 'download: no cloud DB, skipping'); return; }

  const localTime = getLocalDbTime();
  if (localTime && localTime >= cloudTime) { log('INFO', 'download: local is same or newer, skipping'); return; }

  log('INFO', `download: cloud is newer (cloud=${new Date(cloudTime).toISOString()}, local=${localTime ? new Date(localTime).toISOString() : 'none'})`);

  killWorker();
  await new Promise(r => setTimeout(r, 1000));

  mkdirSync(DATA_DIR, { recursive: true });
  await downloadFile(config, orgUuid, DB_NAME, DB_PATH);

  // Remove stale WAL/SHM
  for (const ext of ['-wal', '-shm']) {
    const p = DB_PATH + ext;
    if (existsSync(p)) try { unlinkSync(p); } catch {}
  }

  await downloadFile(config, orgUuid, SETTINGS_NAME, SETTINGS_PATH).catch(() => {});

  // Download chroma
  const chromaResp = await supaFetch(
    `${config.supabaseUrl}/storage/v1/object/list/${BUCKET}`,
    config.supabaseKey,
    { method: 'POST', contentType: 'application/json', body: JSON.stringify({ prefix: `${orgUuid}/chroma/`, limit: 200 }) }
  );
  if (chromaResp.ok) {
    const chromaList = await chromaResp.json();
    for (const file of chromaList) {
      if (file.id) {
        await downloadFile(config, orgUuid, `chroma/${file.name}`, join(CHROMA_DIR, file.name)).catch(e => {
          log('WARN', `download chroma: ${file.name} - ${e.message}`);
        });
      }
    }
  }

  // Clear worker locks
  const lockPath = join(DATA_DIR, '.worker-start-attempted');
  if (existsSync(lockPath)) try { unlinkSync(lockPath); } catch {}
  try { writeFileSync(join(DATA_DIR, 'supervisor.json'), '{"processes":{}}'); } catch {}

  log('INFO', 'download: complete');
}

async function cmdUpload(config, orgUuid) {
  config = config || loadConfig();
  orgUuid = orgUuid || getOrgUuid();
  if (!config?.enabled || !orgUuid) return;
  if (!existsSync(DB_PATH)) { log('WARN', 'upload: no local DB, skipping'); return; }

  log('INFO', 'upload: starting...');
  checkpointWAL();

  await uploadFile(config, orgUuid, DB_NAME, DB_PATH);
  if (existsSync(SETTINGS_PATH)) await uploadFile(config, orgUuid, SETTINGS_NAME, SETTINGS_PATH);

  for (const file of listChromaFiles()) {
    try { await uploadFile(config, orgUuid, file.remotePath, file.localPath); }
    catch (e) { log('WARN', `upload chroma: ${file.remotePath} - ${e.message}`); }
  }

  // Upload metadata
  const meta = { lastUploadDevice: hostname(), lastUploadAt: new Date().toISOString(), platform: process.platform, dbSizeBytes: statSync(DB_PATH).size };
  try {
    const { DatabaseSync } = require('node:sqlite');
    const db = new DatabaseSync(DB_PATH, { readOnly: true });
    meta.observationCount = db.prepare('SELECT COUNT(*) as c FROM observations').get().c;
    meta.sessionCount = db.prepare('SELECT COUNT(*) as c FROM sessions').get().c;
    db.close();
  } catch {}
  const metaPath = join(DATA_DIR, '_meta.json');
  writeFileSync(metaPath, JSON.stringify(meta, null, 2));
  await uploadFile(config, orgUuid, '_meta.json', metaPath);

  log('INFO', `upload: complete (${meta.dbSizeBytes} bytes, ${meta.observationCount || '?'} obs)`);
}

async function cmdStatus() {
  const config = loadConfig();
  const orgUuid = getOrgUuid();

  console.log('=== Claude-Mem Sync Status ===\n');

  if (!config) {
    console.log('Config: NOT CONFIGURED');
    console.log('Run: node claude-mem-sync.mjs setup --url <url> --key <key>');
    return;
  }
  console.log(`Config: OK (${config.supabaseUrl})`);
  console.log(`Enabled: ${config.enabled}`);

  if (!orgUuid) { console.log('\nIdentity: NOT FOUND'); return; }
  console.log(`Identity: ${orgUuid}`);

  console.log('\n--- Local ---');
  if (existsSync(DB_PATH)) {
    const s = statSync(DB_PATH);
    console.log(`  DB: ${(s.size / 1048576).toFixed(1)} MB (${new Date(s.mtimeMs).toISOString()})`);
  } else console.log('  DB: NOT FOUND');

  if (existsSync(CHROMA_DIR)) {
    const cf = listChromaFiles();
    const sz = cf.reduce((s, f) => s + statSync(f.localPath).size, 0);
    console.log(`  Chroma: ${cf.length} files (${(sz / 1048576).toFixed(1)} MB)`);
  }

  console.log('\n--- Cloud ---');
  try {
    const files = await listCloudFiles(config, orgUuid);
    if (!files.length) { console.log('  (empty)'); return; }
    for (const f of files) {
      if (f.metadata) console.log(`  ${f.name}: ${(f.metadata.size / 1048576).toFixed(1)} MB (${f.updated_at})`);
      else console.log(`  ${f.name}/`);
    }

    const metaResp = await supaFetch(`${config.supabaseUrl}/storage/v1/object/${BUCKET}/${orgUuid}/_meta.json`, config.supabaseKey);
    if (metaResp.ok) {
      const m = await metaResp.json();
      console.log(`\n--- Last Upload ---`);
      console.log(`  Device: ${m.lastUploadDevice}`);
      console.log(`  Time: ${m.lastUploadAt}`);
      console.log(`  Observations: ${m.observationCount || '?'}`);
    }

    const ct = await getCloudDbTime(config, orgUuid);
    const lt = getLocalDbTime();
    console.log('\n--- Sync ---');
    if (ct && lt) {
      if (lt > ct) console.log('  Local is NEWER');
      else if (ct > lt) console.log('  Cloud is NEWER');
      else console.log('  IN SYNC');
    }
  } catch (e) { console.log(`  Error: ${e.message}`); }
}

// ═══════════════════════════════════════════════════════════
async function main() {
  const cmd = process.argv[2];
  try {
    switch (cmd) {
      case 'setup': await cmdSetup(process.argv.slice(3)); break;
      case 'download': await cmdDownload(); break;
      case 'upload': await cmdUpload(); break;
      case 'status': await cmdStatus(); break;
      default:
        console.log('claude-mem-sync — Cross-device memory sync');
        console.log('\nCommands:');
        console.log('  setup --url <url> --key <key>   One-time setup');
        console.log('  download                        Pull cloud DB if newer');
        console.log('  upload                          Push local DB to cloud');
        console.log('  status                          Show sync state');
    }
  } catch (e) {
    log('ERROR', `${cmd}: ${e.message}`);
    process.exit(0); // Never block Claude Code
  }
}

main().catch(e => { log('ERROR', `fatal: ${e.message}`); process.exit(0); });
