# Empresa Autônoma Simulada

Este guia apresenta uma documentação completa do projeto, explicando conceitos, estrutura do código, como rodar a aplicação e formas de expandi-la.

## Visão Geral

O projeto implementa uma **empresa digital autônoma**. Agentes de software representam funcionários que pensam, criam, validam, executam e aprendem com o objetivo principal de **maximizar o lucro**. A cada ciclo da simulação o sistema:

1. Decide se novos agentes devem ser contratados automaticamente pelo módulo de RH.
2. Executa o ciclo criativo de geração e validação de ideias.
3. Envia prompts para modelos de linguagem simulando a decisão de cada agente.
4. Executa as ações retornadas, atualizando histórico e lucro.

O estado da empresa é disponibilizado via **API REST** (FastAPI) e visualizado em um **dashboard React**.

### Fluxo resumido

```
[Ciclo /ciclo/next]
      |
      |-- Módulo RH -> contratações automáticas
      |-- Ciclo criativo -> ideias -> validações -> protótipos
      |-- Agentes -> prompts -> ações (mover, ficar, mensagem)
      |-- Lucro atualizado -> histórico de saldo
```

## Principais Conceitos

- **Agente**: representa um funcionário digital. Possui função, modelo de LLM, local atual e histórico de ações/interações. Seu objetivo primordial é gerar lucro.
- **Sala/Local**: ambiente onde agentes executam tarefas. Armazena inventário de recursos e lista de agentes presentes.
- **RH Automático**: módulo (`rh.py`) que verifica carências de equipe e tarefas pendentes, criando novos agentes quando há saldo positivo.
- **Tarefa**: atividade a ser executada por um agente. Tarefas são registradas em `tarefas_pendentes` e podem originar contratações.
- **Ciclo**: uma iteração completa de decisões e atualizações de todos os agentes.
- **Lucro**: acumulado global. Cada sucesso gera receita, enquanto salários e uso de recursos geram custos.
- **Ciclo Criativo**: módulo (`ciclo_criativo.py`) onde agentes com função *Ideacao* propõem ideias, agentes *Validador* aprovam ou reprovam, e protótipos são executados.

### Auto-criação de Funcionários

Quando existe saldo positivo e faltam pessoas em alguma sala ou função, o RH cria automaticamente novos agentes. Se existirem tarefas pendentes, também são contratados agentes *Executor* para cada tarefa.

### Ciclo de Ideias

1. **Ideia**: agentes do tipo *Ideacao* sugerem produtos/campanhas.
2. **Validação**: agentes *Validador* avaliam riscos, recursos e histórico.
3. **Execução**: ideias aprovadas viram tarefas e podem gerar lucro ou prejuízo.

Logs registram `ideia -> validação -> protótipo -> resultado`, influenciando a preferência por certos temas.

## Estrutura do Código

```
├ empresa_digital.py  # Modelo principal de agentes e locais
├ rh.py               # Módulo de RH automático
├ ciclo_criativo.py   # Ciclo de ideacao/validação
├ api.py              # API REST (FastAPI)
├ dashboard/          # Frontend React para visualização
└ requirements.txt    # Dependências do backend
```

### Principais Módulos

- **empresa_digital.py**: define classes `Agente` e `Local`, funções de criação/movimentação, gera prompts, executa respostas simuladas e calcula lucro por ciclo.
- **rh.py**: implementa `ModuloRH` responsável por contratar agentes de forma autônoma, analisando saldo e tarefas.
- **ciclo_criativo.py**: gerencia ideias, validações e protótipos, armazenando histórico e preferências de temas.
- **api.py**: expõe a API REST com endpoints para agentes, salas e avanço de ciclos. Chama o RH e o ciclo criativo antes de executar ações de cada agente.
- **dashboard/**: aplicação React (Vite + Tailwind) que consome a API, mostra mapa da empresa, edita agentes e salas e exibe o histórico de lucro.

## Como Rodar o Projeto

### Requisitos

- Python 3.10+
- Node.js 18+ (para o dashboard)

Instale as dependências de backend:

```bash
pip install -r requirements.txt
```

### Backend / API

Execute o servidor FastAPI com:

```bash
uvicorn api:app --reload
```

A API ficará acessível em `http://localhost:8000`.

### Frontend / Dashboard

Em outro terminal:

```bash
cd dashboard
npm install
npm run dev
```

A interface abrirá em `http://localhost:5173`. Ela exibe as salas e agentes em tempo real. Utilize o botão **Próximo Ciclo** para simular novas iterações e visualizar o impacto no lucro.

## Como Contribuir e Expandir

1. **Novos Agentes**: crie subclasses ou novas funções no `empresa_digital.py`, especifique modelos de LLM diferentes ou comportamentos customizados.
2. **Novas Salas**: use o endpoint `POST /locais` ou adapte o dashboard para incluir tipos específicos de sala.
3. **Módulos Extras**: adicione arquivos seguindo o padrão dos existentes, por exemplo, um `marketing.py` com agentes especializados.
4. **Métricas e Dashboards**: expanda a API retornando novos indicadores (ex.: produtividade, satisfação). No frontend, crie componentes React em `dashboard/src/components` para mostrar gráficos ou mapas.
5. **Tipos de Agente**: defina funções diferentes (Ideacao, Validador, Executor, etc.) adicionando lógica condicional em `ciclo_criativo.py` ou em prompts personalizados.

## Exemplos de Uso

### Log Típico de Execução

```
INFO:Ideia proposta: Produto IA proposto por Alice
INFO:Validacao de Produto IA proposto por Alice por Bob: aprovada
INFO:Prototipo de Produto IA proposto por Alice resultou em 30.00
Novo agente Auto1 alocado em Sala de Reunião por falta de pessoal
Alice moveu-se para Sala de Reunião.
Bob envia mensagem para Carol: Preciso de ajuda
```

### Impacto no Lucro

Após cada ciclo a função `calcular_lucro_ciclo` registra no histórico:

```json
{
  "saldo": 25.0,
  "receita": 40.0,
  "custos": 15.0
}
```

O dashboard exibe esse saldo acumulado em forma de lista ou gráfico.

## Glossário


| Termo | Significado |
|-------|-------------|
| **Agente** | Entidade digital que executa tarefas e interage com salas |
| **Sala** | Local físico/virtual onde agentes trabalham |
| **RH** | Módulo de Recursos Humanos automático que contrata novos agentes |
| **Ciclo** | Uma iteração da simulação (decisões, execuções e lucro) |
| **Lucro** | Diferença entre receitas e custos no acumulado |
| **Ciclo Criativo** | Processo de criação, validação e prototipagem de ideias |
| **Tarefa** | Atividade específica atribuída a um agente |
Para mais detalhes consulte o README principal e o código fonte.
