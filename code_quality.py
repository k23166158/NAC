import ast
import os
import sys
import subprocess

SOURCE_DIRS = ['tickets', 'resolveme']
MAX_LINES_SOURCE = 15
MAX_NESTING_SOURCE = 1
MAX_LINES_TEST = 25
MAX_NESTING_TEST = 2
MAX_FILE_LINE_LENGTH = 400

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

def read_file(filepath):
    """Internal helper to read file inside a with block."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        return f.readlines()

def get_file_content(filepath):
    """Safely retrieve file content or return None on error."""
    try:
        return read_file(filepath)
    except Exception:
        return None

def find_width_errors(filepath, lines):
    """Generate errors for lines exceeding width using list comprehension."""
    return [
        f"Width Error: {filepath}:{i} exceeds {MAX_FILE_LINE_LENGTH} chars."
        for i, line in enumerate(lines, 1)
        if len(line) > MAX_FILE_LINE_LENGTH
    ]

def check_file_width(filepath):
    """Orchestrate width check without nesting."""
    lines = get_file_content(filepath)
    if lines is None:
        return [f"Read Error: Could not check width for {filepath}"]
    return find_width_errors(filepath, lines)

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

def analyze_python_content(filepath, is_test):
    """Parse and visit Python content to find logical errors."""
    tree, error = get_ast_tree(filepath)
    if error:
        return [f"Syntax Error in {filepath}: {error}"]
        
    auditor = QualityAuditor(filepath, is_test)
    auditor.visit(tree)
    return auditor.errors

def process_file(filepath, root):
    """Dispatch file to appropriate checkers based on extension."""
    errors = check_file_width(filepath)
    
    if filepath.endswith('.py'):
        is_test = 'test' in filepath or 'tests' in root
        errors.extend(analyze_python_content(filepath, is_test))
        
    return errors

def should_skip_directory(root):
    """Determine if a directory should be skipped."""
    skip_markers = ['migrations', '/.', '__pycache__', 'venv', '.git']
    return any(marker in root for marker in skip_markers)

def scan_directory(root, files):
    """Process all files in a single directory."""
    errors = []
    if should_skip_directory(root):
        return errors

    for file in files:
        full_path = os.path.join(root, file)
        errors.extend(process_file(full_path, root))
        
    return errors

def check_coverage():
    """Verify that test coverage is 100% using subprocess.run."""
    cmd = [sys.executable, '-m', 'coverage', 'report', '--fail-under=100']
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    
    if result.returncode != 0:
        return ["Coverage Error: Test coverage is below 100%."]
    return []

def print_errors(errors):
    """Print all reported errors."""
    print("Code Quality Audit Failed:")
    for err in errors:
        print(f" - {err}")

def walk_and_scan(start_dir):
    """Recursively scan a directory tree."""
    errors = []
    if not os.path.exists(start_dir):
        return errors

    for root, _, files in os.walk(start_dir):
        errors.extend(scan_directory(root, files))
    return errors

def run_audit():
    """Main execution entry point."""
    targets = ['resolveme', 'static', 'tickets']
    all_errors = []

    for target in targets:
        all_errors.extend(walk_and_scan(target))

    all_errors.extend(check_coverage())

    if all_errors:
        print_errors(all_errors)
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    run_audit()