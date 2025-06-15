# Autonomous AI Enterprise

Este projeto é uma simulação de um sistema de IA projetado para atuar como um "empreendedor autônomo".
O objetivo é que a IA possa identificar oportunidades de mercado e sugerir planos de monetização.

## Módulo Atual: Agente de Pesquisa de Mercado

O primeiro componente desenvolvido é o `Agente de Pesquisa de Mercado e Identificação de Oportunidades`.
Este agente simula a coleta de dados de mercado e, com base nesses dados, sugere uma oportunidade de negócio e um plano de monetização básico.

## Como Executar

1.  **Pré-requisitos:**
    *   Python 3.x instalado.

2.  **Configuração do Ambiente (Opcional, mas recomendado):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate
    ```

3.  **Instalar Dependências:**
    Navegue até a raiz do projeto (`autonomous_ai_enterprise`) e execute:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Executar o Agente de Pesquisa de Mercado:**
    A partir da raiz do projeto (`autonomous_ai_enterprise`), execute o script principal do agente:
    ```bash
    python -m src.market_research_agent.main
    ```
    Isso executará o agente com o domínio padrão configurado em `config/settings.py`.

## Estrutura do Projeto

*   `src/`: Contém o código fonte principal da aplicação.
    *   `market_research_agent/`: Módulo do agente de pesquisa de mercado.
        *   `main.py`: Script principal do agente.
    *   `utils/`: Utilitários, como o simulador de dados.
        *   `data_simulator.py`: Simula a coleta de dados de mercado.
*   `config/`: Arquivos de configuração.
    *   `settings.py`: Configurações da aplicação (ex: domínio padrão).
*   `data/`: Diretório para armazenar dados (atualmente vazio).
*   `reports/`: Diretório para armazenar relatórios gerados (atualmente vazio).
*   `requirements.txt`: Lista de dependências Python do projeto.
*   `README.md`: Este arquivo.
