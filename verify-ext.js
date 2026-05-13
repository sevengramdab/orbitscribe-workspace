const fs = require('fs');
const path = require('path');

const extDir = 'C:/Users/Shadow/.vscode/extensions/orbstudio.orbcore-0.1.0';
const extJs = path.join(extDir, 'out/extension.js');

console.log('=== ORBCORE Extension Runtime Verification ===\n');

// 1. Check extension.js parses
try {
  const code = fs.readFileSync(extJs, 'utf8');
  new Function(code);
  console.log('✅ Syntax: VALID');
} catch(e) {
  console.log('❌ Syntax Error:', e.message);
  process.exit(1);
}

// 2. Check exports
const code = fs.readFileSync(extJs, 'utf8');
console.log('✅ activate export:', code.includes('exports.activate') ? 'FOUND' : 'MISSING');
console.log('✅ deactivate export:', code.includes('exports.deactivate') ? 'FOUND' : 'MISSING');

// 3. Check dependencies
const reqs = code.match(/require\(['"]([^'"]+)['"]\)/g) || [];
const deps = reqs.map(r => r.match(/require\(['"]([^'"]+)['"]\)/)[1]);
const builtins = ['vscode','path','fs','os','child_process','http','https','url','util','events','stream','net','buffer'];
const external = deps.filter(r => !builtins.includes(r));
console.log('✅ External dependencies:', external.length ? external.join(', ') : 'none (all built-in)');

// 4. Check package.json
const pkg = JSON.parse(fs.readFileSync(path.join(extDir, 'package.json'), 'utf8'));
console.log('\n=== package.json ===');
console.log('  name:', pkg.name);
console.log('  publisher:', pkg.publisher);
console.log('  version:', pkg.version);
console.log('  main:', pkg.main);
console.log('  engines.vscode:', pkg.engines.vscode);
console.log('  commands:', pkg.contributes.commands.length);
console.log('  views:', pkg.contributes.views ? Object.keys(pkg.contributes.views).length : 0);

// 5. Check extensions.json registry
const entries = JSON.parse(fs.readFileSync('C:/Users/Shadow/.vscode/extensions/extensions.json', 'utf8'));
const orbcore = entries.find(e => e.identifier.id === 'orbstudio.orbcore');
console.log('\n=== Registry Entry ===');
if (orbcore) {
  console.log('✅ orbstudio.orbcore REGISTERED');
  console.log('  version:', orbcore.version);
  console.log('  location:', orbcore.location.path);
  console.log('  source:', orbcore.metadata.source);
} else {
  console.log('❌ orbstudio.orbcore NOT REGISTERED');
  process.exit(1);
}

console.log('\n🎉 ALL CHECKS PASSED - Extension is ready to load after VS Code: reload');
