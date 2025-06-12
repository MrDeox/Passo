# Empresa Digital Autônoma (EDA) - Nova Versão

Este projeto visa criar uma empresa digital autônoma, onde todos os principais setores são automatizados utilizando Inteligência Artificial. O sistema é projetado para operar como uma empresa real: capaz de criar, validar, lançar, divulgar e vender novos produtos ou serviços digitais de forma contínua e automatizada, tudo rodando em Python.

A versão anterior do projeto, que serviu como aprendizado e prototipagem, foi arquivada na pasta `versao_antiga/`.

## Visão Geral da Arquitetura

O núcleo do sistema reside no diretório `src/` e é organizado nos seguintes módulos principais:

-   **`src/core/`**: Contém as entidades centrais da empresa (estado, ideias, produtos, serviços, tarefas, eventos) e configurações.
-   **`src/agents/`**: Define os diferentes agentes de IA (Criativo, Validador, Executor, Marketing, Financeiro, CEC) responsáveis por executar as operações da empresa.
-   **`src/workflows/`**: Orquestra os processos de negócios, como ideação, desenvolvimento de produtos e entrega de serviços, coordenando as ações dos agentes.
-   **`src/products/`**: Lógica específica para a gestão do ciclo de vida de produtos digitais.
-   **`src/services/`**: Lógica específica para a definição, oferta e entrega de serviços.
-   **`src/finance/`**: Módulo para gerenciamento financeiro, transações e relatórios.
-   **`src/marketing/`**: Ferramentas e lógica para campanhas de marketing e geração de conteúdo.
-   **`src/api/`**: Uma API FastAPI para interação externa, monitoramento e controle da simulação/empresa.
-   **`src/utils/`**: Funções auxiliares, integração com LLMs e carregamento de configurações.
-   **`src/main.py`**: Ponto de entrada principal para iniciar e executar a simulação da empresa.
-   **`src/config.py`**: Configurações padrão do projeto.

## Objetivos do Projeto

-   **Autonomia**: Capacidade da empresa operar com mínima intervenção humana.
-   **Ciclo de Vida Completo**: Automatizar desde a concepção da ideia até a venda e o pós-venda.
-   **Modularidade e Escalabilidade**: Construir um sistema flexível que possa ser expandido com novos agentes, workflows e funcionalidades.
-   **Integração com IA**: Utilizar LLMs e outras técnicas de IA para tomada de decisão, execução de tarefas e criatividade.
-   **Simulação e Realidade**: Embora comece como uma simulação, o objetivo é evoluir para uma plataforma capaz de operar negócios reais.

## Como Começar (Placeholder)

1.  **Configuração do Ambiente:**
    ```text
    # Crie e ative um ambiente virtual (ex: venv)
    # python -m venv venv
    # source venv/bin/activate # ou venv\Scripts\activate no Windows
    # pip install -r requirements.txt
    # (requirements.txt a ser criado)
    ```

2.  **Configurar Variáveis de Ambiente:**
    -   Copie `.env.example` para `.env` (a ser criado).
    -   Preencha as chaves de API para os LLMs (ex: `OPENAI_API_KEY`).

3.  **Executar a Simulação:**
    ```text
    # python src/main.py --cycles 10
    # (ou outros parâmetros)
    ```

4.  **Acessar a API (se rodando):**
    -   A API estará disponível em `http://localhost:8000` (Uvicorn).

## Contribuindo

Consulte `CONTRIBUTING.md` (a ser criado) para diretrizes de contribuição.

## Roadmap

Veja o arquivo `ROADMAP.md` para os próximos passos e funcionalidades planejadas.

## Melhores Práticas

Consulte o arquivo `BEST_PRACTICES.md` para dicas sobre como manter o projeto organizado e escalável.

---
*Este projeto é uma exploração ambiciosa no campo da automação empresarial com IA.*
