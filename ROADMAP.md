# Roadmap do Projeto EDA (Empresa Digital Autônoma)

Este roadmap delineia as fases e funcionalidades planejadas para o desenvolvimento da Empresa Digital Autônoma.

## Fase 1: Fundação e Simulação Básica (Em Progresso)

-   [X] **Estrutura do Projeto**: Definir arquitetura de pastas e módulos em `src/`.
-   [X] **Agentes de IA Fundamentais**: Esqueletos para `CreativeAgent`, `ValidationAgent`, `ExecutionAgent`, `MarketingAgent`, `FinancialAgent`, `CECAgent`.
-   [X] **Core do Sistema**: Entidades centrais (`CompanyState`, `Idea`, `Product`, `Service`, `Task`, `Event`, `CompanySettings`).
-   [X] **Workflows Principais**: Esqueletos para `IdeationWorkflow`, `ProductDevelopmentWorkflow`, `ServiceDeliveryWorkflow`.
-   [X] **Módulos de Produtos e Serviços**: Estrutura básica para `ProductManager`, `ProductCatalog`, `ServiceManager`, `ServiceCatalog`.
-   [X] **Módulos de Finanças e Marketing**: Estrutura básica para `FinancialManager`, `MarketingManager`, etc.
-   [X] **API e Utilitários**: Esqueletos para API FastAPI, integração LLM e helpers.
-   [X] **Documentação Inicial**: `README.md`, `ROADMAP.md`, `BEST_PRACTICES.md`.
-   [ ] **Ponto de Entrada (`src/main.py`)**:
    -   [ ] Implementar a inicialização do `CompanyState` com configurações.
    -   [ ] Criar instâncias dos principais managers e agentes.
    -   [ ] Loop de simulação básico que avança ciclos.
    -   [ ] No loop, invocar workflows principais (ex: IdeationWorkflow).
-   [ ] **Integração LLM Real**:
    -   [ ] Implementar a lógica em `src/utils/llm_integration.py` para um provider (ex: OpenAI ou OpenRouter).
    -   [ ] Configurar chaves de API via `settings_loader.py` e variáveis de ambiente.
    -   [ ] Fazer com que os `BaseAgent`s usem a integração LLM real.
-   [ ] **Interação Agente-Workflow-Estado**:
    -   [ ] Workflows devem criar `Task`s no `CompanyState`.
    -   [ ] Agentes devem ser capazes de consultar/pegar tarefas relevantes para seu papel.
    -   [ ] Agentes devem atualizar o `CompanyState` com os resultados de suas ações (novas ideias, produtos atualizados, etc.).
-   [ ] **Testes Unitários Iniciais**: Para módulos core e utilitários.
-   [ ] **API Básica Funcional**: Endpoints para visualizar estado, ideias, produtos, etc.

## Fase 2: Funcionalidades de Negócio e Automação Aprimorada

-   [ ] **Workflows Detalhados**:
    -   [ ] Implementação completa da lógica de cada workflow, com múltiplos passos e condições.
    -   [ ] Lógica de decisão nos workflows para iniciar outros workflows ou tarefas.
-   [ ] **Agentes Mais Inteligentes**:
    -   [ ] Prompts mais sofisticados para LLMs.
    -   [ ] Capacidade dos agentes de planejar sequências de ações.
    -   [ ] Memória de longo prazo para agentes (além do histórico simples).
-   [ ] **Criação Real de Produtos/Serviços (Simulada)**:
    -   [ ] `ExecutionAgent` simulando a criação de artefatos digitais (ex: gerar código, escrever e-books).
    -   [ ] Integração com plataformas de venda (simulada, ex: Gumroad).
-   [ ] **Marketing e Vendas (Simulada)**:
    -   [ ] `MarketingAgent` gerando conteúdo e simulando postagens.
    -   [ ] Simulação de funil de vendas e aquisição de clientes.
-   [ ] **Gestão Financeira Detalhada**:
    -   [ ] Orçamentação, alocação de custos para projetos/produtos.
    -   [ ] Análise de rentabilidade.
-   [ ] **Persistência de Estado**: Salvar e carregar o `CompanyState` para retomar simulações.
-   [ ] **Dashboard/UI (Básico)**: Interface web simples para visualização do estado da empresa (via API).

## Fase 3: Rumo à Operação Real

-   [ ] **Integrações com Ferramentas Externas Reais**:
    -   [ ] Plataformas de e-commerce (Shopify, Gumroad).
    -   [ ] Gateways de pagamento (Stripe).
    -   [ ] Ferramentas de marketing (Mailchimp, plataformas de redes sociais).
    -   [ ] Sistemas de CRM.
-   [ ] **Segurança e Robustez**: Tratamento de erros, validação de dados, segurança da API.
-   [ ] **Escalabilidade**: Otimizações para lidar com mais agentes, dados e transações.
-   [ ] **Monitoramento e Analytics Avançado**: Coleta e visualização de KPIs de negócio.
-   [ ] **Personalização e Treinamento de Agentes**: Fine-tuning de modelos LLM para tarefas específicas.
-   [ ] **Governança e Ética**: Mecanismos para garantir que as ações da IA estejam alinhadas com objetivos éticos e de negócios.

## Contínuo

-   Documentação.
-   Testes (unitários, integração, E2E).
-   Refatoração e otimização.
-   Pesquisa de novas tecnologias e abordagens de IA.

Este roadmap é um documento vivo e será atualizado conforme o projeto evolui.
