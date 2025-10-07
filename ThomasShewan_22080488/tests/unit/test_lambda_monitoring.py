"""
Unit tests specifically for Lambda memory monitoring
Tests that memory alarms and metrics are properly configured
"""
import aws_cdk as cdk
import aws_cdk.assertions as assertions
import pytest
from thomas_shewan_22080488.thomas_shewan_22080488_stack import ThomasShewan22080488Stack


@pytest.fixture
def stack():
    app = cdk.App()
    return ThomasShewan22080488Stack(app, "thomas-shewan-22080488")


@pytest.fixture
def template(stack):
    return assertions.Template.from_stack(stack)


def test_memory_alarm_configuration(template):
    """Test that memory alarm is properly configured"""
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {
            "AlarmName": "MonitoringLambda-Memory-Alarm",
            "AlarmDescription": "Lambda memory usage > 102MB (80% of 128MB)",
            "Threshold": 102,
            "ComparisonOperator": "GreaterThanThreshold",
            "EvaluationPeriods": 2,
            "DatapointsToAlarm": 2,
            "TreatMissingData": "notBreaching"
        }
    )

def test_memory_alarm_uses_correct_metric(template):
    """Test that memory alarm uses Lambda Insights metric"""
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {
            "AlarmName": "MonitoringLambda-Memory-Alarm",  
            "MetricName": "used_memory_max",  
            "Namespace": "LambdaInsights",  
            "Statistic": "Maximum"
        }
    )

def test_all_lambda_operational_alarms_exist(template):
    """Test that all 4 required Lambda operational alarms exist"""
    # Updated alarm names to match actual implementation
    alarm_names = [
        "MonitoringLambda-Duration-Alarm",
        "MonitoringLambda-Invocations-Alarm",
        "MonitoringLambda-Errors-Alarm",
        "MonitoringLambda-Memory-Alarm"
    ]
    
    for alarm_name in alarm_names:
        template.has_resource_properties(
            "AWS::CloudWatch::Alarm",
            {"AlarmName": alarm_name}
        )

def test_memory_alarm_threshold_appropriate(template):
    """Test that memory alarm threshold is set to reasonable value (80% of 128MB)"""
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {
            "AlarmName": "MonitoringLambda-Memory-Alarm",  # Updated name
            "Threshold": 102, 
            "ComparisonOperator": "GreaterThanThreshold"
        }
    )