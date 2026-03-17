"""Tests for Stage 5: CLIP embedding helpers."""

from pipeline.stage_5_embedding import extract_motif_tags


class TestExtractMotifTags:
    def test_spiral_and_wave(self):
        tags = extract_motif_tags("A spiral pattern with wave decoration")
        assert tags == ["spiral", "wave"]

    def test_multiple_patterns(self):
        tags = extract_motif_tags(
            "Geometric meander border with floral rosette in center"
        )
        assert "geometric" in tags
        assert "meander" in tags
        assert "floral" in tags
        assert "rosette" in tags

    def test_no_match(self):
        tags = extract_motif_tags("Plain undecorated pottery shard")
        assert tags == []

    def test_case_insensitive(self):
        tags = extract_motif_tags("SPIRAL and Chevron motifs")
        assert "spiral" in tags
        assert "chevron" in tags

    def test_concentric_circles(self):
        tags = extract_motif_tags("Concentric circle pattern on base")
        assert "concentric_circles" in tags

    def test_hatching_variants(self):
        tags = extract_motif_tags("Cross-hatched surface with hatching lines")
        assert "hatching" in tags

    def test_figural_variant(self):
        tags = extract_motif_tags("Figurative scene depicting warriors")
        assert "figural" in tags
