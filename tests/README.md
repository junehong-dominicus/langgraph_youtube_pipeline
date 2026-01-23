# Tests for LangGraph YouTube Pipeline

This directory contains the test suite for the LangGraph YouTube Pipeline project. The tests cover unit logic for individual nodes, state management, graph routing, and full integration scenarios.

## Prerequisites

Ensure you have the test dependencies installed. From the project root:

```bash
pip install -r requirements-test.txt
```

## Running Tests

To run the full test suite, execute the following command from the project root:

```bash
pytest
```

### Running Specific Tests

To run only unit tests (fast):
```bash
pytest tests/test_nodes.py tests/test_state.py tests/test_graph.py
```

To run integration tests (simulates full pipeline execution):
```bash
pytest tests/test_integration.py
```

## Test Structure

- **`conftest.py`**: Sets up the Python path and defines shared fixtures (e.g., `default_state`).
- **`test_nodes.py`**: Unit tests for individual LangGraph nodes (e.g., `script_generator`, `topic_planner`).
- **`test_state.py`**: Tests for the `VideoState` TypedDict and reducer functions.
- **`test_graph.py`**: Tests for graph compilation, routing logic (`route_content_type`), and retry conditions (`should_retry`).
- **`test_integration.py`**: Integration tests that run the compiled graph (`app.invoke`) to verify end-to-end flow for different content types (Long, Short, Both).