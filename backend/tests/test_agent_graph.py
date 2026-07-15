import pytest
from unittest.mock import patch, MagicMock

# Attempt to load the graph
from app.llm.graph import agent_graph

@pytest.mark.asyncio
async def test_agent_graph_create_task():
    with patch("app.llm.graph.ChatGroq") as mock_groq:
        mock_instance = MagicMock()
        mock_instance.bind.return_value = mock_instance
        
        # First call is for route_node, second is for extract_node
        # We will mock invoke behavior
        def mock_invoke(messages):
            sys_msg = messages[0]["content"]
            response_mock = MagicMock()
            if "intent routing" in sys_msg.lower() or "intent router" in sys_msg.lower():
                response_mock.content = '{"intent": "CREATE_TASK"}'
            else:
                response_mock.content = '{"title": "Test Task", "task_type": "personal", "category": "home", "severity": "low", "duration_minutes": 15, "is_blocking": false}'
            return response_mock
            
        mock_instance.invoke.side_effect = mock_invoke
        mock_groq.return_value = mock_instance

        # Invoke the graph
        final_state = await agent_graph.ainvoke({"text": "Test Task"})
        
        assert final_state["intent"] == "CREATE_TASK"
        assert "task_raw" in final_state
        assert final_state["task_raw"]["title"] == "Test Task"

@pytest.mark.asyncio
async def test_agent_graph_show_insights():
    with patch("app.llm.graph.ChatGroq") as mock_groq:
        mock_instance = MagicMock()
        mock_instance.bind.return_value = mock_instance
        
        def mock_invoke(messages):
            response_mock = MagicMock()
            response_mock.content = '{"intent": "SHOW_INSIGHTS"}'
            return response_mock
            
        mock_instance.invoke.side_effect = mock_invoke
        mock_groq.return_value = mock_instance

        # Invoke the graph
        final_state = await agent_graph.ainvoke({"text": "Show me insights"})
        
        assert final_state["intent"] == "SHOW_INSIGHTS"
        # Since it goes to end, task_raw should not be processed
        assert final_state.get("task_raw") is None

