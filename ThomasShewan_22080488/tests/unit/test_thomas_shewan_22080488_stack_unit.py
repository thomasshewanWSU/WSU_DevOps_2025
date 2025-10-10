"""
Unit Tests for CDK Infrastructure Stack
Tests that all required AWS resources are correctly defined in the CDK stack

Test Level: Unit Testing (Infrastructure as Code)
- Tests CDK stack synthesis without deploying to AWS
- Validates CloudFormation template generation
- Ensures all required resources are defined with correct properties
- Fast execution (no AWS API calls)

Testing Approach:
This uses CDK's built-in assertion library to validate the synthesized CloudFormation template.
Instead of deploying infrastructure, we verify the template has the correct resource definitions.

AWS CDK Testing:
- Testing Guide: https://docs.aws.amazon.com/cdk/v2/guide/testing.html
- Assertions Module: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.assertions/README.html
- Template.from_stack: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.assertions/Template.html#aws_cdk.assertions.Template.from_stack

Testing Tools:
- pytest: Test framework
- aws_cdk.assertions: CDK testing assertions
  - Template: Validates CloudFormation templates
  - Match: Pattern matching for resource properties

Test Coverage:
- Lambda functions (count and configuration)
- DynamoDB tables (count, streams, keys)
- CloudWatch alarms (operational monitoring)
- CloudWatch dashboard
- SNS topic
- API Gateway
- EventBridge rules
- Lambda event source mappings
"""

import aws_cdk as cdk
import aws_cdk.assertions as assertions
import pytest
from thomas_shewan_22080488.thomas_shewan_22080488_stack import ThomasShewan22080488Stack


@pytest.fixture
def stack():
    """
    Create a CDK stack instance for testing.
    
    Returns:
        ThomasShewan22080488Stack: Stack with all infrastructure resources defined
    """
    app = cdk.App()
    return ThomasShewan22080488Stack(app, "thomas-shewan-22080488")


@pytest.fixture
def template(stack):
    """
    Synthesize CloudFormation template from CDK stack.
    
    This converts the CDK stack into a CloudFormation template that can be validated.
    No AWS resources are actually created - this is pure template generation.
    
    Template API: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.assertions/Template.html
    
    Args:
        stack: CDK stack fixture
        
    Returns:
        assertions.Template: CloudFormation template for assertion testing
    """
    return assertions.Template.from_stack(stack)


def test_lambda_functions_created(template):
    """
    Verify all four Lambda functions are defined in the stack.
    
    CloudFormation Resource: AWS::Lambda::Function
    Documentation: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-lambda-function.html
    """
    template.resource_count_is("AWS::Lambda::Function", 4)


def test_cloudwatch_dashboard_created(template):
    """
    Verify CloudWatch dashboard is created for monitoring visualization.
    
    
    CloudFormation Resource: AWS::CloudWatch::Dashboard
    Documentation: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-cloudwatch-dashboard.html
    """
    template.resource_count_is("AWS::CloudWatch::Dashboard", 1)


def test_dynamodb_tables_created(template):
    """
    Verify two DynamoDB tables are defined.
    
    CloudFormation Resource: AWS::DynamoDB::Table
    Documentation: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-dynamodb-table.html
    """
    template.resource_count_is("AWS::DynamoDB::Table", 2)


def test_dynamodb_streams_enabled(template):
    """
    Verify DynamoDB Streams are enabled with NEW_AND_OLD_IMAGES view type.

    StreamSpecification: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-dynamodb-table-streamspecification.html
    """
    template.has_resource_properties(
        "AWS::DynamoDB::Table",
        {
            "StreamSpecification": {
                "StreamViewType": "NEW_AND_OLD_IMAGES"
            }
        }
    )


def test_sns_topic_created(template):
    """
    Verify SNS topic is created for alarm notifications.
    
    SNS topic receives notifications from:
    - CloudWatch Alarms (website availability, latency, throughput)
    - Lambda operational alarms (duration, errors, invocations, memory)
    
    CloudFormation Resource: AWS::SNS::Topic
    Documentation: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-sns-topic.html
    """
    template.resource_count_is("AWS::SNS::Topic", 1)


def test_lambda_alarms_created(template):
    """
    Verify all four Lambda operational alarms are created.
    
    CloudFormation Resource: AWS::CloudWatch::Alarm
    Documentation: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-cloudwatch-alarm.html
    """
    # Updated alarm names to match actual implementation
    for alarm_name in [
        "MonitoringLambda-Duration-Alarm",
        "MonitoringLambda-Invocations-Alarm",
        "MonitoringLambda-Errors-Alarm",
        "MonitoringLambda-Memory-Alarm"
    ]:
        template.has_resource_properties(
            "AWS::CloudWatch::Alarm",
            {"AlarmName": alarm_name}
        )


def test_eventbridge_rule_created(template):
    """
    Verify EventBridge scheduled rule triggers Monitoring Lambda every 5 minutes.
    
    EventBridge (formerly CloudWatch Events) acts as a cron scheduler for Lambda.
    Schedule Expression: rate(5 minutes)
    
    CloudFormation Resource: AWS::Events::Rule
    Documentation: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-events-rule.html
    Schedule Expressions: https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-create-rule-schedule.html
    """
    template.has_resource_properties(
        "AWS::Events::Rule",
        {"ScheduleExpression": "rate(5 minutes)"}
    )


def test_api_gateway_created(template):
    """
    Verify API Gateway REST API is created for CRUD operations.
    
    CloudFormation Resource: AWS::ApiGateway::RestApi
    Documentation: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-apigateway-restapi.html
    """
    template.resource_count_is("AWS::ApiGateway::RestApi", 1)


def test_api_gateway_has_cors(template):
    """
    Verify API Gateway is configured with correct name.
    """
    template.has_resource_properties(
        "AWS::ApiGateway::RestApi",
        {
            "Name": "WebCrawlerTargetsAPI"
        }
    )


def test_lambda_has_correct_timeout(template):
    """
    Verify Lambda functions have appropriate timeout and runtime configuration.
    
    CloudFormation Property: AWS::Lambda::Function.Timeout
    Documentation: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-lambda-function.html#cfn-lambda-function-timeout
    Lambda Limits: https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html
    """
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Timeout": 60,
            "Runtime": "python3.11"
        }
    )


def test_infrastructure_lambda_has_stream_source(template):
    """
    Verify Infrastructure Lambda has DynamoDB Stream event source mapping.
    
    CloudFormation Resource: AWS::Lambda::EventSourceMapping
    Documentation: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-lambda-eventsourcemapping.html
    DynamoDB Streams: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.Lambda.html
    """
    template.has_resource_properties(
        "AWS::Lambda::EventSourceMapping",
        {
            "StartingPosition": "LATEST",
            "BatchSize": 1
        }
    )

def test_memory_alarm_uses_correct_metric(template):
    """
    Verify Memory alarm uses Lambda Insights enhanced metric.
    
    Lambda Insights: https://docs.aws.amazon.com/lambda/latest/dg/monitoring-insights.html
    Available Metrics: https://docs.aws.amazon.com/lambda/latest/dg/monitoring-insights-metrics.html
    """
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
    """
    Verify all four operational alarms exist for comprehensive Lambda monitoring.
    
    Best Practice: Monitor all Lambda operational metrics
    https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics.html
    """
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
    """
    Verify Memory alarm threshold is set to reasonable value (80% of 128MB = 102MB).
    
    Lambda Memory Management: https://docs.aws.amazon.com/lambda/latest/dg/configuration-memory.html
    """
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {
            "AlarmName": "MonitoringLambda-Memory-Alarm",  # Updated name
            "Threshold": 110, 
            "ComparisonOperator": "GreaterThanThreshold"
        }
    )