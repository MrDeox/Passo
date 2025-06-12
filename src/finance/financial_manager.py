from typing import Any, Optional, Dict, List
from enum import Enum
import time
import uuid
from dataclasses import dataclass, field # Adicionado para Transaction

# from src.core.company_state import CompanyState
# from src.core.event import Event

class TransactionType(Enum):
    INCOME = "RECEITA"
    EXPENSE = "DESPESA"
    INVESTMENT = "INVESTIMENTO"
    SALARY = "SALÁRIO"

@dataclass
class Transaction:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    type: TransactionType
    description: str
    amount: float # Positivo para income, negativo para expense
    category: Optional[str] = None # Ex: "Venda Produto X", "Custo Servidor", "Marketing Ads"
    related_item_id: Optional[str] = None # ID do produto, serviço, campanha, etc.

class FinancialManager:
    """
    Gerencia as transações financeiras, o balanço e orçamentos.
    """
    def __init__(self, company_state: Any):
        self.company_state = company_state

    def record_transaction(self, type: TransactionType, description: str, amount: float, category: Optional[str] = None, related_item_id: Optional[str] = None) -> Transaction:
        """
        Registra uma transação financeira e atualiza o balanço da empresa.
        Amount é positivo para receitas e negativo para despesas.
        """
        transaction = Transaction(
            type=type,
            description=description,
            amount=amount,
            category=category,
            related_item_id=related_item_id
        )

        if not hasattr(self.company_state, 'transactions'):
            self.company_state.transactions = []

        self.company_state.transactions.append(transaction)

        # Atualiza o balanço
        # Assume amount is positive for INCOME, and for EXPENSE types it represents the cost magnitude
        if type == TransactionType.INCOME:
            self.company_state.balance += amount
        elif type in [TransactionType.EXPENSE, TransactionType.SALARY, TransactionType.INVESTMENT]:
             self.company_state.balance -= abs(amount) # Deduct the absolute amount for expenses

        self.company_state.log_event(
            event_type="FINANCIAL_TRANSACTION_RECORDED",
            description=f"Transação: {transaction.type.value} de {transaction.amount:.2f} ({transaction.description})",
            payload=transaction.__dict__,
            source="FinancialManager"
        )
        print(f"[FinancialManager] Transação registrada: {transaction.id} - {transaction.type.value} {transaction.amount:.2f} ({transaction.description}). Novo balanço: {self.company_state.balance:.2f}")
        return transaction

    def calculate_profit_loss(self, period_start: Optional[float] = None, period_end: Optional[float] = None) -> Dict[str, float]:
        """
        Calcula o lucro/prejuízo em um determinado período.
        Se os períodos não forem fornecidos, calcula sobre todas as transações.
        """
        total_income = 0.0
        total_expense = 0.0

        # Ensure transactions list exists
        transactions_to_consider = getattr(self.company_state, 'transactions', [])

        if period_start or period_end:
            transactions_to_consider = [
                t for t in transactions_to_consider
                if (not period_start or t.timestamp >= period_start) and                    (not period_end or t.timestamp <= period_end)
            ]

        for t in transactions_to_consider:
            if t.type == TransactionType.INCOME:
                total_income += t.amount # Assume positive amount for income
            elif t.type in [TransactionType.EXPENSE, TransactionType.SALARY, TransactionType.INVESTMENT]:
                total_expense += abs(t.amount)

        profit = total_income - total_expense
        print(f"[FinancialManager] Lucro/Prejuízo calculado: Receita={total_income:.2f}, Despesa={total_expense:.2f}, Resultado={profit:.2f}")
        return {"total_income": total_income, "total_expense": total_expense, "profit_or_loss": profit}
