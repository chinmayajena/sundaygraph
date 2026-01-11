"""Cortex Analyst regression test harness."""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import time
import requests
import json

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class QuestionExpectation:
    """Expected results for a question."""
    question: str
    expected_tables: Optional[List[str]] = None
    expected_sql_patterns: Optional[List[str]] = None
    expected_answer_snippet: Optional[str] = None


@dataclass
class QuestionResult:
    """Result of a single question test."""
    question: str
    passed: bool
    sql: Optional[str] = None
    answer: Optional[str] = None
    latency_ms: float = 0.0
    failure_reason: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "question": self.question,
            "passed": self.passed,
            "sql": self.sql,
            "answer": self.answer,
            "latency_ms": self.latency_ms,
            "failure_reason": self.failure_reason,
            "details": self.details
        }


@dataclass
class RegressionRunResult:
    """Result of a regression test run."""
    semantic_view_fqname: str
    total_questions: int
    passed: int
    failed: int
    question_results: List[QuestionResult] = field(default_factory=list)
    overall_pass: bool = True
    total_latency_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "semantic_view_fqname": self.semantic_view_fqname,
            "total_questions": self.total_questions,
            "passed": self.passed,
            "failed": self.failed,
            "overall_pass": self.overall_pass,
            "total_latency_ms": self.total_latency_ms,
            "question_results": [r.to_dict() for r in self.question_results]
        }


class CortexAnalystClient:
    """Client for Cortex Analyst REST API."""
    
    def __init__(
        self,
        account_url: str,
        database: str,
        schema: str,
        semantic_view_name: str,
        api_key: Optional[str] = None,
        session_token: Optional[str] = None
    ):
        """
        Initialize Cortex Analyst client.
        
        Args:
            account_url: Snowflake account URL (e.g., "https://abc12345.snowflakecomputing.com")
            database: Database name
            schema: Schema name
            semantic_view_name: Semantic view name
            api_key: Optional API key for authentication
            session_token: Optional session token for authentication
        """
        self.account_url = account_url.rstrip('/')
        self.database = database
        self.schema = schema
        self.semantic_view_name = semantic_view_name
        self.api_key = api_key
        self.session_token = session_token
        
        # Construct API endpoint
        self.api_endpoint = f"{self.account_url}/api/v1/cortex/analyst/query"
    
    def ask_question(self, question: str) -> Dict[str, Any]:
        """
        Ask a question to Cortex Analyst.
        
        Args:
            question: Natural language question
            
        Returns:
            Response dictionary with SQL, answer, and metadata
        """
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.session_token:
            headers["X-Snowflake-Token"] = self.session_token
        
        payload = {
            "database": self.database,
            "schema": self.schema,
            "semantic_view": self.semantic_view_name,
            "question": question
        }
        
        try:
            start_time = time.time()
            response = requests.post(
                self.api_endpoint,
                json=payload,
                headers=headers,
                timeout=60
            )
            latency_ms = (time.time() - start_time) * 1000
            
            response.raise_for_status()
            result = response.json()
            
            return {
                "sql": result.get("sql"),
                "answer": result.get("answer"),
                "tables": result.get("tables", []),
                "latency_ms": latency_ms,
                "success": True
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Cortex Analyst API error: {e}")
            return {
                "sql": None,
                "answer": None,
                "tables": [],
                "latency_ms": 0.0,
                "success": False,
                "error": str(e)
            }


class CortexRegressionRunner:
    """Runner for Cortex Analyst regression tests."""
    
    def __init__(
        self,
        client: CortexAnalystClient,
        questions: List[QuestionExpectation]
    ):
        """
        Initialize regression runner.
        
        Args:
            client: Cortex Analyst client
            questions: List of questions with expectations
        """
        self.client = client
        self.questions = questions
    
    def run(self) -> RegressionRunResult:
        """
        Run regression tests.
        
        Returns:
            RegressionRunResult with all test results
        """
        result = RegressionRunResult(
            semantic_view_fqname=f"{self.client.database}.{self.client.schema}.{self.client.semantic_view_name}",
            total_questions=len(self.questions),
            passed=0,
            failed=0
        )
        
        for expectation in self.questions:
            question_result = self._test_question(expectation)
            result.question_results.append(question_result)
            
            if question_result.passed:
                result.passed += 1
            else:
                result.failed += 1
                result.overall_pass = False
            
            result.total_latency_ms += question_result.latency_ms
        
        return result
    
    def _test_question(self, expectation: QuestionExpectation) -> QuestionResult:
        """Test a single question against expectations."""
        # Call Cortex Analyst
        response = self.client.ask_question(expectation.question)
        
        if not response.get("success", False):
            return QuestionResult(
                question=expectation.question,
                passed=False,
                failure_reason=f"API call failed: {response.get('error', 'Unknown error')}",
                details={"response": response}
            )
        
        sql = response.get("sql")
        answer = response.get("answer", "")
        tables = response.get("tables", [])
        latency_ms = response.get("latency_ms", 0.0)
        
        # Check expectations
        passed = True
        failure_reasons = []
        details = {
            "sql": sql,
            "answer": answer,
            "tables": tables,
            "latency_ms": latency_ms
        }
        
        # Check expected tables
        if expectation.expected_tables:
            missing_tables = set(expectation.expected_tables) - set(tables)
            if missing_tables:
                passed = False
                failure_reasons.append(f"Missing expected tables: {', '.join(missing_tables)}")
                details["missing_tables"] = list(missing_tables)
        
        # Check expected SQL patterns
        if expectation.expected_sql_patterns and sql:
            sql_upper = sql.upper()
            missing_patterns = []
            for pattern in expectation.expected_sql_patterns:
                if pattern.upper() not in sql_upper:
                    missing_patterns.append(pattern)
            
            if missing_patterns:
                passed = False
                failure_reasons.append(f"Missing SQL patterns: {', '.join(missing_patterns)}")
                details["missing_patterns"] = missing_patterns
        
        # Check expected answer snippet
        if expectation.expected_answer_snippet and answer:
            if expectation.expected_answer_snippet.lower() not in answer.lower():
                passed = False
                failure_reasons.append(f"Answer snippet not found: '{expectation.expected_answer_snippet}'")
                details["expected_snippet"] = expectation.expected_answer_snippet
        
        return QuestionResult(
            question=expectation.question,
            passed=passed,
            sql=sql,
            answer=answer,
            latency_ms=latency_ms,
            failure_reason="; ".join(failure_reasons) if failure_reasons else None,
            details=details
        )


def load_questions_from_yaml(yaml_path: str) -> List[QuestionExpectation]:
    """
    Load questions and expectations from YAML file.
    
    Args:
        yaml_path: Path to golden_questions.yaml file
        
    Returns:
        List of QuestionExpectation objects
    """
    import yaml
    from pathlib import Path
    
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Questions file not found: {yaml_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    questions = []
    for item in data.get("questions", []):
        questions.append(QuestionExpectation(
            question=item["question"],
            expected_tables=item.get("expected_tables"),
            expected_sql_patterns=item.get("expected_sql_patterns"),
            expected_answer_snippet=item.get("expected_answer_snippet")
        ))
    
    return questions


def generate_junit_xml(result: RegressionRunResult, output_path: Union[str, Path]):
    """
    Generate JUnit XML report for CI.
    
    Args:
        result: Regression run result
        output_path: Path to write junit.xml
    """
    import xml.etree.ElementTree as ET
    
    # Create test suite
    testsuite = ET.Element("testsuite")
    testsuite.set("name", "Cortex Analyst Regression Tests")
    testsuite.set("tests", str(result.total_questions))
    testsuite.set("failures", str(result.failed))
    testsuite.set("time", f"{result.total_latency_ms / 1000:.3f}")
    
    # Add test cases
    for i, question_result in enumerate(result.question_results):
        testcase = ET.SubElement(testsuite, "testcase")
        testcase.set("name", f"Question {i+1}: {question_result.question[:50]}...")
        testcase.set("classname", result.semantic_view_fqname)
        testcase.set("time", f"{question_result.latency_ms / 1000:.3f}")
        
        if not question_result.passed:
            failure = ET.SubElement(testcase, "failure")
            failure.set("message", question_result.failure_reason or "Test failed")
            failure.text = f"Question: {question_result.question}\n"
            if question_result.sql:
                failure.text += f"SQL: {question_result.sql}\n"
            if question_result.answer:
                failure.text += f"Answer: {question_result.answer}\n"
            failure.text += f"Details: {json.dumps(question_result.details, indent=2)}"
        
        # Add system-out with full details
        system_out = ET.SubElement(testcase, "system-out")
        system_out.text = json.dumps(question_result.to_dict(), indent=2)
    
    # Write XML
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding='utf-8', xml_declaration=True)
    
    logger.info(f"Generated JUnit XML: {output_path}")
