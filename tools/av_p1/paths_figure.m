function paths_figure()
%PATHS_FIGURE  Homepage version of the Project-1 path figure (images/av_projects/p1_paths.png).
%
%   Run through make.sh (sets AV_P1 / AV_P1_LOGS, then scales the PNG into images/).
%
%   Same seed-1 runs as the report's figure (read from the saved .mat files, nothing is re-run).
%   Differences: plain labels, A* in black, and the sampling planners' last step into the goal is
%   drawn dashed (RRT, RRT* and Informed RRT* accept a path ending within goal_tol = 20 cells of the goal;
%   the report's costs include the straight line from there; RRT-Connect ends exactly at the goal).
%   Writes p1_paths_300dpi.png next to this file.

    here = fileparts(mfilename('fullpath'));
    p1 = getenv('AV_P1'); logs = getenv('AV_P1_LOGS');
    assert(~isempty(p1) && ~isempty(logs), 'set AV_P1 and AV_P1_LOGS');
    addpath(fullfile(p1, 'matlab'));
    p = init_params();

    col.RRT      = [0.902 0.624 0.000];   % Okabe-Ito, as in the report
    col.RRTstar  = [0.000 0.447 0.698];
    col.Connect  = [0.000 0.620 0.451];
    col.Informed = [0.800 0.475 0.655];
    col.Astar    = [0 0 0];
    col.start    = [0.106 0.620 0.467];
    col.goal     = [0.835 0.161 0.161];
    col.obst     = [0.78 0.78 0.78];

    maps = p.maps;
    f = figure('Visible', 'off', 'Units', 'inches', 'Position', [1 1 11 10], 'Color', 'w');
    t = tiledlayout(f, 2, 2, 'TileSpacing', 'compact', 'Padding', 'compact');
    for k = 1:numel(maps)
        [BW, s, g] = load_map_full(fullfile(p.maps_dir, [maps{k} '.png']));
        n = size(BW, 1);
        ax = nexttile(t); hold(ax, 'on');
        img = ones(n, n, 3);
        for c = 1:3, ch = img(:,:,c); ch(~BW) = col.obst(c); img(:,:,c) = ch; end
        image(ax, [1 n], [1 n], img);
        set(ax, 'YDir', 'reverse', 'XTick', [], 'YTick', []); axis(ax, 'equal'); axis(ax, [0.5 n+0.5 0.5 n+0.5]);

        art = @(dir, name) load(fullfile(logs, dir, sprintf('%s_seed1_%s_300.mat', name, maps{k})));
        ast  = load(fullfile(logs, 'm2_artifacts', sprintf('astar_euclid8_%s_300.mat', maps{k})));
        rrt  = art('m2_artifacts', 'rrt');
        conn = art('m4_artifacts', 'rrt_connect');
        star = art('m3_artifacts', 'rrt_star');
        info = art('m5_artifacts', 'rrt_informed');
        assert(star.budget == p.budget_300 && info.budget == p.budget_300, 'unexpected anytime budget');

        ids = ast.path(:).';
        hA = plot(ax, mod(ids-1, ast.n) + 1, floor((ids-1) / ast.n) + 1, '-', 'Color', col.Astar, 'LineWidth', 2.2);
        hR = plan(ax, rrt.path_xy,  g, col.RRT);
        hC = plan(ax, conn.path_xy, g, col.Connect);
        hS = plan(ax, star.path_xy, g, col.RRTstar);
        hI = plan(ax, info.path_xy, g, col.Informed);
        hSt = plot(ax, s(1), s(2), 'o', 'MarkerFaceColor', col.start, 'MarkerEdgeColor', 'k', 'MarkerSize', 10, 'LineWidth', 1);
        hGo = plot(ax, g(1), g(2), 's', 'MarkerFaceColor', col.goal,  'MarkerEdgeColor', 'k', 'MarkerSize', 11, 'LineWidth', 1);
        title(ax, sprintf('Map %d', k), 'FontSize', 12, 'FontWeight', 'normal');
        hD = plot(ax, nan, nan, ':', 'Color', [0.35 0.35 0.35], 'LineWidth', 2.2);   % legend entry only
        hold(ax, 'off');
    end
    lgd = legend([hR hC hS hI hA hD hSt hGo], ...
        {'RRT (first path)', 'RRT-Connect (first path)', 'RRT* (after 48,000 iterations)', ...
         'Informed RRT* (after 48,000 iterations)', 'A* (8-connected grid)', 'straight line to the goal', ...
         'start', 'goal'}, 'Orientation', 'horizontal', 'NumColumns', 4, 'FontSize', 10.5);
    lgd.Layout.Tile = 'south';
    assert(p.budget_300 == 48000, 'legend text assumes the 300x300 budget of 48,000 iterations');
    exportgraphics(f, fullfile(here, 'p1_paths_300dpi.png'), 'Resolution', 300);
    close(f);
    fprintf('PATHS_FIGURE_DONE\n');
end

function h = plan(ax, xy, g, c)
%PLAN  Solid path from the start to the accepting node, dashed straight line on to the exact goal.
    h = plot(ax, xy(:,1), xy(:,2), '-', 'Color', c, 'LineWidth', 1.6);
    plot(ax, [xy(end,1) g(1)], [xy(end,2) g(2)], ':', 'Color', c, 'LineWidth', 2.2);
end
