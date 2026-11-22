---
name: csfoundation-orchestrator-recipe
description: >-
  Manages, audits, and maintains the csfoundation build recipe for the cscosine
  base C++ libraries (csCore, csLie, csCamera, csVisOpenGL, built with csCMake)
  powered by csorchestrator. Use when inspecting or updating the base-libraries
  build pipeline, validating recipe consistency (extra files, versions,
  repositories, providers), re-generating the GitHub Actions CI workflow, or
  running pre-commit and quality checks.
---

# csfoundation Orchestrator Recipe Management

## Overview

csfoundation is a distribution: its recipe checks out the four first-party libraries, downloads their precompiled
dependencies from other releases (its providers), builds them on every platform and publishes them as one release
(packages + `csfoundation-<version>.csOrchestratorManifest`). How a project uses csorchestrator in general: the
`csorchestrator-usage` skill of the `csorchestrator` plugin (`cscosine` marketplace).

## The files

- [`csfoundation_project.py`](../../../csfoundation_project.py): the recipe: the libraries and their refs (`repos`,
  `RepoRefBuildPublishConfig("main", BuildConfig...)`), the csCMake release (`cscmake_version`), the version and the
  weekly slot (`create_default_orchestrator`), the deployments of the csVisOpenGL sample and their smoke test.
- [`csfoundation_config.py`](../../../csfoundation_config.py): shipped in the release (`additional_files_list`) for
  the consumers, who load it from their `dependencies/` folder:
  - `LIBRARY_LIST`, `LIBRARY_DEPENDENCIES` (first-party edges: csLie, csCamera, csVisOpenGL → csCore),
    `LIBRARY_DEPENDENCIES_DEV`;
  - `install_requirements()`: Ubuntu packages (`libomp-dev` always, the OpenGL packages only with csVisOpenGL);
  - `install_csfoundation_build_dependencies()`: the providers (`ManifestGithub`: third_party_base_libs and csqt6, at
    their release tags) and, per library, what it needs from each (`external_dependencies`, `..._dev` for the tests:
    Catch2; csVisOpenGL → csqt6 `qt6` with the `qt6_mapping` function of csqt6);
  - `auto_install_csorchestrator_managed_libraries()`: the entry point a consumer's recipe calls (through its
    `dependencies/csfoundation_config.py`): the dependencies above, then the requested csfoundation packages.
- `dependencies/`: the providers' manifests and configs, downloaded by the recipe: never edited by hand.
- `csorchestratorsdk/portable/`, `.github/workflows/csfoundation.yml`: generated.

**Consistency checks (fail loudly, report to the user rather than guess):**

- Every path in `additional_files_list` exists.
- The version in `create_default_orchestrator(version=...)` matches `pyproject.toml` at release time (the release
  commit sets both).
- Every library in `repos` is in `LIBRARY_LIST`, and `LIBRARY_DEPENDENCIES` matches the `cs_find_package` calls of
  the libraries' `CMakeLists.txt` (e.g. csLie finds csCore).
- The provider tags in `csfoundation_config.py` are released (a missing release fails every command of the recipe,
  which downloads the manifests first).

## Local execution policy

Do not run the recipe (`./csfoundation_project.py`): it builds every library for the whole pipeline. Use
`./csfoundation_project.py describe`, `pytest`, and CI (a tag build is the test of a release; a feature branch:
`gh workflow run csfoundation.yml --ref feature/<topic>`).

## Regenerating the workflow

After any change of `csfoundation_project.py` or `csfoundation_config.py`:

```bash
./csfoundation_project.py generate-github-workflow
git diff .github/workflows/csfoundation.yml
```

Commit the recipe, the workflow, `dependencies/` and `csorchestratorsdk/` together.

## Quality checks

```bash
pre-commit run --all-files
```

## Documentation

When the libraries, their dependencies, the providers or the version change, update `README.md` (included libraries,
dependencies, graph) and the `csfoundation-libs` skill (`agent-plugin/skills/csfoundation-libs/SKILL.md`).

## Common mistakes

1. Running the full recipe locally.
2. Changing the recipe without regenerating the workflow.
3. A file in `additional_files_list` that does not exist: the release job fails.
4. A dependency added in a library's `CMakeLists.txt` but not in `csfoundation_config.py`: the package is not
   downloaded in CI, the configure fails with `find_package` errors.
