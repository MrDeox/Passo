# Passo

Este repositório contém um esqueleto simples para simular uma "empresa digital" composta por agentes e locais.

O arquivo principal é `empresa_digital.py`, que define as classes `Agente` e
`Local` e diversas funções de utilidade para manipular agentes e locais.

Para executar o exemplo de uso basta rodar:

```bash
python empresa_digital.py
```

O script cria dois locais, três agentes e demonstra a movimentação de um
agente entre salas. Ele também exibe prompts dinâmicos contendo informações do
agente, salva o estado em arquivos JSON e recarrega os dados para provar a
persistência.

Cada agente mantém um histórico adaptativo contendo:

- últimas 3 ações e resultados
- últimas mensagens trocadas
- últimos 2 locais visitados
- objetivo atual e feedback do CEO
- um estado emocional que varia conforme o sucesso das ações

Essas informações são incluídas no prompt gerado a cada ciclo, permitindo que a
IA leve em conta a memória recente do agente.

## Decisões via LLM

Cada agente pode ter sua próxima ação definida por um modelo de linguagem. A
função `gerar_prompt_decisao` monta um texto com o contexto atual e pede que a
IA escolha entre ficar na sala, mover-se para outro local ou mandar uma
mensagem para algum colega. A resposta deve ser em JSON e é executada pelo
sistema.

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
agentes gerados participam normalmente dos próximos ciclos e aparecem no
dashboard. Novas tarefas podem ser adicionadas pela função `adicionar_tarefa`.

## Lucro virtual

Cada ciclo contabiliza receitas e custos gerando um **saldo** global. A receita
é obtida quando agentes executam ações com sucesso (10 unidades por ação) e os
custos incluem um salário fixo de 5 por agente mais 1 unidade por recurso da
sala utilizada. O histórico do saldo é registrado e exibido no dashboard.

O RH somente contrata novos agentes quando o saldo é positivo e existem tarefas
pendentes, sinalizando perspectiva de aumento de lucro. Os prompts de decisão e
de contexto informam que o objetivo principal é *maximizar o lucro da empresa*.

Exemplo: se o saldo estiver baixo, o RH não abrirá vagas extras mesmo que uma
sala esteja vazia. Já com saldo alto e tarefas pendentes, novos agentes são
criados para acelerar a entrega de MVPs e gerar mais receita.

## API REST

A aplicação possui uma API REST construída com **FastAPI** disponível no arquivo `api.py`.
Para utilizar instale as dependências e execute o servidor com o `uvicorn`:

```bash
pip install -r requirements.txt
uvicorn api:app --reload
```

Os principais endpoints retornam dados em JSON:

- `GET /agentes` – lista todos os agentes cadastrados.
- `POST /agentes` – cria um novo agente.
- `PUT /agentes/{nome}` – atualiza informações ou move o agente de local.
- `DELETE /agentes/{nome}` – remove o agente.
- `GET /locais` – mostra todas as salas e quem está em cada uma.
- `POST /locais` – cria uma nova sala.
- `PUT /locais/{nome}` – edita a sala existente.
- `DELETE /locais/{nome}` – exclui a sala.
- `POST /ciclo/next` – executa um novo ciclo da simulação para todos os agentes.



## Dashboard React

O diretório `dashboard` contém uma aplicação React que permite visualizar os agentes e salas de maneira interativa. Para rodar em modo de desenvolvimento instale as dependências e execute:

```bash
cd dashboard
npm install
npm run dev
```

Durante a execução é possível movimentar agentes entre salas arrastando seus cards no mapa da empresa. Cada ciclo da simulação também atualiza as posições automaticamente.
