# test_automation.py - Lokaler Test der Automatisierung
import os
from dotenv import load_dotenv
from auto_analyzer import AutoNewspaperAnalyzer

# Lade Umgebungsvariablen aus .env Datei
load_dotenv()

def test_single_source():
    """Testet eine einzelne Zeitungsquelle"""
    print("🧪 Teste automatische Zeitungsanalyse lokal...")
    
    # Analyzer initialisieren
    analyzer = AutoNewspaperAnalyzer()
    
    # Test-Quelle (anpassen für deine Zeitung)
    test_source = {
        'name': 'Test_Zeitung',
        'pdf_url': 'https://example.com/test.pdf',  # Ersetze mit echter URL
        'enabled': True
    }
    
    print(f"📰 Teste Quelle: {test_source['name']}")
    
    # App-Status prüfen
    print("🔍 Prüfe App-Status...")
    app_online = analyzer.check_app_status()
    print(f"   App online: {'✅' if app_online else '❌'}")
    
    # PDF Download testen
    print("📥 Teste PDF-Download...")
    pdf_content = analyzer.download_pdf(test_source)
    if pdf_content:
        print(f"   ✅ PDF heruntergeladen: {len(pdf_content)} bytes")
        
        # Text-Extraktion testen
        print("📄 Teste Text-Extraktion...")
        text = analyzer.extract_pdf_text(pdf_content)
        if text:
            print(f"   ✅ Text extrahiert: {len(text)} Zeichen")
            
            # Nur die ersten 1000 Zeichen für Test-Analyse
            test_text = text[:1000]
            print("🤖 Teste Gemini-Analyse...")
            
            analysis = analyzer.analyze_text_with_gemini(test_text, test_source['name'])
            if analysis:
                print("   ✅ Analyse erfolgreich")
                print(f"   📝 Analyse-Länge: {len(analysis)} Zeichen")
                
                # Artikel parsen
                articles = analyzer.parse_articles_from_analysis(analysis)
                print(f"   📄 Artikel gefunden: {len(articles)}")
                
                for i, article in enumerate(articles[:3], 1):  # Nur erste 3 anzeigen
                    print(f"      {i}. {article['title']} (Priorität: {article['priority']})")
                
                return True
            else:
                print("   ❌ Analyse fehlgeschlagen")
        else:
            print("   ❌ Text-Extraktion fehlgeschlagen")
    else:
        print("   ❌ PDF-Download fehlgeschlagen")
    
    return False

def test_configuration():
    """Testet die Konfiguration"""
    print("⚙️ Teste Konfiguration...")
    
    # Prüfe Umgebungsvariablen
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY', 
        'GEMINI_API_KEY',
        'STREAMLIT_APP_URL'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
            print(f"   ❌ {var} fehlt")
        else:
            print(f"   ✅ {var} gesetzt")
    
    if missing_vars:
        print(f"\n🚨 Fehlende Umgebungsvariablen: {', '.join(missing_vars)}")
        print("💡 Erstelle eine .env Datei mit:")
        for var in missing_vars:
            print(f"   {var}=dein_wert_hier")
        return False
    
    return True

def create_env_template():
    """Erstellt eine .env Template-Datei"""
    env_template = """# Umgebungsvariablen für automatische Zeitungsanalyse
# Kopiere diese Datei zu .env und fülle die Werte aus

# Supabase Konfiguration
SUPABASE_URL=https://deinprojekt.supabase.co
SUPABASE_ANON_KEY=dein_supabase_anon_key_hier

# Google Gemini API
GEMINI_API_KEY=dein_gemini_api_key_hier

# Streamlit App URL
STREAMLIT_APP_URL=https://deine-app.streamlit.app

# Optional: Debugging
DEBUG=true
"""
    
    with open('.env.template', 'w') as f:
        f.write(env_template)
    
    print("📝 .env.template erstellt!")
    print("💡 Kopiere zu .env und fülle die Werte aus")

def main():
    """Hauptfunktion für lokale Tests"""
    print("🚀 Automatische Zeitungsanalyse - Lokaler Test\n")
    
    # Prüfe ob .env existiert
    if not os.path.exists('.env'):
        print("⚠️ Keine .env Datei gefunden")
        create_env_template()
        return
    
    # Teste Konfiguration
    if not test_configuration():
        return
    
    # Teste einzelne Komponenten
    print("\n" + "="*50)
    success = test_single_source()
    
    print("\n" + "="*50)
    if success:
        print("🎉 Alle Tests erfolgreich!")
        print("💡 Du kannst jetzt die GitHub Action einrichten")
    else:
        print("❌ Einige Tests sind fehlgeschlagen")
        print("🔍 Prüfe die Fehlermeldungen oben")

if __name__ == "__main__":
    main()
