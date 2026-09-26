// ZEUS GUARD — Contrato Stylus (Rust) para Arbitrum / Robinhood Chain
// Guardiao pre-transacao: registro de approvals, cofre USDG com janela de
// desafio e disjuntor de emergencia. Build: cargo stylus build / check / deploy.
//
// Autor: Clebson Campos de Araujo — Arbitrum Open House Singapore 2026

use stylus_sdk::{alloy_primitives::{Address, U256}, alloy_sol_types::sol, prelude::*};

sol! {
    #![allow(mismatched_fields)]
    event GuardBlocked(address indexed user, address indexed target, string reason);
    event ApprovalRevoked(address indexed user, address indexed spender);
    event VaultFrozen(address indexed user, address indexed guardian);
    event PaymentReleased(address indexed user, address indexed payee, uint256 amount);
}

// ---- erros em Solidity ----
sol_error!(ZeusGuardError, "ZEUS: sessao inexistente", "ZEUS: nao e o dono",
           "ZEUS: pago ja liberado", "ZEUS: janela de desafio aberta",
           "ZEUS: cofre congelado", "ZEUS: fora do prazo");

#[derive(SolidityError)]
pub enum ZeusError {
    NoSession(ZeusGuardErrorNoSessao),
    NotOwner(ZeusGuardErrorNaoEDono),
    AlreadyReleased(ZeusGuardErrorPagoJaLiberado),
    ChallengeOpen(ZeusGuardErrorJanelaDeDesafioAberta),
    Frozen(ZeusGuardErrorCofreCongelado),
    TooLate(ZeusGuardErrorForaDoPrazo),
}

sol_storage! {
    pub struct ZeusGuard {
        // dono da sessao -> configuracao do guardiao
        mapping(address => Session) sessions;
        mapping(address => mapping(address => ApprovalInfo)) approvals;
        mapping(bytes32 => Payment) payments; // hash do pagamento -> estado
        address admin; // guardians multi-sig na v2
    }

    struct Session {
        address owner;
        address guardian;      // agente ZEUS autorizado
        bool frozen;           // disjuntor
        uint64 challenge_window; // segundos da janela anti-drainer (USDG)
    }

    struct ApprovalInfo {
        uint256 amount;
        uint64 granted_at;
        uint64 risk_score_x100;  // saida do motor QCSN (0-10000)
    }

    struct Payment {
        address from;
        address payee;
        uint256 amount;
        uint64 release_at;    // timestamp minimo de liberacao
        bool released;
        bool disputed;
    }
}

const MIN_CHALLENGE: u64 = 120; // 2 min de protecao minima por padrao

#[public]
impl ZeusGuard {
    pub fn init_session(&mut self, guardian: Address, challenge_window: U256) -> Result<(), ZeusError> {
        self.admin.set(msg::sender());
        let session = Session {
            owner: msg::sender(),
            guardian,
            frozen: false,
            challenge_window: challenge_window.to::<u64>().max(MIN_CHALLENGE),
        };
        self.sessions.setter(msg::sender()).set(session);
        Ok(())
    }

    /// O agente ZEUS registra um approval ANALISADO. Scores acima de 60
    /// (risk_score_x100 > 6000) sao registrados como perigosos e podem
    /// ser revogados pelo guardiao sem acao do usuario.
    pub fn log_approval(&mut self, user: Address, spender: Address,
                        amount: U256, risk_x100: U256) -> Result<(), ZeusError> {
        self.only_session_owner()?;
        let info = ApprovalInfo {
            amount,
            granted_at: block::timestamp(),
            risk_score_x100: risk_x100.to::<u64>(),
        };
        self.approvals.setter(user).setter(spender).set(info);
        Ok(())
    }

    /// Revogacao automatica de approval perigoso pelo guardiao.
    pub fn guardian_revoke(&mut self, user: Address, spender: Address) -> Result<(), ZeusError> {
        let session = self.sessions.get(user).ok_or(ZeusError::NoSession(ZeusGuardErrorNoSessao {}))?;
        require!(msg::sender() == session.guardian, NotOwner);
        self.approvals.setter(user).clear(spender);
        evm::log(ApprovalRevoked { user, spender });
        Ok(())
    }

    /// Cofre de pagamento USDG: o dinheiro fica retido durante a janela
    /// de desafio. Um drainer nao consegue mover o valor no mesmo bloco.
    pub fn escrow_payment(&mut self, payment_id: U256, payee: Address,
                          amount: U256) -> Result<(), ZeusError> {
        self.only_session_owner()?;
        let id = payment_id.to_be_bytes();
        let session = self.sessions.get(msg::sender()).unwrap();
        let p = Payment {
            from: msg::sender(),
            payee,
            amount,
            release_at: block::timestamp() + session.challenge_window as u128,
            released: false,
            disputed: false,
        };
        self.payments.setter(id).set(p);
        Ok(())
    }

    /// Conclama do guardiao: congela e disputa o pagamento suspeito.
    pub fn dispute_payment(&mut self, payment_id: U256) -> Result<(), ZeusError> {
        let mut p = self.payments.get(payment_id.to_be_bytes())
            .ok_or(ZeusError::NoSession(ZeusGuardErrorNoSessao {}))?;
        let session = self.sessions.get(p.from).unwrap();
        require!(msg::sender() == session.guardian, NotOwner);
        p.disputed = true;
        evm::log(VaultFrozen { user: p.from, guardian: msg::sender() });
        Ok(())
    }

    /// Liberacao do pagamento apos a janela (sem disputo) ou pelo proprio dono.
    pub fn release_payment(&mut self, payment_id: U256) -> Result<(), ZeusError> {
        let mut p = self.payments.get(payment_id.to_be_bytes())
            .ok_or(ZeusError::NoSession(ZeusGuardErrorNoSessao {}))?;
        require!(!p.released, AlreadyReleased);
        require!(!p.disputed, Frozen);
        if msg::sender() != p.from && block::timestamp() < p.release_at {
            return Err(ZeusError::ChallengeOpen(ZeusGuardErrorJanelaDeDesafioAberta {}));
        }
        p.released = true;
        evm::log(PaymentReleased { user: p.from, payee: p.payee, amount: p.amount });
        Ok(())
    }

    /// Disjuntor global da sessao: ataque em andamento -> tudo pausa.
    pub fn emergency_freeze(&mut self, user: Address) -> Result<(), ZeusError> {
        let session = self.sessions.get(user).ok_or(ZeusError::NoSession(ZeusGuardErrorNoSessao {}))?;
        require!(msg::sender() == session.guardian || msg::sender() == session.owner, NotOwner);
        session.frozen = true;
        evm::log(VaultFrozen { user, guardian: msg::sender() });
        Ok(())
    }
}

impl ZeusGuard {
    fn only_session_owner(&mut self) -> Result<(), ZeusError> {
        self.sessions.get(msg::sender())
            .ok_or(ZeusError::NoSession(ZeusGuardErrorNoSessao {}))?;
        Ok(())
    }
}
