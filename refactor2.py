import os
import glob
import re

files = glob.glob('frontend/src/pages/*.tsx')
for fpath in files:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove old API_BASE const
    content = re.sub(r"const API_BASE\s*=\s*['\"].*?['\"]", "", content)
    content = re.sub(r"const PHONE\s*=\s*['\"].*?['\"]", "const PHONE = TEST_PHONE", content)
    
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
