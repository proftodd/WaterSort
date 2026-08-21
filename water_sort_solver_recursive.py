import copy

def is_solution(puzzle):
    """
    Check if the puzzle is solved (all bottles are empty or have a single layer).
    """
    for bottle in puzzle.values():
        layers = bottle['layers']
        if len(layers) > 1:
            return False
        if len(layers) == 1 and layers[0]['depth'] != bottle['capacity']:
            return False
    return True

def get_valid_pours(puzzle):
    """
    Generate all valid pours from the current state of the puzzle.
    """
    valid_pours = []

    for src, src_bottle in puzzle.items():
        if not src_bottle['layers'] or len(src_bottle['layers']) == 1 and src_bottle['layers'][0]['depth'] == src_bottle['capacity']:
            continue

        top_layer_src = src_bottle['layers'][-1]

        for dest, dest_bottle in puzzle.items():
            if src == dest:
                continue

            if not dest_bottle['layers']:
                # Destination bottle is empty
                valid_pours.append((src, dest))
            else:
                top_layer_dest = dest_bottle['layers'][-1]
                if top_layer_src['color'] == top_layer_dest['color'] and top_layer_src['depth'] + top_layer_dest['depth'] <= dest_bottle['capacity']:
                    # Top layers have the same color and destination can accept the pour
                    valid_pours.append((src, dest))

    return valid_pours

def perform_pour(puzzle, src, dest):
    """
    Perform a pour from source bottle to destination bottle.
    Returns a new puzzle state with the pour applied.
    """
    new_puzzle = copy.deepcopy(puzzle)

    top_layer_src = new_puzzle[src]['layers'].pop()
    if new_puzzle[dest]['layers']:
        top_layer_dest = new_puzzle[dest]['layers'].pop()
        combined_depth = top_layer_src['depth'] + top_layer_dest['depth']
        new_layer = {'color': top_layer_src['color'], 'depth': combined_depth}
    else:
        new_layer = copy.deepcopy(top_layer_src)

    new_puzzle[dest]['layers'].append(new_layer)

    return new_puzzle

def solve_water_sort(puzzle):
    """
    Recursively attempt to solve the water sort puzzle.
    Returns a list of pours if a solution is found, otherwise returns None.
    """
    if is_solution(puzzle):
        return []

    valid_pours = get_valid_pours(puzzle)

    for pour in valid_pours:
        new_puzzle = perform_pour(puzzle, *pour)
        result = solve_water_sort(new_puzzle)
        if result is not None:
            return [pour] + result

    return None

# Example usage
puzzle_input = {
    "a": { "capacity": 4, "layers": [ { "depth": 2, "color": "blue" }, { "depth": 2, "color": "white" } ] },
    "b": { "capacity": 4, "layers": [ { "depth": 2, "color": "white" } ] },
    "c": { "capacity": 4, "layers": [ { "depth": 2, "color": "blue" } ] }
}

solution = solve_water_sort(puzzle_input)
print(solution)  # Output should be a list of pours that solves the puzzle

