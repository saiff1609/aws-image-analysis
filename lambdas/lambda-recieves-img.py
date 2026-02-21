import json
import boto3
from decimal import Decimal

# Initialize AWS clients
rekognition = boto3.client('rekognition')
dynamodb = boto3.resource('dynamodb')

# DynamoDB table name
TABLE_NAME = "image-results"
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    try:
        # Get bucket and object key from S3 event
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']

        # Call Rekognition to detect labels
        response = rekognition.detect_labels(
            Image={'S3Object': {'Bucket': bucket, 'Name': key}},
            MaxLabels=5,
            MinConfidence=70  # optional: filter weak matches
        )

        # Convert float Confidence to Decimal for DynamoDB
        labels = [
            {
                'Name': label['Name'],
                'Confidence': Decimal(str(label['Confidence']))
            }
            for label in response['Labels']
        ]

        # Generate image URL (works if bucket is public or presigned later)
        image_url = f"https://{bucket}.s3.amazonaws.com/{key}"

        # Save results to DynamoDB
        table.put_item(
            Item={
                'imageid': key,          # must match partition key
                'bucket': bucket,
                'image_url': image_url,
                'labels': labels,        # now safe for DynamoDB
                'status': 'Processed'
            }
        )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Image processed successfully',
                'labels': labels
            })
        }

    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps('Error processing image')
        }

