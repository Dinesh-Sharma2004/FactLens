from langgraph.graph import StateGraph

async def retriever_agent(state):
    query = state["query"]
    retriever = state["retriever"]

    docs = await retriever(query)

    return {"docs": docs}



def confidence_agent(state):
    docs = state.get("docs", [])

    score = len(docs) / 5 if docs else 0
    return {"confidence": round(score, 2)}


def build_graph(retriever):
    graph = StateGraph(dict)

    # Nodes
    graph.add_node(
        "retriever",
        lambda state: retriever_agent({**state, "retriever": retriever})
    )
    graph.add_node("confidence", confidence_agent)

    # Flow
    graph.set_entry_point("retriever")
    graph.add_edge("retriever", "confidence")

    return graph.compile()
