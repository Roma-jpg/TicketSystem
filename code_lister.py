import os
import sys


def scan_code_files(root_dir=".", ignore_folders=None, file_extensions=None):
    """
    Recursively scan for specified file types, ignoring specified folders.

    Args:
        root_dir (str): Root directory to start scanning from
        ignore_folders (list): List of folder names to ignore
        file_extensions (list): List of file extensions to scan for (e.g., ['.py', '.yml', '.html'])

    Returns:
        tuple: (list of found file paths, formatted output string)
    """
    if ignore_folders is None:
        ignore_folders = ['addons', '.git', 'node_modules', '__pycache__', '.venv', 'venv']

    if file_extensions is None:
        file_extensions = ['.py', 'html', 'yml']

    root_dir = os.path.abspath(root_dir)

    if not os.path.exists(root_dir):
        return [], f"Error: Directory '{root_dir}' doesn't exist!"

    found_files = []
    ext_display = ', '.join(file_extensions)
    output_parts = [f"Scanning for files with extensions {ext_display} in: {root_dir}"]
    output_parts.append(f"Ignoring folders: {', '.join(ignore_folders)}")
    output_parts.append('-' * 5 + '\n')

    # Convert ignore folders to lowercase for case-insensitive comparison
    ignore_folders_lower = [folder.lower() for folder in ignore_folders]

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Modify dirnames in-place to skip ignored directories
        dirnames[:] = [
            d for d in dirnames
            if d.lower() not in ignore_folders_lower
               and not d.startswith('.')  # Also ignore hidden directories
        ]

        # Filter for specified file extensions
        matched_files = []
        for filename in filenames:
            file_ext_lower = os.path.splitext(filename)[1].lower()
            if file_ext_lower in [ext.lower() for ext in file_extensions]:
                matched_files.append(filename)

        for matched_file in matched_files:
            full_path = os.path.join(dirpath, matched_file)
            rel_path = os.path.relpath(full_path, root_dir)
            found_files.append((rel_path, full_path))

    if not found_files:
        output_parts.append(f"No files with extensions {ext_display} found!")
        return [], '\n'.join(output_parts)

    # Sort files by relative path for better readability
    found_files.sort(key=lambda x: x[0])

    # Build output string
    for i, (rel_path, full_path) in enumerate(found_files):
        # Add separator and file header
        output_parts.append(f"\n[{'=' * 6}]")
        output_parts.append(f"[{rel_path}]")
        output_parts.append(f"[{'=' * 6}]\n")

        try:
            # Try UTF-8 first (most common)
            with open(full_path, 'r', encoding='utf-8') as file:
                content = file.read()
                output_parts.append(content)
        except UnicodeDecodeError:
            try:
                # Try with different encoding if UTF-8 fails
                with open(full_path, 'r', encoding='latin-1') as file:
                    content = file.read()
                    output_parts.append(content)
            except Exception as e:
                output_parts.append(f"Error reading file: {e}")
        except Exception as e:
            output_parts.append(f"Error reading file {rel_path}: {e}")

        # Add separator between files (except after last one)
        if i < len(found_files) - 1:
            output_parts.append(f"\n{'=' * 8}\n")

    output_parts.append(f"\n{'=' * 50}")
    output_parts.append(f"Total files found: {len(found_files)}")

    return found_files, '\n'.join(output_parts)


def copy_to_clipboard(text):
    """Copy text to clipboard using pyperclip."""
    try:
        import pyperclip
        pyperclip.copy(text)
        print("✓ Output copied to clipboard successfully!")
        return True
    except ImportError:
        print("⚠  pyperclip not installed. Installing it now...")
        try:
            import subprocess
            import sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyperclip"])
            import pyperclip
            pyperclip.copy(text)
            print("✓ pyperclip installed and output copied to clipboard!")
            return True
        except Exception as e:
            print(f"✗ Failed to install or use pyperclip: {e}")
            print("You can install it manually with: pip install pyperclip")
            return False
    except Exception as e:
        print(f"✗ Error copying to clipboard: {e}")
        return False


def main():
    """Main function to orchestrate scanning and clipboard operations."""
    # Parse command line arguments
    import argparse

    parser = argparse.ArgumentParser(description='Scan and collect code files (Python, YAML, HTML)')
    parser.add_argument('directory', nargs='?', default='.',
                        help='Directory to scan (default: current directory)')
    parser.add_argument('--extensions', '-e', nargs='+',
                        default=['.py', '.yml', '.yaml', '.html'],
                        help='File extensions to scan for (default: .py .yml .yaml .html)')
    parser.add_argument('--ignore', '-i', nargs='+',
                        default=['addons', '.git', 'node_modules', '__pycache__', '.venv', 'venv'],
                        help='Folders to ignore (default: addons .git node_modules __pycache__ .venv venv)')

    args = parser.parse_args()

    start_dir = args.directory
    file_extensions = args.extensions
    ignore_folders = args.ignore

    print(f"Starting scan in: {os.path.abspath(start_dir)}")
    print(f"Scanning for: {', '.join(file_extensions)}")
    print(f"Ignoring folders: {', '.join(ignore_folders)}")
    print("-" * 5)

    # Scan for files
    found_files, output = scan_code_files(start_dir, ignore_folders, file_extensions)

    if not found_files and "Error:" in output:
        print(output)
        return

    # Print to console
    print(output)

    # Copy to clipboard
    print("\n" + "=" * 50)
    print("Copying to clipboard...")
    if copy_to_clipboard(output):
        # Show a preview of what was copied
        lines = output.split('\n')
        print(f"\n📋 Clipboard preview (first 5 lines):")
        print("-" * 4)
        for line in lines[:5]:
            print(line[:80] + "..." if len(line) > 80 else line)
        print("...")
    else:
        print("\n⚠  Could not copy to clipboard. The output is shown above.")

    # Optional: Save to file as backup
    try:
        backup_file = "code_files_scan.txt"
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"\n💾 Backup saved to: {backup_file}")
    except Exception as e:
        print(f"\n⚠  Could not save backup file: {e}")


if __name__ == "__main__":
    # Check if running in a terminal that supports clipboard
    import platform

    system = platform.system()

    if system == "Linux":
        print("Note: On Linux, you may need to install xclip or xsel for clipboard support")
        print("  sudo apt-get install xclip")
        print("  or")
        print("  sudo apt-get install xsel")
        print("-" * 5)

    main()