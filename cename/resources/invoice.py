from cename.resources.base import BaseResource
from cename import db
from cename.models import Invoice, Batch
from datetime import datetime
import json
import logging


# Table of content
# -----------------
# ... 1. Get invoice
# ... 2. Add invoice
# ... 3. Update invoice
# ... 4. Delete invoice


class Get_invoice(BaseResource):
    def __init__(self):
        super().__init__()

    def get(self, invoice_no=None):
        temp = []
        if invoice_no:
            try:
                logging.info("Getting highly detailed invoice data for an invoice")
                temp = Invoice.query.get(invoice_no).jsonify(details="high")
            except Exception as e:
                logging.error(str(e))
                temp = []
        else:
            logging.info("Getting low details invoice data for all invoices")
            temp = [{**invoice.jsonify(details="low")} \
                    for invoice in Invoice.query.all()]
        return temp


class Add_invoice(BaseResource):
    def __init__(self):
        super().__init__()

    def missing_args(self):
        if self.get_request_data() == "":
            return True
        return False
    
    def post(self):
        if self.missing_args():
            logging.warning("data for adding invoice/batch not found")
            return {'message': "Sorry but 'data' argument value is missing!"}, 500
        else:
            logging.info("Data preprocessing for adding invoice")
            json_data = self.convert_data_to_dict(self.get_request_data())
            invoice_data = json_data['invoice_data']
            batches_data = json_data['batches']

            if len(batches_data) > 0:
                if not self.row_exist(Invoice, invoice_data['invoice_no']):
                    logging.info("Adding invoice")
                    invoice_no = self.add_invoice(invoice_data)
                    logging.info("adding batches")
                    for batch in batches_data:
                        if not self.row_exist(Batch, batch['batch_no']):
                            self.add_batch(batch, invoice_no)
                        else:
                            logging.warning("Adding batch failed due to duplicate entry")
                            return {'message': "Cannot add batch. Duplicate 'batch_no' '%s'"%(batch['batch_no'])}, 500
                    
                    logging.info("Invoice and batche(s) added successfully")
                    return {'message': "Invoice and batche(s) added successfully!"}, 200
                else:
                    logging.warning("Adding invoice failed due to duplicate entry")
                    return {'message': "Cannot add Invoice. Duplicate 'invoice_no' '%s'"%(invoice_data['invoice_no'])}, 500
            else:
                logging.warning("Missing data, cannot add invoice/batche(s)")
                return {'message': "No data recieved. Cannot add invoice"}, 500

    def add_invoice(self, invoice_dict):
        invoice_dict['invoice_date'] = self.convert_to_date(invoice_dict['invoice_date'])
        inv = Invoice(**invoice_dict)
        db.session.add(inv)
        try:
            db.session.commit()
        except:
            db.session.rollback()
            return {"message": "Error while updating the database. Probably internal."}, 500
        finally:
            return inv.invoice_no


    def add_batch(self, batch_dic, invoice_no):
        batch_dic['exp_date'] = self.convert_to_date(batch_dic['exp_date'])
        batch_dic['mfg_date'] = self.convert_to_date(batch_dic['mfg_date'])
        batch_dic['invoice_no'] = invoice_no
        batch_dic['available'] = batch_dic['quantity'] * batch_dic['num_of_ships']

        db.session.add(Batch(**batch_dic))
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logging.error(str(e))
            return {"message": "Error while updating the database. Probably internal."}, 500

    def row_exist(self, model, pk):
        if model.query.get(pk):
            return True
        return False


class Update_invoice(BaseResource):
    def __init__(self):
        super().__init__()
        self.arguments_list = []
        self.init_args()
        self.args = self.parse_args()

    def put(self):
        data = self.get_request_data()
        if data != "":
            data = self.convert_data_to_dict(data)

            invoice = Invoice.query.get(data['invoice_no'])
            msg, code = "Successfull", 200
            logging.info("Invoice update preprocessing ok. Proceeding with update")

            for k in data.keys():
                try:
                    getattr(invoice, k) # raise an attribute error if trying to update a non-existing column
                    if k.endswith("date"):
                        data[k] = self.convert_to_date(data[k])

                    # ignore 'created_on' and 'invoice_no' updates
                    if k != "created_on" and k != "invoice_no":
                        setattr(invoice, k, data[k])
                        db.session.commit()

                except AttributeError:
                    logging.warning("Invalid invoice attribute for update")
                    msg, code = "Invalid attribute '%s'"%(k), 500
                    break

                except Exception as e:
                    logging.error(str(e))
                    db.session.rollback()
                    msg, code = "Internal error", 500
                    break

                else:
                    continue
            if code == 200:
                logging.info("Invoice update successfull")
            return {'msg': msg}, code
            
        else:
            logging.warning("Update invoice failed. No data found")
            return {"message": "no invoice data recieved"}, 500


class Delete_invoice(BaseResource):
    def __init__(self):
        super().__init__()

    def delete(self, invoice_no=None):
        if invoice_no:
            inv = Invoice.query.get(invoice_no)
            if inv:    
                try:
                    db.session.delete(inv)
                    db.session.commit()
                except Exception as e:
                    logging.error(str(e))
                    db.session.rollback()
                    return {'message': "Internal Error while trying to delete"}, 500
                else:
                    logging.info("Invoice deletion successfull")
                    return {'message': "invoice deleted successfully"}, 200
            else:
                logging.warning("No invoice found for deletion")
                return {"message": "no such invoice with invoice_no '%s'"%(invoice_no)}, 500
        else:
            logging.warning("No data given for invoice deletion")
            return {'message': "no invoice_no given "}, 500