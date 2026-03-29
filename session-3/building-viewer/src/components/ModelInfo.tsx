import type { BuildingModel } from "../types"
import { polygonArea, extractHumans } from "../utils"

interface Props {
  model: BuildingModel
}

export default function ModelInfo({ model }: Props) {
  const floors = model.floors
  const allSpaces = floors.flatMap(f => f.spaces ?? [])
  const allWalls = floors.flatMap(f => f.walls ?? [])
  const allFixtures = floors.flatMap(f => f.fixtures ?? [])
  const humans = extractHumans(model)
  const totalArea = allSpaces.reduce(
    (s, sp) => s + (sp.areaSqUnits ?? polygonArea(sp.boundary.outer)), 0
  )

  return (
    <div style={{
      padding: 16, background: "#1a2a4a", borderRadius: 8,
      color: "#c8d7eb", fontSize: 13, lineHeight: 1.6,
    }}>
      <h3 style={{ margin: "0 0 8px", color: "#e6ecf5" }}>{model.title}</h3>
      <p style={{ margin: "0 0 4px", color: "#8ca5c8" }}>{model.building.name}</p>
      {model.building.address && (
        <p style={{ margin: "0 0 8px", color: "#8ca5c8", fontSize: 12 }}>
          {model.building.address}
        </p>
      )}
      <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
        <tbody>
          <Row label="Schema" value={`v${model.schemaVersion}`} />
          <Row label="Units" value={model.lengthUnit} />
          <Row label="Floors" value={String(floors.length)} />
          <Row label="Spaces" value={String(allSpaces.length)} />
          <Row label="Walls" value={String(allWalls.length)} />
          <Row label="Fixtures" value={String(allFixtures.length)} />
          <Row label="People" value={String(humans.length)} />
          <Row label="Total area" value={`~${Math.round(totalArea)} m\u00b2`} />
        </tbody>
      </table>

      <h4 style={{ margin: "12px 0 6px", color: "#e6ecf5", fontSize: 12 }}>Spaces</h4>
      <div style={{ maxHeight: 150, overflowY: "auto", fontSize: 11 }}>
        {allSpaces.map(sp => (
          <div key={sp.id} style={{
            padding: "3px 0", borderBottom: "1px solid #253a5a",
            display: "flex", justifyContent: "space-between",
          }}>
            <span>{sp.name}</span>
            <span style={{ color: "#8ca5c8" }}>
              {(sp.areaSqUnits ?? polygonArea(sp.boundary.outer)).toFixed(1)} m²
            </span>
          </div>
        ))}
      </div>

      {humans.length > 0 && (
        <>
          <h4 style={{ margin: "12px 0 6px", color: "#e6ecf5", fontSize: 12 }}>People</h4>
          <div style={{ maxHeight: 150, overflowY: "auto", fontSize: 11 }}>
            {humans.map(h => (
              <div key={h.id} style={{
                padding: "3px 0", borderBottom: "1px solid #253a5a",
                display: "flex", justifyContent: "space-between", alignItems: "center",
              }}>
                <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{
                    width: 8, height: 8, borderRadius: "50%", display: "inline-block",
                    background: h.clothingColor
                      ? `rgb(${h.clothingColor.r},${h.clothingColor.g},${h.clothingColor.b})`
                      : "#cc8844",
                  }} />
                  {h.name}
                </span>
                <span style={{ color: "#8ca5c8" }}>
                  {h.pose ?? "standing"}
                </span>
              </div>
            ))}
          </div>
        </>
      )}

      <div style={{ marginTop: 12, fontSize: 10, color: "#5a7a9f" }}>
        Created by {model.metadata.createdBy}
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <tr>
      <td style={{ padding: "2px 8px 2px 0", color: "#8ca5c8" }}>{label}</td>
      <td style={{ padding: "2px 0", color: "#dce6f5" }}>{value}</td>
    </tr>
  )
}
