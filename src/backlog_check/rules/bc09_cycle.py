"""BC-09: dependencies form a cycle. One finding per cycle names all items involved."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence

from ..context import Context
from ..model import Finding

RULE = "BC-09"


def check_bc09(ctx: Context) -> Iterator[Finding]:
    # ASSUMPTION: done items are left out of the graph; a cycle through a done item is resolved.
    # Items that depend on each other in any way form one finding (strongly connected component).
    graph = {
        item.id: list(dict.fromkeys(d for d in item.depends_on if d in ctx.active_ids))
        for item in ctx.active
    }
    for component in strongly_connected(graph):
        if len(component) > 1 or component[0] in graph[component[0]]:
            members = sorted(component, key=ctx.position.__getitem__)
            yield ctx.finding(
                RULE,
                ctx.by_id[members[0]],
                "bc09.cycle",
                params={"items": members},
                related=tuple(members[1:]),
                field="depends_on",
            )


def strongly_connected(graph: Mapping[str, Sequence[str]]) -> list[list[str]]:
    """Tarjan's algorithm without recursion. Nodes are visited in the order of ``graph``."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[list[str]] = []

    def visit(node: str) -> None:
        index[node] = low[node] = len(index)
        stack.append(node)
        on_stack.add(node)

    for root in graph:
        if root in index:
            continue
        visit(root)
        work = [(root, iter(graph[root]))]
        while work:
            node, successors = work[-1]
            for successor in successors:
                if successor not in index:
                    visit(successor)
                    work.append((successor, iter(graph[successor])))
                    break
                if successor in on_stack:
                    low[node] = min(low[node], index[successor])
            else:
                work.pop()
                if work:
                    parent = work[-1][0]
                    low[parent] = min(low[parent], low[node])
                if low[node] == index[node]:
                    component = []
                    while True:
                        member = stack.pop()
                        on_stack.discard(member)
                        component.append(member)
                        if member == node:
                            break
                    components.append(component)
    return components
