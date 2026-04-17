import py3dbp
from py3dbp import Packer, Bin, Item
import plotly.graph_objects as go
import time
import streamlit as st
import random
import sys
import math

from config import PACKING_TIMEOUT_SECONDS

def run_3d_packing(items, armada_specs, timeout=PACKING_TIMEOUT_SECONDS):
    """
    items: list of dicts with keys 'Item_Name', 'Length', 'Height', 'Width', 'Weight', 'Qty'
    armada_specs: dict with 'Length_cm', 'Height_cm', 'Width_cm', 'Max_Tonase_Kg', 'Safety_Factor'
    """
    packer = Packer()
    
    sf = armada_specs.get("Safety_Factor", 1.0)
    # Adjust bins by cubic root of safety factor
    dim_adjust = sf ** (1/3)
    
    bin_l = float(armada_specs["Length_cm"] * dim_adjust)
    bin_h = float(armada_specs["Height_cm"] * dim_adjust)
    bin_w = float(armada_specs["Width_cm"] * dim_adjust)
    bin_weight = float(armada_specs["Max_Tonase_Kg"] * sf)
    
    packer.add_bin(Bin('Armada', bin_l, bin_h, bin_w, bin_weight))
    
    total_qty = 0
    for item in items:
        qty = int(item['Qty'])
        total_qty += qty
        
    total_qty = 0
    for item in items:
        qty = int(item['Qty'])
        total_qty += qty
        
        # Aggressive Optimization: Always target ~15-20 virtual blocks per SKU
        # This keeps the total number of items handled by py3dbp small and fast.
        group_size = max(1, qty // 15)
        
        # Ensure the bundled length doesn't exceed the bin length or width
        # We group along the longest dimension of the item to be efficient
        if (item['Length'] * group_size) > bin_l:
            group_size = 1
            
        num_groups = qty // group_size
        remainder = qty % group_size
        
        # Add Bundled blocks (as single items to the packer)
        for i in range(num_groups):
            packer.add_item(Item(
                f"{item['Item_Name']}_G{i}", 
                float(item['Length'] * group_size), 
                float(item['Height']), 
                float(item['Width']), 
                float(item['Weight'] * group_size)
            ))
            
        # Add Remainders (individual boxes)
        for i in range(remainder):
            packer.add_item(Item(
                f"{item['Item_Name']}_R{i}", 
                float(item['Length']), 
                float(item['Height']), 
                float(item['Width']), 
                float(item['Weight'])
            ))
            
    start_time = time.time()
    fitted_items = 0
    
    # We will use simple timeout by running packer.pack(), but py3dbp doesn't support built-in timeout,
    # so we'll wrap it or just hope it doesn't hang. Actually py3dbp is usually fast for small number of items.
    b = None
    try:
        packer.pack()
        b = packer.bins[0]
        fitted_items = len(b.items)
        unfitted_items = len(b.unfitted_items)
        success = True
    except Exception as e:
        st.warning(f"⚠️ 3D packing error: {str(e)}. Menggunakan kalkulasi volume.")
        fitted_items = 0
        unfitted_items = total_qty
        success = False
        
    return {
        "success": success,
        "fitted": fitted_items,
        "total": total_qty,
        "unfitted": total_qty - fitted_items,
        "bin": b
    }

def generate_colors(n):
    colors = []
    for _ in range(n):
        colors.append(f"rgb({random.randint(50, 200)}, {random.randint(50, 200)}, {random.randint(50, 200)})")
    return colors

def draw_2d_floor_plan(items, armada_specs, title="Visualisasi Lantai Armada"):
    """
    Simple 2D shelf packing for visualization
    items: list of dicts with 'Item_Name', 'Length', 'Width', 'Qty'
    """
    bin_width = armada_specs["Width_cm"]
    bin_length = armada_specs["Length_cm"]
    
    fig = go.Figure()
    
    # Draw bin outline
    fig.add_shape(type="rect",
        x0=0, y0=0, x1=bin_width, y1=bin_length,
        line=dict(color="black", width=3),
        fillcolor="rgba(0,0,0,0)"
    )
    
    # Shelf algorithm
    x, y = 0, 0
    current_row_length = 0
    
    color_map = {}
    
    # Sort items by width (as proxy for best fit in a row)
    flat_items = []
    for it in items:
        for _ in range(int(it['Qty'])):
            flat_items.append(it)
            
    flat_items.sort(key=lambda x: max(x['Length'], x['Width']), reverse=True)
    
    for it in flat_items:
        if it['Item_Name'] not in color_map:
            color_map[it['Item_Name']] = f"rgb({random.randint(100, 250)}, {random.randint(100, 250)}, {random.randint(100, 250)})"
            
        w, l = it['Width'], it['Length']
        
        # If it doesn't fit in current row, move to next
        if x + w > bin_width:
            x = 0
            y += current_row_length
            current_row_length = 0
            
        # If it doesn't fit in the remaining length, skip visualization (overflow)
        if y + l > bin_length:
            continue
            
        # Draw rectangle
        fig.add_shape(type="rect",
            x0=x, y0=y, x1=x+w, y1=y+l,
            line=dict(color="white", width=1),
            fillcolor=color_map[it['Item_Name']]
        )
        
        # Add text if it's large enough
        if w > 20 and l > 20:
            fig.add_annotation(
                x=x+w/2, y=y+l/2,
                text=it['Item_Name'][:10] + ".." if len(it['Item_Name']) > 10 else it['Item_Name'],
                showarrow=False,
                font=dict(color="black", size=9)
            )
            
        x += w
        current_row_length = max(current_row_length, l)
        
    fig.update_layout(
        title=title,
        xaxis=dict(title="Width (cm)", range=[0, bin_width + 10]),
        yaxis=dict(title="Length (cm)", range=[0, bin_length + 10]),
        width=500, height=600,
        showlegend=False
    )
    # Set y axis reversed if we want to build from top to bottom, but bottom to top is fine
    fig.update_yaxes(autorange="reversed")
    
    return fig

def draw_3d_packing_bin(bin_obj, armada_specs, title="Visualisasi Layout 3D"):    
    fig = go.Figure()

    if not bin_obj or not bin_obj.items:
        fig.update_layout(title="Tidak ada barang untuk ditampilkan")
        return fig

    # Get bin limits
    w = bin_obj.width
    h = bin_obj.height
    d = bin_obj.depth

    color_map = {}

    for item in bin_obj.items:
        base_name = item.name.rsplit('_', 1)[0]
        if base_name not in color_map:
            color_map[base_name] = f"rgb({random.randint(50, 240)}, {random.randint(50, 240)}, {random.randint(50, 240)})"
            
        x, y, z = item.position
        dx, dy, dz = item.get_dimension()
        
        # A 3D box has 8 vertices
        x_c = [x, x+dx, x+dx, x, x, x+dx, x+dx, x]
        y_c = [y, y, y+dy, y+dy, y, y, y+dy, y+dy]
        z_c = [z, z, z, z, z+dz, z+dz, z+dz, z+dz]

        i_pts = [7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2]
        j_pts = [3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3]
        k_pts = [0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6]

        fig.add_trace(go.Mesh3d(
            x=x_c, y=y_c, z=z_c,
            i=i_pts, j=j_pts, k=k_pts,
            opacity=0.8,
            color=color_map[base_name],
            flatshading=True,
            name=base_name,
            hoverinfo="name",
            showlegend=False
        ))

    # Add truck frame via Scatter3d lines to give spatial boundary references
    frame_x = [0, w, w, 0, 0, 0, w, w, 0, 0, w, w, w, w, 0, 0]
    frame_y = [0, 0, h, h, 0, 0, 0, h, h, 0, 0, 0, h, h, h, h]
    frame_z = [0, 0, 0, 0, 0, d, d, d, d, d, d, 0, 0, d, d, 0]
    
    fig.add_trace(go.Scatter3d(
        x=frame_x, y=frame_y, z=frame_z,
        mode='lines',
        line=dict(color='black', width=4),
        name='Batas Armada',
        hoverinfo='skip'
    ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(title='Width', range=[0, w+20]),
            yaxis=dict(title='Height', range=[0, h+20]),
            zaxis=dict(title='Depth / Length', range=[0, d+20]),
            aspectmode='data'
        ),
        title=title,
        height=600,
        margin=dict(r=10, l=10, b=10, t=50)
    )
    return fig
