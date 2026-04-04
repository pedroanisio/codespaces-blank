"""Tests for FigureData model, landmark detection, B-spline fitting, and serialization."""

import json
import unittest
from pathlib import Path

import numpy as np

from lib.model import FigureData, Landmark, ParametricFit, SplineSegment
from lib.profile import find_anatomical_landmarks
from lib.geometry import fit_bspline_segments, reconstruct_from_segments


def _make_synthetic_contour(n: int = 600) -> np.ndarray:
    """Generate a synthetic right-half silhouette mimicking a human figure.

    Returns Nx2 array (dx, dy) in head-unit coordinates.
    The silhouette goes down the outer edge then back up the inner edge.
    """
    t = np.linspace(0, 8, n // 2)

    # Outer profile: head → neck → shoulder → waist → hip → knee → ankle
    outer_dx = (
        0.3 * np.exp(-((t - 0.5) ** 2) / 0.08)   # head bump
        + 1.2 * np.exp(-((t - 2.0) ** 2) / 0.5)   # shoulder
        - 0.4 * np.exp(-((t - 3.0) ** 2) / 0.15)  # waist dip
        + 1.0 * np.exp(-((t - 4.0) ** 2) / 0.3)   # hip
        + 0.6 * np.exp(-((t - 6.0) ** 2) / 1.0)   # leg
    )
    outer_dx = np.maximum(outer_dx, 0.05)

    # Inner profile: narrower, same dy reversed
    inner_dx = outer_dx * 0.15
    inner_dy = t[::-1]

    contour = np.vstack([
        np.column_stack([outer_dx, t]),
        np.column_stack([inner_dx, inner_dy]),
    ])
    return contour


class TestLandmark(unittest.TestCase):
    def test_round_trip(self) -> None:
        lm = Landmark(name="shoulder_peak", index=42, dx=1.523, dy=1.94)
        d = lm.to_dict()
        restored = Landmark.from_dict(d)
        self.assertEqual(restored.name, lm.name)
        self.assertEqual(restored.index, lm.index)
        self.assertAlmostEqual(restored.dx, lm.dx, places=4)
        self.assertAlmostEqual(restored.dy, lm.dy, places=4)


class TestSplineSegment(unittest.TestCase):
    def test_n_parameters(self) -> None:
        seg = SplineSegment(
            label="a_to_b", landmark_start="a", landmark_end="b",
            knots=[0, 0, 0, 0.5, 1, 1, 1],
            coeffs_dx=[0.1, 0.2, 0.3],
            coeffs_dy=[0.4, 0.5, 0.6],
            degree=3,
        )
        self.assertEqual(seg.n_parameters, 7 + 3 + 3)

    def test_round_trip(self) -> None:
        seg = SplineSegment(
            label="a_to_b", landmark_start="a", landmark_end="b",
            knots=[0.0, 0.0, 0.5, 1.0, 1.0],
            coeffs_dx=[1.0, 2.0],
            coeffs_dy=[3.0, 4.0],
            degree=3,
        )
        d = seg.to_dict()
        restored = SplineSegment.from_dict(d)
        self.assertEqual(restored.label, seg.label)
        self.assertEqual(restored.degree, seg.degree)
        self.assertEqual(len(restored.knots), len(seg.knots))


class TestAnatomicalLandmarks(unittest.TestCase):
    def test_detects_landmarks_on_synthetic_contour(self) -> None:
        contour = _make_synthetic_contour()
        landmarks = find_anatomical_landmarks(contour)
        names = [lm.name for lm in landmarks]

        # Should find at least head, neck, shoulder, waist
        self.assertIn("head_peak", names)
        self.assertIn("shoulder_peak", names)

        # Landmarks should be in increasing dy order
        dys = [lm.dy for lm in landmarks]
        self.assertEqual(dys, sorted(dys))

    def test_landmarks_within_figure_bounds(self) -> None:
        contour = _make_synthetic_contour()
        landmarks = find_anatomical_landmarks(contour)
        for lm in landmarks:
            self.assertGreaterEqual(lm.dy, 0.0)
            self.assertLessEqual(lm.dy, 8.0)
            self.assertGreaterEqual(lm.dx, 0.0)
            self.assertLess(lm.index, len(contour))


class TestBSplineFit(unittest.TestCase):
    def test_fit_and_reconstruct(self) -> None:
        contour = _make_synthetic_contour()
        landmarks = find_anatomical_landmarks(contour)
        self.assertGreaterEqual(len(landmarks), 2)

        segments, max_err, mean_err = fit_bspline_segments(contour, landmarks)
        self.assertGreater(len(segments), 0)
        self.assertGreater(max_err, 0)
        # Error should be small relative to figure size (8 HU)
        self.assertLess(max_err, 1.0)

        # Reconstruction should produce valid points
        recon = reconstruct_from_segments(segments)
        self.assertGreater(len(recon), 0)
        self.assertEqual(recon.shape[1], 2)

    def test_compression_ratio(self) -> None:
        contour = _make_synthetic_contour(800)
        landmarks = find_anatomical_landmarks(contour)
        segments, _, _ = fit_bspline_segments(contour, landmarks)
        n_params = sum(s.n_parameters for s in segments)
        # Should achieve at least 5x compression
        self.assertGreater(len(contour) * 2 / n_params, 5.0)

    def test_empty_landmarks(self) -> None:
        contour = _make_synthetic_contour()
        segments, max_err, mean_err = fit_bspline_segments(contour, [])
        self.assertEqual(segments, [])
        self.assertEqual(max_err, 0.0)

    def test_single_landmark(self) -> None:
        contour = _make_synthetic_contour()
        lm = Landmark(name="test", index=50, dx=0.5, dy=1.0)
        segments, max_err, mean_err = fit_bspline_segments(contour, [lm])
        self.assertEqual(segments, [])


class TestFigureData(unittest.TestCase):
    def _make_figure(self) -> FigureData:
        contour = _make_synthetic_contour()
        landmarks = find_anatomical_landmarks(contour)
        segments, max_err, mean_err = fit_bspline_segments(contour, landmarks)
        parametric = ParametricFit(
            segments=segments,
            max_error=max_err,
            mean_error=mean_err,
            n_original_points=len(contour),
            n_parameters=sum(s.n_parameters for s in segments),
        )
        return FigureData(
            contour=contour,
            strokes=[np.array([[0.1, 1.0], [0.2, 1.5]])],
            meta={"source": "test", "contour_points": len(contour), "detail_strokes": 1},
            landmarks=landmarks,
            parametric=parametric,
        )

    def test_to_dict_has_required_keys(self) -> None:
        fig = self._make_figure()
        d = fig.to_dict()
        for key in ("meta", "contour", "strokes"):
            self.assertIn(key, d)

    def test_to_dict_has_enrichment_keys(self) -> None:
        fig = self._make_figure()
        d = fig.to_dict()
        self.assertIn("landmarks", d)
        self.assertIn("parametric", d)

    def test_round_trip_json(self) -> None:
        fig = self._make_figure()
        d = fig.to_dict()

        # Serialize to JSON and back
        json_str = json.dumps(d)
        parsed = json.loads(json_str)

        restored = FigureData.from_dict(parsed)
        self.assertEqual(len(restored.contour), len(fig.contour))
        self.assertEqual(len(restored.landmarks), len(fig.landmarks))
        self.assertIsNotNone(restored.parametric)
        self.assertEqual(len(restored.parametric.segments), len(fig.parametric.segments))

    def test_landmark_vector(self) -> None:
        fig = self._make_figure()
        vec = fig.landmark_vector()
        # Each landmark produces 2 entries (name_dx, name_dy)
        self.assertEqual(len(vec), len(fig.landmarks) * 2)
        for key in vec:
            self.assertTrue(key.endswith("_dx") or key.endswith("_dy"))

    def test_landmark_by_name(self) -> None:
        fig = self._make_figure()
        if fig.landmarks:
            name = fig.landmarks[0].name
            found = fig.landmark_by_name(name)
            self.assertIsNotNone(found)
            self.assertEqual(found.name, name)

        self.assertIsNone(fig.landmark_by_name("nonexistent"))

    def test_backward_compat_without_enrichment(self) -> None:
        """Legacy dicts without landmarks/parametric should load cleanly."""
        legacy = {
            "meta": {"source": "old", "contour_points": 3, "detail_strokes": 0},
            "contour": [[0.1, 0.0], [0.5, 4.0], [0.1, 8.0]],
            "strokes": [],
        }
        fig = FigureData.from_dict(legacy)
        self.assertEqual(len(fig.landmarks), 0)
        self.assertIsNone(fig.parametric)
        self.assertEqual(len(fig.contour), 3)

    def test_compression_ratio_property(self) -> None:
        fig = self._make_figure()
        self.assertGreater(fig.parametric.compression_ratio, 1.0)


class TestRealDataLandmarks(unittest.TestCase):
    """Run landmark detection on actual extracted figures if available."""

    DATA_DIR = Path(__file__).parent.parent / "data" / "input_extracted"

    def test_landmarks_on_all_extracted_figures(self) -> None:
        if not self.DATA_DIR.exists():
            self.skipTest("No extracted data directory")

        json_files = list(self.DATA_DIR.glob("*.json"))
        if not json_files:
            self.skipTest("No extracted JSON files")

        for path in json_files:
            with self.subTest(file=path.name):
                data = json.loads(path.read_text())
                contour = np.array(data["contour"])
                landmarks = find_anatomical_landmarks(contour)

                # Every figure should produce at least 3 landmarks
                self.assertGreaterEqual(
                    len(landmarks), 3,
                    f"{path.name}: only {len(landmarks)} landmarks detected",
                )

                # Landmarks should have valid indices
                for lm in landmarks:
                    self.assertLess(lm.index, len(contour))
                    self.assertGreaterEqual(lm.index, 0)


if __name__ == "__main__":
    unittest.main()
