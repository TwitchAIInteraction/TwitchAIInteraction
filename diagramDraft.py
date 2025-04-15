from matplotlib import pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

# Set up the figure and axis
fig, ax = plt.subplots(figsize=(20, 15))
ax.axis('off')

# Define colors for different types of components
colors = {
    "Service": "#AED6F1",
    "API": "#F9E79F",
    "Storage": "#A9DFBF",
    "Configuration": "#F5B7B1",
    "ErrorHandling": "#D7BDE2",
    "User": "#FAD7A0"
}

# Define component details: (Label, (x, y), Type)
components = [
    ("User", (0.1, 0.9), "User"),
    ("Twitch API", (0.3, 0.8), "API"),
    ("OpenAI API\n(Chat Completion)", (0.7, 0.8), "API"),
    ("Twitch Bot", (0.5, 0.6), "Service"),
    ("ElevenLabs API\n(Voice Generation)", (0.7, 0.6), "API"),
    ("Logging &\nChat Storage", (0.9, 0.6), "Storage"),
    (".env Configuration\nFile", (0.3, 0.4), "Configuration"),
    ("Prompt File", (0.3, 0.3), "Configuration"),
    ("Chat Log File", (0.7, 0.4), "Storage"),
    ("Local Storage &\nLogging", (0.9, 0.4), "Storage"),
    ("Error Handling &\nDebugging", (0.5, 0.2), "ErrorHandling")
]

# Adjusted rectangle size
rect_width = 0.12
rect_height = 0.06

# Draw rectangles with labels
for label, (x, y), comp_type in components:
    facecolor = colors.get(comp_type, "lightgrey")
    rect = mpatches.FancyBboxPatch(
        (x - rect_width / 2, y - rect_height / 2),
        rect_width, rect_height,
        boxstyle="round,pad=0.02",
        edgecolor="black",
        facecolor=facecolor,
        linewidth=1.5
    )
    ax.add_patch(rect)
    plt.text(x, y, label, ha="center", va="center", fontsize=10, fontweight="bold")

# Define connections: (start_label, end_label, label_text, (x, y) for label)
connections = [
    ("User", "Twitch API", "Sends Messages & Events", (0.2, 0.85)),
    ("Twitch API", "Twitch Bot", "Delivers Chat Data", (0.35, 0.75)),
    ("Twitch Bot", "OpenAI API\n(Chat Completion)", "Sends Filtered Messages", (0.55, 0.7)),
    ("OpenAI API\n(Chat Completion)", "Twitch Bot", "Returns AI Responses", (0.7, 0.75)),
    ("Twitch Bot", "ElevenLabs API\n(Voice Generation)", "Sends Text for Voice", (0.65, 0.55)),
    ("ElevenLabs API\n(Voice Generation)", "Twitch Bot", "Returns Audio", (0.7, 0.5)),
    ("Twitch Bot", "Logging &\nChat Storage", "Logs Interactions", (0.8, 0.55)),
    ("Twitch Bot", ".env Configuration\nFile", "Loads Configuration", (0.4, 0.45)),
    ("Twitch Bot", "Prompt File", "Uses Prompts", (0.4, 0.35)),
    ("Twitch Bot", "Chat Log File", "Logs Interactions", (0.75, 0.45)),
    ("Twitch Bot", "Local Storage &\nLogging", "Stores Logs", (0.95, 0.45)),
    ("Twitch Bot", "Error Handling &\nDebugging", "Logs Errors", (0.5, 0.25)),
    (".env Configuration\nFile", "Twitch Bot", "Provides API Keys & Settings", (0.3, 0.35)),
    ("Prompt File", "Twitch Bot", "Provides Response Templates", (0.3, 0.25)),
    ("Chat Log File", "Local Storage &\nLogging", "Stores Logs", (0.8, 0.35))
]

# Draw connections with arrows and labels
for start, end, label, (lx, ly) in connections:
    start_comp = next(comp for comp in components if comp[0] == start)
    end_comp = next(comp for comp in components if comp[0] == end)
    start_x, start_y = start_comp[1]
    end_x, end_y = end_comp[1]

    # Calculate arrow start and end points
    dx = end_x - start_x
    dy = end_y - start_y
    distance = (dx**2 + dy**2)**0.5
    if distance == 0:
        distance = 1
    # Normalize
    dx_norm = dx / distance
    dy_norm = dy / distance
    # Adjust for rectangle size
    start_adj_x = start_x + dx_norm * rect_width / 2
    start_adj_y = start_y + dy_norm * rect_height / 2
    end_adj_x = end_x - dx_norm * rect_width / 2
    end_adj_y = end_y - dy_norm * rect_height / 2

    # Draw arrow
    arrow = Line2D([start_adj_x, end_adj_x], [start_adj_y, end_adj_y],
                   linewidth=1.5, color="black", linestyle="-", marker='>', markersize=8)
    ax.add_line(arrow)

    # Add label with a white background for better readability
    plt.text(lx, ly, label, ha="center", va="center", fontsize=8,
             bbox=dict(facecolor='white', edgecolor='none', pad=1))

# Add a title
plt.title("Twitch AI Interaction", fontsize=20, fontweight="bold")

# Save as Visio-compatible format
visio_path = "Twitch_Bot_Architecture_Diagram.svg"
fig.savefig(visio_path, format="svg", bbox_inches='tight')
plt.show()

# Output the path (for environments where file access is available)
visio_path
