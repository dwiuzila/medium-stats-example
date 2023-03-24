"""
Parse network data from dataframe format into visdcc format 
"""

import re
import numpy as np
import pandas as pd
from config import DEFAULT_NODE_SIZE


def preprocess_data(df):
    table = df.copy()
    table[["stories", "writers"]] = np.exp(table[["stories", "writers"]]).round()
    table = (table
        .drop("related_topics", axis=1)
        .sort_values("stories", ascending=False)
    )
    table.columns = ["Topics", "Stories", "Writers"]
    return table

def generate_data(df, selected_topic="Life"):
    if selected_topic == "" or selected_topic is None:
        return None, None
    
    regex_pattern = "[^0-9a-zA-Z]+"
    clean_selected_topic = re.sub(regex_pattern, " ", selected_topic).lower().strip()
    clean_topics = df["topic"].str.replace(regex_pattern, " ", regex=True).str.lower().str.strip().values
    if clean_selected_topic not in clean_topics:
        return None, None

    related_topics = df.loc[clean_topics==clean_selected_topic, "related_topics"].item()
    df_filter = df["topic"].isin(related_topics + [selected_topic])
    df_graph = (
        df
        .loc[df_filter, ["topic", "related_topics"]]
        .explode(column="related_topics")
        .apply(set, axis=1)
        .drop_duplicates()
    )
    
    edges = pd.DataFrame()
    edges["from"], edges["to"] = df_graph.apply(list).str

    nodes = set.union(*df_graph)
    nodes = (
        df
        .loc[df["topic"].isin(nodes)]
        .drop("related_topics", axis=1)
        .rename({"topic": "id"}, axis=1)
    )
    return edges, nodes

def compute_scaling_vars_for_numerical_cols(df):
    """Identify and scale numerical cols"""
    # identify numerical cols
    numerics = ["int16", "int32", "int64", "float16", "float32", "float64"]
    numeric_cols = df.select_dtypes(include=numerics).columns.tolist()
    # var to hold the scaling function
    scaling_vars = {}
    # scale numerical cols
    for col in numeric_cols:
        minn, maxx = df[col].min(), df[col].max()
        scaling_vars[col] = {"min": minn, "max": maxx} 
    # return
    return scaling_vars

def parse_data(edge_df, node_df=None):
    """Parse the network dataframe into visdcc format
    Parameters
    -------------
    edge_df: pandas dataframe
            The network edge data stored in format of pandas dataframe 
    
    node_df: pandas dataframe (optional)
            The network node data stored in format of pandas dataframe 
    """
    # Data checks
    # Check 1: mandatory columns presence
    if ("from" not in edge_df.columns) or ("to" not in edge_df.columns):
        raise Exception("Edge dataframe missing either 'from' or 'to' column.")
    # Check 2: if node_df is present, it should contain "node" column
    if node_df is not None:
        if "id" not in node_df.columns:
            raise Exception("Node dataframe missing 'id' column.")

    # Data post processing - convert the from and to columns in edge data as string for searching
    edge_df.loc[:, ["from", "to"]] = edge_df.loc[:, ["from", "to"]].astype(str)

    # Data pot processing (scaling numerical cols in nodes and edge)
    scaling_vars = {"node": None, "edge": None}
    if node_df is not None:
        scaling_vars["node"] = compute_scaling_vars_for_numerical_cols(node_df)
    scaling_vars["edge"] = compute_scaling_vars_for_numerical_cols(edge_df)
    
    # create node list w.r.t. the presence of absence of node_df
    nodes = []
    if node_df is None:
        node_list = list(set(edge_df["from"].unique().tolist() + edge_df["to"].unique().tolist()))
        nodes = [{"id": node_name, "label": node_name, "shape": "dot", "size": DEFAULT_NODE_SIZE} for node_name in node_list]
    else:
        # convert the node id column to string
        node_df.loc[:, "id"] = node_df.loc[:, "id"].astype(str)
        # see if node imge url is present or not
        node_image_url_flag = "node_image_url" in node_df.columns
        # create the node data
        for node in node_df.to_dict(orient="records"):
            if not node_image_url_flag:
                nodes.append({**node, **{"label": node["id"], "shape": "dot", "size": DEFAULT_NODE_SIZE}})
            else:
                nodes.append({**node, **{"label": node["id"], "shape": "circularImage",
                                "image": node["node_image_url"], 
                                "size": 20}})

    # create edges from df
    edges = []
    for row in edge_df.to_dict(orient="records"):
        edges.append({**row, **{"id": row["from"] + "__" + row["to"],  "color": {"color": "#97C2FC"}}})
    
    # return
    return {"nodes": nodes, "edges": edges}, scaling_vars