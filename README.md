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
