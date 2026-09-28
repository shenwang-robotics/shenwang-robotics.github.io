function informed_frames()
%INFORMED_FRAMES  Exact Informed RRT* states for the homepage clip (map 2, 30x30, seed 1).
%
%   Run through make.sh. Writes informed_frames.mat next to this file; informed_clip.py draws it.
%
%   rrt_informed.m reseeds the RNG on entry and only reads max_iters as its loop bound, so a run
%   with max_iters = k is exactly the planner state after iteration k: tree with the parents as
%   rewired so far, best path, and the ellipse's c_best. One such run per frame.
%
%   Samples: the planner only records its post-solution (ellipse) samples. The whole sample
%   stream is replayed here from the same RNG (1 rand() for the goal-bias coin, +2 for a
%   uniform point before the first path; 2 per ellipse sample after it) and checked against
%   that record.

    here = fileparts(mfilename('fullpath'));
    p1 = getenv('AV_P1'); logs = getenv('AV_P1_LOGS');
    assert(~isempty(p1) && ~isempty(logs), 'set AV_P1 and AV_P1_LOGS');
    addpath(fullfile(p1, 'matlab'));
    p = init_params(); addpath(p.a4_dir);

    [BW, sx, gx] = load_map(fullfile(p.maps_dir, 'map_2_d.png'));
    P = p.rrt30; P.gamma_safety = p.rrt_star_gamma_safety; P.seed = 1; P.max_iters = p.budget_30;

    % full run: must reproduce the report's saved run
    P.emit_samples = true;
    [~, ~, tree, info] = rrt_informed(BW, sx, gx, P);
    P.emit_samples = false;
    A = load(fullfile(logs, 'm5_artifacts', 'rrt_informed_seed1_map_2_d_30.mat'));
    assert(isequal(tree.nodes, A.nodes) && isequal(tree.parent, A.parent), 'full run differs from the saved run');
    B  = P.max_iters;
    fs = info.first_solution_iter;

    % sample stream replay
    n = size(BW, 1); goal = gx(:); samples = zeros(2, B);
    rng(P.seed, 'twister');
    for it = 1:fs
        if rand() < P.p_goal, samples(:,it) = goal;
        else, samples(:,it) = [0.5 + n*rand(); 0.5 + n*rand()]; end
    end
    for it = fs+1:B
        cb = info.improve_costs(find(info.improve_iters < it, 1, 'last'));   % c_best in force
        r1 = cb/2; conj = sqrt(max(cb^2 - info.c_min^2, 0))/2;
        br = sqrt(rand()); th = 2*pi*rand();
        samples(:,it) = info.ellipse_C * [r1*br*cos(th); conj*br*sin(th)] + info.ellipse_centre;
    end
    assert(max(abs(samples(:,fs+1:B) - info.ellipse_samples), [], 'all') < 1e-9, 'sample replay mismatch');

    % frame schedule: the search before the first path, then quadratic spacing so the fast early
    % shrinking of the ellipse gets more frames than the slow tail
    u  = (1:200) / 200;
    ks = unique([round(linspace(0, fs, 41)), fs + round((B - fs) * u.^2)]);

    F = struct('iter', num2cell(ks), 'n_nodes', 0, 'parent', [], 'path_xy', [], 'c_best', inf);
    for i = 1:numel(ks)
        Q = P; Q.max_iters = ks(i);
        [path_xy, ~, tr, inf_k] = rrt_informed(BW, sx, gx, Q);
        assert(isequal(tr.nodes, tree.nodes(:, 1:tr.n_nodes)), 'node prefix mismatch');
        F(i).n_nodes = tr.n_nodes;
        F(i).parent  = int32(tr.parent);
        F(i).path_xy = path_xy;
        F(i).c_best  = inf_k.best_completed_cost;
    end
    assert(isequal(F(end).parent, int32(tree.parent)), 'last frame differs from the full run');

    frames = F; nodes = tree.nodes; c_min = info.c_min;  %#ok<NASGU>
    ellipse_C = info.ellipse_C; ellipse_centre = info.ellipse_centre; first_solution_iter = fs;  %#ok<NASGU>
    budget = B; start_xy = sx; goal_xy = gx; free = BW;  %#ok<NASGU>
    save(fullfile(here, 'informed_frames.mat'), 'frames', 'nodes', 'samples', 'c_min', 'ellipse_C', ...
        'ellipse_centre', 'first_solution_iter', 'budget', 'start_xy', 'goal_xy', 'free', '-v7');
    fprintf('INFORMED_FRAMES_DONE %d frames, first path at iteration %d, final c_best %.3f\n', ...
        numel(ks), fs, F(end).c_best);
end
