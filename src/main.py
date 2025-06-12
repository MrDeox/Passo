import argparse
import asyncio
import time

from src.core.company_state import CompanyState
from src.core.company_settings import CompanySettings
from src.utils.settings_loader import load_app_settings
from src.utils.llm_integration import LLMIntegration
# Importar managers e workflows principais conforme necessário para a simulação
# from src.products.product_manager import ProductManager
# from src.services.service_manager import ServiceManager
# from src.finance.financial_manager import FinancialManager, TransactionType # Import TransactionType if used
# from src.marketing.campaign_manager import CampaignManager
# from src.workflows.ideation_workflow import IdeationWorkflow # Consider moving import if only used in one place
# from src.agents.cec_agent import CECAgent # Exemplo de agente inicial

async def run_simulation_cycle(company_state: CompanyState, llm_integration: LLMIntegration):
    """
    Executa um único ciclo da simulação.
    """
    company_state.advance_cycle()
    print(f"--- Iniciando Ciclo {company_state.current_cycle} ---")

    # 1. Lógica de Planejamento Estratégico (ex: CECAgent define metas)
    # cec_agent = company_state.agents.get("CEC") # Supondo que o CEC foi adicionado
    # if cec_agent:
    #     await cec_agent.perform_task()
    # else:
    #     print("ALERTA: CECAgent não encontrado.")

    # 2. Executar Workflows (ex: IdeationWorkflow)
    # from src.workflows.ideation_workflow import IdeationWorkflow # Import localmente ou no topo se usado em mais lugares
    # ideation_wf_id = f"ideation_cycle_{company_state.current_cycle}"
    # print(f"Criando IdeationWorkflow com ID: {ideation_wf_id}")
    # ideation_wf = IdeationWorkflow(workflow_id=ideation_wf_id, company_state=company_state)
    # await ideation_wf.run()
    # print(f"IdeationWorkflow status: {ideation_wf.status.value}")

    # 3. Agentes executam tarefas atribuídas
    # (Lógica para iterar sobre agentes e fazer com que executem tarefas pendentes)
    # if hasattr(company_state, 'agents') and company_state.agents: # Check if agents attribute exists and is not empty
    #    for agent_name, agent in company_state.agents.items():
    #        # Example: only run if agent has a task or for specific roles that act proactively
    #        # if agent.current_task or agent.role in ["CreativeAgent", "ValidationAgent"]:
    #        print(f"Agente {agent.name} ({agent.role}) verificando tarefas...")
    #        # await agent.perform_task() # This would need more logic to assign/pick tasks
    # else:
    #    print("Nenhum agente definido no company_state.agents ou o atributo não existe.")


    # 4. Atualizar finanças, marketing, etc.
    # from src.finance.financial_manager import FinancialManager, TransactionType # Import localmente ou no topo
    # financial_manager = FinancialManager(company_state)
    # financial_manager.record_transaction(TransactionType.EXPENSE, "Custos Operacionais do Ciclo", 100.0, "Operacional")


    # Exemplo placeholder: Simular alguma atividade
    await asyncio.sleep(0.1) # Simula trabalho sendo feito

    print(f"--- Fim do Ciclo {company_state.current_cycle} ---")
    print(f"Balanço da Empresa: {company_state.balance:.2f}")
    print(f"Total de Ideias: {len(company_state.ideas)}")
    print(f"Total de Tarefas: {len(company_state.tasks)}")


async def main(args):
    """
    Ponto de entrada principal da simulação.
    """
    print("Iniciando a Empresa Digital Autônoma...")

    # Carregar configurações
    app_config_dict = load_app_settings() # De src.utils.settings_loader

    company_settings = CompanySettings(
        company_name=app_config_dict.get("COMPANY_NAME", "EDA (Main)"),
        starting_balance=float(app_config_dict.get("STARTING_BALANCE", 50000.0)),
        llm_provider=app_config_dict.get("LLM_PROVIDER", "mock"),
        default_llm_model=app_config_dict.get("DEFAULT_LLM_MODEL", "mock_model")
        # Adicionar outras configurações conforme necessário
    )
    print(f"Configurações da Empresa: {company_settings.company_name}, Provider LLM: {company_settings.llm_provider}")

    # Inicializar estado da empresa e integrações
    company_state = CompanyState(settings=company_settings)
    llm_integration = LLMIntegration(settings=company_settings) # Passar settings para llm_integration

    # TODO: Inicializar agentes, managers, etc. e adicioná-los ao company_state se necessário
    # Exemplo:
    # from typing import Dict # Import Dict for type hinting
    # from src.agents.base_agent import BaseAgent # For type hinting if used
    # from src.agents.cec_agent import CECAgent
    # # Ensure company_state.agents is initialized if you plan to add agents
    # if not hasattr(company_state, 'agents'): # Checa se o atributo existe
    #    company_state.agents: Dict[str, BaseAgent] = {} # Define e tipa o atributo
    #
    # cec = CECAgent(name="CEC-001", company_state=company_state, llm_integration=llm_integration)
    # company_state.agents[cec.name] = cec

    num_cycles = args.cycles
    if num_cycles == 0: # Modo infinito
        print("Executando simulação em modo infinito. Pressione Ctrl+C para parar.")
        try:
            while True:
                await run_simulation_cycle(company_state, llm_integration)
                await asyncio.sleep(args.delay)
        except KeyboardInterrupt:
            print("\nSimulação interrompida pelo usuário.")
    else:
        print(f"Executando simulação por {num_cycles} ciclos.")
        for i in range(num_cycles):
            print(f"\nIniciando ciclo de simulação {i+1}/{num_cycles}") # Mensagem adicionada
            await run_simulation_cycle(company_state, llm_integration)
            if i < num_cycles - 1:
                 await asyncio.sleep(args.delay)


    print("\nSimulação concluída.")
    print(f"Estado Final: Ciclo={company_state.current_cycle}, Balanço={company_state.balance:.2f}")
    # TODO: Salvar estado final da simulação

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Executa a simulação da Empresa Digital Autônoma.")
    parser.add_argument(
        "--cycles",
        type=int,
        default=5,
        help="Número de ciclos de simulação a executar. 0 para modo infinito."
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.2, # Default delay reduzido
        help="Delay em segundos entre os ciclos (usado principalmente no modo infinito ou para observação)."
    )
    # Adicionar outros argumentos conforme necessário (ex: --config-file)

    parsed_args = parser.parse_args() # Renomeado para parsed_args

    try:
        asyncio.run(main(parsed_args)) # Usar parsed_args
    except KeyboardInterrupt:
        print("\nExecução principal interrompida.")
    finally:
        print("Encerrando EDA.")
