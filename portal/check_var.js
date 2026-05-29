const fs = require('fs');
const js = fs.readFileSync('temp_check.js', 'utf-8');

// Remove template literals and strings to find real var declarations
const clean = js
  .replace(/`[\s\S]*?`/g, '``')
  .replace(/"[^"]*"/g, '""')
  .replace(/'[^']*'/g, "''");

const varDecls = clean.match(/\bvar\b\s+\w+/g) || [];
const cssVars = (js.match(/var\(--/g) || []).length;

console.log('CSS var() calls (OK):', cssVars);
console.log('Real JS var declarations:', varDecls.length);
varDecls.forEach(v => console.log(' -', v));

// Validate syntax
try {
  new Function(js);
  console.log('\nJS Syntax: OK');
} catch(e) {
  console.error('\nJS Syntax ERROR:', e.message);
}
