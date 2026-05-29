import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

original = content

# Fix: add type="button" to all <button> tags that don't have a type attribute
# Pattern: <button (not followed by type= anywhere before the >)
def add_button_type(m):
    full = m.group(0)
    attrs = m.group(1)
    if 'type=' not in attrs:
        return '<button type="button"' + attrs + '>'
    return full

content = re.sub(r'<button((?:[^>](?!type=))*?)>', add_button_type, content)

# Count changes
btn_before = original.count('<button ')
btn_after_typed = content.count('type="button"') + content.count("type='button'") + content.count('type="submit"')
print('Buttons before:', btn_before)
print('Typed buttons after:', btn_after_typed)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done - buttons fixed.')
