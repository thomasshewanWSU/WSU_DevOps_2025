"""
Unit tests for the CRUD Lambda handler
Tests all CRUD operations without requiring actual AWS resources
"""
import os
import json
import pytest
from unittest.mock import patch, MagicMock

# Set required environment variables before importing the Lambda handler
os.environ['TARGETS_TABLE_NAME'] = 'test-table'
os.environ['AWS_DEFAULT_REGION'] = 'ap-southeast-2'

from modules.CRUDLambda import lambda_handler as CrudLambda

@patch('modules.CRUDLambda.table')
def test_create_target_success(mock_table):
	"""Test successful target creation"""
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
def test_create_target_missing_fields(mock_table):
	"""Test target creation with missing required fields"""
	event = {
		'httpMethod': 'POST',
		'path': '/targets',
		'body': json.dumps({'name': 'TestSite'})  # Missing 'url'
	}
	response = CrudLambda(event, {})
	
	assert response['statusCode'] == 400
	body = json.loads(response['body'])
	assert 'error' in body

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
def test_get_nonexistent_target(mock_table):
	"""Test retrieving a target that doesn't exist"""
	event = {
		'httpMethod': 'GET',
		'path': '/targets/999',
		'pathParameters': {'id': '999'}
	}
	mock_table.get_item.return_value = {}  # No Item key = not found
	response = CrudLambda(event, {})
	
	assert response['statusCode'] == 404

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
def test_update_nonexistent_target(mock_table):
	"""Test updating a target that doesn't exist"""
	event = {
		'httpMethod': 'PUT',
		'path': '/targets/999',
		'pathParameters': {'id': '999'},
		'body': json.dumps({'name': 'Updated'})
	}
	mock_table.get_item.return_value = {}  # Not found
	response = CrudLambda(event, {})
	
	assert response['statusCode'] == 404

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

@patch('modules.CRUDLambda.table')
def test_delete_nonexistent_target(mock_table):
	"""Test deleting a target that doesn't exist"""
	event = {
		'httpMethod': 'DELETE',
		'path': '/targets/999',
		'pathParameters': {'id': '999'}
	}
	mock_table.get_item.return_value = {}  # Not found
	response = CrudLambda(event, {})
	
	assert response['statusCode'] == 404

def test_invalid_http_method():
	"""Test handling of unsupported HTTP methods"""
	event = {
		'httpMethod': 'PATCH',
		'path': '/targets'
	}
	response = CrudLambda(event, {})
	
	assert response['statusCode'] == 404
