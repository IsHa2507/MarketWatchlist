import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine,
} from 'recharts'
import type { HistoryDataPoint } from '../../types'
import { formatVolume } from '../../utils/format'

interface VolumeChartProps {
  data: HistoryDataPoint[]
  averageVolume?: number
}

function CustomTooltip({ active, payload, label }: {
  active?: boolean
  payload?: Array<{ value: number }>
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-card border border-surface-border rounded-lg p-3 shadow-xl">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className="text-sm font-bold text-white">{formatVolume(payload[0].value)}</p>
    </div>
  )
}

export function VolumeChart({ data, averageVolume }: VolumeChartProps) {
  if (!data.length) return null

  const currentVolume = data[data.length - 1]?.volume || 0
  const multiplier = averageVolume ? (currentVolume / averageVolume).toFixed(1) : null

  return (
    <div className="space-y-3">
      {averageVolume && multiplier && (
        <div className="flex items-center gap-4 text-sm">
          <div>
            <span className="text-slate-500">Current:</span>{' '}
            <span className="font-semibold text-white">{formatVolume(currentVolume)}</span>
          </div>
          <div>
            <span className="text-slate-500">Average:</span>{' '}
            <span className="font-semibold text-slate-300">{formatVolume(averageVolume)}</span>
          </div>
          <div>
            <span className={`font-bold ${Number(multiplier) >= 2 ? 'text-orange-400' : Number(multiplier) >= 1.5 ? 'text-yellow-400' : 'text-slate-400'}`}>
              {multiplier}x average
            </span>
          </div>
        </div>
      )}
      <div className="w-full h-40">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2535" vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fill: '#64748b', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(d) => {
                const date = new Date(d)
                return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
              }}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fill: '#64748b', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={formatVolume}
              width={50}
            />
            <Tooltip content={<CustomTooltip />} />
            {averageVolume && (
              <ReferenceLine
                y={averageVolume}
                stroke="#3b82f6"
                strokeDasharray="4 4"
                label={{ value: 'Avg', fill: '#3b82f6', fontSize: 10 }}
              />
            )}
            <Bar
              dataKey="volume"
              fill="#3b82f6"
              opacity={0.7}
              radius={[2, 2, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
