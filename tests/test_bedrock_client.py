from unittest.mock import patch
import pytest
from app.bedrock_client import BedrockClient

@pytest.fixture
def client():
    return BedrockClient()

@patch("app.bedrock_client.BedrockClient.generate_response")
def test_generate_response(mock_generate, client):
    mock_generate.return_value = {
        "status": "success",
        "content": "Sustainable finance refers to..."
    }

    response = client.generate_response("What is sustainable finance?")
    assert response["status"] == "success"
    assert "content" in response

@patch("app.bedrock_client.BedrockClient.generate_response")
def test_analyze_financial_action(mock_generate, client):
    mock_generate.return_value = {
        "status": "success",
        "content": "This action is Green under MAS guidelines."
    }

    action = {
        "description": "Installing a 500MW solar farm in Singapore",
        "amount": 1000000,
        "currency": "SGD",
        "organization": {
            "org_type": "Large Enterprise",
            "industry": "Energy",
            "country": "Singapore"
        }
    }

    response = client.analyze_financial_action(action)
    assert response["status"] == "success"
    assert "analysis" not in response  # remember: it returns 'content', not 'analysis' in current version
    assert "content" in response

def test_error_handling(client):
    with pytest.raises(TypeError):  # Because prompt=None fails at str formatting
        client.generate_response(None)

    bad_action = {"description": None}
    response = client.analyze_financial_action(bad_action)
    assert response["status"] == "error"
    assert "error" in response
