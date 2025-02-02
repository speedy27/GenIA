from fpdf import FPDF
from datetime import datetime

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, "Analyse des Risques Climatiques, Environnementaux et Financiers", ln=True, align='C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def add_section(self, title, content):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, title, ln=True)
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 8, content)
        self.ln(5)

# Création du PDF
pdf = PDFReport()
pdf.add_page()

# Données fictives pour la commune
data = {
    "commune": "[Nom de la Commune]",
    "date": datetime.now().strftime("%d/%m/%Y"),
    "dicrim_date": "[Date]",
    "risques_identifies": "[Inondations, mouvements de terrain, canicules, etc.]",
    "mesures_prevention": "[Description des mesures]",
    "budget_alloue": "[Montant]",
    "depenses_prevention": "[Montant]",
    "subventions": "[Détails des aides reçues]",
    "recommandations": "[Détails des recommandations]"
}

# Sections du rapport
pdf.add_section("Commune : " + data["commune"], f"Date du rapport : {data['date']}")

intro = ("Ce rapport présente une analyse des risques climatiques, environnementaux et financiers pour la commune de "
        f"{data['commune']}. Il repose sur des données extraites de documents officiels tels que le DICRIM, PCAET, PLU/PLUi, "
        "SCoT, SRADDET, et des données financières associées.")
pdf.add_section("1. Introduction", intro)

dicrim = (f"Date de publication : {data['dicrim_date']}\n"
          f"Principaux risques identifiés : {data['risques_identifies']}\n"
          f"Mesures de prévention en place : {data['mesures_prevention']}")
pdf.add_section("2. Synthèse des Documents d'Urbanisme et de Planification", dicrim)

finances = (f"Budget alloué à la gestion des risques : {data['budget_alloue']}\n"
            f"Dépenses annuelles en matière de prévention : {data['depenses_prevention']}\n"
            f"Subventions et financements externes : {data['subventions']}")
pdf.add_section("3. Analyse Financière", finances)

recommandations = (f"1. {data['recommandations']}\n"
                   "2. Amélioration des systèmes d'alerte et de prévention\n"
                   "3. Optimisation de l'utilisation des ressources financières\n"
                   "4. Sensibilisation des populations")
pdf.add_section("4. Recommandations", recommandations)

# Sauvegarde du PDF
pdf_output = "rapport_analyse_risques.pdf"
pdf.output(pdf_output)

print(f"PDF généré avec succès : {pdf_output}")
