"""Stable, versioned serialization of the pronunciation feature vector.

Used by training/evaluation tooling and the shadow runner so that identical
inputs always produce byte-identical feature vectors under one version.
"""

import hashlib
import json

from .policy import FEATURE_VERSION


def canonical_features(features: dict) -> dict:
    """Round floats deterministically and drop None-free nested noise."""
    return json.loads(json.dumps(features, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=True, default=str))


def feature_vector_checksum(features: dict) -> str:
    canonical = json.dumps(canonical_features(features), sort_keys=True,
                           separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def serialize_feature_vector(features: dict) -> dict:
    canonical = canonical_features(features)
    return {
        "feature_version": FEATURE_VERSION,
        "checksum": feature_vector_checksum(canonical),
        "features": canonical,
    }
