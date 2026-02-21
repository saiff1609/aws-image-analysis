import json
import boto3
import uuid

s3 = boto3.client('s3')
BUCKET_NAME = "img-uploads-buck"

# map MIME types to file extensions
EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif"
}

def lambda_handler(event, context):
    # Handle preflight OPTIONS request
    if event.get("httpMethod") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET,POST,PUT,OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type,Authorization"
            },
            "body": json.dumps({"message": "CORS preflight"})
        }

    try:
        # get file type from query params (default to jpeg)
        file_type = "image/jpeg"
        if event.get("queryStringParameters") and "fileType" in event["queryStringParameters"]:
            file_type = event["queryStringParameters"]["fileType"]

        extension = EXTENSIONS.get(file_type, ".jpg")
        key = f"uploads/{str(uuid.uuid4())}{extension}"

        presigned_url = s3.generate_presigned_url(
            ClientMethod='put_object',
            Params={'Bucket': BUCKET_NAME, 'Key': key, 'ContentType': file_type},
            ExpiresIn=900
        )

        return {
            'statusCode': 200,
            'body': json.dumps({'uploadUrl': presigned_url, 'key': key}),
            'headers': {
                "Access-Control-Allow-Origin": "*"
            }
        }

    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}),
            'headers': {
                "Access-Control-Allow-Origin": "https://d1wsn1qg1pmuzj.cloudfront.net",
                "Access-Control-Allow-Headers": "Content-Type,Authorization",
                "Access-Control-Allow-Methods": "GET,POST,PUT,OPTIONS"
            }
        }
