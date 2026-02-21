import json
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = "image-results"  # your DynamoDB table name
table = dynamodb.Table(TABLE_NAME)

# helper to convert Decimal to float for JSON serialization
def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    try:
        # Expecting query string parameter 'key'
        key = event.get('queryStringParameters', {}).get('key')
        if not key:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing key parameter'}),
                'headers': {"Access-Control-Allow-Origin": "*"}
            }

        # Get item from DynamoDB
        response = table.get_item(Key={'imageid': key})
        item = response.get('Item')
        if not item:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Image not found'}),
                'headers': {"Access-Control-Allow-Origin": "*"}
            }

        # Return labels with Decimal converted to float
        return {
            'statusCode': 200,
            'body': json.dumps({'Labels': item.get('labels', [])}, default=decimal_default),
            'headers': {"Access-Control-Allow-Origin": "*"}
        }

    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}),
            'headers': {"Access-Control-Allow-Origin": "*"}
        }
