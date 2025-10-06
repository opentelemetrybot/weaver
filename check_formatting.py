#!/usr/bin/env python3

import sys

def analyze_yaml_formatting(file_path):
    """
    Analyzes the blank line pattern after the 'on:' block in a YAML workflow file.
    Use this to determine which formatting rule (A or B) to apply.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # Find the 'on:' root-level block
    on_block_end = -1
    in_on_block = False
    next_block_line = -1
    on_line = -1
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Found root-level 'on:' block (either multiline or single line)
        if (stripped == 'on:' or stripped.startswith('on: ')) and not line.startswith(' '):
            on_line = i
            if stripped == 'on:':
                # Multiline on block
                in_on_block = True
                print(f"Found multiline 'on:' block at line {i+1}")
                continue
            else:
                # Single line on block like "on: [push, pull_request]"
                on_block_end = i
                print(f"Found single-line 'on:' block at line {i+1}")
                # Find next root-level block
                for j in range(i + 1, len(lines)):
                    next_stripped = lines[j].strip()
                    if next_stripped and not lines[j].startswith(' '):
                        next_block_line = j
                        break
                break
            
        # We're in the on block, look for the end
        if in_on_block:
            # If this line has content and is indented, it's part of the on block
            if stripped and line.startswith(' '):
                on_block_end = i
            # If line starts with non-space and isn't empty, we've found the next root-level block
            elif stripped and not line.startswith(' '):
                next_block_line = i
                break
    
    if on_block_end == -1:
        print("Could not find complete 'on:' block structure")
        return
    
    # Check if there's a blank line between on block and next block
    has_blank_line = (on_block_end + 1 < len(lines) and 
                     lines[on_block_end + 1].strip() == '')
    
    print(f"On block ends at line {on_block_end + 1}")
    print(f"Next root-level block starts at line {next_block_line + 1}: '{lines[next_block_line].strip()}'")
    print(f"Blank line between them: {has_blank_line}")
    print()
    
    if has_blank_line:
        print("🟢 RULE B APPLIES: Insert permissions with blank lines above and below")
        print("Format should be:")
        print("on:")
        print("  # on block content")
        print("")
        print("permissions:")
        print("  contents: read")
        print("")
        print("next-block:")
    else:
        print("🟢 RULE A APPLIES: Insert permissions with NO blank lines")
        print("Format should be:")
        print("on:")
        print("  # on block content")
        print("permissions:")
        print("  contents: read")
        print("next-block:")


def verify_root_permissions(file_path):
    """
    Verifies that the root-level permissions block is correctly formatted.
    Must be either 'permissions: read-all' or 'permissions:\\n  contents: read'
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading file: {e}")
        return False
    
    # Find the root-level permissions block
    permissions_line = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Found root-level 'permissions:' block (not indented)
        if stripped.startswith('permissions:') and not line.startswith(' '):
            permissions_line = i
            break
    
    if permissions_line == -1:
        print("❌ ERROR: No root-level 'permissions:' block found")
        return False
    
    perm_line = lines[permissions_line].strip()
    
    # Check for valid formats
    if perm_line == 'permissions: read-all':
        print("✅ VALID: Root-level permissions is 'permissions: read-all'")
        return True
    elif perm_line == 'permissions:':
        # Check if next line is '  contents: read' and there are no additional permissions
        if permissions_line + 1 >= len(lines):
            print(f"❌ ERROR: Found 'permissions:' but no content following it")
            return False
        
        contents_line = lines[permissions_line + 1]
        if (contents_line.strip() == 'contents: read' and 
            contents_line.startswith('  ')):
            
            # Check that there are no additional permissions after contents: read
            next_line_idx = permissions_line + 2
            if (next_line_idx < len(lines) and 
                lines[next_line_idx].strip() != '' and 
                lines[next_line_idx].startswith('  ')):
                print(f"❌ ERROR: Found additional permissions after 'contents: read'")
                print(f"Additional line: '{lines[next_line_idx].strip()}'")
                print("Root-level permissions must contain ONLY 'contents: read'")
                return False
            
            print("✅ VALID: Root-level permissions is 'permissions:\\n  contents: read'")
            return True
        else:
            print(f"❌ ERROR: Found 'permissions:' but next line is not '  contents: read'")
            print(f"Next line: '{contents_line.strip()}'")
            return False
    else:
        print(f"❌ ERROR: Invalid root-level permissions format: '{perm_line}'")
        print("Must be either 'permissions: read-all' or 'permissions:' followed by '  contents: read'")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        analyze_yaml_formatting(file_path)
    else:
        print("Usage: python check_formatting.py <workflow_file.yml>")