import pytest
from app.graph import evaluate_financial_action
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_solar_farm_evaluation():
    action = {
        "description": "We are planning to install a 500MW solar farm in Singapore",
        "amount": 1000000,
        "currency": "SGD",
        "organization": {
            "org_type": "Large Enterprise",
            "industry": "Energy",
            "country": "Singapore"
        }
    }

    result = evaluate_financial_action(action)
    assert result["status"] != "error"
    assert "evaluation" in result or "explanation" in result

def test_building_upgrade_evaluation():
    action = {
        "description": "Upgrading HVAC system in our commercial building to reduce energy consumption by 30%",
        "amount": 500000,
        "currency": "SGD",
        "organization": {
            "org_type": "SME",
            "industry": "Real Estate",
            "country": "Singapore"
        }
    }

    result = evaluate_financial_action(action)
    assert result["status"] != "error"
    assert "evaluation" in result or "explanation" in result
