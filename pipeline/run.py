"""Run pipeline stages selectively."""
import argparse
import importlib
import logging
import sys

logger = logging.getLogger("pipeline")

STAGES = {
    1: ("Site Matching", "pipeline.stage_1_site_matching"),
    2: ("Artifact Harvesting", "pipeline.stage_2_artifact_harvest"),
    3: ("Image Collection", "pipeline.stage_3_image_collection"),
    4: ("Motif Segmentation", "pipeline.stage_4_segmentation"),
    5: ("Motif Embedding", "pipeline.stage_5_embedding"),
    6: ("Similarity + Clustering", "pipeline.stage_6_similarity"),
    7: ("Export", "pipeline.stage_7_export"),
}


def main():
    parser = argparse.ArgumentParser(description="Ancient Motif Pipeline")
    parser.add_argument("--stages", nargs="+", type=int,
                        default=list(STAGES.keys()))
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    for n in args.stages:
        if n not in STAGES:
            logger.error(f"Unknown stage: {n}")
            sys.exit(1)
        name, mod = STAGES[n]
        logger.info(f"=== Stage {n}: {name} ===")
        importlib.import_module(mod).run()
        logger.info(f"=== Stage {n} complete ===\n")


if __name__ == "__main__":
    main()
