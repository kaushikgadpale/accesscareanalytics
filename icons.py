import streamlit as st
import base64
from config import THEME_CONFIG

def get_svg_icon(icon_path, color=THEME_CONFIG['DARK_COLOR'], width="24px", height="24px"):
    """Generate an SVG icon with custom styling"""
    svg_content = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        {icon_path}
    </svg>
    """
    return svg_content

def get_icon_html(icon_name, color=THEME_CONFIG['DARK_COLOR'], width="24px", height="24px", 
                 classes="", style=""):
    """Get HTML for a specific icon with styling"""
    icon_paths = {
        # Dashboard icons
        "dashboard": "M3 3h7v9H3V3zm11 0h7v5h-7V3zm0 9h7v9h-7v-9zm-11 4h7v5H3v-5z",
        "analytics": "M4 15h4v5H4v-5zm6-6h4v11h-4V9zm6-6h4v17h-4V3z",
        "chart": "M18 20V10m-6 10V4m-6 16v-6",
        
        # Calendar and appointments
        "calendar": "M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z",
        "clock": "M12 22a10 10 0 100-20 10 10 0 000 20zm0-18v8l4 4",
        "user": "M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2m8-10a4 4 0 100-8 4 4 0 000 8z",
        
        # Communication
        "phone": "M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 16.92z",
        "mail": "M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z M22 6l-10 7L2 6",
        "message": "M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10z",
        
        # Integrations
        "graph": "M12 12V3m0 9l-3 3m3-3l3 3M3 8h3V5M3 16h3v3M21 8h-3V5m3 11h-3v3",
        "airtable": "M4 4h16a2 2 0 012 2v12a2 2 0 01-2 2H4a2 2 0 01-2-2V6a2 2 0 012-2zm0 0v18",
        "link": "M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71 M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71",
        
        # Tools
        "tool": "M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z",
        "search": "M11 17.25a6.25 6.25 0 110-12.5 6.25 6.25 0 010 12.5z M16 16l4.5 4.5",
        "upload": "M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4 M17 8l-5-5-5 5 M12 3v12",
        
        # Content creation
        "document": "M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm-2 15H8m6-4H8m6-4H8",
        "template": "M21 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h6 M17 2l5 5-5 5 M12 7h10",
        "layout": "M19 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V5a2 2 0 00-2-2zm-9 15H5v-4h5v4zm9 0h-5v-4h5v4zm0-7H5V5h14v6z",
        
        # Navigation and misc
        "settings": "M12 15a3 3 0 100-6 3 3 0 000 6z M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z",
        "help": "M12 22a10 10 0 100-20 10 10 0 000 20z M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3 M12 17h.01",
        "alert": "M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z M12 9v4 M12 17h.01",
        "close": "M18 6L6 18M6 6l12 12",
        "check": "M20 6L9 17l-5-5",
        "refresh": "M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15",
        "edit": "M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7 M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z",
        "trash": "M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2",
        "info": "M12 22a10 10 0 100-20 10 10 0 000 20z M12 16v-4 M12 8h.01",
        "home": "M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z",
        "book": "M4 19.5A2.5 2.5 0 016.5 17H20M4 19.5A2.5 2.5 0 016.5 17H20M4 19.5V4a2 2 0 012-2h6.5M20 8V4a2 2 0 00-2-2h-.5"
    }
    
    if icon_name not in icon_paths:
        icon_name = "alert"  # Default to alert icon if not found
    
    icon_svg = get_svg_icon(icon_paths[icon_name], color, width, height)
    
    # Base64 encode the SVG content
    base64_svg = base64.b64encode(icon_svg.encode('utf-8')).decode('utf-8')
    
    # Create the HTML with classes and style
    icon_html = f'<img src="data:image/svg+xml;base64,{base64_svg}" class="{classes}" style="{style}" alt="{icon_name} icon">'
    
    return icon_html

def render_tab_bar(tabs, active_tab=None, callback=None):
    """Render a custom tab bar with icons"""
    cols = st.columns(len(tabs))
    
    for i, (tab_id, tab_info) in enumerate(tabs.items()):
        is_active = active_tab == tab_id
        tab_color = THEME_CONFIG['ACCENT_COLOR'] if is_active else THEME_CONFIG['DARK_COLOR']
        
        # Create the tab with label and icon displayed in the button
        with cols[i]:
            # Create a unique key for the button to ensure it works properly
            button_key = f"tab_{tab_id}_{i}"
            
            # Get icon HTML to put before the button (can't put HTML in button directly)
            icon_html = get_icon_html(tab_info['icon'], tab_color, "16px", "16px")
            st.markdown(f"<div style='text-align: center; height: 20px;'>{icon_html}</div>", unsafe_allow_html=True)
            
            # Create the actual button with proper label for accessibility
            button_label = tab_info.get('label', tab_id.capitalize())
            
            if st.button(
                button_label,
                key=button_key,
                use_container_width=True
            ):
                active_tab = tab_id
                if callback:
                    callback(tab_id)
    
    # Add a separator line
    st.markdown(f'<div style="height: 1px; background-color: #e5e7eb; margin-bottom: 20px;"></div>', 
                unsafe_allow_html=True)
    
    return active_tab

def render_icon(icon_name, color=None, width="24px", height="24px", tooltip=""):
    """Render an icon with optional tooltip"""
    if color is None:
        color = THEME_CONFIG['DARK_COLOR']
        
    icon_html = get_icon_html(icon_name, color, width, height)
    
    # Remove tooltip functionality as requested
    st.markdown(icon_html, unsafe_allow_html=True)

def render_empty_state(message, icon_name=None, action_button=None):
    """Render an empty state with icon and optional action button"""
    if icon_name is None:
        icon_name = "alert"
        
    empty_state_html = f"""
    <div class="empty-state">
        <div class="empty-state-icon">
            {get_icon_html(icon_name, THEME_CONFIG['LIGHT_COLOR'], "60px", "60px")}
        </div>
        <div class="empty-state-text">
            {message}
        </div>
    </div>
    """
    
    st.markdown(empty_state_html, unsafe_allow_html=True)
    
    if action_button:
        st.button(action_button)

def render_info_box(message, box_type="info"):
    """Render an info/warning/error box with an icon"""
    icon_map = {
        "info": "info",
        "warning": "alert",
        "error": "alert",
        "success": "check"
    }
    
    color_map = {
        "info": THEME_CONFIG['PRIMARY_COLOR'],
        "warning": THEME_CONFIG['WARNING_COLOR'],
        "error": THEME_CONFIG['DANGER_COLOR'],
        "success": THEME_CONFIG['SUCCESS_COLOR']
    }
    
    icon = icon_map.get(box_type, "info")
    color = color_map.get(box_type, THEME_CONFIG['PRIMARY_COLOR'])
    
    box_html = f"""
    <div class="{box_type}-box">
        <div style="display: flex; align-items: flex-start;">
            <div style="margin-right: 10px;">
                {get_icon_html(icon, color)}
            </div>
            <div>
                {message}
            </div>
        </div>
    </div>
    """
    
    st.markdown(box_html, unsafe_allow_html=True)

def get_logo_base64():
    """Generate a simple logo with initials ACA in SVG format and return as base64"""
    svg_logo = """<svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        <rect width="100" height="100" rx="10" fill="#f8fafc"/>
        <text x="50" y="60" font-family="Arial, sans-serif" font-size="36" font-weight="bold" fill="#1f2937" text-anchor="middle">ACA</text>
        <path d="M20 80 L80 80" stroke="#7c3aed" stroke-width="4" stroke-linecap="round"/>
        <path d="M30 70 L70 70" stroke="#6b7280" stroke-width="4" stroke-linecap="round"/>
    </svg>"""
    
    # Base64 encode the SVG content
    base64_logo = base64.b64encode(svg_logo.encode('utf-8')).decode('utf-8')
    return base64_logo

def render_logo(width="100px"):
    """Render the application logo"""
    base64_logo = get_logo_base64()
    logo_html = f'<img src="data:image/svg+xml;base64,{base64_logo}" width="{width}" alt="Access Care Analytics Logo">'
    return logo_html 