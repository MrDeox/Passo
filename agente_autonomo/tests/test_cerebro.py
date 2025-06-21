from src.cerebro import CerebroExterno


def test_cerebro_resposta(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=30):
        captured['json'] = json

        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return {'choices': [{'message': {'content': 'ok'}}]}

        return Resp()

    monkeypatch.setattr('requests.post', fake_post)
    cerebro = CerebroExterno()
    resp = cerebro.gerar_resposta('teste')
    assert resp == 'ok'
    assert captured['json']['model'] == 'deepseek/deepseek-chat-v3-0324:free'


def test_cerebro_resposta_vazia(monkeypatch):
    def fake_post(*args, **kwargs):
        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return {'choices': [{'message': {'content': ''}}]}

        return Resp()

    monkeypatch.setattr('requests.post', fake_post)
    cerebro = CerebroExterno()
    resp = cerebro.gerar_resposta('teste')
    assert resp == ''
