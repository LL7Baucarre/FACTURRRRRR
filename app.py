from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from datetime import datetime
import os
from facturx_generator import FacturXGenerator, ValidationError

app = Flask(__name__)
app.secret_key = 'votre_cle_secrete_ici'

# Configuration
UPLOAD_FOLDER = 'generated_invoices'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('invoice_form.html')

@app.route('/generate_invoice', methods=['POST'])
def generate_invoice():
    try:
        # Récupération des données du formulaire
        invoice_data = {
            'date': request.form['date'],
            'invoice_number': request.form['invoice_number'],  # Obligatoire
            'issuer': {
                'name': request.form['issuer_name'],
                'address': request.form['issuer_address'],
                'postal_code': request.form['issuer_postal'],
                'city': request.form['issuer_city'],
                'siret': request.form.get('issuer_siret', ''),
                'vat_number': request.form.get('issuer_vat', '')
            },
            'recipient': {
                'name': request.form['recipient_name'],
                'address': request.form['recipient_address'],
                'postal_code': request.form['recipient_postal'],
                'city': request.form['recipient_city'],
                'siret': request.form.get('recipient_siret', ''),
                'vat_number': request.form.get('recipient_vat', '')
            },
            'items': []
        }
        
        # Traitement des lignes de facture
        descriptions = request.form.getlist('description[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')
        vat_rates = request.form.getlist('vat_rate[]')
        
        for i in range(len(descriptions)):
            if descriptions[i]:  # Ne traiter que les lignes non vides
                quantity = float(quantities[i])
                unit_price = float(unit_prices[i])
                vat_rate_percent = float(vat_rates[i])  # Taux en pourcentage
                vat_rate_decimal = vat_rate_percent / 100  # Taux en décimal
                
                amount_ht = quantity * unit_price
                vat_amount = amount_ht * vat_rate_decimal
                amount_ttc = amount_ht + vat_amount
                
                invoice_data['items'].append({
                    'description': descriptions[i],
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'amount_ht': amount_ht,
                    'vat_rate': vat_rate_percent,  # Stocké en pourcentage (20 pour 20%)
                    'vat_amount': vat_amount,
                    'amount_ttc': amount_ttc
                })
        
        # Calcul des totaux
        total_ht = sum(item['amount_ht'] for item in invoice_data['items'])
        total_vat = sum(item['vat_amount'] for item in invoice_data['items'])
        total_ttc = sum(item['amount_ttc'] for item in invoice_data['items'])
        
        invoice_data.update({
            'total_ht': total_ht,
            'total_vat': total_vat,
            'total_ttc': total_ttc
        })
        
        # Génération du document Factur-X
        generator = FacturXGenerator()
        filename = f"facture_{invoice_data['invoice_number']}.pdf"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        try:
            generator.generate_facturx(invoice_data, filepath)
            flash('Facture Factur-X générée avec succès! ✅', 'success')
            return send_file(filepath, as_attachment=True, download_name=filename)
            
        except ValidationError as ve:
            flash(f'Erreur de validation:\n{str(ve)}', 'error')
            return redirect(url_for('index'))
            
    except ValidationError as ve:
        flash(f'Erreur de validation:\n{str(ve)}', 'error')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Erreur lors de la génération: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/preview')
def preview():
    return render_template('preview.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)