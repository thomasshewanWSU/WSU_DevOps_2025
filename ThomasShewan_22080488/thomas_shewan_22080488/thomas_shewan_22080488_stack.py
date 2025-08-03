from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda
)
import aws_cdk.aws_lambda as lambda_

from constructs import Construct

class ThomasShewan22080488Stack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Lambda function for canary monitoring
        canary_lambda = lambda_.Function(
            self, "MonitoringLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="MonitoringLambda.lambda_handler",
            code=lambda_.Code.from_asset("./modules"),
            timeout=Duration.seconds(30),
            description="Simple web health monitoring canary - manual trigger"
        )

    