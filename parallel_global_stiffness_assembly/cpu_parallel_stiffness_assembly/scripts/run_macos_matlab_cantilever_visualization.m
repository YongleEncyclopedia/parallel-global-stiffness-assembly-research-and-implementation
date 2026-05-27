function run_macos_matlab_cantilever_visualization(validation_export_exe, output_root)
% Generate MATLAB figures for cantilever mesh topology and stiffness sparsity.
%
% Usage:
% matlab -batch "run_macos_matlab_cantilever_visualization('/path/to/validation_export')"

if nargin < 1 || strlength(string(validation_export_exe)) == 0
    validation_export_exe = default_validation_export_exe();
end
if nargin < 2 || strlength(string(output_root)) == 0
    output_root = fullfile(project_root(), 'results', '2026-05-27-macos-matlab-cantilever-topology-sparsity');
end

validation_export_exe = char(validation_export_exe);
output_root = char(output_root);
assert(isfile(validation_export_exe), 'validation_export executable not found: %s', validation_export_exe);
assert(~isempty(ver('pde')), 'Partial Differential Equation Toolbox is required for the irregular Tet4 mesh.');

if ~exist(output_root, 'dir')
    mkdir(output_root);
end

matlab_info = matlab_runtime_info();
cases = configure_cases(output_root);
tet_inp = fullfile(output_root, 'mesh_inputs', 'cantilever_tet4_unstructured_medium.inp');
if ~exist(fileparts(tet_inp), 'dir')
    mkdir(fileparts(tet_inp));
end
write_irregular_tet4_inp(tet_inp, 1.0, 0.2, 0.1, 0.05);

run_validation_export(validation_export_exe, cases(1), '');
run_validation_export(validation_export_exe, cases(2), tet_inp);

for i = 1:numel(cases)
    cases(i) = enrich_case(cases(i));
    plot_mesh_topology(cases(i), fullfile(cases(i).out_dir, cases(i).name + "_mesh_topology_matlab"));
    plot_stiffness_sparsity(cases(i), fullfile(cases(i).out_dir, cases(i).name + "_stiffness_sparsity_matlab"));
end

plot_contact_sheet(cases, fullfile(output_root, 'cantilever_topology_sparsity_contact_sheet_matlab'));
write_manifest(output_root, validation_export_exe, matlab_info, cases);
write_readme(output_root, validation_export_exe, matlab_info, cases);
fprintf('MATLAB cantilever visualization complete: %s\n', output_root);
end

function root = project_root()
script_dir = fileparts(mfilename('fullpath'));
root = fileparts(script_dir);
end

function exe = default_validation_export_exe()
root = project_root();
candidates = [
    fullfile(root, 'build', 'bin', 'validation_export')
    fullfile(root, 'cmake-build-release', 'bin', 'validation_export')
    fullfile(root, 'cmake-build-debug', 'bin', 'validation_export')
];
exe = '';
for i = 1:numel(candidates)
    if isfile(candidates(i))
        exe = char(candidates(i));
        return;
    end
end
end

function info = matlab_runtime_info()
v = ver;
names = string({v.Name});
info = struct();
info.version = char(string(version));
info.pde_toolbox = any(names == "Partial Differential Equation Toolbox");
info.generated_at = char(datetime('now', 'TimeZone', 'local', 'Format', 'yyyy-MM-dd''T''HH:mm:ssXXX'));
end

function cases = configure_cases(output_root)
cases(1) = struct( ...
    'name', "cantilever_hex8_medium", ...
    'label', "Structured Hex8 / C3D8 topology", ...
    'element_family', "hex8", ...
    'stiffness_model', "legacy_synthetic", ...
    'mesh_source', "validation_export generated structured Hex8 grid, nx=12, ny=4, nz=4", ...
    'out_dir', string(fullfile(output_root, 'cantilever_hex8_medium')), ...
    'extra_args', "--case cantilever_hex8_medium --allow-legacy-synthetic");
cases(2) = struct( ...
    'name', "cantilever_tet4_unstructured_medium", ...
    'label', "Irregular Tet4 / C3D4 topology", ...
    'element_family', "tet4", ...
    'stiffness_model', "linear_elastic_solid", ...
    'mesh_source', "MATLAB PDE Toolbox linear Tet4 mesh, Hmax=0.05", ...
    'out_dir', string(fullfile(output_root, 'cantilever_tet4_unstructured_medium')), ...
    'extra_args', "--mesh inp --case-name cantilever_tet4_unstructured_medium");
for i = 1:numel(cases)
    cases(i).nodes_path = "";
    cases(i).elements_path = "";
    cases(i).metadata_path = "";
    cases(i).k_path = "";
    cases(i).nodes = table();
    cases(i).elements = table();
    cases(i).metadata = struct();
    cases(i).K = sparse([]);
    cases(i).K_pattern = sparse([]);
end
end

function run_validation_export(exe, c, inp_path)
if ~exist(c.out_dir, 'dir')
    mkdir(c.out_dir);
end
cmd = sprintf('"%s" %s --stiffness-model %s --E 1 --nu 0.3 --total-load -1 --load-dof 2 --out-dir "%s" --prefix %s', ...
    exe, c.extra_args, c.stiffness_model, c.out_dir, c.name);
if strlength(string(inp_path)) > 0
    cmd = sprintf('%s --inp "%s"', cmd, inp_path);
end
status = system(cmd);
assert(status == 0, 'validation_export failed for %s', c.name);
end

function c = enrich_case(c)
base = fullfile(c.out_dir, c.name);
c.nodes_path = string(base + "_nodes.csv");
c.elements_path = string(base + "_elements.csv");
c.metadata_path = string(base + "_metadata.json");
c.k_path = string(base + "_K.mtx");
c.nodes = readtable(c.nodes_path);
c.elements = readtable(c.elements_path);
c.metadata = jsondecode(fileread(c.metadata_path));
[c.K, c.K_pattern] = read_matrix_market_symmetric(c.k_path);
validate_case(c);
end

function validate_case(c)
assert(size(c.K, 1) == c.metadata.mesh.dofs, 'K rows mismatch for %s', c.name);
assert(size(c.K, 2) == c.metadata.mesh.dofs, 'K cols mismatch for %s', c.name);
assert(c.metadata.mesh.dofs == 3 * height(c.nodes), 'DOF count mismatch for %s', c.name);
assert(nnz(c.K_pattern) == c.metadata.matrix.nnz, 'K structural nnz mismatch for %s', c.name);
sym_diff = norm(c.K - c.K', 'fro');
assert(sym_diff <= 1.0e-9 * max(1.0, norm(c.K, 'fro')), 'K symmetry mismatch for %s', c.name);
end

function write_irregular_tet4_inp(path, L, W, T, hmax)
model = createpde;
model.Geometry = multicuboid(L, W, T);
msh = generateMesh(model, 'GeometricOrder', 'linear', 'Hmax', hmax);
nodes = msh.Nodes;
nodes(1, :) = nodes(1, :) + L / 2;
nodes(2, :) = nodes(2, :) + W / 2;
elements = msh.Elements(1:4, :);
for e = 1:size(elements, 2)
    conn = elements(:, e);
    p = nodes(:, conn)';
    jac = [p(2,:) - p(1,:); p(3,:) - p(1,:); p(4,:) - p(1,:)];
    if det(jac) < 0
        elements([3 4], e) = elements([4 3], e);
    end
end

fid = fopen(path, 'w');
assert(fid > 0, 'Cannot write Tet4 inp: %s', path);
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, '*Heading\n');
fprintf(fid, '** MATLAB PDE Toolbox irregular C3D4 cantilever mesh.\n');
fprintf(fid, '** Dimensions: L=1, W=0.2, T=0.1. Hmax=0.05.\n');
fprintf(fid, '*Node\n');
for i = 1:size(nodes, 2)
    fprintf(fid, '%d, %.17g, %.17g, %.17g\n', i, nodes(1,i), nodes(2,i), nodes(3,i));
end
fprintf(fid, '*Element, type=C3D4\n');
for e = 1:size(elements, 2)
    fprintf(fid, '%d, %d, %d, %d, %d\n', e, elements(1,e), elements(2,e), elements(3,e), elements(4,e));
end
fprintf(fid, '*End Part\n');
end

function [K, K_pattern] = read_matrix_market_symmetric(path)
fid = fopen(path, 'r');
assert(fid > 0, 'Cannot read MatrixMarket file: %s', path);
cleanup = onCleanup(@() fclose(fid));
line = fgetl(fid);
assert(ischar(line) && contains(line, 'coordinate real symmetric'), 'Unsupported MatrixMarket header: %s', path);
line = fgetl(fid);
while ischar(line) && startsWith(strtrim(line), '%')
    line = fgetl(fid);
end
dims = sscanf(line, '%d %d %d');
data = textscan(fid, '%d %d %f');
i = data{1};
j = data{2};
v = data{3};
offdiag = i ~= j;
K = sparse([i; j(offdiag)], [j; i(offdiag)], [v; v(offdiag)], dims(1), dims(2));
K_pattern = sparse([i; j(offdiag)], [j; i(offdiag)], true, dims(1), dims(2));
end

function plot_mesh_topology(c, out_base)
fig = figure('Visible', 'off', 'Color', 'w', 'Position', [100 100 1100 650]);
ax = axes(fig);
draw_mesh(ax, c);
title(ax, figure_title(c, 'mesh topology'), 'Interpreter', 'none', 'FontWeight', 'bold', 'FontSize', 10);
save_figure(fig, out_base, true);
close(fig);
end

function plot_stiffness_sparsity(c, out_base)
fig = figure('Visible', 'off', 'Color', 'w', 'Position', [100 100 850 760]);
ax = axes(fig);
draw_sparsity(ax, c);
title(ax, figure_title(c, 'global stiffness sparsity'), 'Interpreter', 'none', 'FontWeight', 'bold', 'FontSize', 10);
save_figure(fig, out_base, true);
close(fig);
end

function plot_contact_sheet(cases, out_base)
fig = figure('Visible', 'off', 'Color', 'w', 'Position', [100 100 1500 1100]);
t = tiledlayout(fig, 2, 2, 'Padding', 'loose', 'TileSpacing', 'compact');
for i = 1:numel(cases)
    ax = nexttile(t, i);
    draw_mesh(ax, cases(i));
    title(ax, figure_title(cases(i), 'mesh topology'), 'Interpreter', 'none', 'FontWeight', 'bold', 'FontSize', 9);
end
for i = 1:numel(cases)
    ax = nexttile(t, i + numel(cases));
    draw_sparsity(ax, cases(i));
    title(ax, figure_title(cases(i), 'global stiffness sparsity'), 'Interpreter', 'none', 'FontWeight', 'bold', 'FontSize', 9);
end
save_figure(fig, out_base, false);
exportgraphics(fig, out_base + ".pdf", 'ContentType', 'vector');
close(fig);
end

function draw_mesh(ax, c)
V = [c.nodes.x, c.nodes.y, c.nodes.z];
faces = boundary_faces(c.elements);
if c.element_family == "hex8"
    face_color = [0.80, 0.88, 0.97];
    edge_color = [0.08, 0.22, 0.38];
else
    face_color = [0.86, 0.90, 0.82];
    edge_color = [0.22, 0.30, 0.16];
end
patch(ax, 'Faces', faces, 'Vertices', V, 'FaceColor', face_color, 'FaceAlpha', 0.78, ...
    'EdgeColor', edge_color, 'LineWidth', 0.35);
axis(ax, 'equal');
grid(ax, 'on');
box(ax, 'on');
xlabel(ax, 'x');
ylabel(ax, 'y');
zlabel(ax, 'z');
xlim(ax, [0 1]);
ylim(ax, [0 0.2]);
zlim(ax, [0 0.1]);
view(ax, 38, 20);
camlight(ax, 'headlight');
lighting(ax, 'gouraud');
end

function draw_sparsity(ax, c)
axes(ax);
spy(c.K_pattern);
h = findobj(ax, 'Type', 'Line');
set(h, 'Marker', '.', 'MarkerSize', 3, 'Color', [0.08, 0.18, 0.32]);
axis(ax, 'square');
set(ax, 'YDir', 'reverse');
xlabel(ax, 'column');
ylabel(ax, 'row');
grid(ax, 'on');
end

function faces = boundary_faces(elements)
if all(string(elements.element_type) == "hex8")
    template = [1 2 3 4; 5 6 7 8; 1 2 6 5; 2 3 7 6; 3 4 8 7; 4 1 5 8];
    faces = zeros(height(elements) * 6, 4);
    row = 1;
    for e = 1:height(elements)
        nodes = table2array(elements(e, {'n0','n1','n2','n3','n4','n5','n6','n7'})) + 1;
        for f = 1:6
            faces(row, :) = nodes(template(f, :));
            row = row + 1;
        end
    end
    keys = sort(faces, 2);
    [~, ~, group] = unique(keys, 'rows');
    counts = accumarray(group, 1);
    faces = faces(counts(group) == 1, :);
else
    template = [1 2 3; 1 2 4; 1 3 4; 2 3 4];
    faces = zeros(height(elements) * 4, 3);
    row = 1;
    for e = 1:height(elements)
        nodes = table2array(elements(e, {'n0','n1','n2','n3'})) + 1;
        for f = 1:4
            faces(row, :) = nodes(template(f, :));
            row = row + 1;
        end
    end
    keys = sort(faces, 2);
    [~, ~, group] = unique(keys, 'rows');
    counts = accumarray(group, 1);
    faces = faces(counts(group) == 1, :);
end
end

function title_text = figure_title(c, suffix)
title_text = sprintf('%s | %s\nnodes=%d, elements=%d, DOFs=%d, nnz(K)=%d', ...
    c.name, suffix, c.metadata.mesh.nodes, c.metadata.mesh.elements, ...
    c.metadata.mesh.dofs, c.metadata.matrix.nnz);
end

function save_figure(fig, out_base, save_fig_file)
exportgraphics(fig, out_base + ".svg", 'ContentType', 'vector');
exportgraphics(fig, out_base + ".png", 'Resolution', 300);
if save_fig_file
    savefig(fig, out_base + ".fig");
end
end

function write_manifest(output_root, exe, matlab_info, cases)
manifest = struct();
manifest.generated_at = matlab_info.generated_at;
manifest.matlab_version = matlab_info.version;
manifest.pde_toolbox_available = matlab_info.pde_toolbox;
manifest.validation_export = exe;
manifest.note = 'Topology and sparsity visualization only; this artifact does not claim displacement-solve correctness.';
for i = 1:numel(cases)
    manifest.cases(i).name = char(cases(i).name);
    manifest.cases(i).label = char(cases(i).label);
    manifest.cases(i).element_family = char(cases(i).element_family);
    manifest.cases(i).stiffness_model = char(cases(i).metadata.stiffness_model);
    manifest.cases(i).mesh_source = char(cases(i).mesh_source);
    manifest.cases(i).nodes = cases(i).metadata.mesh.nodes;
    manifest.cases(i).elements = cases(i).metadata.mesh.elements;
    manifest.cases(i).dofs = cases(i).metadata.mesh.dofs;
    manifest.cases(i).nnz = cases(i).metadata.matrix.nnz;
    manifest.cases(i).files.K = char(cases(i).k_path);
    manifest.cases(i).files.nodes = char(cases(i).nodes_path);
    manifest.cases(i).files.elements = char(cases(i).elements_path);
end
fid = fopen(fullfile(output_root, 'manifest.json'), 'w');
assert(fid > 0, 'Cannot write manifest.json');
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, '%s\n', jsonencode(manifest, 'PrettyPrint', true));
end

function write_readme(output_root, exe, matlab_info, cases)
fid = fopen(fullfile(output_root, 'README.md'), 'w');
assert(fid > 0, 'Cannot write README.md');
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, '# macOS + MATLAB cantilever topology and sparsity figures\n\n');
fprintf(fid, '- MATLAB: `%s`\n', matlab_info.version);
fprintf(fid, '- PDE Toolbox available: `%s`\n', string(matlab_info.pde_toolbox));
fprintf(fid, '- validation_export: `%s`\n\n', exe);
fprintf(fid, 'These figures visualize mesh topology and global stiffness sparsity only; they do not claim displacement-solve correctness.\n\n');
fprintf(fid, '| case | mesh source | stiffness model provenance | nodes | elements | DOFs | nnz(K) |\n');
fprintf(fid, '|---|---|---:|---:|---:|---:|---:|\n');
for i = 1:numel(cases)
    fprintf(fid, '| `%s` | %s | `%s` | %d | %d | %d | %d |\n', ...
        cases(i).name, cases(i).mesh_source, cases(i).metadata.stiffness_model, ...
        cases(i).metadata.mesh.nodes, cases(i).metadata.mesh.elements, ...
        cases(i).metadata.mesh.dofs, cases(i).metadata.matrix.nnz);
end
fprintf(fid, '\nTet4 case uses MATLAB PDE Toolbox `generateMesh(..., ''GeometricOrder'', ''linear'', ''Hmax'', 0.05)` on the same `L=1, W=0.2, T=0.1` cantilever block.\n');
end
