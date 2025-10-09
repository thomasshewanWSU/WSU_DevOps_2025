import json
import boto3
import os
from datetime import datetime
from constants import ENV_ALARM_LOG_TABLE

# Initialize DynamoDB resource
# DynamoDB provides two API styles: resource (high-level) and client (low-level)
# Resource API documentation: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/resources.html
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['ALARM_LOG_TABLE'])


def lambda_handler(event, context):
    """
    Lambda handler for processing SNS alarm notifications.
    """
    # Process each SNS record in the event
    # SNS can batch multiple notifications into a single Lambda invocation
    for record in event['Records']:
        # Parse the SNS message (CloudWatch alarm details)
        message = json.loads(record['Sns']['Message'])
        alarm_name = message.get('AlarmName', 'Unknown')
        timestamp = datetime.utcnow().isoformat()
        
        # Store alarm event in DynamoDB for audit trail
        # put_item documentation: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb/table/put_item.html
        table.put_item(
            Item={
                'AlarmName': alarm_name,
                'Timestamp': timestamp,
                'Message': json.dumps(message)
            }
        )
    
    return {"status": "logged"}