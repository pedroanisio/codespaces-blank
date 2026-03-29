import { useState, useCallback, useEffect } from "react"
import type { BuildingModel } from "./types"
import BlueprintView from "./components/BlueprintView"
import ModelView3D from "./components/ModelView3D"
import ModelInfo from "./components/ModelInfo"

type ViewMode = "2d" | "3d" | "split"

export default function App() {
  const [model, setModel] = useState<BuildingModel | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>("split")
  const [fileName, setFileName] = useState<string>("")

  useEffect(() => {
    fetch("/models/pulp-fiction-coffee-shop.json")
      .then(r => r.json())
      .then(data => { setModel(data); setFileName("pulp-fiction-coffee-shop.json") })
      .catch(() => {})
  }, [])

  const loadJSON = useCallback((file: File) => {
    setFileName(file.name)
    const reader = new FileReader()
    reader.onload = (ev) => {
      try {
        const data = JSON.parse(ev.target?.result as string) as BuildingModel
        if (!data.schemaVersion || !data.floors || !data.building) {
          throw new Error("Not a valid BuildingModel JSON (missing schemaVersion, floors, or building)")
        }
        setModel(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to parse JSON")
        setModel(null)
      }
    }
    reader.readAsText(file)
  }, [])

  const handleFile = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) loadJSON(file)
  }, [loadJSON])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) loadJSON(file)
  }, [loadJSON])

  return (
    <div>
      <header style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "8px 0", marginBottom: 12, borderBottom: "1px solid #1e3052",
      }}>
        <h1 style={{
          fontSize: 20, fontWeight: 600, color: "#e6ecf5",
          display: "flex", alignItems: "center", gap: 8,
        }}>
          <span style={{ fontSize: 24 }}>&#9633;</span>
          Building Model Viewer
          <span style={{ fontSize: 11, color: "#5a7a9f", fontWeight: 400 }}>v2.0 / v2.1</span>
        </h1>

        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {model && (
            <div style={{
              display: "flex", background: "#1a2a4a", borderRadius: 6, overflow: "hidden",
            }}>
              {(["2d", "split", "3d"] as ViewMode[]).map(m => (
                <button
                  key={m}
                  onClick={() => setViewMode(m)}
                  style={{
                    padding: "6px 14px", border: "none", cursor: "pointer",
                    fontSize: 12, fontWeight: viewMode === m ? 600 : 400,
                    background: viewMode === m ? "#2a4a6a" : "transparent",
                    color: viewMode === m ? "#e6ecf5" : "#8ca5c8",
                  }}
                >
                  {m === "2d" ? "Blueprint" : m === "3d" ? "3D Model" : "Split"}
                </button>
              ))}
            </div>
          )}
          <label style={{
            padding: "6px 14px", background: "#2a4a6a", borderRadius: 6,
            cursor: "pointer", fontSize: 12, color: "#e6ecf5",
          }}>
            Load JSON
            <input type="file" accept=".json" onChange={handleFile} style={{ display: "none" }} />
          </label>
        </div>
      </header>

      {error && (
        <div style={{
          padding: 12, background: "#4a1a1a", borderRadius: 8,
          color: "#f0a0a0", marginBottom: 12, fontSize: 13,
        }}>
          {error}
        </div>
      )}

      {!model ? (
        <div
          onDrop={handleDrop}
          onDragOver={e => e.preventDefault()}
          style={{
            border: "2px dashed #2a4a6a", borderRadius: 12,
            padding: 60, textAlign: "center", color: "#5a7a9f",
          }}
        >
          <p style={{ fontSize: 18, marginBottom: 8 }}>Drop a BuildingModel JSON here</p>
          <p style={{ fontSize: 13 }}>Compatible with building-model-3d-schema v2.0 and v2.1</p>
        </div>
      ) : (
        <div
          onDrop={handleDrop}
          onDragOver={e => e.preventDefault()}
          style={{ display: "flex", gap: 12, minHeight: "calc(100vh - 100px)" }}
        >
          <div style={{ width: 260, flexShrink: 0 }}>
            <ModelInfo model={model} />
            {fileName && (
              <div style={{
                marginTop: 8, padding: 8, background: "#1a2a4a",
                borderRadius: 6, fontSize: 11, color: "#5a7a9f",
              }}>
                {fileName}
              </div>
            )}
          </div>

          <div style={{ flex: 1, display: "flex", gap: 12 }}>
            {(viewMode === "2d" || viewMode === "split") && (
              <div style={{
                flex: 1, background: "#0f1a2e", borderRadius: 8,
                display: "flex", alignItems: "center", justifyContent: "center",
                overflow: "hidden",
              }}>
                <BlueprintView
                  model={model}
                  width={viewMode === "split" ? 540 : 1080}
                  height={700}
                />
              </div>
            )}
            {(viewMode === "3d" || viewMode === "split") && (
              <div style={{ flex: 1, borderRadius: 8, overflow: "hidden", minHeight: 700 }}>
                <ModelView3D model={model} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
