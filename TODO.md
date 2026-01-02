# Release Preparation TODO

A checklist and roadmap for preparing this project for public release.

---

## Pre-release Checklist

- [ ] **Version tagging strategy**
  - [ ] Adopt semantic versioning (MAJOR.MINOR.PATCH)
  - [ ] Create initial version tag (e.g., `v0.1.0` or `v1.0.0`)
  - [ ] Document versioning policy in README

- [ ] **CHANGELOG.md creation**
  - [ ] Create CHANGELOG.md following [Keep a Changelog](https://keepachangelog.com/) format
  - [ ] Document initial features and capabilities

- [ ] **LICENSE file verification**
  - [ ] Verify LICENSE file is present and correct
  - [ ] Ensure license headers in source files (if required)

- [ ] **PyPI packaging consideration**
  - [ ] Verify `pyproject.toml` metadata is complete
  - [ ] Add classifiers and keywords for discoverability
  - [ ] Test local installation with `pip install .`
  - [ ] Test build with `python -m build`

---

## Future Enhancements (Phase 3)

- [ ] **Incremental sync**
  - [ ] Track which notebooks have already been exported
  - [ ] Skip unchanged notebooks on subsequent runs
  - [ ] Store export metadata (timestamps, hashes)

- [ ] **Duplicate detection**
  - [ ] Detect duplicate notebook entries
  - [ ] Handle merge/deduplication strategies

- [ ] **Notebook organization**
  - [ ] Organize exports by date
  - [ ] Organize exports by topic/category
  - [ ] Configurable folder structure

- [ ] **Performance optimizations**
  - [ ] Optimize for large Obsidian vaults
  - [ ] Batch processing improvements
  - [ ] Memory usage optimization for large databases

---

## Distribution Options

- [ ] **PyPI publication**
  - [ ] Register project name on PyPI
  - [ ] Set up PyPI API token
  - [ ] Publish initial release with `twine upload`
  - [ ] Verify installation works: `pip install kobo-notebooks-markdown`

- [ ] **GitHub Releases**
  - [ ] Create GitHub Release for each version
  - [ ] Include release notes from CHANGELOG
  - [ ] Attach any built artifacts

- [ ] **Homebrew formula** (optional/future)
  - [ ] Create Homebrew tap repository
  - [ ] Write formula for macOS/Linux installation

---

## Documentation

- [ ] **API documentation** (optional)
  - [ ] Add docstrings to public functions
  - [ ] Generate docs with Sphinx or mkdocs
  - [ ] Host on GitHub Pages or Read the Docs

- [ ] **Contributing guide** (optional)
  - [ ] Create CONTRIBUTING.md
  - [ ] Document development setup
  - [ ] Define code style and PR process
  - [ ] Add issue/PR templates

---

## Quick Start for First Release

1. Finalize and test all Phase 1 & 2 features
2. Create CHANGELOG.md with initial release notes
3. Tag version `v0.1.0`
4. Publish to PyPI
5. Create GitHub Release
