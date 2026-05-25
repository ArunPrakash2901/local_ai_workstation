# Human Review Artifacts

This directory contains static HTML review surfaces and associated metadata for product development artifacts.

## Purpose

The Human Review Artifact Layer (v0.2) provides a visual and structured way for human operators to inspect, judge, and approve generated planning artifacts.

- **Markdown/JSON** remain the canonical source of truth (Bucket 1).
- **HTML** serves as the human review surface (Bucket 2).
- **Interactive Playgrounds** are for future development (Bucket 3).

## Directory Structure

- `contracts/`: Definitions and doctrine for review artifacts.
- `html/`: Generated static HTML review pages and dashboards.
- `manifests/`: JSON manifests tracking generated review artifacts and source checksums.
- `reports/`: Markdown reports summarizing the generation of review artifacts.

## Usage

Review surfaces are generated using `product_development_lane/tools/build_review_html.py`. These files are intended for manual inspection in a web browser or VS Code's built-in preview.

## Safety Notice

HTML review surfaces are **read-only representations**. They do not:
- Execute worker prompts.
- Create, checkout, or modify branches.
- Commit, push, or merge code.
- Store approval decisions (this remains in Bucket 1).
