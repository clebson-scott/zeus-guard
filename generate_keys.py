#!/usr/bin/env python3
"""
ZEUS GUARD — Gerador de Credenciais do Oraculo Multisig (v6)

O contrato v6 exige threshold 2-de-3: gere as chaves do conjunto e cadastre
os enderecos publicos no init_oracle([o1, o2, (o3)]). As chaves privadas viram
ORACLE_PRIVATE_KEY_1/2/3 no .env do servidor (engine/oracle_service.py).

Nunca comite as chaves privadas. O .gitignore ja bloqueia .env e oracle_key.txt.

Uso:
    python3 generate_keys.py            # conjunto de 3 (threshold on-chain = 2)
"""

from eth_account import Account


def generate_oracle_credentials() -> None:
    print("=" * 66)
    print("CREDENCIAIS DO ORACULO MULTISIG ZEUS GUARD (v6, threshold 2-de-3)")
    print("=" * 66)
    accounts = []
    for i in range(3):
        acc = Account.create()
        accounts.append(acc)
        print(f"\nORACULO {i+1}")
        print(f"  Endereco publico (init_oracle / update_oracle_key): {acc.address}")
        print(f"  Chave privada (.env: ORACLE_PRIVATE_KEY_{i+1}): 0x{acc.key.hex()}")
    print("\n" + "-" * 66)
    print("init_oracle:   [" + ",".join(a.address for a in accounts) + "]")
    print("-" * 66)
    print("[AVISO] Chave comprometida? update_oracle_key(antiga, nova) gira sem redeploy.")
    print("[AVISO] Se esta chave vazar, todo o sistema de validacao on-chain")
    print("podera ser comprometido. Use ambiente seguro para o servidor.")


if __name__ == "__main__":
    generate_oracle_credentials()
