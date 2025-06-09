import { useState } from 'react'
import { Button } from './components/ui/Button'
import { Input } from './components/ui/Input'
import { Card } from './components/ui/Card'

interface Agent {
  id: number
  nome: string
  funcao: string
  salaAtual: string
  modelo: string
  estadoEmocional: number
  historico: string[]
}

interface Sala {
  id: number
  nome: string
  descricao: string
  inventario: string[]
  agentes: number[]
}

const initialAgents: Agent[] = [
  {
    id: 1,
    nome: 'Alice',
    funcao: 'Gerente',
    salaAtual: 'Sala de Reuni\u00e3o',
    modelo: 'gpt-3.5-turbo',
    estadoEmocional: 1,
    historico: ['mover para Sala de Tecnologia -> ok']
  },
  {
    id: 2,
    nome: 'Bob',
    funcao: 'Dev',
    salaAtual: 'Sala de Tecnologia',
    modelo: 'deepseek-chat',
    estadoEmocional: 0,
    historico: []
  }
]

const initialSalas: Sala[] = [
  {
    id: 1,
    nome: 'Sala de Reuni\u00e3o',
    descricao: 'Espa\u00e7o para reuni\u00f5es',
    inventario: ['mesa', 'projetor'],
    agentes: [1]
  },
  {
    id: 2,
    nome: 'Sala de Tecnologia',
    descricao: 'Lab de dev',
    inventario: ['computadores'],
    agentes: [2]
  }
]

export default function App() {
  const [agents, setAgents] = useState<Agent[]>(initialAgents)
  const [salas, setSalas] = useState<Sala[]>(initialSalas)
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)

  const [newAgent, setNewAgent] = useState<Partial<Agent>>({})
  const [newSala, setNewSala] = useState<Partial<Sala>>({})

  function handleAddAgent() {
    if (!newAgent.nome || !newAgent.funcao || !newAgent.salaAtual || !newAgent.modelo) return
    const id = agents.length + 1
    const agent: Agent = {
      id,
      nome: newAgent.nome,
      funcao: newAgent.funcao,
      salaAtual: newAgent.salaAtual,
      modelo: newAgent.modelo,
      estadoEmocional: 0,
      historico: []
    }
    setAgents([...agents, agent])
    setNewAgent({})
  }

  function handleAddSala() {
    if (!newSala.nome) return
    const id = salas.length + 1
    const sala: Sala = {
      id,
      nome: newSala.nome,
      descricao: newSala.descricao || '',
      inventario: [],
      agentes: []
    }
    setSalas([...salas, sala])
    setNewSala({})
  }

  function proximoCiclo() {
    // simula altera\u00e7\u00f5es nos agentes
    setAgents(prev =>
      prev.map(a => ({ ...a, estadoEmocional: a.estadoEmocional + (Math.random() > 0.5 ? 1 : -1) }))
    )
  }

  return (
    <div className="min-h-screen bg-gray-100 p-6 space-y-6">
      <h1 className="text-2xl font-bold">Dashboard de Agentes</h1>

      <div className="flex space-x-6">
        <Card className="flex-1 space-y-2">
          <h2 className="text-xl font-semibold">Novo Agente</h2>
          <Input placeholder="Nome" value={newAgent.nome || ''} onChange={e => setNewAgent({ ...newAgent, nome: e.target.value })} />
          <Input placeholder="Fun\u00e7\u00e3o" value={newAgent.funcao || ''} onChange={e => setNewAgent({ ...newAgent, funcao: e.target.value })} />
          <Input placeholder="Sala atual" value={newAgent.salaAtual || ''} onChange={e => setNewAgent({ ...newAgent, salaAtual: e.target.value })} />
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
                <tr key={a.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => setSelectedAgent(a)}>
                  <td className="border-b p-2">{a.nome}</td>
                  <td className="border-b p-2">{a.funcao}</td>
                  <td className="border-b p-2">{a.salaAtual}</td>
                  <td className="border-b p-2">{a.modelo}</td>
                  <td className="border-b p-2">{a.estadoEmocional}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card className="flex-1">
          <h2 className="text-xl font-semibold mb-2">Salas</h2>
          {salas.map(s => (
            <div key={s.id} className="mb-4">
              <h3 className="font-medium">{s.nome}</h3>
              <p className="text-sm text-gray-600">{s.descricao}</p>
              <p className="text-sm">Invent\u00e1rio: {s.inventario.join(', ') || 'vazio'}</p>
              <p className="text-sm">Agentes: {agents.filter(a => a.salaAtual === s.nome).map(a => a.nome).join(', ') || 'nenhum'}</p>
            </div>
          ))}
        </Card>
      </div>

      {selectedAgent && (
        <Card className="fixed inset-0 m-auto w-1/2 h-1/2 overflow-auto z-10">
          <Button className="float-right" onClick={() => setSelectedAgent(null)}>Fechar</Button>
          <h2 className="text-xl font-semibold mb-2">Hist\u00f3rico de {selectedAgent.nome}</h2>
          <ul className="list-disc pl-6 space-y-1">
            {selectedAgent.historico.map((h, i) => <li key={i}>{h}</li>)}
          </ul>
        </Card>
      )}
    </div>
  )
}
