# backend/api/services/equatorial_service.py
import os
import json
import logging
import time
import re
from datetime import datetime
from django.utils import timezone
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
            
            # Configurações para evitar detecção de bot
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

    def _handle_alert(self):
        """Verifica e lida com alertas do navegador"""
        try:
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            logger.warning(f"Alert detectado: {alert_text}")
            alert.accept()  # Clica OK no alert
            return alert_text
        except Exception:
            return None

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

    def login(self):
        """Realiza o login no sistema da Equatorial com retry automático"""
        try:
            return self._wait_and_retry_on_site_error(self._perform_login)
        except Exception as e:
            logger.error(f"Erro no login após tentativas: {e}")
            return False
    
    def _perform_login(self):
        """Executa o processo de login propriamente dito com fluxo de 2 etapas"""
        try:
            # ETAPA 1: Acessar página e preencher UC/CPF
            if not self._step1_access_and_fill():
                return False
            
            # ETAPA 2: Clicar em "Entrar" 
            if not self._step1_submit():
                return False
            
            # ETAPA 3: Preencher data de nascimento
            if not self._step2_fill_birth_date():
                return False
            
            # ETAPA 4: Clicar em "Validar"
            if not self._step2_submit():
                return False
            
            # ETAPA 5: Navegar para Segunda Via
            if not self._navigate_to_segunda_via():
                return False
            
            logger.info("Login completo realizado com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"Erro no login: {e}")
            return False
    
    def _step1_access_and_fill(self):
        """Etapa 1: Acessar página e preencher UC/CPF"""
        try:
            logger.info("ETAPA 1: Acessando página e preenchendo UC/CPF")
            
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
                
                # Verifica se o site está fora do ar
                self._check_for_site_errors()
                
                # Tenta encontrar algum elemento na página para verificar se carregou
                try:
                    self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    time.sleep(5)  # Aguarda carregamento completo
                    
                    # Tenta encontrar campos de login
                    try:
                        uc_field = self.driver.find_element(By.CSS_SELECTOR, "input[name*='UC' i], input[id*='UC' i], input[placeholder*='Unidade' i]")
                        logger.info("Campo UC encontrado com sucesso!")
                        break  # Sucesso, sai do loop
                    except Exception as e:
                        logger.warning(f"Não encontrou campo UC: {e}")
                        if attempt == max_retries - 1:  # Última tentativa
                            raise Exception("Falha ao encontrar campo UC após múltiplas tentativas")
                        time.sleep(5)  # Aguarda antes da próxima tentativa
                        
                except Exception as e:
                    logger.warning(f"Erro ao aguardar carregamento da página: {e}")
                    if attempt == max_retries - 1:  # Última tentativa
                        raise
                    time.sleep(5)  # Aguarda antes da próxima tentativa
            
            # Busca dados do cliente
            cpf_titular = self.customer.cpf_titular or self.customer.cpf
            logger.info(f"CPF titular a ser usado: {cpf_titular}")
            
            # Busca primeira UC ativa do cliente
            uc_ativa = self.customer.unidades_consumidoras.filter(
                data_vigencia_fim__isnull=True
            ).first()
            
            if not uc_ativa:
                raise Exception("Cliente não possui UC ativa")
            
            logger.info(f"UC ativa encontrada: {uc_ativa.codigo}")
            
            # Preenche campo UC
            uc_selectors = [
                "input[name*='UC' i]",
                "input[id*='UC' i]",
                "input[placeholder*='Unidade' i]",
                "input[class*='UC' i]"
            ]
            
            uc_field = None
            for selector in uc_selectors:
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
                raise Exception("Campo UC não encontrado")
            
            # Preenche campo CPF
            cpf_selectors = [
                "input[name*='CPF' i]",
                "input[id*='CPF' i]",
                "input[placeholder*='CPF' i]",
                "input[class*='CPF' i]"
            ]
            
            cpf_field = None
            for selector in cpf_selectors:
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
                raise Exception("Campo CPF não encontrado")
            
            logger.info("UC e CPF preenchidos com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"Erro na etapa 1: {e}")
            return False
    
    def _step1_submit(self):
        """Etapa 1: Clica no botão Entrar"""
        try:
            logger.info("ETAPA 1: Clicando no botão 'Entrar'")
            time.sleep(2)
            
            # Seletores para o botão Entrar
            submit_selectors = [
                "button.button[onclick*='ValidarCamposAreaLogada']",
                "button.button",
                "button[type='submit']",
                "input[type='submit']",
                "button",
                "input[value*='Entrar' i]"
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    logger.info(f"Botão Entrar encontrado com seletor: {selector}")
                    break
                except:
                    continue
            
            # Tenta XPath se CSS não funcionou
            if not submit_button:
                xpath_selectors = [
                    "//button[contains(@onclick, 'ValidarCamposAreaLogada')]",
                    "//button[@class='button']",
                    "//button[contains(text(), 'Entrar')]",
                    "//input[@value='Entrar']"
                ]
                
                for xpath in xpath_selectors:
                    try:
                        submit_button = self.driver.find_element(By.XPATH, xpath)
                        logger.info(f"Botão Entrar encontrado com XPath: {xpath}")
                        break
                    except:
                        continue
            
            if submit_button:
                # Tenta clicar
                try:
                    submit_button.click()
                    logger.info("Botão 'Entrar' clicado com método normal")
                except:
                    try:
                        self.driver.execute_script("arguments[0].click();", submit_button)
                        logger.info("Botão 'Entrar' clicado com JavaScript")
                    except:
                        # Tenta executar função onclick
                        onclick = submit_button.get_attribute('onclick')
                        if onclick and 'ValidarCamposAreaLogada' in onclick:
                            self.driver.execute_script("ValidarCamposAreaLogada();")
                            logger.info("Botão 'Entrar' acionado via função JavaScript")
                        else:
                            raise Exception("Todos os métodos de clique falharam")
                
                time.sleep(5)  # Aguarda navegação
                logger.info("Clique no botão 'Entrar' realizado com sucesso!")
                return True
            else:
                raise Exception("Botão 'Entrar' não encontrado")
                
        except Exception as e:
            logger.error(f"Erro ao clicar em 'Entrar': {e}")
            return False
    
    def _step2_fill_birth_date(self):
        """Etapa 2: Preenche data de nascimento"""
        try:
            if not self.customer.data_nascimento:
                raise Exception("Cliente não possui data de nascimento cadastrada")
            
            data_nascimento = self.customer.data_nascimento.strftime("%d/%m/%Y")
            logger.info(f"ETAPA 2: Preenchendo data de nascimento ({data_nascimento})")
            
            # Aguarda nova página carregar
            time.sleep(3)
            logger.info(f"URL atual: {self.driver.current_url}")
            
            # Verifica se o site está fora do ar
            self._check_for_site_errors()
            
            # Seletores robustos para data de nascimento
            data_selectors = [
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
                "input[type='text'][maxlength='10']"
            ]
            
            data_field = None
            for selector in data_selectors:
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
                return True
            else:
                # Debug adicional
                logger.error("Campo de data de nascimento não encontrado")
                inputs = self.driver.find_elements(By.TAG_NAME, "input")
                logger.error(f"Total de inputs encontrados: {len(inputs)}")
                for i, inp in enumerate(inputs):
                    try:
                        name = inp.get_attribute('name') or ''
                        id_attr = inp.get_attribute('id') or ''
                        placeholder = inp.get_attribute('placeholder') or ''
                        type_attr = inp.get_attribute('type') or ''
                        logger.error(f"Input {i}: name='{name}', id='{id_attr}', placeholder='{placeholder}', type='{type_attr}'")
                    except:
                        pass
                
                raise Exception("Campo de data de nascimento não encontrado")
                
        except Exception as e:
            logger.error(f"Erro ao preencher data de nascimento: {e}")
            return False
    
    def _step2_submit(self):
        """Etapa 2: Clica no botão Validar"""
        try:
            logger.info("ETAPA 2: Clicando no botão 'Validar'")
            time.sleep(2)
            
            # Seletores para o botão Validar
            validate_selectors = [
                "input[name='ctl00$WEBDOOR$headercorporativogo$btnValidar']",
                "input[id='WEBDOOR_headercorporativogo_btnValidar']",
                "input[value='Validar']",
                "input[name*='btnValidar']",
                "input[id*='btnValidar']",
                "input[type='submit'][value*='Validar' i]",
                "input[class='button'][value*='Validar' i]",
                "input[value*='Confirmar' i]",
                "input[value*='OK' i]"
            ]
            
            validate_button = None
            for selector in validate_selectors:
                try:
                    validate_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    logger.info(f"Botão Validar encontrado com seletor: {selector}")
                    break
                except:
                    continue
            
            # Tenta XPath para botões
            if not validate_button:
                xpath_selectors = [
                    "//input[contains(@name, 'btnValidar')]",
                    "//input[contains(@id, 'btnValidar')]",
                    "//input[@value='Validar']",
                    "//button[contains(text(), 'Validar')]"
                ]
                
                for xpath in xpath_selectors:
                    try:
                        validate_button = self.driver.find_element(By.XPATH, xpath)
                        logger.info(f"Botão Validar encontrado com XPath: {xpath}")
                        break
                    except:
                        continue
            
            if validate_button:
                # Tenta clicar
                try:
                    validate_button.click()
                    logger.info("Botão 'Validar' clicado com método normal")
                except:
                    try:
                        self.driver.execute_script("arguments[0].click();", validate_button)
                        logger.info("Botão 'Validar' clicado com JavaScript")
                    except:
                        # Tenta submit do formulário
                        try:
                            form = validate_button.find_element(By.XPATH, "./ancestor::form[1]")
                            form.submit()
                            logger.info("Formulário submetido via form.submit()")
                        except:
                            raise Exception("Todos os métodos de clique falharam")
                
                time.sleep(5)  # Aguarda processamento
                logger.info("Clique no botão 'Validar' realizado com sucesso!")
                return True
            else:
                raise Exception("Botão 'Validar' não encontrado")
                
        except Exception as e:
            logger.error(f"Erro ao clicar em 'Validar': {e}")
            return False
    
    def _navigate_to_segunda_via(self):
        """Etapa final: Navega para página de Segunda Via"""
        try:
            logger.info("ETAPA FINAL: Navegando para página de Segunda Via")
            
            # Verifica se o site está fora do ar
            self._check_for_site_errors()
            
            segunda_via_url = f"{self.base_url}/AgenciaGO/Servi%C3%A7os/aberto/SegundaVia.aspx"
            self.driver.get(segunda_via_url)
            logger.info(f"URL atual após navegar para Segunda Via: {self.driver.current_url}")
            time.sleep(5)  # Aguarda carregamento
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao navegar para Segunda Via: {e}")
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
                        logger.warning(f"UC {uc_code} não encontrada no banco de dados do cliente")
                        continue
                    
                    # Atualiza status da task se existir
                    task = FaturaTask.objects.filter(
                        customer=self.customer,
                        unidade_consumidora=uc_obj,
                        status='pending'
                    ).first()
                    
                    if task:
                        task.status = 'processing'
                        task.save()
                        logger.info(f"Task {task.id} atualizada para status 'processing'")
                    
                    # Seleciona UC no dropdown
                    dropdown = self.driver.find_element(By.CSS_SELECTOR, "#CONTENT_comboBoxUC")
                    select = Select(dropdown)
                    select.select_by_value(uc_code)
                    logger.info(f"UC {uc_code} selecionada no dropdown")
                    
                    time.sleep(3)  # Aguarda carregamento após seleção
                    
                    # Clica no botão emitir
                    emit_button = self.driver.find_element(By.CSS_SELECTOR, "input[value='Emitir']")
                    emit_button.click()
                    logger.info("Botão emitir clicado")
                    
                    time.sleep(5)  # Aguarda processamento
                    
                    # Busca e baixa faturas
                    faturas_uc = self.download_faturas_for_uc(uc_obj)
                    faturas_encontradas[uc_code] = faturas_uc
                    
                    logger.info(f"Faturas encontradas para UC {uc_code}: {len(faturas_uc)}")
                    
                    # Atualiza status da task como concluída
                    if task:
                        task.status = 'completed'
                        task.completed_at = timezone.now()
                        task.save()
                        logger.info(f"Task {task.id} concluída com sucesso")
                    
                    # Volta para página de Segunda Via para próxima UC
                    if uc_code != self.target_ucs[-1]:  # Se não é a última UC
                        segunda_via_url = f"{self.base_url}/AgenciaGO/Servi%C3%A7os/aberto/SegundaVia.aspx"
                        self.driver.get(segunda_via_url)
                        logger.info("Retornando para página de Segunda Via")
                        time.sleep(3)
                        
                except Exception as e:
                    logger.error(f"Erro ao processar UC {uc_code}: {e}")
                    processamento_completo = False
                    
                    # Marca task como falha se existir
                    if task:
                        task.status = 'failed'
                        task.error_message = str(e)
                        task.save()
                    
                    continue
            
            # Atualiza log com faturas encontradas
            fatura_log.faturas_encontradas = faturas_encontradas
            fatura_log.save()
            logger.info("Log de faturas atualizado")
            
            return processamento_completo
            
        except Exception as e:
            logger.error(f"Erro no processamento de faturas: {e}")
            return False
    
    def download_faturas_for_uc(self, uc_obj):
        """Baixa faturas para uma UC específica"""
        faturas_encontradas = []
        
        try:
            # Busca links de download na página
            download_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='.pdf']")
            
            for link in download_links:
                try:
                    # Extrai informações da fatura
                    link_text = link.text.strip()
                    href = link.get_attribute('href')
                    
                    # Extrai mês/ano da fatura (formato pode variar)
                    mes_referencia = self.extract_month_year(link_text, href)
                    
                    if mes_referencia:
                        # Verifica se já existe essa fatura no banco
                        existing_fatura = Fatura.objects.filter(
                            customer=self.customer,
                            unidade_consumidora=uc_obj,
                            mes_referencia=mes_referencia
                        ).first()
                        
                        if existing_fatura:
                            logger.info(f"Fatura {mes_referencia} já existe no banco")
                            continue
                        
                        # Faz download da fatura
                        link.click()
                        time.sleep(2)  # Aguarda download
                        
                        # Processa arquivo baixado
                        downloaded_file = self.get_downloaded_file()
                        if downloaded_file:
                            # Salva no banco
                            fatura = Fatura.objects.create(
                                customer=self.customer,
                                unidade_consumidora=uc_obj,
                                mes_referencia=mes_referencia,
                                arquivo=downloaded_file
                            )
                            
                            faturas_encontradas.append({
                                'mes': mes_referencia,
                                'arquivo': fatura.arquivo.name,
                                'baixada': True
                            })
                            
                            logger.info(f"Fatura {mes_referencia} salva no banco")
                        
                except Exception as e:
                    logger.warning(f"Erro ao processar link de fatura: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Erro ao baixar faturas para UC {uc_obj.codigo}: {e}")
        
        return faturas_encontradas
    
    def extract_month_year(self, text, href):
        """Extrai mês/ano de um texto ou URL"""
        import re
        
        # Padrões comuns para mês/ano
        patterns = [
            r'(\w{3})/(\d{4})',  # JAN/2024
            r'(\d{2})/(\d{4})',  # 01/2024
            r'(\w{3})\s*(\d{4})',  # JAN 2024
        ]
        
        combined_text = f"{text} {href}"
        
        for pattern in patterns:
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                month, year = match.groups()
                # Converte mês numérico para nome se necessário
                if month.isdigit():
                    month_names = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN',
                                   'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']
                    month = month_names[int(month) - 1]
                
                return f"{month.upper()}/{year}"
        
        return None
    
    def get_downloaded_file(self):
        """Obtém o arquivo baixado mais recente"""
        try:
            download_dir = os.path.join(settings.MEDIA_ROOT, 'temp_faturas')
            files = os.listdir(download_dir)
            
            if not files:
                return None
            
            # Ordena por data de modificação (mais recente primeiro)
            files.sort(key=lambda x: os.path.getmtime(os.path.join(download_dir, x)), reverse=True)
            
            latest_file = files[0]
            file_path = os.path.join(download_dir, latest_file)
            
            # Cria um novo nome baseado na UC e timestamp
            new_name = f"{self.customer.cpf}_{latest_file}"
            
            # Lê o arquivo e cria ContentFile
            with open(file_path, 'rb') as f:
                content = ContentFile(f.read(), name=new_name)
            
            # Remove arquivo temporário
            os.remove(file_path)
            
            return content
            
        except Exception as e:
            logger.error(f"Erro ao obter arquivo baixado: {e}")
            return None
    
    def close(self):
        """Fecha o driver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Driver fechado com sucesso")
            except Exception as e:
                logger.warning(f"Erro ao fechar driver: {e}")
