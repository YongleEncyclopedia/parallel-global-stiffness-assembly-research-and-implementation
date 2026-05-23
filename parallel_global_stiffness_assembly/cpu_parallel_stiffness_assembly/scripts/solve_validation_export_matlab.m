function solve_validation_export_matlab(out_dir, prefix)
%SOLVE_VALIDATION_EXPORT_MATLAB Solve a validation_export stiffness system.
% Usage from MATLAB:
%   solve_validation_export_matlab("validation-export", "hex8_small")

if nargin < 1 || isempty(out_dir)
    out_dir = pwd;
end
if nargin < 2 || isempty(prefix)
    prefix = 'validation';
end

K = read_matrix_market_symmetric(fullfile(out_dir, [prefix '_K.mtx']));
n = size(K, 1);
if mod(n, 3) ~= 0
    error('Matrix dimension must be divisible by 3 DOFs per node.');
end
num_nodes = n / 3;

force_table = read_numeric_csv(fullfile(out_dir, [prefix '_force.csv']), 3);
bc_table = read_numeric_csv(fullfile(out_dir, [prefix '_bc.csv']), 3);
probe_table = read_probe_csv(fullfile(out_dir, [prefix '_probes.csv']));

F = zeros(n, 1);
for i = 1:size(force_table, 1)
    idx = dof_index(force_table(i, 1), force_table(i, 2));
    F(idx) = F(idx) + force_table(i, 3);
end

U = zeros(n, 1);
fixed = false(n, 1);
for i = 1:size(bc_table, 1)
    idx = dof_index(bc_table(i, 1), bc_table(i, 2));
    fixed(idx) = true;
    U(idx) = bc_table(i, 3);
end

free = find(~fixed);
fixed_idx = find(fixed);
rhs = F(free) - K(free, fixed_idx) * U(fixed_idx);
U(free) = K(free, free) \ rhs;

nodes = (0:num_nodes - 1).';
ux = U(1:3:end);
uy = U(2:3:end);
uz = U(3:3:end);
umag = sqrt(ux.^2 + uy.^2 + uz.^2);
write_displacements(fullfile(out_dir, [prefix '_matlab_displacements.csv']), nodes, ux, uy, uz, umag);

probe_nodes = probe_table.nodes;
probe_ux = ux(probe_nodes + 1);
probe_uy = uy(probe_nodes + 1);
probe_uz = uz(probe_nodes + 1);
probe_umag = umag(probe_nodes + 1);
write_probe_summary(fullfile(out_dir, [prefix '_matlab_probe_summary.csv']), ...
    probe_table.names, probe_nodes, probe_ux, probe_uy, probe_uz, probe_umag);

fprintf('Solved %s: nodes=%d, fixed_dofs=%d, free_dofs=%d\n', prefix, num_nodes, nnz(fixed), numel(free));

    function idx = dof_index(node, dof)
        idx = double(node) * 3 + double(dof) + 1;
        if idx < 1 || idx > n
            error('DOF index out of range: node=%g dof=%g', node, dof);
        end
    end
end

function K = read_matrix_market_symmetric(path)
fid = fopen(path, 'r');
if fid < 0
    error('Cannot open MatrixMarket file: %s', path);
end
cleanup = onCleanup(@() fclose(fid));

header = fgetl(fid);
if ~ischar(header) || isempty(strfind(header, 'MatrixMarket')) || isempty(strfind(lower(header), 'symmetric'))
    error('Expected MatrixMarket symmetric coordinate file: %s', path);
end

line = fgetl(fid);
while ischar(line) && starts_with(strtrim(line), '%')
    line = fgetl(fid);
end
if ~ischar(line)
    error('MatrixMarket size line is missing: %s', path);
end
dims = sscanf(line, '%d %d %d');
if numel(dims) ~= 3
    error('Invalid MatrixMarket size line: %s', line);
end

data = textscan(fid, '%d %d %f');
rows = double(data{1});
cols = double(data{2});
vals = double(data{3});
K = sparse(rows, cols, vals, dims(1), dims(2));
offdiag = rows ~= cols;
K = K + sparse(cols(offdiag), rows(offdiag), vals(offdiag), dims(1), dims(2));
end

function tf = starts_with(text, prefix)
tf = length(text) >= length(prefix) && strcmp(text(1:length(prefix)), prefix);
end

function data = read_numeric_csv(path, expected_cols)
fid = fopen(path, 'r');
if fid < 0
    error('Cannot open CSV file: %s', path);
end
cleanup = onCleanup(@() fclose(fid));
fgetl(fid);
format = repmat('%f', 1, expected_cols);
cells = textscan(fid, format, 'Delimiter', ',');
data = zeros(numel(cells{1}), expected_cols);
for col = 1:expected_cols
    data(:, col) = cells{col};
end
end

function probes = read_probe_csv(path)
fid = fopen(path, 'r');
if fid < 0
    error('Cannot open probes CSV file: %s', path);
end
cleanup = onCleanup(@() fclose(fid));
fgetl(fid);
cells = textscan(fid, '%s%f%f%f%f%f%f%f', 'Delimiter', ',');
probes.names = cells{1};
probes.nodes = cells{2};
end

function write_displacements(path, nodes, ux, uy, uz, umag)
fid = fopen(path, 'w');
if fid < 0
    error('Cannot write displacement CSV file: %s', path);
end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, 'node,ux,uy,uz,umag\n');
for i = 1:numel(nodes)
    fprintf(fid, '%d,%.17g,%.17g,%.17g,%.17g\n', nodes(i), ux(i), uy(i), uz(i), umag(i));
end
end

function write_probe_summary(path, names, nodes, ux, uy, uz, umag)
fid = fopen(path, 'w');
if fid < 0
    error('Cannot write probe summary CSV file: %s', path);
end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, 'name,node,ux,uy,uz,umag\n');
for i = 1:numel(nodes)
    fprintf(fid, '%s,%d,%.17g,%.17g,%.17g,%.17g\n', names{i}, nodes(i), ux(i), uy(i), uz(i), umag(i));
end
end
