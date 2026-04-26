#!/usr/bin/env node
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const skillRoot = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: skillRoot,
    encoding: 'utf8',
    ...options
  });
  if (result.status !== 0) {
    throw new Error([
      `Command failed: ${command} ${args.join(' ')}`,
      result.stdout,
      result.stderr
    ].filter(Boolean).join('\n'));
  }
  return result;
}

async function readJson(filePath) {
  return JSON.parse(await fs.readFile(filePath, 'utf8'));
}

async function main() {
  run('node', ['scripts/preflight.mjs']);

  const tmpRoot = await fs.mkdtemp(path.join(os.tmpdir(), 'postman2insomnia-test-'));
  const outputDir = path.join(tmpRoot, 'out');
  run('node', ['scripts/postman2insomnia.mjs', '--source', 'fixtures/postman', '--output', outputDir]);

  const simple = await readJson(path.join(outputDir, 'simple-request.insomnia.json'));
  const folder = await readJson(path.join(outputDir, 'folder-auth-scripts.insomnia.json'));
  const folderReport = await readJson(path.join(outputDir, 'folder-auth-scripts.migration-report.json'));

  assert.equal(simple._type, 'export');
  assert.equal(simple.__export_format, 4);
  assert.equal(simple.resources.filter((resource) => resource._type === 'request').length, 1);
  assert.equal(simple.resources.filter((resource) => resource._type === 'environment').length, 2);

  const statusRequest = simple.resources.find((resource) => resource._type === 'request' && resource.name === 'Status');
  assert.ok(statusRequest);
  assert.match(statusRequest.afterResponseScript, /insomnia\.test/);
  assert.match(statusRequest.afterResponseScript, /insomnia\.expect\(insomnia\.response\.status\)/);

  const createThing = folder.resources.find((resource) => resource._type === 'request' && resource.name === 'Create Thing');
  assert.ok(createThing);
  assert.equal(createThing.parentId, '__folder_1__');
  assert.equal(createThing.authentication.type, 'bearer');
  assert.match(createThing.preRequestScript, /insomnia\.collectionVariables\.set/);
  assert.match(createThing.preRequestScript, /const env = insomnia\.environment/);
  assert.match(createThing.afterResponseScript, /insomnia\.sendRequest/);
  assert.match(createThing.afterResponseScript, /TODO\(postman2insomnia\): pm\.execution\.setNextRequest/);
  assert.equal(folder.resources.filter((resource) => resource._type === 'response').length, 1);

  assert.equal(folderReport.counts.sourceRequests, folderReport.counts.targetRequests);
  assert.equal(folderReport.counts.sourceFolders, folderReport.counts.targetFolders);
  assert.ok(folderReport.warnings.some((warning) => warning.includes('pm.execution.setNextRequest')));
  assert.ok(folderReport.warnings.some((warning) => warning.includes('skipped disabled query parameter')));

  const strictResult = spawnSync('node', ['scripts/postman2insomnia.mjs', '--source', 'fixtures/postman', '--output', path.join(tmpRoot, 'strict'), '--strict'], {
    cwd: skillRoot,
    encoding: 'utf8'
  });
  assert.notEqual(strictResult.status, 0, 'strict mode should fail when fixture warnings are present');

  console.log('postman2insomnia tests passed');
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
