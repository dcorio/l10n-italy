from osv import fields, osv
import datetime

class account_account_template(osv.osv):
    _inherit = "account.account.template"
    _columns =  {
        'child_consol_ids': fields.many2many('account.account.template', 'account_account_template_consol_rel', 'child_id', 'parent_id', 'Consolidated Children'),
    }
account_account_template()

class wizard_multi_charts_accounts(osv.osv_memory):
    _inherit = 'wizard.multi.charts.accounts'
    _columns = {
        'chart_template_id': fields.many2one('account.chart.template', 'Chart Template', required=True, readonly=True),
        }
    _defaults = {
        'code_digits': lambda *a:0,
    }
    def execute(self, cr, uid, ids, context=None):
        super(wizard_multi_charts_accounts, self).execute(cr, uid, ids, context=None)

        obj_multi = self.browse(cr, uid, ids[0])
        obj_acc = self.pool.get('account.account')
        obj_acc_template = self.pool.get('account.account.template')
        obj_acc_chart = self.pool.get('account.chart.template')
        company_id = obj_multi.company_id.id
        acc_template_ref = {}
        #cerco tutti gli account.chart.template diversi da quello creato dal wizard di default
        chart_template_ids = obj_acc_chart.search(cr, uid, [('id', '!=', obj_multi.chart_template_id.id)])
        for chart_template_id in chart_template_ids:
            #genero il pdc consolidato
            chart_template = obj_acc_chart.browse(cr, uid, chart_template_id)
            children_acc_template = obj_acc_template.search(cr, uid, [('parent_id','child_of',[chart_template.account_root_id.id]),('nocreate','!=',True)])
            children_acc_template.sort()
            for account_template in obj_acc_template.browse(cr, uid, children_acc_template):
                tax_ids = []
                for tax in account_template.tax_ids:
                    tax_ids.append(tax_template_ref[tax.id])
                dig = 0
                code_main = account_template.code and len(account_template.code) or 0
                code_acc = account_template.code or ''
                if code_main>0 and code_main<=dig and account_template.type != 'view':
                    code_acc=str(code_acc) + (str('0'*(dig-code_main)))
                vals={
                    'name': (chart_template.account_root_id.id == account_template.id) and chart_template.name or account_template.name,
                    'currency_id': account_template.currency_id and account_template.currency_id.id or False,
                    'code': code_acc,
                    'type': account_template.type,
                    'user_type': account_template.user_type and account_template.user_type.id or False,
                    'reconcile': account_template.reconcile,
                    'shortcut': account_template.shortcut,
                    'note': account_template.note,
                    'parent_id': account_template.parent_id and ((account_template.parent_id.id in acc_template_ref) and acc_template_ref[account_template.parent_id.id]) or False,
                    'tax_ids': [(6,0,tax_ids)],
                    'company_id': company_id,
                }
                
                if(account_template.child_consol_ids):
                    #scrivo i consolidati in account.account prendendoli da account.template
                    account_id = obj_acc.search(cr, uid, [('code','=',code_acc)])
                    child_consol_ids = []
                    for child in account_template.child_consol_ids:
                        child_consol_ids.append(child.id)
                    vals['child_consol_ids'] = [(6, 0, child_consol_ids)]

                new_account = obj_acc.create(cr, uid, vals)
                acc_template_ref[account_template.id] = new_account

wizard_multi_charts_accounts()


class res_partner(osv.osv):
    _inherit = 'res.partner'

    def check_fiscalcode(self, cr, uid, ids, context={}):
        
        for partner in self.browse(cr, uid, ids):
            if not partner.fiscalcode:
                return True
            if len(partner.fiscalcode) != 16:
                return False

        return True

    _columns = {
        'fiscalcode': fields.char('Fiscal Code', size=16, help="Italian Fiscal Code"),
        'fiscalcode_surname': fields.char('Surname', size=64),
        'fiscalcode_firstname': fields.char('First name', size=64),
        'birth_date': fields.date('Date of birth'),
        'birth_city': fields.many2one('res.city', 'City of birth'),
        'sex': fields.selection([
            ('M','Male'),
            ('F', 'Female'),
            ], "Sex"),
    }
    #_constraints = [(check_fiscalcode, "The fiscal code doesn't seem to be correct.", ["fiscalcode"])]

     
    def _codicefiscale(self, cognome, nome, giornonascita, mesenascita, annonascita,
                      sesso, cittanascita):

        MESI = 'ABCDEHLMPRST'
        CONSONANTI = 'BCDFGHJKLMNPQRSTVWXYZ'
        VOCALI = 'AEIOU'
        LETTERE = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        REGOLECONTROLLO = {
            'A':(0,1),   'B':(1,0),   'C':(2,5),   'D':(3,7),   'E':(4,9),
            'F':(5,13),  'G':(6,15),  'H':(7,17),  'I':(8,19),  'J':(9,21),
            'K':(10,2),  'L':(11,4),  'M':(12,18), 'N':(13,20), 'O':(14,11),
            'P':(15,3),  'Q':(16,6),  'R':(17,8),  'S':(18,12), 'T':(19,14),
            'U':(20,16), 'V':(21,10), 'W':(22,22), 'X':(23,25), 'Y':(24,24),
            'Z':(25,23),
            '0':(0,1),   '1':(1,0),   '2':(2,5),   '3':(3,7),   '4':(4,9),
            '5':(5,13),  '6':(6,15),  '7':(7,17),  '8':(8,19),  '9':(9,21)
                          }
        ###
        # Funzioni
        ##
         
        def _surname(stringa):
            """Ricava, da stringa, 3 lettere in base alla convenzione dei CF."""
            cons = [c for c in stringa if c in CONSONANTI]
            voc = [c for c in stringa if c in VOCALI]
            chars=cons+voc
            if len(chars)<3:
                chars+=['X', 'X']
            return chars[:3]
         
        def _name(stringa):
            """Ricava, da stringa, 3 lettere in base alla convenzione dei CF."""
            cons = [c for c in stringa if c in CONSONANTI]
            voc = [c for c in stringa if c in VOCALI]
            if len(cons)>3:
                cons = [cons[0]] +[cons[2]] + [cons[3]]
            chars=cons+voc
            if len(chars)<3:
                chars+=['X', 'X']
            return chars[:3]
         
        def _datan(giorno, mese, anno, sesso):
            """Restituisce il campo data del CF."""
            chars = (list(anno[-2:]) + [MESI[int(mese)-1]])
            gn=int(giorno)
            if sesso=='F':
                gn+=40
            chars += list("%02d" % gn)
            return chars
         
        def _codicecontrollo(c):
            """Restituisce il codice di controllo, l'ultimo carattere del CF."""
            sommone = 0
            for i, car in enumerate(c):
                j = 1 - i % 2
                sommone += REGOLECONTROLLO[car][j]
            resto = sommone % 26
            return [LETTERE[resto]]

        """Restituisce il CF costruito sulla base degli argomenti."""
        nome=nome.upper()
        cognome=cognome.upper()
        sesso=sesso.upper()
        cittanascita = cittanascita.upper()
        chars = (_surname(cognome) +
                 _name(nome) +
                 _datan(giornonascita, mesenascita, annonascita, sesso) +
                 list(cittanascita))
        chars += _codicecontrollo(chars)
        return ''.join(chars)
     
    def compute_fiscal_code(self, cr, uid, ids, context):
        partners = self.browse(cr, uid, ids, context)
        for partner in partners:
            if not partner.fiscalcode_surname or not partner.fiscalcode_firstname or not partner.birth_date or not partner.birth_city or not partner.sex:
                raise osv.except_osv('Error', 'One or more fields are missing')
            birth_date = datetime.datetime.strptime(partner.birth_date, "%Y-%m-%d")
            CF = self._codicefiscale(partner.fiscalcode_surname, partner.fiscalcode_firstname, str(birth_date.day),
                str(birth_date.month), str(birth_date.year), partner.sex,
                partner.birth_city.cadaster_code)
            self.write(cr, uid, partner.id, {'fiscalcode': CF})
        return True
    
res_partner()