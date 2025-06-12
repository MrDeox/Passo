# Empresa Autônoma Simulada

Este guia apresenta uma documentação completa do projeto, explicando conceitos, estrutura do código, como rodar a aplicação e formas de expandi-la.

## Visão Geral

O projeto implementa uma **empresa digital autônoma**. Agentes de software representam funcionários que pensam, criam, validam, executam e aprendem com o objetivo principal de **maximizar o lucro**. A cada ciclo da simulação o sistema:

1. Decide se novos agentes devem ser contratados automaticamente pelo módulo de RH.
2. Executa o ciclo criativo de geração, validação e, potencialmente, criação e publicação de produtos.
3. Envia prompts para modelos de linguagem simulando a decisão de cada agente.
4. Executa as ações retornadas, atualizando histórico e lucro.

O estado da empresa é disponibilizado via **API REST** (FastAPI) e visualizado em um **dashboard React**.

### Fluxo resumido

```
[Ciclo /ciclo/next]
      |
      |-- Módulo RH -> contratações automáticas
      |-- Ciclo criativo -> ideias -> validações -> [Criação de Produto Digital] -> protótipos/resultados
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
- **Ciclo Criativo**: módulo (`ciclo_criativo.py`) onde agentes com função *Ideacao* propõem ideias, agentes *Validador* aprovam ou reprovam. Ideias validadas podem se tornar produtos digitais.
- **CriadorDeProdutos**: Lógica no módulo `criador_de_produtos.py` responsável por pegar uma `Ideia` validada, gerar seu conteúdo usando um LLM, e publicar o produto na Gumroad.
- **Divulgador**: Lógica no módulo `divulgador.py` que, para um produto publicado, usa um LLM para sugerir conteúdo de marketing (posts para redes sociais, etc.).
- **Simulação Contínua**: Para evitar que a empresa fique paralisada, diversos mecanismos garantem atividade constante:
    - *Receita Mínima*: Se o saldo da empresa cair criticamente, uma pequena quantia é injetada para cobrir custos básicos e permitir que o RH continue operando.
    - *Tarefas Automáticas*: Na ausência de tarefas pendentes, o sistema cria automaticamente novas tarefas genéricas, assegurando que sempre haja trabalho a ser feito.
    - *Ideias Automáticas*: Similarmente, se nenhum agente propuser ideias em um ciclo, uma ideia genérica é criada para manter o ciclo de inovação ativo.
    - *RH Proativo em Crises*: Em cenários de saldo muito baixo e pouquíssimos agentes, mas com tarefas pendentes, o RH pode ativar um "fundo de emergência" para contratações vitais.

- **Modo Vida Infinita**: Um modo especial de simulação (`MODO_VIDA_INFINITA` em `empresa_digital.py`) projetado para demonstrações e testes de estresse. Quando ativo:
    - *Saldo Abundante*: A empresa recebe injeções generosas de capital regularmente, eliminando preocupações financeiras.
    - *Geração Intensificada de Tarefas e Ideias*: Um volume maior de tarefas e ideias, muitas vezes mais ambiciosas, são criadas automaticamente.
    - *RH Sem Restrições*: O módulo de RH opera sem se preocupar com o saldo para contratações e pode ser mais agressivo ao preencher vagas e criar novas posições.
    Para ativar este modo, pode-se alterar a variável global `MODO_VIDA_INFINITA` diretamente no código `empresa_digital.py` para `True` ou utilizar a função `definir_modo_vida_infinita(True)`.

### Auto-criação de Funcionários

Quando existe saldo positivo e faltam pessoas em alguma sala ou função, o RH cria automaticamente novos agentes. Se existirem tarefas pendentes, também são contratados agentes *Executor* para cada tarefa.

### Ciclo de Ideias e Criação de Produtos Digitais

O ciclo de vida de uma ideia foi expandido para incluir a criação e publicação de produtos digitais:

1.  **Ideação**: Agentes com a função "Ideacao" propõem novas ideias de produtos ou serviços, detalhando a descrição e a justificativa de potencial de lucro.
2.  **Validação**: Agentes "Validador" analisam as ideias propostas, considerando riscos, recursos necessários e o histórico de sucessos e fracassos de temas semelhantes.
3.  **Criação de Conteúdo (se validada)**: Se uma ideia é validada e ainda não possui um produto associado:
    *   O módulo `criador_de_produtos.py` é acionado.
    *   Um LLM é utilizado para gerar o conteúdo do produto digital (ex: um e-book, um guia, um template) em formato Markdown, com base na descrição e justificativa da ideia.
    *   O arquivo `.md` gerado é salvo localmente no diretório `produtos_gerados/`.
4.  **Publicação na Gumroad**:
    *   O produto (arquivo `.md`) é então automaticamente publicado na plataforma Gumroad.
    *   Isso requer que uma chave de API da Gumroad esteja configurada no sistema (veja "Gumroad Integration Configuration").
    *   O link público do produto na Gumroad é armazenado junto à `Ideia` original.
5.  **Sugestões de Marketing (Opcional)**:
    *   Após a publicação bem-sucedida, o módulo `divulgador.py` pode ser chamado.
    *   Ele utiliza um LLM para gerar sugestões de conteúdo de marketing (posts para redes sociais, snippets de e-mail) para o produto recém-criado, utilizando o link da Gumroad. Essas sugestões são registradas nos eventos do sistema.
6.  **Resultado e Aprendizado**: A `Ideia` tem seu campo `resultado` atualizado com base no sucesso da criação do produto e outros fatores de simulação. Ideias que resultam em produtos publicados e potencialmente lucrativos podem influenciar positivamente a preferência por temas semelhantes em ciclos futuros.

Logs detalhados registram cada etapa desse processo, desde a proposição da ideia até a publicação e sugestão de marketing.

## Configuração de API Keys

Para o pleno funcionamento da simulação, especialmente as interações com serviços externos como OpenRouter (para LLMs) e Gumroad (para publicação de produtos), é crucial configurar as respectivas API Keys.

### OpenRouter API Key
Usada para todas as chamadas a Modelos de Linguagem que direcionam as decisões e a criatividade dos agentes.
*   **Método 1 (Recomendado para desenvolvimento local):** Crie um arquivo chamado `.openrouter_key` na raiz do projeto. Cole sua API Key da OpenRouter (disponível em [https://openrouter.ai/keys](https://openrouter.ai/keys)) neste arquivo.
*   **Método 2 (Para ambientes de produção ou CI/CD):** Defina a variável de ambiente `OPENROUTER_API_KEY` com o valor da sua chave.
O arquivo `.openrouter_key` já está listado no `.gitignore` para prevenir que sua chave seja acidentalmente versionada.

### Gumroad Integration Configuration

A integração com a Gumroad permite que a empresa digital publique automaticamente os produtos criados. Para isso, você precisa de um "Access Token" da Gumroad.

#### Obtendo um Gumroad Access Token:
1.  Acesse sua conta Gumroad.
2.  Vá para Configurações (Settings).
3.  Navegue até a seção "Avançado" (Advanced).
4.  No final da página, você encontrará a seção "Aplicativos Externos" (Third-party apps) ou "API".
5.  Crie uma nova aplicação OAuth ou use um token de acesso pessoal, se disponível. Se estiver criando uma aplicação, dê um nome (ex: "EmpresaDigitalSim"), e defina as permissões necessárias (geralmente, para criar e gerenciar produtos - escopo `edit_products`).
6.  Após criar a aplicação ou solicitar um token, a Gumroad fornecerá um "Access Token". Copie este valor.

#### Configurando a Chave no Projeto:
*   **Método 1 (Recomendado para desenvolvimento local):**
    1.  Crie um arquivo chamado `.gumroad_key` na raiz do seu projeto.
    2.  Cole o Access Token da Gumroad que você obteve dentro deste arquivo. Salve o arquivo.
*   **Método 2 (Para ambientes de produção ou CI/CD):**
    1.  Defina a variável de ambiente `GUMROAD_API_KEY` com o valor do seu Access Token da Gumroad.

**Importante**: O arquivo `.gumroad_key` está incluído no `.gitignore` do projeto, garantindo que sua chave de API não seja enviada para o controle de versão (como o Git). Mantenha seu Access Token seguro.

## Estrutura do Código

```
├ empresa_digital.py      # Modelo principal de agentes e locais
├ ciclo_criativo.py       # Ciclo de ideação, validação e criação de produtos
├ criador_de_produtos.py  # Lógica para gerar conteúdo de produto e publicar na Gumroad
├ divulgador.py           # Lógica para gerar sugestões de marketing para produtos
├ rh.py                   # Módulo de RH automático
├ openrouter_utils.py     # Utilitários para interagir com a API OpenRouter
├ gumroad.py              # Módulo para interagir com a API Gumroad
├ api.py                  # API REST (FastAPI)
├ dashboard/              # Frontend React para visualização
└ requirements.txt        # Dependências do backend
```

### Principais Módulos

- **empresa_digital.py**: define classes `Agente` e `Local`, funções de criação/movimentação, gera prompts, executa respostas simuladas e calcula lucro por ciclo. Gerencia o estado global da empresa.
- **ciclo_criativo.py**: gerencia o fluxo de ideias desde a proposição, passando pela validação, até a coordenação da criação do produto digital (chamando `criador_de_produtos.py`) e, opcionalmente, a geração de conteúdo de marketing (chamando `divulgador.py`).
- **criador_de_produtos.py**: contém a função `produto_digital` que orquestra a geração de conteúdo por LLM para uma ideia validada e sua publicação na Gumroad através do módulo `gumroad.py`.
- **divulgador.py**: contém a função `sugerir_conteudo_marketing` que usa um LLM para criar posts e textos promocionais para um produto publicado.
- **rh.py**: implementa `ModuloRH` responsável por contratar agentes de forma autônoma.
- **openrouter_utils.py**: centraliza a lógica de interação com a API OpenRouter, incluindo seleção de modelos e realização de chamadas LLM.
- **gumroad.py**: encapsula a lógica de comunicação com a API da Gumroad, como obtenção da chave e criação de produtos.
- **api.py**: expõe a API REST e inicializa automaticamente salas e agentes. Chama o RH e o ciclo criativo antes de executar ações de cada agente.
- **dashboard/**: aplicação React (Vite + Tailwind) apenas para visualização em tempo real do que a empresa está fazendo.

## Acessando Produtos Criados

Quando um produto digital é criado e publicado com sucesso na Gumroad:
*   O **link público do produto** é armazenado no atributo `link_produto` do objeto `Ideia` correspondente.
*   Este objeto `Ideia` (com o link) é parte da lista `historico_ideias`, que pode ser persistida e carregada entre sessões (salva em `historico_ideias.json` por padrão).
*   Um evento é registrado no `historico_eventos` do sistema, contendo uma mensagem sobre a criação do produto e o seu link na Gumroad. Ex: `"Novo produto 'Nome do Produto' criado e publicado na Gumroad: https://gum.co/linkproduto"`.
*   Se o `Divulgador` gerar sugestões de marketing, um evento adicional é registrado: `"Geradas sugestões de marketing para o produto: Nome do Produto"`. As sugestões em si são logadas no console/arquivo de log do sistema.

Para acessar os links e informações dos produtos:
1.  **Via API**: Se houver endpoints na API REST (`api.py`) para consultar `historico_ideias` (ex: `/ideias`) ou `historico_eventos` (ex: `/eventos`), esses podem ser usados para obter os links programaticamente.
2.  **Logs da Aplicação**: Os logs detalhados (console ou arquivos de log) conterão as mensagens de criação de produto com os respectivos links e as sugestões de marketing.
3.  **Arquivo `historico_ideias.json`**: Após salvar os dados da simulação, este arquivo conterá os detalhes de todas as ideias, incluindo o `link_produto` para aquelas que foram publicadas.

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

A interface abrirá em `http://localhost:5173`. Ela apenas exibe as salas, agentes e o histórico de saldo. Use **Próximo Ciclo** para acompanhar as decisões automáticas.

O modelo de linguagem de cada agente é definido internamente pelo backend, sem intervenção do usuário.

## Como Contribuir e Expandir

1. **Novos Agentes**: crie subclasses ou novas funções no `empresa_digital.py`, especifique modelos de LLM diferentes ou comportamentos customizados.
2. **Novas Salas**: use o endpoint `POST /locais` ou adapte o dashboard para incluir tipos específicos de sala.
3. **Módulos Extras**: adicione arquivos seguindo o padrão dos existentes, por exemplo, um `analise_de_mercado.py` com agentes especializados.
4. **Métricas e Dashboards**: expanda a API retornando novos indicadores (ex.: produtividade, satisfação, vendas de produtos Gumroad). No frontend, crie componentes React em `dashboard/src/components` para mostrar gráficos ou mapas.
5. **Tipos de Agente**: defina funções diferentes (Ideacao, Validador, Executor, CriadorDeConteudo, EspecialistaEmMarketing, etc.) adicionando lógica condicional em `ciclo_criativo.py` ou em prompts personalizados.

## Exemplos de Uso

### Log Típico de Execução (com criação de produto)

```
INFO:Ideia proposta: Guia de IA para Pequenas Empresas
INFO:Validacao de Guia de IA para Pequenas Empresas por ValidadorGPT: aprovada
INFO:Tentando criar produto digital para ideia validada: Guia de IA para Pequenas Empresas
INFO:Conteúdo do produto salvo em: produtos_gerados/guia_de_ia_para_pequenas_empresas.md
INFO:Chave da API Gumroad obtida com sucesso.
INFO:Tentando publicar produto 'Guia de IA para Pequenas Empresas' na Gumroad.
INFO:Produto 'Guia de IA para Pequenas Empresas' publicado com sucesso na Gumroad: https://gum.co/guiaIApeqemp
INFO:EVENTO: Novo produto 'Guia de IA para Pequenas Empresas' criado e publicado na Gumroad: https://gum.co/guiaIApeqemp
INFO:Tentando gerar sugestões de marketing para 'Guia de IA para Pequenas Empresas'...
INFO:Sugestões de marketing geradas com sucesso para 'Guia de IA para Pequenas Empresas'.
INFO:EVENTO: Geradas sugestões de marketing para o produto: Guia de IA para Pequenas Empresas. Link: https://gum.co/guiaIApeqemp
INFO:Sugestões de marketing para 'Guia de IA para Pequenas Empresas':
### Post para Twitter/X 1
Descubra como a IA pode transformar sua pequena empresa! 🚀 Nosso novo "Guia de IA para Pequenas Empresas" está disponível! Acesse já: https://gum.co/guiaIApeqemp #IA #PequenasEmpresas #Inovacao
... (outras sugestões) ...
INFO:Prototipo/Execução de Guia de IA para Pequenas Empresas resultou em 75.00 (Link produto: https://gum.co/guiaIApeqemp)
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
O resultado das ideias que se tornam produtos também contribui para o `saldo` através do campo `ideia.resultado`.

O dashboard exibe esse saldo acumulado em forma de lista ou gráfico.

## Glossário


| Termo | Significado |
|-------|-------------|
| **Agente** | Entidade digital que executa tarefas e interage com salas |
| **Sala** | Local físico/virtual onde agentes trabalham |
| **RH** | Módulo de Recursos Humanos automático que contrata novos agentes |
| **Ciclo** | Uma iteração da simulação (decisões, execuções e lucro) |
| **Lucro** | Diferença entre receitas e custos no acumulado |
| **Ciclo Criativo** | Processo de criação, validação e prototipagem/criação de ideias e produtos |
| **CriadorDeProdutos** | Componente que gera conteúdo de produto e o publica na Gumroad |
| **Divulgador** | Componente que gera sugestões de marketing para produtos publicados |
| **Tarefa** | Atividade específica atribuída a um agente |
Para mais detalhes consulte o README principal e o código fonte.

[end of docs/GuiaCompleto.md]
