# backend/api/services/__init__.py
import os
import chromedriver_autoinstaller

def setup_chromedriver():
    """Configura o ChromeDriver automaticamente"""
    try:
        # Instala o ChromeDriver correspondente à versão do Chrome instalada
        chromedriver_path = chromedriver_autoinstaller.install()
        print(f"ChromeDriver instalado em: {chromedriver_path}")
        return True
    except Exception as e:
        print(f"Erro ao instalar ChromeDriver: {e}")
        return False

# Executa a configuração ao importar o módulo
setup_chromedriver()