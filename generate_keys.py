#!/usr/bin/env python3
"""
ZEUS GUARD — Gerador de credenciais do Oráculo Analítico (v5)

Gera um par de chaves exclusivo para o servidor do oráculo:
  * Endereço público  -> init_oracle() do contrato Stylus (lib.rs)
  * Chave privada     -> ORACLE_PRIVATE_KEY no .env do servidor (engine/oracle_service.py)

Nunca comite a chave privada. O .gitignore já bloqueia .env e oracle_key.txt.

Uso:
    python3 generate_keys.py
"""

import os

from eth_account import Account


def generate_oracle_credentials() -> None:
    # Gera uma nova conta criptográfica segura (entropia do OS)
    acc = Account.create()

    print("=" * 62)
    print("⚡ CREDENCIAIS OFICIAIS DO ORÁCULO ZEUS GUARD ⚡")
    print("=" * 62)
    print("Endereço Público (use no init_oracle do contrato Rust):")
    print(f"👉 {acc.address}")
    print("-" * 62)
    print("Chave Privada (guarde em .env — NUNCA compartilhe ou comite):")
    print(f"👉 0x{acc.key.hex()}")
    print("=" * 62)
    print()
    print("[AVISO] Se esta chave vazar, todo o sistema de validação on-chain")
    print("poderá ser comprometido. Use ambiente seguro para o servidor.")


if __name__ == "__main__":
    generate_oracle_credentials()
