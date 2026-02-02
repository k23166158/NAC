import ast
import os
import re
import sys
from pathlib import Path

SOURCE_DIRS = ['tickets', 'resolveme', 'static']
TARGET_EXTENSIONS = {'.py', '.html', '.css', '.js'}
MAX_LINES_SOURCE = 15
MAX_NESTING_SOURCE = 1
MAX_LINES_TEST = 25
MAX_NESTING_TEST = 2
MAX_FILE_LINE_LENGTH = 400
STYLE_TAG_REGEX = re.compile(r'<\s*style\b', re.IGNORECASE)
STYLE_ATTR_REGEX = re.compile(r'\bstyle\s*=', re.IGNORECASE)

class QualityAuditor(ast.NodeVisitor):
    """
    Visitor to check code quality standards including length,
    naming conventions, and documentation presence.
    """

    def __init__(self, filename, is_test_file=False):
        """Initialize the auditor with file context."""
        self.filename = filename
        self.is_test_file = is_test_file
        self.errors = []

    def visit_FunctionDef(self, node):
        """Run checks on function definitions."""
        self.check_docstring(node, "Function")
        self.check_length(node)
        self.check_nesting_limit(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """Run checks on class definitions."""
        self.check_docstring(node, "Class")
        self.generic_visit(node)

    def check_docstring(self, node, node_type):
        """Ensure the node has a docstring."""
        if not ast.get_docstring(node):
            self.errors.append(
                f"Docstring Missing: {node_type} '{node.name}' "
                f"in {self.filename}:{node.lineno} has no documentation."
            )

    def check_length(self, node):
        """Ensure function length is within limits."""
        length = node.end_lineno - node.lineno
        limit = MAX_LINES_TEST if self.is_test_file else MAX_LINES_SOURCE
        if length > limit:
            self.errors.append(
                f"Length Error: Function '{node.name}' in {self.filename}:{node.lineno} "
                f"is too long ({length} lines). Max allowed: {limit}."
            )

    def check_nesting_limit(self, node):
        """Ensure function nesting depth is within limits."""
        limit = MAX_NESTING_TEST if self.is_test_file else MAX_NESTING_SOURCE
        depth = compute_max_nesting(node)
        if depth > limit:
            self.errors.append(
                f"Nesting Error: Function '{node.name}' in {self.filename}:{node.lineno} "
                f"has nesting level {depth}. Max allowed: {limit}."
            )

def run_check():
    """Main entry point to run code quality checks."""
    files = []
    for folder in SOURCE_DIRS:
        files += get_directory_files(folder)

    errors = []
    for file in files:
        errors += handle_file(file)

    if errors:
        print_errors(errors)
        sys.exit(1)
    
    print("Code Quality Passed.")
    sys.exit(0)

def get_directory_files(directory):
    """Retrieve all nested targeted files from a directory."""
    path_obj = Path(directory)
    
    files = [
        str(file.resolve()) 
        for file in path_obj.rglob('*') 
        if file.is_file() and file.suffix in TARGET_EXTENSIONS
    ]
    return files

def handle_file(file):
    """Dispatch file to appropriate handler based on extension."""
    extension = os.path.splitext(file)[-1]
    errors = []
    if extension == '.py':
        errors = handle_python_file(file)
    elif extension == '.html':
        errors = handle_html_file(file)
    elif extension == '.css':
        errors = handle_css_file(file)
    elif extension == '.js':
        errors = handle_js_file(file)
    return errors

def handle_python_file(filepath):
    """Parse and visit Python content to find logical errors."""
    is_migration = 'migration' in filepath
    if is_migration:
        return []

    is_test = 'test' in filepath
    tree, error = get_ast_tree(filepath)
    if error:
        return [f"Syntax Error in {filepath}: {error}"]
        
    auditor = QualityAuditor(filepath, is_test)
    auditor.visit(tree)
    return auditor.errors

def handle_html_file(file):
    """Check HTML files for inline styles and scripts."""
    errors = []
    lines = get_file_content(file)
    if lines is None:
        return errors
    
    if len(lines) >= MAX_FILE_LINE_LENGTH:
        errors += [f"Width Error: {file} exceeds {MAX_FILE_LINE_LENGTH} lines."]
    
    content = ''.join(lines)
    if STYLE_TAG_REGEX.search(content) or STYLE_ATTR_REGEX.search(content):
        errors += [f"HTML Error: Inline <style> tag or style attribute found in {file}. Use external CSS only."]
    
    return errors

def handle_css_file(file):
    """Check CSS files for line length."""
    lines = get_file_content(file)
    if len(lines) >= MAX_FILE_LINE_LENGTH:
        return [f"Width Error: {file} exceeds {MAX_FILE_LINE_LENGTH} lines."]
    return []

def handle_js_file(file):
    """Check JS files for line length."""
    lines = get_file_content(file)
    if len(lines) >= MAX_FILE_LINE_LENGTH:
        return [f"Width Error: {file} exceeds {MAX_FILE_LINE_LENGTH} lines."]
    return []

def parse_ast(filepath):
    """Internal helper to parse AST inside a with block."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return ast.parse(f.read())

def get_ast_tree(filepath):
    """Safely get AST tree or return error message."""
    try:
        return parse_ast(filepath), None
    except Exception as e:
        return None, str(e)
    
def get_child_depth(child, current, nesting_nodes):
    """Helper to calculate depth for a single child node."""
    next_depth = current + 1 if isinstance(child, nesting_nodes) else current
    return compute_max_nesting(child, next_depth)

def compute_max_nesting(node, current_depth=0):
    """
    Recursively find maximum nesting of control structures.
    Uses generator to avoid loop nesting.
    """
    nesting_nodes = (ast.If, ast.For, ast.While, ast.With, ast.Try)
    
    child_depths = (
        get_child_depth(child, current_depth, nesting_nodes)
        for child in ast.iter_child_nodes(node)
        if not isinstance(child, ast.FunctionDef)
    )
    return max(child_depths, default=current_depth)

def print_errors(errors):
    """Print all reported errors."""
    print("Code Quality Failed:")
    for err in errors:
        print(f" - {err}")

def get_file_content(filepath):
    """Safely retrieve file content or return None on error."""
    try:
        return read_file(filepath)
    except Exception:
        return None

def read_file(filepath):
    """Internal helper to read file inside a with block."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        return f.readlines()

if __name__ == "__main__":
    run_check()