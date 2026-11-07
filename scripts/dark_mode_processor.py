import re
import os

def replace_icons(content):
    icon_map = {
        'fa-arrow-left': 'arrow-left',
        'fa-camera': 'camera',
        'fa-user': 'user',
        'fa-phone': 'phone',
        'fa-chevron-down': 'chevron-down',
        'fa-chevron-up': 'chevron-up',
        'fa-envelope': 'mail',
        'fa-location-dot': 'map-pin',
        'fa-globe': 'globe',
        'fa-shield-heart': 'shield-check',
        'fa-xmark': 'x',
        'fa-check': 'check',
        'fa-circle-check': 'check-circle',
        'fa-plus': 'plus',
        'fa-ellipsis-vertical': 'more-vertical',
        'fa-clock': 'clock',
        'fa-pencil': 'pencil',
        'fa-file-arrow-down': 'file-down',
        'fa-trash-can': 'trash-2',
        'fa-arrow-trend-down': 'trending-down',
        'fa-arrow-down-left': 'arrow-down-left',
        'fa-arrow-up-right': 'arrow-up-right',
        'fa-magnifying-glass': 'search',
        'fa-money-bill-1-wave': 'banknote',
        'fa-mobile-screen': 'smartphone',
        'fa-building-columns': 'landmark',
        'fa-money-check': 'credit-card',
        'fa-hand-holding-dollar': 'banknote',
        'fa-table-cells': 'layout-grid',
        'fa-receipt': 'receipt',
        'fa-user-check': 'user-check',
        'fa-share-nodes': 'share-2',
        'fa-circle-info': 'info',
        'fa-folder-open': 'folder-open',
        'fa-circle': 'circle'
    }

    def repl(m):
        cls_attr = m.group(1)
        classes = cls_attr.split()
        
        icon_name = 'circle'
        other_classes = []
        for c in classes:
            if c.startswith('fa-') and c != 'fa-solid' and c != 'fa-regular':
                icon_name = icon_map.get(c, c.replace('fa-', ''))
            elif c not in ('fa-solid', 'fa-regular'):
                other_classes.append(c)
        
        lucide_classes = " ".join(other_classes)
        return f'<i data-lucide="{icon_name}" class="w-4 h-4 stroke-[1.8] {lucide_classes}"></i>'

    # Handle standard HTML tags
    content = re.sub(r'<i\s+class="([^"]*fa-(?:solid|regular)[^"]*)"></i>', repl, content)
    
    # Handle JS string literals with icons
    content = re.sub(r'<i\s+class=\\?["\']([^"\']*fa-(?:solid|regular)[^"\']*)\\?["\']></i>', repl, content)

    return content

def inject_lucide_js(content):
    if 'lucide.createIcons()' not in content:
        # insert at end of block extra_scripts if available, or just at end of script tags inside it
        if '{% endblock %}' in content:
            script_injection = """
  if (window.lucide) {
    lucide.createIcons();
  }
"""
            # find last </script> before {% endblock %}
            last_script_idx = content.rfind('</script>')
            if last_script_idx != -1:
                content = content[:last_script_idx] + script_injection + content[last_script_idx:]
    return content

def add_dark_mode(content):
    # This maps regular classes to their dark variants
    
    # 1. Backgrounds
    content = content.replace('bg-white', 'bg-white dark:bg-chitDark-surface')
    content = content.replace('bg-slate-50', 'bg-slate-50 dark:bg-chitDark-bg')
    content = content.replace('bg-slate-100', 'bg-slate-100 dark:bg-chitDark-elevated')
    content = content.replace('bg-slate-200', 'bg-slate-200 dark:bg-slate-800')
    content = content.replace('bg-slate-900', 'bg-slate-900 dark:bg-white')
    content = content.replace('bg-slate-800', 'bg-slate-800 dark:bg-slate-200')
    
    # 2. Text Colors
    content = content.replace('text-slate-900', 'text-slate-900 dark:text-slate-100')
    content = content.replace('text-slate-800', 'text-slate-800 dark:text-slate-200')
    content = content.replace('text-slate-700', 'text-slate-700 dark:text-slate-300')
    content = content.replace('text-slate-600', 'text-slate-600 dark:text-slate-400')
    content = content.replace('text-slate-500', 'text-slate-500 dark:text-slate-400')
    content = content.replace('text-slate-400', 'text-slate-400 dark:text-slate-500')
    
    # Text on dark background (bg-slate-900 usually has text-white)
    content = content.replace('text-white', 'text-white dark:text-slate-900')
    
    # 3. Borders
    content = content.replace('border-slate-200', 'border-slate-200 dark:border-slate-700/50')
    content = content.replace('border-slate-300', 'border-slate-300 dark:border-slate-600')
    content = content.replace('border-slate-100', 'border-slate-100 dark:border-slate-800')
    
    # 4. Specific components / Premium polish
    content = content.replace('shadow-xs', 'shadow-xs card-shine dark:shadow-none')
    content = content.replace('shadow-2xs', 'shadow-2xs card-shine dark:shadow-none')
    content = content.replace('card-shadow', 'card-shadow card-shine dark:shadow-none')
    
    # Fix broken string replace if "dark:text-slate-900" is double matched
    content = content.replace('dark:bg-white dark:text-slate-900', 'dark:bg-white dark:text-slate-900')
    
    # Add createIcons in dynamic rendering loops
    content = content.replace("container.appendChild(card);", "container.appendChild(card);\n      if(window.lucide) { lucide.createIcons(); }")
    content = content.replace("rowsContainer.appendChild(div);", "rowsContainer.appendChild(div);\n      if(window.lucide) { lucide.createIcons(); }")
    
    return content

for filename in ['member_form.html', 'member_detail.html']:
    filepath = os.path.join(r'd:\Finance_online_Application\sd-finance-tool\templates\chit', filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = replace_icons(content)
    content = add_dark_mode(content)
    content = inject_lucide_js(content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Processing complete.")
