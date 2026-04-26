#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

export const REQUIRED_PACKAGES = [
  'ajv',
  'ajv-draft-04',
  '@babel/parser',
  '@babel/traverse',
  '@babel/generator',
  '@babel/types'
];

export const SKILL_ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

function packageRequire(root = SKILL_ROOT) {
  return createRequire(path.join(root, 'package.json'));
}

export function assertNodeRuntime() {
  const version = process.version;
  if (!version || !version.startsWith('v')) {
    throw new Error('Node.js runtime is unavailable. Install Node.js before using postman2insomnia.');
  }
  return version;
}

export function findMissingDependencies(root = SKILL_ROOT) {
  const require = packageRequire(root);
  const missing = [];
  for (const packageName of REQUIRED_PACKAGES) {
    try {
      require.resolve(packageName);
    } catch {
      missing.push(packageName);
    }
  }
  return missing;
}

export function verifyRequiredImports(root = SKILL_ROOT) {
  const require = packageRequire(root);
  for (const packageName of REQUIRED_PACKAGES) {
    require(packageName);
  }
}

export async function ensureDependencies({ install = true, root = SKILL_ROOT, quiet = false } = {}) {
  const nodeVersion = assertNodeRuntime();
  let missing = findMissingDependencies(root);

  if (missing.length > 0) {
    if (!install) {
      throw new Error(`Missing Node dependencies: ${missing.join(', ')}`);
    }

    const command = 'npm install --no-audit --no-fund';
    if (!quiet) {
      console.error(`[postman2insomnia] Missing dependencies: ${missing.join(', ')}`);
      console.error(`[postman2insomnia] Running: ${command}`);
    }

    const result = spawnSync('npm', ['install', '--no-audit', '--no-fund'], {
      cwd: root,
      stdio: 'inherit',
      env: { ...process.env, npm_config_audit: 'false', npm_config_fund: 'false' }
    });

    if (result.error || result.status !== 0) {
      const detail = result.error ? ` (${result.error.message})` : '';
      throw new Error(`Dependency installation failed while running "${command}" in ${root}${detail}`);
    }
  }

  missing = findMissingDependencies(root);
  if (missing.length > 0) {
    throw new Error(`Dependencies remain missing after install: ${missing.join(', ')}`);
  }

  verifyRequiredImports(root);
  if (!quiet) {
    console.error(`[postman2insomnia] Node ${nodeVersion} and required dependencies are ready.`);
  }
  return { nodeVersion, packages: REQUIRED_PACKAGES };
}

function isDirectRun() {
  return process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
}

if (isDirectRun()) {
  ensureDependencies().catch((error) => {
    console.error(`[postman2insomnia] ${error.message}`);
    process.exit(1);
  });
}
