import boto3
import os

ssm = boto3.client("ssm")

_API_TOKEN_PARAM = os.environ["API_TOKEN_PARAM"]

# Cache the token for the lifetime of the Lambda container to avoid an SSM
# call on every invocation. API Gateway also caches the authorizer result for
# authorizer_result_ttl_in_seconds (configured in Terraform), so SSM is only
# hit on the first request after a cold start or cache expiry.
_cached_token: str | None = None


def _get_token() -> str:
    global _cached_token
    if _cached_token is None:
        response = ssm.get_parameter(Name=_API_TOKEN_PARAM, WithDecryption=True)
        _cached_token = response["Parameter"]["Value"]
    return _cached_token


def lambda_handler(event, _context):
    """
    Simple Lambda REQUEST authorizer for API Gateway HTTP API.
    Expects: Authorization: Bearer <token>
    Returns the simple-response format (enable_simple_responses = true).
    """
    auth_header = event.get("headers", {}).get("authorization", "")

    if auth_header.startswith("Bearer "):
        incoming_token = auth_header[len("Bearer "):]
    else:
        return {"isAuthorized": False}

    try:
        expected_token = _get_token()
    except Exception:
        # SSM unavailable — deny rather than fail open
        return {"isAuthorized": False}

    return {"isAuthorized": incoming_token == expected_token}
