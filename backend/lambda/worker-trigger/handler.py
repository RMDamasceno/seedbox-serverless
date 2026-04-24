"""Lambda Worker Trigger — liga/desliga a instância EC2 Spot."""

import json
import logging
import os
import time

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

EC2_INSTANCE_ID = os.environ.get("EC2_INSTANCE_ID", "")
ec2 = boto3.client("ec2")


def handler(event, context):
    """
    Handler principal. Recebe action (start/stop) e controla a EC2.

    Invocada assincronamente pela Lambda API (InvocationType=Event).
    """
    action = event.get("action", "start")

    if not EC2_INSTANCE_ID:
        logger.error("EC2_INSTANCE_ID not configured")
        return {"statusCode": 500, "body": json.dumps({"error": "ec2_not_configured"})}

    if action == "start":
        return _start_worker()
    elif action == "stop":
        return _stop_worker()

    return {"statusCode": 400, "body": json.dumps({"error": "invalid_action"})}


def _get_instance_state() -> str:
    """Retorna o estado atual da instância (running, stopped, stopping, etc)."""
    try:
        resp = ec2.describe_instances(InstanceIds=[EC2_INSTANCE_ID])
        instances = resp["Reservations"][0]["Instances"]
        return instances[0]["State"]["Name"]
    except (ClientError, IndexError, KeyError) as e:
        logger.error("Failed to describe instance: %s", e)
        return "unknown"


def _start_worker() -> dict:
    """
    Liga a EC2 se parada. Se stopping, aguarda 30s e tenta novamente.

    Returns:
        HTTP response dict.
    """
    state = _get_instance_state()
    logger.info("Worker state: %s", state)

    if state in ("running", "pending"):
        return {"statusCode": 200, "body": json.dumps({"status": state})}

    if state == "stopping":
        logger.info("Instance is stopping, waiting 30s before retry")
        time.sleep(30)
        state = _get_instance_state()
        if state != "stopped":
            return {"statusCode": 200, "body": json.dumps({"status": state})}

    if state == "stopped":
        try:
            ec2.start_instances(InstanceIds=[EC2_INSTANCE_ID])
            logger.info("Instance start requested")
            return {"statusCode": 200, "body": json.dumps({"status": "starting"})}
        except ClientError as e:
            logger.error("Failed to start instance: %s", e)
            return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

    return {"statusCode": 200, "body": json.dumps({"status": state})}


def _stop_worker() -> dict:
    """
    Para a EC2 (usado apenas para manutenção manual).

    Returns:
        HTTP response dict.
    """
    state = _get_instance_state()

    if state in ("stopped", "stopping"):
        return {"statusCode": 200, "body": json.dumps({"status": state})}

    try:
        ec2.stop_instances(InstanceIds=[EC2_INSTANCE_ID])
        logger.info("Instance stop requested")
        return {"statusCode": 200, "body": json.dumps({"status": "stopping"})}
    except ClientError as e:
        logger.error("Failed to stop instance: %s", e)
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
