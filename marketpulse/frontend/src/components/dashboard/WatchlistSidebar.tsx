import { useState } from 'react'
import { Plus, Edit2, Trash2, Check, X, List } from 'lucide-react'
import type { Watchlist } from '../../types'
import { clsx } from 'clsx'
import { getErrorMessage } from '../../services/api'
import { Alert } from '../ui/Alert'

interface WatchlistSidebarProps {
  watchlists: Watchlist[]
  activeId?: number
  onSelect: (id: number) => void
  onCreate: (name: string) => Promise<void>
  onRename: (id: number, name: string) => Promise<void>
  onDelete: (id: number) => Promise<void>
}

export function WatchlistSidebar({
  watchlists,
  activeId,
  onSelect,
  onCreate,
  onRename,
  onDelete,
}: WatchlistSidebarProps) {
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [error, setError] = useState<string | null>(null)

  const handleCreate = async () => {
    if (!newName.trim()) return
    try {
      await onCreate(newName.trim())
      setNewName('')
      setCreating(false)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const handleRename = async (id: number) => {
    if (!editName.trim()) return
    try {
      await onRename(id, editName.trim())
      setEditingId(null)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this watchlist?')) return
    try {
      await onDelete(id)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <List className="w-4 h-4 text-slate-500" />
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Watchlists</span>
        </div>
        <button
          onClick={() => setCreating(true)}
          className="p-1 text-slate-500 hover:text-accent transition-colors rounded"
          title="New watchlist"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {error && (
        <Alert message={error} onDismiss={() => setError(null)} className="text-xs" />
      )}

      {/* Create form */}
      {creating && (
        <div className="flex gap-1 bg-surface-elevated border border-accent/40 rounded-lg p-1">
          <input
            autoFocus
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            placeholder="List name"
            className="flex-1 bg-transparent text-sm text-slate-200 placeholder-slate-500 focus:outline-none px-2"
          />
          <button onClick={handleCreate} className="p-1 text-green-400 hover:text-green-300">
            <Check className="w-4 h-4" />
          </button>
          <button onClick={() => { setCreating(false); setNewName('') }} className="p-1 text-slate-500 hover:text-slate-300">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Watchlist items */}
      {watchlists.map((wl) => (
        <div key={wl.id} className={clsx(
          'group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-colors',
          activeId === wl.id
            ? 'bg-accent/15 border border-accent/30 text-white'
            : 'hover:bg-surface-elevated text-slate-400 hover:text-white border border-transparent'
        )}>
          {editingId === wl.id ? (
            <div className="flex flex-1 gap-1">
              <input
                autoFocus
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleRename(wl.id)}
                className="flex-1 bg-transparent text-sm focus:outline-none text-white"
              />
              <button onClick={() => handleRename(wl.id)} className="text-green-400">
                <Check className="w-3.5 h-3.5" />
              </button>
              <button onClick={() => setEditingId(null)} className="text-slate-500">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <>
              <button className="flex-1 text-left text-sm font-medium truncate" onClick={() => onSelect(wl.id)}>
                {wl.name}
              </button>
              <span className="text-xs text-slate-600 group-hover:text-slate-500">
                {wl.stocks.length}
              </span>
              <div className="hidden group-hover:flex gap-1">
                <button
                  onClick={() => { setEditingId(wl.id); setEditName(wl.name) }}
                  className="p-1 text-slate-500 hover:text-slate-300 rounded"
                >
                  <Edit2 className="w-3 h-3" />
                </button>
                <button
                  onClick={() => handleDelete(wl.id)}
                  className="p-1 text-slate-500 hover:text-red-400 rounded"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            </>
          )}
        </div>
      ))}

      {watchlists.length === 0 && !creating && (
        <p className="text-xs text-slate-600 text-center py-2">No watchlists yet</p>
      )}
    </div>
  )
}
