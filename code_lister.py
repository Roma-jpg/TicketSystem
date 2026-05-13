import os
import sys
import re
import argparse
import tokenize
import io
import platform
from pathlib import Path


# ----------------------------------------------------------------------
# Minification helpers (unchanged from your original request)
# ----------------------------------------------------------------------

def strip_python_comments_and_docstrings(source: str) -> str:
    """Remove comments and docstrings from Python source using tokenize."""
    result = []
    prev_toktype = tokenize.INDENT
    last_lineno = -1
    last_col = 0

    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for toktype, ttext, (slineno, scol), (elineno, ecol), _ in tokens:
            if slineno > last_lineno:
                last_col = 0
            if toktype == tokenize.COMMENT:
                continue
            if toktype == tokenize.STRING and prev_toktype in (tokenize.INDENT, tokenize.NEWLINE):
                continue
            if scol > last_col:
                result.append(" " * (scol - last_col))
            result.append(ttext)
            prev_toktype = toktype
            last_col = ecol
            last_lineno = elineno
        return "".join(result)
    except Exception:
        lines = source.splitlines(True)
        out = []
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if "#" in line:
                line = line[: line.index("#")].rstrip() + "\n"
            out.append(line)
        return "".join(out)


def strip_html_comments(source: str) -> str:
    """Remove HTML comments <!-- ... -->."""
    return re.sub(r"<!--.*?-->", "", source, flags=re.DOTALL)


def strip_yaml_comments(source: str) -> str:
    """Remove YAML comments (#) line by line."""
    lines = source.splitlines(True)
    out = []
    for line in lines:
        new_line = re.sub(r"(?<!\S)#.*", "", line)
        out.append(new_line)
    return "".join(out)


def strip_comments_by_ext(content: str, ext: str) -> str:
    ext = ext.lower()
    if ext == ".py":
        return strip_python_comments_and_docstrings(content)
    elif ext in (".html", ".htm"):
        return strip_html_comments(content)
    elif ext in (".yml", ".yaml"):
        return strip_yaml_comments(content)
    return content


def minify_indentation(content: str, ext: str) -> str:
    ext = ext.lower()
    if ext in (".py", ".yml", ".yaml"):
        lines = content.splitlines(True)
        indent_counts = []
        for line in lines:
            if line.strip() == "":
                continue
            leading = len(line) - len(line.lstrip(" "))
            if leading > 0:
                indent_counts.append(leading)
        if not indent_counts:
            step = 4
        else:
            from collections import Counter
            most_common = Counter(indent_counts).most_common(1)
            step = most_common[0][0] if most_common else 4

        new_lines = []
        for line in lines:
            if line.strip() == "":
                new_lines.append(line)
                continue
            leading_spaces = len(line) - len(line.lstrip(" "))
            level = leading_spaces // step
            new_lines.append(" " * level + line.lstrip(" "))
        return "".join(new_lines)

    elif ext in (".html", ".htm"):
        lines = content.splitlines()
        new_lines = []
        prev_empty = False
        for line in lines:
            stripped = line.lstrip()
            if stripped == "":
                if not prev_empty:
                    new_lines.append("")
                    prev_empty = True
            else:
                new_lines.append(stripped)
                prev_empty = False
        return "\n".join(new_lines)

    return content


def collapse_blank_lines(content: str, max_consecutive: int = 1) -> str:
    lines = content.splitlines(True)
    out = []
    blank_count = 0
    for line in lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= max_consecutive:
                out.append(line)
        else:
            blank_count = 0
            out.append(line)
    return "".join(out)


# ----------------------------------------------------------------------
# Core scanner (unchanged except parameter names)
# ----------------------------------------------------------------------

def scan_code_files(
    root_dir=".",
    ignore_folders=None,
    file_extensions=None,
    compact_headers=True,
    strip_comments=True,
    minify_indent=True,
    collapse_empty_lines=True,
    exclude_patterns=None,
):
    if ignore_folders is None:
        ignore_folders = ["addons", ".git", "node_modules", "__pycache__", ".venv", "venv"]
    if file_extensions is None:
        file_extensions = [".py", ".html", ".yml", ".yaml"]
    if exclude_patterns is None:
        exclude_patterns = []

    # Normalise extensions: ensure they all start with a dot
    file_extensions = [
        f".{ext.lstrip('.')}" if not ext.startswith(".") else ext
        for ext in file_extensions
    ]

    root_dir = os.path.abspath(root_dir)
    if not os.path.exists(root_dir):
        return [], f"Error: Directory '{root_dir}' doesn't exist!"

    import fnmatch
    exclude_funcs = [lambda p, pat=pat: fnmatch.fnmatch(p, pat) for pat in exclude_patterns]

    found_files = []
    ignore_folders_lower = [f.lower() for f in ignore_folders]

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [
            d for d in dirnames
            if d.lower() not in ignore_folders_lower and not d.startswith(".")
        ]

        matched_files = []
        for filename in filenames:
            file_ext_lower = os.path.splitext(filename)[1].lower()
            if file_ext_lower in [ext.lower() for ext in file_extensions]:
                matched_files.append(filename)

        for matched_file in matched_files:
            full_path = os.path.join(dirpath, matched_file)
            rel_path = os.path.relpath(full_path, root_dir)

            if any(func(rel_path) for func in exclude_funcs):
                continue

            found_files.append((rel_path, full_path))

    if not found_files:
        return [], f"No files found (extensions: {', '.join(file_extensions)})"

    found_files.sort(key=lambda x: x[0])

    output_parts = []
    for i, (rel_path, full_path) in enumerate(found_files):
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(full_path, "r", encoding="latin-1") as f:
                    content = f.read()
            except Exception as e:
                content = f"Error reading file: {e}"
        except Exception as e:
            content = f"Error reading file {rel_path}: {e}"

        ext = os.path.splitext(rel_path)[1]
        if strip_comments:
            content = strip_comments_by_ext(content, ext)
        if minify_indent:
            content = minify_indentation(content, ext)
        if collapse_empty_lines:
            content = collapse_blank_lines(content, max_consecutive=1)

        if compact_headers:
            output_parts.append(f"[{rel_path}]")
        else:
            output_parts.append(f"\n[{'=' * 6}]")
            output_parts.append(f"[{rel_path}]")
            output_parts.append(f"[{'=' * 6}]\n")

        output_parts.append(content)

        if i < len(found_files) - 1:
            output_parts.append("\n")

    output_parts.append(f"\nTotal files: {len(found_files)}")
    return found_files, "\n".join(output_parts)


# ----------------------------------------------------------------------
# Clipboard (unchanged)
# ----------------------------------------------------------------------

def copy_to_clipboard(text):
    try:
        import pyperclip
        pyperclip.copy(text)
        print("✓ Output copied to clipboard!")
        return True
    except ImportError:
        print("⚠  pyperclip not installed. Installing...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyperclip"])
            import pyperclip
            pyperclip.copy(text)
            print("✓ pyperclip installed and output copied!")
            return True
        except Exception as e:
            print(f"✗ Failed: {e}")
            return False
    except Exception as e:
        print(f"✗ Clipboard error: {e}")
        return False


# ----------------------------------------------------------------------
# Main – all optimisations ON by default, with --no-* flags to disable
# ----------------------------------------------------------------------

def main():
    # Sensible default exclusions (tests, migrations, boilerplate)
    DEFAULT_EXCLUDE = ["*tests.py", "*/migrations/*", "admin.py", "apps.py", "__init__.py"]

    parser = argparse.ArgumentParser(
        description="Collect and minify project files for AI prompts. "
                    "All minification and sensible exclusions are ENABLED by default."
    )
    parser.add_argument("directory", nargs="?", default=".", help="Root directory")
    parser.add_argument(
        "--extensions", "-e", nargs="+",
        default=[".py", ".html", ".yml", ".yaml"],
        help="File extensions to include (with leading dot, e.g. .py .html)",
    )
    parser.add_argument(
        "--ignore", "-i", nargs="+",
        default=["addons", ".git", "node_modules", "__pycache__", ".venv", "venv"],
        help="Folder names to skip",
    )

    # Exclusion controls
    parser.add_argument(
        "--no-exclude", action="store_true",
        help="Disable all file exclusion patterns (include tests, migrations, etc.)",
    )
    parser.add_argument(
        "--extra-exclude", nargs="+", action="extend", default=[],
        help="Additional exclusion patterns (appended to defaults)",
    )

    # Optimisation toggles (all on by default; use --no-* to turn off)
    parser.add_argument(
        "--no-compact-headers", action="store_true",
        help="Use decorative file headers instead of compact [path]",
    )
    parser.add_argument(
        "--no-strip-comments", action="store_true",
        help="Keep all comments and docstrings (disable stripping)",
    )
    parser.add_argument(
        "--no-minify-indent", action="store_true",
        help="Keep original indentation (disable minification)",
    )
    parser.add_argument(
        "--keep-empty-lines", action="store_true",
        help="Preserve multiple consecutive blank lines (disable collapsing)",
    )

    parser.add_argument(
        "--no-clipboard", action="store_true",
        help="Do not copy output to clipboard",
    )

    args = parser.parse_args()

    # Build final exclusion list
    if args.no_exclude:
        exclude_patterns = []
    else:
        exclude_patterns = DEFAULT_EXCLUDE + args.extra_exclude

    # Determine optimisation flags
    compact_headers = not args.no_compact_headers
    strip_comments = not args.no_strip_comments
    minify_indent = not args.no_minify_indent
    collapse_empty_lines = not args.keep_empty_lines   # collapse unless --keep-empty-lines is given

    print(f"Scanning: {os.path.abspath(args.directory)}")
    print(f"Extensions: {', '.join(args.extensions)}")
    print(f"Ignoring folders: {', '.join(args.ignore)}")
    print(f"Excluding patterns: {exclude_patterns if exclude_patterns else '(none)'}")
    print(f"Minification: {'ON' if strip_comments else 'OFF'} (comments), "
          f"{'ON' if minify_indent else 'OFF'} (indent), "
          f"{'ON' if collapse_empty_lines else 'OFF'} (empty lines)")
    print(f"Headers: {'compact' if compact_headers else 'decorative'}")
    print("-" * 40)

    found_files, output = scan_code_files(
        root_dir=args.directory,
        ignore_folders=args.ignore,
        file_extensions=args.extensions,
        compact_headers=compact_headers,
        strip_comments=strip_comments,
        minify_indent=minify_indent,
        collapse_empty_lines=collapse_empty_lines,
        exclude_patterns=exclude_patterns,
    )

    if not found_files and "Error:" in output:
        print(output)
        return

    print(output)

    if not args.no_clipboard:
        print("\n" + "=" * 40)
        if copy_to_clipboard(output):
            lines = output.split("\n")
            print("📋 Clipboard preview (first 3 lines):")
            for line in lines[:3]:
                print(line[:100])

    try:
        backup_file = "code_files_scan.txt"
        with open(backup_file, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"\n💾 Backup saved to: {backup_file}")
    except Exception as e:
        print(f"\n⚠  Could not save backup: {e}")


if __name__ == "__main__":
    system = platform.system()
    if system == "Linux":
        print("Note: Linux clipboard may need xclip/xsel (see --help)")
        print("-" * 40)
    main()