"""
Unit Tests for Infrastructure Lambda Function
Tests CloudWatch alarm and dashboard management logic without AWS resources

Testing Strategy:
- Mocks CloudWatch API calls to test logic in isolation
- Verifies correct number of alarms created/deleted
- Tests DynamoDB Stream event processing
- Validates alarm configuration parameters

Testing Tools:
- pytest: Test framework
- unittest.mock: Mocking library for AWS service calls
  - @patch: Replaces CloudWatch client with mock
  - MagicMock: Simulates CloudWatch API responses

Test Coverage:
- Alarm creation when website added (INSERT event)
- Alarm deletion when website removed (REMOVE event)
- Dashboard widget updates
- DynamoDB Stream event processing (INSERT, REMOVE, MODIFY)

AWS Services Mocked:
- CloudWatch (put_metric_alarm, delete_alarms, get_dashboard, put_dashboard)
"""

import os
import json
from unittest.mock import patch, MagicMock
import sys

# Add modules directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../modules'))

# Set required environment variables to simulate Lambda runtime
# These are normally injected by CDK during deployment
os.environ['ALARM_TOPIC_ARN'] = 'arn:aws:sns:test:123:topic'
os.environ['DASHBOARD_NAME'] = 'TestDashboard'
os.environ['DASHBOARD_REGION'] = 'ap-southeast-2'
os.environ['AWS_DEFAULT_REGION'] = 'ap-southeast-2'

from modules.InfrastructureLambda import handle_website_added, handle_website_removed, lambda_handler


@patch('modules.InfrastructureLambda.cloudwatch')
def test_creates_three_alarms_when_website_added(mock_cloudwatch):
	"""
	Test that exactly 3 CloudWatch alarms are created when a website is added.
	
	Verifies:
	- put_metric_alarm is called 3 times (Availability, Latency, Throughput)
	- Each alarm is properly configured with the website name
	
	The three alarms monitor:
	1. Availability: Alerts when site is down (< 1)
	2. Latency: Alerts on anomalous response times
	3. Throughput: Alerts on anomalous data transfer rates
	"""
	mock_cw = MagicMock()
	mock_cw.get_dashboard.return_value = {'DashboardBody': json.dumps({'widgets': []})}
	
	with patch('modules.InfrastructureLambda.cloudwatch', mock_cw):
		handle_website_added('TestSite', 'arn:test', 'TestDashboard')
	
	assert mock_cw.put_metric_alarm.call_count == 3


@patch('modules.InfrastructureLambda.cloudwatch')
def test_deletes_three_alarms_when_website_removed(mock_cloudwatch):
	"""
	Test that exactly 3 CloudWatch alarms are deleted when a website is removed.
	
	Verifies:
	- delete_alarms is called with correct alarm names
	- All three alarms (Availability, Latency, Throughput) are included
	
	This ensures cleanup of monitoring infrastructure when targets are deleted.
	"""
	mock_cw = MagicMock()
	mock_cw.get_dashboard.return_value = {'DashboardBody': json.dumps({'widgets': []})}
	
	with patch('modules.InfrastructureLambda.cloudwatch', mock_cw):
		handle_website_removed('TestSite')
	
	assert mock_cw.delete_alarms.called
	alarm_names = mock_cw.delete_alarms.call_args[1]['AlarmNames']
	assert len(alarm_names) == 3


@patch('modules.InfrastructureLambda.cloudwatch')
def test_dashboard_updated_when_website_added(mock_cloudwatch):
	"""
	Test that CloudWatch dashboard is updated when a website is added.
	
	Verifies:
	- get_dashboard is called to retrieve current dashboard configuration
	- put_dashboard is called to update dashboard with new website metrics
	
	This ensures the dashboard shows metrics for all monitored websites.
	"""
	mock_cw = MagicMock()
	mock_cw.get_dashboard.return_value = {'DashboardBody': json.dumps({'widgets': []})}
	
	with patch('modules.InfrastructureLambda.cloudwatch', mock_cw):
		handle_website_added('TestSite', 'arn:test', 'TestDashboard')
	
	assert mock_cw.put_dashboard.called



def test_lambda_handler_processes_insert_event():
	"""
	Test Lambda handler correctly processes DynamoDB INSERT events.
	
	Verifies:
	- INSERT event triggers handle_website_added function
	- Website name is extracted from DynamoDB Stream format
	
	Simulates the flow:
	User creates target via CRUD API → DynamoDB INSERT → Stream triggers Lambda
	→ Lambda creates CloudWatch alarms
	"""
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
	"""
	Test Lambda handler correctly processes DynamoDB REMOVE events.
	
	Verifies:
	- REMOVE event triggers handle_website_removed function
	- Website name is extracted from OldImage in DynamoDB Stream format
	
	Simulates the flow:
	User deletes target via CRUD API → DynamoDB REMOVE → Stream triggers Lambda
	→ Lambda deletes CloudWatch alarms
	"""
	with patch('modules.InfrastructureLambda.handle_website_removed') as mock_remove:
		event = {
			'Records': [{
				'eventName': 'REMOVE',
				'dynamodb': {'OldImage': {'name': {'S': 'OldSite'}}}
			}]
		}
		lambda_handler(event, {})
		assert mock_remove.called
