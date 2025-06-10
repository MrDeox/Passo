"""Testes de integração simulando um ciclo completo."""

from unittest.mock import patch, MagicMock
import json # Necessário para criar o mock da resposta JSON
import empresa_digital as ed
import rh
from ciclo_criativo import executar_ciclo_criativo


@patch('empresa_digital.obter_api_key', return_value="fake_api_key") # Mock API key globally for this test
@patch('requests.post') # Mock requests.post globally for this test
def test_ciclo_completo_altera_saldo(mock_post, mock_obter_key, reset_state): # Added reset_state fixture
    # Configurar o mock para requests.post para retornar uma resposta padrão
    # Isso garante que os agentes executem uma ação (ex: "ficar")
    mock_response = MagicMock()
    mock_response.status_code = 200
    # Usar uma ação simples e válida para todos os agentes neste teste de integração
    # O conteúdo exato da ação pode não ser crítico, desde que seja válido
    action_content = {"acao": "ficar"}
    mock_response.json.return_value = {"choices": [{"message": {"content": json.dumps(action_content)}}]}
    mock_response.text = json.dumps({"choices": [{"message": {"content": json.dumps(action_content)}}]})
    mock_post.return_value = mock_response

    # Configura dois locais e agentes basicos
    ed.criar_local("Tecnologia", "", ["pc"]) # reset_state deve limpar isso se executado antes
    ed.criar_local("Reuniao", "", [])
    # É importante que reset_state seja usado se este teste modificar o estado global
    # que outros testes podem depender, ou se ele espera um estado limpo.
    # Assumindo que reset_state limpa ed.locais, ed.agentes, etc.

    alice = ed.criar_agente("Alice", "Ideacao", "gpt-test", "Tecnologia") # Usar um modelo de teste
    bob = ed.criar_agente("Bob", "Validador", "gpt-test", "Reuniao")   # Usar um modelo de teste

    # Tarefa inicial para acionar o RH
    ed.adicionar_tarefa("Inicial")
    ed.saldo = 20
    # rh.saldo = ed.saldo # rh.py deve usar ed.saldo diretamente ou ter seu próprio gerenciamento
                           # Se rh.saldo é uma cópia, precisa ser atualizado se ed.saldo mudar.
                           # Para este teste, vamos assumir que a lógica interna do RH acessa ed.saldo corretamente.
    rh.modulo_rh.verificar() # Isso pode criar "Auto1"

    # Ciclo criativo gera nova tarefa
    executar_ciclo_criativo() # Isso pode adicionar tarefas a ed.tarefas_pendentes

    # Assegurar que todos os agentes tenham histórico de ações para cálculo de lucro
    # A resposta mockada fará todos os agentes executarem 'ficar -> ok'
    alice.historico_acoes.append("dummy action ok") # Para garantir alguma receita se 'ficar' não gerar.
                                                 # Na verdade, 'ficar -> ok' já é registrado.

    # Executa decisoes para cada agente (agora mockado para não fazer chamadas reais)
    # O mock_post configurado no início do teste será usado por chamar_openrouter_api
    for ag_nome in list(ed.agentes.keys()): # Iterar sobre nomes para evitar problemas de modificação de dict
        ag = ed.agentes[ag_nome]
        prompt = ed.gerar_prompt_decisao(ag)
        # enviar_para_llm chamará chamar_openrouter_api que usará o mock_post
        resp = ed.enviar_para_llm(ag, prompt)
        ed.executar_resposta(ag, resp)

    result = ed.calcular_lucro_ciclo()

    # Verifica contratacao e atualizacao do saldo
    # O número de agentes será Alice, Bob, e Auto1 (se o RH contratar)
    # Custos: 3 agentes * 5 = 15
    # Recursos: Alice no Tecnologia (pc) = 1. Bob na Reuniao = 0. Auto1 (se criado) em Lab (se Lab existir e tiver itens)
    # Se Auto1 é criado pelo RH, ele é colocado em um local. Precisamos saber qual.
    # rh.py: novo_agente.local_atual = locais_ordenados[0] (primeiro local por nome)
    # Se "Lab" é o primeiro, e tem itens, isso afeta os custos.
    # Para este teste, vamos assumir que "Reuniao" é o primeiro local por nome (ordem alfabética)
    # ou que o local de Auto1 não tem recursos extras para simplificar.
    # Se Auto1 está em "Reuniao" (0 recursos) ou "Tecnologia" (1 recurso).
    # Assumindo Auto1 em "Reuniao" (0 recursos) se "Lab" não for criado ou for depois.
    # Locais criados: Tecnologia, Reuniao. "Reuniao" vem antes de "Tecnologia" alfabeticamente.
    # Então Auto1 irá para "Reuniao". Custo de recursos = 1 (somente de Alice).
    # Total de custos = 15 (salarios) + 1 (recursos) = 16.

    # Receita: cada agente que registra "-> ok" gera 10.
    # Alice (ficar -> ok), Bob (ficar -> ok), Auto1 (ficar -> ok) = 3 * 10 = 30.
    # Saldo anterior = 20.
    # Novo saldo = 20 + 30 (receita) - 16 (custos) = 34.

    assert "Auto1" in ed.agentes, "RH deveria ter contratado Auto1"
    # Ajustar as expectativas de saldo com base na lógica acima.
    # O saldo inicial é 20.
    # Receita: 3 agentes * 10 (por 'ficar -> ok') = 30.
    # Custo de salários: 3 agentes * 5 = 15.
    # Custo de recursos: Alice em Tecnologia (1 item 'pc') = 1. Bob em Reuniao (0 itens) = 0.
    # Auto1, se criado, vai para 'Reuniao' (primeiro local em ordem alfabética). Custo de recursos = 0.
    # Total de custos = 15 (salários) + 1 (recursos) = 16.
    # Saldo final = Saldo inicial + Receita - Custos = 20 + 30 - 16 = 34.

    assert result["saldo"] == 34.0, f"Saldo calculado incorretamente. Detalhes: {result}"
    assert ed.historico_saldo[-1] == 34.0
    assert ed.tarefas_pendentes # tarefa gerada pelo ciclo criativo

