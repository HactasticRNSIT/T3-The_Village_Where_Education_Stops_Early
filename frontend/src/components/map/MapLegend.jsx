/**
 * MapLegend.jsx
 * SafeRoute AI — Responsive map legend mounted in the bottom-right corner.
 * Consumed by both the village UI and the lawmaker dashboard.
 *
 * Props:
 *   mode   'village' | 'lawmaker'   controls which legend items are shown
 *   style  object                   optional override styles on the container
 */

import React, { useState } from 'react';

const LegendItem = ({ colour, label, dashed = false, icon = null, shape = 'line' }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '2px 0' }}>
        {shape === 'line' && (
            <svg width="28" height="10" style={{ flexShrink: 0 }}>
                <line
                    x1="2" y1="5" x2="26" y2="5"
                    stroke={colour}
                    strokeWidth={dashed ? 2.5 : 3}
                    strokeDasharray={dashed ? '5 3' : null}
                    strokeLinecap="round"
                />
            </svg>
        )}
        {shape === 'circle' && (
            <svg width="14" height="14" style={{ flexShrink: 0 }}>
                <circle cx="7" cy="7" r="6" fill={colour} fillOpacity="0.18"
                    stroke={colour} strokeWidth="1.5"
                    strokeDasharray="4 2" />
            </svg>
        )}
        {shape === 'dot' && (
            <div style={{
                width: 12, height: 12, borderRadius: '50%',
                background: colour, flexShrink: 0,
                opacity: 0.85,
            }} />
        )}
        {shape === 'icon' && (
            <div style={{
                width: 18, height: 18, borderRadius: '50%',
                background: colour, flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 10,
            }}>
                {icon}
            </div>
        )}
        <span style={{
            fontSize: 11,
            color: '#374151',
            lineHeight: 1.3,
            fontFamily: "'DM Sans', sans-serif",
        }}>
            {label}
        </span>
    </div>
);

const Divider = () => (
    <div style={{
        borderTop: '0.5px solid #e5e7eb',
        margin: '6px 0',
    }} />
);

export default function MapLegend({ mode = 'village', style = {} }) {
    const [collapsed, setCollapsed] = useState(false);

    return (
        <div style={{
            position: 'absolute',
            bottom: 24,
            right: 10,
            zIndex: 1000,
            background: 'rgba(255,255,255,0.97)',
            backdropFilter: 'blur(6px)',
            borderRadius: 10,
            boxShadow: '0 2px 12px rgba(0,0,0,0.15)',
            border: '0.5px solid #e5e7eb',
            overflow: 'hidden',
            maxWidth: 190,
            transition: 'max-height 0.25s ease',
            ...style,
        }}>
            {/* Header */}
            <button
                onClick={() => setCollapsed((c) => !c)}
                style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    width: '100%', padding: '7px 10px',
                    background: 'transparent', border: 'none', cursor: 'pointer',
                    borderBottom: collapsed ? 'none' : '0.5px solid #e5e7eb',
                }}
            >
                <span style={{
                    fontSize: 11, fontWeight: 700, color: '#111827',
                    fontFamily: "'DM Sans', sans-serif", letterSpacing: '0.04em',
                    textTransform: 'uppercase',
                }}>
                    Legend
                </span>
                <span style={{ fontSize: 10, color: '#6b7280' }}>
                    {collapsed ? '▲' : '▼'}
                </span>
            </button>

            {!collapsed && (
                <div style={{ padding: '6px 10px 10px' }}>

                    {/* Route safety — both modes */}
                    <div style={{
                        fontSize: 10, fontWeight: 700, color: '#9ca3af',
                        letterSpacing: '0.06em', textTransform: 'uppercase',
                        marginBottom: 4, fontFamily: "'DM Sans', sans-serif",
                    }}>
                        Route safety
                    </div>
                    <LegendItem colour="#22c55e" label="Safe (score > 70%)" shape="line" />
                    <LegendItem colour="#f0962a" label="Moderate (40–70%)" shape="line" />
                    <LegendItem colour="#e84545" label="High risk (< 40%)" shape="line" />

                    <Divider />

                    {/* School markers */}
                    <LegendItem colour="#185FA5" label="School" shape="dot" />
                    <LegendItem colour="#378ADD" label="7 km boundary" shape="circle" />

                    {/* Heatmap */}
                    <Divider />
                    <div style={{
                        fontSize: 10, fontWeight: 700, color: '#9ca3af',
                        letterSpacing: '0.06em', textTransform: 'uppercase',
                        marginBottom: 4, fontFamily: "'DM Sans', sans-serif",
                    }}>
                        Risk heatmap
                    </div>
                    <div style={{ display: 'flex', gap: 2, alignItems: 'center', marginBottom: 3 }}>
                        {['#22c55e', '#78c453', '#f0962a', '#e84545', '#991b1b'].map((c, i) => (
                            <div key={i} style={{
                                height: 8, flex: 1, background: c, borderRadius: i === 0 ? '3px 0 0 3px'
                                    : i === 4 ? '0 3px 3px 0' : 0,
                            }} />
                        ))}
                    </div>
                    <div style={{
                        display: 'flex', justifyContent: 'space-between',
                        fontSize: 9, color: '#9ca3af',
                        fontFamily: "'DM Sans', sans-serif",
                    }}>
                        <span>Low risk</span><span>High risk</span>
                    </div>

                    {/* Lawmaker-only items */}
                    {mode === 'lawmaker' && (
                        <>
                            <Divider />
                            <div style={{
                                fontSize: 10, fontWeight: 700, color: '#9ca3af',
                                letterSpacing: '0.06em', textTransform: 'uppercase',
                                marginBottom: 4, fontFamily: "'DM Sans', sans-serif",
                            }}>
                                Infrastructure gaps
                            </div>
                            <LegendItem colour="#E24B4A" label="No bus stop" shape="line" dashed />
                            <LegendItem colour="#7c3aed" label="Mobile dead zone" shape="icon" icon="📵" />
                            <LegendItem colour="#f59e0b" label="Unlit road" shape="icon" icon="🌙" />
                        </>
                    )}
                </div>
            )}
        </div>
    );
}
