"""
Dash app to be rendered
"""

import visdcc
import pandas as pd
from dash import Dash, dcc, html, dash_table
from dash.dependencies import Input, Output
from utils import preprocess_data, generate_data, parse_data
from config import MIN_NODE_SIZE, MAX_NODE_SIZE, DEFAULT_NODE_SIZE


class Medial:
    """The main class"""

    def __init__(self):
        # Read data
        self.df = pd.read_json("datasets/medium_topics.json")
        
        # Preprocess data
        self.table = preprocess_data(self.df)
        edge_df, node_df = generate_data(self.df)
        self.data, self.scaling_vars = parse_data(edge_df, node_df)

        # List of methods to size topic nodes
        self.size_topics_by = ["Number of stories", "Number of writers"]
    
    def get_app_layout(self, size_topics_by, data, df):
        return html.Div(
            children=[
                html.Div(
                    className="row",
                    children=[
                        # Column for user controls
                        html.Div(
                            className="four columns div-user-controls",
                            children=[
                                html.A(
                                    html.Img(
                                        className="logo",
                                        src="assets/medial-logo.png",
                                    ),
                                    href="https://dwiuzila.medium.com/membership/",
                                ),
                                html.H2("KNOW YOUR MEDIUM TOPICS"),
                                html.P(
                                    """Discover a topic, observe how it relates to others,
                                    and of course play with the graph for a soothing fun."""
                                ),
                                # Change to side-by-side for mobile layout
                                html.Div(
                                    className="row",
                                    children=[
                                        html.Div(
                                            className="div-for-dropdown",
                                            children=[
                                                # Search box for topics
                                                dcc.Input(
                                                    id="topic-search", 
                                                    type="search", 
                                                    placeholder="Search for a topic (e.g. Life, Blockchain, Poetry)",
                                                    style={"width": "100%"}
                                                )
                                            ]
                                        ),
                                        html.Div(
                                            className="div-for-dropdown",
                                            children=[
                                                # Dropdown for topic sizing methods
                                                dcc.Dropdown(
                                                    id="topic-size-dropdown",
                                                    options=[
                                                        {"label": i, "value": i}
                                                        for i in size_topics_by
                                                    ],
                                                    placeholder="Size topics by",
                                                )
                                            ]
                                        )
                                    ]
                                ),
                                html.P(id="total-related-topics"),
                                html.P("Total number of topics you can search: {:,d}".format(len(df))),
                                dcc.Markdown("---"),
                                html.H2("MOST POPULAR"),
                                dash_table.DataTable(
                                    data=self.table.to_dict("records"),
                                    columns=[{"name": i, "id": i} for i in self.table.columns],
                                    page_size=9,
                                    sort_action="native",
                                    style_header={
                                        "backgroundColor": "rgb(30, 30, 30)",
                                        "fontWeight": "bold",
                                        "border": "none"
                                    },
                                    style_data={
                                        "backgroundColor": "rgb(50, 50, 50)",
                                    },
                                    style_cell_conditional=[
                                        {
                                            "if": {"column_id": "Topics"},
                                            "textAlign": "left"
                                        }
                                    ]
                                )
                            ]
                        ),
                        # Column for app graphs and plots
                        html.Div(
                            className="eight columns div-for-charts bg-grey",
                            children=[
                                visdcc.Network(
                                    id="graph",
                                    data=data,
                                    options={
                                        "height": "900px",
                                        "width": "100%",
                                        "nodes": {"font": {"color": "white"}},
                                        "interaction": {"hover": True},
                                        "physics": {"stabilization": {"iterations": 100}}
                                    }
                                )
                            ]
                        )
                    ]
                )
            ]
        )

    def callback_search_graph(self, df, search_text):
        edge_df, node_df = generate_data(df, search_text)
        if node_df is not None:
            data, scaling_vars = parse_data(edge_df, node_df)
            return data, scaling_vars
        return self.data, self.scaling_vars

    def callback_size_nodes(self, data, scaling_vars, size_topics_by):
        if size_topics_by is not None:
            method = size_topics_by.split()[-1]
            for node in data["nodes"]:
                max_size = scaling_vars["node"][method]["max"]
                min_size = scaling_vars["node"][method]["min"]
                scaling = (MAX_NODE_SIZE - MIN_NODE_SIZE) / (max_size - min_size)
                node["size"] = (node[method] - min_size) * scaling + MIN_NODE_SIZE
        else:
            for node in data["nodes"]:
                node["size"] = DEFAULT_NODE_SIZE
        return data

    def create(self):
        app = Dash(
            __name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}]
        )

        app.index_string = """
        <!DOCTYPE html>
        <html>
            <head>
                {%metas%}
                <title>{%title%}</title>
                <script 
                    data-name="BMC-Widget" 
                    data-cfasync="false" 
                    src="https://cdnjs.buymeacoffee.com/1.0.0/widget.prod.min.js" 
                    data-id="dwiuzila" 
                    data-description="Support me on Buy me a coffee!" 
                    data-message="Like what you see here? Consider tipping :)" 
                    data-color="#5F7FFF" 
                    data-position="Right" 
                    data-x_margin="18" 
                    data-y_margin="18">
                </script>
                {%favicon%}
                {%css%}
            </head>
            <body>
                {%app_entry%}
                <footer>
                    {%config%}
                    {%scripts%}
                    {%renderer%}
                </footer>
            </body>
        </html>
        """

        app.title = "MEDIAL - Medium For All"
        app.layout = self.get_app_layout(self.size_topics_by, self.data, self.df)

        # Update the total number of related topics
        @app.callback(
            Output("total-related-topics", "children"),
            Input("topic-search", "value"),
        )
        def update_total_related_topics(search_text):
            _, node_df = generate_data(self.df, search_text)
            if node_df is not None:
                return """Total number of "{}" related topics: {:,d}""".format(search_text, len(node_df)-1)
            elif search_text is None or search_text == "":
                return "Type a topic you want to find."
            return "Topic not found."

        # Create the main callbacks
        @app.callback(
            Output("graph", "data"),
            [Input("topic-search", "value"), Input("topic-size-dropdown", "value")],
        )
        def setting_pane_callback(search_text, size_topics_by):
            data, scaling_vars = self.callback_search_graph(self.df, search_text)
            data = self.callback_size_nodes(data, scaling_vars, size_topics_by)
            self.scaling_vars = scaling_vars
            self.data = data
            return data
        
        # Return server
        return app


medial = Medial()
app = medial.create()
server = app.server
app.run_server()