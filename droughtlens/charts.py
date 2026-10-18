"""Chart styling shared by every page, in the DroughtLens palette."""
import plotly.graph_objects as go

from droughtlens.theme import CHARCOAL, FOREST, IVORY, MUTED, OLIVE, RED, RULE, AMBER, SILK

BAR_TEXT = dict(textposition="outside", cliponaxis=False)
STATE_COLORS = {"IA": FOREST, "NE": AMBER}


def style(fig, height=340, legend=True):
    fig.update_layout(
        height=height, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor=IVORY, plot_bgcolor=IVORY,
        font=dict(family="DM Sans, sans-serif", size=15, color=CHARCOAL),
        legend=dict(orientation="h", y=-0.22, title_text=""), showlegend=legend,
    )
    fig.update_xaxes(showgrid=False, linecolor=MUTED)
    fig.update_yaxes(gridcolor=RULE, zeroline=True, zerolinecolor=MUTED)
    return fig
