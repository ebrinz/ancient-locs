import pytest
import numpy as np
from pipeline.stage_6_similarity import jaccard_similarity, combined_score, find_medoid

def test_jaccard_identical():
    assert jaccard_similarity(["spiral", "wave"], ["spiral", "wave"]) == 1.0

def test_jaccard_partial():
    assert jaccard_similarity(["spiral", "wave"], ["spiral", "cross"]) == pytest.approx(1/3)

def test_jaccard_empty():
    assert jaccard_similarity([], []) == 0.0

def test_combined_score():
    s = combined_score(tag_score=0.5, embed_score=0.8, tag_w=0.3, embed_w=0.7)
    assert s == pytest.approx(0.5 * 0.3 + 0.8 * 0.7)

def test_find_medoid():
    embeddings = np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]])
    centroid = np.array([0.95, 0.05])
    assert find_medoid(embeddings, centroid) == 1
