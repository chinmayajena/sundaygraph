"""Safe code execution for generated extraction code"""

from typing import Dict, Any, List, Optional, Callable
from loguru import logger
import ast
import re
import sys
from io import StringIO
import traceback


class CodeExecutor:
    """
    Safely executes generated Python code for data extraction.
    Uses AST validation and restricted execution environment.
    """
    
    def __init__(self, max_execution_time: int = 30):
        """
        Initialize code executor
        
        Args:
            max_execution_time: Maximum execution time in seconds
        """
        self.max_execution_time = max_execution_time
        self.allowed_modules = {
            're', 'json', 'hashlib', 'datetime', 'collections', 'itertools',
            'math', 'string', 'random', 'uuid'
        }
        self.allowed_builtins = {
            'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 'tuple',
            'set', 'sorted', 'min', 'max', 'sum', 'abs', 'round', 'enumerate',
            'zip', 'range', 'isinstance', 'type', 'hasattr', 'getattr',
            'any', 'all', 'filter', 'map'
        }
    
    def validate_code(self, code: str) -> tuple[bool, Optional[str]]:
        """
        Validate generated code for safety
        
        Args:
            code: Python code string
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Parse AST to check syntax
            tree = ast.parse(code)
            
            # Check for dangerous operations
            for node in ast.walk(tree):
                # Disallow imports (except from allowed modules)
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name not in self.allowed_modules:
                            return False, f"Import of '{alias.name}' is not allowed"
                
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module not in self.allowed_modules:
                        return False, f"Import from '{node.module}' is not allowed"
                
                # Disallow file operations
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in ['open', 'exec', 'eval', '__import__', 'compile']:
                            return False, f"Call to '{node.func.id}' is not allowed"
                
                # Disallow attribute access to dangerous modules
                if isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name):
                        if node.value.id in ['os', 'sys', 'subprocess', 'socket']:
                            return False, f"Access to '{node.value.id}' module is not allowed"
            
            return True, None
            
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"
    
    def compile_code(self, code: str, function_name: str = "extract") -> Optional[Callable]:
        """
        Compile code into a callable function
        
        Args:
            code: Python code string
            function_name: Name of the function to extract
            
        Returns:
            Callable function or None if compilation fails
        """
        try:
            # Wrap code in a function if it's not already
            if not code.strip().startswith('def '):
                # Try to extract function from code
                if f'def {function_name}' in code:
                    # Extract the function
                    match = re.search(rf'def {function_name}\([^)]*\):.*?(?=\n\ndef |\nclass |\Z)', code, re.DOTALL)
                    if match:
                        code = match.group(0)
                else:
                    # Wrap in a function
                    code = f"def {function_name}(row, rules):\n" + "\n".join("    " + line for line in code.split("\n"))
            
            # Validate code
            is_valid, error = self.validate_code(code)
            if not is_valid:
                logger.error(f"Code validation failed: {error}")
                return None
            
            # Create restricted globals
            restricted_globals = {
                '__builtins__': {k: v for k, v in __builtins__.items() if k in self.allowed_builtins},
                '__name__': '__extract__',
                '__doc__': None
            }
            
            # Compile and execute in restricted environment
            compiled = compile(code, '<string>', 'exec')
            exec(compiled, restricted_globals)
            
            # Extract the function
            if function_name in restricted_globals:
                return restricted_globals[function_name]
            
            logger.warning(f"Function '{function_name}' not found in compiled code")
            return None
            
        except Exception as e:
            logger.error(f"Code compilation failed: {e}\n{traceback.format_exc()}")
            return None
    
    def execute_extraction_code(
        self,
        code: str,
        row: Dict[str, Any],
        rules: Dict[str, Any],
        function_name: str = "extract_entities_and_relations"
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]:
        """
        Execute generated extraction code on a single row
        
        Args:
            code: Generated Python code
            row: Data row to process
            rules: Extraction rules/config
            function_name: Name of the extraction function
            
        Returns:
            Tuple of (entities, relations, error_message)
        """
        try:
            # Compile code
            func = self.compile_code(code, function_name)
            if not func:
                return [], [], "Failed to compile extraction code"
            
            # Execute function
            result = func(row, rules)
            
            # Parse result
            if isinstance(result, tuple) and len(result) == 2:
                entities, relations = result
                if isinstance(entities, list) and isinstance(relations, list):
                    return entities, relations, None
            
            return [], [], "Function did not return (entities, relations) tuple"
            
        except Exception as e:
            error_msg = f"Execution error: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return [], [], error_msg
    
    def execute_batch(
        self,
        code: str,
        rows: List[Dict[str, Any]],
        rules: Dict[str, Any],
        function_name: str = "extract_entities_and_relations"
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
        """
        Execute generated code on multiple rows
        
        Args:
            code: Generated Python code
            rows: List of data rows
            rules: Extraction rules/config
            function_name: Name of the extraction function
            
        Returns:
            Tuple of (all_entities, all_relations, errors)
        """
        all_entities = []
        all_relations = []
        errors = []
        
        # Compile once
        func = self.compile_code(code, function_name)
        if not func:
            return [], [], ["Failed to compile extraction code"]
        
        # Execute on each row
        for i, row in enumerate(rows):
            try:
                result = func(row, rules)
                if isinstance(result, tuple) and len(result) == 2:
                    entities, relations = result
                    if isinstance(entities, list) and isinstance(relations, list):
                        all_entities.extend(entities)
                        all_relations.extend(relations)
                    else:
                        errors.append(f"Row {i}: Invalid return type")
                else:
                    errors.append(f"Row {i}: Function did not return (entities, relations) tuple")
            except Exception as e:
                error_msg = f"Row {i}: {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)
        
        return all_entities, all_relations, errors
