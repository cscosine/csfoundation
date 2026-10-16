import importlib
from pathlib import Path

from csorchestrator.application.recipes.manifest_github import (
    ExternalLibraryDependenciesMap,
    LibraryDependenciesMap,
    LibraryList,
    ManifestGithub,
    ProviderList,
    download_manifest,
    download_manifest_bundle,
    extract_provider_libs_list,
    extract_provider_names,
    fill_in_libraries_in_dependecies,
    fill_in_library_list,
    fill_in_providers_and_libs_in_dependencies,
    install_ubuntu_apt_packages,
    merge_library_dependencies,
    merge_providers_dependencies,
    resolve_library_dependencies,
)
from csorchestrator.domain.orchestrator.orchestrator import Orchestrator
from csorchestrator.foundation.core.report import Report
from csorchestrator.frontend.step.step_get_precompiled_lib_github import (
    StepGetPrecompiledLibGithub,
)
from csorchestrator.portable.release_manifest import ReleaseManifest

LIBRARY_LIST: LibraryList = ["csCore", "csLie", "csCamera", "csVisOpenGL"]

# project internal dependencies
LIBRARY_DEPENDENCIES: LibraryDependenciesMap = {
    "csCore": [],
    "csLie": ["csCore"],
    "csCamera": ["csCore"],
    "csVisOpenGL": ["csCore"],
}

# project additional dependencies for `dev`
LIBRARY_DEPENDENCIES_DEV: LibraryDependenciesMap = {
    "csCore": [],
    "csLie": [],
    "csCamera": [],
    "csVisOpenGL": [],
}

# external providers
THIRD_PARTY_BASE_LIBS_PROVIDER = ManifestGithub(
    base_url=StepGetPrecompiledLibGithub.GITHUB_BASE_URL_HTTPS,
    org="cscosine",
    git_repo="third_party_base_libs",
    project_name="third_party_base_libs",
    project_version="0.1.0",
    release_tag="v0.1.0-rc1",
)

CSQT6_PROVIDER = ManifestGithub(
    base_url=StepGetPrecompiledLibGithub.GITHUB_BASE_URL_HTTPS,
    org="cscosine",
    git_repo="csqt6",
    project_name="csqt6",
    project_version="6.11.1",
    release_tag="v6.11.1-rc1",
)

EXTERNAL_PROVIDERS: ProviderList = [
    THIRD_PARTY_BASE_LIBS_PROVIDER,
    CSQT6_PROVIDER,
]

# we should not need this...
EXTERNAL_PROVIDERS_MAP: dict[str, ManifestGithub] = {
    THIRD_PARTY_BASE_LIBS_PROVIDER.project_name: THIRD_PARTY_BASE_LIBS_PROVIDER,
    CSQT6_PROVIDER.project_name: CSQT6_PROVIDER,
}

EXTERNAL_DEPENDENCIES: ExternalLibraryDependenciesMap = {
    # provider third_party_base_libs
    THIRD_PARTY_BASE_LIBS_PROVIDER.project_name: {
        "csCore": ["eigen3", "fmt", "fmt-eigen", "libassert", "pipes", "NamedType", "tl-expected", "tl-optional"],
        "csLie": ["eigen3"],
        "csCamera": ["eigen3"],
        "csVisOpenGL": ["eigen3"],
    },
    # provider qt6
    CSQT6_PROVIDER.project_name: {
        "csCore": [],
        "csLie": [],
        "csCamera": [],
        "csVisOpenGL": ["qt6"],
    },
}

EXTERNAL_DEPENDENCIES_DEV: ExternalLibraryDependenciesMap = {
    # provider third_party_base_libs
    THIRD_PARTY_BASE_LIBS_PROVIDER.project_name: {
        "csCore": ["Catch2"],
        "csLie": ["Catch2"],
        "csCamera": ["Catch2"],
        "csVisOpenGL": ["Catch2"],
    },
    # provider qt6
    CSQT6_PROVIDER.project_name: {
        "csCore": [],
        "csLie": [],
        "csCamera": [],
        "csVisOpenGL": [],
    },
}


def install_requirements(
    orchestrator: Orchestrator,
    lib_list: list[str] | None = None,  # none means all
) -> None:
    """Install the Linux system requirements needed by the requested libraries.

    The OpenGL system packages are only required by ``csVisOpenGL``, so they
    are installed only when it is in ``lib_list`` (``None`` means all
    libraries).
    """

    lib_list = fill_in_library_list(lib_list, LIBRARY_LIST)

    if "csVisOpenGL" in lib_list:
        install_ubuntu_apt_packages(
            orchestrator,
            [
                "libgl1-mesa-dev",
                "libopengl-dev",
                "mesa-common-dev",
            ],
        )


def install_csfoundation_build_dependencies(
    orchestrator: Orchestrator,
    base_libs_dir: Path,
    dependencies_config_path: str,
    dev: bool,
    required_libs: list[str] | None = None,
) -> Report:

    report = Report()

    # the packages we need to install
    install_requirements(orchestrator, required_libs)

    # the library requested
    required_libs = fill_in_library_list(required_libs, LIBRARY_LIST)

    # the library self dependencies
    libs_self_dependencies = fill_in_libraries_in_dependecies(LIBRARY_DEPENDENCIES, LIBRARY_LIST)
    if dev:
        # extend them if we are in dev mode
        libs_self_dependencies = merge_library_dependencies(
            fill_in_libraries_in_dependecies(LIBRARY_DEPENDENCIES, LIBRARY_LIST),
            fill_in_libraries_in_dependecies(LIBRARY_DEPENDENCIES_DEV, LIBRARY_LIST),
        )

    # the library effectively requested, after resolving dependencies
    required_libs = resolve_library_dependencies(required_libs, libs_self_dependencies)

    # the indirect dependencies
    libs_external_dependencies = fill_in_providers_and_libs_in_dependencies(
        EXTERNAL_DEPENDENCIES, extract_provider_names(EXTERNAL_PROVIDERS), LIBRARY_LIST
    )
    if dev:
        libs_external_dependencies_dev = fill_in_providers_and_libs_in_dependencies(
            EXTERNAL_DEPENDENCIES_DEV, extract_provider_names(EXTERNAL_PROVIDERS), LIBRARY_LIST
        )
        libs_external_dependencies = merge_providers_dependencies(
            libs_external_dependencies, libs_external_dependencies_dev
        )

    for _, provider_manifest_desc in EXTERNAL_PROVIDERS_MAP.items():
        manifest_filename = Path(provider_manifest_desc.create_manifest_filename())

        manifest = download_manifest(provider_manifest_desc, Path(dependencies_config_path))
        report.append_report(manifest.report)
        if manifest.result is not None:
            report.append_report(
                download_manifest_bundle(
                    provider_manifest_desc,
                    ReleaseManifest.load_release_manifest(manifest.result),
                    Path(dependencies_config_path),
                )
            )

    if report.has_errors():
        return report

    # for each provider, load the module it provides and run its autoinstall
    provider_libs_list = extract_provider_libs_list(libs_external_dependencies)

    for provider, libs in provider_libs_list.items():
        module_name = f"{dependencies_config_path}.{provider}_config"

        provider_module = importlib.import_module(module_name)

        provider_manifest_desc = EXTERNAL_PROVIDERS_MAP[provider]

        manifest_filename = Path(provider_manifest_desc.create_manifest_filename())

        provider_manifest_loaded = ReleaseManifest.load_release_manifest(dependencies_config_path / manifest_filename)

        report.append_report(
            provider_module.auto_install_csorchestrator_managed_libraries(
                orchestrator=orchestrator,
                base_libs_dir=base_libs_dir,
                required_libs=libs,
                manifest_description=provider_manifest_desc,
                manifest_loaded=provider_manifest_loaded,
                # mapping ?
            )
        )

    return report
