import boto3
import json
import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load .env file (for local development)
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BedrockClient:
    def __init__(self):
        """Initialize AWS Bedrock client with credentials from environment variables"""
        self.client = boto3.client(
            'bedrock-runtime',
            region_name=os.getenv("AWS_DEFAULT_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )

    def generate_response(self, prompt: str) -> Dict[str, Any]:
        """Generate a response using Claude 3 with Bedrock Messages API"""
        try:
            model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0:28k")
            use_streaming = os.getenv("USE_STREAMING", "false").lower() == "true"

            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1600,
                "temperature": 0.7
            }

            if use_streaming:
                response = self.client.invoke_model_with_response_stream(
                    modelId=model_id,
                    body=json.dumps(request_body),
                    contentType="application/json",
                    accept="application/json"
                )

                # Decode the streaming response
                response_body = b"".join([chunk["chunk"]["bytes"] for chunk in response["body"]])
                decoded = json.loads(response_body)

            else:
                response = self.client.invoke_model(
                    modelId=model_id,
                    body=json.dumps(request_body),
                    contentType="application/json",
                    accept="application/json"
                )

                decoded = json.loads(response["body"].read())

            return {
                "content": decoded["content"][0]["text"],
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
