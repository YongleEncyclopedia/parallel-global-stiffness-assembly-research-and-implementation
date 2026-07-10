function solve_validation_export_matlab(result_dir, prefix)
%SOLVE_VALIDATION_EXPORT_MATLAB Solve one validation_export case in MATLAB.

if nargin ~= 2
    error('solve_validation_export_matlab requires result_dir and prefix.');
end
result_dir = normalize_text_scalar(result_dir, 'result_dir');
prefix = normalize_text_scalar(prefix, 'prefix');

matrix_path = fullfile(result_dir, [prefix '_K.mtx']);
force_path = fullfile(result_dir, [prefix '_force.csv']);
bc_path = fullfile(result_dir, [prefix '_bc.csv']);
probes_path = fullfile(result_dir, [prefix '_probes.csv']);
require_file(matrix_path);
require_file(force_path);
require_file(bc_path);
require_file(probes_path);

[K, stored_nnz] = read_matrix_market_symmetric(matrix_path);
[n_rows, n_cols] = size(K);
if n_rows ~= n_cols
    error('Stiffness matrix must be square; got %d-by-%d.', n_rows, n_cols);
end
n_dofs = n_rows;
if mod(n_dofs, 3) ~= 0
    error('Stiffness dimension %d is not divisible by three.', n_dofs);
end
n_nodes = n_dofs / 3;
symmetry_error = norm(K - K', 'fro');
symmetry_scale = max(1.0, norm(K, 'fro'));
if symmetry_error > 1.0e-12 * symmetry_scale
    error('Reconstructed stiffness matrix is not symmetric.');
end
if ~all(isfinite(nonzeros(K)))
    error('Stiffness matrix contains non-finite values.');
end

forces = readtable(force_path);
require_columns(forces, {'node', 'dof', 'force'}, force_path);
force_dofs = csv_dof_to_matlab(forces.node, forces.dof, n_nodes, 'force CSV');
validate_finite_vector(forces.force, 'force CSV force');
force_vector = accumarray(force_dofs, forces.force, [n_dofs, 1], @sum, 0);
if ~all(isfinite(force_vector))
    error('Aggregated force vector contains non-finite values.');
end

constraints = readtable(bc_path);
require_columns(constraints, {'node', 'dof', 'value'}, bc_path);
constrained_dofs = csv_dof_to_matlab( ...
    constraints.node, constraints.dof, n_nodes, 'boundary-condition CSV');
if numel(unique(constrained_dofs)) ~= numel(constrained_dofs)
    error('Boundary-condition CSV contains duplicate constrained node/DOF pairs.');
end
constrained_values = constraints.value;
validate_finite_vector(constrained_values, 'boundary-condition CSV value');

free_mask = true(n_dofs, 1);
free_mask(constrained_dofs) = false;
free_dofs = find(free_mask);
displacement = zeros(n_dofs, 1);
displacement(constrained_dofs) = constrained_values;
rhs_free = force_vector(free_dofs) - K(free_dofs, constrained_dofs) * constrained_values;
if ~isempty(free_dofs)
    displacement(free_dofs) = K(free_dofs, free_dofs) \ rhs_free;
end
if ~all(isfinite(displacement))
    error('MATLAB solve produced non-finite displacements.');
end

probes = readtable(probes_path);
require_columns(probes, {'name', 'node'}, probes_path);
validate_integer_vector(probes.node, 'probes CSV node');
if any(probes.node < 0 | probes.node >= n_nodes)
    error('Probes CSV contains a node outside the zero-based mesh range.');
end
probe_names = string(probes.name);
if any(ismissing(probe_names)) || any(strlength(strtrim(probe_names)) == 0)
    error('Probes CSV contains an empty probe name.');
end

components = reshape(displacement, 3, n_nodes)';
node = (0:n_nodes - 1)';
ux = components(:, 1);
uy = components(:, 2);
uz = components(:, 3);
umag = sqrt(ux.^2 + uy.^2 + uz.^2);
displacement_table = table( ...
    node, ux, uy, uz, umag, ...
    'VariableNames', {'node', 'ux', 'uy', 'uz', 'umag'});

probe_rows = probes.node + 1;
name = probe_names;
node = probes.node;
ux = components(probe_rows, 1);
uy = components(probe_rows, 2);
uz = components(probe_rows, 3);
umag = sqrt(ux.^2 + uy.^2 + uz.^2);
probe_table = table( ...
    name, node, ux, uy, uz, umag, ...
    'VariableNames', {'name', 'node', 'ux', 'uy', 'uz', 'umag'});

displacement_output = fullfile(result_dir, [prefix '_matlab_displacements.csv']);
probe_output = fullfile(result_dir, [prefix '_matlab_probe_summary.csv']);
metadata_output = fullfile(result_dir, [prefix '_matlab_solve_metadata.json']);
writetable(displacement_table, displacement_output);
writetable(probe_table, probe_output);

equilibrium_residual = K * displacement - force_vector;
absolute_free_l2 = norm(equilibrium_residual(free_dofs), 2);
rhs_free_l2 = norm(rhs_free, 2);
relative_free_l2 = absolute_free_l2 / max(rhs_free_l2, eps('double'));

metadata = struct();
metadata.schema_version = 'matlab-validation-solve-v1';
metadata.status = 'PASS';
metadata.solver = 'MATLAB backslash';
metadata.prefix = prefix;
metadata.indexing = struct('csv', 'zero-based', 'matrix_market', 'one-based');
metadata.matrix.rows = n_rows;
metadata.matrix.cols = n_cols;
metadata.matrix.stored_lower_triangle_entries = stored_nnz;
metadata.matrix.reconstructed_nnz = nnz(K);
metadata.matrix.symmetry_error_fro = symmetry_error;
metadata.system.node_count = n_nodes;
metadata.system.dof_count = n_dofs;
metadata.system.free_dof_count = numel(free_dofs);
metadata.system.constrained_dof_count = numel(constrained_dofs);
metadata.residual.absolute_free_l2 = absolute_free_l2;
metadata.residual.relative_free_l2 = relative_free_l2;
metadata.residual.effective_rhs_l2 = rhs_free_l2;
metadata.files.displacements = displacement_output;
metadata.files.probes = probe_output;
metadata.files.metadata = metadata_output;
write_json(metadata_output, metadata);
end


function value = normalize_text_scalar(value, label)
if ~(ischar(value) || (isstring(value) && isscalar(value)))
    error('%s must be a character vector or scalar string.', label);
end
value = char(value);
if isempty(strtrim(value))
    error('%s must not be empty.', label);
end
end


function require_file(path)
if ~isfile(path)
    error('Required validation export file does not exist: %s', path);
end
end


function require_columns(data, required, path)
missing = setdiff(required, data.Properties.VariableNames, 'stable');
if ~isempty(missing)
    error('CSV %s is missing required columns: %s', path, strjoin(missing, ', '));
end
end


function validate_integer_vector(values, label)
if ~isnumeric(values) || ~isreal(values) || ...
        any(~isfinite(values)) || any(values ~= fix(values))
    error('%s must contain finite integers.', label);
end
end


function validate_finite_vector(values, label)
if ~isnumeric(values) || ~isreal(values) || any(~isfinite(values))
    error('%s must contain finite numeric values.', label);
end
end


function matlab_dofs = csv_dof_to_matlab(nodes, dofs, n_nodes, label)
validate_integer_vector(nodes, [label ' node']);
validate_integer_vector(dofs, [label ' dof']);
if any(nodes < 0 | nodes >= n_nodes)
    error('%s contains a node outside the zero-based mesh range.', label);
end
if any(dofs < 0 | dofs > 2)
    error('%s contains a DOF outside the zero-based range 0..2.', label);
end
matlab_dofs = 3 * nodes + dofs + 1;
end


function [K, stored_nnz] = read_matrix_market_symmetric(path)
fid = fopen(path, 'rt');
if fid < 0
    error('Cannot open Matrix Market file: %s', path);
end
cleanup = onCleanup(@() fclose(fid)); %#ok<NASGU>

header = fgetl(fid);
expected_header = '%%MatrixMarket matrix coordinate real symmetric';
if ~ischar(header) || ~strcmp(strtrim(header), expected_header)
    error('Matrix Market header must be exactly: %s', expected_header);
end

dimension_line = next_data_line(fid);
dimensions = parse_numeric_triplet(dimension_line, 'Matrix Market dimensions');
if ~isreal(dimensions) || any(~isfinite(dimensions)) || any(dimensions ~= fix(dimensions))
    error('Matrix Market dimensions must be finite integers.');
end
n_rows = dimensions(1);
n_cols = dimensions(2);
stored_nnz = dimensions(3);
if n_rows <= 0 || n_cols <= 0 || stored_nnz < 0
    error('Matrix Market dimensions and entry count are invalid.');
end

rows = zeros(stored_nnz, 1);
cols = zeros(stored_nnz, 1);
values = zeros(stored_nnz, 1);
entry_count = 0;
while true
    line = fgetl(fid);
    if ~ischar(line)
        break;
    end
    trimmed = strtrim(line);
    if isempty(trimmed) || startsWith(trimmed, '%')
        continue;
    end
    entry_count = entry_count + 1;
    if entry_count > stored_nnz
        error('Matrix Market file has more entries than declared.');
    end
    entry = parse_numeric_triplet(trimmed, 'Matrix Market entry');
    rows(entry_count) = entry(1);
    cols(entry_count) = entry(2);
    values(entry_count) = entry(3);
end
if entry_count ~= stored_nnz
    error('Matrix Market file declared %d entries but contains %d.', stored_nnz, entry_count);
end
if ~isreal(values) || ~all(isfinite(values))
    error('Matrix Market values must be finite.');
end
if any(rows ~= fix(rows)) || any(cols ~= fix(cols))
    error('Matrix Market row and column indices must be integers.');
end
if any(rows < 1) || any(cols < 1) || any(rows > n_rows) || any(cols > n_cols)
    error('Matrix Market row or column index is out of range.');
end
if any(rows < cols)
    error('Symmetric Matrix Market input must contain the lower triangle only.');
end

off_diagonal = rows ~= cols;
K = sparse([rows; cols(off_diagonal)], ...
    [cols; rows(off_diagonal)], ...
    [values; values(off_diagonal)], n_rows, n_cols);
if ~all(isfinite(nonzeros(K)))
    error('Reconstructed Matrix Market matrix contains non-finite values.');
end
end


function line = next_data_line(fid)
while true
    line = fgetl(fid);
    if ~ischar(line)
        error('Matrix Market file ended before its dimension line.');
    end
    trimmed = strtrim(line);
    if ~isempty(trimmed) && ~startsWith(trimmed, '%')
        line = trimmed;
        return;
    end
end
end


function values = parse_numeric_triplet(line, label)
tokens = strsplit(strtrim(line));
if numel(tokens) ~= 3
    error('%s must contain exactly three fields.', label);
end
values = str2double(tokens)';
if numel(values) ~= 3 || any(isnan(values))
    error('%s contains a malformed numeric field.', label);
end
end


function write_json(path, payload)
fid = fopen(path, 'wt');
if fid < 0
    error('Cannot write MATLAB solve metadata: %s', path);
end
cleanup = onCleanup(@() fclose(fid)); %#ok<NASGU>
fprintf(fid, '%s\n', jsonencode(payload));
end
