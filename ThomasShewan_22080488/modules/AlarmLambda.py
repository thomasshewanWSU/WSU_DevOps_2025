import json
import boto3
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['ALARM_LOG_TABLE'])

def lambda_handler(event, context):
    for record in event['Records']:
        message = json.loads(record['Sns']['Message'])
        alarm_name = message.get('AlarmName', 'Unknown')
        timestamp = datetime.utcnow().isoformat()
        table.put_item(
            Item={
                'AlarmName': alarm_name,
                'Timestamp': timestamp,
                'Message': json.dumps(message)
            }
        )
    return {"status": "logged"}