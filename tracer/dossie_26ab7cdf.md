# DOSSIÊ — Operador de tokens homoglifo (‘ÚЅDС’ cirílico) e varredor de USDT0
**Endereço:** `0x26ab7cdfce9a9be094b68caab97d08f2b6f50556`  
**Chain:** Arbitrum One

## Fluxos recentes (logs on-chain)

### ENTRADAS
(nenhuma)

### SAÍDAS
(nenhuma)

## Evidências da sessão de forense (28/09/2026)

- 28/09/2026: 8.296 USDT0 puxados via transferFrom de 54 carteiras distintas
  (approvals uniformes de 999.999,99 = automação)
- 28/09/2026: mesmo endereço opera no Ethereum envio em massa de tokens
  falsos ‘ÚЅDС’ (homoglifo com caracteres cirílicos) — +199 transfers/dia
  (fonte: ethplorer.io/tx/0x7842a1b3f55cce442c56229fcfcb2c618055a096095cac6577879afe8765cea4)
- Padrão: dusting/envenenamento de endereço + consolidação de fundos.
  Não constatado roubo direto de carteiras nesta chain na janela analisada.
- NOTA DE HONESTIDADE: o endereço é infraestrutura de abuso (spam/poisoning),
  não um drainer clássico; recomenda-se submissão como 'token scam/dusting',
  não como 'wallet drainer', para não fragilizar o dossiê.

## Achado forense adicional (28/09/2026, 20:52)
Varredura por tópicos de Transfer (from/to) NÃO encontra o endereço como parte
de transferências: os pulls são executados como SPENDER (transferFrom via
tx própria), sem figurar como from/to do evento. Ferramentas de rastreio
ingênuas (exploradores por endereço) são CEGAS a esse padrão — o rastro
correto exige indexar tx.from do spender e decodificar os eventos internos.

## Classificação final (honesta)
Na janela analisada, NÃO há evidência de drainer clássico nesta chain.
Classificação: infraestrutura de dusting/homoglifo + consolidação automatizada
(probável sybil/farming). O dossiê deve ser submetido como 'scam token /
address poisoning' — categoria real do abuso — e não como roubo de carteiras.

## Submissão sugerida
- Chainabuse: https://www.chainabuse.com (categoria: phishing/scam token)
- Phish.report; compliance de exchanges com KYC onde houver off-ramp
- Delegacia de crimes cibernéticos (documento público)