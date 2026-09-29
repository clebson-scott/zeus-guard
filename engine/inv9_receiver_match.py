#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
INV9 — Receiver-Match Invariant | ZEUS GUARD (módulo de produção)
================================================================================
Ameaça (validada em forense + PoC, 28/09/2026): phishing por intents.
Sites falsos usam a API e os contratos OFICIAIS de agregadores (LI.FI/Jumper)
e constroem bridges onde o campo `receiver` aponta para a carteira do
golpista. Zero artefato malicioso on-chain; o crime vive num parâmetro.

Lição estrutural do falso positivo "Permit2Proxy": heurística de padrão sem
fonte de verdade gera FP em massa. INV9 não infere — COMPARA o receiver
contra a carteira conectada, com veredito honesto de 3 níveis.

Duas camadas de intercepção:

1. REQUEST (autoritativa quando interceptável — hook de extensão nas
   chamadas HTTP a agregadores): o parâmetro `receiver` viaja em texto
   puro no request. Evidência PoC: a RESPOSTA pode ser enganosa
   (`action.toAddress` exibe a carteira da própria vítima mesmo com
   receiver != vítima) — logo o display é DESCONFIADO por padrão.

2. CALLDATA (fallback para interação direta com contratos): decodifica o
   receiver nos formatos onde ele viaja em texto puro. Nos formatos
   intent (receiver = keccak256(receiver||salt), words 3-4 — evidência
   empírica LI.FI polymer/layerswap/near-intents) o calldata é CEGO para
   o receiver e o veredito é INDETERMINADO com razão explícita. Nunca
   adivinha. Nunca aprova sem fonte de verdade.

Vereditos:
  PASS           receiver == carteira conectada (ou divergente com
                 confirmação explícita do usuário registrada).
  ALERT          receiver != carteira conectada, sem confirmação.
  INDETERMINADO  camada não consegue verificar (intent-commitment /
                 seletor desconhecido / calldata inválido) → escalar.

Sem dependências de rede: funções puras, testáveis offline.
================================================================================
"""
from dataclasses import dataclass, field
from Crypto.Hash import keccak

# ---------------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------------

def _sel(sig: str) -> str:
    k = keccak.new(digest_bits=256)
    k.update(sig.encode())
    return "0x" + k.hexdigest()[:8]


def _norm(addr) -> str:
    """Normaliza endereço (hex, case-insensitive). '' se vazio/inválido."""
    a = (addr or "").strip().lower()
    if not a.startswith("0x"):
        return ""
    if len(a) != 42:
        return ""
    try:
        int(a[2:], 16)
    except ValueError:
        return ""
    return a


def _is_addr_word(word: bytes) -> bool:
    """Palavra ABI de 32 bytes que codifica um address válido."""
    return len(word) == 32 and word[:12] == b"\x00" * 12 and word[12:] != b"\x00" * 20


# ---------------------------------------------------------------------------
# decodificadores verificados (fonte de verdade da camada calldata)
# ---------------------------------------------------------------------------
# Assinaturas canônicas confirmadas: fillV3Relay registrado no openchain
# signature-database com contrato verificado; depositV3 compartilha o MESMO
# struct V3Deposit (Across V3, source público). Posições extraídas por offset
# ABI, não por índice fixo.

V3_DEPOSIT_TUPLE = (
    "(address,address,address,address,uint256,uint256,uint256,uint32,uint32,uint32,address,bytes)"
)

VERIFIED_DECODERS = {
    # seletor: (nome do formato, índice do parâmetro-tupla no head)
    _sel("depositV3(" + V3_DEPOSIT_TUPLE + ")"): ("across-v3-depositV3", 0),
    _sel("fillV3Relay(" + V3_DEPOSIT_TUPLE + ",uint256)"): ("across-v3-fillV3Relay", 0),
}

# Seletores intent da LI.FI (empíricos, 28/09/2026): receiver existe apenas
# como keccak256(receiver || salt) nas words 3-4 do tail do intent.
# 0x17917a4e swapAndStartBridgeTokensViaPolymerCCTP
# 0x4c279d6b / 0x1794958f swapAndStartBridgeTokensViaLayerSwap (variantes)
# 0x3110c7b9 swapAndStartBridgeTokensViaNEARIntents
INTENT_COMMITMENT_SELECTORS = {
    "0x17917a4e": "li.fi-polymerCCTP",
    "0x4c279d6b": "li.fi-layerSwap",
    "0x1794958f": "li.fi-layerSwap-v2",
    "0x3110c7b9": "li.fi-nearIntents",
}

PASS, ALERT, INDETERMINADO = "PASS", "ALERT", "INDETERMINADO"


@dataclass
class Inv9Verdict:
    verdict: str
    layer: str                       # "request" | "calldata" | "nenhuma"
    receiver: str = ""               # endereço extraído/declarado ('' se oculto)
    reason: str = ""
    deceptive_display: bool = False  # display da resposta contradiz o receiver real
    explicit_confirmation: bool = False
    details: dict = field(default_factory=dict)

    def as_dict(self):
        return {
            "verdict": self.verdict, "layer": self.layer, "receiver": self.receiver,
            "reason": self.reason, "deceptive_display": self.deceptive_display,
            "explicit_confirmation": self.explicit_confirmation, "details": self.details,
        }


# ---------------------------------------------------------------------------
# camada 1: REQUEST (autoritativa)
# ---------------------------------------------------------------------------

def inv9_request(from_addr: str, receiver_param: str,
                 response_display: str = None,
                 explicit_confirmation: bool = False) -> Inv9Verdict:
    """
    Fonte de verdade: o PARÂMETRO do request HTTP (texto puro).
    O display da resposta (`action.toAddress` da LI.FI) é comparado apenas
    para DETECTAR engano ativo — nunca usado como fonte do receiver.
    """
    f, r = _norm(from_addr), _norm(receiver_param)
    if not f or not r:
        return Inv9Verdict(INDETERMINADO, "request",
                           reason="endereço ausente/inválido (from=%r receiver=%r)" % (from_addr, receiver_param))
    deceptive = False
    if response_display is not None:
        d = _norm(response_display)
        if d and d != r:
            deceptive = True  # UI mostraria destino diferente do receiver real
    if r == f:
        return Inv9Verdict(PASS, "request", receiver=r,
                           reason="receiver == carteira conectada",
                           deceptive_display=deceptive)
    if explicit_confirmation:
        return Inv9Verdict(PASS, "request", receiver=r,
                           reason="receiver != carteira conectada — confirmação EXPLÍCITA do usuário registrada",
                           explicit_confirmation=True, deceptive_display=deceptive)
    return Inv9Verdict(
        ALERT, "request", receiver=r,
        reason="receiver do request (%s) != carteira conectada (%s)%s" % (
            r[:10] + "..", f[:10] + "..",
            " | display da resposta exibe %s.. (ENGENO ATIVO: UI mostraria outro destino)" % (response_display[:10],)
            if deceptive else ""),
        deceptive_display=deceptive)


# ---------------------------------------------------------------------------
# camada 2: CALLDATA (fallback honesto)
# ---------------------------------------------------------------------------

def _words(calldata: str):
    """Hex calldata (0x…) → (selector, lista de words de 32 bytes). Lança ValueError se malformado."""
    h = calldata.strip().lower()
    if not h.startswith("0x") or len(h) < 10 or (len(h) - 2) % 2:
        raise ValueError("calldata malformado")
    b = bytes.fromhex(h[2:])
    return h[:10], [b[i:i + 32] for i in range(4, len(b), 32)]


def extract_receiver(calldata: str):
    """
    Extrai o receiver de calldata nos formatos VERIFICADOS.
    Retorna (receiver|None, formato, motivo). None ⇒ camada cega.
    """
    try:
        selector, words = _words(calldata)
    except ValueError as e:
        return None, "invalid", str(e)

    if selector in VERIFIED_DECODERS:
        name, head_idx = VERIFIED_DECODERS[selector]
        if len(words) < head_idx + 1:
            return None, name, "calldata truncado (head)"
        # parâmetro-tupla dinâmico: head contém offset (em bytes) para os dados
        try:
            off = int.from_bytes(words[head_idx], "big")
        except Exception:
            return None, name, "offset ilegível"
        w0 = off // 32  # word inicial da tupla (relativo ao início do body)
        if len(words) <= w0 + 1:
            return None, name, "calldata truncado (tuple)"
        depositor_w, recipient_w = words[w0], words[w0 + 1]
        if _is_addr_word(recipient_w):
            rec = "0x" + recipient_w[12:].hex()
            return rec, name, "V3Deposit.depositor=%s" % ("0x" + depositor_w[12:].hex())
        return None, name, "word de recipient não é address válido"

    if selector in INTENT_COMMITMENT_SELECTORS:
        name = INTENT_COMMITMENT_SELECTORS[selector]
        return None, "intent-commitment", (
            "formato intent %s: receiver existe apenas como keccak256(receiver||salt) "
            "(words 3-4) — calldata CEGO para o receiver; verificar na camada request" % name)

    return None, "unknown-selector", (
        "seletor %s fora da tabela de decodificadores verificados — sem fonte de "
        "verdade, INV9 não aprova nem alerta por calldata" % selector)


def inv9_calldata(from_addr: str, calldata: str,
                  explicit_confirmation: bool = False) -> Inv9Verdict:
    f = _norm(from_addr)
    if not f:
        return Inv9Verdict(INDETERMINADO, "calldata", reason="from_address ausente/inválido")
    receiver, fmt, why = extract_receiver(calldata)
    if receiver is None:
        return Inv9Verdict(INDETERMINADO, "calldata",
                           reason="%s: %s" % (fmt, why), details={"formato": fmt})
    if receiver == f:
        return Inv9Verdict(PASS, "calldata", receiver=receiver,
                           reason="receiver extraído do calldata (%s) == carteira conectada" % fmt,
                           details={"formato": fmt, "decodificacao": why})
    if explicit_confirmation:
        return Inv9Verdict(PASS, "calldata", receiver=receiver,
                           reason="receiver (%s) != carteira conectada — confirmação EXPLÍCITA registrada" % receiver[:12],
                           explicit_confirmation=True, details={"formato": fmt})
    return Inv9Verdict(ALERT, "calldata", receiver=receiver,
                       reason="receiver extraído do calldata (%s) = %s != carteira conectada %s" % (
                           fmt, receiver, f),
                       details={"formato": fmt, "decodificacao": why})


# ---------------------------------------------------------------------------
# orquestrador
# ---------------------------------------------------------------------------

def inv9_evaluate(from_addr: str,
                  request_receiver: str = None,
                  calldata: str = None,
                  response_display: str = None,
                  explicit_confirmation: bool = False) -> Inv9Verdict:
    """
    Orquestra as camadas. Prioridade: request (autoritativa) → calldata.
    Sem nenhuma fonte de verdade disponível: INDETERMINADO (escalar para
    confirmação explícita do usuário; nunca aprovar).
    """
    if request_receiver is not None:
        return inv9_request(from_addr, request_receiver, response_display, explicit_confirmation)
    if calldata is not None:
        return inv9_calldata(from_addr, calldata, explicit_confirmation)
    return Inv9Verdict(INDETERMINADO, "nenhuma",
                       reason="nem request nem calldata disponíveis — exigir confirmação explícita do usuário")
