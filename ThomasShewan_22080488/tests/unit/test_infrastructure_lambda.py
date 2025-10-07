"""
Unit tests for the Infrastructure Lambda handler
Tests alarm and dashboard management logic
"""
import os
import json
import pytest
from unittest.mock import patch, MagicMock

# Set required environment variables
os.environ['ALARM_TOPIC_ARN'] = 'arn:aws:sns:test:123:topic'
os.environ['DASHBOARD_NAME'] = 'TestDashboard'
os.environ['DASHBOARD_REGION'] = 'ap-southeast-2'
os.environ['AWS_DEFAULT_REGION'] = 'ap-southeast-2'

from modules.InfrastructureLambda import handle_website_added, handle_website_removed, lambda_handler


@patch('modules.InfrastructureLambda.cloudwatch')
def test_creates_three_alarms_when_website_added(mock_cloudwatch):
	"""Test that 3 alarms are created when website is added"""
	mock_cw = MagicMock()
	mock_cw.get_dashboard.return_value = {'DashboardBody': json.dumps({'widgets': []})}
	
	with patch('modules.InfrastructureLambda.cloudwatch', mock_cw):
		handle_website_added('TestSite', 'arn:test', 'TestDashboard')
	
	assert mock_cw.put_metric_alarm.call_count == 3


@patch('modules.InfrastructureLambda.cloudwatch')
def test_deletes_three_alarms_when_website_removed(mock_cloudwatch):
	"""Test that 3 alarms are deleted when website is removed"""
	mock_cw = MagicMock()
	mock_cw.get_dashboard.return_value = {'DashboardBody': json.dumps({'widgets': []})}
	
	with patch('modules.InfrastructureLambda.cloudwatch', mock_cw):
		handle_website_removed('TestSite')
	
	assert mock_cw.delete_alarms.called
	alarm_names = mock_cw.delete_alarms.call_args[1]['AlarmNames']
	assert len(alarm_names) == 3


@patch('modules.InfrastructureLambda.cloudwatch')
def test_dashboard_updated_when_website_added(mock_cloudwatch):
	"""Test that dashboard is updated when website is added"""
	mock_cw = MagicMock()
	mock_cw.get_dashboard.return_value = {'DashboardBody': json.dumps({'widgets': []})}
	
	with patch('modules.InfrastructureLambda.cloudwatch', mock_cw):
		handle_website_added('TestSite', 'arn:test', 'TestDashboard')
	
	assert mock_cw.put_dashboard.called


@patch('modules.InfrastructureLambda.cloudwatch')
def test_dashboard_updated_when_website_removed(mock_cloudwatch):
	"""Test that dashboard is updated when website is removed"""
	mock_cw = MagicMock()
	dashboard_body = {'widgets': [{'properties': {'metrics': []}}]}
	mock_cw.get_dashboard.return_value = {'DashboardBody': json.dumps(dashboard_body)}
	
	with patch('modules.InfrastructureLambda.cloudwatch', mock_cw):
		handle_website_removed('TestSite')
	
	assert mock_cw.put_dashboard.called


def test_lambda_handler_processes_insert_event():
	"""Test Lambda handler calls add function for INSERT events"""
	with patch('modules.InfrastructureLambda.handle_website_added') as mock_add:
		event = {
			'Records': [{
				'eventName': 'INSERT',
				'dynamodb': {'NewImage': {'name': {'S': 'NewSite'}}}
			}]
		}
		lambda_handler(event, {})
		assert mock_add.called


def test_lambda_handler_processes_remove_event():
	"""Test Lambda handler calls remove function for REMOVE events"""
	with patch('modules.InfrastructureLambda.handle_website_removed') as mock_remove:
		event = {
			'Records': [{
				'eventName': 'REMOVE',
				'dynamodb': {'OldImage': {'name': {'S': 'OldSite'}}}
			}]
		}
		lambda_handler(event, {})
		assert mock_remove.called
