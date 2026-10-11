# OraOne AWS setup status

Updated 2026-10-11. This document records only verified configuration and does not contain secrets.

## Verified AWS configuration

| Area | Status | Evidence | Cost / blocker |
| --- | --- | --- | --- |
| Account plan | VERIFIED COMPLETE | AWS console account is assigned to the Free plan | Advanced features were not activated |
| Region | VERIFIED COMPLETE | OraOne resources use `ap-southeast-2` (Sydney) | Mumbai is unavailable on the current plan |
| Cognito user pool | VERIFIED COMPLETE | AWS created the current pool and app client in Sydney; the console currently names the pool `User pool - fsc2sp` | Essentials plan; monitor MAU/message usage |
| Email sign-in | VERIFIED COMPLETE | User pool sign-in identifier is Email | Delivery is not yet live-tested |
| Hosted login client | VERIFIED COMPLETE | Authorization code grant, HTTPS callback `https://oraone.in/auth/callback`, sign-out URL `https://oraone.in/`, and OIDC scopes `email openid phone profile` | Google provider is not yet attached |
| Passwordless email OTP | CONFIGURED — UNTESTED | Essentials exposes the feature, but it remains inactive | Keep disabled until delivery and cost are approved/verified |
| Google sign-in | BLOCKED — ACCESS | Cognito form requires Google client ID and client secret | Requires an authorized Google Cloud OAuth app |
| Mobile OTP | CONFIGURED — UNTESTED | No phone sign-in or SMS factor was enabled | Keep disabled; India SMS may incur charges and regulatory setup |
| Custom sender | BLOCKED — ACCESS | `noreply@oraone.in` is the intended sender | Requires DNS/SES access and a live delivery test |
| AWS budget | VERIFIED COMPLETE | `OraOne-Account-Safety-Budget`, recurring `$1/month`, actual 50/80/100%, forecast 100% | Budget email recipient must verify the address |
| Free Tier alerts | BLOCKED — ACCESS | Billing preferences page reports the feature is enterprise-only for this account | No plan upgrade performed |
| S3 bucket | NOT APPLICABLE | No AWS S3 bucket was created | OraOne retains the MinIO/S3-compatible abstraction for Hostinger |

## OraOne environment

The private, ignored root file `.env.production` contains the Sydney Cognito region, pool, app-client, domain, callback, and Hostinger domain values. Database and MinIO secrets remain blank until they are supplied directly on the deployment host.

Never commit `.env.production`, Cognito tokens, Google OAuth secrets, AWS credentials, database passwords, or MinIO passwords.

## Git remote decision

The working repository currently tracks `https://github.com/varunjakkampudi-tech/OraOne.git`, which was the previously requested OraOne remote. `https://github.com/OraOneHQ/OraOne.git` also exists, but its `main` history has no merge base with this checkout. The remote was therefore not changed and neither repository was overwritten.

Before changing `origin`, explicitly select the canonical repository and perform a deliberate migration or pull request review.

## Remaining activation steps

1. Verify the AWS budget recipient from the verification email.
2. Supply Google OAuth credentials from an authorized Google Cloud project, then configure the Cognito provider and exact callback `/oauth2/idpresponse`.
3. Verify `oraone.in` DNS ownership, configure SES only after confirming the cost/sandbox state, and live-test `noreply@oraone.in`.
4. Keep SMS and passwordless email OTP disabled until delivery, abuse controls, and cost are verified.
5. Fill deployment secrets on Hostinger and run the production Compose preflight.
