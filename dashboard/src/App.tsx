import { useEffect, useState, useRef } from 'react'
import { Button } from './components/ui/Button'
import { Card } from './components/ui/Card'
import { CompanyMap } from './components/CompanyMap'

const API_URL = 'http://localhost:8000'

interface Agent {
  nome: string
  funcao: string
  modelo_llm: string
  local_atual: string | null
  historico_acoes: string[]
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
}

export default function App() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [salas, setSalas] = useState<Sala[]>([])
  const [timeline, setTimeline] = useState<TimelineItem[]>([])
  const [saldo, setSaldo] = useState(0)
  const [historicoSaldo, setHistoricoSaldo] = useState<number[]>([])
  const [eventos, setEventos] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const lastEventos = useRef<string[]>([])

  // Busca dados da API e atualiza todos os painéis do dashboard.
  // Esta função é chamada no carregamento inicial e em intervalos regulares.
  async function loadData() {
    try {
      setError(null)
      const [ag, sl, ev, lc] = await Promise.all([
        fetch(`${API_URL}/agentes`).then(r => {
          if (!r.ok) throw new Error('agentes')
          return r.json()
        }),
        fetch(`${API_URL}/locais`).then(r => {
          if (!r.ok) throw new Error('locais')
          return r.json()
        }),
        fetch(`${API_URL}/eventos`).then(r => {
          if (!r.ok) throw new Error('eventos')
          return r.json()
        }),
        fetch(`${API_URL}/lucro`).then(r => {
          if (!r.ok) throw new Error('lucro')
          return r.json()
        }),
      ])

      const prev = agents

      // Atualiza estados principais
      setAgents(ag)
      setSalas(sl)
      setEventos(ev)
      setSaldo(lc.saldo || 0)
      setHistoricoSaldo(lc.historico_saldo || [])

      // Gera itens da linha do tempo comparando ações mais recentes
      const novos: TimelineItem[] = []
      ag.forEach(a => {
        const anterior = prev.find(p => p.nome === a.nome)
        if (!anterior) return
        const ultima = a.historico_acoes[a.historico_acoes.length - 1]
        const antUltima = anterior.historico_acoes[anterior.historico_acoes.length - 1]
        if (ultima && ultima !== antUltima) {
          novos.push({ id: Date.now() + novos.length, agente: a.nome, acao: ultima, sala: a.local_atual || '' })
        }
      })
      ev.forEach((txt, idx) => {
        if (!lastEventos.current.includes(txt)) {
          novos.push({ id: Date.now() + novos.length + idx, agente: '', acao: txt, sala: '' })
        }
      })
      lastEventos.current = ev
      if (novos.length) setTimeline(tl => [...novos, ...tl].slice(0, 50))

      if ((!ag || ag.length === 0) && (!sl || sl.length === 0)) {
        setError('Nenhum dado retornado do backend.')
      }
    } catch (err) {
      setError(`Erro ao carregar dados: ${err}`)
    } finally {
      setLoading(false)
    }
  }

  // Carrega os dados iniciais e agenda atualizações periódicas
  useEffect(() => {
    loadData()
    const id = setInterval(loadData, 5000)
    return () => clearInterval(id)
  }, [])

  // Dispara manualmente um novo ciclo e atualiza as informacoes na tela
  async function proximoCiclo() {
    try {
      const prev = agents
      const resp = await fetch(`${API_URL}/ciclo/next`, { method: 'POST' })
      if (!resp.ok) throw new Error('ciclo')
      const data = await resp.json()
      setAgents(data.agentes)
      setSaldo(data.saldo)
      setHistoricoSaldo(data.historico_saldo)
      setEventos(data.eventos)

      const eventos: TimelineItem[] = []
      data.agentes.forEach((a: Agent) => {
        const anterior = prev.find(p => p.nome === a.nome)
        if (!anterior) return
        const ultima = a.historico_acoes[a.historico_acoes.length - 1]
        const antUltima = anterior.historico_acoes[anterior.historico_acoes.length - 1]
        if (ultima && ultima !== antUltima) {
          eventos.push({ id: Date.now() + eventos.length, agente: a.nome, acao: ultima, sala: a.local_atual || '' })
        }
      })
      data.eventos.forEach((txt: string, idx: number) => {
        eventos.push({ id: Date.now() + eventos.length + idx, agente: '', acao: txt, sala: '' })
      })
      lastEventos.current = data.eventos
      if (eventos.length) setTimeline(prevTl => [...eventos, ...prevTl].slice(0, 50))
    } catch (err) {
      setError(`Erro ao executar ciclo: ${err}`)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 p-6 space-y-6">
      {loading && (
        <div className="fixed inset-0 flex items-center justify-center bg-white/80 z-50">
          <p className="text-xl font-semibold">Carregando/Iniciando a empresa...</p>
        </div>
      )}
      <h1 className="text-2xl font-bold">Dashboard</h1>
      {error && <p className="text-red-600">{error}</p>}

      <Card>
        <h2 className="text-xl font-semibold mb-2">Mapa da Empresa</h2>
        <CompanyMap agentes={agents.map((a, i) => ({ id: i, nome: a.nome, salaAtual: a.local_atual || '' }))} salas={salas.map((s, i) => ({ id: i, nome: s.nome }))} />
      </Card>

      <div className="flex space-x-6">
        <Card className="flex-1">
          <div className="flex justify-between items-center mb-2">
            <h2 className="text-xl font-semibold">Agentes</h2>
            <Button onClick={proximoCiclo}>Próximo ciclo</Button>
          </div>
          <table className="w-full text-left border-collapse">
            <thead>
              <tr>
                <th className="border-b p-2">Nome</th>
                <th className="border-b p-2">Função</th>
                <th className="border-b p-2">Sala</th>
                <th className="border-b p-2">Modelo</th>
                <th className="border-b p-2">Emoção</th>
              </tr>
            </thead>
            <tbody>
              {agents.map(a => (
                <tr key={a.nome} className="hover:bg-gray-50">
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
              <h3 className="font-medium">{s.nome}</h3>
              <p className="text-sm text-gray-600">{s.descricao}</p>
              <p className="text-sm">Inventário: {s.inventario.join(', ') || 'vazio'}</p>
              <p className="text-sm">Agentes: {agents.filter(a => a.local_atual === s.nome).map(a => a.nome).join(', ') || 'nenhum'}</p>
            </div>
          ))}
        </Card>

        <Card className="flex-1">
          <h2 className="text-xl font-semibold mb-2">Linha do Tempo</h2>
          <div className="space-y-2 max-h-96 overflow-auto">
            {timeline.length === 0 && <p className="text-sm text-gray-600">Sem eventos ainda</p>}
            {timeline.map(ev => (
              <div key={ev.id} className="border-b pb-1">
                <p className="text-sm">
                  <span className="font-medium">{ev.agente}</span> {ev.acao} {ev.sala}
                </p>
              </div>
            ))}
          </div>
        </Card>

        <Card className="flex-1">
          <h2 className="text-xl font-semibold mb-2">Eventos</h2>
          <div className="space-y-1 max-h-96 overflow-auto text-sm">
            {eventos.length === 0 && <p className="text-gray-600">Nenhum evento</p>}
            {eventos.map((e, i) => (
              <div key={i} className="border-b pb-1">{e}</div>
            ))}
          </div>
        </Card>

        <Card className="flex-1">
          <h2 className="text-xl font-semibold mb-2">Lucro</h2>
          <p className="text-sm">Saldo atual: {saldo.toFixed(2)}</p>
          <div className="mt-2 space-y-1 max-h-96 overflow-auto text-xs">
            {historicoSaldo.map((v, i) => (
              <div key={i}>{i + 1}: {v.toFixed(2)}</div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
