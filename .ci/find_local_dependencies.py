import sys
import os

import ast
from importlib.util import find_spec
from pathlib import Path

# Use like: python3 find_local_dependencies.py [file]
# Note: The script will crash if the [file] imports a library that isn't
# accessible to it (ie, use the same venv as [file])

def _remove_non_local_dependencies(local_root, import_list):
    """Check import_list against the contents of the local_root path to see
    which modules are local. Return a list only containing local imports."""

    # Assume that relative imports are always local (ast.Import/ImportFrom
    # objects with relative imports have a 'level' attribute)
    local_imports = [module for module in import_list if
        hasattr(module, 'level') and module.level > 0]

    import_list = [module for module in import_list if module not in local_imports]

    script_paths = []
    for _path, _subdirs, _files in os.walk(local_root):
        for _file in _files:
            if _file[-3:] == '.py':
                script_paths.append("{}/{}".format(_path, _file))

    for module in import_list:
        if type(module) == ast.Import:
            for name in module.names:

                spec = find_spec(name.name)
                if spec is None:
                    print("Couldn't find anything for import {}"
                        .format(name.name), file=sys.stderr)
                    continue

                # Checks module path against local root
                if spec.origin.startswith(local_root):
                    local_imports.append(module)

        elif type(module) == ast.ImportFrom:
            # Only interested in the module being imported from
            spec = find_spec(module.module)
            if spec is None:
                print("Couldn't find anything for import {}"
                    .format(module.module), file=sys.stderr)
                continue

            if spec.origin.startswith(local_root):
                local_imports.append(module)

    return local_imports

def _find_dependency_uses(syntax_tree, import_list):
    """Scans the syntax tree for uses of methods and classes from each module
    in the import list."""

    # keywords to scan the tree for
    modules = {}
    properties = {} # TODO: name this something more useful probably

    for imp in import_list:
        if type(imp) == ast.Import:
            for name in imp.names:
                if name.asname is None:
                    modules[name.name] = imp
                else:
                    modules[name.asname] = imp
        if type(imp) == ast.ImportFrom:
            for name in imp.names:
                _module = imp.module
                if imp.module is None:
                    _module = '.'
                if imp.module not in properties.keys():
                    properties[imp.module] = []
                properties[_module].append(name.name)
    # TODO


def get_local_dependencies(module_path):
    """Return a list of the local dependencies of a module."""
    # Assumes the local scope is the parent of the file's directory
    local_root = Path(os.path.realpath(__file__)).parents[1]

    # Assumes that the file is valid Python code
    module_code = ''
    for line in open(module_path, 'r'):
        module_code += line + '\n'

    import_list = []
    tree = ast.parse(module_code)

    for node in ast.walk(tree):
        if type(node) in (ast.Import, ast.ImportFrom):
            import_list.append(node)

    local_imports = _remove_non_local_dependencies(str(local_root), import_list)

    return local_imports

if __name__ == "__main__":
    path = Path(sys.argv[1])
    module_path = str(path.resolve())
    dependency_list = get_local_dependencies(module_path)

    for dep in dependency_list:
        if type(dep) == ast.Import:
            for name in dep.names:
                print('{}'.format(name.name))

        elif type(dep) == ast.ImportFrom:
            if dep.module is None:
                print('.')
            print('{}'.format(dep.module))
