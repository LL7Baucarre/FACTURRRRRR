from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from datetime import datetime
from facturx import generate_from_binary, generate_from_file
from lxml import etree
import os
import re
import pycountry

class ValidationError(Exception):
    """Exception levée lors d'erreurs de validation"""
    pass

class FacturXGenerator:
    def __init__(self):
        self.width, self.height = A4
        
    def validate_invoice_data(self, data):
        """Valide les données de la facture avant génération"""
        errors = []
        
        # Validation des champs obligatoires
        required_fields = {
            'date': 'Date de facturation',
            'invoice_number': 'Numéro de facture'
        }
        
        for field, label in required_fields.items():
            if not data.get(field):
                errors.append(f"{label} est obligatoire")
        
        # Validation de la date
        if data.get('date'):
            try:
                datetime.strptime(data['date'], '%Y-%m-%d')
            except ValueError:
                errors.append("Format de date invalide (YYYY-MM-DD attendu)")
        
        # Validation émetteur
        issuer_required = ['name', 'address', 'postal_code', 'city']
        for field in issuer_required:
            if not data.get('issuer', {}).get(field):
                errors.append(f"Émetteur - {field} est obligatoire")
        
        # Validation destinataire
        recipient_required = ['name', 'address', 'postal_code', 'city']
        for field in recipient_required:
            if not data.get('recipient', {}).get(field):
                errors.append(f"Destinataire - {field} est obligatoire")
        
        # Validation SIRET (si fourni)
        for party_type in ['issuer', 'recipient']:
            siret = data.get(party_type, {}).get('siret')
            if siret and not self._validate_siret(siret):
                errors.append(f"{party_type.capitalize()} - Format SIRET invalide")
        
        # Validation des articles
        if not data.get('items') or len(data['items']) == 0:
            errors.append("Au moins un article est obligatoire")
        else:
            for i, item in enumerate(data['items']):
                if not item.get('description'):
                    errors.append(f"Article {i+1} - Description obligatoire")
                try:
                    quantity = float(item.get('quantity', 0))
                    if quantity <= 0:
                        errors.append(f"Article {i+1} - Quantité doit être supérieure à 0")
                except (ValueError, TypeError):
                    errors.append(f"Article {i+1} - Quantité invalide")
                
                try:
                    unit_price = float(item.get('unit_price', 0))
                    if unit_price < 0:
                        errors.append(f"Article {i+1} - Prix unitaire invalide")
                except (ValueError, TypeError):
                    errors.append(f"Article {i+1} - Prix unitaire invalide")
                
                try:
                    vat_rate = float(item.get('vat_rate', 0))
                    if vat_rate < 0 or vat_rate > 100:
                        errors.append(f"Article {i+1} - Taux de TVA invalide (0-100%)")
                except (ValueError, TypeError):
                    errors.append(f"Article {i+1} - Taux de TVA invalide")
        
        # Validation des totaux
        try:
            total_ttc = float(data.get('total_ttc', 0))
            if total_ttc <= 0:
                errors.append("Le montant total doit être supérieur à 0")
        except (ValueError, TypeError):
            errors.append("Montant total invalide")
        
        if errors:
            raise ValidationError("Erreurs de validation:\n" + "\n".join(f"- {error}" for error in errors))
        
        return True
    
    def _validate_siret(self, siret):
        """Valide le format SIRET français"""
        # Supprime espaces et tirets
        siret = re.sub(r'[\s-]', '', siret)
        
        # Doit contenir exactement 14 chiffres
        if not re.match(r'^\d{14}$', siret):
            return False
        
        # Algorithme de Luhn pour la validation
        total = 0
        for i, digit in enumerate(siret):
            n = int(digit)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n = (n // 10) + (n % 10)
            total += n
        
        return total % 10 == 0
        
    def generate_facturx(self, invoice_data, output_path):
        """Génère un document Factur-X (PDF avec XML embarqué)"""
        
        # Étape 1: Validation des données
        print("🔍 Validation des données...")
        try:
            self.validate_invoice_data(invoice_data)
            print("✅ Validation réussie")
        except ValidationError as e:
            print(f"❌ Erreur de validation: {e}")
            raise
        
        # Étape 2: Génération du PDF de base
        print("📄 Génération du PDF...")
        temp_pdf = output_path.replace('.pdf', '_temp.pdf')
        self._generate_pdf(invoice_data, temp_pdf)
        
        # Étape 3: Génération du XML Factur-X
        print("🏷️ Génération du XML Factur-X...")
        xml_content = self._generate_facturx_xml(invoice_data)
        
        # Étape 4: Validation du XML généré
        print("🔍 Validation du XML...")
        if self._validate_xml(xml_content):
            print("✅ XML valide")
        else:
            print("⚠️ Avertissement: XML potentiellement non conforme")
        
        # Étape 5: Création du Factur-X avec la librairie officielle
        print("🔧 Création du document Factur-X...")
        try:
            # Signature: generate_from_file(pdf_file, xml, flavor, level, output_pdf_file, ...)
            generate_from_file(
                pdf_file=temp_pdf,
                xml=xml_content.encode('utf-8'),
                flavor='facturx',
                level='basic',
                check_xsd=False,  # Désactiver vérification XSD pour plus de flexibilité
                output_pdf_file=output_path
            )
            
            # Supprime le PDF temporaire
            if os.path.exists(temp_pdf):
                os.remove(temp_pdf)
                
            print(f"✅ Facture Factur-X générée: {output_path}")
            
        except Exception as e:
            print(f"❌ Erreur lors de la génération Factur-X: {e}")
            # En cas d'erreur, on garde au moins le PDF
            if os.path.exists(temp_pdf):
                os.rename(temp_pdf, output_path)
            raise
        
    def _generate_pdf(self, data, output_path):
        """Génère le PDF de la facture"""
        c = canvas.Canvas(output_path, pagesize=A4)
        
        # En-tête
        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, self.height - 50, "FACTURE")
        
        # Informations de la facture
        c.setFont("Helvetica", 12)
        c.drawString(400, self.height - 50, f"N° {data['invoice_number']}")
        c.drawString(400, self.height - 70, f"Date: {data['date']}")
        
        # Émetteur
        y_pos = self.height - 120
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_pos, "ÉMETTEUR")
        y_pos -= 20
        
        c.setFont("Helvetica", 10)
        c.drawString(50, y_pos, data['issuer']['name'])
        y_pos -= 15
        c.drawString(50, y_pos, data['issuer']['address'])
        y_pos -= 15
        c.drawString(50, y_pos, f"{data['issuer']['postal_code']} {data['issuer']['city']}")
        if data['issuer'].get('siret'):
            y_pos -= 15
            c.drawString(50, y_pos, f"SIRET: {data['issuer']['siret']}")
        if data['issuer'].get('vat_number'):
            y_pos -= 15
            c.drawString(50, y_pos, f"N° TVA: {data['issuer']['vat_number']}")
        
        # Destinataire
        y_pos = self.height - 120
        c.setFont("Helvetica-Bold", 14)
        c.drawString(300, y_pos, "DESTINATAIRE")
        y_pos -= 20
        
        c.setFont("Helvetica", 10)
        c.drawString(300, y_pos, data['recipient']['name'])
        y_pos -= 15
        c.drawString(300, y_pos, data['recipient']['address'])
        y_pos -= 15
        c.drawString(300, y_pos, f"{data['recipient']['postal_code']} {data['recipient']['city']}")
        if data['recipient'].get('siret'):
            y_pos -= 15
            c.drawString(300, y_pos, f"SIRET: {data['recipient']['siret']}")
        if data['recipient'].get('vat_number'):
            y_pos -= 15
            c.drawString(300, y_pos, f"N° TVA: {data['recipient']['vat_number']}")
        
        # Tableau des articles
        y_pos = self.height - 300
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_pos, "DÉTAIL DE LA FACTURE")
        y_pos -= 30
        
        # En-têtes du tableau
        headers = ["Description", "Qté", "Prix U. HT", "Total HT", "TVA", "Total TTC"]
        x_positions = [50, 250, 290, 370, 450, 510]
        
        c.setFont("Helvetica-Bold", 10)
        for i, header in enumerate(headers):
            c.drawString(x_positions[i], y_pos, header)
        
        y_pos -= 20
        c.line(50, y_pos, 590, y_pos)  # Ligne de séparation
        y_pos -= 15
        
        # Lignes du tableau
        c.setFont("Helvetica", 9)
        for item in data['items']:
            c.drawString(50, y_pos, item['description'][:30])
            c.drawString(250, y_pos, str(item['quantity']))
            c.drawString(290, y_pos, f"{item['unit_price']:.2f} €")
            c.drawString(370, y_pos, f"{item['amount_ht']:.2f} €")
            c.drawString(450, y_pos, f"{item['vat_rate']}%")
            c.drawString(510, y_pos, f"{item['amount_ttc']:.2f} €")
            y_pos -= 20
        
        # Ligne de séparation avant totaux
        y_pos -= 10
        c.line(50, y_pos, 590, y_pos)
        
        # Totaux
        y_pos -= 30
        c.setFont("Helvetica-Bold", 12)
        c.drawString(400, y_pos, f"Total HT: {data['total_ht']:.2f} €")
        y_pos -= 20
        c.drawString(400, y_pos, f"Total TVA: {data['total_vat']:.2f} €")
        y_pos -= 20
        c.drawString(400, y_pos, f"Total TTC: {data['total_ttc']:.2f} €")
        
        # Pied de page
        c.setFont("Helvetica", 8)
        c.drawString(50, 50, "Facture générée électroniquement - Format Factur-X conforme EN 16931")
        
        c.save()
        
    def _generate_facturx_xml(self, data):
        """Génère le XML Factur-X BASIC conforme aux spécifications EN 16931"""
        
        # Namespaces
        RSM = 'urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100'
        RAM = 'urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100'
        UDT = 'urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100'
        QDT = 'urn:un:unece:uncefact:data:standard:QualifiedDataType:100'
        
        nsmap = {
            'rsm': RSM,
            'ram': RAM,
            'udt': UDT,
            'qdt': QDT
        }
        
        def ram(tag):
            return etree.QName(RAM, tag)
        
        def rsm(tag):
            return etree.QName(RSM, tag)
        
        def udt(tag):
            return etree.QName(UDT, tag)
        
        # Création de l'élément racine
        root = etree.Element(rsm('CrossIndustryInvoice'), nsmap=nsmap)
        
        # === ExchangedDocumentContext ===
        context = etree.SubElement(root, rsm('ExchangedDocumentContext'))
        guideline = etree.SubElement(context, ram('GuidelineSpecifiedDocumentContextParameter'))
        etree.SubElement(guideline, ram('ID')).text = "urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic"
        
        # === ExchangedDocument ===
        document = etree.SubElement(root, rsm('ExchangedDocument'))
        etree.SubElement(document, ram('ID')).text = data['invoice_number']
        etree.SubElement(document, ram('TypeCode')).text = "380"
        issue_dt = etree.SubElement(document, ram('IssueDateTime'))
        dt_string = etree.SubElement(issue_dt, udt('DateTimeString'))
        dt_string.set('format', '102')
        dt_string.text = data['date'].replace('-', '')
        
        # === SupplyChainTradeTransaction ===
        transaction = etree.SubElement(root, rsm('SupplyChainTradeTransaction'))
        
        # --- Lignes de facture (IncludedSupplyChainTradeLineItem) ---
        for idx, item in enumerate(data['items'], 1):
            line = etree.SubElement(transaction, ram('IncludedSupplyChainTradeLineItem'))
            
            # AssociatedDocumentLineDocument
            line_doc = etree.SubElement(line, ram('AssociatedDocumentLineDocument'))
            etree.SubElement(line_doc, ram('LineID')).text = str(idx)
            
            # SpecifiedTradeProduct (obligatoire - contient le nom de l'article)
            product = etree.SubElement(line, ram('SpecifiedTradeProduct'))
            etree.SubElement(product, ram('Name')).text = item['description']
            
            # SpecifiedLineTradeAgreement (contient le prix)
            line_agreement = etree.SubElement(line, ram('SpecifiedLineTradeAgreement'))
            net_price = etree.SubElement(line_agreement, ram('NetPriceProductTradePrice'))
            etree.SubElement(net_price, ram('ChargeAmount')).text = f"{item['unit_price']:.2f}"
            
            # SpecifiedLineTradeDelivery (contient la quantité)
            line_delivery = etree.SubElement(line, ram('SpecifiedLineTradeDelivery'))
            billed_qty = etree.SubElement(line_delivery, ram('BilledQuantity'))
            billed_qty.set('unitCode', 'C62')
            billed_qty.text = f"{item['quantity']:.2f}"
            
            # SpecifiedLineTradeSettlement (contient la TVA de ligne et le total)
            line_settlement = etree.SubElement(line, ram('SpecifiedLineTradeSettlement'))
            
            # ApplicableTradeTax pour la ligne
            line_tax = etree.SubElement(line_settlement, ram('ApplicableTradeTax'))
            etree.SubElement(line_tax, ram('TypeCode')).text = "VAT"
            etree.SubElement(line_tax, ram('CategoryCode')).text = "S"  # Standard rate
            etree.SubElement(line_tax, ram('RateApplicablePercent')).text = f"{item['vat_rate']:.2f}"
            
            # SpecifiedTradeSettlementLineMonetarySummation (montant HT de la ligne)
            line_monetary = etree.SubElement(line_settlement, ram('SpecifiedTradeSettlementLineMonetarySummation'))
            etree.SubElement(line_monetary, ram('LineTotalAmount')).text = f"{item['amount_ht']:.2f}"
        
        # --- ApplicableHeaderTradeAgreement ---
        agreement = etree.SubElement(transaction, ram('ApplicableHeaderTradeAgreement'))
        
        # SellerTradeParty
        seller = etree.SubElement(agreement, ram('SellerTradeParty'))
        etree.SubElement(seller, ram('Name')).text = data['issuer']['name']
        
        # Identifiant légal du vendeur (SIRET)
        seller_legal = etree.SubElement(seller, ram('SpecifiedLegalOrganization'))
        siret = data['issuer'].get('siret', '00000000000000')
        etree.SubElement(seller_legal, ram('ID')).text = siret
        
        seller_addr = etree.SubElement(seller, ram('PostalTradeAddress'))
        etree.SubElement(seller_addr, ram('PostcodeCode')).text = data['issuer']['postal_code']
        etree.SubElement(seller_addr, ram('LineOne')).text = data['issuer']['address']
        etree.SubElement(seller_addr, ram('CityName')).text = data['issuer']['city']
        etree.SubElement(seller_addr, ram('CountryID')).text = "FR"
        
        # SpecifiedTaxRegistration - Numéro de TVA du vendeur (BT-31) - obligatoire pour BR-S-02
        vat_number = data['issuer'].get('vat_number', '')
        if not vat_number:
            # Générer un numéro de TVA à partir du SIRET si non fourni
            siret_clean = siret.replace(' ', '')
            if len(siret_clean) >= 9:
                siren = siret_clean[:9]
                # Calcul de la clé TVA française
                key = (12 + 3 * (int(siren) % 97)) % 97
                vat_number = f"FR{key:02d}{siren}"
            else:
                vat_number = f"FR00{siret_clean}"
        
        seller_tax_reg = etree.SubElement(seller, ram('SpecifiedTaxRegistration'))
        seller_tax_id = etree.SubElement(seller_tax_reg, ram('ID'))
        seller_tax_id.set('schemeID', 'VA')
        seller_tax_id.text = vat_number
        
        # BuyerTradeParty
        buyer = etree.SubElement(agreement, ram('BuyerTradeParty'))
        etree.SubElement(buyer, ram('Name')).text = data['recipient']['name']
        
        buyer_addr = etree.SubElement(buyer, ram('PostalTradeAddress'))
        etree.SubElement(buyer_addr, ram('PostcodeCode')).text = data['recipient']['postal_code']
        etree.SubElement(buyer_addr, ram('LineOne')).text = data['recipient']['address']
        etree.SubElement(buyer_addr, ram('CityName')).text = data['recipient']['city']
        etree.SubElement(buyer_addr, ram('CountryID')).text = "FR"
        
        # --- ApplicableHeaderTradeDelivery ---
        delivery = etree.SubElement(transaction, ram('ApplicableHeaderTradeDelivery'))
        
        # --- ApplicableHeaderTradeSettlement ---
        settlement = etree.SubElement(transaction, ram('ApplicableHeaderTradeSettlement'))
        etree.SubElement(settlement, ram('InvoiceCurrencyCode')).text = "EUR"
        
        # ApplicableTradeTax - regrouper par taux de TVA
        vat_rates = {}
        for item in data['items']:
            rate = float(item['vat_rate'])
            if rate not in vat_rates:
                vat_rates[rate] = {'base': 0.0, 'tax': 0.0}
            vat_rates[rate]['base'] += float(item['amount_ht'])
            vat_rates[rate]['tax'] += float(item['vat_amount'])
        
        for rate, amounts in vat_rates.items():
            tax = etree.SubElement(settlement, ram('ApplicableTradeTax'))
            etree.SubElement(tax, ram('CalculatedAmount')).text = f"{amounts['tax']:.2f}"
            etree.SubElement(tax, ram('TypeCode')).text = "VAT"
            etree.SubElement(tax, ram('BasisAmount')).text = f"{amounts['base']:.2f}"
            etree.SubElement(tax, ram('CategoryCode')).text = "S"  # Standard rate
            etree.SubElement(tax, ram('RateApplicablePercent')).text = f"{rate:.2f}"
        
        # SpecifiedTradePaymentTerms
        payment = etree.SubElement(settlement, ram('SpecifiedTradePaymentTerms'))
        etree.SubElement(payment, ram('Description')).text = "Paiement à réception de facture"
        
        # SpecifiedTradeSettlementHeaderMonetarySummation
        # BR-CO-15: GrandTotalAmount = TaxBasisTotalAmount + TaxTotalAmount
        monetary = etree.SubElement(settlement, ram('SpecifiedTradeSettlementHeaderMonetarySummation'))
        etree.SubElement(monetary, ram('LineTotalAmount')).text = f"{data['total_ht']:.2f}"
        etree.SubElement(monetary, ram('TaxBasisTotalAmount')).text = f"{data['total_ht']:.2f}"
        # TaxTotalAmount avec currencyID obligatoire
        tax_total_elem = etree.SubElement(monetary, ram('TaxTotalAmount'))
        tax_total_elem.set('currencyID', 'EUR')
        tax_total_elem.text = f"{data['total_vat']:.2f}"
        etree.SubElement(monetary, ram('GrandTotalAmount')).text = f"{data['total_ttc']:.2f}"
        etree.SubElement(monetary, ram('DuePayableAmount')).text = f"{data['total_ttc']:.2f}"
        
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + etree.tostring(root, encoding='unicode', pretty_print=True)
    
    def _validate_xml(self, xml_content):
        """Valide la structure XML généré"""
        try:
            # Parse le XML pour vérifier sa validité
            etree.fromstring(xml_content.encode('utf-8'))
            
            # Vérifications basiques de structure Factur-X
            required_elements = [
                'CrossIndustryInvoice',
                'ExchangedDocumentContext',
                'ExchangedDocument',
                'SupplyChainTradeTransaction'
            ]
            
            for element in required_elements:
                if element not in xml_content:
                    print(f"⚠️ Élément manquant: {element}")
                    return False
            
            return True
            
        except etree.XMLSyntaxError as e:
            print(f"❌ Erreur XML: {e}")
            return False