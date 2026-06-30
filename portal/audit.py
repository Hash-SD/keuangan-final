import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

issues = []

# 1. Check meta description
if 'meta name="description"' not in content:
    issues.append('MISSING: meta description tag')

# 2. Check display=swap on fonts
if 'display=swap' not in content:
    issues.append('PERF: Google fonts missing display=swap')

# 3. Check JavaScript var declarations. CSS custom properties use var(...)
# legitimately, so only flag declaration-like tokens such as `var name`.
vars_used = re.findall(r'\bvar\s+[$A-Za-z_]', content)
if vars_used:
    issues.append('JS: var used ' + str(len(vars_used)) + ' times - should use const/let')

# 4. Check rel noopener on external links
ext_links = re.findall(r'<a[^>]+target=["\']_blank["\'][^>]*>', content)
for lnk in ext_links:
    if 'noreferrer' not in lnk:
        issues.append('SECURITY: target=_blank without noreferrer: ' + lnk[:100])

# 5. Check buttons without type
btn_pattern = re.compile(r'<button([^>]*)>')
for m in btn_pattern.finditer(content):
    attrs = m.group(1)
    if 'type=' not in attrs:
        issues.append('HTML: button without type attribute: ' + m.group(0)[:80])

# 6. Check html lang
if '<html lang=' not in content:
    issues.append('A11Y: missing lang attribute on html tag')

# 7. Check for title
if '<title>' not in content:
    issues.append('SEO: missing title tag')

print('\n'.join(issues) if issues else 'No critical issues found')
print('\nTotal issues found: ' + str(len(issues)))
