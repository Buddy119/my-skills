#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { ensureDependencies, SKILL_ROOT } from './preflight.mjs';

const require = createRequire(import.meta.url);
const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const SOURCE_NAME = 'postman2insomnia-skill';
const DEFAULT_EXPORT_FORMAT = 4;
const SKIP_DIRS = new Set(['node_modules', '.git', 'insomnia-migration']);

let AjvDraft04;
let parser;
let traverse;
let generate;
let t;

async function loadRuntime() {
  await ensureDependencies({ install: true, root: SKILL_ROOT, quiet: true });
  AjvDraft04 = require('ajv-draft-04');
  parser = require('@babel/parser');
  const traverseModule = require('@babel/traverse');
  const generatorModule = require('@babel/generator');
  traverse = traverseModule.default || traverseModule;
  generate = generatorModule.default || generatorModule;
  t = require('@babel/types');
}

function usage() {
  return `Usage: node ${path.relative(process.cwd(), path.join(SCRIPT_DIR, 'postman2insomnia.mjs'))} --source <folder-path-to-postman> [--output <folder>] [--strict]`;
}

function parseArgs(argv) {
  const options = { strict: false };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--source') {
      options.source = argv[++index];
    } else if (arg === '--output') {
      options.output = argv[++index];
    } else if (arg === '--strict') {
      options.strict = true;
    } else if (arg === '--help' || arg === '-h') {
      options.help = true;
    } else {
      throw new Error(`Unknown argument: ${arg}\n${usage()}`);
    }
  }
  if (!options.help && !options.source) {
    throw new Error(`Missing required --source.\n${usage()}`);
  }
  return options;
}

async function readJson(filePath) {
  const text = await fs.readFile(filePath, 'utf8');
  try {
    return JSON.parse(text);
  } catch (error) {
    const wrapped = new Error(`Invalid JSON in ${filePath}: ${error.message}`);
    wrapped.cause = error;
    throw wrapped;
  }
}

async function loadSchema(relativePath) {
  return readJson(path.join(SKILL_ROOT, relativePath));
}

function makeValidator(schema) {
  const ajv = new AjvDraft04({ allErrors: true, strict: false });
  return ajv.compile(schema);
}

function formatAjvErrors(errors = []) {
  return errors.map((error) => `${error.instancePath || error.dataPath || '/'} ${error.message}`).join('; ');
}

async function listJsonFiles(rootPath) {
  const stat = await fs.stat(rootPath);
  if (stat.isFile()) {
    return rootPath.endsWith('.json') ? [rootPath] : [];
  }

  const files = [];
  async function walk(current) {
    const entries = await fs.readdir(current, { withFileTypes: true });
    for (const entry of entries) {
      const entryPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        if (!SKIP_DIRS.has(entry.name)) {
          await walk(entryPath);
        }
      } else if (entry.isFile() && entry.name.toLowerCase().endsWith('.json')) {
        files.push(entryPath);
      }
    }
  }
  await walk(rootPath);
  return files.sort();
}

function classifyJson(filePath, data) {
  if (data && data.info && Array.isArray(data.item)) {
    return 'collection';
  }
  if (data && Array.isArray(data.values)) {
    const scope = String(data._postman_variable_scope || '').toLowerCase();
    const fileName = path.basename(filePath).toLowerCase();
    if (scope === 'globals' || fileName.includes('globals')) {
      return 'globals';
    }
    return 'environment';
  }
  return 'unknown';
}

function descriptionToString(description) {
  if (description == null) return '';
  if (typeof description === 'string') return description;
  if (typeof description === 'object' && typeof description.content === 'string') return description.content;
  return String(description);
}

function valueToText(value) {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  return JSON.stringify(value);
}

function slugify(value, fallback = 'collection') {
  const slug = String(value || fallback)
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .replace(/-{2,}/g, '-');
  return slug || fallback;
}

function normalizeVariables(values = [], context, report, { enabledField = false } = {}) {
  const result = {};
  let enabledCount = 0;
  for (const variable of values || []) {
    if (!variable || !variable.key) continue;
    const disabled = variable.disabled === true || (enabledField && variable.enabled === false);
    if (disabled) {
      report.warnings.push(`${context}: skipped disabled variable "${variable.key}".`);
      continue;
    }
    enabledCount += 1;
    result[variable.key] = variable.value ?? '';
    detectDynamicVariables(valueToText(variable.value), `${context} variable "${variable.key}"`, report);
  }
  report.counts.enabledVariables += enabledCount;
  return result;
}

function headersToInsomnia(headers = [], context, report) {
  const result = [];
  for (const header of headers || []) {
    if (!header || !header.key) continue;
    if (header.disabled) {
      report.warnings.push(`${context}: skipped disabled header "${header.key}".`);
      continue;
    }
    result.push({ name: header.key, value: header.value ?? '' });
    detectDynamicVariables(valueToText(header.value), `${context} header "${header.key}"`, report);
  }
  return result;
}

function queryToInsomnia(query = [], context, report) {
  const result = [];
  for (const param of query || []) {
    if (!param || !param.key) continue;
    if (param.disabled) {
      report.warnings.push(`${context}: skipped disabled query parameter "${param.key}".`);
      continue;
    }
    result.push({ name: param.key, value: param.value ?? '' });
    detectDynamicVariables(valueToText(param.value), `${context} query parameter "${param.key}"`, report);
  }
  return result;
}

function appendQueryIfMissing(rawUrl, parameters) {
  if (!parameters.length || rawUrl.includes('?')) return rawUrl;
  const query = parameters
    .map(({ name, value }) => `${encodeURIComponent(name)}=${encodeURIComponent(valueToText(value))}`)
    .join('&');
  return `${rawUrl}${rawUrl.endsWith('?') ? '' : '?'}${query}`;
}

function urlToString(url, parameters) {
  if (typeof url === 'string') return appendQueryIfMissing(url, parameters);
  if (!url || typeof url !== 'object') return '';
  if (url.raw) return appendQueryIfMissing(String(url.raw), parameters);

  const protocol = url.protocol ? `${url.protocol}://` : '';
  const host = Array.isArray(url.host) ? url.host.join('.') : (url.host || '');
  const pathValue = Array.isArray(url.path) ? url.path.join('/') : (url.path || '');
  const slash = host && pathValue ? '/' : '';
  return appendQueryIfMissing(`${protocol}${host}${slash}${pathValue}`, parameters);
}

function detectDynamicVariables(text, context, report) {
  const matches = String(text || '').match(/\{\{\$[a-zA-Z0-9_]+\}\}/g) || [];
  for (const match of matches) {
    report.warnings.push(`${context}: dynamic Postman variable ${match} needs manual validation in Insomnia.`);
  }
}

function extractScripts(events = [], listen, context, report) {
  const scripts = [];
  for (const event of events || []) {
    if (!event || event.listen !== listen) continue;
    if (event.disabled) {
      report.warnings.push(`${context}: skipped disabled ${listen} script event.`);
      continue;
    }
    report.counts.sourceScriptEvents += 1;
    const exec = event.script?.exec;
    let script = '';
    if (Array.isArray(exec)) {
      script = exec.join('\n');
    } else if (typeof exec === 'string') {
      script = exec;
    } else {
      report.warnings.push(`${context}: ${listen} script has no string or array exec body.`);
      continue;
    }
    scripts.push({ context, listen, script });
  }
  return scripts;
}

function joinScriptParts(parts) {
  return parts
    .filter((part) => part.script.trim().length > 0)
    .map((part) => `// Migrated ${part.listen} script from ${part.context}\n${part.script.trim()}`)
    .join('\n\n');
}

function authAttributesToObject(attrs = []) {
  const result = {};
  for (const attr of attrs || []) {
    if (!attr || !attr.key) continue;
    result[attr.key] = attr.value ?? '';
  }
  return result;
}

function mapAuth(auth, context, report) {
  if (!auth || auth.type === 'noauth') return {};
  const type = auth.type;
  const attrs = authAttributesToObject(auth[type] || []);
  const warn = (message) => report.warnings.push(`${context}: ${message}`);

  if (type === 'basic') {
    return { type: 'basic', username: attrs.username ?? '', password: attrs.password ?? '' };
  }
  if (type === 'bearer') {
    return { type: 'bearer', token: attrs.token ?? '', prefix: attrs.prefix ?? 'Bearer' };
  }
  if (type === 'apikey') {
    warn('API key auth was preserved but header/query placement needs manual validation.');
    return { type: 'apikey', key: attrs.key ?? '', value: attrs.value ?? '', addTo: attrs.in ?? attrs.addTo ?? '' };
  }
  if (['digest', 'oauth1', 'oauth2', 'awsv4', 'ntlm', 'edgegrid', 'hawk'].includes(type)) {
    warn(`${type} auth helper attributes were preserved, but helper behavior needs manual validation.`);
    return { type, ...attrs };
  }

  warn(`unknown auth type "${type}" was not converted.`);
  return {};
}

function contentTypeFromHeaders(headers) {
  const header = headers.find((item) => item.name.toLowerCase() === 'content-type');
  return header ? String(header.value) : '';
}

function bodyToInsomnia(body, headers, context, report) {
  if (!body || typeof body !== 'object') return undefined;
  const contentType = contentTypeFromHeaders(headers);
  if (body.mode === 'raw') {
    const mimeType = contentType || (body.options?.raw?.language === 'json' ? 'application/json' : 'text/plain');
    const text = typeof body.raw === 'string' ? body.raw : valueToText(body.raw);
    detectDynamicVariables(text, `${context} raw body`, report);
    return { mimeType, text };
  }
  if (body.mode === 'urlencoded') {
    return {
      mimeType: 'application/x-www-form-urlencoded',
      params: bodyParams(body.urlencoded || [], context, report)
    };
  }
  if (body.mode === 'formdata') {
    return {
      mimeType: 'multipart/form-data',
      params: bodyParams(body.formdata || [], context, report)
    };
  }
  if (body.mode === 'file') {
    const src = body.file?.src || body.file?.content || '';
    report.warnings.push(`${context}: file body reference was preserved but needs manual validation.`);
    return { mimeType: contentType || 'application/octet-stream', fileName: valueToText(src) };
  }
  if (body.mode === 'graphql') {
    report.warnings.push(`${context}: GraphQL body was serialized as JSON and needs manual validation.`);
    return { mimeType: 'application/json', text: JSON.stringify(body.graphql ?? {}, null, 2) };
  }
  report.warnings.push(`${context}: unsupported body mode "${body.mode}" was not converted.`);
  return undefined;
}

function bodyParams(values = [], context, report) {
  const result = [];
  for (const param of values || []) {
    if (!param || !param.key) continue;
    if (param.disabled) {
      report.warnings.push(`${context}: skipped disabled body parameter "${param.key}".`);
      continue;
    }
    const converted = { name: param.key, value: param.value ?? '' };
    if (param.type) converted.type = param.type;
    if (param.type === 'file' || param.src) {
      converted.fileName = Array.isArray(param.src) ? param.src.join(',') : valueToText(param.src);
      report.warnings.push(`${context}: file form-data parameter "${param.key}" needs manual validation.`);
    }
    detectDynamicVariables(valueToText(converted.value), `${context} body parameter "${param.key}"`, report);
    result.push(converted);
  }
  return result;
}

function normalizeCollection(collection, filePath, environments, globals, report) {
  const ast = {
    kind: 'collection',
    sourceFile: filePath,
    name: collection.info?.name || path.basename(filePath, '.json'),
    description: descriptionToString(collection.info?.description),
    variables: normalizeVariables(collection.variable || [], 'collection', report),
    auth: collection.auth || null,
    preRequestScripts: extractScripts(collection.event, 'prerequest', 'collection', report),
    afterResponseScripts: extractScripts(collection.event, 'test', 'collection', report),
    children: []
  };

  ast.environmentFiles = environments;
  ast.globalsFiles = globals;
  ast.children = (collection.item || []).map((item) => normalizeItem(item, 'collection', report)).filter(Boolean);
  return ast;
}

function normalizeItem(item, parentContext, report) {
  if (!item || typeof item !== 'object') return null;
  const context = `${parentContext} > ${item.name || 'unnamed'}`;
  if (Array.isArray(item.item)) {
    report.counts.sourceFolders += 1;
    return {
      kind: 'folder',
      name: item.name || 'Unnamed Folder',
      description: descriptionToString(item.description),
      variables: normalizeVariables(item.variable || [], context, report),
      auth: item.auth || null,
      preRequestScripts: extractScripts(item.event, 'prerequest', context, report),
      afterResponseScripts: extractScripts(item.event, 'test', context, report),
      children: item.item.map((child) => normalizeItem(child, context, report)).filter(Boolean)
    };
  }

  if (item.request) {
    report.counts.sourceRequests += 1;
    const request = typeof item.request === 'string' ? { method: 'GET', url: item.request } : item.request;
    const headers = headersToInsomnia(request.header || [], context, report);
    const parameters = typeof request.url === 'object' ? queryToInsomnia(request.url.query || [], context, report) : [];
    const url = urlToString(request.url, parameters);
    detectDynamicVariables(url, `${context} URL`, report);
    return {
      kind: 'request',
      name: item.name || 'Unnamed Request',
      description: descriptionToString(item.description || request.description),
      method: request.method || 'GET',
      url,
      headers,
      parameters,
      body: bodyToInsomnia(request.body, headers, context, report),
      auth: request.auth || item.auth || null,
      preRequestScripts: extractScripts(item.event, 'prerequest', context, report),
      afterResponseScripts: extractScripts(item.event, 'test', context, report),
      responses: (item.response || []).map((response) => normalizeResponse(response, context, report))
    };
  }

  report.warnings.push(`${context}: item is neither folder nor request and was skipped.`);
  return null;
}

function normalizeResponse(response, context, report) {
  report.counts.sourceResponses += 1;
  return {
    name: response?.name || response?.status || 'Example Response',
    statusCode: Number.isInteger(response?.code) ? response.code : undefined,
    statusMessage: response?.status || '',
    headers: headersToInsomnia(response?.header || [], `${context} response`, report),
    body: typeof response?.body === 'string' ? response.body : valueToText(response?.body)
  };
}

function environmentDataFromFile(file, report) {
  return normalizeVariables(file.data.values || [], `${file.kind} ${file.name}`, report, { enabledField: true });
}

function emitBundle(ast, report) {
  const idCounters = { folder: 0, request: 0, response: 0, environment: 0 };
  const resources = [];

  resources.push({
    _id: '__WORKSPACE_ID__',
    _type: 'workspace',
    name: ast.name,
    ...(ast.description ? { description: ast.description } : {})
  });

  const baseData = { ...ast.variables };
  for (const globalsFile of ast.globalsFiles) {
    const data = environmentDataFromFile(globalsFile, report);
    report.warnings.push(`globals ${globalsFile.name}: merged into base environment; validate Insomnia global scope manually.`);
    for (const [key, value] of Object.entries(data)) {
      if (Object.prototype.hasOwnProperty.call(baseData, key)) {
        report.warnings.push(`globals ${globalsFile.name}: variable "${key}" collided with collection variable and was not overwritten.`);
      } else {
        baseData[key] = value;
      }
    }
  }

  resources.push({
    _id: '__BASE_ENVIRONMENT_ID__',
    _type: 'environment',
    parentId: '__WORKSPACE_ID__',
    name: 'Base Environment',
    data: baseData
  });

  for (const envFile of ast.environmentFiles) {
    idCounters.environment += 1;
    resources.push({
      _id: `__environment_${idCounters.environment}__`,
      _type: 'environment',
      parentId: '__BASE_ENVIRONMENT_ID__',
      name: envFile.name,
      data: environmentDataFromFile(envFile, report)
    });
  }

  const emitChildren = (children, parentId, inheritedPre, inheritedAfter, inheritedAuth) => {
    for (const child of children) {
      if (child.kind === 'folder') {
        idCounters.folder += 1;
        report.counts.targetFolders += 1;
        const folderId = `__folder_${idCounters.folder}__`;
        resources.push({
          _id: folderId,
          _type: 'folder',
          parentId,
          name: child.name,
          ...(child.description ? { description: child.description } : {}),
          ...(Object.keys(child.variables).length ? { environment: child.variables } : {})
        });
        emitChildren(
          child.children,
          folderId,
          inheritedPre.concat(child.preRequestScripts),
          inheritedAfter.concat(child.afterResponseScripts),
          child.auth || inheritedAuth
        );
      } else if (child.kind === 'request') {
        idCounters.request += 1;
        report.counts.targetRequests += 1;
        const requestId = `__request_${idCounters.request}__`;
        const preRewrite = rewriteScript(joinScriptParts(inheritedPre.concat(child.preRequestScripts)), `${child.name} pre-request`, report);
        const afterRewrite = rewriteScript(joinScriptParts(inheritedAfter.concat(child.afterResponseScripts)), `${child.name} after-response`, report);
        const resource = {
          _id: requestId,
          _type: 'request',
          parentId,
          name: child.name,
          ...(child.description ? { description: child.description } : {}),
          method: child.method,
          url: child.url,
          headers: child.headers,
          ...(child.parameters.length ? { parameters: child.parameters } : {}),
          ...(child.body ? { body: child.body } : {}),
          authentication: mapAuth(child.auth || inheritedAuth, child.name, report),
          preRequestScript: preRewrite.code,
          afterResponseScript: afterRewrite.code
        };
        report.scriptReports.push(...preRewrite.reports, ...afterRewrite.reports);
        if (resource.preRequestScript || resource.afterResponseScript) {
          report.counts.targetRequestsWithScripts += 1;
        }
        resources.push(resource);
        for (const response of child.responses || []) {
          idCounters.response += 1;
          report.counts.targetResponses += 1;
          resources.push({
            _id: `__response_${idCounters.response}__`,
            _type: 'response',
            parentId: requestId,
            name: response.name,
            ...(response.statusCode ? { statusCode: response.statusCode } : {}),
            ...(response.statusMessage ? { statusMessage: response.statusMessage } : {}),
            headers: response.headers,
            body: response.body
          });
        }
      }
    }
  };

  emitChildren(
    ast.children,
    '__WORKSPACE_ID__',
    ast.preRequestScripts,
    ast.afterResponseScripts,
    ast.auth
  );

  return {
    _type: 'export',
    __export_format: DEFAULT_EXPORT_FORMAT,
    __export_date: new Date().toISOString(),
    __export_source: SOURCE_NAME,
    resources
  };
}

function memberChain(node) {
  if (t.isIdentifier(node)) return [node.name];
  if (t.isThisExpression(node)) return ['this'];
  if (!t.isMemberExpression(node)) return null;
  const object = memberChain(node.object);
  if (!object) return null;
  let property;
  if (t.isIdentifier(node.property) && !node.computed) {
    property = node.property.name;
  } else if (t.isStringLiteral(node.property) || t.isNumericLiteral(node.property)) {
    property = String(node.property.value);
  } else {
    return null;
  }
  return object.concat(property);
}

function buildMember(chain) {
  return chain.slice(1).reduce((node, property) => t.memberExpression(node, t.identifier(property)), t.identifier(chain[0]));
}

function rewriteChain(chain, aliasMap, report, context) {
  if (!chain || chain.length === 0) return null;
  const alias = aliasMap.get(chain[0]);
  const expanded = alias ? alias.concat(chain.slice(1)) : chain;
  const text = expanded.join('.');

  const exact = new Map([
    ['pm.environment', ['insomnia', 'environment']],
    ['pm.collectionVariables', ['insomnia', 'collectionVariables']],
    ['pm.variables', ['insomnia', 'variables']],
    ['pm.globals', ['insomnia', 'globals']],
    ['pm.response', ['insomnia', 'response']],
    ['pm.response.code', ['insomnia', 'response', 'status']],
    ['pm.test', ['insomnia', 'test']],
    ['pm.expect', ['insomnia', 'expect']],
    ['pm.sendRequest', ['insomnia', 'sendRequest']]
  ]);

  if (exact.has(text)) {
    if (text.startsWith('pm.globals')) {
      report.warnings.push(`${context}: pm.globals was rewritten to insomnia.globals; validate global scope support manually.`);
    }
    if (text === 'pm.sendRequest') {
      report.warnings.push(`${context}: pm.sendRequest was rewritten to insomnia.sendRequest; validate callback flow manually.`);
    }
    return exact.get(text);
  }

  for (const [prefix, replacement] of exact.entries()) {
    const prefixParts = prefix.split('.');
    if (expanded.length > prefixParts.length && prefixParts.every((part, index) => expanded[index] === part)) {
      if (prefix === 'pm.response.code') continue;
      return replacement.concat(expanded.slice(prefixParts.length));
    }
  }

  return null;
}

function unsupportedScriptFindings(script) {
  const checks = [
    [/pm\.execution\.setNextRequest\s*\(/, 'pm.execution.setNextRequest is collection-runner control flow and is not equivalent in Insomnia.'],
    [/postman\.setNextRequest\s*\(/, 'postman.setNextRequest is collection-runner control flow and is not equivalent in Insomnia.'],
    [/pm\.visualizer\b/, 'pm.visualizer is unsupported and needs manual migration.'],
    [/pm\.cookies\b/, 'pm.cookies usage needs manual validation.'],
    [/pm\.request\b/, 'pm.request mutation or access needs manual validation.'],
    [/\brequire\s*\(/, 'external package usage needs manual validation in the Insomnia script runtime.']
  ];
  return checks.filter(([pattern]) => pattern.test(script)).map(([, message]) => message);
}

function compatibilityShim() {
  return `// Migrated from Postman to Insomnia.
// Compatibility layer generated by postman2insomnia because safe AST rewrite was not possible.
const pm = {
  environment: insomnia.environment,
  globals: insomnia.globals,
  collectionVariables: insomnia.collectionVariables,
  variables: insomnia.variables,
  response: {
    json: () => insomnia.response.json(),
    text: () => insomnia.response.text(),
    code: insomnia.response.status,
    headers: insomnia.response.headers,
    cookies: insomnia.response.cookies
  },
  test: insomnia.test,
  expect: insomnia.expect,
  sendRequest: insomnia.sendRequest
};
`;
}

function rewriteScript(script, context, report) {
  const reports = [];
  const trimmed = script.trim();
  if (!trimmed) return { code: '', reports };

  for (const finding of unsupportedScriptFindings(trimmed)) {
    const message = `${context}: ${finding}`;
    report.warnings.push(message);
    reports.push({ context, severity: 'warning', message });
  }

  if (/pm\s*\[/.test(trimmed) || /\{\s*[^}]+\s*\}\s*=\s*pm\b/.test(trimmed)) {
    const message = `${context}: complex pm aliasing detected; preserved with compatibility shim.`;
    report.warnings.push(message);
    reports.push({ context, severity: 'warning', message });
    return {
      code: `// TODO(postman2insomnia): ${message}\n${compatibilityShim()}\n${trimmed}`,
      reports
    };
  }

  try {
    const ast = parser.parse(trimmed, {
      sourceType: 'unambiguous',
      allowReturnOutsideFunction: true,
      plugins: ['topLevelAwait']
    });
    const aliasMap = new Map();

    traverse(ast, {
      VariableDeclarator(pathRef) {
        if (!t.isIdentifier(pathRef.node.id) || !pathRef.node.init) return;
        const chain = memberChain(pathRef.node.init);
        const rewritten = rewriteChain(chain, aliasMap, report, context);
        if (rewritten) {
          aliasMap.set(pathRef.node.id.name, rewritten);
          pathRef.node.init = buildMember(rewritten);
        }
      },
      MemberExpression(pathRef) {
        const parent = pathRef.parentPath;
        if (parent?.isMemberExpression() && parent.node.object === pathRef.node) return;
        const chain = memberChain(pathRef.node);
        const rewritten = rewriteChain(chain, aliasMap, report, context);
        if (rewritten && rewritten.join('.') !== chain?.join('.')) {
          pathRef.replaceWith(buildMember(rewritten));
        }
      }
    });

    const todoLines = unsupportedScriptFindings(trimmed).map((finding) => `// TODO(postman2insomnia): ${finding}`);
    const code = generate(ast, { comments: true, retainLines: false }).code;
    report.counts.emittedScriptBlocks += 1;
    return { code: todoLines.concat(code).join('\n'), reports };
  } catch (error) {
    const message = `${context}: script parse failed; preserved with compatibility shim (${error.message}).`;
    report.warnings.push(message);
    reports.push({ context, severity: 'warning', message });
    return {
      code: `// TODO(postman2insomnia): ${message}\n${compatibilityShim()}\n${trimmed}`,
      reports
    };
  }
}

function createReport() {
  return {
    warnings: [],
    errors: [],
    scriptReports: [],
    inputs: {},
    outputs: {},
    counts: {
      sourceRequests: 0,
      targetRequests: 0,
      sourceFolders: 0,
      targetFolders: 0,
      sourceResponses: 0,
      targetResponses: 0,
      sourceScriptEvents: 0,
      targetRequestsWithScripts: 0,
      emittedScriptBlocks: 0,
      enabledVariables: 0
    }
  };
}

function validateBundle(bundle, validateInsomnia, report) {
  const valid = validateInsomnia(bundle);
  if (!valid) {
    report.errors.push(`Generated Insomnia bundle failed schema validation: ${formatAjvErrors(validateInsomnia.errors)}`);
  }

  const ids = new Set(bundle.resources.map((resource) => resource._id));
  for (const resource of bundle.resources) {
    if (resource._type !== 'workspace' && !resource.parentId) {
      report.errors.push(`${resource._id}: missing parentId.`);
    } else if (resource.parentId && !ids.has(resource.parentId)) {
      report.errors.push(`${resource._id}: parentId ${resource.parentId} does not exist.`);
    }
    if (typeof resource.preRequestScript !== 'undefined' && typeof resource.preRequestScript !== 'string') {
      report.errors.push(`${resource._id}: preRequestScript must be a string.`);
    }
    if (typeof resource.afterResponseScript !== 'undefined' && typeof resource.afterResponseScript !== 'string') {
      report.errors.push(`${resource._id}: afterResponseScript must be a string.`);
    }
  }

  if (report.counts.sourceRequests !== report.counts.targetRequests) {
    report.errors.push(`Request count mismatch: source ${report.counts.sourceRequests}, target ${report.counts.targetRequests}.`);
  }
  if (report.counts.sourceFolders !== report.counts.targetFolders) {
    report.errors.push(`Folder count mismatch: source ${report.counts.sourceFolders}, target ${report.counts.targetFolders}.`);
  }
  if (report.counts.sourceResponses !== report.counts.targetResponses) {
    report.errors.push(`Response count mismatch: source ${report.counts.sourceResponses}, target ${report.counts.targetResponses}.`);
  }
}

async function writeReports(basePath, report) {
  const jsonPath = `${basePath}.migration-report.json`;
  const mdPath = `${basePath}.migration-report.md`;
  const scriptPath = `${basePath}.script-report.md`;

  report.outputs.migrationReportJson = jsonPath;
  report.outputs.migrationReportMarkdown = mdPath;
  report.outputs.scriptReportMarkdown = scriptPath;

  await fs.writeFile(jsonPath, `${JSON.stringify(report, null, 2)}\n`);
  await fs.writeFile(mdPath, migrationReportMarkdown(report));
  await fs.writeFile(scriptPath, scriptReportMarkdown(report));
}

function migrationReportMarkdown(report) {
  const lines = [
    '# Postman to Insomnia Migration Report',
    '',
    '## Counts',
    '',
    `- Source requests: ${report.counts.sourceRequests}`,
    `- Target requests: ${report.counts.targetRequests}`,
    `- Source folders: ${report.counts.sourceFolders}`,
    `- Target folders: ${report.counts.targetFolders}`,
    `- Source responses: ${report.counts.sourceResponses}`,
    `- Target responses: ${report.counts.targetResponses}`,
    `- Source script events: ${report.counts.sourceScriptEvents}`,
    `- Emitted script blocks: ${report.counts.emittedScriptBlocks}`,
    '',
    '## Errors',
    ''
  ];
  lines.push(...(report.errors.length ? report.errors.map((item) => `- ${item}`) : ['- None']));
  lines.push('', '## Warnings', '');
  lines.push(...(report.warnings.length ? report.warnings.map((item) => `- ${item}`) : ['- None']));
  return `${lines.join('\n')}\n`;
}

function scriptReportMarkdown(report) {
  const lines = ['# Script Compatibility Report', ''];
  if (report.scriptReports.length === 0) {
    lines.push('- No script compatibility warnings.');
  } else {
    for (const item of report.scriptReports) {
      lines.push(`- [${item.severity}] ${item.message}`);
    }
  }
  return `${lines.join('\n')}\n`;
}

async function convertSource(options) {
  await loadRuntime();
  const sourcePath = path.resolve(options.source);
  const outputPath = path.resolve(options.output || path.join(sourcePath, 'insomnia-migration'));
  await fs.mkdir(outputPath, { recursive: true });

  const [postmanSchema, environmentSchema, insomniaSchema] = await Promise.all([
    loadSchema('schemas/postman-collection-v2.1.schema.json'),
    loadSchema('schemas/postman-environment.schema.json'),
    loadSchema('schemas/insomnia-v11-import.schema.json')
  ]);
  const validateCollection = makeValidator(postmanSchema);
  const validateEnvironment = makeValidator(environmentSchema);
  const validateInsomnia = makeValidator(insomniaSchema);

  const jsonFiles = await listJsonFiles(sourcePath);
  const classified = { collection: [], environment: [], globals: [], unknown: [] };
  for (const filePath of jsonFiles) {
    const data = await readJson(filePath);
    const kind = classifyJson(filePath, data);
    classified[kind].push({ filePath, data, kind, name: data.name || path.basename(filePath, '.json') });
  }

  if (classified.collection.length === 0) {
    throw new Error(`No Postman collection JSON files found under ${sourcePath}.`);
  }

  const environmentFiles = classified.environment.map((file) => validateEnvFile(file, validateEnvironment));
  const globalsFiles = classified.globals.map((file) => validateEnvFile(file, validateEnvironment));
  const results = [];
  const usedSlugs = new Map();

  for (const collectionFile of classified.collection) {
    const report = createReport();
    report.inputs.source = sourcePath;
    report.inputs.collection = collectionFile.filePath;
    report.inputs.environments = environmentFiles.map((file) => file.filePath);
    report.inputs.globals = globalsFiles.map((file) => file.filePath);
    report.inputs.unknown = classified.unknown.map((file) => file.filePath);

    if (!validateCollection(collectionFile.data)) {
      report.errors.push(`Postman collection schema validation failed: ${formatAjvErrors(validateCollection.errors)}`);
    }
    const schemaUrl = collectionFile.data.info?.schema || '';
    if (!schemaUrl.includes('v2.1.0')) {
      report.warnings.push(`Collection schema is not explicitly Postman v2.1.0: ${schemaUrl || 'missing'}.`);
    }
    for (const unknown of classified.unknown) {
      report.warnings.push(`Unclassified JSON file ignored: ${unknown.filePath}.`);
    }

    const ast = normalizeCollection(collectionFile.data, collectionFile.filePath, environmentFiles, globalsFiles, report);
    const bundle = emitBundle(ast, report);
    validateBundle(bundle, validateInsomnia, report);

    const baseSlug = slugify(ast.name);
    const seen = usedSlugs.get(baseSlug) || 0;
    usedSlugs.set(baseSlug, seen + 1);
    const slug = seen === 0 ? baseSlug : `${baseSlug}-${seen + 1}`;
    const basePath = path.join(outputPath, slug);
    const insomniaPath = `${basePath}.insomnia.json`;
    report.outputs.insomniaJson = insomniaPath;

    await fs.writeFile(insomniaPath, `${JSON.stringify(bundle, null, 2)}\n`);
    await writeReports(basePath, report);

    if (options.strict && report.warnings.length) {
      report.errors.push(`Strict mode failed because ${report.warnings.length} warning(s) were reported.`);
      await writeReports(basePath, report);
    }

    results.push({ bundle, report, insomniaPath });
  }

  const errors = results.flatMap((result) => result.report.errors);
  if (errors.length) {
    const message = errors.map((error) => `- ${error}`).join('\n');
    throw new Error(`Conversion completed with validation errors:\n${message}`);
  }
  return results;
}

function validateEnvFile(file, validateEnvironment) {
  if (!validateEnvironment(file.data)) {
    const error = new Error(`Postman environment/global schema validation failed for ${file.filePath}: ${formatAjvErrors(validateEnvironment.errors)}`);
    error.file = file.filePath;
    throw error;
  }
  return file;
}

export { convertSource, rewriteScript };

function isDirectRun() {
  return process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
}

if (isDirectRun()) {
  (async () => {
    const options = parseArgs(process.argv.slice(2));
    if (options.help) {
      console.log(usage());
      return;
    }
    const results = await convertSource(options);
    for (const result of results) {
      console.log(result.insomniaPath);
    }
  })().catch((error) => {
    console.error(`[postman2insomnia] ${error.message}`);
    process.exit(1);
  });
}
