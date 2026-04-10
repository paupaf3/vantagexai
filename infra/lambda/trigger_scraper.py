import json
import os

import boto3

ecs = boto3.client("ecs")


def _response(status_code: int, body: dict):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _parse_event_body(event: dict) -> dict:
    body = event.get("body")
    if body is None:
        return {}
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            raise ValueError("Request body must be valid JSON.")
    if isinstance(body, dict):
        return body
    raise ValueError("Unsupported request body format.")


def _parse_env_list(var_name: str) -> list[str]:
    raw = os.environ.get(var_name, "[]")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Environment variable {var_name} must be valid JSON array.") from exc

    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(
            f"Environment variable {var_name} must be a non-empty array of strings.")
    return value


def lambda_handler(event, _context):
    try:
        payload = _parse_event_body(event)
    except ValueError as exc:
        return _response(400, {"error": str(exc)})

    mode = payload.get("mode")
    if mode not in {"ebay", "serper"}:
        return _response(400, {"error": "'mode' must be either 'ebay' or 'serper'."})

    items = payload.get("items")
    if not isinstance(items, list) or not items or not all(isinstance(i, str) and i.strip() for i in items):
        return _response(400, {"error": "'items' must be a non-empty array of strings."})

    cluster_arn = os.environ.get("ECS_CLUSTER_ARN")
    task_definition_arn = os.environ.get("ECS_TASK_DEFINITION_ARN")
    container_name = os.environ.get("ECS_CONTAINER_NAME", "scraper")

    if not cluster_arn:
        return _response(500, {"error": "ECS_CLUSTER_ARN is not configured."})
    if not task_definition_arn:
        return _response(500, {"error": "ECS_TASK_DEFINITION_ARN is not configured."})

    try:
        subnet_ids = _parse_env_list("ECS_SUBNET_IDS")
        security_group_ids = _parse_env_list("ECS_SECURITY_GROUP_IDS")
    except ValueError as exc:
        return _response(500, {"error": str(exc)})

    s3_bucket = payload.get("s3_bucket") or os.environ.get("DEFAULT_S3_BUCKET")

    command_parts = [mode, *items]
    if s3_bucket:
        command_parts.extend(["--s3-bucket", s3_bucket])

    run_task_kwargs = {
        "cluster": cluster_arn,
        "launchType": "FARGATE",
        "taskDefinition": task_definition_arn,
        "networkConfiguration": {
            "awsvpcConfiguration": {
                "subnets": subnet_ids,
                "securityGroups": security_group_ids,
                "assignPublicIp": os.environ.get("ECS_ASSIGN_PUBLIC_IP", "ENABLED"),
            }
        },
        "overrides": {
            "containerOverrides": [
                {
                    "name": container_name,
                    "command": command_parts,
                }
            ]
        },
    }

    try:
        run_result = ecs.run_task(**run_task_kwargs)
    except Exception as exc:
        return _response(500, {"error": f"Failed to run ECS task: {exc}"})

    failures = run_result.get("failures", [])
    if failures:
        reasons = [f.get("reason", "unknown") for f in failures]
        return _response(500, {"error": "ECS failed to start task.", "reasons": reasons})

    tasks = run_result.get("tasks", [])
    if not tasks:
        return _response(500, {"error": "ECS did not return a task ARN."})

    task_arn = tasks[0].get("taskArn")
    return _response(
        202,
        {
            "message": "Scraper job accepted.",
            "task_arn": task_arn,
            "cluster_arn": cluster_arn,
            "launch_type": "FARGATE",
            "mode": mode,
            "items": items,
        },
    )
