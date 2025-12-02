import streamlit as st
import math
import pandas as pd
import matplotlib.pyplot as pd_plt
import matplotlib.patches as patches

# ==========================================
# PART 1: THE ENGINE (Your Logic)
# ==========================================

# 1. DATA BANK
COEFF_DATA_SHORT = {
    1.0: [0.024, 0.028, 0.028, 0.033, 0.032, 0.033, 0.040, 0.038, 0.048],
    1.1: [0.028, 0.032, 0.032, 0.037, 0.035, 0.040, 0.046, 0.043, 0.056],
    1.2: [0.033, 0.036, 0.037, 0.042, 0.039, 0.047, 0.052, 0.048, 0.064],
    1.3: [0.036, 0.039, 0.041, 0.046, 0.043, 0.053, 0.057, 0.052, 0.071],
    1.4: [0.039, 0.042, 0.044, 0.050, 0.045, 0.059, 0.062, 0.056, 0.077],
    1.5: [0.041, 0.045, 0.048, 0.053, 0.048, 0.064, 0.066, 0.059, 0.083],
    1.75: [0.045, 0.049, 0.055, 0.059, 0.052, 0.073, 0.075, 0.065, 0.093],
    2.0: [0.048, 0.052, 0.063, 0.065, 0.055, 0.082, 0.083, 0.070, 0.103]
}
COEFF_DATA_LONG = [0.024, 0.024, 0.028, 0.028, 0.024, 0.033, 0.033, 0.028, 0.048]

PANEL_TYPES = [
    "Interior Panel", "One Short Edge Discontinuous", "One Long Edge Discontinuous",
    "Two Adjacent Edges Discontinuous", "Two Short Edges Discontinuous", 
    "Two Long Edges Discontinuous", "Three Edges Discontinuous (1 Long Cont)",
    "Three Edges Discontinuous (1 Short Cont)", "Four Edges Discontinuous"
]

BAR_AREAS_SINGLE = {8: 50.3, 10: 78.5, 12: 113.1, 16: 201.1, 20: 314.2}
STANDARD_SPACINGS = [75, 100, 125, 150, 175, 200, 250, 300]

# 2. LOGIC FUNCTIONS
def get_short_coefficient(ratio, panel_index):
    ratio = min(ratio, 2.0)
    table_ratios = sorted(COEFF_DATA_SHORT.keys())
    if ratio in COEFF_DATA_SHORT: return COEFF_DATA_SHORT[ratio][panel_index]
    lower_r = max([r for r in table_ratios if r < ratio])
    upper_r = min([r for r in table_ratios if r > ratio])
    lower_val = COEFF_DATA_SHORT[lower_r][panel_index]
    upper_val = COEFF_DATA_SHORT[upper_r][panel_index]
    return round(lower_val + (ratio - lower_r) * (upper_val - lower_val) / (upper_r - lower_r), 4)

def check_edge_continuity(panel_index, direction):
    p_name = PANEL_TYPES[panel_index]
    if direction == "Short Span Support":
        if p_name in ["Two Long Edges Discontinuous", "Four Edges Discontinuous", "Three Edges Discontinuous (1 Short Cont)"]:
            return False 
    if direction == "Long Span Support":
        if p_name in ["Two Short Edges Discontinuous", "Four Edges Discontinuous", "Three Edges Discontinuous (1 Long Cont)"]:
            return False 
    return True

def get_bar_provision_details(as_required, bar_dia):
    area_one_bar = BAR_AREAS_SINGLE[bar_dia]
    selected_spacing = 0
    area_prov_val = 0
    for spacing in reversed(STANDARD_SPACINGS):
        area_provided = (1000 / spacing) * area_one_bar
        if area_provided >= as_required:
            selected_spacing = spacing
            area_prov_val = area_provided
            break 
    if selected_spacing == 0:
        return {"text": "FAIL: Increase Bar", "area_prov": 0, "spacing": 0}
    return {"text": f"Y{bar_dia} @ {selected_spacing}", "area_prov": area_prov_val, "spacing": selected_spacing}

def check_deflection(Lx, d, fck, As_req, As_prov, panel_index):
    if As_req <= 0: return {"status": "N/A", "actual": 0, "allowable": 0}
    p_name = PANEL_TYPES[panel_index]
    K = 1.0 if p_name == "Four Edges Discontinuous" else (1.5 if p_name == "Interior Panel" else 1.3)
    rho = As_req / (1000 * d)
    rho_0 = math.sqrt(fck) * 0.001
    if rho <= rho_0:
        basic = K * (11 + 1.5 * math.sqrt(fck) * (rho_0/rho))
    else:
        basic = K * (11 + 1.5 * math.sqrt(fck) * (rho_0/rho) + 3.2 * math.sqrt(fck) * ((rho_0/rho) - 1)**1.5)
    factor = min(1.5, (500/460) * (As_prov / As_req))
    allowable = basic * factor
    if Lx > 7000: allowable *= (7000/Lx)
    actual = Lx / d
    return {"actual": round(actual, 2), "allowable": round(allowable, 2), "status": "PASS" if actual <= allowable else "FAIL"}

def check_shear(n, Lx, d, fck, As_prov):
    V_Ed = 0.5 * n * (Lx / 1000)
    k = min(1 + math.sqrt(200 / d), 2.0)
    rho_l = min(As_prov / (1000 * d), 0.02)
    v_min = 0.035 * (k**1.5) * (fck**0.5)
    val_1 = (0.12) * k * (100 * rho_l * fck)**(1/3)
    V_Rdc = max(val_1, v_min) * 1000 * d / 1000
    return {"V_Ed": round(V_Ed, 2), "V_Rdc": round(V_Rdc, 2), "status": "PASS" if V_Ed <= V_Rdc else "FAIL", "utilization": round(V_Ed/V_Rdc*100, 1)}

def draw_slab_diagram(Lx, Ly, prov_sx, prov_sy):
    """
    Draws a visual representation of the slab with reinforcement.
    Lx, Ly: Slab dimensions (mm)
    prov_sx, prov_sy: Dictionary with 'text' provision for X and Y directions
    """
    
    # Create Figure
    fig, ax = pd_plt.subplots(figsize=(6, 5))
    
    # Draw Slab Rectangle
    # Convert mm to m for plotting scale
    width = Lx / 1000
    height = Ly / 1000
    
    slab_rect = patches.Rectangle((0, 0), width, height, linewidth=2, edgecolor='black', facecolor='#f0f2f6')
    ax.add_patch(slab_rect)
    
    # Draw Short Span Reinforcement (Horizontal Lines distributed vertically)
    # These represent bars running PARALLEL to Lx (Short Span)
    # Actually, main bars for short span moment run PARALLEL to Lx, so they are drawn horizontal.
    # Wait - Structural check:
    # Short Span moment (Msx) is resisted by bars running ALONG the short span (Lx).
    # So lines should be horizontal (y=constant).
    
    # Visualizing 'Main' bars (Red) - Short Span
    ax.text(width/2, height*0.1, f"Main: {prov_sx['text']}", color='red', ha='center', fontweight='bold')
    # Draw a few sample lines
    y_positions = [height * 0.3, height * 0.5, height * 0.7]
    for y in y_positions:
        ax.plot([0.1*width, 0.9*width], [y, y], color='red', linewidth=2, linestyle='-')
        
    # Draw Long Span Reinforcement (Vertical Lines distributed horizontally)
    # These run PARALLEL to Ly
    
    # Visualizing 'Secondary' bars (Blue) - Long Span
    ax.text(width*0.1, height/2, f"Sec: {prov_sy['text']}", color='blue', rotation=90, va='center', fontweight='bold')
    # Draw a few sample lines
    x_positions = [width * 0.3, width * 0.5, width * 0.7]
    for x in x_positions:
        ax.plot([x, x], [0.1*height, 0.9*height], color='blue', linewidth=2, linestyle='--')

    # Set Chart Properties
    ax.set_xlim(-0.5, width + 0.5)
    ax.set_ylim(-0.5, height + 0.5)
    ax.set_aspect('equal')
    ax.axis('off') # Hide axes numbers
    ax.set_title(f"Slab Plan View ({int(Lx)}mm x {int(Ly)}mm)", fontsize=12)
    
    return fig

# ==========================================
# PART 2: THE INTERFACE (Streamlit)
# ==========================================

st.set_page_config(page_title="Slab Design Pro", page_icon="🏗️")

st.title("🏗️ Eurocode 2 Slab Designer")
st.markdown("Designed for Nigerian/British Standards (BS 8110 / EC2)")

# --- SIDEBAR INPUTS ---
st.sidebar.header("1. Material Properties")
fck = st.sidebar.selectbox("Concrete Grade (fck)", [20, 25, 30, 35, 40], index=1)
fyk = st.sidebar.number_input("Steel Yield (fyk)", value=460)
cover = st.sidebar.number_input("Nominal Cover (mm)", value=25)
bar_dia = st.sidebar.selectbox("Preferred Bar Diameter", [8, 10, 12, 16, 20], index=2)

st.sidebar.header("2. Geometry")
Lx = st.sidebar.number_input("Short Span Lx (mm)", value=3000)
Ly = st.sidebar.number_input("Long Span Ly (mm)", value=5000)
h = st.sidebar.number_input("Slab Thickness (mm)", value=150)

st.sidebar.header("3. Loading")
Gk = st.sidebar.number_input("Dead Load Gk (kN/m²)", value=6.45)
Qk = st.sidebar.number_input("Live Load Qk (kN/m²)", value=1.5)

st.header("Panel Configuration")
panel_type = st.selectbox("Select Panel Boundary Condition", PANEL_TYPES)
panel_index = PANEL_TYPES.index(panel_type)

# --- CALCULATE BUTTON ---
if st.button("Calculate Design"):
    
    # 1. PRE-CALCULATIONS
    ratio = round(Ly/Lx, 2)
    n = 1.35*Gk + 1.5*Qk
    st.info(f"**Design Load (n):** {round(n, 2)} kN/m²  |  **Ratio:** {ratio}")
    
    if ratio > 2.0:
        st.warning("⚠️ Ratio > 2.0. This is technically a One-Way Slab.")

    # 2. COEFFICIENTS & MOMENTS
    Bsx_mid = get_short_coefficient(ratio, panel_index)
    Bsy_mid = COEFF_DATA_LONG[panel_index]
    
    Bsx_sup = 1.33 * Bsx_mid if check_edge_continuity(panel_index, "Short Span Support") else 0.0
    Bsy_sup = 1.33 * Bsy_mid if check_edge_continuity(panel_index, "Long Span Support") else 0.0

    Msx_mid = Bsx_mid * n * (Lx/1000)**2
    Msy_mid = Bsy_mid * n * (Lx/1000)**2
    Msx_sup = Bsx_sup * n * (Lx/1000)**2
    Msy_sup = Bsy_sup * n * (Lx/1000)**2

    # 3. STEEL AREAS
    dx = h - cover - (bar_dia/2)
    dy = h - cover - bar_dia - (bar_dia/2)
    fctm = 0.3 * (fck**(2/3))
    As_min = max(0.26 * (fctm/fyk) * 1000 * dx, 0.0013 * 1000 * dx)

    # Function to Process Results
    def process_result(M, eff_d):
        if M == 0: return 0, As_min, get_bar_provision_details(As_min, bar_dia)
        K = (M * 10**6) / (1000 * eff_d**2 * fck)
        if K > 0.167: return 9999, 0, {"text": "FAIL (K>0.167)", "area_prov": 0, "spacing": 0}
        z = min(eff_d * (0.5 + math.sqrt(0.25 - K/1.134)), 0.95*eff_d)
        req = (M * 10**6) / (0.87 * fyk * z)
        target = max(req, As_min)
        return req, target, get_bar_provision_details(target, bar_dia)

    # Calculate
    req_sx, targ_sx, prov_sx = process_result(Msx_mid, dx)
    req_sy, targ_sy, prov_sy = process_result(Msy_mid, dy)
    req_sx_sup, targ_sx_sup, prov_sx_sup = process_result(Msx_sup, dx)
    req_sy_sup, targ_sy_sup, prov_sy_sup = process_result(Msy_sup, dy)

    # 4. DISPLAY RESULTS (The "SkyCiv" Style Table)
    st.subheader("Reinforcement Schedule")
    
    res_data = []
    
    # Midspan Logic
    if targ_sx >= targ_sy:
        res_data.append(["Midspan", "MAIN", "Short (Lx)", f"{int(targ_sx)}", prov_sx['text']])
        res_data.append(["Midspan", "SECONDARY", "Long (Ly)", f"{int(targ_sy)}", prov_sy['text']])
        main_mid_prov = prov_sx
        sec_mid_prov = prov_sy
    else:
        res_data.append(["Midspan", "MAIN", "Long (Ly)", f"{int(targ_sy)}", prov_sy['text']])
        res_data.append(["Midspan", "SECONDARY", "Short (Lx)", f"{int(targ_sx)}", prov_sx['text']])
        main_mid_prov = prov_sy
        sec_mid_prov = prov_sx

    # Support Logic
    if targ_sx_sup >= targ_sy_sup:
        res_data.append(["Support", "MAIN", "Short (Lx)", f"{int(targ_sx_sup)}", prov_sx_sup['text']])
        res_data.append(["Support", "SECONDARY", "Long (Ly)", f"{int(targ_sy_sup)}", prov_sy_sup['text']])
    else:
        res_data.append(["Support", "MAIN", "Long (Ly)", f"{int(targ_sy_sup)}", prov_sy_sup['text']])
        res_data.append(["Support", "SECONDARY", "Short (Lx)", f"{int(targ_sx_sup)}", prov_sx_sup['text']])

    df_res = pd.DataFrame(res_data, columns=["Location", "Role", "Direction", "Area Req (mm²)", "Provision"])
    st.table(df_res)

    # 5. VISUALIZATION (New!)
    st.subheader("Slab Layout")
    st.write("Visual representation of Midspan Reinforcement:")
    # We pass the provisions for Lx (Short Span) and Ly (Long Span) specifically
    fig = draw_slab_diagram(Lx, Ly, prov_sx, prov_sy)
    st.pyplot(fig)

    # 6. CHECKS
    st.subheader("Design Checks")
    col1, col2 = st.columns(2)

    # Deflection
    check_val = max(req_sx, As_min)
    defl = check_deflection(Lx, dx, fck, check_val, prov_sx['area_prov'], panel_index)
    
    with col1:
        if defl['status'] == "PASS":
            st.success(f"**Deflection: PASS**")
        else:
            st.error(f"**Deflection: FAIL**")
        st.write(f"Actual L/d: {defl['actual']}")
        st.write(f"Allowable: {defl['allowable']}")

    # Shear
    shear_steel = prov_sx_sup['area_prov'] if targ_sx_sup > targ_sy_sup else prov_sy_sup['area_prov']
    sh_res = check_shear(n, Lx, dx, fck, shear_steel)
    
    with col2:
        if sh_res['status'] == "PASS":
            st.success(f"**Shear: PASS**")
        else:
            st.error(f"**Shear: FAIL**")
        st.write(f"V_Ed: {sh_res['V_Ed']} kN")
        st.write(f"V_Rdc: {sh_res['V_Rdc']} kN")
        st.progress(min(sh_res['utilization']/100, 1.0), text=f"Utilization: {sh_res['utilization']}%")
