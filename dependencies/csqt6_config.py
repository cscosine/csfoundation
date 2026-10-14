"""Toolchain and compiler mapping configuration for csqt6.

This module defines the authoritative project name and version as single
sources of truth, keeps the toolchain mapping used by the build recipe, and
provides the ``auto_install_csorchestrator_managed_libraries`` helper that
client projects can use to download the manifest, the bundle, and the
selected (pre-)compiled Qt libraries from a GitHub release with minimal
boilerplate.
"""

from pathlib import Path

from csorchestrator.application.recipes.manifest_github import (
    ManifestGithub,
    create_steps_to_get_libs_from_manifest,
)
from csorchestrator.domain.context.context_compiler_generator import (
    Compiler,
    ContextCompilerGenerator,
    GeneratorWithType,
)
from csorchestrator.domain.context.context_os_architecture import OS
from csorchestrator.domain.context.context_os_architecture_compiler_generator import (
    ContextOsArchitectureCompilerGenerator,
)
from csorchestrator.domain.orchestrator.orchestrator import Orchestrator
from csorchestrator.foundation.core.report import Report
from csorchestrator.frontend.step.step_get_precompiled_lib_github import (
    MappingFunction,
)
from csorchestrator.portable.release_manifest import ReleaseManifest

# ---------------------------------------------------------------------------
# Single source of truth for the project identity.  ``csqt6_project.py``
# imports these constants so there is exactly one place to update on release.
# Please keep the version aligned with the Qt release being built.
# ---------------------------------------------------------------------------
CSQT6_PROJECT_NAME: str = "csqt6"
CSQT6_PROJECT_VERSION: str = "6.11.1"
CSQT6_PROJECT_RELEASE_TAG: str = "v6.11.1-rc1"

# ---------------------------------------------------------------------------
# Authoritative list of library dependencies.
#
# The Qt 6 build is a self-contained, single-source project: the qt6
# repository does not depend on any other csorchestrator-managed library,
# so this map is intentionally empty.  It is kept here so the auto-install
# helper stays drop-in compatible with the csorchestrator download API (and
# so future dependencies can be added without touching the helper).
# ---------------------------------------------------------------------------
LIBRARY_DEPENDENCIES: dict[str, list[str]] = {}


def qt6_mapping(
    context: ContextOsArchitectureCompilerGenerator,
) -> ContextOsArchitectureCompilerGenerator | None:
    if context.context_os_architecture.os == OS.LINUX:
        new_context = context
        new_context.context_compiler_generator = ContextCompilerGenerator(
            compiler_family=Compiler.GCC,
            compiler_version=ContextCompilerGenerator.COMPILER_VERSION_DEFAULT,
            build_generator=GeneratorWithType.NINJA,
        )
        return new_context
    elif context.context_os_architecture.os == OS.WINDOWS:
        new_context = context
        new_context.context_compiler_generator = ContextCompilerGenerator(
            compiler_family=Compiler.MSVC,
            compiler_version=ContextCompilerGenerator.COMPILER_VERSION_MSVC_2022_17,
            build_generator=GeneratorWithType.NINJA,
        )
        return new_context
    return None


def auto_install_csorchestrator_managed_libraries(
    orchestrator: Orchestrator,
    base_libs_dir: Path,
    manifest_description: ManifestGithub,
    manifest_loaded: ReleaseManifest,
    required_libs: list[str] | None = None,
    mapping_function: MappingFunction | None = qt6_mapping,
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
