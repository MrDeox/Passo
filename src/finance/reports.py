from typing import Any, List, Dict, Optional
# from src.core.company_state import CompanyState
from .financial_manager import TransactionType # Import local

class FinancialReports:
    """
    Gera relatórios financeiros com base no estado da empresa.
    """
    def __init__(self, company_state: Any):
        self.company_state = company_state

    def generate_balance_sheet(self) -> Dict[str, Any]:
        """
        Gera um balanço patrimonial simplificado.
        """
        assets = {"cash": self.company_state.balance, "other_simulated_assets": 0}
        liabilities = {"simulated_debts": 0}
        equity = assets["cash"] + assets["other_simulated_assets"] - liabilities["simulated_debts"]

        report = {
            "report_type": "Balance Sheet (Simplified)",
            "timestamp": self.company_state.current_time,
            "assets": assets,
            "liabilities": liabilities,
            "equity": equity
        }
        print(f"[FinancialReports] Balanço Patrimonial gerado. Patrimônio Líquido: {equity:.2f}")
        self.company_state.log_event("FINANCIAL_REPORT_GENERATED", "Balanço Patrimonial gerado.", report, "FinancialReports")
        return report

    def generate_income_statement(self, period_start: Optional[float] = None, period_end: Optional[float] = None) -> Dict[str, Any]:
        """
        Gera uma demonstração de resultados (DRE) para um período.
        """
        total_income = 0.0
        total_expense = 0.0

        transactions_to_consider = getattr(self.company_state, 'transactions', [])
        if period_start or period_end:
            transactions_to_consider = [
                t for t in transactions_to_consider
                if (not period_start or t.timestamp >= period_start) and                    (not period_end or t.timestamp <= period_end)
            ]

        for t in transactions_to_consider:
            if t.type == TransactionType.INCOME:
                total_income += t.amount
            elif t.type in [TransactionType.EXPENSE, TransactionType.SALARY, TransactionType.INVESTMENT]:
                total_expense += abs(t.amount)

        net_income = total_income - total_expense

        report = {
            "report_type": "Income Statement",
            "period_start": period_start or "all_time",
            "period_end": period_end or self.company_state.current_time,
            "total_revenue": total_income,
            "total_expenses": total_expense,
            "net_income": net_income
        }
        print(f"[FinancialReports] DRE gerado. Resultado Líquido: {net_income:.2f}")
        self.company_state.log_event("FINANCIAL_REPORT_GENERATED", "Demonstração de Resultados gerada.", report, "FinancialReports")
        return report
