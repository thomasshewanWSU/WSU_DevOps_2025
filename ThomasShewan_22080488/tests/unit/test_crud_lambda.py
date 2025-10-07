# Unit tests for the CRUD Lambda handler
import os
import json
import pytest
from unittest.mock import patch

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
	assert 'TargetId' in body

@patch('modules.CRUDLambda.table')
def test_list_targets(mock_table):
	"""Test listing all targets"""
	event = {
		'httpMethod': 'GET',
		'path': '/targets'
	}
	mock_table.scan.return_value = {
		'Items': [{'TargetId': '123', 'name': 'Test', 'url': 'https://test.com'}]
	}
	response = CrudLambda(event, {})
	assert response['statusCode'] == 200
	body = json.loads(response['body'])
	assert body['count'] == 1

@patch('modules.CRUDLambda.table')
def test_update_target(mock_table):
	"""Test updating a target"""
	event = {
		'httpMethod': 'PUT',
		'path': '/targets/123',
		'pathParameters': {'id': '123'},
		'body': json.dumps({'name': 'Updated'})
	}
	mock_table.get_item.return_value = {'Item': {'TargetId': '123'}}
	mock_table.update_item.return_value = {
		'Attributes': {'TargetId': '123', 'name': 'Updated'}
	}
	response = CrudLambda(event, {})
	assert response['statusCode'] == 200

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
