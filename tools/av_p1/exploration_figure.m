function exploration_figure()
%EXPLORATION_FIGURE  Homepage version of the Project-1 exploration figure (images/av_projects/p1_exploration.png).
%
%   Run through make.sh (sets AV_P1 / AV_P1_LOGS, then scales the PNG into images/).
%
%   Same seed-1 RRT trees and 8-connected A* expansions as the report's figure, read from the saved .mat
%   files (nothing is re-run), on maps 1 and 3 at 300 x 300. Differences: plain labels instead of internal
%   map / planner names, and no figure title. Writes p1_exploration_300dpi.png next to this file.

    here = fileparts(mfilename('fullpath'));
    p1 = getenv('AV_P1'); logs = getenv('AV_P1_LOGS');
    assert(~isempty(p1) && ~isempty(logs), 'set AV_P1 and AV_P1_LOGS');
    addpath(fullfile(p1, 'matlab'));
    p = init_params();

    col.tree     = [0.902 0.624 0.000];   % RRT colour of p1_paths.png
    col.expanded = [0.914 0.659 0.463];
    col.Astar    = [0 0 0];
    col.start    = [0.106 0.620 0.467];
    col.goal     = [0.835 0.161 0.161];
    col.obst     = [0.78 0.78 0.78];

    f = figure('Visible', 'off', 'Units', 'inches', 'Position', [1 1 11 11], 'Color', 'w');
    t = tiledlayout(f, 2, 2, 'TileSpacing', 'compact', 'Padding', 'compact');
    for k = [1 3]
        name = p.maps{k};
        [BW, s, g] = load_map_full(fullfile(p.maps_dir, [name '.png']));
        n = size(BW, 1);
        rrt = load(fullfile(logs, 'm2_artifacts', sprintf('rrt_seed1_%s_300.mat', name)));
        ast = load(fullfile(logs, 'm2_artifacts', sprintf('astar_euclid8_%s_300.mat', name)));
        assert(ast.n == n, 'A* artifact grid size differs from the map');

        % Left: the RRT tree when it reaches the goal.
        ax = map_axes(t, BW, col.obst, ones(n, n, 3));
        N = rrt.nodes; if size(N, 1) == 2 && size(N, 2) ~= 2, N = N.'; end   % stored as 2 x n_nodes
        par = rrt.parent(:); child = find(par > 0);
        X = [N(child, 1), N(par(child), 1), nan(numel(child), 1)].';
        Y = [N(child, 2), N(par(child), 2), nan(numel(child), 1)].';
        plot(ax, X(:), Y(:), '-', 'Color', col.tree, 'LineWidth', 0.8);
        ends(ax, s, g, col);
        title(ax, sprintf('Map %d: RRT tree, %s nodes', k, thousands(size(N, 1))), ...
            'FontSize', 12, 'FontWeight', 'normal');

        % Right: the cells A* expands before it reaches the goal, and its path.
        img = ones(n, n, 3);
        ids = ast.expanded_order(:);
        xs = mod(ids - 1, n) + 1; ys = floor((ids - 1) / n) + 1;
        for c = 1:3
            ch = img(:,:,c); ch(sub2ind([n n], ys, xs)) = col.expanded(c); img(:,:,c) = ch;
        end
        ax = map_axes(t, BW, col.obst, img);
        pid = ast.path(:).';
        plot(ax, mod(pid - 1, n) + 1, floor((pid - 1) / n) + 1, '-', 'Color', col.Astar, 'LineWidth', 2);
        ends(ax, s, g, col);
        title(ax, sprintf('Map %d: 8-connected A*, %s cells expanded', k, thousands(numel(ids))), ...
            'FontSize', 12, 'FontWeight', 'normal');
    end
    exportgraphics(f, fullfile(here, 'p1_exploration_300dpi.png'), 'Resolution', 300);
    close(f);
    fprintf('EXPLORATION_FIGURE_DONE\n');
end

function ax = map_axes(t, BW, obst, img)
    n = size(BW, 1);
    ax = nexttile(t); hold(ax, 'on');
    for c = 1:3, ch = img(:,:,c); ch(~BW) = obst(c); img(:,:,c) = ch; end
    image(ax, [1 n], [1 n], img);
    set(ax, 'YDir', 'reverse', 'XTick', [], 'YTick', []); axis(ax, 'equal'); axis(ax, [0.5 n+0.5 0.5 n+0.5]);
end

function ends(ax, s, g, col)
    plot(ax, s(1), s(2), 'o', 'MarkerFaceColor', col.start, 'MarkerEdgeColor', 'k', 'MarkerSize', 10, 'LineWidth', 1);
    plot(ax, g(1), g(2), 's', 'MarkerFaceColor', col.goal,  'MarkerEdgeColor', 'k', 'MarkerSize', 11, 'LineWidth', 1);
end

function str = thousands(v)
    str = regexprep(sprintf('%d', v), '(\d)(?=(\d{3})+$)', '$1 ');
end
