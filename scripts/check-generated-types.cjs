// Read-only compiler analysis. Does not import generated JS or execute Vite configuration.
const fs = require('fs');
const path = require('path');
const trustedModules = path.resolve(__dirname, '../frontend/node_modules');
const ts = require(path.join(trustedModules, 'typescript'));
const frontend = path.resolve(process.argv[2], 'frontend');
const allowed = file => [frontend, trustedModules].some(root => {
  const relative = path.relative(root, path.resolve(file));
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
});
const config = JSON.parse(fs.readFileSync(path.join(frontend, 'tsconfig.json'), 'utf8'));
const parsed = ts.convertCompilerOptionsFromJson(config.compilerOptions || {}, frontend);
const options = {...parsed.options, noEmit: true, plugins: undefined};
const files = [];
function visit(directory) {
  for (const entry of fs.readdirSync(directory, {withFileTypes: true})) {
    if (entry.isSymbolicLink()) throw new Error('Linked source is forbidden');
    const file = path.join(directory, entry.name);
    if (entry.isDirectory() && entry.name !== 'node_modules') visit(file);
    else if (entry.isFile() && /\.tsx?$/.test(entry.name)) files.push(file);
  }
}
visit(frontend);
const host = ts.createCompilerHost(options);
const read = host.readFile;
host.readFile = file => allowed(file) ? read(file) : undefined;
host.resolveModuleNames = (names, containing) => names.map(name => {
  let resolved = ts.resolveModuleName(name, containing, options, host).resolvedModule;
  if (!resolved && !name.startsWith('.')) {
    resolved = ts.resolveModuleName(name, path.resolve(__dirname, '../frontend/src/__static__.tsx'), options, host).resolvedModule;
  }
  return resolved && allowed(resolved.resolvedFileName) ? resolved : undefined;
});
const program = ts.createProgram(files, options, host);
const diagnostics = [...parsed.errors, ...ts.getPreEmitDiagnostics(program)];
const result = diagnostics.map(d => ({
  file: d.file && allowed(d.file.fileName) ? path.relative(frontend, d.file.fileName) : undefined,
  line: d.file && d.start !== undefined ? d.file.getLineAndCharacterOfPosition(d.start).line + 1 : undefined,
  message: ts.flattenDiagnosticMessageText(d.messageText, '\n')
}));
console.log(JSON.stringify({check: 'static_types_only', files: files.length, passed: result.length === 0, diagnostics: result}, null, 2));
process.exitCode = result.length ? 1 : 0;
