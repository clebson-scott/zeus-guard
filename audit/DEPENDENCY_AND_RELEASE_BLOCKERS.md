# v6 Release Blockers

## Dependency audit

`cargo audit` was executed on 2026-10-01. It reports:

- `RUSTSEC-2025-0137`: `ruint 1.16.0`, fixed in `>=1.17.1`.
- `RUSTSEC-2026-0220`: `ruint 1.16.0`, fixed in `>=1.20.0`.
- `derivative`, `paste`, and `proc-macro-error` are unmaintained warnings.

`stylus-sdk 0.10.9` currently constrains `ruint` to `>=1.16, <1.17`. A direct lockfile override to 1.20.0 is rejected by Cargo. No unreviewed fork or unsafe suppression was added. Mainnet remains blocked until the Stylus dependency chain is updated upstream or an independently reviewed patched fork is adopted.

## Deployment alignment — RESOLVED (2026-10-01)

The hardening branch (signed domain + ABI changes) was deployed fresh on 2026-10-01: contract `0x9b7608536a9704e120f0fc2c6722e2abb0fef848`, activated, cached in ArbOS, with a fresh 2-of-3 oracle set registered on-chain and a live red-team run of 10 PASS / 0 FAIL. See `deploy/DEPLOYADO_V6_ARBITRUM_SEPOLIA.md`. The old pre-hardening v6 at `0x4a7cdfa8ca7a3969b3427c42948abbd988097dd9` is obsolete and kept only as history. Deploy/oracle keys remain outside the repository (environment variables only).

## Size

With `opt-level = "z"`, the v6 contract build reports approximately 31.2 KiB contract size and 110.5 KiB WASM. The old v4 claim of 23.4 KiB was removed from the v6 verifier. The exact network limit and the optimized artifact must be reviewed before release.
