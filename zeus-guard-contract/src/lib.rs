//! ZEUS GUARD - Contrato Stylus (Rust) para Arbitrum / Robinhood Chain
//!
//! Guardiao pre-transacao do usuario leigo:
//!   1. Firewall de approvals: registro + score QCSN + revogacao pelo guardiao
//!   2. Cofre de pagamento com janela de desafio (anti-drainer, USDG-native)
//!   3. Guarda de pagamento agentico (x402/MPP): o agente so paga dentro da politica
//!   4. Disjuntor de emergencia (freeze da sessao inteira)
//!
//! Autor: Clebson Campos de Araujo - Arbitrum Open House Singapore 2026
//! Nota: codigo de hackathon, nao auditado.
//!
//! v2 (26/09/2026): cofre USDG nativo (IERC20.transferFrom real), reembolso de
//! pagamento contestado, testes nativos de unidade e helper puro de janela/teto.
//! Politica ERC-20 por sessao: set_usdg_token(token) ativa modo real;
//! address(0) mantem o modo ledger (compativel com os receipts v1).

// Allow `cargo stylus export-abi` to generate a main function.
#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
extern crate alloc;

use stylus_sdk::prelude::*;
use stylus_sdk::call::RawCall;
use stylus_sdk::alloy_sol_types::SolCall;
use stylus_sdk::alloy_sol_types::sol;
use stylus_sdk::alloy_primitives::{Address, B256, U64, U128, U256};

pub const MIN_CHALLENGE_WINDOW: u64 = 120; // 2 min de protecao minima
pub const RISK_BLOCK_X100: u64 = 6000; // score >= 60% => drainer (saida QCSN)
pub const DAILY_CAP_DEFAULT: u128 = 1000 * 10_u128.pow(18); // 1.000 USDG/dia

sol! {
    event SessionInit(address indexed owner, address indexed guardian, uint64 challenge_window);
    event ApprovalLogged(address indexed user, address indexed spender, uint256 amount, uint64 risk_x100);
    event ApprovalRevoked(address indexed user, address indexed spender, uint64 risk_x100);
    event PaymentEscrowed(bytes32 indexed payment_id, address indexed payer, address payee, uint256 amount, uint64 release_at);
    event PaymentContested(bytes32 indexed payment_id, address indexed guardian);
    event PaymentReleased(bytes32 indexed payment_id, address indexed payee, uint256 amount);
    event SessionFrozen(address indexed user, address indexed by);
    event SessionUnfrozen(address indexed user, address indexed by);
    event UsdgTokenSet(address indexed user, address usdg);
    event PaymentRefunded(bytes32 indexed payment_id, address indexed payer, uint256 amount);

    error NoSession();
    error NotSessionOwner();
    error NotGuardian();
    error AlreadyReleased();
    error ChallengeWindowOpen();
    error PaymentDisputed();
    error SessionFrozenError();
    error TooRisky(uint64 risk_x100, uint64 threshold);
    error AboveDailyCap(uint256 requested, uint256 remaining);
    error UnknownPayment();
    error PaymentIdInUse();
    error TokenTransferFailed(bool returned);
    error NotDisputed();
    error AlreadyRefunded();

}

/// Todas as formas de falha do guardiao.
#[derive(SolidityError)]
pub enum ZeusError {
    NoSession(NoSession),
    NotSessionOwner(NotSessionOwner),
    NotGuardian(NotGuardian),
    AlreadyReleased(AlreadyReleased),
    ChallengeWindowOpen(ChallengeWindowOpen),
    PaymentDisputed(PaymentDisputed),
    SessionFrozen(SessionFrozenError),
    TooRisky(TooRisky),
    AboveDailyCap(AboveDailyCap),
    UnknownPayment(UnknownPayment),
    PaymentIdInUse(PaymentIdInUse),
    TokenTransferFailed(TokenTransferFailed),
    NotDisputed(NotDisputed),
    AlreadyRefunded(AlreadyRefunded),
}

/// IERC20 minimo para o cofre USDG nativo (Paxos Global Dollar).
sol! {
    interface IERC20 {
        function transferFrom(address from, address to, uint256 amount) external returns (bool);
        function transfer(address to, uint256 amount) external returns (bool);
    }
}

sol_storage! {
    #[entrypoint]
    pub struct ZeusGuard {
        // ---- sessao do usuario (achatado: gas baixo e superficie simples) ----
        mapping(address => bool) session_exists;
        mapping(address => address) session_owner;
        mapping(address => address) session_guardian;
        mapping(address => bool) session_frozen;
        mapping(address => uint64) session_window;
        mapping(address => uint128) session_cap;
        mapping(address => address) session_usdg; // address(0) = modo ledger
        // ---- approvals analisados pelo motor QCSN ----
        mapping(address => mapping(address => uint256)) approval_amount;
        mapping(address => mapping(address => uint64)) approval_risk;
        mapping(address => mapping(address => bool)) approval_revoked;
        // ---- cofre de pagamentos (janela de desafio) ----
        mapping(bytes32 => bool) payment_exists;
        mapping(bytes32 => address) payment_from;
        mapping(bytes32 => address) payment_payee;
        mapping(bytes32 => uint256) payment_amount;
        mapping(bytes32 => uint64) payment_release_at;
        mapping(bytes32 => bool) payment_released;
        mapping(bytes32 => bool) payment_disputed;
        mapping(bytes32 => bool) payment_refunded;
        // ---- teto diario (janela rolante de 24h) ----
        mapping(address => uint128) daily_spent;
        mapping(address => uint64) daily_window_start;
    }
}

/// Janela de 24h ainda valida? (puro, testavel nativamente)
fn spent_in_window(ws: u64, now: u64, spent: U128) -> U128 {
    if ws > 0 && now.saturating_sub(ws) < 86400 { spent } else { U128::ZERO }
}

/// Janela de desafio efetiva: o minimo de protecao sempre se aplica.
fn effective_window(w: u64) -> u64 {
    if w < MIN_CHALLENGE_WINDOW { MIN_CHALLENGE_WINDOW } else { w }
}

impl ZeusGuard {
    fn require_session(&self, user: Address) -> Result<(), ZeusError> {
        if self.session_exists.getter(user).get() {
            return Ok(());
        }
        Err(ZeusError::NoSession(NoSession {}))
    }

    fn current_daily_spent(&self, user: Address) -> U128 {
        let now = self.vm().block_timestamp();
        spent_in_window(
            self.daily_window_start.getter(user).get().to::<u64>(),
            now,
            self.daily_spent.getter(user).get(),
        )
    }
}

#[public]
impl ZeusGuard {
    /// O usuario instala o guardiao: agente, janela de desafio e teto diario.
    pub fn init_session(&mut self, guardian: Address, challenge_window: U256, daily_cap: U256) -> Result<(), ZeusError> {
        let user = self.vm().msg_sender();
        self.session_exists.setter(user).set(true);
        self.session_owner.setter(user).set(user);
        self.session_guardian.setter(user).set(guardian);
        self.session_frozen.setter(user).set(false);
        let cw = effective_window(challenge_window.to::<u64>());
        self.session_window.setter(user).set(U64::from(cw));
        let cap = if daily_cap.is_zero() { DAILY_CAP_DEFAULT } else { daily_cap.to::<u128>() };
        self.session_cap.setter(user).set(U128::from(cap));
        self.vm().log(SessionInit { owner: user, guardian, challenge_window: cw });
        Ok(())
    }

    /// Ajusta teto/janela sem reinstalar (dono apenas).
    pub fn update_policy(&mut self, challenge_window: U256, daily_cap: U256) -> Result<(), ZeusError> {
        let user = self.vm().msg_sender();
        self.require_session(user)?;
        if self.session_owner.getter(user).get() != user {
            return Err(ZeusError::NotSessionOwner(NotSessionOwner {}));
        }
        if !challenge_window.is_zero() {
            self.session_window.setter(user).set(U64::from(effective_window(challenge_window.to::<u64>())));
        }
        if !daily_cap.is_zero() {
            self.session_cap.setter(user).set(U128::from(daily_cap.to::<u128>()));
        }
        Ok(())
    }

    /// O agente ZEUS registra um approval ANALISADO pelo motor QCSN.
    pub fn log_approval(&mut self, user: Address, spender: Address, amount: U256, risk_x100: U256) -> Result<(), ZeusError> {
        self.require_session(user)?;
        let sender = self.vm().msg_sender();
        if sender != self.session_owner.getter(user).get() && sender != self.session_guardian.getter(user).get() {
            return Err(ZeusError::NotSessionOwner(NotSessionOwner {}));
        }
        self.approval_amount.setter(user).setter(spender).set(amount);
        self.approval_risk.setter(user).setter(spender).set(U64::from(risk_x100.to::<u64>()));
        self.approval_revoked.setter(user).setter(spender).set(false);
        self.vm().log(ApprovalLogged { user, spender, amount, risk_x100: risk_x100.to::<u64>() });
        Ok(())
    }

    /// Revogacao de approval perigoso: o guardiao age sem esperar o usuario.
    pub fn guardian_revoke(&mut self, user: Address, spender: Address) -> Result<(), ZeusError> {
        self.require_session(user)?;
        if self.vm().msg_sender() != self.session_guardian.getter(user).get() {
            return Err(ZeusError::NotGuardian(NotGuardian {}));
        }
        let risk = self.approval_risk.getter(user).getter(spender).get().to::<u64>();
        self.approval_revoked.setter(user).setter(spender).set(true);
        self.vm().log(ApprovalRevoked { user, spender, risk_x100: risk });
        Ok(())
    }

    /// Consulta do firewall: esta transacao passa? (usada pelo agente antes do sign)
    pub fn check_tx(&self, user: Address, amount: U256, risk_x100: U256) -> Result<(), ZeusError> {
        self.require_session(user)?;
        if self.session_frozen.getter(user).get() {
            return Err(ZeusError::SessionFrozen(SessionFrozenError {}));
        }
        if risk_x100.to::<u64>() >= RISK_BLOCK_X100 {
            return Err(ZeusError::TooRisky(TooRisky { risk_x100: risk_x100.to::<u64>(), threshold: RISK_BLOCK_X100 }));
        }
        let cap = self.session_cap.getter(user).get();
        let spent = self.current_daily_spent(user);
        let remaining = cap.saturating_sub(spent);
        if U128::from(amount.to::<u128>()) > remaining {
            return Err(ZeusError::AboveDailyCap(AboveDailyCap { requested: amount, remaining: U256::from(remaining.to::<u128>()) }));
        }
        Ok(())
    }

    /// Cofre (x402/MPP friendly): o valor fica retido pela janela de desafio.
    pub fn escrow_payment(&mut self, payment_id: B256, payee: Address, amount: U256, risk_x100: U256) -> Result<(), ZeusError> {
        let user = self.vm().msg_sender();
        self.require_session(user)?;
        if self.session_frozen.getter(user).get() {
            return Err(ZeusError::SessionFrozen(SessionFrozenError {}));
        }
        if self.payment_exists.getter(payment_id).get() {
            return Err(ZeusError::PaymentIdInUse(PaymentIdInUse {}));
        }
        self.consume_daily_cap(user, amount)?;

        self.payment_exists.setter(payment_id).set(true);
        self.payment_from.setter(payment_id).set(user);
        self.payment_payee.setter(payment_id).set(payee);
        self.payment_amount.setter(payment_id).set(amount);
        let release_at = self.vm().block_timestamp() + self.session_window.getter(user).get().to::<u64>();
        self.payment_release_at.setter(payment_id).set(U64::from(release_at));
        self.payment_released.setter(payment_id).set(false);
        self.payment_disputed.setter(payment_id).set(false);
        self.vm().log(PaymentEscrowed { payment_id, payer: user, payee, amount, release_at });
        // Cofre USDG nativo: se a sessao tem token configurado, o valor e retenido DE VERDADE.
        let usdg = self.session_usdg.getter(user).get();
        if usdg != Address::ZERO {
            let here = self.vm().contract_address();
            let data = IERC20::transferFromCall { from: user, to: here, amount }.abi_encode();
            let result = unsafe {
                RawCall::new(self.vm()).gas(u64::MAX).flush_storage_cache().call(usdg, &data)
            };
            let out = result.map_err(|_| ZeusError::TokenTransferFailed(TokenTransferFailed { returned: false }))?;
            let ok: bool = IERC20::transferFromCall::abi_decode_returns(&out)
                .map_err(|_| ZeusError::TokenTransferFailed(TokenTransferFailed { returned: false }))?;
            if !ok {
                return Err(ZeusError::TokenTransferFailed(TokenTransferFailed { returned: false }));
            }
        }
        Ok(())
    }

    /// O guardiao contesta um pagamento suspeito dentro da janela.
    pub fn dispute_payment(&mut self, payment_id: B256) -> Result<(), ZeusError> {
        if !self.payment_exists.getter(payment_id).get() {
            return Err(ZeusError::UnknownPayment(UnknownPayment {}));
        }
        let payer = self.payment_from.getter(payment_id).get();
        if self.vm().msg_sender() != self.session_guardian.getter(payer).get() {
            return Err(ZeusError::NotGuardian(NotGuardian {}));
        }
        self.payment_disputed.setter(payment_id).set(true);
        self.vm().log(PaymentContested { payment_id, guardian: self.vm().msg_sender() });
        Ok(())
    }

    /// Liberacao: apos a janela sem disputa, ou a qualquer momento pelo dono.
    pub fn release_payment(&mut self, payment_id: B256) -> Result<(), ZeusError> {
        if !self.payment_exists.getter(payment_id).get() {
            return Err(ZeusError::UnknownPayment(UnknownPayment {}));
        }
        if self.payment_released.getter(payment_id).get() {
            return Err(ZeusError::AlreadyReleased(AlreadyReleased {}));
        }
        if self.payment_disputed.getter(payment_id).get() {
            return Err(ZeusError::PaymentDisputed(PaymentDisputed {}));
        }
        let payer = self.payment_from.getter(payment_id).get();
        if self.vm().msg_sender() != payer
            && self.vm().block_timestamp() < self.payment_release_at.getter(payment_id).get().to::<u64>()
        {
            return Err(ZeusError::ChallengeWindowOpen(ChallengeWindowOpen {}));
        }
        self.payment_released.setter(payment_id).set(true);
        let usdg = self.session_usdg.getter(payer).get();
        if usdg != Address::ZERO {
            let payee = self.payment_payee.getter(payment_id).get();
            let amount = self.payment_amount.getter(payment_id).get();
            let data = IERC20::transferCall { to: payee, amount }.abi_encode();
            let result = unsafe {
                RawCall::new(self.vm()).gas(u64::MAX).flush_storage_cache().call(usdg, &data)
            };
            let out = result.map_err(|_| ZeusError::TokenTransferFailed(TokenTransferFailed { returned: false }))?;
            let ok: bool = IERC20::transferCall::abi_decode_returns(&out)
                .map_err(|_| ZeusError::TokenTransferFailed(TokenTransferFailed { returned: false }))?;
            if !ok {
                return Err(ZeusError::TokenTransferFailed(TokenTransferFailed { returned: false }));
            }
        }
        self.vm().log(PaymentReleased {
            payment_id,
            payee: self.payment_payee.getter(payment_id).get(),
            amount: self.payment_amount.getter(payment_id).get(),
        });
        Ok(())
    }

    /// Disjuntor: ataque em andamento congela a sessao inteira.
    pub fn emergency_freeze(&mut self, user: Address) -> Result<(), ZeusError> {
        self.require_session(user)?;
        let sender = self.vm().msg_sender();
        if sender != self.session_guardian.getter(user).get() && sender != self.session_owner.getter(user).get() {
            return Err(ZeusError::NotGuardian(NotGuardian {}));
        }
        self.session_frozen.setter(user).set(true);
        self.vm().log(SessionFrozen { user, by: sender });
        Ok(())
    }

    /// Rearme manual pelo dono quando o perigo passou.
    pub fn unfreeze(&mut self) -> Result<(), ZeusError> {
        let user = self.vm().msg_sender();
        self.require_session(user)?;
        if self.session_owner.getter(user).get() != user {
            return Err(ZeusError::NotSessionOwner(NotSessionOwner {}));
        }
        self.session_frozen.setter(user).set(false);
        self.vm().log(SessionUnfrozen { user, by: user });
        Ok(())
    }

    /// Telemetria da sessao (para o dashboard Dune e o app do guardiao).
    pub fn session_exists(&self, user: Address) -> bool {
        self.session_exists.getter(user).get()
    }

    pub fn session_owner_pub(&self, user: Address) -> Result<Address, ZeusError> {
        self.require_session(user)?;
        Ok(self.session_owner.getter(user).get())
    }

    pub fn session_guardian_pub(&self, user: Address) -> Result<Address, ZeusError> {
        self.require_session(user)?;
        Ok(self.session_guardian.getter(user).get())
    }

    pub fn session_frozen_pub(&self, user: Address) -> Result<bool, ZeusError> {
        self.require_session(user)?;
        Ok(self.session_frozen.getter(user).get())
    }

    pub fn session_window_pub(&self, user: Address) -> Result<u64, ZeusError> {
        self.require_session(user)?;
        Ok(self.session_window.getter(user).get().to::<u64>())
    }

    pub fn session_cap_pub(&self, user: Address) -> Result<U256, ZeusError> {
        self.require_session(user)?;
        Ok(U256::from(self.session_cap.getter(user).get().to::<u128>()))
    }

    /// Configura o token USDG da sessao (dono apenas). address(0) = modo ledger.
    pub fn set_usdg_token(&mut self, usdg: Address) -> Result<(), ZeusError> {
        let user = self.vm().msg_sender();
        self.require_session(user)?;
        if self.session_owner.getter(user).get() != user {
            return Err(ZeusError::NotSessionOwner(NotSessionOwner {}));
        }
        self.session_usdg.setter(user).set(usdg);
        self.vm().log(UsdgTokenSet { user, usdg });
        Ok(())
    }

    /// Token USDG configurado na sessao (address(0) = modo ledger puro).
    pub fn usdg_token_pub(&self, user: Address) -> Result<Address, ZeusError> {
        self.require_session(user)?;
        Ok(self.session_usdg.getter(user).get())
    }

    /// Guardiao devolve ao dono o valor de um pagamento contestado (cofre real).
    pub fn refund_disputed(&mut self, payment_id: B256) -> Result<(), ZeusError> {
        if !self.payment_exists.getter(payment_id).get() {
            return Err(ZeusError::UnknownPayment(UnknownPayment {}));
        }
        if self.payment_released.getter(payment_id).get() {
            return Err(ZeusError::AlreadyReleased(AlreadyReleased {}));
        }
        if self.payment_refunded.getter(payment_id).get() {
            return Err(ZeusError::AlreadyRefunded(AlreadyRefunded {}));
        }
        if !self.payment_disputed.getter(payment_id).get() {
            return Err(ZeusError::NotDisputed(NotDisputed {}));
        }
        let payer = self.payment_from.getter(payment_id).get();
        if self.vm().msg_sender() != self.session_guardian.getter(payer).get() {
            return Err(ZeusError::NotGuardian(NotGuardian {}));
        }
        let amount = self.payment_amount.getter(payment_id).get();
        self.payment_refunded.setter(payment_id).set(true);
        let usdg = self.session_usdg.getter(payer).get();
        if usdg != Address::ZERO {
            let data = IERC20::transferCall { to: payer, amount }.abi_encode();
            let result = unsafe {
                RawCall::new(self.vm()).gas(u64::MAX).flush_storage_cache().call(usdg, &data)
            };
            let out = result.map_err(|_| ZeusError::TokenTransferFailed(TokenTransferFailed { returned: false }))?;
            let ok: bool = IERC20::transferCall::abi_decode_returns(&out)
                .map_err(|_| ZeusError::TokenTransferFailed(TokenTransferFailed { returned: false }))?;
            if !ok {
                return Err(ZeusError::TokenTransferFailed(TokenTransferFailed { returned: false }));
            }
        }
        self.vm().log(PaymentRefunded { payment_id, payer, amount });
        Ok(())
    }
}

impl ZeusGuard {
    fn consume_daily_cap(&mut self, user: Address, amount: U256) -> Result<(), ZeusError> {
        let cap = self.session_cap.getter(user).get();
        let now = self.vm().block_timestamp();
        let spent = self.current_daily_spent(user);
        let remaining = cap.saturating_sub(spent);
        if U128::from(amount.to::<u128>()) > remaining {
            return Err(ZeusError::AboveDailyCap(AboveDailyCap { requested: amount, remaining: U256::from(remaining.to::<u128>()) }));
        }
        let ws = self.daily_window_start.getter(user).get().to::<u64>();
        if ws == 0 || now.saturating_sub(ws) >= 86400 {
            self.daily_window_start.setter(user).set(U64::from(now));
            self.daily_spent.setter(user).set(U128::from(0));
        }
        let new_spent = self.daily_spent.getter(user).get() + U128::from(amount.to::<u128>());
        self.daily_spent.setter(user).set(new_spent);
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn janela_minima_de_desafio_sempre_aplicada() {
        assert_eq!(effective_window(0), 120);
        assert_eq!(effective_window(60), 120);
        assert_eq!(effective_window(500), 500);
    }

    #[test]
    fn gasto_diario_expira_em_24h() {
        let spent = U128::from(100u64);
        assert_eq!(spent_in_window(0, 5000, spent), U128::ZERO);            // janela nunca iniciada
        assert_eq!(spent_in_window(1000, 1000 + 86399, spent), spent);      // dentro da janela
        assert_eq!(spent_in_window(1000, 1000 + 86400, spent), U128::ZERO); // expirou (saturating)
    }

    #[test]
    fn constantes_de_politica_estaveis() {
        assert_eq!(MIN_CHALLENGE_WINDOW, 120); // segundos
        assert_eq!(RISK_BLOCK_X100, 6000);      // score >= 60% = drainer
    }
    #[test]
    fn janela_efetiva_e_monotona() {
        // nunca abaixo do minimo, nunca reduz uma janela maior
        assert!(effective_window(u64::MAX - 1) >= MIN_CHALLENGE_WINDOW);
        assert_eq!(effective_window(MIN_CHALLENGE_WINDOW), MIN_CHALLENGE_WINDOW);
        assert_eq!(effective_window(MIN_CHALLENGE_WINDOW + 1), MIN_CHALLENGE_WINDOW + 1);
    }

    #[test]
    fn gasto_diario_borda_de_janela() {
        let spent = U128::from(1000u64);
        // exatamente o limite 86399s: ainda dentro
        assert_eq!(spent_in_window(100, 100 + 86399, spent), spent);
        // janela nunca iniciada (ws=0) nunca conta gasto antigo
        assert_eq!(spent_in_window(0, u64::MAX, spent), U128::ZERO);
        // agora ANTERIOR ao inicio (saturating): trata como dentro? nao - 0-100 saturates to 0 < 86400 => conta
        assert_eq!(spent_in_window(500, 100, spent), spent);
    }

    #[test]
    fn teto_padrao_e_um_mil_usdg() {
        // DAILY_CAP_DEFAULT = 1000 USDG em 18 decimais
        assert_eq!(DAILY_CAP_DEFAULT, 1000 * 10_u128.pow(18));
    }

    #[test]
    fn limiar_de_bloqueio_e_sesenta_porcento() {
        // o contrato bloqueia em >= 6000 (x100). Espelha o mirror JS da demo.
        assert!(RISK_BLOCK_X100 >= 6000);
        assert_eq!(RISK_BLOCK_X100 % 100, 0);
    }

}
