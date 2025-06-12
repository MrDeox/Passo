# Passo

Este repositório contém um esqueleto simples para simular uma "empresa digital" composta por agentes e locais.

O arquivo principal é `empresa_digital.py`, que define as classes `Agente` e
`Local` e diversas funções de utilidade para manipular agentes e locais.

Ao ser executado o sistema **cria tudo sozinho**: salas, agentes e objetivos
iniciais surgem automaticamente. A escolha do modelo LLM de cada agente é
decidida em tempo real por uma LLM que analisa a função do agente e a lista de
modelos gratuitos da OpenRouter. Nenhum input manual é necessário. O script
apenas imprime as decisões tomadas e executa alguns ciclos para demonstrar a
autonomia.

Ao ser executado, o sistema inicializa a empresa (salas, agentes, objetivos
iniciais e tarefas), com a configuração inicial de agentes podendo usar heurísticas
para seleção de modelos LLM. Durante os ciclos de simulação, as decisões de cada
agente são tomadas através de chamadas reais a Modelos de Linguagem (LLMs)
configurados para cada agente, via API OpenRouter.
É necessário configurar chaves de API para OpenRouter e Gumroad para que o sistema funcione
completamente (veja a seção "Configuração" para detalhes).


Cada agente mantém um histórico adaptativo contendo:

- últimas 3 ações e resultados
- últimas mensagens trocadas
- últimos 2 locais visitados
- objetivo atual e feedback do CEO
- um estado emocional que varia conforme o sucesso das ações

Essas informações são incluídas no prompt gerado a cada ciclo, permitindo que a
IA leve em conta a memória recente do agente.

## Configuração

Para o pleno funcionamento da simulação, especialmente as interações com serviços externos, são necessárias as seguintes configurações de chaves de API:

### OpenRouter API Key
Utilizada para as chamadas aos Modelos de Linguagem (LLMs) que impulsionam as decisões dos agentes.
- **Método 1 (Recomendado):** Crie um arquivo chamado `.openrouter_key` na raiz do projeto e cole sua API Key da OpenRouter nele.
- **Método 2:** Defina a variável de ambiente `OPENROUTER_API_KEY` com o valor da sua chave.
O arquivo `.openrouter_key` está incluído no `.gitignore` para evitar commits acidentais.

### Gumroad API Key
Necessária para a funcionalidade de criação e publicação automática de produtos digitais na plataforma Gumroad.
- **Método 1 (Recomendado):** Crie um arquivo chamado `.gumroad_key` na raiz do projeto e cole seu Access Token da Gumroad nele.
- **Método 2:** Defina a variável de ambiente `GUMROAD_API_KEY` com o valor do seu Access Token.
O arquivo `.gumroad_key` também está incluído no `.gitignore`.

## Running the Application

Existem duas formas principais de executar a simulação:

### Usando a Interface de Linha de Comando (CLI)
Esta é a forma recomendada para executar simulações e interagir com a empresa digital. O script `cli.py` oferece diversos comandos para controlar e observar a simulação.

Para ver a lista de comandos disponíveis e suas opções, execute:
```bash
python cli.py --help
```

Por exemplo, para executar a simulação por um número específico de ciclos:
```bash
python cli.py ciclo --cycles N
```
(Substitua N pelo número de ciclos desejado)

Para retomar uma simulação a partir de dados salvos anteriormente:
```bash
python cli.py ciclo --resume
```

O CLI também permite listar agentes, locais, obter o status do lucro, entre outras funcionalidades. Certifique-se de que as chaves de API (OpenRouter e, opcionalmente, Gumroad) estejam configuradas conforme a seção "Configuração".

### Rodando o Servidor da API
Você pode iniciar o servidor FastAPI backend diretamente. Isso é útil para desenvolvimento, para interagir com a API usando ferramentas como `curl` ou Postman, ou se você estiver construindo uma interface personalizada.

Para iniciar o servidor:
```bash
python start_backend.py
```
O script `start_backend.py` irá:
1. Solicitar as chaves de API (OpenRouter e Gumroad), se ainda não estiverem configuradas.
2. Instalar as dependências Python listadas em `requirements.txt` (se necessário).
3. Iniciar o backend FastAPI, geralmente na porta 8000.

Após iniciado, o backend ficará acessível em `http://localhost:8000` (ou na porta informada pela variável de ambiente `BACKEND_PORT`). Todos os endpoints da API podem ser consumidos.

Você pode passar argumentos para `start_backend.py`, como sua chave OpenRouter:
```bash
python start_backend.py --apikey SUA_OPENROUTER_KEY
```
Use `python start_backend.py --help` para ver as opções disponíveis.

## Decisões via LLM (Modelos de Linguagem Grandes)

A tomada de decisão de cada agente é impulsionada por um Modelo de Linguagem (LLM).
A função `gerar_prompt_decisao` constrói um prompt detalhado com o contexto atual
do agente (local, colegas, inventário, histórico de ações, objetivo, etc.).
Este prompt é então enviado para o LLM configurado para o agente (no atributo `Agente.modelo_llm`)
através da API OpenRouter (utilizando a função `chamar_openrouter_api`).
A resposta do LLM, esperada em formato JSON, dita a próxima ação do agente
(ficar, mover, ou enviar mensagem), que é então processada e executada pela função `executar_resposta`.
Este processo permite que os agentes atuem de forma autônoma e dinâmica com base na
interpretação do LLM sobre sua situação e objetivos.

Na criação de cada agente o sistema consulta a lista de modelos gratuitos
disponíveis na OpenRouter e envia essas opções para uma LLM real decidir qual é
o mais adequado para a função e objetivo do agente. O raciocínio e o modelo
escolhido são registrados no log, permitindo auditoria posterior.

### Exemplo de prompt

```
Agente: Alice
Função: Gerente
Local: Sala de Tecnologia - Laboratório de desenvolvimento
Colegas presentes: Bob
Inventário disponível: computadores, ferramentas de rede
Outros locais disponíveis: Sala de Reunião

Seu objetivo final é maximizar o lucro da empresa.

Escolha UMA das ações a seguir e responda apenas em JSON:
1. 'ficar' - permanecer no local atual.
2. 'mover' - ir para outro local. Use o campo 'local' com o destino.
3. 'mensagem' - enviar uma mensagem. Use 'destinatario' e 'texto'.
Exemplos:
{"acao": "ficar"}
{"acao": "mover", "local": "Sala de Reunião"}
{"acao": "mensagem", "destinatario": "Bob", "texto": "bom dia"}
```

### Evolução do prompt

Após cada ciclo, o histórico é atualizado e o texto enviado para a IA passa a
incluir essas informações. Exemplo simplificado de dois ciclos consecutivos para
um mesmo agente:

```
Agente: Alice
Função: Gerente
Local: Sala de Tecnologia - Laboratório de desenvolvimento
Últimas ações: mover para Sala de Reunião -> ok
Últimas interações: para Bob: Preciso de ajuda
Últimos locais: Sala de Reunião -> Sala de Tecnologia
Objetivo: Planejar projeto X
Feedback do CEO: Nenhum
Estado emocional: 1
...
```

No ciclo seguinte, após nova ação, o histórico muda e o estado emocional é
ajustado conforme o sucesso ou falha, alterando também o prompt enviado.

## Módulo RH automático

O backend possui o arquivo `rh.py`, que implementa um pequeno sistema de RH.
Ele é executado a cada ciclo de simulação e verifica se alguma sala ou função
está com menos agentes do que o mínimo configurado. Caso haja carência ou
tarefas registradas em `tarefas_pendentes`, o módulo cria automaticamente um
novo agente (com nome e modelo padrão) e registra a contratação no log. Os
agentes gerados participam normalmente dos próximos ciclos. Novas tarefas podem
ser adicionadas pela função `adicionar_tarefa`.

## Lucro virtual

Cada ciclo contabiliza receitas e custos gerando um **saldo** global. A receita
é obtida quando agentes executam ações com sucesso (10 unidades por ação) e os
custos incluem um salário fixo de 5 por agente mais 1 unidade por recurso da
sala utilizada. O histórico do saldo é registrado.

O RH somente contrata novos agentes quando o saldo é positivo e existem tarefas
pendentes, sinalizando perspectiva de aumento de lucro. Os prompts de decisão e
de contexto informam que o objetivo principal é *maximizar o lucro da empresa*.

Exemplo: se o saldo estiver baixo, o RH não abrirá vagas extras mesmo que uma
sala esteja vazia. Já com saldo alto e tarefas pendentes, novos agentes são
criados para acelerar a entrega de MVPs e gerar mais receita.

## Ciclo Criativo Automatizado e Criação de Produtos

O módulo `ciclo_criativo.py` adiciona um fluxo de ideação e validação em cada
`/ciclo/next` (quando disparado pela API ou pelo CLI). Agentes com função **Ideacao** propõem produtos ou campanhas e
justificam o potencial de lucro. Em seguida, agentes com função **Validador**
avaliam riscos, recursos disponíveis e experiências anteriores.

Se aprovadas, as ideias não apenas se tornam tarefas para executores, mas também podem
desencadear a **criação automática de um produto digital**. O sistema utiliza um LLM para
gerar o conteúdo do produto (por exemplo, um guia em formato Markdown) com base na descrição
e justificativa da ideia. Este arquivo é salvo localmente no diretório `produtos_gerados/`.

### Publicação na Gumroad
Após a geração do conteúdo, o produto é automaticamente publicado na plataforma **Gumroad**.
Isso requer uma chave de API da Gumroad configurada (veja a seção "Configuração").
O link público do produto na Gumroad é então registrado no sistema.

### Divulgação com o Agente Divulgador
Opcionalmente, após a publicação bem-sucedida de um produto, o agente **Divulgador**
entra em ação. Este agente utiliza um LLM para gerar sugestões de conteúdo de marketing
(posts para redes sociais, snippets de email) para promover o novo produto, utilizando
o link da Gumroad.

Cada passagem registra no log a sequência `ideia -> validação -> prototipagem/criação -> resultado`.
Ideias lucrativas aumentam a prioridade de temas semelhantes nos ciclos
seguintes; prejuízos reduzem essa preferência. O link do produto Gumroad e as sugestões
de marketing também são registradas como eventos no sistema.

Exemplo de log de sucesso na criação de produto:

```text
INFO:Ideia proposta: Produto IA proposto por Alice
INFO:Validacao de Produto IA proposto por Alice por Bob: aprovada
INFO:Tentando criar produto digital para ideia validada: Produto IA proposto por Alice
INFO:Conteúdo do produto salvo em: produtos_gerados/produto_ia_proposto_por_alice.md
INFO:Chave da API Gumroad obtida com sucesso.
INFO:Tentando publicar produto 'Produto IA proposto por Alice' na Gumroad.
INFO:Produto 'Produto IA proposto por Alice' publicado com sucesso na Gumroad: https://gum.co/exemplolink
INFO:Tentando gerar sugestões de marketing para 'Produto IA proposto por Alice'...
INFO:Sugestões de marketing geradas para 'Produto IA proposto por Alice'.
INFO:Prototipo/Execução de Produto IA proposto por Alice resultou em X.XX (Link produto: https://gum.co/exemplolink)
```

## Simulação Contínua e Modo Vida Infinita

Para garantir que a simulação permaneça sempre dinâmica e não pare por falta de recursos ou atividades, foram implementados os seguintes mecanismos:

*   **Receita Mínima Garantida:** O sistema injeta uma receita mínima caso o saldo da empresa fique muito baixo, permitindo que o RH continue operando e novas atividades possam ser iniciadas.
*   **Geração Automática de Tarefas e Ideias:** Se não houver tarefas pendentes ou nenhuma nova ideia for proposta pelos agentes, o sistema automaticamente gera tarefas e ideias genéricas para manter o fluxo de trabalho.
*   **Fundo de Emergência para RH:** Em situações críticas (saldo zero, pouquíssimos agentes e tarefas urgentes), o RH tem uma chance de ativar um fundo de emergência para realizar contratações essenciais.

Além disso, um **Modo Vida Infinita** opcional pode ser ativado ao iniciar a aplicação (por exemplo, com a flag `--infinite` nos scripts `start_backend.py` ou `cli.py`). Neste modo:

*   O saldo da empresa é constantemente reabastecido com valores generosos.
*   Um número maior de tarefas e ideias ambiciosas são geradas automaticamente.
*   O RH opera sem restrições de saldo e de forma mais agressiva.
Este modo é útil para demonstrações contínuas e testes de estresse do sistema.

## API REST

A aplicação possui uma API REST construída com **FastAPI** disponível no arquivo `api.py`.
Para interagir com a API, você pode iniciar o servidor usando `python start_backend.py` e então enviar requisições HTTP para os endpoints.

Os principais endpoints retornam dados em JSON:

- `GET /agentes` – lista todos os agentes cadastrados.
- `POST /agentes` – cria um novo agente.
- `PUT /agentes/{nome}` – atualiza informações ou move o agente de local.
- `DELETE /agentes/{nome}` – remove o agente.
- `GET /locais` – mostra todas as salas e quem está em cada uma.
- `POST /locais` – cria uma nova sala.
- `PUT /locais/{nome}` – edita a sala existente.
- `DELETE /locais/{nome}` – exclui a sala.
- `GET /lucro` – retorna o saldo atual e o histórico acumulado.
- `POST /ciclo/next` – executa um novo ciclo da simulação para todos os agentes.
- `GET /eventos` - retorna o histórico de eventos registrados.
- `GET /ideias` - retorna o histórico de ideias (incluindo links de produtos, se criados).

## Testes Automatizados

Uma bateria de testes em `pytest` valida as partes isoladas do sistema e o comportamento integrado.

Para executar todos os testes:

```bash
# instalar dependências do backend e o pytest
pip install -r requirements.txt pytest

# defina as chaves de API (OpenRouter e, opcionalmente, Gumroad para testes de produto)
export OPENROUTER_API_KEY=XXXX
export GUMROAD_API_KEY=YYYY # Opcional para testes específicos de Gumroad
# ou crie um arquivo .env com essas variáveis

# exemplo:
# cp .env.example .env
# edite e depois execute `source .env`

# rodar a suíte (é importante incluir o diretório raiz no PYTHONPATH)
PYTHONPATH=. pytest -q
```

O pacote `httpx` permanece travado na versão 0.23.x (menor que 0.24) para
evitar problemas de compatibilidade durante os testes.

O relatório exibirá quantos testes foram executados e possíveis falhas. Os testes
estão organizados em:

- `tests/test_core.py` e `tests/test_llm.py` – verificações unitárias das funções
  principais e do processo de seleção automática de modelos.
- `tests/test_integration.py`, `tests/test_simulation.py` e `tests/test_rh_auto.py`
  – integração entre módulos como RH, ciclo criativo e cálculo de lucro.
- `tests/test_end_to_end.py` e `tests/test_api_event_cycle.py` (anteriormente `test_frontend_api.py`) – simulam a
  inicialização completa e ciclos via API.
- `tests/test_resilience.py` – cenários de erro e validação de mensagens.

Todos devem passar indicando que a empresa digital consegue se comportar de forma
autônoma e resiliente.
