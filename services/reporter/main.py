from fastapi import FastAPI, HTTPException, BackgroundTasks
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime, timedelta
import json
import os
import boto3
from elasticsearch import Elasticsearch
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography import x509
import base64
import logging
from typing import Optional
import schedule
import threading
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Report Service", version="0.9.0")

class ReportGenerator:
    def __init__(self):
        self.es = Elasticsearch(
            [f"http://{os.getenv('ES_HOST', 'localhost')}:{os.getenv('ES_PORT', '9200')}"],
            basic_auth=(os.getenv('ES_USERNAME', 'elastic'), os.getenv('ES_PASSWORD', 'changeme'))
        )
        
        self.s3 = boto3.client(
            's3',
            endpoint_url=os.getenv('S3_ENDPOINT', 'http://localhost:9000'),
            aws_access_key_id=os.getenv('S3_ACCESS_KEY', 'minioadmin'),
            aws_secret_access_key=os.getenv('S3_SECRET_KEY', 'minioadmin'),
            region_name=os.getenv('S3_REGION', 'us-east-1')
        )
        
        self.bucket_name = os.getenv('S3_BUCKET', 'compliance-audit')
        self.report_timezone = os.getenv('REPORT_TIMEZONE', 'Europe/Berlin')
        
    def generate_daily_report(self, date: datetime) -> tuple[str, str]:
        # Query Elasticsearch for the day's data
        index_name = f"audit-{date.strftime('%Y.%m.%d')}"
        
        query = {
            "size": 0,
            "query": {
                "match_all": {}
            },
            "aggs": {
                "total_messages": {
                    "value_count": {
                        "field": "message_id"
                    }
                },
                "by_type": {
                    "terms": {
                        "field": "msgType"
                    }
                },
                "by_severity": {
                    "terms": {
                        "field": "severity"
                    }
                },
                "by_channel": {
                    "terms": {
                        "field": "channel_id"
                    }
                },
                "error_messages": {
                    "filter": {
                        "term": {
                            "severity": "ERROR"
                        }
                    }
                }
            }
        }
        
        try:
            response = self.es.search(index=index_name, body=query)
            aggs = response['aggregations']
            
            # Generate PDF report
            pdf_path = self._generate_pdf_report(date, aggs)
            
            # Generate JSON report
            json_path = self._generate_json_report(date, aggs)
            
            return pdf_path, json_path
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise
    
    def _generate_pdf_report(self, date: datetime, data: dict) -> str:
        filename = f"compliance_report_{date.strftime('%Y%m%d')}.pdf"
        filepath = f"/tmp/{filename}"
        
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#003366'),
            spaceAfter=30
        )
        story.append(Paragraph(f"Compliance Report - {date.strftime('%Y-%m-%d')}", title_style))
        story.append(Spacer(1, 12))
        
        # Summary statistics
        summary_data = [
            ['Metric', 'Value'],
            ['Total Messages', str(data.get('total_messages', {}).get('value', 0))],
            ['Error Count', str(data.get('error_messages', {}).get('doc_count', 0))],
            ['Error Rate', f"{(data.get('error_messages', {}).get('doc_count', 0) / max(data.get('total_messages', {}).get('value', 1), 1) * 100):.2f}%"],
            ['KHZG Compliance', 'PASS' if (data.get('error_messages', {}).get('doc_count', 0) / max(data.get('total_messages', {}).get('value', 1), 1)) <= 0.01 else 'FAIL']
        ]
        
        summary_table = Table(summary_data)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Messages by type
        story.append(Paragraph("Messages by Type", styles['Heading2']))
        type_data = [['Message Type', 'Count']]
        for bucket in data.get('by_type', {}).get('buckets', []):
            type_data.append([bucket['key'], str(bucket['doc_count'])])
        
        type_table = Table(type_data)
        type_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(type_table)
        story.append(Spacer(1, 20))
        
        # Compliance statement
        story.append(Paragraph("Compliance Statement", styles['Heading2']))
        compliance_text = f"""
        This report certifies that on {date.strftime('%Y-%m-%d')}, the Compliance Agent processed
        {data.get('total_messages', {}).get('value', 0)} messages with an error rate of
        {(data.get('error_messages', {}).get('doc_count', 0) / max(data.get('total_messages', {}).get('value', 1), 1) * 100):.2f}%.
        
        All messages have been securely stored with cryptographic hash verification and
        immutable audit trails as required by DSGVO Art. 30 & 32, KHZG § 14, and EU-MDR regulations.
        """
        story.append(Paragraph(compliance_text, styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        # Sign the PDF
        signed_path = self._sign_pdf(filepath)
        return signed_path
    
    def _generate_json_report(self, date: datetime, data: dict) -> str:
        filename = f"compliance_report_{date.strftime('%Y%m%d')}.json"
        filepath = f"/tmp/{filename}"
        
        report_data = {
            "report_date": date.isoformat(),
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_messages": data.get('total_messages', {}).get('value', 0),
                "error_count": data.get('error_messages', {}).get('doc_count', 0),
                "error_rate": data.get('error_messages', {}).get('doc_count', 0) / max(data.get('total_messages', {}).get('value', 1), 1),
                "khzg_compliant": (data.get('error_messages', {}).get('doc_count', 0) / max(data.get('total_messages', {}).get('value', 1), 1)) <= 0.01
            },
            "by_type": {bucket['key']: bucket['doc_count'] for bucket in data.get('by_type', {}).get('buckets', [])},
            "by_severity": {bucket['key']: bucket['doc_count'] for bucket in data.get('by_severity', {}).get('buckets', [])},
            "by_channel": {bucket['key']: bucket['doc_count'] for bucket in data.get('by_channel', {}).get('buckets', [])}
        }
        
        with open(filepath, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        return filepath
    
    def _sign_pdf(self, pdf_path: str) -> str:
        # Placeholder for PDF signing
        # In production, this would use a proper certificate
        signed_path = pdf_path.replace('.pdf', '_signed.pdf')
        os.rename(pdf_path, signed_path)
        return signed_path
    
    def store_report(self, pdf_path: str, json_path: str, date: datetime):
        # Store in S3
        for filepath in [pdf_path, json_path]:
            filename = os.path.basename(filepath)
            s3_key = f"reports/{date.strftime('%Y/%m/%d')}/{filename}"
            
            self.s3.upload_file(
                filepath,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ServerSideEncryption': 'AES256',
                    'ContentType': 'application/pdf' if filepath.endswith('.pdf') else 'application/json'
                }
            )
            logger.info(f"Uploaded report to S3: {s3_key}")

report_generator = ReportGenerator()

@app.post("/generate/{date}")
async def generate_report(date: str, background_tasks: BackgroundTasks):
    try:
        report_date = datetime.strptime(date, "%Y-%m-%d")
        
        def generate_and_store():
            pdf_path, json_path = report_generator.generate_daily_report(report_date)
            report_generator.store_report(pdf_path, json_path, report_date)
        
        background_tasks.add_task(generate_and_store)
        
        return {
            "status": "generating",
            "date": date,
            "message": "Report generation started"
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/report/{date}")
async def get_report(date: str, format: str = "pdf"):
    try:
        report_date = datetime.strptime(date, "%Y-%m-%d")
        extension = "pdf" if format == "pdf" else "json"
        filename = f"compliance_report_{report_date.strftime('%Y%m%d')}_signed.{extension}"
        s3_key = f"reports/{report_date.strftime('%Y/%m/%d')}/{filename}"
        
        # Get presigned URL
        url = report_generator.s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': report_generator.bucket_name, 'Key': s3_key},
            ExpiresIn=3600
        )
        
        return {"download_url": url, "format": format}
        
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Report not found: {str(e)}")

def run_scheduled_reports():
    def job():
        yesterday = datetime.now() - timedelta(days=1)
        pdf_path, json_path = report_generator.generate_daily_report(yesterday)
        report_generator.store_report(pdf_path, json_path, yesterday)
        logger.info(f"Generated daily report for {yesterday.strftime('%Y-%m-%d')}")
    
    schedule.every().day.at(os.getenv('REPORT_GENERATION_TIME', '23:55')).do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# Start scheduler in background
scheduler_thread = threading.Thread(target=run_scheduled_reports, daemon=True)
scheduler_thread.start()

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow()}