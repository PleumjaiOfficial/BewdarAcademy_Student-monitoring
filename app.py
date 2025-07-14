import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Set page config
st.set_page_config(
    page_title="Student Performance Tracker",
    page_icon="📊",
    layout="wide"
)

# Title and description

# Header
st.image("bd-logo.png", width=2000)  # ใส่ชื่อไฟล์และกำหนดขนาด
st.title("Bewdar Academy Lamphun: Student Monitoring")
st.markdown("### ระบบติดตามผลการเรียนของนักเรียนสำหรับคุณครู")
st.markdown("---")

@st.cache_data
def load_google_sheet_by_id(spreadsheet_id: str, worksheet_name: str) -> pd.DataFrame:
    """โหลดข้อมูลจาก Google Sheet ด้วย Spreadsheet ID และชื่อ Worksheet"""
    try:
        # Define scope
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        # Authorize using credentials from secrets.toml
        gcp_credentials = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(gcp_credentials, scope)
        client = gspread.authorize(creds)

        # Load the specific sheet and worksheet
        sheet = client.open_by_key(spreadsheet_id)
        worksheet = sheet.worksheet(worksheet_name)

        # Read data
        records = worksheet.get_all_records()
        df = pd.DataFrame(records)
        return df

    except Exception as e:
        st.error(f"❌ Error loading data from Google Sheets: {e}")
        return pd.DataFrame()
    
# Function to create the performance plot
def plot_classroom_cluster(df, focus_on):
    """Interactive Scatter Plot (Plotly) แสดง STEM vs Language พร้อม Zoning และ Cluster ถ้ามี"""
    
    tier_colors = {
        'Diamond': "#00ff2f",
        'Platinum': "#8e44ad",
        'Gold': "#f1c40f",
        'Silver': "#5dade2",
        'Bronze': "#c0392b"
    }

    zones = [
        (0, 50, 0, 50, "Warning Zone", "#f9ebea"),
        (0, 50, 50, 80, "STEM Support", "#fef9e7"),
        (0, 50, 80, 100, "Language Expert", "#eafaf1"),
        (50, 80, 0, 50, "Language Support", "#fef5e7"),
        (50, 80, 50, 80, "Development Zone", "#e8f8f5"),
        (80, 100, 0, 50, "STEM Expert", "#f4ecf7"),
        (80, 100, 50, 80, "STEM Strong", "#e8daef"),
        (50, 80, 80, 100, "Language Strong", "#eaf2f8"),
        (80, 100, 80, 100, "Perfect Zone", "#d4efdf")
    ]

    fig = go.Figure()

    # วาด zoning พื้นหลัง
    for xmin, xmax, ymin, ymax, label, color in zones:
        fig.add_shape(
            type="rect",
            x0=xmin, x1=xmax,
            y0=ymin, y1=ymax,
            fillcolor=color,
            opacity=0.3,
            line_width=0
        )
        fig.add_annotation(
            x=(xmin + xmax)/2,
            y=(ymin + ymax)/2,
            text=label,
            showarrow=False,
            font=dict(size=10, color="black")
        )

    # ตรวจสอบว่ามี column TIER และมีค่าไม่ใช่ NaN หรือไม่
    use_tier = f'TIER_{focus_on}' in df.columns and df[f'TIER_{focus_on}'].notna().sum() > 0

    if use_tier:
        # วาดตาม tier
        for tier, group in df.groupby(f'TIER_{focus_on}'):
            fig.add_trace(go.Scatter(
                x=group['STEM_AVG'],
                y=group['LANGUAGE_AVG'],
                mode='markers+text',
                name=tier,
                marker=dict(
                    size=20,
                    color=tier_colors.get(tier, "#888888"),
                    symbol='diamond',
                    line=dict(width=1, color='white')
                ),
                text=group['PERSON_ID'],
                textposition='top center',
                textfont=dict(color='black', size=10)
            ))
    else:
        # ไม่มี tier — วาดแบบปกติ
        fig.add_trace(go.Scatter(
            x=df['STEM_AVG'],
            y=df['LANGUAGE_AVG'],
            mode='markers+text',
            name="Students",
            marker=dict(
                color='red',
                size=20,
                symbol='diamond',
                line=dict(width=1, color='white')
            ),
            text=df['PERSON_ID'],
            textposition='top center',
            textfont=dict(color='black', size=10)
        ))

    # เส้นแบ่ง
    fig.add_shape(type="line", x0=50, x1=50, y0=0, y1=100,
                  line=dict(color="red", dash="dash", width=1))
    fig.add_shape(type="line", x0=80, x1=80, y0=0, y1=100,
                  line=dict(color="gray", dash="dot", width=1))
    fig.add_shape(type="line", x0=0, x1=100, y0=50, y1=50,
                  line=dict(color="red", dash="dash", width=1))
    fig.add_shape(type="line", x0=0, x1=100, y0=80, y1=80,
                  line=dict(color="gray", dash="dot", width=1))
    fig.add_shape(type="line", x0=0, x1=100, y0=0, y1=100,
                  line=dict(color="gray", dash="dot", width=1))

    fig.update_layout(
        title='Student Performance by Zone' + (" and Tier" if use_tier else ""),
        xaxis=dict(title='STEM Average (Math + Science)', range=[0, 100]),
        yaxis=dict(title='Language Average (English + Thai)', range=[0, 100]),
        plot_bgcolor='white',
        legend_title='Tier' if use_tier else 'Students',
        height=700,
    )

    return fig


# Sidebar for configuration
st.sidebar.header("📋 Configuration")

# Sheet mapping - โหลดจาก st.secrets
try:
    sheet_map = dict(st.secrets["sheet_mapping"])
    print("Sheet mapping loaded from secrets:", sheet_map)
except Exception as e:
    st.error(f"❌ Error loading sheet mapping from secrets: {e}")
    # Fallback to default mapping
    sheet_map = {
        "Primary4": "1qUHxr2HmNSzuUZQ2KbcbD-3_2nWuhtVGxDIb5yGBhKg",
        "Primary6": "11UBdhdiB7ear04ZnJ6WLN5ZIRu1SLVTOwMTqz1iKEW0"
    }
    st.warning("⚠️ ใช้ Sheet mapping เริ่มต้น เนื่องจากโหลดจาก secrets ไม่สำเร็จ")

# Select level
level = st.sidebar.selectbox(
    "Select Grade Level",
    options=list(sheet_map.keys()),
    index=0
)

# Focus options
focus_options = st.sidebar.multiselect(
    "Select Focus Areas",
    options=["ALL", "LANGUAGE", "MATH_SCIENCE"],
    default=["ALL"]
)

# Refresh button
# if st.sidebar.button("🔄 นำเข้าข้อมูลใหม่"):
#     st.cache_data.clear()
#     st.rerun()

# Main content
if level and focus_options:
    spreadsheet_id = sheet_map[level]
    
    st.info(f"📊 Loading data for **{level}**")
    
    # Create tabs for different focus areas
    tabs = st.tabs([f"📈 {focus.replace('_', ' ').title()}" for focus in focus_options])
    
    for i, focus_on in enumerate(focus_options):
        with tabs[i]:
            st.subheader(f"Performance Analysis: {focus_on.replace('_', ' ').title()}")
            
            # Load data
            with st.spinner(f"Loading data for {focus_on}..."):
                df = load_google_sheet_by_id(
                    spreadsheet_id=spreadsheet_id,
                    worksheet_name=focus_on,
                )
            
            if df is not None and not df.empty:
                # Display data overview
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Students", len(df))
                
                with col2:
                    if 'STEM_AVG' in df.columns:
                        avg_stem = df['STEM_AVG'].mean()
                        st.metric("Average STEM Score", f"{avg_stem:.1f}")
                
                with col3:
                    if 'LANGUAGE_AVG' in df.columns:
                        avg_lang = df['LANGUAGE_AVG'].mean()
                        st.metric("Average Language Score", f"{avg_lang:.1f}")
                
                # Display the plot
                st.subheader("📊 Performance Visualization")
                
                if 'STEM_AVG' in df.columns and 'LANGUAGE_AVG' in df.columns:
                    fig = plot_classroom_cluster(df, focus_on)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.error("Required columns (STEM_AVG, LANGUAGE_AVG) not found in the data")
                
                # Display raw data
                with st.expander("📋 View Raw Data"):
                    st.dataframe(df, use_container_width=True, key=f"{focus_on}_scatter")
                
                
                # Zone analysis
                if 'STEM_AVG' in df.columns and 'LANGUAGE_AVG' in df.columns:
                    st.subheader("🎯 Zone Analysis")
                    
                    # Create zone counts
                    zone_counts = {}
                    for _, row in df.iterrows():
                        stem_score = row['STEM_AVG']
                        lang_score = row['LANGUAGE_AVG']
                        
                        if stem_score < 50 and lang_score < 50:
                            zone = "Warning Zone"
                        elif stem_score < 50 and 50 <= lang_score < 80:
                            zone = "STEM Support"
                        elif stem_score < 50 and lang_score >= 80:
                            zone = "Language Expert"
                        elif 50 <= stem_score < 80 and lang_score < 50:
                            zone = "Language Support"
                        elif 50 <= stem_score < 80 and 50 <= lang_score < 80:
                            zone = "Development Zone"
                        elif stem_score >= 80 and lang_score < 50:
                            zone = "STEM Expert"
                        elif stem_score >= 80 and 50 <= lang_score < 80:
                            zone = "STEM Strong"
                        elif 50 <= stem_score < 80 and lang_score >= 80:
                            zone = "Language Strong"
                        else:  # stem_score >= 80 and lang_score >= 80
                            zone = "Perfect Zone"
                        
                        zone_counts[zone] = zone_counts.get(zone, 0) + 1
                    
                    # Display zone distribution
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Zone Distribution:**")
                        for zone, count in zone_counts.items():
                            percentage = (count / len(df)) * 100
                            st.write(f"- {zone}: {count} students ({percentage:.1f}%)")
                    
                    with col2:
                        # Create pie chart for zone distribution
                        fig_pie = px.pie(
                            values=list(zone_counts.values()),
                            names=list(zone_counts.keys()),
                            title="Student Distribution by Zone"
                        )
                        st.plotly_chart(fig_pie, use_container_width=True, key=f"{focus_on}_pie")
            
            else:
                st.error(f"No data found for {focus_on}")

# Footer
st.markdown("---")
st.markdown("**Student Performance Tracker** | For Teacher")
st.markdown("*For support, please contact Thornthan Yasukam*")