import json


def convert_to_sse_format(payload):
    return f"data: {json.dumps(payload)}\n\n"
