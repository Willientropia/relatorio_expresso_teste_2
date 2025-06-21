# backend/api/services/equatorial_service.py
import os
import json
import logging
import time
from datetime import datetime
from selenium import webdriver
try:
    import undetected_chromedriver as uc
except ImportError:  # Fallback if the package is not installed
    uc = None
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from django.conf import settings
from django.core.files.base import ContentFile
from api.models import Customer, UnidadeConsumidora, Fatura, FaturaTask, FaturaLog

logger = logging.getLogger(__name__)


class EquatorialService:
    def __init__(self, customer_id):
        self.customer = Customer.objects.get(id=customer_id)
        self.driver = None
        self.wait = None
        self.base_url = "https://goias.equatorialenergia.com.br"
        self.login_url = f"{self.base_url}/LoginGO.aspx"
        self.target_ucs = []  # Lista de UCs que devem ser baixadas
        
    def setup_driver(self):
        """Configura o driver de forma robusta e compatível com Docker."""
        try:
            logger.info("Inicializando driver (método robusto para Docker)...")
            
            chrome_options = Options()
            
            # --- Opções Essenciais para Docker/Headless ---
            # chrome_options.add_argument("--headless=new") # Comentado para visualização
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # --- Opções de Anti-Detecção (para Selenium padrão) ---
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

            # --- Configuração de Download (limpa e direta) ---
            download_dir = os.path.join(settings.MEDIA_ROOT, 'temp_faturas')
            os.makedirs(download_dir, exist_ok=True)
            prefs = {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "plugins.always_open_pdf_externally": True
            }
            chrome_options.add_experimental_option("prefs", prefs)

            # --- A PONTE ESTÁVEL ---
            # webdriver-manager baixa e gerencia a versão correta do chromedriver.
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Script de evasão injetado de forma segura
            evasion_script = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': evasion_script})
            
            self.wait = WebDriverWait(self.driver, 45)
            logger.info("Driver do Chrome inicializado com sucesso (sem 'magia').")
            return True
            
        except Exception as e:
            # Adicionar exc_info=True é ótimo para depurar logs
            logger.error(f"Erro ao configurar driver: {e}", exc_info=True)
            return False
    
    def login(self):
        """Realiza o login no sistema da Equatorial"""
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
            
            # Preenche data de nascimento
            if self.customer.data_nascimento:
                data_nascimento = self.customer.data_nascimento.strftime("%d/%m/%Y")
                logger.info(f"Data de nascimento a ser usada: {data_nascimento}")
                
                try:
                    # Tenta diferentes seletores para o campo de data
                    selectors = [
                        "input[name*='txtData']",
                        "input[id*='txtData']", 
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
            
            # Filtra apenas as UCs ativas do cliente
            active_ucs = self.customer.unidades_consumidoras.filter(
                data_vigencia_fim__isnull=True
            ).values_list('codigo', flat=True)
            
            # Define quais UCs devem ser processadas
            self.target_ucs = [uc for uc in all_ucs if uc in active_ucs]
            
            # Cria log de busca
            fatura_log = FaturaLog.objects.create(
                customer=self.customer,
                cpf_titular=self.customer.cpf_titular or self.customer.cpf,
                ucs_encontradas=all_ucs
            )
            
            faturas_encontradas = {}
            
            # Processa cada UC
            for uc_code in self.target_ucs:
                try:
                    # Encontra a UC no banco
                    uc_obj = self.customer.unidades_consumidoras.filter(
                        codigo=uc_code,
                        data_vigencia_fim__isnull=True
                    ).first()
                    
                    if not uc_obj:
                        continue
                    
                    # Atualiza task para processando
                    task = FaturaTask.objects.filter(
                        customer=self.customer,
                        unidade_consumidora=uc_obj,
                        status__in=['pending', 'processing']  # Procura por ambos os status
                    ).first()
                    
                    if task:
                        task.status = 'processing'
                        task.save()
                    
                    # Seleciona a UC
                    dropdown = self.driver.find_element(By.CSS_SELECTOR, "#CONTENT_comboBoxUC")
                    select = Select(dropdown)
                    select.select_by_value(uc_code)
                    time.sleep(2)
                    
                    # Configura opções
                    self.set_emission_type("completa")
                    self.set_emission_reason("ESV05")
                    
                    # Clica em emitir
                    emit_button = self.driver.find_element(By.CSS_SELECTOR, "#CONTENT_btEnviar")
                    emit_button.click()
                    time.sleep(4)
                    
                    # Processa faturas da UC
                    faturas_da_uc = self.extract_and_download_invoices(uc_obj)
                    faturas_encontradas[uc_code] = faturas_da_uc
                    
                    # Atualiza task
                    if task:
                        task.status = 'completed'
                        task.completed_at = datetime.now()
                        task.save()
                    
                    # Volta para Segunda Via
                    self.driver.get(f"{self.base_url}/AgenciaGO/Servi%C3%A7os/aberto/SegundaVia.aspx")
                    time.sleep(3)
                    
                except Exception as e:
                    logger.error(f"Erro ao processar UC {uc_code}: {e}")
                    if task:
                        task.status = 'failed'
                        task.error_message = str(e)
                        task.save()
                    continue
            
            # Atualiza log
            fatura_log.faturas_encontradas = faturas_encontradas
            fatura_log.save()
            
            return True
            
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
        
        logger.info(f"Iniciando extração e download das faturas para UC: {uc_obj.codigo}")
        try:
            # Encontra todas as faturas disponíveis
            rows = self.driver.find_elements(By.XPATH, "//tr[.//a[contains(text(), 'Download')]]")
            logger.info(f"Encontradas {len(rows)} faturas disponíveis para download na UC {uc_obj.codigo}")
            for row in rows:
                try:
                    # Extrai informações
                    month_element = row.find_element(By.XPATH, "./td[1]")
                    month_text = month_element.text.strip()
                    logger.info(f"Processando fatura do mês: {month_text}")
                    # Clica no download
                    download_link = row.find_element(By.XPATH, ".//a[contains(text(), 'Download')]")
                    logger.info(f"Clicando para baixar a fatura do mês: {month_text}")
                    download_link.click()
                    # Aguarda e trata popup
                    time.sleep(2)
                    try:
                        ok_button = self.driver.find_element(By.CSS_SELECTOR, "#CONTENT_btnModal")
                        if ok_button.is_displayed():
                            logger.info("Botão OK do modal encontrado, clicando...")
                            ok_button.click()
                            time.sleep(3)
                    except:
                        logger.info("Nenhum modal de confirmação após download.")
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
                        logger.info(f"Arquivo baixado localizado: {latest_file}")
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
                        logger.info(f"Fatura do mês {month_text} {'criada' if created else 'atualizada'} no banco de dados.")
                        # Remove arquivo temporário
                        os.remove(file_path)
                        logger.info(f"Arquivo temporário removido: {latest_file}")
                        faturas_info.append({
                            'mes': month_text,
                            'arquivo': fatura.arquivo.name,
                            'baixada': True
                        })
                    else:
                        logger.warning(f"Nenhum arquivo PDF encontrado após tentativa de download da fatura {month_text}.")
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
        logger.info(f"Finalizado processamento das faturas para UC: {uc_obj.codigo}")
        return faturas_info
    
    def close(self):
        """Fecha o navegador"""
        if self.driver:
            self.driver.quit()
    
    def _find_element_with_retry(self, selectors, max_attempts=3, wait_time=2):
        """Encontra um elemento usando diferentes seletores e tenta novamente em caso de falha."""
        for attempt in range(max_attempts):
            for by, selector in selectors:
                try:
                    element = self.driver.find_element(by, selector)
                    logger.info(f"Elemento encontrado com seletor: {selector}")
                    return element
                except Exception as e:
                    logger.warning(f"Não conseguiu encontrar elemento com seletor {selector}: {e}")
                    continue
            time.sleep(wait_time)
        
        raise Exception("Não foi possível encontrar o elemento com os seletores fornecidos.")
    
    def log_error(self, uc, message):
        """Registra um erro no processamento da UC."""
        logger.error(f"Erro na UC {uc.codigo}: {message}")
        # Aqui você pode adicionar lógica para registrar em um banco de dados ou enviar notificações
        FaturaTask.objects.filter(
            customer=self.customer,
            unidade_consumidora=uc
        ).update(status='failed', error_message=message)
    
    def processar_todas_faturas(self):
        """Processa o download de todas as faturas para as UCs ativas do cliente."""
        # Inicia o driver se ainda não estiver iniciado
        if not self.driver:
            self.setup_driver()
        
        # Realiza o login
        if not self.login():
            logger.error("Falha no login. Abortando processo.")
            return False
        
        # Aguarda um tempo para garantir que a página inicialize completamente
        time.sleep(5)
        
        # Obtém todas as UCs ativas do cliente
        ucs_ativas = self.customer.unidades_consumidoras.filter(data_vigencia_fim__isnull=True)
        
        if not ucs_ativas:
            logger.warning("Nenhuma UC ativa encontrada para o cliente.")
            return False
        
        # Inicia o processo para cada UC
        for uc in ucs_ativas:
            try:
                self._processar_faturas_por_uc(uc)
            except Exception as e:
                logger.error(f"Erro ao processar faturas para UC {uc.codigo}: {e}")
                self.log_error(uc, f"Erro geral no processamento: {e}")
                continue # Continua para a próxima UC
        
        return True

    def _processar_faturas_por_uc(self, uc):
        """Processa as faturas de uma única UC"""
        logger.info(f"Iniciando extração e download das faturas para UC: {uc.codigo}")
        
        # Seleciona a UC no dropdown, se houver mais de uma
        num_ucs = len(self.driver.find_elements(By.CSS_SELECTOR, "#ContentPlaceHolder1_gdvInstalacoes_lnkbtnInstalacao"))
        if num_ucs > 1:
            try:
                uc_link = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, f"//a[contains(text(), '{uc.codigo}')]")
                ))
                uc_link.click()
                time.sleep(5) # Aguarda o carregamento da página da UC
            except TimeoutException:
                logger.warning(f"Não foi possível selecionar a UC {uc.codigo}. Pulando.")
                self.log_error(uc, "Não foi possível selecionar a UC no site.")
                return

        # Encontra todas as faturas disponíveis
        try:
            faturas_disponiveis = self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table.faturas a.btnDownload"))
            )
            logger.info(f"Encontradas {len(faturas_disponiveis)} faturas disponíveis para download na UC {uc.codigo}")
        except TimeoutException:
            logger.info(f"Nenhuma fatura encontrada para a UC {uc.codigo}")
            return

        # Processa cada fatura
        for i in range(len(faturas_disponiveis)):
            # Re-encontra os elementos para evitar StaleElementReferenceException
            faturas_disponiveis = self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table.faturas a.btnDownload"))
            )
            fatura_link = faturas_disponiveis[i]
            
            # Extrai o mês de referência
            try:
                parent_row = fatura_link.find_element(By.XPATH, "./ancestor::tr")
                mes_referencia = parent_row.find_element(By.CSS_SELECTOR, "td:nth-child(1)").text.strip()
                logger.info(f"Processando fatura do mês: {mes_referencia}")
            except Exception as e:
                logger.warning(f"Não foi possível extrair o mês de referência: {e}")
                mes_referencia = f"desconhecido_{i}"

            # Verifica se a fatura já existe
            if Fatura.objects.filter(unidade_consumidora=uc, mes_referencia=mes_referencia).exists():
                # logger.info(f"Fatura para {mes_referencia} já existe. Pulando.")
                continue

            # Clica para baixar
            try:
                # logger.info(f"Clicando para baixar a fatura do mês: {mes_referencia}")
                self.driver.execute_script("arguments[0].click();", fatura_link)
                time.sleep(2) # Espera o início do download
                
                # Lida com o modal de confirmação
                self._handle_modal_and_download(uc, mes_referencia)

            except Exception as e:
                logger.error(f"Erro ao clicar no link de download para {mes_referencia}: {e}")
                self.log_error(uc, f"Erro no download da fatura {mes_referencia}: {e}")
                # Tenta fechar qualquer modal que possa ter travado o processo
                self._close_modal_if_present()
        
        logger.info(f"Finalizado processamento das faturas para UC: {uc.codigo}")

    def _handle_modal_and_download(self, uc, mes_referencia):
        """Lida com o modal de confirmação e aguarda o download do PDF."""
        try:
            # Espera e clica no botão "OK" do modal
            modal_ok_button = self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "div.modal-confirm a.btn-primary")
            ))
            # logger.info("Botão OK do modal encontrado, clicando...")
            modal_ok_button.click()
            
            # Aguarda o download do arquivo
            download_dir = os.path.join(settings.MEDIA_ROOT, 'temp_faturas')
            arquivo_baixado = self._wait_for_download(download_dir)
            
            if arquivo_baixado:
                # logger.info(f"Arquivo baixado localizado: os.path.basename(arquivo_baixado)}")
                self._save_fatura(uc, mes_referencia, arquivo_baixado)
            else:
                logger.error(f"Download da fatura {mes_referencia} falhou (timeout).")
                self.log_error(uc, f"Timeout no download da fatura {mes_referencia}.")

        except TimeoutException:
            logger.warning(f"Modal de confirmação não apareceu ou não foi encontrado para {mes_referencia}.")
            # Se o modal não aparecer, talvez o download tenha iniciado diretamente
            download_dir = os.path.join(settings.MEDIA_ROOT, 'temp_faturas')
            arquivo_baixado = self._wait_for_download(download_dir, timeout=15) # Timeout menor
            if arquivo_baixado:
                # logger.info(f"Arquivo baixado (sem modal) localizado: {os.path.basename(arquivo_baixado)}")
                self._save_fatura(uc, mes_referencia, arquivo_baixado)
            else:
                logger.warning(f"Nenhum arquivo baixado para {mes_referencia} mesmo sem modal.")
        
        except Exception as e:
            logger.error(f"Erro inesperado ao lidar com modal/download para {mes_referencia}: {e}")
            self.log_error(uc, f"Erro no modal/download da fatura {mes_referencia}: {e}")


    def _wait_for_download(self, download_dir, timeout=60):
        """Aguarda até que um arquivo seja baixado no diretório especificado."""
        import time
        seconds = 0
        while seconds < timeout:
            time.sleep(1)
            seconds += 1
            
            # Verifica se há arquivos PDF no diretório de download
            files = [f for f in os.listdir(download_dir) if f.endswith('.pdf')]
            if files:
                # Retorna o caminho completo do primeiro arquivo encontrado
                return os.path.join(download_dir, files[0])
        
        return None  # Nenhum arquivo encontrado dentro do tempo limite
    
    def _save_fatura(self, uc, mes_referencia, arquivo_baixado):
        """Salva a fatura no banco de dados e renomeia o arquivo."""
        # Renomeia o arquivo para incluir o ID do cliente, ano e mês
        ano = mes_referencia.split('/')[1]
        mes = mes_referencia.split('/')[0]
        nome_arquivo = f"fatura_{self.customer.id}_{ano}_{mes}.pdf"
        
        # Move o arquivo para o diretório final
        final_path = os.path.join(settings.MEDIA_ROOT, 'faturas', str(self.customer.id), ano, mes, nome_arquivo)
        os.makedirs(os.path.dirname(final_path), exist_ok=True)
        os.rename(arquivo_baixado, final_path)
        
        # Atualiza o registro da fatura no banco de dados
        fatura = Fatura.objects.get(unidade_consumidora=uc, mes_referencia=mes_referencia)
        fatura.arquivo_pdf.name = os.path.join('faturas', str(self.customer.id), ano, mes, nome_arquivo)
        fatura.save()
        
        # logger.info(f"Fatura do mês {mes_referencia} criada no banco de dados.")

        # Limpa o arquivo temporário
        try:
            os.remove(final_path)
            # logger.info(f"Arquivo temporário removido: os.path.basename(final_path)}")
        except OSError as e:
            logger.error(f"Erro ao remover arquivo temporário {final_path}: {e}")

    def _close_modal_if_present(self):
        """Tenta fechar um modal de confirmação se ele estiver visível."""
        try:
            modal = self.driver.find_element(By.CSS_SELECTOR, "div.modal-confirm")
            if modal.is_displayed():
                close_button = modal.find_element(By.CSS_SELECTOR, "button.close")
                close_button.click()
                logger.info("Modal de confirmação fechado.")
                time.sleep(2)  # Aguarda o fechamento do modal
        except Exception as e:
            logger.warning(f"Não foi possível fechar o modal de confirmação: {e}")
    
    def step5_extract_ucs_and_create_structure(self):
        """
        Etapa 5: Extrai UCs, cria log no banco de dados.
        Adaptado do script original para integrar com Django Models.
        """
        try:
            logger.info("ETAPA 5: Extraindo UCs e criando estrutura de relatório...")
            time.sleep(3)

            # 1. EXTRAIR NOME DO CLIENTE (já temos em self.customer)
            client_name = self.customer.nome
            logger.info(f"Cliente: {client_name}")

            # 2. EXTRAIR UCS DO DROPDOWN
            logger.info("Extraindo UCs do dropdown...")
            uc_dropdown = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id*='comboBoxUC']")))
            select = Select(uc_dropdown)
            options = select.options
            
            ucs_list = [opt.get_attribute('value').strip() for opt in options if opt.get_attribute('value').strip()]
            
            if not ucs_list:
                logger.error("Nenhuma UC encontrada no dropdown!")
                return False

            logger.info(f"{len(ucs_list)} UCs encontradas: {ucs_list}")

            # 3. CRIAR ESTRUTURA DE "RELATÓRIO" (LOG NO BANCO)
            logger.info("Criando log de busca no banco de dados...")
            self.fatura_log = FaturaLog.objects.create(
                customer=self.customer,
                cpf_titular=self.customer.cpf_titular or self.customer.cpf,
                status='processing',
                ucs_encontradas=ucs_list,
                total_ucs_encontradas=len(ucs_list)
            )
            logger.info(f"Log de busca criado com ID: {self.fatura_log.id}")

            # 4. SALVAR INFORMAÇÕES NA CLASSE
            self.ucs_list = ucs_list
            self.faturas_encontradas_geral = {} # Dicionário para armazenar resultados

            logger.info("ETAPA 5 CONCLUÍDA COM SUCESSO!")
            return True

        except Exception as e:
            logger.error(f"Erro na ETAPA 5: {e}", exc_info=True)
            if hasattr(self, 'fatura_log'):
                self.fatura_log.status = 'failed'
                self.fatura_log.error_message = f"Erro na Etapa 5: {e}"
                self.fatura_log.save()
            return False

    def step6_process_each_uc(self):
        """
        Etapa 6: Processa cada UC individualmente.
        """
        try:
            logger.info("ETAPA 6: Processando cada UC individualmente...")
            if not hasattr(self, 'ucs_list') or not self.ucs_list:
                logger.error("Lista de UCs não encontrada! Execute a Etapa 5 primeiro.")
                return False

            active_ucs_in_db = list(self.customer.unidades_consumidoras.filter(
                data_vigencia_fim__isnull=True
            ).values_list('codigo', flat=True))
            
            logger.info(f"UCs ativas no banco de dados para este cliente: {active_ucs_in_db}")

            # Processa apenas as UCs que estão na lista do dropdown E ativas no nosso DB
            ucs_to_process = [uc for uc in self.ucs_list if uc in active_ucs_in_db]
            logger.info(f"Total de UCs para processar: {len(ucs_to_process)}")

            for i, uc_code in enumerate(ucs_to_process, 1):
                logger.info(f"--- PROCESSANDO UC {i}/{len(ucs_to_process)}: {uc_code} ---")
                
                # Pega o objeto UC do banco
                uc_obj = UnidadeConsumidora.objects.get(codigo=uc_code, customer=self.customer)

                # Cria ou atualiza a Task para esta UC
                task, _ = FaturaTask.objects.update_or_create(
                    customer=self.customer,
                    unidade_consumidora=uc_obj,
                    defaults={'status': 'processing', 'error_message': None}
                )

                try:
                    if self._process_single_uc(uc_obj):
                        logger.info(f"UC {uc_code} processada com sucesso!")
                        task.status = 'completed'
                        task.completed_at = datetime.now()
                        task.save()
                    else:
                        raise Exception("Falha no processamento individual da UC")

                except Exception as e:
                    logger.error(f"Erro ao processar UC {uc_code}: {e}", exc_info=True)
                    task.status = 'failed'
                    task.error_message = str(e)
                    task.save()
                
                # Volta para a página de Segunda Via antes da próxima UC
                if i < len(ucs_to_process):
                    self._navigate_back_to_second_copy()

            logger.info("ETAPA 6 CONCLUÍDA!")
            self.fatura_log.status = 'completed'
            self.fatura_log.faturas_encontradas = self.faturas_encontradas_geral
            self.fatura_log.save()
            return True

        except Exception as e:
            logger.error(f"Erro inesperado na ETAPA 6: {e}", exc_info=True)
            if hasattr(self, 'fatura_log'):
                self.fatura_log.status = 'failed'
                self.fatura_log.error_message = f"Erro na Etapa 6: {e}"
                self.fatura_log.save()
            return False

    def _process_single_uc(self, uc_obj):
        """
        Processa uma única UC: seleciona, configura, emite e chama o download.
        """
        uc_code = uc_obj.codigo
        logger.info(f"Processando UC: {uc_code}")

        # 1. Selecionar a UC no dropdown
        self._select_uc_in_dropdown(uc_code)
        time.sleep(3)

        # 2. Configurar tipo de emissão
        self._set_emission_type("completa")

        # 3. Configurar motivo da emissão
        self._set_emission_reason("ESV05") # ESV05 = Outros

        # 4. Clicar no botão "Emitir"
        self._click_emit_button()
        time.sleep(4)

        # 5. Verificar se chegou na página de faturas e processá-las
        if self._verify_invoices_page():
            logger.info(f"Navegação bem-sucedida para faturas da UC {uc_code}")
            
            # 6. Extrair e baixar faturas (Etapa 7)
            faturas_da_uc = self.step7_extract_and_download_invoices(uc_obj)
            self.faturas_encontradas_geral[uc_code] = faturas_da_uc
            return True
        else:
            logger.error(f"Não foi possível acessar a página de faturas da UC {uc_code}")
            return False

    def _navigate_back_to_second_copy(self):
        """Navega de volta para a página de Segunda Via."""
        try:
            logger.info("Navegando de volta para página de Segunda Via...")
            segunda_via_url = f"{self.base_url}/AgenciaGO/Servi%C3%A7os/aberto/SegundaVia.aspx"
            self.driver.get(segunda_via_url)
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id*='comboBoxUC']")))
            logger.info("Retornou com sucesso para página de Segunda Via")
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Erro ao navegar de volta para Segunda Via: {e}", exc_info=True)
            return False

    def _select_uc_in_dropdown(self, uc_code):
        """Seleciona uma UC específica no dropdown."""
        logger.info(f"Selecionando UC {uc_code} no dropdown...")
        dropdown = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id*='comboBoxUC']")))
        select = Select(dropdown)
        select.select_by_value(uc_code)

    def _set_emission_type(self, emission_type="completa"):
        """Configura o tipo de emissão."""
        logger.info(f"Configurando tipo de emissão para '{emission_type}'...")
        dropdown = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id*='cbTipoEmissao']")))
        select = Select(dropdown)
        select.select_by_value(emission_type)

    def _set_emission_reason(self, reason_code="ESV05"):
        """Configura o motivo da emissão."""
        logger.info(f"Configurando motivo da emissão para '{reason_code}'...")
        dropdown = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[id*='cbMotivo']")))
        select = Select(dropdown)
        select.select_by_value(reason_code)

    def _click_emit_button(self):
        """Clica no botão 'Emitir'."""
        logger.info("Clicando no botão 'Emitir'...")
        button = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[id*='btEnviar']")))
        self.driver.execute_script("arguments[0].click();", button)

    def _verify_invoices_page(self):
        """Verifica se a página de faturas foi carregada."""
        try:
            logger.info("Verificando se chegou na página de faturas...")
            self.wait.until(EC.any_of(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'faturas em aberto')]")),
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'segunda via')]")),
                EC.presence_of_element_located((By.XPATH, "//tr[.//a[contains(text(), 'Download')]]"))
            ))
            logger.info("Página de faturas identificada com sucesso.")
            return True
        except TimeoutException:
            logger.warning("Não foi possível confirmar se está na página de faturas. Nenhum indicador encontrado.")
            return False

    def step7_extract_and_download_invoices(self, uc_obj):
        """
        Etapa 7: Extrai informações das faturas, faz o download e salva no banco.
        """
        uc_code = uc_obj.codigo
        logger.info(f"ETAPA 7: Processando faturas da UC {uc_code}...")
        faturas_processadas_info = []
        
        try:
            # 1. ENCONTRAR TABELA DE FATURAS
            invoice_rows = self.driver.find_elements(By.XPATH, "//tr[.//a[contains(text(), 'Download')]]")
            if not invoice_rows:
                logger.info(f"Nenhuma fatura com link de 'Download' encontrada para a UC {uc_code}")
                return []

            logger.info(f"Encontradas {len(invoice_rows)} faturas disponíveis para download.")

            # Itera sobre uma cópia dos índices para evitar StaleElementReferenceException
            for i in range(len(invoice_rows)):
                # Re-encontra os elementos a cada iteração
                all_rows = self.driver.find_elements(By.XPATH, "//tr[.//a[contains(text(), 'Download')]]")
                if i >= len(all_rows):
                    logger.warning("A lista de faturas mudou durante a iteração. Interrompendo.")
                    break
                
                row = all_rows[i]
                
                try:
                    # 2. EXTRAIR INFORMAÇÕES
                    month_text = row.find_element(By.XPATH, "./td[1]").text.strip()
                    valor_text = row.find_element(By.XPATH, "./td[3]").text.strip()
                    vencimento_text = row.find_element(By.XPATH, "./td[2]").text.strip()
                    download_link = row.find_element(By.XPATH, ".//a[contains(text(), 'Download')]")
                    
                    logger.info(f"Processando fatura {i+1}/{len(invoice_rows)}: Mês={month_text}, Valor={valor_text}")

                    # 3. FAZER DOWNLOAD
                    start_time = time.time()
                    self.driver.execute_script("arguments[0].click();", download_link)

                    # 4. TRATAR POPUP
                    time.sleep(2) # Espera para o popup aparecer
                    try:
                        ok_button = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input#CONTENT_btnModal")));
                        logger.info("Popup detectado! Clicando em OK...")
                        self.driver.execute_script("arguments[0].click();", ok_button)
                    except TimeoutException:
                        logger.info("Nenhum popup de confirmação apareceu.")
                    
                    # 5. AGUARDAR E VERIFICAR DOWNLOAD
                    download_dir = os.path.join(settings.MEDIA_ROOT, 'temp_faturas')
                    downloaded_file_path = self._wait_for_download_complete(download_dir, start_time)

                    if downloaded_file_path:
                        logger.info(f"Arquivo baixado: {os.path.basename(downloaded_file_path)}")
                        
                        # 6. SALVAR NO BANCO DE DADOS
                        fatura = self._save_fatura_to_db(uc_obj, month_text, vencimento_text, valor_text, downloaded_file_path)
                        
                        faturas_processadas_info.append({
                            'mes': month_text,
                            'arquivo': fatura.arquivo.name,
                            'baixada': True
                        })
                        os.remove(downloaded_file_path) # Remove o arquivo temporário
                    else:
                        logger.warning(f"Download da fatura {month_text} falhou ou não foi detectado.")
                        faturas_processadas_info.append({
                            'mes': month_text,
                            'arquivo': None,
                            'baixada': False,
                            'erro': 'Download não concluído'
                        })

                except Exception as e:
                    logger.error(f"Erro ao processar uma linha de fatura: {e}", exc_info=True)
                    # Se a página recarregou, pode dar StaleElement... o loop principal deve continuar
                    continue
            
            logger.info(f"ETAPA 7 CONCLUÍDA para UC {uc_code}!")
            return faturas_processadas_info

        except Exception as e:
            logger.error(f"Erro geral na ETAPA 7 para UC {uc_code}: {e}", exc_info=True)
            return faturas_processadas_info # Retorna o que conseguiu processar

    def _wait_for_download_complete(self, download_folder, start_time, timeout=60):
        """Aguarda o download ser concluído e retorna o path do novo arquivo."""
        end_time = time.time() + timeout
        while time.time() < end_time:
            # Procura por arquivos PDF que foram modificados após o clique no download
            files = [os.path.join(download_folder, f) for f in os.listdir(download_folder) if f.endswith('.pdf')]
            for f_path in files:
                if os.path.getmtime(f_path) > start_time:
                    # Verifica se o download ainda está em progresso (.crdownload)
                    if not any(file.endswith('.crdownload') for file in os.listdir(download_folder)):
                        return f_path
            time.sleep(1)
        return None

    def _save_fatura_to_db(self, uc_obj, month_text, vencimento_text, valor_text, file_path):
        """Cria ou atualiza a fatura no banco de dados."""
        
        # Converte data e valor
        try:
            data_vencimento = datetime.strptime(vencimento_text, '%d/%m/%Y').date()
        except ValueError:
            data_vencimento = None
        
        try:
            # Remove 'R$ ' e substitui vírgula por ponto
            valor = float(valor_text.replace('R$', '').strip().replace('.', '').replace(',', '.'))
        except (ValueError, TypeError):
            valor = 0.0

        with open(file_path, 'rb') as f:
            file_content = ContentFile(f.read())

        # Gera um nome de arquivo seguro
        file_name = f"fatura_{uc_obj.codigo}_{month_text.replace('/', '-')}.pdf"

        fatura, created = Fatura.objects.update_or_create(
            customer=self.customer,
            unidade_consumidora=uc_obj,
            mes_referencia=month_text,
            defaults={
                'data_vencimento': data_vencimento,
                'valor': valor,
                'status': 'aberta' # ou extrair do site se possível
            }
        )
        fatura.arquivo.save(file_name, file_content, save=True)
        
        logger.info(f"Fatura do mês {month_text} {'criada' if created else 'atualizada'} no banco.")
        return fatura

    def run(self):
        """
        Executa o fluxo completo de login, extração e download de faturas.
        Este é o novo método de entrada principal.
        """
        try:
            if not self.setup_driver():
                raise Exception("Falha ao configurar o driver.")
            
            if not self.login():
                raise Exception("Falha no processo de login.")

            if not self.step5_extract_ucs_and_create_structure():
                raise Exception("Falha na Etapa 5: Extração de UCs.")

            if not self.step6_process_each_uc():
                raise Exception("Falha na Etapa 6: Processamento das UCs.")

            logger.info("Processo concluído com sucesso!")
            return True

        except Exception as e:
            logger.error(f"Ocorreu um erro no fluxo principal: {e}", exc_info=True)
            # Garante que o log principal reflita o erro
            if hasattr(self, 'fatura_log') and self.fatura_log:
                self.fatura_log.status = 'failed'
                self.fatura_log.error_message = str(e)
                self.fatura_log.save()
            return False
        finally:
            self.close()
