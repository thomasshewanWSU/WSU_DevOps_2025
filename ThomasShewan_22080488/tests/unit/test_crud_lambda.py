"""
Unit Tests for CRUD Lambda Function
Tests all CRUD operations without requiring actual AWS resources

Testing Strategy:
- Uses unittest.mock to mock AWS services (DynamoDB)
- Tests Lambda function logic in isolation
- Fast execution (no network calls or AWS API usage)
- Verifies request routing, validation, and response formatting

Testing Tools:
- pytest: Test framework
  Documentation: https://docs.pytest.org/
- unittest.mock: Mocking library for Python
  Documentation: https://docs.python.org/3/library/unittest.mock.html
  - @patch: Replaces real objects with mock objects
"""

import os
import json
from unittest.mock import patch

# Set required environment variables before importing the Lambda handler
# These simulate the runtime environment provided by Lambda
os.environ['TARGETS_TABLE_NAME'] = 'test-table'
os.environ['AWS_DEFAULT_REGION'] = 'ap-southeast-2'

from modules.CRUDLambda import lambda_handler as CrudLambda

@patch('modules.CRUDLambda.table')
def test_create_target_success(mock_table):
	"""
	Test successful target creation.
	
	Verifies:
	- HTTP 201 Created status code
	- Response contains all required fields (TargetId, name, url, created_at)
	- UUID is generated for TargetId
	- Timestamp is added automatically
	
	Mock Behavior:
	- DynamoDB put_item is mocked to avoid actual database calls
	"""
	event = {
		'httpMethod': 'POST',
		'path': '/targets',
		'body': json.dumps({
			'name': 'TestSite',
			'url': 'https://example.com'
		})
	}
	mock_table.put_item.return_value = {}
	response = CrudLambda(event, {})
	
	assert response['statusCode'] == 201
	body = json.loads(response['body'])
	assert body['name'] == 'TestSite'
	assert body['url'] == 'https://example.com'
	assert 'TargetId' in body
	assert 'created_at' in body

@patch('modules.CRUDLambda.table')
def test_list_targets(mock_table):
	"""Test listing all targets"""
	event = {
		'httpMethod': 'GET',
		'path': '/targets'
	}
	mock_table.scan.return_value = {
		'Items': [
			{'TargetId': '123', 'name': 'Test1', 'url': 'https://test1.com'},
			{'TargetId': '456', 'name': 'Test2', 'url': 'https://test2.com'}
		]
	}
	response = CrudLambda(event, {})
	
	assert response['statusCode'] == 200
	body = json.loads(response['body'])
	assert body['count'] == 2
	assert len(body['targets']) == 2

@patch('modules.CRUDLambda.table')
def test_get_single_target(mock_table):
	"""Test retrieving a single target by ID"""
	event = {
		'httpMethod': 'GET',
		'path': '/targets/123',
		'pathParameters': {'id': '123'}
	}
	mock_table.get_item.return_value = {
		'Item': {'TargetId': '123', 'name': 'Test', 'url': 'https://test.com'}
	}
	response = CrudLambda(event, {})
	
	assert response['statusCode'] == 200
	body = json.loads(response['body'])
	assert body['TargetId'] == '123'
	assert body['name'] == 'Test'

@patch('modules.CRUDLambda.table')
def test_update_target(mock_table):
	"""Test updating a target"""
	event = {
		'httpMethod': 'PUT',
		'path': '/targets/123',
		'pathParameters': {'id': '123'},
		'body': json.dumps({'name': 'Updated', 'enabled': False})
	}
	mock_table.get_item.return_value = {'Item': {'TargetId': '123'}}
	mock_table.update_item.return_value = {
		'Attributes': {'TargetId': '123', 'name': 'Updated', 'enabled': False}
	}
	response = CrudLambda(event, {})
	
	assert response['statusCode'] == 200
	body = json.loads(response['body'])
	assert body['name'] == 'Updated'
	assert body['enabled'] == False

@patch('modules.CRUDLambda.table')
def test_delete_target(mock_table):
	"""Test deleting a target"""
	event = {
		'httpMethod': 'DELETE',
		'path': '/targets/123',
		'pathParameters': {'id': '123'}
	}
	mock_table.get_item.return_value = {'Item': {'TargetId': '123'}}
	mock_table.delete_item.return_value = {}
	response = CrudLambda(event, {})
	
	assert response['statusCode'] == 200
	body = json.loads(response['body'])
	assert 'message' in body

