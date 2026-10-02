# ZEUS GUARD Release Index

This file is the navigation point for external reviewers. The hardened V6 deployment is canonical. V4 is retained only as the audit-frozen release that powers the public demo.

## Canonical release

- Arbitrum Sepolia V6 hardened: `0x9b7608536a9704e120f0fc2c6722e2abb0fef848`
- Robinhood Chain Testnet V6: `0xe18332679dc0bcfd1dda9e2e022252cbadb65eb5`
- Source of truth: [`deploy/DEPLOYADO_V6_ARBITRUM_SEPOLIA.md`](../deploy/DEPLOYADO_V6_ARBITRUM_SEPOLIA.md)
- Judge instructions: [`JUDGE_VERIFICATION.md`](JUDGE_VERIFICATION.md)

## Review order

1. [`../JUDGE_SUBMISSION.md`](../JUDGE_SUBMISSION.md) for the five-minute project overview.
2. [`JUDGE_VERIFICATION.md`](JUDGE_VERIFICATION.md) for reproducible checks and public transactions.
3. [`ARCHITECTURE.md`](ARCHITECTURE.md) and [`MATH.md`](MATH.md) for design and model details.
4. [`AUDIT_CHECKLIST.md`](AUDIT_CHECKLIST.md) and [`RELATORIO_FINAL_REDTEAM.md`](RELATORIO_FINAL_REDTEAM.md) for security findings and residual limitations.
5. [`REAL_DATA.md`](REAL_DATA.md) for the corrected identity-aware benchmark and temporal validation.

## Evidence policy

Historical V4 files and receipts remain in the repository for reproducibility. They are not claims that V4 is the canonical deployment. No private keys, `.env` files, credentials, or production secrets belong in this repository.
