import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ReferenceDot,
} from 'recharts'
import type { HistoryDataPoint } from '../../types'

interface PriceChartProps {
  data: HistoryDataPoint[]
  currency?: string
  ticker?: string
}

function CustomTooltip({ active, payload, label, currency }: {
  active?: boolean
  payload?: Array<{ value: number }>
  label?: string
  currency: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-card border border-surface-border rounded-lg p-3 shadow-xl">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className="text-sm font-bold text-white">{currency}{payload[0].value.toLocaleString()}</p>
    </div>
  )
}

export function PriceChart({ data, currency = '$', ticker }: PriceChartProps) {
  if (!data.length) return null

  const currencySymbol = currency === 'INR' ? '₹' : '$'
  const lastClose = data[data.length - 1]?.close
  const firstClose = data[0]?.close
  const isPositive = lastClose >= firstClose
  const checkpointIdx = data.findIndex((d) => d.is_checkpoint)
  const checkpointDate = checkpointIdx >= 0 ? data[checkpointIdx].date : null

  const strokeColor = isPositive ? '#22c55e' : '#ef4444'
  const gradientId = `gradient_${ticker || 'price'}`

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={strokeColor} stopOpacity={0.2} />
              <stop offset="95%" stopColor={strokeColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2535" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(d) => {
              const date = new Date(d)
              return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
            }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${currencySymbol}${v.toLocaleString()}`}
            width={70}
            domain={['auto', 'auto']}
          />
          <Tooltip content={<CustomTooltip currency={currencySymbol} />} />

          {/* Last check reference line */}
          {checkpointDate && (
            <ReferenceLine
              x={checkpointDate}
              stroke="#3b82f6"
              strokeDasharray="4 4"
              label={{ value: 'Last check', fill: '#3b82f6', fontSize: 10, position: 'top' }}
            />
          )}

          <Area
            type="monotone"
            dataKey="close"
            stroke={strokeColor}
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            dot={false}
            activeDot={{ r: 4, fill: strokeColor, stroke: '#0f1117', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
