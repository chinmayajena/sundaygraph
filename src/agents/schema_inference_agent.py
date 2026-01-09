"""Schema inference agent that uses LLM to generate extraction rules"""

from typing import Dict, Any, List, Optional
from loguru import logger
import json
import ast
import re

from .base_agent import BaseAgent
from ..utils.llm_service import LLMService


class SchemaInferenceAgent(BaseAgent):
    """
    Agent that uses LLM to analyze data structure and generate extraction rules/code.
    This avoids per-row LLM calls by generating reusable extraction logic.
    """
    
    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize schema inference agent
        
        Args:
            llm_service: LLM service for reasoning
            config: Agent configuration
        """
        super().__init__(config)
        self.llm_service = llm_service
        self.sample_size = self.config.get("sample_size", 20)  # Number of rows to analyze
        self.max_sample_chars = self.config.get("max_sample_chars", 10000)  # Max chars in sample
    
    async def infer_extraction_rules(
        self,
        data_sample: List[Dict[str, Any]],
        file_type: str,
        ontology_schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Use LLM to analyze data sample and generate extraction rules
        
        Args:
            data_sample: Sample of data rows (first N rows)
            file_type: Type of file (csv, json, pdf, etc.)
            ontology_schema: Optional ontology schema for mapping
            
        Returns:
            Extraction rules dictionary with:
            - entity_extraction: Rules/code for extracting entities
            - relation_extraction: Rules/code for extracting relations
            - entity_type_mapping: Mapping of data patterns to entity types
            - property_mapping: Mapping of column names to property names
        """
        if not self.llm_service:
            logger.warning("LLM service not available, falling back to rule-based extraction")
            return self._generate_default_rules(data_sample, file_type)
        
        logger.info(f"Inferring extraction rules from {len(data_sample)} sample rows")
        
        # Prepare sample data for LLM (limit size)
        sample_str = self._format_sample_for_llm(data_sample)
        
        # Build prompt for LLM
        system_prompt = """You are an expert data engineer. Your task is to analyze data samples and generate extraction rules that can be executed programmatically without LLM calls.

Your output should be a JSON object with:
1. **entity_extraction**: Rules for extracting entities from each row
   - entity_type: How to determine entity type (pattern matching, column-based, etc.)
   - id_generation: How to generate unique entity IDs
   - property_mapping: How to map data fields to entity properties
   
2. **relation_extraction**: Rules for extracting relations
   - foreign_key_detection: Patterns for detecting foreign keys (e.g., columns ending in "_id")
   - relation_type_mapping: How to determine relation types from column names/patterns
   - source_target_mapping: How to identify source and target entities
   
3. **entity_type_mapping**: Mapping rules from data patterns to ontology entity types
   - column_patterns: Regex patterns or exact matches for column names
   - value_patterns: Patterns in values that indicate entity types
   
4. **property_mapping**: Mapping of source column names to ontology property names
   - exact_matches: Direct column name to property name mappings
   - pattern_matches: Regex patterns for column name matching
   - transformations: Data transformations (e.g., type conversions, formatting)

Generate rules that are:
- Executable without LLM calls
- Handle edge cases (missing values, nulls, etc.)
- Efficient for processing large datasets
- Aligned with the provided ontology schema if available

Format your response as valid JSON only."""
        
        context = f"""File Type: {file_type}
Data Sample (first {len(data_sample)} rows):
{sample_str}"""
        
        if ontology_schema:
            context += f"\n\nOntology Schema:\n{json.dumps(ontology_schema, indent=2)}"
            context += "\n\nGenerate extraction rules that map data to this ontology schema."
        
        prompt = f"""Analyze the following data sample and generate extraction rules:

{context}

Provide extraction rules as a JSON object that can be used to process all rows in the dataset without LLM calls."""
        
        try:
            # Use LLM to generate rules
            response = await self.llm_service.think(
                prompt=prompt,
                system_prompt=system_prompt,
                thinking_mode=False,  # Faster, no need for deep thinking
                task_complexity="medium"
            )
            
            # Parse JSON from response
            rules = self._parse_llm_response(response)
            
            # Validate and enhance rules
            rules = self._validate_and_enhance_rules(rules, data_sample, file_type)
            
            logger.info(f"Generated extraction rules: {len(rules.get('entity_type_mapping', {}))} entity types, {len(rules.get('property_mapping', {}))} property mappings")
            return rules
            
        except Exception as e:
            logger.error(f"Failed to infer extraction rules with LLM: {e}")
            logger.info("Falling back to rule-based extraction")
            return self._generate_default_rules(data_sample, file_type)
    
    def _format_sample_for_llm(self, data_sample: List[Dict[str, Any]]) -> str:
        """Format data sample for LLM consumption"""
        # Limit sample size
        sample = data_sample[:self.sample_size]
        
        # Convert to string representation
        sample_str = json.dumps(sample, indent=2, default=str)
        
        # Truncate if too long
        if len(sample_str) > self.max_sample_chars:
            sample_str = sample_str[:self.max_sample_chars] + "\n... (truncated)"
        
        return sample_str
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response"""
        # Try to extract JSON from response
        # LLM might wrap JSON in markdown code blocks or add explanations
        
        # Remove markdown code blocks if present
        response = re.sub(r'```json\s*', '', response)
        response = re.sub(r'```\s*', '', response)
        response = response.strip()
        
        # Try to find JSON object
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from LLM response")
        
        # Fallback: try parsing entire response
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return {}
    
    def _validate_and_enhance_rules(self, rules: Dict[str, Any], data_sample: List[Dict[str, Any]], file_type: str) -> Dict[str, Any]:
        """Validate and enhance extraction rules with defaults"""
        # Ensure all required keys exist
        default_rules = {
            "entity_extraction": {
                "entity_type": "infer_from_columns",
                "id_generation": "use_first_unique_field",
                "property_mapping": "direct"
            },
            "relation_extraction": {
                "foreign_key_detection": ["_id", "Id", "_ref"],
                "relation_type_mapping": {},
                "source_target_mapping": "foreign_key_based"
            },
            "entity_type_mapping": {},
            "property_mapping": {}
        }
        
        # Merge with defaults
        for key, default_value in default_rules.items():
            if key not in rules:
                rules[key] = default_value
            elif isinstance(default_value, dict):
                rules[key] = {**default_value, **rules[key]}
        
        # Auto-detect entity types from column names if not provided
        if not rules.get("entity_type_mapping") and data_sample:
            rules["entity_type_mapping"] = self._infer_entity_types_from_columns(data_sample[0])
        
        # Auto-detect property mappings from column names
        if not rules.get("property_mapping") and data_sample:
            rules["property_mapping"] = self._infer_property_mappings(data_sample[0])
        
        return rules
    
    def _infer_entity_types_from_columns(self, sample_row: Dict[str, Any]) -> Dict[str, Any]:
        """Infer entity types from column names"""
        entity_types = {}
        
        # Common patterns
        patterns = {
            r'customer|client': 'Customer',
            r'product|item': 'Product',
            r'employee|staff|worker': 'Employee',
            r'project|task': 'Project',
            r'order|transaction|purchase': 'Transaction',
            r'user|account': 'User',
            r'company|organization|org': 'Organization',
            r'location|address|city': 'Location'
        }
        
        for col_name in sample_row.keys():
            col_lower = col_name.lower()
            for pattern, entity_type in patterns.items():
                if re.search(pattern, col_lower):
                    entity_types[col_name] = entity_type
                    break
        
        return entity_types
    
    def _infer_property_mappings(self, sample_row: Dict[str, Any]) -> Dict[str, Any]:
        """Infer property mappings from column names"""
        # For now, return direct mappings (column name -> property name)
        # This can be enhanced with ontology schema matching
        return {col: col for col in sample_row.keys()}
    
    def _generate_default_rules(self, data_sample: List[Dict[str, Any]], file_type: str) -> Dict[str, Any]:
        """Generate default extraction rules without LLM"""
        if not data_sample:
            return {}
        
        sample_row = data_sample[0]
        
        return {
            "entity_extraction": {
                "entity_type": "infer_from_columns",
                "id_generation": "use_first_unique_field",
                "property_mapping": "direct"
            },
            "relation_extraction": {
                "foreign_key_detection": ["_id", "Id", "_ref"],
                "relation_type_mapping": {},
                "source_target_mapping": "foreign_key_based"
            },
            "entity_type_mapping": self._infer_entity_types_from_columns(sample_row),
            "property_mapping": self._infer_property_mappings(sample_row)
        }
    
    async def generate_extraction_code(self, data_sample: List[Dict[str, Any]], file_type: str, ontology_schema: Optional[Dict[str, Any]] = None) -> str:
        """
        Use LLM to generate Python code for extraction (CodeAct approach)
        
        Args:
            data_sample: Sample data rows
            file_type: Type of file being processed
            ontology_schema: Optional ontology schema for mapping
            
        Returns:
            Python code string that can be executed
        """
        if not self.llm_service:
            # Fallback to template-based code generation
            return self._generate_template_code(data_sample, file_type)
        
        logger.info("Generating extraction code using LLM (CodeAct approach)...")
        
        # Prepare sample for LLM
        sample_str = self._format_sample_for_llm(data_sample)
        
        system_prompt = """You are an expert Python programmer. Your task is to write Python code that extracts entities and relations from data rows.

Write a Python function called `extract_entities_and_relations(row: dict, rules: dict)` that:
1. Takes a data row (dictionary) and extraction rules (dictionary) as input
2. Returns a tuple of (entities: list, relations: list)

The function should:
- Extract entities with: type, id, properties
- Extract relations with: type, source_id, target_id, source_type, target_type, properties
- Handle missing values gracefully
- Use the rules dictionary for configuration (entity type mapping, property mapping, etc.)
- Be efficient and handle edge cases

The code should be:
- Self-contained (no external imports except standard library: re, json, hashlib)
- Safe (no file operations, network calls, or dangerous operations)
- Well-structured and readable
- Handle the specific data structure provided

Return ONLY the Python function code, no explanations or markdown."""
        
        context = f"""File Type: {file_type}
Data Sample:
{sample_str}"""
        
        if ontology_schema:
            context += f"\n\nOntology Schema:\n{json.dumps(ontology_schema, indent=2)}"
            context += "\n\nGenerate code that maps data to this ontology schema."
        
        prompt = f"""Write a Python function to extract entities and relations from data rows:

{context}

Generate the complete function code that processes each row and returns (entities, relations)."""
        
        try:
            # Get code from LLM
            code = await self.llm_service.think(
                prompt=prompt,
                system_prompt=system_prompt,
                thinking_mode=False,
                task_complexity="medium"
            )
            
            # Clean up code (remove markdown, extract function)
            code = self._clean_generated_code(code)
            
            # Validate code structure
            if 'def extract_entities_and_relations' not in code:
                logger.warning("Generated code doesn't contain expected function, using template")
                return self._generate_template_code(data_sample, file_type)
            
            logger.info(f"Generated extraction code ({len(code)} characters)")
            return code
            
        except Exception as e:
            logger.error(f"Failed to generate code with LLM: {e}")
            return self._generate_template_code(data_sample, file_type)
    
    def _clean_generated_code(self, code: str) -> str:
        """Clean and extract code from LLM response"""
        # Remove markdown code blocks
        code = re.sub(r'```python\s*', '', code)
        code = re.sub(r'```\s*', '', code)
        code = code.strip()
        
        # Extract function if code contains multiple functions
        if 'def extract_entities_and_relations' in code:
            # Try to extract just the function
            match = re.search(
                r'def extract_entities_and_relations\([^)]*\):.*?(?=\n\ndef |\nclass |\Z)',
                code,
                re.DOTALL
            )
            if match:
                return match.group(0)
        
        return code
    
    def _generate_template_code(self, data_sample: List[Dict[str, Any]], file_type: str) -> str:
        """Generate template-based code as fallback"""
        return """def extract_entities_and_relations(row: dict, rules: dict) -> tuple[list, list]:
    import hashlib
    import re
    
    entities = []
    relations = []
    
    # Determine entity type
    entity_mapping = rules.get("entity_type_mapping", {})
    entity_type = "Entity"
    for col_name, et in entity_mapping.items():
        if col_name in row and row[col_name]:
            entity_type = et
            break
    
    if entity_type == "Entity":
        col_names = " ".join(row.keys()).lower()
        if "customer" in col_names or "client" in col_names:
            entity_type = "Customer"
        elif "product" in col_names or "item" in col_names:
            entity_type = "Product"
        elif "employee" in col_names or "staff" in col_names:
            entity_type = "Employee"
        elif "project" in col_names or "task" in col_names:
            entity_type = "Project"
        elif "order" in col_names or "transaction" in col_names:
            entity_type = "Transaction"
    
    # Generate entity ID
    entity_id = None
    for key in ["id", "name", "title", "email", "customer_id", "product_id", "employee_id", "project_id"]:
        if key in row and row[key]:
            entity_id = f"{entity_type}:{row[key]}"
            break
    
    if not entity_id and row:
        first_key = list(row.keys())[0]
        if first_key not in ["type", "id", "source", "chunk_index", "total_chunks", "metadata"]:
            first_value = str(row[first_key])[:50]
            entity_id = f"{entity_type}:{first_key}_{first_value}"
    
    if not entity_id:
        row_str = str(sorted(row.items()))
        row_hash = hashlib.md5(row_str.encode()).hexdigest()[:8]
        entity_id = f"{entity_type}:{row_hash}"
    
    # Extract properties
    property_mapping = rules.get("property_mapping", {})
    properties = {}
    for col_name, value in row.items():
        if col_name not in ["type", "id", "source", "chunk_index", "total_chunks", "metadata"]:
            prop_name = property_mapping.get(col_name, col_name)
            properties[prop_name] = value
    
    if entity_type and entity_id:
        entities.append({
            "type": entity_type,
            "id": entity_id,
            "properties": properties
        })
        
        # Extract relations (foreign keys)
        relation_rules = rules.get("relation_extraction", {})
        fk_patterns = relation_rules.get("foreign_key_detection", ["_id", "Id", "_ref"])
        
        for col_name, value in row.items():
            if not value:
                continue
            
            is_fk = any(col_name.endswith(p) or p in col_name for p in fk_patterns)
            if is_fk and col_name.lower() != "id":
                target_type = col_name.replace("_id", "").replace("Id", "").replace("_ref", "").strip("_").title()
                if not target_type:
                    target_type = "Entity"
                
                relation_type = "HAS_" + col_name.upper().replace("_", "").replace("ID", "")
                target_id = f"{target_type}:{value}"
                
                relations.append({
                    "type": relation_type,
                    "source_id": entity_id,
                    "target_id": target_id,
                    "source_type": entity_type,
                    "target_type": target_type,
                    "properties": {}
                })
    
    return entities, relations
"""
