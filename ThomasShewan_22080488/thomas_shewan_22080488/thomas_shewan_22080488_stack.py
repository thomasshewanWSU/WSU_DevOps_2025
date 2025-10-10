"""
Web Monitoring Application Stack
Defines infrastructure for website health monitoring with CRUD API

AWS Services Used:
- AWS Lambda: Serverless compute for monitoring and API operations
  Documentation: https://docs.aws.amazon.com/lambda/latest/dg/welcome.html
- Amazon API Gateway: RESTful API for managing monitoring targets
  Documentation: https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html
- Amazon DynamoDB: NoSQL database for target storage and alarm logs
  Documentation: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html
- Amazon CloudWatch: Metrics, alarms, and dashboards for monitoring
  Documentation: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html
- Amazon EventBridge: Scheduled Lambda invocations
  Documentation: https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-what-is.html
- Amazon SNS: Alarm notification distribution
  Documentation: https://docs.aws.amazon.com/sns/latest/dg/welcome.html

Architecture Overview:
1. API Gateway + CRUD Lambda: Manage monitoring targets in DynamoDB
2. DynamoDB Streams + Infrastructure Lambda: Auto-create CloudWatch alarms
3. EventBridge + Monitoring Lambda: Periodic health checks (every 5 minutes)
4. CloudWatch: Store metrics, trigger alarms, display dashboards
5. SNS + Alarm Logger Lambda: Distribute and log alarm notifications
"""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_lambda as lambda_,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_dynamodb as dynamodb,
    aws_cloudwatch_actions as cloudwatch_actions,
    aws_logs as logs,
    aws_apigateway as apigateway,
    aws_lambda_event_sources as lambda_event_sources
)
from constructs import Construct
from modules.constants import (
    METRIC_NAMESPACE,
    METRIC_AVAILABILITY,
    METRIC_LATENCY,
    METRIC_THROUGHPUT,
    DIM_WEBSITE,
)


class ThomasShewan22080488Stack(Stack):
    """
    Main application stack containing all monitoring infrastructure.
    
    This stack is deployed to multiple stages (alpha, prod) via the CI/CD pipeline.
    The stage_name parameter ensures resource names are unique per environment.
    """
    
    def __init__(self, scope: Construct, construct_id: str, stage_name: str = "prod", **kwargs) -> None:
        """
        Initialize the web monitoring stack.
        """
        super().__init__(scope, construct_id, **kwargs)
        
        # RESOURCE NAMING: Stage-specific prefixes prevent conflicts - for alpha/prod stages
        stage_prefix = f"{stage_name}-" if stage_name != "prod" else ""
        
        # ========================================================================
        # DYNAMODB TABLE: Web Monitoring Targets Storage
        # ========================================================================
        # Stores website monitoring targets (name, URL, enabled status)
        # DynamoDB Table documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_dynamodb/Table.html
        
        targets_table = dynamodb.Table(
            self, "WebTargetsTable",
            # Partition key uniquely identifies each target
            # Attribute documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_dynamodb/Attribute.html
            partition_key=dynamodb.Attribute(
                name="TargetId",
                # String type for UUID-based identifiers
                # AttributeType documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_dynamodb/AttributeType.html
                type=dynamodb.AttributeType.STRING
            ),
            # Automatically delete table when stack is destroyed (dev/test only)
            # RemovalPolicy documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk/RemovalPolicy.html
            removal_policy=RemovalPolicy.DESTROY,
            table_name=f"{stage_prefix}WebMonitoringTargets",
            # DynamoDB Streams capture item changes for Infrastructure Lambda triggers
            # StreamViewType documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_dynamodb/StreamViewType.html
            # NEW_AND_OLD_IMAGES provides both before and after states for updates
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES
        )

        # IAM ROLE: API Gateway CloudWatch Logging
        # Allows API Gateway to write access logs to CloudWatch Logs
        # Role documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_iam/Role.html
        api_log_role = iam.Role(
            self, "ApiGatewayCloudWatchLogsRole",
            # Service principal documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_iam/ServicePrincipal.html
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
            # Managed policy for API Gateway logging
            # ManagedPolicy documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_iam/ManagedPolicy.html
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonAPIGatewayPushToCloudWatchLogs"
                )
            ]
        )
        
        # Configure account-level API Gateway logging settings
        # CfnAccount documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_apigateway/CfnAccount.html
        apigateway.CfnAccount(
            self, "ApiGatewayAccount",
            cloud_watch_role_arn=api_log_role.role_arn
        )
        # ========================================================================
        # LAMBDA FUNCTION: CRUD API Handler
        # ========================================================================
        # Handles HTTP requests from API Gateway to manage monitoring targets
        # Supports: GET (list/read), POST (create), PUT (update), DELETE operations
        # Lambda Function documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_lambda/Function.html
        
        crud_lambda = lambda_.Function(
            self, "CrudLambda",
            # Python 3.11 runtime environment
            # Runtime documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_lambda/Runtime.html
            runtime=lambda_.Runtime.PYTHON_3_11,
            # Handler format: filename.function_name
            # Handler documentation: https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html
            handler="CRUDLambda.lambda_handler",
            # Load code from local modules directory
            # Code.from_asset documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_lambda/Code.html#aws_cdk.aws_lambda.Code.from_asset
            code=lambda_.Code.from_asset("./modules"),
            # 30 second timeout for database operations
            # Duration documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk/Duration.html
            timeout=Duration.seconds(30),
            function_name=f"{stage_prefix}WebMonitoringCRUD",
            description=f"[{stage_name.upper()}] CRUD operations for web monitoring targets",
            # Environment variables passed to Lambda function
            # Environment variables documentation: https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html
            environment={
                "TARGETS_TABLE_NAME": targets_table.table_name
            }
        )

        # IAM PERMISSIONS: Grant DynamoDB read/write access
        # grant_read_write_data documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_dynamodb/Table.html#aws_cdk.aws_dynamodb.Table.grant_read_write_data
        targets_table.grant_read_write_data(crud_lambda)

        # ========================================================================
        # API GATEWAY: RESTful API for Target Management
        # ========================================================================
        # Provides HTTP endpoints for creating, reading, updating, and deleting targets
        # RestApi documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_apigateway/RestApi.html
        
        api = apigateway.RestApi(
            self, "TargetsApi",
            rest_api_name=f"{stage_prefix}WebCrawlerTargetsAPI",
            description=f"[{stage_name.upper()}] CRUD API for managing web monitoring targets",
            # Deployment options for the API stage
            # StageOptions documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_apigateway/StageOptions.html
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                # Enable CloudWatch metrics for API monitoring
                metrics_enabled=True,
                # Log all requests at INFO level
                # MethodLoggingLevel documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_apigateway/MethodLoggingLevel.html
                logging_level=apigateway.MethodLoggingLevel.INFO,
                # Log request/response data for debugging
                data_trace_enabled=True,
                # Enable AWS X-Ray tracing for performance analysis
                # X-Ray documentation: https://docs.aws.amazon.com/xray/latest/devguide/xray-services-apigateway.html
                tracing_enabled=True,
            ),
            # CORS configuration for cross-origin requests
            # CorsOptions documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_apigateway/CorsOptions.html
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS
            )
        )

        
        # LAMBDA INTEGRATION: Connect API Gateway to CRUD Lambda
        # LambdaIntegration documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_apigateway/LambdaIntegration.html
        # Proxy integration guide: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
        crud_integration = apigateway.LambdaIntegration(crud_lambda, proxy=True)

        # API ROUTES: Define RESTful endpoints
        # Resource documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_apigateway/Resource.html
        
        # /targets - Collection operations
        targets_resource = api.root.add_resource("targets")
        targets_resource.add_method("GET", crud_integration)    # List all targets
        targets_resource.add_method("POST", crud_integration)   # Create new target

        # /targets/{id} - Individual target operations
        # {id} is a path parameter that gets passed to the Lambda function
        # Path parameters guide: https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-method-settings-method-request.html
        target_resource = targets_resource.add_resource("{id}")
        target_resource.add_method("GET", crud_integration)     # Get single target
        target_resource.add_method("PUT", crud_integration)     # Update target
        target_resource.add_method("DELETE", crud_integration)  # Delete target

        
        # ========================================================================
        # CLOUDFORMATION OUTPUTS: Export Stack Values
        # ========================================================================
        # Outputs make stack values available for testing and cross-stack references
        # CfnOutput documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk/CfnOutput.html
        
        # Export API Gateway URL for integration testing
        CfnOutput(
            self, "ApiUrl",
            # API Gateway URL is auto-generated during deployment
            # RestApi.url documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_apigateway/RestApi.html#aws_cdk.aws_apigateway.RestApi.url
            value=api.url,
            description=f"[{stage_name.upper()}] API Gateway URL for CRUD operations",
            # Export name enables cross-stack references in CloudFormation
            # Exports guide: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-exports.html
            export_name=f"{stage_prefix}WebCrawlerApiUrl"
        )
        
        # Export DynamoDB table name for testing and debugging
        CfnOutput(
            self, "TargetsTableName",
            value=targets_table.table_name,
            description=f"[{stage_name.upper()}] DynamoDB table name for targets",
            export_name=f"{stage_prefix}TargetsTableName"
        )


        # ========================================================================
        # LAMBDA FUNCTION: Website Health Monitoring
        # ========================================================================
        # Periodically checks website availability and performance
        # Triggered every 5 minutes by EventBridge (configured later)
        # Lambda Function documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_lambda/Function.html
        
        canary_lambda = lambda_.Function(
            self, "MonitoringLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="MonitoringLambda.lambda_handler",
            code=lambda_.Code.from_asset("./modules"),
            # 60 second timeout for multiple HTTP requests
            timeout=Duration.seconds(60),
            function_name=f"{stage_prefix}WebMonitoring",
            description=f"[{stage_name.upper()}] Web health monitoring - checks multiple websites",
            environment={
                # Pass DynamoDB table name to Lambda for reading targets
                "TARGETS_TABLE_NAME": targets_table.table_name
            },
            # Lambda Insights provides enhanced monitoring metrics - used for memory
            # LambdaInsightsVersion documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_lambda/LambdaInsightsVersion.html
            # Lambda Insights guide: https://docs.aws.amazon.com/lambda/latest/dg/monitoring-insights.html
            insights_version=lambda_.LambdaInsightsVersion.VERSION_1_0_229_0
        )
        
        # IAM PERMISSIONS: Allow Lambda to publish custom metrics to CloudWatch
        # PolicyStatement documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_iam/PolicyStatement.html
        canary_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                # PutMetricData API: https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutMetricData.html
                actions=["cloudwatch:PutMetricData"],
                # CloudWatch metrics are not resource-specific
                resources=["*"]
            )
        )

        # IAM PERMISSIONS: Allow Lambda to read monitoring targets from DynamoDB
        # grant_read_data documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_dynamodb/Table.html#aws_cdk.aws_dynamodb.Table.grant_read_data
        targets_table.grant_read_data(canary_lambda)

        # ========================================================================
        # LAMBDA VERSIONING: Enable Safe Deployments
        # ========================================================================
        # Lambda versions and aliases enable gradual traffic shifting and rollback
        # Versions documentation: https://docs.aws.amazon.com/lambda/latest/dg/configuration-versions.html
        # Aliases documentation: https://docs.aws.amazon.com/lambda/latest/dg/configuration-aliases.html
        
        # Create immutable version of the Lambda function
        # Version documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_lambda/Version.html
        lambda_version = canary_lambda.current_version
        
        # Create mutable alias pointing to the current version
        # Alias allows routing traffic between versions during deployments
        # Alias documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_lambda/Alias.html
        prod_alias = lambda_.Alias(
            self, "ProdAlias",
            alias_name="prod",
            version=lambda_version,
            description="Production alias for safe deployments"
        )
        
        # Note: EventBridge will invoke the alias (not the function directly)
        # This allows CodeDeploy to gradually shift traffic during updates
        # Traffic shifting guide: https://docs.aws.amazon.com/lambda/latest/dg/lambda-traffic-shifting-using-aliases.html

        # ========================================================================
        # SNS TOPIC: CloudWatch Alarm Notifications
        # ========================================================================
        # Distributes alarm notifications to multiple subscribers (email, Lambda, etc.)
        # SNS Topic documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_sns/Topic.html
        # SNS guide: https://docs.aws.amazon.com/sns/latest/dg/welcome.html
        
        alarm_topic = sns.Topic(
            self, "AlarmNotificationTopic",
            topic_name=f"{stage_prefix}WebMonitoringAlarms",
            display_name=f"[{stage_name.upper()}] Web Monitoring Alarm Notifications"
        )

        # ========================================================================
        # DYNAMODB TABLE: Alarm History Storage
        # ========================================================================
        # Stores audit trail of all alarm state changes
        # Composite key (AlarmName + Timestamp) allows querying alarm history
        
        alarm_log_table = dynamodb.Table(
            self, "AlarmLogTable",
            # Partition key groups alarms by name
            partition_key=dynamodb.Attribute(
                name="AlarmName",
                type=dynamodb.AttributeType.STRING
            ),
            # Sort key orders events chronologically
            # Sort key documentation: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.CoreComponents.html#HowItWorks.CoreComponents.PrimaryKey
            sort_key=dynamodb.Attribute(
                name="Timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            table_name=f"{stage_prefix}AlarmLog",
            removal_policy=RemovalPolicy.DESTROY
        )

        # ========================================================================
        # LAMBDA FUNCTION: Alarm Logger
        # ========================================================================
        # Subscribes to SNS topic and persists alarm events to DynamoDB
        
        alarm_logger_lambda = lambda_.Function(
            self, "AlarmLoggerLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="AlarmLambda.lambda_handler",
            code=lambda_.Code.from_asset("./modules"),
            function_name=f"{stage_prefix}AlarmLogger",
            environment={
                "ALARM_LOG_TABLE": alarm_log_table.table_name
            },
            timeout=Duration.seconds(30),
            description=f"[{stage_name.upper()}] Logs alarm notifications to DynamoDB"
        )

        # IAM PERMISSIONS: Allow Lambda to write alarm history
        alarm_log_table.grant_write_data(alarm_logger_lambda)

        # SNS SUBSCRIPTION: Connect alarm logger Lambda to SNS topic
        # When CloudWatch publishes to SNS, SNS invokes this Lambda
        # LambdaSubscription documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_sns_subscriptions/LambdaSubscription.html
        alarm_topic.add_subscription(
            subscriptions.LambdaSubscription(alarm_logger_lambda)
        )

        # SNS SUBSCRIPTION: Email notifications for alarm events
        # User must confirm subscription via email
        # EmailSubscription documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_sns_subscriptions/EmailSubscription.html
        alarm_topic.add_subscription(
            subscriptions.EmailSubscription("22080488@student.westernsydney.edu.au")
        )
        
        # ========================================================================
        # LAMBDA FUNCTION: Infrastructure Manager
        # ========================================================================
        # Automatically creates/updates/deletes CloudWatch alarms when targets change
        # Triggered by DynamoDB Streams when CRUD API modifies the targets table
        # This implements Infrastructure as Code for monitoring resources
        # DynamoDB Streams guide: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.Lambda.html
        
        infra_lambda = lambda_.Function(
            self, "InfrastructureLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="InfrastructureLambda.lambda_handler",
            code=lambda_.Code.from_asset("./modules"),
            timeout=Duration.seconds(60),
            function_name=f"{stage_prefix}InfrastructureManager",
            description=f"[{stage_name.upper()}] Manages CloudWatch alarms and dashboard dynamically",
            environment={
                # SNS topic ARN for alarm actions
                "ALARM_TOPIC_ARN": alarm_topic.topic_arn,
                # Dashboard name for widget management
                "DASHBOARD_NAME": f"{stage_prefix}WebsiteHealthMonitoring",
                # Region needed for dashboard widget configuration
                "DASHBOARD_REGION": self.region
            }
        )
        
        # IAM PERMISSIONS: Allow Lambda to manage CloudWatch resources
        # This Lambda creates/deletes alarms and updates dashboards programmatically
        infra_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    # Publish custom metrics
                    "cloudwatch:PutMetricData",
                    # Create and configure alarms
                    # PutMetricAlarm API: https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutMetricAlarm.html
                    "cloudwatch:PutMetricAlarm",
                    # Delete alarms when targets are removed
                    # DeleteAlarms API: https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_DeleteAlarms.html
                    "cloudwatch:DeleteAlarms",
                    # Query existing alarms
                    "cloudwatch:DescribeAlarms",
                    # Read dashboard configuration
                    # GetDashboard API: https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_GetDashboard.html
                    "cloudwatch:GetDashboard",
                    # Update dashboard widgets
                    # PutDashboard API: https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutDashboard.html
                    "cloudwatch:PutDashboard"
                ],
                resources=["*"]
            )
        )
        
        # DYNAMODB STREAM EVENT SOURCE: Trigger Lambda on table changes
        # Processes INSERT, MODIFY, and REMOVE events from DynamoDB
        # DynamoEventSource documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_lambda_event_sources/DynamoEventSource.html
        infra_lambda.add_event_source(
            lambda_event_sources.DynamoEventSource(
                targets_table,
                # Only process new records (not historical data)
                # StartingPosition documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_lambda/StartingPosition.html
                starting_position=lambda_.StartingPosition.LATEST,
                # Process one record at a time for immediate response
                batch_size=1,
                # Retry failed records 3 times before sending to DLQ
                retry_attempts=3
            )
        )
        
        # ========================================================================
        # CLOUDWATCH DASHBOARD: Monitoring Visualization
        # ========================================================================
        # Central dashboard displaying all website health metrics and Lambda performance
        # Infrastructure Lambda will dynamically add/remove website widgets
        # Dashboard documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_cloudwatch/Dashboard.html
        # Dashboard guide: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Dashboards.html
        
        dashboard = cloudwatch.Dashboard(
            self, "WebHealthDashboard",
            dashboard_name=f"{stage_prefix}WebsiteHealthMonitoring"
        )

        # ========================================================================
        # CLOUDWATCH ALARMS: Lambda Operational Monitoring
        # ========================================================================
        # These alarms monitor the health of the monitoring Lambda itself
        # Helps detect issues with the monitoring infrastructure before they impact users
        # Alarm documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_cloudwatch/Alarm.html
        # Lambda metrics guide: https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics.html
        
        # DURATION ALARM: Lambda Execution Time
        # Monitors how long the Lambda takes to execute
        # Long duration may indicate network issues or too many targets to monitor
        # metric_duration documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_lambda/IFunction.html#aws_cdk.aws_lambda.IFunction.metric_duration
        duration_metric = prod_alias.metric_duration(
            statistic="Average",
            period=Duration.minutes(5)
        )
        duration_alarm = cloudwatch.Alarm(
            self, "CanaryLambdaDurationAlarm",
            alarm_name=f"{stage_prefix}MonitoringLambda-Duration-Alarm",
            alarm_description=f"[{stage_name.upper()}] Lambda execution time exceeds 30 seconds",
            metric=duration_metric,
            # Alert if average duration exceeds 30 seconds (50% of 60s timeout)
            threshold=30000,  # milliseconds
            evaluation_periods=1,
            datapoints_to_alarm=1,
            # ComparisonOperator documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_cloudwatch/ComparisonOperator.html
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            # TreatMissingData documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_cloudwatch/TreatMissingData.html
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        # Send notification to SNS when alarm triggers
        # SnsAction documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_cloudwatch_actions/SnsAction.html
        duration_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarm_topic))

        # INVOCATIONS ALARM: Lambda Execution Frequency
        # Monitors how often the Lambda is invoked
        # Unexpected spike may indicate event source misconfiguration
        # metric_invocations documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_lambda/IFunction.html#aws_cdk.aws_lambda.IFunction.metric_invocations
        invocations_metric = prod_alias.metric_invocations(
            statistic="Sum",
            period=Duration.minutes(5)
        )
        invocations_alarm = cloudwatch.Alarm(
            self, "CanaryLambdaInvocationsAlarm",
            alarm_name=f"{stage_prefix}MonitoringLambda-Invocations-Alarm",
            alarm_description=f"[{stage_name.upper()}] Lambda invoked more than 100 times in 5 minutes",
            metric=invocations_metric,
            # Alert if invoked more than 100 times (expected: ~1 per 5 minutes)
            threshold=100,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        invocations_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarm_topic))

        # ERRORS ALARM: Lambda Execution Failures
        # Monitors Lambda function errors (unhandled exceptions, timeouts, etc.)
        # metric_errors documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_lambda/IFunction.html#aws_cdk.aws_lambda.IFunction.metric_errors
        errors_metric = prod_alias.metric_errors(
            statistic="Sum",
            period=Duration.minutes(5)
        )
        errors_alarm = cloudwatch.Alarm(
            self, "CanaryLambdaErrorsAlarm",
            alarm_name=f"{stage_prefix}MonitoringLambda-Errors-Alarm",
            alarm_description=f"[{stage_name.upper()}] Lambda function errors detected",
            metric=errors_metric,
            # Alert on any errors (monitoring should be highly reliable)
            threshold=0,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        errors_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarm_topic))

        # MEMORY ALARM: Lambda Memory Utilization
        # Monitors Lambda memory usage to detect memory leaks or insufficient allocation
        # Memory usage is tracked via Lambda Insights (enabled on the function)
        # Lambda Insights guide: https://docs.aws.amazon.com/lambda/latest/dg/monitoring-insights.html
        
        # Get Lambda log group for metric extraction
        # LogGroup documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_logs/LogGroup.html
        # Lambda automatically creates log groups at /aws/lambda/{function-name}
        log_group = logs.LogGroup.from_log_group_name(
            self, "MonitoringLambdaLogGroup",
            log_group_name=f"/aws/lambda/{canary_lambda.function_name}"
        )
        
        # Lambda Insights publishes memory metrics to LambdaInsights namespace
        # This metric shows the maximum memory used during each invocation
        # Metric documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_cloudwatch/Metric.html
        max_memory_used_metric = cloudwatch.Metric(
            # Lambda Insights metrics namespace
            namespace="LambdaInsights",
            # Maximum memory used in MB
            metric_name="used_memory_max",
            # Filter by function name dimension
            dimensions_map={"function_name": canary_lambda.function_name},
            # Maximum statistic shows peak memory usage
            statistic="Maximum",
            period=Duration.minutes(5)
        )
        
        # Alert if memory usage exceeds 80% ish of allocated memory
        # Memory configuration guide: https://docs.aws.amazon.com/lambda/latest/dg/configuration-memory.html
        memory_alarm = cloudwatch.Alarm(
            self, "CanaryLambdaMemoryAlarm",
            alarm_name=f"{stage_prefix}MonitoringLambda-Memory-Alarm",
            alarm_description=f"[{stage_name.upper()}] Lambda memory usage exceeds 80% threshold",
            metric=max_memory_used_metric,
            threshold=110,
            # Require 2 consecutive breaches to reduce false positives
            evaluation_periods=2,
            datapoints_to_alarm=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        memory_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarm_topic))

        # DASHBOARD WIDGETS: Lambda Operational Metrics
        # Add widgets displaying Lambda health metrics to the dashboard
        # GraphWidget documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_cloudwatch/GraphWidget.html
        dashboard.add_widgets(
            # Duration widget shows Lambda execution time trend
            cloudwatch.GraphWidget(
                title="Monitoring Lambda Duration (ms)",
                left=[duration_metric],
                width=6,  # Each unit is 1/24th of dashboard width
                height=4  # Each unit is 1/24th of dashboard height
            ),
            # Invocations widget shows how often Lambda runs
            cloudwatch.GraphWidget(
                title="Monitoring Lambda Invocations",
                left=[invocations_metric],
                width=6,
                height=4
            ),
            # Errors widget shows function failures
            cloudwatch.GraphWidget(
                title="Monitoring Lambda Errors",
                left=[errors_metric],
                width=6,
                height=4
            ),
            # Memory widget shows resource utilization
            cloudwatch.GraphWidget(
                title="Monitoring Lambda Memory (MB)",
                left=[max_memory_used_metric],
                width=6,
                height=4
            )
        )

        # ========================================================================
        # AWS CODEDEPLOY: Gradual Lambda Deployment (COMMENTED OUT - NOT FREE TIER)
        # ========================================================================
        # CodeDeploy enables safe Lambda deployments with gradual traffic shifting

        # CodeDeploy documentation: https://docs.aws.amazon.com/codedeploy/latest/userguide/welcome.html
        # Lambda deployment guide: https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-steps-lambda.html
        
        # # Create CodeDeploy application for Lambda deployments
        # # LambdaApplication documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_codedeploy/LambdaApplication.html
        # application = codedeploy.LambdaApplication(
        #     self, "CanaryDeploymentApplication",
        #     application_name="WebMonitoringCanaryApp"
        # )
        
        # # Create deployment group with canary strategy
        # # LambdaDeploymentGroup documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_codedeploy/LambdaDeploymentGroup.html
        # deployment_group = codedeploy.LambdaDeploymentGroup(
        #     self, "CanaryDeploymentGroup",
        #     application=application,
        #     # Use the prod alias for traffic shifting
        #     alias=prod_alias,
        #     # Canary deployment: 10% traffic to new version, wait 5 minutes, then 100%
        #     # LambdaDeploymentConfig documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_codedeploy/LambdaDeploymentConfig.html
        #     deployment_config=codedeploy.LambdaDeploymentConfig.CANARY_10_PERCENT_5_MINUTES,
        #     # Monitor these alarms during deployment
        #     alarms=[
        #         duration_alarm,
        #         invocations_alarm,
        #         errors_alarm,
        #     ],
        #     # Automatic rollback configuration
        #     # AutoRollbackConfig documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_codedeploy/AutoRollbackConfig.html
        #     auto_rollback=codedeploy.AutoRollbackConfig(
        #         # Rollback on deployment failure (e.g., new version throws errors)
        #         failed_deployment=True,
        #         # Rollback if deployment is manually stopped
        #         stopped_deployment=True,
        #         # Rollback if any CloudWatch alarm triggers during deployment
        #         deployment_in_alarm=True
        #     ),
        #     deployment_group_name="WebMonitoringCanaryDeploymentGroup"
        # )

        # ========================================================================
        # AMAZON EVENTBRIDGE: Scheduled Lambda Invocation
        # ========================================================================
        # EventBridge (formerly CloudWatch Events) triggers the monitoring Lambda periodically
        # Acts as a serverless cron job to run health checks every 5 minutes
        # EventBridge guide: https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-what-is.html
        # Rule documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_events/Rule.html
        
        monitoring_rule = events.Rule(
            self, "MonitoringScheduleRule",
            rule_name=f"{stage_prefix}WebMonitoringSchedule",
            # Schedule expression using rate syntax
            # Schedule documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_events/Schedule.html
            # Rate expressions: https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-create-rule-schedule.html#eb-rate-expressions
            schedule=events.Schedule.rate(Duration.minutes(5)),
            description=f"[{stage_name.upper()}] Trigger web monitoring every 5 minutes"
        )
        
        # Configure Lambda as the target for this rule
        # EventBridge invokes the prod alias (not the function directly)
        # This allows CodeDeploy to manage traffic during deployments
        # LambdaFunction target documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_events_targets/LambdaFunction.html
        monitoring_rule.add_target(
            targets.LambdaFunction(prod_alias)
        )

        # ========================================================================
        # DASHBOARD WIDGETS: Website Health Metrics
        # ========================================================================
        # These widgets display aggregate metrics for all monitored websites
        # Infrastructure Lambda dynamically adds/removes website metrics as targets change
        # Initial dummy metrics are replaced when first website is added via CRUD API
        # GraphWidget documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_cloudwatch/GraphWidget.html
        
        # Create placeholder metric for initial dashboard state
        # Uses non-existent dimension value so no data is displayed until real sites are added
        dummy_metric = cloudwatch.Metric(
            namespace=METRIC_NAMESPACE,
            metric_name=METRIC_AVAILABILITY,
            dimensions_map={DIM_WEBSITE: "__placeholder__"},
            statistic="Average",
            period=Duration.minutes(5),
            label="No websites configured yet"
        )
        
        dashboard.add_widgets(
            # AVAILABILITY WIDGET: Website Uptime Status
            # Shows binary availability (1 = up, 0 = down) for all monitored websites
            # Each website appears as a separate line on the graph
            cloudwatch.GraphWidget(
                title="Website Availability (All Sites)",
                # Infrastructure Lambda replaces dummy metric with real website metrics
                left=[dummy_metric],
                width=24,  # Full dashboard width for visibility
                height=6,
                # Y-axis configuration
                # YAxisProps documentation: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_cloudwatch/YAxisProps.html
                left_y_axis=cloudwatch.YAxisProps(
                    min=0,    # 0 = website down
                    max=1.1   # 1 = website up (1.1 adds padding)
                )
            ),

            # LATENCY WIDGET: Website Response Time
            # Shows HTTP response time in milliseconds for all monitored websites
            # Helps identify performance degradation across sites
            cloudwatch.GraphWidget(
                title="Response Time - All Websites (ms)",
                left=[cloudwatch.Metric(
                    namespace=METRIC_NAMESPACE,
                    metric_name=METRIC_LATENCY,
                    dimensions_map={DIM_WEBSITE: "__placeholder__"},
                    statistic="Average",
                    period=Duration.minutes(5),
                    label="No websites configured yet"
                )],
                width=12,  # Half dashboard width
                height=6,
                left_y_axis=cloudwatch.YAxisProps(
                    min=0  # Response time starts at 0ms
                )
            ),

            # THROUGHPUT WIDGET: Data Transfer Rate
            # Shows bytes per second transferred from each website
            # Helps monitor bandwidth usage and detect unusually large/small responses
            cloudwatch.GraphWidget(
                title="Throughput - All Websites (bytes/s)",
                left=[cloudwatch.Metric(
                    namespace=METRIC_NAMESPACE,
                    metric_name=METRIC_THROUGHPUT,
                    dimensions_map={DIM_WEBSITE: "__placeholder__"},
                    statistic="Average",
                    period=Duration.minutes(5),
                    label="No websites configured yet"
                )],
                width=12,  # Half dashboard width
                height=6,
                left_y_axis=cloudwatch.YAxisProps(
                    min=0  # Throughput starts at 0 bytes/s
                )
            )
        )
