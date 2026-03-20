"""Tests for Stage 4: CLIPSeg segmentation helpers."""

import numpy as np

from pipeline.stage_4_segmentation import count_svg_paths, filter_segments


class TestFilterSegments:
    """Test connected-component filtering by area ratio and aspect ratio."""

    def _make_stats(self, components: list[tuple[int, int, int, int, int]]) -> np.ndarray:
        """Build a stats array with a background row prepended."""
        bg = (0, 0, 100, 100, 10000)  # background row
        rows = [bg] + list(components)
        return np.array(rows, dtype=np.int32)

    def test_keeps_good_segment(self):
        # area_ratio = 500 / 10000 = 0.05  (within 0.03 .. 0.40)
        # aspect = 50/10 = 5.0 (equal to max, should pass)
        stats = self._make_stats([(0, 0, 50, 10, 500)])
        kept = filter_segments(stats, image_area=10000)
        assert kept == [1]

    def test_rejects_too_small(self):
        # area_ratio = 10 / 10000 = 0.001  (below 0.03)
        stats = self._make_stats([(0, 0, 10, 1, 10)])
        kept = filter_segments(stats, image_area=10000)
        assert kept == []

    def test_rejects_too_large(self):
        # area_ratio = 6000 / 10000 = 0.6  (above 0.55)
        stats = self._make_stats([(0, 0, 100, 60, 6000)])
        kept = filter_segments(stats, image_area=10000)
        assert kept == []

    def test_rejects_bad_aspect_ratio(self):
        # area_ratio = 600 / 10000 = 0.06  (OK)
        # aspect = 100/1 = 100  (above 5.0)
        stats = self._make_stats([(0, 0, 100, 1, 600)])
        kept = filter_segments(stats, image_area=10000)
        assert kept == []

    def test_multiple_components(self):
        stats = self._make_stats([
            (0, 0, 50, 10, 500),   # good
            (0, 0, 10, 1, 10),     # too small
            (0, 0, 20, 20, 800),   # good
        ])
        kept = filter_segments(stats, image_area=10000)
        assert kept == [1, 3]


class TestCountSvgPaths:
    def test_counts_paths(self):
        svg = '<svg><path d="M0 0"/><path d="M1 1"/></svg>'
        assert count_svg_paths(svg) == 2

    def test_zero_paths(self):
        assert count_svg_paths("<svg><rect/></svg>") == 0

    def test_case_insensitive(self):
        svg = '<svg><Path d="M0 0"/><PATH d="M1 1"/></svg>'
        assert count_svg_paths(svg) == 2
