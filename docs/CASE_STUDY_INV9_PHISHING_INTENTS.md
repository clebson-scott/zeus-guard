# INV9 — Receiver-Match: do achado forense ao módulo de produção

**Data:** 28/09/2026 · **Autor:** agente red-team ZEUS GUARD · **Status:** módulo implementado e validado

## 1. A ameaça (classe "phishing por intents")

Sites falsos (ex.: "Axioraswap") usam a **API e os contratos OFICIAIS** de
agregadores de bridge (LI.FI/Jumper, rotas intent: polymerStandard, layerSwap,
NEARIntents). O usuário conecta a carteira, o site injeta no request HTTP o
parâmetro `receiver` = carteira do golpista na chain de destino. Toda a
infraestrutura transacionada é legítima: contrato executor auditado, rotulagem
limpa, taxa real, cotação real. **O crime existe em um único parâmetro HTTP.**

## 2. PoC controlado (28/09/2026 — nada assinado/transmitido, sem chaves)

Dois cenários contra a API real da LI.FI, idênticos exceto pelo campo
`receiver`:

| Cenário | receiver no request | `action.toAddress` na resposta | INV9 |
|---|---|---|---|
| Legítimo | carteira conectada | carteira conectada | PASS |
| Golpe | carteira do atacante | **carteira da própria vítima** | ALERT |

Evidências-chave (`poc/POC_SAIDA_EVIDENCIA.txt`):
1. A API aceita ambos sem restrição (HTTP 200).
2. Mesmo contrato executor (LI.FI Diamond `0x1231DEB6...4EaE`), mesmo tamanho
   de calldata (1316 bytes) — diferença confinada em 32 bytes.
3. **Duplo engano:** a resposta exibe `action.toAddress` = carteira da vítima
   enquanto o receiver real do request é outro. A UI mostraria o destino "certo".

## 3. Evidência empírica: o calldata das intents é CEGO para o receiver

Diff palavra-a-palavra do calldata (receiver=legítimo vs receiver=atacante),
obtido de quotes reais nas três famílias de rota intent da LI.FI:

| Rota | Seletor | Receiver em texto puro? |
|---|---|---|
| polymerStandard (polymerCCTP) | `0x17917a4e` | NÃO — words 3-4 (compromisso+sal) |
| layerSwap | `0x4c279d6b` / `0x1794958f` | NÃO — words 3-4 |
| NEARIntents | `0x3110c7b9` | NÃO — words 3-4 |

Assinaturas canônicas confirmadas no openchain signature-database (contratos
verificados): `swapAndStartBridgeTokensViaPolymerCCTP`, `...ViaLayerSwap`,
`...ViaNEARIntents`. Em todas, o receiver viaja apenas como
`keccak256(receiver || salt)` — **invisível on-chain**. Conclusão estrutural:
para intents, INV9 só pode decidir na camada REQUEST; a camada calldata é
honestamente INDETERMINADA.

## 4. O módulo de produção — `engine/inv9_receiver_match.py`

Vereditos de 3 níveis (a lição do falso positivo Permit2Proxy: heurística sem
fonte de verdade gera FP; INV9 não infere — compara):

- **PASS** — receiver == carteira conectada (ou divergência com confirmação
  explícita registrada).
- **ALERT** — receiver != carteira conectada sem confirmação; flag
  `deceptive_display=True` quando o display da resposta contradiz o receiver
  real (engano ativo).
- **INDETERMINADO** — sem fonte de verdade (intent-commitment / seletor
  desconhecido / malformado). Fail-closed: nunca aprova no escuro.

Camadas:
1. **REQUEST (autoritativa):** compara o parâmetro do request HTTP; o display
   da resposta é usado apenas para detectar engano, nunca como fonte.
2. **CALLDATA (fallback):** decodificadores verificados para formatos onde o
   receiver viaja em texto puro — Across V3 `depositV3` (`0x7d0ece9c`) e
   `fillV3Relay` (`0xc39ffe76`, seletor confirmado no openchain; struct
   V3Deposit comum, extração por offset ABI). Intents conhecidas mapeadas para
   o motivo intent-commitment com explicação da cegueira.

## 5. Validação

- `engine/test_inv9.py` — 33 testes, todos passando: request-layer (match,
  engano ativo, confirmação explícita, case-insensitive), calldata sintético
  via `eth_abi` (depositV3/fillV3Relay, depositor terceiro), fixture REAL de
  quote polymer (1316 bytes, capturado ao vivo) → INDETERMINADO correto,
  invariante fail-closed (tabela de decoders vazia jamais fabrica PASS),
  malformados sem crash.
- Validação ao vivo contra a API LI.FI (28/09/2026): cenário do golpe →
  `ALERT` com `deceptive_display=true` ("ENGENO ATIVO: UI mostraria outro
  destino"); cenário legítimo → `PASS`; calldata intent isolado →
  `INDETERMINADO`.
- Regressão do motor existente: `test_engine_invariants.py` exit 0.
- Validação on-chain pendente opcional: captura de `depositV3`/`fillV3Relay`
  reais na Arbitrum para decodificação cruzada (`engine/data/scan_across.py`).

## 6. Integração futura (extensão MV3)

O hook EIP-1193 existente deve chamar `inv9_evaluate(from_addr,
request_receiver=…, calldata=…, response_display=…)` no `eth_sendTransaction`
de bridge/intents: ALERT com `deceptive_display` → bloqueio + aviso de engano
ativo; INDETERMINADO → exigir confirmação explícita do receiver.
