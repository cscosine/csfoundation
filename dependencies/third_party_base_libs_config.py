"""Toolchain and compiler mapping configuration for third_party_base_libs.

This module defines the authoritative project name and version as single
sources of truth, and provides the ``auto_install_csorchestrator_managed_libraries``
helper that client projects can use to download the manifest, the bundle, and the
selected (pre-)compiled libraries from a GitHub release with minimal boilerplate.
"""

from pathlib import Path

from csorchestrator.application.recipes.manifest_github import (
    ManifestGithub,
    create_steps_to_get_libs_from_manifest,
)
from csorchestrator.domain.orchestrator.orchestrator import Orchestrator
from csorchestrator.foundation.core.report import Report
from csorchestrator.frontend.step.step_get_precompiled_lib_github import (
    MappingFunction,
)
from csorchestrator.portable.release_manifest import ReleaseManifest

# ---------------------------------------------------------------------------
# Single source of truth for the project identity.  ``third_party_base_libs_project.py``
# imports these constants so there is exactly one place to update on release.
# ---------------------------------------------------------------------------
THIRD_PARTY_BASE_LIBS_PROJECT_NAME: str = "third_party_base_libs"
THIRD_PARTY_BASE_LIBS_PROJECT_VERSION: str = "0.1.0"
THIRD_PARTY_BASE_LIBS_RELEASE_TAG: str = "v0.1.0-rc1"

# ---------------------------------------------------------------------------
# Authoritative list of library dependencies, derived from the
# "Library Dependency Graph" section of README.md.
#
# Only **link-time / compile-time** dependencies are listed here.  Test-only
# dependencies (e.g. pipes -> Catch2) are intentionally excluded -- they are
# documented as dotted arrows in the README and are not required for a normal
# downstream consumer.
# ---------------------------------------------------------------------------
LIBRARY_DEPENDENCIES: dict[str, list[str]] = {
    "fmt-eigen": ["eigen3", "fmt"],
    "libassert": ["cpptrace"],
}


def auto_install_csorchestrator_managed_libraries(
    orchestrator: Orchestrator,
    base_libs_dir: Path,
    manifest_description: ManifestGithub,
    manifest_loaded: ReleaseManifest,
    required_libs: list[str] | None = None,
    mapping_function: MappingFunction | None = None,
) -> Report:

    # TODO resolve libs for transitive deps and resolve "none" --> all libs
    # opt1: here, but then every libs has to handle, opt2, in create_steps_to_get_libs_from_manifest

    return create_steps_to_get_libs_from_manifest(
        orchestrator=orchestrator,
        manifest_description=manifest_description,
        manifest_loaded=manifest_loaded,
        base_libs_dir=base_libs_dir,
        lib_name_list=required_libs,
        mapping_function=mapping_function,
    )
