import boto3
import json

def call_claude(prompt: str) -> str:
    bedrock = boto3.client('bedrock-runtime', region_name='ap-southeast-1')

    body = json.dumps({
            "prompt": prompt,
            "max_tokens_to_sample": 1000,
            "temperature": 0.3,
            "top_p": 0.95
        })

    response = client.invoke_model(
        modelId='anthropic.claude-2',
        body = body,
        contentType='application/json',
        accept='application/json'
    )
    response_body = json.loads(response['body'].read())
    return response_body['completion']
