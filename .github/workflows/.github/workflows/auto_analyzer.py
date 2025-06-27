# auto_analyzer.py - Automatischer Zeitungsanalyse-Bot
import os
import time
import requests
import google.generativeai as genai
from supabase import create_client, Client
from datetime import datetime, timedelta
import re
from pypdf import PdfReader
import io
import sys
import logging

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('auto_analyzer.log')
    ]
)

class AutoNewspaperAnalyzer:
    def __init__(self):
        """Initialisiert den automatischen Analyzer"""
        self.supabase = self.init_supabase()
        self.gemini_model = self.init_gemini()
        self.app_url = os.getenv('STREAMLIT_APP_URL', 'https://deine-app.streamlit.app')
        
        # Zeitungsquellen konfigurieren
        self.newspaper_sources = [
            {
                'name': 'Mitteldeutsche Zeitung',
                'pdf_url': 'https://epaper.mz-web.de/today.pdf',  # Beispiel
                'enabled': True
            },
            {
                'name': 'Volksstimme',
                'pdf_url': 'https://epaper.volksstimme.de/today.pdf',  # Beispiel
                'enabled': False
            }
        ]
    
    def init_supabase(self):
        """Initialisiert Supabase Client"""
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_ANON_KEY')
            
            if not supabase_url or not supabase_key:
                logging.error("❌ Supabase Credentials fehlen!")
                return None
            
            supabase = create_client(supabase_url, supabase_key)
            logging.info("✅ Supabase verbunden")
            return supabase
            
        except Exception as e:
            logging.error(f"❌ Supabase Fehler: {e}")
            return None
    
    def init_gemini(self):
        """Initialisiert Gemini API"""
        try:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                logging.error("❌ Gemini API Key fehlt!")
                return None
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            logging.info("✅ Gemini API konfiguriert")
            return model
            
        except Exception as e:
            logging.error(f"❌ Gemini Fehler: {e}")
            return None
    
    def check_app_status(self):
        """Prüft ob die Streamlit App online ist"""
        try:
            response = requests.get(self.app_url, timeout=30)
            if response.status_code == 200:
                logging.info(f"✅ App ist online: {self.app_url}")
                return True
            else:
                logging.warning(f"⚠️ App antwortet mit Status {response.status_code}")
                return False
        except Exception as e:
            logging.error(f"❌ App nicht erreichbar: {e}")
            return False
    
    def wait_for_app_recovery(self, max_retries=5):
        """Wartet bis die App wieder online ist"""
        for attempt in range(max_retries):
            if self.check_app_status():
                return True
            
            wait_time = 180  # 3 Minuten
            logging.info(f"⏳ Warte {wait_time} Sekunden... (Versuch {attempt + 1}/{max_retries})")
            time.sleep(wait_time)
        
        logging.error("❌ App konnte nicht erreicht werden nach mehreren Versuchen")
        return False
    
    def download_pdf(self, source):
        """Lädt PDF von einer Zeitungsquelle herunter"""
        try:
            logging.info(f"📥 Lade PDF herunter: {source['name']}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(source['pdf_url'], headers=headers, timeout=60)
            response.raise_for_status()
            
            if response.headers.get('content-type', '').startswith('application/pdf'):
                logging.info(f"✅ PDF erfolgreich heruntergeladen: {len(response.content)} bytes")
                return response.content
            else:
                logging.error(f"❌ Kein PDF erhalten, Content-Type: {response.headers.get('content-type')}")
                return None
                
        except Exception as e:
            logging.error(f"❌ Fehler beim PDF-Download von {source['name']}: {e}")
            return None
    
    def extract_pdf_text(self, pdf_content):
        """Extrahiert Text aus PDF"""
        try:
            pdf_reader = PdfReader(io.BytesIO(pdf_content))
            text = ""
            
            logging.info(f"📄 PDF hat {len(pdf_reader.pages)} Seiten")
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                page_text = page.extract_text()
                text += f"=== SEITE {page_num} ===\n{page_text}\n\n"
            
            logging.info(f"✅ Text extrahiert: {len(text)} Zeichen")
            return text
            
        except Exception as e:
            logging.error(f"❌ PDF-Text-Extraktion fehlgeschlagen: {e}")
            return None
    
    def analyze_text_with_gemini(self, text, source_name):
        """Analysiert Text mit Gemini"""
        try:
            logging.info("🤖 Starte Gemini-Analyse...")
            
            # Text in Chunks aufteilen für große Zeitungen
            chunk_size = 15000
            chunks = []
            current_pos = 0
            
            while current_pos < len(text):
                end_pos = min(current_pos + chunk_size, len(text))
                
                if end_pos < len(text):
                    last_paragraph = text.rfind('\n\n', current_pos, end_pos)
                    if last_paragraph > current_pos:
                        end_pos = last_paragraph
                
                chunk = text[current_pos:end_pos].strip()
                if chunk:
                    chunks.append(chunk)
                current_pos = end_pos
            
            logging.info(f"📦 Text in {len(chunks)} Chunks aufgeteilt")
            
            all_analyses = []
            
            for i, chunk in enumerate(chunks, 1):
                logging.info(f"🔍 Analysiere Chunk {i}/{len(chunks)}...")
                
                prompt = f"""
                AUFTRAG: Analysiere diesen Zeitungstext für die Jungen Liberalen (JuLi).
                Quelle: {source_name}
                Datum: {datetime.now().strftime('%Y-%m-%d')}

                KATEGORIEN & PRIORITÄTEN:
                🔥 HÖCHSTE PRIORITÄT: Kommunalpolitik, Wirtschaft & Gewerbe, Bildung, Verkehr & Infrastruktur
                ⚡ HOHE PRIORITÄT: Digitalisierung & Innovation, Umwelt & Nachhaltigkeit, Bürgerbeteiligung & Demokratie, Jugendthemen
                📰 STANDARD: Kultur & Events, Sport, Soziales, Sonstiges

                FORMAT für jeden Artikel:
                **[KATEGORIE] - Überschrift**
                📍 Kurze prägnante Zusammenfassung (max. 2 Sätze)
                📄 Seite: [Seitennummer falls erkennbar]
                🎯 JuLi-Relevanz: Konkrete Begründung für Relevanz
                ---

                WICHTIG:
                - Verwende immer "JuLi" (nie "JL")
                - Nur vollständige, relevante Artikel
                - Fokus auf lokale/regionale Politik

                TEXT CHUNK {i}/{len(chunks)}:
                {chunk}
                """
                
                try:
                    response = self.gemini_model.generate_content(prompt)
                    all_analyses.append(response.text)
                    time.sleep(2)  # Rate limiting
                except Exception as e:
                    logging.error(f"❌ Fehler bei Chunk {i}: {e}")
                    all_analyses.append(f"❌ Fehler bei Chunk {i}: {e}")
            
            combined_analysis = '\n\n'.join(all_analyses)
            logging.info("✅ Gemini-Analyse abgeschlossen")
            return combined_analysis
            
        except Exception as e:
            logging.error(f"❌ Gemini-Analyse fehlgeschlagen: {e}")
            return None
    
    def parse_articles_from_analysis(self, analysis_text):
        """Extrahiert strukturierte Artikel-Daten"""
        articles = []
        
        try:
            article_blocks = analysis_text.split('---')
            
            for block in article_blocks:
                block = block.strip()
                if len(block) < 50:
                    continue
                
                # Daten mit Regex extrahieren
                title_match = re.search(r'\*\*(.*?)\*\*', block)
                summary_match = re.search(r'📍\s*(.*?)(?=📄|🎯|$)', block, re.DOTALL)
                page_match = re.search(r'📄.*?Seite:\s*(.*?)(?=🎯|$)', block)
                relevance_match = re.search(r'🎯\s*JuLi-Relevanz:\s*(.*?)$', block, re.DOTALL)
                
                if title_match:
                    title = title_match.group(1).strip()
                    
                    # Kategorie extrahieren
                    if ' - ' in title:
                        category, actual_title = title.split(' - ', 1)
                    else:
                        category = "Allgemein"
                        actual_title = title
                    
                    # Priorität bestimmen
                    priority = "standard"
                    if any(cat in category.lower() for cat in ['kommunalpolitik', 'wirtschaft', 'bildung', 'verkehr']):
                        priority = "höchste"
                    elif any(cat in category.lower() for cat in ['digitalisierung', 'umwelt', 'bürgerbeteiligung', 'jugend']):
                        priority = "hohe"
                    
                    article_data = {
                        'title': actual_title,
                        'category': category,
                        'priority': priority,
                        'summary': summary_match.group(1).strip() if summary_match else "",
                        'page': page_match.group(1).strip() if page_match else "nicht erkennbar",
                        'relevance': relevance_match.group(1).strip() if relevance_match else ""
                    }
                    
                    articles.append(article_data)
            
            logging.info(f"📄 {len(articles)} Artikel extrahiert")
            return articles
            
        except Exception as e:
            logging.error(f"❌ Artikel-Parsing fehlgeschlagen: {e}")
            return []
    
    def save_to_database(self, source_name, original_text, articles_data):
        """Speichert Analyse in Supabase"""
        try:
            if not self.supabase:
                logging.error("❌ Keine Supabase-Verbindung")
                return None
            
            # Analyse-Name generieren
            analysis_name = f"AUTO_{source_name}_{datetime.now().strftime('%Y%m%d')}"
            
            # Prioritäten zählen
            high_count = len([a for a in articles_data if a['priority'] == 'höchste'])
            medium_count = len([a for a in articles_data if a['priority'] == 'hohe'])
            
            # Hauptanalyse speichern
            analysis_data = {
                'name': analysis_name,
                'original_text': original_text[:10000],  # Kürzen für DB
                'total_articles': len(articles_data),
                'high_priority_count': high_count,
                'medium_priority_count': medium_count,
                'analysis_metadata': {
                    'source': source_name,
                    'auto_generated': True,
                    'text_length': len(original_text),
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            result = self.supabase.table('analyses').insert(analysis_data).execute()
            analysis_id = result.data[0]['id']
            
            # Artikel speichern
            for article in articles_data:
                article_data = {
                    'analysis_id': analysis_id,
                    'title': article['title'],
                    'category': article['category'],
                    'priority': article['priority'],
                    'page_number': article['page'],
                    'summary': article['summary'],
                    'relevance': article['relevance']
                }
                
                self.supabase.table('articles').insert(article_data).execute()
            
            logging.info(f"✅ Analyse gespeichert: {analysis_name} (ID: {analysis_id})")
            return analysis_id
            
        except Exception as e:
            logging.error(f"❌ Datenbank-Speicherung fehlgeschlagen: {e}")
            return None
    
    def check_already_analyzed_today(self, source_name):
        """Prüft ob heute bereits eine Analyse für diese Quelle existiert"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            analysis_name_pattern = f"AUTO_{source_name}_{datetime.now().strftime('%Y%m%d')}"
            
            result = self.supabase.table('analyses').select('*').eq('name', analysis_name_pattern).execute()
            
            if result.data:
                logging.info(f"ℹ️ Heute bereits analysiert: {source_name}")
                return True
            return False
            
        except Exception as e:
            logging.error(f"❌ Fehler bei Duplikat-Check: {e}")
            return False
    
    def process_newspaper_source(self, source):
        """Verarbeitet eine einzelne Zeitungsquelle"""
        logging.info(f"🗞️ Verarbeite: {source['name']}")
        
        # Check ob heute schon analysiert
        if self.check_already_analyzed_today(source['name']):
            logging.info(f"⏭️ Überspringe {source['name']} - heute bereits analysiert")
            return False
        
        # PDF herunterladen
        pdf_content = self.download_pdf(source)
        if not pdf_content:
            return False
        
        # Text extrahieren
        text = self.extract_pdf_text(pdf_content)
        if not text:
            return False
        
        # Mit Gemini analysieren
        analysis = self.analyze_text_with_gemini(text, source['name'])
        if not analysis:
            return False
        
        # Artikel parsen
        articles = self.parse_articles_from_analysis(analysis)
        if not articles:
            logging.warning(f"⚠️ Keine Artikel gefunden in {source['name']}")
            return False
        
        # In Datenbank speichern
        analysis_id = self.save_to_database(source['name'], text, articles)
        if analysis_id:
            high_count = len([a for a in articles if a['priority'] == 'höchste'])
            medium_count = len([a for a in articles if a['priority'] == 'hohe'])
            
            logging.info(f"🎉 Erfolgreich analysiert: {source['name']}")
            logging.info(f"   📊 Artikel: {len(articles)} | Hoch: {high_count} | Medium: {medium_count}")
            return True
        
        return False
    
    def run_daily_analysis(self):
        """Führt die tägliche automatische Analyse durch"""
        logging.info("🚀 Starte automatische tägliche Zeitungsanalyse")
        
        # Prüfe Konfiguration
        if not self.supabase:
            logging.error("❌ Supabase nicht konfiguriert")
            return False
        
        if not self.gemini_model:
            logging.error("❌ Gemini nicht konfiguriert")
            return False
        
        # Warte auf App-Recovery falls nötig
        if not self.wait_for_app_recovery():
            logging.error("❌ App ist nicht erreichbar - breche ab")
            return False
        
        success_count = 0
        enabled_sources = [s for s in self.newspaper_sources if s['enabled']]
        
        logging.info(f"📰 Verarbeite {len(enabled_sources)} Zeitungsquellen")
        
        for source in enabled_sources:
            try:
                if self.process_newspaper_source(source):
                    success_count += 1
                
                # Pause zwischen Quellen
                time.sleep(30)
                
            except Exception as e:
                logging.error(f"❌ Fehler bei {source['name']}: {e}")
        
        # Abschlussbericht
        logging.info(f"✅ Automatische Analyse abgeschlossen:")
        logging.info(f"   📊 Erfolgreiche Analysen: {success_count}/{len(enabled_sources)}")
        
        return success_count > 0

def main():
    """Hauptfunktion für automatische Ausführung"""
    analyzer = AutoNewspaperAnalyzer()
    
    # Führe tägliche Analyse durch
    success = analyzer.run_daily_analysis()
    
    if success:
        logging.info("🎉 Automatische Analyse erfolgreich!")
        sys.exit(0)
    else:
        logging.error("❌ Automatische Analyse fehlgeschlagen!")
        sys.exit(1)

if __name__ == "__main__":
    main()
