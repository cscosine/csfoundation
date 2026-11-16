#!/usr/bin/env python3
import sys
from collections.abc import Sequence
from pathlib import Path

from csorchestrator.application.cli.cli import orchestrator_main_with_default_run
from csorchestrator.application.factory.factory import OptionalOrchestratorWithReport
from csorchestrator.application.recipes.checkout_build import (
    build_repos,
    checkout_repos,
    create_and_upload_artifacts,
    create_and_upload_deployments,
)
from csorchestrator.application.recipes.create_orchestrator import create_default_orchestrator
from csorchestrator.application.recipes.cscmake_release import create_cscmake_release_archive
from csorchestrator.application.recipes.gui_deployments import add_gui_deployment_smoke_test_return_0
from csorchestrator.application.recipes.repos_config import (
    RepoRefBuildPublishConfig,
    RepoRefBuildPublishConfigDict,
    extract_build_config_dict,
    extract_repo_list_build_non_none,
    extract_repo_ref_dict,
)
from csorchestrator.foundation.core.report import Report
from csorchestrator.frontend.cscmake_presets.supported_variants import (
    BuildConfig,
    get_context_list_linux,
    get_context_list_macos,
)
from csorchestrator.frontend.step.step_get_precompiled_lib_github import identity_mapping_function

from csfoundation_config import (
    LIBRARY_DEPENDENCIES,
    LIBRARY_DEPENDENCIES_DEV,
    install_csfoundation_build_dependencies,
)


def create_orchestrator() -> OptionalOrchestratorWithReport:
    report = Report()

    base_target_dir = Path("workspace")
    base_install_dir = base_target_dir / Path("install")
    base_libs_dir = base_target_dir / Path("libs")
    base_build_dir = base_target_dir / Path("build")
    deploy_archives_dir = base_target_dir / Path("deploy-archives")
    common_repo_ref = "dev"
    cscmake_version = "1.0.0-rc7"
    build_config = BuildConfig.DEBUG_RELEASE_RELWITHDEBINFO_PARANOID

    repos: RepoRefBuildPublishConfigDict = {
        "csCore": RepoRefBuildPublishConfig(common_repo_ref, BuildConfig.DEBUG_RELEASE_RELWITHDEBINFO_PARANOID),
        "csLie": RepoRefBuildPublishConfig(common_repo_ref, BuildConfig.DEBUG_RELEASE_RELWITHDEBINFO_PARANOID),
        "csCamera": RepoRefBuildPublishConfig(common_repo_ref, BuildConfig.DEBUG_RELEASE_RELWITHDEBINFO_PARANOID),
        "csVisOpenGL": RepoRefBuildPublishConfig(common_repo_ref, BuildConfig.DEBUG_RELEASE_RELWITHDEBINFO_PARANOID),
    }

    # convert to dict[str, set(str)]
    library_dependencies: dict[str, set[str]] = {
        name: set(dependencies) for name, dependencies in LIBRARY_DEPENDENCIES.items()
    }

    library_dependencies_dev: dict[str, set[str]] = {
        name: set(dependencies) for name, dependencies in LIBRARY_DEPENDENCIES_DEV.items()
    }

    o = create_default_orchestrator(
        name="csfoundation",
        version="0.1.0",
        base_install_dir=base_install_dir,
        additional_files_list=[Path("csfoundation_config.py")],
        repo_dependencies_dict=library_dependencies,
        repo_dependencies_dev_dict=library_dependencies_dev,
        # opt-in variants: Ubuntu 26.04 (as 22.04/24.04), macOS 15/26 (Ninja Multi-Config, Xcode)
        additional_matrix_list=(
            get_context_list_linux("ubuntu26.04")
            + get_context_list_macos("macos15")
            + get_context_list_macos("macos26")
        ),
    )

    # ----------------------------------------------------------------
    checkout_repos(
        orchestrator=o,
        base_target_dir=base_target_dir,
        repo_ref_dict=extract_repo_ref_dict(repos),
        repo_access_token="${{ secrets.ACTIONS_ORG_ACCESS }}",
        release_archive_list=[create_cscmake_release_archive(cscmake_version)],
    )

    # ----------------------------------------------------------------
    # Install Requirements (Linux-Ubuntu) & Get Precompiled Libraries
    #
    # The auto-install helper installs the Linux system requirements for the
    # libraries being built and downloads, transitively and cross-repo, only
    # the managed libraries they need from the third_party_base_libs and
    # csqt6 releases (e.g. qt6 only when csVisOpenGL is built).
    built_first_party_libs = extract_repo_list_build_non_none(extract_build_config_dict(repos))

    report.append_report(
        install_csfoundation_build_dependencies(
            orchestrator=o,
            base_libs_dir=base_libs_dir,
            required_libs=built_first_party_libs,
            dev=True,
            dependencies_config_path=Path("dependencies"),
            mapping_function=identity_mapping_function,
            download_dependencies_manifest_and_bundle=True,
            phase_name_suffix="csoptimization dependencies",
        )
    )

    # ----------------------------------------------------------------
    build_repos(
        orchestrator=o,
        base_target_dir=base_target_dir,
        repo_build_config_dict=extract_build_config_dict(repos),
    )

    create_and_upload_artifacts(
        orchestrator=o,
        base_install_dir=base_install_dir,
        repos_auto_search_list=built_first_party_libs,
    )

    # ----------------------------------------------------------------
    # deployments (cs_deployment in csVisOpenGL/sample/CMakeLists.txt, made by the install): archived, uploaded,
    # attached to the release; then run, extracted from their archive, with a clean environment: the closing check of
    # the whole chain (third_party_base_libs, csqt6, the libraries of csfoundation, the deployment of csCMake)
    if "csVisOpenGL" in built_first_party_libs:
        create_and_upload_deployments(
            orchestrator=o,
            base_build_dir=base_build_dir,
            build_config=build_config,
            output_dir=deploy_archives_dir,
        )
        add_gui_deployment_smoke_test_return_0(
            o,
            deployment="sample",
            executable="bin/csVisOpenGLSample",
            base_build_dir=base_build_dir,
            build_config=build_config,
            archives_dir=deploy_archives_dir,
        )

    # single return point
    if report.has_errors():
        return OptionalOrchestratorWithReport.create_report(report)
    return OptionalOrchestratorWithReport.create_result_and_report(o, report)


def main(argv: Sequence[str] | None = None) -> int:
    script_path = str(Path(__file__).resolve())
    return orchestrator_main_with_default_run(script_path, argv)


if __name__ == "__main__":
    sys.exit(main())
