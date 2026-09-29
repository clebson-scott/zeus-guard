# CASE STUDY RED-TEAM v2 (CORRIGIDO): Permit2Proxy — Falso Positivo Forense e o Golpe Invisível por Intents

> **CORREÇÃO DE MÉTODO:** A primeira versão deste case study (28/09/2026) afirmava que o
> contrato `0x89c6340b1a1f4b25d36cd8b063d49045caf3f818` era um "drainer de ~US$ 500k".
> **Isso estava ERRADO.** A reengenharia completa do contrato provou que ele é o
> **Permit2Proxy OFICIAL da LI.FI** processando tráfego legítimo do Jumper Exchange.
> Este documento registra o erro, sua causa raiz e o que a reengenharia revelou de fato.

## 1. Reengenharia completa do contrato

**Identidade:** `Permit2Proxy v1.0.4` — autor **LI.FI** (LGPL-3.0), Solidity 0.8.17,
otimizador com 1.000.000 de runs. Implantação determinística (create2) no MESMO
endereço em todas as chains: Arbitrum (18/09/2026), Avalanche (14/07/2025), Ethereum
(labeled "LI.FI: Permit2 Proxy 2" no Etherscan), Gnosis, XDC etc.

**Construtor:** `(_lifiDiamond=0x1231deb6..., _permit2=0x000000000022d473...,
_owner=0x9e606d0d...)`. O Diamond e o Permit2 são os endereços oficiais da LI.FI/Uniswap.

**Arquitetura (funções decodificadas do source de 13.682 chars):**
1. `callDiamondWithEIP2612Signature(token, amount, deadline, v, r, s, calldata)` —
   bridge gasless: executa `ERC20Permit.permit()` (aprovação POR ASSINATURA, sem tx de
   approve) + `transferFrom(vítima → contrato)` + `maxApprove(Diamond)` + executa o
   calldata do bridge no Diamond. **Tudo na MESMA transação** — por isso 63% dos
   "pulls" ocorriam junto ao approve: é o design legítimo.
2. `callDiamondWithPermit2(...)` e `callDiamondWithPermit2Witness(...)` — variantes via
   Permit2 da Uniswap com witness que bloqueia substituição do calldata.
3. `getPermit2MsgHash/nextNonce` — utilidades; `WithdrawablePeriphery` — owner (LI.FI)
   pode sacar tokens presos; `receive()` para reembolsos do Diamond.

**Decodificação da tx 0x3239e91f... (vítima "0x145d602b"):**
permit EIP-2612 de 300 USDC com deadline 23:30 UTC → transferFrom da vítima →
calldata LI.FI **"lifiIntents"** com integrator **"jumper.exchange"**,
receiver = **a própria vítima** (0x145d602b...), taxa de integrador 0,01%
(0,03 USDC → 0xc06ebbefd9...) → bridge cross-chain legítimo.

## 2. Por que o falso positivo aconteceu (causa raiz)

1. Approve+transferFrom na mesma tx = assinatura de "dreno one-click" NA MINHA HEURÍSTICA,
   mas é o comportamento normal de qualquer fluxo gasless (EIP-2612/Permit2).
2. O scanner "drenagem pura" só vê a chain de origem: no bridge legítimo, a
   contraparte chega NA CHAIN DE DESTINO (invisível na forense single-chain).
3. O nome "Permit2Proxy" + source idêntico ao oficial enganou na direção oposta:
   parecia clone malicioso, e é o original.
4. Não verifiquei identidade/idade do contrato ANTES de classificar — a mesma falha
   metodológica que o benchmark v2 corrigiu com a lista de protocolos verificados.

## 3. O golpe REAL que a reengenharia revelou: phishing via intents oficiais

O padrão documentado pela comunidade (caso "Axioraswap", Reddit r/CryptoScams):
sites de phishing **usam a API e os contratos OFICIAIS da LI.FI** para construir
intents perfeitamente legítimos — com UMA diferença: o campo **receiver** aponta para
a carteira do GOLPISTA na chain de destino. A vítima assina um bridge real, paga a taxa
real, e o dinheiro chega legalmente na carteira do ladrão em outra chain.

**Implicação forense:** esta classe de golpe é INVISÍVEL para rotulagem por desfecho
on-chain — todo o tráfego é LI.FI legítimo; o crime existe apenas no parâmetro
`receiver` do calldata e no frontend que o construiu.

## 4. Novas invariantes para o ZEUS GUARD

- **INV9 (receiver-match) → IMPLEMENTADA (28/09/2026):** módulo de produção
  `engine/inv9_receiver_match.py` (33/33 testes). Em intents/bridges,
  `receiver != tx.origin` sem confirmação explícita → ALERTAR; detectaria o
  phishing-Axioraswap. A camada calldata é cega para intents (receiver viaja
  como keccak256(receiver‖sal) — ver diff empírico em
  `docs/CASE_STUDY_INV9_PHISHING_INTENTS.md`), portanto a decisão autoritativa
  é a camada REQUEST; display da resposta é tratado apenas como sinal de
  engano ativo, nunca como fonte do receiver.
- **REV-INV8:** a INV8 proposta na versão anterior ("approve+transferFrom atômico =
  BLOQUEAR") é **INCORRETA** — bloquearia TODO o tráfego gasless legítimo do Jumper.
  Deve ser refinada para: approve+transferFrom atômico **+ spender não-oficial**.
- **Falso positivo de fluxo gasless:** qualquer motor baseado em "pull por terceiro"
  gera FP estrutural em bridges gasless (tx real pode ser submetida por relayer).
  Recomendação: tratar fluxos EIP-2612/Permit2 com spender verificado como benignos.

## 5. As campanhas de apoio (reclassificadas)

- `0x26ab7cdf...` — não é drainer de carteiras: operador de **tokens homoglifo
  ("ÚЅDС" com caracteres cirílicos)** em massa no Ethereum (+199 transfers/dia) e
  consolidação/sybil de USDT0 na Arbitrum (approves uniformes de 999.999,99 =
  automação). Infraestrutura de dusting/envenenamento de endereço.
- `0x0e9c1a3a...` — sonda de allowances (transferFrom de ZERO contra 24 carteiras):
  reconhecimento de superfície de ataque.

## 6. Lição consolidada para o 10/10

A cadeia de erros e correções deste case study é evidência direta de que o motor
produção-grade precisa de **camada de identidade** (verificação de quem é cada
contrato: idade, implantação multi-chain, integrator, labels) **acima** das
heurísticas de padrão. Padrão sem identidade gera tanto falsos negativos (intent
phishing) quanto falsos positivos em massa (Jumper gasless).
