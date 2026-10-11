"""One-off probe: what can this Bedrock key actually do?

Tests, in ap-southeast-2 (Sydney) on account 552823820939:
  1. Titan Text Embeddings v2  (amazon.titan-embed-text-v2:0)  -> for Phase 9 RAG
  2. A chat model via the OpenAI-compatible endpoint            -> sanity
The bearer token is read from AWS_BEARER_TOKEN_BEDROCK.
"""
import json
import os

REGION = os.environ.get("BEDROCK_REGION", "ap-southeast-2")
TOKEN = os.environ.get("AWS_BEARER_TOKEN_BEDROCK", "")
print(f"region={REGION}  token_set={bool(TOKEN)}  token_len={len(TOKEN)}")

import botocore
print("botocore", botocore.__version__)

import boto3

# ---- 1. Titan embeddings via boto3 invoke_model (uses bearer token) ----
def test_titan():
    client = boto3.client("bedrock-runtime", region_name=REGION)
    body = json.dumps({"inputText": "hello world", "dimensions": 1024, "normalize": True})
    resp = client.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        accept="application/json", contentType="application/json", body=body,
    )
    payload = json.loads(resp["body"].read())
    vec = payload.get("embedding")
    print(f"TITAN OK: dim={len(vec)} first3={vec[:3]}")


# ---- 2. List foundation models (control plane) ----
def test_list():
    bedrock = boto3.client("bedrock", region_name=REGION)
    r = bedrock.list_foundation_models()
    ids = [m["modelId"] for m in r.get("modelSummaries", [])]
    titan = [i for i in ids if "titan-embed" in i]
    print(f"LIST OK: {len(ids)} models; titan-embed ids: {titan}")


for name, fn in (("titan-embeddings", test_titan), ("list-models", test_list)):
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        print(f"{name} FAILED: {type(e).__name__}: {e}")
