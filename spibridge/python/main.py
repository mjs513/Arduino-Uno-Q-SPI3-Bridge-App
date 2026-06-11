import time
from datetime import datetime
import numpy as np
import spibridge
import struct
import schedule
import streamlit as st
import plotly.graph_objects as go
import base64
from io import BytesIO
import cv2

# -----------------------------
# SPI CONFIG
# -----------------------------
print(spibridge.config_speed(2000000))
print(spibridge.config_mode(0))
print(spibridge.config_bits(8))
print(spibridge.config_bytes_to_read(2048))

from collections import deque # Add this import if not present

# -----------------------------
# GLOBAL DATA + FLAGS
# -----------------------------
latest_lidar = None
latest_imu = None
latest_gps = None

lidar_ready = False
imu_ready = False
gps_ready = False

# NEW: Fixed-size history buffers (keeps the last 50 readings)
MAX_HISTORY = 50
imu_time_history = deque(maxlen=MAX_HISTORY)
yaw_history = deque(maxlen=MAX_HISTORY)
pitch_history = deque(maxlen=MAX_HISTORY)
roll_history = deque(maxlen=MAX_HISTORY)


def render_lidar_radar(angles, ranges):
    """
    Converts raw LIDAR arrays into a 2D top-down circular radar sweep.
    Renders cleanly inside OpenCV and returns a Plotly figure.
    """
    # Canvas Size Settings
    w, h = 450, 650
    cx, cy = w // 2, h // 2
    
    # Create empty black canvas background
    canvas = np.zeros((h, w, 3), dtype=np.uint8)
    
    # Scale setup: Map raw distance units to screen pixels
    # Adjust max_range (e.g., 20 meters or 2000 mm) to match your physical sensor
    max_range = 2000.0 if np.max(ranges) > 100 else 20.0
    scale_factor = (w // 2 - 20) / max_range

    # -----------------------------
    # RADAR GRID BACKGROUND
    # -----------------------------
    # Draw crosshair axes lines
    cv2.line(canvas, (0, cy), (w, cy), (35, 35, 35), 1)
    cv2.line(canvas, (cx, 0), (cx, h), (35, 35, 35), 1)
    
    # Draw standard circular range concentric rings (Quarter, Half, Max)
    for ratio in [0.25, 0.5, 0.75, 1.0]:
        r_px = int((w // 2 - 20) * ratio)
        cv2.circle(canvas, (cx, cy), r_px, (40, 50, 40), 1, cv2.LINE_AA)
        
        # Add quick text distance stamps
        dist_lbl = f"{int(max_range * ratio)}"
        tsize = cv2.getTextSize(dist_lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.3, 1)
        
        # FIXED: Added correct double index [0][0] to completely extract text width as an integer
        lbl_w = tsize[0][0]
        cv2.putText(canvas, dist_lbl, (cx + r_px - lbl_w - 4, cy - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (80, 100, 80), 1, cv2.LINE_AA)

    # -----------------------------
    # PLOT LIDAR POINT CLOUD DATA
    # -----------------------------
    # FIXED: Add pi/2 (90 degrees) to shift 0 degrees to point straight up
    rad_angles = np.radians(angles) + (np.pi / 2)
    
    # Filter out dead-zone noise readings or maximum out-of-bounds dropouts
    valid_mask = (ranges > 0.05) & (ranges <= max_range)
    v_ranges = ranges[valid_mask]
    v_angles = rad_angles[valid_mask]
    
    # Trigonometric map projection math
    xs = cx + (v_ranges * scale_factor * np.cos(v_angles)).astype(np.int32)
    ys = cy - (v_ranges * scale_factor * np.sin(v_angles)).astype(np.int32) # Invert Y for screen space

    # Safely draw valid hits onto the screen matrix canvas
    for x, y in zip(xs, ys):
        if 0 <= x < w and 0 <= y < h:
            # Bright neon green obstacle dots
            cv2.circle(canvas, (x, y), 2, (0, 255, 0), -1, cv2.LINE_AA)

    # Central vehicle platform reference icon indicator
    cv2.circle(canvas, (cx, cy), 5, (0, 0, 255), -1) # Red origin dot
    chv_poly = np.array([[cx, cy - 8], [cx - 5, cy + 6], [cx + 5, cy + 6]], np.int32)
    cv2.drawContours(canvas, [chv_poly], 0, (255, 255, 255), 1, cv2.LINE_AA)

    # -----------------------------
    # WRAP INTO PLOTLY FRAMEWORK
    # -----------------------------
    canvas_rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
    _, buffer = cv2.imencode(".png", canvas_rgb)
    encoded_image = base64.b64encode(buffer).decode("ascii")

    fig = go.Figure()
    fig.add_layout_image(
        dict(
            source="data:image/png;base64," + encoded_image,
            xref="x", yref="y",
            x=-200, y=200,
            sizex=400, sizey=400,
            xanchor="left", yanchor="top",
            layer="below"
        )
    )
    fig.update_layout(
        xaxis=dict(visible=False, range=[-200, 200]),
        yaxis=dict(visible=False, range=[-200, 200]),
        height=450,
        width=450,
        paper_bgcolor="black",
        plot_bgcolor="black",
        margin=dict(l=0, r=0, t=0, b=0)
    )
    return fig


def render_imu_timeline(times, yaws, pitches, rolls):
    """
    Generates a standard Plotly line chart plotting Yaw, Pitch, and Roll
    as a time-series graph layout.
    """
    fig = go.Figure()

    # Convert deques to standard lists for Plotly compatibility
    x_axis = list(times)

    # Add trace lines for each axis
    fig.add_trace(go.Scatter(x=x_axis, y=list(yaws), mode='lines+markers', name='Yaw (Heading)', line=dict(color='#00FFFF', width=2)))
    fig.add_trace(go.Scatter(x=x_axis, y=list(pitches), mode='lines', name='Pitch', line=dict(color='#FF00FF', width=2)))
    fig.add_trace(go.Scatter(x=x_axis, y=list(rolls), mode='lines', name='Roll', line=dict(color='#FFFF00', width=2)))

    fig.update_layout(
        title=dict(
            text="IMU Telemetry Timeline History",
            font=dict(color="white", size=16)  # High contrast white title
        ),
        xaxis=dict(
            title=dict(text="System Time stamp", font=dict(color="white")),  # White label
            tickfont=dict(color="#BBBBBB", size=10),  # Crisp gray time tags
            gridcolor="#333333"
        ),
        yaxis=dict(
            title=dict(text="Degrees (°)", font=dict(color="white")),  # White label
            tickfont=dict(color="#BBBBBB", size=12),  # Crisp gray angle values
            gridcolor="#333333"
        ),
        paper_bgcolor="black",
        plot_bgcolor="#151515",
        font=dict(color="white"),  # Global fallback text color
        height=500,
        margin=dict(l=50, r=40, t=50, b=50),
        legend=dict(
            orientation="h", 
            yanchor="bottom", y=1.02, 
            xanchor="right", x=1,
            font=dict(color="white")  # High contrast white legend keys
        )
    )
    return fig


def render_attitude_indicator(yaw, pitch, roll):
    """
    Renders a Garmin G1000-styled Attitude Indicator and Heading Tape.
    Draws everything inside OpenCV natively for maximum speed, 
    then wraps it in a Plotly graph to fit your current display system.
    """
    # 1. Canvas Settings
    w, h = 450, 450
    tape_h = 50  # Height of heading tape bar
    cx, cy = w // 2, (h - tape_h) // 2 + tape_h

    # Create empty black image canvas
    canvas = np.zeros((h, w, 3), dtype=np.uint8)

    # -----------------------------
    # G1000 PART 1: Horizon Background
    # -----------------------------
    pitch_scale = 4.0
    offset_y = int(pitch * pitch_scale)
    base_y = cy + offset_y

    angle_rad = np.radians(-roll)
    cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)

    def rotate_point(pt_x, pt_y, origin_x, origin_y):
        dx, dy = pt_x - origin_x, pt_y - origin_y
        rx = dx * cos_a - dy * sin_a + origin_x
        ry = dx * sin_a + dy * cos_a + origin_y
        return int(rx), int(ry)

    pt1_r = rotate_point(-w, base_y, cx, cy)
    pt2_r = rotate_point(2 * w, base_y, cx, cy)

    sky_color = (42, 80, 145)     # Deep Sky Blue 
    ground_color = (150, 70, 40)   # Horizon Ground Brown

    bg_layer = np.zeros_like(canvas)
    if abs(sin_a) > 0.001:
        pts_sky = np.array([[0, tape_h], [w, tape_h], pt2_r, pt1_r], np.int32)
        pts_ground = np.array([[0, h], [w, h], pt2_r, pt1_r], np.int32)
    else:
        clamped_y = max(tape_h, min(base_y, h))
        pts_sky = np.array([[0, tape_h], [w, tape_h], [w, clamped_y], [0, clamped_y]], np.int32)
        pts_ground = np.array([[0, clamped_y], [w, clamped_y], [w, h], [0, h]], np.int32)

    cv2.fillPoly(bg_layer, [pts_sky], sky_color)
    cv2.fillPoly(bg_layer, [pts_ground], ground_color)
    cv2.line(bg_layer, pt1_r, pt2_r, (255, 255, 255), 2)

    # -----------------------------
    # G1000 PART 2: Pitch Ladder Rings
    # -----------------------------
    pitch_marks = [-20, -10, -5, 5, 10, 20]
    for deg in pitch_marks:
        mark_y = int(cy + offset_y - (deg * pitch_scale))
        if tape_h < mark_y < h:
            l_pt1 = rotate_point(cx - 40, mark_y, cx, cy)
            l_pt2 = rotate_point(cx + 40, mark_y, cx, cy)
            
            cv2.line(bg_layer, l_pt1, l_pt2, (255, 255, 255), 1)
            
            text_p1 = rotate_point(cx - 60, mark_y + 4, cx, cy)
            text_p2 = rotate_point(cx + 45, mark_y + 4, cx, cy)
            cv2.putText(bg_layer, str(abs(deg)), text_p1, cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(bg_layer, str(abs(deg)), text_p2, cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)

    canvas[tape_h:] = bg_layer[tape_h:]

    # -----------------------------
    # G1000 Inward Roll Scale with Text Labels
    # -----------------------------
    arc_radius = 140
    roll_center_y = cy  

    cv2.ellipse(canvas, (cx, roll_center_y), (arc_radius, arc_radius), 0, -150, -30, (255, 255, 255), 2, cv2.LINE_AA)

    roll_ticks = [-60, -45, -30, -20, -10, 0, 10, 20, 30, 45, 60]
    for tick in roll_ticks:
        rad = np.radians(-90 + tick)
        x1 = int(cx + arc_radius * np.cos(rad))
        y1 = int(roll_center_y + arc_radius * np.sin(rad))
        
        tick_len = 14 if tick in [-60, -30, 0, 30, 60] else 8
        x2 = int(cx + (arc_radius - tick_len) * np.cos(rad))
        y2 = int(roll_center_y + (arc_radius - tick_len) * np.sin(rad))
        
        if y1 > tape_h and y2 > tape_h:
            cv2.line(canvas, (x1, y1), (x2, y2), (255, 255, 255), 2, cv2.LINE_AA)
            
            if tick in [-60, -30, 30, 60]:
                lbl_text = str(abs(tick))
                tsize = cv2.getTextSize(lbl_text, cv2.FONT_HERSHEY_SIMPLEX, 0.3, 1)
                # FIXED: Extracted deep inner width dimension directly using [0][0]
                lbl_w = tsize[0][0]
                xl = int(cx + (arc_radius + 15) * np.cos(rad)) - lbl_w // 2
                yl = int(roll_center_y + (arc_radius + 15) * np.sin(rad)) + tsize[0][1] // 2
                if yl > tape_h:
                    cv2.putText(canvas, lbl_text, (xl, yl), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (200, 200, 200), 1, cv2.LINE_AA)

    ptr_rad = np.radians(-90 + roll)
    px = cx + arc_radius * np.cos(ptr_rad)
    py = roll_center_y + arc_radius * np.sin(ptr_rad)

    perp_rad = ptr_rad + np.pi / 2
    p1_x = int(cx + (arc_radius - 12) * np.cos(ptr_rad) + 8 * np.cos(perp_rad))
    p1_y = int(roll_center_y + (arc_radius - 12) * np.sin(ptr_rad) + 8 * np.sin(perp_rad))
    p2_x = int(cx + (arc_radius - 12) * np.cos(ptr_rad) - 8 * np.cos(perp_rad))
    p2_y = int(roll_center_y + (arc_radius - 12) * np.sin(ptr_rad) - 8 * np.sin(perp_rad))
    p3_x = int(px)
    p3_y = int(py)

    if py > tape_h:
        roll_ptr_pts = np.array([[p1_x, p1_y], [p2_x, p2_y], [p3_x, p3_y]], np.int32)
        cv2.drawContours(canvas, [roll_ptr_pts], 0, (0, 255, 255), -1, cv2.LINE_AA)

    # -----------------------------
    # G1000 PART 3: Fixed Indicators
    # -----------------------------
    chv = 20
    cv2.line(canvas, (cx, cy), (cx - chv, cy + chv), (0, 255, 255), 3, cv2.LINE_AA)
    cv2.line(canvas, (cx, cy), (cx + chv, cy + chv), (0, 255, 255), 3, cv2.LINE_AA)
    cv2.line(canvas, (cx - chv, cy + chv), (cx - int(chv * 0.5), cy + chv), (0, 255, 255), 3, cv2.LINE_AA)
    cv2.line(canvas, (cx + chv, cy + chv), (cx + int(chv * 0.5), cy + chv), (0, 255, 255), 3, cv2.LINE_AA)
    cv2.circle(canvas, (cx, cy), 3, (0, 255, 255), -1)

    # -----------------------------
    # G1000 PART 4: Heading Tape
    # -----------------------------
    cv2.rectangle(canvas, (0, 0), (w, tape_h), (25, 25, 25), -1)
    cv2.line(canvas, (0, tape_h), (w, tape_h), (255, 255, 255), 2)

    px_per_deg = 3.0  
    view_range = int((w / px_per_deg) / 2) + 5
    norm_yaw = yaw % 360

    start_deg = int(norm_yaw - view_range)
    end_deg = int(norm_yaw + view_range)

    for deg in range(start_deg, end_deg + 1):
        display_deg = deg % 360
        if display_deg < 0:
            display_deg += 360

        tx = int(cx + (deg - norm_yaw) * px_per_deg)

        if 0 <= tx <= w:
            if display_deg == 0:   lbl = "N"
            elif display_deg == 90:  lbl = "E"
            elif display_deg == 180: lbl = "S"
            elif display_deg == 270: lbl = "W"
            elif display_deg % 10 == 0: lbl = f"{display_deg // 10:02d}"
            else: lbl = None

            if lbl:
                cv2.line(canvas, (tx, tape_h), (tx, tape_h - 14), (255, 255, 255), 1)
                col = (0, 255, 255) if lbl in ["N", "E", "S", "W"] else (255, 255, 255)
                tsize = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)
                # FIXED: Extracted deep inner width dimension directly using [0][0]
                text_w = tsize[0][0]
                cv2.putText(canvas, lbl, (tx - text_w // 2, tape_h - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.35, col, 1, cv2.LINE_AA)
            elif display_deg % 5 == 0:
                cv2.line(canvas, (tx, tape_h), (tx, tape_h - 10), (255, 255, 255), 1)
            elif display_deg % 1 == 0:
                cv2.line(canvas, (tx, tape_h), (tx, tape_h - 5), (180, 180, 180), 1)

    ptr_pts = np.array([[cx, tape_h], [cx - 6, tape_h - 8], [cx + 6, tape_h - 8]], np.int32)
    cv2.drawContours(canvas, [ptr_pts], 0, (0, 255, 255), -1)

    cv2.rectangle(canvas, (cx - 22, 4), (cx + 22, tape_h - 26), (0, 0, 0), -1)
    cv2.rectangle(canvas, (cx - 22, 4), (cx + 22, tape_h - 26), (0, 255, 255), 1)
    
    readout_str = f"{int(norm_yaw):03d}"
    r_size = cv2.getTextSize(readout_str, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
    # FIXED: Extracted deep inner width dimension directly using [0][0]
    readout_w = r_size[0][0]
    cv2.putText(canvas, readout_str, (cx - readout_w // 2, tape_h - 32), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255), 1, cv2.LINE_AA)

    # -----------------------------
    # Conversion into Plotly Graph
    # -----------------------------
    canvas_rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
    _, buffer = cv2.imencode(".png", canvas_rgb)
    encoded_image = base64.b64encode(buffer).decode("ascii")

    fig = go.Figure()
    fig.add_layout_image(
        dict(
            source="data:image/png;base64," + encoded_image,
            xref="x", yref="y",
            x=-200, y=200,
            sizex=400, sizey=400,
            xanchor="left", yanchor="top",
            layer="below"
        )
    )

    fig.update_layout(
        xaxis=dict(visible=False, range=[-200, 200]),
        yaxis=dict(visible=False, range=[-200, 200]),
        height=450,
        width=450,
        paper_bgcolor="black",
        plot_bgcolor="black",
        margin=dict(l=0, r=0, t=0, b=0)
    )

    return fig


# -----------------------------
# UTIL
# -----------------------------
def ts():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

# -----------------------------
# HEADER + FRAME
# -----------------------------
def read_header():
    hdr = bytes(spibridge.readBytes(n=9))
    if len(hdr) != 9 or hdr[0] != 0xAA:
        return 0xFF, 0, 0, 0
    return (
        hdr[1],
        int.from_bytes(hdr[2:4], "little"),
        int.from_bytes(hdr[4:8], "little"),
        hdr[8]
    )

def read_frame():
    data_type, block_size, total_size, block_count = read_header()
    if data_type == 0xFF:
        return 0xFF, b""

    blocks = []
    remaining = total_size

    for _ in range(block_count):
        chunk = min(block_size, remaining)
        blocks.append(bytes(spibridge.readBytes(n=chunk)))
        remaining -= chunk

    return data_type, b"".join(blocks)

# -----------------------------
# LIDAR
# -----------------------------
def read_lidar():
    global latest_lidar, lidar_ready

    spibridge.config_command("bytes", [0x1A])
    time.sleep(0.001)
    spibridge.readBytes(n=5)

    data_type, raw = read_frame()
    if data_type != 0x1A:
        return

    ints = struct.unpack("<1444i", raw)
    arr = np.array(ints, dtype=np.int32)

    latest_lidar = {
        "angle":   arr[0:361],
        "range":   arr[1083:1444],
        "timestamp": ts()
    }
    #print("NEW LIDAR:", latest_lidar["timestamp"])

    lidar_ready = True

# -----------------------------
# IMU
# -----------------------------
def read_imu():
    global latest_imu, imu_ready
    global imu_time_history, yaw_history, pitch_history, roll_history

    spibridge.config_command("bytes", [0x2A])
    time.sleep(0.001)
    spibridge.readBytes(n=5)

    data_type, raw = read_frame()
    if data_type != 0x2A:
        return

    yaw, pitch, roll = struct.unpack("<3f", raw)

    timestamp_str = ts()
    latest_imu = {
        "yaw": yaw,
        "pitch": pitch,
        "roll": roll,
        "timestamp": timestamp_str
    }

    # NEW: Append to rolling timeline data streams
    imu_time_history.append(timestamp_str)
    yaw_history.append(yaw)
    pitch_history.append(pitch)
    roll_history.append(roll)

    imu_ready = True


# -----------------------------
# GPS
# -----------------------------
def read_gps():
    global latest_gps, gps_ready

    spibridge.config_command("bytes", [0x3A])
    time.sleep(0.001)
    spibridge.readBytes(n=5)

    data_type, raw = read_frame()
    if data_type != 0x3A:
        return

    lat, lon, alt = struct.unpack("<ddfxxxx", raw)

    latest_gps = {
        "lat": lat,
        "lon": lon,
        "alt": alt,
        "timestamp": ts()
    }

    gps_ready = True

# -----------------------------
# SCHEDULING
# -----------------------------
schedule.every(0.25).seconds.do(read_lidar)
schedule.every(0.01).seconds.do(read_imu)
#schedule.every(1).seconds.do(read_gps)

# -----------------------------
# MAIN LOOP
# -----------------------------
def main():
    global lidar_ready, imu_ready, gps_ready

    st.set_page_config(layout="wide")
    st.title("Real-Time LIDAR + IMU Dashboard")

    if "frame" not in st.session_state:
        st.session_state.frame = 0
    
    # Row 1: LIDAR + Attitude Indicator
    col_lidar, col_att = st.columns([2, 2])
    lidar_plot = col_lidar.empty()
    att_plot = col_att.empty()

    # NEW ROW 2: Spans the full layout width right below Row 1
    st.markdown("---") # Visual separator line 
    timeline_plot = st.empty()

    #gps_box = col_gps.empty()

    while True:
        schedule.run_pending()
        
        # -----------------------------
        # RENDER LIDAR
        # -----------------------------
        #if lidar_ready and latest_lidar:
            # Call our newly added point cloud sweep calculation
        #    radar_fig = render_lidar_radar(
        #        angles=latest_lidar["angle"],
        #        ranges=latest_lidar["range"]
        #    )
            
            # Instantly refresh the left column block visual
        #    lidar_plot.plotly_chart(radar_fig, use_container_width=True, key=f"radar_{st.session_state.frame}")
        #    lidar_ready = False
        
        # -----------------------------
        # RENDER LIDAR
        # -----------------------------
        if lidar_ready and latest_lidar:
            angles = latest_lidar["angle"]
            ranges = latest_lidar["range"]
    
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=ranges,
                theta=angles,
                mode="lines",
                line=dict(color="cyan", width=2)
            ))
    
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(range=[0, int(max(ranges)) + 200]),
                    angularaxis=dict(direction="clockwise")
                ),
                showlegend=False,
                height=600
            )
    
            lidar_plot.plotly_chart(
                fig,
                #use_container_width=True,
                width='stretch',
                key=f"lidar_{st.session_state.frame}"
            )
    
            lidar_ready = False
            
        # -----------------------------
        # RENDER IMU + ATTITUDE INDICATOR
        # -----------------------------
        if imu_ready and latest_imu:
            yaw = latest_imu["yaw"]
            pitch = latest_imu["pitch"]
            roll = latest_imu["roll"]
    
   
            fig_att = render_attitude_indicator(yaw, pitch, roll)
    
            att_plot.plotly_chart(
                fig_att,
                #use_container_width=False,
                width='content',
                key=f"att_{st.session_state.frame}"
            )

            # 3. NEW: Generate and Update the Timeline History Chart below them
            if len(imu_time_history) > 1:
                history_fig = render_imu_timeline(
                    times=imu_time_history,
                    yaws=yaw_history,
                    pitches=pitch_history,
                    rolls=roll_history
                )
                timeline_plot.plotly_chart(history_fig, use_container_width=True, key=f"history_{st.session_state.frame}")

            imu_ready = False

        
        # -----------------------------
        # AUTO REFRESH
        # -----------------------------
        time.sleep(0.05)
        st.session_state.frame += 1
        #st.rerun()

if __name__ == "__main__":
    main()
