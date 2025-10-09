import json
import os
import uuid
from datetime import datetime 
import boto3

# Initialize DynamoDB resource for table operations
# DynamoDB Resource API: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#service-resource
dynamodb = boto3.resource('dynamodb')

# Get table name from environment variable (set by CDK during deployment)
# Environment variables documentation: https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html
table_name = os.environ['TARGETS_TABLE_NAME']

# Get table resource for performing operations
# Table Resource API: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb/table/index.html
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    """
    Main handler - routes requests based on HTTP method and path
    
    Lambda Proxy Integration: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    Event format: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format
    Response format: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-output-format
    """
    print(f"Received event: {json.dumps(event)}")
    
    try:
        http_method = event['httpMethod']
        path = event['path']
        path_parameters = event.get('pathParameters') or {}
        
        # Route to appropriate handler
        if path == '/targets':
            if http_method == 'GET':
                return list_targets()
            elif http_method == 'POST':
                body = json.loads(event['body'])
                return create_target(body)
                
        elif path.startswith('/targets/'):
            target_id = path_parameters.get('id')
            if not target_id:
                return error_response(400, "Missing target ID")
                
            if http_method == 'GET':
                return get_target(target_id)
            elif http_method == 'PUT':
                body = json.loads(event['body'])
                return update_target(target_id, body)
            elif http_method == 'DELETE':
                return delete_target(target_id)
        
        return error_response(404, "Route not found")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response(500, f"Internal error: {str(e)}")


def list_targets():
    """
    GET /targets - List all monitoring targets
    
    DynamoDB Scan: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb/table/scan.html
    API Reference: https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_Scan.html
    """
    try:
        response = table.scan()
        items = response.get('Items', [])
        
        return success_response({
            'targets': items,
            'count': len(items)
        })
    except Exception as e:
        return error_response(500, f"Failed to list targets: {str(e)}")


def get_target(target_id):
    """
    GET /targets/{id} - Get a single target
    
    DynamoDB GetItem: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb/table/get_item.html
    API Reference: https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_GetItem.html
    """
    try:
        response = table.get_item(Key={'TargetId': target_id})
        
        if 'Item' not in response:
            return error_response(404, f"Target {target_id} not found")
            
        return success_response(response['Item'])
    except Exception as e:
        return error_response(500, f"Failed to get target: {str(e)}")


def create_target(data):
    """
    POST /targets - Create a new monitoring target
    
    DynamoDB PutItem: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb/table/put_item.html
    API Reference: https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_PutItem.html
    UUID generation: https://docs.python.org/3/library/uuid.html#uuid.uuid4
    """
    try:
        # Validate required fields
        if 'name' not in data or 'url' not in data:
            return error_response(400, "Missing required fields: name and url")
        
        # Create new target
        # Generate unique ID: https://docs.python.org/3/library/uuid.html
        target_id = str(uuid.uuid4())
        # ISO 8601 timestamp: https://docs.python.org/3/library/datetime.html#datetime.datetime.isoformat
        timestamp = datetime.utcnow().isoformat()
        
        item = {
            'TargetId': target_id,
            'name': data['name'],
            'url': data['url'],
            'enabled': data.get('enabled', True),
            'created_at': timestamp,
            'updated_at': timestamp
        }
        
        table.put_item(Item=item)
        print(f"Created target: {target_id}")
        
        return success_response(item, status_code=201)
    except Exception as e:
        return error_response(500, f"Failed to create target: {str(e)}")


def update_target(target_id, data):
    """
    PUT /targets/{id} - Update an existing target
    
    DynamoDB UpdateItem: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb/table/update_item.html
    API Reference: https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_UpdateItem.html
    Update Expressions: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.UpdateExpressions.html
    """
    try:
        # Check if target exists
        response = table.get_item(Key={'TargetId': target_id})
        if 'Item' not in response:
            return error_response(404, f"Target {target_id} not found")
        
        # Build update expression dynamically
        update_expression = "SET updated_at = :timestamp"
        expression_values = {':timestamp': datetime.utcnow().isoformat()}
        expression_names = {}
        
        if 'name' in data:
            update_expression += ", #name = :name"
            expression_values[':name'] = data['name']
            expression_names['#name'] = 'name'
            
        if 'url' in data:
            update_expression += ", #url = :url"
            expression_values[':url'] = data['url']
            expression_names['#url'] = 'url'
            
        if 'enabled' in data:
            update_expression += ", enabled = :enabled"
            expression_values[':enabled'] = data['enabled']
        
        # Update item
        response = table.update_item(
            Key={'TargetId': target_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_names if expression_names else None,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )
        
        print(f"Updated target: {target_id}")
        return success_response(response['Attributes'])
    except Exception as e:
        return error_response(500, f"Failed to update target: {str(e)}")


def delete_target(target_id):
    """
    DELETE /targets/{id} - Delete a target
    
    DynamoDB DeleteItem: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb/table/delete_item.html
    API Reference: https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_DeleteItem.html
    """
    try:
        # Check if target exists
        response = table.get_item(Key={'TargetId': target_id})
        if 'Item' not in response:
            return error_response(404, f"Target {target_id} not found")
        
        # Delete item
        table.delete_item(Key={'TargetId': target_id})
        print(f"Deleted target: {target_id}")
        
        return success_response({'message': f'Target {target_id} deleted successfully'})
    except Exception as e:
        return error_response(500, f"Failed to delete target: {str(e)}")


def success_response(data, status_code=200):
    """
    Generate successful API response
    
    Lambda Proxy Response Format: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-output-format
    CORS Headers: https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-cors.html
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'  # CDK CORS config: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_apigateway/CorsOptions.html
        },
        'body': json.dumps(data)
    }


def error_response(status_code, message):
    """
    Generate error API response
    
    HTTP Status Codes: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({'error': message})
    }