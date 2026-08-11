// 这里读取 Abaqus .inp 中的节点和单一类型实体单元，并生成紧凑的零基网格。
// 目前只支持 C3D4/C3D8；Git LFS 指针、混合单元和坏记录都会直接报错。
#include "csc3_demo_tools/evidence.h"

#include <array>
#include <cerrno>
#include <charconv>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace csc3_demo::evidence {
namespace {

enum class Section {
    Ignore,
    Nodes,
    Elements,
};

struct RawElement {
    ElementId identifier = 0;
    std::size_t line_number = 0;
    std::array<std::uint64_t, 8> external_node_labels{};
    std::size_t node_count = 0;
};

[[noreturn]] void throw_line(std::size_t line_number, const std::string& message) {
    throw std::invalid_argument("line " + std::to_string(line_number) + ": " + message);
}

std::string_view trim(std::string_view value) {
    const std::size_t first = value.find_first_not_of(" \t\r\n");
    if (first == std::string_view::npos) {
        return {};
    }
    const std::size_t last = value.find_last_not_of(" \t\r\n");
    return value.substr(first, last - first + 1);
}

std::string lower_copy(std::string_view value) {
    std::string result;
    result.reserve(value.size());
    for (const char character : value) {
        if (character >= 'A' && character <= 'Z') {
            result.push_back(static_cast<char>(character - 'A' + 'a'));
        } else {
            result.push_back(character);
        }
    }
    return result;
}

std::vector<std::string_view> split_fields(std::string_view line) {
    std::vector<std::string_view> fields;
    std::size_t begin = 0;
    while (true) {
        const std::size_t delimiter = line.find(',', begin);
        if (delimiter == std::string_view::npos) {
            fields.push_back(trim(line.substr(begin)));
            return fields;
        }
        fields.push_back(trim(line.substr(begin, delimiter - begin)));
        begin = delimiter + 1;
    }
}

std::uint64_t parse_positive_identifier(std::string_view field, std::size_t line_number,
                                        const char* label) {
    if (field.empty()) {
        throw_line(line_number, std::string(label) + " is missing");
    }
    std::uint64_t value = 0;
    const char* const begin = field.data();
    const char* const end = begin + field.size();
    const auto parsed = std::from_chars(begin, end, value, 10);
    if (parsed.ec != std::errc{} || parsed.ptr != end || value == 0) {
        throw_line(line_number, std::string(label) + " is invalid");
    }
    return value;
}

ElementId parse_element_identifier(std::string_view field, std::size_t line_number) {
    const std::uint64_t value = parse_positive_identifier(field, line_number, "element identifier");
    if (value > static_cast<std::uint64_t>(std::numeric_limits<ElementId>::max())) {
        throw_line(line_number, "element identifier exceeds representable capacity");
    }
    return static_cast<ElementId>(value);
}

double parse_coordinate(std::string_view field, std::size_t line_number) {
    if (field.empty()) {
        throw_line(line_number, "coordinate is missing");
    }
    const std::string text(field);
    char* parsed_end = nullptr;
    errno = 0;
    const double value = std::strtod(text.c_str(), &parsed_end);
    if (parsed_end != text.c_str() + text.size() || parsed_end == text.c_str() || errno == ERANGE) {
        throw_line(line_number, "coordinate is malformed");
    }
    if (!std::isfinite(value)) {
        throw_line(line_number, "coordinate is nonfinite");
    }
    return value;
}

std::optional<std::string> header_attribute(const std::vector<std::string_view>& fields,
                                            const std::string& requested_name) {
    for (std::size_t index = 1; index < fields.size(); ++index) {
        const std::size_t equals = fields[index].find('=');
        if (equals == std::string_view::npos) {
            continue;
        }
        const std::string name = lower_copy(trim(fields[index].substr(0, equals)));
        if (name == requested_name) {
            return lower_copy(trim(fields[index].substr(equals + 1)));
        }
    }
    return std::nullopt;
}

ElementType parse_element_type(const std::vector<std::string_view>& fields,
                               std::size_t line_number) {
    const std::optional<std::string> type = header_attribute(fields, "type");
    if (!type || type->empty()) {
        throw_line(line_number, "unsupported element type: missing type attribute");
    }
    if (*type == "c3d4") {
        return ElementType::Tet4;
    }
    if (*type == "c3d8") {
        return ElementType::Hex8;
    }
    throw_line(line_number, "unsupported element type: " + *type);
}

std::size_t nodes_per_element(ElementType element_type) {
    switch (element_type) {
    case ElementType::Tet4:
        return 4;
    case ElementType::Hex8:
        return 8;
    }
    throw std::logic_error("invalid internal element type");
}

Offset size_to_offset(std::size_t value, std::size_t line_number) {
    if constexpr (std::numeric_limits<std::size_t>::digits > std::numeric_limits<Offset>::digits) {
        if (value > static_cast<std::size_t>(std::numeric_limits<Offset>::max())) {
            throw_line(line_number, "element offset exceeds representable capacity");
        }
    }
    return static_cast<Offset>(value);
}

} // namespace

ParsedMesh parse_abaqus_inp(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw std::runtime_error("could not open Abaqus input: " + path.string());
    }

    ParsedMesh result;
    result.name = path.filename().string();

    Section section = Section::Ignore;
    std::optional<ElementType> selected_element_type;
    std::unordered_map<std::uint64_t, std::size_t> node_index_by_label;
    std::unordered_set<ElementId> element_identifiers;
    std::vector<RawElement> raw_elements;
    std::string line;
    std::size_t line_number = 0;

    while (std::getline(input, line)) {
        ++line_number;
        const std::string_view text = trim(line);
        if (line_number == 1 && text == "version https://git-lfs.github.com/spec/v1") {
            throw_line(line_number, "Git LFS pointer is not a materialized input");
        }
        if (text.empty() || text.rfind("**", 0) == 0) {
            continue;
        }
        if (text.front() == '*') {
            const std::vector<std::string_view> fields = split_fields(text);
            const std::string keyword = lower_copy(fields.front());
            if (keyword == "*node") {
                section = Section::Nodes;
            } else if (keyword == "*element") {
                const ElementType header_type = parse_element_type(fields, line_number);
                if (selected_element_type && *selected_element_type != header_type) {
                    throw_line(line_number, "mixed element formulations are unsupported");
                }
                selected_element_type = header_type;
                section = Section::Elements;
            } else {
                section = Section::Ignore;
            }
            continue;
        }

        const std::vector<std::string_view> fields = split_fields(text);
        if (section == Section::Nodes) {
            if (fields.size() != 4) {
                throw_line(line_number, "node record must contain label,x,y,z");
            }
            const std::uint64_t external_label =
                parse_positive_identifier(fields[0], line_number, "node identifier");
            if (node_index_by_label.find(external_label) != node_index_by_label.end()) {
                throw_line(line_number, "duplicate node identifier");
            }
            const std::size_t compact_index = result.nodes.size();
            node_index_by_label.emplace(external_label, compact_index);
            result.nodes.push_back(Node{
                parse_coordinate(fields[1], line_number),
                parse_coordinate(fields[2], line_number),
                parse_coordinate(fields[3], line_number),
            });
        } else if (section == Section::Elements) {
            if (!selected_element_type) {
                throw_line(line_number, "element record has no active element type");
            }
            const std::size_t expected_nodes = nodes_per_element(*selected_element_type);
            if (fields.size() != expected_nodes + 1) {
                throw_line(line_number, "element record has the wrong field count");
            }
            RawElement element;
            element.identifier = parse_element_identifier(fields[0], line_number);
            element.line_number = line_number;
            if (!element_identifiers.emplace(element.identifier).second) {
                throw_line(line_number, "duplicate element identifier");
            }
            element.node_count = expected_nodes;
            for (std::size_t index = 1; index < fields.size(); ++index) {
                element.external_node_labels[index - 1] = parse_positive_identifier(
                    fields[index], line_number, "element node identifier");
            }
            raw_elements.push_back(std::move(element));
        }
    }
    if (!input.eof()) {
        throw std::runtime_error("failed while reading Abaqus input: " + path.string());
    }

    if (result.nodes.empty() || raw_elements.empty() || !selected_element_type) {
        throw_line(line_number == 0 ? 1 : line_number, "empty mesh");
    }
    result.element_type = *selected_element_type;
    result.external_element_ids.reserve(raw_elements.size());
    result.element_node_offsets.reserve(raw_elements.size() + 1);
    result.element_node_offsets.push_back(0);
    const std::size_t expected_nodes = nodes_per_element(result.element_type);
    if (raw_elements.size() > std::numeric_limits<std::size_t>::max() / expected_nodes) {
        throw_line(line_number, "element connectivity exceeds representable capacity");
    }
    result.compact_node_indices.reserve(raw_elements.size() * expected_nodes);
    for (const RawElement& element : raw_elements) {
        result.external_element_ids.push_back(element.identifier);
        for (std::size_t local_node = 0; local_node < element.node_count; ++local_node) {
            const std::uint64_t external_node_label = element.external_node_labels[local_node];
            const auto found = node_index_by_label.find(external_node_label);
            if (found == node_index_by_label.end()) {
                throw_line(element.line_number,
                           "unknown node identifier " + std::to_string(external_node_label));
            }
            result.compact_node_indices.push_back(found->second);
        }
        result.element_node_offsets.push_back(
            size_to_offset(result.compact_node_indices.size(), element.line_number));
    }
    return result;
}

} // namespace csc3_demo::evidence
