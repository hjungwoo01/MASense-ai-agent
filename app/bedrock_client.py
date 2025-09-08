import boto3
import logging
import json
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv

load_dotenv()

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
            
            if 'content' not in response_body or not response_body['content']:
                return {
                    "status": "error",
                    "error": "Invalid response from Bedrock"
                }
                
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


    def analyze_financial_action(self, action: dict) -> dict:
        """
        Use Bedrock Claude model to analyze a financial action and return classification.
        """
        try:
            prompt = f"""
    You are an ESG compliance analyst evaluating financial actions based on MAS Taxonomy.

    Here is a financial action submitted by an organization:

    Description: {action['description']}
    Amount: {action['amount']} {action['currency']}
    Organization Type: {action['organization'].get('org_type')}
    Industry: {action['organization'].get('industry')}
    Country: {action['organization'].get('country')}

    Evaluate whether this action aligns with MAS ESG classification guidelines.

    Return your analysis in the following JSON format:

    {{
    "classification": "Green / Amber / Ineligible / Uncertain",
    "explanation": "Rationale for classification",
    "required_documentation": ["List", "Of", "Supporting", "Documents"]
    }}

    Only return valid JSON. Do not include any commentary or explanation outside the JSON.
    """

            response = self.generate_response(prompt)
            return {
                "status": "success",
                "content": response
            }

        except Exception as e:
            logger.error(f"[Bedrock Error] Failed to analyze financial action: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


