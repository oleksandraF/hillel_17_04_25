import dash
from dash import html

print("Dash version:", dash.__version__)  

app = dash.Dash(__name__)
app.layout = html.Div("Hello, Dash! If you see this, server is running.")

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)
