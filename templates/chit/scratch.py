import re
import sys

file_path = r'd:\Finance_online_Application\sd-finance-tool\templates\chit\groups_edit.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Font Awesome icons with Lucide icons
def replace_fa_with_lucide(text):
    # Mapping for specific static icons based on user rules
    mapping = {
        r'<i class="fa-solid fa-arrow-left text-\[10px\]"></i>': '<i data-lucide="arrow-left" class="w-3.5 h-3.5 stroke-[1.8]"></i>',
        r'<i class="fa-solid fa-pen text-\[10px\]"></i>': '<i data-lucide="pencil" class="w-3.5 h-3.5 stroke-[1.8]"></i>',
        r'<i class="fa-solid fa-arrow-trend-up text-emerald-600"></i>': '<i data-lucide="trending-up" class="w-4 h-4 stroke-[1.8] text-emerald-600 dark:text-emerald-400"></i>',
        r'<i id="marginToggleIcon" class="fa-solid fa-chevron-down text-emerald-600 text-xs transition-transform"></i>': '<i id="marginToggleIcon" data-lucide="chevron-down" class="w-3.5 h-3.5 stroke-[1.8] text-emerald-600 dark:text-emerald-400 transition-transform"></i>',
        r'<i id="advToggleIcon" class="fa-solid fa-chevron-down text-\[10px\]"></i>': '<i id="advToggleIcon" data-lucide="chevron-down" class="w-3.5 h-3.5 stroke-[1.8]"></i>',
        r'<i class="fa-regular fa-trash-can text-xs"></i>': '<i data-lucide="trash-2" class="w-3.5 h-3.5 stroke-[1.8]"></i>',
        r'<i class="fa-solid fa-trash-can"></i>': '<i data-lucide="trash-2" class="w-4 h-4 stroke-[1.8]"></i>',
        r'<i class="fa-solid fa-plus text-xs"></i>': '<i data-lucide="plus" class="w-3.5 h-3.5 stroke-[1.8]"></i>',
        r'<i class="fa-solid fa-user-plus text-\[10px\]"></i>': '<i data-lucide="user-plus" class="w-3.5 h-3.5 stroke-[1.8]"></i>',
        r'<i class="fa-solid fa-xmark"></i>': '<i data-lucide="x" class="w-4 h-4 stroke-[1.8]"></i>',
        r'<i class="fa-solid fa-magnifying-glass absolute left-3\.5 top-1/2 -translate-y-1/2 text-slate-400 text-xs"></i>': '<i data-lucide="search" class="w-3.5 h-3.5 stroke-[1.8] absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500"></i>',
        r'<i class="fa-solid fa-circle-check text-emerald-600 text-sm"></i>': '<i data-lucide="check-circle" class="w-4 h-4 stroke-[1.8] text-emerald-600 dark:text-emerald-400"></i>',
        r'<i class="fa-solid fa-user-plus text-xs text-emerald-600"></i>': '<i data-lucide="user-plus" class="w-3.5 h-3.5 stroke-[1.8] text-emerald-600 dark:text-emerald-400"></i>',
        r'<i id="quickNewCustChevron" class="fa-solid fa-chevron-down text-\[10px\]"></i>': '<i id="quickNewCustChevron" data-lucide="chevron-down" class="w-3.5 h-3.5 stroke-[1.8]"></i>',
        r'<i class="fa-solid fa-chevron-down text-\[10px\]"></i>': '<i data-lucide="chevron-down" class="w-3.5 h-3.5 stroke-[1.8]"></i>'
    }
    for old, new in mapping.items():
        text = re.sub(old, new, text)
        
    # Also handle dynamic template literal icons in JS
    text = text.replace(
        '<i class="fa-solid ${isSelected ? \'fa-check\' : \'fa-user\'} text-[10px] opacity-70"></i>',
        '<i data-lucide="${isSelected ? \'check\' : \'user\'}" class="w-3.5 h-3.5 stroke-[1.8] opacity-70"></i>'
    )
    
    # Fix advToggleIcon class assignments in JS
    text = text.replace(
        "icon.className = 'fa-solid fa-chevron-down text-[10px]';",
        "icon.setAttribute('data-lucide', 'chevron-down');\n      if (window.lucide) lucide.createIcons({attrs: {class: 'w-3.5 h-3.5 stroke-[1.8]'}, nameAttr: 'data-lucide'});"
    )
    text = text.replace(
        "icon.className = 'fa-solid fa-chevron-up text-[10px]';",
        "icon.setAttribute('data-lucide', 'chevron-up');\n      if (window.lucide) lucide.createIcons({attrs: {class: 'w-3.5 h-3.5 stroke-[1.8]'}, nameAttr: 'data-lucide'});"
    )

    return text

content = replace_fa_with_lucide(content)

# Regex to safely replace words only if not already followed by dark:
def add_dark_classes(text, old_class, dark_class):
    return re.sub(rf'(?<!dark:)\b{re.escape(old_class)}\b(?!\s*dark:)', f'{old_class} {dark_class}', text)

# Common utility mappings
colors = [
    ('bg-slate-100', 'dark:bg-chitDark-elevated'),
    ('bg-white', 'dark:bg-chitDark-surface'),
    ('bg-slate-50', 'dark:bg-chitDark-bg'),
    ('bg-slate-900', 'dark:bg-white dark:text-slate-900'),
    ('text-slate-900', 'dark:text-slate-100'),
    ('text-slate-800', 'dark:text-slate-100'),
    ('text-slate-700', 'dark:text-slate-300'),
    ('text-slate-600', 'dark:text-slate-300'),
    ('text-slate-500', 'dark:text-slate-400'),
    ('text-slate-400', 'dark:text-slate-500'),
    ('text-slate-300', 'dark:text-slate-600'),
    ('border-slate-200', 'dark:border-chitDark-border'),
    ('border-slate-100', 'dark:border-chitDark-border'),
    ('hover:text-slate-800', 'dark:hover:text-slate-200'),
    ('hover:bg-slate-100', 'dark:hover:bg-white/[0.05]'),
    ('hover:bg-slate-50', 'dark:hover:bg-white/[0.02]'),
    ('hover:bg-slate-800', 'dark:hover:bg-slate-200'),
    
    ('bg-emerald-50/40', 'dark:bg-emerald-900/10'),
    ('border-emerald-200/80', 'dark:border-emerald-800/30'),
    ('bg-emerald-50', 'dark:bg-emerald-900/20'),
    ('border-emerald-100', 'dark:border-emerald-800/30'),
    ('border-emerald-200', 'dark:border-emerald-800/30'),
    ('text-emerald-950', 'dark:text-emerald-100'),
    ('text-emerald-600', 'dark:text-emerald-400'),
    ('text-emerald-700', 'dark:text-emerald-400'),
    
    ('bg-rose-50/40', 'dark:bg-rose-900/10'),
    ('bg-rose-50/70', 'dark:bg-rose-900/20'),
    ('border-rose-200', 'dark:border-rose-800/30'),
    ('border-rose-300', 'dark:border-rose-800/40'),
    ('text-rose-800', 'dark:text-rose-400'),
    ('text-rose-700', 'dark:text-rose-400'),
    ('text-rose-900', 'dark:text-rose-300'),
    ('hover:bg-rose-100', 'dark:hover:bg-rose-900/30'),
    
    ('bg-amber-50', 'dark:bg-amber-900/20'),
    ('border-amber-200/80', 'dark:border-amber-800/30'),
    ('text-amber-950', 'dark:text-amber-100'),
    ('text-amber-800/90', 'dark:text-amber-200/90'),
    ('text-amber-800', 'dark:text-amber-400'),
    
    ('focus:bg-white', 'dark:focus:bg-chitDark-elevated'),
    ('focus:ring-slate-900', 'dark:focus:ring-slate-400'),
    
    ('bg-slate-900/60', 'dark:bg-slate-900/80'),
]

# Specifically replace some inputs for dark mode styling
content = content.replace('bg-slate-900 text-white', 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900')

for old, dark in colors:
    content = add_dark_classes(content, old, dark)

# Add card-shine
content = content.replace('cb-card', 'cb-card card-shine')

# Add lucide.createIcons() to injected JS logic
content = content.replace('container.appendChild(card);\n    });', 'container.appendChild(card);\n    });\n    if (window.lucide) lucide.createIcons();')
content = content.replace('container.appendChild(btn);\n    });', 'container.appendChild(btn);\n    });\n    if (window.lucide) lucide.createIcons();')

if 'lucide.createIcons()' not in content.split('</script>')[-2]:
    content = content.replace('</script>', '  if (window.lucide) lucide.createIcons();\n</script>')


with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
