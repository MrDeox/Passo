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
