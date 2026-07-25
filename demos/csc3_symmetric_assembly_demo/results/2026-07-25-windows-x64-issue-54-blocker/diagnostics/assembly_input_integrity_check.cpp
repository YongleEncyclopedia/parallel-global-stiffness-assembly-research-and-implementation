#include "csc3_demo/assembly_helper.h"
#include "csc3_demo_tools/evidence.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <exception>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

std::uint64_t bits(double value) noexcept {
    std::uint64_t result = 0;
    static_assert(sizeof(result) == sizeof(value));
    std::memcpy(&result, &value, sizeof(result));
    return result;
}

void validate_initial_batch(const csc3_demo::evidence::AssemblyCase& assembly_case) {
    const auto& map = assembly_case.element_dof_map;
    const auto& batch = assembly_case.element_matrices;
    if (batch.element_value_offsets.size() != map.element_ids.size() + 1) {
        throw std::runtime_error("matrix offset count mismatch");
    }
    for (std::size_t element = 0; element < map.element_ids.size(); ++element) {
        const std::size_t dimension = static_cast<std::size_t>(
            map.element_dof_offsets[element + 1] - map.element_dof_offsets[element]);
        const std::size_t begin =
            static_cast<std::size_t>(batch.element_value_offsets[element]);
        const std::size_t end =
            static_cast<std::size_t>(batch.element_value_offsets[element + 1]);
        if (end - begin != dimension * dimension) {
            throw std::runtime_error("matrix segment size mismatch");
        }
        for (std::size_t row = 0; row < dimension; ++row) {
            for (std::size_t column = 0; column < dimension; ++column) {
                const double value =
                    batch.values_row_major[begin + row * dimension + column];
                if (!std::isfinite(value)) {
                    throw std::runtime_error("initial matrix contains nonfinite value");
                }
                if (bits(value) !=
                    bits(batch.values_row_major[begin + column * dimension + row])) {
                    std::cerr << "INITIAL_NONSYMMETRY element=" << element
                              << " row=" << row << " column=" << column
                              << " upper_bits=0x" << std::hex << std::setw(16)
                              << std::setfill('0') << bits(value)
                              << " lower_bits=0x" << std::setw(16)
                              << bits(batch.values_row_major[
                                     begin + column * dimension + row])
                              << std::dec << '\n';
                    throw std::runtime_error("initial matrix is not bitwise symmetric");
                }
            }
        }
    }
}

void require_unchanged(const std::vector<double>& baseline,
                       const std::vector<double>& observed,
                       const std::string& stage) {
    if (baseline.size() != observed.size()) {
        throw std::runtime_error(stage + ": value count changed");
    }
    for (std::size_t index = 0; index < baseline.size(); ++index) {
        const std::uint64_t expected_bits = bits(baseline[index]);
        const std::uint64_t observed_bits = bits(observed[index]);
        if (expected_bits != observed_bits) {
            std::cerr << "INPUT_MUTATION stage=" << stage
                      << " index=" << index
                      << " expected_bits=0x" << std::hex << std::setw(16)
                      << std::setfill('0') << expected_bits
                      << " observed_bits=0x" << std::setw(16) << observed_bits
                      << " xor=0x" << std::setw(16)
                      << (expected_bits ^ observed_bits) << std::dec << '\n';
            std::size_t repeated_mismatches = 0;
            std::uint64_t last_expected_bits = 0;
            std::uint64_t last_observed_bits = 0;
            for (std::size_t retry = 0; retry < 1024; ++retry) {
                last_expected_bits = bits(baseline[index]);
                last_observed_bits = bits(observed[index]);
                if (last_expected_bits != last_observed_bits) {
                    ++repeated_mismatches;
                }
            }
            std::cerr << "IMMEDIATE_RECHECK stage=" << stage
                      << " index=" << index
                      << " repeated_mismatches=" << repeated_mismatches
                      << " attempts=1024 last_expected_bits=0x"
                      << std::hex << std::setw(16) << std::setfill('0')
                      << last_expected_bits << " last_observed_bits=0x"
                      << std::setw(16) << last_observed_bits << std::dec << '\n';
            throw std::runtime_error(stage + ": element matrix storage changed");
        }
    }
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: assembly_input_integrity_check INPUT.inp\n";
        return 64;
    }
    try {
        csc3_demo::evidence::AssemblyCase assembly_case =
            csc3_demo::evidence::load_abaqus_case(std::filesystem::path(argv[1]));
        validate_initial_batch(assembly_case);
        const std::vector<double> baseline =
            assembly_case.element_matrices.values_row_major;
        require_unchanged(
            baseline, assembly_case.element_matrices.values_row_major,
            "after-baseline-copy");
        for (std::size_t scan = 0; scan < 32; ++scan) {
            require_unchanged(
                baseline, assembly_case.element_matrices.values_row_major,
                "preflight-scan-" + std::to_string(scan + 1));
            if ((scan + 1) % 8 == 0) {
                std::cout << "PREFLIGHT_SCAN_PASS count=" << (scan + 1) << '\n';
                std::cout.flush();
            }
        }

        constexpr std::array<int, 8> thread_cycle{{1, 13, 16, 7, 2, 15, 8, 4}};
        for (std::size_t round = 0; round < 32; ++round) {
            const int thread_count = thread_cycle[round % thread_cycle.size()];
            csc3_demo::SymmetricCscAssembler assembler;
            assembler.build_symbolic_parallel(
                assembly_case.element_dof_map, thread_count);
            require_unchanged(
                baseline, assembly_case.element_matrices.values_row_major,
                "round-" + std::to_string(round + 1) + "-after-symbolic-p" +
                    std::to_string(thread_count));
            assembler.assemble_numeric_atomic(
                assembly_case.element_matrices, thread_count);
            require_unchanged(
                baseline, assembly_case.element_matrices.values_row_major,
                "round-" + std::to_string(round + 1) + "-after-numeric-p" +
                    std::to_string(thread_count));
            std::cout << "ROUND_PASS round=" << (round + 1)
                      << " threads=" << thread_count
                      << " nnz=" << assembler.matrix().values.size() << '\n';
            std::cout.flush();
        }
        std::cout << "RESULT status=PASS rounds=32\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "RESULT status=FAIL error=" << error.what() << '\n';
        return 1;
    }
}
