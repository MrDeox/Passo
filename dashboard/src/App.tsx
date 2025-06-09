import { useEffect, useState } from 'react'
import { Button } from './components/ui/Button'
import { Input } from './components/ui/Input'
import { Card } from './components/ui/Card'
import { CompanyMap } from './components/CompanyMap'

const API_URL = 'http://localhost:8000'

interface Agent {
  nome: string
  funcao: string
  modelo_llm: string
  local_atual: string | null
  historico_acoes: string[]
  historico_interacoes: string[]
  historico_locais: string[]
  objetivo_atual: string
  feedback_ceo: string
  estado_emocional: number
}

interface Sala {
  nome: string
  descricao: string
  inventario: string[]
  agentes_presentes: string[]
}

interface TimelineItem {
  id: number
  agente: string
  acao: string
  sala: string
  motivo: string
}

export default function App() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [salas, setSalas] = useState<Sala[]>([])
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)

  const [editAgent, setEditAgent] = useState<Partial<Agent> | null>(null)
  const [editSala, setEditSala] = useState<Partial<Sala> | null>(null)

  const [newAgent, setNewAgent] = useState<{ nome?: string; funcao?: string; modelo?: string; sala?: string }>({})
  const [newSala, setNewSala] = useState<Partial<Sala>>({})
  const [timeline, setTimeline] = useState<TimelineItem[]>([])

  async function loadData() {
    const ag = await fetch(`${API_URL}/agentes`).then(r => r.json())
    const sl = await fetch(`${API_URL}/locais`).then(r => r.json())
    setAgents(ag)
    setSalas(sl)
  }

  useEffect(() => {
    loadData()
  }, [])

  async function handleAddAgent() {
    if (!newAgent.nome || !newAgent.funcao || !newAgent.sala || !newAgent.modelo) return
    await fetch(`${API_URL}/agentes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nome: newAgent.nome,
        funcao: newAgent.funcao,
        modelo_llm: newAgent.modelo,
        local: newAgent.sala,
      }),
    })
    setNewAgent({})
    loadData()
  }

  async function handleAddSala() {
    if (!newSala.nome) return
    await fetch(`${API_URL}/locais`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nome: newSala.nome,
        descricao: newSala.descricao || '',
        inventario: newSala.inventario || [],
      }),
    })
    setNewSala({})
    loadData()
  }

  function handleMoveAgent(id: number, sala: string) {
    setAgents(prev =>
      prev.map(a => (a.id === id ? { ...a, salaAtual: sala } : a))
    )
    const ag = agents.find(a => a.id === id)
    if (ag) {
      setTimeline(prev => [
        {
          id: Date.now(),
          agente: ag.nome,
          acao: 'Arrasto',
          sala,
          motivo: 'Movido manualmente'
        },
        ...prev
      ].slice(0, 50))
    }
  }

  function proximoCiclo() {
  async function proximoCiclo() {
    const prev = agents
    const data = await fetch(`${API_URL}/ciclo/next`, { method: 'POST' }).then(r => r.json())
    setAgents(data.agentes)

    const eventos: TimelineItem[] = []
    data.agentes.forEach((a: Agent) => {
      const anterior = prev.find(p => p.nome === a.nome)
      if (!anterior) return
      const ultima = a.historico_acoes[a.historico_acoes.length - 1]
      const anteriorUltima = anterior.historico_acoes[anterior.historico_acoes.length - 1]
      if (ultima && ultima !== anteriorUltima) {
        eventos.push({
          id: Date.now() + eventos.length,
          agente: a.nome,
          acao: ultima,
          sala: a.local_atual || '',
          motivo: ultima,
        })
      }
    })
    if (eventos.length) {
      setTimeline(prevTl => [...eventos, ...prevTl].slice(0, 50))
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 p-6 space-y-6">
      <h1 className="text-2xl font-bold">Dashboard de Agentes</h1>

      <div className="flex space-x-6">
        <Card className="flex-1 space-y-2">
          <h2 className="text-xl font-semibold">Novo Agente</h2>
          <Input placeholder="Nome" value={newAgent.nome || ''} onChange={e => setNewAgent({ ...newAgent, nome: e.target.value })} />
          <Input placeholder="Fun\u00e7\u00e3o" value={newAgent.funcao || ''} onChange={e => setNewAgent({ ...newAgent, funcao: e.target.value })} />
          <Input placeholder="Sala atual" value={newAgent.sala || ''} onChange={e => setNewAgent({ ...newAgent, sala: e.target.value })} />
          <Input placeholder="Modelo" value={newAgent.modelo || ''} onChange={e => setNewAgent({ ...newAgent, modelo: e.target.value })} />
          <Button onClick={handleAddAgent}>Adicionar</Button>
        </Card>

        <Card className="flex-1 space-y-2">
          <h2 className="text-xl font-semibold">Nova Sala</h2>
          <Input placeholder="Nome" value={newSala.nome || ''} onChange={e => setNewSala({ ...newSala, nome: e.target.value })} />
          <Input placeholder="Descri\u00e7\u00e3o" value={newSala.descricao || ''} onChange={e => setNewSala({ ...newSala, descricao: e.target.value })} />
          <Button onClick={handleAddSala}>Adicionar</Button>
          </Card>

      </div>

      <Card>
        <h2 className="text-xl font-semibold mb-2">Mapa da Empresa</h2>
        <CompanyMap agentes={agents} salas={salas} onMove={handleMoveAgent} />
      </Card>

      <div className="flex space-x-6">
        <Card className="flex-1">
          <div className="flex justify-between items-center mb-2">
            <h2 className="text-xl font-semibold">Agentes</h2>
            <Button onClick={proximoCiclo}>Pr\u00f3ximo ciclo</Button>
          </div>
          <table className="w-full text-left border-collapse">
            <thead>
              <tr>
                <th className="border-b p-2">Nome</th>
                <th className="border-b p-2">Fun\u00e7\u00e3o</th>
                <th className="border-b p-2">Sala</th>
                <th className="border-b p-2">Modelo</th>
                <th className="border-b p-2">Emo\u00e7\u00e3o</th>
              </tr>
            </thead>
            <tbody>
              {agents.map(a => (
                <tr key={a.nome} className="hover:bg-gray-50 cursor-pointer" onClick={() => setSelectedAgent(a)}>
                  <td className="border-b p-2">{a.nome}</td>
                  <td className="border-b p-2">{a.funcao}</td>
                  <td className="border-b p-2">{a.local_atual}</td>
                  <td className="border-b p-2">{a.modelo_llm}</td>
                  <td className="border-b p-2">{a.estado_emocional}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card className="flex-1">
          <h2 className="text-xl font-semibold mb-2">Salas</h2>
          {salas.map(s => (
            <div key={s.nome} className="mb-4">
              {editSala && editSala.nome === s.nome ? (
                <div className="space-y-2">
                  <Input value={editSala.descricao || ''} onChange={e => setEditSala({ ...editSala!, descricao: e.target.value })} />
                  <Input value={(editSala.inventario || []).join(', ')} onChange={e => setEditSala({ ...editSala!, inventario: e.target.value.split(',').map(v => v.trim()).filter(Boolean) })} />
                  <div className="space-x-2">
                    <Button onClick={async () => { await fetch(`${API_URL}/locais/${editSala!.nome}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ descricao: editSala!.descricao, inventario: editSala!.inventario }) }); setEditSala(null); loadData(); }}>Salvar</Button>
                    <Button onClick={() => setEditSala(null)}>Cancelar</Button>
                  </div>
                </div>
              ) : (
                <>
                  <h3 className="font-medium">{s.nome}</h3>
                  <p className="text-sm text-gray-600">{s.descricao}</p>
                  <p className="text-sm">Invent\u00e1rio: {s.inventario.join(', ') || 'vazio'}</p>
                  <p className="text-sm">Agentes: {agents.filter(a => a.local_atual === s.nome).map(a => a.nome).join(', ') || 'nenhum'}</p>
                  <Button className="mt-1" onClick={() => setEditSala({ ...s })}>Editar</Button>
                </>
              )}
            </div>
          ))}
        </Card>
        <Card className="flex-1">
          <h2 className="text-xl font-semibold mb-2">Linha do Tempo</h2>
          <div className="space-y-2 max-h-96 overflow-auto">
            {timeline.length === 0 && (
              <p className="text-sm text-gray-600">Sem eventos ainda</p>
            )}
            {timeline.map(ev => (
              <div key={ev.id} className="border-b pb-1">
                <p className="text-sm">
                  <span className="font-medium">{ev.agente}</span> {ev.acao} em {ev.sala}
                </p>
                <p className="text-xs text-gray-600">{ev.motivo}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {selectedAgent && (
        <Card className="fixed inset-0 m-auto w-1/2 h-1/2 overflow-auto z-10 space-y-2">
          <Button className="float-right" onClick={() => { setSelectedAgent(null); setEditAgent(null) }}>Fechar</Button>
          <h2 className="text-xl font-semibold mb-2">Hist\u00f3rico de {selectedAgent.nome}</h2>
          <div className="space-y-2">
            <Input placeholder="Função" value={editAgent?.funcao ?? selectedAgent.funcao} onChange={e => setEditAgent({ ...editAgent, funcao: e.target.value })} />
            <Input placeholder="Modelo" value={editAgent?.modelo_llm ?? selectedAgent.modelo_llm} onChange={e => setEditAgent({ ...editAgent, modelo_llm: e.target.value })} />
            <Input placeholder="Sala" value={(editAgent?.local_atual ?? selectedAgent.local_atual) || ''} onChange={e => setEditAgent({ ...editAgent, local_atual: e.target.value })} />
            <Input placeholder="Objetivo" value={editAgent?.objetivo_atual ?? selectedAgent.objetivo_atual} onChange={e => setEditAgent({ ...editAgent, objetivo_atual: e.target.value })} />
            <Input placeholder="Feedback" value={editAgent?.feedback_ceo ?? selectedAgent.feedback_ceo} onChange={e => setEditAgent({ ...editAgent, feedback_ceo: e.target.value })} />
            <Button onClick={async () => {
              await fetch(`${API_URL}/agentes/${selectedAgent.nome}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  funcao: editAgent?.funcao,
                  modelo_llm: editAgent?.modelo_llm,
                  local: editAgent?.local_atual,
                  objetivo: editAgent?.objetivo_atual,
                  feedback_ceo: editAgent?.feedback_ceo,
                })
              })
              setEditAgent(null)
              setSelectedAgent(null)
              loadData()
            }}>Salvar</Button>
          </div>
          <ul className="list-disc pl-6 space-y-1">
            {selectedAgent.historico_acoes.map((h, i) => <li key={i}>{h}</li>)}
          </ul>
        </Card>
      )}
    </div>
  )
}
