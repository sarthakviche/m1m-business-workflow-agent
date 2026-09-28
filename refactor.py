import os
import glob
import re

files = glob.glob('frontend/src/pages/*.tsx')
for fpath in files:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove old API_BASE const
    content = re.sub(r'const API_BASE\s*=\s*[''"]http://127\.0\.0\.1:8000[''"]\n?', '', content)
    
    # Add imports if fetch is used
    if 'fetch(' in content and 'API_BASE' not in content:
        # maybe we need API_BASE, wait we'll just check if we need imports
        pass

    import_statement = "import { API_BASE, TEST_PHONE } from '../api/config';\n"
    if import_statement not in content:
        # insert after last import
        imports_end = [m.end() for m in re.finditer(r'^import .*\n', content, re.MULTILINE)]
        if imports_end:
            insert_pos = imports_end[-1]
            content = content[:insert_pos] + import_statement + content[insert_pos:]
        else:
            content = import_statement + content

    # Replace hardcoded endpoints
    content = content.replace('http://localhost:8000/chat/message', '/chat')
    content = content.replace('http://localhost:8000', '')
    
    # Replace phone
    content = content.replace('9876543210', '')

    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
