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
            region_name=os.getenv("AWS_DEFAULT_REGION", "ap-southeast-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )

    def generate_response(self, user_prompt: str) -> Dict[str, Any]:
        """Generate a response using Claude 3 Sonnet model via Bedrock"""

        # Claude models require a structured prompt
        formatted_prompt = f"\n\nHuman: {user_prompt}\n\nAssistant:"

        request_body = {
            "prompt": formatted_prompt,
            "max_tokens_to_sample": 1600,
            "temperature": 0.7,
            "top_p": 0.999,
            "stop_sequences": ["\n\nHuman:"]
        }

        try:
            response = self.client.invoke_model(
                modelId="anthropic.claude-3-sonnet-20240229-v1",
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )

            # Read and parse the response
            body = response["body"].read().decode("utf-8")
            logger.debug(f"Raw Bedrock response: {body}")
            parsed = json.loads(body)

            return {
                "status": "success",
                "content": parsed.get("completion", "").strip()
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
