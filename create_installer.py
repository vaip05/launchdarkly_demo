#!/usr/bin/env python3
"""
create_installer.py - Generate installation script from existing project
Usage:
    python create_installer.py                    # Use current directory
    python create_installer.py my_project_name    # Custom output name
    python create_installer.py /path/to/project   # Scan different folder
"""

import os
import sys
import base64
import json
import platform
from pathlib import Path

# Directories and files to ignore
IGNORE_PATTERNS = {
    '__pycache__',
    '.git',
    '.gitignore',
    'venv',
    'env',
    '.env',
    '*.pyc',
    '*.pyo',
    '*.db',
    'flask_session',
    '.DS_Store',
    'node_modules',
    'create_installer.py',
    'install.py',
    'install_',
}

# Files to encode as binary
BINARY_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', '.woff', '.woff2', '.ttf'}


def should_ignore(path_str):
    """Check if path should be ignored"""
    for pattern in IGNORE_PATTERNS:
        if pattern.startswith('*'):
            if path_str.endswith(pattern[1:]):
                return True
        elif pattern in path_str.split(os.sep) or path_str.endswith(pattern):
            return True
    return False


def get_file_content(filepath):
    """Get file content (text or binary)"""
    ext = Path(filepath).suffix.lower()
    
    try:
        if ext in BINARY_EXTENSIONS:
            with open(filepath, 'rb') as f:
                content = base64.b64encode(f.read()).decode('utf-8')
            return content, True
        else:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return content, False
    except Exception as e:
        print(f"  Warning: Could not read {filepath}: {e}")
        return "", False


def scan_project(root_dir):
    """Scan project and collect all files"""
    project_structure = {
        'directories': [],
        'files': {}
    }
    
    root_path = Path(root_dir).resolve()
    
    if not root_path.exists():
        print(f"Error: Directory not found: {root_path}")
        sys.exit(1)
    
    print(f"Scanning: {root_path}")
    print("")
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        current_path = Path(dirpath).resolve()
        
        # Filter out ignored directories
        dirnames[:] = [d for d in dirnames if not should_ignore(d)]
        
        # Calculate relative path
        try:
            rel_dir = current_path.relative_to(root_path)
            rel_dir_str = str(rel_dir)
        except ValueError:
            continue
        
        # Add directory (skip root)
        if rel_dir_str != '.' and rel_dir_str:
            project_structure['directories'].append(rel_dir_str)
        
        # Process files
        for filename in filenames:
            if should_ignore(filename):
                continue
            
            filepath = os.path.join(dirpath, filename)
            
            # Get relative file path
            try:
                rel_file = str(Path(filepath).resolve().relative_to(root_path))
            except ValueError:
                continue
            
            if should_ignore(rel_file):
                continue
            
            content, is_binary = get_file_content(filepath)
            
            if content or not is_binary:
                project_structure['files'][rel_file] = {
                    'content': content,
                    'binary': is_binary
                }
                file_type = "(binary)" if is_binary else ""
                print(f"  Added: {rel_file} {file_type}")
    
    return project_structure


def generate_installer(project_structure, project_name, output_file):
    """Generate installation script"""
    
    # Convert to JSON string
    data_json = json.dumps(project_structure)
    
    installer_lines = []
    
    installer_lines.append('#!/usr/bin/env python3')
    installer_lines.append('"""')
    installer_lines.append(f'install.py - Installation script for {project_name}')
    installer_lines.append('Auto-generated installer - Run with: python install.py')
    installer_lines.append('"""')
    installer_lines.append('')
    installer_lines.append('import os')
    installer_lines.append('import sys')
    installer_lines.append('import subprocess')
    installer_lines.append('import platform')
    installer_lines.append('import base64')
    installer_lines.append('import json')
    installer_lines.append('')
    installer_lines.append(f'PROJECT_NAME = "{project_name}"')
    installer_lines.append('')
    installer_lines.append('# Embedded project data')
    installer_lines.append(f'PROJECT_DATA = json.loads({repr(data_json)})')
    installer_lines.append('')
    installer_lines.append('')
    installer_lines.append('def print_banner():')
    installer_lines.append('    print("")')
    installer_lines.append('    print("=" * 60)')
    installer_lines.append('    print(f"  {PROJECT_NAME.upper()} - INSTALLER")')
    installer_lines.append('    print("=" * 60)')
    installer_lines.append('    print("")')
    installer_lines.append('')
    installer_lines.append('')
    installer_lines.append('def check_python():')
    installer_lines.append('    print("Checking Python version...")')
    installer_lines.append('    v = sys.version_info')
    installer_lines.append('    if v.major < 3 or (v.major == 3 and v.minor < 7):')
    installer_lines.append('        print(f"Error: Python 3.7+ required. You have {v.major}.{v.minor}")')
    installer_lines.append('        sys.exit(1)')
    installer_lines.append('    print(f"  OK: Python {v.major}.{v.minor}.{v.micro}")')
    installer_lines.append('')
    installer_lines.append('')
    installer_lines.append('def create_directories():')
    installer_lines.append('    print("")')
    installer_lines.append('    print("Creating directories...")')
    installer_lines.append('    os.makedirs(PROJECT_NAME, exist_ok=True)')
    installer_lines.append('    print(f"  Created: {PROJECT_NAME}/")')
    installer_lines.append('    ')
    installer_lines.append('    for directory in sorted(PROJECT_DATA["directories"]):')
    installer_lines.append('        dir_path = os.path.join(PROJECT_NAME, directory)')
    installer_lines.append('        os.makedirs(dir_path, exist_ok=True)')
    installer_lines.append('        print(f"  Created: {dir_path}/")')
    installer_lines.append('')
    installer_lines.append('')
    installer_lines.append('def create_files():')
    installer_lines.append('    print("")')
    installer_lines.append('    print("Creating files...")')
    installer_lines.append('    ')
    installer_lines.append('    for filepath, file_info in PROJECT_DATA["files"].items():')
    installer_lines.append('        full_path = os.path.join(PROJECT_NAME, filepath)')
    installer_lines.append('        ')
    installer_lines.append('        # Ensure parent directory exists')
    installer_lines.append('        parent_dir = os.path.dirname(full_path)')
    installer_lines.append('        if parent_dir:')
    installer_lines.append('            os.makedirs(parent_dir, exist_ok=True)')
    installer_lines.append('        ')
    installer_lines.append('        try:')
    installer_lines.append('            if file_info["binary"]:')
    installer_lines.append('                content = base64.b64decode(file_info["content"])')
    installer_lines.append('                with open(full_path, "wb") as f:')
    installer_lines.append('                    f.write(content)')
    installer_lines.append('            else:')
    installer_lines.append('                with open(full_path, "w", encoding="utf-8") as f:')
    installer_lines.append('                    f.write(file_info["content"])')
    installer_lines.append('            print(f"  Created: {filepath}")')
    installer_lines.append('        except Exception as e:')
    installer_lines.append('            print(f"  Error creating {filepath}: {e}")')
    installer_lines.append('')
    installer_lines.append('')
    installer_lines.append('def create_venv():')
    installer_lines.append('    print("")')
    installer_lines.append('    print("Creating virtual environment...")')
    installer_lines.append('    venv_path = os.path.join(PROJECT_NAME, "venv")')
    installer_lines.append('    ')
    installer_lines.append('    try:')
    installer_lines.append('        subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)')
    installer_lines.append('        print(f"  Created: venv/")')
    installer_lines.append('        ')
    installer_lines.append('        if platform.system() == "Windows":')
    installer_lines.append('            pip_path = os.path.join(venv_path, "Scripts", "pip")')
    installer_lines.append('        else:')
    installer_lines.append('            pip_path = os.path.join(venv_path, "bin", "pip")')
    installer_lines.append('        ')
    installer_lines.append('        return pip_path')
    installer_lines.append('    except Exception as e:')
    installer_lines.append('        print(f"  Warning: Could not create venv: {e}")')
    installer_lines.append('        return None')
    installer_lines.append('')
    installer_lines.append('')
    installer_lines.append('def install_deps(pip_path):')
    installer_lines.append('    req_file = os.path.join(PROJECT_NAME, "requirements.txt")')
    installer_lines.append('    ')
    installer_lines.append('    if not os.path.exists(req_file):')
    installer_lines.append('        print("  No requirements.txt found")')
    installer_lines.append('        return')
    installer_lines.append('    ')
    installer_lines.append('    if not pip_path:')
    installer_lines.append('        print("  Skipping dependencies (no venv)")')
    installer_lines.append('        return')
    installer_lines.append('    ')
    installer_lines.append('    print("")')
    installer_lines.append('    print("Installing dependencies...")')
    installer_lines.append('    print("  This may take a minute...")')
    installer_lines.append('    ')
    installer_lines.append('    try:')
    installer_lines.append('        result = subprocess.run(')
    installer_lines.append('            [pip_path, "install", "-r", req_file],')
    installer_lines.append('            capture_output=True,')
    installer_lines.append('            text=True')
    installer_lines.append('        )')
    installer_lines.append('        if result.returncode == 0:')
    installer_lines.append('            print("  Dependencies installed!")')
    installer_lines.append('        else:')
    installer_lines.append('            print(f"  Warning: {result.stderr[:200]}")')
    installer_lines.append('    except Exception as e:')
    installer_lines.append('        print(f"  Error: {e}")')
    installer_lines.append('        print("  Run manually: pip install -r requirements.txt")')
    installer_lines.append('')
    installer_lines.append('')
    installer_lines.append('def create_env_file():')
    installer_lines.append('    env_example = os.path.join(PROJECT_NAME, ".env.example")')
    installer_lines.append('    env_file = os.path.join(PROJECT_NAME, ".env")')
    installer_lines.append('    ')
    installer_lines.append('    if os.path.exists(env_example) and not os.path.exists(env_file):')
    installer_lines.append('        print("")')
    installer_lines.append('        print("Creating .env file...")')
    installer_lines.append('        try:')
    installer_lines.append('            with open(env_example, "r") as f:')
    installer_lines.append('                content = f.read()')
    installer_lines.append('            with open(env_file, "w") as f:')
    installer_lines.append('                f.write(content)')
    installer_lines.append('            print("  Created: .env")')
    installer_lines.append('            print("")')
    installer_lines.append('            print("  *** IMPORTANT: Update .env with your settings! ***")')
    installer_lines.append('        except Exception as e:')
    installer_lines.append('            print(f"  Error: {e}")')
    installer_lines.append('')
    installer_lines.append('')
    installer_lines.append('def print_done():')
    installer_lines.append('    abs_path = os.path.abspath(PROJECT_NAME)')
    installer_lines.append('    ')
    installer_lines.append('    print("")')
    installer_lines.append('    print("=" * 60)')
    installer_lines.append('    print("  INSTALLATION COMPLETE!")')
    installer_lines.append('    print("=" * 60)')
    installer_lines.append('    print("")')
    installer_lines.append('    print(f"  Project: {abs_path}")')
    installer_lines.append('    print("")')
    installer_lines.append('    print("  Next steps:")')
    installer_lines.append('    print("")')
    installer_lines.append('    print(f"    1. cd {PROJECT_NAME}")')
    installer_lines.append('    print("")')
    installer_lines.append('    print("    2. Activate virtual environment:")')
    installer_lines.append('    if platform.system() == "Windows":')
    installer_lines.append('        print("       venv\\\\Scripts\\\\activate")')
    installer_lines.append('    else:')
    installer_lines.append('        print("       source venv/bin/activate")')
    installer_lines.append('    print("")')
    installer_lines.append('    print("    3. Configure your settings:")')
    installer_lines.append('    print("       Edit .env file")')
    installer_lines.append('    print("")')
    installer_lines.append('    print("    4. Run the application:")')
    installer_lines.append('    print("       python app.py")')
    installer_lines.append('    print("")')
    installer_lines.append('    print("    5. Open in browser:")')
    installer_lines.append('    print("       http://localhost:5000")')
    installer_lines.append('    print("")')
    installer_lines.append('    print("=" * 60)')
    installer_lines.append('    print("")')
    installer_lines.append('')
    installer_lines.append('')
    installer_lines.append('def main():')
    installer_lines.append('    print_banner()')
    installer_lines.append('    check_python()')
    installer_lines.append('    create_directories()')
    installer_lines.append('    create_files()')
    installer_lines.append('    pip_path = create_venv()')
    installer_lines.append('    install_deps(pip_path)')
    installer_lines.append('    create_env_file()')
    installer_lines.append('    print_done()')
    installer_lines.append('')
    installer_lines.append('')
    installer_lines.append('if __name__ == "__main__":')
    installer_lines.append('    try:')
    installer_lines.append('        main()')
    installer_lines.append('    except KeyboardInterrupt:')
    installer_lines.append('        print("\\n\\nInstallation cancelled by user")')
    installer_lines.append('        sys.exit(1)')
    installer_lines.append('    except Exception as e:')
    installer_lines.append('        print(f"\\n\\nInstallation error: {e}")')
    installer_lines.append('        sys.exit(1)')
    
    # Write installer
    installer_code = '\n'.join(installer_lines)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(installer_code)
    
    # Make executable on Unix
    if platform.system() != 'Windows':
        os.chmod(output_file, 0o755)
    
    return output_file


def main():
    """Main function"""
    
    # Parse arguments
    source_dir = '.'
    project_name = None
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        # Check if it's a path or just a name
        if os.path.isdir(arg):
            source_dir = arg
            project_name = Path(arg).resolve().name
        else:
            project_name = arg
    
    # Default project name from current directory
    if project_name is None:
        project_name = Path(source_dir).resolve().name
    
    # Clean project name (remove spaces and special chars)
    project_name = project_name.replace(' ', '_').replace('-', '_')
    
    print("")
    print("=" * 60)
    print("  CREATE INSTALLER")
    print("=" * 60)
    print("")
    print(f"  Source directory: {Path(source_dir).resolve()}")
    print(f"  Project name: {project_name}")
    print("")
    print("-" * 60)
    print("")
    
    # Scan project
    project_structure = scan_project(source_dir)
    
    # Count items
    num_dirs = len(project_structure['directories'])
    num_files = len(project_structure['files'])
    
    print("")
    print(f"Found: {num_dirs} directories, {num_files} files")
    
    if num_files == 0:
        print("")
        print("Error: No files found! Check the source directory.")
        sys.exit(1)
    
    # Generate installer
    output_file = f"install_{project_name}.py"
    generate_installer(project_structure, project_name, output_file)
    
    # Get file size
    file_size = os.path.getsize(output_file) / 1024
    
    print("")
    print("=" * 60)
    print("  SUCCESS!")
    print("=" * 60)
    print("")
    print(f"  Installer: {output_file}")
    print(f"  Size: {file_size:.1f} KB")
    print("")
    print("  Usage:")
    print(f"    python {output_file}")
    print("")
    print("=" * 60)
    print("")


if __name__ == "__main__":
    main()
