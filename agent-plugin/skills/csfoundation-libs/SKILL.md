---
name: csfoundation-libs
description: The cscosine base C++ libraries released by csfoundation - csCore (asserts, CS_OMP OpenMP macro, float32_t / float64_t, fmt formatting, expected / optional, NamedType, angles, Eigen rotation / isometry checks, Catch2 test utilities), csLie (SO2, SO3, SE2, SE3, S2 exp / log / adjoint on Eigen), csCamera (pinhole and Mei / unified camera models, distortion, projection with Jacobians), csVisOpenGL (Qt OpenGL 3D view, renderers, painters). Use when C++ code in a cscosine project needs one of these capabilities, includes a csCore / csLie / csCamera / csVisOpenGL header, or its CMakeLists.txt finds one of these packages, or when adding one of them to a project.
---

# The csfoundation libraries

csfoundation builds and releases four first-party libraries (C++17, on Eigen; csCMake packages with components),
each in its own repository: `cscosine/csCore`, `csLie`, `csCamera`, `csVisOpenGL`. Before writing a helper for one of
the needs below, use the library: one concern, one place.

## Which library for what

| Need | Library, component | Header / API |
|---|---|---|
| `float32_t`, `float64_t`, float type traits | csCore `core` | `csCore/core/BasicTypes.hpp` (`csCore::core::is_float32_or_64_t`) |
| OpenMP that also builds without it | csCore `core` | `csCore/core/OpenMP.hpp`: `CS_OMP(parallel for ...)` instead of `#pragma omp` (indented like the statement it precedes), `csCore::core::ompMaxThreads()`; the target also calls csCMake `cs_target_use_openmp` |
| asserts | csCore `assert` (libassert) | `csCore/assert/Assert.hpp`: `CS_ASSERT`, `CS_DEBUG_ASSERT`, `CS_ASSUME`, `CS_PANIC`, `CS_UNREACHABLE`, `*_VAL` forms |
| per-configuration assert levels of a project | csCore `assert` | CMake `cs_assert_generate_project(<project> <namespace>)` → `<namespace>::<project>Assert`, header `<project>/<project>Assert.hpp`, macros `<PROJECT>_ASSERT_<LEVEL>` (`RELEASE`, `RELWITHDEBINFO`, `DEBUG`, `PARANOID`, `SAFE_MATH`); defaults per configuration with `cs_assert_set_default_on_for_config` |
| string formatting (fmt) | csCore `format`; Eigen types: `formatEigen` | `csCore/format/Format.hpp` (and `Core`, `Ranges`, `Chrono`, `Std`, ...: the fmt headers); `csCore/formatEigen/FormatEigen.hpp` |
| `expected`, `optional` (C++17) | csCore `language` (tl-expected, tl-optional) | `csCore/language/Expected.hpp`, `Optional.hpp`: `csCore::language::expected`, `optional` |
| strong types | csCore `namedType` (NamedType) | `csCore/namedType/NamedType.hpp`: `csCore::namedType::NamedType<...>` |
| angles | csCore `math` | `csCore/math/Angles.hpp`: `degToRad`, `radToDeg`, `wrapToPi`, `angleDistance` |
| Eigen checks | csCore `eigenUtils` | `RotationMatrix.hpp` (`isValidRotationMatrix2D/3D`), `IsometryMatrix.hpp`, `MatrixShape.hpp` |
| test helpers (Catch2) | csCore `testUtils` | tests only (`PRIVATE`) |
| Lie groups | csLie | `csLie/SO2.hpp`, `SO3.hpp`, `SE2.hpp`, `SE3.hpp`, `S2.hpp`: free functions `so3Exp`, `so3Log`, `se3Exp`, `se3Log`, `se3Adjoint`, ...; types in `csLie/Types.hpp` are plain Eigen types (`SO3<S>` = `Eigen::Matrix<S, 3, 3>`, `SE3<S>` = `Eigen::Transform<S, 3, Eigen::Isometry>`, `SO3Alg<S>` / `SE3Alg<S>` = tangent vectors of size 3 / 6; `d` / `f` suffixes for double / float) |
| camera models | csCamera | `csCamera/Camera.hpp`: `Camera<T>` (pinhole: `fx`, `fy`, `cx`, `cy`, `K()`, `points3D_to_image`, `pointsImage_to_Z1`, `pointsZ1_to_image`, Jacobians), `CameraMei<T>` (unified model, `epsilon`); `CameraDistortionModel.hpp` (OpenCV-style rational, tangential, thin prism) |
| 3D view in a Qt application | csVisOpenGL `csVisOpenGL` (Qt6 Widgets / OpenGL, OpenGL) | `csVisOpenGL/Frame.hpp`: `Frame` (a `QOpenGLWidget`), `addVisualizer(std::shared_ptr<VisualizerInterface>)`; implement `VisualizerInterface` (`initialize`, `update`, `paint`, `paintTransparent`, `paintQt`, ...); `OrbitCameraController` |
| drawing points, lines, meshes, textures | csVisOpenGL `renderers` | `csVisOpenGL/renderers/*`: `PerVertexPointRenderer`, `UniformLineRenderer`, `MeshRenderer`, `SingleTextureRenderer`, `UniformEllipsoidsRenderer`, ... |
| axes, grid, boxes, cameras, checkerboard | csVisOpenGL `painters` | `csVisOpenGL/painters/Painter*.hpp` |

csVisOpenGL has a sample (`sample/` in its repository) showing a window with a `Frame` and visualizers.

## In CMake (csCMake)

Find the package with its components, link the targets `<package>::<component>`:

```cmake
cs_find_package(myLib PUBLIC csCore COMPONENTS core assert math REQUIRED CONFIG)
cs_find_package(myLib PUBLIC csLie REQUIRED CONFIG)
cs_find_package(myApp PUBLIC csVisOpenGL COMPONENTS csVisOpenGL painters renderers REQUIRED CONFIG)
cs_target_link_libraries(myLib PUBLIC csCore::core csCore::assert csCore::math csLie::csLie)
cs_find_package(myLibTest PRIVATE csCore COMPONENTS testUtils REQUIRED CONFIG)
```

- Packages: `csCore` (components `core`, `assert`, `format`, `formatEigen`, `language`, `namedType`, `math`,
  `eigenUtils`, `testUtils`), `csLie`, `csCamera` (component = the package name, default), `csVisOpenGL`
  (`csVisOpenGL`, `renderers`, `painters`).
- Their own dependencies (Eigen3, fmt, libassert, tl-expected / tl-optional, NamedType, Qt6, OpenGL) are found by
  their package configs: a project does not repeat them, but must have them installed (below).
- `cs_assert_generate_project` comes from the installed csCore: `find_package(csCore REQUIRED COMPONENTS assert
  CONFIG)`, `list(APPEND CMAKE_MODULE_PATH "${csCore_BASE_DIR}/cmake/csCore/assert/")`, `include(csAssert)`, before
  the call.

## Getting them into a project

A csorchestrator project takes the prebuilt packages from the csfoundation release (its provider) instead of building
them: in `<name>_config.py`, a `ManifestGithub(org="cscosine", git_repo="csfoundation",
project_name="csfoundation", project_version="0.1.0", release_tag="v0.1.0")` and the libraries each target needs,
e.g. `{"csfoundation": {"myApp": ["csCore", "csVisOpenGL"]}}`; csfoundation's own providers (third_party_base_libs,
csqt6 for csVisOpenGL) come with it. Then `./<name>_project.py generate-github-workflow`. See the
`csorchestrator-usage` skill of the `csorchestrator` plugin. The packages land in `workspace/libs/<variant>`, which
the csCMake presets put in `CMAKE_PREFIX_PATH`.

Release versions: the [csfoundation releases](https://github.com/cscosine/csfoundation/releases) (each library also
has its own semver tag on the commit built). Changing a library itself: its repository, built and validated by
csfoundation's CI (an inner repository: no CI of its own).
