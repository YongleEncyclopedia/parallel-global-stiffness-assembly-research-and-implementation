# Third-Party Dependency Notice

The delivery archive contains no vendored third-party source code, binary
library, compiler runtime, package-manager cache, or prebuilt executable.

Building and testing the demo requires tools and runtimes supplied separately
by the evaluation environment:

- a C++17 compiler and its standard library;
- an OpenMP implementation compatible with that compiler, such as GCC
  `libgomp`, LLVM `libomp`, or the Microsoft Visual C++ OpenMP runtime;
- CMake 3.21 or newer;
- Ninja;
- Git, used by the package contract tests to create isolated fixture repositories;
- Python 3.11 or newer for the evidence, report, package, and repository
  contract tests.

Those components are not redistributed in this archive. Their copyright,
license, installation, and export terms are controlled by their respective
suppliers. Evaluators are responsible for using approved copies on the target
system.

The absence of vendored third-party material does not change the demo's own
distribution status. The project source remains **INTERNAL EVALUATION ONLY**
until the repository owner adopts a public license and release policy.
