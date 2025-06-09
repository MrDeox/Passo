import { Card } from './ui/Card'

export interface Agent {
  id: number
  nome: string
  salaAtual: string
}

export interface Sala {
  id: number
  nome: string
}

export interface CompanyMapProps {
  agentes: Agent[]
  salas: Sala[]
  onMove: (agenteId: number, salaNome: string) => void
}

export function CompanyMap({ agentes, salas, onMove }: CompanyMapProps) {
  function handleDrop(e: React.DragEvent<HTMLDivElement>, sala: Sala) {
    e.preventDefault()
    const id = Number(e.dataTransfer.getData('text'))
    if (!id) return
    onMove(id, sala.nome)
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
      {salas.map((s) => (
        <Card
          key={s.id}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => handleDrop(e, s)}
          className="min-h-[120px]"
        >
          <h3 className="font-semibold mb-2">{s.nome}</h3>
          <div className="space-y-1">
            {agentes.filter((a) => a.salaAtual === s.nome).map((a) => (
              <div
                key={a.id}
                draggable
                onDragStart={(e) => e.dataTransfer.setData('text', String(a.id))}
                className="cursor-move px-2 py-1 bg-gray-100 rounded"
              >
                {a.nome}
              </div>
            ))}
            {agentes.filter((a) => a.salaAtual === s.nome).length === 0 && (
              <p className="text-sm text-gray-500">Vazio</p>
            )}
          </div>
        </Card>
      ))}
    </div>
  )
}
