import boto3
import logging
import json
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv

# Load .env file (for local development)
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BedrockClient:
    def __init__(self):
        """Initialize Bedrock client using boto3"""
        self.client = boto3.client(
            service_name='bedrock-runtime',
            region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        )
        self.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

    def generate_response(self, prompt: str) -> Dict[str, Any]:
        """Generate a response using Claude 3 via AWS Bedrock"""
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1600,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7
            }

            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            response_body = json.loads(response['body'].read().decode())
            return {
                "content": response_body['content'][0]['text'],
                "status": "success"
            }

        except Exception as e:
            logger.error(f"[Bedrock Error] Failed to get response: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


    def analyze_financial_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Builds prompt to analyze financial action using MAS taxonomy"""

        prompt = f"""Analyze this financial action according to MAS sustainability frameworks:

Action: {action.get('description', 'N/A')}
Amount: {action.get('amount', 'N/A')} {action.get('currency', 'SGD')}
Organization Type: {action.get('organization', {}).get('org_type', 'N/A')}
Industry: {action.get('organization', {}).get('industry', 'N/A')}

Provide:
1. Classification (Green / Amber / Ineligible)
2. Explanation with taxonomy citations
3. Required documentation or disclosures
4. Suggestions for improvement if any."""

        return self.generate_response(prompt)
