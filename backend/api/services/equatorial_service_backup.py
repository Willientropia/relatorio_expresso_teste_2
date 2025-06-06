# backend/api/services/equatorial_service.py
import os
import json
import logging
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from django.conf import settings
from django.core.files.base import ContentFile
from api.models import Customer, UnidadeConsumidora, Fatura, FaturaTask, FaturaLog
from . import setup_chromedriver

logger = logging.getLogger(__name__)


class EquatorialService:
    def __init__(self, customer_id):
        try:
            # Garantir que customer_id seja um inteiro
            self.customer_id = int(customer_id)
            self.customer = Customer.objects.get(id=self.customer_id)
            logger.info(f"EquatorialService inicializado para o cliente {self.customer.nome} (ID: {self.customer_id})")
        except Customer.DoesNotExist:
            logger.error(f"Cliente com ID {customer_id} não encontrado")
            raise Exception(f"Cliente com ID {customer_id} não encontrado")
        except Exception as e:
            logger.error(f"Erro ao inicializar EquatorialService: {e}")
            raise
            
        self.driver = None
        self.wait = None
        self.base_url = "https://goias.equatorialenergia.com.br"
        self.login_url = f"{self.base_url}/LoginGO.aspx"
        self.target_ucs = []  # Lista de UCs que devem ser baixadas
        
    def setup_driver(self):
        """Configura o driver do Chrome para rodar no servidor"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Sempre headless no servidor
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")  # Resolução maior
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Adicionar User-Agent real para evitar detecção - usando um mais recente
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
            
            # Configurações adicionais para evitar detecção
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
            chrome_options.add_argument("--disable-site-isolation-trials")
            
            # Mais opções para evitar detecção
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--ignore-certificate-errors")
            chrome_options.add_argument("--ignore-ssl-errors")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--start-maximized")
            
            # Configuração de download
            download_dir = os.path.join(settings.MEDIA_ROOT, 'temp_faturas')
            os.makedirs(download_dir, exist_ok=True)
            
            prefs = {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False,  # Desativar SafeBrowsing
                "safebrowsing.disable_download_protection": True,
                "plugins.always_open_pdf_externally": True,
                "profile.default_content_setting_values.automatic_downloads": 1,
                "profile.default_content_settings.popups": 0,
                "profile.default_content_setting_values.cookies": 1,  # Permitir cookies
                "profile.cookie_controls_mode": 0,  # Permitir todos os cookies
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                # Configurações para evitar detecção de bot
                "useAutomationExtension": False,
                "excludeSwitches": ["enable-automation"],
                "profile.default_content_setting_values.notifications": 2,  # Bloquear notificações
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Inicializar o driver
            logger.info("Inicializando o driver do Chrome...")
            self.driver = webdriver.Chrome(options=chrome_options)
              # Injetar script para enganar detecção de automação - versão mais simples
            logger.info("Aplicando scripts para evasão de detecção...")
            
            # Use a safer approach to avoid errors with redefining properties
            evasion_script = """
            // Hide Automation
            if (!Object.getOwnPropertyDescriptor(navigator, 'webdriver') || 
                Object.getOwnPropertyDescriptor(navigator, 'webdriver').configurable) {
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                    configurable: true
                });
            }
            
            // Add Chrome runtime
            if (!window.chrome) {
                window.chrome = {};
            }
            if (!window.chrome.runtime) {
                window.chrome.runtime = {};
            }
            
            // Add plugins
            if (navigator.plugins.length === 0) {
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                    configurable: true
                });
            }
            
            // Add languages
            if (navigator.languages.length === 0) {
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['pt-BR', 'pt', 'en-US', 'en'],
                    configurable: true
                });
            }
            """
            self.driver.execute_script(evasion_script)
            
            # Habilita download em modo headless
            params = {
                "behavior": "allow",
                "downloadPath": download_dir
            }
            self.driver.execute_cdp_cmd("Page.setDownloadBehavior", params)
            
            # Aumentar timeout para 45 segundos para sites com carregamento lento
            self.wait = WebDriverWait(self.driver, 45)
            logger.info("Driver do Chrome inicializado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao configurar driver: {e}")
            return False
      def login(self):
        """Realiza o login no sistema da Equatorial com retry automático"""
        try:
            return self._wait_and_retry_on_site_error(self._perform_login)
        except Exception as e:
            logger.error(f"Erro no login após tentativas: {e}")
            return False
    
    def _perform_login(self):
        """Executa o processo de login propriamente dito"""
        try:
            # Abre página de login com retry
            max_retries = 3
            for attempt in range(max_retries):
                logger.info(f"Tentativa {attempt+1} de acessar página de login")
                
                self.driver.get(self.login_url)
                logger.info(f"Acessando página de login: {self.login_url}")
                logger.info(f"URL atual: {self.driver.current_url}")
                logger.info(f"Título da página: {self.driver.title}")
                
                # Adiciona cookies para evitar detecção
                self.driver.add_cookie({"name": "incap_ses_", "value": "accept"})
                
                # Captura screenshot para debug
                try:
                    screenshot_path = os.path.join(settings.MEDIA_ROOT, f'debug_login_{attempt}.png')
                    self.driver.save_screenshot(screenshot_path)
                    logger.info(f"Screenshot salvo em: {screenshot_path}")
                except Exception as e:
                    logger.warning(f"Erro ao salvar screenshot: {e}")
                
                # Log HTML para debug
                logger.info(f"HTML da página (primeiros 2000 caracteres): {self.driver.page_source[:2000]}")
                
                # Tenta encontrar algum elemento na página para verificar se carregou
                try:
                    self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    time.sleep(5)  # Aguarda mais tempo para carregamento completo
                    
                    # Verifica redirecionamentos contínuos
                    if self.driver.current_url != self.login_url:
                        logger.info(f"Redirecionado para: {self.driver.current_url}")
                    
                    # Tenta encontrar campos de login
                    try:
                        uc_field = self.driver.find_element(By.CSS_SELECTOR, "input[name*='UC' i], input[id*='UC' i], input[placeholder*='Unidade' i]")
                        logger.info("Campo UC encontrado com sucesso!")
                        break  # Sucesso, sai do loop
                    except Exception as e:
                        logger.warning(f"Não encontrou campo UC: {e}")
                        if attempt == max_retries - 1:  # Última tentativa
                            logger.error("HTML da página de login:")
                            logger.error(self.driver.page_source[:5000])
                            raise Exception("Falha ao encontrar campo UC após múltiplas tentativas")
                        time.sleep(5)  # Aguarda antes da próxima tentativa
                        
                except Exception as e:
                    logger.warning(f"Erro ao aguardar carregamento da página: {e}")
                    if attempt == max_retries - 1:  # Última tentativa
                        raise
                    time.sleep(5)  # Aguarda antes da próxima tentativa
            
            # Preenche UC e CPF
            cpf_titular = self.customer.cpf_titular or self.customer.cpf
            logger.info(f"CPF titular a ser usado: {cpf_titular}")
            
            # Busca primeira UC ativa do cliente
            uc_ativa = self.customer.unidades_consumidoras.filter(
                data_vigencia_fim__isnull=True
            ).first()
            
            if not uc_ativa:
                raise Exception("Cliente não possui UC ativa")
            
            logger.info(f"UC ativa encontrada: {uc_ativa.codigo}")
            
            # Preenche campos com retry
            try:
                # Tenta diferentes seletores para o campo UC
                selectors = [
                    "input[name*='UC' i]",
                    "input[id*='UC' i]",
                    "input[placeholder*='Unidade' i]",
                    "input[class*='UC' i]"
                ]
                
                uc_field = None
                for selector in selectors:
                    try:
                        uc_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                        logger.info(f"Campo UC encontrado com seletor: {selector}")
                        break
                    except:
                        continue
                
                if uc_field:
                    uc_field.clear()
                    uc_field.send_keys(uc_ativa.codigo)
                    logger.info(f"UC preenchida: {uc_ativa.codigo}")
                else:
                    logger.error("Campo UC não encontrado após tentar múltiplos seletores")
                    logger.info(f"HTML da página: {self.driver.page_source[:5000]}")
                    raise Exception("Campo UC não encontrado")
                
                # Tenta diferentes seletores para o campo CPF
                selectors = [
                    "input[name*='CPF' i]",
                    "input[id*='CPF' i]",
                    "input[placeholder*='CPF' i]",
                    "input[class*='CPF' i]"
                ]
                
                cpf_field = None
                for selector in selectors:
                    try:
                        cpf_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                        logger.info(f"Campo CPF encontrado com seletor: {selector}")
                        break
                    except:
                        continue
                
                if cpf_field:
                    cpf_field.clear()
                    cpf_field.send_keys(cpf_titular)
                    logger.info(f"CPF preenchido: {cpf_titular}")
                else:
                    logger.error("Campo CPF não encontrado após tentar múltiplos seletores")
                    logger.info(f"HTML da página: {self.driver.page_source[:5000]}")
                    raise Exception("Campo CPF não encontrado")
                
            except Exception as e:
                logger.error(f"Erro ao preencher campos: {e}")
                raise
            
            # Clica em entrar
            try:
                # Tenta diferentes seletores para o botão Entrar
                selectors = [
                    "button.button",
                    "button[type='submit']",
                    "input[type='submit']",
                    "button:contains('Entrar')",
                    "button",
                    "input[value*='Entrar' i]"
                ]
                
                submit_button = None
                for selector in selectors:
                    try:
                        submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        logger.info(f"Botão Entrar encontrado com seletor: {selector}")
                        break
                    except:
                        continue
                
                if submit_button:
                    submit_button.click()
                    logger.info("Botão Entrar clicado")
                else:
                    # Tenta usar JavaScript para clicar em qualquer botão
                    self.driver.execute_script("document.querySelector('button').click();")
                    logger.info("Tentativa de clicar no botão via JavaScript")
                
            except Exception as e:
                logger.error(f"Erro ao clicar no botão Entrar: {e}")
                logger.info(f"HTML da página: {self.driver.page_source[:5000]}")
                raise
              time.sleep(5)  # Aguarda mais tempo para processamento
            
            # Verifica se o site está fora do ar
            self._check_for_site_errors()
            
            # Preenche data de nascimento
            if self.customer.data_nascimento:
                data_nascimento = self.customer.data_nascimento.strftime("%d/%m/%Y")
                logger.info(f"Data de nascimento a ser usada: {data_nascimento}")
                
                try:
                    # Aguarda um pouco mais para garantir que a página carregou
                    time.sleep(3)
                    
                    # Seletores mais robustos baseados no código que funcionava
                    selectors = [
                        "input[name='ctl00$WEBDOOR$headercorporativogo$txtData']",
                        "input[id='WEBDOOR_headercorporativogo_txtData']",
                        "input[name*='txtData']",
                        "input[id*='txtData']",
                        "input[placeholder*='DD/MM/YYYY']",
                        "input[placeholder*='DD/MM/YY']",
                        "input[name*='DataNascimento']",
                        "input[id*='DataNascimento']",
                        "input[name*='data'][class*='numero-cliente']",
                        "input[placeholder*='nascimento' i]",
                        "input[placeholder*='data' i]",
                        "input[type='text'][maxlength='10']",
                        "input[placeholder*='Data' i]",
                        "input[class*='data' i]"
                    ]
                    
                    data_field = None
                    for selector in selectors:
                        try:
                            data_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                            logger.info(f"Campo de data encontrado com seletor: {selector}")
                            break
                        except:
                            continue
                    
                    # Se não encontrou com CSS, tenta XPath
                    if not data_field:
                        xpath_selectors = [
                            "//input[contains(@name, 'txtData')]",
                            "//input[contains(@id, 'txtData')]",
                            "//input[contains(@placeholder, 'DD/MM')]",
                            "//input[@type='text' and @maxlength='10']",
                            "//input[contains(@name, 'DataNascimento')]"
                        ]
                        
                        for xpath in xpath_selectors:
                            try:
                                data_field = self.driver.find_element(By.XPATH, xpath)
                                logger.info(f"Campo de data encontrado com XPath: {xpath}")
                                break
                            except:
                                continue
                    
                    if data_field:
                        data_field.clear()
                        data_field.send_keys(data_nascimento)
                        logger.info(f"Data de nascimento preenchida: {data_nascimento}")
                    else:
                        logger.error("Campo de data não encontrado após tentar múltiplos seletores")
                        logger.info(f"URL atual: {self.driver.current_url}")
                        logger.info(f"HTML da página: {self.driver.page_source[:5000]}")
                        raise Exception("Campo de data de nascimento não encontrado")
                    
                    # Tenta diferentes seletores para o botão Validar
                    selectors = [
                        "input[name*='btnValidar']",
                        "input[id*='btnValidar']",
                        "button[type='submit']",
                        "input[type='submit']",
                        "button:contains('Validar')",
                        "button",
                        "input[value*='Validar' i]"
                    ]
                    
                    validate_button = None
                    for selector in selectors:
                        try:
                            validate_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                            logger.info(f"Botão Validar encontrado com seletor: {selector}")
                            break
                        except:
                            continue
                    
                    if validate_button:
                        validate_button.click()
                        logger.info("Botão Validar clicado")
                    else:
                        # Tenta usar JavaScript para clicar em qualquer botão ou input submit
                        self.driver.execute_script("document.querySelector('input[type=\"submit\"]').click();")
                        logger.info("Tentativa de clicar no botão via JavaScript")
                    
                except Exception as e:
                    logger.error(f"Erro ao preencher data de nascimento: {e}")
                    raise
                
                time.sleep(5)  # Aguarda mais tempo para processamento
            
            # Navega para Segunda Via
            logger.info("Navegando para página de Segunda Via")
            segunda_via_url = f"{self.base_url}/AgenciaGO/Servi%C3%A7os/aberto/SegundaVia.aspx"
            self.driver.get(segunda_via_url)
            logger.info(f"URL atual após navegar para Segunda Via: {self.driver.current_url}")
            time.sleep(5)  # Aguarda mais tempo para carregamento
            
            return True
            
        except Exception as e:
            logger.error(f"Erro no login: {e}")
            return False
    
    def get_all_ucs_from_dropdown(self):
        """Extrai todas as UCs disponíveis no dropdown"""
        try:
            dropdown = self.driver.find_element(By.CSS_SELECTOR, "#CONTENT_comboBoxUC")
            select = Select(dropdown)
            
            ucs_list = []
            for option in select.options:
                uc_number = option.get_attribute('value').strip()
                if uc_number:
                    ucs_list.append(uc_number)
            
            return ucs_list
            
        except Exception as e:
            logger.error(f"Erro ao extrair UCs: {e}")
            return []
    
    def process_faturas(self):
        """Processa o download das faturas"""
        try:
            # Obtém todas as UCs disponíveis
            all_ucs = self.get_all_ucs_from_dropdown()
            logger.info(f"UCs encontradas no dropdown: {all_ucs}")
            
            # Filtra apenas as UCs ativas do cliente
            active_ucs = self.customer.unidades_consumidoras.filter(
                data_vigencia_fim__isnull=True
            ).values_list('codigo', flat=True)
            logger.info(f"UCs ativas do cliente: {list(active_ucs)}")
            
            # Define quais UCs devem ser processadas
            self.target_ucs = [uc for uc in all_ucs if uc in active_ucs]
            logger.info(f"UCs alvo para processamento: {self.target_ucs}")
            
            if not self.target_ucs:
                logger.warning("Nenhuma UC do cliente encontrada no sistema da Equatorial")
                return False
            
            # Cria log de busca
            fatura_log = FaturaLog.objects.create(
                customer=self.customer,
                cpf_titular=self.customer.cpf_titular or self.customer.cpf,
                ucs_encontradas=all_ucs
            )
            
            faturas_encontradas = {}
            processamento_completo = True
            
            # Processa cada UC
            for uc_code in self.target_ucs:
                try:
                    # Encontra a UC no banco
                    uc_obj = self.customer.unidades_consumidoras.filter(
                        codigo=uc_code,
                        data_vigencia_fim__isnull=True
                    ).first()
                    
                    if not uc_obj:
                        logger.warning(f"UC {uc_code} não encontrada no banco de dados")
                        continue
                    
                    # Atualiza task para processando
                    task = FaturaTask.objects.filter(
                        customer=self.customer,
                        unidade_consumidora=uc_obj,
                        status__in=['pending', 'processing']
                    ).first()
                    
                    if task:
                        task.status = 'processing'
                        task.save()
                        logger.info(f"Task {task.id} atualizada para status 'processing'")
                    
                    # Seleciona a UC
                    dropdown = self.driver.find_element(By.CSS_SELECTOR, "#CONTENT_comboBoxUC")
                    select = Select(dropdown)
                    select.select_by_value(uc_code)
                    logger.info(f"UC {uc_code} selecionada no dropdown")
                    time.sleep(2)
                    
                    # Configura opções
                    self.set_emission_type("completa")
                    self.set_emission_reason("ESV05")
                    
                    # Clica em emitir
                    emit_button = self.driver.find_element(By.CSS_SELECTOR, "#CONTENT_btEnviar")
                    emit_button.click()
                    logger.info("Botão emitir clicado")
                    time.sleep(4)
                    
                    # Processa faturas da UC
                    faturas_da_uc = self.extract_and_download_invoices(uc_obj)
                    faturas_encontradas[uc_code] = faturas_da_uc
                    logger.info(f"Faturas encontradas para UC {uc_code}: {len(faturas_da_uc)}")
                    
                    # Atualiza task
                    if task:
                        task.status = 'completed'
                        task.completed_at = datetime.now()
                        task.save()
                        logger.info(f"Task {task.id} concluída com sucesso")
                    
                    # Volta para Segunda Via
                    self.driver.get(f"{self.base_url}/AgenciaGO/Servi%C3%A7os/aberto/SegundaVia.aspx")
                    logger.info("Retornando para página de Segunda Via")
                    time.sleep(3)
                    
                except Exception as e:
                    logger.error(f"Erro ao processar UC {uc_code}: {e}")
                    processamento_completo = False
                    if task:
                        task.status = 'failed'
                        task.error_message = str(e)
                        task.save()
                        logger.info(f"Task {task.id} marcada como falha: {str(e)}")
                    continue
            
            # Atualiza log
            fatura_log.faturas_encontradas = faturas_encontradas
            fatura_log.save()
            logger.info("Log de faturas atualizado")
            
            return processamento_completo
            
        except Exception as e:
            logger.error(f"Erro no processamento de faturas: {e}")
            return False
    
    def set_emission_type(self, emission_type="completa"):
        """Configura o tipo de emissão"""
        try:
            dropdown = self.driver.find_element(By.CSS_SELECTOR, "#CONTENT_cbTipoEmissao")
            select = Select(dropdown)
            select.select_by_value(emission_type)
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Erro ao configurar tipo de emissão: {e}")
            return False
    
    def set_emission_reason(self, reason_code="ESV05"):
        """Configura o motivo da emissão"""
        try:
            dropdown = self.driver.find_element(By.CSS_SELECTOR, "#CONTENT_cbMotivo")
            select = Select(dropdown)
            select.select_by_value(reason_code)
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Erro ao configurar motivo: {e}")
            return False
    
    def extract_and_download_invoices(self, uc_obj):
        """Extrai e baixa as faturas de uma UC específica"""
        faturas_info = []
        
        try:
            # Encontra todas as faturas disponíveis
            rows = self.driver.find_elements(By.XPATH, "//tr[.//a[contains(text(), 'Download')]]")
            
            for row in rows:
                try:
                    # Extrai informações
                    month_element = row.find_element(By.XPATH, "./td[1]")
                    month_text = month_element.text.strip()
                    
                    # Clica no download
                    download_link = row.find_element(By.XPATH, ".//a[contains(text(), 'Download')]")
                    download_link.click()
                    
                    # Aguarda e trata popup
                    time.sleep(2)
                    try:
                        ok_button = self.driver.find_element(By.CSS_SELECTOR, "#CONTENT_btnModal")
                        if ok_button.is_displayed():
                            ok_button.click()
                            time.sleep(3)
                    except:
                        pass
                    
                    # Aguarda download
                    time.sleep(5)
                    
                    # Procura arquivo baixado
                    download_dir = os.path.join(settings.MEDIA_ROOT, 'temp_faturas')
                    files = sorted([f for f in os.listdir(download_dir) if f.endswith('.pdf')], 
                                 key=lambda x: os.path.getctime(os.path.join(download_dir, x)))
                    
                    if files:
                        # Pega o arquivo mais recente
                        latest_file = files[-1]
                        file_path = os.path.join(download_dir, latest_file)
                        
                        # Lê o arquivo
                        with open(file_path, 'rb') as f:
                            file_content = f.read()
                        
                        # Cria ou atualiza fatura no banco
                        fatura, created = Fatura.objects.update_or_create(
                            customer=self.customer,
                            unidade_consumidora=uc_obj,
                            mes_referencia=month_text,
                            defaults={
                                'arquivo': ContentFile(file_content, name=f"{uc_obj.codigo}_{month_text.replace('/', '_')}.pdf")
                            }
                        )
                        
                        # Remove arquivo temporário
                        os.remove(file_path)
                        
                        faturas_info.append({
                            'mes': month_text,
                            'arquivo': fatura.arquivo.name,
                            'baixada': True
                        })
                    
                except Exception as e:
                    logger.error(f"Erro ao baixar fatura {month_text}: {e}")
                    faturas_info.append({
                        'mes': month_text,
                        'arquivo': None,
                        'baixada': False,
                        'erro': str(e)
                    })
                    continue
            
        except Exception as e:
            logger.error(f"Erro ao processar faturas: {e}")
        
        return faturas_info
    
    def close(self):
        """Fecha o navegador"""
        if self.driver:
            self.driver.quit()
    
    def _check_for_site_errors(self):
        """Verifica se o site está apresentando erros ou está fora do ar"""
        try:
            page_source = self.driver.page_source.lower()
            current_url = self.driver.current_url
            
            # Lista de indicadores de que o site está com problemas
            error_indicators = [
                "sistema fora do ar",
                "sistema indisponível", 
                "erro interno",
                "temporarily unavailable",
                "service unavailable",
                "erro 500",
                "erro 503",
                "manutenção",
                "maintenance"
            ]
            
            # Verifica se algum indicador de erro está presente
            for indicator in error_indicators:
                if indicator in page_source:
                    logger.warning(f"Site apresentando problemas: {indicator}")
                    raise Exception(f"Site da Equatorial com problemas: {indicator}")
            
            # Verifica se houve redirecionamento para página de erro
            if "erro" in current_url.lower() or "error" in current_url.lower():
                logger.warning(f"Redirecionado para página de erro: {current_url}")
                raise Exception(f"Redirecionado para página de erro: {current_url}")
                
        except Exception as e:
            if "Site da Equatorial com problemas" in str(e):
                raise e
            else:
                # Se for outro tipo de erro, apenas loga mas não interrompe
                logger.debug(f"Erro ao verificar problemas do site: {e}")

    def _wait_and_retry_on_site_error(self, func, *args, **kwargs):
        """Executa uma função com retry automático se o site estiver fora do ar"""
        max_retries = 3
        wait_time = 60  # 1 minuto
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = str(e).lower()
                
                # Verifica se é erro relacionado ao site estar fora do ar
                site_error_keywords = [
                    "sistema fora do ar",
                    "sistema indisponível",
                    "service unavailable",
                    "maintenance",
                    "manutenção"
                ]
                
                is_site_error = any(keyword in error_msg for keyword in site_error_keywords)
                
                if is_site_error and attempt < max_retries - 1:
                    logger.warning(f"Tentativa {attempt + 1}/{max_retries} falhou - Site com problemas: {e}")
                    logger.info(f"Aguardando {wait_time} segundos antes de tentar novamente...")
                    time.sleep(wait_time)
                    continue
                else:
                    # Se não é erro do site ou é a última tentativa, re-raise o erro
                    raise e
        
        return None
