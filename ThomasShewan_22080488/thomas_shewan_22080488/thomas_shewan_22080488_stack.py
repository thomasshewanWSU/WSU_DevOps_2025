from aws_cdk import (
    Stack,
    aws_apigateway as apigw,
    aws_lambda as _lambda
)
import aws_cdk.aws_lambda as lambda_

from constructs import Construct

class ThomasShewan22080488Stack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        fn = lambda_.Function(
            self, "WHLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="WHLambda.lambda_handler",
            code=lambda_.Code.from_asset("./modules")
        )

    