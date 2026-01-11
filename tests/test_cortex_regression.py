"""Tests for Cortex Analyst regression harness."""

import sys
from pathlib import Path
import tempfile
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.snowflake.cortex_analyst import (
    CortexAnalystClient, CortexRegressionRunner,
    QuestionExpectation, QuestionResult, RegressionRunResult,
    load_questions_from_yaml, generate_junit_xml
)


class MockCortexClient:
    """Mock Cortex Analyst client for testing."""
    
    def __init__(self):
        self.responses = {}
    
    def set_response(self, question: str, sql: str, answer: str, tables: List[str] = None):
        """Set mock response for a question."""
        self.responses[question] = {
            "sql": sql,
            "answer": answer,
            "tables": tables or [],
            "latency_ms": 100.0,
            "success": True
        }
    
    def ask_question(self, question: str):
        """Mock ask_question method."""
        return self.responses.get(question, {
            "sql": None,
            "answer": None,
            "tables": [],
            "latency_ms": 0.0,
            "success": False,
            "error": "Question not found in mock responses"
        })


def test_load_questions_from_yaml():
    """Test loading questions from YAML."""
    print("Test 1: Load questions from YAML")
    
    # Create temporary YAML file
    yaml_content = """
questions:
  - question: "What is the total revenue?"
    expected_tables:
      - "OrderItem"
    expected_sql_patterns:
      - "SUM"
    expected_answer_snippet: "revenue"
  
  - question: "How many orders?"
    expected_tables:
      - "Order"
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name
    
    try:
        questions = load_questions_from_yaml(yaml_path)
        
        assert len(questions) == 2, "Should load 2 questions"
        assert questions[0].question == "What is the total revenue?"
        assert questions[0].expected_tables == ["OrderItem"]
        assert questions[0].expected_sql_patterns == ["SUM"]
        assert questions[0].expected_answer_snippet == "revenue"
        
        assert questions[1].question == "How many orders?"
        assert questions[1].expected_tables == ["Order"]
        
        print("  [PASS] Questions loaded from YAML")
    finally:
        Path(yaml_path).unlink()


def test_question_result_passing():
    """Test question result when all expectations pass."""
    print("\nTest 2: Question result passing")
    
    expectation = QuestionExpectation(
        question="What is the total revenue?",
        expected_tables=["OrderItem"],
        expected_sql_patterns=["SUM"],
        expected_answer_snippet="revenue"
    )
    
    # Mock client response
    mock_client = MockCortexClient()
    mock_client.set_response(
        "What is the total revenue?",
        sql="SELECT SUM(amount) FROM OrderItem",
        answer="The total revenue is $1,234,567",
        tables=["OrderItem", "Order"]
    )
    
    # Create runner with mock
    runner = CortexRegressionRunner(mock_client, [expectation])
    result = runner.run()
    
    assert result.total_questions == 1
    assert result.passed == 1
    assert result.failed == 0
    assert result.overall_pass is True
    
    question_result = result.question_results[0]
    assert question_result.passed is True
    assert question_result.failure_reason is None
    assert "SUM" in question_result.sql
    
    print("  [PASS] Question result passes when expectations met")


def test_question_result_failing_missing_table():
    """Test question result when expected table is missing."""
    print("\nTest 3: Question result failing - missing table")
    
    expectation = QuestionExpectation(
        question="What is the total revenue?",
        expected_tables=["OrderItem", "Product"],
        expected_sql_patterns=["SUM"]
    )
    
    mock_client = MockCortexClient()
    mock_client.set_response(
        "What is the total revenue?",
        sql="SELECT SUM(amount) FROM OrderItem",
        answer="The total revenue is $1,234,567",
        tables=["OrderItem"]  # Product missing
    )
    
    runner = CortexRegressionRunner(mock_client, [expectation])
    result = runner.run()
    
    assert result.failed == 1
    assert result.overall_pass is False
    
    question_result = result.question_results[0]
    assert question_result.passed is False
    assert "Missing expected tables" in question_result.failure_reason
    assert "Product" in question_result.failure_reason
    
    print("  [PASS] Question result fails when table missing")


def test_question_result_failing_missing_sql_pattern():
    """Test question result when expected SQL pattern is missing."""
    print("\nTest 4: Question result failing - missing SQL pattern")
    
    expectation = QuestionExpectation(
        question="What is the total revenue?",
        expected_sql_patterns=["SUM", "JOIN"]
    )
    
    mock_client = MockCortexClient()
    mock_client.set_response(
        "What is the total revenue?",
        sql="SELECT SUM(amount) FROM OrderItem",  # No JOIN
        answer="The total revenue is $1,234,567",
        tables=["OrderItem"]
    )
    
    runner = CortexRegressionRunner(mock_client, [expectation])
    result = runner.run()
    
    assert result.failed == 1
    
    question_result = result.question_results[0]
    assert question_result.passed is False
    assert "Missing SQL patterns" in question_result.failure_reason
    assert "JOIN" in question_result.failure_reason
    
    print("  [PASS] Question result fails when SQL pattern missing")


def test_question_result_failing_missing_answer_snippet():
    """Test question result when expected answer snippet is missing."""
    print("\nTest 5: Question result failing - missing answer snippet")
    
    expectation = QuestionExpectation(
        question="What is the total revenue?",
        expected_answer_snippet="revenue"
    )
    
    mock_client = MockCortexClient()
    mock_client.set_response(
        "What is the total revenue?",
        sql="SELECT SUM(amount) FROM OrderItem",
        answer="The total is $1,234,567",  # No "revenue" in answer
        tables=["OrderItem"]
    )
    
    runner = CortexRegressionRunner(mock_client, [expectation])
    result = runner.run()
    
    assert result.failed == 1
    
    question_result = result.question_results[0]
    assert question_result.passed is False
    assert "Answer snippet not found" in question_result.failure_reason
    
    print("  [PASS] Question result fails when answer snippet missing")


def test_api_call_failure():
    """Test handling of API call failures."""
    print("\nTest 6: API call failure handling")
    
    expectation = QuestionExpectation(
        question="What is the total revenue?",
        expected_tables=["OrderItem"]
    )
    
    mock_client = MockCortexClient()
    # Don't set response, so it will return error
    
    runner = CortexRegressionRunner(mock_client, [expectation])
    result = runner.run()
    
    assert result.failed == 1
    assert result.overall_pass is False
    
    question_result = result.question_results[0]
    assert question_result.passed is False
    assert "API call failed" in question_result.failure_reason
    
    print("  [PASS] API call failure handled correctly")


def test_generate_junit_xml():
    """Test JUnit XML generation."""
    print("\nTest 7: Generate JUnit XML")
    
    result = RegressionRunResult(
        semantic_view_fqname="TEST_DB.PUBLIC.test_view",
        total_questions=2,
        passed=1,
        failed=1,
        overall_pass=False,
        total_latency_ms=200.0,
        question_results=[
            QuestionResult(
                question="Question 1",
                passed=True,
                sql="SELECT * FROM test",
                answer="Answer 1",
                latency_ms=100.0
            ),
            QuestionResult(
                question="Question 2",
                passed=False,
                sql="SELECT * FROM test2",
                answer="Answer 2",
                latency_ms=100.0,
                failure_reason="Missing table"
            )
        ]
    )
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        xml_path = f.name
    
    try:
        generate_junit_xml(result, xml_path)
        
        assert Path(xml_path).exists(), "JUnit XML should be created"
        
        # Read and verify XML structure
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        assert 'testsuite' in xml_content
        assert 'tests="2"' in xml_content
        assert 'failures="1"' in xml_content
        assert 'testcase' in xml_content
        assert 'failure' in xml_content
        
        print("  [PASS] JUnit XML generated correctly")
    finally:
        Path(xml_path).unlink()


def test_multiple_questions():
    """Test regression run with multiple questions."""
    print("\nTest 8: Multiple questions")
    
    expectations = [
        QuestionExpectation(
            question="Question 1",
            expected_tables=["Table1"]
        ),
        QuestionExpectation(
            question="Question 2",
            expected_tables=["Table2"]
        ),
        QuestionExpectation(
            question="Question 3",
            expected_tables=["Table3"]
        )
    ]
    
    mock_client = MockCortexClient()
    mock_client.set_response("Question 1", "SELECT * FROM Table1", "Answer 1", ["Table1"])
    mock_client.set_response("Question 2", "SELECT * FROM Table2", "Answer 2", ["Table2"])
    mock_client.set_response("Question 3", "SELECT * FROM Table3", "Answer 3", ["Table3"])
    
    runner = CortexRegressionRunner(mock_client, expectations)
    result = runner.run()
    
    assert result.total_questions == 3
    assert result.passed == 3
    assert result.failed == 0
    assert result.overall_pass is True
    assert len(result.question_results) == 3
    
    print("  [PASS] Multiple questions handled correctly")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Cortex Analyst Regression Tests")
    print("=" * 60)
    
    tests = [
        test_load_questions_from_yaml,
        test_question_result_passing,
        test_question_result_failing_missing_table,
        test_question_result_failing_missing_sql_pattern,
        test_question_result_failing_missing_answer_snippet,
        test_api_call_failure,
        test_generate_junit_xml,
        test_multiple_questions,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
