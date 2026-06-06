import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

scripts = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
js = scripts[1]

# Remove template literals to find real var declarations
clean = re.sub(r'`[^`]*`', '``', js, flags=re.DOTALL)
clean = re.sub(r'"[^"]*"', '""', clean)

# CSS var() are fine - only flag JS var declarations
var_decls = re.findall(r'\bvar\b\s+(\w+)', clean)
css_vars = clean.count('var(--')

print('CSS var() calls (OK):', css_vars)
print('Real JS var declarations (should be const/let):', len(var_decls))
for v in var_decls:
    print(' -', v)

with open('temp_check.js', 'w', encoding='utf-8') as f:
    f.write(js)
print('\nWritten temp_check.js for node validation')
