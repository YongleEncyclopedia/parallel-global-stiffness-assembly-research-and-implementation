function run_comsol_validation(result_root, port)
%RUN_COMSOL_VALIDATION Build COMSOL reference solves for PGSA validation cases.
%
% This script is intentionally stored with the result package. It is a
% traceable one-run workflow for the 2026-05-23 macOS + COMSOL validation
% package, not a new repository-level validation API.

if nargin < 1 || strlength(string(result_root)) == 0
    result_root = "results/validation-export/2026-05-23-macos-comsol";
end
if nargin < 2
    port = 20361;
end

addpath('/Applications/COMSOL62/Multiphysics/mli');
mphstart(port);

import com.comsol.model.*
import com.comsol.model.util.*

cases = { ...
    'cantilever_hex8_small', ...
    'cantilever_hex8_medium', ...
    'cantilever_tet4_small', ...
    'cantilever_tet4_medium' ...
};

root = char(result_root);
status_rows = {};

for c = 1:numel(cases)
    case_name = cases{c};
    case_dir = fullfile(root, case_name);
    prefix = case_name;
    metadata_path = fullfile(case_dir, [prefix '_metadata.json']);
    probes_path = fullfile(case_dir, [prefix '_probes.csv']);
    out_csv = fullfile(case_dir, [prefix '_comsol_displacements.csv']);
    out_mph = fullfile(case_dir, [prefix '_comsol_reference.mph']);

    metadata = jsondecode(fileread(metadata_path));
    probes = readtable(probes_path, 'FileType', 'text');
    dims = case_grid_dims(case_name);
    L = metadata.mesh.bounds.xmax - metadata.mesh.bounds.xmin;
    W = metadata.mesh.bounds.ymax - metadata.mesh.bounds.ymin;
    T = metadata.mesh.bounds.zmax - metadata.mesh.bounds.zmin;
    E = metadata.material.E;
    nu = metadata.material.nu;
    total_load = metadata.load.total_load;
    load_dof = metadata.load.load_dof;
    if load_dof ~= 2
        error('This COMSOL workflow currently expects load_dof=2, got %d', load_dof);
    end

    model_tag = ['pgsa_' regexprep(case_name, '[^A-Za-z0-9_]', '_')];
    if any(strcmp(cell(ModelUtil.tags), model_tag))
        ModelUtil.remove(model_tag);
    end
    model = ModelUtil.create(model_tag);
    model.modelPath(case_dir);
    model.component.create('comp1');
    model.component('comp1').geom.create('geom1', 3);
    mesh = model.component('comp1').mesh.create('mesh1', 'geom1');

    [vertices, elems, elem_type] = structured_mesh(dims.nx, dims.ny, dims.nz, L, W, T, metadata.element_type);
    mesh.data.setVertex(vertices);
    mesh.data.setElem(elem_type, elems);
    mesh.data.createMesh;

    eps_box = max([L W T 1.0]) * 1e-8;
    fixed_box = [-eps_box eps_box; -eps_box W + eps_box; -eps_box T + eps_box];
    loaded_box = [L - eps_box L + eps_box; -eps_box W + eps_box; -eps_box T + eps_box];
    fixed_boundaries = mphselectbox(model, 'geom1', fixed_box, 'boundary');
    loaded_boundaries = mphselectbox(model, 'geom1', loaded_box, 'boundary');
    if isempty(fixed_boundaries)
        error('No COMSOL fixed x=0 boundaries selected for %s', case_name);
    end
    if isempty(loaded_boundaries)
        error('No COMSOL loaded x=L boundaries selected for %s', case_name);
    end

    model.component('comp1').material.create('mat1', 'Common');
    model.component('comp1').material('mat1').propertyGroup.create('Enu', 'Young''s_modulus_and_Poisson''s_ratio');
    model.component('comp1').material('mat1').propertyGroup('Enu').set('E', {num2str(E, 17)});
    model.component('comp1').material('mat1').propertyGroup('Enu').set('nu', {num2str(nu, 17)});

    model.component('comp1').physics.create('solid', 'SolidMechanics', 'geom1');
    model.component('comp1').physics('solid').prop('ShapeProperty').set('order_displacement', '1');
    model.component('comp1').physics('solid').create('fix1', 'Fixed', 2);
    model.component('comp1').physics('solid').feature('fix1').selection.set(fixed_boundaries);
    model.component('comp1').physics('solid').create('bndl1', 'BoundaryLoad', 2);
    model.component('comp1').physics('solid').feature('bndl1').selection.set(loaded_boundaries);
    model.component('comp1').physics('solid').feature('bndl1').set('LoadType', 'ForceArea');
    traction_z = total_load / (W * T);
    model.component('comp1').physics('solid').feature('bndl1').set('FperArea', {'0' '0' num2str(traction_z, 17)});

    model.study.create('std1');
    model.study('std1').create('stat', 'Stationary');
    model.study('std1').feature('stat').setSolveFor('/physics/solid', true);
    model.study('std1').run;

    coords = [probes.x.'; probes.y.'; probes.z.'];
    [ux, uy, uz] = mphinterp(model, {'u', 'v', 'w'}, 'coord', coords);
    write_comsol_displacements(out_csv, case_name, probes, ux, uy, uz, elem_type, traction_z, total_load);
    mphsave(model, out_mph);

    status_rows(end + 1, :) = {case_name, 'solved', elem_type, num2str(numel(fixed_boundaries)), ...
        num2str(numel(loaded_boundaries)), out_csv, out_mph}; %#ok<AGROW>
    ModelUtil.remove(model_tag);
end

write_status(fullfile(root, 'comsol_reference_status.csv'), status_rows);
end

function dims = case_grid_dims(case_name)
if contains(case_name, 'small')
    dims = struct('nx', 2, 'ny', 2, 'nz', 2);
elseif contains(case_name, 'medium')
    dims = struct('nx', 12, 'ny', 4, 'nz', 4);
else
    error('Unknown case grid dimensions for %s', case_name);
end
end

function [vertices, elems, elem_type] = structured_mesh(nx, ny, nz, L, W, T, element_type)
num_nodes = (nx + 1) * (ny + 1) * (nz + 1);
vertices = zeros(3, num_nodes);
for k = 0:nz
    for j = 0:ny
        for i = 0:nx
            n = node_id(i, j, k, nx, ny);
            vertices(:, n + 1) = [L * i / nx; W * j / ny; T * k / nz];
        end
    end
end

if strcmpi(element_type, 'hex8')
    elem_type = 'hex';
    elems = zeros(8, nx * ny * nz, 'int32');
    e = 1;
    for k = 0:(nz - 1)
        for j = 0:(ny - 1)
            for i = 0:(nx - 1)
                n000 = node_id(i, j, k, nx, ny);
                n100 = node_id(i + 1, j, k, nx, ny);
                n010 = node_id(i, j + 1, k, nx, ny);
                n110 = node_id(i + 1, j + 1, k, nx, ny);
                n001 = node_id(i, j, k + 1, nx, ny);
                n101 = node_id(i + 1, j, k + 1, nx, ny);
                n011 = node_id(i, j + 1, k + 1, nx, ny);
                n111 = node_id(i + 1, j + 1, k + 1, nx, ny);
                % COMSOL imported hex ordering is 000,100,010,110,001,101,011,111.
                elems(:, e) = int32([n000; n100; n010; n110; n001; n101; n011; n111]);
                e = e + 1;
            end
        end
    end
elseif strcmpi(element_type, 'tet4')
    elem_type = 'tet';
    elems = zeros(4, nx * ny * nz * 6, 'int32');
    e = 1;
    for k = 0:(nz - 1)
        for j = 0:(ny - 1)
            for i = 0:(nx - 1)
                n000 = node_id(i, j, k, nx, ny);
                n100 = node_id(i + 1, j, k, nx, ny);
                n010 = node_id(i, j + 1, k, nx, ny);
                n110 = node_id(i + 1, j + 1, k, nx, ny);
                n001 = node_id(i, j, k + 1, nx, ny);
                n101 = node_id(i + 1, j, k + 1, nx, ny);
                n011 = node_id(i, j + 1, k + 1, nx, ny);
                n111 = node_id(i + 1, j + 1, k + 1, nx, ny);
                elems(:, e) = int32([n000; n100; n110; n111]); e = e + 1;
                elems(:, e) = int32([n000; n110; n010; n111]); e = e + 1;
                elems(:, e) = int32([n000; n010; n011; n111]); e = e + 1;
                elems(:, e) = int32([n000; n011; n001; n111]); e = e + 1;
                elems(:, e) = int32([n000; n001; n101; n111]); e = e + 1;
                elems(:, e) = int32([n000; n101; n100; n111]); e = e + 1;
            end
        end
    end
else
    error('Unsupported element_type: %s', element_type);
end
end

function n = node_id(i, j, k, nx, ny)
n = i + (nx + 1) * (j + (ny + 1) * k);
end

function write_comsol_displacements(path, case_name, probes, ux, uy, uz, elem_type, traction_z, total_load)
fid = fopen(path, 'w');
if fid < 0
    error('Cannot write %s', path);
end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, 'case,node,node_id_or_probe_id,probe,x,y,z,ux,uy,uz,source,nearest_distance,element_formulation,integration,load_area,load_traction_z,total_load_check\n');
load_area = 0.02;
for r = 1:height(probes)
    dist = sqrt((probes.target_x(r) - probes.x(r))^2 + (probes.target_y(r) - probes.y(r))^2 + (probes.target_z(r) - probes.z(r))^2);
    if strcmp(elem_type, 'hex')
        formulation = 'COMSOL imported linear hexahedral mesh';
        integration = 'COMSOL solid mechanics default integration for linear hex; closest C3D8/full-integration reference';
    else
        formulation = 'COMSOL imported linear tetrahedral mesh';
        integration = 'COMSOL solid mechanics default integration for linear tet';
    end
    fprintf(fid, '%s,%d,%d,%s,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,COMSOL 6.2 LiveLink imported mesh,%.17g,%s,%s,%.17g,%.17g,%.17g\n', ...
        case_name, probes.node(r), probes.node(r), string(probes.name(r)), probes.x(r), probes.y(r), probes.z(r), ...
        ux(r), uy(r), uz(r), dist, formulation, integration, load_area, traction_z, traction_z * load_area);
end
end

function write_status(path, rows)
fid = fopen(path, 'w');
if fid < 0
    error('Cannot write %s', path);
end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, 'case,status,mesh_element_type,fixed_boundary_count,loaded_boundary_count,displacements_csv,model_mph\n');
for i = 1:size(rows, 1)
    fprintf(fid, '%s,%s,%s,%s,%s,%s,%s\n', rows{i, :});
end
end
