# v6 Release Blockers

## Dependency audit

`cargo audit` was executed on 2026-10-01. It reports:

- `RUSTSEC-2025-0137`: `ruint 1.16.0`, fixed in `>=1.17.1`.
- `RUSTSEC-2026-0220`: `ruint 1.16.0`, fixed in `>=1.20.0`.
- `derivative`, `paste`, and `proc-macro-error` are unmaintained warnings.

`stylus-sdk 0.10.9` currently constrains `ruint` to `>=1.16, <1.17`. A direct lockfile override to 1.20.0 is rejected by Cargo. No unreviewed fork or unsafe suppression was added. Mainnet remains blocked until the Stylus dependency chain is updated upstream or an independently reviewed patched fork is adopted.

## Deployment alignment

The hardening branch changes the signed domain and ABI. The old v6 deployment at `0x4a7cdfa8ca7a3969b3427c42948abbd988097dd9` is not evidence for this build. A new Arbitrum Sepolia deployment and live red-team run are required.

The repository has no deployer private key or oracle signer credentials in the configured secret store, so no deployment was attempted. The deployment script uses environment variables only and never writes keys to the repository.

## Size

With `opt-level = "z"`, the v6 contract build reports approximately 31.2 KiB contract size and 110.5 KiB WASM. The old v4 claim of 23.4 KiB was removed from the v6 verifier. The exact network limit and the optimized artifact must be reviewed before release.
