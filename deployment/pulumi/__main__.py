"""
Create and configure a Cloudflare R2 bucket.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import os

import pulumi
import pulumi_cloudflare as cloudflare

BACKUP_PREFIX = "application-database/"
LOCK_SECONDS = 30 * 24 * 60 * 60
RETENTION_SECONDS = 90 * 24 * 60 * 60

r2_bucket_lnkr_api_backup = cloudflare.R2Bucket(
    "r2_bucket_lnkr_api_backup",
    account_id=os.environ["CLOUDFLARE_ACCOUNT_ID"],
    name="lnkr-api",  # Must match the application_name used in ansible's playbook.yml.
    location="eeur",
    storage_class="Standard",
    opts=pulumi.ResourceOptions(protect=True),
)

# A compromised VPS cannot replace or delete a recent backup.
r2_bucket_lnkr_api_backup_lock = cloudflare.R2BucketLock(
    "r2_bucket_lnkr_api_backup_lock",
    account_id=os.environ["CLOUDFLARE_ACCOUNT_ID"],
    bucket_name=r2_bucket_lnkr_api_backup.name,
    rules=[
        {
            "id": f"lock-{BACKUP_PREFIX.rstrip('/')}-30-days",
            "condition": {
                "max_age_seconds": LOCK_SECONDS,
                "type": "Age",
            },
            "enabled": True,
            "prefix": BACKUP_PREFIX,
        }
    ],
    opts=pulumi.ResourceOptions(protect=True),
)

# Each encrypted dump is independent, so R2 can safely delete it after the retention window.
r2_bucket_lnkr_api_backup_lifecycle = cloudflare.R2BucketLifecycle(
    "r2_bucket_lnkr_api_backup_lifecycle",
    account_id=os.environ["CLOUDFLARE_ACCOUNT_ID"],
    bucket_name=r2_bucket_lnkr_api_backup.name,
    rules=[
        {
            "id": f"delete-{BACKUP_PREFIX.rstrip('/')}-after-90-days",
            "conditions": {"prefix": BACKUP_PREFIX},
            "delete_objects_transition": {
                "condition": {
                    "max_age": RETENTION_SECONDS,
                    "type": "Age",
                },
            },
            "enabled": True,
        }
    ],
    opts=pulumi.ResourceOptions(protect=True),
)
