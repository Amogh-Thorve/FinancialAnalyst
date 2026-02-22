import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

def generate_pdf(history, filename, metrics=None):
    """
    Generates a PDF report from the agent history and optional metrics.
    """
    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Custom Styles
    user_style = ParagraphStyle(
        'UserStyle', 
        parent=normal_style, 
        textColor=colors.blue,
        backColor=colors.whitesmoke,
        borderPadding=5,
        spaceAfter=10
    )
    
    ai_style = ParagraphStyle(
        'AIStyle',
        parent=normal_style,
        textColor=colors.black,
        spaceAfter=10
    )

    story.append(Paragraph("Financial Analysis Report", title_style))
    story.append(Spacer(1, 12))

    # Add Metrics Summary if available
    if metrics:
        story.append(Paragraph("Financial Summary", heading_style))
        story.append(Spacer(1, 6))
        
        # Prepare table data
        table_data = [
            ["Metric", "Value", "Status"],
        ]
        
        # Define key metrics to show
        display_keys = [
            ("Company", "company_name"),
            ("Ticker", "ticker"),
            ("EPS", "eps"),
            ("P/E Ratio", "pe_ratio"),
            ("ROE", "roe"),
            ("Revenue Growth", "revenue_growth"),
            ("Profit Margin", "profit_margin"),
            ("Debt/Equity", "debt_equity"),
            ("Market Cap", "market_cap"),
        ]
        
        for label, key in display_keys:
            val = metrics.get(key, "N/A")
            status = metrics.get(f"{key}_status", "ANALYZED")
            table_data.append([label, str(val), status])
            
        # Create Table
        table = Table(table_data, colWidths=[150, 150, 100])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,(-1)), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 12),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        story.append(table)
        story.append(Spacer(1, 24))

    if history:
        story.append(Paragraph("Analysis Log & Consultation", heading_style))
        story.append(Spacer(1, 12))
        
        for message in history:
            if isinstance(message, HumanMessage):
                text = f"<b>User:</b> {message.content}"
                story.append(Paragraph(text, user_style))
                story.append(Spacer(1, 6))
                
            elif isinstance(message, AIMessage):
                content = message.content
                
                # Check for Image marker
                if content.startswith("[IMAGE]"):
                    image_url = content.replace("[IMAGE] ", "").strip()
                    fs_path = image_url.lstrip("/")
                    
                    if os.path.exists(fs_path):
                        try:
                            img = Image(fs_path, width=400, height=240)
                            story.append(img)
                            story.append(Spacer(1, 12))
                        except Exception as e:
                            story.append(Paragraph(f"<i>[Error loading image: {str(e)}]</i>", ai_style))
                    else:
                        story.append(Paragraph(f"<i>[Image not found: {fs_path}]</i>", ai_style))
                
                elif content.startswith("[CHART]"):
                    ticker = content.replace("[CHART] ", "").strip()
                    text = f"<b>Analyst:</b> <i>(Interactive Chart for {ticker} was displayed in UI)</i>"
                    story.append(Paragraph(text, ai_style))
                    story.append(Spacer(1, 6))
                    
                else:
                    text = f"<b>Analyst:</b> {content}"
                    text = text.replace("\n", "<br/>")
                    story.append(Paragraph(text, ai_style))
                    story.append(Spacer(1, 6))

    doc.build(story)
    return filename
