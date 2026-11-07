import re
import os

def fixup_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix chained dark classes: e.g. dark:text-slate-400 dark:text-slate-500
    # Actually, it's easier to just find the pattern `dark:\S+ dark:\S+`
    content = re.sub(r'dark:text-slate-400 dark:text-slate-500', 'dark:text-slate-400', content)
    content = re.sub(r'dark:text-slate-300 dark:text-slate-400', 'dark:text-slate-300', content)
    content = re.sub(r'dark:text-slate-200 dark:text-slate-300', 'dark:text-slate-200', content)
    content = re.sub(r'dark:text-slate-100 dark:text-slate-200', 'dark:text-slate-100', content)
    content = re.sub(r'dark:bg-slate-200 dark:bg-slate-800', 'dark:bg-slate-200', content)
    
    # Fix broken borders like dark:border-slate-700/50/90
    content = re.sub(r'dark:border-slate-700/50/\d+', 'dark:border-slate-700/50', content)
    content = re.sub(r'dark:border-slate-700/50/80', 'dark:border-slate-700/50', content)

    # Some missed things
    content = content.replace('dark:bg-chitDark-surface focus:outline-none focus:ring-2 focus:ring-slate-900', 'dark:bg-chitDark-surface focus:outline-none focus:ring-2 focus:ring-slate-900 dark:focus:ring-white')
    content = content.replace('dark:bg-chitDark-surface focus:outline-none focus:ring-2 focus:ring-emerald-400', 'dark:bg-chitDark-surface focus:outline-none focus:ring-2 focus:ring-emerald-400 dark:focus:ring-emerald-500')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for filename in ['member_form.html', 'member_detail.html']:
    filepath = os.path.join(r'd:\Finance_online_Application\sd-finance-tool\templates\chit', filename)
    fixup_file(filepath)

print("Fixup complete.")
