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
            "AlarmName": "CanaryLambda-Memory-Alarm",
            "AlarmDescription": "Lambda memory utilization > 80%",
            "Threshold": 80,
            "ComparisonOperator": "GreaterThanThreshold",
            "EvaluationPeriods": 2,
            "DatapointsToAlarm": 2,
            "TreatMissingData": "notBreaching"
        }
    )


def test_memory_alarm_uses_correct_metric(template):
    """Test that memory alarm uses AWS/Lambda MemoryUtilization metric"""
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {
            "AlarmName": "CanaryLambda-Memory-Alarm",
            "MetricName": "MemoryUtilization",
            "Namespace": "AWS/Lambda",
            "Statistic": "Maximum"
        }
    )


def test_memory_alarm_has_sns_action(template):
    """Test that memory alarm is connected to SNS topic for notifications"""
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {
            "AlarmName": "CanaryLambda-Memory-Alarm",
            "AlarmActions": assertions.Match.array_with([
                assertions.Match.any_value()  # Should have at least one alarm action (SNS)
            ])
        }
    )


def test_all_lambda_operational_alarms_exist(template):
    """Test that all 4 required Lambda operational alarms exist"""
    # Duration alarm
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {"AlarmName": "CanaryLambda-Duration-Alarm"}
    )
    
    # Invocations alarm
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm", 
        {"AlarmName": "CanaryLambda-Invocations-Alarm"}
    )
    
    # Errors alarm
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {"AlarmName": "CanaryLambda-Errors-Alarm"}
    )
    
    # Memory alarm
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {"AlarmName": "CanaryLambda-Memory-Alarm"}
    )


def test_memory_alarm_threshold_appropriate(template):
    """Test that memory alarm threshold is set to reasonable value (80%)"""
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {
            "AlarmName": "CanaryLambda-Memory-Alarm",
            "Threshold": 80,  # 80% is appropriate threshold
            "ComparisonOperator": "GreaterThanThreshold"
        }
    )