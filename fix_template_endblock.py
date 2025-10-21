#!/usr/bin/env python3
"""
Fix template endblock issues
"""

def check_template_blocks(file_path):
    """Check for unmatched blocks in a template file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    block_stack = []
    
    for i, line in enumerate(lines, 1):
        if '{% block' in line and not line.strip().startswith('#'):
            block_name = line.split('{% block')[1].split('%}')[0].strip()
            block_stack.append((i, block_name))
            print(f"Line {i}: Opening block '{block_name}'")
        elif '{% endblock' in line and not line.strip().startswith('#'):
            if block_stack:
                _, block_name = block_stack.pop()
                print(f"Line {i}: Closing block '{block_name}'")
            else:
                print(f"Line {i}: ERROR - Closing block without opening block!")
    
    if block_stack:
        print(f"\nERROR: Unclosed blocks:")
        for line_num, block_name in block_stack:
            print(f"  Line {line_num}: '{block_name}'")
        return False
    else:
        print(f"\n✓ All blocks properly closed")
        return True

if __name__ == "__main__":
    print("Checking role_teacher_dashboard.html...")
    check_template_blocks('templates/management/role_teacher_dashboard.html')
