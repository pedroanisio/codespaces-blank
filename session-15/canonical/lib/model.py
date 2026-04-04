"""Typed data model for extracted figure data.

Replaces raw dicts with structured, serializable dataclasses.
All coordinates are in head-unit space (8.0 = full figure height).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Landmark:
    """A named anatomical point on the contour."""

    name: str
    index: int      # index into the contour array
    dx: float       # head-unit x (distance from midline)
    dy: float       # head-unit y (distance from crown)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "index": self.index, "dx": round(self.dx, 4), "dy": round(self.dy, 4)}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Landmark:
        return cls(name=d["name"], index=d["index"], dx=d["dx"], dy=d["dy"])


@dataclass
class SplineSegment:
    """A cubic B-spline fit to a contour segment between two landmarks."""

    label: str                  # e.g. "neck_to_shoulder"
    landmark_start: str         # starting landmark name
    landmark_end: str           # ending landmark name
    knots: list[float]          # knot vector (scipy tck[0])
    coeffs_dx: list[float]      # B-spline coefficients for dx axis (tck[1][0])
    coeffs_dy: list[float]      # B-spline coefficients for dy axis (tck[1][1])
    degree: int = 3             # spline degree

    @property
    def n_parameters(self) -> int:
        return len(self.coeffs_dx) + len(self.coeffs_dy) + len(self.knots)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "landmark_start": self.landmark_start,
            "landmark_end": self.landmark_end,
            "knots": [round(k, 6) for k in self.knots],
            "coeffs_dx": [round(c, 6) for c in self.coeffs_dx],
            "coeffs_dy": [round(c, 6) for c in self.coeffs_dy],
            "degree": self.degree,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SplineSegment:
        return cls(
            label=d["label"],
            landmark_start=d["landmark_start"],
            landmark_end=d["landmark_end"],
            knots=d["knots"],
            coeffs_dx=d["coeffs_dx"],
            coeffs_dy=d["coeffs_dy"],
            degree=d.get("degree", 3),
        )


@dataclass
class ParametricFit:
    """Parametric B-spline representation of the full contour."""

    segments: list[SplineSegment]
    max_error: float            # max L2 distance from original contour (head-units)
    mean_error: float           # mean L2 distance
    n_original_points: int      # point count of the source contour
    n_parameters: int           # total parameter count across all segments

    @property
    def compression_ratio(self) -> float:
        if self.n_parameters == 0:
            return 0.0
        return (self.n_original_points * 2) / self.n_parameters

    def to_dict(self) -> dict[str, Any]:
        return {
            "segments": [s.to_dict() for s in self.segments],
            "max_error": round(self.max_error, 6),
            "mean_error": round(self.mean_error, 6),
            "n_original_points": self.n_original_points,
            "n_parameters": self.n_parameters,
            "compression_ratio": round(self.compression_ratio, 2),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ParametricFit:
        return cls(
            segments=[SplineSegment.from_dict(s) for s in d["segments"]],
            max_error=d["max_error"],
            mean_error=d["mean_error"],
            n_original_points=d["n_original_points"],
            n_parameters=d["n_parameters"],
        )


@dataclass
class FigureData:
    """Complete extracted figure: contour, strokes, metadata, and optional enrichments.

    This is the canonical output type for all extraction pipelines.
    ``to_dict()`` produces a superset of the legacy JSON format, so existing
    consumers (render.py, analyze.py) continue to work unchanged.
    """

    contour: np.ndarray                         # Nx2 (dx, dy) head-unit coords
    strokes: list[np.ndarray]                   # list of Mx2 stroke arrays
    meta: dict[str, Any]                        # pipeline metadata
    landmarks: list[Landmark] = field(default_factory=list)
    parametric: ParametricFit | None = None
    symmetry: dict[str, Any] | None = None
    measurements: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict compatible with the legacy JSON format.

        Adds ``landmarks`` and ``parametric`` keys when present.
        """
        d: dict[str, Any] = {
            "meta": self.meta,
            "contour": self.contour.round(4).tolist(),
            "strokes": [s.tolist() if isinstance(s, np.ndarray) else s for s in self.strokes],
        }
        if self.landmarks:
            d["landmarks"] = [lm.to_dict() for lm in self.landmarks]
        if self.parametric is not None:
            d["parametric"] = self.parametric.to_dict()
        if self.symmetry is not None:
            d["symmetry"] = self.symmetry
        if self.measurements is not None:
            d["measurements"] = self.measurements
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> FigureData:
        """Deserialize from a dict (legacy or enriched format)."""
        landmarks = [Landmark.from_dict(lm) for lm in d.get("landmarks", [])]
        parametric = ParametricFit.from_dict(d["parametric"]) if "parametric" in d else None

        return cls(
            contour=np.array(d["contour"]),
            strokes=[np.array(s) for s in d["strokes"]],
            meta=d["meta"],
            landmarks=landmarks,
            parametric=parametric,
            symmetry=d.get("symmetry"),
            measurements=d.get("measurements"),
        )

    def landmark_by_name(self, name: str) -> Landmark | None:
        """Look up a landmark by name."""
        for lm in self.landmarks:
            if lm.name == name:
                return lm
        return None

    def landmark_vector(self) -> dict[str, float]:
        """Return a flat {name_dx: val, name_dy: val} dict for comparison/search."""
        vec: dict[str, float] = {}
        for lm in self.landmarks:
            vec[f"{lm.name}_dx"] = lm.dx
            vec[f"{lm.name}_dy"] = lm.dy
        return vec
