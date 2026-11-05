"""
Script to replace all emojis across Jinja2 templates with {{ icon('...') }} SVG calls.
"""
import glob
import re
import sys

mapping = {
    # Combined emojis first
    '🧑‍🏫': "{{ icon('mentor') }}",
    '👨‍👩‍👦': "{{ icon('family') }}",
    '🗓️': "{{ icon('calendar') }}",
    '🗓': "{{ icon('calendar') }}",
    '📅': "{{ icon('calendar') }}",
    '🗑️': "{{ icon('trash') }}",
    '🗑': "{{ icon('trash') }}",
    '➕': "{{ icon('plus') }}",
    '🎓': "{{ icon('student') }}",
    '📝': "{{ icon('pencil') }}",
    '📖': "{{ icon('book') }}",
    '📞': "{{ icon('phone') }}",
    '🔄': "{{ icon('refresh') }}",
    '✏️': "{{ icon('edit') }}",
    '✏': "{{ icon('edit') }}",
    '📋': "{{ icon('clipboard') }}",
    '💾': "{{ icon('backup') }}",
    '📦': "{{ icon('package') }}",
    '⚙️': "{{ icon('settings') }}",
    '⚙': "{{ icon('settings') }}",
    '✅': "{{ icon('check-circle') }}",
    '🔔': "{{ icon('bell') }}",
    '📜': "{{ icon('history') }}",
    '📈': "{{ icon('trending-up') }}",
    '📑': "{{ icon('report') }}",
    '🎯': "{{ icon('target') }}",
    '💡': "{{ icon('lightbulb') }}",
    '👥': "{{ icon('users') }}",
    '⚠️': "{{ icon('alert') }}",
    '⚠': "{{ icon('alert') }}",
    '✉️': "{{ icon('mail') }}",
    '✉': "{{ icon('mail') }}",
    '👉': "{{ icon('arrow-right') }}",
    '📊': "{{ icon('dashboard') }}",
    '🔑': "{{ icon('key') }}",
    '👁️': "{{ icon('eye') }}",
    '👁': "{{ icon('eye') }}",
    '⚡': "{{ icon('zap') }}",
    '💬': "{{ icon('chat') }}",
    '📥': "{{ icon('download') }}",
    '🖨️': "{{ icon('printer') }}",
    '🖨': "{{ icon('printer') }}",
    '🔍': "{{ icon('search') }}",
    '❌': "{{ icon('close') }}",
    '👤': "{{ icon('user') }}",
    '🏠': "{{ icon('home') }}",
    '🚪': "{{ icon('logout') }}",
    '🔒': "{{ icon('lock') }}",
    '✨': "{{ icon('sparkles') }}",
    '🚨': "{{ icon('alert') }}",
    '🎉': "{{ icon('sparkles') }}",
    '☕': "{{ icon('calendar') }}",
    '🕒': "{{ icon('clock') }}",
    '⏰': "{{ icon('clock') }}",
    '🟢': "{{ icon('check-circle') }}",
    '📍': "{{ icon('school') }}",
    '🚫': "{{ icon('close') }}",
    '✍️': "{{ icon('edit') }}",
    '✍': "{{ icon('edit') }}",
    '👋': "{{ icon('user') }}",
    'ℹ️': "{{ icon('info') }}",
    'ℹ': "{{ icon('info') }}",
    '🧑': "{{ icon('user') }}",
    '🏫': "{{ icon('school') }}",
    '☰': "{{ icon('menu') }}",
    '📂': "{{ icon('package') }}"
}

files = glob.glob('templates/**/*.html', recursive=True)
count = 0
for f in files:
    with open(f, 'r', encoding='utf-8') as fp:
        content = fp.read()
    orig = content
    for emoji, repl in mapping.items():
        content = content.replace(emoji, repl)
    if content != orig:
        with open(f, 'w', encoding='utf-8') as fp:
            fp.write(content)
        count += 1
        print(f"Updated: {f}")

print(f"Total files updated: {count}")

