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
