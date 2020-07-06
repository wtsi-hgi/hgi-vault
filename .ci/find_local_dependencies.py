import sys
import os

import ast
import importlib
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

    # modfinder.find_spec is used to find local imports relative to local_root
    loader_details = (importlib.machinery.SourceFileLoader,
        importlib.machinery.SOURCE_SUFFIXES)
    modfinder = importlib.machinery.FileFinder(local_root, loader_details)

    for module in import_list:
        if type(module) == ast.Import:
            for name in module.names:

                # search locally
                spec = modfinder.find_spec(name.name)
                # if not found locally, search in the gobal namespace
                if spec is None:
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
            # search locally
            spec = modfinder.find_spec(module.module)
            # if not found locally, search in the global namespace
            if spec is None:
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
    modules = []
    properties = {}

    for imp in import_list:
        if type(imp) == ast.Import:
            for name in imp.names:
                if name.asname is None:
                    modules.append(name.name)
                else:
                    modules.append(name.asname)

        if type(imp) == ast.ImportFrom:
            for name in imp.names:
                _module = imp.module
                # 'from . import x' makes imp.module become None
                if imp.module is None:
                    _module = '.'

                # If imported under a new name, the new name will be used to
                # scan the syntax tree but we want the (module, class/method)
                # tuple to contain the original module name
                if name.asname is None:
                    properties[name.name] = _module
                else:
                    properties[name.asname] = (_module, name.name)

    # list of (module, class/method) tuples, for testing purposes
    print("Modules: {}\nProperties: {}".format(modules, properties))
    # TODO: remove/don't add duplicate tuples
    use_list = []
    for node in ast.walk(syntax_tree):
        # Documentation for the various nodes can be found here:
        # https://greentreesnakes.readthedocs.io/en/latest/nodes.html
        if type(node) == ast.Name:
            if node.id in properties.keys():
                if type(properties[node.id]) == tuple:
                    # the key is the 'import as' name, which isn't relevant
                    use_list.append(properties[node.id])
                else:
                    # the key is the standard module name
                    use_list.append((properties[node.id], node.id))

        elif type(node) == ast.Attribute:
            # Attributes can be chained (like 'abc.xyz.something()') so we
            # have to compare both 'abc' and 'abc.xyz' to the imports list
            _namespace = []
            _attribute = node.attr

            _node = node.value
            while type(_node) in [ast.Attribute, ast.Call]:
                if type(_node) == ast.Attribute:
                    _namespace = [_node.attr] + _namespace
                    _node = _node.value
                elif type(_node) == ast.Call:
                    _namespace = [_node.func.attr + '()'] + _namespace
                    _node = _node.func.value

            try:
                _namespace = [_node.id] + _namespace
            except AttributeError:
                print(list(ast.iter_child_nodes(_node)))
                print("attribute node ended up as a call: {}.{}"
                    .format(_node.func.value.id, _node.func.attr))

            for i in reversed(range(len(_namespace))):
                to_try = '.'.join(_namespace[:i+1])

                remaining_namespace = '.'.join(_namespace[i+1:])
                if len(remaining_namespace) > 0:
                    full_attribute = '.'.join(_namespace[i+1:]) + '.' + _attribute
                else:
                    full_attribute = _attribute

                if to_try in modules:
                    use_list.append((to_try, full_attribute))
                    break
                elif to_try in properties.keys():
                    if type(properties[to_try]) == tuple:
                        use_list.append(properties[to_try])
                    else:
                        use_list.append((properties[to_try]),
                            "{}.{}".format(to_try, full_attribute))
                    break

    return use_list

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
    use_list = _find_dependency_uses(tree, local_imports)

    return use_list

if __name__ == "__main__":
    path = Path(sys.argv[1])
    module_path = str(path.resolve())
    dependency_list = set(get_local_dependencies(module_path))

    for i in dependency_list:
        print(i)
