"""
Fixed extraction script that properly handles Windows path issues.
"""
import tarfile
import os
import sys

def sanitize_windows_path(path):
    """Sanitize path for Windows."""
    # Replace invalid characters
    invalid = '<>:"|?*'
    for char in invalid:
        path = path.replace(char, '_')
    # Remove leading ./
    if path.startswith('./'):
        path = path[2:]
    elif path.startswith('.\\'):
        path = path[2:]
    return path

def extract_tar(archive_path, extract_to):
    """Extract tar.gz file with Windows path sanitization."""
    print(f"Extracting {archive_path} to {extract_to}...")
    
    os.makedirs(extract_to, exist_ok=True)
    
    with tarfile.open(archive_path, 'r:gz') as tar:
        members = tar.getmembers()
        print(f"Found {len(members)} files to extract")
        
        extracted_count = 0
        for member in members:
            original_name = member.name
            sanitized_name = sanitize_windows_path(original_name)
            member.name = sanitized_name
            
            try:
                tar.extract(member, extract_to)
                extracted_count += 1
                if extracted_count % 100 == 0:
                    print(f"  Extracted {extracted_count} files...")
            except Exception as e:
                print(f"  Warning: Could not extract {original_name}: {e}")
        
        print(f"\n[OK] Extracted {extracted_count} files to {extract_to}")
        
        # Find toc.dat
        import pathlib
        toc_files = list(pathlib.Path(extract_to).rglob("toc.dat"))
        if toc_files:
            print(f"\n[OK] Found database directory: {toc_files[0].parent}")
            return str(toc_files[0].parent)
        else:
            print("\n[WARNING] No toc.dat found. Listing directories:")
            dirs = [d for d in pathlib.Path(extract_to).rglob("*") if d.is_dir()]
            for d in dirs[:10]:
                print(f"  - {d}")
            return None

if __name__ == '__main__':
    archive = '2025-11-20T14_32Z.dir.tar.gz'
    extract_dir = 'database_export'
    
    # Remove old extraction
    if os.path.exists(extract_dir):
        import shutil
        shutil.rmtree(extract_dir)
    
    result = extract_tar(archive, extract_dir)
    if result:
        print(f"\nDatabase directory: {result}")
        print("\nYou can now run: .\RUN_IMPORT.ps1")

