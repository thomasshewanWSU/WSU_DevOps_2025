import json
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_lambda as lambda_,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_dynamodb as dynamodb,
    aws_cloudwatch_actions as cloudwatch_actions,
)
from constructs import Construct

from modules.constants import (
    METRIC_NAMESPACE,
    METRIC_AVAILABILITY,
    METRIC_LATENCY,
    METRIC_THROUGHPUT,
    DIM_WEBSITE,
    DEFAULT_WEBSITES,
    ENV_WEBSITES,
)

class ThomasShewan22080488Stack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Web Monitoring Lambda Function------------------------
        # Create the main Lambda function that performs health checks on websites
        # This function runs every 5 minutes and publishes metrics to CloudWatch
        
        canary_lambda = lambda_.Function(
            self, "MonitoringLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="MonitoringLambda.lambda_handler",
            code=lambda_.Code.from_asset("./modules"),
            timeout=Duration.seconds(60), 
            description="Web health monitoring canary - crawls multiple websites",
            environment={
                ENV_WEBSITES: json.dumps(DEFAULT_WEBSITES)
            }
        )
        
        # Grant CloudWatch permissions so Lambda can publish custom metrics
        canary_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cloudwatch:PutMetricData"
                ],
                resources=["*"]
            )
        )

        # Lambda Versioning & Alias Setup------------------------
        # Create a version and alias to enable gradual deployments with rollback
        # Create a new version of the Lambda on each deployment
        lambda_version = canary_lambda.current_version
        
        # Create a "prod" alias that points to the current version
        # This alias will be used by EventBridge and allows safe deployments
        prod_alias = lambda_.Alias(
            self, "ProdAlias",
            alias_name="prod",
            version=lambda_version,
            description="Production alias for gradual deployments"
        )

        # Alarm Notification Setup--------------------------
        # Configure SNS topic for alarm notifications and DynamoDB for logging
    
        # Create SNS topic to send alarm notifications
        alarm_topic = sns.Topic(
            self, "AlarmNotificationTopic",
            display_name="Web Monitoring Alarm Notifications"
        )

        # Create DynamoDB table to store alarm history
        alarm_log_table = dynamodb.Table(
            self, "AlarmLogTable",
            partition_key=dynamodb.Attribute(
                name="AlarmName",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="Timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY  # For dev/demo only
        )

        # Create Lambda function to process alarm notifications and log them
        alarm_logger_lambda = lambda_.Function(
            self, "AlarmLoggerLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="AlarmLambda.lambda_handler",
            code=lambda_.Code.from_asset("./modules"),
            environment={
                "ALARM_LOG_TABLE": alarm_log_table.table_name
            },
            timeout=Duration.seconds(30),
            description="Logs alarm notifications to DynamoDB"
        )

        # Grant write permissions to the alarm logger Lambda
        alarm_log_table.grant_write_data(alarm_logger_lambda)

        # Subscribe alarm logger Lambda to SNS topic
        alarm_topic.add_subscription(
            subscriptions.LambdaSubscription(alarm_logger_lambda)
        )

        # Subscribe email address to receive alarm notifications
        alarm_topic.add_subscription(
            subscriptions.EmailSubscription("22080488@student.westernsydney.edu.au")
        )
        
        # CloudWatch Dashboard-------------------------------
        # Create a centralized dashboard for monitoring all metrics
        dashboard = cloudwatch.Dashboard(
            self, "WebHealthDashboard",
            dashboard_name="WebsiteHealthMonitoring"
        )

        # Lambda Operational Metrics & Alarms----------------------
        # Monitor the health and performance of the monitoring Lambda itself
        # This helps identify issues with the monitoring infrastructure
        
        # Duration Metric & Alarm
        # Tracks how long the Lambda takes to execute
        duration_metric = prod_alias.metric_duration(statistic="Average", period=Duration.minutes(5))
        duration_alarm = cloudwatch.Alarm(
            self, "CanaryLambdaDurationAlarm",
            alarm_name="CanaryLambda-Duration-Alarm",
            alarm_description="Lambda average duration > 30000ms",
            metric=duration_metric,
            threshold=30000,  # Alert if average duration exceeds 30 seconds
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        duration_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarm_topic))

        # Invocations Metric & Alarm
        # Tracks the number of times the Lambda is invoked
        invocations_metric = prod_alias.metric_invocations(statistic="Sum", period=Duration.minutes(5))
        invocations_alarm = cloudwatch.Alarm(
            self, "CanaryLambdaInvocationsAlarm",
            alarm_name="CanaryLambda-Invocations-Alarm",
            alarm_description="Lambda invocations > 100 in 5 min",
            metric=invocations_metric,
            threshold=100,  # Alert if invoked more than 100 times in 5 minutes
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        invocations_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarm_topic))

        # Errors Metric & Alarm
        # Tracks Lambda execution failures
        errors_metric = prod_alias.metric_errors(statistic="Sum", period=Duration.minutes(5))
        errors_alarm = cloudwatch.Alarm(
            self, "CanaryLambdaErrorsAlarm",
            alarm_name="CanaryLambda-Errors-Alarm",
            alarm_description="Lambda errors > 0 in 5 min",
            metric=errors_metric,
            threshold=0,  # Alert on any errors
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        errors_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarm_topic))

        # Add Lambda operational widgets to dashboard
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Crawler Lambda Duration (ms)",
                left=[duration_metric],
                width=6,
                height=4
            ),
            cloudwatch.GraphWidget(
                title="Crawler Lambda Invocations",
                left=[invocations_metric],
                width=6,
                height=4
            ),
            cloudwatch.GraphWidget(
                title="Crawler Lambda Errors",
                left=[errors_metric],
                width=6,
                height=4
            )
        )

        # # CodeDeploy Configuration for Gradual Rollout-------------------
        # # Configure CodeDeploy to gradually shift traffic with automatic rollback
        
        # # Create a CodeDeploy application for Lambda deployments
        # application = codedeploy.LambdaApplication(
        #     self, "CanaryDeploymentApplication",
        #     application_name="WebMonitoringCanaryApp"
        # )
        
        # # Create deployment group with canary deployment strategy
        # deployment_group = codedeploy.LambdaDeploymentGroup(
        #     self, "CanaryDeploymentGroup",
        #     application=application,
        #     alias=prod_alias,
        #     deployment_config=codedeploy.LambdaDeploymentConfig.CANARY_10_PERCENT_5_MINUTES,

        #     alarms=[
        #         duration_alarm,
        #         invocations_alarm,
        #         errors_alarm,
        #     ],
            
        #     # Automatically rollback if any alarm triggers
        #     auto_rollback=codedeploy.AutoRollbackConfig(
        #         failed_deployment=True,  # Rollback on deployment failure
        #         stopped_deployment=True,  # Rollback if deployment is manually stopped
        #         deployment_in_alarm=True  # Rollback if any alarm triggers
        #     ),
            
        #     deployment_group_name="WebMonitoringCanaryDeploymentGroup"
        # )

        # EventBridge Scheduling ------------------------

        # Configure scheduled trigger for the monitoring Lambda
        
        # Create EventBridge rule to run every 5 minutes
        monitoring_rule = events.Rule(
            self, "MonitoringScheduleRule",
            schedule=events.Schedule.rate(Duration.minutes(5)),
            description="Trigger web monitoring every 5 minutes"
        )
        
        # Set the monitoring Lambda as the target for the scheduled rule
        monitoring_rule.add_target(
            targets.LambdaFunction(prod_alias)
        )

        # Website Monitoring Setup-----------------------------
        # Create metrics and alarms for each monitored website
        # This section processes all configured websites and sets up monitoring
        
        # Extract website names from configuration
        websites = [w["name"] for w in DEFAULT_WEBSITES]

        # Lists to collect metrics from all websites for aggregate dashboard widgets
        availability_metrics = []
        latency_metrics = []
        throughput_metrics = []

        # Loop through each website and create monitoring resources
        for website in websites:
            metrics = self.create_website_monitoring(website, dashboard, alarm_topic)
            availability_metrics.append(metrics['availability'])
            latency_metrics.append(metrics['latency'])
            throughput_metrics.append(metrics['throughput'])

        # Aggregate Dashboard -----------------------
        # Create dashboard widgets that show metrics for all websites combined
        
        dashboard.add_widgets(
            # Availability widget - shows uptime status for all monitored sites
            cloudwatch.GraphWidget(
                title="Website Availability (All Sites)",
                left=availability_metrics,
                width=12,
                height=6,
                left_y_axis=cloudwatch.YAxisProps(
                    min=0,
                    max=1.1  # 0 = down, 1 = up
                )
            ),

            # Latency widget - shows response time for all monitored sites
            cloudwatch.GraphWidget(
                title="Response Time - All Websites (ms)",
                left=latency_metrics,
                width=12,
                height=6,
                left_y_axis=cloudwatch.YAxisProps(
                    min=0
                )
            ),

            # Throughput widget - shows data transfer rate for all monitored sites
            cloudwatch.GraphWidget(
                title="Throughput - All Websites (bytes/sec)",
                left=throughput_metrics,
                width=12,
                height=6,
                left_y_axis=cloudwatch.YAxisProps(
                    min=0
                )
            )
        )

        # Output deployment information
        print(f"Created monitoring Lambda: {canary_lambda.function_name}")
        print("Lambda will be triggered every 5 minutes via EventBridge")
        print(f"CloudWatch Dashboard: {dashboard.dashboard_name}")
    
    # Create Website Monitoring-----------------------------
    def create_website_monitoring(self, website_name: str, dashboard: cloudwatch.Dashboard, alarm_topic: sns.Topic):
        """
        Create comprehensive monitoring setup for a single website.
        
        This method creates:
        - CloudWatch metrics for availability, latency, and throughput
        - Alarms that trigger when metrics exceed thresholds
        - Returns metrics for use in aggregate dashboard widgets
        
        Args:
            website_name: The name of the website to monitor
            dashboard: The CloudWatch dashboard to add widgets to
            alarm_topic: The SNS topic to send alarm notifications to
            
        Returns:
            Dictionary containing the three metric objects
        """
        
        # Define CloudWatch metrics for this website
        # These metrics are published by the monitoring Lambda
        
        # Availability: 1 if site is up, 0 if down
        availability_metric = cloudwatch.Metric(
            namespace=METRIC_NAMESPACE,
            metric_name=METRIC_AVAILABILITY,
            dimensions_map={DIM_WEBSITE: website_name},
            statistic="Average",
            period=Duration.minutes(5)
        )
        
        # Latency: Response time in milliseconds
        latency_metric = cloudwatch.Metric(
            namespace=METRIC_NAMESPACE,
            metric_name=METRIC_LATENCY,
            dimensions_map={DIM_WEBSITE: website_name},
            statistic="Average",
            period=Duration.minutes(5)
        )
        
        # Throughput: Data transfer rate in bytes per second
        throughput_metric = cloudwatch.Metric(
            namespace=METRIC_NAMESPACE,
            metric_name=METRIC_THROUGHPUT,
            dimensions_map={DIM_WEBSITE: website_name},
            statistic="Average",
            period=Duration.minutes(5)
        )
        
        # Availability Alarm
        # Triggers when the site becomes unavailable
        availability_alarm = cloudwatch.Alarm(
            self, f"{website_name}AvailabilityAlarm",
            alarm_name=f"{website_name}-Availability-Alarm",
            alarm_description=f"Alert when {website_name} is unavailable",
            metric=availability_metric,
            threshold=1,  # Alert when availability < 1 (site is down)
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            evaluation_periods=2,  # Check over 2 periods (10 minutes)
            datapoints_to_alarm=2,  # Must be down for both periods to alarm
            treat_missing_data=cloudwatch.TreatMissingData.BREACHING  # Missing data = alarm
        )
        availability_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarm_topic))
        
        # Latency Alarm with Anomaly Detection
        latency_alarm = cloudwatch.AnomalyDetectionAlarm(
            self, f"{website_name}LatencyAlarm",
            alarm_name=f"{website_name}-Latency-Alarm", 
            alarm_description=f"Alert when {website_name} latency is anomalous (outside 2 standard deviations)",
            metric=latency_metric,
            evaluation_periods=3,
            datapoints_to_alarm=2,
            std_devs=2,  # 2 standard deviations from normal
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_LOWER_OR_GREATER_THAN_UPPER_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        latency_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarm_topic))

        # Throughput Alarm with Anomaly Detection
        throughput_alarm = cloudwatch.AnomalyDetectionAlarm(
            self, f"{website_name}ThroughputAlarm",
            alarm_name=f"{website_name}-Throughput-Alarm",
            alarm_description=f"Alert when {website_name} throughput is anomalous (outside 2 standard deviations)",
            metric=throughput_metric,
            evaluation_periods=3,
            datapoints_to_alarm=2,
            std_devs=2,  # 2 standard deviations from normal
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_LOWER_OR_GREATER_THAN_UPPER_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        throughput_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarm_topic))

        # Return metrics for use in aggregate dashboard widgets
        return {
            'availability': availability_metric,
            'latency': latency_metric, 
            'throughput': throughput_metric
        }
    

