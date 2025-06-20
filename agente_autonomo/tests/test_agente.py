from src.agente import Agente


def test_instalar_dependencia():
    agente = Agente()
    agente.instalar_dependencia('pytest')
    # apenas verifica que o método roda sem exception
    assert True
