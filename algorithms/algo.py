import math
import networkx as nx
import itertools
import random

def CaGreS(dag, k, similarity_df=None, semantic_threshold=0.0):
    """
    Implements Algorithm 1 (CaGreS) from the paper
    Inputs:
      dag (nx.DiGraph) : The original causal DAG.
      k (int)          : Target number of summary nodes.
      similarity_df    : (Optional) A DataFrame or dict with semantic similarities.
    
    Returns:
      A summary DAG (NetworkX DiGraph) with k (or fewer) nodes.
    """
    H = dag.copy()

    H = low_cost_merges(H, similarity_df)
    while len(H.nodes) > k:
        min_cost = math.inf
        best_pair = None

        # Explore all pairs
        for (U, V) in itertools.combinations(H.nodes, 2):
            if not a_valid_pair(U, V, H, similarity_df, semantic_threshold=0.0):
                continue

            c = get_cost(U, V, H)

            # Keep the pair with the minimal cost
            if c < min_cost:
                min_cost = c
                best_pair = (U, V)
            elif math.isclose(c, min_cost, rel_tol=1e-9):
                # Tie-break randomly (line 13 at CaGreS in the paper)
                if random.choice([True, False]):
                    best_pair = (U, V)

        # If no valid pair was found, break to avoid infinite loops
        if best_pair is None:
            break

        # Merge the best pair
        U, V = best_pair
        H = merge_nodes(H, U, V)
    return H

def a_valid_pair(U, V, H, similarity_df=None, semantic_threshold=0.0):
    """
    Checks if merging U, V would be valid (Algorithm 1, line 8, IsValidPair).
    1) Optional semantic check (like your code did)
    2) Check if merging them would create a directed cycle in H
    """
    # Semantic check
    if not check_semantic(U, V, similarity_df, semantic_threshold):
        return False

    # Cycle check: Merge the nodes in a temporary graph, see if the result is still a DAG to avoid self loops or cycles
    temp = H.copy()
    temp = merge_nodes(temp, U, V, self_loops=True)  # or self_loops=False, as desired
    if not nx.is_directed_acyclic_graph(temp):
        return False

    return True

def check_semantic(node1, node2, similarity_df, semantic_threshold):
    if similarity_df is None:
        return True

    sub1 = node1.split(',\n')
    sub2 = node2.split(',\n')
    for s1 in sub1:
        for s2 in sub2:
            sim = max(similarity_df[s1][s2], similarity_df[s2][s1])
            if sim < semantic_threshold:
                return False
    return True

def merge_nodes(G, n1, n2, self_loops=False):
    """
    Merge n2 into n1 using nx.contracted_nodes, then rename the merged node 
    to a combined label "n1,\nn2".
    """
    merged = nx.contracted_nodes(G, n1, n2, self_loops=self_loops)
    new_label = n1 + ",\n" + n2
    merged = nx.relabel_nodes(merged, {n1: new_label})
    return merged

def get_cost(U, V, H):
    """
    Implements Algorithm 2 from the paper: The GetCost procedure.
    1) cost for "new edges" among the cluster
    2) cost for "new parents"
    3) cost for "new children"
    """
    # Determine how many original nodes each label represents
    subU = U.split(',\n')
    subV = V.split(',\n')
    sizeU = len(subU)
    sizeV = len(subV)

    cost = 0

    # If H does NOT have edge U->V, add size(U)*size(V)
    if not H.has_edge(U, V):
        cost += sizeU * sizeV

    # "New parents" penalty
    parentsU = set(H.predecessors(U))
    parentsV = set(H.predecessors(V))
    parentsOnlyU = parentsU - parentsV
    parentsOnlyV = parentsV - parentsU
    cost += len(parentsOnlyU) * sizeV
    cost += len(parentsOnlyV) * sizeU

    # "New children" penalty
    childrenU = set(H.successors(U))
    childrenV = set(H.successors(V))
    childrenOnlyU = childrenU - childrenV
    childrenOnlyV = childrenV - childrenU
    cost += len(childrenOnlyU) * sizeV
    cost += len(childrenOnlyV) * sizeU

    return cost

def low_cost_merges(dag, similarity_df=None, semantic_threshold=0.0):
    """
    Implements "Merge node‐pairs in which their cost <= 1" (Algorithm 1, line 2).
    We do this one merge at a time in a loop (not all simultaneously),
    because each merge changes the graph and can affect subsequent costs.
    """
    G = dag.copy()

    # Keep trying until no more merges of cost <= 1 can be found
    while True:
        merged_something = False
        for (n1, n2) in itertools.combinations(list(G.nodes), 2):
            if not a_valid_pair(n1, n2, G, similarity_df, semantic_threshold):
                continue

            c = get_cost(n1, n2, G)
            if c <= 1:
                # Merge them immediately
                G = merge_nodes(G, n1, n2)
                merged_something = True
                # Because we changed the graph, start again
                break  
        if not merged_something:
            # No more merges with cost <= 1
            break
    return G