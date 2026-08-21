import streamlit as st
import pandas as pd
import io
import os
import pypdf
from datetime import datetime, timedelta
import zoneinfo
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ---------------------------------------------------------
# 1. PAGE & BRANDED DARK THEME CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="Yenepoya Admission & Fee Engine",
    page_icon="🤖",
    layout="wide"
)

# Force KSA Standard Time (Asia/Riyadh UTC+3)
try:
    ksa_tz = zoneinfo.ZoneInfo("Asia/Riyadh")
    current_ksa_date = datetime.now(ksa_tz).date()
except Exception:
    current_ksa_date = datetime.now().date()

# Dark Tech Theme Styling
st.markdown("""
    <style>
    .stApp {
        background-color: #0F172A !important;
        color: #F8FAFC !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #1E293B !important;
        border-right: 1px solid #334155;
    }
    section[data-testid="stSidebar"] * {
        color: #F8FAFC !important;
    }
    .main-header {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        border: 1px solid #38BDF8;
        color: #FFFFFF;
        padding: 24px;
        border-radius: 12px;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(56, 189, 248, 0.15);
    }
    .main-header h1 {
        color: #38BDF8 !important;
        margin: 0;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .main-header p {
        color: #F59E0B !important;
        margin-top: 5px;
        font-size: 1.05rem;
        font-weight: 600;
    }
    .quote-box {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-left: 5px solid #F59E0B;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 20px;
    }
    [data-testid="stMetricValue"] {
        color: #38BDF8 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Header Section
logo_path = "our-logo.png"

col_header_left, col_header_right = st.columns([1, 4])
with col_header_left:
    if os.path.exists(logo_path):
        st.image(logo_path, width=110)
    else:
        st.write("🤖")

with col_header_right:
    st.markdown("""
        <div class="main-header">
            <h1>YENEPOYA INTERNATIONAL SCHOOL</h1>
            <p>A Next Generation of Learning — Official Parent Fee Quotation Portal</p>
        </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. MASTER DATA MAPPINGS
# ---------------------------------------------------------
# KG: 500 | Grade 1-3: 1200 | Grade 4 and above: 1500
books_fee_map = {
    "KG. 1": 500, "KG. 2": 500, "KG. 3": 500,
    "Grade 1": 1200, "Grade 2": 1200, "Grade 3": 1200,
    "Grade 4": 1500, "Grade 5": 1500, "Grade 6": 1500,
    "Grade 7": 1500, "Grade 8": 1500, "Grade 9": 1500,
    "Grade 10": 1500, "Grade 11": 1500, "Grade 12": 1500
}

new_tuition_map = {
    "KG. 1": 26000, "KG. 2": 26000, "KG. 3": 28000,
    "Grade 1": 33000, "Grade 2": 33000, "Grade 3": 33000,
    "Grade 4": 33000, "Grade 5": 36000, "Grade 6": 36000,
    "Grade 7": 36000, "Grade 8": 36000, "Grade 9": 36000,
    "Grade 10": 38000, "Grade 11": 40000, "Grade 12": 42000
}

old_tuition_map = {
    "KG. 1": 21500, "KG. 2": 21500, "KG. 3": 23500,
    "Grade 1": 28500, "Grade 2": 28500, "Grade 3": 28500,
    "Grade 4": 30500, "Grade 5": 30500, "Grade 6": 30500,
    "Grade 7": 31500, "Grade 8": 32500, "Grade 9": 32500,
    "Grade 10": 34500, "Grade 11": 36500, "Grade 12": 38500
}

# ---------------------------------------------------------
# 3. SIDEBAR CONTROLS & VALIDITY SETTINGS
# ---------------------------------------------------------
st.sidebar.header("⚙️ Student & Family Setup")
num_students = st.sidebar.number_input("Number of Students", min_value=1, max_value=6, value=1, step=1)
nationality = st.sidebar.selectbox("Nationality (Tax Category)", ["Saudi National (0% VAT)", "Non-Saudi (15% VAT)"])
parent_name = st.sidebar.text_input("Parent / Guardian Name", "Parent/Guardian")

is_non_saudi = "Non-Saudi" in nationality
vat_rate = 0.15 if is_non_saudi else 0.0

st.sidebar.divider()
st.sidebar.header("📅 Date & Validity Controls")
issue_date = st.sidebar.date_input("Quotation Issue Date (KSA)", value=current_ksa_date)
discount_validity_days = st.sidebar.slider("Discount Validity (Days)", min_value=1, max_value=60, value=15)
quote_validity_days = st.sidebar.slider("Quotation Validity (Days)", min_value=1, max_value=90, value=30)

discount_expiry_date = issue_date + timedelta(days=discount_validity_days)
quote_expiry_date = issue_date + timedelta(days=quote_validity_days)

family_total_quote = 0.0
student_summaries = []
full_ipad_pkg_students = []

# ---------------------------------------------------------
# 4. DYNAMIC STUDENT INPUT TABS
# ---------------------------------------------------------
tabs = st.tabs([f"🎓 Student {i+1}" for i in range(num_students)])

for i, tab in enumerate(tabs):
    with tab:
        st.subheader(f"Student {i+1} Configuration")
        
        student_name_input = st.text_input(f"Student {i+1} Full Name", value=f"Student {i+1}", key=f"name_{i}")
        
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            student_type = st.selectbox("Student Status", ["New Student", "Returning Student"], key=f"status_{i}")
            grade = st.selectbox("Select Grade", list(new_tuition_map.keys()), key=f"grade_{i}")
            default_discount = 35 + (5 if i > 0 else 0)
            discount_pct = st.slider("Discount (%)", 0, 50, min(default_discount, 50), 5, key=f"disc_{i}")
            
        with c2:
            default_book_fee = books_fee_map.get(grade, 1500)
            use_custom_books = st.checkbox("Custom Books Fee", key=f"cust_book_check_{i}")
            if use_custom_books:
                books_fee = st.number_input("Books Fee (SAR)", min_value=0.0, value=float(default_book_fee), step=50.0, key=f"cust_book_val_{i}")
            else:
                books_fee = float(default_book_fee)

        with c3:
            ipad_option = st.selectbox(
                "iPad Package / Migration",
                [
                    "None",
                    "SAR 2,800 - Full iPad Package",
                    "SAR 600 - Migration Only (License & Config)",
                    "SAR 700 - Migration with Pen",
                    "SAR 800 - Migration with Pen & Cover",
                    "Custom Value"
                ],
                key=f"ipad_opt_{i}"
            )
            
            ipad_fee = 0.0
            if "2,800" in ipad_option:
                ipad_fee = 2800.0
                full_ipad_pkg_students.append(student_name_input)
            elif "600" in ipad_option:
                ipad_fee = 600.0
            elif "700" in ipad_option:
                ipad_fee = 700.0
            elif "800" in ipad_option:
                ipad_fee = 800.0
            elif ipad_option == "Custom Value":
                ipad_fee = st.number_input("Custom iPad/Migration Fee (SAR)", min_value=0.0, value=0.0, step=50.0, key=f"cust_ipad_val_{i}")
            
        with c4:
            bus_options_list = [
                "None",
                "One Side (1 Term) - SAR 1,500",
                "One Side (Whole Year) - SAR 3,000",
                "Two Side (Whole Year) - SAR 5,000",
                "Two Side Premium (Whole Year) - SAR 6,500"
            ]
            if student_type == "Returning Student":
                bus_options_list.extend([
                    "Old Student: 1 Side Whole Year - SAR 2,000",
                    "Old Student: 2 Side Whole Year - SAR 4,000"
                ])
            bus_options_list.append("Custom Value")
                
            bus_option = st.selectbox("Bus Transportation", bus_options_list, key=f"bus_{i}")

            bus_fee = 0.0
            if "1,500" in bus_option:
                bus_fee = 1500.0
            elif "2,000" in bus_option:
                bus_fee = 2000.0
            elif "3,000" in bus_option:
                bus_fee = 3000.0
            elif "4,000" in bus_option:
                bus_fee = 4000.0
            elif "5,000" in bus_option:
                bus_fee = 5000.0
            elif "6,500" in bus_option:
                bus_fee = 6500.0
            elif bus_option == "Custom Value":
                bus_fee = st.number_input("Custom Bus Fee (SAR)", min_value=0.0, value=0.0, step=50.0, key=f"cust_bus_val_{i}")

        if student_type == "Returning Student":
            base_tuition = old_tuition_map.get(grade, 28500)
        else:
            base_tuition = new_tuition_map.get(grade, 33000)

        discount_amount = base_tuition * (discount_pct / 100.0)
        net_tuition = base_tuition - discount_amount
        
        vat_amount = net_tuition * vat_rate
        tuition_with_vat = net_tuition + vat_amount

        total_student_fee = tuition_with_vat + books_fee + ipad_fee + bus_fee
        family_total_quote += total_student_fee

        student_summaries.append({
            "Student Name": student_name_input,
            "Student Status": student_type,
            "Grade": grade,
            "Base Tuition": base_tuition,
            "Discount %": f"{discount_pct}%",
            "Discount Amt": discount_amount,
            "VAT": vat_amount,
            "Mandatory Books": books_fee,
            "iPad Fee": ipad_fee,
            "Bus Fee": bus_fee,
            "Total Fee (SAR)": total_student_fee
        })

        st.markdown('<div class="quote-box">', unsafe_allow_html=True)
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Base Tuition", f"{base_tuition:,.2f} SAR")
        m2.metric(f"Discount ({discount_pct}%)", f"-{discount_amount:,.2f} SAR")
        m3.metric("Mandatory Books", f"{books_fee:,.2f} SAR")
        m4.metric("iPad & Bus Add-Ons", f"{ipad_fee + bus_fee:,.2f} SAR")
        m5.metric("Student Total", f"{total_student_fee:,.2f} SAR")
        st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. STREAMLIT SCREEN SUMMARY DISPLAY
# ---------------------------------------------------------
st.divider()
st.subheader("📊 Official Family Quotation Breakdown")

val_col1, val_col2, val_col3 = st.columns(3)
val_col1.info(f"📅 **Issue Date (KSA):** {issue_date.strftime('%d %b %Y')}")
val_col2.warning(f"⏳ **Discount Valid Until:** {discount_expiry_date.strftime('%d %b %Y')} ({discount_validity_days} Days)")
val_col3.error(f"🛑 **Quotation Expires:** {quote_expiry_date.strftime('%d %b %Y')} ({quote_validity_days} Days)")

metrics_labels = [
    "Student Status",
    "Grade Level",
    "Base Tuition (SAR)",
    "Discount Percentage",
    "Discount Amount (SAR)",
    "VAT Amount (SAR)",
    "Mandatory Books Fee (SAR)",
    "iPad Package / Migration (SAR)",
    "Bus Transportation (SAR)",
    "Student Total Fee (SAR)"
]

horizontal_data = {"Fee Component": metrics_labels}

for s in student_summaries:
    col_name = s["Student Name"]
    horizontal_data[col_name] = [
        s["Student Status"],
        s["Grade"],
        f"{s['Base Tuition']:,.2f}",
        s["Discount %"],
        f"-{s['Discount Amt']:,.2f}",
        f"+{s['VAT']:,.2f}",
        f"{s['Mandatory Books']:,.2f}",
        f"{s['iPad Fee']:,.2f}",
        f"{s['Bus Fee']:,.2f}",
        f"{s['Total Fee (SAR)']:,.2f}"
    ]

df_horizontal = pd.DataFrame(horizontal_data)
st.table(df_horizontal)

st.subheader("📋 Student Totals Summary Table")

totals_table_data = []
for idx, s in enumerate(student_summaries):
    row = {
        "Student": f"Student {idx+1}: {s['Student Name']}",
        "Grade": s["Grade"],
        "Net School Tuition": f"{s['Base Tuition'] - s['Discount Amt']:,.2f} SAR",
    }
    if is_non_saudi:
        row["VAT (15% on Tuition)"] = f"{s['VAT']:,.2f} SAR"
    row["Books & Add-Ons"] = f"{s['Mandatory Books'] + s['iPad Fee'] + s['Bus Fee']:,.2f} SAR"
    row["Total Amount"] = f"{s['Total Fee (SAR)']:,.2f} SAR"
    totals_table_data.append(row)

st.table(pd.DataFrame(totals_table_data))

st.markdown(f"### **Grand Total Quote: `{family_total_quote:,.2f} SAR`**")

if len(full_ipad_pkg_students) > 0:
    with st.container(border=True):
        st.subheader("📱 Full Student iPad Package Details")
        st.markdown(f"**Selected for Student(s):** :blue[{', '.join(full_ipad_pkg_students)}]")
        st.divider()

        col_hw, col_sw = st.columns(2)
        with col_hw:
            st.markdown("**📦 Included Hardware & Protection:**")
            st.markdown("""
            * **Brand New iPad A16 (128GB Storage)**
            * **Rugged Heavy-Duty Protective Case**
            * **School-Approved High-Precision Stylus Pen**
            * **AppleCare+ Enterprise Warranty** (36 Months full coverage)
            """)

        with col_sw:
            st.markdown("**⚙️ Digital Ecosystem & Management:**")
            st.markdown("""
            * **Jamf School Management System** (MDM)
            * **Microsoft 365 Education Account** (1TB Cloud storage)
            * **Apple Managed Educational ID & 200GB iCloud**
            * **Pre-configured Security Profiles & Learning Apps**
            """)

        st.divider()

        st.warning(
            "**💳 Payment Options:**\n\n"
            "The total package fee is **SAR 2,800**. "
            "Parents can pay full upfront or opt for the **C-Pay 12-Month Installment Plan** (12 payments of ~SAR 233.33/month)."
        )

        st.error(
            "**⚠️ Annual Software License Renewal Notice:**\n\n"
            "The initial package fee covers Year 1 hardware, provisioning, and software setups. "
            "All active management licenses (Jamf MDM, Microsoft 365, Cloud platform access) **must be renewed annually** "
            "by parents to keep the device compliant with school systems."
        )

st.divider()

# ---------------------------------------------------------
# 6. EXACT MATCH PDF GENERATOR
# ---------------------------------------------------------
def create_pdf_bytes():
    try:
        content_buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            content_buffer, 
            pagesize=letter, 
            rightMargin=25, 
            leftMargin=25, 
            topMargin=65,
            bottomMargin=130
        )
        
        elements = []
        styles = getSampleStyleSheet()

        # --- Typography Styles ---
        section_heading_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=13,
            textColor=colors.HexColor('#0B2545'),
            spaceBefore=6,
            spaceAfter=5
        )
        
        meta_header_style = ParagraphStyle(
            'MetaHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor('#0B2545')
        )

        badge_text_blue = ParagraphStyle('BadgeBlue', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor('#1E40AF'), alignment=1)
        badge_text_olive = ParagraphStyle('BadgeOlive', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor('#854D0E'), alignment=1)
        badge_text_red = ParagraphStyle('BadgeRed', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor('#991B1B'), alignment=1)

        cell_hdr_style = ParagraphStyle(
            'TableHdr',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=10.5,
            textColor=colors.white,
            alignment=1
        )
        
        cell_body_style = ParagraphStyle(
            'TableBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=10.5,
            textColor=colors.HexColor('#1E293B'),
            alignment=1
        )

        cell_body_left = ParagraphStyle(
            'TableBodyLeft',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=10.5,
            textColor=colors.HexColor('#0B2545'),
            alignment=0
        )

        # -----------------------------------------------------
        # 1. HEADER METADATA & STYLED BADGES
        # -----------------------------------------------------
        elements.append(Paragraph(f"<b>Parent / Guardian Name:</b> {parent_name} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Tax Category:</b> {nationality}", meta_header_style))
        elements.append(Spacer(1, 6))

        badge_col1 = [Paragraph(f"📅 Issue Date (KSA):<br/><b>{issue_date.strftime('%d %b %Y')}</b>", badge_text_blue)]
        badge_col2 = [Paragraph(f"⏳ Discount Valid Until:<br/><b>{discount_expiry_date.strftime('%d %b %Y')} ({discount_validity_days} Days)</b>", badge_text_olive)]
        badge_col3 = [Paragraph(f"🛑 Quotation Expires:<br/><b>{quote_expiry_date.strftime('%d %b %Y')} ({quote_validity_days} Days)</b>", badge_text_red)]

        badge_table = Table([[badge_col1, badge_col2, badge_col3]], colWidths=[180, 190, 185])
        badge_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,0), (0,0), colors.HexColor('#DBEAFE')),
            ('BACKGROUND', (1,0), (1,0), colors.HexColor('#FEF9C3')),
            ('BACKGROUND', (2,0), (2,0), colors.HexColor('#FEE2E2')),
            ('BOX', (0,0), (0,0), 0.5, colors.HexColor('#93C5FD')),
            ('BOX', (1,0), (1,0), 0.5, colors.HexColor('#FDE047')),
            ('BOX', (2,0), (2,0), 0.5, colors.HexColor('#FCA5A5')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(badge_table)
        elements.append(Spacer(1, 8))

        # -----------------------------------------------------
        # 2. TABLE 1: OFFICIAL FAMILY QUOTATION BREAKDOWN
        # -----------------------------------------------------
        elements.append(Paragraph("📊 Official Family Quotation Breakdown", section_heading_style))
        
        t1_headers = [Paragraph("Fee Component", cell_body_left)] + [Paragraph(s["Student Name"], cell_hdr_style) for s in student_summaries]
        t1_data = [t1_headers]

        for idx, row_name in enumerate(metrics_labels):
            row_cells = [Paragraph(row_name, cell_body_left)]
            for s in student_summaries:
                if idx == 0: val = s["Student Status"]
                elif idx == 1: val = s["Grade"]
                elif idx == 2: val = f"{s['Base Tuition']:,.2f}"
                elif idx == 3: val = s["Discount %"]
                elif idx == 4: val = f"-{s['Discount Amt']:,.2f}"
                elif idx == 5: val = f"+{s['VAT']:,.2f}"
                elif idx == 6: val = f"{s['Mandatory Books']:,.2f}"
                elif idx == 7: val = f"{s['iPad Fee']:,.2f}"
                elif idx == 8: val = f"{s['Bus Fee']:,.2f}"
                elif idx == 9: val = f"<b>{s['Total Fee (SAR)']:,.2f}</b>"
                row_cells.append(Paragraph(str(val), cell_body_style))
            t1_data.append(row_cells)

        num_cols = len(t1_headers)
        f_width = 155
        r_width = (555 - f_width) / max(1, num_cols - 1)
        t1_col_widths = [f_width] + [r_width] * (num_cols - 1)

        pdf_t1 = Table(t1_data, colWidths=t1_col_widths)
        pdf_t1.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0B2545')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('TOPPADDING', (0,0), (-1,-1), 3.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8FAFC')),
        ]))
        elements.append(pdf_t1)
        elements.append(Spacer(1, 10))

        # -----------------------------------------------------
        # 3. TABLE 2: STUDENT TOTALS SUMMARY TABLE
        # -----------------------------------------------------
        elements.append(Paragraph("📋 Student Totals Summary Table", section_heading_style))
        
        if is_non_saudi:
            t2_headers = ["Student", "Grade", "Net School Tuition", "VAT (15%)", "Books & Add-Ons", "Total Amount"]
            t2_widths = [120, 50, 100, 85, 100, 100]
        else:
            t2_headers = ["Student", "Grade", "Net School Tuition", "Books & Add-Ons", "Total Amount"]
            t2_widths = [135, 60, 120, 120, 120]

        t2_data = [[Paragraph(h, cell_hdr_style) for h in t2_headers]]

        for idx, s in enumerate(student_summaries):
            net_t = s['Base Tuition'] - s['Discount Amt']
            add_ons = s['Mandatory Books'] + s['iPad Fee'] + s['Bus Fee']
            
            if is_non_saudi:
                row = [
                    Paragraph(f"Student {idx+1}: {s['Student Name']}", cell_body_left),
                    Paragraph(s['Grade'], cell_body_style),
                    Paragraph(f"{net_t:,.2f} SAR", cell_body_style),
                    Paragraph(f"{s['VAT']:,.2f} SAR", cell_body_style),
                    Paragraph(f"{add_ons:,.2f} SAR", cell_body_style),
                    Paragraph(f"<b>{s['Total Fee (SAR)']:,.2f} SAR</b>", cell_body_style)
                ]
            else:
                row = [
                    Paragraph(f"Student {idx+1}: {s['Student Name']}", cell_body_left),
                    Paragraph(s['Grade'], cell_body_style),
                    Paragraph(f"{net_t:,.2f} SAR", cell_body_style),
                    Paragraph(f"{add_ons:,.2f} SAR", cell_body_style),
                    Paragraph(f"<b>{s['Total Fee (SAR)']:,.2f} SAR</b>", cell_body_style)
                ]
            t2_data.append(row)

        pdf_t2 = Table(t2_data, colWidths=t2_widths)
        pdf_t2.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('TOPPADDING', (0,0), (-1,-1), 3.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#FFFFFF')),
        ]))
        elements.append(pdf_t2)
        elements.append(Spacer(1, 8))

        # -----------------------------------------------------
        # 4. GRAND TOTAL SUMMARY BANNER
        # -----------------------------------------------------
        summary_p_style = ParagraphStyle(
            'GrandTotalBanner',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=12.5,
            textColor=colors.HexColor('#0B2545'),
            alignment=1
        )
        
        banner_text = f"Grand Total Quote: <font color='#059669'>{family_total_quote:,.2f} SAR</font>"
        
        banner_table = Table([[Paragraph(banner_text, summary_p_style)]], colWidths=[555])
        banner_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0FDF4')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#16A34A')),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(banner_table)

        # -----------------------------------------------------
        # 5. FULL STUDENT IPAD PACKAGE DETAILS
        # -----------------------------------------------------
        if len(full_ipad_pkg_students) > 0:
            elements.append(Spacer(1, 8))

            ipad_title_style = ParagraphStyle('IpadTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=12, textColor=colors.HexColor('#0B2545'))
            ipad_sub_style = ParagraphStyle('IpadSub', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor('#334155'))

            elements.append(Paragraph("📱 Full Student iPad Package Details", ipad_title_style))
            elements.append(Paragraph(f"<b>Selected for Student(s):</b> <font color='#2563EB'>{', '.join(full_ipad_pkg_students)}</font>", ipad_sub_style))
            elements.append(Spacer(1, 4))

            ipad_hdr_style = ParagraphStyle('IpadHdr', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor('#0B2545'))
            ipad_item_style = ParagraphStyle('IpadItem', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9.5, textColor=colors.HexColor('#1E293B'))

            col1_content = [
                Paragraph("<b>📦 Included Hardware & Protection:</b>", ipad_hdr_style),
                Paragraph("• Brand New iPad A16 (128GB Storage)", ipad_item_style),
                Paragraph("• Rugged Heavy-Duty Protective Case", ipad_item_style),
                Paragraph("• School-Approved High-Precision Stylus Pen", ipad_item_style),
                Paragraph("• AppleCare+ Enterprise Warranty (36 Months)", ipad_item_style),
            ]
            
            col2_content = [
                Paragraph("<b>⚙️ Digital Ecosystem & Management:</b>", ipad_hdr_style),
                Paragraph("• Jamf School Management System (MDM)", ipad_item_style),
                Paragraph("• Microsoft 365 Education Account (1TB Cloud)", ipad_item_style),
                Paragraph("• Apple Managed Educational ID & 200GB iCloud", ipad_item_style),
                Paragraph("• Pre-configured Security Profiles & Learning Apps", ipad_item_style),
            ]

            ipad_spec_table = Table([[col1_content, col2_content]], colWidths=[275, 280])
            ipad_spec_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ]))
            elements.append(ipad_spec_table)
            elements.append(Spacer(1, 5))

            policy_style = ParagraphStyle('PolicyBox', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9.5, textColor=colors.HexColor('#1E293B'))
            
            p_terms = "<b>💳 Payment Options:</b> Package fee is <b>SAR 2,800</b>. Parents can pay upfront or select the 12-Month Installment Plan via C-Pay."
            p_table = Table([[Paragraph(p_terms, policy_style)]], colWidths=[555])
            p_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEF3C7')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#F59E0B')),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                ('LEFTPADDING', (0,0), (-1,-1), 5),
                ('RIGHTPADDING', (0,0), (-1,-1), 5),
            ]))
            elements.append(p_table)
            elements.append(Spacer(1, 4))

            p_renew = "<b>⚠️ Annual License Renewal:</b> Initial fee covers Year 1 setup. Active management licenses (Jamf MDM, Microsoft 365) <b>must be renewed annually</b> by parents."
            r_table = Table([[Paragraph(p_renew, policy_style)]], colWidths=[555])
            r_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEE2E2')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#EF4444')),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                ('LEFTPADDING', (0,0), (-1,-1), 5),
                ('RIGHTPADDING', (0,0), (-1,-1), 5),
            ]))
            elements.append(r_table)

        # -----------------------------------------------------
        # 6. SIGNATURE CANVAS DRAWING (POSITIONED ABOVE FOOTER)
        # -----------------------------------------------------
        def draw_bottom_signatures(canvas, doc):
            canvas.saveState()
            
            sig_label_style = ParagraphStyle('SigLabel', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=10.5, textColor=colors.HexColor('#0B2545'))
            sig_sub_style = ParagraphStyle('SigSub', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9.5, textColor=colors.HexColor('#64748B'))

            sig_cell_left = [
                Paragraph("<b>Parent / Guardian Acknowledgment:</b>", sig_label_style),
                Spacer(1, 14),
                Paragraph("__________________________________________", sig_sub_style),
                Paragraph("Signature & Date", sig_sub_style)
            ]

            sig_cell_right = [
                Paragraph("<b>For Yenepoya International Schools:</b>", sig_label_style),
                Spacer(1, 14),
                Paragraph("__________________________________________", sig_sub_style),
                Paragraph("Authorized Stamp & Date", sig_sub_style)
            ]

            sig_table = Table([[sig_cell_left, sig_cell_right]], colWidths=[275, 280])
            sig_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ]))

            w, h = sig_table.wrap(555, 60)
            sig_table.drawOn(canvas, 25, 120)
            canvas.restoreState()

        # Build PDF
        doc.build(elements, onFirstPage=draw_bottom_signatures, onLaterPages=draw_bottom_signatures)
        content_buffer.seek(0)

        template_path = "LetterHead (Updated).pdf"
        if os.path.exists(template_path):
            reader_template = pypdf.PdfReader(template_path)
            reader_content = pypdf.PdfReader(content_buffer)
            
            writer = pypdf.PdfWriter()
            template_page = reader_template.pages[0]
            content_page = reader_content.pages[0]
            
            template_page.merge_page(content_page)
            writer.add_page(template_page)
            
            final_buffer = io.BytesIO()
            writer.write(final_buffer)
            final_buffer.seek(0)
            return final_buffer.getvalue()
        else:
            return content_buffer.getvalue()
            
    except Exception as err:
        st.error(f"Error generating PDF: {err}")
        return b""

btn_col1, btn_col2 = st.columns(2)

with btn_col1:
    st.components.v1.html(
        """
        <button onclick="window.parent.print()" style="background-color: #38BDF8; color: #0F172A; padding: 12px 20px; border: none; border-radius: 6px; cursor: pointer; width: 100%; font-weight: bold; font-size: 14px;">
            🖨️ Print Quotation Directly
        </button>
        """,
        height=50
    )

with btn_col2:
    pdf_data = create_pdf_bytes()
    if pdf_data:
        st.download_button(
            label="📄 Export Official Letterhead PDF",
            data=pdf_data,
            file_name=f"Yenepoya_Fee_Quotation_{parent_name.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
