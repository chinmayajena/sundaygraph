"""LLM service for thinking and reasoning"""

from typing import Dict, Any, List, Optional
from loguru import logger
import json

from .llm_cost_optimizer import LLMCostOptimizer


class LLMService:
    """Service for LLM-based thinking and reasoning"""
    
    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        enable_cache: bool = True,
        cache_ttl: int = 3600,
        cost_optimizer: Optional[LLMCostOptimizer] = None
    ):
        """
        Initialize LLM service
        
        Args:
            provider: LLM provider ("openai", "anthropic", "local")
            model: Model name
            temperature: Temperature for generation
            max_tokens: Maximum tokens
            enable_cache: Enable response caching
            cache_ttl: Cache time-to-live in seconds
            cost_optimizer: Optional cost optimizer instance
        """
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None
        self.cost_optimizer = cost_optimizer or LLMCostOptimizer(
            cache_ttl=cache_ttl,
            enable_cache=enable_cache
        )
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize LLM client based on provider"""
        try:
            if self.provider == "openai":
                try:
                    import openai
                    import os
                    api_key = os.getenv("OPENAI_API_KEY")
                    if not api_key:
                        logger.warning("OPENAI_API_KEY not set in environment")
                    self._client = openai.OpenAI(api_key=api_key) if api_key else openai.OpenAI()
                    logger.info("Initialized OpenAI client")
                except ImportError:
                    logger.warning("OpenAI not installed. Install with: pip install openai")
            
            elif self.provider == "anthropic":
                try:
                    import anthropic
                    self._client = anthropic.Anthropic()
                    logger.info("Initialized Anthropic client")
                except ImportError:
                    logger.warning("Anthropic not installed. Install with: pip install anthropic")
            
            elif self.provider == "local":
                # For local models (Ollama, etc.)
                logger.info("Using local LLM provider")
                self._client = None  # Implement local client
            
            else:
                logger.warning(f"Unknown provider: {self.provider}")
        
        except Exception as e:
            logger.error(f"Error initializing LLM client: {e}")
            self._client = None
    
    async def think(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        thinking_mode: bool = True,
        use_cache: bool = True,
        task_complexity: str = "medium"
    ) -> str:
        """
        Use LLM for thinking/reasoning with cost optimization
        
        Args:
            prompt: User prompt
            system_prompt: System prompt for context
            thinking_mode: Whether to use thinking/reasoning mode
            use_cache: Whether to use cached responses
            task_complexity: Task complexity for model selection ("simple", "medium", "complex")
            
        Returns:
            LLM response
        """
        if not self._client:
            logger.warning("LLM client not initialized, returning empty response")
            return ""
        
        # Optimize prompt
        optimized_prompt = self.cost_optimizer.optimize_prompt(prompt)
        
        # Check cache
        if use_cache:
            cached = self.cost_optimizer.get_cached_response(
                optimized_prompt,
                system_prompt,
                self.model
            )
            if cached is not None:
                return cached
        
        # Select model based on complexity (if different from default)
        model_to_use = self.model
        if task_complexity != "complex" and "gpt-4" in self.model:
            # Use cheaper model for simple/medium tasks
            model_to_use = self.cost_optimizer.select_model(task_complexity, prefer_cheap=True)
            logger.debug(f"Using {model_to_use} for {task_complexity} complexity task")
        
        try:
            if self.provider == "openai":
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": optimized_prompt})
                
                # Estimate input tokens
                input_tokens = self.cost_optimizer._estimate_tokens(
                    (system_prompt or "") + optimized_prompt
                )
                
                response = self._client.chat.completions.create(
                    model=model_to_use,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                
                result = response.choices[0].message.content
                
                # Track usage
                output_tokens = response.usage.completion_tokens if hasattr(response, 'usage') else \
                    self.cost_optimizer._estimate_tokens(result)
                input_tokens = response.usage.prompt_tokens if hasattr(response, 'usage') else input_tokens
                
                self.cost_optimizer.track_request(
                    model_to_use,
                    input_tokens,
                    output_tokens,
                    cached=False
                )
                
                # Cache response
                if use_cache:
                    self.cost_optimizer.cache_response(
                        optimized_prompt,
                        result,
                        system_prompt,
                        model_to_use
                    )
                
                return result
            
            elif self.provider == "anthropic":
                system_msg = system_prompt or ""
                response = self._client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=system_msg,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
            
            else:
                logger.warning(f"Provider {self.provider} not implemented")
                return ""
        
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return ""
    
    async def reason_about_ontology(
        self,
        context: str,
        question: str,
        ontology_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use LLM to reason about ontology
        
        Args:
            context: Context information
            question: Question to reason about
            ontology_schema: Ontology schema
            
        Returns:
            Reasoning result
        """
        system_prompt = f"""You are an ontology reasoning expert. Your task is to reason about entities, relations, and properties based on the provided ontology schema.

Ontology Schema:
{json.dumps(ontology_schema, indent=2)}

Use your reasoning to:
1. Infer entity types from properties
2. Suggest appropriate relations
3. Map properties to schema
4. Validate semantic correctness
5. Suggest improvements to the ontology

Think step by step and provide structured reasoning."""
        
        prompt = f"""Context: {context}

Question: {question}

Please reason about this and provide:
1. Your reasoning process
2. Recommended entity type (if applicable)
3. Recommended properties mapping
4. Any relations that should be created
5. Validation results

Format your response as JSON with keys: reasoning, entity_type, properties, relations, validation."""
        
        response = await self.think(prompt, system_prompt=system_prompt)
        
        # Try to parse JSON response
        try:
            # Extract JSON from response if it's wrapped in markdown
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                response = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                response = response[json_start:json_end].strip()
            
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON")
            return {
                "reasoning": response,
                "entity_type": None,
                "properties": {},
                "relations": [],
                "validation": {}
            }
    
    async def extract_entities_with_reasoning(
        self,
        text: str,
        ontology_schema: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract entities from text using LLM reasoning
        
        Args:
            text: Text to extract entities from
            ontology_schema: Ontology schema
            
        Returns:
            List of extracted entities
        """
        system_prompt = f"""You are an expert at extracting structured information from text based on an ontology schema.

Ontology Schema:
{json.dumps(ontology_schema, indent=2)}

Extract entities and their properties from the text, mapping them to the ontology schema."""
        
        prompt = f"""Extract entities from the following text and map them to the ontology schema:

Text: {text}

For each entity found, provide:
1. Entity type (from schema)
2. Properties (mapped to schema)
3. Confidence score

Format as JSON array of entities."""
        
        response = await self.think(prompt, system_prompt=system_prompt)
        
        try:
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                response = response[json_start:json_end].strip()
            
            entities = json.loads(response)
            if isinstance(entities, list):
                return entities
            else:
                return [entities]
        except json.JSONDecodeError:
            logger.warning("Failed to parse entity extraction response")
            return []
    
    async def suggest_relations(
        self,
        source_entity: Dict[str, Any],
        target_entity: Dict[str, Any],
        context: Optional[str] = None,
        ontology_schema: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Suggest relations between entities using LLM reasoning
        
        Args:
            source_entity: Source entity
            target_entity: Target entity
            context: Optional context
            ontology_schema: Ontology schema
            
        Returns:
            List of suggested relations
        """
        system_prompt = f"""You are an expert at identifying relationships between entities based on ontology schemas.

Ontology Schema:
{json.dumps(ontology_schema or {}, indent=2)}

Analyze the relationship between entities and suggest appropriate relation types."""
        
        prompt = f"""Source Entity: {json.dumps(source_entity, indent=2)}
Target Entity: {json.dumps(target_entity, indent=2)}
Context: {context or "No additional context"}

Suggest appropriate relations between these entities. Consider:
1. Semantic relationships
2. Ontology schema constraints
3. Context clues

Format as JSON array of relations with: type, confidence, properties."""
        
        response = await self.think(prompt, system_prompt=system_prompt)
        
        try:
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                response = response[json_start:json_end].strip()
            
            relations = json.loads(response)
            if isinstance(relations, list):
                return relations
            else:
                return [relations]
        except json.JSONDecodeError:
            logger.warning("Failed to parse relation suggestion response")
            return []

