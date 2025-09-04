# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# ::::::::::::::::::::::: IMPORTS :::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
import os
import dash
from dash import dcc, html, Input, Output
import dash_leaflet as dl
import dash_bootstrap_components as dbc
import dash_leaflet.express as dlx
from dash_extensions.javascript import assign
from dash import Dash
import rioxarray as rxr
import numpy as np
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib import colors
from rasterio.crs import CRS
from PIL import Image
import dask.array as da
from flask_caching import Cache
import json



# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::: INITIALIZING THE DASH APP ::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# app = dash.Dash(
#     __name__, 
#     external_stylesheets=[dbc.themes.BOOTSTRAP],
#     external_scripts=["https://cdnjs.cloudflare.com/ajax/libs/chroma-js/2.1.0/chroma.min.js"],
#     prevent_initial_callbacks=True
# )

app = Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    external_scripts=[
        "https://cdnjs.cloudflare.com/ajax/libs/chroma-js/2.1.0/chroma.min.js",
        "https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"
    ],
    prevent_initial_callbacks=True
)

# Add this meta tag to ensure proper mobile rendering
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{%title%}</title>
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
'''

server = app.server  # Required for static file serving
app.title = "Cilvēka dzīvotnes modelēšanas rīks"


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::: LOADING DATA FUNCTIONS AND CACHING :::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
cache = Cache(app.server, config={"CACHE_TYPE": "SimpleCache"})

# Load the data with caching
def load_raster(file_path):
    """Load raster data using Dask."""
    return rxr.open_rasterio(file_path, chunks="auto").squeeze()

@cache.memoize(timeout=300)  # Cache for 5 minutes
def load_data_list(file_path):
    """Load data list from an Excel file."""
    return pd.read_excel(file_path)

@cache.memoize(timeout=300)  # Cache for 5 minutes
def get_jet_colorscale(n_colors=10):
    cmap = plt.get_cmap('jet')
    return [colors.to_hex(cmap(i / (n_colors - 1))) for i in range(n_colors)]


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::: CONSTANTS ::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
SELECTED_FONT_CSS = "'Poppins', sans-serif"
VRI_LOGO_PATH = "/assets/images/VRI_logo.png"
CESIS_KAD_GEOJSON = "assets/geojson/Cesis_kad.geojson"
CESIS_ROAD_GEOJSON = "/assets/geojson/Cesis_road4.geojson"
STATIC_PATH = "static"
os.makedirs(STATIC_PATH, exist_ok=True)
COLORSCALE = get_jet_colorscale()
CORRECT_BOUNDS = [[57.507346438, 24.77478809], [56.91368127, 26.189455607999996]]


data_list = load_data_list('Layers/HH_layers.xlsx')
data_keys = list(data_list.Name)
base_raster = load_raster('Layers/10301.tif')
base_raster.data[base_raster.data >= 0] = 0
base_raster = base_raster.astype(np.float64)

with open(CESIS_KAD_GEOJSON, 'r', encoding='utf-8') as f:
    cesis_kad_data = json.load(f)

# Debugging:
# print(cesis_kad_data["features"][0]["properties"])
# print(cesis_kad_data) 

# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# ::::::::::::::::::::::: JS FUNCTIONS ::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

# JS Function needed for propertues Values on hover
on_each_feature = assign("""
function(feature, layer, context){
    layer.bindTooltip(`KAD: ${feature.properties.KAD || 'No KAD available'} <br> ha: ${feature.properties.Hectares} <br> pag: ${feature.properties.pag}`)
}
""")

# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# ::::::::::::::::::::::: PAGE LAYOUT :::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

app.layout = dbc.Container([
    # ::::::::::::::::::::::: Title and Logo row :::::::::::::::::::::::
    dbc.Row([
        dbc.Col([
            html.Img(
                src = VRI_LOGO_PATH, 
                style={"height": "90px", "margin-right": "1px"} 
            ), 
        ], width="auto"),

        dbc.Col([
            html.H1("Cilvēka dzīvotnes modelēšanas rīks", 
                    className="text-center mt-4 mb-4", 
                    style={
                        "display": "inline-block", 
                        "vertical-align": "middle", 
                        "font-family": SELECTED_FONT_CSS,
                        "font-size": "36px" ,
                        "font-weight": "500",
                        }),
        ], width=True),

    ], justify="center", align="center"),
    
    # ::::::::::::::::::::::: DIVIDIER :::::::::::::::::::::::
    dbc.Row([
        dbc.Col([
            html.Hr(),  
        ])
    ]),

    # ::::::::::::::::::::::: POSITIVE AND NEGATIVE FACTORS SELECTION :::::::::::::::::::::::
    dbc.Row([
        dbc.Col([

            html.H6("Demo versija Cēsu novadam",
                    className="text-danger mb-4",
                    style={
                        "font-family": SELECTED_FONT_CSS,            
                        "font-weight": "700",
                        }
                    ),

            html.H5("Faktoru izvēlne",
                    style={
                        "font-family": SELECTED_FONT_CSS,                
                        "font-weight": "600",
                        }
                    ),

            html.H6("Pozitīvie faktori (+1):",
                    style={
                        "font-family": SELECTED_FONT_CSS,           
                        "font-weight": "500",
                        }
                    ),
            dcc.Dropdown(
                id="pos-factors",
                options=[{"label": key, "value": key} for key in data_keys],
                multi=True,
                value=["Ainavas atvērtums"]
            ),

            html.H6("Negatīvie faktori (-1):",
                    className="mt-3",
                    style={
                        "font-family": SELECTED_FONT_CSS,           
                        "font-weight": "500",
                        }
                    ),
            dcc.Dropdown(
                id="neg-factors",
                options=[{"label": key, "value": key} for key in data_keys],
                multi=True
            ),

            html.H5("Vizualizāciju izvēlne",
                    className="mt-3",
                    style={"font-family": SELECTED_FONT_CSS, "font-weight": "600"}),

            html.H6("Caurspīdīguma maiņa:",
                    style={"font-family": SELECTED_FONT_CSS, "font-weight": "500"}),

            dcc.Slider(
                id="layer-transparency",
                min=0,
                max=1,
                step=0.05,
                value=0.5,
                marks={0: '0%', 0.5: '50%', 1: '100%'}
            ),

            html.H6("Slieksnis datu vizualizēšanai:",
                    className="mt-3",
                    style={"font-family": SELECTED_FONT_CSS, "font-weight": "500"}),

            dcc.Slider(
                id="data-threshold",
                min=0,
                max=100,
                step=1,
                value=0,
                marks={0: '0', 50: '50', 100: '100'}
            ),

        ], width=3),
        
         # ::::::::::::::::::::::: MAP SECTION :::::::::::::::::::::::
        # dbc.Col([
        #     dl.Map(center=[57.22, 25.42], zoom=9, children=[
        #         dl.LayersControl([

        #             # ::::::::::::::::::::::: COLORBAR :::::::::::::::::::::::
        #             dl.LayerGroup(id="layer-group"),
        #                 dl.Colorbar(
        #                     id="colorbar",
        #                     min=0, max=100, 
        #                     nTicks=5, 
        #                     colorscale=COLORSCALE,  
        #                     position="topright",
        #                     width=300,
        #                     height=10,
        #                 ),

        #             # ::::::::::::::::::::::: BASE LAYERS ::::::::::::::::::::::
        #             dl.BaseLayer(dl.TileLayer(url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"), name="OpenStreetMap", checked=True),
        #             dl.BaseLayer(dl.TileLayer(url="http://{s}.google.com/vt/lyrs=s,h&x={x}&y={y}&z={z}",
        #                 maxZoom=20,
        #                 subdomains=['mt0', 'mt1', 'mt2', 'mt3']), name="Google Satellite"),

        #             # ::::::::::::::::::::::: RESULT LAYER AND GEOJSON FILES ::::::::::::::::::::::
                
        #             # dl.Overlay(dl.GeoJSON(
        #             #     url=CESIS_KAD_GEOJSON,
        #             #     id="cesis-kad-overlay",
        #             #     options={"style": {"color": "#df543a"}},
                        
        #             # ), name="Kadastri", checked=False)
                    
        #             dl.Overlay(
        #                 dl.GeoJSON(
        #                     data=cesis_kad_data, 
        #                     id="cesis-kad-overlay",
        #                     options={
        #                         "style": {
        #                             "color": "#FEFEFA",  
        #                             "weight": 1,         
        #                         }
        #                     },
        #                     hoverStyle={
        #                         "weight": 3,  
        #                         "color": "#ff0000",  
        #                         "dashArray": "5,5"  
        #                     },

        #                     onEachFeature=on_each_feature,

        #                 ),
        #                 name="Kadastri",
        #                 checked=False
        #             ),

        #             dl.Overlay(dl.GeoJSON(
        #                 url=CESIS_ROAD_GEOJSON,
        #                 id="cesis-road-overlay",
        #                 options={"style": {
        #                     "color": "#000000", 
        #                     "weight": 2, 
        #                     }
        #                 },
        #             ), name="Ceļi", checked=False),

        #             dl.Overlay(dl.ImageOverlay(
        #                 id="raster-overlay", 
        #                 url="/static/default_raster.webp", 
        #                 bounds=CORRECT_BOUNDS,
        #                 opacity=0.5
        #             ), name="Dzīvotnes Kartējums", checked=True),

                    
        #         ]),
                
        #     ], style={"height": "600px", "width": "100%"}, id="map"),

        # ], width=9),

        dbc.Col([
            dl.Map(
                center=[57.22, 25.42],
                zoom=9,
                style={"height": "600px", "width": "100%"},
                id="map",
                children=[
                    dl.LayersControl(
                        children=[

                            # ::::::::::::::::::::::: COLORBAR :::::::::::::::::::::::
                            dl.LayerGroup(id="layer-group"),
                            dl.Colorbar(
                                id="colorbar",
                                min=0, max=100,
                                nTicks=5,
                                colorscale=COLORSCALE,
                                position="topright",
                                width=300,
                                height=10,
                            ),

                            # ::::::::::::::::::::::: BASE LAYERS ::::::::::::::::::::::
                            dl.BaseLayer(
                                dl.TileLayer(
                                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                                ),
                                name="OpenStreetMap",
                                checked=True
                            ),
                            dl.BaseLayer(
                                dl.TileLayer(
                                    url="http://{s}.google.com/vt/lyrs=s,h&x={x}&y={y}&z={z}",
                                    maxZoom=20,
                                    subdomains=['mt0', 'mt1', 'mt2', 'mt3']
                                ),
                                name="Google Satellite"
                            ),

                            # ::::::::::::::::::::::: RESULT LAYER AND GEOJSON FILES ::::::::::::::::::::::
                            dl.Overlay(
                                dl.GeoJSON(
                                    data=cesis_kad_data,
                                    id="cesis-kad-overlay",
                                    options={
                                        "style": {
                                            "color": "#FEFEFA",
                                            "weight": 1,
                                        }
                                    },
                                    hoverStyle={
                                        "weight": 3,
                                        "color": "#ff0000",
                                        "dashArray": "5,5"
                                    },
                                    onEachFeature=on_each_feature,
                                ),
                                name="Kadastri",
                                checked=False
                            ),

                            dl.Overlay(
                                dl.GeoJSON(
                                    url=CESIS_ROAD_GEOJSON,
                                    id="cesis-road-overlay",
                                    options={"style": {"color": "#000000", "weight": 2}},
                                ),
                                name="Ceļi",
                                checked=False
                            ),

                            dl.Overlay(
                                dl.ImageOverlay(
                                    id="raster-overlay",
                                    url="/static/default_raster.webp",
                                    bounds=CORRECT_BOUNDS,
                                    opacity=0.5
                                ),
                                name="Dzīvotnes Kartējums",
                                checked=True
                            ),
                        ]
                    )
                ]
            ),
        ], width=9),



    ]),

    # ::::::::::::::::::::::: DIVIDIER :::::::::::::::::::::::
    dbc.Row([
        dbc.Col([
            html.Hr(),  
        ])
    ]),

    # ::::::::::::::::: POSITIVE AND NEGATIVE FACTORS DESCRIPTION DISPLAY :::::::::::::::::
    dbc.Row([
        dbc.Col([
            html.H5("Faktoru apraksti",
                    className="mt-3",
                    style={"font-family": SELECTED_FONT_CSS, "font-weight": "600"}),
            dcc.Markdown(id="factors-description", style={"font-family": SELECTED_FONT_CSS, "font-weight": "400"})
        ])
    ]),

    # ::::::::::::::::::::::: DIVIDIER :::::::::::::::::::::::
    dbc.Row([
        dbc.Col([
            html.Hr(),  
        ])
    ]),

    # ::::::::::::::::::::::: FOOTER :::::::::::::::::::::::
    dbc.Row([
        dbc.Col([ 
            html.P(f"Copyright © 2025 Vides risinājumu institūts"),  
        ])
    ]),

])







# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# ::::::::::::::::::::::: FUNCTIONALITY :::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
@app.callback(
    [Output("raster-overlay", "url"),
     Output("raster-overlay", "bounds"),
     Output("raster-overlay", "opacity"),
     Output("factors-description", "children")],
    [Input("pos-factors", "value"),
     Input("neg-factors", "value"),
     Input("layer-transparency", "value"),
     Input("data-threshold", "value")]
)
def update_map(pos_factors, neg_factors, transparency, data_threshold):
    if not pos_factors and not neg_factors:
        return "", [[56.0, 24.0], [58.0, 26.0]], transparency, "No factors selected."

    A = base_raster.copy()
    n = 0

    if pos_factors:
        for factor in pos_factors:
            filename = 'Layers/' + data_list.Layer[data_list.Name == factor].values[0]
            B = load_raster(filename)
            A.data += B.data
            n += 1

    if neg_factors:
        for factor in neg_factors:
            filename = 'Layers/' + data_list.Layer[data_list.Name == factor].values[0]
            B = load_raster(filename)
            A.data -= B.data
            n += 1

    if n > 0:
        A.data /= n
    A.data[A.data < 0] = 0  # Mask negative values
    A_max = A.data.max()

    # Normalize the data to range 0-1 for the colormap
    normalized_data = A.data / A_max

    # Apply a threshold to remove dead zones
    threshold = data_threshold / 100.0  # Convert percentage to range 0-1
    normalized_data[normalized_data < threshold] = 0

    # Set insignificant areas to transparent
    colormap = plt.get_cmap("jet")  # Jet colormap
    A_rgba = colormap(normalized_data)  # Apply colormap to normalized data
    A_rgba[..., 3] = (normalized_data > 0).astype(float)  # Set alpha channel based on significance

    # Crop to the bounding box of significant values
    nonzero_indices = np.argwhere(normalized_data > 0)
    if nonzero_indices.size > 0:
        min_row, min_col = nonzero_indices.min(axis=0)
        max_row, max_col = nonzero_indices.max(axis=0)

        # Crop the RGBA image to the bounding box
        A_cropped = A_rgba[min_row:max_row+1, min_col:max_col+1]

        # Calculate geographic bounds for the cropped raster
        bounds = base_raster.rio.bounds()
        pixel_width = (bounds[2] - bounds[0]) / A.shape[1]
        pixel_height = (bounds[3] - bounds[1]) / A.shape[0]

        # Correct the geographic bounds for leaflet (invert latitude and longitude)
        cropped_bounds = [
            [bounds[3] - (max_row + 1) * pixel_height, bounds[0] + min_col * pixel_width],
            [bounds[3] - min_row * pixel_height, bounds[0] + (max_col + 1) * pixel_width],
        ]
    else:
        A_cropped = A_rgba  # Fallback to the original data
        bounds = base_raster.rio.bounds()
        cropped_bounds = [
            [bounds[3], bounds[0]],
            [bounds[1], bounds[2]],
        ]

    # Save the cropped raster as a transparent image
    output_filename = "output_raster.webp"
    output_path = os.path.join(STATIC_PATH, output_filename)
    img = Image.fromarray((A_cropped * 255).astype(np.uint8))
    img.save(output_path, format="WEBP", quality=75)  # Faster saving and better compression

    # Add a timestamp to force the browser to fetch the updated image
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    image_url = f"/static/{output_filename}?t={timestamp}"

    # Generate description for selected factors
    description = "**Pozitīvie faktori ar koeficienta vērtību +1:**  \n"
    if pos_factors:
        for factor in pos_factors: 
            description += f"***- {factor}***  \n"
            description += data_list.Comment[data_list.Name == factor].values[0] + "  \n"
    else:
        description += "- Nav izvēlēts neviens  \n"
    
    description += "  \n**Negatīvie faktori ar koeficienta vērtību -1:**  \n"
    if neg_factors:
        for factor in neg_factors:
            description += f"***- {factor}***  \n"
            description += data_list.Comment[data_list.Name == factor].values[0] + "  \n"
    else:
        description += "- Nav izvēlēts neviens"

    # DEBUGGING:
    # print(cropped_bounds)

    return image_url, cropped_bounds, transparency, description

# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# ::::::::::::::::::::::: APP EXECUTION :::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
if __name__ == "__main__":
    app.run_server(debug = False)