import streamlit as st
import os
import io
import base64
import json
import random
from datetime import datetime
from PIL import Image

# ==========================================
# LOGIC: Gemini SDK & ReportLab Imports
# ==========================================
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# ==========================================
# UI EDITING: Page Configuration & Custom CSS
# ==========================================
st.set_page_config(
    page_title="Explorer Quest: Lyon Edition",
    page_icon="🦁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS with Google Fonts loading & Dual-Language styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Caveat:wght@600&family=Cinzel:wght@600;700&family=Lobster&family=Montserrat:wght@400;600;800&family=Oswald:wght@500;700&family=Pacifico&family=Playfair+Display:ital,wght@0,600;1,400&family=Space+Grotesk:wght@500;700&family=Special+Elite&family=Syne:wght@700;800&display=swap');

    .main-title-fr {
        font-family: 'Cinzel', serif;
        font-size: 2.4rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0px;
        letter-spacing: -0.5px;
    }
    .main-subtitle-en {
        font-family: 'Montserrat', sans-serif;
        font-size: 1.1rem;
        color: #4B5563;
        font-style: italic;
        margin-top: 2px;
        margin-bottom: 20px;
        font-weight: 500;
    }
    .section-fr {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0F172A;
        margin-top: 15px;
        margin-bottom: 0px;
    }
    .section-en {
        font-size: 0.95rem;
        color: #64748B;
        font-style: italic;
        margin-bottom: 15px;
    }
    .tier-badge {
        background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .landmark-card {
        background-color: #FFFFFF;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        padding: 18px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
    }
</style>
""", unsafe_allow_html=True)

# Helper function for Dual-Language UI Headers
def dual_header(fr_text: str, en_text: str, level: int = 2, icon: str = ""):

    icon_str = f"{icon} " if icon else ""
    if level == 1:
        st.markdown(f"""
            <div style="margin-bottom: 20px; border-bottom: 2px solid #E2E8F0; padding-bottom: 10px;">
                <h1 class="main-title-fr">{icon_str}{fr_text}</h1>
                <div class="main-subtitle-en">{en_text}</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div style="margin-top: 15px; margin-bottom: 12px;">
                <h{level} class="section-fr">{icon_str}{fr_text}</h{level}>
                <div class="section-en">{en_text}</div>
            </div>
        """, unsafe_allow_html=True)

# ==========================================
# LOGIC: State Management & Tier Calculation
# ==========================================
if "explorer_name" not in st.session_state:
    st.session_state.explorer_name = "Explorer"
if "points" not in st.session_state:
    st.session_state.points = 0
if "completed_riddles" not in st.session_state:
    st.session_state.completed_riddles = set()
if "completed_quests" not in st.session_state:
    st.session_state.completed_quests = {}
if "album_entries" not in st.session_state:
    st.session_state.album_entries = []
if "redeemed_coupons" not in st.session_state:
    st.session_state.redeemed_coupons = []
if "custom_riddles" not in st.session_state:
    st.session_state.custom_riddles = None

def get_explorer_tier(points: int):

    if points < 150:
        return "Explorateur Débutant", "Rookie Explorer", "🥉", 150
    elif points < 400:
        return "Aventurier Lyonnais", "Adventurer", "🥈", 400
    elif points < 800:
        return "Explorateur d'Élite", "Elite Explorer", "🥇", 800
    else:
        return "Légende du Rhône", "Premium Legend", "👑", 1000

# ==========================================
# LOGIC: Fallback Data (Lyon Landmarks & Riddles)
# ==========================================
LYON_LANDMARKS = [
    {
        "id": "fourviere",
        "name_fr": "Basilique Notre-Dame de Fourvière",
        "name_en": "Basilica of Notre-Dame de Fourvière",
        "tag": "Architecture & Spirituality",
        "image": "https://images.unsplash.com/photo-1590082871875-064201a27373?auto=format&fit=crop&w=800&q=80",
        "desc_fr": "Surplombant Lyon depuis la 'colline qui prie', cette basilique du XIXe siècle offre une vue panoramique spectaculaire sur toute la ville.",
        "desc_en": "Dominating Lyon from the 'hill that prays', this 19th-century basilica offers a breathtaking panoramic view of the entire city.",
        "fact_fr": "La basilique possède 8 cloches monumentales et plus de 2 millions de mosaïques dorées à l'intérieur.",
        "fact_en": "The basilica features 8 monumental bells and over 2 million gold mosaic tiles inside."
    },
    {
        "id": "traboules",
        "name_fr": "Les Traboules du Vieux Lyon",
        "name_en": "The Secret Traboules of Old Lyon",
        "tag": "Cool History & Secret Spots",
        "image": "https://images.unsplash.com/photo-1570701564993-e00652af8aa7?auto=format&fit=crop&w=800&q=80",
        "desc_fr": "Passages secrets piétons à travers les cours intérieures d'immeubles, utilisés historiquement par les tisseurs de soie (Canuts).",
        "desc_en": "Secret pedestrian passageways cutting through courtyard buildings, historically used by silk weavers (Canuts) to carry textiles dry.",
        "fact_fr": "Il existe plus de 500 traboules à Lyon, mais environ 80 sont ouvertes au public.",
        "fact_en": "There are over 500 traboules in Lyon, though only around 80 are publicly accessible."
    },
    {
        "id": "bellecour",
        "name_fr": "Place Bellecour",
        "name_en": "Place Bellecour",
        "tag": "Urban Icon",
        "image": "https://images.unsplash.com/photo-1524397057410-1e775ed476f3?auto=format&fit=crop&w=800&q=80",
        "desc_fr": "L'une des plus grandes places ouvertes d'Europe, au cœur de la Presqu'île, avec la statue équestre de Louis XIV.",
        "desc_en": "One of the largest open pedestrian squares in Europe, located in the heart of Presqu'île, featuring a majestic statue of Louis XIV.",
        "fact_fr": "C'est le point zéro des routes partant de Lyon et le point de rendez-vous sous la statue du Petit Prince et Saint-Exupéry.",
        "fact_en": "It is kilometer zero for all roads leaving Lyon and home to the Saint-Exupéry & Little Prince statue."
    },
    {
        "id": "halles",
        "name_fr": "Halles de Lyon - Paul Bocuse",
        "name_en": "Paul Bocuse Indoor Food Market",
        "tag": "Gastronomy & Bouchons",
        "image": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?auto=format&fit=crop&w=800&q=80",
        "desc_fr": "Le temple absolu de la gastronomie lyonnaise abritant 48 commerçants d'exception (fromages, charcuteries, pralines).",
        "desc_en": "The ultimate temple of Lyonnaise gastronomy featuring 48 artisan food merchants (cheeses, cured meats, pink pralines).",
        "fact_fr": "Nommé d'après le légendaire chef 3 étoiles Paul Bocuse, 'le Pape de la gastronomie'.",
        "fact_en": "Named after 3-star Michelin legendary chef Paul Bocuse, hailed as the 'Pope of French Gastronomy'."
    },
    {
        "id": "tete_or",
        "name_fr": "Parc de la Tête d'Or",
        "name_en": "Golden Head Park",
        "tag": "Nature & Recreation",
        "image": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80",
        "desc_fr": "Un immense parc urbain de 117 hectares incluant un lac, un jardin botanique et un zoo totalement gratuit.",
        "desc_en": "A massive 117-hectare urban park housing a central lake, botanical gardens, and an entirely free zoo.",
        "fact_fr": "La légende raconte qu'une tête de Christ en or massif y serait cachée quelque part sous la terre.",
        "fact_en": "Legend has it that a solid gold head of Christ is buried somewhere under the park grounds."
    },
    {
        "id": "confluences",
        "name_fr": "Musée des Confluences",
        "name_en": "Confluence Museum",
        "tag": "Modern Architecture",
        "image": "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=800&q=80",
        "desc_fr": "Un musée futuriste en verre et acier situé exactement au point de jonction du Rhône et de la Saône.",
        "desc_en": "A futuristic glass-and-steel architectural marvel sitting precisely where the Rhône and Saône rivers converge.",
        "fact_fr": "Surnommé 'Le Nuage' en raison de sa structure flottante en trame métallique imprimée.",
        "fact_en": "Nicknamed 'The Cloud' because of its floating metallic lattice structure."
    }
]

DEFAULT_12_RIDDLES = [
    {
        "id": 1,
        "question_fr": "Je domine Lyon depuis la 'colline qui prie' avec ma statue dorée de la Vierge. Qui suis-je ?",
        "question_en": "I overlook Lyon from the 'hill that prays' with my golden statue of Mary. What am I?",
        "options": ["Basilique de Fourvière", "Cathédrale Saint-Jean", "Église Saint-Nizier", "Tour Part-Dieu"],
        "answer": "Basilique de Fourvière",
        "hint": "Look at the highest hilltop near Vieux Lyon."
    },
    {
        "id": 2,
        "question_fr": "Quel est le nom de ces passages couverts secrets à travers les immeubles lyonnais ?",
        "question_en": "What is the name of these secret covered passages cutting through Lyon buildings?",
        "options": ["Traboules", "Passages Couverts", "Soustets", "Arcades"],
        "answer": "Traboules",
        "hint": "Famous for helping silk weavers keep dry!"
    },
    {
        "id": 3,
        "question_fr": "Quelle fresque murale géante de 1200 m² à la Croix-Rousse représente la vie des tisseurs de soie ?",
        "question_en": "Which giant 1,200 m² trompe-l'œil mural in Croix-Rousse depicts the silk weavers' life?",
        "options": ["Le Mur des Canuts", "La Fresque des Lyonnais", "Le Mur de la Soie", "L'Arbre de la Croix-Rousse"],
        "answer": "Le Mur des Canuts",
        "hint": "Canut is the traditional word for silk worker."
    },
    {
        "id": 4,
        "question_fr": "Comment s'appellent les restaurants traditionnels et typiques de Lyon ?",
        "question_en": "What are traditional, authentic Lyon dining taverns called?",
        "options": ["Les Bouchons", "Les Estaminets", "Les Guinguettes", "Les Brasseries"],
        "answer": "Les Bouchons",
        "hint": "Check for red-and-white checkered tablecloths."
    },
    {
        "id": 5,
        "question_fr": "Quelle célèbre fête des lumières a lieu chaque année autour du 8 Décembre à Lyon ?",
        "question_en": "Which famous light festival takes place every year around December 8th in Lyon?",
        "options": ["La Fête des Lumières", "Le Nuits de Fourvière", "Le Festival Lumière", "Les Illuminations du Rhône"],
        "answer": "La Fête des Lumières",
        "hint": "Locals put lumignons (candles) on their windows."
    },
    {
        "id": 6,
        "question_fr": "Quel parc lyonnais abrite un zoo gratuit et tirerait son nom d'un trésor caché ?",
        "question_en": "Which Lyon park houses a free zoo and allegedly hides a sacred treasure under its soil?",
        "options": ["Parc de la Tête d'Or", "Parc Blandan", "Parc de Gerland", "Jardin des Chartreux"],
        "answer": "Parc de la Tête d'Or",
        "hint": "Gold head is in its name."
    },
    {
        "id": 7,
        "question_fr": "Deux fleuves se rejoignent à Lyon au niveau de la Presqu'île : la Saône et... ?",
        "question_en": "Two rivers merge at the tip of Lyon's Presqu'île: the Saône and... ?",
        "options": ["Le Rhône", "La Loire", "La Seine", "L'Isère"],
        "answer": "Le Rhône",
        "hint": "It flows down towards the Mediterranean Sea."
    },
    {
        "id": 8,
        "question_fr": "Quelle est la spécialité pâtissière lyonnaise de couleur rose éclatante ?",
        "question_en": "Which iconic Lyonnaise pastry specialty has a bright vibrant pink color?",
        "options": ["La Praline Rose", "Le Macaron Lyon", "Le Bugne de Lyon", "Le Coussin de Lyon"],
        "answer": "La Praline Rose",
        "hint": "Made with almonds coated in cooked sugar."
    },
    {
        "id": 9,
        "question_fr": "Quelle marionnette satirique créée en 1808 par Laurent Mourguet est le symbole de Lyon ?",
        "question_en": "Which satirical puppet created in 1808 by Laurent Mourguet is a beloved symbol of Lyon?",
        "options": ["Guignol", "Gnafron", "Polichinelle", "Madelon"],
        "answer": "Guignol",
        "hint": "He wears a tricorn hat and speaks with a Lyon accent."
    },
    {
        "id": 10,
        "question_fr": "Quel gratte-ciel emblématique de Lyon est surnommé 'La Crayon' ?",
        "question_en": "Which iconic Lyon skyscraper is affectionately nicknamed 'The Pencil'?",
        "options": ["Tour Part-Dieu", "Tour Incity", "Tour Oxygène", "Tour To-Lyon"],
        "answer": "Tour Part-Dieu",
        "hint": "It is cylindrical with a pointed pyramid top."
    },
    {
        "id": 11,
        "question_fr": "Quel chef cuisinier de renommée mondiale possédait son restaurant 3 étoiles à Collonges-au-Mont-d'Or ?",
        "question_en": "Which world-famous 3-star Michelin chef had his flagship restaurant near Lyon?",
        "options": ["Paul Bocuse", "Auguste Escoffier", "Joël Robuchon", "Alain Ducasse"],
        "answer": "Paul Bocuse",
        "hint": "The halles food market bears his name."
    },
    {
        "id": 12,
        "question_fr": "Quelle spécialité charcutière lyonnaise est enrobée de pâte brisée chaud ?",
        "question_en": "Which Lyonnaise charcuterie specialty consists of seasoned sausage baked inside a hot pastry shell?",
        "options": ["Saucisson en Brioche", "Tablier de Sapeur", "Rosette de Lyon", "Andouillette"],
        "answer": "Saucisson en Brioche",
        "hint": "Sausage baked in buttery dough."
    }
]

REAL_LIFE_QUESTS = [
    {
        "id": "quest_1",
        "title_fr": "Quête 1: Le Passage Secret des Canuts",
        "title_en": "Quest 1: The Secret Canut Passage",
        "points": 200,
        "location": "Vieux Lyon / Rue Saint-Jean",
        "desc_fr": "Trouvez et franchissez la traboule au 54 Rue Saint-Jean. Prenez une photo de l'intérieur de la cour gothique.",
        "desc_en": "Find and walk through the traboule at 54 Rue Saint-Jean. Capture a photo inside the gothic inner courtyard."
    },
    {
        "id": "quest_2",
        "title_fr": "Quête 2: L'Assiette du Bouchon Authentique",
        "title_en": "Quest 2: Authentic Bouchon Tasting",
        "points": 200,
        "location": "Presqu'île / Les Halles",
        "desc_fr": "Commandez une Quenelle de Brochet ou une Tarte aux Pralines. Prenez une photo gourmande de votre plat !",
        "desc_en": "Order a Pike Quenelle or a Pink Praline Tart. Snap a culinary photo of your dish!"
    },
    {
        "id": "quest_3",
        "title_fr": "Quête 3: La Jonction des Fleuves",
        "title_en": "Quest 3: Confluence River Merging",
        "points": 200,
        "location": "Musée des Confluences",
        "desc_fr": "Rendez-vous à la pointe sud de la Presqu'île et photographiez le point de rencontre exact du Rhône et de la Saône.",
        "desc_en": "Go to the southernmost tip of Presqu'île and take a photo where the Rhône and Saône rivers collide."
    }
]

ALBUM_THEMES = {
    "Vintage Map": {"bg": "#F4ECD8", "text": "#451A03", "border": "#78350F", "accent": "#B45309"},
    "Cyberpunk Neon": {"bg": "#0F172A", "text": "#F472B6", "border": "#EC4899", "accent": "#06B6D4"},
    "Minimalist Journal": {"bg": "#FAFAFA", "text": "#1E293B", "border": "#CBD5E1", "accent": "#475569"},
    "Golden Hour": {"bg": "#FFFBEB", "text": "#78350F", "border": "#F59E0B", "accent": "#D97706"},
    "Editorial Magazine": {"bg": "#FFFFFF", "text": "#111827", "border": "#000000", "accent": "#E11D48"},
    "Retro Stamp": {"bg": "#F5EBE0", "text": "#1E3A8A", "border": "#3B82F6", "accent": "#B91C1C"},
    "Dark Elegance": {"bg": "#18181B", "text": "#F3F4F6", "border": "#D4AF37", "accent": "#EAB308"},
    "Pop Art": {"bg": "#FEF08A", "text": "#000000", "border": "#DC2626", "accent": "#2563EB"},
    "Botanical Travel": {"bg": "#F0FDF4", "text": "#14532D", "border": "#166534", "accent": "#15803D"},
    "Classic Blueprint": {"bg": "#0C4A6E", "text": "#E0F2FE", "border": "#0284C7", "accent": "#38BDF8"}
}

CUSTOM_FONTS = [
    "Cinzel", "Playfair Display", "Space Grotesk", "Caveat", "Lobster",
    "Montserrat", "Pacifico", "Oswald", "Syne", "Special Elite"
]

COUPONS_DATA = [
    {
        "id": "c1",
        "title_fr": "Remise 10% - Le Bouchon des Cordeliers",
        "title_en": "10% Discount - Le Bouchon des Cordeliers",
        "cost": 100,
        "vendor": "Le Bouchon des Cordeliers (Presqu'île)",
        "code_prefix": "BOUCHON10"
    },
    {
        "id": "c2",
        "title_fr": "Tartelette Praline Rose Offerte",
        "title_en": "Complimentary Pink Praline Tartlet",
        "cost": 150,
        "vendor": "Boulangerie du Palais (Vieux Lyon)",
        "code_prefix": "PRALINEFREE"
    },
    {
        "id": "c3",
        "title_fr": "Réduction 20% Lyon City Card",
        "title_en": "20% Off Official Lyon City Pass",
        "cost": 200,
        "vendor": "ONLYLYON Tourisme",
        "code_prefix": "LYONCARD20"
    },
    {
        "id": "c4",
        "title_fr": "Voucher Spa 30€ - Villa Florentine 5★",
        "title_en": "€30 Spa Credit - Villa Florentine 5★",
        "cost": 300,
        "vendor": "Villa Florentine (Fourvière)",
        "code_prefix": "FLORENTINE30"
    },
    {
        "id": "c5",
        "title_fr": "Billet Croisière Saône Offert",
        "title_en": "Free River Cruise Ticket",
        "cost": 400,
        "vendor": "Les Bateaux Lyonnais",
        "code_prefix": "CRUISEFREE"
    },
    {
        "id": "c6",
        "title_fr": "Panier Dégustation Gastronomique",
        "title_en": "Gourmet Tasting Basket",
        "cost": 500,
        "vendor": "Les Halles Paul Bocuse",
        "code_prefix": "BOCUSEGOURMET"
    }
]

# ==========================================
# LOGIC: Gemini AI Riddle Generator
# ==========================================
def generate_gemini_riddles(api_key: str):

    # LOGIC: Constructing prompt for Gemini to generate 12 Lyon riddles
    if not GEMINI_AVAILABLE:
        st.error("google-genai library not installed. Using fallback riddles.")
        return DEFAULT_12_RIDDLES

    try:
        client = genai.Client(api_key=api_key)
        prompt = """
        Generate 12 location-bound riddles and trivia questions grounded exclusively in Lyon, France's history, landmarks, gastronomy, and secret spots.
        Return ONLY a JSON array with 12 objects. Each object MUST have:
        - "id": integer 1..12
        - "question_fr": string (riddle in French)
        - "question_en": string (riddle in English)
        - "options": list of 4 strings
        - "answer": string (exact match with one option)
        - "hint": string (helpful location hint in English)
        """
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        parsed = json.loads(response.text)
        if isinstance(parsed, list) and len(parsed) >= 12:
            return parsed[:12]
        else:
            return DEFAULT_12_RIDDLES
    except Exception as e:
        st.warning(f"Could not contact Gemini API ({e}). Defaulting to offline Lyon dataset.")
        return DEFAULT_12_RIDDLES

# ==========================================
# LOGIC: ReportLab PDF Export Engine
# ==========================================
def build_album_pdf(entries, explorer_name, total_points, tier_en):

    if not REPORTLAB_AVAILABLE:
        return None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    story = []
    styles = getSampleStyleSheet()

    # Base PDF Header Style
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1E3A8A'),
        alignment=1,
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=12,
        textColor=colors.HexColor('#4B5563'),
        alignment=1,
        spaceAfter=20
    )

    story.append(Paragraph("Explorer Quest: Lyon Edition", title_style))
    story.append(Paragraph(f"Official Travel Album & Souvenir Log — Explorer: {explorer_name} | Rank: {tier_en} ({total_points} Pts)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1E3A8A'), spaceAfter=15))

    if not entries:
        story.append(Paragraph("No photo album entries recorded yet! Explorer, log your memories to build your album.", styles['Normal']))
    else:
        for idx, entry in enumerate(entries):
            theme_info = ALBUM_THEMES.get(entry['theme'], ALBUM_THEMES['Vintage Map'])
            bg_color = colors.HexColor(theme_info['bg'])
            border_color = colors.HexColor(theme_info['border'])
            text_color = colors.HexColor(theme_info['text'])

            # Section Container Table
            card_data = []

            # Entry Title Header
            entry_title_style = ParagraphStyle(
                f'ETitle_{idx}',
                fontName='Helvetica-Bold',
                fontSize=16,
                leading=18,
                textColor=text_color
            )
            meta_style = ParagraphStyle(
                f'EMeta_{idx}',
                fontName='Helvetica-Oblique',
                fontSize=10,
                leading=12,
                textColor=text_color
            )
            note_style = ParagraphStyle(
                f'ENote_{idx}',
                fontName='Helvetica',
                fontSize=11,
                leading=14,
                textColor=text_color
            )

            card_data.append([Paragraph(f"<b>{entry['title']}</b>", entry_title_style)])
            card_data.append([Paragraph(f"📍 Location: {entry['location']} | 📅 Date: {entry['date']} | Theme: {entry['theme']} ({entry['font']})", meta_style)])

            # Image processing for PDF
            if entry.get('image_bytes'):
                try:
                    img_io = io.BytesIO(entry['image_bytes'])
                    rl_img = RLImage(img_io, width=4.5*inch, height=3.0*inch)
                    card_data.append([rl_img])
                except Exception:
                    card_data.append([Paragraph("[Image Format Error]", meta_style)])

            card_data.append([Paragraph(f"<b>Explorer Notes:</b><br/>{entry['note']}", note_style)])

            # Render Table Box
            entry_table = Table(card_data, colWidths=[6.8*inch])
            entry_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), bg_color),
                ('BOX', (0,0), (-1,-1), 1.5, border_color),
                ('PADDING', (0,0), (-1,-1), 12),
                ('ALIGN', (0,2), (-1,2), 'CENTER'),
                ('BOTTOMPADDING', (0,-1), (-1,-1), 12),
            ]))

            story.append(entry_table)
            story.append(Spacer(1, 18))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# ==========================================
# UI EDITING: Sidebar Navigation & User Info
# ==========================================
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1590082871875-064201a27373?auto=format&fit=crop&w=400&q=80", use_container_width=True)
    st.markdown("### 🦁 Explorer Profile")
    
    explorer_input = st.text_input("Explorer Call Sign / Nom:", value=st.session_state.explorer_name)
    if explorer_input:
        st.session_state.explorer_name = explorer_input

    # Tier Badge Display
    tier_fr, tier_en, badge, next_pts = get_explorer_tier(st.session_state.points)
    
    st.markdown(f"""
    <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 12px; border-radius: 10px; text-align: center; margin-bottom: 15px;">
        <div style="font-size: 2rem;">{badge}</div>
        <div style="font-weight: 700; color: #1E3A8A; font-size: 1.1rem;">{tier_fr}</div>
        <div style="font-size: 0.85rem; color: #64748B;">{tier_en}</div>
        <div style="font-size: 1.4rem; font-weight: 800; color: #D97706; margin-top: 6px;">{st.session_state.points} Pts</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.progress(min(1.0, st.session_state.points / next_pts))
    st.caption(f"Next Rank: {next_pts} Pts")

    st.markdown("---")
    st.markdown("### 🔑 API Configuration")
    user_api_key = st.text_input("Google Gemini API Key:", type="password", help="Enter key to enable dynamic AI Lyon riddle generation.")
    if user_api_key:
        st.session_state.gemini_api_key = user_api_key

    st.markdown("---")
    st.markdown("📍 **Target Coordinates:**")
    st.write("Lyon, France (45.7640° N, 4.8357° E)")
    st.success("GPS Lock Established: Lyon Central Hub")

# ==========================================
# UI EDITING: Main App Title
# ==========================================
dual_header(
    fr_text="Explorer Quest : Édition Lyon",
    en_text="Explorer Quest: Lyon Edition — Interactive AI Travel Companion & Souvenir Studio",
    level=1,
    icon="🦁"
)

# Tabs Definition
tab1, tab2, tab3, tab4 = st.tabs([
    "📍 Guide Interactif\nInteractive Lyon Hub",
    "🧩 Énigmes & Quêtes\nAI Riddles & Quests",
    "📸 Album Studio & PDF\nExplorer Album Studio",
    "🎟️ Boutique de Coupons\nReal-World Store"
])

# ==========================================
# TAB 1: LYON LOCATION HUB (GUIDE INTERACTIF)
# ==========================================
with tab1:
    dual_header("Les Incontournables de Lyon", "Must-Visit Iconic Places in Lyon", level=2, icon="🏛️")
    st.info("👋 Bonjour Explorer! Welcome to Lyon, France. Explore history, secrets, architecture, and gastronomy across the city.")

    # Lyon Overview Columns
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("**📜 Histoire & Traboules**")
        st.caption("Founded in 43 BC by Romans as Lugdunum. Famous for silk weaving (Canuts) and subterranean passages.")
    with col_b:
        st.markdown("**🍽️ Capitale de la Gastronomie**")
        st.caption("Home of traditional Bouchons, Paul Bocuse, quenelles, saucisson brioché, and pink pralines.")
    with col_c:
        st.markdown("**✨ Fête des Lumières**")
        st.caption("Annual light festival in December drawing millions of visitors to illuminate Lyon's monuments.")

    st.markdown("---")

    # Landmark Photo Cards Grid
    grid_col1, grid_col2 = st.columns(2)
    for index, landmark in enumerate(LYON_LANDMARKS):
        target_col = grid_col1 if index % 2 == 0 else grid_col2
        with target_col:
            st.markdown(f"""
            <div class="landmark-card">
                <img src="{landmark['image']}" style="width:100%; height:200px; object-fit:cover; border-radius:8px; margin-bottom:10px;">
                <span style="background-color:#DBEAFE; color:#1E40AF; padding:3px 8px; border-radius:12px; font-size:0.75rem; font-weight:600;">{landmark['tag']}</span>
                <h3 style="margin-top:8px; margin-bottom:2px; color:#1E3A8A;">{landmark['name_fr']}</h3>
                <div style="font-size:0.9rem; color:#4B5563; font-style:italic; margin-bottom:8px;">{landmark['name_en']}</div>
                <p style="font-size:0.9rem; color:#334155;"><b>FR:</b> {landmark['desc_fr']}</p>
                <p style="font-size:0.9rem; color:#475569;"><b>EN:</b> {landmark['desc_en']}</p>
                <div style="background-color:#FEF3C7; border-left:4px solid #F59E0B; padding:8px; border-radius:4px; font-size:0.85rem; margin-top:8px;">
                    💡 <b>Cool Fact:</b> {landmark['fact_en']}
                </div>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# TAB 2: AI RIDDLES & QUESTS (ÉNIGMES & QUÊTES)
# ==========================================
with tab2:
    dual_header("Énigmes et Quêtes Lyonnaises", "Lyon Riddles & Real-Life Photo Quests", level=2, icon="🧩")
    st.write(f"Greetings, **Explorer {st.session_state.explorer_name}**! Complete riddles (+50 pts) and real-life photo quests (+200 pts) to unlock higher explorer ranks and store vouchers.")

    # AI Refresh Logic
    col_gen1, col_gen2 = st.columns([3, 1])
    with col_gen1:
        st.caption("Riddles are grounded exclusively in Lyon's secret spots, history, and culinary lore.")
    with col_gen2:
        if st.button("🔄 Générer avec IA / Refresh AI", use_container_width=True):
            api_key_to_use = st.session_state.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY")
            with st.spinner("Gemini AI is crafting 12 new Lyon riddles..."):
                st.session_state.custom_riddles = generate_gemini_riddles(api_key_to_use)
                st.success("New Lyon Riddles Loaded!")

    active_riddles = st.session_state.custom_riddles or DEFAULT_12_RIDDLES

    # Riddles Accordion / Expander Grid
    st.markdown("### 🏛️ 12 Location Riddles (50 Points Each)")
    riddle_cols = st.columns(2)

    for idx, r in enumerate(active_riddles):
        c_target = riddle_cols[idx % 2]
        r_id = r['id']
        is_done = r_id in st.session_state.completed_riddles

        with c_target:
            with st.expander(f"Énigme #{r_id}: {r['question_fr'][:40]}... {'✅' if is_done else '🔒'}"):
                st.markdown(f"**FR:** {r['question_fr']}")
                st.markdown(f"*EN:* {r['question_en']}")
                st.caption(f"💡 Hint: {r.get('hint', 'Explore Lyon!')}")

                if is_done:
                    st.success("✅ Riddle Solved! +50 Points Awarded.")
                else:
                    user_choice = st.radio(f"Select Answer for #{r_id}:", r['options'], key=f"riddle_opt_{r_id}")
                    if st.button(f"Submit Answer #{r_id}", key=f"btn_riddle_{r_id}"):
                        if user_choice == r['answer']:
                            st.session_state.points += 50
                            st.session_state.completed_riddles.add(r_id)
                            st.balloons()
                            st.success(f"Bravo Explorer! Correct answer: {r['answer']} (+50 Pts)")
                            st.rerun()
                        else:
                            st.error("Incorrect answer! Try again, Explorer.")

    st.markdown("---")
    dual_header("Quêtes Photo du Monde Réel", "Real-Life Photo Quests (High Reward: 200 Pts)", level=2, icon="📸")

    quest_cols = st.columns(3)
    for q_idx, q in enumerate(REAL_LIFE_QUESTS):
        with quest_cols[q_idx]:
            q_id = q['id']
            is_q_done = q_id in st.session_state.completed_quests

            st.markdown(f"""
            <div class="landmark-card" style="border: 2px solid {'#10B981' if is_q_done else '#3B82F6'};">
                <div style="font-weight:700; color:#1E3A8A; font-size:1.1rem;">{q['title_fr']}</div>
                <div style="font-size:0.85rem; color:#64748B; font-style:italic;">{q['title_en']}</div>
                <div style="color:#D97706; font-weight:bold; margin-top:5px;">🏆 Reward: {q['points']} Pts</div>
                <div style="font-size:0.85rem; color:#334155; margin-top:8px;"><b>📍 Location:</b> {q['location']}</div>
                <p style="font-size:0.85rem; margin-top:6px;">{q['desc_en']}</p>
            </div>
            """, unsafe_allow_html=True)

            if is_q_done:
                st.success("✅ Quest Completed!")
                if st.session_state.completed_quests[q_id].get("img"):
                    st.image(st.session_state.completed_quests[q_id]["img"], caption="Uploaded Quest Proof", use_container_width=True)
            else:
                uploaded_proof = st.file_uploader(f"Upload Photo Proof ({q_id}):", type=["jpg", "jpeg", "png"], key=f"file_{q_id}")
                quest_loc_note = st.text_input(f"Log Location Note ({q_id}):", key=f"txt_{q_id}", placeholder="e.g., 54 Rue Saint-Jean Traboule")
                
                if st.button(f"Log & Complete {q_id}", key=f"submit_{q_id}"):
                    if uploaded_proof is not None:
                        st.session_state.points += q['points']
                        st.session_state.completed_quests[q_id] = {
                            "img": uploaded_proof.getvalue(),
                            "note": quest_loc_note
                        }
                        st.balloons()
                        st.success(f"Awesome job Explorer! Quest completed (+{q['points']} Pts)!")
                        st.rerun()
                    else:
                        st.warning("Please upload a photo proof to claim your reward, Explorer!")

# ==========================================
# TAB 3: EXPLORER ALBUM STUDIO & PDF EXPORT
# ==========================================
with tab3:
    dual_header("Studio d'Album Photo & Export PDF", "Explorer Album Studio & PDF Export Engine", level=2, icon="🎨")
    st.write("Customize your travel photos with 10 visual themes and 10 custom typography styles, then export your album as a downloadable PDF.")

    col_edit, col_prev = st.columns([1, 1])

    with col_edit:
        st.markdown("### 🖋️ Create New Album Entry")
        entry_title = st.text_input("Entry Title / Titre:", value="Flânerie dans le Vieux Lyon")
        entry_location = st.text_input("Location / Lieu:", value="Traboule de la Rue Saint-Jean, Lyon")
        entry_note = st.text_area("Explorer Travel Notes / Notes de voyage:", value="Discovered an astonishing gothic spiral staircase tucked inside a quiet courtyard. The atmosphere was pure magic!")
        
        col_th, col_fo = st.columns(2)
        with col_th:
            selected_theme = st.selectbox("Visual Theme (10 Styles):", list(ALBUM_THEMES.keys()))
        with col_fo:
            selected_font = st.selectbox("Typography Font (10 Fonts):", CUSTOM_FONTS)

        entry_img = st.file_uploader("Upload Album Photo:", type=["jpg", "jpeg", "png"], key="album_img_uploader")

        if st.button("➕ Add Entry to Album / Ajouter à l'Album", use_container_width=True):
            img_bytes = entry_img.getvalue() if entry_img else None
            new_entry = {
                "title": entry_title,
                "location": entry_location,
                "note": entry_note,
                "theme": selected_theme,
                "font": selected_font,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "image_bytes": img_bytes
            }
            st.session_state.album_entries.append(new_entry)
            st.success("Entry added to Explorer Album!")

    with col_prev:
        st.markdown("### 👁️ Live Album Preview")
        if not st.session_state.album_entries:
            st.info("No entries added yet. Use the editor on the left to add your first photo memory!")
        else:
            for idx, item in enumerate(st.session_state.album_entries):
                theme_cfg = ALBUM_THEMES[item["theme"]]
                st.markdown(f"""
                <div style="background-color:{theme_cfg['bg']}; border:3px solid {theme_cfg['border']}; color:{theme_cfg['text']}; padding:16px; border-radius:12px; margin-bottom:15px; font-family:'{item['font']}', serif;">
                    <div style="font-size:1.3rem; font-weight:bold; color:{theme_cfg['accent']};">{item['title']}</div>
                    <div style="font-size:0.85rem; opacity:0.8;">📍 {item['location']} | 📅 {item['date']}</div>
                    <div style="font-size:0.8rem; background-color:rgba(0,0,0,0.05); padding:2px 6px; border-radius:4px; display:inline-block; margin-top:4px;">Theme: {item['theme']} | Font: {item['font']}</div>
                    <p style="margin-top:10px;">{item['note']}</p>
                </div>
                """, unsafe_allow_html=True)
                if item["image_bytes"]:
                    st.image(item["image_bytes"], use_container_width=True)

    st.markdown("---")
    dual_header("Générateur d'Exportation PDF", "Export Complete Album to PDF File", level=2, icon="📄")

    col_pdf1, col_pdf2 = st.columns([2, 1])
    with col_pdf1:
        st.write("Generates a professionally formatted, downloadable PDF travel log complete with theme styling, photo entries, notes, and Explorer tier rank.")
    with col_pdf2:
        if st.button("📄 Generate PDF Album / Générer PDF", use_container_width=True):
            if not REPORTLAB_AVAILABLE:
                st.error("ReportLab is not installed. Please install `reportlab` to render PDF files.")
            else:
                pdf_bytes = build_album_pdf(
                    entries=st.session_state.album_entries,
                    explorer_name=st.session_state.explorer_name,
                    total_points=st.session_state.points,
                    tier_en=tier_en
                )
                if pdf_bytes:
                    st.download_button(
                        label="💾 Download PDF Album",
                        data=pdf_bytes,
                        file_name=f"Explorer_Quest_Lyon_{st.session_state.explorer_name}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    st.success("PDF Generated Successfully!")

# ==========================================
# TAB 4: REAL-WORLD COUPON STORE (BOUTIQUE)
# ==========================================
with tab4:
    dual_header("Boutique de Vouchers Lyon", "Real-World Lyon Coupon Store", level=2, icon="🎟️")
    st.write(f"Redeem your earned quest points (**Current Balance: {st.session_state.points} Pts**) for real vouchers at authentic Lyon bouchons, bakery shops, and hotels.")

    # Display Coupon Cards Grid
    c_store1, c_store2 = st.columns(2)
    for c_idx, coupon in enumerate(COUPONS_DATA):
        target_store_col = c_store1 if c_idx % 2 == 0 else c_store2
        is_redeemed = coupon['id'] in [r['id'] for r in st.session_state.redeemed_coupons]

        with target_store_col:
            st.markdown(f"""
            <div class="landmark-card" style="border-left: 5px solid {'#10B981' if is_redeemed else '#F59E0B'};">
                <div style="font-size:1.1rem; font-weight:bold; color:#1E3A8A;">{coupon['title_fr']}</div>
                <div style="font-size:0.85rem; color:#64748B; font-style:italic;">{coupon['title_en']}</div>
                <div style="margin-top:6px; font-size:0.9rem; color:#334155;">🏬 <b>Partner Vendor:</b> {coupon['vendor']}</div>
                <div style="font-size:1.1rem; font-weight:800; color:#D97706; margin-top:6px;">🏷️ Cost: {coupon['cost']} Pts</div>
            </div>
            """, unsafe_allow_html=True)

            if is_redeemed:
                redeemed_entry = next(r for r in st.session_state.redeemed_coupons if r['id'] == coupon['id'])
                st.success(f"✅ Redeemed! Voucher Code: `{redeemed_entry['code']}`")
            else:
                can_afford = st.session_state.points >= coupon['cost']
                if st.button(f"Échanger ({coupon['cost']} Pts) / Redeem", key=f"btn_cp_{coupon['id']}", disabled=not can_afford):
                    st.session_state.points -= coupon['cost']
                    unique_code = f"{coupon['code_prefix']}-{random.randint(1000, 9999)}"
                    st.session_state.redeemed_coupons.append({
                        "id": coupon['id'],
                        "code": unique_code,
                        "title": coupon['title_en']
                    })
                    st.balloons()
                    st.success(f"Voucher Claimed! Use Code: {unique_code}")
                    st.rerun()

    if st.session_state.redeemed_coupons:
        st.markdown("---")
        dual_header("Vos Vouchers Échangés", "Your Claimed Vouchers Wallet", level=2, icon="👛")
        for r_item in st.session_state.redeemed_coupons:
            st.info(f"🎫 **{r_item['title']}** — Redemption Code: `{r_item['code']}` (Present to partner in Lyon)")