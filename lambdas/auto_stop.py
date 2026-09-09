import os
from datetime import datetime, timedelta, timezone

import boto3


ec2 = boto3.client("ec2")
cloudwatch = boto3.client("cloudwatch")


def lambda_handler(event, context):
    threshold = float(os.environ.get("CPU_THRESHOLD", "5")) # CPU utilization minimum to consider is 5% of usage
    idle_minutes = int(os.environ.get("IDLE_MINUTES", "30")) # Idle time in minutes to consider an instance is 30 minutes
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(minutes=idle_minutes)

    response = ec2.describe_instances(
        Filters=[
            {"Name": "tag:AutoStop", "Values": ["true"]},
            {"Name": "instance-state-name", "Values": ["running"]},
        ]
    )

    stopped = []
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            instance_id = instance["InstanceId"]
            metrics = cloudwatch.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start_time,
                EndTime=now,
                Period=300,
                Statistics=["Average"],
            )
            datapoints = metrics.get("Datapoints", [])
            if not datapoints:
                continue

            is_idle = all(point["Average"] <= threshold for point in datapoints)
            if is_idle:
                ec2.stop_instances(InstanceIds=[instance_id])
                stopped.append(instance_id)

    return {"stopped_instances": stopped}
